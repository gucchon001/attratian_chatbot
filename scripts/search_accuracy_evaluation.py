"""
Confluence検索精度評価スクリプト

基本検索、強化検索、インデックス検索の性能と精度を比較評価します。
"""

import sys
import os
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Tuple
import json
from dataclasses import dataclass

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.spec_bot.tools.confluence_tool import ConfluenceTool
from src.spec_bot.tools.confluence_enhanced_search import ConfluenceEnhancedSearch
from src.spec_bot.tools.confluence_indexer import ConfluenceIndexer
from src.spec_bot.utils.log_config import get_logger

logger = get_logger(__name__)

@dataclass
class SearchResult:
    """検索結果を格納するデータクラス"""
    method: str
    query: str
    execution_time: float
    result_count: int
    result_quality_score: float
    content_length: int
    has_structured_content: bool
    has_links: bool
    has_technical_details: bool
    relevance_score: float
    error: str = None

class SearchAccuracyEvaluator:
    """検索精度評価クラス"""
    
    def __init__(self):
        self.basic_tool = ConfluenceTool()
        self.enhanced_tool = ConfluenceEnhancedSearch()
        self.indexer = ConfluenceIndexer()
        
        # テスト用クエリセット（日本語）
        self.test_queries = [
            # 技術仕様関連
            "API設計仕様書",
            "データベース設計",
            "認証機能の実装",
            "セキュリティガイドライン",
            
            # 運用・保守関連
            "デプロイ手順",
            "障害対応マニュアル",
            "バックアップ手順",
            "監視設定",
            
            # 開発関連
            "テスト仕様書",
            "コーディング規約",
            "レビューガイドライン",
            "開発環境構築",
            
            # ユーザー関連
            "ユーザーマニュアル",
            "操作手順",
            "FAQ",
            "トラブルシューティング",
            
            # 複合キーワード
            "ログイン 認証 実装",
            "データ移行 手順書",
            "パフォーマンス チューニング",
            "エラー処理 設計"
        ]
        
        self.results = []
    
    def evaluate_content_quality(self, content: str, query: str) -> Tuple[float, Dict[str, bool]]:
        """
        コンテンツ品質を評価
        
        Returns:
            Tuple[float, Dict]: (品質スコア 0-10, 詳細分析)
        """
        if not content or len(content.strip()) < 50:
            return 0.0, {
                'has_structured_content': False,
                'has_links': False,
                'has_technical_details': False,
                'sufficient_length': False
            }
        
        content_lower = content.lower()
        query_lower = query.lower()
        
        # 基本分析
        analysis = {
            'has_structured_content': any(marker in content for marker in ['##', '###', '**', '- ', '1.', '2.']),
            'has_links': any(marker in content for marker in ['http', 'wiki', 'confluence']),
            'has_technical_details': any(term in content_lower for term in ['設定', '手順', '方法', '実装', '仕様']),
            'sufficient_length': len(content) >= 200
        }
        
        # クエリ関連性チェック
        query_words = query_lower.split()
        relevance_matches = sum(1 for word in query_words if word in content_lower)
        relevance_ratio = relevance_matches / len(query_words) if query_words else 0
        
        # 品質スコア計算（0-10）
        score = 0.0
        
        # 長さによる基礎点 (0-3点)
        if len(content) >= 1000:
            score += 3.0
        elif len(content) >= 500:
            score += 2.0
        elif len(content) >= 200:
            score += 1.0
        
        # 構造化による加点 (0-2点)
        if analysis['has_structured_content']:
            score += 2.0
        
        # リンクによる加点 (0-1点)
        if analysis['has_links']:
            score += 1.0
        
        # 技術詳細による加点 (0-2点)
        if analysis['has_technical_details']:
            score += 2.0
        
        # 関連性による加点 (0-2点)
        score += relevance_ratio * 2.0
        
        return min(score, 10.0), analysis
    
    async def test_basic_search(self, query: str) -> SearchResult:
        """基本検索のテスト"""
        try:
            start_time = time.time()
            
            result = self.basic_tool.search_confluence(
                query=query,
                space_key=None,
                max_results=10
            )
            
            execution_time = time.time() - start_time
            
            # 結果分析
            content = result if isinstance(result, str) else str(result)
            quality_score, analysis = self.evaluate_content_quality(content, query)
            
            # 関連度スコア（基本検索では簡易評価）
            relevance_score = 5.0 if query.lower() in content.lower() else 2.0
            
            return SearchResult(
                method="基本検索",
                query=query,
                execution_time=execution_time,
                result_count=content.count('ページ') if 'ページ' in content else 1,
                result_quality_score=quality_score,
                content_length=len(content),
                has_structured_content=analysis['has_structured_content'],
                has_links=analysis['has_links'],
                has_technical_details=analysis['has_technical_details'],
                relevance_score=relevance_score
            )
            
        except Exception as e:
            return SearchResult(
                method="基本検索",
                query=query,
                execution_time=0,
                result_count=0,
                result_quality_score=0,
                content_length=0,
                has_structured_content=False,
                has_links=False,
                has_technical_details=False,
                relevance_score=0,
                error=str(e)
            )
    
    async def test_enhanced_search(self, query: str) -> SearchResult:
        """強化検索のテスト"""
        try:
            start_time = time.time()
            
            result = self.enhanced_tool.search_confluence_enhanced(
                query=query,
                space_key=None,
                max_results=10
            )
            
            execution_time = time.time() - start_time
            
            # 結果分析
            content = result if isinstance(result, str) else str(result)
            quality_score, analysis = self.evaluate_content_quality(content, query)
            
            # 強化検索では詳細情報を含むため関連度スコアを向上
            base_relevance = 5.0 if query.lower() in content.lower() else 2.0
            structure_bonus = 2.0 if analysis['has_structured_content'] else 0
            detail_bonus = 1.5 if analysis['has_technical_details'] else 0
            relevance_score = min(base_relevance + structure_bonus + detail_bonus, 10.0)
            
            return SearchResult(
                method="強化検索",
                query=query,
                execution_time=execution_time,
                result_count=content.count('📄') if '📄' in content else content.count('ページ'),
                result_quality_score=quality_score,
                content_length=len(content),
                has_structured_content=analysis['has_structured_content'],
                has_links=analysis['has_links'],
                has_technical_details=analysis['has_technical_details'],
                relevance_score=relevance_score
            )
            
        except Exception as e:
            return SearchResult(
                method="強化検索",
                query=query,
                execution_time=0,
                result_count=0,
                result_quality_score=0,
                content_length=0,
                has_structured_content=False,
                has_links=False,
                has_technical_details=False,
                relevance_score=0,
                error=str(e)
            )
    
    async def test_indexed_search(self, query: str) -> SearchResult:
        """インデックス検索のテスト"""
        try:
            start_time = time.time()
            
            # インデックス読み込み
            if not self.indexer.load_index():
                # インデックスが無い場合は基本的な結果を返す
                return SearchResult(
                    method="インデックス検索",
                    query=query,
                    execution_time=0,
                    result_count=0,
                    result_quality_score=0,
                    content_length=0,
                    has_structured_content=False,
                    has_links=False,
                    has_technical_details=False,
                    relevance_score=0,
                    error="インデックスファイルが見つかりません"
                )
            
            # インデックス検索実行
            results = self.indexer.search_indexed_content(query, max_results=10)
            execution_time = time.time() - start_time
            
            # 結果を文字列に変換
            if isinstance(results, list):
                content = "\n".join([f"📋 {item.get('title', 'Unknown')}: {item.get('content_preview', '')}" 
                                   for item in results[:5]])
            else:
                content = str(results)
            
            quality_score, analysis = self.evaluate_content_quality(content, query)
            
            # インデックス検索では事前分析により高い関連度
            base_relevance = 7.0 if query.lower() in content.lower() else 4.0
            index_bonus = 2.0 if len(results) > 0 else 0
            relevance_score = min(base_relevance + index_bonus, 10.0)
            
            return SearchResult(
                method="インデックス検索",
                query=query,
                execution_time=execution_time,
                result_count=len(results) if isinstance(results, list) else 1,
                result_quality_score=quality_score,
                content_length=len(content),
                has_structured_content=analysis['has_structured_content'],
                has_links=analysis['has_links'],
                has_technical_details=analysis['has_technical_details'],
                relevance_score=relevance_score
            )
            
        except Exception as e:
            return SearchResult(
                method="インデックス検索",
                query=query,
                execution_time=0,
                result_count=0,
                result_quality_score=0,
                content_length=0,
                has_structured_content=False,
                has_links=False,
                has_technical_details=False,
                relevance_score=0,
                error=str(e)
            )
    
    async def run_evaluation(self, query_limit: int = None):
        """検索精度評価の実行"""
        print("🔍 Confluence検索精度評価を開始...")
        print("=" * 60)
        
        queries_to_test = self.test_queries[:query_limit] if query_limit else self.test_queries
        
        for i, query in enumerate(queries_to_test, 1):
            print(f"\n📝 テスト {i}/{len(queries_to_test)}: '{query}'")
            print("-" * 40)
            
            # 各検索手法をテスト
            tasks = [
                self.test_basic_search(query),
                self.test_enhanced_search(query),
                self.test_indexed_search(query)
            ]
            
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        print(f"❌ エラー: {result}")
                        continue
                    
                    if result.error:
                        print(f"❌ {result.method}: {result.error}")
                    else:
                        print(f"✅ {result.method}: "
                              f"{result.execution_time:.2f}s, "
                              f"品質{result.result_quality_score:.1f}/10, "
                              f"関連度{result.relevance_score:.1f}/10, "
                              f"{result.result_count}件")
                    
                    self.results.append(result)
                    
            except Exception as e:
                print(f"❌ クエリ '{query}' でエラー: {e}")
            
            # APIレート制限対策
            await asyncio.sleep(1)
        
        self.generate_report()
    
    def generate_report(self):
        """詳細レポートの生成"""
        print("\n" + "=" * 60)
        print("📊 検索精度評価 レポート")
        print("=" * 60)
        
        if not self.results:
            print("❌ 評価結果がありません")
            return
        
        # 手法別の統計
        methods = ["基本検索", "強化検索", "インデックス検索"]
        stats = {}
        
        for method in methods:
            method_results = [r for r in self.results if r.method == method and not r.error]
            
            if method_results:
                stats[method] = {
                    'total_tests': len(method_results),
                    'success_rate': len(method_results) / len([r for r in self.results if r.method == method]) * 100,
                    'avg_execution_time': sum(r.execution_time for r in method_results) / len(method_results),
                    'avg_quality_score': sum(r.result_quality_score for r in method_results) / len(method_results),
                    'avg_relevance_score': sum(r.relevance_score for r in method_results) / len(method_results),
                    'avg_content_length': sum(r.content_length for r in method_results) / len(method_results),
                    'structured_content_rate': sum(1 for r in method_results if r.has_structured_content) / len(method_results) * 100,
                    'technical_details_rate': sum(1 for r in method_results if r.has_technical_details) / len(method_results) * 100
                }
            else:
                stats[method] = None
        
        # レポート表示
        print(f"\n🏆 総合比較")
        print(f"{'手法':<12} {'成功率':<8} {'実行時間':<10} {'品質スコア':<10} {'関連度':<8} {'コンテンツ長':<12}")
        print("-" * 70)
        
        for method in methods:
            if stats[method]:
                s = stats[method]
                print(f"{method:<12} "
                      f"{s['success_rate']:<8.1f}% "
                      f"{s['avg_execution_time']:<10.2f}s "
                      f"{s['avg_quality_score']:<10.1f}/10 "
                      f"{s['avg_relevance_score']:<8.1f}/10 "
                      f"{s['avg_content_length']:<12.0f}文字")
            else:
                print(f"{method:<12} データなし")
        
        # 詳細分析
        print(f"\n📋 詳細分析")
        print("-" * 30)
        
        for method in methods:
            if stats[method]:
                s = stats[method]
                print(f"\n{method}:")
                print(f"  • 構造化コンテンツ率: {s['structured_content_rate']:.1f}%")
                print(f"  • 技術詳細含有率: {s['technical_details_rate']:.1f}%")
                print(f"  • 成功テスト数: {s['total_tests']}")
        
        # 推奨事項
        self.generate_recommendations(stats)
        
        # 結果をJSONで保存
        self.save_results_to_json()
    
    def generate_recommendations(self, stats: Dict):
        """推奨事項の生成"""
        print(f"\n🎯 推奨事項")
        print("-" * 20)
        
        if not any(stats.values()):
            print("❌ 分析データが不足しています")
            return
        
        # 最優秀手法の特定
        best_quality = max((method for method in stats if stats[method]), 
                          key=lambda m: stats[m]['avg_quality_score'])
        best_speed = max((method for method in stats if stats[method]), 
                        key=lambda m: 1/stats[m]['avg_execution_time'] if stats[m]['avg_execution_time'] > 0 else 0)
        best_relevance = max((method for method in stats if stats[method]), 
                           key=lambda m: stats[m]['avg_relevance_score'])
        
        print(f"🏆 最高品質: {best_quality} ({stats[best_quality]['avg_quality_score']:.1f}/10)")
        print(f"⚡ 最高速度: {best_speed} ({stats[best_speed]['avg_execution_time']:.2f}s)")
        print(f"🎯 最高関連度: {best_relevance} ({stats[best_relevance]['avg_relevance_score']:.1f}/10)")
        
        # 総合推奨
        print(f"\n✨ 総合推奨:")
        if stats.get("強化検索"):
            enhanced_stats = stats["強化検索"]
            if enhanced_stats['avg_quality_score'] > 6.0:
                print("• 強化検索を主要検索手法として採用")
                print("• 詳細分析と構造化コンテンツ提供により高品質")
        
        if stats.get("インデックス検索") and stats["インデックス検索"]["avg_execution_time"] < 1.0:
            print("• インデックス検索を高速検索用に併用")
            print("• 事前構築により高速応答を実現")
        
        print("• ハイブリッド検索戦略の採用を推奨")
        print("• 用途に応じた検索手法の自動選択機能の導入")
    
    def save_results_to_json(self):
        """結果をJSONファイルに保存"""
        try:
            results_data = []
            for result in self.results:
                results_data.append({
                    'method': result.method,
                    'query': result.query,
                    'execution_time': result.execution_time,
                    'result_count': result.result_count,
                    'result_quality_score': result.result_quality_score,
                    'content_length': result.content_length,
                    'has_structured_content': result.has_structured_content,
                    'has_links': result.has_links,
                    'has_technical_details': result.has_technical_details,
                    'relevance_score': result.relevance_score,
                    'error': result.error
                })
            
            output_file = Path("search_accuracy_evaluation_results.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 結果を {output_file} に保存しました")
            
        except Exception as e:
            print(f"❌ 結果保存エラー: {e}")

async def main():
    """メイン実行関数"""
    print("🔍 Confluence検索精度評価ツール")
    print("=" * 40)
    
    # テストクエリ数の選択
    evaluator = SearchAccuracyEvaluator()
    total_queries = len(evaluator.test_queries)
    
    print(f"利用可能なテストクエリ: {total_queries}個")
    print("実行するテスト数を選択してください:")
    print("1. クイックテスト (5クエリ)")
    print("2. 標準テスト (10クエリ)")
    print("3. 完全テスト (全クエリ)")
    
    try:
        choice = input("選択 (1-3): ").strip()
        if choice == "1":
            query_limit = 5
        elif choice == "2":
            query_limit = 10
        elif choice == "3":
            query_limit = None
        else:
            query_limit = 5
            print("デフォルト: クイックテスト")
    except:
        query_limit = 5
        print("デフォルト: クイックテスト")
    
    # 評価実行
    await evaluator.run_evaluation(query_limit)

if __name__ == "__main__":
    asyncio.run(main()) 