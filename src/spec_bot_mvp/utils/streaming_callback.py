"""
リアルタイムストリーミングコールバック

LangChainエージェントの実行プロセスを透明化し、
LLMの思考プロセスをリアルタイムで表示するためのコールバックハンドラー
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union, Sequence
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import BaseMessage, LLMResult
from langchain.schema.agent import AgentAction, AgentFinish
from langchain.schema.output import GenerationChunk
import streamlit as st
from threading import Lock
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamlitStreamingCallback(BaseCallbackHandler):
    """
    Streamlitアプリ用のストリーミングコールバックハンドラー
    
    LangChainエージェントの実行プロセスを詳細に追跡し、
    Streamlitコンテナにリアルタイムで表示します。
    """
    
    def __init__(self, container=None):
        """
        Args:
            container: Streamlitのコンテナ（st.empty()など）
        """
        super().__init__()
        self.container = container
        self.messages = []
        self.current_step = 0
        self.lock = Lock()
        self.agent_state = "initializing"
        self.current_tool = None
        self.llm_response_buffer = ""
        
    def add_message(self, message: str, message_type: str = "info"):
        """メッセージを追加してコンテナを更新"""
        with self.lock:
            timestamp = time.strftime("%H:%M:%S")
            formatted_message = f"**[{timestamp}]** {message}"
            self.messages.append((formatted_message, message_type))
            self._update_container()
    
    def _update_container(self):
        """Streamlitコンテナを更新"""
        if self.container:
            content = ""
            for message, msg_type in self.messages[-20:]:  # 最新20件のみ表示
                if msg_type == "thought":
                    content += f"🤔 **思考**: {message}\n\n"
                elif msg_type == "action":
                    content += f"⚡ **実行**: {message}\n\n"
                elif msg_type == "observation":
                    content += f"👁️ **結果**: {message}\n\n"
                elif msg_type == "llm_token":
                    content += f"📝 **回答生成**: {message}\n\n"
                else:
                    content += f"ℹ️ {message}\n\n"
            
            try:
                self.container.markdown(content)
            except:
                pass  # Streamlitコンテナが無効な場合は無視
    
    def on_llm_start(
        self, 
        serialized: Dict[str, Any], 
        prompts: List[str], 
        **kwargs: Any
    ) -> None:
        """LLM開始時のコールバック"""
        try:
            self.add_message("🧠 **LLM思考開始**", "info")
        except Exception as e:
            logger.warning(f"on_llm_start callback error: {e}")
        
    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """LLMの新しいトークン生成時のコールバック"""
        try:
            self.llm_response_buffer += token
            
            # 意味のある単位で表示（句読点や改行など）
            if token in ["。", "、", "！", "？", "\n"] or len(self.llm_response_buffer) % 20 == 0:
                self.add_message(f"```\n{self.llm_response_buffer[-100:]}\n```", "llm_token")
        except Exception as e:
            logger.warning(f"on_llm_new_token callback error: {e}")
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """LLM完了時のコールバック"""
        try:
            self.add_message("✅ **LLM思考完了**", "info")
            if self.llm_response_buffer:
                self.add_message(f"**最終応答**:\n```\n{self.llm_response_buffer[-200:]}\n```", "llm_token")
            self.llm_response_buffer = ""
        except Exception as e:
            logger.warning(f"on_llm_end callback error: {e}")
    
    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """LLMエラー時のコールバック"""
        try:
            self.add_message(f"❌ **LLMエラー**: {str(error)}", "error")
        except Exception as e:
            logger.warning(f"on_llm_error callback error: {e}")
    
    def on_chain_start(
        self, 
        serialized: Dict[str, Any], 
        inputs: Dict[str, Any], 
        **kwargs: Any
    ) -> None:
        """チェーン開始時のコールバック - LangChain v0.2+対応"""
        try:
            # LangChain 0.2+では引数構造が変更されている可能性があるため、安全に処理
            chain_name = "Unknown"
            if serialized and isinstance(serialized, dict):
                chain_name = serialized.get("name", "Unknown")
            
            # inputsがNoneまたは辞書でない場合の安全な処理
            input_info = ""
            if inputs is not None and isinstance(inputs, dict):
                # 重要なキーのみを表示
                important_keys = ["input", "query", "question"]
                for key in important_keys:
                    if key in inputs:
                        value = str(inputs[key])[:50]
                        input_info = f" | 入力: {value}{'...' if len(str(inputs[key])) > 50 else ''}"
                        break
            
            self.add_message(f"🔗 **チェーン開始**: {chain_name}{input_info}", "info")
            
        except Exception as e:
            # エラーハンドリング - コールバックエラーを防ぐ
            logger.warning(f"on_chain_start callback error: {e}")
            self.add_message(f"🔗 **チェーン開始**: 詳細取得エラー", "info")
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """チェーン完了時のコールバック"""
        try:
            self.add_message("✅ **チェーン完了**", "info")
        except Exception as e:
            logger.warning(f"on_chain_end callback error: {e}")
    
    def on_chain_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """チェーンエラー時のコールバック"""
        try:
            self.add_message(f"❌ **チェーンエラー**: {str(error)}", "error")
        except Exception as e:
            logger.warning(f"on_chain_error callback error: {e}")
    
    def on_tool_start(
        self, 
        serialized: Dict[str, Any], 
        input_str: str, 
        **kwargs: Any
    ) -> None:
        """ツール開始時のコールバック"""
        try:
            tool_name = "Unknown Tool"
            if serialized and isinstance(serialized, dict):
                tool_name = serialized.get("name", "Unknown Tool")
                
            self.current_tool = tool_name
            self.add_message(f"🔧 **ツール実行開始**: {tool_name}", "action")
            
            if input_str:
                preview = input_str[:100] + ('...' if len(input_str) > 100 else '')
                self.add_message(f"📥 **入力**: {preview}", "action")
        except Exception as e:
            logger.warning(f"on_tool_start callback error: {e}")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """ツール完了時のコールバック"""
        try:
            self.add_message(f"✅ **ツール実行完了**: {self.current_tool}", "observation")
        except Exception as e:
            logger.warning(f"on_tool_end callback error: {e}")
    
    def on_tool_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """ツールエラー時のコールバック"""
        self.add_message(f"❌ **ツールエラー** ({self.current_tool}): {str(error)}", "error")
    
    def on_text(self, text: str, **kwargs: Any) -> None:
        """テキスト出力時のコールバック"""
        # エージェントの思考プロセスを解析
        if "Thought:" in text:
            thought = text.split("Thought:")[-1].split("Action:")[0].strip()
            self.add_message(f"思考: {thought}", "thought")
        elif "Action:" in text:
            action = text.split("Action:")[-1].split("Action Input:")[0].strip()
            self.add_message(f"アクション: {action}", "action")
        elif "Observation:" in text:
            observation = text.split("Observation:")[-1].strip()
            self.add_message(f"観察: {observation[:300]}{'...' if len(observation) > 300 else ''}", "observation")
        else:
            # その他のテキスト
            if text.strip() and len(text.strip()) > 5:
                self.add_message(f"テキスト: {text[:200]}{'...' if len(text) > 200 else ''}", "info")
    
    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """エージェントアクション時のコールバック"""
        self.current_step += 1
        self.add_message(f"🤖 **エージェント ステップ {self.current_step}**", "action")
        self.add_message(f"🎯 **アクション**: {action.tool}", "action")
        self.add_message(f"📋 **入力**: {action.tool_input}", "action")
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """エージェント完了時のコールバック"""
        self.add_message("🎊 **エージェント処理完了**", "info")
        final_output = finish.return_values.get("output", "")
        if final_output:
            self.add_message(f"🎯 **最終回答**: {final_output[:300]}{'...' if len(final_output) > 300 else ''}", "info")
    
    def clear_messages(self):
        """メッセージをクリア"""
        with self.lock:
            self.messages = []
            self._update_container()


class ProcessDetailCallback(StreamlitStreamingCallback):
    """
    プロセス詳細追跡用の拡張コールバック
    
    より詳細な実行情報を提供し、CQL検索の詳細プロセスも表示します。
    """
    
    def __init__(self, container=None, process_tracker=None):
        super().__init__(container)
        self.process_tracker = process_tracker
        self.step_details = {}
        self.cql_search_active = False
        
    def add_cql_message(self, message: str, level: str = "info"):
        """CQL検索専用のメッセージ追加"""
        try:
            with self.lock:
                timestamp = datetime.now().strftime("%H:%M:%S")
                if level == "info":
                    formatted_msg = f"ℹ️ [{timestamp}] {message}"
                elif level == "success":
                    formatted_msg = f"✅ [{timestamp}] {message}"
                elif level == "warning":
                    formatted_msg = f"⚠️ [{timestamp}] {message}"
                else:
                    formatted_msg = f"📝 [{timestamp}] {message}"
                
                self.messages.append((formatted_msg, level))
                self._update_container()
        except Exception as e:
            logger.warning(f"add_cql_message error: {e}")
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        try:
            super().on_llm_start(serialized, prompts, **kwargs)
            
            # プロンプトの詳細を表示
            if prompts and len(prompts) > 0 and len(prompts[0]) > 50:
                prompt_preview = prompts[0][:200] + "..." if len(prompts[0]) > 200 else prompts[0]
                self.add_message(f"📝 **プロンプト**: {prompt_preview}", "info")
        except Exception as e:
            logger.warning(f"ProcessDetailCallback.on_llm_start error: {e}")
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        try:
            super().on_tool_start(serialized, input_str, **kwargs)
            
            tool_name = "Unknown"
            if serialized and isinstance(serialized, dict):
                tool_name = serialized.get("name", "Unknown")
            
            # CQL検索ツールの検出
            if "confluence_enhanced_cql_search" in tool_name:
                self.cql_search_active = True
                self.add_cql_message("🔍 Enhanced CQL検索開始", "info")
                if input_str:
                    preview = input_str[:100] + ('...' if len(input_str) > 100 else '')
                    self.add_cql_message(f"📥 入力クエリ: '{preview}'", "info")
            
            # ProcessTrackerにリアルタイム詳細を追加
            if self.process_tracker:
                try:
                    if hasattr(self.process_tracker, 'add_detail'):
                        self.process_tracker.add_detail(f"ツール実行: {tool_name}")
                except (AttributeError, Exception) as e:
                    logger.debug(f"ProcessTracker add_detail error: {e}")
        except Exception as e:
            logger.warning(f"ProcessDetailCallback.on_tool_start error: {e}")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        try:
            super().on_tool_end(output, **kwargs)
            
            # CQL検索の結果を詳細表示
            if self.cql_search_active:
                self.cql_search_active = False
                self.add_cql_message("✅ Enhanced CQL検索完了", "success")
                
                # 出力からCQL詳細情報を抽出
                if output and "戦略別結果:" in output:
                    lines = output.split('\n')
                    for line in lines:
                        line = line.strip()
                        if "戦略別結果:" in line:
                            self.add_cql_message(f"🎯 {line}", "success")
                        elif "実行時間:" in line:
                            self.add_cql_message(f"⏱️ {line}", "info")
                        elif "検索クエリ:" in line:
                            self.add_cql_message(f"🔍 {line}", "info") 
        except Exception as e:
            logger.warning(f"ProcessDetailCallback.on_tool_end error: {e}") 