"""
Agent選択ロジック

品質評価結果に基づいて、適切なAgentを選択する制御ロジック。
仕様書準拠のハイブリッドアーキテクチャの中核部分。

参照仕様書: SPEC-DS-001 4.3. メインアプリケーション設計
"""

import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

# 品質評価しきい値（仕様書準拠）
HIGH_QUALITY_THRESHOLD = 0.75
MEDIUM_QUALITY_THRESHOLD = 0.5

class AgentSelector:
    """
    Agent選択ロジック
    
    固定検索パイプラインの結果を評価し、次に実行すべきAgentを選択する。
    - 高品質結果: 回答生成Agent
    - 低品質結果: フォールバック検索Agent → 回答生成Agent
    """
    
    def __init__(self):
        """AgentSelector初期化"""
        self.selection_history = []  # 選択履歴（分析用）
        logger.info("✅ AgentSelector初期化完了")
    
    def select_agent_strategy(self, 
                            search_results: List[Dict], 
                            quality_score: float,
                            user_query: str,
                            filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        検索結果の品質に基づいてAgent戦略を選択
        
        Args:
            search_results: 固定パイプライン検索結果
            quality_score: 品質評価スコア
            user_query: ユーザー質問
            filters: フィルター条件
            
        Returns:
            Tuple[選択戦略, 戦略パラメータ]
        """
        # 選択基準の評価
        decision_factors = self._analyze_decision_factors(
            search_results, quality_score, user_query, filters
        )
        
        # 戦略選択
        strategy, params = self._decide_strategy(decision_factors)
        
        # 選択履歴記録
        self._record_selection(strategy, decision_factors, params)
        
        logger.info("🎯 Agent戦略選択: %s (品質スコア=%.2f)", strategy, quality_score)
        return strategy, params
    
    def _analyze_decision_factors(self,
                                search_results: List[Dict],
                                quality_score: float, 
                                user_query: str,
                                filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agent選択の判断要素を分析
        
        Args:
            search_results: 検索結果
            quality_score: 品質スコア
            user_query: ユーザー質問
            filters: フィルター条件
            
        Returns:
            判断要素辞書
        """
        factors = {
            # 基本品質評価
            "quality_score": quality_score,
            "result_count": len(search_results),
            
            # 品質分類
            "is_high_quality": quality_score >= HIGH_QUALITY_THRESHOLD,
            "is_medium_quality": MEDIUM_QUALITY_THRESHOLD <= quality_score < HIGH_QUALITY_THRESHOLD,
            "is_low_quality": quality_score < MEDIUM_QUALITY_THRESHOLD,
            
            # 結果内容分析
            "has_results": len(search_results) > 0,
            "result_diversity": self._calculate_result_diversity(search_results),
            "avg_relevance": self._calculate_avg_relevance(search_results),
            
            # クエリ特性分析
            "query_length": len(user_query),
            "query_complexity": self._estimate_query_complexity(user_query),
            "has_specific_filters": self._has_specific_filters(filters),
            
            # 文脈要素
            "query_type": self._classify_query_type(user_query),
            "expected_answer_type": self._estimate_answer_type(user_query)
        }
        
        return factors
    
    def _decide_strategy(self, factors: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        判断要素に基づいて最適戦略を決定
        
        Args:
            factors: 判断要素辞書
            
        Returns:
            Tuple[戦略名, 戦略パラメータ]
        """
        # 戦略決定ロジック
        if factors["is_high_quality"] and factors["has_results"]:
            # 高品質結果 → 直接回答生成
            return "direct_response_generation", {
                "confidence": "high",
                "use_fallback": False,
                "response_style": "comprehensive",
                "quality_context": factors
            }
        
        elif factors["is_medium_quality"] and factors["result_count"] >= 2:
            # 中品質結果 → 結果改善後に回答生成
            return "enhanced_response_generation", {
                "confidence": "medium", 
                "use_fallback": False,
                "response_style": "cautious",
                "enhancement_needed": True,
                "quality_context": factors
            }
        
        elif factors["is_low_quality"] or not factors["has_results"]:
            # 低品質/結果なし → フォールバック検索
            return "fallback_then_response", {
                "confidence": "low",
                "use_fallback": True,
                "fallback_strategy": self._select_fallback_strategy(factors),
                "response_style": "exploratory",
                "quality_context": factors
            }
        
        else:
            # デフォルト: 保守的アプローチ
            return "conservative_response", {
                "confidence": "unknown",
                "use_fallback": True,
                "response_style": "minimal",
                "quality_context": factors
            }
    
    def _select_fallback_strategy(self, factors: Dict[str, Any]) -> str:
        """
        フォールバック戦略の詳細選択
        
        Args:
            factors: 判断要素辞書
            
        Returns:
            フォールバック戦略名
        """
        if factors["query_complexity"] == "high":
            return "creative_search"  # 創造的検索
        elif factors["query_type"] == "specific":
            return "targeted_search"  # 標的型検索
        elif not factors["has_results"]:
            return "expansive_search"  # 拡張検索
        else:
            return "standard_search"  # 標準検索
    
    def _calculate_result_diversity(self, search_results: List[Dict]) -> float:
        """
        検索結果の多様性を計算
        
        Args:
            search_results: 検索結果
            
        Returns:
            多様性スコア (0.0-1.0)
        """
        if not search_results:
            return 0.0
        
        # ソースの多様性
        sources = set(result.get('source', '') for result in search_results)
        source_diversity = len(sources) / max(len(search_results), 1)
        
        # 単純化した多様性指標
        return min(source_diversity, 1.0)
    
    def _calculate_avg_relevance(self, search_results: List[Dict]) -> float:
        """
        平均関連度を計算
        
        Args:
            search_results: 検索結果
            
        Returns:
            平均関連度スコア
        """
        if not search_results:
            return 0.0
        
        relevance_scores = [
            result.get('relevance_score', 0.0) 
            for result in search_results
        ]
        
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    
    def _estimate_query_complexity(self, user_query: str) -> str:
        """
        クエリの複雑さを推定
        
        Args:
            user_query: ユーザー質問
            
        Returns:
            複雑さレベル (low/medium/high)
        """
        query_length = len(user_query)
        
        # 複雑さ指標
        complexity_indicators = [
            "どのように" in user_query,
            "なぜ" in user_query, 
            "比較" in user_query,
            "違い" in user_query,
            "関係" in user_query,
            "AND" in user_query.upper() or "OR" in user_query.upper()
        ]
        
        complexity_score = sum(complexity_indicators)
        
        if query_length > 50 or complexity_score >= 3:
            return "high"
        elif query_length > 20 or complexity_score >= 1:
            return "medium"
        else:
            return "low"
    
    def _has_specific_filters(self, filters: Dict[str, Any]) -> bool:
        """
        具体的なフィルターが設定されているかチェック
        
        Args:
            filters: フィルター条件
            
        Returns:
            具体的フィルター設定の有無
        """
        # None, 空文字, False以外の値を持つフィルターをカウント
        active_filters = [
            k for k, v in filters.items() 
            if v and v != "" and v is not False
        ]
        
        return len(active_filters) > 2  # 基本データソース選択以外のフィルター
    
    def _classify_query_type(self, user_query: str) -> str:
        """
        質問タイプを分類
        
        Args:
            user_query: ユーザー質問
            
        Returns:
            質問タイプ (specific/general/procedural/troubleshooting)
        """
        if any(word in user_query for word in ["エラー", "問題", "不具合", "うまくいかない"]):
            return "troubleshooting"
        elif any(word in user_query for word in ["手順", "方法", "やり方", "どうやって"]):
            return "procedural"
        elif any(word in user_query for word in ["仕様", "詳細", "具体的", "正確"]):
            return "specific"
        else:
            return "general"
    
    def _estimate_answer_type(self, user_query: str) -> str:
        """
        期待される回答タイプを推定
        
        Args:
            user_query: ユーザー質問
            
        Returns:
            回答タイプ (factual/explanatory/procedural/comparative)
        """
        if "?" in user_query or any(word in user_query for word in ["何", "いつ", "どこ", "誰"]):
            return "factual"
        elif any(word in user_query for word in ["なぜ", "理由", "背景"]):
            return "explanatory"
        elif any(word in user_query for word in ["手順", "ステップ", "方法"]):
            return "procedural"
        elif any(word in user_query for word in ["比較", "違い", "差"]):
            return "comparative"
        else:
            return "general"
    
    def _record_selection(self, strategy: str, factors: Dict[str, Any], params: Dict[str, Any]):
        """
        選択履歴を記録（分析・改善用）
        
        Args:
            strategy: 選択された戦略
            factors: 判断要素
            params: 戦略パラメータ
        """
        selection_record = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "strategy": strategy,
            "quality_score": factors.get("quality_score", 0.0),
            "result_count": factors.get("result_count", 0),
            "confidence": params.get("confidence", "unknown"),
            "factors": factors
        }
        
        self.selection_history.append(selection_record)
        
        # 履歴サイズ制限（メモリ管理）
        if len(self.selection_history) > 100:
            self.selection_history = self.selection_history[-50:]  # 最新50件を保持
    
    def get_selection_statistics(self) -> Dict[str, Any]:
        """
        選択統計情報を取得
        
        Returns:
            選択統計辞書
        """
        if not self.selection_history:
            return {"message": "選択履歴なし"}
        
        strategies = [record["strategy"] for record in self.selection_history]
        confidences = [record["confidence"] for record in self.selection_history]
        
        return {
            "total_selections": len(self.selection_history),
            "strategy_distribution": {
                strategy: strategies.count(strategy) 
                for strategy in set(strategies)
            },
            "confidence_distribution": {
                confidence: confidences.count(confidence)
                for confidence in set(confidences)
            },
            "avg_quality_score": sum(
                record["quality_score"] for record in self.selection_history
            ) / len(self.selection_history)
        } 