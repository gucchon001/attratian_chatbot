"""
ハイブリッド検索ツール

仕様書準拠のStep1-3統合フローを提供する検索エンジン
- Step1: フィルタ機能
- Step2: ユーザー質問解析・抽出 (キーワード抽出、データソース判定)
- Step3: CQL検索実行
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.spec_bot_mvp.steps.step1_keyword_extraction import KeywordExtractor
from src.spec_bot_mvp.steps.step2_datasource_judgment import DataSourceJudge
from src.spec_bot_mvp.steps.step3_cql_search import CQLSearchEngine
from src.spec_bot_mvp.steps.step4_quality_evaluation import QualityEvaluator

logger = logging.getLogger(__name__)

class HybridSearchTool:
    """ハイブリッド検索ツール（仕様書準拠版）"""
    
    def __init__(self):
        """初期化"""
        self.name = "hybrid_search"
        self.description = """
        JiraとConfluenceを横断した高度なハイブリッド検索を実行します。
        
        仕様書準拠のステップ定義：
        - Step1: フィルタ機能（階層フィルタ、削除ページフィルタ、データソース選択）
        - Step2: ユーザー質問解析・抽出（キーワード抽出、データソース判定）
        - Step3: CQL検索実行（3段階検索戦略）
        
        使用例:
        - "ログイン機能のバグを調査したい"
        - "API設計の仕様書を探して"
        - "データベース接続エラーの原因を調べて"
        """
        self._init_components()
    
    def _init_components(self):
        """Step2-4コンポーネント初期化（Step1はUIで処理済み）"""
        try:
            self.extractor = KeywordExtractor()
            self.judge = DataSourceJudge()
            self.search_engine = CQLSearchEngine()
            self.evaluator = QualityEvaluator()
            logger.info("ハイブリッド検索ツール初期化完了")
        except Exception as e:
            logger.error(f"ハイブリッド検索ツール初期化失敗: {e}")
            raise
    
    def run(self, query: str) -> str:
        """LangChain Agent互換のrunメソッド"""
        return self.search(query)
    
    def search(self, query: str) -> str:
        """ハイブリッド検索実行（仕様書準拠）"""
        try:
            logger.info(f"ハイブリッド検索開始: {query[:50]}...")
            
            # Step1: フィルタ機能（UIで既に処理済み）
            # - 階層フィルタ、削除ページフィルタ、データソース選択
            step1_result = {"status": "ui_processed", "filters_applied": True}
            
            # Step2: ユーザー質問解析・抽出
            step2_keyword_result = self.extractor.extract_keywords(query)
            step2_datasource_result = self.judge.judge_datasource(step2_keyword_result)
            
            # Step3: CQL検索実行
            step3_result = self.search_engine.execute_search(step2_datasource_result, step2_keyword_result)
            
            # Step4: 品質評価・ランキング
            step4_result = self.evaluator.evaluate_and_rank(step3_result, step2_keyword_result, step2_datasource_result)
            
            # 結果データ統合（UI表示用）- 重複表示回避のため表示はUI側に委ねる
            final_result = {
                "query": query,
                "step1_result": step1_result,
                "step2_keyword_result": step2_keyword_result,
                "step2_datasource_result": step2_datasource_result,
                "step3_result": step3_result,
                "step4_result": step4_result,
                # 統計情報をUI側で利用可能にする
                "search_summary": {
                    "total_results": len(step3_result.get("all_results", [])),
                    "selected_count": len(step4_result.get("ranked_results", [])),
                    "avg_quality": step4_result.get("avg_quality", 0),
                    "high_quality_rate": step4_result.get("high_quality_rate", 0),
                    "max_score": step4_result.get("max_score", 0),
                    "quality_stats": step4_result.get("quality_stats", {}),
                    "evaluation_summary": step4_result.get("evaluation_summary", "")
                }
            }
            
            # ログ出力のみ（表示は UI側で統一）
            search_summary = final_result["search_summary"]
            logger.info(f"ハイブリッド検索完了: {search_summary['selected_count']}件選出, 平均品質: {search_summary['avg_quality']:.2f}")
            
            return final_result
            
        except Exception as e:
            logger.error(f"ハイブリッド検索エラー: {e}")
            # エラー時もUI側で統一表示するため、エラー情報を含む結果を返す
            error_result = {
                "query": query,
                "error": str(e),
                "step1_result": {"status": "error"},
                "step2_keyword_result": {},
                "step2_datasource_result": {},
                "step3_result": {},
                "step4_result": {},
                "search_summary": {
                    "total_results": 0,
                    "selected_count": 0,
                    "avg_quality": 0,
                    "high_quality_rate": 0,
                    "max_score": 0,
                    "quality_stats": {},
                    "evaluation_summary": f"検索エラー: {str(e)}"
                }
            }
            return error_result
    
    # _format_resultsメソッドは削除（UI側で統一表示するため不要）
    # streamlit_app_integrated.pyで統一的に結果表示を行うため、
    # ここでの個別フォーマット処理は重複を避けるため削除
    
    def get_step_details(self, query: str) -> Dict[str, Any]:
        """各ステップの詳細情報を取得（デバッグ用・仕様書準拠）"""
        try:
            # Step1: フィルタ機能（UIで処理済み）
            step1_result = {"status": "ui_processed", "filters_applied": True}
            
            # Step2: ユーザー質問解析・抽出
            step2_keyword_result = self.extractor.extract_keywords(query)
            step2_datasource_result = self.judge.judge_datasource(step2_keyword_result)
            
            # Step3: CQL検索実行
            step3_result = self.search_engine.execute_search(step2_datasource_result, step2_keyword_result)
            
            # Step4: 品質評価・ランキング
            step4_result = self.evaluator.evaluate_and_rank(step3_result, step2_keyword_result, step2_datasource_result)
            
            return {
                "step1": step1_result,
                "step2_keyword": step2_keyword_result,
                "step2_datasource": step2_datasource_result,
                "step3": step3_result,
                "step4": step4_result
            }
            
        except Exception as e:
            logger.error(f"ステップ詳細取得エラー: {e}")
            return {"error": str(e)}


# LangChain Tool ラッパー（オプション）
try:
    from langchain.tools import BaseTool
    from pydantic import BaseModel, Field
    from typing import Type
    
    class HybridSearchInput(BaseModel):
        """ハイブリッド検索ツールの入力スキーマ"""
        query: str = Field(description="自然言語による検索クエリ")
    
    class LangChainHybridSearchTool(BaseTool):
        """LangChain互換ハイブリッド検索ツール"""
        
        name: str = "hybrid_search"
        description: str = "JiraとConfluenceを横断した高度なハイブリッド検索を実行します。"
        args_schema: Type[BaseModel] = HybridSearchInput
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.search_tool = HybridSearchTool()
        
        def _run(self, query: str, run_manager=None) -> str:
            return self.search_tool.search(query)
        
        async def _arun(self, query: str, run_manager=None) -> str:
            return self._run(query, run_manager)

except ImportError:
    LangChainHybridSearchTool = None


# 利便性のためのファクトリー関数
def create_hybrid_search_tool() -> HybridSearchTool:
    """ハイブリッド検索ツールのインスタンスを作成"""
    return HybridSearchTool()

def create_langchain_tool():
    """LangChain互換ツールを作成（利用可能な場合）"""
    if LangChainHybridSearchTool:
        return LangChainHybridSearchTool()
    else:
        return None

# スタンドアロン実行用
def standalone_search(query: str) -> str:
    """スタンドアロンでハイブリッド検索を実行"""
    tool = create_hybrid_search_tool()
    return tool.search(query)


if __name__ == "__main__":
    # テスト実行
    test_query = "ログイン機能のバグを調査したい"
    result = standalone_search(test_query)
    print("=" * 80)
    print("ハイブリッド検索ツール テスト（仕様書準拠版）")
    print("=" * 80)
    print(result) 