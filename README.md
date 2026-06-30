# fansite-rader

## アーカイブ自動取得セットアップ

ツイキャスの新着アーカイブを自動取得し、`archives.json` に追記する仕組みです。

### 1. ツイキャス API アプリを登録

https://twitcasting.tv/developer.php で新規登録し、`ClientID` / `ClientSecret` を取得します。

### 2. GitHub Secrets を設定

リポジトリの **Settings → Secrets and variables → Actions** で以下を登録：

| シークレット名 | 値 |
|---|---|
| `TWITCASTING_USER_ID` | 対象ユーザーの screen_id（例: `xxxxx`） |
| `TWITCASTING_CLIENT_ID` | 手順1のClientID |
| `TWITCASTING_CLIENT_SECRET` | 手順1のClientSecret |

### 3. 動作確認

**Actions → Update TwitCasting Archives → Run workflow** で手動実行できます。
以降は毎日 JST 10:00 に自動実行され、新着アーカイブのみ `archives.json` の先頭に追記されます。

### 注意点

- 新着分は `tags`（カテゴリ）・`game`（ゲーム名）・`notes`（コメント）を API から取得できないため、ひな形（`tags: ["other"]`, `game: null`, `notes: ""`）で追加されます。サイトに正しく分類表示させるには、追加後に手動でこの3項目を編集してください。
- 重複判定は配信URL（`url`）で行うため、既存の手動データは上書きされません。
- 録画（アーカイブ）が残っている配信のみが対象です。
