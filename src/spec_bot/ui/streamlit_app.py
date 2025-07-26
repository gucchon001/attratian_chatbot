"""
仕様書作成支援ボット - StreamlitメインUI（シンプル版）

LangChainエージェントを使用したチャットボットのメインUIです。
"""

import streamlit as st
import logging
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from spec_bot.core.agent import SpecBotAgent
from spec_bot.config.settings import settings
from spec_bot.utils.log_config import setup_logging, get_logger

# ログ設定
setup_logging(log_level="INFO", enable_file_logging=True)
logger = get_logger(__name__)

def initialize_session_state():
    """セッションステートの初期化"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        try:
            st.session_state.agent = SpecBotAgent()
            logger.info("✅ SpecBotAgentの初期化に成功しました。")
        except Exception as e:
            st.error(f"❌ SpecBotAgentの初期化に失敗しました: {e}")
            logger.error(f"❌ SpecBotAgentの初期化失敗: {e}", exc_info=True)
            st.session_state.agent = None

def render_sidebar():
    """サイドバーの描画"""
    with st.sidebar:
        st.title("📊 検索対象データソース")
        st.caption("Confluenceの仕様書とJiraのチケットを検索します")

def render_main_chat():
    """メインのチャットUIを描画する"""
    st.title("🤖 仕様書作成支援ボット")
    st.caption("Atlassianの情報を検索し、回答します。")

    # 履歴の表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザーからのチャット入力
    if prompt := st.chat_input("質問を入力してください（例：ログイン機能について教えて）"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            agent = st.session_state.agent
            if agent:
                try:
                    # エージェント実行
                    response = agent.process_input(prompt)
                    st.markdown(response)
                    
                    # 履歴に追加
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"申し訳ありません、処理中にエラーが発生しました: {e}"
                    st.error(error_msg)
                    logger.error(f"エージェント処理中にエラーが発生: {e}", exc_info=True)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                st.error("エージェントが初期化されていません")

def main():
    """アプリケーションのメイン関数"""
    st.set_page_config(page_title="仕様書作成支援ボット", layout="wide")
    initialize_session_state()
    render_sidebar()
    render_main_chat()

if __name__ == "__main__":
    main() 