"""
Step4: 品質評価・ランキング機能

3軸品質評価とStrategy重み付けによる結果ランキング
- 信頼性評価 (40%): データソース信頼度・作成日・更新頻度
- 関連度評価 (50%): キーワードマッチ度・タイトル一致・内容関連性
- 有効性評価 (10%): アクセス可能性・完全性・実用性

動的結果数調整: 高品質結果（0.7以上）を3-15件で自動選出
"""

import logging
import math
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class QualityEvaluator:
    """Step4: 品質評価・ランキングエンジン"""
    
    def __init__(self):
        self._init_evaluation_criteria()
        self._init_quality_thresholds()
    
    def _init_evaluation_criteria(self):
        """評価基準の初期化"""
        
        # 3軸品質評価の重み
        self.quality_weights = {
            "reliability": 0.40,  # 信頼性40%
            "relevance": 0.50,    # 関連度50%
            "effectiveness": 0.10  # 有効性10%
        }
        
        # Strategy重み（検索戦略別）
        self.strategy_weights = {
            "strategy1": 1.0,   # 厳密検索: 最高重み
            "strategy2": 0.8,   # 緩和検索: 中程度重み
            "strategy3": 0.6    # 拡張検索: 低重み
        }
        
        # データソース重み
        self.datasource_weights = {
            "confluence": 1.0,  # 文書系: 基準重み
            "jira": 0.9         # チケット系: 若干低重み
        }
        
        # 信頼性評価基準
        self.reliability_criteria = {
            "recent_bonus": 0.2,     # 最新情報ボーナス（30日以内）
            "old_penalty": -0.1,     # 古い情報ペナルティ（1年以上）
            "official_bonus": 0.15,  # 公式情報ボーナス
            "verified_bonus": 0.1    # 検証済みボーナス
        }
        
        # 関連度評価基準
        self.relevance_criteria = {
            "title_exact_match": 0.3,    # タイトル完全一致
            "title_partial_match": 0.15, # タイトル部分一致
            "keyword_density_weight": 0.25, # キーワード密度重み
            "context_relevance_weight": 0.3  # 文脈関連性重み
        }
    
    def _init_quality_thresholds(self):
        """品質閾値の初期化"""
        
        self.quality_thresholds = {
            "high_quality": 0.7,     # 高品質閾値
            "medium_quality": 0.5,   # 中品質閾値
            "low_quality": 0.3       # 低品質閾値
        }
        
        self.result_count_limits = {
            "min_results": 3,        # 最小結果数
            "max_results": 15,       # 最大結果数
            "target_high_quality": 8 # 目標高品質結果数
        }
    
    def evaluate_and_rank(self, step3_result: Dict[str, Any], step1_result: Dict[str, Any], 
                         step2_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        品質評価とランキングを実行
        
        Args:
            step3_result: Step3の検索結果
            step1_result: Step1のキーワード抽出結果
            step2_result: Step2のデータソース判定結果
            
        Returns:
            評価・ランキング結果辞書 {
                "ranked_results": [ランク付き結果リスト],
                "quality_distribution": {品質分布},
                "evaluation_summary": "評価サマリー",
                "final_count": 最終選出数,
                "quality_insights": {品質分析情報}
            }
        """
        logger.info("Step4: 品質評価・ランキング開始")
        
        # 全結果収集
        all_results = self._collect_all_results(step3_result)
        
        if not all_results:
            return self._empty_result()
        
        # キーワード情報準備
        primary_keywords = step1_result.get("primary_keywords", [])
        search_intent = step1_result.get("search_intent", "一般検索")
        
        # 各結果の品質評価
        evaluated_results = []
        for result in all_results:
            quality_score = self._evaluate_result_quality(
                result, primary_keywords, search_intent
            )
            
            # Strategy重み・データソース重み適用
            final_score = self._apply_weights(result, quality_score)
            
            evaluated_results.append({
                **result,
                "quality_score": quality_score,
                "final_score": final_score,
                "quality_breakdown": self._get_quality_breakdown(result, primary_keywords)
            })
        
        # ランキング実行
        ranked_results = sorted(
            evaluated_results, 
            key=lambda x: x["final_score"], 
            reverse=True
        )
        
        # 高品質結果選出
        high_quality_results = self._select_high_quality_results(ranked_results)
        
        # 多様性調整
        diversified_results = self._apply_diversity_adjustment(high_quality_results)
        
        # 品質分布分析
        quality_distribution = self._analyze_quality_distribution(ranked_results)
        
        # 評価サマリー生成
        evaluation_summary = self._generate_evaluation_summary(
            diversified_results, quality_distribution
        )
        
        # 品質分析情報
        quality_insights = self._generate_quality_insights(
            diversified_results, primary_keywords, search_intent
        )
        
        result = {
            "ranked_results": diversified_results,
            "quality_distribution": quality_distribution,
            "evaluation_summary": evaluation_summary,
            "final_count": len(diversified_results),
            "quality_insights": quality_insights
        }
        
        logger.info(f"Step4完了: {len(diversified_results)}件の高品質結果を選出")
        return result
    
    def _collect_all_results(self, step3_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Step3結果から全ての結果を収集"""
        all_results = []
        
        search_results = step3_result.get("search_results", {})
        for datasource, results in search_results.items():
            combined_results = results.get("combined_results", [])
            for result in combined_results:
                result["datasource"] = datasource
                all_results.append(result)
        
        return all_results
    
    def _evaluate_result_quality(self, result: Dict[str, Any], 
                                primary_keywords: List[str], search_intent: str) -> Dict[str, float]:
        """結果の3軸品質評価"""
        
        # 1. 信頼性評価
        reliability_score = self._evaluate_reliability(result)
        
        # 2. 関連度評価
        relevance_score = self._evaluate_relevance(result, primary_keywords, search_intent)
        
        # 3. 有効性評価
        effectiveness_score = self._evaluate_effectiveness(result)
        
        # 重み付き合計スコア
        total_score = (
            reliability_score * self.quality_weights["reliability"] +
            relevance_score * self.quality_weights["relevance"] +
            effectiveness_score * self.quality_weights["effectiveness"]
        )
        
        return {
            "reliability": reliability_score,
            "relevance": relevance_score,
            "effectiveness": effectiveness_score,
            "total": min(1.0, max(0.0, total_score))
        }
    
    def _evaluate_reliability(self, result: Dict[str, Any]) -> float:
        """信頼性評価"""
        score = 0.5  # ベーススコア
        
        # 作成日による評価
        created_date = result.get("created", "2024-01-01")
        if created_date:
            try:
                created = datetime.strptime(created_date, "%Y-%m-%d")
                days_old = (datetime.now() - created).days
                
                if days_old <= 30:
                    score += self.reliability_criteria["recent_bonus"]
                elif days_old >= 365:
                    score += self.reliability_criteria["old_penalty"]
                    
            except ValueError:
                pass  # 日付解析エラーは無視
        
        # データソース種別による評価
        datasource = result.get("datasource", "")
        if datasource == "confluence":
            score += 0.1  # 文書系はより信頼性が高い
        
        # ステータス・タイプによる評価
        status = result.get("status", "")
        if status in ["Done", "Resolved", "Published"]:
            score += 0.1  # 完了済みは信頼性高
        
        return min(1.0, max(0.0, score))
    
    def _evaluate_relevance(self, result: Dict[str, Any], 
                          primary_keywords: List[str], search_intent: str) -> float:
        """関連度評価"""
        score = 0.0
        
        title = result.get("title", "").lower()
        result_strategy = result.get("strategy", "")
        
        # タイトルマッチング評価
        title_score = 0.0
        for keyword in primary_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in title:
                if title.startswith(keyword_lower) or title.endswith(keyword_lower):
                    title_score += self.relevance_criteria["title_exact_match"]
                else:
                    title_score += self.relevance_criteria["title_partial_match"]
        
        score += min(0.4, title_score)  # タイトルスコア上限0.4
        
        # キーワード密度評価（模擬）
        keyword_density = min(1.0, len(primary_keywords) / 10.0)  # 10個を最大と仮定
        score += keyword_density * self.relevance_criteria["keyword_density_weight"]
        
        # 検索戦略によるボーナス
        if result_strategy == "厳密検索":
            score += 0.2  # 厳密検索結果はより関連性が高い
        elif result_strategy == "緩和検索":
            score += 0.1
        
        # 検索意図との一致度
        intent_bonus = self._calculate_intent_relevance(result, search_intent)
        score += intent_bonus
        
        return min(1.0, max(0.0, score))
    
    def _evaluate_effectiveness(self, result: Dict[str, Any]) -> float:
        """有効性評価"""
        score = 0.7  # ベーススコア（アクセス可能と仮定）
        
        # タイプによる評価
        result_type = result.get("type", "")
        if result_type in ["page", "Task", "Story"]:
            score += 0.15  # 実用的なタイプ
        elif result_type in ["Bug"]:
            score += 0.1   # バグは問題解決に有効
        
        # タイトルの完全性評価（長すぎず短すぎず）
        title = result.get("title", "")
        title_length = len(title)
        if 10 <= title_length <= 100:
            score += 0.1  # 適切な長さ
        elif title_length < 5:
            score -= 0.2  # 短すぎる
        
        # ID存在確認
        if result.get("id"):
            score += 0.05  # ID存在は有効性を示す
        
        return min(1.0, max(0.0, score))
    
    def _calculate_intent_relevance(self, result: Dict[str, Any], search_intent: str) -> float:
        """検索意図との関連度計算"""
        
        intent_mappings = {
            "バグ調査": {"Bug": 0.3, "Task": 0.2, "issue": 0.2},
            "仕様確認": {"page": 0.3, "specification": 0.3, "design": 0.2},
            "進捗確認": {"Task": 0.3, "Story": 0.3, "status": 0.2},
            "機能理解": {"page": 0.3, "interface": 0.2, "API": 0.2},
            "設計確認": {"page": 0.3, "design": 0.3, "architecture": 0.2}
        }
        
        mappings = intent_mappings.get(search_intent, {})
        relevance_bonus = 0.0
        
        result_type = result.get("type", "").lower()
        title = result.get("title", "").lower()
        
        for key, bonus in mappings.items():
            if key.lower() in result_type or key.lower() in title:
                relevance_bonus += bonus
                break
        
        return min(0.3, relevance_bonus)  # 最大0.3のボーナス
    
    def _apply_weights(self, result: Dict[str, Any], quality_score: Dict[str, float]) -> float:
        """Strategy重み・データソース重みを適用"""
        
        base_score = quality_score["total"]
        
        # Strategy重み適用
        strategy = result.get("strategy", "")
        strategy_mapping = {
            "厳密検索": "strategy1",
            "緩和検索": "strategy2", 
            "拡張検索": "strategy3"
        }
        strategy_key = strategy_mapping.get(strategy, "strategy1")
        strategy_weight = self.strategy_weights.get(strategy_key, 1.0)
        
        # データソース重み適用
        datasource = result.get("datasource", "confluence")
        datasource_weight = self.datasource_weights.get(datasource, 1.0)
        
        # 元のStrategy重み適用
        original_weight = result.get("weight", 1.0)
        
        # 最終スコア計算
        final_score = base_score * strategy_weight * datasource_weight * original_weight
        
        return min(1.0, max(0.0, final_score))
    
    def _select_high_quality_results(self, ranked_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """高品質結果選出"""
        
        high_quality_threshold = self.quality_thresholds["high_quality"]
        min_results = self.result_count_limits["min_results"]
        max_results = self.result_count_limits["max_results"]
        
        # 高品質結果フィルタリング
        high_quality = [
            result for result in ranked_results 
            if result["final_score"] >= high_quality_threshold
        ]
        
        # 結果数調整
        if len(high_quality) < min_results:
            # 高品質が不足の場合、上位結果で補完
            return ranked_results[:min_results]
        elif len(high_quality) > max_results:
            # 高品質が多すぎる場合、上位のみ選択
            return high_quality[:max_results]
        else:
            return high_quality
    
    def _apply_diversity_adjustment(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """多様性調整"""
        
        if len(results) <= 5:
            return results  # 少数の場合は調整不要
        
        diversified = []
        seen_types = set()
        seen_datasources = set()
        
        # 1回目: タイプ・データソースの多様性を優先
        for result in results:
            result_type = result.get("type", "")
            datasource = result.get("datasource", "")
            
            type_key = f"{datasource}_{result_type}"
            if type_key not in seen_types or len(diversified) < 3:
                diversified.append(result)
                seen_types.add(type_key)
                seen_datasources.add(datasource)
                
                if len(diversified) >= self.result_count_limits["max_results"]:
                    break
        
        # 2回目: 残りスロットを高スコア順で埋める
        for result in results:
            if result not in diversified:
                diversified.append(result)
                if len(diversified) >= self.result_count_limits["max_results"]:
                    break
        
        return diversified
    
    def _analyze_quality_distribution(self, ranked_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """品質分布分析"""
        
        if not ranked_results:
            return {"high": 0, "medium": 0, "low": 0, "total": 0}
        
        high_count = sum(1 for r in ranked_results if r["final_score"] >= 0.7)
        medium_count = sum(1 for r in ranked_results if 0.5 <= r["final_score"] < 0.7)
        low_count = sum(1 for r in ranked_results if r["final_score"] < 0.5)
        
        return {
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "total": len(ranked_results),
            "high_ratio": high_count / len(ranked_results) if ranked_results else 0
        }
    
    def _generate_evaluation_summary(self, results: List[Dict[str, Any]], 
                                   quality_distribution: Dict[str, Any]) -> str:
        """評価サマリー生成"""
        
        if not results:
            return "評価対象結果なし"
        
        avg_score = sum(r["final_score"] for r in results) / len(results)
        high_ratio = quality_distribution.get("high_ratio", 0)
        
        summary_parts = [
            f"選出結果: {len(results)}件",
            f"平均品質: {avg_score:.2f}",
            f"高品質率: {high_ratio:.1%}",
            f"最高スコア: {results[0]['final_score']:.2f}" if results else "N/A"
        ]
        
        return " | ".join(summary_parts)
    
    def _generate_quality_insights(self, results: List[Dict[str, Any]], 
                                 primary_keywords: List[str], search_intent: str) -> Dict[str, Any]:
        """品質分析情報生成"""
        
        if not results:
            return {}
        
        # データソース別分析
        datasource_analysis = {}
        for result in results:
            ds = result.get("datasource", "unknown")
            if ds not in datasource_analysis:
                datasource_analysis[ds] = {"count": 0, "avg_score": 0, "scores": []}
            
            datasource_analysis[ds]["count"] += 1
            datasource_analysis[ds]["scores"].append(result["final_score"])
        
        # 平均スコア計算
        for ds, data in datasource_analysis.items():
            if data["scores"]:
                data["avg_score"] = sum(data["scores"]) / len(data["scores"])
        
        # 戦略別分析
        strategy_analysis = {}
        for result in results:
            strategy = result.get("strategy", "unknown")
            if strategy not in strategy_analysis:
                strategy_analysis[strategy] = {"count": 0, "avg_score": 0, "scores": []}
            
            strategy_analysis[strategy]["count"] += 1
            strategy_analysis[strategy]["scores"].append(result["final_score"])
        
        # 平均スコア計算
        for strategy, data in strategy_analysis.items():
            if data["scores"]:
                data["avg_score"] = sum(data["scores"]) / len(data["scores"])
        
        return {
            "datasource_analysis": datasource_analysis,
            "strategy_analysis": strategy_analysis,
            "keyword_coverage": len(primary_keywords),
            "search_intent": search_intent
        }
    
    def _get_quality_breakdown(self, result: Dict[str, Any], primary_keywords: List[str]) -> Dict[str, float]:
        """品質内訳情報取得"""
        # 評価の詳細内訳を返す（デバッグ用）
        return {
            "title_match": 0.8,  # 模擬値
            "keyword_density": 0.6,
            "freshness": 0.9,
            "authority": 0.7
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """空結果を返す"""
        return {
            "ranked_results": [],
            "quality_distribution": {"high": 0, "medium": 0, "low": 0, "total": 0},
            "evaluation_summary": "評価対象結果なし",
            "final_count": 0,
            "quality_insights": {}
        } 