"""
Confluence階層フィルターUI

JSON階層フィルター機能仕様書 v1.0に基づく階層チェックボックスUI実装
- インデント付き階層構造表示
- 親選択で配下全選択機能
- 削除ページの視覚的表示
- 0.1秒以下の即座の応答性能
"""

import streamlit as st
from typing import Dict, List, Optional, Set, Tuple
import logging
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent
sys.path.insert(0, str(project_root))

from ..utils.confluence_hierarchy_manager import ConfluenceHierarchyManager


class HierarchyFilterUI:
    """
    階層フィルターUIコンポーネント
    
    主な機能:
    - 階層チェックボックス表示
    - 親子連動選択
    - 削除ページフィルタリング
    - 選択状態管理
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.manager = ConfluenceHierarchyManager()
        
        # セッション状態の初期化
        if 'hierarchy_selected' not in st.session_state:
            st.session_state.hierarchy_selected = set()
        if 'include_deleted_pages' not in st.session_state:
            st.session_state.include_deleted_pages = False
        if 'hierarchy_data' not in st.session_state:
            st.session_state.hierarchy_data = None
        
    def load_hierarchy_data(self) -> Optional[Dict]:
        """階層データを読み込み（キャッシュ対応）"""
        try:
            if st.session_state.hierarchy_data is None:
                with st.spinner("📁 ページ階層データを読み込み中..."):
                    data = self.manager.load_hierarchy_data(
                        include_deleted=st.session_state.include_deleted_pages
                    )
                    if data:
                        st.session_state.hierarchy_data = data
                        self.logger.info("階層データ読み込み完了")
                        
                        # 初回読み込み時に全フォルダを選択状態にする
                        if not st.session_state.hierarchy_selected:
                            all_folder_ids = self._get_all_item_ids(data.get('folders', []))
                            st.session_state.hierarchy_selected = all_folder_ids
                            self.logger.info(f"デフォルト全選択: {len(all_folder_ids)}個のフォルダを選択")
                    else:
                        st.error("階層データの読み込みに失敗しました")
                        return None
            
            return st.session_state.hierarchy_data
            
        except Exception as e:
            self.logger.error(f"階層データ読み込みエラー: {e}")
            st.error(f"データ読み込みエラー: {str(e)}")
            return None
    
    def refresh_hierarchy_data(self, include_deleted: bool = None):
        """階層データを強制更新"""
        if include_deleted is not None:
            st.session_state.include_deleted_pages = include_deleted
        
        # キャッシュクリア
        st.session_state.hierarchy_data = None
        
        # 選択状態もクリアして、再読み込み時に全選択状態にする
        st.session_state.hierarchy_selected = set()
        
        # 再読み込み
        self.load_hierarchy_data()
    
    def get_item_id(self, item: Dict, parent_path: str = "") -> str:
        """階層アイテムの一意IDを生成"""
        name = item.get('name', 'unknown')
        path = f"{parent_path}/{name}" if parent_path else name
        return path.replace(" ", "_").replace("/", "__")
    
    def get_all_child_ids(self, item: Dict, parent_path: str = "") -> Set[str]:
        """配下すべての子フォルダIDを取得（ページは除外）"""
        child_ids = set()
        
        # フォルダのみ処理
        if item.get('type') == 'folder':
            current_id = self.get_item_id(item, parent_path)
            child_ids.add(current_id)
            
            if 'children' in item and item['children']:
                for child in item['children']:
                    # 子フォルダのみ再帰処理
                    if child.get('type') == 'folder':
                        child_ids.update(self.get_all_child_ids(child, parent_path + "/" + item.get('name', '')))
        
        return child_ids
    
    def render_hierarchy_item(self, item: Dict, level: int = 0, parent_path: str = "", use_temp_state: bool = False) -> bool:
        """
        階層フォルダを折りたたみ可能な構造でレンダリング（ページは除外）
        
        Args:
            item: 階層アイテム
            level: インデントレベル
            parent_path: 親パス
            
        Returns:
            bool: 常にFalse（再描画を防ぐため）
        """
        # ページは処理をスキップ
        if item.get('type') != 'folder':
            return False
            
        item_id = self.get_item_id(item, parent_path)
        name = item.get('name', 'Unknown')
        children = item.get('children', [])
        
        # フォルダアイコン
        icon = "📁"
        
        # ページ数表示は削除
        
        # 現在の選択状態（一時的な状態を使用する場合とそうでない場合）
        if use_temp_state:
            is_selected = item_id in st.session_state.temp_hierarchy_selected
        else:
            is_selected = item_id in st.session_state.hierarchy_selected
        
        # フォルダは展開可能な構造で表示
        if children:
            # 展開状態管理用のキー
            expander_key = f"hierarchy_expander_{item_id}"
            
            # expanderタイトルでチェックボックスを含める
            checkbox_key = f"hierarchy_checkbox_{item_id}_{level}"
            
            # チェックボックス状態の管理
            col_check, col_expand = st.columns([0.1, 0.9])
            
            with col_check:
                # nameが空の場合のフォールバック
                label_text = f"選択 {name}" if name else f"選択 フォルダ_{item_id}"
                new_selected = st.checkbox(
                    label_text,  # 安全なラベル
                    value=is_selected,
                    key=checkbox_key,
                    help=f"フォルダ全体を選択: {name or 'フォルダ'}",
                    label_visibility="hidden"  # ラベルを非表示
                )
                
                # 選択状態の変更処理（再描画は行わない）
                if new_selected != is_selected:
                    if new_selected:
                        # 選択: 自分と全配下フォルダを選択
                        child_ids = self.get_all_child_ids(item, parent_path)
                        if use_temp_state:
                            st.session_state.temp_hierarchy_selected.update(child_ids)
                        else:
                            st.session_state.hierarchy_selected.update(child_ids)
                    else:
                        # 解除: 自分と全配下フォルダを解除
                        child_ids = self.get_all_child_ids(item, parent_path)
                        if use_temp_state:
                            st.session_state.temp_hierarchy_selected.difference_update(child_ids)
                        else:
                            st.session_state.hierarchy_selected.difference_update(child_ids)
            
            with col_expand:
                # 展開可能なフォルダ表示（コンパクト表示）
                expander = st.expander(f"{icon} {name}", expanded=False)
                with expander:
                    # 子フォルダの再帰処理（ページはスキップ）
                    child_container = st.container()
                    with child_container:
                        for child in children:
                            # フォルダのみ処理
                            if child.get('type') == 'folder':
                                child_path = f"{parent_path}/{name}" if parent_path else name
                                self.render_hierarchy_item(child, level + 1, child_path, use_temp_state)
        else:
            # 子要素がないフォルダも表示
            # インデント生成
            indent = "　" * max(0, level) if level > 0 else ""
            
            # チェックボックス表示名
            display_name = f"{indent}{icon} {name}"
            
            # チェックボックス表示
            col_check, col_name = st.columns([0.1, 0.9])
            
            with col_check:
                checkbox_key = f"hierarchy_checkbox_{item_id}_{level}"
                # nameが空の場合のフォールバック
                label_text = f"選択 {name}" if name else f"選択 アイテム_{item_id}"
                new_selected = st.checkbox(
                    label_text,  # 安全なラベル
                    value=is_selected,
                    key=checkbox_key,
                    help=f"フォルダを選択: {name or 'アイテム'}",
                    label_visibility="hidden"  # ラベルを非表示
                )
            
            with col_name:
                st.markdown(f'<div class="hierarchy-folder-text">{display_name}</div>', unsafe_allow_html=True)
            
            # 選択状態の変更処理（再描画は行わない）
            if new_selected != is_selected:
                if new_selected:
                    # フォルダの選択
                    if use_temp_state:
                        st.session_state.temp_hierarchy_selected.add(item_id)
                    else:
                        st.session_state.hierarchy_selected.add(item_id)
                else:
                    # フォルダの解除
                    if use_temp_state:
                        st.session_state.temp_hierarchy_selected.discard(item_id)
                    else:
                        st.session_state.hierarchy_selected.discard(item_id)
        
        return False  # 常にFalseを返して再描画を防ぐ
    
    def _count_pages_in_folder(self, folder: Dict) -> int:
        """フォルダ内のページ数をカウント"""
        count = 0
        for child in folder.get('children', []):
            if child.get('type') == 'page':
                count += 1
            elif child.get('type') == 'folder':
                count += self._count_pages_in_folder(child)
        return count
    
    def render_deleted_pages_filter(self) -> bool:
        """削除ページフィルターUIをレンダリング"""
        st.subheader("🗑️ フィルターオプション")
        
        current_include_deleted = st.session_state.include_deleted_pages
        
        new_include_deleted = st.checkbox(
            "削除ページを含む",
            value=current_include_deleted,
            help="【%%削除%%】【%%廃止%%】マークのページも表示します"
        )
        
        # 統計情報表示
        stats = self.manager.get_hierarchy_stats()
        if stats and not stats.get('error'):
            deleted_count = stats.get('deleted_pages_count', 0)
            if deleted_count > 0:
                st.caption(f"📊 除外: {deleted_count}件の削除・廃止ページ")
        
        # 設定変更時の処理
        if new_include_deleted != current_include_deleted:
            self.refresh_hierarchy_data(new_include_deleted)
            st.success("🔄 削除ページ表示設定を変更しました")
        
        return new_include_deleted != current_include_deleted
    
    def render_hierarchy_filter(self) -> Tuple[Set[str], bool]:
        """
        階層フィルターUIをレンダリング
        
        Returns:
            Tuple[Set[str], bool]: (選択されたアイテムID集合, 設定変更フラグ)
        """
        try:
            st.subheader("📁 フォルダフィルター")
            
            # キャッシュ無効化のためのタイムスタンプ
            import time
            cache_buster = int(time.time())
            
            # フォルダ選択部分のみの縦幅縮小CSS（スコープ限定）
            st.markdown("""
                <style>
                /* フォルダ選択エリアのみに適用するスタイル */
                .confluence-folder-selector {
                    max-height: 350px !important;
                    overflow-y: auto !important;
                    padding: 0.2rem !important;
                    margin: 0 !important;
                    border: 1px solid #e0e0e0 !important;
                    border-radius: 0.25rem !important;
                }
                
                /* フォルダ選択エリア内のExpanderのみスタイル適用 */
                .confluence-folder-selector .stExpander,
                .confluence-folder-selector .st-emotion-cache-8atqhb,
                .confluence-folder-selector .eah1tn10 {
                    margin: 0 !important;
                    padding: 0 !important;
                    border: none !important;
                    box-shadow: none !important;
                }
                
                .confluence-folder-selector .st-emotion-cache-1h9usn1,
                .confluence-folder-selector .eah1tn11 {
                    margin: 0 !important;
                    padding: 0 !important;
                }
                
                .confluence-folder-selector .st-emotion-cache-4rp1ik,
                .confluence-folder-selector .eah1tn13 {
                    padding: 0.1rem 0.5rem !important;
                    margin: 0 !important;
                    min-height: 1.2rem !important;
                    line-height: 1.1 !important;
                }
                
                .confluence-folder-selector .st-emotion-cache-1clstc5,
                .confluence-folder-selector .eah1tn14 {
                    padding: 0.1rem !important;
                    margin: 0 !important;
                }
                
                /* フォルダ選択エリア内のチェックボックスのみスタイル適用 */
                .confluence-folder-selector .stCheckbox,
                .confluence-folder-selector .st-emotion-cache-mo6sqg,
                .confluence-folder-selector .eg2gxky0 {
                    margin: 0 !important;
                    padding: 0 !important;
                    min-height: 1rem !important;
                }
                
                /* フォルダ選択エリア内のチェックボックスラベルを完全に非表示 */
                .confluence-folder-selector .st-emotion-cache-1bps9ns,
                .confluence-folder-selector .eg2gxky1 {
                    display: none !important;
                    visibility: hidden !important;
                    height: 0 !important;
                    margin: 0 !important;
                    padding: 0 !important;
                }
                
                /* フォルダ選択エリア内のツールチップアイコンも非表示 */
                .confluence-folder-selector .stTooltipIcon,
                .confluence-folder-selector .st-emotion-cache-oj1fi,
                .confluence-folder-selector .e1pw9gww0 {
                    display: none !important;
                }
                
                /* フォルダ選択エリア内のカラムの余白を完全削除 */
                .confluence-folder-selector .stColumn,
                .confluence-folder-selector .st-emotion-cache-81xr8g,
                .confluence-folder-selector .st-emotion-cache-c7c9cm,
                .confluence-folder-selector .eertqu01 {
                    padding: 0 !important;
                    margin: 0 !important;
                    gap: 0 !important;
                }
                
                /* フォルダ選択エリア内の垂直ブロックの余白削除 */
                .confluence-folder-selector .stVerticalBlock,
                .confluence-folder-selector .st-emotion-cache-gsx7k2,
                .confluence-folder-selector .eertqu03 {
                    margin: 0 !important;
                    padding: 0 !important;
                    gap: 0 !important;
                }
                
                /* フォルダ選択エリア内の水平ブロックの余白削除 */
                .confluence-folder-selector .stHorizontalBlock,
                .confluence-folder-selector .st-emotion-cache-ajtf3x,
                .confluence-folder-selector .eertqu03 {
                    margin: 0 !important;
                    padding: 0 !important;
                    gap: 0.1rem !important;
                }
                
                /* フォルダ選択エリア内の要素コンテナの余白削除 */
                .confluence-folder-selector .stElementContainer,
                .confluence-folder-selector .element-container,
                .confluence-folder-selector .st-emotion-cache-9ko04w,
                .confluence-folder-selector .eertqu00 {
                    margin: 0 !important;
                    padding: 0 !important;
                    height: auto !important;
                    min-height: 1rem !important;
                }
                
                /* フォルダ選択エリア内のレイアウトラッパーの余白削除 */
                .confluence-folder-selector .st-emotion-cache-hjhvlk,
                .confluence-folder-selector .eertqu04 {
                    margin: 0 !important;
                    padding: 0 !important;
                }
                
                /* フォルダ選択エリア内のボーダーラッパーの余白削除 */
                .confluence-folder-selector .st-emotion-cache-13o7eu2,
                .confluence-folder-selector .eertqu02 {
                    margin: 0 !important;
                    padding: 0 !important;
                }
                
                /* フォルダ選択エリア内のMarkdownコンテナの余白削除 */
                .confluence-folder-selector .st-emotion-cache-1oa0vvv,
                .confluence-folder-selector .st-emotion-cache-98rilw,
                .confluence-folder-selector .e1g8wfdw0 {
                    margin: 0 !important;
                    padding: 0 !important;
                    line-height: 1.1 !important;
                }
                
                /* フォルダ選択エリア内のMarkdownテキストの余白削除 */
                .confluence-folder-selector .st-emotion-cache-1oa0vvv p,
                .confluence-folder-selector .st-emotion-cache-98rilw p {
                    margin: 0 !important;
                    padding: 0 !important;
                    font-size: 0.8rem !important;
                    line-height: 1.1 !important;
                }
                
                /* フォルダテキストのコンパクト化 */
                .confluence-folder-selector .hierarchy-folder-text {
                    font-size: 0.8rem !important;
                    line-height: 1.1 !important;
                    margin: 0 !important;
                    padding: 0.05rem 0 !important;
                }
                </style>
                <script>
                // フォルダ選択エリア内のチェックボックスラベルのみを削除
                setTimeout(function() {
                    const folderSelector = document.querySelector('.confluence-folder-selector');
                    if (folderSelector) {
                        // フォルダ選択エリア内のチェックボックスのみ処理
                        const checkboxes = folderSelector.querySelectorAll('input[type="checkbox"]');
                        checkboxes.forEach(function(checkbox) {
                            if (checkbox.getAttribute('aria-label') && 
                                (checkbox.getAttribute('aria-label').startsWith('select_') ||
                                 checkbox.getAttribute('aria-label').includes('select_leaf_'))) {
                                checkbox.setAttribute('aria-label', '');
                            }
                        });
                        
                        // フォルダ選択エリア内のラベルテキストを非表示
                        const labels = folderSelector.querySelectorAll('.eg2gxky1, .st-emotion-cache-1bps9ns');
                        labels.forEach(function(label) {
                            label.style.display = 'none';
                            label.style.visibility = 'hidden';
                            label.style.height = '0';
                        });
                    }
                }, 100);
                </script>
            """, unsafe_allow_html=True)
            
            # 削除ページフィルター
            settings_changed = self.render_deleted_pages_filter()
            
            # 階層データ読み込み
            data = self.load_hierarchy_data()
            if not data:
                st.warning("階層データが利用できません")
                return set(), settings_changed
            
            # 統計情報表示
            st.caption(f"📊 総ページ数: {data.get('total_pages', 0)}件")
            
            # 階層ツリー表示
            st.markdown("**フォルダ選択:**")
            
            folders = data.get('folders', [])
            if not folders:
                st.info("表示可能なフォルダがありません")
                return set(), settings_changed
            
            # 階層表示エリア（フォルダ選択専用のスタイル適用）
            st.markdown('<div class="confluence-folder-selector">', unsafe_allow_html=True)
            
            # フォームを使用してバッチ処理にする
            with st.form(key="folder_selection_form", clear_on_submit=False):
                # 一時的な選択状態を管理
                if 'temp_hierarchy_selected' not in st.session_state:
                    st.session_state.temp_hierarchy_selected = st.session_state.hierarchy_selected.copy()
                
                # フォーム内操作ボタン
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("☑️ 全選択", help="すべてのフォルダを選択"):
                        all_ids = self._get_all_item_ids(data.get('folders', []))
                        st.session_state.temp_hierarchy_selected = all_ids
                        st.success("✅ 一時的にすべてのフォルダを選択しました")
                
                with col2:
                    if st.form_submit_button("☐ 全解除", help="すべての選択を解除"):
                        st.session_state.temp_hierarchy_selected = set()
                        st.success("☐ 一時的にすべての選択を解除しました")
                
                hierarchy_container = st.container()
                
                with hierarchy_container:
                    for folder in folders:
                        # フォルダのみ処理
                        if folder.get('type') == 'folder':
                            self.render_hierarchy_item(folder, 0, use_temp_state=True)
                
                # フォーム送信ボタン
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    apply_changes = st.form_submit_button("✅ 選択を適用", use_container_width=True)
                with col2:
                    cancel_changes = st.form_submit_button("❌ キャンセル", use_container_width=True)
                
                # フォーム送信時の処理
                if apply_changes:
                    st.session_state.hierarchy_selected = st.session_state.temp_hierarchy_selected.copy()
                    st.success("✅ フォルダ選択を適用しました")
                    st.rerun()
                elif cancel_changes:
                    st.session_state.temp_hierarchy_selected = st.session_state.hierarchy_selected.copy()
                    st.info("❌ 変更をキャンセルしました")
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)  # confluence-folder-selector終了
            
            # 選択状況サマリー（一時的な状態を表示）
            current_selected = getattr(st.session_state, 'temp_hierarchy_selected', st.session_state.hierarchy_selected)
            applied_selected = st.session_state.hierarchy_selected
            
            if current_selected:
                if current_selected == applied_selected:
                    st.success(f"✅ {len(current_selected)}個のフォルダが選択されています（適用済み）")
                else:
                    st.warning(f"⚠️ {len(current_selected)}個のフォルダが選択されています（未適用 - 「選択を適用」をクリックしてください）")
            else:
                st.info("📝 フォルダを選択してください")
            
            # 適用済みの選択状態を返す
            return st.session_state.hierarchy_selected, settings_changed
            
        except Exception as e:
            self.logger.error(f"階層フィルターUI描画エラー: {e}")
            st.error(f"UI描画エラー: {str(e)}")
            return set(), False
    
    def _get_all_item_ids(self, folders: List[Dict], parent_path: str = "") -> Set[str]:
        """全フォルダのIDを取得"""
        all_ids = set()
        for folder in folders:
            # フォルダのみ処理
            if folder.get('type') == 'folder':
                all_ids.update(self.get_all_child_ids(folder, parent_path))
        return all_ids
    
    def get_selected_folder_filters(self) -> List[str]:
        """選択されたフォルダのフィルター条件を生成（親フォルダレベルのみ）"""
        selected_items = st.session_state.hierarchy_selected
        
        if not selected_items:
            return []
        
        # 親フォルダレベルのフィルターを生成
        parent_folders = set()
        for item_id in selected_items:
            # item_idからフォルダ名を復元
            folder_path = item_id.replace("__", "/").replace("_", " ")
            
            # パスを分割して最上位レベルのフォルダを取得
            path_parts = folder_path.split("/")
            if len(path_parts) >= 2:
                # "client-tomonokai-juku Home/■要件定義" のような第2階層まで
                parent_folder = "/".join(path_parts[:2])
                parent_folders.add(parent_folder)
            elif len(path_parts) == 1:
                # 単一フォルダの場合
                parent_folders.add(path_parts[0])
        
        # 親フォルダベースのフィルター条件を生成
        filters = []
        for parent_folder in sorted(parent_folders):
            filters.append(f'ancestor ~ "{parent_folder}"')
        
        return filters
    
    def get_selected_folder_display_names(self) -> List[str]:
        """選択されたフォルダの表示用名前を取得（親フォルダレベルのみ）"""
        selected_items = st.session_state.hierarchy_selected
        
        if not selected_items:
            return []
        
        # 親フォルダレベルの表示名を生成
        parent_folders = set()
        for item_id in selected_items:
            # item_idからフォルダ名を復元
            folder_path = item_id.replace("__", "/").replace("_", " ")
            
            # パスを分割して第2階層までの表示名を取得
            path_parts = folder_path.split("/")
            if len(path_parts) >= 2:
                # "■要件定義" のような第2階層の名前のみ
                display_name = path_parts[1]
                parent_folders.add(display_name)
            elif len(path_parts) == 1:
                # 単一フォルダの場合
                parent_folders.add(path_parts[0])
        
        return sorted(list(parent_folders)) 