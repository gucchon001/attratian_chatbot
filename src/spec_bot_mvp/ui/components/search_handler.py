import streamlit as st
import logging
from typing import Dict, Any

from src.spec_bot_mvp.tools.hybrid_search_tool import HybridSearchTool
from src.spec_bot_mvp.ui.components.thinking_process_ui import IntegratedThinkingProcessUI
from src.spec_bot_mvp.agents.response_generator import ResponseGenerationAgent  # 変更: 全文取得対応版を使用

logger = logging.getLogger(__name__)

def format_search_results(search_data: Dict) -> str:
    """
    検索結果データ（辞書）をNotebookLMスタイルの包括的回答に変換
    ResponseGenerationAgent（全文取得対応）を使用した高品質回答生成
    """
    
    if not search_data or "error" in search_data:
        return f"🚨 **検索エラー**\n\n{search_data.get('error', '不明なエラーが発生しました。')}"

    # 検索データの抽出
    query = search_data.get("query", "N/A")
    step3_result = search_data.get("step3_result", {})
    step4_result = search_data.get("step4_result", {})
    
    # 検索結果の取得
    ranked_results = step4_result.get("ranked_results", [])
    
    try:
        # ResponseGenerationAgent（全文取得対応）の初期化と実行
        response_generator = ResponseGenerationAgent()
        
        # 包括的回答生成（全文取得機能付き）
        comprehensive_response = response_generator.generate_response(
            search_results=ranked_results,
            user_query=query
        )
        
        logger.info(f"✅ ResponseGenerationAgent回答生成完了: {len(comprehensive_response)}文字")
        return comprehensive_response
        
    except Exception as e:
        logger.error(f"❌ ResponseGenerationAgent エラー: {e}")
        
        # フォールバック: 従来の形式
        search_metadata = {
            "total_results": step3_result.get("total_results", 0),
            "execution_summary": step3_result.get("execution_summary", ""),
            "strategies_executed": step3_result.get("strategies_executed", []),
            "query_details": step3_result.get("query_details", {})
        }
        return _generate_fallback_format(query, ranked_results, search_metadata)

def _generate_fallback_format(query: str, ranked_results: list, search_metadata: dict) -> str:
    """エラー時のフォールバック形式（従来型）"""
    
    output = [
        f"## 🎯 「{query}」の検索結果",
        "---",
        f"**{len(ranked_results)}件**の関連情報が見つかりました。",
        ""
    ]

    # 結果の簡易表示
    for i, result in enumerate(ranked_results[:5], 1):
        title = result.get("title", "タイトルなし")
        score = result.get("final_score", 0)
        datasource = result.get("datasource", "unknown").capitalize()
        excerpt = result.get("excerpt", "")[:150]
        
        output.extend([
            f"### {i}. {title}",
            f"**データソース**: {datasource} | **品質スコア**: {score:.3f}",
            "",
            excerpt + ("..." if len(result.get("excerpt", "")) > 150 else ""),
            ""
        ])

    output.extend([
        "---",
        "**⚠️ 注意**: AI分析機能でエラーが発生したため、基本形式で表示しています。"
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