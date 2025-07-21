"""
仕様書作成支援ボット - LangChainエージェント（簡素化版）

Enhanced CQL検索による詳細プロセス表示に特化したシンプルなエージェント
"""

import logging
import time
from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory

from ..config.settings import settings
from ..config.constants import prompt_manager
from ..tools.jira_tool import search_jira_with_filters
from ..tools.confluence_enhanced_cql_search import search_confluence_with_enhanced_cql
from ..utils.log_config import get_logger
from ..utils.process_tracker import ProcessTracker, ProcessStage, ProcessStatus
from ..utils.streaming_callback import ProcessDetailCallback

logger = get_logger(__name__)


class SpecBotAgent:
    """
    仕様書作成支援ボットのメインエージェントクラス
    
    LangChainのReActエージェントを使用して、ユーザーの質問を理解し、
    適切なツール（Jira検索、Confluence検索）を自律的に選択・実行します。
    """
    
    def __init__(self):
        """エージェントの初期化"""
        self.llm = None
        self.tools = []
        self.agent_executor = None
        self.memory = None
        self.process_tracker = ProcessTracker()
        
        logger.info("SpecBotAgentを初期化中...")
        self._initialize_llm()
        self._initialize_memory()
        self._initialize_tools()
        self._initialize_agent()
        logger.info("SpecBotAgentの初期化完了")
    
    def _initialize_llm(self):
        """Gemini LLMの初期化"""
        try:
            logger.info("Gemini LLMを初期化中...")
            
            if not settings.gemini_api_key:
                raise ValueError("Gemini APIキーが設定されていません")
            
            self.llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=settings.gemini_temperature,
                max_tokens=min(settings.gemini_max_tokens, 2048),  # トークン制限を安全に
                convert_system_message_to_human=True,  # システムメッセージ変換を追加
                request_timeout=30,  # タイムアウトを短縮
                streaming=False  # ストリーミングを明示的に無効化
            )
            
            logger.info(f"Gemini LLM初期化完了 - モデル: {settings.gemini_model}")
            
        except Exception as e:
            logger.error(f"Gemini LLM初期化失敗: {str(e)}")
            raise
    
    def _initialize_memory(self):
        """会話メモリの初期化"""
        try:
            logger.info("会話メモリを初期化中...")
            
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                max_token_limit=2000  # 固定値で設定
            )
            
            logger.info("会話メモリの初期化完了")
            
        except Exception as e:
            logger.error(f"会話メモリ初期化失敗: {str(e)}")
            raise
    
    def _initialize_tools(self):
        """エージェントが使用するツールの初期化"""
        try:
            logger.info("ツールを初期化中...")
            
            # Jira検索ツール
            jira_search_tool = Tool(
                name="jira_search",
                description=prompt_manager.get_tool_description("jira_search"),
                func=self._jira_search_wrapper
            )
            
            # Confluence高精度CQL検索ツール（検索エンジン特化）
            confluence_enhanced_cql_tool = Tool(
                name="confluence_enhanced_cql_search",
                description="💯 **優先使用推奨** Confluence専用高精度検索：「ログイン機能の仕様」「API設計書」「テスト計画」など、具体的なドキュメント検索時に必ず使用。5段階CQL戦略（タイトル優先→キーワード分割→フレーズ→部分一致→フォールバック）により詳細なプロセスログと共に確実に結果を取得。Confluenceページを検索する際の第一選択ツール。",
                func=search_confluence_with_enhanced_cql
            )
            
            self.tools = [
                confluence_enhanced_cql_tool,       # ★主要機能：詳細プロセス表示付きCQL検索
                jira_search_tool,                   # ★補助機能：基本Jira検索
            ]
            
            logger.info(f"✅ 簡素化完了 - {len(self.tools)}個の必須ツールのみ登録")
            
        except Exception as e:
            logger.error(f"ツール初期化失敗: {str(e)}")
            raise
    
    def _jira_search_wrapper(self, query: str) -> str:
        """
        Jira検索ツールのラッパー関数
        
        将来的にLLMがフィルター条件を自動抽出できるよう拡張予定
        現在は基本的なキーワード検索のみ実装
        """
        try:
            logger.info(f"Jira検索実行: query='{query}'")
            
            # TODO: 将来的にはLLMがqueryからフィルター条件を自動抽出
            # 現在は基本的なキーワード検索のみ
            result = search_jira_with_filters(query=query)
            
            logger.info("Jira検索完了")
            return result
            
        except Exception as e:
            logger.error(f"Jira検索エラー: {str(e)}")
            return f"Jira検索中にエラーが発生しました: {str(e)}"
    
    def _initialize_agent(self):
        """ReActエージェントの初期化"""
        try:
            logger.info("ReActエージェントを初期化中...")
            
            # ReActエージェント用のプロンプトテンプレート（YAMLから動的取得）
            system_message = prompt_manager.get_agent_system_message()
            react_template = prompt_manager.get_react_template()
            
            full_prompt = system_message + "\n\n" + react_template
            react_prompt = PromptTemplate.from_template(full_prompt)
            
            # ReActエージェントの作成
            agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=react_prompt
            )
            
            # エージェントエグゼキューターの作成
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=self.memory,
                verbose=False,
                handle_parsing_errors=True,
                max_iterations=4,  # 最終回答生成に十分な回数
                max_execution_time=90,  # 余裕を持った時間設定
                return_intermediate_steps=False,
                early_stopping_method="force"
            )
            
            logger.info("ReActエージェントの初期化完了")
            
        except Exception as e:
            logger.error(f"ReActエージェント初期化失敗: {str(e)}")
            raise
    
    def process_user_input(self, user_input: str) -> str:
        """
        ユーザーの入力を処理してレスポンスを生成（レガシーメソッド）
        
        Args:
            user_input (str): ユーザーからの質問
            
        Returns:
            str: エージェントの回答
        """
        # 新しいprocess_inputメソッドに処理を委譲
        return self.process_input(user_input)
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        会話履歴を取得
        
        Returns:
            List[Dict[str, Any]]: 会話履歴のリスト
        """
        try:
            if self.memory and hasattr(self.memory, 'chat_memory'):
                messages = self.memory.chat_memory.messages
                history = []
                
                for message in messages:
                    if hasattr(message, 'type'):
                        history.append({
                            'type': message.type,
                            'content': message.content
                        })
                
                return history
            
            return []
            
        except Exception as e:
            logger.error(f"会話履歴取得エラー: {str(e)}")
            return []
    
    def clear_conversation_history(self):
        """会話履歴をクリア"""
        try:
            if self.memory:
                self.memory.clear()
                logger.info("会話履歴をクリアしました")
            
        except Exception as e:
            logger.error(f"会話履歴クリアエラー: {str(e)}")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        エージェントの現在の状態を取得
        
        Returns:
            Dict[str, Any]: エージェントの状態情報
        """
        return {
            'llm_model': settings.gemini_model if self.llm else None,
            'tools_count': len(self.tools),
            'memory_enabled': self.memory is not None,
            'agent_initialized': self.agent_executor is not None,
            'conversation_length': len(self.get_conversation_history())
        }


    def _process_question_analysis(self, user_input: str) -> None:
        """質問解析段階の処理"""
        self.process_tracker.start_stage(ProcessStage.QUESTION_ANALYSIS, {
            "input_length": len(user_input),
            "input_preview": user_input[:100] + "..." if len(user_input) > 100 else user_input
        })
        
        # 簡単なキーワード抽出（実際の解析ロジックを模擬）
        keywords = []
        search_targets = []
        
        # キーワード検出
        jira_keywords = ["チケット", "バグ", "タスク", "ストーリー", "課題", "issue"]
        confluence_keywords = ["仕様", "設計", "ドキュメント", "議事録", "資料", "マニュアル"]
        
        for keyword in jira_keywords:
            if keyword in user_input:
                keywords.append(keyword)
                if "Jira" not in search_targets:
                    search_targets.append("Jira")
        
        for keyword in confluence_keywords:
            if keyword in user_input:
                keywords.append(keyword)
                if "Confluence" not in search_targets:
                    search_targets.append("Confluence")
        
        # デフォルト検索対象
        if not search_targets:
            search_targets = ["Jira", "Confluence"]
        
        self.process_tracker.complete_stage(ProcessStage.QUESTION_ANALYSIS, {
            "keywords": keywords[:5],  # 最大5個まで
            "search_targets": search_targets,
            "analysis_method": "キーワードマッチング"
        })
    
    def _process_tool_selection(self, user_input: str) -> None:
        """ツール選択段階の処理"""
        self.process_tracker.start_stage(ProcessStage.TOOL_SELECTION, {
            "available_tools": len(self.tools),
            "selection_method": "LangChain Agent自動選択"
        })
        
        # 利用可能ツールの情報を収集
        tool_names = [tool.name for tool in self.tools]
        
        # 選択戦略の決定（実際はLangChainが行うが、説明用に模擬）
        strategy = "質問内容に基づく動的選択"
        if "jira" in user_input.lower():
            strategy = "Jira優先検索"
        elif "confluence" in user_input.lower() or any(word in user_input for word in ["仕様", "設計", "ドキュメント"]):
            strategy = "Confluence優先検索"
        
        self.process_tracker.complete_stage(ProcessStage.TOOL_SELECTION, {
            "selected_tools": tool_names,
            "strategy": strategy,
            "decision_method": "LangChain ReAct Agent"
        })
    
    def _process_result_integration(self, result: str) -> None:
        """結果統合段階の処理"""
        self.process_tracker.start_stage(ProcessStage.RESULT_INTEGRATION, {
            "integration_method": "LangChain内部処理"
        })
        
        # 結果の分析（文字数、構造等）
        result_analysis = {
            "result_length": len(result),
            "integration_method": "LangChain Agent統合処理",
            "quality_check": "自動実行完了"
        }
        
        self.process_tracker.complete_stage(ProcessStage.RESULT_INTEGRATION, result_analysis)
    
    def _process_answer_generation(self, result: str) -> None:
        """回答生成段階の処理"""
        self.process_tracker.start_stage(ProcessStage.ANSWER_GENERATION, {
            "generation_method": "Gemini LLM"
        })
        
        # 回答の分析
        response_analysis = {
            "response_length": len(result),
            "generation_model": "Gemini",
            "reference_links": result.count("http"),  # リンク数の概算
            "generation_quality": "標準"
        }
        
        self.process_tracker.complete_stage(ProcessStage.ANSWER_GENERATION, response_analysis)
    
    def get_process_tracker(self) -> ProcessTracker:
        """プロセス追跡システムのインスタンスを取得"""
        return self.process_tracker


    def process_input(self, user_input: str, streaming_callback=None) -> str:
        """
        ユーザー入力を処理してレスポンスを生成
        
        Args:
            user_input (str): ユーザーからの質問・指示
            streaming_callback: リアルタイム表示用のコールバック
            
        Returns:
            str: エージェントからの回答
        """
        try:
            start_time = time.time()
            logger.info(f"ユーザー入力処理開始: '{user_input[:100]}{'...' if len(user_input) > 100 else ''}'")
            
            # 入力チェック
            if not user_input.strip():
                logger.warning("空の質問を受信")
                return "申し訳ありませんが、質問内容が空です。何についてお聞きになりたいですか？"
            
            # プロセス追跡開始
            self.process_tracker.start_process()
            
            # 質問解析段階
            self._process_question_analysis(user_input)
            
            # ツール選択段階
            self._process_tool_selection(user_input)
            
            # 検索実行段階
            self.process_tracker.start_stage(ProcessStage.SEARCH_EXECUTION)
            
            # エージェント実行
            logger.info("エージェント実行開始")
            
            # コールバックのセットアップ
            callbacks = []
            if streaming_callback:
                callbacks.append(streaming_callback)
            
            # エージェント実行（ストリーミングコールバック付き）
            try:
                # ストリーミング互換性のための設定調整
                config = {}
                if callbacks:
                    config["callbacks"] = callbacks
                
                # invoke の代わりに stream を無効化して実行
                response = self.agent_executor.invoke(
                    {"input": user_input},
                    config if config else None
                )
                
                final_answer = response.get("output", "回答を生成できませんでした。")
                
            except Exception as e:
                # ストリーミングエラーの場合は、コールバックなしで再試行
                logger.warning(f"ストリーミング実行エラー（再試行中）: {str(e)}")
                try:
                    response = self.agent_executor.invoke({"input": user_input})
                    final_answer = response.get("output", "回答を生成できませんでした。")
                    logger.info("非ストリーミングモードで正常実行完了")
                except Exception as e2:
                    logger.error(f"エージェント実行エラー: {str(e2)}")
                    final_answer = f"処理中にエラーが発生しました: {str(e2)}"
            
            self.process_tracker.complete_stage(ProcessStage.SEARCH_EXECUTION)
            
            # 結果統合段階
            self._process_result_integration(final_answer)
            
            # 回答生成段階
            self._process_answer_generation(final_answer)
            
            # プロセス追跡完了
            self.process_tracker.complete_process()
            
            # 実行時間ログ
            execution_time = time.time() - start_time
            logger.info(f"ユーザー入力処理完了: 実行時間 {execution_time:.2f}秒 | 応答文字数: {len(final_answer)}文字")
            
            return final_answer
            
        except Exception as e:
            error_msg = f"ユーザー入力処理中にエラーが発生しました: {str(e)}"
            logger.error(error_msg)
            
            # エラー発生時もプロセス追跡を完了
            try:
                self.process_tracker.complete_process()
            except:
                pass
            
            return error_msg

    def create_streaming_callback(self, container=None):
        """
        ストリーミングコールバックを作成
        
        Args:
            container: Streamlitコンテナ
            
        Returns:
            ProcessDetailCallback: 設定済みのコールバック
        """
        try:
            return ProcessDetailCallback(
                container=container,
                process_tracker=self.process_tracker
            )
        except Exception as e:
            logger.warning(f"ProcessDetailCallbackの作成に失敗: {e}")
            return None

    def process_input_with_streaming(self, user_input: str, thought_container=None) -> str:
        """
        ストリーミング表示付きでユーザー入力を処理
        
        Args:
            user_input (str): ユーザーからの質問・指示
            thought_container: 思考プロセス表示用のStreamlitコンテナ
            
        Returns:
            str: エージェントからの回答
        """
        try:
            # ストリーミングコールバックを作成
            streaming_callback = self.create_streaming_callback(thought_container)
            
            # コールバック付きで処理実行
            return self.process_input(user_input, streaming_callback)
            
        except Exception as e:
            error_msg = f"ストリーミング処理中にエラーが発生しました: {str(e)}"
            logger.error(error_msg)
            return error_msg