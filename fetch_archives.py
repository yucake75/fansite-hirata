#!/usr/bin/env python3
"""
ツイキャス アーカイブ自動取得スクリプト

既存の archives.json は以下の配列フォーマット：
[
  {
    "id": 1,
    "title": "...",
    "date": "2025-05-10",
    "tags": ["game"],
    "url": "https://twitcasting.tv/xxxxx/movie/000001",
    "game": "Minecraft",
    "notes": "..."
  },
  ...
]

このスクリプトは TwitCasting API から新着アーカイブを取得し、
既存データを壊さずに「新着分だけ」を先頭に追記する。
tags / game は game_keywords.json のキーワードリストとタイトルを照合し、
一致すれば自動判定する。マッチしなかった場合のみ tags:["other"] / game:null
のままにし、手動編集してもらう。notes は API では取得できないため常に空。
"""

import json
import os
import sys
import time
import base64
import urllib.request
import urllib.error

# ============================================================
# 設定 — GitHub Actions の Secrets / 環境変数で上書き可能
# ============================================================
USER_ID       = os.environ.get("TWITCASTING_USER_ID", "YOUR_USER_ID")
CLIENT_ID     = os.environ.get("TWITCASTING_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("TWITCASTING_CLIENT_SECRET", "")
OUTPUT_FILE   = os.environ.get("OUTPUT_FILE", "archives.json")
GAME_KEYWORDS_FILE = os.environ.get("GAME_KEYWORDS_FILE", "game_keywords.json")

BASE_URL = "https://apiv2.twitcasting.tv"

_token = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
AUTH_HEADER = f"Basic {_token}"


def fetch_movies(offset: int = 0, limit: int = 50) -> dict:
    """ユーザームービーリスト API を呼び出す"""
    url = f"{BASE_URL}/users/{USER_ID}/movies?offset={offset}&limit={limit}"
    req = urllib.request.Request(
        url,
        headers={
            "X-Api-Version": "2.0",
            "Authorization": AUTH_HEADER,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode())


def fetch_all_movies() -> list[dict]:
    """ページネーションで全アーカイブを取得する"""
    all_movies = []
    offset = 0
    limit = 50
    MAX_OFFSET = 1000  # TwitCasting API の offset 上限

    while True:
        if offset > MAX_OFFSET:
            print(f"  offset が上限({MAX_OFFSET})に達したため取得を終了します")
            break

        print(f"  取得中: offset={offset} ...", flush=True)
        try:
            data = fetch_movies(offset=offset, limit=limit)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                print(f"  offset={offset} で400エラー。取得できる範囲はここまでと判断し終了します")
                break
            raise
        movies = data.get("movies", [])
        total = data.get("total_count", 0)

        all_movies.extend(movies)
        offset += len(movies)

        if offset >= total or len(movies) == 0:
            break

        time.sleep(1)  # レートリミット対策 (60 req/min)

    return all_movies


def to_date_str(unix_ts) -> str:
    """UNIXタイムスタンプ -> 'YYYY-MM-DD'"""
    if not unix_ts:
        return ""
    from datetime import datetime, timezone
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).strftime("%Y-%m-%d")


def load_game_keywords(path: str = GAME_KEYWORDS_FILE) -> list[list[str]]:
    """ゲーム名キーワードリストを読み込む。なければ空リスト"""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("games", [])
    return []


def detect_game(title: str, game_keywords: list[list[str]]) -> str | None:
    """
    タイトル文字列にキーワードリストの単語が含まれていたら、
    対応する正式名（リストの先頭要素）を返す。マッチしなければ None。
    """
    if not title:
        return None
    for aliases in game_keywords:
        if not aliases:
            continue
        canonical = aliases[0]
        for alias in aliases:
            if alias and alias.lower() in title.lower():
                return canonical
    return None


def normalize(movie: dict, game_keywords: list[list[str]]) -> dict:
    """API レスポンスを既存JSONのフォーマットに変換する"""
    title = movie.get("title") or f"配信 #{movie.get('id')}"
    matched_game = detect_game(title, game_keywords)

    return {
        "id":       movie.get("id"),              # ツイキャスの movie id（文字列）をそのまま使う
        "title":    title,
        "date":     to_date_str(movie.get("created")),
        "tags":     ["game"] if matched_game else ["other"],  # マッチすればgameタグ、未マッチはother（要手動確認）
        "url":      movie.get("link"),
        "game":     matched_game,                              # キーワード一覧から自動判定。未マッチはNone
        "notes":    "",                                         # API では取得不可。後で手動編集してください
        "_synced":  True,                                       # 自動取得分の識別用フラグ（手動編集時に消してOK）
    }


def load_existing(path: str) -> list[dict]:
    """既存の archives.json（配列）を読み込む。なければ空配列"""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    return []


def next_id(existing: list[dict]) -> int:
    """既存の id（数値前提）の最大値+1から連番を振る"""
    nums = [a["id"] for a in existing if isinstance(a.get("id"), int)]
    return (max(nums) + 1) if nums else 1


def merge(existing: list[dict], fetched: list[dict]) -> tuple[list[dict], int]:
    """
    既存データと新規取得をマージ。
    同一配信の重複判定は url（ツイキャスの動画URLは一意）で行う。
    新着は既存リストの先頭に追加し、id は連番を振り直さず継続させる。
    """
    existing_urls = {a.get("url") for a in existing}
    new_items = [m for m in fetched if m.get("url") not in existing_urls]

    # 新しい配信ほど先に取得されるため、その順のまま id を振る
    nid = next_id(existing)
    for item in new_items:
        item["id"] = nid
        nid += 1

    merged = new_items + existing
    return merged, len(new_items)


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("エラー: TWITCASTING_CLIENT_ID / TWITCASTING_CLIENT_SECRET が設定されていません")
        sys.exit(1)

    print(f"対象ユーザー: {USER_ID}")
    print("アーカイブ取得開始...")

    try:
        raw_movies = fetch_all_movies()
    except urllib.error.HTTPError as e:
        print(f"APIエラー: {e.code} {e.reason}")
        sys.exit(1)

    # is_recorded（録画あり）のみ対象にする
    raw_movies = [m for m in raw_movies if m.get("is_recorded")]

    game_keywords = load_game_keywords()
    print(f"ゲームキーワード {len(game_keywords)} 件を読み込みました")

    fetched = [normalize(m, game_keywords) for m in raw_movies]
    print(f"API から録画あり {len(fetched)} 件取得")

    auto_matched = sum(1 for f in fetched if f["game"])
    print(f"  うちゲーム自動判定できたもの: {auto_matched} 件")

    existing = load_existing(OUTPUT_FILE)
    merged, new_count = merge(existing, fetched)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"完了: 新着 {new_count} 件 / 合計 {len(merged)} 件 → {OUTPUT_FILE}")
    if new_count > 0:
        print("※ ゲーム名が自動判定できなかった新着は tags:[\"other\"] / game:null のままです。")
        print("  game_keywords.json にキーワードを追加するか、archives.json を直接編集してください。")


if __name__ == "__main__":
    main()