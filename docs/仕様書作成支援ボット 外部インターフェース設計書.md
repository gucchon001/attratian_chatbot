### 3. 仕様書作成支援ボット 外部インターフェース設計書 v1.1

```markdown
# 仕様書作成支援ボット 外部インターフェース設計書

| バージョン | ステータス | 作成日 | 参照ドキュメント |
| :--- | :--- | :--- | :--- |
| **v1.3** | **最新版** | 2025/01/17 | 要件定義書 v3.5, MVP開発設計書 v2.0, JSON階層フィルター機能仕様書 v1.0 |

**v1.3更新内容:**
- EIF-01: Jira検索インターフェースを3→12パラメータに拡張
- CTJプロジェクト専用カスタムフィールド対応
- 複雑なJQLクエリ生成ロジックの詳細仕様
- EIF-06: 新規追加 - JSON階層データインターフェース詳細仕様
- Confluenceページ階層のJSONファイル管理・更新機能
- 30-100倍パフォーマンス向上のための技術仕様

**v1.2更新内容:**
- EIF-01: Jira検索に12種類のフィルターパラメータ仕様を追加
- EIF-02: Confluence検索に4種類のフィルターパラメータ仕様を追加
- EIF-05: 新規追加 - SQLiteキャッシュインターフェース詳細仕様

## 1. はじめに

本ドキュメントは、「仕様書作成支援ボット」と、それが連携する外部システム（Jira, Confluence, Gemini API, Google Chat）とのインターフェース仕様を定義するものである。各インターフェースの技術選定理由、接続方式、データ形式、エラーハンドリングなどを明確にし、円滑な開発を目的とする。

## 2. システム構成図 (MVP版)

MVP開発におけるシステム全体の構成は以下の通り。

[ユーザー] <=> [Streamlit UI] <=> [ボットアプリケーション (Python)]
|
+--------------------+--------------------+--------------------+
| (EIF-01)           | (EIF-02)           | (EIF-03)           | (EIF-04)
V                    V                    V                    V
[Jira Cloud]      [Confluence Cloud]      [Gemini API]        [Google Chat]


## 3. インターフェース一覧

| ID | インターフェース名 | 連携先システム | 目的 | 通信方式 |
| :--- | :--- | :--- | :--- | :--- |
| EIF-01 | Jira検索インターフェース | Jira Cloud | キーワード・フィルター条件に合致するチケット情報を検索 | REST API |
| EIF-02 | Confluence検索インターフェース | Confluence Cloud | キーワード・フィルター条件に合致するページ情報を検索 | REST API |
| EIF-03 | AI要約生成インターフェース | Gemini API | 収集した情報を元に要約文を生成 | REST API |
| EIF-04 | エラー通知インターフェース | Google Chat | 捕捉したエラーを開発チームに通知 | REST API (Webhook) |
| **EIF-05** | **フィルター選択肢キャッシュインターフェース** | **SQLite DB** | **フィルター選択肢（プロジェクト・ステータス等）の高速キャッシュ** | **Local DB** |
| **EIF-06** | **JSON階層データインターフェース** | **ローカルファイル** | **Confluenceページ階層のJSONデータ管理・更新** | **Local File** |

## 4. インターフェース詳細仕様

### **EIF-01: Jira検索インターフェース**

* **目的:** ユーザーが入力したキーワードに基づき、関連するJiraチケットの情報を取得する。
* **選定技術・サービス:** Atlassian REST API (Jira Cloud platform)
    * **使用ライブラリ:** `atlassian-python-api`
    * **選定理由:** Jira/Confluenceと統一されたインターフェースでアクセスでき、Pythonからの利用を簡素化するラッパーライブラリとして実績があるため。JQL (Jira Query Language) を利用した柔軟な検索が可能であり、要件を満たす。
* **エンドポイント・メソッド:** `GET /rest/api/3/search` (ライブラリ内部で抽象化)
* **認証方式:** ベーシック認証 (メールアドレス + Atlassian APIトークン)
* **リクエストデータ:**
    | パラメータ | 型 | 説明 | 例 |
    | :--- | :--- | :--- | :--- |
    | `jql` | string | 検索クエリ。基本キーワード検索に加え、12種類のフィルター条件を動的に組み合わせてJQLクエリを生成。 | `text ~ "ログイン画面" AND project = "CTJ" AND status = "進行中"` |
    
* **フィルター対応JQLパラメータ（v1.3拡張: 3→12種類）:**

    **基本フィルター (従来からの継続):**
    | フィルター項目 | JQL構文 | バージョン | 説明 |
    | :--- | :--- | :--- | :--- |
    | **プロジェクト** | `project = "KEY"` | v1.0〜 | プロジェクトキーによる絞り込み |
    | **ステータス** | `status = "STATUS"` | v1.0〜 | ステータス名による絞り込み |
    | **担当者** | `assignee = "ID"` | v1.0〜 | 担当者アカウントIDによる絞り込み |
    
    **拡張フィルター (v1.3新規追加):**
    | フィルター項目 | JQL構文 | バージョン | 説明 |
    | :--- | :--- | :--- | :--- |
    | **チケットタイプ** | `issuetype = "TYPE"` | **v1.3〜** | Story、Bug、Task等による絞り込み |
    | **優先度** | `priority = "PRIORITY"` | **v1.3〜** | High、Medium、Low等による絞り込み |
    | **報告者** | `reporter = "ID"` | **v1.3〜** | 報告者アカウントIDによる絞り込み |
    | **カスタム担当** | `customfield_10277 = "VALUE"` | **v1.3〜** | **CTJプロジェクト専用フィールド** |
    | **カスタム影響業務** | `customfield_10291 = "VALUE"` | **v1.3〜** | **CTJプロジェクト専用フィールド** |
    | **作成日以降** | `created >= "YYYY-MM-DD"` | **v1.3〜** | 作成日による範囲絞り込み |
    | **作成日以前** | `created <= "YYYY-MM-DD"` | **v1.3〜** | 作成日による範囲絞り込み |
    | **更新日以降** | `updated >= "YYYY-MM-DD"` | **v1.3〜** | 更新日による範囲絞り込み |
    | **更新日以前** | `updated <= "YYYY-MM-DD"` | **v1.3〜** | 更新日による範囲絞り込み |
    
    **v1.3機能拡張の主な改善点:**
    - **フィルター数**: 300%増加（3 → 12パラメータ）
    - **専用対応**: CTJプロジェクト固有ワークフローへの最適化
    - **日付分析**: 時系列での課題追跡機能
    - **クエリ品質**: AND/OR条件の複雑な組み合わせ対応
    
* **JQLクエリ生成例:**
    ```sql
    text ~ "ログイン" 
    AND (project = "CTJ" OR project = "SAMPLE") 
    AND (status = "進行中" OR status = "完了") 
    AND assignee = "accountId123"
    AND customfield_10277 = "フロントエンド"
    AND created >= "2024-01-01" 
    AND updated <= "2024-12-31"
    ```
* **レスポンスデータ (主要項目):**
    | フィールド | 型 | 説明 |
    | :--- | :--- | :--- |
    | `issues[].key` | string | チケットキー (例: "PROJ-123") |
    | `issues[].fields.summary` | string | チケットの要約（タイトル） |
    | `issues[].fields.description` | object | チケットの説明（ADF形式） |
    | `issues[].fields.status.name`| string | チケットのステータス (例: "完了") |
* **エラーハンドリング:**
    * `401 Unauthorized`: 認証失敗。APIトークンが不正。
    * `400 Bad Request`: JQLクエリが不正。
    * `5xx Server Error`: Atlassian側のサーバーエラー。

### **EIF-02: Confluence検索インターフェース**

* **目的:** ユーザーが入力したキーワードに基づき、関連するConfluenceページの情報を取得する。
* **選定技術・サービス:** Atlassian REST API (Confluence Cloud platform)
    * **使用ライブラリ:** `atlassian-python-api`
    * **選定理由:** Jiraとの連携と同一ライブラリを使用することで、開発効率と保守性を高めるため。CQL (Confluence Query Language) による高度な検索が可能。
* **エンドポイント・メソッド:** `GET /wiki/rest/api/search` (ライブラリ内部で抽象化)
* **認証方式:** ベーシック認証 (メールアドレス + Atlassian APIトークン)
* **リクエストデータ:**
    | パラメータ | 型 | 説明 | 例 |
    | :--- | :--- | :--- | :--- |
    | `cql` | string | 検索クエリ。基本キーワード検索に加え、4種類のフィルター条件を動的に組み合わせてCQLクエリを生成。 | `text ~ "ログイン仕様" AND space = "TECH" AND type = "page"` |
    
* **フィルター対応CQLパラメータ（4種類）:**
    | フィルター項目 | CQL構文 | 実装状況 | 説明 |
    | :--- | :--- | :--- | :--- |
    | **スペース** | `space = "KEY"` | ✅ 実装済み | スペースキーによる絞り込み |
    | **コンテンツタイプ** | `type = "TYPE"` | ✅ 実装済み | page または blogpost による絞り込み |
    | **作成日以降** | `created >= "YYYY-MM-DD"` | ✅ 実装済み | 作成日による範囲絞り込み |
    | **作成日以前** | `created <= "YYYY-MM-DD"` | ✅ 実装済み | 作成日による範囲絞り込み |
    
* **CQLクエリ生成例:**
    ```sql
    text ~ "仕様書" 
    AND (space = "TECH" OR space = "DESIGN") 
    AND type = "page"
    AND created >= "2024-01-01"
    ```
* **レスポンスデータ (主要項目):**
    | フィールド | 型 | 説明 |
    | :--- | :--- | :--- |
    | `results[].content.id` | string | ページID |
    | `results[].content.title` | string | ページタイトル |
    | `results[].excerpt` | string | 検索キーワード周辺の本文抜粋 |
    | `results[].url` | string | ページへのWebリンク |
* **エラーハンドリング:**
    * `401 Unauthorized`: 認証失敗。APIトークンが不正。
    * `400 Bad Request`: CQLクエリが不正。
    * `5xx Server Error`: Atlassian側のサーバーエラー。

### **EIF-03: AI要約生成インターフェース**
* **目的:** EIF-01およびEIF-02で収集した情報をコンテキストとして与え、AIに自然言語で要約を生成させる。
* **選定技術・サービス:** **Gemini API**
    * **使用ライブラリ:** `langchain-google-genai`
    * **選定モデル:** `gemini-1.5-flash`
    * **選定理由:** 高速な応答性能とコスト効率に優れ、日本語の要約品質も高い。LangChainとの統合ライブラリが提供されており、開発初期段階での実装が容易であるため。
* **エンドポイント・メソッド:** `v1beta/models/gemini-1.5-flash:generateContent` (ライブラリ内部で抽象化)
* **認証方式:** APIキー認証 (Google API Key)
* **リクエストデータ (主要項目):**
    | パラメータ | 型 | 説明 |
    | :--- | :--- | :--- |
    | `model` | string | 使用するモデルID (`gemini-1.5-flash`) |
    | `contents` | array | 会話の履歴。LangChainの`Memory`と`Agent`によって自動的に構築される。 |
* **レスポンスデータ (主要項目):**
    | フィールド | 型 | 説明 |
    | :--- | :--- | :--- |
    | `candidates[0].content.parts[0].text` | string | AIが生成した要約テキスト。 (ライブラリ内部で抽象化) |
* **エラーハンドリング:**
    * `400 InvalidArgument`: リクエストが不正。
    * `401 Unauthenticated`: 認証失敗。APIキーが不正。
    * `429 ResourceExhausted`: レート制限超過。

### **EIF-04: エラー通知インターフェース**
* **目的:** アプリケーションで発生した捕捉可能なエラー（API接続失敗など）を、開発チームのGoogle Chatスペースにリアルタイムで通知する。
* **選定技術・サービス:** Google Chat Incoming Webhooks
    * **使用ライブラリ:** `requests`
    * **選定理由:** 特定のURLにJSONペイロードをPOSTするだけで簡単に通知を送信でき、標準的なライブラリのみで実装可能なため。
* **エンドポイント・メソッド:** `POST {Webhook URL}`
* **認証方式:** Webhook URL自体が認証トークンを含むため、追加の認証は不要。
* **リクエストデータ:**
    * Google Chatのメッセージ形式に準拠したJSON。
    * **例:** `{"text": "【Botエラー通知】\n*エラー種別:* API接続失敗\n*詳細:* Jira APIへの接続がタイムアウトしました。"}`
* **レスポンスデータ (主要項目):** `200 OK` (成功時)
* **エラーハンドリング:** Webhook URLが不正な場合や、ネットワークエラーが発生した場合のログ出力。

### **EIF-05: フィルター選択肢キャッシュインターフェース**
* **目的:** Jira/Confluenceから取得したフィルター選択肢（プロジェクト一覧、ステータス一覧等）をローカルキャッシュし、UI応答性能を大幅に向上させる。
* **選定技術・サービス:** SQLite Database
    * **使用ライブラリ:** `sqlite3` (Python標準ライブラリ)
    * **選定理由:** ファイルベースの軽量データベースで、追加インフラ不要。JSON形式でのデータ保存・取得が容易で、有効期限管理も実装しやすいため。
* **データベースファイル:** `cache/filter_cache.db`
* **テーブル構造:**
    ```sql
    CREATE TABLE filter_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cache_key TEXT UNIQUE NOT NULL,
        data TEXT NOT NULL,              -- JSON文字列
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL
    )
    ```
* **主要操作:**
    | 操作 | 説明 | パフォーマンス |
    | :--- | :--- | :--- |
    | **GET操作** | キャッシュキーでデータを取得（有効期限チェック付き） | ~0.1秒 |
    | **SET操作** | データをJSON形式でキャッシュに保存 | ~0.05秒 |
    | **DELETE操作** | 期限切れキャッシュの削除 | ~0.02秒 |
    | **REFRESH操作** | 強制更新（UI「選択肢を更新」ボタン） | 3-5秒（API呼び出し含む） |
* **キャッシュキー例:**
    * `jira_filter_options`: Jira全般のフィルター選択肢
    * `confluence_spaces`: Confluenceスペース一覧
* **データ形式例:**
    ```json
    {
        "projects": [{"key": "CTJ", "name": "Customer Journey", "id": "10001"}],
        "statuses": [{"id": "1", "name": "To Do", "category": "new"}],
        "users": [{"accountId": "123", "displayName": "原口", "emailAddress": "user@example.com"}]
    }
    ```
* **有効期限管理:**
    * **デフォルト有効期間:** 1時間（configurable）
    * **自動期限切れ削除:** データ取得時に実行
    * **強制更新:** UIボタンまたは `force_update=True` フラグ
* **エラーハンドリング:**
    * **キャッシュ破損:** 自動削除して継続動作
    * **ディスク容量不足:** ログ出力後、キャッシュなしで動作継続
    * **権限エラー:** 代替パス利用またはメモリキャッシュへフォールバック

---

### **EIF-06: JSON階層データインターフェース**

* **目的:** Confluenceページ階層をJSONファイルで高速管理し、階層フィルター機能に30-100倍のパフォーマンス向上を提供。

* **対象システム:** ローカルファイルシステム
* **通信方式:** File I/O

#### **データファイル構成:**
* **主ファイル:** `data/confluence_hierarchy.json`
* **バックアップ:** `data/confluence_hierarchy_backup.json`  
* **メタデータ:** `data/cache_metadata.json`

#### **JSON構造仕様:**
```json
{
  "space_name": "client-tomonokai-juku",
  "space_key": "CLIENTTOMO",
  "generated_at": "2025-01-17T16:27:59",
  "total_pages": 1129,
  "deleted_pages_count": 12,
  "version": "1.0",
  "folders": [
    {
      "id": "folder_001",
      "name": "■要件定義",
      "type": "folder",
      "page_count": 45,
      "is_deleted": false,
      "children": [...]
    }
  ]
}
```

#### **更新スケジュール:**
* **自動更新:** 週1回（月曜日 AM 3:00）
* **手動更新:** UIボタン経由（30-60秒）
* **差分検知:** Confluence最終更新日時比較

#### **パフォーマンス仕様:**
* **読み込み時間:** 0.1秒以下
* **ファイルサイズ:** 100KB-1MB（圧縮時）
* **メモリ使用量:** 5-50MB

**📄 詳細仕様:** [JSON階層フィルター機能_仕様書.md](./JSON階層フィルター機能_仕様書.md#システム設計) を参照
