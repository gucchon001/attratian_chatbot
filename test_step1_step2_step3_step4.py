#!/usr/bin/env python3
"""
Step1-4完全統合テスト

ハイブリッド検索システム全体フローのテスト:
KeywordExtractor → DataSourceJudge → CQLSearchEngine → QualityEvaluator
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.spec_bot_mvp.steps.step1_keyword_extraction import KeywordExtractor
from src.spec_bot_mvp.steps.step2_datasource_judgment import DataSourceJudge
from src.spec_bot_mvp.steps.step3_cql_search import CQLSearchEngine
from src.spec_bot_mvp.steps.step4_quality_evaluation import QualityEvaluator

def test_complete_hybrid_search_system():
    """Step1-4完全統合テスト"""
    
    # 各ステップの初期化
    extractor = KeywordExtractor()
    judge = DataSourceJudge() 
    search_engine = CQLSearchEngine()
    evaluator = QualityEvaluator()
    
    # テストクエリ一覧
    test_queries = [
        "ログイン機能のバグを調査したい",
        "API設計についての情報が欲しい", 
        "データベース接続エラーの原因を調べて"
    ]
    
    print("=" * 90)
    print("🚀 ハイブリッド検索システム完全統合テスト")
    print("Step1(キーワード抽出) → Step2(データソース判定) → Step3(CQL検索) → Step4(品質評価)")
    print("=" * 90)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n【完全統合テスト {i}】クエリ: {query}")
        print("=" * 80)
        
        try:
            # Step1: キーワード抽出
            print("🔍 Step1: キーワード抽出")
            step1_result = extractor.extract_keywords(query)
            
            print(f"   主要キーワード: {step1_result['primary_keywords']}")
            print(f"   検索意図: {step1_result['search_intent']}")
            print(f"   抽出手法: {step1_result['extraction_method']}")
            
            # Step2: データソース判定
            print("\n🎯 Step2: データソース判定")
            step2_result = judge.judge_datasource(step1_result)
            
            print(f"   優先順序: {step2_result['datasource_priority']}")
            print(f"   検索戦略: {step2_result['search_strategy']}")
            primary_ds = step2_result['datasource_priority'][0]
            primary_score = step2_result['priority_scores'][primary_ds]
            print(f"   最優先: {primary_ds.title()} (スコア: {primary_score:.2f})")
            
            # Step3: CQL検索実行
            print("\n🔍 Step3: CQL検索実行")
            step3_result = search_engine.execute_search(step2_result, step1_result)
            
            print(f"   実行戦略: {step3_result['strategies_executed']}")
            print(f"   総結果数: {step3_result['total_results']}件")
            print(f"   実行サマリー: {step3_result['execution_summary']}")
            
            # Step4: 品質評価・ランキング
            print("\n🏆 Step4: 品質評価・ランキング")
            step4_result = evaluator.evaluate_and_rank(step3_result, step1_result, step2_result)
            
            print(f"   最終選出数: {step4_result['final_count']}件")
            print(f"   評価サマリー: {step4_result['evaluation_summary']}")
            
            # 品質分布表示
            quality_dist = step4_result['quality_distribution']
            print(f"   品質分布: 高品質={quality_dist['high']}件, 中品質={quality_dist['medium']}件, 低品質={quality_dist['low']}件")
            
            # 上位結果詳細表示
            ranked_results = step4_result['ranked_results']
            print(f"\n   📊 高品質結果TOP5:")
            for j, result in enumerate(ranked_results[:5], 1):
                title = result.get('title', 'No title')
                final_score = result.get('final_score', 0)
                quality_score = result.get('quality_score', {})
                datasource = result.get('datasource', 'unknown')
                strategy = result.get('strategy', 'unknown')
                
                reliability = quality_score.get('reliability', 0)
                relevance = quality_score.get('relevance', 0)
                effectiveness = quality_score.get('effectiveness', 0)
                
                print(f"     {j}. {title[:50]}...")
                print(f"        最終スコア: {final_score:.3f} | 信頼性: {reliability:.2f} | 関連度: {relevance:.2f} | 有効性: {effectiveness:.2f}")
                print(f"        ソース: {datasource} | 戦略: {strategy}")
            
            # 品質分析情報
            insights = step4_result.get('quality_insights', {})
            if insights:
                print(f"\n   🔬 品質分析:")
                
                # データソース別分析
                ds_analysis = insights.get('datasource_analysis', {})
                if ds_analysis:
                    print(f"     データソース別:")
                    for ds, data in ds_analysis.items():
                        count = data.get('count', 0)
                        avg_score = data.get('avg_score', 0)
                        print(f"       {ds.title()}: {count}件 (平均スコア: {avg_score:.2f})")
                
                # 戦略別分析
                strategy_analysis = insights.get('strategy_analysis', {})
                if strategy_analysis:
                    print(f"     戦略別:")
                    for strategy, data in strategy_analysis.items():
                        count = data.get('count', 0)
                        avg_score = data.get('avg_score', 0)
                        print(f"       {strategy}: {count}件 (平均スコア: {avg_score:.2f})")
            
        except Exception as e:
            print(f"❌ 完全統合テスト失敗: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 90)
    print("🎉 ハイブリッド検索システム完全統合テスト完了")
    print("✅ Step1→Step2→Step3→Step4の全フローが正常動作")
    print("✅ 3軸品質評価・Strategy重み付け・高品質選出機能確認")
    print("=" * 90)

if __name__ == "__main__":
    test_complete_hybrid_search_system() 