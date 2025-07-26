import streamlit as st
import logging
from typing import Dict, Any

from src.spec_bot_mvp.tools.hybrid_search_tool import HybridSearchTool
from src.spec_bot_mvp.ui.components.thinking_process_ui import IntegratedThinkingProcessUI

logger = logging.getLogger(__name__)

def format_search_results(search_data: Dict) -> str:
    """検索結果データ（辞書）をUI表示用のMarkdown文字列にフォーマットする"""
    
    if not search_data or "error" in search_data:
        return f"🚨 **検索エラー**\n\n{search_data.get('error', '不明なエラーが発生しました。')}"

    query = search_data.get("query", "N/A")
    step2_keyword = search_data.get("step2_keyword_result", {})
    step2_datasource = search_data.get("step2_datasource_result", {})
    step3_result = search_data.get("step3_result", {})
    step4_result = search_data.get("step4_result", {})

    # 主要情報の抽出
    primary_keywords = step2_keyword.get("primary_keywords", [])
    search_intent = step2_keyword.get("search_intent", "不明")
    selected_ds = step2_datasource.get("selected_datasources", ["不明"])
    primary_datasource = selected_ds[0] if selected_ds else "不明"
    
    ranked_results = step4_result.get("ranked_results", [])
    top_results = ranked_results[:5]  # 上位5件に制限

    # --- 回答生成 ---
    output = [
        f"## 🎯 「{query}」の検索結果",
        "---",
        "### 💡 総括",
        f"**{len(ranked_results)}件**の関連情報が見つかりました。特に品質の高い上位**{len(top_results)}件**を以下に要約します。",
        ""
    ]

    # --- 上位結果の要約 ---
    if not top_results:
        output.append("**検索結果が見つかりませんでした。** フィルタ条件やキーワードを変更して再度お試しください。")
    else:
        output.append("### 📊 高品質な検索結果 TOP5")
        for i, res in enumerate(top_results, 1):
            title = res.get("title", "タイトルなし")
            url = res.get("url", "#")
            score = res.get("final_score", 0)
            datasource = res.get("datasource", "不明").capitalize()
            
            output.append(f"**{i}. [{title}]({url})**")
            output.append(f"   - **品質スコア:** `{score:.3f}`")
            output.append(f"   - **データソース:** `{datasource}`")
            if "summary" in res and res["summary"]:
                output.append(f"   - **要約:** {res['summary']}")
        output.append("")

    # --- 深掘り提案 ---
    # ここでは固定の提案だが、将来的には結果に基づいて動的に生成する
    output.extend([
        "### 🎯 さらなる深掘り・関連情報",
        "- 「ログイン機能の会員機能について知りたい」",
        "- 「ログイン認証のセキュリティ仕様を確認したい」",
        "- 「ログイン後の画面遷移フローを見たい」"
    ])

    return "\n".join(output)

def execute_integrated_search_with_progress(prompt: str, thinking_ui: IntegratedThinkingProcessUI, process_placeholder) -> Dict[str, Any]:
    """プロセス可視化付き統合検索実行（本番データ接続版）"""
    try:
        # HybridSearchToolのインスタンスを取得
        hybrid_tool = st.session_state.hybrid_tool

        # コールバック関数を正しく定義（ログ出力とエラーハンドリング付き）
        def update_callback(stage_id, details):
            try:
                logger.info(f"🔄 思考プロセス更新: {stage_id} -> completed")
                thinking_ui.update_stage_status(stage_id, "completed", details)
                # Streamlitのリアルタイム更新のため、placeholderを直接書き換え
                process_placeholder.empty()  # 既存内容をクリア
                with process_placeholder.container():
                    thinking_ui.render_process_visualization()
                # 表示の確実性のため短時間待機
                import time
                time.sleep(0.1)
                logger.info(f"✅ 思考プロセス更新完了: {stage_id}")
            except Exception as e:
                logger.error(f"❌ 思考プロセス更新エラー({stage_id}): {e}")
        
        def in_progress_callback(stage_id):
            try:
                logger.info(f"🚀 思考プロセス開始: {stage_id} -> in_progress")
                thinking_ui.update_stage_status(stage_id, "in_progress")
                # Streamlitのリアルタイム更新のため、placeholderを直接書き換え
                process_placeholder.empty()  # 既存内容をクリア
                with process_placeholder.container():
                    thinking_ui.render_process_visualization()
                # 表示の確実性のため短時間待機
                import time
                time.sleep(0.1)
                logger.info(f"✅ 思考プロセス開始完了: {stage_id}")
            except Exception as e:
                logger.error(f"❌ 思考プロセス開始エラー({stage_id}): {e}")

        # 思考プロセスの各ステップをリアルタイムで更新しながら検索実行
        logger.info("🔍 ハイブリッド検索開始...")
        search_result_data = hybrid_tool.search(
            query=prompt,
            update_callback=update_callback,
            in_progress_callback=in_progress_callback
        )

        # 最終的な思考プロセス表示を更新
        logger.info("📊 最終的な思考プロセス表示更新中...")
        with process_placeholder.container():
            thinking_ui.render_process_visualization()
        
        # UI表示用に結果をフォーマット
        formatted_result = format_search_results(search_result_data)
        
        # 思考プロセスデータをUIの状態と統合
        final_thinking_process_data = search_result_data.copy() # 元の辞書を変更しないようにコピー
        if hasattr(thinking_ui, 'process_stages'):
            final_thinking_process_data["process_stages"] = thinking_ui.process_stages

        logger.info("✅ 統合検索完了")
        return {
            "search_result": formatted_result,
            "thinking_process": final_thinking_process_data,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"統合検索エラー: {str(e)}")
        # エラー時もUIで表示を統一
        thinking_ui.update_stage_status("response_generation", "error", {"error_message": str(e)})
        with process_placeholder.container():
            thinking_ui.render_process_visualization()
            
        return {
            "search_result": f"申し訳ございません。検索処理中にエラーが発生しました: {str(e)}",
            "thinking_process": {"process_stages": thinking_ui.process_stages} if hasattr(thinking_ui, 'process_stages') else {},
            "success": False
        } 