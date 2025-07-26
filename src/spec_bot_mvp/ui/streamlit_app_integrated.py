"""
統合版 思考プロセス可視化UI（リファクタリング版）

UIロジックと検索実行ロジックをモジュールに分割し、
メインファイルは全体の骨格とコンポーネントの呼び出しに専念。
"""

import streamlit as st
import time
import sys
from pathlib import Path
from typing import Dict, List, Any

# --- パス設定とモジュールインポート ---
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.spec_bot.ui.hierarchy_filter_ui import HierarchyFilterUI
    from src.spec_bot.core.agent import SpecBotAgent
    from src.spec_bot.config.settings import settings
    from src.spec_bot.utils.log_config import setup_logging, get_logger
    SPEC_BOT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ spec_bot モジュールのインポートに失敗: {e}")
    SPEC_BOT_AVAILABLE = False

try:
    from src.spec_bot_mvp.tools.hybrid_search_tool import HybridSearchTool
    from src.spec_bot_mvp.config.settings import Settings
    from src.spec_bot_mvp.ui.components.thinking_process_ui import IntegratedThinkingProcessUI
    from src.spec_bot_mvp.ui.components.search_handler import execute_integrated_search_with_progress
    SPEC_BOT_MVP_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ spec_bot_mvp モジュールのインポートに失敗: {e}")
    SPEC_BOT_MVP_AVAILABLE = False

# --- ロガー設定 ---
if SPEC_BOT_AVAILABLE:
    setup_logging(log_level="INFO", enable_file_logging=True)
    logger = get_logger(__name__)
else:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


# --- アプリケーション初期化 ---
def initialize_app():
    """アプリケーションとセッション状態の初期化"""
    if not SPEC_BOT_MVP_AVAILABLE:
        st.error("⚠️ spec_bot_mvp モジュールが利用できません。システム設定を確認してください。")
        return False

    # セッション状態の初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "thinking_ui" not in st.session_state:
        st.session_state.thinking_ui = IntegratedThinkingProcessUI()
    
    if "hybrid_tool" not in st.session_state:
        try:
            st.session_state.hybrid_tool = HybridSearchTool()
        except Exception as e:
            logger.error(f"HybridSearchTool初期化失敗: {e}")
            st.error(f"検索ツールの初期化に失敗しました: {e}")
            return False
    
    if "filter_ui" not in st.session_state and SPEC_BOT_AVAILABLE:
        try:
            st.session_state.filter_ui = HierarchyFilterUI()
        except Exception as e:
            logger.warning(f"HierarchyFilterUI初期化失敗: {e}")
    
    return True


def render_sidebar():
    """サイドバーレンダリング"""
    with st.sidebar:
        st.markdown("## 📊 検索対象データソース")
        
        # HierarchyFilterUIが利用可能な場合は統合フィルターを表示
        if SPEC_BOT_AVAILABLE and "filter_ui" in st.session_state:
            try:
                st.session_state.filter_ui.render_filter_ui()
            except Exception as e:
                logger.error(f"階層フィルターUI描画エラー: {e}")
                st.error(f"フィルターUIの描画中にエラー: {e}")
        else:
            # 基本フィルター（spec_bot未使用時）
            st.markdown("### 🔍 高度な検索フィルター")
            st.info("階層フィルター機能は spec_bot モジュールが必要です")
            
            # 基本データソース選択
            st.markdown("### 📋 Jiraフィルター")
            jira_enabled = st.checkbox("Jira検索を有効化", value=True)
            
            st.markdown("### 📚 Confluenceフィルター")
            confluence_enabled = st.checkbox("Confluence検索を有効化", value=True)


def display_saved_thinking_process(thinking_data: Dict):
    """過去の思考プロセス表示"""
    if "process_stages" in thinking_data:
        ui = IntegratedThinkingProcessUI()
        ui.process_stages = thinking_data["process_stages"]
        ui.render_process_visualization()
        
        # デバッグ情報も表示（JSON形式）
        with st.expander("🔧 詳細デバッグ情報 (JSON)", expanded=False):
            # process_stages以外のデータをJSONで表示
            debug_data = {k: v for k, v in thinking_data.items() if k != "process_stages"}
            if debug_data:
                st.json(debug_data)
            else:
                st.info("追加のデバッグ情報はありません。")
    else:
        # フォールバック：全データをJSONで表示
        st.json(thinking_data)


def main():
    """メイン処理"""
    # アプリケーション設定
    st.set_page_config(
        page_title="🤖 仕様書作成支援ボット（統合版）",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 初期化
    if not initialize_app():
        return
    
    # タイトル表示
    st.title("🤖 仕様書作成支援ボット（統合版）")
    
    # サイドバー描画
    render_sidebar()
    
    # クリアボタン
    if st.button("🗑️ 会話履歴をクリア", type="secondary"):
        st.session_state.messages = []
        if "thinking_ui" in st.session_state:
            st.session_state.thinking_ui = IntegratedThinkingProcessUI()
        st.rerun()
    
    # 会話履歴表示
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # アシスタントメッセージの思考プロセス表示
            if message["role"] == "assistant" and "thinking_process" in message:
                if message["thinking_process"]:
                    st.markdown("---")
                    with st.expander("🧠 思考プロセスを見る", expanded=False):
                        display_saved_thinking_process(message["thinking_process"])
    
    # チャット入力
    if prompt := st.chat_input("質問を入力してください"):
        # ユーザーメッセージ追加
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # ユーザーメッセージ表示
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # アシスタント回答処理
        with st.chat_message("assistant"):
            thinking_ui = st.session_state.thinking_ui
            process_placeholder = st.empty()

            try:
                # 検索実行（プロセス可視化はexecute_integrated_search_with_progress内で処理）
                result = execute_integrated_search_with_progress(prompt, thinking_ui, process_placeholder)
                
                # 検索完了後も思考プロセスを表示し続ける（クリアしない）
                with process_placeholder.container():
                    thinking_ui.render_process_visualization()

                # 検索結果を表示
                st.markdown(result["search_result"])
                
                # メッセージ履歴に追加
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["search_result"],
                    "thinking_process": result["thinking_process"]
                })

            except Exception as e:
                logger.error(f"検索実行中にエラーが発生: {e}")
                # エラー時も思考プロセスを表示
                with process_placeholder.container():
                    thinking_ui.render_process_visualization()
                st.error(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    main() 