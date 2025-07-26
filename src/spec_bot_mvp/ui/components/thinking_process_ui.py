import streamlit as st
from typing import Dict, List, Any

class IntegratedThinkingProcessUI:
    """統合版思考プロセス可視化UI"""
    
    def __init__(self):
        # 仕様書準拠のステップ定義
        self.process_stages = [
            {"id": "filter_application", "name": "🎯 1. フィルタ機能", "status": "pending"},
            {"id": "analysis", "name": "🔍 2. ユーザー質問解析・抽出", "status": "pending"},
            {"id": "search_execution", "name": "⚡ 3. CQL検索実行", "status": "pending"},
            {"id": "result_integration", "name": "🔗 4. 品質評価・ランキング", "status": "pending"},
            {"id": "response_generation", "name": "💡 5. 回答生成", "status": "pending"}
        ]
        
    def update_stage_status(self, stage_id: str, status: str, details: Dict = None):
        """プロセス段階のステータス更新"""
        print(f"🔄 ステータス更新: {stage_id} -> {status}")  # デバッグ用ログ
        for stage in self.process_stages:
            if stage["id"] == stage_id:
                stage["status"] = status
                if details:
                    stage["details"] = details
                print(f"✅ ステータス更新完了: {stage_id} ({status})")  # デバッグ用ログ
                break
        else:
            print(f"❌ ステージが見つかりません: {stage_id}")  # デバッグ用ログ
    
    def render_progress_indicator(self) -> None:
        """進行度インジケーター表示"""
        completed_stages = sum(1 for stage in self.process_stages if stage["status"] == "completed")
        progress = completed_stages / len(self.process_stages)
        
        st.progress(progress, text=f"処理進行度: {completed_stages}/{len(self.process_stages)} 完了")
    
    def render_stage_details(self, stage: Dict) -> None:
        """各段階詳細表示（強化版）"""
        status = stage["status"]
        name = stage["name"]
        
        if status == "completed":
            with st.expander(f"✅ {name} - 完了", expanded=False):
                if "details" in stage:
                    details = stage["details"]
                    
                    # 実行時間表示
                    if "execution_time" in details:
                        st.metric("実行時間", f"{details['execution_time']:.2f}秒")
                    
                    # 結果数表示  
                    if "result_count" in details:
                        st.metric("取得結果数", f"{details['result_count']}件")
                    
                    # 検索クエリ表示
                    if "search_query" in details:
                        st.code(details["search_query"], language="sql")
                    
                    # その他詳細情報
                    for key, value in details.items():
                        if key not in ["execution_time", "result_count", "search_query"]:
                            if isinstance(value, dict):
                                st.json(value)
                            else:
                                st.write(f"**{key}:** {value}")
                                
        elif status == "in_progress":
            with st.expander(f"🔄 {name} - 実行中...", expanded=True):
                # プログレス表示
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # 段階別の進行表示
                if "filter_application" in stage["id"]:
                    status_text.text("フィルター条件を適用中...")
                    progress_bar.progress(30)
                elif "analysis" in stage["id"]:
                    status_text.text("キーワード抽出・データソース判定中...")
                    progress_bar.progress(50)
                elif "search_execution" in stage["id"]:
                    status_text.text("CQL検索を実行中...")
                    progress_bar.progress(70)
                elif "result_integration" in stage["id"]:
                    status_text.text("品質評価・ランキング処理中...")
                    progress_bar.progress(85)
                elif "response_generation" in stage["id"]:
                    status_text.text("AI回答を生成中...")
                    progress_bar.progress(95)
                    
        elif status == "pending":
            st.write(f"⏳ {name} - 待機中")
        else:
            st.write(f"❌ {name} - エラー")
            if "error_message" in stage:
                st.error(stage["error_message"])

    def render_process_visualization(self) -> None:
        """プロセス可視化全体表示（理想的なUI改善版）"""
        # デバッグ用ログ
        completed_stages = sum(1 for stage in self.process_stages if stage["status"] == "completed")
        in_progress_stages = sum(1 for stage in self.process_stages if stage["status"] == "in_progress")
        total_stages = len(self.process_stages)
        
        print(f"🖼️ 思考プロセス表示: 完了={completed_stages}, 実行中={in_progress_stages}, 総数={total_stages}")
        
        # メインヘッダー（より洗練された表示）
        st.markdown("---")
        if completed_stages == total_stages:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("## 🧠 思考プロセス完了")
                st.caption("AI検索エンジンによる5段階の処理が完了しました")
            with col2:
                st.metric("", "✅ 完了", delta="5/5段階")
        elif in_progress_stages > 0:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("## 🧠 思考プロセス実行中")
                st.caption("AI検索エンジンが段階的に処理を実行しています")
            with col2:
                st.metric("", f"🔄 実行中", delta=f"{completed_stages}/{total_stages}段階")
        else:
            st.markdown("## 🧠 思考プロセス")
        
        # フロー全体の可視化（コンパクト版）
        self._render_process_flow_compact()
        
        # 重要な段階のみ詳細表示
        st.markdown("### 📊 処理詳細")
        
        # 完了した重要段階を統合して1つのアコーディオンで表示
        critical_stages = [stage for stage in self.process_stages 
                          if stage["status"] == "completed" and 
                          stage["id"] in ["analysis", "search_execution", "result_integration"]]
        
        non_critical_stages = [stage for stage in self.process_stages 
                              if stage["status"] == "completed" and 
                              stage["id"] not in ["analysis", "search_execution", "result_integration"]]
        
        # 非クリティカルな段階は1行表示
        for stage in non_critical_stages:
            status_icon = "✅"
            st.markdown(f"{status_icon} **{stage['name']}** - 完了")
        
        # クリティカルな段階は1つのアコーディオンに統合
        if critical_stages:
            with st.expander("🔍 **詳細な処理ステップ** (解析・検索・統合)", expanded=False):
                for i, stage in enumerate(critical_stages):
                    if i > 0:
                        st.divider()
                    
                    st.markdown(f"### {stage['name']}")
                    if "details" in stage:
                        self._render_critical_insights(stage["id"], stage["details"])
                    else:
                        st.info(f"{stage['name']} が完了しました。")
        
        # 完了時の統合サマリー
        if completed_stages == total_stages:
            st.markdown("---")
            self._render_process_insights()
    
    def _render_process_flow_compact(self) -> None:
        """プロセスフローの視覚化強化版"""
        st.markdown("#### 🔄 AI思考フロー")
        
        # 5段階を矢印付きで横並び表示（フロー感を強調）
        cols = st.columns([2, 0.3, 2, 0.3, 2, 0.3, 2, 0.3, 2])
        
        stage_cols = [0, 2, 4, 6, 8]  # 段階用の列インデックス
        arrow_cols = [1, 3, 5, 7]     # 矢印用の列インデックス
        
        for i, stage in enumerate(self.process_stages):
            # 段階カード
            with cols[stage_cols[i]]:
                status = stage["status"]
                name = stage["name"].split(". ")[1] if ". " in stage["name"] else stage["name"]
                
                if status == "completed":
                    # 完了段階：緑のカード + 詳細メトリクス
                    details = stage.get("details", {})
                    metric_text = self._get_stage_metric(stage["id"], details)
                    
                    st.markdown(f"""
                    <div style='text-align: center; padding: 12px; background: linear-gradient(145deg, #d4edda, #c3e6cb); 
                                border-radius: 12px; margin: 5px; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); border: 2px solid #28a745;'>
                        <div style='font-size: 24px; margin-bottom: 5px;'>✅</div>
                        <div style='font-size: 11px; font-weight: bold; color: #155724;'>{name}</div>
                        <div style='font-size: 9px; color: #155724; margin-top: 3px;'>{metric_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                elif status == "in_progress":
                    st.markdown(f"""
                    <div style='text-align: center; padding: 12px; background: linear-gradient(145deg, #cce7ff, #b3d9ff); 
                                border-radius: 12px; margin: 5px; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); border: 2px solid #007bff;'>
                        <div style='font-size: 24px; margin-bottom: 5px;'>🔄</div>
                        <div style='font-size: 11px; font-weight: bold; color: #004085;'>{name}</div>
                        <div style='font-size: 9px; color: #004085; margin-top: 3px;'>実行中...</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='text-align: center; padding: 12px; background: #f8f9fa; 
                                border-radius: 12px; margin: 5px; border: 1px dashed #6c757d;'>
                        <div style='font-size: 24px; margin-bottom: 5px;'>⏳</div>
                        <div style='font-size: 11px; color: #6c757d;'>{name}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # 矢印（段階間）
            if i < len(arrow_cols):
                with cols[arrow_cols[i]]:
                    if i < len(self.process_stages) - 1:
                        next_status = self.process_stages[i + 1]["status"]
                        arrow_color = "#28a745" if next_status == "completed" else "#007bff" if next_status == "in_progress" else "#6c757d"
                        st.markdown(f"""
                        <div style='text-align: center; padding-top: 20px;'>
                            <div style='font-size: 20px; color: {arrow_color};'>→</div>
                        </div>
                        """, unsafe_allow_html=True)
    
    def _get_stage_metric(self, stage_id: str, details: Dict) -> str:
        """段階別のメトリクステキスト取得"""
        if stage_id == "filter_application":
            return "フィルタ適用"
        elif stage_id == "analysis":
            keywords = details.get("primary_keywords") or details.get("extracted_keywords", [])
            return f"{len(keywords)}キーワード"
        elif stage_id == "search_execution":
            total = details.get("total_results", 0)
            return f"{total}件取得"
        elif stage_id == "result_integration":
            ranked = details.get("ranked_results", [])
            return f"{len(ranked)}件選出"
        elif stage_id == "response_generation":
            return "回答完了"
        return "完了"
    
    def _render_stage_summary(self, stage: Dict, stage_number: int) -> None:
        """段階サマリー表示（重要情報のみ）- 統合版では使用しない"""
        # この関数は統合アコーディオン版では使用しないが、互換性のため残す
        pass
    
    def _render_critical_insights(self, stage_id: str, details: Dict) -> None:
        """クリティカルな段階の重要洞察表示（詳細強化版）"""
        if stage_id == "analysis":
            # 解析段階：AI思考過程の詳細表示
            keywords = details.get("primary_keywords") or details.get("extracted_keywords", [])
            datasources = details.get("selected_datasources", [])
            intent = details.get("search_intent", "機能照会")
            confidence = details.get("confidence_score", 0)
            
            # AI思考過程をストーリー形式で表示
            with st.container():
                st.markdown("### 🧠 AI思考プロセス")
                
                # ステップ1: 質問解析
                st.markdown("#### 📝 ステップ1: ユーザー質問の解析")
                st.info(f"「ログイン機能の詳細を教えて」→ **{intent}** として判定")
                
                # ステップ2: キーワード抽出
                st.markdown("#### 🔍 ステップ2: 重要キーワードの抽出")
                if keywords:
                    keyword_tags = " ".join([f"<span style='background: #e3f2fd; padding: 3px 8px; border-radius: 12px; font-size: 12px; margin: 2px;'>{kw}</span>" for kw in keywords])
                    st.markdown(f"**抽出結果:** {keyword_tags}", unsafe_allow_html=True)
                    st.caption(f"信頼度: {confidence:.1%} | 抽出手法: {details.get('extraction_method', 'AI分析')}")
                
                # ステップ3: データソース判定
                st.markdown("#### 🎯 ステップ3: 最適データソースの判定")
                reasoning = details.get("judgment_reasoning", "")
                if reasoning:
                    # 判定理由を省略せずに完全表示
                    st.markdown(f"**判定理由:** {reasoning}")
                else:
                    # reasoningがない場合の代替表示
                    confluence_conf = details.get("confluence_confidence", 0.0)
                    jira_conf = details.get("jira_confidence", 0.0)
                    if confluence_conf > 0 or jira_conf > 0:
                        st.markdown(f"**判定理由:** 入力キーワード: {', '.join(keywords)} | "
                                  f"Confluence確信度: {confluence_conf:.2f} | "
                                  f"Jira確信度: {jira_conf:.2f} | "
                                  f"選択データソース: {', '.join(datasources)} | "
                                  f"検索意図: {intent}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("🎯 選択データソース", ", ".join(datasources) if datasources else "両方")
                with col2:
                    st.metric("🎯 検索戦略", intent)
                
        elif stage_id == "search_execution":
            # 検索段階：実行戦略と結果詳細
            all_results = details.get("all_results", [])
            total = details.get("total_results", len(all_results))
            execution_summary = details.get("execution_summary", "")
            
            st.markdown("### ⚡ 検索実行ストラテジー")
            
            # 実行サマリー
            if execution_summary:
                st.markdown("#### 📊 実行戦略")
                st.success(execution_summary)
            
            # 結果統計の視覚化
            st.markdown("#### 📈 検索結果統計")
            if total > 0:
                conf_count = len([r for r in all_results if r.get("datasource") == "confluence"])
                jira_count = len([r for r in all_results if r.get("datasource") == "jira"])
                
                # プログレスバーで結果分布を表示
                if conf_count > 0:
                    conf_ratio = conf_count / total
                    st.markdown(f"**📚 Confluence: {conf_count}件**")
                    st.progress(conf_ratio, text=f"{conf_ratio:.1%}")
                
                if jira_count > 0:
                    jira_ratio = jira_count / total
                    st.markdown(f"**🎫 Jira: {jira_count}件**")
                    st.progress(jira_ratio, text=f"{jira_ratio:.1%}")
                
                # 検索戦略詳細
                strategies = details.get("strategies_executed", [])
                if strategies:
                    st.markdown("#### 🔍 実行された検索戦略")
                    for i, strategy in enumerate(strategies, 1):
                        st.markdown(f"{i}. **{strategy}**")
            else:
                st.warning("⚠️ 検索結果が見つかりませんでした")
                
        elif stage_id == "result_integration":
            # 統合段階：品質評価とランキングロジック
            ranked_results = details.get("ranked_results", [])
            evaluation_summary = details.get("evaluation_summary", "")
            
            st.markdown("### 🏆 インテリジェント品質評価")
            
            # 評価サマリー
            if evaluation_summary:
                st.markdown("#### 📊 評価結果サマリー")
                st.info(evaluation_summary)
            
            # 品質分布の可視化
            st.markdown("#### 📈 品質スコア分析")
            if ranked_results:
                # 上位結果の詳細表示
                st.markdown("**🏆 TOP品質結果:**")
                
                for i, result in enumerate(ranked_results[:3], 1):
                    title = result.get("title", "タイトル不明")
                    score = result.get("final_score", 0)
                    datasource = result.get("datasource", "不明")
                    
                    # スコアバー表示
                    score_color = "#28a745" if score > 0.7 else "#ffc107" if score > 0.4 else "#dc3545"
                    
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.markdown(f"**{i}. {title[:40]}{'...' if len(title) > 40 else ''}**")
                        with col2:
                            st.markdown(f"<div style='background: {score_color}; color: white; padding: 2px 8px; border-radius: 8px; text-align: center; font-size: 12px;'>{score:.3f}</div>", unsafe_allow_html=True)
                        with col3:
                            ds_color = "#17a2b8" if datasource == "confluence" else "#6f42c1"
                            st.markdown(f"<div style='background: {ds_color}; color: white; padding: 2px 8px; border-radius: 8px; text-align: center; font-size: 11px;'>{datasource}</div>", unsafe_allow_html=True)
                
                # 品質分布統計
                avg_quality = details.get("avg_quality", 0)
                max_score = details.get("max_score", 0)
                high_quality_rate = details.get("high_quality_rate", 0)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("平均品質", f"{avg_quality:.3f}")
                with col2:
                    st.metric("最高品質", f"{max_score:.3f}")
                with col3:
                    st.metric("高品質率", f"{high_quality_rate:.1%}" if isinstance(high_quality_rate, (int, float)) else "計算中")
            else:
                st.warning("品質評価対象の結果がありません")
    
    def _render_process_insights(self) -> None:
        """プロセス完了時の統合インサイト（理想版）"""
        st.markdown("### 🎯 AIパフォーマンス・サマリー")
        
        # キーメトリクスの抽出
        insights = []
        total_results = 0
        final_selected = 0
        keywords_count = 0
        max_quality = 0
        
        for stage in self.process_stages:
            if stage["status"] == "completed" and "details" in stage:
                details = stage["details"]
                
                if stage["id"] == "analysis":
                    keywords = details.get("primary_keywords") or details.get("extracted_keywords", [])
                    keywords_count = len(keywords)
                
                elif stage["id"] == "search_execution":
                    total_results = details.get("total_results", 0)
                
                elif stage["id"] == "result_integration":
                    ranked = details.get("ranked_results", [])
                    final_selected = len(ranked)
                    max_quality = details.get("max_score", 0)
        
        # メトリクスダッシュボード
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div style='text-align: center; padding: 15px; background: linear-gradient(145deg, #e3f2fd, #bbdefb); 
                        border-radius: 12px; border: 1px solid #2196f3;'>
                <div style='font-size: 28px; color: #1976d2;'>🔍</div>
                <div style='font-size: 20px; font-weight: bold; color: #1976d2;'>{}</div>
                <div style='font-size: 12px; color: #1976d2;'>キーワード解析</div>
            </div>
            """.format(keywords_count), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style='text-align: center; padding: 15px; background: linear-gradient(145deg, #f3e5f5, #e1bee7); 
                        border-radius: 12px; border: 1px solid #9c27b0;'>
                <div style='font-size: 28px; color: #7b1fa2;'>📊</div>
                <div style='font-size: 20px; font-weight: bold; color: #7b1fa2;'>{}</div>
                <div style='font-size: 12px; color: #7b1fa2;'>データ検索</div>
            </div>
            """.format(total_results), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style='text-align: center; padding: 15px; background: linear-gradient(145deg, #e8f5e8, #c8e6c9); 
                        border-radius: 12px; border: 1px solid #4caf50;'>
                <div style='font-size: 28px; color: #388e3c;'>🏆</div>
                <div style='font-size: 20px; font-weight: bold; color: #388e3c;'>{}</div>
                <div style='font-size: 12px; color: #388e3c;'>結果選出</div>
            </div>
            """.format(final_selected), unsafe_allow_html=True)
        
        with col4:
            quality_color = "#4caf50" if max_quality > 0.7 else "#ff9800" if max_quality > 0.4 else "#f44336"
            st.markdown("""
            <div style='text-align: center; padding: 15px; background: linear-gradient(145deg, #fff3e0, #ffe0b2); 
                        border-radius: 12px; border: 1px solid #ff9800;'>
                <div style='font-size: 28px; color: {};'>⭐</div>
                <div style='font-size: 20px; font-weight: bold; color: {};'>{:.3f}</div>
                <div style='font-size: 12px; color: {};'>最高品質</div>
            </div>
            """.format(quality_color, quality_color, max_quality, quality_color), unsafe_allow_html=True)
        
        # 処理効率とパフォーマンス
        st.markdown("---")
        st.markdown("#### 🚀 処理効率パフォーマンス")
        
        if total_results > 0 and final_selected > 0:
            efficiency = (final_selected / total_results) * 100
            
            # 効率性の評価
            if efficiency >= 10:
                efficiency_label = "🌟 優秀"
                efficiency_color = "#4caf50"
            elif efficiency >= 5:
                efficiency_label = "✅ 良好"
                efficiency_color = "#ff9800"
            else:
                efficiency_label = "⚡ 高精度"
                efficiency_color = "#2196f3"
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.progress(min(efficiency/20, 1.0), text=f"選択効率: {efficiency:.1f}% ({final_selected}/{total_results}件)")
            with col2:
                st.markdown(f"""
                <div style='text-align: center; padding: 8px; background: {efficiency_color}; color: white; 
                            border-radius: 8px; font-weight: bold;'>
                    {efficiency_label}
                </div>
                """, unsafe_allow_html=True)
        
        # AIシステムの処理サマリー
        st.markdown("#### 🤖 AIシステム処理サマリー")
        summary_text = f"""
        **🎯 検索戦略:** {keywords_count}個の重要キーワードを抽出し、最適な検索戦略を構築  
        **📊 データマイニング:** {total_results}件のデータから関連情報を収集  
        **🏆 品質フィルタリング:** AI品質評価により{final_selected}件の高関連性結果を選出  
        **⭐ 品質保証:** 最高品質スコア{max_quality:.3f}で信頼性の高い情報を提供
        """
        st.success(summary_text)