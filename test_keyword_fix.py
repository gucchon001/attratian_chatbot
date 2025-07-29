#!/usr/bin/env python3
"""
キーワード抽出修正のテストスクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.spec_bot_mvp.steps.step1_keyword_extraction import KeywordExtractor
    
    print("=" * 60)
    print("🔍 キーワード抽出修正テスト")
    print("=" * 60)
    
    # テストケース
    test_cases = [
        "ログイン機能の仕様の詳細",
        "急募機能について教えて",
        "API設計書の内容を確認したい",
        "データベース設計の詳細",
        "会員登録フローを調べて"
    ]
    
    extractor = KeywordExtractor()
    
    for test_query in test_cases:
        print(f"\n📝 テストクエリ: '{test_query}'")
        print("-" * 40)
        
        # キーワード抽出実行
        result = extractor.extract_keywords(test_query)
        
        print(f"✅ 抽出結果:")
        print(f"   キーワード: {result.get('primary_keywords', [])}")
        print(f"   抽出手法: {result.get('extraction_method', 'unknown')}")
        print(f"   信頼度: {result.get('confidence_score', 0):.2f}")
        
        # 期待される結果の確認
        keywords = result.get('primary_keywords', [])
        
        # 汎用語除去確認
        generic_words = ['仕様', '詳細', '機能', '設計', '内容']
        has_generic = any(word in keywords for word in generic_words if word in keywords and len([k for k in keywords if word in k]) == 1)
        
        if has_generic:
            print(f"   ⚠️ 汎用語が残存: {[w for w in keywords if w in generic_words]}")
        else:
            print(f"   ✅ 汎用語除去正常")
        
        # 複合語分解確認
        if test_query == "ログイン機能の仕様の詳細":
            expected_keywords = ["ログイン機能", "ログイン"]
            if set(expected_keywords).issubset(set(keywords)):
                print(f"   ✅ 複合語分解正常: {expected_keywords}")
            else:
                print(f"   ⚠️ 複合語分解不適切: 期待{expected_keywords}, 実際{keywords}")
    
    print("\n" + "=" * 60)
    print("🎯 テスト完了")
    print("=" * 60)

except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 予期しないエラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)