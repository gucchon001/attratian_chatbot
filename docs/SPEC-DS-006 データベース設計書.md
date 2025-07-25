# SPEC-DS-006 データベース設計書

| バージョン | ステータス | 作成日 | 参照ドキュメント |
| :--- | :--- | :--- | :--- |
| **v1.0** | **最新版** | 2025/01/24 | SPEC-DS-001 開発設計書, SPEC-DS-005 UML設計書 |

---

## 🗄️ **概要**
本ドキュメントは、「仕様書作成支援ボット」で使用するデータベース（SQLite）の論理設計・物理設計・テーブル構造を定義するものである。主にキャッシュデータ、会話履歴、フィルター設定の永続化を担う。

---

## 📊 **1. データベース概要**

### **1.1 データベース仕様**
- **DBMS**: SQLite 3.x + JSON File Storage (ハイブリッド)
- **SQLiteファイル**: `{project_root}/cache/filter_cache.db`
- **JSONファイル**: 
  - `{project_root}/data/confluence_hierarchy.json` (階層データ)
  - `{project_root}/data/cache_metadata.json` (メタデータ)
- **文字コード**: UTF-8
- **主要目的**: 高速キャッシュ・階層データ永続化・ユーザー体験改善

### **1.2 設計方針**
1. **軽量性**: SQLite + JSON ハイブリッドによる軽量設計
2. **高速性**: 
   - SQLite: 高頻度アクセスデータ（キャッシュ・フィルター）
   - JSON: 大容量階層データ（Confluence構造）
3. **実用性**: 実装コストと性能のバランス重視
4. **保守性**: シンプルな構造・明確なデータ分離

---

## 🏗️ **2. 論理設計**

### **2.1 データ構造図 (ハイブリッド設計)**
```mermaid
erDiagram
    %% SQLite Tables
    FILTER_CACHE {
        INTEGER id PK "自動ID"
        TEXT cache_key UNIQUE "キャッシュキー"
        TEXT data "JSONデータ"
        TIMESTAMP created_at "作成日時"
        TIMESTAMP expires_at "有効期限"
    }

    %% JSON File Structures
    CONFLUENCE_HIERARCHY_JSON {
        TEXT space_name "スペース名"
        TEXT space_key "スペースキー"
        TIMESTAMP generated_at "生成日時"
        INTEGER total_pages "総ページ数"
        INTEGER deleted_pages_count "削除ページ数"
        TEXT version "バージョン"
        JSON folders "階層フォルダ構造"
    }

    CACHE_METADATA_JSON {
        TIMESTAMP last_update "最終更新日時"
        TEXT version "バージョン"
        INTEGER total_pages "総ページ数"
        INTEGER deleted_pages_count "削除ページ数"
    }

    %% Future Extension Tables (Phase 2以降)
    CONVERSATION_HISTORY {
        INTEGER id PK "履歴ID"
        TEXT session_id "セッションID"
        TEXT user_message "ユーザーメッセージ"
        TEXT bot_response "ボット回答"
        TIMESTAMP created_at "作成日時"
    }

    SEARCH_ANALYTICS {
        INTEGER id PK "分析ID"
        TEXT query_text "検索クエリ"
        TEXT extracted_keywords "抽出キーワード(JSON)"
        REAL quality_score "品質スコア"
        TIMESTAMP executed_at "実行日時"
    }

    FILTER_CACHE ||--o{ CONFLUENCE_HIERARCHY_JSON : "hierarchy_reference"
    CACHE_METADATA_JSON ||--o{ CONFLUENCE_HIERARCHY_JSON : "metadata_for"
```

### **2.2 データ構造定義**

#### **SQLite Tables (実装済み)**

##### **FILTER_CACHE (フィルターキャッシュ)**
- **目的**: フィルター選択肢のキャッシュ・API削減
- **データ量**: 小量（数十レコード）
- **更新頻度**: 低頻度（24時間キャッシュ）
- **実装状況**: ✅ 完全実装済み

#### **JSON File Storage (実装済み)**

##### **CONFLUENCE_HIERARCHY.JSON (Confluence階層)**
- **目的**: Confluenceページ階層の永続化・高速フィルタリング
- **データ量**: 大量（1129ページ、260KB）
- **更新頻度**: 低頻度（手動更新）
- **実装状況**: ✅ 完全実装済み

##### **CACHE_METADATA.JSON (キャッシュメタデータ)**
- **目的**: キャッシュ管理・バージョン管理
- **データ量**: 極小（1レコード）
- **更新頻度**: 階層データ更新時
- **実装状況**: ✅ 完全実装済み

#### **Future Extension Tables (Phase 2以降)**

##### **CONVERSATION_HISTORY (会話履歴)**
- **目的**: ユーザー会話の永続化・文脈保持
- **データ量**: 中量（数十～数百レコード/ユーザー）
- **更新頻度**: 低頻度（質問ごと）
- **実装状況**: 📋 Phase 2実装予定

##### **SEARCH_ANALYTICS (検索分析)**
- **目的**: 検索パフォーマンス分析・品質改善
- **データ量**: 中量（数百～数千レコード）
- **更新頻度**: 中頻度（検索ごと）
- **実装状況**: 📋 Phase 2実装予定

#### **FILTER_SETTINGS (フィルター設定)**
- **目的**: ユーザー個別フィルター設定の保存
- **データ量**: 小量（数十レコード/ユーザー）
- **更新頻度**: 低頻度（設定変更時）

#### **SEARCH_ANALYTICS (検索分析)**
- **目的**: 検索パフォーマンス分析・改善指標
- **データ量**: 大量（数千～数万レコード）
- **更新頻度**: 高頻度（検索ごと）

#### **CONFLUENCE_HIERARCHY (Confluence階層)**
- **目的**: ページ階層構造の高速フィルタリング
- **データ量**: 中量（数百～数千レコード）
- **更新頻度**: 低頻度（日次更新）

---

## 🔧 **3. 物理設計**

### **3.1 SQLite テーブル定義 (実装済み)**

#### **3.1.1 FILTER_CACHE テーブル (実装済み)**
```sql
CREATE TABLE IF NOT EXISTS filter_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    CHECK (length(cache_key) <= 255),
    CHECK (expires_at > created_at)
);

-- インデックス (実装済み)
CREATE INDEX IF NOT EXISTS idx_filter_cache_key ON filter_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_filter_cache_expires ON filter_cache(expires_at);
```

### **3.2 JSON File 構造定義 (実装済み)**

#### **3.2.1 confluence_hierarchy.json (実装済み)**
```json
{
  "space_name": "client-tomonokai-juku",
  "space_key": "CLIENTTOMO", 
  "generated_at": "2025-07-17T17:08:20.783550",
  "total_pages": 1129,
  "deleted_pages_count": 0,
  "version": "1.0",
  "folders": [
    {
      "name": "フォルダ名",
      "type": "folder|page",
      "updated": "YYYY-MM-DD HH:MM",
      "children": [...]
    }
  ]
}
```

#### **3.2.2 cache_metadata.json (実装済み)**
```json
{
  "last_update": "2025-07-17T17:08:20.800193",
  "version": "1.0",
  "total_pages": 1129,
  "deleted_pages_count": 0
}
```

### **3.3 Future Extension Tables (Phase 2以降)**

#### **3.3.1 CONVERSATION_HISTORY テーブル**
```sql
CREATE TABLE IF NOT EXISTS conversation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    thinking_process TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}',
    CHECK (length(session_id) <= 255),
    CHECK (length(user_message) > 0),
    CHECK (json_valid(metadata))
);

-- インデックス
CREATE INDEX idx_conv_session ON conversation_history(session_id);
CREATE INDEX idx_conv_created ON conversation_history(created_at DESC);
```

#### **3.1.3 FILTER_SETTINGS テーブル**
```sql
CREATE TABLE IF NOT EXISTS filter_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_session TEXT NOT NULL,
    filter_type TEXT NOT NULL,
    filter_value TEXT NOT NULL DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(user_session) <= 255),
    CHECK (filter_type IN ('jira', 'confluence', 'global')),
    CHECK (json_valid(filter_value)),
    UNIQUE(user_session, filter_type)
);

-- インデックス
CREATE INDEX idx_filter_session ON filter_settings(user_session);
CREATE INDEX idx_filter_type ON filter_settings(filter_type);

-- 更新時のトリガー
CREATE TRIGGER update_filter_timestamp 
    AFTER UPDATE ON filter_settings
BEGIN
    UPDATE filter_settings SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

#### **3.1.4 SEARCH_ANALYTICS テーブル**
```sql
CREATE TABLE IF NOT EXISTS search_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text TEXT NOT NULL,
    extracted_keywords TEXT DEFAULT '[]',
    search_strategy TEXT,
    result_count INTEGER DEFAULT 0,
    relevance_score REAL,
    response_time REAL,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(query_text) > 0),
    CHECK (json_valid(extracted_keywords)),
    CHECK (result_count >= 0),
    CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    CHECK (response_time >= 0.0)
);

-- インデックス
CREATE INDEX idx_analytics_executed ON search_analytics(executed_at DESC);
CREATE INDEX idx_analytics_score ON search_analytics(relevance_score DESC);
CREATE INDEX idx_analytics_strategy ON search_analytics(search_strategy);
```

#### **3.1.5 CONFLUENCE_HIERARCHY テーブル**
```sql
CREATE TABLE IF NOT EXISTS confluence_hierarchy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id TEXT NOT NULL UNIQUE,
    page_title TEXT NOT NULL,
    parent_id TEXT,
    level INTEGER DEFAULT 0,
    path TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    cached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(page_id) > 0),
    CHECK (length(page_title) > 0),
    CHECK (level >= 0),
    FOREIGN KEY (parent_id) REFERENCES confluence_hierarchy(page_id)
);

-- インデックス
CREATE INDEX idx_hierarchy_parent ON confluence_hierarchy(parent_id);
CREATE INDEX idx_hierarchy_level ON confluence_hierarchy(level);
CREATE INDEX idx_hierarchy_deleted ON confluence_hierarchy(is_deleted);
CREATE INDEX idx_hierarchy_path ON confluence_hierarchy(path);
```

### **3.2 初期データ投入**
```sql
-- サンプルキャッシュエントリ
INSERT OR IGNORE INTO cache_entries (key, data, expires_at, category) VALUES
('jira_statuses', '["To Do", "In Progress", "Done"]', datetime('now', '+24 hours'), 'jira'),
('confluence_spaces', '["CLIENTTOMO", "DEV", "QA"]', datetime('now', '+24 hours'), 'confluence');

-- デフォルトフィルター設定
INSERT OR IGNORE INTO filter_settings (user_session, filter_type, filter_value) VALUES
('default', 'confluence', '{"include_deleted": false, "default_space": "CLIENTTOMO"}'),
('default', 'jira', '{"default_project": "CTJ", "max_results": 50}');
```

---

## 📈 **4. パフォーマンス設計**

### **4.1 現在の実装によるパフォーマンス戦略**

#### **SQLite パフォーマンス (実装済み)**
```sql
-- FILTER_CACHE インデックス (実装済み)
CREATE INDEX IF NOT EXISTS idx_filter_cache_key ON filter_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_filter_cache_expires ON filter_cache(expires_at);

-- キャッシュクリーンアップ (CacheManager実装済み)
DELETE FROM filter_cache WHERE expires_at <= datetime('now');
```

#### **JSON File パフォーマンス (実装済み)**
- **メモリロード**: 起動時に260KBのconfluence_hierarchy.jsonを一括ロード
- **階層フィルタリング**: Pythonでの高速フィルタリング処理
- **キャッシュ戦略**: 24時間有効期限による適切なキャッシュ管理

### **4.2 実際の使用例 (実装済み)**

#### **CacheManager での SQLite 操作**
```python
# キャッシュ取得 (実装済み)
def get(self, cache_key: str) -> Optional[Any]:
    with self._get_connection() as conn:
        cursor = conn.execute("""
            SELECT data, expires_at FROM filter_cache 
            WHERE cache_key = ? AND expires_at > ?
        """, (cache_key, datetime.now().isoformat()))

# キャッシュ設定 (実装済み)
def set(self, cache_key: str, data: Any, expiry_hours: int = 24):
    expires_at = datetime.now() + timedelta(hours=expiry_hours)
    with self._get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO filter_cache 
            (cache_key, data, expires_at) VALUES (?, ?, ?)
        """, (cache_key, json.dumps(data), expires_at.isoformat()))
```

#### **Confluence階層データの使用例**
```python
# JSON ファイルからの階層読み込み (実装済み)
with open("data/confluence_hierarchy.json", "r") as f:
    hierarchy_data = json.load(f)
    total_pages = hierarchy_data["total_pages"]  # 1129
    folders = hierarchy_data["folders"]
```

---

## 🔒 **5. データ整合性・制約**

### **5.1 制約定義**
```sql
-- 1. データ型制約
ALTER TABLE cache_entries ADD CONSTRAINT chk_expires_future 
CHECK (expires_at > created_at);

-- 2. 参照整合性
ALTER TABLE confluence_hierarchy ADD CONSTRAINT fk_parent_exists
FOREIGN KEY (parent_id) REFERENCES confluence_hierarchy(page_id);

-- 3. 値範囲制約  
ALTER TABLE search_analytics ADD CONSTRAINT chk_score_range
CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0);

-- 4. JSON形式制約
ALTER TABLE filter_settings ADD CONSTRAINT chk_json_valid
CHECK (json_valid(filter_value));
```

### **5.2 データクリーンアップ**
```sql
-- 期限切れキャッシュの自動削除
CREATE TRIGGER cleanup_expired_cache
    AFTER INSERT ON cache_entries
BEGIN
    DELETE FROM cache_entries WHERE expires_at <= CURRENT_TIMESTAMP;
END;

-- 古い会話履歴の定期削除（30日以上前）
DELETE FROM conversation_history 
WHERE created_at < datetime('now', '-30 days');

-- 古い検索分析データの定期削除（90日以上前）
DELETE FROM search_analytics 
WHERE executed_at < datetime('now', '-90 days');
```

---

## 💾 **6. バックアップ・メンテナンス**

### **6.1 バックアップ戦略**
```sql
-- 1. 完全バックアップ（日次）
.backup cache/filter_cache_backup_$(date +%Y%m%d).db

-- 2. 重要データのみバックアップ
CREATE TABLE backup_conversation_history AS 
SELECT * FROM conversation_history WHERE created_at >= datetime('now', '-7 days');

-- 3. 設定データのエクスポート
.mode json
.output filter_settings_backup.json
SELECT * FROM filter_settings;
```

### **6.2 メンテナンス操作**
```sql
-- 1. VACUUM（定期実行）
VACUUM;

-- 2. インデックス再構築
REINDEX;

-- 3. 統計情報更新
ANALYZE;

-- 4. データベース整合性チェック
PRAGMA integrity_check;

-- 5. データベースサイズ確認
PRAGMA page_count;
PRAGMA page_size;
```

---

## 📊 **7. 使用例・アクセスパターン**

### **7.1 CacheManagerクラスでの利用**
```python
# キャッシュ取得
def get_cached_data(self, key: str) -> Optional[Any]:
    with self._get_connection() as conn:
        cursor = conn.execute(
            "SELECT data FROM cache_entries WHERE key = ? AND expires_at > CURRENT_TIMESTAMP",
            (key,)
        )
        result = cursor.fetchone()
        return json.loads(result[0]) if result else None

# キャッシュ設定
def set_cached_data(self, key: str, data: Any, expiry_hours: int = 24):
    expires_at = datetime.now() + timedelta(hours=expiry_hours)
    with self._get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache_entries (key, data, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(data), expires_at)
        )
```

### **7.2 会話履歴管理**
```python
# 履歴保存
def save_conversation(self, session_id: str, user_msg: str, bot_response: str, thinking: str):
    with self._get_connection() as conn:
        conn.execute(
            "INSERT INTO conversation_history (session_id, user_message, bot_response, thinking_process) VALUES (?, ?, ?, ?)",
            (session_id, user_msg, bot_response, thinking)
        )

# 履歴取得
def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
    with self._get_connection() as conn:
        cursor = conn.execute(
            "SELECT user_message, bot_response, created_at FROM conversation_history WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit)
        )
        return [{"user": row[0], "bot": row[1], "timestamp": row[2]} for row in cursor.fetchall()]
```

---

## 🚀 **8. 将来拡張計画**

### **8.1 Phase 2.2対応準備**
```sql
-- 実Confluence連携用テーブル
CREATE TABLE IF NOT EXISTS confluence_pages (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    space_key TEXT NOT NULL,
    version INTEGER,
    last_modified DATETIME,
    author TEXT,
    url TEXT
);

-- 実Jira連携用テーブル  
CREATE TABLE IF NOT EXISTS jira_issues (
    key TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    assignee TEXT,
    project_key TEXT NOT NULL,
    created DATETIME,
    updated DATETIME
);
```

### **8.2 分析機能強化**
```sql
-- ユーザー行動分析
CREATE TABLE IF NOT EXISTS user_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_detail TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 検索改善提案
CREATE VIEW search_improvement_suggestions AS
SELECT 
    query_text,
    AVG(relevance_score) as avg_score,
    COUNT(*) as usage_count
FROM search_analytics 
WHERE relevance_score < 0.7
GROUP BY query_text
HAVING usage_count > 1
ORDER BY usage_count DESC;
```

---

*最終更新: 2025年1月24日 - v1.0 システム完成版* 