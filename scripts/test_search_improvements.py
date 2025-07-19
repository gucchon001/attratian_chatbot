#!/usr/bin/env python3
"""
Confluence検索改善効果テストツール

各検索手法の性能と品質を比較し、改善効果を定量的に評価します。
"""

import sys
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.spec_bot_mvp.tools.confluence_tool import search_confluence_tool
from src.spec_bot_mvp.tools.confluence_enhanced_search import search_confluence_enhanced
from src.spec_bot_mvp.tools.confluence_indexer import search_indexed_confluence, ensure_index_ready


class SearchComparison:
    """検索手法比較クラス"""
    
    def __init__(self):
        self.test_queries = [
            "ログイン機能",
            "ログイン機能 仕様",
            "認証",
            "セキュリティ",
            "API仕様",
            "UI設計",
            "データベース設計",
            "エラーハンドリング"
        ]
        
        self.search_methods = {
            'basic': {
                'name': '基本検索',
                'func': search_confluence_tool,
                'description': '従来のCQL検索'
            },
            'enhanced': {
                'name': '高精度検索',
                'func': search_confluence_enhanced,
                'description': '並列取得+詳細分析'
            },
            'indexed': {
                'name': 'インデックス検索',
                'func': search_indexed_confluence,
                'description': '事前インデックス化'
            }
        }
    
    def run_performance_test(self) -> Dict[str, Any]:
        """パフォーマンステストを実行"""
        print("🚀 パフォーマンステスト開始")
        print("=" * 60)
        
        results = {}
        
        # インデックス事前構築
        print("📊 インデックス準備中...")
        indexer = ensure_index_ready()
        print(f"✅ インデックス準備完了\n")
        
        for method_key, method_info in self.search_methods.items():
            print(f"🔍 {method_info['name']}テスト ({method_info['description']})")
            
            method_results = {
                'total_time': 0,
                'average_time': 0,
                'success_count': 0,
                'error_count': 0,
                'results_per_query': {},
                'quality_scores': []
            }
            
            for query in self.test_queries:
                try:
                    print(f"  クエリ: '{query}'", end=' ')
                    
                    start_time = time.time()
                    result = method_info['func'](query)
                    execution_time = time.time() - start_time
                    
                    # 結果の品質評価
                    quality_score = self._evaluate_result_quality(result, query)
                    
                    method_results['results_per_query'][query] = {
                        'execution_time': execution_time,
                        'quality_score': quality_score,
                        'result_length': len(result),
                        'success': True
                    }
                    
                    method_results['total_time'] += execution_time
                    method_results['success_count'] += 1
                    method_results['quality_scores'].append(quality_score)
                    
                    print(f"✅ {execution_time:.2f}s (品質: {quality_score:.1f}/10)")
                    
                except Exception as e:
                    print(f"❌ エラー: {str(e)[:50]}...")
                    method_results['error_count'] += 1
                    method_results['results_per_query'][query] = {
                        'execution_time': 0,
                        'quality_score': 0,
                        'result_length': 0,
                        'success': False,
                        'error': str(e)
                    }
            
            # 統計計算
            if method_results['success_count'] > 0:
                method_results['average_time'] = method_results['total_time'] / method_results['success_count']
                method_results['average_quality'] = sum(method_results['quality_scores']) / len(method_results['quality_scores'])
            else:
                method_results['average_quality'] = 0
            
            results[method_key] = method_results
            print(f"  📊 平均実行時間: {method_results['average_time']:.2f}s")
            print(f"  📊 平均品質スコア: {method_results['average_quality']:.1f}/10")
            print(f"  📊 成功率: {method_results['success_count']}/{len(self.test_queries)}\n")
        
        return results
    
    def _evaluate_result_quality(self, result: str, query: str) -> float:
        """結果の品質を評価（10点満点）"""
        score = 0.0
        
        # 基本的な応答チェック
        if not result or len(result) < 50:
            return 1.0  # 最低点
        
        # 長さによる評価（適度な長さが良い）
        if 200 <= len(result) <= 2000:
            score += 2.0
        elif 50 <= len(result) < 200:
            score += 1.0
        elif len(result) > 2000:
            score += 1.5
        
        # キーワードマッチング
        query_lower = query.lower()
        result_lower = result.lower()
        
        if query_lower in result_lower:
            score += 2.0
        
        # 構造化された内容の評価
        structure_indicators = ['📄', '📚', '🔍', '📊', '💡', '⭐', '📋', '🎯']
        structure_score = sum(1 for indicator in structure_indicators if indicator in result)
        score += min(structure_score * 0.5, 2.0)
        
        # URLリンクの存在
        if 'http' in result:
            score += 1.0
        
        # 詳細情報の存在
        detail_keywords = ['仕様', 'セクション', '重要', 'ポイント', '設計', '実装']
        detail_score = sum(1 for keyword in detail_keywords if keyword in result)
        score += min(detail_score * 0.3, 2.0)
        
        # エラーメッセージの場合は低スコア
        if 'エラー' in result or 'error' in result_lower:
            score = max(score - 3.0, 0.0)
        
        return min(score, 10.0)
    
    def generate_comparison_report(self, results: Dict[str, Any]) -> str:
        """比較レポートを生成"""
        report_lines = [
            "📊 **Confluence検索改善効果レポート**",
            "=" * 60,
            ""
        ]
        
        # 概要テーブル
        report_lines.extend([
            "## 📈 パフォーマンス概要",
            "",
            "| 手法 | 平均実行時間 | 平均品質 | 成功率 | 改善度 |",
            "|------|-------------|----------|--------|--------|"
        ])
        
        basic_time = results.get('basic', {}).get('average_time', 0)
        basic_quality = results.get('basic', {}).get('average_quality', 0)
        
        for method_key, method_info in self.search_methods.items():
            method_results = results.get(method_key, {})
            avg_time = method_results.get('average_time', 0)
            avg_quality = method_results.get('average_quality', 0)
            success_rate = method_results.get('success_count', 0) / len(self.test_queries) * 100
            
            # 改善度計算
            time_improvement = ""
            quality_improvement = ""
            
            if method_key != 'basic' and basic_time > 0:
                time_ratio = (basic_time - avg_time) / basic_time * 100
                time_improvement = f"{time_ratio:+.1f}%"
                
            if method_key != 'basic' and basic_quality > 0:
                quality_ratio = (avg_quality - basic_quality) / basic_quality * 100
                quality_improvement = f"{quality_ratio:+.1f}%"
            
            improvement = f"{time_improvement} | {quality_improvement}".strip(" |")
            if not improvement:
                improvement = "-"
            
            report_lines.append(
                f"| {method_info['name']} | {avg_time:.2f}s | {avg_quality:.1f}/10 | {success_rate:.0f}% | {improvement} |"
            )
        
        # 詳細分析
        report_lines.extend([
            "",
            "## 🔍 詳細分析",
            ""
        ])
        
        # 最良の改善例を特定
        best_improvements = self._find_best_improvements(results)
        
        if best_improvements:
            report_lines.extend([
                "### ✨ 主要な改善点",
                ""
            ])
            
            for improvement in best_improvements:
                report_lines.append(f"- {improvement}")
        
        # クエリ別詳細
        report_lines.extend([
            "",
            "### 📋 クエリ別詳細結果",
            ""
        ])
        
        for query in self.test_queries:
            report_lines.append(f"**クエリ: '{query}'**")
            
            for method_key, method_info in self.search_methods.items():
                method_results = results.get(method_key, {})
                query_result = method_results.get('results_per_query', {}).get(query, {})
                
                if query_result.get('success', False):
                    time_val = query_result['execution_time']
                    quality_val = query_result['quality_score']
                    report_lines.append(f"  - {method_info['name']}: {time_val:.2f}s (品質: {quality_val:.1f}/10)")
                else:
                    report_lines.append(f"  - {method_info['name']}: ❌ 失敗")
            
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def _find_best_improvements(self, results: Dict[str, Any]) -> List[str]:
        """最良の改善点を特定"""
        improvements = []
        
        basic_results = results.get('basic', {})
        enhanced_results = results.get('enhanced', {})
        indexed_results = results.get('indexed', {})
        
        # 実行時間の改善
        basic_time = basic_results.get('average_time', 0)
        enhanced_time = enhanced_results.get('average_time', 0)
        indexed_time = indexed_results.get('average_time', 0)
        
        if indexed_time > 0 and basic_time > 0:
            indexed_improvement = (basic_time - indexed_time) / basic_time * 100
            if indexed_improvement > 20:
                improvements.append(f"インデックス検索により実行時間が {indexed_improvement:.1f}% 短縮")
        
        # 品質の改善
        basic_quality = basic_results.get('average_quality', 0)
        enhanced_quality = enhanced_results.get('average_quality', 0)
        
        if enhanced_quality > 0 and basic_quality > 0:
            quality_improvement = (enhanced_quality - basic_quality) / basic_quality * 100
            if quality_improvement > 30:
                improvements.append(f"高精度検索により情報品質が {quality_improvement:.1f}% 向上")
        
        # 成功率の改善
        basic_success = basic_results.get('success_count', 0)
        enhanced_success = enhanced_results.get('success_count', 0)
        
        if enhanced_success > basic_success:
            improvements.append(f"高精度検索により成功率が向上 ({basic_success} → {enhanced_success} 件)")
        
        return improvements
    
    def save_report(self, report: str, filename: str = None):
        """レポートをファイルに保存"""
        if filename is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"search_comparison_report_{timestamp}.md"
        
        report_path = Path("reports") / filename
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📄 レポート保存完了: {report_path}")


def main():
    """メイン実行関数"""
    print("🔍 Confluence検索改善効果テスト")
    print("=" * 60)
    
    try:
        # 比較テスト実行
        comparison = SearchComparison()
        results = comparison.run_performance_test()
        
        # レポート生成
        report = comparison.generate_comparison_report(results)
        
        # 結果表示
        print("\n" + "=" * 60)
        print(report)
        
        # レポート保存
        comparison.save_report(report)
        
    except KeyboardInterrupt:
        print("\n⏹️  テスト中断")
    except Exception as e:
        print(f"\n❌ テストエラー: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 