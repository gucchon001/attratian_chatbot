# SPEC-DS-005A クラス図設計書

| バージョン | ステータス | 作成日 | 参照ドキュメント |
| :--- | :--- | :--- | :--- |
| **v1.0** | **最新版** | 2025/01/24 | SPEC-DS-001 開発設計書, SPEC-DS-002 ハイブリッド検索システム仕様書 |

---

## 📊 **概要**
本ドキュメントは、「仕様書作成支援ボット」のクラス構造・継承関係・依存関係をUMLクラス図で詳細に定義するものである。システムの静的構造を明確化し、オブジェクト指向設計の理解を促進する。

---

## 🏗️ **1. システムクラス概観**

### **1.1 パッケージ構成**
```
📦 仕様書作成支援ボット
├── 🎨 presentation (プレゼンテーション層)
│   ├── streamlit_app_integrated.py
│   └── hierarchy_filter_ui.py
├── 🧠 application (アプリケーション層)
│   ├── SpecBotAgent
│   └── ProcessTracker
├── 🔍 domain (ドメイン層)
│   ├── HybridSearchTool
│   ├── KeywordExtractor
│   ├── DataSourceJudgment
│   ├── CQLSearch
│   └── QualityEvaluator
└── 🛠️ infrastructure (インフラ層)
    ├── CacheManager
    ├── Settings
    └── ConfluenceHierarchyManager
```

---

## 📊 **2. 詳細クラス図**

### **2.1 アプリケーション層クラス図**
```mermaid
classDiagram
    class SpecBotAgent {
        -llm: ChatGoogleGenerativeAI
        -tools: List[Tool]
        -agent_executor: AgentExecutor
        -memory: ConversationBufferMemory
        -process_tracker: ProcessTracker
        +__init__()
        +_initialize_llm(): void
        +_initialize_memory(): void
        +_initialize_tools(): void
        +_initialize_agent(): void
        +process_request(user_input: str, **kwargs): Dict[str, Any]
        +get_conversation_history(session_id: str): List[Dict]
        +clear_conversation_history(session_id: str): bool
        -_create_agent_prompt(): PromptTemplate
        -_handle_agent_error(error: Exception): str
    }

    class ProcessTracker {
        -stages: List[ProcessStage]
        -current_stage_index: int
        -start_time: datetime
        -session_id: str
        +__init__(session_id: str)
        +start_stage(stage_name: str, details: Dict): void
        +complete_stage(stage_name: str, result: Dict): void
        +fail_stage(stage_name: str, error: str): void
        +get_progress_summary(): Dict[str, Any]
        +get_current_stage(): ProcessStage
        +reset(): void
        -_calculate_progress(): float
    }

    class ProcessStage {
        +name: str
        +status: ProcessStatus
        +start_time: datetime
        +end_time: Optional[datetime]
        +details: Dict[str, Any]
        +result: Optional[Dict]
        +error: Optional[str]
        +__init__(name: str)
        +start(): void
        +complete(result: Dict): void
        +fail(error: str): void
        +get_duration(): float
    }

    class ProcessStatus {
        <<enumeration>>
        PENDING
        IN_PROGRESS
        COMPLETED
        FAILED
    }

    SpecBotAgent --> ProcessTracker : tracks
    ProcessTracker --> ProcessStage : manages
    ProcessStage --> ProcessStatus : has_status
```

### **2.2 ドメイン層 - ツール・検索クラス図**
```mermaid
classDiagram
    class HybridSearchTool {
        -step1_extractor: KeywordExtractor
        -step2_judgment: DataSourceJudgment
        -step3_search: CQLSearch
        -step4_quality: QualityEvaluator
        -process_tracker: ProcessTracker
        +__init__()
        +_run(query: str, **kwargs): str
        +_execute_hybrid_search(query: str): Dict[str, Any]
        -_format_final_response(results: Dict): str
        -_handle_search_error(error: Exception): str
    }

    class KeywordExtractor {
        -llm: ChatGoogleGenerativeAI
        -gemini_available: bool
        -specialist_dictionary: Dict[str, List[str]]
        +__init__()
        +extract_keywords(query: str): Dict[str, Any]
        +_init_gemini(): bool
        +_extract_with_gemini(query: str): Dict[str, Any]
        +_extract_with_rules(query: str): Dict[str, Any]
        +_classify_question_type(query: str): str
        +_expand_with_dictionary(keywords: List[str]): List[str]
        -_remove_generic_terms(keywords: List[str]): List[str]
        -_calculate_confidence(method: str, keywords: List[str]): float
    }

    class DataSourceJudgment {
        -llm: ChatGoogleGenerativeAI
        -confidence_threshold: float
        +__init__()
        +judge_optimal_datasource(keywords: List[str], question_type: str): Dict[str, Any]
        +_analyze_keyword_context(keywords: List[str]): Dict[str, Any]
        +_determine_primary_source(analysis: Dict): str
        +_suggest_filters(source: str, keywords: List[str]): Dict[str, Any]
        -_calculate_confidence_score(analysis: Dict): float
    }

    class CQLSearch {
        -api_client: Optional[Any]
        -mock_mode: bool
        -strategy_weights: Dict[str, float]
        +__init__()
        +search_confluence(keywords: List[str], filters: Dict): Dict[str, Any]
        +_execute_strategy1(keywords: List[str]): List[Dict]
        +_execute_strategy2(keywords: List[str]): List[Dict]
        +_execute_strategy3(keywords: List[str]): List[Dict]
        +_merge_results(strategy_results: Dict): List[Dict]
        +_deduplicate_results(results: List[Dict]): List[Dict]
        -_build_cql_query(strategy: str, keywords: List[str]): str
        -_execute_api_call(cql_query: str): Dict[str, Any]
    }

    class QualityEvaluator {
        -relevance_weight: float
        -content_weight: float
        -freshness_weight: float
        -coverage_weight: float
        +__init__()
        +evaluate_search_quality(results: List[Dict], keywords: List[str]): Dict[str, Any]
        +_calculate_relevance_score(result: Dict, keywords: List[str]): float
        +_assess_content_quality(result: Dict): Dict[str, Any]
        +_check_freshness(result: Dict): Dict[str, Any]
        +_analyze_coverage(results: List[Dict], keywords: List[str]): Dict[str, Any]
        -_calculate_keyword_density(text: str, keywords: List[str]): float
        -_assess_document_completeness(result: Dict): float
    }

    HybridSearchTool --> KeywordExtractor : uses
    HybridSearchTool --> DataSourceJudgment : uses
    HybridSearchTool --> CQLSearch : uses
    HybridSearchTool --> QualityEvaluator : uses
```

### **2.3 インフラストラクチャ層クラス図**
```mermaid
classDiagram
    class CacheManager {
        -db_path: str
        -cache_duration_hours: int
        -connection_pool: ConnectionPool
        +__init__(db_path: Optional[str])
        +get_cached_data(key: str): Optional[Any]
        +set_cached_data(key: str, data: Any, expiry_hours: int): bool
        +clear_cache(pattern: str): bool
        +clear_expired_cache(): int
        +get_cache_stats(): Dict[str, Any]
        +_initialize_database(): void
        +_get_connection(): sqlite3.Connection
        +_is_cache_valid(stored_at: datetime): bool
        -_serialize_data(data: Any): str
        -_deserialize_data(data_str: str): Any
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
        +cache_ttl_hours: int
        +max_search_results: int
        +__init__()
        +validate_api_keys(): Dict[str, bool]
        +get_missing_keys(): List[str]
        +reload_settings(): void
        +_load_env_file(): void
        +_load_environment(): void
        +_validate_required_settings(): bool
    }

    class ConfluenceHierarchyManager {
        -cache_manager: CacheManager
        -hierarchy_data: Dict[str, Any]
        -last_update: Optional[datetime]
        +__init__(cache_manager: CacheManager)
        +load_hierarchy_data(include_deleted: bool): Dict[str, Any]
        +get_folder_structure(): Dict[str, Any]
        +filter_by_selection(selected_folders: List[str]): List[str]
        +update_hierarchy_cache(): bool
        +_build_tree_structure(pages: List[Dict]): Dict[str, Any]
        +_flatten_hierarchy(tree: Dict): List[Dict]
        -_sort_hierarchy(items: List[Dict]): List[Dict]
        -_calculate_hierarchy_stats(): Dict[str, int]
    }

    class DatabaseConnection {
        -connection: sqlite3.Connection
        -is_active: bool
        +__init__(db_path: str)
        +execute_query(query: str, params: tuple): sqlite3.Cursor
        +execute_many(query: str, params_list: List[tuple]): void
        +begin_transaction(): void
        +commit_transaction(): void
        +rollback_transaction(): void
        +close(): void
        -_setup_connection(): void
    }

    CacheManager --> DatabaseConnection : uses
    ConfluenceHierarchyManager --> CacheManager : depends_on
    Settings <-- CacheManager : configuration
    Settings <-- ConfluenceHierarchyManager : configuration
```

### **2.4 外部API連携クラス図**
```mermaid
classDiagram
    class APIClientBase {
        <<abstract>>
        -base_url: str
        -timeout: int
        -retry_count: int
        +__init__(base_url: str, timeout: int)
        +make_request(endpoint: str, method: str, **kwargs): Dict[str, Any]
        +handle_rate_limit(): void
        +validate_response(response: Dict): bool
        -_build_headers(): Dict[str, str]
        -_handle_error(error: Exception): None
    }

    class GeminiAPIClient {
        -api_key: str
        -model_name: str
        -generation_config: Dict
        +__init__(api_key: str)
        +generate_content(prompt: str, **kwargs): str
        +_prepare_request_payload(prompt: str): Dict
        +_extract_content_from_response(response: Dict): str
        -_validate_api_key(): bool
        -_handle_gemini_error(error: Dict): str
    }

    class ConfluenceAPIClient {
        -username: str
        -api_token: str
        -space_key: str
        +__init__(base_url: str, username: str, api_token: str)
        +search_content(cql_query: str, **kwargs): Dict[str, Any]
        +get_page_content(page_id: str): Dict[str, Any]
        +get_space_list(): List[Dict]
        +_build_cql_url(cql: str, params: Dict): str
        +_parse_search_results(response: Dict): List[Dict]
        -_authenticate(): bool
        -_handle_confluence_error(error: Dict): str
    }

    class JiraAPIClient {
        -username: str
        -api_token: str
        -project_key: str
        +__init__(base_url: str, username: str, api_token: str)
        +search_issues(jql_query: str, **kwargs): Dict[str, Any]
        +get_issue_details(issue_key: str): Dict[str, Any]
        +get_project_list(): List[Dict]
        +_build_jql_url(jql: str, params: Dict): str
        +_parse_issue_results(response: Dict): List[Dict]
        -_authenticate(): bool
        -_handle_jira_error(error: Dict): str
    }

    APIClientBase <|-- GeminiAPIClient : inherits
    APIClientBase <|-- ConfluenceAPIClient : inherits
    APIClientBase <|-- JiraAPIClient : inherits
```

---

## 🔗 **3. クラス関係・依存関係詳細**

### **3.1 継承関係 (IS-A)**
- `GeminiAPIClient` IS-A `APIClientBase`
- `ConfluenceAPIClient` IS-A `APIClientBase`
- `JiraAPIClient` IS-A `APIClientBase`

### **3.2 集約関係 (HAS-A)**
- `SpecBotAgent` HAS-A `ProcessTracker`
- `HybridSearchTool` HAS-A `KeywordExtractor`, `DataSourceJudgment`, `CQLSearch`, `QualityEvaluator`
- `CacheManager` HAS-A `DatabaseConnection`

### **3.3 依存関係 (USES)**
- `ConfluenceHierarchyManager` USES `CacheManager`
- `KeywordExtractor` USES `GeminiAPIClient`
- `CQLSearch` USES `ConfluenceAPIClient`

### **3.4 関連関係 (ASSOCIATES)**
- `ProcessTracker` ↔ `ProcessStage` (1:many)
- `CacheManager` ↔ `Settings` (many:1)

---

## 📋 **4. 設計パターン適用**

### **4.1 Strategy Pattern**
```mermaid
classDiagram
    class SearchStrategy {
        <<interface>>
        +execute(keywords: List[str]): List[Dict]
    }

    class Strategy1TitleSearch {
        +execute(keywords: List[str]): List[Dict]
    }

    class Strategy2KeywordSearch {
        +execute(keywords: List[str]): List[Dict]
    }

    class Strategy3PhraseSearch {
        +execute(keywords: List[str]): List[Dict]
    }

    class SearchContext {
        -strategy: SearchStrategy
        +set_strategy(strategy: SearchStrategy): void
        +execute_search(keywords: List[str]): List[Dict]
    }

    SearchStrategy <|-- Strategy1TitleSearch
    SearchStrategy <|-- Strategy2KeywordSearch  
    SearchStrategy <|-- Strategy3PhraseSearch
    SearchContext --> SearchStrategy
```

### **4.2 Observer Pattern**
```mermaid
classDiagram
    class ProcessObserver {
        <<interface>>
        +update(stage: str, status: str, data: Dict): void
    }

    class ProcessSubject {
        -observers: List[ProcessObserver]
        +attach(observer: ProcessObserver): void
        +detach(observer: ProcessObserver): void
        +notify(stage: str, status: str, data: Dict): void
    }

    class StreamlitUIObserver {
        +update(stage: str, status: str, data: Dict): void
    }

    class LoggingObserver {
        +update(stage: str, status: str, data: Dict): void
    }

    ProcessObserver <|-- StreamlitUIObserver
    ProcessObserver <|-- LoggingObserver
    ProcessSubject --> ProcessObserver
    ProcessTracker --|> ProcessSubject
```

### **4.3 Factory Pattern**
```mermaid
classDiagram
    class ToolFactory {
        <<abstract>>
        +create_tool(tool_type: str, config: Dict): Tool
    }

    class SearchToolFactory {
        +create_tool(tool_type: str, config: Dict): Tool
        +_create_hybrid_search_tool(config: Dict): HybridSearchTool
        +_create_confluence_tool(config: Dict): ConfluenceTool
        +_create_jira_tool(config: Dict): JiraTool
    }

    class Tool {
        <<abstract>>
        +_run(query: str): str
    }

    ToolFactory <|-- SearchToolFactory
    SearchToolFactory ..> Tool : creates
```

---

## 🔧 **5. クラス責務・原則**

### **5.1 Single Responsibility Principle (SRP)**
| クラス | 単一責務 |
|--------|----------|
| `KeywordExtractor` | キーワード抽出のみ |
| `DataSourceJudgment` | データソース判定のみ |
| `CQLSearch` | CQL検索実行のみ |
| `QualityEvaluator` | 品質評価のみ |
| `CacheManager` | キャッシュ管理のみ |

### **5.2 Open/Closed Principle (OCP)**
- **SearchStrategy**: 新検索戦略追加時、既存コード変更不要
- **APIClientBase**: 新API追加時、継承で対応可能
- **ProcessObserver**: 新通知先追加時、既存観察者への影響なし

### **5.3 Liskov Substitution Principle (LSP)**
- **APIClientBase派生クラス**: 基底クラスと置換可能
- **SearchStrategy実装**: インターフェース準拠で置換可能

### **5.4 Interface Segregation Principle (ISP)**
- **ProcessObserver**: 必要なメソッドのみ定義
- **SearchStrategy**: 検索実行に特化したインターフェース

### **5.5 Dependency Inversion Principle (DIP)**
- **高レベルモジュール**: 抽象に依存（APIClientBase使用）
- **低レベルモジュール**: 具象実装（GeminiAPIClient等）

---

## 🚀 **6. 拡張性・保守性考慮**

### **6.1 新機能追加時の拡張ポイント**
1. **新検索戦略**: `SearchStrategy`インターフェース実装
2. **新API連携**: `APIClientBase`継承
3. **新品質評価軸**: `QualityEvaluator`メソッド追加
4. **新キャッシュ戦略**: `CacheManager`拡張

### **6.2 テスト容易性**
- **依存性注入**: コンストラクタ注入によるモック可能
- **インターフェース分離**: 単体テスト時の部分モック
- **純粋関数**: 副作用なしの関数による予測可能性

---

*最終更新: 2025年1月24日 - v1.0 クラス構造完成版* 