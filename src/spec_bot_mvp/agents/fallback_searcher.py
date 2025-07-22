"""
フォールバック検索Agent

仕様書定義 (SPEC-DS-001 4.1):
- 役割: 固定パイプライン失敗時の探索的検索
- タイプ: ReAct Agent（ツール有り）
- ツール: fallback_jira_search, fallback_confluence_search
- 特徴: 創造的・試行錯誤的な検索実行
"""

import logging
from typing import Dict, List, Any
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from langchain.agents import create_react_agent, AgentExecutor
    from langchain.tools import Tool
    from langchain.prompts import PromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from src.spec_bot_mvp.config.settings import Settings
from src.spec_bot_mvp.utils.atlassian_api_client import AtlassianAPIClient

logger = logging.getLogger(__name__)

class FallbackSearchAgent:
    """
    フォールバック検索Agent
    
    固定検索パイプラインで十分な結果が得られなかった場合に、
    より柔軟で創造的な検索アプローチを実行する。
    ReActフレームワークによる推論・行動・観察のサイクルで最適解を探索。
    """
    
    def __init__(self):
        """Agent初期化"""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain関連パッケージが必要です: pip install langchain langchain-google-genai")
        
        self.settings = Settings()
        self.api_client = AtlassianAPIClient(
            jira_url=self.settings.jira_url,
            jira_username=self.settings.jira_username,
            jira_token=self.settings.jira_api_token,
            confluence_url=self.settings.confluence_url,
            confluence_username=self.settings.confluence_username,
            confluence_token=self.settings.confluence_api_token
        )
        self._init_react_agent()
        logger.info("✅ FallbackSearchAgent初期化完了")
    
    def _init_react_agent(self):
        """ReAct Agent初期化"""
        # Gemini LLM設定（柔軟性重視）
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.settings.google_api_key,
            temperature=0.7,  # 柔軟性重視
            max_output_tokens=2048
        )
        
        # フォールバック検索ツール群
        self.tools = [
            Tool(
                name="fallback_jira_search",
                description="より柔軟なJira検索を実行。キーワードを変更・拡張して再検索する",
                func=self._fallback_jira_search
            ),
            Tool(
                name="fallback_confluence_search",
                description="より柔軟なConfluence検索を実行。類義語・関連語を含めて検索する",
                func=self._fallback_confluence_search
            ),
            Tool(
                name="keyword_expansion",
                description="検索キーワードを拡張・変換して新しい検索戦略を提案する",
                func=self._expand_keywords
            )
        ]
        
        # ReAct Agent構築
        react_prompt = self._get_react_prompt()
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=react_prompt
        )
        
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,  # 最大試行回数
            handle_parsing_errors=True
        )
    
    def _get_react_prompt(self) -> PromptTemplate:
        """ReAct Agent用プロンプトテンプレート"""
        template = """あなたは仕様書検索の専門家AIエージェントです。
固定検索パイプラインで十分な結果が得られなかった場合に、より柔軟で創造的な検索アプローチを実行します。

利用可能なツール:
{tools}

ユーザーからの質問: {input}

あなたの使命は、以下の手順で最適な検索結果を見つけることです：

1. **問題分析**: なぜ固定検索で結果が得られなかったかを分析
2. **戦略立案**: 異なる検索アプローチを複数検討  
3. **試行実行**: ツールを使って様々な検索を試行
4. **結果評価**: 各検索結果の品質と関連性を評価
5. **最終統合**: 最も有用な情報を統合して提供

Think: 現在の状況を分析し、次に何をすべきか考えてください
Action: 実行するツール名
Action Input: ツールへの入力
Observation: ツールの実行結果

この思考→行動→観察のサイクルを、満足のいく結果が得られるまで繰り返してください。

{agent_scratchpad}"""

        return PromptTemplate(
            input_variables=["input", "agent_scratchpad", "tools"],
            template=template
        )
    
    def execute_fallback_search(self, user_query: str, filters: Dict[str, Any]) -> List[Dict]:
        """
        フォールバック検索実行
        
        Args:
            user_query: ユーザー質問
            filters: フィルター条件
            
        Returns:
            フォールバック検索結果リスト
        """
        try:
            logger.info("🔄 フォールバック検索開始: クエリ='%s'", user_query)
            
            # Agent実行（検索戦略の思考・実行を委譲）
            agent_input = f"""
固定検索パイプラインで十分な結果が得られませんでした。
以下の質問について、より効果的な検索戦略を実行してください：

質問: {user_query}
フィルター条件: {filters}

創造的で柔軟なアプローチで、ユーザーの質問に答えるのに役立つ情報を見つけてください。
"""
            
            result = self.agent_executor.invoke({"input": agent_input})
            
            # Agent実行結果を構造化
            search_results = self._parse_agent_result(result, user_query)
            
            logger.info("✅ フォールバック検索完了: 結果数=%d", len(search_results))
            return search_results
            
        except Exception as e:
            logger.error("❌ フォールバック検索失敗: %s", str(e))
            return self._generate_emergency_fallback(user_query)
    
    def _fallback_jira_search(self, query: str) -> str:
        """
        柔軟なJira検索実行
        
        Args:
            query: 検索クエリ
            
        Returns:
            検索結果の文字列表現
        """
        try:
            # より広範囲なJQL検索実行
            flexible_queries = [
                f'text ~ "{query}"',  # 全文検索
                f'summary ~ "{query}" OR description ~ "{query}"',  # 要約・説明検索
                f'text ~ "{query}" AND project = CTJ',  # プロジェクト限定
            ]
            
            all_results = []
            for jql in flexible_queries:
                try:
                    results = self.api_client.search_jira_flexible(jql, max_results=5)
                    all_results.extend(results)
                except Exception as e:
                    logger.warning("Jira検索エラー (JQL: %s): %s", jql, str(e))
            
            if not all_results:
                return f"Jira検索結果なし: クエリ='{query}'"
            
            # 結果を文字列形式で返す
            formatted_results = []
            for result in all_results[:10]:  # 上位10件
                formatted_results.append(
                    f"[Jira] {result.get('key', 'N/A')}: {result.get('summary', 'タイトルなし')}"
                )
            
            return "Jira検索結果:\n" + "\n".join(formatted_results)
            
        except Exception as e:
            return f"Jira検索エラー: {str(e)}"
    
    def _fallback_confluence_search(self, query: str) -> str:
        """
        柔軟なConfluence検索実行
        
        Args:
            query: 検索クエリ
            
        Returns:
            検索結果の文字列表現
        """
        try:
            # より広範囲なCQL検索実行
            flexible_queries = [
                f'text ~ "{query}"',  # 全文検索
                f'title ~ "{query}"',  # タイトル検索
                f'text ~ "{query}" AND space = CLIENTTOMO',  # スペース限定
            ]
            
            all_results = []
            for cql in flexible_queries:
                try:
                    results = self.api_client.search_confluence_flexible(cql, limit=5)
                    all_results.extend(results)
                except Exception as e:
                    logger.warning("Confluence検索エラー (CQL: %s): %s", cql, str(e))
            
            if not all_results:
                return f"Confluence検索結果なし: クエリ='{query}'"
            
            # 結果を文字列形式で返す
            formatted_results = []
            for result in all_results[:10]:  # 上位10件
                formatted_results.append(
                    f"[Confluence] {result.get('title', 'タイトルなし')}"
                )
            
            return "Confluence検索結果:\n" + "\n".join(formatted_results)
            
        except Exception as e:
            return f"Confluence検索エラー: {str(e)}"
    
    def _expand_keywords(self, original_query: str) -> str:
        """
        キーワード拡張・変換
        
        Args:
            original_query: 元のクエリ
            
        Returns:
            拡張キーワード提案
        """
        # 簡易的なキーワード拡張ロジック（Phase 3で改善予定）
        keyword_map = {
            "ログイン": ["認証", "サインイン", "auth", "login", "authentication"],
            "パスワード": ["password", "pwd", "認証情報", "credential"],
            "API": ["エンドポイント", "interface", "REST", "JSON"],
            "エラー": ["error", "例外", "exception", "bug", "不具合"],
            "仕様": ["spec", "requirement", "要件", "specification"],
            "画面": ["UI", "ユーザーインターフェース", "フロントエンド", "view"]
        }
        
        expanded_keywords = []
        for keyword, expansions in keyword_map.items():
            if keyword in original_query:
                expanded_keywords.extend(expansions)
        
        if expanded_keywords:
            return f"拡張キーワード候補: {', '.join(expanded_keywords)}"
        else:
            return f"キーワード拡張提案なし: '{original_query}'"
    
    def _parse_agent_result(self, agent_result: Dict, user_query: str) -> List[Dict]:
        """
        Agent実行結果を構造化された検索結果に変換
        
        Args:
            agent_result: Agent実行結果
            user_query: ユーザークエリ
            
        Returns:
            構造化された検索結果リスト
        """
        # Agent結果から有用な情報を抽出（簡易実装）
        output = agent_result.get('output', '')
        
        # 簡易的な結果構造化
        fallback_result = {
            'source': 'FallbackAgent',
            'title': f'フォールバック検索結果: {user_query}',
            'content': output,
            'summary': output[:200] + '...' if len(output) > 200 else output,
            'relevance_score': 0.6,  # フォールバック結果の基本スコア
            'search_method': 'ReAct Agent',
            'url': ''
        }
        
        return [fallback_result]
    
    def _generate_emergency_fallback(self, user_query: str) -> List[Dict]:
        """
        緊急時フォールバック（Agent実行失敗時）
        
        Args:
            user_query: ユーザークエリ
            
        Returns:
            緊急フォールバック結果
        """
        emergency_result = {
            'source': 'EmergencyFallback',
            'title': '検索システム一時利用不可',
            'content': f"""
申し訳ございません。現在検索システムに一時的な問題が発生しております。

**お客様のご質問**: {user_query}

**代替手段のご提案**:
1. **手動検索**: JiraやConfluenceで直接キーワード検索をお試しください
2. **時間をおいて再試行**: システム復旧後に再度お試しください  
3. **管理者へ連絡**: 緊急の場合は開発チームまでお問い合わせください

ご不便をおかけして申し訳ございません。
""",
            'summary': '検索システム一時利用不可につき代替手段をご提案',
            'relevance_score': 0.1,
            'search_method': 'Emergency Fallback',
            'url': ''
        }
        
        return [emergency_result] 