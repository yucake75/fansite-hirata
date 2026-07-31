#!/usr/bin/env python3
"""
既存 archives.json の再分類スクリプト（タグルール一括適用・何度実行してもOK）

タグの付け方ルール：
- デフォルトは "talk"（雑談）。"other" は使わない。
- game_keywords.json に一致するタイトルがあれば game をセットし、
  tags は ["game"] のみにする（他のタグは全部外す）。
- すでに tags に "game" または "collab" が手動で入っている場合も、
  そのタグだけにして他は全部外す（例: ["talk","collab"] -> ["collab"]）。
- 上記いずれにも該当しない場合は tags を ["talk"] にする
  （"other" のみだった場合もこれに統一される。後で手動で talk 以外に直してOK）。

全件を対象に毎回タグを再計算するので、何度実行しても安全（冪等）。
game がすでに手動セットされていても、タグの形だけは上記ルールに揃える。

使い方:
  python3 reclassify_games.py
"""

import json
import os

ARCHIVES_FILE = "archives.json"
GAME_KEYWORDS_FILE = "game_keywords.json"

# このタグが1つでも立っていたら「専用タグ」として他を排除する優先タグ
EXCLUSIVE_TAGS = ["game", "collab"]


def load_game_keywords(path: str = GAME_KEYWORDS_FILE) -> list[list[str]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
        return data.get("games", [])


def detect_game(title: str, game_keywords: list[list[str]]) -> str | None:
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


def resolve_tags(item: dict, matched_game: str | None) -> list[str]:
    """
    新ルールでタグを再計算する。
    優先順位: game判定 > 既存collabタグ > 既存gameタグ > デフォルトtalk
    """
    existing_tags = item.get("tags", [])

    # キーワードでゲームと判定できた場合は問答無用で ["game"]
    if matched_game:
        return ["game"]

    # すでに専用タグ（game/collab）が手動で付いているなら、そのタグだけ残す
    for exclusive in EXCLUSIVE_TAGS:
        if exclusive in existing_tags:
            return [exclusive]

    # それ以外（talk, other, 未分類など）はすべて talk に統一
    return ["talk"]


def main():
    if not os.path.exists(ARCHIVES_FILE):
        print(f"エラー: {ARCHIVES_FILE} が見つかりません")
        return
    if not os.path.exists(GAME_KEYWORDS_FILE):
        print(f"エラー: {GAME_KEYWORDS_FILE} が見つかりません")
        return

    with open(ARCHIVES_FILE, encoding="utf-8") as f:
        archives = json.load(f)

    game_keywords = load_game_keywords()

    game_matched = []
    tag_changed = []

    for item in archives:
        title = item.get("title", "")
        before_tags = list(item.get("tags", []))
        before_game = item.get("game")

        # game が未設定のものだけキーワード照合（手動セット済みのgame名は壊さない）
        matched_game = None
        if not before_game:
            matched_game = detect_game(title, game_keywords)
            if matched_game:
                item["game"] = matched_game

        item["tags"] = resolve_tags(item, matched_game)

        if matched_game:
            game_matched.append(item)
        if item["tags"] != before_tags:
            tag_changed.append((item, before_tags))

    with open(ARCHIVES_FILE, "w", encoding="utf-8") as f:
        json.dump(archives, f, ensure_ascii=False, indent=2)

    print(f"処理完了: 全{len(archives)}件中 タグ変更 {len(tag_changed)}件 / ゲーム新規判定 {len(game_matched)}件\n")

    if game_matched:
        print("【今回新たにゲーム判定したもの】")
        for item in game_matched:
            print(f"  - {item['title']} -> {item['game']}")
        print()

    if tag_changed:
        print("【タグを変更したもの】")
        for item, before in tag_changed:
            print(f"  - {item['title']}: {before} -> {item['tags']}")
    else:
        print("タグの変更はありませんでした。")


if __name__ == "__main__":
    main()