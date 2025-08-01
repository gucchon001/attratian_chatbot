"""
Step5: Agent連携機能

仕様書定義 (SPEC-DS-002 2.6):
- 固定検索パイプライン（Step1-4）の結果を評価
- 品質に応じて適切なAgentに処理を委譲
- ハイブリッドアーキテクチャの橋渡し役
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Agent機能（Phase 2で実装済み）
try:
    from ..agents.response_generator import ResponseGenerationAgent
from ..agents.fallback_searcher import FallbackSearchAgent
from ..agents.agent_selector import AgentSelector
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

logger = logging.getLogger(__name__)

class AgentHandoverManager:
    """
    Agent連携マネージャー
    
    固定検索パイプライン（Step1-4）から各種Agentへの
    スムーズな処理引き継ぎを管理する。
    """
    
    def __init__(self):
        """初期化"""
        self.handover_history = []  # 連携履歴
        self._init_agents()
        logger.info("✅ AgentHandoverManager初期化完了")
    
    def _init_agents(self):
        """Agent初期化"""
        if AGENTS_AVAILABLE:
            try:
                self.response_generator = ResponseGenerationAgent()
                self.fallback_searcher = FallbackSearchAgent()
                self.agent_selector = AgentSelector()
                logger.info("✅ 全Agent初期化完了")
            except Exception as e:
                logger.error("❌ Agent初期化失敗: %s", str(e))
                self.response_generator = None
                self.fallback_searcher = None
                self.agent_selector = None
        else:
            logger.warning("⚠️ Agent機能利用不可 - フォールバック処理で継続")
            self.response_generator = None
            self.fallback_searcher = None
            self.agent_selector = None
    
    def execute_agent_handover(self,
                              search_results: List[Dict],
                              quality_score: float,
                              user_query: str,
                              filters: Dict[str, Any],
                              pipeline_metadata: Dict[str, Any]) -> str:
        """
        Agent連携実行
        
        Args:
            search_results: Step4までの検索結果
            quality_score: 品質評価スコア
            user_query: ユーザー質問
            filters: フィルター条件
            pipeline_metadata: パイプライン実行メタデータ
            
        Returns:
            最終回答文字列
        """
        try:
            logger.info("🔗 Agent連携開始: 品質スコア=%.2f", quality_score)
            
            # Agent連携可能性チェック
            if not self._validate_agent_availability():
                return self._generate_non_agent_response(search_results, user_query)
            
            # Agent戦略選択
            strategy, strategy_params = self.agent_selector.select_agent_strategy(
                search_results, quality_score, user_query, filters
            )
            
            # 戦略に基づく実行
            response = self._execute_strategy(
                strategy, strategy_params, search_results, user_query, filters
            )
            
            # 連携履歴記録
            self._record_handover(strategy, quality_score, response, pipeline_metadata)
            
            logger.info("✅ Agent連携完了: 戦略=%s", strategy)
            return response
            
        except Exception as e:
            logger.error("❌ Agent連携失敗: %s", str(e))
            return self._generate_error_response(user_query, str(e))
    
    def _validate_agent_availability(self) -> bool:
        """Agent利用可能性検証"""
        if not AGENTS_AVAILABLE:
            logger.warning("⚠️ Agent機能無効: LangChain未インストール")
            return False
        
        if not all([self.response_generator, self.fallback_searcher, self.agent_selector]):
            logger.warning("⚠️ Agent初期化不完全")
            return False
        
        return True
    
    def _execute_strategy(self,
                         strategy: str,
                         strategy_params: Dict[str, Any],
                         search_results: List[Dict],
                         user_query: str,
                         filters: Dict[str, Any]) -> str:
        """
        選択された戦略を実行
        
        Args:
            strategy: 選択戦略名
            strategy_params: 戦略パラメータ
            search_results: 検索結果
            user_query: ユーザー質問
            filters: フィルター条件
            
        Returns:
            実行結果（最終回答）
        """
        logger.info("🎯 戦略実行: %s", strategy)
        
        if strategy == "direct_response_generation":
            # 高品質結果 → 直接回答生成
            return self._execute_direct_response(search_results, user_query, strategy_params)
        
        elif strategy == "enhanced_response_generation":
            # 中品質結果 → 強化回答生成
            return self._execute_enhanced_response(search_results, user_query, strategy_params)
        
        elif strategy == "fallback_then_response":
            # 低品質結果 → フォールバック検索 → 回答生成
            return self._execute_fallback_flow(search_results, user_query, filters, strategy_params)
        
        elif strategy == "conservative_response":
            # 保守的アプローチ
            return self._execute_conservative_response(search_results, user_query, strategy_params)
        
        else:
            logger.warning("⚠️ 未知の戦略: %s", strategy)
            return self._execute_direct_response(search_results, user_query, strategy_params)
    
    def _execute_direct_response(self,
                               search_results: List[Dict],
                               user_query: str,
                               strategy_params: Dict[str, Any]) -> str:
        """直接回答生成実行"""
        logger.info("💡 直接回答生成実行")
        
        try:
            response = self.response_generator.generate_response(search_results, user_query)
            
            # 高品質の場合は信頼度情報を付加
            if strategy_params.get("confidence") == "high":
                response += "\n\n---\n**信頼度**: 高 - 検索結果の品質が高く、包括的な回答を提供できました。"
            
            return response
            
        except Exception as e:
            logger.error("❌ 直接回答生成失敗: %s", str(e))
            return self._generate_agent_error_response(user_query, "直接回答生成", str(e))
    
    def _execute_enhanced_response(self,
                                 search_results: List[Dict],
                                 user_query: str,
                                 strategy_params: Dict[str, Any]) -> str:
        """強化回答生成実行"""
        logger.info("🔧 強化回答生成実行")
        
        try:
            # 検索結果の品質向上処理（簡易実装）
            enhanced_results = self._enhance_search_results(search_results)
            
            response = self.response_generator.generate_response(enhanced_results, user_query)
            
            # 中品質の注意事項を付加
            response += "\n\n---\n**注意**: 検索結果の品質が中程度のため、より詳細な情報が必要な場合は追加の質問をお願いします。"
            
            return response
            
        except Exception as e:
            logger.error("❌ 強化回答生成失敗: %s", str(e))
            return self._execute_direct_response(search_results, user_query, strategy_params)
    
    def _execute_fallback_flow(self,
                             search_results: List[Dict],
                             user_query: str,
                             filters: Dict[str, Any],
                             strategy_params: Dict[str, Any]) -> str:
        """フォールバック検索 → 回答生成フロー実行"""
        logger.info("🔄 フォールバック検索フロー実行")
        
        try:
            # フォールバック検索実行
            fallback_results = self.fallback_searcher.execute_fallback_search(user_query, filters)
            
            # 元の結果と統合
            combined_results = self._combine_search_results(search_results, fallback_results)
            
            # 統合結果で回答生成
            response = self.response_generator.generate_response(combined_results, user_query)
            
            # フォールバック実行の説明を付加
            response += f"\n\n---\n**検索方法**: 拡張検索を実行しました。通常検索で十分な結果が得られなかったため、より幅広い検索アプローチを適用しています。"
            
            return response
            
        except Exception as e:
            logger.error("❌ フォールバック検索フロー失敗: %s", str(e))
            return self._execute_direct_response(search_results, user_query, strategy_params)
    
    def _execute_conservative_response(self,
                                     search_results: List[Dict],
                                     user_query: str,
                                     strategy_params: Dict[str, Any]) -> str:
        """保守的回答生成実行"""
        logger.info("🛡️ 保守的回答生成実行")
        
        try:
            response = self.response_generator.generate_response(search_results, user_query)
            
            # 保守的な注意事項を付加
            response += "\n\n---\n**注意**: 検索結果の品質が不明確なため、より確実な情報が必要な場合は検索条件を変更してお試しください。"
            
            return response
            
        except Exception as e:
            logger.error("❌ 保守的回答生成失敗: %s", str(e))
            return self._generate_agent_error_response(user_query, "保守的回答生成", str(e))
    
    def _enhance_search_results(self, search_results: List[Dict]) -> List[Dict]:
        """検索結果の品質向上処理"""
        if not search_results:
            return search_results
        
        # 関連度スコアによるソート
        enhanced_results = sorted(
            search_results,
            key=lambda x: x.get('relevance_score', 0.0),
            reverse=True
        )
        
        # 上位結果のみ保持（品質重視）
        return enhanced_results[:3]
    
    def _combine_search_results(self,
                              original_results: List[Dict],
                              fallback_results: List[Dict]) -> List[Dict]:
        """検索結果の統合"""
        combined = original_results.copy()
        
        # 重複除去しつつフォールバック結果を追加
        for fallback_result in fallback_results:
            if not self._is_duplicate_result(fallback_result, combined):
                combined.append(fallback_result)
        
        # 関連度スコアでソート
        return sorted(combined, key=lambda x: x.get('relevance_score', 0.0), reverse=True)
    
    def _is_duplicate_result(self, result: Dict, existing_results: List[Dict]) -> bool:
        """重複結果チェック"""
        result_title = result.get('title', '').lower()
        result_url = result.get('url', '')
        
        for existing in existing_results:
            if (result_title and result_title == existing.get('title', '').lower()) or \
               (result_url and result_url == existing.get('url', '')):
                return True
        
        return False
    
    def _generate_non_agent_response(self, search_results: List[Dict], user_query: str) -> str:
        """Agent非利用時の回答生成"""
        logger.info("📝 非Agent回答生成")
        
        if not search_results:
            return f"""
申し訳ございません。「{user_query}」に関する情報が見つかりませんでした。

**検索のヒント:**
- より具体的なキーワードをお試しください
- フィルター条件を調整してみてください
- 類義語や関連用語での検索もお試しください

何かご不明な点がございましたら、お気軽にお尋ねください。
"""
        
        # 簡易的な結果要約
        result_summary = []
        for i, result in enumerate(search_results[:3], 1):
            source = result.get('source', 'Unknown')
            title = result.get('title', 'タイトルなし')
            summary = result.get('summary', '')[:150] + '...' if result.get('summary') else ''
            
            result_summary.append(f"""
**{i}. [{source}] {title}**
{summary}
""")
        
        return f"""
「{user_query}」に関する検索結果をお示しします：

{''.join(result_summary)}

---
**注意**: 現在は簡易表示モードです。より詳細な分析機能を利用するには、LangChain環境の設定が必要です。
"""
    
    def _generate_error_response(self, user_query: str, error_message: str) -> str:
        """エラー時の応答生成"""
        return f"""
申し訳ございません。「{user_query}」の処理中にエラーが発生しました。

**エラー詳細**: {error_message}

**対処方法**:
1. しばらく時間をおいてから再度お試しください
2. より簡潔なキーワードで質問を言い換えてみてください
3. フィルター条件をリセットしてお試しください

問題が継続する場合は、システム管理者にお問い合わせください。
"""
    
    def _generate_agent_error_response(self, user_query: str, agent_type: str, error_message: str) -> str:
        """Agent実行エラー時の応答生成"""
        return f"""
申し訳ございません。{agent_type}の実行中にエラーが発生しました。

**質問**: {user_query}
**エラー**: {error_message}

**代替手段**:
- 基本検索機能は継続して利用可能です
- より単純な質問に分割してお試しください
- システム復旧後に再度お試しください

ご不便をおかけして申し訳ございません。
"""
    
    def _record_handover(self,
                        strategy: str,
                        quality_score: float,
                        response: str,
                        pipeline_metadata: Dict[str, Any]):
        """連携履歴記録"""
        handover_record = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "strategy": strategy,
            "quality_score": quality_score,
            "response_length": len(response),
            "pipeline_metadata": pipeline_metadata
        }
        
        self.handover_history.append(handover_record)
        
        # 履歴サイズ制限
        if len(self.handover_history) > 50:
            self.handover_history = self.handover_history[-25:]
    
    def get_handover_statistics(self) -> Dict[str, Any]:
        """連携統計情報取得"""
        if not self.handover_history:
            return {"message": "連携履歴なし"}
        
        strategies = [record["strategy"] for record in self.handover_history]
        
        return {
            "total_handovers": len(self.handover_history),
            "strategy_distribution": {
                strategy: strategies.count(strategy)
                for strategy in set(strategies)
            },
            "avg_quality_score": sum(
                record["quality_score"] for record in self.handover_history
            ) / len(self.handover_history),
            "avg_response_length": sum(
                record["response_length"] for record in self.handover_history
            ) / len(self.handover_history)
        } 