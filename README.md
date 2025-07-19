# 仕様書作成支援ボット MVP

JiraとConfluenceを統合した仕様書作成支援ボットです。

## 🚀 概要

このボットは、開発チームの効率的な情報共有をサポートする LangChain + Gemini ベースの AI アシスタントです。

### ✨ 主な機能

- 🎯 **Jira 検索・分析**: チケット、バグ、タスクの検索と進捗管理
- 📚 **Confluence 検索・要約**: 仕様書、議事録、技術文書の検索
- 🔍 **高速フィルター機能**: 30-100x の検索パフォーマンス向上
- 🤖 **自然言語対話**: Gemini AI による直感的な質問応答
- 📊 **階層フィルター**: JSON ベースの柔軟なページ階層選択

### 🏗️ アーキテクチャ

- **フロントエンド**: Streamlit
- **AI エンジン**: LangChain + Google Gemini
- **外部連携**: Atlassian API (Jira/Confluence)
- **キャッシュ**: SQLite
- **設定管理**: YAML 外部プロンプト

## 🛠️ セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 設定ファイルの作成

`src/spec_bot_mvp/config/secrets.env` ファイルを作成してください：

```env
# Atlassian API 設定
ATLASSIAN_API_TOKEN=your_atlassian_api_token_here

# Gemini API 設定  
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Google Cloud Service Account の設定（オプション）

Google BigQuery や他の GCP サービスを使用する場合は、サービスアカウントの JSON ファイルを `src/spec_bot_mvp/config/` フォルダーに配置してください。

⚠️ **セキュリティ注意**: 
- JSON クレデンシャルファイルは `.gitignore` で除外されています
- 絶対に Git にコミットしないでください
- 本番環境では環境変数または安全なシークレット管理サービスを使用してください

## 🚀 起動方法

### 🚀 クイック起動（推奨）
指定のIPアドレス・ポートで起動：

**Windows PowerShell:**
```powershell
.\start_bot.ps1
```

**Windows コマンドプロンプト:**
```cmd
start_bot.bat
```

どちらも以下のURLでアクセス可能になります：
**http://192.168.1.227:8401/**

### 📋 手動起動
```bash
# 指定IPアドレス・ポートで起動
streamlit run app.py --server.address=192.168.1.227 --server.port=8401

# 標準起動（localhost:8501）
streamlit run app.py

# CLI テスト
python test_agent_cli.py
```

## 🧪 テスト

```bash
# 全テスト実行
python -m pytest tests/ -v

# エージェント単体テスト
python -m pytest tests/unit/test_agent.py -v
```

## 📁 プロジェクト構造

```
src/spec_bot_mvp/
├── config/          # 設定・プロンプト管理
│   ├── prompts.yaml # AI プロンプト設定
│   ├── settings.py  # アプリケーション設定
│   └── secrets.env  # 機密情報（Git 除外）
├── core/            # エージェント本体
├── tools/           # Jira/Confluence ツール
├── ui/              # Streamlit UI
└── utils/           # ユーティリティ

tests/
├── unit/            # 単体テスト  
├── integration/     # 結合テスト
└── e2e/             # E2E テスト

docs/                # 設計書・仕様書
```

## 📝 使用例

```
💡 「ログイン機能の仕様書を探して」
💡 「UI バグの進捗を教えて」  
💡 「今月のタスク一覧を見せて」
💡 「設計書を検索したい」
```

## 🔧 カスタマイズ

プロンプトの調整は `src/spec_bot_mvp/config/prompts.yaml` を編集してください。エージェントの応答品質を簡単にチューニングできます。

## 🛡️ セキュリティ

- API キーや認証情報は `secrets.env` に保存
- 機密ファイルは `.gitignore` で Git 追跡から除外
- Google Cloud クレデンシャルは環境変数での管理を推奨

## 📊 パフォーマンス

- **フィルター機能**: 30-100x 高速化実現
- **Jira**: 12 パラメータ対応 + JQL 生成
- **Confluence**: 階層選択 + 日付フィルター
- **キャッシュ**: SQLite による高速データアクセス

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で提供されています。

## 🆘 サポート

質問や問題がある場合は、GitHub の Issues を作成してください。 