# SPEC-DS-005 UML設計書

| バージョン | ステータス | 作成日 | 参照ドキュメント |
| :--- | :--- | :--- | :--- |
| **v1.0** | **最新版** | 2025/01/24 | SPEC-DS-001 開発設計書, SPEC-DS-002 ハイブリッド検索システム仕様書 |

---

## 📐 **概要**
本ドキュメントは、「仕様書作成支援ボット」のシステムアーキテクチャをUML（統一モデリング言語）で視覚化し、クラス構造・処理フロー・コンポーネント関係を明確に定義するものである。

---

## 🏗️ **1. システム全体アーキテクチャ**

### **1.1 レイヤー構成**
```
┌─────────────────────────────────────────────────────────────┐
│                    🎨 プレゼンテーション層                    │
│  Streamlit UI (streamlit_app_integrated.py)                │
├─────────────────────────────────────────────────────────────┤
│                    🧠 アプリケーション層                      │
│  SpecBotAgent (LangChain) + HybridSearchTool              │
├─────────────────────────────────────────────────────────────┤
│                    🔍 ビジネスロジック層                      │
│  Step1-4 Processing + CQL/JQL Search Engines             │
├─────────────────────────────────────────────────────────────┤
│                    🛠️ インフラストラクチャ層                  │
│  Cache Manager (SQLite) + API Clients                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 **2. クラス図**

### **2.1 エージェント・ツール層**
```mermaid
classDiagram
    class SpecBotAgent {
        -llm: ChatGoogleGenerativeAI
        -tools: List[Tool]
        -agent_executor: AgentExecutor
        -memory: ConversationBufferMemory
        -process_tracker: ProcessTracker
        +__init__()
        +_initialize_llm()
        +_initialize_memory()
        +_initialize_tools()
        +_initialize_agent()
        +process_request(user_input: str): str
        +get_conversation_history(): List[Dict]
        +clear_conversation_history()
    }

    class HybridSearchTool {
        -step1_extractor: KeywordExtractor
        -step2_judgment: DataSourceJudgment
        -step3_search: CQLSearch
        -step4_quality: QualityEvaluator
        +__init__()
        +_run(query: str): str
        +_execute_hybrid_search(query: str): Dict
    }

    class ProcessTracker {
        -stages: List[ProcessStage]
        -current_stage: int
        -start_time: datetime
        +__init__()
        +start_stage(stage_name: str)
        +complete_stage(stage_name: str, result: Dict)
        +get_progress_summary(): Dict
        +reset()
    }

    SpecBotAgent --> HybridSearchTool : uses
    SpecBotAgent --> ProcessTracker : tracks
    HybridSearchTool --> ProcessTracker : updates
```

### **2.2 検索処理層 (Step1-4)**
```mermaid
classDiagram
    class KeywordExtractor {
        -llm: ChatGoogleGenerativeAI
        -gemini_available: bool
        +__init__()
        +_init_gemini(): bool
        +extract_keywords(query: str): Dict
        +_extract_with_gemini(query: str): Dict
        +_extract_with_rules(query: str): Dict
        +_classify_question_type(query: str): str
    }

    class DataSourceJudgment {
        -llm: ChatGoogleGenerativeAI
        +__init__()
        +judge_optimal_datasource(keywords: List[str], question_type: str): Dict
        +_analyze_keyword_context(keywords: List[str]): Dict
    }

    class CQLSearch {
        -api_client: Optional[Any]
        -mock_mode: bool
        +__init__()
        +search_confluence(keywords: List[str], filters: Dict): Dict
        +_execute_strategy1(keywords: List[str]): List[Dict]
        +_execute_strategy2(keywords: List[str]): List[Dict]
        +_execute_strategy3(keywords: List[str]): List[Dict]
        +_merge_results(results: List[List[Dict]]): List[Dict]
    }

    class QualityEvaluator {
        +__init__()
        +evaluate_search_quality(results: List[Dict], keywords: List[str]): Dict
        +_calculate_relevance_score(result: Dict, keywords: List[str]): float
        +_assess_content_quality(result: Dict): Dict
        +_check_freshness(result: Dict): Dict
        +_analyze_coverage(results: List[Dict], keywords: List[str]): Dict
    }

    KeywordExtractor --> DataSourceJudgment : keywords
    DataSourceJudgment --> CQLSearch : datasource + keywords
    CQLSearch --> QualityEvaluator : search results
```

### **2.3 インフラストラクチャ層**
```mermaid
classDiagram
    class CacheManager {
        -db_path: str
        -cache_duration_hours: int
        +__init__(db_path: Optional[str])
        +_initialize_database()
        +get_cached_data(key: str): Optional[Any]
        +set_cached_data(key: str, data: Any, expiry_hours: int)
        +clear_cache(key: str)
        +_get_connection(): sqlite3.Connection
        +_is_cache_valid(stored_at: datetime): bool
    }

    class Settings {
        +project_root: Path
        +google_api_key: str
        +jira_url: str
        +jira_username: str
        +jira_api_token: str
        +confluence_url: str
        +confluence_username: str
        +confluence_api_token: str
        +__init__()
        +_load_env_file()
        +_load_environment()
        +validate_api_keys(): Dict
        +get_missing_keys(): List[str]
    }

    class ConfluenceHierarchyManager {
        -cache_manager: CacheManager
        -hierarchy_data: Dict
        +__init__()
        +load_hierarchy_data(include_deleted: bool): Dict
        +get_folder_structure(): Dict
        +filter_by_selection(selected_folders: List[str]): List[str]
        +_build_tree_structure(pages: List[Dict]): Dict
    }

    CacheManager <-- ConfluenceHierarchyManager : uses
    Settings <-- CacheManager : configuration
```

---

## 🔄 **3. シーケンス図**

### **3.1 ユーザー質問処理フロー**
```mermaid
sequenceDiagram
    participant User as 👤 ユーザー
    participant UI as 🎨 Streamlit UI
    participant Agent as 🧠 SpecBotAgent
    participant Tool as 🔍 HybridSearchTool
    participant Step1 as 📝 KeywordExtractor
    participant Step2 as 🎯 DataSourceJudgment
    participant Step3 as 🔍 CQLSearch
    participant Step4 as ⚖️ QualityEvaluator
    participant Cache as 💾 CacheManager

    User->>UI: 質問入力「ログイン機能について教えて」
    UI->>Agent: process_request(user_input)
    
    Agent->>Tool: _run(query)
    Tool->>Step1: extract_keywords(query)
    Step1-->>Tool: {"keywords": ["ログイン", "認証"], "question_type": "機能照会"}
    
    Tool->>Step2: judge_optimal_datasource(keywords, question_type)
    Step2-->>Tool: {"primary": "confluence", "confidence": 0.9}
    
    Tool->>Step3: search_confluence(keywords, filters)
    Step3->>Cache: get_cached_data("confluence_search_" + hash)
    Cache-->>Step3: None (キャッシュなし)
    Step3->>Step3: _execute_strategy1(keywords)
    Step3->>Step3: _execute_strategy2(keywords)
    Step3->>Step3: _execute_strategy3(keywords)
    Step3->>Step3: _merge_results(all_results)
    Step3->>Cache: set_cached_data(key, results, 1)
    Step3-->>Tool: [{"title": "ログイン機能仕様", "url": "..."}]
    
    Tool->>Step4: evaluate_search_quality(results, keywords)
    Step4-->>Tool: {"relevance": 0.88, "quality": "高", "coverage": "完全"}
    
    Tool-->>Agent: formatted_response
    Agent-->>UI: 最終回答
    UI-->>User: 回答表示 + 思考プロセス表示
```

### **3.2 キャッシュ管理フロー**
```mermaid
sequenceDiagram
    participant App as 📱 Application
    participant Cache as 💾 CacheManager
    participant DB as 🗄️ SQLite Database

    App->>Cache: get_cached_data("filter_options")
    Cache->>DB: SELECT * FROM cache_entries WHERE key = ?
    DB-->>Cache: {"data": "{...}", "created_at": "2025-01-24 10:00:00"}
    Cache->>Cache: _is_cache_valid(created_at)
    Cache-->>App: cached_data (有効な場合)
    
    Note over App,DB: キャッシュが無効または存在しない場合
    App->>App: fetch_fresh_data_from_api()
    App->>Cache: set_cached_data("filter_options", fresh_data, 24)
    Cache->>DB: INSERT OR REPLACE INTO cache_entries
    DB-->>Cache: success
    Cache-->>App: データ保存完了
```

---

## 🧩 **4. コンポーネント図**

### **4.1 モジュール構成**
```mermaid
graph TB
    subgraph "🎨 UI Layer"
        StreamlitApp[streamlit_app_integrated.py]
        HierarchyFilter[hierarchy_filter_ui.py]
    end

    subgraph "🧠 Agent Layer"
        SpecBotAgent[core/agent.py]
        ProcessTracker[utils/process_tracker.py]
        Memory[ConversationBufferMemory]
    end

    subgraph "🔍 Tool Layer"
        HybridTool[tools/hybrid_search_tool.py]
        ConfluenceTool[tools/confluence_enhanced_cql_search.py]
        JiraTool[tools/jira_tool.py]
    end

    subgraph "📝 Processing Layer"
        Step1[steps/step1_keyword_extraction.py]
        Step2[steps/step2_datasource_judgment.py]
        Step3[steps/step3_cql_search.py]
        Step4[steps/step4_quality_evaluation.py]
    end

    subgraph "🛠️ Infrastructure Layer"
        CacheManager[utils/cache_manager.py]
        Settings[config/settings.py]
        LogConfig[utils/log_config.py]
        HierarchyManager[utils/confluence_hierarchy_manager.py]
    end

    subgraph "💾 Data Layer"
        SQLite[(SQLite Cache DB)]
        EnvFiles[(.env files)]
    end

    StreamlitApp --> SpecBotAgent
    StreamlitApp --> HierarchyFilter
    HierarchyFilter --> HierarchyManager
    
    SpecBotAgent --> HybridTool
    SpecBotAgent --> ProcessTracker
    SpecBotAgent --> Memory
    
    HybridTool --> Step1
    HybridTool --> Step2
    HybridTool --> Step3
    HybridTool --> Step4
    
    Step3 --> ConfluenceTool
    Step3 --> JiraTool
    
    HierarchyManager --> CacheManager
    Step1 --> Settings
    Step2 --> Settings
    Step3 --> Settings
    
    CacheManager --> SQLite
    Settings --> EnvFiles
```

### **4.2 外部システム依存関係**
```mermaid
graph LR
    subgraph "🏢 Internal System"
        ChatBot[仕様書作成支援ボット]
    end

    subgraph "🤖 AI Services"
        Gemini[Google Gemini API]
    end

    subgraph "🏢 Atlassian Services"
        Confluence[Confluence API]
        Jira[Jira API]
    end

    subgraph "💾 Local Storage"
        SQLiteDB[(SQLite Database)]
        LogFiles[(Log Files)]
        CacheFiles[(Cache Files)]
    end

    ChatBot -->|API Calls| Gemini
    ChatBot -->|REST API| Confluence
    ChatBot -->|REST API| Jira
    ChatBot -->|Read/Write| SQLiteDB
    ChatBot -->|Write| LogFiles
    ChatBot -->|Read/Write| CacheFiles
```

---

## 🔄 **5. アクティビティ図**

### **5.1 ハイブリッド検索プロセス**
```mermaid
flowchart TD
    Start([ユーザー質問入力]) --> ExtractKeywords[Step1: キーワード抽出]
    ExtractKeywords --> CheckGemini{Gemini API利用可能?}
    CheckGemini -->|Yes| GeminiExtract[Gemini AIによる抽出]
    CheckGemini -->|No| RuleExtract[ルールベース抽出]
    GeminiExtract --> JudgeDataSource[Step2: データソース判定]
    RuleExtract --> JudgeDataSource
    
    JudgeDataSource --> CheckConfidence{信頼度 > 0.7?}
    CheckConfidence -->|Yes| ExecuteSearch[Step3: CQL検索実行]
    CheckConfidence -->|No| FallbackSearch[フォールバック検索]
    
    ExecuteSearch --> Strategy1[Strategy1: タイトル優先]
    Strategy1 --> Strategy2[Strategy2: キーワード分割]
    Strategy2 --> Strategy3[Strategy3: フレーズ検索]
    Strategy3 --> MergeResults[結果統合・重複除去]
    
    FallbackSearch --> MergeResults
    MergeResults --> EvaluateQuality[Step4: 品質評価]
    
    EvaluateQuality --> CheckQuality{品質スコア > 0.6?}
    CheckQuality -->|Yes| GenerateResponse[最終回答生成]
    CheckQuality -->|No| RetrySearch[検索戦略再試行]
    RetrySearch --> ExecuteSearch
    
    GenerateResponse --> UpdateCache[キャッシュ更新]
    UpdateCache --> End([回答表示])
```

---

## 📋 **6. 設計パターン・原則**

### **6.1 適用設計パターン**
- **Strategy Pattern**: Step3のCQL検索戦略切り替え
- **Factory Pattern**: Tool作成時の動的生成
- **Observer Pattern**: ProcessTrackerによる進捗監視
- **Singleton Pattern**: Settings、CacheManagerの単一インスタンス
- **Adapter Pattern**: LangChain ToolとStep1-4の連携

### **6.2 SOLID原則適用**
- **Single Responsibility**: 各Stepクラスは単一責務
- **Open/Closed**: 新検索戦略の追加が容易
- **Liskov Substitution**: Tool継承構造の置換可能性
- **Interface Segregation**: 最小限のインターフェース定義
- **Dependency Inversion**: 依存性注入による疎結合

---

## 🔧 **7. 技術的考慮事項**

### **7.1 パフォーマンス設計**
- **非同期処理**: 複数検索戦略の並列実行可能性
- **キャッシュ戦略**: SQLiteによる1時間キャッシュ
- **メモリー管理**: LangChainメモリーの適切な制限

### **7.2 拡張性設計**
- **プラグイン機構**: 新ツール追加の容易性
- **設定外部化**: 環境変数による柔軟な設定
- **モジュール分離**: レイヤー間の疎結合

### **7.3 保守性設計**
- **ログ統合**: 構造化ログによる問題追跡
- **エラーハンドリング**: 段階的フォールバック
- **テスト容易性**: 依存性注入による単体テスト支援

---

*最終更新: 2025年1月24日 - v1.0 システム完成版* 