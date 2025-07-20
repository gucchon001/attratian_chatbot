#!/usr/bin/env python3
"""
CQL検索詳細プロセス表示テストスクリプト

「ログイン機能の仕様を教えて」でのCQL検索戦略プロセス表示をテストします。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from spec_bot_mvp.tools.confluence_enhanced_cql_search import ConfluenceEnhancedCQLSearch


def test_cql_detailed_process():
    """CQL検索詳細プロセステスト"""
    print("🔍 CQL検索詳細プロセステスト開始")
    print("=" * 60)
    
    # テストクエリ
    test_query = "ログイン機能の仕様を教えて"
    print(f"📝 テストクエリ: '{test_query}'")
    print()
    
    try:
        # Enhanced CQL検索インスタンス作成
        enhanced_search = ConfluenceEnhancedCQLSearch()
        
        # 詳細プロセス付きで検索実行
        print("🚀 詳細CQL検索実行開始...")
        print("-" * 40)
        
        result = enhanced_search.search_with_enhanced_cql(test_query, max_results=10)
        
        print("-" * 40)
        print("🏆 検索実行完了!")
        print()
        
        # 結果分析
        metadata = result.get('metadata', {})
        
        print("📊 【最終結果サマリー】")
        print(f"   📊 取得件数: {metadata.get('total_results', 0)}件")
        print(f"   🔍 ユニークページ: {metadata.get('unique_pages', 0)}件") 
        print(f"   ⏱️ 実行時間: {metadata.get('execution_time', 0):.2f}秒")
        print(f"   🎯 戦略別結果: {metadata.get('strategies_used', {})}")
        
        # 詳細プロセスログ表示
        if 'detailed_process_log' in metadata:
            print()
            print("🔍 【詳細プロセスログ】")
            for log_entry in metadata['detailed_process_log']:
                step = log_entry.get('step', '?')
                strategy = log_entry.get('strategy', '不明')
                new_results = log_entry.get('new_results', 0)
                total_results = log_entry.get('total_results', 0)
                
                print(f"   Step {step}: {strategy}")
                print(f"     新規取得: {new_results}件 (累計: {total_results}件)")
                
                # 戦略詳細情報
                if 'details' in log_entry:
                    details = log_entry['details']
                    
                    # CQLクエリ表示
                    if 'queries' in details:
                        print(f"     実行クエリ({len(details['queries'])}個):")
                        for i, query in enumerate(details['queries'], 1):
                            print(f"       {i}. {query}")
                    
                    # 結果内訳表示
                    if 'results_breakdown' in details:
                        breakdown_str = " | ".join(details['results_breakdown'])
                        print(f"     結果内訳: {breakdown_str}")
                
                print()
        
        # キーワード抽出結果
        if 'extracted_keywords' in metadata:
            keywords_str = " | ".join(metadata['extracted_keywords'])
            print(f"🔤 抽出キーワード: {keywords_str}")
        
        print()
        print("✅ テスト完了!")
        return True
        
    except Exception as e:
        print(f"❌ テスト失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_cql_detailed_process()
    exit(0 if success else 1) 