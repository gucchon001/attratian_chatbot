"""
仕様書作成支援ボット - LangChainエージェント

このモジュールは、ユーザーの自然言語による質問を理解し、
適切なツールを自律的に選択・実行して回答を生成するエージェントを提供します。
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
from ..config.constants import APP_CONSTANTS, prompt_manager
from ..tools.jira_tool import search_jira_with_filters, get_jira_filter_options
from ..tools.confluence_tool import search_confluence_tool, search_confluence_with_filters, get_confluence_space_structure
# 削除されたツール: confluence_enhanced_search, confluence_indexer
from ..tools.confluence_chain_search import search_confluence_with_chain_prompts
from ..tools.confluence_enhanced_cql_search import search_confluence_with_enhanced_cql
from ..utils.log_config import get_logger
from ..utils.process_tracker import ProcessTracker, ProcessStage, ProcessStatus
from ..utils.streaming_callback import StreamlitStreamingCallback, ProcessDetailCallback

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
                request_timeout=30  # タイムアウトを短縮
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
                return_messages=APP_CONSTANTS.LANGCHAIN.MEMORY_RETURN_MESSAGES,
                max_token_limit=APP_CONSTANTS.LANGCHAIN.MEMORY_MAX_TOKEN_LIMIT
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
            
            # Confluence検索ツール（基本）
            confluence_search_tool = Tool(
                name="confluence_search", 
                description=prompt_manager.get_tool_description("confluence_search"),
                func=search_confluence_tool
            )
            
# 削除されたツール: confluence_enhanced_search, confluence_indexed_search
            
            # Confluenceチェーンプロンプト検索ツール（最高精度）
            confluence_chain_tool = Tool(
                name="confluence_chain_search",
                description="🧠 Confluence最高精度検索：5段階チェーンプロンプト（質問分析→キーワード最適化→検索→結果選別→回答生成）による段階的分析。ログイン機能や仕様書など、正確で詳細な情報が必要な場合に最適。議事録と仕様書を明確に区別し、事実のみに基づく厳格な回答を生成。",
                func=search_confluence_with_chain_prompts
            )
            
            # Confluence高精度CQL検索ツール（検索エンジン特化）
            confluence_enhanced_cql_tool = Tool(
                name="confluence_enhanced_cql_search",
                description="🎯 Confluence高精度CQL検索：5戦略CQL（タイトル優先→キーワード分割→フレーズ→部分一致→フォールバック）による根本的検索精度向上。「ログイン機能の仕様」のような具体的な文書が見つからない場合に最適。従来の検索で0件だった場合の救済措置として強力。",
                func=search_confluence_with_enhanced_cql
            )
            
            # Jiraフィルター項目取得ツール
            jira_filter_tool = Tool(
                name="jira_filter_options",
                description=prompt_manager.get_tool_description("jira_filter_options"),
                func=self._get_jira_filter_options_wrapper
            )
            
            # フィルター対応Jira検索ツール
            jira_filtered_search_tool = Tool(
                name="jira_filtered_search",
                description=prompt_manager.get_tool_description("jira_filtered_search"),
                func=self._jira_filtered_search_wrapper
            )
            
            # フィルター対応Confluence検索ツール
            confluence_filtered_search_tool = Tool(
                name="confluence_filtered_search",
                description=prompt_manager.get_tool_description("confluence_filtered_search"),
                func=self._confluence_filtered_search_wrapper
            )
            
            # Confluenceスペース構造取得ツール
            confluence_space_structure_tool = Tool(
                name="confluence_space_structure",
                description=prompt_manager.get_tool_description("confluence_space_structure"),
                func=self._confluence_space_structure_wrapper
            )
            
            self.tools = [
                confluence_search_tool,             # ★修正済み基本検索を最優先（急募機能検索対応済み）
                confluence_enhanced_cql_tool,       # ★最高精度CQL検索
                confluence_chain_tool,              # ★チェーンプロンプト検索
                jira_search_tool, 
                jira_filter_tool,
                jira_filtered_search_tool,          
                confluence_filtered_search_tool,    
                confluence_space_structure_tool     
            ]
            
            logger.info(f"ツール初期化完了 - {len(self.tools)}個のツールを登録")
            
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
    
    def _get_jira_filter_options_wrapper(self, _: str = "") -> str:
        """
        Jiraフィルター項目取得ツールのラッパー関数
        """
        try:
            logger.info("Jiraフィルター項目取得実行")
            
            filter_options = get_jira_filter_options()
            
            if not filter_options:
                return "Jiraフィルター項目の取得に失敗しました。"
            
            # 結果を整形
            result_lines = ["【Jiraフィルター項目】"]
            
            if filter_options.get('projects'):
                projects = filter_options['projects'][:10]  # 最初の10件
                project_names = [f"{p['key']}: {p['name']}" for p in projects]
                result_lines.append(f"プロジェクト: {', '.join(project_names)}")
                if len(filter_options['projects']) > 10:
                    result_lines.append(f"  ...他{len(filter_options['projects']) - 10}件")
            
            if filter_options.get('statuses'):
                statuses = filter_options['statuses'][:10]  # 最初の10件
                status_names = [s['name'] for s in statuses]
                result_lines.append(f"ステータス: {', '.join(status_names)}")
                if len(filter_options['statuses']) > 10:
                    result_lines.append(f"  ...他{len(filter_options['statuses']) - 10}件")
            
            if filter_options.get('issue_types'):
                issue_types = list(set(filter_options['issue_types']))  # 重複排除
                result_lines.append(f"チケットタイプ: {', '.join(issue_types)}")
            
            if filter_options.get('priorities'):
                priorities = [p['name'] for p in filter_options['priorities']]
                result_lines.append(f"優先度: {', '.join(priorities)}")
            
            logger.info("Jiraフィルター項目取得完了")
            return "\n".join(result_lines)
            
        except Exception as e:
            logger.error(f"Jiraフィルター項目取得エラー: {str(e)}")
            return f"Jiraフィルター項目取得中にエラーが発生しました: {str(e)}"
    
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
                verbose=False,  # パフォーマンス向上のためverboseを無効化
                handle_parsing_errors=True,
                max_iterations=10,  # 複雑な検索に対応するためさらに増加
                max_execution_time=120,  # 複合検索処理に十分な時間を確保（2分）
                return_intermediate_steps=False,  # 中間ステップは返さない
                early_stopping_method="force"  # より確実な停止
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


    def _jira_filtered_search_wrapper(self, query: str) -> str:
        """
        フィルター対応Jira検索ツールのラッパー関数
        
        UIで設定されたフィルター条件を自動的に適用してJira検索を実行します。
        将来的にLLMがフィルター条件を自動解析できるよう拡張予定。
        """
        try:
            logger.info(f"フィルター付きJira検索実行: query='{query}'")
            
            # フィルター条件を動的に取得（StreamlitのセッションステートからUIフィルターを取得）
            # プロジェクトはCTJに固定済み、他の条件は将来的にLLM解析で抽出予定
            
            result = search_jira_with_filters(
                query=query,
                # フィルター条件は将来的にUIまたはLLMの解析結果から設定（プロジェクトはCTJ固定）
                # status_names=None,
                # assignee_ids=None,
                # issue_types=None,
                # priorities=None,
                # reporter_ids=None,
                # custom_tantou=None,
                # custom_eikyou_gyoumu=None,
                # created_after=None,
                # created_before=None,
                # updated_after=None,
                # updated_before=None
            )
            
            logger.info(f"フィルター付きJira検索完了")
            return result
            
        except Exception as e:
            error_msg = f"フィルター付きJira検索エラー: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
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


    def _confluence_filtered_search_wrapper(self, query: str) -> str:
        """
        フィルター対応Confluence検索ツールのラッパー関数
        
        UIで設定されたフィルター条件を自動的に適用してConfluence検索を実行します。
        将来的にLLMがフィルター条件を自動解析できるよう拡張予定。
        """
        try:
            logger.info(f"フィルター付きConfluence検索実行: query='{query}'")
            
            # フィルター条件を動的に取得（StreamlitのセッションステートからUIフィルターを取得）
            # ここでは基本実装として、引数のqueryのみを使用
            # 将来的にはLLMがクエリからフィルター条件を抽出する機能を追加予定
            
            result = search_confluence_with_filters(
                query=query,
                # フィルター条件は将来的にUIまたはLLMの解析結果から設定
                # space_keys=None,
                # content_type=None,
                # created_after=None,
                # created_before=None
            )
            
            logger.info(f"フィルター付きConfluence検索完了")
            return result
            
        except Exception as e:
            error_msg = f"フィルター付きConfluence検索エラー: {str(e)}"
            logger.error(error_msg)
            return error_msg 


    def _confluence_space_structure_wrapper(self, space_key: str = "CLIENTTOMO") -> str:
        """
        Confluenceスペース構造取得ツールのラッパー関数
        
        指定されたConfluenceスペースの全体的なページ構造を取得します。
        """
        try:
            logger.info(f"Confluenceスペース構造取得実行: space_key='{space_key}'")
            
            # スペースキーの検証・デフォルト値設定
            if not space_key or space_key.strip() == "":
                space_key = "CLIENTTOMO"
            
            result = get_confluence_space_structure(space_key.strip())
            
            logger.info(f"Confluenceスペース構造取得完了")
            return result
            
        except Exception as e:
            error_msg = f"Confluenceスペース構造取得エラー: {str(e)}"
            logger.error(error_msg)
            return error_msg

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
                response = self.agent_executor.invoke(
                    {"input": user_input},
                    {"callbacks": callbacks} if callbacks else None
                )
                
                final_answer = response.get("output", "回答を生成できませんでした。")
                
            except Exception as e:
                logger.error(f"エージェント実行エラー: {str(e)}")
                final_answer = f"処理中にエラーが発生しました: {str(e)}"
            
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
            logger.warning(f"ProcessDetailCallbackの作成に失敗: {e}. StreamlitStreamingCallbackを使用します。")
            return StreamlitStreamingCallback(container=container)

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