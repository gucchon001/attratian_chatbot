# 仕様書作成支援ボット デプロイ手順書

| バージョン | ステータス | 作成日 | 参照ドキュメント |
| :--- | :--- | :--- | :--- |
| **v1.0** | **作成完了** | 2025/07/16 | 要件定義書 v3.0, MVP開発計画書 v2.1 |

---

## 1. 概要
本ドキュメントは、「仕様書作成支援ボット」を本番環境へ展開（デプロイ）するための手順を定義するものである。この手順に従うことで、誰でも安全かつ確実にアプリケーションを公開・更新することを目指す。

## 2. デプロイ先プラットフォーム
* **プラットフォーム:** Streamlit Community Cloud
* **選定理由:**
    * 無料で利用開始できる。
    * GitHubリポジトリと連携し、`git push` をトリガーに自動でデプロイが実行されるため、CI/CDの構築が不要。
    * Streamlitアプリケーションのホスティングに最適化されている。
    * APIキーなどの機密情報を安全に管理するための「Secrets」機能が提供されている。

---

## 3. 事前準備
デプロイ作業を開始する前に、以下の準備が完了していることを確認する。

### 3.1. GitHubリポジトリの準備
* プロジェクトのソースコード一式が、GitHub上の専用リポジトリにプッシュされていること。
* リポジトリはPublicでもPrivateでも構わない。

### 3.2. ファイル構成の確認
リポジトリには、少なくとも以下のファイルが含まれている必要がある。

spec-bot-mvp/
├── .streamlit/
│   └── secrets.toml.example  # シークレットのテンプレート（推奨）
├── app.py                    # メインのアプリケーションコード
├── requirements.txt          # 依存ライブラリ一覧
└── .env                      # ローカル開発用のAPIキー（.gitignoreに追加すること）


### 3.3. `requirements.txt` の作成
プロジェクトで使用しているPythonライブラリをリストアップしたファイルを作成する。ターミナルで以下のコマンドを実行して生成する。
```bash
# 仮想環境が有効化されていることを確認
pip freeze > requirements.txt
```requirements.txt`の中身の例：
streamlit==1.35.0
langchain==0.2.1
langchain-google-genai==1.0.4
atlassian-python-api==3.41.8
python-dotenv==1.0.1


---

## 4. デプロイ手順

### Step 1: Streamlit Community Cloudへのサインアップ
1.  [Streamlit Community Cloud](https://share.streamlit.io/)にアクセスする。
2.  GitHubアカウントでサインアップまたはログインする。

### Step 2: 新規アプリケーションの作成
1.  ダッシュボード右上の**「New app」**ボタンをクリックする。
2.  **「Deploy from existing repo」**を選択する。

### Step 3: リポジトリの連携
1.  **Repository:** デプロイしたいGitHubリポジトリを選択する。
2.  **Branch:** デプロイ対象のブランチ（例: `main`）を選択する。
3.  **Main file path:** メインのPythonファイル（`app.py`）を指定する。
4.  **App URL:** アプリケーションのURLを任意の名前に設定する。

### Step 4: シークレット情報（APIキー）の設定
1.  **「Advanced settings...」**をクリックする。
2.  **Secrets**のテキストエリアに、ローカルの`.env`ファイルの内容を**TOML形式**で貼り付ける。詳細は次章「5. シークレット管理」を参照。
3.  **「Save」**をクリックする。

### Step 5: デプロイの実行
1.  **「Deploy!」**ボタンをクリックする。
2.  デプロイが開始され、ログが表示される。初回は数分かかる場合がある。
3.  デプロイが完了すると、自動的にアプリケーションのURLにリダイレクトされ、ボットが起動する。

---

## 5. シークレット管理
本番環境では、`.env`ファイルは使用されない。代わりにStreamlit Community Cloudが提供する**Secrets機能**を利用する。

* **ローカル開発 (`.env`):**
    ```
    GEMINI_API_KEY="your_gemini_api_key"
    JIRA_URL="https://..."
    ```
* **本番環境 (Streamlit Secrets / `secrets.toml`形式):**
    * デプロイ設定のSecrets欄には、以下の形式で記述する。
    ```toml
    # .streamlit/secrets.toml
    GEMINI_API_KEY = "your_gemini_api_key"
    JIRA_URL = "[https://your-domain.atlassian.net](https://your-domain.atlassian.net)"
    JIRA_USERNAME = "your-email@example.com"
    JIRA_API_TOKEN = "your_jira_api_token"
    CONFLUENCE_URL = "[https://your-domain.atlassian.net/wiki](https://your-domain.atlassian.net/wiki)"
    CONFLUENCE_USERNAME = "your-email@example.com"
    CONFLUENCE_API_TOKEN = "your_confluence_api_token"
    ```
* **コードでの読み込み:**
    * Streamlitは自動でSecretsを環境変数として読み込むため、`python-dotenv`を使ったローカルでの読み込みと互換性がある。
    ```python
    import os
    # ローカルでは.envから、本番ではSecretsから読み込まれる
    api_key = os.environ.get("GEMINI_API_KEY") 
    ```

---

## 6. アプリケーションの更新
アプリケーションのコードを修正・更新したい場合は、以下の手順で行う。
1.  ローカルでコードを修正し、テストする。
2.  修正内容をGitHubリポジトリのデプロイ対象ブランチ（例: `main`）に`git push`する。
3.  プッシュを検知したStreamlit Community Cloudが、自動的にアプリケーションの再デプロイを開始する。

---

## 7. トラブルシューティング
* **`ModuleNotFoundError`:**
    * `requirements.txt`に必要なライブラリが記載されているか確認する。
* **API認証エラー:**
    * StreamlitダッシュボードのSecrets設定が正しいか、キーのスペルミスやコピーミスがないか再確認する。
* **アプリがクラッシュする:**
    * Streamlitダッシュボード右上のハンバーガーメニューから「View logs」を選択し、エラーログを確認する。