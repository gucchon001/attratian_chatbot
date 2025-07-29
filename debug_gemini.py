#!/usr/bin/env python3
"""
Gemini AI設定確認・デバッグスクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.spec_bot_mvp.config.settings import Settings
    from src.spec_bot_mvp.steps.step1_keyword_extraction import KeywordExtractor
    
    print("=" * 50)
    print("🔍 Gemini AI設定確認・デバッグ")
    print("=" * 50)
    
    # 1. 設定確認
    print("\n📋 1. 設定確認")
    settings = Settings()
    print(f"✅ API Key: {settings.gemini_api_key[:10] if settings.gemini_api_key else 'None'}...")
    print(f"✅ Model: {settings.gemini_model}")
    print(f"✅ Temperature: {settings.gemini_temperature}")
    print(f"✅ Max Tokens: {settings.gemini_max_tokens}")
    
    # 2. KeywordExtractor初期化テスト
    print("\n🔧 2. KeywordExtractor初期化テスト")
    try:
        extractor = KeywordExtractor()
        print("✅ KeywordExtractor初期化成功")
        print(f"✅ Gemini利用可能: {extractor.gemini_available}")
    except Exception as e:
        print(f"❌ KeywordExtractor初期化失敗: {e}")
        sys.exit(1)
    
    # 3. 簡単なGemini API接続テスト
    print("\n🌐 3. Gemini API接続テスト")
    try:
        test_response = extractor.llm.invoke("テスト")
        if test_response and hasattr(test_response, 'content') and test_response.content:
            print(f"✅ Gemini API接続成功: {test_response.content[:50]}...")
        else:
            print(f"⚠️ Gemini API接続は成功したが空応答: {test_response}")
    except Exception as e:
        print(f"❌ Gemini API接続失敗: {e}")
    
    # 4. キーワード抽出テスト
    print("\n🔍 4. キーワード抽出テスト")
    test_queries = [
        "急募機能の詳細",
        "ログイン機能について",
        "API設計書を教えて"
    ]
    
    for query in test_queries:
        print(f"\n📝 クエリ: '{query}'")
        try:
            result = extractor.extract_keywords(query)
            print(f"✅ 抽出成功:")
            print(f"   - キーワード: {result.get('primary_keywords', [])}")
            print(f"   - 手法: {result.get('extraction_method', 'unknown')}")
            print(f"   - 検索意図: {result.get('search_intent', 'unknown')}")
        except Exception as e:
            print(f"❌ 抽出失敗: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 デバッグ完了")
    print("=" * 50)

except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 予期しないエラー: {e}")
    sys.exit(1)