"""
シンプル検索精度評価スクリプト

基本検索、強化検索、インデックス検索の基本性能を比較します。
"""

import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from spec_bot.tools.confluence_tool import search_confluence_tool
from spec_bot.tools.confluence_enhanced_search import search_confluence_enhanced
from spec_bot.tools.confluence_indexer import ConfluenceIndexer
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    print("プロジェクトの設定を確認してください")
    sys.exit(1)

class SimpleSearchEvaluator:
    """シンプル検索評価クラス"""
    
    def __init__(self):
        self.test_queries = [
            "API設計仕様書",
            "データベース設計", 
            "認証機能",
            "セキュリティ",
            "デプロイ手順"
        ]
        
    def evaluate_result(self, result: str, query: str) -> dict:
        """結果の簡易評価"""
        if not result or len(result) < 10:
            return {
                'quality_score': 0,
                'content_length': 0,
                'has_structure': False,
                'relevance': 0
            }
        
        content_length = len(result)
        has_structure = any(marker in result for marker in ['##', '**', '📄', '🔍', '-'])
        relevance = 1 if query.lower() in result.lower() else 0
        
        # 品質スコア (0-10)
        quality = 0
        if content_length > 100: quality += 2
        if content_length > 500: quality += 2
        if content_length > 1000: quality += 2
        if has_structure: quality += 2
        if relevance: quality += 2
        
        return {
            'quality_score': quality,
            'content_length': content_length,
            'has_structure': has_structure,
            'relevance': relevance
        }
    
    def test_basic_search(self, query: str) -> dict:
        """基本検索テスト"""
        try:
            start_time = time.time()
            result = search_confluence_tool(query=query, analyze_content=True)
            execution_time = time.time() - start_time
            
            evaluation = self.evaluate_result(str(result), query)
            evaluation['method'] = '基本検索'
            evaluation['execution_time'] = execution_time
            evaluation['success'] = True
            
            return evaluation
        except Exception as e:
            return {
                'method': '基本検索',
                'execution_time': 0,
                'success': False,
                'error': str(e),
                'quality_score': 0,
                'content_length': 0,
                'has_structure': False,
                'relevance': 0
            }
    
    def test_enhanced_search(self, query: str) -> dict:
        """強化検索テスト"""
        try:
            start_time = time.time()
            result = search_confluence_enhanced(query=query, max_pages=5)
            execution_time = time.time() - start_time
            
            evaluation = self.evaluate_result(str(result), query)
            evaluation['method'] = '強化検索'
            evaluation['execution_time'] = execution_time
            evaluation['success'] = True
            
            return evaluation
        except Exception as e:
            return {
                'method': '強化検索',
                'execution_time': 0,
                'success': False,
                'error': str(e),
                'quality_score': 0,
                'content_length': 0,
                'has_structure': False,
                'relevance': 0
            }
    
    def test_indexed_search(self, query: str) -> dict:
        """インデックス検索テスト"""
        try:
            indexer = ConfluenceIndexer()
            
            # インデックス読み込み
            if not indexer.load_index():
                return {
                    'method': 'インデックス検索',
                    'execution_time': 0,
                    'success': False,
                    'error': 'インデックスファイルが見つかりません',
                    'quality_score': 0,
                    'content_length': 0,
                    'has_structure': False,
                    'relevance': 0
                }
            
            start_time = time.time()
            results = indexer.search_by_keyword(query, max_results=5)
            execution_time = time.time() - start_time
            
            # 結果を文字列に変換
            if isinstance(results, list) and results:
                content = "\n".join([f"📋 {item.get('title', 'Unknown')}: {item.get('content_preview', '')[:100]}" 
                                   for item in results[:3]])
            else:
                content = "検索結果なし"
            
            evaluation = self.evaluate_result(content, query)
            evaluation['method'] = 'インデックス検索'
            evaluation['execution_time'] = execution_time
            evaluation['success'] = True
            evaluation['result_count'] = len(results) if isinstance(results, list) else 0
            
            return evaluation
        except Exception as e:
            return {
                'method': 'インデックス検索',
                'execution_time': 0,
                'success': False,
                'error': str(e),
                'quality_score': 0,
                'content_length': 0,
                'has_structure': False,
                'relevance': 0
            }
    
    def run_evaluation(self):
        """評価実行"""
        print("🔍 Confluence検索精度 簡易評価")
        print("=" * 50)
        
        all_results = []
        
        for i, query in enumerate(self.test_queries, 1):
            print(f"\n📝 テスト {i}/{len(self.test_queries)}: '{query}'")
            print("-" * 30)
            
            # 各検索手法をテスト
            basic_result = self.test_basic_search(query)
            enhanced_result = self.test_enhanced_search(query)
            indexed_result = self.test_indexed_search(query)
            
            results = [basic_result, enhanced_result, indexed_result]
            
            for result in results:
                if result['success']:
                    print(f"✅ {result['method']}: "
                          f"{result['execution_time']:.2f}s, "
                          f"品質{result['quality_score']}/10, "
                          f"{result['content_length']}文字")
                else:
                    print(f"❌ {result['method']}: {result.get('error', 'エラー')}")
                
                result['query'] = query
                all_results.append(result)
            
            # API制限対策
            time.sleep(1)
        
        self.generate_summary(all_results)
    
    def generate_summary(self, results):
        """サマリーレポート生成"""
        print(f"\n{'='*50}")
        print("📊 評価サマリー")
        print(f"{'='*50}")
        
        methods = ['基本検索', '強化検索', 'インデックス検索']
        
        # 統計計算
        stats = {}
        for method in methods:
            method_results = [r for r in results if r['method'] == method and r['success']]
            
            if method_results:
                stats[method] = {
                    'success_count': len(method_results),
                    'total_tests': len([r for r in results if r['method'] == method]),
                    'avg_time': sum(r['execution_time'] for r in method_results) / len(method_results),
                    'avg_quality': sum(r['quality_score'] for r in method_results) / len(method_results),
                    'avg_length': sum(r['content_length'] for r in method_results) / len(method_results),
                    'structure_rate': sum(1 for r in method_results if r['has_structure']) / len(method_results) * 100
                }
            else:
                stats[method] = None
        
        # 結果表示
        print(f"\n🏆 総合比較")
        print(f"{'手法':<12} {'成功率':<8} {'平均時間':<10} {'平均品質':<10} {'構造化率':<10}")
        print("-" * 55)
        
        for method in methods:
            if stats[method]:
                s = stats[method]
                success_rate = (s['success_count'] / s['total_tests']) * 100
                print(f"{method:<12} "
                      f"{success_rate:<8.1f}% "
                      f"{s['avg_time']:<10.2f}s "
                      f"{s['avg_quality']:<10.1f}/10 "
                      f"{s['structure_rate']:<10.1f}%")
            else:
                print(f"{method:<12} データなし")
        
        # 推奨事項
        print(f"\n🎯 推奨事項:")
        
        # 最優秀手法の特定
        valid_methods = [method for method in methods if stats[method]]
        
        if valid_methods:
            best_quality = max(valid_methods, key=lambda m: stats[m]['avg_quality'])
            best_speed = max(valid_methods, key=lambda m: 1/stats[m]['avg_time'] if stats[m]['avg_time'] > 0 else 0)
            
            print(f"• 最高品質: {best_quality} ({stats[best_quality]['avg_quality']:.1f}/10)")
            print(f"• 最高速度: {best_speed} ({stats[best_speed]['avg_time']:.2f}s)")
            
            if stats.get('強化検索') and stats['強化検索']['avg_quality'] > 5:
                print("• 推奨: 強化検索を主要手法として採用")
            if stats.get('インデックス検索') and stats['インデックス検索']['avg_time'] < 1.0:
                print("• 推奨: インデックス検索を高速検索用に併用")
        else:
            print("• 評価データが不足しています")

def main():
    """メイン実行"""
    print("🚀 検索精度評価を開始します...")
    
    evaluator = SimpleSearchEvaluator()
    evaluator.run_evaluation()

if __name__ == "__main__":
    main() 