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
        
        # 🗑️ コンテンツフィルター（新規追加）
        st.markdown("### 🗑️ コンテンツフィルター")
        
        # 削除ページを含むチェックボックス
        include_deleted = st.checkbox(
            "削除ページを含む",
            value=False,
            help="【削除】【廃止】などのマークが付いたページも検索結果に含める",
            key="include_deleted_pages"
        )
        
        # 除外フィルター状況の可視化
        if include_deleted:
            st.success("🟢 除外フィルター: 無効（すべてのページを表示）")
        else:
            st.info("🔴 除外フィルター: 有効（削除・廃止ページを除外）")
            with st.expander("🔍 除外対象パターン", expanded=False):
                st.caption("以下のパターンを含むタイトルを除外:")
                st.markdown("""
                - 【削除】【削除予定】【削除済み】
                - 【廃止】【廃止予定】【システム廃止】  
                - 【終了】【停止】【無効】【利用停止】
                - 【非推奨】【deprecated】【obsolete】
                - 【テスト用】【一時的】【暫定】
                - %%削除%% %%廃止%% などの%記号
                """)
        
        # Note: ウィジェットにkeyが設定されているため、自動的にst.session_state.include_deleted_pagesに保存される
        
        st.divider()
        
        # フィルターオプション初期化
        if 'filter_options' not in st.session_state:
            st.session_state.filter_options = {
                'statuses': ['TODO', 'In Progress', 'Done', 'Closed'],
                'users': ['kanri@jukust.jp'],
                'issue_types': ['Story', 'Bug', 'Task', 'Epic'],
                'priorities': ['Highest', 'High', 'Medium', 'Low', 'Lowest'],
                'reporters': ['kanri@jukust.jp'],
                'custom_tantou': ['フロントエンド', 'バックエンド', 'インフラ', 'QA'],
                'custom_eikyou_gyoumu': ['ユーザー認証', '決済処理', 'データ連携', 'レポート']
            }
        
        if 'filters' not in st.session_state:
            st.session_state.filters = {}
        
        # Jiraフィルター（最上部に移動）
        with st.expander("📋 Jiraフィルター", expanded=False):
            # ステータス選択
            status_options = ['すべて'] + st.session_state.filter_options['statuses'] 
            selected_status = st.selectbox(
                "ステータス:",
                status_options,
                index=0,
                key='filter_jira_status'
            )
            st.session_state.filters['jira_status'] = selected_status if selected_status != 'すべて' else None
            
            # 担当者選択
            user_options = ['すべて'] + st.session_state.filter_options['users']
            selected_user = st.selectbox(
                "担当者:",
                user_options,
                index=0,
                key='filter_jira_assignee'
            )
            st.session_state.filters['jira_assignee'] = selected_user if selected_user != 'すべて' else None
            
            # チケットタイプ選択
            issue_type_options = ['すべて'] + st.session_state.filter_options.get('issue_types', [])
            selected_issue_type = st.selectbox(
                "チケットタイプ:",
                issue_type_options,
                index=0,
                key='filter_jira_issue_type'
            )
            st.session_state.filters['jira_issue_type'] = selected_issue_type if selected_issue_type != 'すべて' else None
            
            # 優先度選択
            priority_options = ['すべて'] + st.session_state.filter_options.get('priorities', [])
            selected_priority = st.selectbox(
                "優先度:",
                priority_options,
                index=0,
                key='filter_jira_priority'
            )
            st.session_state.filters['jira_priority'] = selected_priority if selected_priority != 'すべて' else None
            
            # 報告者選択
            reporter_options = ['すべて'] + st.session_state.filter_options.get('reporters', [])
            selected_reporter = st.selectbox(
                "報告者:",
                reporter_options,
                index=0,
                key='filter_jira_reporter'
            )
            st.session_state.filters['jira_reporter'] = selected_reporter if selected_reporter != 'すべて' else None
            
            st.divider()
            st.caption("**カスタムフィールド (CTJプロジェクト専用)**")
            
            # カスタムフィールド - 担当
            custom_tantou_options = ['すべて'] + st.session_state.filter_options.get('custom_tantou', ['フロントエンド', 'バックエンド', 'インフラ', 'QA'])
            selected_custom_tantou = st.selectbox(
                "担当 (カスタム):",
                custom_tantou_options,
                index=0,
                key='filter_jira_custom_tantou'
            )
            st.session_state.filters['jira_custom_tantou'] = selected_custom_tantou if selected_custom_tantou != 'すべて' else None
            
            # カスタムフィールド - 影響業務
            custom_eikyou_options = ['すべて'] + st.session_state.filter_options.get('custom_eikyou_gyoumu', ['ユーザー認証', '決済処理', 'データ連携', 'レポート'])
            selected_custom_eikyou = st.selectbox(
                "影響業務:",
                custom_eikyou_options,
                index=0,
                key='filter_jira_custom_eikyou'
            )
            st.session_state.filters['jira_custom_eikyou'] = selected_custom_eikyou if selected_custom_eikyou != 'すべて' else None
            
            st.divider()
            st.caption("**日付範囲フィルター**")
            
            # 作成日範囲
            col1, col2 = st.columns(2)
            with col1:
                created_after = st.date_input(
                    "作成日 (以降):",
                    value=None,
                    key='filter_jira_created_after'
                )
                st.session_state.filters['jira_created_after'] = created_after.strftime('%Y-%m-%d') if created_after else None
            
            with col2:
                created_before = st.date_input(
                    "作成日 (以前):",
                    value=None,
                    key='filter_jira_created_before'
                )
                st.session_state.filters['jira_created_before'] = created_before.strftime('%Y-%m-%d') if created_before else None
            
            # 更新日範囲
            col1, col2 = st.columns(2)
            with col1:
                updated_after = st.date_input(
                    "更新日 (以降):",
                    value=None,
                    key='filter_jira_updated_after'
                )
                st.session_state.filters['jira_updated_after'] = updated_after.strftime('%Y-%m-%d') if updated_after else None
            
            with col2:
                updated_before = st.date_input(
                    "更新日 (以前):",
                    value=None,
                    key='filter_jira_updated_before'
                )
                st.session_state.filters['jira_updated_before'] = updated_before.strftime('%Y-%m-%d') if updated_before else None
        
        # Confluenceフィルター（最上部に移動）
        with st.expander("📚 Confluenceフィルター", expanded=False):
            st.caption("**日付範囲フィルター**")
            
            # 作成日範囲
            col1, col2 = st.columns(2)
            with col1:
                confluence_created_after = st.date_input(
                    "作成日 (以降):",
                    value=None,
                    key='filter_confluence_created_after'
                )
                st.session_state.filters['confluence_created_after'] = confluence_created_after.strftime('%Y-%m-%d') if confluence_created_after else None
            
            with col2:
                confluence_created_before = st.date_input(
                    "作成日 (以前):",
                    value=None,
                    key='filter_confluence_created_before'
                )
                st.session_state.filters['confluence_created_before'] = confluence_created_before.strftime('%Y-%m-%d') if confluence_created_before else None
            
            st.divider()
            
        # HierarchyFilterUIが利用可能な場合は統合フィルターを表示（下部に移動）
        if SPEC_BOT_AVAILABLE and "filter_ui" in st.session_state:
            try:
                selected_items, settings_changed = st.session_state.filter_ui.render_hierarchy_filter()
                # フィルター選択結果をセッション状態に保存
                if settings_changed:
                    st.session_state.hierarchy_filters = selected_items
            except Exception as e:
                logger.error(f"階層フィルターUI描画エラー: {e}")
                st.error(f"フィルターUIの描画中にエラー: {e}")
                
        # フィルター操作ボタン
        if st.button("🗑️ フィルターをクリア", use_container_width=True):
            # フィルターのクリア処理
            for key in list(st.session_state.keys()):
                if key.startswith('filter_'):
                    del st.session_state[key]
            if 'filters' in st.session_state:
                st.session_state.filters.clear()
            st.rerun()
        

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