"""
LLMプロセス可視化機能 - プロセス管理システム

チャット回答生成中のLLMエージェントの思考プロセスを
リアルタイムで追跡・管理するためのクラス群
"""

import time
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
import streamlit as st
from ..utils.log_config import get_logger

logger = get_logger(__name__)


class ProcessStatus(Enum):
    """プロセス段階の状態"""
    PENDING = "⏳ 待機中"
    RUNNING = "🔄 実行中..."
    COMPLETED = "✅ 完了"
    ERROR = "❌ エラー"


class ProcessStage(Enum):
    """LLMプロセスの5段階"""
    QUESTION_ANALYSIS = "question_analysis"
    TOOL_SELECTION = "tool_selection"
    SEARCH_EXECUTION = "search_execution"
    RESULT_INTEGRATION = "result_integration"
    ANSWER_GENERATION = "answer_generation"


@dataclass
class ProcessStageInfo:
    """各プロセス段階の詳細情報"""
    stage: ProcessStage
    title: str
    icon: str
    status: ProcessStatus = ProcessStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """実行時間を計算"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def duration_str(self) -> str:
        """実行時間を文字列で取得"""
        if self.duration:
            return f"{self.duration:.2f}秒"
        return "未計測"


class ProcessTracker:
    """
    LLMプロセス追跡・管理クラス
    
    各段階の進行状況を管理し、Streamlit UIでの表示用データを提供
    """
    
    def __init__(self):
        """プロセス追跡システムの初期化"""
        self.stages = self._initialize_stages()
        self.current_stage: Optional[ProcessStage] = None
        self.total_start_time: Optional[float] = None
        self.total_end_time: Optional[float] = None
        self.is_active = False
        self.real_time_details: List[Dict[str, Any]] = []  # リアルタイム詳細ログ
        self.current_activity: str = ""  # 現在のアクティビティ
        
        logger.info("ProcessTracker初期化完了")
    
    def _initialize_stages(self) -> Dict[ProcessStage, ProcessStageInfo]:
        """プロセス段階の初期化"""
        return {
            ProcessStage.QUESTION_ANALYSIS: ProcessStageInfo(
                stage=ProcessStage.QUESTION_ANALYSIS,
                title="質問解析",
                icon="🔍"
            ),
            ProcessStage.TOOL_SELECTION: ProcessStageInfo(
                stage=ProcessStage.TOOL_SELECTION,
                title="ツール選択",
                icon="🛠️"
            ),
            ProcessStage.SEARCH_EXECUTION: ProcessStageInfo(
                stage=ProcessStage.SEARCH_EXECUTION,
                title="検索実行",
                icon="📊"
            ),
            ProcessStage.RESULT_INTEGRATION: ProcessStageInfo(
                stage=ProcessStage.RESULT_INTEGRATION,
                title="結果統合",
                icon="🔗"
            ),
            ProcessStage.ANSWER_GENERATION: ProcessStageInfo(
                stage=ProcessStage.ANSWER_GENERATION,
                title="回答生成",
                icon="✍️"
            )
        }
    
    def start_process(self) -> None:
        """プロセス全体の開始"""
        self.total_start_time = time.time()
        self.is_active = True
        
        # 全段階を待機中にリセット
        for stage_info in self.stages.values():
            stage_info.status = ProcessStatus.PENDING
            stage_info.start_time = None
            stage_info.end_time = None
            stage_info.details = {}
        
        logger.info("プロセス追跡開始")
    
    def start_stage(self, stage: ProcessStage, details: Optional[Dict[str, Any]] = None) -> None:
        """特定段階の開始"""
        if not self.is_active:
            logger.warning(f"プロセス非アクティブ中に段階開始: {stage}")
            return
        
        stage_info = self.stages[stage]
        stage_info.status = ProcessStatus.RUNNING
        stage_info.start_time = time.time()
        
        if details:
            stage_info.details.update(details)
        
        self.current_stage = stage
        
        logger.info(f"段階開始: {stage_info.title}")
    
    def complete_stage(self, stage: ProcessStage, details: Optional[Dict[str, Any]] = None) -> None:
        """特定段階の完了"""
        if not self.is_active:
            logger.warning(f"プロセス非アクティブ中に段階完了: {stage}")
            return
        
        stage_info = self.stages[stage]
        stage_info.status = ProcessStatus.COMPLETED
        stage_info.end_time = time.time()
        
        if details:
            stage_info.details.update(details)
        
        logger.info(f"段階完了: {stage_info.title} ({stage_info.duration_str})")
    
    def error_stage(self, stage: ProcessStage, error_msg: str) -> None:
        """特定段階でのエラー"""
        if not self.is_active:
            logger.warning(f"プロセス非アクティブ中に段階エラー: {stage}")
            return
        
        stage_info = self.stages[stage]
        stage_info.status = ProcessStatus.ERROR
        stage_info.end_time = time.time()
        stage_info.details["error"] = error_msg
        
        logger.error(f"段階エラー: {stage_info.title} - {error_msg}")
    
    def complete_process(self) -> None:
        """プロセス全体の完了"""
        self.total_end_time = time.time()
        self.is_active = False
        self.current_stage = None
        
        total_duration = self.total_end_time - self.total_start_time if self.total_start_time else 0
        logger.info(f"プロセス追跡完了 (総実行時間: {total_duration:.2f}秒)")
    
    def get_progress_percentage(self) -> int:
        """全体進行度をパーセンテージで取得"""
        if not self.is_active:
            return 100
        
        completed_stages = sum(1 for stage_info in self.stages.values() 
                             if stage_info.status == ProcessStatus.COMPLETED)
        
        # 実行中の段階は50%として計算
        running_stages = sum(0.5 for stage_info in self.stages.values() 
                           if stage_info.status == ProcessStatus.RUNNING)
        
        total_progress = (completed_stages + running_stages) / len(self.stages)
        return min(int(total_progress * 100), 100)
    
    def get_stage_info(self, stage: ProcessStage) -> ProcessStageInfo:
        """特定段階の情報を取得"""
        return self.stages[stage]
    
    def get_all_stages_info(self) -> List[ProcessStageInfo]:
        """全段階の情報をリストで取得"""
        return list(self.stages.values())
    
    def update_stage_details(self, stage: ProcessStage, details: Dict[str, Any]) -> None:
        """段階の詳細情報を更新"""
        if stage in self.stages:
            self.stages[stage].details.update(details)
    
    def get_total_duration(self) -> Optional[float]:
        """全体実行時間を取得"""
        if self.total_start_time and self.total_end_time:
            return self.total_end_time - self.total_start_time
        return None

    def add_real_time_detail(self, stage: ProcessStage, detail_key: str, detail_value: str) -> None:
        """リアルタイムで段階の詳細情報を追加"""
        if stage in self.stages:
            if "real_time_details" not in self.stages[stage].details:
                self.stages[stage].details["real_time_details"] = []
            
            # タイムスタンプ付きで詳細情報を追加
            import time
            timestamp = time.strftime("%H:%M:%S")
            self.stages[stage].details["real_time_details"].append({
                "timestamp": timestamp,
                "key": detail_key,
                "value": detail_value
            })
            
            # 最新の10件まで保持
            if len(self.stages[stage].details["real_time_details"]) > 10:
                self.stages[stage].details["real_time_details"] = \
                    self.stages[stage].details["real_time_details"][-10:]
    
    def set_current_activity(self, stage: ProcessStage, activity: str) -> None:
        """現在の活動内容を設定"""
        if stage in self.stages:
            self.stages[stage].details["current_activity"] = activity
    
    def get_current_activity(self, stage: ProcessStage) -> Optional[str]:
        """現在の活動内容を取得"""
        if stage in self.stages:
            return self.stages[stage].details.get("current_activity")
        return None
    
    # ストリーミングコールバック用のメソッド
    def add_streaming_detail(self, title: str, description: str = "") -> None:
        """ストリーミング詳細ログを追加（コールバック用）"""
        if not hasattr(self, 'streaming_details'):
            self.streaming_details = []
        
        detail = {
            "timestamp": time.time(),
            "title": title,
            "description": description,
            "formatted_time": time.strftime("%H:%M:%S")
        }
        self.streaming_details.append(detail)
        
        # 最新50件のみ保持（メモリ管理）
        if len(self.streaming_details) > 50:
            self.streaming_details = self.streaming_details[-50:]
    
    def get_streaming_details(self) -> List[Dict[str, Any]]:
        """ストリーミング詳細ログを取得（コールバック用）"""
        if not hasattr(self, 'streaming_details'):
            self.streaming_details = []
        return self.streaming_details.copy()

    def get_real_time_details(self, stage: ProcessStage) -> List[Dict[str, str]]:
        """リアルタイム詳細情報を取得"""
        if stage in self.stages:
            return self.stages[stage].details.get("real_time_details", [])
        return []

    def add_filter_conditions(self, stage: ProcessStage, filter_conditions: Dict[str, Any]) -> None:
        """フィルタ条件を段階詳細に追加（XAI対応）"""
        if stage in self.stages:
            if "filter_conditions" not in self.stages[stage].details:
                self.stages[stage].details["filter_conditions"] = {}
            
            self.stages[stage].details["filter_conditions"].update(filter_conditions)
            
            # フィルタ条件のサマリーを生成
            filter_summary = self._generate_filter_summary(filter_conditions)
            self.stages[stage].details["filter_summary"] = filter_summary
            
    def _generate_filter_summary(self, filter_conditions: Dict[str, Any]) -> str:
        """フィルタ条件のサマリー文字列を生成"""
        summary_parts = []
        
        # スペースフィルタ
        if "space_key" in filter_conditions:
            summary_parts.append(f"📁 スペース: {filter_conditions['space_key']}")
        
        # 階層フィルタ
        if "hierarchy_filters" in filter_conditions and filter_conditions["hierarchy_filters"]:
            folder_count = len(filter_conditions["hierarchy_filters"])
            summary_parts.append(f"🗂️ フォルダ: {folder_count}個選択")
        
        # 削除ページフィルタ
        if "include_deleted" in filter_conditions:
            status = "含む" if filter_conditions["include_deleted"] else "除外"
            summary_parts.append(f"🗑️ 削除ページ: {status}")
        
        # 時期フィルタ
        if "date_filters" in filter_conditions:
            date_filters = filter_conditions["date_filters"]
            if date_filters.get("created_after") or date_filters.get("created_before"):
                summary_parts.append("📅 作成日フィルタ: 適用")
            if date_filters.get("updated_after") or date_filters.get("updated_before"):
                summary_parts.append("📅 更新日フィルタ: 適用")
        
        return " | ".join(summary_parts) if summary_parts else "フィルタなし"

    def get_filter_conditions(self, stage: ProcessStage) -> Dict[str, Any]:
        """フィルタ条件を取得"""
        if stage in self.stages:
            return self.stages[stage].details.get("filter_conditions", {})
        return {}


class StreamlitProcessDisplay:
    """
    Streamlit用プロセス表示コンポーネント
    """
    
    @staticmethod
    def render_process_tracker(tracker: ProcessTracker, placeholder=None) -> None:
        """
        プロセス追跡情報をStreamlitで描画（リアルタイム対応）
        
        Args:
            tracker: ProcessTrackerインスタンス
            placeholder: リアルタイム更新用のst.empty()プレースホルダー
        """
        if not tracker.is_active and tracker.get_progress_percentage() == 0:
            return
        
        # プロセス全体の進行度
        progress = tracker.get_progress_percentage()
        
        # リアルタイム更新のためにplaceholderを直接使用
        if placeholder:
            # placeholder内に全体をレンダリング
            with placeholder.container():
                st.progress(progress / 100, text=f"🤖 回答生成中... {progress}%")
                
                # 単一のアコーディオンにすべてのプロセスをまとめる
                progress_text = f"{tracker.get_progress_percentage()}%完了"
                current_stage_text = ""
                if tracker.current_stage:
                    current_stage_info = tracker.get_stage_info(tracker.current_stage)
                    current_stage_text = f" - {current_stage_info.title}実行中"
                
                with st.expander(f"🔍 処理プロセス詳細 ({progress_text}{current_stage_text})", expanded=True):
                    StreamlitProcessDisplay._render_all_stages_combined(tracker)
        else:
            # 通常の描画
            st.progress(progress / 100, text=f"🤖 回答生成中... {progress}%")
            
            # 単一のアコーディオンにすべてのプロセスをまとめる
            progress_text = f"{tracker.get_progress_percentage()}%完了"
            current_stage_text = ""
            if tracker.current_stage:
                current_stage_info = tracker.get_stage_info(tracker.current_stage)
                current_stage_text = f" - {current_stage_info.title}実行中"
            
            with st.expander(f"🔍 処理プロセス詳細 ({progress_text}{current_stage_text})", expanded=True):
                StreamlitProcessDisplay._render_all_stages_combined(tracker)
    
    @staticmethod
    def _render_all_stages_combined(tracker: ProcessTracker) -> None:
        """すべてのプロセス段階を一つのアコーディオンにまとめて表示"""
        # 全体状況の表示
        total_stages = len(tracker.get_all_stages_info())
        completed_stages = sum(1 for stage in tracker.get_all_stages_info() if stage.status == ProcessStatus.COMPLETED)
        
        st.markdown(f"**処理状況: {completed_stages}/{total_stages}段階完了**")
        
        # 現在実行中の段階を強調表示
        current_stage_name = ""
        if tracker.current_stage:
            current_stage_info = tracker.get_stage_info(tracker.current_stage)
            current_stage_name = f" （現在: {current_stage_info.title}）"
        
        st.caption(f"🔄 {current_stage_name}")
        st.divider()
        
        for i, stage_info in enumerate(tracker.get_all_stages_info(), 1):
            # ステータスアイコンの取得
            status_icon = StreamlitProcessDisplay._get_status_icon(stage_info.status)
            
            # 現在実行中の段階を強調
            if tracker.current_stage == stage_info.stage:
                st.markdown(f"**▶️ {i}. {stage_info.icon} {stage_info.title}** {status_icon} **← 実行中**")
            else:
                st.markdown(f"**{i}. {stage_info.icon} {stage_info.title}** {status_icon}")
            
            # 詳細情報の表示
            if stage_info.details:
                StreamlitProcessDisplay._render_stage_details_inline(stage_info)
            
            # 実行時間の表示
            if stage_info.duration:
                st.caption(f"⏱️ 実行時間: {stage_info.duration_str}")
            elif stage_info.status == ProcessStatus.RUNNING and stage_info.start_time:
                # 実行中の経過時間を表示
                import time
                elapsed = time.time() - stage_info.start_time
                st.caption(f"⏱️ 経過時間: {elapsed:.1f}秒")
            
            # 段階間の区切り線（最後以外）
            if i < len(tracker.get_all_stages_info()):
                st.markdown("---")
    
    @staticmethod
    def _get_status_icon(status: ProcessStatus) -> str:
        """ステータスに応じたアイコンを取得"""
        status_icons = {
            ProcessStatus.PENDING: "⏳",
            ProcessStatus.RUNNING: "🔄",
            ProcessStatus.COMPLETED: "✅",
            ProcessStatus.ERROR: "❌"
        }
        return status_icons.get(status, "⏳")
    
    @staticmethod
    def _render_stage(stage_info: ProcessStageInfo) -> None:
        """個別段階の描画"""
        # ステータスに応じたスタイル
        status_color = {
            ProcessStatus.PENDING: "background-color: #f0f0f0; color: #666;",
            ProcessStatus.RUNNING: "background-color: #e3f2fd; color: #1976d2;",
            ProcessStatus.COMPLETED: "background-color: #e8f5e8; color: #388e3c;",
            ProcessStatus.ERROR: "background-color: #ffebee; color: #d32f2f;"
        }
        
        # 段階タイトルとステータス
        title = f"{stage_info.icon} {stage_info.title}"
        expanded = stage_info.status in [ProcessStatus.COMPLETED, ProcessStatus.ERROR]
        
        with st.expander(f"{title} {stage_info.status.value}", expanded=expanded):
            if stage_info.details:
                StreamlitProcessDisplay._render_stage_details(stage_info)
            
            if stage_info.duration:
                st.caption(f"⏱️ 実行時間: {stage_info.duration_str}")
    
    @staticmethod
    def _render_stage_details_inline(stage_info: ProcessStageInfo) -> None:
        """段階詳細情報のインライン描画"""
        details = stage_info.details
        
        # 現在の活動内容を表示
        if "current_activity" in details:
            st.markdown(f"🔄 **{details['current_activity']}**")
        
        # CQL検索戦略の詳細情報を表示
        if "cql_search_details" in details:
            cql_details = details["cql_search_details"]
            st.markdown("🔍 **CQL検索詳細:**")
            
            # キーワード抽出結果
            if "extracted_keywords" in cql_details:
                keywords_str = " | ".join(cql_details["extracted_keywords"])
                st.caption(f"🔤 抽出キーワード: {keywords_str}")
            
            # 各戦略の実行結果（最新3件）
            if "detailed_process_log" in cql_details:
                st.markdown("📊 **戦略実行ログ:**")
                for log_entry in cql_details["detailed_process_log"][-3:]:
                    strategy_name = log_entry.get("strategy", "不明")
                    new_results = log_entry.get("new_results", 0)
                    total_results = log_entry.get("total_results", 0)
                    
                    # 戦略の詳細情報があれば表示
                    if "details" in log_entry:
                        strategy_details = log_entry["details"]
                        
                        # CQLクエリを表示
                        if "queries" in strategy_details:
                            st.caption(f"🔍 **{strategy_name}**:")
                            for query in strategy_details["queries"][-2:]:  # 最新2つのクエリ
                                st.code(query, language="sql")
                        
                        # 結果件数の内訳を表示
                        if "results_breakdown" in strategy_details:
                            breakdown_str = " | ".join(strategy_details["results_breakdown"])
                            st.caption(f"📊 結果: {breakdown_str} → 新規{new_results}件 (累計{total_results}件)")
        
        # フィルタ条件を表示（XAI対応）
        if "filter_summary" in details:
            st.markdown("🔍 **適用フィルタ:**")
            st.info(details["filter_summary"])
        
        # フィルタ条件の詳細表示
        if "filter_conditions" in details:
            filter_conditions = details["filter_conditions"]
            
            # 階層フィルタの詳細
            if "hierarchy_filters" in filter_conditions and filter_conditions["hierarchy_filters"]:
                hierarchy_filters = filter_conditions["hierarchy_filters"]
                st.markdown("📂 **フォルダフィルタ詳細:**")
                
                # フォルダ名を見やすく表示（最大5個まで）
                display_folders = hierarchy_filters[:5]
                for folder in display_folders:
                    st.caption(f"• {folder}")
                
                if len(hierarchy_filters) > 5:
                    st.caption(f"... 他{len(hierarchy_filters)-5}個のフォルダ")
            
            # CQLクエリの詳細表示
            if "generated_cql_queries" in filter_conditions:
                cql_queries = filter_conditions["generated_cql_queries"]
                st.markdown("💻 **生成CQLクエリ:**")
                for i, query in enumerate(cql_queries[:2], 1):  # 最大2つ表示
                    st.code(query, language="sql")
        
        # リアルタイム詳細情報を表示
        if "real_time_details" in details and details["real_time_details"]:
            st.markdown("📝 **実行ログ:**")
            # 最新の3件を表示
            for detail in details["real_time_details"][-3:]:
                st.caption(f"[{detail['timestamp']}] {detail['value']}")
        
        # その他の詳細情報をコンパクトに表示
        detail_items = []
        
        if stage_info.stage == ProcessStage.QUESTION_ANALYSIS:
            if "keywords" in details and details["keywords"]:
                detail_items.append(f"📝 キーワード: {', '.join(details['keywords'][:3])}" + 
                                  (f" 他{len(details['keywords'])-3}件" if len(details['keywords']) > 3 else ""))
            if "search_targets" in details:
                detail_items.append(f"🎯 検索対象: {details['search_targets']}")
        
        elif stage_info.stage == ProcessStage.TOOL_SELECTION:
            if "selected_tools" in details:
                detail_items.append(f"🛠️ 選択ツール: {', '.join(details['selected_tools'])}")
        
        elif stage_info.stage == ProcessStage.SEARCH_EXECUTION:
            if "search_queries" in details:
                detail_items.append(f"🔍 実行クエリ数: {len(details['search_queries'])}件")
            if "results_count" in details:
                detail_items.append(f"📊 取得結果: {details['results_count']}件")
        
        elif stage_info.stage == ProcessStage.RESULT_INTEGRATION:
            if "sources_count" in details:
                detail_items.append(f"📚 統合ソース: {details['sources_count']}件")
        
        elif stage_info.stage == ProcessStage.ANSWER_GENERATION:
            if "response_length" in details:
                detail_items.append(f"📝 回答文字数: {details['response_length']}文字")
        
        # 詳細項目を表示
        if detail_items:
            for item in detail_items:
                st.caption(item)
    
    @staticmethod
    def _render_stage(stage_info: ProcessStageInfo) -> None:
        """個別段階の描画（後方互換性のため残存）"""
        # 段階タイトルとステータス
        title = f"{stage_info.icon} {stage_info.title}"
        expanded = stage_info.status in [ProcessStatus.COMPLETED, ProcessStatus.ERROR]
        
        with st.expander(f"{title} {stage_info.status.value}", expanded=expanded):
            if stage_info.details:
                StreamlitProcessDisplay._render_stage_details_inline(stage_info)
            
            if stage_info.duration:
                st.caption(f"⏱️ 実行時間: {stage_info.duration_str}") 