# SPEC-DS-005C コンポーネント図設計書

| バージョン | ステータス | 作成日 | 参照ドキュメント |
| :--- | :--- | :--- | :--- |
| **v1.0** | **最新版** | 2025/01/24 | SPEC-DS-005A クラス図設計書, SPEC-DS-005B シーケンス図設計書 |

---

## 🧩 **概要**
本ドキュメントは、「仕様書作成支援ボット」のシステムコンポーネント構成・モジュール依存関係・配置構造をUMLコンポーネント図で詳細に定義するものである。アーキテクチャの物理的構造と論理的分離を明確化する。

---

## 🏗️ **1. システム全体コンポーネント構成**

### **1.1 高レベルアーキテクチャ**
```mermaid
graph TB
    subgraph "🌐 External Systems"
        GeminiAPI[🤖 Google Gemini API]
        ConfluenceAPI[📚 Confluence REST API]
        JiraAPI[🎫 Jira REST API]
    end

    subgraph "🎨 Presentation Layer"
        StreamlitApp[📱 Streamlit Web App]
        UIComponents[🖥️ UI Components]
    end

    subgraph "🧠 Application Layer"
        AgentCore[🤖 Agent Core]
        ProcessManagement[⚙️ Process Management]
    end

    subgraph "🔍 Business Logic Layer"
        SearchEngine[🔍 Search Engine]
        QualityAssurance[⚖️ Quality Assurance]
        KeywordProcessing[📝 Keyword Processing]
    end

    subgraph "🛠️ Infrastructure Layer"
        DataAccess[💾 Data Access]
        Configuration[⚙️ Configuration]
        Logging[📝 Logging]
    end

    subgraph "💾 Data Layer"
        SQLiteDB[(🗄️ SQLite Database)]
        CacheStorage[(💾 Cache Storage)]
        ConfigFiles[(📄 Config Files)]
    end

    %% Presentation Layer connections
    StreamlitApp --> UIComponents
    StreamlitApp --> AgentCore

    %% Application Layer connections
    AgentCore --> ProcessManagement
    AgentCore --> SearchEngine

    %% Business Logic connections
    SearchEngine --> KeywordProcessing
    SearchEngine --> QualityAssurance
    KeywordProcessing --> GeminiAPI

    %% Infrastructure connections
    SearchEngine --> DataAccess
    AgentCore --> Configuration
    ProcessManagement --> Logging

    %% Data Layer connections
    DataAccess --> SQLiteDB
    DataAccess --> CacheStorage
    Configuration --> ConfigFiles

    %% External API connections
    SearchEngine --> ConfluenceAPI
    SearchEngine --> JiraAPI
```

---

## 📦 **2. 詳細コンポーネント分解**

### **2.1 プレゼンテーション層コンポーネント**
```mermaid
graph TB
    subgraph "🎨 Presentation Components"
        direction TB
        
        subgraph "📱 Streamlit Application"
            MainApp[streamlit_app_integrated.py]
            ChatInterface[chat_interface_component]
            ThinkingProcess[thinking_process_component] 
            HistoryManager[history_manager_component]
        end
        
        subgraph "🖥️ UI Components"
            HierarchyFilter[hierarchy_filter_ui.py]
            FilterControls[filter_controls_component]
            SearchResults[search_results_component]
            DeepDive[deep_dive_component]
        end
        
        subgraph "🎛️ Interactive Elements"
            ClearButton[clear_history_button]
            DrillDownButtons[drill_down_buttons]
            AccordionUI[accordion_ui_component]
        end
    end

    %% Internal connections
    MainApp --> ChatInterface
    MainApp --> ThinkingProcess
    MainApp --> HistoryManager
    ChatInterface --> HierarchyFilter
    SearchResults --> DeepDive
    HistoryManager --> ClearButton
    SearchResults --> DrillDownButtons
    ThinkingProcess --> AccordionUI

    %% External interface
    MainApp -.->|st.session_state| SessionState[🔄 Session State]
    MainApp -.->|API calls| AgentCore[🤖 Agent Core]
```

### **2.2 アプリケーション層コンポーネント**
```mermaid
graph TB
    subgraph "🧠 Application Components"
        direction TB
        
        subgraph "🤖 Agent Core"
            SpecBotAgent[SpecBotAgent]
            AgentExecutor[LangChain AgentExecutor]
            MemoryManager[ConversationBufferMemory]
            PromptTemplates[PromptTemplate Manager]
        end
        
        subgraph "⚙️ Process Management"
            ProcessTracker[ProcessTracker]
            StageManager[ProcessStage Manager]
            ProgressMonitor[Progress Monitor]
            ObserverPattern[Observer Notifications]
        end
        
        subgraph "🔄 Integration Layer"
            ToolOrchestrator[Tool Orchestrator]
            CallbackManager[Callback Manager]
            ErrorHandler[Error Handler]
        end
    end

    %% Internal connections
    SpecBotAgent --> AgentExecutor
    SpecBotAgent --> MemoryManager
    SpecBotAgent --> PromptTemplates
    SpecBotAgent --> ProcessTracker
    
    ProcessTracker --> StageManager
    ProcessTracker --> ProgressMonitor
    ProcessTracker --> ObserverPattern
    
    SpecBotAgent --> ToolOrchestrator
    AgentExecutor --> CallbackManager
    ToolOrchestrator --> ErrorHandler

    %% External dependencies
    SpecBotAgent -.->|uses| HybridSearchTool[🔍 Hybrid Search Tool]
    ProcessTracker -.->|notifies| UIObserver[👁️ UI Observer]
```

### **2.3 ビジネスロジック層コンポーネント**
```mermaid
graph TB
    subgraph "🔍 Business Logic Components"
        direction TB
        
        subgraph "🔍 Search Engine"
            HybridSearchTool[HybridSearchTool]
            CQLSearchEngine[CQL Search Engine]
            JQLSearchEngine[JQL Search Engine]
            SearchStrategies[Search Strategies]
        end
        
        subgraph "📝 Keyword Processing"
            KeywordExtractor[KeywordExtractor]
            GeminiIntegration[Gemini Integration]
            RuleBasedExtractor[Rule-Based Extractor]
            DictionaryExpander[Dictionary Expander]
        end
        
        subgraph "🎯 Data Source Management"
            DataSourceJudgment[DataSourceJudgment]
            SourceAnalyzer[Source Analyzer]
            FilterSuggester[Filter Suggester]
        end
        
        subgraph "⚖️ Quality Assurance"
            QualityEvaluator[QualityEvaluator]
            RelevanceCalculator[Relevance Calculator]
            FreshnessChecker[Freshness Checker]
            CoverageAnalyzer[Coverage Analyzer]
        end
        
        subgraph "🔄 Result Processing"
            ResultMerger[Result Merger]
            Deduplicator[Deduplicator]
            Formatter[Response Formatter]
        end
    end

    %% Internal connections within Search Engine
    HybridSearchTool --> CQLSearchEngine
    HybridSearchTool --> JQLSearchEngine
    CQLSearchEngine --> SearchStrategies
    
    %% Keyword Processing connections
    KeywordExtractor --> GeminiIntegration
    KeywordExtractor --> RuleBasedExtractor
    KeywordExtractor --> DictionaryExpander
    
    %% Data Source connections
    DataSourceJudgment --> SourceAnalyzer
    DataSourceJudgment --> FilterSuggester
    
    %% Quality Assurance connections
    QualityEvaluator --> RelevanceCalculator
    QualityEvaluator --> FreshnessChecker
    QualityEvaluator --> CoverageAnalyzer
    
    %% Result Processing connections
    CQLSearchEngine --> ResultMerger
    ResultMerger --> Deduplicator
    Deduplicator --> Formatter
    
    %% Cross-component connections
    HybridSearchTool --> KeywordExtractor
    HybridSearchTool --> DataSourceJudgment
    HybridSearchTool --> QualityEvaluator
    CQLSearchEngine --> ResultMerger
```

### **2.4 インフラストラクチャ層コンポーネント**
```mermaid
graph TB
    subgraph "🛠️ Infrastructure Components"
        direction TB
        
        subgraph "💾 Data Access"
            CacheManager[CacheManager]
            DatabaseConnector[Database Connector]
            HierarchyManager[Hierarchy Manager]
            SessionManager[Session Manager]
        end
        
        subgraph "⚙️ Configuration"
            SettingsManager[Settings Manager]
            EnvLoader[Environment Loader]
            SecretsManager[Secrets Manager]
            APIKeyValidator[API Key Validator]
        end
        
        subgraph "📝 Logging & Monitoring"
            LogConfig[Log Configuration]
            StructuredLogger[Structured Logger]
            PerformanceMonitor[Performance Monitor]
            MetricsCollector[Metrics Collector]
        end
        
        subgraph "🌐 External Integrations"
            APIClientBase[API Client Base]
            GeminiClient[Gemini API Client]
            ConfluenceClient[Confluence API Client]
            JiraClient[Jira API Client]
        end
        
        subgraph "🔒 Security & Auth"
            AuthManager[Authentication Manager]
            TokenManager[Token Manager]
            RateLimiter[Rate Limiter]
        end
    end

    %% Data Access connections
    CacheManager --> DatabaseConnector
    HierarchyManager --> CacheManager
    CacheManager --> SessionManager
    
    %% Configuration connections
    SettingsManager --> EnvLoader
    SettingsManager --> SecretsManager
    SettingsManager --> APIKeyValidator
    
    %% Logging connections
    LogConfig --> StructuredLogger
    StructuredLogger --> PerformanceMonitor
    PerformanceMonitor --> MetricsCollector
    
    %% External Integration connections
    GeminiClient --> APIClientBase
    ConfluenceClient --> APIClientBase
    JiraClient --> APIClientBase
    
    %% Security connections
    APIClientBase --> AuthManager
    AuthManager --> TokenManager
    APIClientBase --> RateLimiter

    %% Cross-layer dependencies
    CacheManager -.->|uses| SettingsManager
    APIClientBase -.->|uses| LogConfig
    PerformanceMonitor -.->|monitors| DatabaseConnector
```

---

## 🔗 **3. コンポーネント間依存関係**

### **3.1 依存関係マトリックス**
| Component | Depends On | Dependency Type |
|-----------|------------|-----------------|
| StreamlitApp | SpecBotAgent | uses |
| SpecBotAgent | HybridSearchTool | aggregates |
| HybridSearchTool | KeywordExtractor, CQLSearch | composes |
| KeywordExtractor | GeminiClient | uses |
| CQLSearch | ConfluenceClient | uses |
| CacheManager | DatabaseConnector | composes |
| SettingsManager | EnvLoader | uses |

### **3.2 インターフェース定義**
```mermaid
graph LR
    subgraph "🔌 Component Interfaces"
        ISearchTool[<<interface>> ISearchTool]
        IAPIClient[<<interface>> IAPIClient]
        ICacheManager[<<interface>> ICacheManager]
        IQualityEvaluator[<<interface>> IQualityEvaluator]
        IProcessObserver[<<interface>> IProcessObserver]
    end

    subgraph "💡 Implementation Classes"
        HybridSearchTool[HybridSearchTool]
        GeminiClient[GeminiAPIClient]
        CacheManager[CacheManager]
        QualityEvaluator[QualityEvaluator]
        UIObserver[StreamlitUIObserver]
    end

    %% Interface implementations
    ISearchTool <|.. HybridSearchTool
    IAPIClient <|.. GeminiClient
    ICacheManager <|.. CacheManager
    IQualityEvaluator <|.. QualityEvaluator
    IProcessObserver <|.. UIObserver
```

---

## 📍 **4. 配置・デプロイメント構成**

### **4.1 物理配置図**
```mermaid
graph TB
    subgraph "💻 Local Development"
        DevMachine[Developer Machine]
        LocalStreamlit[Streamlit Dev Server :8402]
        LocalDB[SQLite Database File]
        LocalLogs[Local Log Files]
    end

    subgraph "☁️ Cloud Services"
        GeminiService[Google Gemini API]
        AtlassianCloud[Atlassian Cloud]
        ConfluenceService[Confluence Service]
        JiraService[Jira Service]
    end

    subgraph "🔧 Configuration Sources"
        EnvFiles[.env Files]
        StreamlitSecrets[Streamlit Secrets]
        ConfigFiles[config/*.ini Files]
    end

    %% Local connections
    DevMachine --> LocalStreamlit
    LocalStreamlit --> LocalDB
    LocalStreamlit --> LocalLogs

    %% External service connections
    LocalStreamlit -.->|HTTPS| GeminiService
    LocalStreamlit -.->|HTTPS| AtlassianCloud
    AtlassianCloud --> ConfluenceService
    AtlassianCloud --> JiraService

    %% Configuration connections
    LocalStreamlit --> EnvFiles
    LocalStreamlit --> StreamlitSecrets
    LocalStreamlit --> ConfigFiles
```

### **4.2 コンポーネント配置マッピング**
```mermaid
graph TB
    subgraph "🐍 Python Process"
        direction TB
        
        subgraph "🧵 Main Thread"
            StreamlitApp[Streamlit Application]
            AgentCore[Agent Core Components]
            SearchEngine[Search Engine Components]
        end
        
        subgraph "🔄 Background Processing"
            CacheCleanup[Cache Cleanup Service]
            LogRotation[Log Rotation Service]
            PerformanceMetrics[Performance Metrics Collection]
        end
        
        subgraph "💾 Persistent Storage"
            SQLiteFile[SQLite Database File]
            LogFiles[Structured Log Files]
            CacheFiles[Cache Storage Files]
        end
    end

    subgraph "🌐 External Network"
        APIs[External API Services]
        ConfigSources[Configuration Sources]
    end

    %% Thread interactions
    StreamlitApp --> AgentCore
    AgentCore --> SearchEngine
    SearchEngine -.->|async| APIs

    %% Background services
    CacheCleanup --> SQLiteFile
    LogRotation --> LogFiles
    PerformanceMetrics --> LogFiles

    %% Persistent storage access
    AgentCore --> SQLiteFile
    SearchEngine --> CacheFiles
    StreamlitApp --> ConfigSources
```

---

## ⚡ **5. パフォーマンス・スケーラビリティ考慮**

### **5.1 コンポーネント負荷分散**
```mermaid
graph TB
    subgraph "🔄 Load Distribution Strategy"
        direction TB
        
        subgraph "⚡ High Frequency Components"
            UIRendering[UI Rendering - 50ms]
            KeywordExtraction[Keyword Extraction - 500ms]
            CacheAccess[Cache Access - 10ms]
        end
        
        subgraph "🕐 Medium Frequency Components"
            CQLSearch[CQL Search - 1000ms]
            QualityEvaluation[Quality Evaluation - 300ms]
            ResultFormatting[Result Formatting - 100ms]
        end
        
        subgraph "🐌 Low Frequency Components"
            HierarchyUpdate[Hierarchy Update - 5000ms]
            LogAggregation[Log Aggregation - 2000ms]
            MetricsCollection[Metrics Collection - 1000ms]
        end
    end

    %% Performance optimization strategies
    UIRendering -.->|st.cache_data| CacheLayer[🚀 Streamlit Cache]
    KeywordExtraction -.->|async/await| AsyncPool[⚡ Async Pool]
    CQLSearch -.->|connection pooling| ConnectionPool[🔗 Connection Pool]
```

### **5.2 メモリー・リソース管理**
```mermaid
graph LR
    subgraph "💾 Memory Management"
        direction TB
        
        subgraph "🔵 Low Memory Footprint"
            Settings[Settings: ~1KB]
            ProcessTracker[Process Tracker: ~10KB]
            Logger[Logger: ~5KB]
        end
        
        subgraph "🟡 Medium Memory Usage"
            ConversationMemory[Conversation Memory: ~100KB]
            CacheData[Cache Data: ~10MB]
            SearchResults[Search Results: ~1MB]
        end
        
        subgraph "🔴 High Memory Potential"
            HierarchyData[Hierarchy Data: ~50MB]
            FullTextIndex[Full Text Index: ~100MB]
            StreamlitSession[Streamlit Session: ~20MB]
        end
    end

    subgraph "♻️ Resource Cleanup"
        AutoCleanup[Automatic Cleanup]
        ManualCleanup[Manual Cleanup Triggers]
        MemoryMonitoring[Memory Monitoring]
    end

    %% Cleanup strategies
    ConversationMemory -.->|TTL: 1hour| AutoCleanup
    CacheData -.->|TTL: 24hours| AutoCleanup
    HierarchyData -.->|user action| ManualCleanup
    StreamlitSession -.->|threshold: 100MB| MemoryMonitoring
```

---

## 🔒 **6. セキュリティ・コンプライアンス**

### **6.1 セキュリティコンポーネント配置**
```mermaid
graph TB
    subgraph "🛡️ Security Architecture"
        direction TB
        
        subgraph "🔐 Authentication Layer"
            APIKeyManager[API Key Manager]
            TokenValidator[Token Validator]
            CredentialStore[Credential Store]
        end
        
        subgraph "🔒 Authorization Layer"
            AccessControl[Access Control]
            RoleManager[Role Manager]
            PermissionChecker[Permission Checker]
        end
        
        subgraph "🔍 Audit & Monitoring"
            SecurityLogger[Security Logger]
            AccessAuditor[Access Auditor]
            AnomalyDetector[Anomaly Detector]
        end
        
        subgraph "🛠️ Security Utils"
            DataMasker[Data Masker]
            InputSanitizer[Input Sanitizer]
            OutputFilter[Output Filter]
        end
    end

    %% Security flow
    APIKeyManager --> TokenValidator
    TokenValidator --> AccessControl
    AccessControl --> PermissionChecker
    
    %% Monitoring flow
    AccessControl -.->|logs| SecurityLogger
    SecurityLogger --> AccessAuditor
    AccessAuditor --> AnomalyDetector
    
    %% Data protection flow
    InputSanitizer --> DataMasker
    DataMasker --> OutputFilter
```

---

## 🚀 **7. 拡張性・将来対応**

### **7.1 Phase 2.2拡張準備**
```mermaid
graph TB
    subgraph "🔮 Future Extensions"
        direction TB
        
        subgraph "📚 Real Confluence Integration"
            LiveConfluenceAPI[Live Confluence API]
            RealTimeSync[Real-time Synchronization]
            ContentIndexer[Content Indexer]
        end
        
        subgraph "🎫 Real Jira Integration"
            LiveJiraAPI[Live Jira API]
            IssueTracker[Issue Tracker]
            WorkflowEngine[Workflow Engine]
        end
        
        subgraph "🔍 Advanced Search"
            MLSearchEngine[ML-based Search Engine]
            SemanticSearch[Semantic Search]
            VectorDatabase[Vector Database]
        end
        
        subgraph "📊 Analytics & BI"
            UsageAnalytics[Usage Analytics]
            PerformanceDashboard[Performance Dashboard]
            UserBehaviorTracker[User Behavior Tracker]
        end
    end

    %% Extension interfaces (準備済み)
    LiveConfluenceAPI -.->|implements| IAPIClient[IAPIClient Interface]
    MLSearchEngine -.->|implements| ISearchTool[ISearchTool Interface]
    UsageAnalytics -.->|implements| IAnalytics[IAnalytics Interface]
```

### **7.2 プラグイン・モジュラー設計**
```mermaid
graph LR
    subgraph "🔌 Plugin Architecture"
        direction TB
        
        subgraph "🏗️ Core Framework"
            PluginManager[Plugin Manager]
            ExtensionRegistry[Extension Registry]
            DynamicLoader[Dynamic Loader]
        end
        
        subgraph "📦 Plugin Types"
            SearchPlugins[Search Plugins]
            UIPlugins[UI Plugins]
            DataPlugins[Data Plugins]
            AuthPlugins[Auth Plugins]
        end
        
        subgraph "🔗 Integration Points"
            HookSystem[Hook System]
            EventBus[Event Bus]
            ConfigExtension[Config Extension]
        end
    end

    %% Plugin management flow
    PluginManager --> ExtensionRegistry
    ExtensionRegistry --> DynamicLoader
    
    %% Plugin types registration
    SearchPlugins -.->|register| ExtensionRegistry
    UIPlugins -.->|register| ExtensionRegistry
    DataPlugins -.->|register| ExtensionRegistry
    AuthPlugins -.->|register| ExtensionRegistry
    
    %% Integration mechanisms
    DynamicLoader --> HookSystem
    HookSystem --> EventBus
    EventBus --> ConfigExtension
```

---

*最終更新: 2025年1月24日 - v1.0 コンポーネント構成完成版* 