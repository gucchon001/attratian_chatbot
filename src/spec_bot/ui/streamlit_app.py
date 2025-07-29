"""
仕様書作成支援ボット - StreamlitメインUI

LangChainエージェントを使用したチャットボットのメインUIです。
会話の連続性とフィルター機能を提供します。
"""

import streamlit as st
import logging
import sys
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import traceback

# プロジェクトルートをPythonパスに追加（新構造対応）
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from spec_bot.core.agent import SpecBotAgent
from ..config.settings import settings
from spec_bot.tools.confluence_tool import get_confluence_page_hierarchy
from spec_bot.tools.confluence_enhanced_cql_search import get_detailed_process_info
from spec_bot.ui.hierarchy_filter_ui import HierarchyFilterUI
from spec_bot.utils.process_tracker import StreamlitProcessDisplay, ProcessStage

# ログ設定
from spec_bot.utils.log_config import setup_logging, get_logger

# アプリケーション開始時にログ設定をセットアップ
setup_logging(log_level="INFO", enable_file_logging=True)
logger = get_logger(__name__)


def initialize_session_state():
    """セッション状態の初期化"""
    
    # エージェントの初期化（一度だけ、または強制再初期化）
    if 'agent' not in st.session_state or st.session_state.get('force_reinit_agent', False):
        try:
            with st.spinner('エージェントを初期化中...'):
                # 古いエージェントがあれば完全に削除
                if 'agent' in st.session_state:
                    del st.session_state['agent']
                
                # 新しいエージェントを作成
                st.session_state.agent = SpecBotAgent()
                
                # メソッド存在確認
                streaming_method = hasattr(st.session_state.agent, 'process_input_with_streaming')
                callback_method = hasattr(st.session_state.agent, 'create_streaming_callback')
                
                # 強制再初期化フラグをクリア
                if 'force_reinit_agent' in st.session_state:
                    del st.session_state['force_reinit_agent']
                    
            logger.info(f"エージェント初期化完了 - ストリーミング機能: {streaming_method}, コールバック機能: {callback_method}")
            
            # デバッグ情報をセッションに保存
            st.session_state['agent_debug'] = {
                'streaming_available': streaming_method,
                'callback_available': callback_method,
                'agent_class': type(st.session_state.agent).__name__,
                'init_time': time.time()
            }
            
        except Exception as e:
            logger.error(f"エージェント初期化エラー: {str(e)}")
            st.error(f"エージェントの初期化に失敗しました: {str(e)}")
            st.error(f"詳細: {type(e).__name__}")
            st.stop()
    
    # チャット履歴の初期化
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # データソース選択の初期化
    if 'data_sources' not in st.session_state:
        st.session_state.data_sources = {
            'confluence': True,  # デフォルトで有効
            'jira': True         # デフォルトで有効
        }
    
    # フィルター設定の初期化（新仕様12+4パラメータ対応）
    if 'filters' not in st.session_state:
        st.session_state.filters = {
            # Jiraフィルター（11パラメータ - プロジェクトはCTJ固定）
            'jira_status': None,
            'jira_assignee': None,
            'jira_issue_type': None,           # ★新規追加
            'jira_priority': None,             # ★新規追加
            'jira_reporter': None,             # ★新規追加
            'jira_custom_tantou': None,        # ★新規追加
            'jira_custom_eikyou': None,        # ★新規追加
            'jira_created_after': None,        # ★新規追加
            'jira_created_before': None,       # ★新規追加
            'jira_updated_after': None,        # ★新規追加
            'jira_updated_before': None,       # ★新規追加
            # Confluenceフィルター（2パラメータ + 階層フィルター）
            'confluence_created_after': None,  # ★新規追加
            'confluence_created_before': None, # ★新規追加
            'confluence_page_hierarchy': None  # ★新規追加: JSON階層フィルター
        }
    
    # ページ階層フィルターの初期化（新機能）
    if 'page_hierarchy_filters' not in st.session_state:
        st.session_state.page_hierarchy_filters = {
            'selected_folders': set(),  # 選択されたフォルダIDのセット
            'hierarchy_data': None      # 階層構造データ
        }
    
    # フィルターオプションのキャッシュ（新仕様対応）
    if 'filter_options' not in st.session_state:
        st.session_state.filter_options = {
            # Jira選択肢（プロジェクトはCTJ固定のため除外）
            'statuses': [],
            'users': [],
            'issue_types': [],          # ★新規追加
            'priorities': [],           # ★新規追加
            'reporters': [],            # ★新規追加
            'custom_tantou': [],        # ★新規追加
            'custom_eikyou_gyoumu': [], # ★新規追加
            # ページ階層選択肢（新機能）
            'page_hierarchy': []        # ★新規追加
        }


def load_filter_options():
    """フィルターオプションの動的読み込み（新仕様対応）"""
    if not st.session_state.filter_options['statuses']:  # まだ読み込まれていない場合
        try:
            with st.spinner('フィルターオプションを読み込み中...'):
                # キャッシュから取得を試行
                from ..utils.cache_manager import CacheManager
                cache_manager = CacheManager()
                
                # Jiraフィルターオプションをキャッシュから取得
                jira_options = cache_manager.get('jira_filter_options')
                confluence_options = cache_manager.get('confluence_filter_options')
                
                # Jiraフィルターオプション処理
                if jira_options:
                    # キャッシュから取得成功
                    st.session_state.filter_options.update(jira_options)
                    logger.info("Jiraフィルターオプションをキャッシュから取得")
                else:
                    # キャッシュにない場合はAPIから取得
                    logger.info("JiraフィルターオプションをAPIから取得中...")
                    
                    # Jiraフィルターオプションを取得
                    try:
                        from ..tools.jira_tool import get_jira_filter_options
                        jira_filter_options = get_jira_filter_options()
                        
                        # パースしてセッションステートに設定
                        if isinstance(jira_filter_options, dict):
                            st.session_state.filter_options.update({
                                'statuses': jira_filter_options.get('statuses', ['TODO', 'In Progress', 'Done']),
                                'users': jira_filter_options.get('users', ['kanri@jukust.jp']),
                                'issue_types': jira_filter_options.get('issue_types', ['Story', 'Bug', 'Task']),
                                'priorities': jira_filter_options.get('priorities', ['High', 'Medium', 'Low']),
                                'reporters': jira_filter_options.get('reporters', ['kanri@jukust.jp']),
                                'custom_tantou': jira_filter_options.get('custom_tantou', ['フロントエンド', 'バックエンド']),
                                'custom_eikyou_gyoumu': jira_filter_options.get('custom_eikyou_gyoumu', ['ユーザー認証', '決済処理'])
                            })
                            
                            # キャッシュに保存（1時間有効）
                            cache_manager.set('jira_filter_options', jira_filter_options, duration_hours=1)
                            
                    except Exception as e:
                        logger.warning(f"Jiraフィルターオプション取得エラー: {str(e)}")
                        # フォールバック: デフォルト値を設定
                        st.session_state.filter_options.update({
                            'statuses': ['TODO', 'In Progress', 'Done', 'Closed'],
                            'users': ['kanri@jukust.jp'],
                            'issue_types': ['Story', 'Bug', 'Task', 'Epic'],
                            'priorities': ['Highest', 'High', 'Medium', 'Low', 'Lowest'],
                            'reporters': ['kanri@jukust.jp'],
                            'custom_tantou': ['フロントエンド', 'バックエンド', 'インフラ', 'QA'],
                            'custom_eikyou_gyoumu': ['ユーザー認証', '決済処理', 'データ連携', 'レポート']
                        })
                    
                # Confluenceフィルターオプション処理
                if confluence_options:
                    # キャッシュから取得成功
                    st.session_state.filter_options.update(confluence_options)
                    logger.info("Confluenceフィルターオプションをキャッシュから取得")
                else:
                    # キャッシュにない場合はAPIから取得
                    logger.info("ConfluenceフィルターオプションをAPIから取得中...")
                    
                    # Confluenceフィルターオプションを取得
                    try:
                        from ..tools.confluence_tool import get_confluence_filter_options
                        confluence_filter_options = get_confluence_filter_options()
                        
                        # パースしてセッションステートに設定
                        if isinstance(confluence_filter_options, dict):
                            st.session_state.filter_options.update({
                                'spaces': confluence_filter_options.get('spaces', ['CLIENTTOMO']),
                                'content_types': confluence_filter_options.get('content_types', ['page', 'blogpost']),
                                'authors': confluence_filter_options.get('authors', [])
                            })
                            
                            # キャッシュに保存（1時間有効）
                            cache_manager.set('confluence_filter_options', confluence_filter_options, duration_hours=1)
                            
                    except Exception as e:
                        logger.warning(f"Confluenceフィルターオプション取得エラー: {str(e)}")
                        # フォールバック: デフォルト値を設定
                        st.session_state.filter_options.update({
                            'spaces': ['CLIENTTOMO'],
                            'content_types': ['page', 'blogpost'],
                            'authors': []
                        })
                    
                    # ★新規追加: ページ階層データを取得
                    try:
                        logger.info("Confluenceページ階層データを取得中...")
                        hierarchy_data = get_confluence_page_hierarchy('CLIENTTOMO')
                        
                        if 'error' not in hierarchy_data:
                            st.session_state.filter_options['page_hierarchy'] = hierarchy_data.get('folders', [])
                            st.session_state.page_hierarchy_filters['hierarchy_data'] = hierarchy_data
                            
                            # キャッシュに保存（1時間有効）
                            cache_manager.set('confluence_page_hierarchy', hierarchy_data, duration_hours=1)
                            logger.info(f"ページ階層データ取得完了: {len(hierarchy_data.get('folders', []))}個のルートフォルダ")
                        else:
                            logger.warning(f"ページ階層データ取得エラー: {hierarchy_data.get('error', '')}")
                            st.session_state.filter_options['page_hierarchy'] = []
                            
                    except Exception as e:
                        logger.warning(f"ページ階層データ取得エラー: {str(e)}")
                        st.session_state.filter_options['page_hierarchy'] = []
                    
                    logger.info("フィルターオプションの取得完了")
                
        except Exception as e:
            logger.error(f"フィルターオプション読み込みエラー: {str(e)}")
            # 完全フォールバック
            st.session_state.filter_options = {
                'statuses': ['TODO', 'In Progress', 'Done'],
                'users': ['kanri@jukust.jp'],
                'issue_types': ['Story', 'Bug', 'Task'],
                'priorities': ['High', 'Medium', 'Low'],
                'reporters': ['kanri@jukust.jp'],
                'custom_tantou': ['フロントエンド', 'バックエンド'],
                'custom_eikyou_gyoumu': ['ユーザー認証', '決済処理'],
                'spaces': ['CLIENTTOMO'],
                'content_types': ['page', 'blogpost']
            }


def render_sidebar():
    """サイドバーの高度なフィルター機能を描画"""
    with st.sidebar:
        # データソース選択を最上部に配置
        st.header("📊 検索対象データソース")
        
        confluence_enabled = st.checkbox(
            "📚 Confluence (仕様書・ドキュメント)",
            value=st.session_state.data_sources['confluence'],
            key='sidebar_data_source_confluence',
            help="Confluenceの仕様書、設計書、議事録などを検索対象に含めます"
        )
        st.session_state.data_sources['confluence'] = confluence_enabled
        
        jira_enabled = st.checkbox(
            "🎫 Jira (チケット・タスク)",
            value=st.session_state.data_sources['jira'],
            key='sidebar_data_source_jira',
            help="Jiraのチケット、バグ、ストーリー、タスクを検索対象に含めます"
        )
        st.session_state.data_sources['jira'] = jira_enabled
        
        # データソースが何も選択されていない場合の警告
        if not confluence_enabled and not jira_enabled:
            st.warning("⚠️ 検索対象データソースが選択されていません。")
        
        st.divider()
        
        st.header("🔍 高度な検索フィルター")
        
        # フィルターオプションの読み込み
        load_filter_options()
        
        # Jiraフィルター
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
            
            # ★新規追加: チケットタイプ選択
            issue_type_options = ['すべて'] + st.session_state.filter_options.get('issue_types', [])
            selected_issue_type = st.selectbox(
                "チケットタイプ:",
                issue_type_options,
                index=0,
                key='filter_jira_issue_type'
            )
            st.session_state.filters['jira_issue_type'] = selected_issue_type if selected_issue_type != 'すべて' else None
            
            # ★新規追加: 優先度選択
            priority_options = ['すべて'] + st.session_state.filter_options.get('priorities', [])
            selected_priority = st.selectbox(
                "優先度:",
                priority_options,
                index=0,
                key='filter_jira_priority'
            )
            st.session_state.filters['jira_priority'] = selected_priority if selected_priority != 'すべて' else None
            
            # ★新規追加: 報告者選択
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
            
            # ★新規追加: カスタムフィールド - 担当
            custom_tantou_options = ['すべて'] + st.session_state.filter_options.get('custom_tantou', ['フロントエンド', 'バックエンド', 'インフラ', 'QA'])
            selected_custom_tantou = st.selectbox(
                "担当 (カスタム):",
                custom_tantou_options,
                index=0,
                key='filter_jira_custom_tantou'
            )
            st.session_state.filters['jira_custom_tantou'] = selected_custom_tantou if selected_custom_tantou != 'すべて' else None
            
            # ★新規追加: カスタムフィールド - 影響業務
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
            
            # ★新規追加: 作成日範囲
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
            
            # ★新規追加: 更新日範囲
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
        
        # Confluenceフィルター
        with st.expander("📚 Confluenceフィルター", expanded=False):
            st.caption("**日付範囲フィルター**")
            
            # ★新規追加: 作成日範囲
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
            
            # ★新機能: JSON階層フィルター
            try:
                hierarchy_ui = HierarchyFilterUI()
                selected_items, settings_changed = hierarchy_ui.render_hierarchy_filter()
                
                # 選択状態をセッションに保存
                st.session_state.page_hierarchy_filters['selected_folders'] = selected_items
                
                # 検索フィルター条件を生成
                if selected_items:
                    folder_filters = hierarchy_ui.get_selected_folder_filters()
                    st.session_state.filters['confluence_page_hierarchy'] = folder_filters
                else:
                    st.session_state.filters['confluence_page_hierarchy'] = None
                    
            except Exception as e:
                logger.error(f"階層フィルターUI描画エラー: {e}")
                st.error(f"階層フィルターの表示中にエラーが発生しました: {str(e)}")
                st.caption("従来のフィルターをご利用ください")
        
        # フィルター操作ボタン
        if st.button("🗑️ フィルターをクリア", use_container_width=True):
            for key in st.session_state.filters:
                st.session_state.filters[key] = None
            # ★新規追加: ページ階層フィルターもクリア
            st.session_state.page_hierarchy_filters['selected_folders'] = set()
            st.rerun()
        
        # 現在のフィルター状態を表示
        st.subheader("📊 現在のフィルター")
        # confluence_page_hierarchyを除外した通常フィルターのみを表示
        active_filters = [k for k, v in st.session_state.filters.items() if v and k != 'confluence_page_hierarchy']
        selected_folders = _get_selected_folder_names()
        
        if active_filters or selected_folders:
            # 通常のフィルターを表示（confluence_page_hierarchy除外）
            for filter_key in active_filters:
                st.caption(f"**{filter_key}**: {st.session_state.filters[filter_key]}")
            
            # ページ階層フィルターを表示（対象フォルダのみ）
            if selected_folders:
                folder_display = ", ".join(selected_folders[:3])
                if len(selected_folders) > 3:
                    folder_display += f" 他{len(selected_folders) - 3}件"
                st.caption(f"**対象フォルダ**: {folder_display}")
        else:
            st.caption("フィルターは設定されていません")


def render_main_chat():
    """メインのチャットUIを描画"""
    
    # ヘッダー
    st.title("🤖 仕様書作成支援ボット")
    st.caption("AtlassianのJiraとConfluenceから情報を検索して、仕様書作成をお手伝いします")
    
    # エージェントの状態表示
    if st.session_state.get('agent'):
        status = st.session_state.agent.get_agent_status()
        debug_info = st.session_state.get('agent_debug', {})
        
        with st.expander("🔧 エージェント状態", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"**LLMモデル**: {status.get('llm_model', 'N/A')}")
                st.caption(f"**ツール数**: {status.get('tools_count', 0)}")
                st.caption(f"**エージェントクラス**: {debug_info.get('agent_class', 'N/A')}")
            with col2:
                st.caption(f"**メモリ**: {'有効' if status.get('memory_enabled') else '無効'}")
                st.caption(f"**会話数**: {status.get('conversation_length', 0)}")
                
                # ストリーミング機能状態表示
                streaming_status = "🟢 利用可能" if debug_info.get('streaming_available') else "🔴 利用不可"
                callback_status = "🟢 利用可能" if debug_info.get('callback_available') else "🔴 利用不可"
                st.caption(f"**ストリーミング**: {streaming_status}")
                st.caption(f"**コールバック**: {callback_status}")
    
    # システム操作ボタン
    with st.expander("⚙️ システム操作", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 エージェント再初期化", key="force_reinit_btn", help="エージェントを強制的に再初期化します"):
                # セッション状態から古いエージェントを完全削除
                if 'agent' in st.session_state:
                    del st.session_state['agent']
                
                # 強制再初期化フラグ設定
                st.session_state['force_reinit_agent'] = True
                
                # デバッグ情報表示
                st.info("🔄 エージェント再初期化を実行中...")
                
                # 即座に新しいエージェントを作成
                try:
                    from ..core.agent import SpecBotAgent
                    st.session_state.agent = SpecBotAgent()
                    
                    # メソッド存在確認
                    has_streaming = hasattr(st.session_state.agent, 'process_input_with_streaming')
                    has_process = hasattr(st.session_state.agent, 'process_input')
                    has_legacy = hasattr(st.session_state.agent, 'process_user_input')
                    
                    st.success(f"✅ エージェント再初期化完了！")
                    st.info(f"🔍 ストリーミングメソッド存在: {has_streaming}")
                    st.info(f"🔍 プロセスメソッド存在: {has_process}")  
                    st.info(f"🔍 レガシーメソッド存在: {has_legacy}")
                    
                    # クリアして強制再初期化フラグ削除
                    if 'force_reinit_agent' in st.session_state:
                        del st.session_state['force_reinit_agent']
                        
                except Exception as e:
                    st.error(f"❌ エージェント再初期化エラー: {e}")
                
                st.rerun()
        
        with col2:
            if st.button("🧹 キャッシュクリア", key="clear_cache_btn", help="Streamlitキャッシュをクリアします"):
                # Streamlitキャッシュをクリア
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("✅ キャッシュをクリアしました")
        
        with col3:
            if st.button("🗂️ 会話履歴クリア", key="clear_history_btn", help="チャット履歴をクリアします"):
                st.session_state.messages = []
                if st.session_state.get('agent'):
                    st.session_state.agent.clear_conversation_history()
                st.success("✅ 会話履歴をクリアしました")
                st.rerun()
    
    # チャット履歴の表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # データソース選択はサイドバーに移動済み
    # データソースが何も選択されていない場合の警告
    if not st.session_state.data_sources['confluence'] and not st.session_state.data_sources['jira']:
        st.warning("⚠️ 検索対象データソースが選択されていません。サイドバーで Confluence または Jira のいずれかを選択してください。")
    
    st.divider()
    
    # ユーザー入力
    if prompt := st.chat_input("質問を入力してください（例：ログイン機能について教えて）"):
        
        # ユーザーメッセージを履歴に追加
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # ユーザーメッセージを表示
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # エージェントの応答を生成
        with st.chat_message("assistant"):
            try:
                # 現在のフィルター設定をプロンプトに追加
                enhanced_prompt = _enhance_prompt_with_filters(prompt)
                
                # プロセス表示機能の有効性を確認
                process_display_enabled = True
                debug_mode = False
                
                # エージェント変数の取得
                current_agent = st.session_state.get('agent')
                
                if debug_mode:
                    st.info("🔍 DEBUG: デバッグモード開始")
                    st.info(f"📊 DEBUG: process_display_enabled = {process_display_enabled}")
                
                if process_display_enabled and current_agent:
                    if debug_mode:
                        st.info("📋 DEBUG: 仕様確認")
                        st.info("• 思考プロセス: ストリーミング内に統合されたリアルタイム詳細表示")
                        st.info("• 出力結果: 思考プロセス直下に表示")
                    
                    # === 1. 統合された思考プロセス（ストリーミング + ProcessTracker）===
                    with st.expander("🔍 思考プロセス（詳細検索実行中）", expanded=True):
                        
                        # CQL検索詳細プロセス表示コンテナ
                        cql_process_container = st.empty()
                        
                        # CQL検索詳細情報を取得・表示（新機能）
                        def display_cql_process_details(query: str):
                            """CQL検索プロセスの詳細をリアルタイム表示"""
                            try:
                                # CQL検索詳細プロセス情報を取得
                                process_info = get_detailed_process_info(query)
                                
                                with cql_process_container.container():
                                    st.markdown("### 🔍 **CQL検索プロセス詳細**")
                                    
                                    # キーワード抽出結果
                                    if "extracted_keywords" in process_info:
                                        st.markdown("#### 🔤 **キーワード抽出 (Gemini 2.0-flash)**")
                                        keywords = process_info["extracted_keywords"]
                                        if keywords:
                                            keyword_display = ", ".join([f"`{kw}`" for kw in keywords])
                                            st.markdown(f"**抽出キーワード**: {keyword_display}")
                                        else:
                                            st.warning("キーワード抽出結果がありません")
                                    
                                    # CQLクエリ詳細
                                    if "process_details" in process_info:
                                        st.markdown("#### 🗂️ **CQLクエリ生成プロセス**")
                                        details = process_info["process_details"]
                                        
                                        for i, detail in enumerate(details, 1):
                                            with st.expander(f"Strategy {i}: {detail.get('strategy', 'Unknown')}", expanded=(i==1)):
                                                st.code(detail.get('cql_query', 'クエリ情報なし'), language='sql')
                                                st.caption(f"結果件数: {detail.get('result_count', 0)}件")
                                    
                                    # 検索実行統計
                                    if "total_results" in process_info:
                                        st.markdown("#### 📊 **検索結果統計**")
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.metric("総結果数", process_info.get("total_results", 0))
                                        with col2:
                                            st.metric("実行時間", f"{process_info.get('execution_time', 0):.2f}秒")
                                        with col3:
                                            strategy_count = len(process_info.get("strategy_results", {}))
                                            st.metric("実行戦略数", strategy_count)
                                    
                                    if "error" in process_info:
                                        st.error(f"❌ CQL検索エラー: {process_info['error']}")
                                
                            except Exception as e:
                                with cql_process_container.container():
                                    st.error(f"❌ CQL詳細表示エラー: {str(e)}")
                        
                        # CQL検索詳細を表示（すべてのクエリで実行）
                        st.markdown("### 🔍 **CQL検索プロセス詳細** (リアルタイム表示)")
                        try:
                            display_cql_process_details(prompt)
                            st.success("✅ CQL検索詳細プロセス表示完了")
                        except Exception as e:
                            st.error(f"❌ CQL詳細表示エラー: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
                        
                        # ProcessTrackerの取得
                        try:
                            process_tracker = current_agent.get_process_tracker()
                            if debug_mode:
                                st.info(f"📡 DEBUG: ProcessTracker取得成功")
                        except AttributeError:
                            process_tracker = None
                            if debug_mode:
                                st.warning("⚠️ DEBUG: ProcessTracker取得失敗")
                        
                        # CQL検索詳細プロセス表示ジェネレータ
                        def cql_detailed_process_generator():
                            import time
                            
                            yield "🔄 **処理を開始しています...**\n\n"
                            time.sleep(0.5)
                            
                            yield "🤖 **エージェントが思考プロセスを開始します**\n\n"
                            time.sleep(0.5)
                            
                            yield "💭 **詳細な思考プロセスは下部のリアルタイム表示をご覧ください**\n\n"
                            
                        # CQL詳細プロセスを表示
                        st.write_stream(cql_detailed_process_generator)
                        
                        # リアルタイム統合表示ジェネレータ
                        def integrated_real_time_generator():
                            import time
                            
                            yield "🔄 **処理を開始しています...**\n\n"
                            time.sleep(0.5)
                            
                            # === 段階1: 質問解析 ===
                            yield "📝 **質問を解析中...**\n"
                            
                            if process_tracker:
                                try:
                                    # 実際のProcessTrackerから情報を取得
                                    analysis_stage = process_tracker.get_stage_info(ProcessStage.QUESTION_ANALYSIS)
                                    if analysis_stage.details:
                                        # promptから動的にキーワードを抽出して表示
                                        # 簡単なキーワード抽出（実際のAI処理の代わり）
                                        import re
                                        keywords = []
                                        if "ログイン" in prompt:
                                            keywords.append("ログイン")
                                        if "機能" in prompt:
                                            keywords.append("機能")
                                        if "仕様" in prompt:
                                            keywords.append("仕様書")
                                        if "バグ" in prompt:
                                            keywords.append("バグ")
                                        if "急募" in prompt:
                                            keywords.append("急募")
                                        if "設計" in prompt:
                                            keywords.append("設計")
                                        
                                        if keywords:
                                            keyword_str = "、".join(keywords)
                                            yield f"  📊 キーワード抽出: {keyword_str}\n"
                                        else:
                                            yield f"  📊 キーワード抽出: {prompt}\n"
                                        
                                        if analysis_stage.duration:
                                            yield f"  ⏱️ 実行時間: {analysis_stage.duration_str}\n\n"
                                except:
                                    pass
                            
                            yield "✅ **質問解析完了**\n\n"
                            time.sleep(0.5)
                            
                            # === 段階2: ツール選択 ===
                            yield "🛠️ **最適なツールを選択中...**\n"
                            yield "  🔧 ConfluenceChainSearchツールを選択\n"
                            yield "✅ **ツール選択完了**\n\n"
                            time.sleep(0.5)
                            
                            # === 段階3: 検索実行（詳細ログ統合） ===
                            yield "🔍 **Confluence/Jira検索を実行中...**\n"
                            yield "  🚀 ConfluenceChainSearch初期化中...\n"
                            time.sleep(1)
                            
                            yield "  ⚡ チェーンプロンプト検索を開始...\n"
                            time.sleep(1)
                            
                            # promptを使った動的な質問分析表示
                            yield f"  🔍 質問分析: {prompt}\n\n"
                            time.sleep(1)
                            
                            # promptから主要キーワードを動的に抽出
                            main_keywords = []
                            if "ログイン" in prompt:
                                main_keywords.extend(["ログイン機能", "ログイン"])
                            elif "急募" in prompt:
                                main_keywords.extend(["急募機能", "急募"])
                            elif "バグ" in prompt:
                                main_keywords.extend(["バグ修正", "バグ"])
                            elif "設計" in prompt:
                                main_keywords.extend(["設計書", "設計"])
                            elif "仕様" in prompt:
                                main_keywords.extend(["仕様書", "仕様"])
                            else:
                                # 一般的なキーワード抽出
                                words = prompt.split()
                                main_keywords = [word for word in words if len(word) > 1][:2]
                            
                            if main_keywords:
                                keyword_display = ", ".join(main_keywords)
                                yield f"  🎯 キーワード最適化: [{keyword_display}]\n\n"
                            else:
                                yield f"  🎯 キーワード最適化: [{prompt}]\n\n"
                            time.sleep(1)
                            
                            yield "  📊 Confluence検索実行中...\n"
                            # 動的クエリ表示
                            if main_keywords:
                                primary_keyword = main_keywords[0]
                                yield f"    - クエリ: '{primary_keyword}' → 10件取得 (実行時間: ~0.6秒)\n"
                                if len(main_keywords) > 1:
                                    secondary_keyword = main_keywords[1]
                                    yield f"    - クエリ: '{secondary_keyword}' → 10件取得 (実行時間: ~0.5秒)\n\n"
                                else:
                                    yield f"    - クエリ: '{prompt[:10]}...' → 8件取得 (実行時間: ~0.5秒)\n\n"
                            else:
                                yield f"    - クエリ: '{prompt[:15]}...' → 8件取得 (実行時間: ~0.6秒)\n\n"
                            time.sleep(2)
                            
                            yield "  ✅ チェーンプロンプト検索完了 (約9秒)\n\n"
                            time.sleep(1)
                            
                            yield "  🎫 Jira検索実行中...\n"
                            # 動的Jira検索表示
                            if main_keywords:
                                primary_keyword = main_keywords[0]
                                yield f"    - フィルター付きJira検索: '{primary_keyword}' AND project = 'CTJ'\n"
                            else:
                                yield f"    - フィルター付きJira検索: '{prompt[:10]}...' AND project = 'CTJ'\n"
                            yield "    - 10件の結果を取得\n\n"
                            time.sleep(1)
                            
                            yield "  🏗️ Confluenceスペース構造分析中...\n"
                            yield "    - スペース: CLIENTTOMO (1129ページ)\n"
                            yield "    - 構造分析実行中...\n\n"
                            time.sleep(2)
                            
                            # ProcessTrackerから実際の実行時間を取得
                            if process_tracker:
                                try:
                                    search_stage = process_tracker.get_stage_info(ProcessStage.SEARCH_EXECUTION)
                                    if search_stage.duration:
                                        yield f"✅ **検索実行完了** (実行時間: {search_stage.duration_str})\n\n"
                                    else:
                                        yield "✅ **検索実行完了** (実行時間: ~120秒)\n\n"
                                except:
                                    yield "✅ **検索実行完了**\n\n"
                            else:
                                yield "✅ **検索実行完了**\n\n"
                            
                            time.sleep(0.5)
                            
                            # === 段階4: 結果統合 ===
                            yield "🔗 **結果統合中...**\n"
                            yield "  📚 Confluenceページ結果の統合\n"
                            yield "  🎫 Jiraチケット結果の統合\n\n"
                            yield "✅ **結果統合完了**\n\n"
                            time.sleep(0.5)
                            
                            # === 段階5: 回答生成 ===
                            yield "✍️ **回答生成中...**\n"
                            yield "  📝 検索結果を分析して回答を構成中...\n\n"
                            yield "✅ **回答生成完了**\n\n"
                            
                            # 総実行時間の表示
                            if process_tracker:
                                try:
                                    total_duration = process_tracker.get_total_duration()
                                    if total_duration:
                                        yield f"🎯 **総実行時間: {total_duration:.1f}秒**\n"
                                    else:
                                        yield "🎯 **処理完了**\n"
                                except:
                                    yield "🎯 **処理完了**\n"
                            else:
                                yield "🎯 **処理完了**\n"
                                
                            return "統合プロセス完了"
                        
                        # 統合プロセス表示を実行（簡略版）
                        if debug_mode:
                            st.info("📡 DEBUG: 統合プロセス表示でストリーミング開始")
                        
                        # 統合プロセス表示（リアルタイムコールバックとの重複を避けるため簡略化）
                        def simplified_process_display():
                            yield "🔄 **処理を開始しています...**\n\n"
                            yield "🤖 **エージェントが思考プロセスを開始します**\n\n"
                            yield "💭 **詳細な思考プロセスは下部のリアルタイム表示をご覧ください**\n\n"
                            return "準備完了"
                        
                        stream_result = st.write_stream(simplified_process_display)
                        
                        if debug_mode:
                            st.success(f"🎯 DEBUG: 統合プロセス表示完了: {stream_result}")
                    
                    # === リアルタイム思考プロセス表示エリア ===
                    st.markdown("### 🧠 **リアルタイム思考プロセス**")
                    thought_process_container = st.empty()
                    
                    # 実際のエージェント処理を実行（ストリーミング表示付き）
                    final_result = None
                    if current_agent:
                        if debug_mode:
                            st.info("🚀 DEBUG: リアルタイムストリーミング付きエージェント処理開始")
                        try:
                            # デバッグ: エージェントメソッド確認（常時表示）
                            streaming_exists = hasattr(current_agent, 'process_input_with_streaming')
                            callback_exists = hasattr(current_agent, 'create_streaming_callback')
                            
                            # メソッド情報を表示
                            with st.expander("🔍 デバッグ情報", expanded=False):
                                st.code(f"""
エージェント情報:
- クラス: {type(current_agent).__name__}
- ID: {id(current_agent)}
- process_input_with_streaming: {streaming_exists}
- create_streaming_callback: {callback_exists}

利用可能メソッド (process関連):
{[m for m in dir(current_agent) if 'process' in m.lower() and not m.startswith('_')]}

インポート情報:
- ProcessDetailCallback: {'ProcessDetailCallback' in str(type(current_agent.create_streaming_callback(None)) if callback_exists else 'N/A')}
                                """)
                            
                            # メソッド存在確認とフォールバック処理
                            if streaming_exists:
                                # ストリーミング表示付きエージェント処理の実行
                                with st.spinner("🔄 エージェントが思考中..."):
                                    actual_result = current_agent.process_input_with_streaming(
                                        enhanced_prompt,
                                        thought_process_container
                                    )
                            else:
                                # フォールバック: 従来のメソッドを使用
                                st.warning("🔄 ストリーミング機能が利用できません。従来の処理方式を使用します。")
                                with st.spinner("🔄 エージェントが処理中..."):
                                    actual_result = current_agent.process_user_input(enhanced_prompt)
                                    # 手動でコンテナ更新
                                    thought_process_container.markdown("📝 **処理完了** - 詳細な思考プロセスは利用できませんでした。")
                            
                            if debug_mode:
                                st.success(f"✅ **エージェント処理完了！** (結果: {len(str(actual_result)[:100])}文字)")
                            final_result = actual_result
                            
                        except Exception as e:
                            st.error(f"❌ **エージェント処理エラー**: {str(e)[:100]}...")
                            final_result = f"エラーが発生しました: {str(e)}"
                    else:
                        st.warning("⚠️ エージェントが初期化されていません")
                        final_result = "エージェントエラー"
                    
                    # === 2. 処理結果（思考プロセス直下）===
                    st.markdown("---")  # 区切り線
                    st.markdown("### 📋 最終回答")
                    
                    if debug_mode:
                        st.info("📊 DEBUG: 思考プロセス直下での結果表示")
                    
                    if final_result and final_result not in ["思考プロセス完了", "検索準備完了", "エージェントエラー"]:
                        # 実際の回答をストリーミング表示
                        def final_answer_generator():
                            answer_text = str(final_result)
                            for i in range(0, len(answer_text), 10):
                                yield answer_text[i:i+10]
                                import time
                                time.sleep(0.05)
                        
                        st.write_stream(final_answer_generator)
                    else:
                        st.markdown("回答の生成に失敗しました。")
                    
                    if debug_mode:
                        st.success("✅ DEBUG: 最終回答表示完了")
                        
                else:
                    # 従来の方式でエージェント実行（フォールバック）
                    placeholder = st.empty()
                    placeholder.text("回答を生成中...")
                    
                    response = st.session_state.agent.process_user_input(enhanced_prompt)
                    
                    placeholder.empty()
                    
                    # 応答を表示
                    st.markdown(response)
                    
                    # アシスタントメッセージを履歴に追加
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
            except Exception as e:
                error_msg = f"申し訳ありませんが、エラーが発生しました: {str(e)}"
                st.error(error_msg)
                logger.error(f"チャット処理エラー: {str(e)}\n{traceback.format_exc()}")
                
                # エラーメッセージも履歴に追加
                st.session_state.messages.append({"role": "assistant", "content": error_msg})


def _enhance_prompt_with_filters(original_prompt: str) -> str:
    """フィルター設定とデータソース選択を元にプロンプトを拡張（新仕様12+4パラメータ対応）"""
    
    # データソース選択を取得
    data_sources = st.session_state.get('data_sources', {'confluence': True, 'jira': True})
    
    # アクティブなフィルターを取得
    active_filters = {k: v for k, v in st.session_state.filters.items() if v}
    
    # 拡張情報を構築
    enhanced_info = []
    
    # データソース制限情報を追加
    available_sources = []
    if data_sources.get('confluence', False):
        available_sources.append("Confluence (仕様書・ドキュメント)")
    if data_sources.get('jira', False):
        available_sources.append("Jira (チケット・タスク)")
    
    if available_sources:
        enhanced_info.append(f"検索対象: {' と '.join(available_sources)} のみ")
    else:
        enhanced_info.append("⚠️ データソースが選択されていません")
    
    # フィルター情報を追加
    filter_info = []
    
    # Jiraフィルター（11パラメータ - プロジェクトはCTJ固定だが表示しない）
    if active_filters.get('jira_status'):
        filter_info.append(f"Jiraステータス: {active_filters['jira_status']}")
    if active_filters.get('jira_assignee'):
        filter_info.append(f"Jira担当者: {active_filters['jira_assignee']}")
    if active_filters.get('jira_issue_type'):
        filter_info.append(f"Jiraチケットタイプ: {active_filters['jira_issue_type']}")
    if active_filters.get('jira_priority'):
        filter_info.append(f"Jira優先度: {active_filters['jira_priority']}")
    if active_filters.get('jira_reporter'):
        filter_info.append(f"Jira報告者: {active_filters['jira_reporter']}")
    if active_filters.get('jira_custom_tantou'):
        filter_info.append(f"Jira担当(カスタム): {active_filters['jira_custom_tantou']}")
    if active_filters.get('jira_custom_eikyou'):
        filter_info.append(f"Jira影響業務: {active_filters['jira_custom_eikyou']}")
    if active_filters.get('jira_created_after'):
        filter_info.append(f"Jira作成日(以降): {active_filters['jira_created_after']}")
    if active_filters.get('jira_created_before'):
        filter_info.append(f"Jira作成日(以前): {active_filters['jira_created_before']}")
    if active_filters.get('jira_updated_after'):
        filter_info.append(f"Jira更新日(以降): {active_filters['jira_updated_after']}")
    if active_filters.get('jira_updated_before'):
        filter_info.append(f"Jira更新日(以前): {active_filters['jira_updated_before']}")
    
    # Confluenceフィルター（2パラメータ）
    if active_filters.get('confluence_created_after'):
        filter_info.append(f"Confluence作成日(以降): {active_filters['confluence_created_after']}")
    if active_filters.get('confluence_created_before'):
        filter_info.append(f"Confluence作成日(以前): {active_filters['confluence_created_before']}")
    
    # ★新規追加: ページ階層フィルター
    selected_folder_names = _get_selected_folder_names()
    if selected_folder_names:
        folder_list = "、".join(selected_folder_names[:5])  # 最大5個まで表示
        if len(selected_folder_names) > 5:
            folder_list += f"他{len(selected_folder_names) - 5}件"
        filter_info.append(f"対象フォルダ: {folder_list}")
        
        # プロンプトに詳細な指示を追加
        enhanced_info.append(f"Confluence検索時は以下のフォルダ内のページのみを優先的に検索してください: {', '.join(selected_folder_names)}")
    
    # フィルター情報を拡張情報に追加
    if filter_info:
        enhanced_info.extend(filter_info)
    
    # 拡張情報がある場合のみプロンプトを拡張
    if enhanced_info:
        enhanced_prompt = f"""
ユーザーの質問: {original_prompt}

検索・回答時に以下の条件を厳守してください:
{chr(10).join(['- ' + info for info in enhanced_info])}

上記の条件に該当する情報のみを検索し、適切に回答してください。
"""
        return enhanced_prompt
    
    return original_prompt


def render_footer():
    """フッター情報を描画"""
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ 会話履歴をクリア", use_container_width=True):
            st.session_state.messages = []
            if st.session_state.get('agent'):
                st.session_state.agent.clear_conversation_history()
            st.rerun()
    
    with col2:
        if st.button("🔄 エージェントを再初期化", use_container_width=True):
            del st.session_state.agent
            st.rerun()
    
    with col3:
        # 設定情報の表示
        with st.popover("⚙️ 設定情報"):
            st.caption(f"**ドメイン**: {settings.atlassian_domain}")
            st.caption(f"**デバッグ**: {settings.debug}")
            st.caption(f"**ログレベル**: {settings.log_level}")


def main():
    """メインアプリケーション"""
    
    # ページ設定
    st.set_page_config(
        page_title="仕様書作成支援ボット",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # サイドバー幅の調整（1.3倍に拡張）
    st.markdown("""
        <style>
        .css-1d391kg {
            width: 437px !important;
        }
        .css-1lcbmhc {
            width: 437px !important;
        }
        .css-17eq0hr {
            width: 437px !important;
        }
        section[data-testid="stSidebar"] {
            width: 437px !important;
        }
        section[data-testid="stSidebar"] > div:first-child {
            width: 437px !important;
        }
        .css-ng1t4o {
            width: 437px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # セッション状態の初期化
    initialize_session_state()
    
    # サイドバーの描画
    render_sidebar()
    
    # メインチャットの描画
    render_main_chat()
    
    # フッターの描画
    render_footer()


def _render_hierarchy_filter(hierarchy_data: List[Dict[str, Any]]):
    """
    階層構造のフィルターUIを描画する
    
    Args:
        hierarchy_data: 階層構造データ
    """
    if not hierarchy_data:
        st.caption("表示できる階層データがありません")
        return
    
    # 階層フィルターのヘルプテキスト
    with st.expander("💡 階層フィルターの使い方", expanded=False):
        st.write("""
        - フォルダをチェックすると、そのフォルダ以下のページが検索対象になります
        - 複数のフォルダを選択可能です
        - 何も選択しない場合は、全ページが検索対象になります
        """)
    
    # 選択状態を管理するためのコンテナ
    selected_folders = st.session_state.page_hierarchy_filters['selected_folders']
    
    # ルートレベルのフォルダを表示
    for root_folder in hierarchy_data:
        _render_folder_checkbox(root_folder, selected_folders, 0)
    
    # 選択されたフォルダの概要を表示
    if selected_folders:
        st.caption(f"選択中: {len(selected_folders)}個のフォルダ")
    else:
        st.caption("選択なし (全フォルダが対象)")


def _render_folder_checkbox(folder_data: Dict[str, Any], selected_folders: set, level: int):
    """
    階層構造の各フォルダにチェックボックスを描画する
    
    Args:
        folder_data: フォルダデータ
        selected_folders: 選択されたフォルダIDのセット
        level: 階層レベル（インデント用）
    """
    folder_name = folder_data.get('name', '名前なし')
    folder_id = folder_data.get('id', '')
    children = folder_data.get('children', [])
    
    # インデントとアイコン
    indent = "　" * level  # 全角スペースでインデント
    icon = "📁" if children else "📄"
    
    # フォルダ名を短縮（長すぎる場合）
    display_name = folder_name
    if len(folder_name) > 40:
        display_name = folder_name[:35] + "..."
    
    # チェックボックス（ユニークなkeyを生成）
    checkbox_key = f"folder_checkbox_{folder_id}_{level}"
    is_selected = folder_id in selected_folders
    
    # チェックボックスの状態変更を監視
    checkbox_checked = st.checkbox(
        f"{indent}{icon} {display_name}",
        value=is_selected,
        key=checkbox_key
    )
    
    # 選択状態を更新
    if checkbox_checked and folder_id not in selected_folders:
        selected_folders.add(folder_id)
    elif not checkbox_checked and folder_id in selected_folders:
        selected_folders.discard(folder_id)
    
    # 子フォルダを再帰的に表示（レベル3まで）
    if children and level < 2:
        for child in children:
            _render_folder_checkbox(child, selected_folders, level + 1)
    elif children and level >= 2:
        # 深い階層は件数のみ表示
        child_count = len(children)
        st.caption(f"{indent}　　└─ 子フォルダ {child_count}件...")


def create_clean_streaming_response(agent: SpecBotAgent, prompt: str, process_placeholder):
    """
    🎯 クリーンなストリーミング関数：結果表示のみ（アコーディオンは別途更新）
    
    Args:
        agent: SpecBotAgentインスタンス
        prompt: ユーザーの質問プロンプト
        process_placeholder: アコーディオン表示用プレースホルダー
        
    Yields:
        str: ストリーミング形式での結果表示のみ
    """
    import time
    import streamlit as st
    from ..utils.process_tracker import ProcessStage, StreamlitProcessDisplay
    
    # プロセス追跡システムの取得
    process_tracker = agent.get_process_tracker()
    
    def update_process_display():
        """アコーディオン内のプロセス表示を更新"""
        with process_placeholder.container():
            StreamlitProcessDisplay.render_process_tracker(process_tracker, process_placeholder)
    
    try:
        # 初期表示（結果エリアのみ）
        yield "## 📋 **回答結果**\n\n"
        
        # プロセス追跡開始（アコーディオンに表示）
        process_tracker.start_process()
        update_process_display()
        
        # 1. 質問解析段階
        agent._process_question_analysis(prompt)
        update_process_display()
        
        # 2. ツール選択段階
        agent._process_tool_selection(prompt)
        update_process_display()
        
        # 3. 検索実行段階
        process_tracker.start_stage(ProcessStage.SEARCH_EXECUTION, {
            "strategy": "LangChain Agent実行",
            "status": "検索開始..."
        })
        update_process_display()
        
        yield "🔍 **情報を検索しています...**\n\n"
        
        # エージェント実行
        execution_start = time.time()
        
        try:
            # LangChainエージェントの直接実行（タイムアウトなし）
            response = agent.process_user_input(prompt)
            execution_time = time.time() - execution_start
            
            yield f"✅ **検索完了! ({execution_time:.1f}秒)**\n\n"
            
            # プロセス完了更新
            process_tracker.complete_stage(ProcessStage.SEARCH_EXECUTION, {
                "execution_method": "直接実行",
                "success": True,
                "result_length": len(response),
                "actual_time": f"{execution_time:.1f}秒"
            })
            update_process_display()
            
            # 4. 結果統合段階
            agent._process_result_integration(response)
            update_process_display()
            
            # 5. 回答生成段階
            agent._process_answer_generation(response)
            update_process_display()
            
            # 最終回答をストリーミング表示
            yield "### **💡 回答内容**\n\n"
            
            # 回答を段階的に表示（タイプライター効果）
            sentences = response.split('。')
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    yield sentence.strip() + "。\n\n"
                    time.sleep(0.5)  # 文章ごとに待機
            
            yield "\n---\n"
            yield "✅ **回答生成が完了しました！**"
            
        except Exception as e:
            yield f"\n❌ **エラーが発生しました: {str(e)}**\n\n"
            
    except Exception as e:
        yield f"\n❌ **処理エラー: {str(e)}**\n"


def create_streaming_response_with_process_display(agent: SpecBotAgent, prompt: str, process_placeholder):
    """
    [DEPRECATED] 旧ストリーミング関数 - 後方互換性のため残存
    """
    # 新しいクリーン関数にリダイレクト
    for chunk in create_clean_streaming_response(agent, prompt, process_placeholder):
        yield chunk


def execute_agent_with_separated_display(agent: SpecBotAgent, prompt: str, process_placeholder, response_container):
    """
    [DEPRECATED] 旧関数 - 後方互換性のため残存
    """
    # 新しいジェネレータ関数をシミュレート
    result = ""
    for chunk in create_streaming_response_with_process_display(agent, prompt, process_placeholder):
        result += chunk
    return result


def execute_agent_with_accordion_and_streaming(agent: SpecBotAgent, prompt: str, process_placeholder, response_container):
    """
    アコーディオン内でプロセス表示 + 結果領域でストリーミング表示
    
    Args:
        agent: SpecBotAgentインスタンス
        prompt: ユーザーの質問プロンプト
        process_placeholder: アコーディオン表示用プレースホルダー
        response_container: 結果表示用コンテナ
        
    Yields:
        str: 結果部分のみのストリーミング表示
    """
    import time
    import streamlit as st
    from ..utils.process_tracker import ProcessStage, StreamlitProcessDisplay
    
    # プロセス追跡システムの取得
    process_tracker = agent.get_process_tracker()
    
    def update_process_display():
        """アコーディオン内のプロセス表示を更新"""
        with process_placeholder.container():
            StreamlitProcessDisplay.render_process_tracker(process_tracker, process_placeholder)
    
    try:
        # プロセス追跡開始
        process_tracker.start_process()
        update_process_display()
        
        # 結果表示の開始
        yield "## 🤖 回答生成中...\n\n"
        time.sleep(0.5)
        
        # 1. 質問解析段階
        yield "📝 **質問を解析中...**\n"
        agent._process_question_analysis(prompt)
        update_process_display()
        time.sleep(0.3)
        
        # 2. ツール選択段階
        yield "🛠️ **最適なツールを選択中...**\n"
        agent._process_tool_selection(prompt)
        update_process_display()
        time.sleep(0.3)
        
        # 3. 検索実行段階
        yield "🔍 **Confluence/Jira検索を実行中...**\n"
        process_tracker.start_stage(ProcessStage.SEARCH_EXECUTION, {
            "strategy": "LangChain Agent実行",
            "status": "検索開始..."
        })
        update_process_display()
        
        yield "⚡ **検索処理を実行中です... (30-60秒程度)**\n\n"
        
        # エージェント実行
        execution_start = time.time()
        
        try:
            response = agent.agent_executor.invoke({"input": prompt})
            execution_time = time.time() - execution_start
            
            # レスポンスからoutputを抽出
            if isinstance(response, dict) and 'output' in response:
                result = response['output']
            else:
                result = str(response)
            
            yield f"✅ **検索完了! ({execution_time:.1f}秒)**\n\n"
            
            # プロセス完了更新
            process_tracker.complete_stage(ProcessStage.SEARCH_EXECUTION, {
                "execution_method": "LangChain Agent",
                "success": True,
                "result_length": len(result),
                "actual_time": f"{execution_time:.1f}秒"
            })
            update_process_display()
            
            # 4. 結果統合段階
            yield "🔗 **結果を統合中...**\n"
            agent._process_result_integration(result)
            update_process_display()
            time.sleep(0.3)
            
            # 5. 回答生成段階
            yield "✍️ **回答を生成中...**\n"
            agent._process_answer_generation(result)
            update_process_display()
            time.sleep(0.3)
            
            # ここから結果のストリーミング表示
            yield "\n---\n\n"
            yield "## 📋 **回答結果**\n\n"
            
            # 回答を段階的に表示（タイプライター効果）
            words = result.split()
            current_line = ""
            for i, word in enumerate(words):
                current_line += word + " "
                if i % 15 == 14:  # 15語ごとに改行
                    yield current_line + "\n"
                    current_line = ""
                    time.sleep(0.1)
                elif i % 5 == 4:  # 5語ごとに少し待機
                    time.sleep(0.05)
            
            # 残りの文字を出力
            if current_line.strip():
                yield current_line + "\n"
                    
            yield "\n\n---\n"
            yield "✅ **処理が完了しました！**"
            
        except Exception as e:
            yield f"❌ **検索エラー: {str(e)}**\n\n"
            
    except Exception as e:
        yield f"\n❌ **処理エラー: {str(e)}**\n"


def stream_agent_response_with_process_tracking(agent: SpecBotAgent, prompt: str, process_placeholder):
    """
    [DEPRECATED] 旧ストリーミング関数（後方互換性のため残存）
    """
    # 新しい関数にリダイレクト
    for chunk in execute_agent_with_accordion_and_streaming(agent, prompt, process_placeholder, None):
        yield chunk


def _execute_agent_with_realtime_display(agent: SpecBotAgent, prompt: str, process_placeholder) -> str:
    """
    リアルタイムプロセス表示付きでエージェントを実行
    
    Args:
        agent: SpecBotAgentインスタンス
        prompt: ユーザーの質問プロンプト
        process_placeholder: Streamlitプロセス表示用プレースホルダー
        
    Returns:
        str: エージェントの回答
    """
    # プロセス追跡システムの取得
    process_tracker = agent.get_process_tracker()
    
    try:
        # リアルタイム更新付きでエージェント実行
        response = _process_user_input_with_realtime_display(agent, prompt, process_placeholder)
        
        # 最終プロセス表示
        with process_placeholder.container():
            st.success("✅ 回答生成が完了しました")
            StreamlitProcessDisplay.render_process_tracker(process_tracker, process_placeholder)
        
        return response
        
    except Exception as e:
        # エラー時のプロセス表示
        with process_placeholder.container():
            st.error(f"❌ エラーが発生しました: {str(e)}")
            StreamlitProcessDisplay.render_process_tracker(process_tracker, process_placeholder)
        raise


def _process_user_input_with_realtime_display(agent: SpecBotAgent, prompt: str, process_placeholder) -> str:
    """
    リアルタイムプロセス表示を組み込んだエージェント実行
    参考: Streamlitストリーミング機能を使用
    """
    import time
    
    # オリジナルのprocess_user_inputメソッドを拡張
    process_tracker = agent.get_process_tracker()
    start_time = time.time()
    
    try:
        logger.info(f"ユーザー入力を処理開始: '{prompt}'")
        
        if not prompt.strip():
            logger.warning("空の質問を受信")
            return "申し訳ありませんが、質問内容が空です。何についてお聞きになりたいですか？"
        
        # プロセス追跡開始
        process_tracker.start_process()
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        # 1. 質問解析段階
        agent._process_question_analysis(prompt)
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        # 2. ツール選択段階  
        agent._process_tool_selection(prompt)
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        # 3. 検索実行段階
        process_tracker.start_stage(ProcessStage.SEARCH_EXECUTION, {
            "strategy": "LangChain Agent実行",
            "status": "開始しました..."
        })
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        # エージェントに質問を投げる（進行状況付き）
        logger.info("エージェント実行開始")
        
        # 実行中の進行状況を更新
        process_tracker.update_stage_details(ProcessStage.SEARCH_EXECUTION, {
            "status": "LangChain Agent実行中...",
            "progress": "Confluence/Jira検索実行中"
        })
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        # 長時間処理の疑似リアルタイム更新付きでエージェント実行
        response = _execute_agent_with_periodic_updates(agent, prompt, process_tracker, process_placeholder)
        
        # レスポンスからoutputを抽出
        if isinstance(response, dict) and 'output' in response:
            result = response['output']
        else:
            result = str(response)
        
        process_tracker.complete_stage(ProcessStage.SEARCH_EXECUTION, {
            "execution_method": "LangChain Agent",
            "success": True,
            "result_length": len(result)
        })
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        # 4. 結果統合段階
        agent._process_result_integration(result)
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        # 5. 回答生成段階
        agent._process_answer_generation(result)
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        # プロセス追跡完了
        process_tracker.complete_process()
        
        execution_time = time.time() - start_time
        logger.info(f"ユーザー入力処理完了: 実行時間 {execution_time:.2f}秒 | 応答文字数: {len(result)}文字")
        return result
        
    except Exception as e:
        # エラー時のプロセス追跡
        if process_tracker.current_stage:
            process_tracker.error_stage(process_tracker.current_stage, str(e))
        process_tracker.complete_process()
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        execution_time = time.time() - start_time
        logger.error(f"ユーザー入力処理エラー: {str(e)} | 実行時間: {execution_time:.2f}秒")
        raise


def _execute_agent_with_periodic_updates(agent, prompt, process_tracker, process_placeholder):
    """
    定期的な進行状況更新付きでエージェントを実行
    """
    import time
    
    # 実行開始時刻を記録
    start_time = time.time()
    
    try:
        # 初期更新
        process_tracker.update_stage_details(ProcessStage.SEARCH_EXECUTION, {
            "status": "検索開始",
            "progress": "Confluence/Jira API接続中",
            "estimated_time": "30-60秒程度"
        })
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        # 実行直前の更新
        process_tracker.update_stage_details(ProcessStage.SEARCH_EXECUTION, {
            "status": "実行中...",
            "progress": "LangChain Agent & Confluence/Jira API実行中",
            "message": "検索処理を実行しています..."
        })
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        # エージェント実行
        response = agent.agent_executor.invoke({"input": prompt})
        
        # 実行完了時の更新
        execution_time = time.time() - start_time
        process_tracker.update_stage_details(ProcessStage.SEARCH_EXECUTION, {
            "status": "検索完了",
            "progress": "結果取得完了",
            "actual_time": f"{execution_time:.1f}秒"
        })
        _realtime_update_process_display(process_placeholder, process_tracker)
        
        return response
        
    except Exception as e:
        # エラー時の更新
        execution_time = time.time() - start_time
        process_tracker.update_stage_details(ProcessStage.SEARCH_EXECUTION, {
            "status": "エラー発生",
            "error": str(e),
            "elapsed_time": f"{execution_time:.1f}秒"
        })
        _realtime_update_process_display(process_placeholder, process_tracker)
        raise


def _realtime_update_process_display(process_placeholder, process_tracker):
    """リアルタイムプロセス表示を更新"""
    try:
        # 参考記事のようにmessage_placeholder.markdown()の手法を使用
        StreamlitProcessDisplay.render_process_tracker(process_tracker, process_placeholder)
    except Exception as e:
        logger.warning(f"プロセス表示更新エラー: {e}")


def _get_selected_folder_names() -> List[str]:
    """
    選択されたフォルダの名前リストを取得する（親フォルダレベルのみ）
    
    Returns:
        List[str]: 親フォルダレベルの選択されたフォルダ名のリスト
    """
    # HierarchyFilterUIのメソッドを使用して親フォルダレベルの表示名を取得
    hierarchy_ui = HierarchyFilterUI()
    return hierarchy_ui.get_selected_folder_display_names()


if __name__ == "__main__":
    main() 