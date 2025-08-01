"""
仕様書作成支援ボット MVP - メインアプリケーション

仕様書準拠のハイブリッドアーキテクチャ実装:
- 主系路: 固定検索パイプライン (Step1-5)  
- 副系路: フォールバック検索Agent
- 集約系: 回答生成Agent

参照仕様書: SPEC-PL-001, SPEC-DS-001, SPEC-DS-002
"""

import logging
import streamlit as st
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 既存実装済みモジュール
from steps.step1_keyword_extraction import KeywordExtractor
from steps.step2_datasource_judgment import DataSourceJudge
from steps.step3_cql_search import CQLSearchEngine
from steps.step4_quality_evaluation import QualityEvaluator
from steps.step5_agent_handover import AgentHandoverManager
from config.settings import Settings
from utils.atlassian_api_client import AtlassianAPIClient

# 新規実装予定モジュール（Phase 2で実装）
try:
    from agents.response_generator import ResponseGenerationAgent
    from agents.fallback_searcher import FallbackSearchAgent
    from agents.agent_selector import AgentSelector
    AGENTS_AVAILABLE = True
except ImportError:
    # Phase 1段階ではAgent未実装のため、フォールバック処理
    AGENTS_AVAILABLE = False

logger = logging.getLogger(__name__)

# 品質評価しきい値（仕様書準拠）
HIGH_QUALITY_THRESHOLD = 0.75

class HybridSearchApplication:
    """
    ハイブリッド検索アプリケーション
    
    仕様書準拠のメイン制御フロー:
    1. 固定検索パイプライン実行 (主系路)
    2. 品質評価・結果判定
    3. Agent選択と実行（回答生成 or フォールバック）
    """
    
    def __init__(self):
        """アプリケーション初期化"""
        self.settings = Settings()
        self._init_components()
        
    def _init_components(self):
        """コンポーネント初期化"""
        try:
            # 固定パイプライン構成要素（Step1-5: 実装済み）
            self.keyword_extractor = KeywordExtractor()
            self.datasource_judge = DataSourceJudge()
            self.cql_search_engine = CQLSearchEngine()
            self.quality_evaluator = QualityEvaluator()
            self.agent_handover_manager = AgentHandoverManager()
            
            # Atlassian API クライアント
            self.api_client = AtlassianAPIClient(
                jira_url=self.settings.jira_url,
                jira_username=self.settings.jira_username,
                jira_token=self.settings.jira_api_token,
                confluence_url=self.settings.confluence_url,
                confluence_username=self.settings.confluence_username,
                confluence_token=self.settings.confluence_api_token
            )
            
            logger.info("✅ HybridSearchApplication初期化完了")
            
        except Exception as e:
            logger.error("❌ HybridSearchApplication初期化失敗: %s", str(e))
            raise
    
    def execute_hybrid_search(self, user_query: str, filters: Dict[str, Any]) -> str:
        """
        ハイブリッド検索メイン実行フロー
        
        Args:
            user_query: ユーザー入力クエリ
            filters: フィルター条件辞書
            
        Returns:
            最終的な回答文字列
        """
        try:
            # Phase 1: 固定検索パイプライン実行 (主系路 Step1-4)
            logger.info("🔍 固定検索パイプライン開始: クエリ='%s'", user_query)
            search_results, quality_score, pipeline_metadata = self._execute_fixed_pipeline(user_query, filters)
            
            # Phase 2: Agent連携実行 (Step5)
            return self.agent_handover_manager.execute_agent_handover(
                search_results=search_results,
                quality_score=quality_score,
                user_query=user_query,
                filters=filters,
                pipeline_metadata=pipeline_metadata
            )
                
        except Exception as e:
            logger.error("❌ ハイブリッド検索実行失敗: %s", str(e))
            return f"申し訳ございません。検索処理中にエラーが発生しました: {str(e)}"
    
    def _execute_fixed_pipeline(self, user_query: str, filters: Dict[str, Any]) -> Tuple[List[Dict], float, Dict[str, Any]]:
        """
        固定検索パイプライン実行 (Step1-4)
        
        Args:
            user_query: ユーザー入力クエリ
            filters: フィルター条件辞書
            
        Returns:
            Tuple[検索結果リスト, 品質スコア, パイプラインメタデータ]
        """
        # Step1: フィルタ機能（UIで処理済み）
        logger.info("⏭️ Step1: フィルタ機能（UI処理済み）")
        
        # Step2: キーワード抽出
        logger.info("🔍 Step2: キーワード抽出開始")
        keyword_result = self.keyword_extractor.extract_keywords(user_query)
        extracted_keywords = keyword_result.get('keywords', [])
        search_intent = keyword_result.get('intent', 'general')
        
        # Step3: データソース判定
        logger.info("📊 Step3: データソース判定開始")
        datasource_result = self.datasource_judge.judge_datasource(user_query, extracted_keywords)
        target_sources = datasource_result.get('target_sources', ['jira', 'confluence'])
        
        # Step4: CQL検索実行
        logger.info("⚡ Step4: CQL検索実行開始 - 対象: %s", target_sources)
        search_results = self.cql_search_engine.execute_search(
            keywords=extracted_keywords,
            target_sources=target_sources,
            filters=filters,
            search_intent=search_intent
        )
        
        # Step5: 品質評価・ランキング
        logger.info("📈 Step5: 品質評価・ランキング開始")
        quality_result = self.quality_evaluator.evaluate_and_rank(
            {"search_results": search_results}, 
            {"extracted_keywords": extracted_keywords}, 
            user_query
        )
        quality_score = quality_result.get("overall_quality_score", 0.0)
        
        logger.info("✅ 固定パイプライン完了: 結果数=%d, 品質スコア=%.2f", 
                   len(search_results), quality_score)
        
        # パイプライン実行メタデータ
        pipeline_metadata = {
            "extracted_keywords": extracted_keywords,
            "search_intent": search_intent,
            "target_sources": target_sources,
            "execution_timestamp": __import__("datetime").datetime.now().isoformat(),
            "filters_applied": filters
        }
        
        return search_results, quality_score, pipeline_metadata
    


def main():
    """
    Streamlitアプリケーションエントリーポイント
    """
    st.set_page_config(
        page_title="仕様書作成支援ボット MVP",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🤖 仕様書作成支援ボット MVP")
    st.caption("ハイブリッドアーキテクチャによる高精度検索システム")
    
    # セッション状態初期化
    if "hybrid_app" not in st.session_state:
        with st.spinner("システム初期化中..."):
            try:
                st.session_state.hybrid_app = HybridSearchApplication()
                st.success("✅ システム初期化完了")
            except Exception as e:
                st.error(f"❌ システム初期化失敗: {str(e)}")
                st.stop()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "filters" not in st.session_state:
        st.session_state.filters = {}
    
    # サイドバー: フィルター設定
    with st.sidebar:
        st.header("🎯 検索フィルター")
        
        # データソース選択
        st.subheader("📊 データソース")
        use_jira = st.checkbox("Jira", value=True)
        use_confluence = st.checkbox("Confluence", value=True)
        
        # 簡易フィルター（Phase 4で高度なフィルターUIに置き換え予定）
        st.subheader("🔍 基本フィルター")
        date_range = st.date_input("作成日範囲", value=None)
        
        # フィルター辞書更新
        st.session_state.filters = {
            "use_jira": use_jira,
            "use_confluence": use_confluence,
            "date_range": date_range
        }
        
        # 現在の実装状況表示
        st.subheader("🚧 実装状況")
        st.success("""
**Phase 1-2 (実装完了):**
✅ 固定検索パイプライン (Step1-4)
✅ Agent機能 (回答生成・フォールバック)
✅ ハイブリッド制御フロー (Step5)
✅ 品質評価システム
✅ 基本UI

**Phase 3-4 (次期開発):**
🔄 高度フィルターUI
🔄 プロセス可視化
🔄 UI独立性確保
""")
    
    # チャット履歴表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # ユーザー入力
    if prompt := st.chat_input("質問を入力してください（例：ログイン機能の仕様について教えて）"):
        # ユーザーメッセージ追加
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # ハイブリッド検索実行
        with st.chat_message("assistant"):
            with st.spinner("検索中..."):
                response = st.session_state.hybrid_app.execute_hybrid_search(
                    user_query=prompt,
                    filters=st.session_state.filters
                )
            st.markdown(response)
        
        # アシスタント応答追加
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main() 