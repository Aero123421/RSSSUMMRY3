# RSS Discord Bot

RSS・Atomフィードを監視し、新規記事をAIで処理してDiscordに投稿するボットシステム

## 特徴

- 📰 複数のRSS/Atomフィードの監視
- 🤖 LM Studio API / Google Gemini APIによるAI処理
  - 日本語への翻訳
  - 指定文字数での要約生成
  - ジャンル分類
- 💬 Discord Embedを使った美しい記事投稿
- ⚙️ スラッシュコマンドによる簡単操作
- 🐳 Docker環境での簡単デプロイ
- 🔓 管理者制限の設定可能（ADMIN_ONLY環境変数）

## セットアップ

### 1. 環境変数の設定

`.env`ファイルを編集して、必要な設定を入力してください：

```env
# Discord Bot Token
DISCORD_TOKEN=your_discord_token_here

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# LM Studio API Settings
LMSTUDIO_API_URL=http://localhost:1234/v1/chat/completions
LMSTUDIO_API_KEY=lm-studio

# Bot Settings
ADMIN_USER_ID=your_admin_user_id_here
DEFAULT_CHECK_INTERVAL=15
ADMIN_ONLY=false
```

### 2. Dockerでの起動

```bash
# Docker Composeで起動
docker-compose up -d

# ログの確認
docker-compose logs -f
```

### 3. 直接Pythonで起動

```bash
# 依存関係のインストール
pip install -r requirements.txt

# ボットの起動
python bot.py
```

## 使用方法

### スラッシュコマンド

- `/rss_config` - 設定パネル表示（ADMIN_ONLY=trueの場合は管理者のみ）
- `/addrss <URL> [チャンネル名]` - RSSフィードを追加
- `/rss_list_feeds` - 登録フィード一覧表示
- `/rss_check_now` - 即座にフィードをチェック
- `/rss_status` - ボットのステータス表示

### 基本的な使用手順

1. ボットをDiscordサーバーに招待
2. `/rss_config`で初期設定を行う
3. `/addrss <RSSのURL>`でフィードを追加
4. 自動的にチャンネルが作成され、記事が投稿される

## 管理者制限について

このボットでは管理者制限を設定できます：

- **ADMIN_ONLY=false（デフォルト）**: 誰でも全てのコマンドを使用可能
- **ADMIN_ONLY=true**: `/rss_config`コマンドは管理者のみ使用可能

管理者制限を有効にする場合は、`.env`ファイルで以下を設定してください：
```env
ADMIN_ONLY=true
ADMIN_USER_ID=your_discord_user_id
```

## ファイル構成

```
├── bot.py                    # メインボットファイル
├── config_manager.py         # 設定管理
├── rss_manager.py           # RSS処理
├── ai_processor.py          # AI処理
├── requirements.txt         # Python依存関係
├── Dockerfile              # Docker設定
├── docker-compose.yml      # Docker Compose設定
├── .env                    # 環境変数
├── config.json             # 設定ファイル（自動生成）
└── processed_articles.json # 処理済み記事管理（自動生成）
```

## 機能詳細

### RSS処理機能
- フィードの自動監視（5分、15分、30分、1時間間隔）
- 重複記事の防止
- フィード追加時の専用チャンネル自動作成

### AI処理機能
- Google Gemini API / LM Studio APIに対応
- 記事の日本語翻訳
- カスタマイズ可能な要約生成
- ジャンル分類（テクノロジー、ビジネスなど）

### Discord連携機能
- リッチなEmbedメッセージでの投稿
- ジャンル別の色分け
- インタラクティブな設定UI

## トラブルシューティング

### よくある問題

1. **ボットが起動しない**
   - `.env`ファイルの`DISCORD_TOKEN`が正しく設定されているか確認
   - ボットがDiscordサーバーに招待されているか確認

2. **記事が投稿されない**
   - RSSフィードのURLが有効か確認
   - チャンネルの書き込み権限を確認
   - `/rss_status`でボットの状態を確認

3. **AI処理が動作しない**
   - Gemini API keyが正しく設定されているか確認
   - LM Studioが起動しているか確認（LM Studio使用時）

### ログの確認

```bash
# Docker使用時
docker-compose logs -f

# 直接起動時
python bot.py
```

## ライセンス

MIT License

## 貢献

プルリクエストやイシューの報告を歓迎します。