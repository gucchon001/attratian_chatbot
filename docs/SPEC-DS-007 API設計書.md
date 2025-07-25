# SPEC-DS-007 API設計書

| バージョン | ステータス | 作成日 | 参照ドキュメント |
| :--- | :--- | :--- | :--- |
| **v1.0** | **最新版** | 2025/01/24 | SPEC-DS-001 開発設計書, SPEC-DS-005 UML設計書, SPEC-DS-006 データベース設計書 |

---

## 🌐 **概要**
本ドキュメントは、「仕様書作成支援ボット」の内部API・外部API・データフローを定義するものである。モジュール間通信、外部システム連携、エラーハンドリング等の詳細仕様を明確化する。

---

## 🏗️ **1. API全体アーキテクチャ**

### **1.1 API層構成**
```
┌─────────────────────────────────────────────────────────────┐
│                    🎨 Presentation API                     │
│         Streamlit Web Interface (HTTP REST-like)           │
├─────────────────────────────────────────────────────────────┤
│                    🧠 Application API                      │
│     SpecBotAgent.process_request() - Main Entry Point     │
├─────────────────────────────────────────────────────────────┤
│                    🔍 Business Logic API                   │
│  Step1-4 APIs + HybridSearchTool + ProcessTracker APIs   │
├─────────────────────────────────────────────────────────────┤
│                    🛠️ Infrastructure API                   │
│    CacheManager + Settings + External API Clients        │
├─────────────────────────────────────────────────────────────┤
│                    🌐 External APIs                        │
│      Gemini AI + Confluence REST + Jira REST APIs        │
└─────────────────────────────────────────────────────────────┘
```

### **1.2 API通信プロトコル**
- **内部API**: Python関数呼び出し（同期・非同期）
- **外部API**: HTTPS REST API (JSON形式)
- **認証方式**: API Key認証 (外部API)
- **エラーハンドリング**: 例外ベース + ステータスコード

---

## 🔌 **2. 内部API仕様**

### **2.1 HybridSearchApplication API**

#### **2.1.1 メイン処理API**
```python
class HybridSearchApplication:
    def process_request(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """
        ユーザー質問の処理エントリーポイント
        
        Args:
            user_input (str): ユーザーからの質問文
            **kwargs: 追加パラメータ (filters, session_id等)
            
        Returns:
            Dict[str, Any]: {
                "response": str,           # 最終回答
                "thinking_process": Dict,  # 思考プロセス詳細
                "sources": List[Dict],     # 参照元情報
                "metadata": Dict          # メタデータ
            }
            
        Raises:
            ValueError: 入力パラメータエラー
            APIError: 外部API接続エラー
            ProcessingError: 処理中エラー
        """
    
    def get_conversation_history(self, session_id: str = None) -> List[Dict]:
        """
        会話履歴の取得
        
        Args:
            session_id (str, optional): セッションID
            
        Returns:
            List[Dict]: [
                {
                    "user_message": str,
                    "bot_response": str,
                    "timestamp": datetime,
                    "thinking_process": Dict
                }
            ]
        """
    
    def clear_conversation_history(self, session_id: str = None) -> bool:
        """
        会話履歴のクリア
        
        Args:
            session_id (str, optional): セッションID
            
        Returns:
            bool: 成功/失敗
        """
```

### **2.2 AgentHandoverManager API**

#### **2.2.1 Agent連携処理API**
```python
class AgentHandoverManager:
    def handover_to_agent(self, results: List[Dict], quality_score: float, query: str) -> str:
        """
        検索結果の品質に基づくAgent選択・実行
        
        Args:
            results (List[Dict]): Step1-4検索結果
            quality_score (float): 品質評価スコア (0.0-1.0)
            query (str): 元のユーザー質問
            
        Returns:
            str: Agent処理済み最終回答
            
        Raises:
            AgentSelectionError: Agent選択エラー
            AgentExecutionError: Agent実行エラー
        """
    
    def get_handover_statistics(self) -> Dict[str, Any]:
        """
        Agent連携統計情報の取得
        
        Returns:
            Dict: {
                "total_handovers": int,
                "response_agent_usage": int,
                "fallback_agent_usage": int,
                "average_quality_score": float
            }
        """
```

#### **2.2.2 ResponseGenerationAgent API**
```python
class ResponseGenerationAgent:
    def generate_response(self, search_results: List[Dict], user_query: str) -> str:
        """
        検索結果の統合・要約による最終回答生成
        
        Args:
            search_results (List[Dict]): 検索結果リスト
            user_query (str): 元のユーザー質問
            
        Returns:
            str: 統合・要約された最終回答
            
        Raises:
            LLMError: LLM処理エラー
            FormattingError: レスポンス形式エラー
        """
```

#### **2.2.3 FallbackSearchAgent API**
```python
class FallbackSearchAgent:
    def search_and_respond(self, query: str, filters: Dict) -> str:
        """
        低品質結果時の追加検索・補完処理
        
        Args:
            query (str): 元のユーザー質問
            filters (Dict): フィルター条件
            
        Returns:
            str: 補完処理済み最終回答
            
        Raises:
            EnhancedSearchError: 追加検索エラー
            FallbackProcessError: フォールバック処理エラー
        """
```

#### **2.2.4 AgentSelector API**
```python
class AgentSelector:
    def select_agent_strategy(self, results: List[Dict], quality_score: float, 
                            query: str, filters: Dict) -> Tuple[str, Dict]:
        """
        品質スコアに基づくAgent戦略選択
        
        Args:
            results (List[Dict]): 検索結果
            quality_score (float): 品質スコア
            query (str): ユーザー質問
            filters (Dict): フィルター条件
            
        Returns:
            Tuple[str, Dict]: (選択戦略, 戦略パラメータ)
                戦略: "response_generation" | "fallback_search"
                
        Raises:
            StrategySelectionError: 戦略選択エラー
        """
```

### **2.3 HybridSearchTool API**
```python
class HybridSearchTool:
    def _run(self, query: str, **kwargs) -> str:
        """
        ハイブリッド検索の実行
        
        Args:
            query (str): 検索クエリ
            **kwargs: フィルター条件等
            
        Returns:
            str: フォーマット済み回答
            
        Raises:
            SearchError: 検索エラー
            QualityError: 品質評価エラー
        """
    
    def _execute_hybrid_search(self, query: str) -> Dict[str, Any]:
        """
        内部ハイブリッド検索処理
        
        Returns:
            Dict[str, Any]: {
                "step1_result": Dict,  # キーワード抽出結果
                "step2_result": Dict,  # データソース判定結果  
                "step3_result": Dict,  # CQL検索結果
                "step4_result": Dict   # 品質評価結果
            }
        """
```

### **2.3 Step1-4 Processing APIs**

#### **Step1: KeywordExtractor API**
```python
class KeywordExtractor:
    def extract_keywords(self, query: str) -> Dict[str, Any]:
        """
        キーワード抽出の実行
        
        Args:
            query (str): 元の質問文
            
        Returns:
            Dict[str, Any]: {
                "keywords": List[str],           # 抽出キーワード
                "question_type": str,            # 質問分類
                "confidence": float,             # 抽出信頼度
                "excluded_terms": List[str],     # 除外した汎用句
                "extraction_method": str         # 抽出手法("gemini"|"rules")
            }
        """
    
    def _classify_question_type(self, query: str) -> str:
        """
        質問タイプの分類
        
        Returns:
            str: "機能照会"|"手順確認"|"設計詳細"|"トラブル対応"|"仕様変更"|"全般質問"
        """
```

#### **Step2: DataSourceJudge API**
```python
class DataSourceJudge:
    def judge_optimal_datasource(self, keywords: List[str], search_intent: str) -> Dict[str, Any]:
        """
        最適データソースの判定
        
        Args:
            keywords (List[str]): 抽出済みキーワード
            search_intent (str): 検索意図分類
            
        Returns:
            Dict[str, Any]: {
                "primary_source": str,      # "confluence"|"jira"|"both"
                "confidence": float,        # 判定信頼度 (0.0-1.0)
                "reasoning": str,           # 判定理由
                "suggested_filters": Dict,  # 推奨フィルター
                "optimized_keywords": List[str]  # 最適化済みキーワード
            }
        """
    
    def optimize_keywords_for_search(self, keywords: List[str], datasource: str) -> List[str]:
        """
        データソース用キーワード最適化
        
        Args:
            keywords (List[str]): 元キーワード
            datasource (str): 対象データソース
            
        Returns:
            List[str]: 最適化済みキーワード
        """
```

#### **Step3: CQLSearch API**
```python
class CQLSearch:
    def search_confluence(self, keywords: List[str], filters: Dict = None) -> Dict[str, Any]:
        """
        Confluence CQL検索の実行
        
        Args:
            keywords (List[str]): 検索キーワード
            filters (Dict, optional): フィルター条件
            
        Returns:
            Dict[str, Any]: {
                "results": List[Dict],         # 検索結果
                "strategy_results": Dict,      # 戦略別結果
                "total_found": int,            # 総件数
                "execution_time": float        # 実行時間
            }
        """
    
    def _execute_strategy1(self, keywords: List[str]) -> List[Dict]:
        """Strategy1: タイトル優先検索"""
    
    def _execute_strategy2(self, keywords: List[str]) -> List[Dict]:
        """Strategy2: キーワード分割検索 (AND + OR)"""
    
    def _execute_strategy3(self, keywords: List[str]) -> List[Dict]:
        """Strategy3: フレーズ検索"""
```

#### **Step4: QualityEvaluator API**
```python
class QualityEvaluator:
    def evaluate_search_quality(self, results: List[Dict], keywords: List[str]) -> Dict[str, Any]:
        """
        検索品質の4軸評価
        
        Args:
            results (List[Dict]): 検索結果
            keywords (List[str]): 元キーワード
            
        Returns:
            Dict[str, Any]: {
                "overall_score": float,        # 総合品質スコア
                "relevance_score": float,      # 関連度
                "content_quality": Dict,       # 内容品質
                "freshness": Dict,             # 新鮮度
                "coverage": Dict               # 網羅性
            }
        """
```

### **2.4 Infrastructure APIs**

#### **CacheManager API**
```python
class CacheManager:
    def get_cached_data(self, key: str) -> Optional[Any]:
        """
        キャッシュデータの取得
        
        Args:
            key (str): キャッシュキー
            
        Returns:
            Optional[Any]: キャッシュされたデータ (期限内の場合)
        """
    
    def set_cached_data(self, key: str, data: Any, expiry_hours: int = 24) -> bool:
        """
        キャッシュデータの設定
        
        Args:
            key (str): キャッシュキー
            data (Any): キャッシュするデータ
            expiry_hours (int): 有効期限(時間)
            
        Returns:
            bool: 成功/失敗
        """
    
    def clear_cache(self, pattern: str = None) -> bool:
        """
        キャッシュのクリア
        
        Args:
            pattern (str, optional): キーパターン (None=全削除)
            
        Returns:
            bool: 成功/失敗
        """
```

#### **ProcessTracker API**
```python
class ProcessTracker:
    def start_stage(self, stage_name: str, details: Dict = None) -> None:
        """処理段階の開始"""
    
    def complete_stage(self, stage_name: str, result: Dict) -> None:
        """処理段階の完了"""
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        進捗サマリーの取得
        
        Returns:
            Dict[str, Any]: {
                "stages": List[Dict],      # 各段階の詳細
                "current_stage": str,      # 現在の段階
                "overall_progress": float, # 全体進捗率
                "elapsed_time": float      # 経過時間
            }
        """
```

### **2.4 Agent統合API群 (実装完了)**

#### **2.4.1 AgentHandoverManager API**
```python
class AgentHandoverManager:
    def __init__(self) -> None:
        """Agent連携マネージャー初期化"""
        
    def execute_agent_handover(self,
                              search_results: List[Dict],
                              quality_score: float,
                              user_query: str,
                              filters: Dict[str, Any],
                              pipeline_metadata: Dict[str, Any]) -> str:
        """
        Agent連携実行
        
        Args:
            search_results: Step4までの検索結果
            quality_score: 品質評価スコア
            user_query: ユーザー質問
            filters: フィルター条件
            pipeline_metadata: パイプライン実行メタデータ
            
        Returns:
            最終回答文字列
            
        Raises:
            AgentInitializationError: Agent初期化失敗
            AgentHandoverError: Agent連携処理失敗
        """
        
    def get_handover_statistics(self) -> Dict[str, Any]:
        """Agent連携統計情報取得"""
        
    def _should_use_fallback(self, quality_score: float) -> bool:
        """フォールバック使用判定"""
        
    def _log_handover_event(self, agent_type: str, metadata: Dict) -> None:
        """連携イベントログ記録"""
```

#### **2.4.2 ResponseGenerationAgent API**
```python
class ResponseGenerationAgent:
    def __init__(self) -> None:
        """回答生成Agent初期化"""
        
    def generate_response(self, 
                         search_results: List[Dict], 
                         user_query: str,
                         context: Optional[Dict] = None) -> str:
        """
        統合回答生成
        
        Args:
            search_results: 検索結果リスト
            user_query: ユーザー質問
            context: 追加コンテキスト（会話履歴等）
            
        Returns:
            CLIENTTOMO最適化済み統合回答（ソース情報・信頼度・深掘り提案付き）
            
        Raises:
            ResponseGenerationError: 回答生成失敗
            LLMConnectionError: Gemini API接続失敗
        """
        
    def _enhance_response_with_sources(self, response: str, search_results: List[Dict]) -> str:
        """回答にソース情報を付加"""
        
    def _generate_sources_section(self, search_results: List[Dict]) -> str:
        """ソース情報セクション生成"""
        
    def _generate_followup_suggestions(self, user_query: str, search_results: List[Dict]) -> List[str]:
        """深掘り検索提案生成"""
```

#### **2.4.3 FallbackSearchAgent API**
```python
class FallbackSearchAgent:
    def __init__(self) -> None:
        """フォールバック検索Agent初期化"""
        
    def search_exploratory(self, 
                          query: str, 
                          context: Dict[str, Any]) -> str:
        """
        探索的検索実行
        
        Args:
            query: 検索クエリ
            context: 検索コンテキスト（フィルター、履歴等）
            
        Returns:
            探索的検索結果
            
        Raises:
            FallbackSearchError: 探索的検索失敗
            AtlassianAPIError: Atlassian API接続失敗
        """
        
    def _init_react_agent(self) -> None:
        """ReAct型Agent初期化"""
        
    def _handle_search_error(self, error: Exception) -> str:
        """検索エラーハンドリング"""
```

#### **2.4.4 AgentSelector API**
```python
class AgentSelector:
    def __init__(self) -> None:
        """Agent選択ロジック初期化"""
        
    def select_agent(self, 
                    quality_score: float, 
                    context: Dict[str, Any]) -> str:
        """
        最適Agent選択
        
        Args:
            quality_score: 検索品質スコア (0.0-1.0)
            context: 選択コンテキスト
            
        Returns:
            選択されたAgent種別 ("response_generation" | "fallback_search")
            
        Raises:
            AgentSelectionError: Agent選択失敗
        """
        
    def _evaluate_pipeline_quality(self, search_results: List[Dict]) -> float:
        """パイプライン品質評価"""
        
    def update_usage_stats(self, agent_type: str) -> None:
        """Agent使用統計更新"""
        
    def get_selection_metrics(self) -> Dict[str, Any]:
        """選択メトリクス取得"""
```

### **2.5 Settings統合管理API (強化版)**

#### **2.5.1 Settings API**
```python
class Settings:
    def __init__(self) -> None:
        """設定管理初期化（settings.ini + secrets.env統合）"""
        
    # Gemini設定
    gemini_model: str  # settings.iniから読み込み (gemini-1.5-flash等)
    gemini_temperature: float  # settings.iniから読み込み
    gemini_max_tokens: int  # settings.iniから読み込み
    
    # Atlassian設定
    domain: str  # settings.iniから読み込み
    email: str  # settings.iniから読み込み
    confluence_space: str  # settings.iniから読み込み
    target_project: str  # settings.iniから読み込み
    
    # 自動構築URL
    jira_url: str  # ドメインから自動構築
    confluence_url: str  # ドメインから自動構築
    jira_username: str  # emailから自動設定
    confluence_username: str  # emailから自動設定
    
    # API認証情報（secrets.envから）
    google_api_key: str
    jira_api_token: str
    confluence_api_token: str
    
    def _load_settings_ini(self) -> None:
        """settings.ini読み込み（configparser使用）"""
        
    def _construct_atlassian_urls(self) -> None:
        """AtlassianURL自動構築"""
        
    def _load_environment(self) -> None:
        """環境変数・secrets.env読み込み"""
```

### **2.5 AtlassianAPIClient API**

#### **2.5.1 統合APIクライアント**
```python
class AtlassianAPIClient:
    def __init__(self, jira_url: str, jira_username: str, jira_token: str,
                 confluence_url: str, confluence_username: str, confluence_token: str):
        """Jira/Confluence統合APIクライアント初期化"""
    
    def test_connection(self) -> Dict[str, bool]:
        """
        API接続テスト
        
        Returns:
            Dict[str, bool]: {
                "jira": bool,      # Jira接続成功
                "confluence": bool # Confluence接続成功
            }
        """
    
    def search_jira(self, keywords: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Jira検索実行
        
        Args:
            keywords (List[str]): 検索キーワード
            max_results (int): 最大結果数
            
        Returns:
            List[Dict]: Jira検索結果
        """
    
    def search_confluence(self, keywords: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Confluence検索実行
        
        Args:
            keywords (List[str]): 検索キーワード
            max_results (int): 最大結果数
            
        Returns:
            List[Dict]: Confluence検索結果
        """
```

---

## 🌐 **3. 外部API仕様**

### **3.1 Google Gemini API**

#### **3.1.1 API基本情報 (実装済み)**
- **エンドポイント**: `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent`
- **認証**: API Key認証（環境変数GOOGLE_API_KEY/GEMINI_API_KEY）
- **リクエスト制限**: 60 requests/minute
- **実装モデル**: gemini-1.5-flash（実装確認済み）
- **温度設定**: 0.1（安定性重視）

#### **3.1.2 リクエスト/レスポンス仕様**
```python
# リクエスト例
POST /v1/models/gemini-2.5-flash:generateContent
{
    "contents": [
        {
            "parts": [
                {
                    "text": "質問文の解析プロンプト..."
                }
            ]
        }
    ],
    "generationConfig": {
        "temperature": 0.1,
        "maxOutputTokens": 2048
    }
}

# レスポンス例
{
    "candidates": [
        {
            "content": {
                "parts": [
                    {
                        "text": "抽出結果..."
                    }
                ]
            },
            "finishReason": "STOP"
        }
    ]
}
```

#### **3.1.3 エラーハンドリング**
```python
class GeminiAPIClient:
    def call_gemini(self, prompt: str, **kwargs) -> str:
        """
        Gemini API呼び出し
        
        Raises:
            APIKeyError: API Key無効
            RateLimitError: レート制限超過
            QuotaExceededError: クォータ超過
            NetworkError: ネットワークエラー
            ParseError: レスポンス解析エラー
        """
```

### **3.2 Confluence REST API**

#### **3.2.1 API基本情報 (実装済み)**
- **エンドポイント**: `{confluence_url}/rest/api/` (設定可能)
- **認証**: Basic認証 (email + API token)
- **バージョン**: v1 (Cloud API)
- **レート制限**: 300 requests/minute
- **実装状況**: AtlassianAPIClient統合済み
- **自動URL構築**: /wiki パス自動追加対応

#### **3.2.2 CQL検索API**
```python
# CQL検索エンドポイント
GET /wiki/rest/api/content/search?cql={cql_query}&limit={limit}&start={start}

# CQLクエリ例
{
    "cql": "space = CLIENTTOMO AND (title ~ \"ログイン\" OR text ~ \"ログイン\")",
    "limit": 25,
    "start": 0,
    "expand": "metadata.labels,space,history.lastUpdated,body.storage"
}

# レスポンス例
{
    "results": [
        {
            "id": "123456",
            "type": "page",
            "title": "ログイン機能仕様書",
            "space": {
                "key": "CLIENTTOMO",
                "name": "クライアント TOMO"
            },
            "history": {
                "lastUpdated": {
                    "when": "2024-12-15T10:30:00.000Z"
                }
            },
            "_links": {
                "webui": "/pages/viewpage.action?pageId=123456"
            }
        }
    ],
    "start": 0,
    "limit": 25,
    "size": 3
}
```

#### **3.2.3 エラーハンドリング**
```python
class ConfluenceAPIClient:
    def search_content(self, cql_query: str, **kwargs) -> Dict[str, Any]:
        """
        Confluence CQL検索
        
        Raises:
            AuthenticationError: 認証エラー
            AuthorizationError: 権限エラー  
            InvalidCQLError: CQLクエリエラー
            SpaceNotFoundError: スペース不存在
            NetworkError: ネットワークエラー
            ServerError: サーバーエラー
        """
```

### **3.3 Jira REST API**

#### **3.3.1 API基本情報 (実装済み)**
- **エンドポイント**: `{jira_url}/rest/api/3/` (設定可能)
- **認証**: Basic認証 (email + API token)
- **バージョン**: v3 (最新API)
- **レート制限**: 300 requests/minute
- **実装状況**: AtlassianAPIClient統合済み

#### **3.3.2 JQL検索API (実装済み)**
```python
# JQL検索エンドポイント
POST /rest/api/3/search

# リクエストペイロード例 (実装済み)
{
    "jql": "text ~ \"ログイン\" AND text ~ \"機能\" ORDER BY updated DESC",
    "maxResults": 50,
    "fields": ["key", "summary", "description", "status", "priority", "issuetype", "created", "updated"],
    "expand": ["renderedFields"]
}

# レスポンス例 (実装確認済み)
{
    "issues": [
        {
            "id": "10001", 
            "key": "CTJ-123",
            "fields": {
                "summary": "ログイン機能の改修",
                "description": "詳細説明...",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "issuetype": {"name": "Story"},
                "created": "2024-12-01T09:00:00.000+0900",
                "updated": "2024-12-15T14:30:00.000+0900"
            }
        }
    ],
    "startAt": 0,
    "maxResults": 50,
    "total": 3
}
```

---

## 📊 **4. データフロー仕様**

### **4.1 主要データフロー**
```mermaid
flowchart TD
    User[👤 ユーザー] --> StreamlitUI[🎨 Streamlit UI]
    StreamlitUI --> Agent[🧠 SpecBotAgent]
    
    Agent --> App[📱 HybridSearchApplication]
    App --> Tool[🔍 HybridSearchTool]
    Tool --> Step2[📝 Step2: KeywordExtractor]
    Tool --> Step3[🎯 Step3: DataSourceJudge]
    Tool --> Step4[🔍 Step4: CQLSearchEngine]
    Tool --> Step5[⚖️ Step5: QualityEvaluator]
    App --> HandoverMgr[🤝 AgentHandoverManager]
    
    Step2 --> GeminiAPI[🤖 Gemini API]
    Step3 --> GeminiAPI
    Step4 --> ConfluenceAPI[📚 Confluence API]
    Step4 --> JiraAPI[🎫 Jira API]
    Step4 --> AtlassianAPI[🔗 AtlassianAPIClient]
    
    Step4 --> Cache[💾 CacheManager]
    Cache --> SQLite[(🗄️ SQLite DB)]
    
    Step4 --> Agent
    Agent --> StreamlitUI
    StreamlitUI --> User
```

### **4.2 API呼び出しシーケンス**
```mermaid
sequenceDiagram
    participant U as 👤 User
    participant UI as 🎨 Streamlit
    participant A as 🧠 Agent
    participant T as 🔍 Tool
    participant S1 as 📝 Step1
    participant G as 🤖 Gemini
    participant S3 as 🔍 Step3
    participant C as 📚 Confluence
    participant Cache as 💾 Cache

    U->>UI: 質問入力
    UI->>A: process_request(query)
    A->>T: _run(query)
    
    T->>S1: extract_keywords(query)
    S1->>G: generateContent(prompt)
    G-->>S1: keywords + question_type
    S1-->>T: extraction_result
    
    T->>S3: search_confluence(keywords)
    S3->>Cache: get_cached_data(key)
    Cache-->>S3: None (cache miss)
    
    S3->>C: GET /content/search?cql=...
    C-->>S3: search_results
    
    S3->>Cache: set_cached_data(key, results)
    S3-->>T: formatted_results
    
    T-->>A: final_response
    A-->>UI: response + thinking_process
    UI-->>U: 回答表示
```

---

## 🔧 **5. エラーハンドリング仕様**

### **5.1 エラー分類体系**
```python
# カスタム例外階層
class SpecBotError(Exception):
    """基底例外クラス"""
    pass

class ConfigurationError(SpecBotError):
    """設定エラー"""
    pass

class APIError(SpecBotError):
    """外部API関連エラー"""
    pass

class NetworkError(APIError):
    """ネットワークエラー"""
    pass

class AuthenticationError(APIError):
    """認証エラー"""
    pass

class RateLimitError(APIError):
    """レート制限エラー"""
    pass

class ProcessingError(SpecBotError):
    """処理エラー"""
    pass

class SearchError(ProcessingError):
    """検索エラー"""
    pass

class QualityError(ProcessingError):
    """品質評価エラー"""
    pass
```

### **5.2 エラーレスポンス統一形式**
```python
# 成功レスポンス
{
    "success": True,
    "data": {...},
    "metadata": {
        "timestamp": "2025-01-24T10:30:00Z",
        "execution_time": 1.234,
        "version": "v1.0"
    }
}

# エラーレスポンス
{
    "success": False,
    "error": {
        "code": "SEARCH_ERROR",
        "message": "検索処理中にエラーが発生しました",
        "details": {
            "step": "step3_cql_search",
            "original_error": "Connection timeout",
            "retry_after": 60
        }
    },
    "metadata": {
        "timestamp": "2025-01-24T10:30:00Z",
        "version": "v1.0"
    }
}
```

### **5.3 フォールバック戦略**
```python
class FallbackManager:
    """フォールバック処理管理"""
    
    def execute_with_fallback(self, primary_func, fallback_func, **kwargs):
        """
        プライマリ処理失敗時のフォールバック実行
        
        1. Gemini API → ルールベース抽出
        2. Confluence API → キャッシュデータ  
        3. 複合検索 → 単一検索
        4. 高品質回答 → 基本回答
        """
```

---

## 📈 **6. パフォーマンス仕様**

### **6.1 レスポンス時間目標**
| API種別 | 目標時間 | 最大許容時間 |
|---------|----------|-------------|
| キーワード抽出 | 0.5秒 | 2秒 |
| データソース判定 | 0.2秒 | 1秒 |
| CQL検索 | 1.0秒 | 5秒 |
| 品質評価 | 0.3秒 | 1秒 |
| **総合処理** | **2.0秒** | **8秒** |

### **6.2 キャッシュ戦略**
```python
# キャッシュ階層
L1_CACHE = {
    "type": "memory",
    "ttl": 300,  # 5分
    "target": ["gemini_responses", "recent_searches"]
}

L2_CACHE = {
    "type": "sqlite", 
    "ttl": 3600,  # 1時間
    "target": ["confluence_results", "jira_results", "filter_options"]
}

L3_CACHE = {
    "type": "file",
    "ttl": 86400,  # 24時間  
    "target": ["hierarchy_data", "space_metadata"]
}
```

### **6.3 並列処理戦略**
```python
# 非同期処理可能箇所
async def parallel_search(keywords: List[str]):
    """
    複数検索戦略の並列実行
    """
    tasks = [
        asyncio.create_task(strategy1_search(keywords)),
        asyncio.create_task(strategy2_search(keywords)), 
        asyncio.create_task(strategy3_search(keywords))
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return merge_results(results)
```

---

## 🔒 **7. セキュリティ仕様**

### **7.1 認証・認可**
```python
# API Key管理
class SecurityManager:
    def validate_api_key(self, api_key: str, service: str) -> bool:
        """API Key有効性検証"""
    
    def mask_sensitive_data(self, data: Dict) -> Dict:
        """機密データのマスキング"""
    
    def log_api_access(self, endpoint: str, status: str) -> None:
        """API アクセスログ記録"""
```

### **7.2 データ保護**
- **API Key**: 環境変数・Streamlit Secretsで管理
- **ログ**: 機密情報自動マスキング
- **キャッシュ**: TTL設定による自動削除
- **通信**: HTTPS必須

---

## 📊 **8. 監視・ログ仕様**

### **8.1 ログ出力形式**
```python
# 構造化ログ例
{
    "timestamp": "2025-01-24T10:30:00Z",
    "level": "INFO",
    "component": "step3_cql_search",
    "event": "search_completed",
    "data": {
        "query": "ログイン機能",
        "results_count": 3,
        "execution_time": 1.234,
        "strategy": "strategy2_and_or"
    },
    "trace_id": "abc123",
    "session_id": "user_session_456"
}
```

### **8.2 メトリクス収集**
- **API呼び出し回数**: エンドポイント別
- **レスポンス時間**: パーセンタイル分布
- **エラー率**: エラー種別統計
- **キャッシュヒット率**: レイヤー別効率
- **ユーザー満足度**: 検索品質スコア

---

*最終更新: 2025年1月24日 - v1.0 システム完成版* 