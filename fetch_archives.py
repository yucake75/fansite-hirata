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
tags / game / notes は API では取得できないため、
新規追加分は手動で書き換えてもらう前提のデフォルト値を入れる。
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

    while True:
        print(f"  取得中: offset={offset} ...", flush=True)
        data = fetch_movies(offset=offset, limit=limit)
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


def normalize(movie: dict) -> dict:
    """API レスポンスを既存JSONのフォーマットに変換する"""
    return {
        "id":       movie.get("id"),              # ツイキャスの movie id（文字列）をそのまま使う
        "title":    movie.get("title") or f"配信 #{movie.get('id')}",
        "date":     to_date_str(movie.get("created")),
        "tags":     ["other"],                      # API では分類不可。後で手動編集してください
        "url":      movie.get("link"),
        "game":     None,                            # 同上
        "notes":    "",                               # 同上
        "_synced":  True,                             # 自動取得分の識別用フラグ（手動編集時に消してOK）
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

    fetched = [normalize(m) for m in raw_movies]
    print(f"API から録画あり {len(fetched)} 件取得")

    existing = load_existing(OUTPUT_FILE)
    merged, new_count = merge(existing, fetched)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"完了: 新着 {new_count} 件 / 合計 {len(merged)} 件 → {OUTPUT_FILE}")
    if new_count > 0:
        print("※ 新着分の tags / game / notes は未分類です。必要に応じて手動で編集してください。")


if __name__ == "__main__":
    main()
