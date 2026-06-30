#!/usr/bin/env python3
"""
既存 archives.json の再分類スクリプト（一度きり実行用）

すでに登録済みのアーカイブのうち、game が未設定（null）のものだけを対象に、
game_keywords.json のキーワードとタイトルを照合してゲーム名を自動セットする。

- マッチしたもの: tags に "game" を追加（重複しないように）、game をセット
- マッチしなかったもの: 変更せず、最後に一覧表示するので手動で直す

使い方:
  python3 reclassify_games.py
"""

import json
import os

ARCHIVES_FILE = "archives.json"
GAME_KEYWORDS_FILE = "game_keywords.json"


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

    updated = []
    unmatched = []

    for item in archives:
        # すでに game が設定されているものはスキップ（手動データを壊さない）
        if item.get("game"):
            continue

        title = item.get("title", "")
        matched = detect_game(title, game_keywords)

        if matched:
            item["game"] = matched
            tags = item.get("tags", [])
            if "game" not in tags:
                tags.append("game")
            if "other" in tags:
                tags.remove("other")
            item["tags"] = tags
            updated.append(item)
        else:
            unmatched.append(item)

    with open(ARCHIVES_FILE, "w", encoding="utf-8") as f:
        json.dump(archives, f, ensure_ascii=False, indent=2)

    print(f"再分類完了: {len(updated)} 件を自動更新しました\n")

    if updated:
        print("【自動更新したもの】")
        for item in updated:
            print(f"  - {item['title']} -> {item['game']}")
        print()

    if unmatched:
        print(f"【マッチしなかったもの（{len(unmatched)}件）: 手動で archives.json の game / tags を編集してください】")
        for item in unmatched:
            print(f"  - id={item.get('id')}: {item['title']}")
    else:
        print("マッチしなかったものはありませんでした。")


if __name__ == "__main__":
    main()