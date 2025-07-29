#!/usr/bin/env python3
"""
API/モック実行モード確認スクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.spec_bot_mvp.steps.step3_cql_search import CQLSearchEngine
    from src.spec_bot_mvp.config.settings import Settings
    
    print("=" * 60)
    print("🔍 API/モック実行モード確認")
    print("=" * 60)
    
    # 1. 設定確認
    print("\n📋 1. Atlassian API設定確認")
    settings = Settings()
    print(f"✅ Domain: {settings.atlassian_domain}")
    print(f"✅ Email: {settings.atlassian_email}")
    print(f"✅ API Token: {settings.atlassian_api_token[:10] if settings.atlassian_api_token else 'None'}...")
    
    # 2. CQLSearchEngine初期化（接続テスト実行）
    print("\n🔧 2. CQLSearchEngine初期化・接続テスト")
    try:
        search_engine = CQLSearchEngine()
        print(f"✅ 初期化成功")
        print(f"🎯 実行モード: {'✅ 本番API' if search_engine.use_real_api else '🔶 模擬データ'}")
        
        if search_engine.use_real_api:
            print("   → 実際のAtlassian APIに接続して検索実行")
        else:
            print("   → モックデータを使用して検索実行")
            
    except Exception as e:
        print(f"❌ 初期化失敗: {e}")
    
    # 3. 検索テスト実行
    print("\n🔍 3. 実際の検索テスト")
    if 'search_engine' in locals():
        try:
            # ダミーのStep1, Step2結果を作成
            mock_step1_result = {
                "primary_keywords": ["急募機能"],
                "search_intent": "仕様確認",
                "confidence_score": 0.85
            }
            
            mock_step2_result = {
                "selected_datasources": ["confluence"],
                "optimized_keywords": ["急募"]
            }
            
            print(f"📝 テストクエリ: {mock_step1_result['primary_keywords']}")
            print(f"📊 選択データソース: {mock_step2_result['selected_datasources']}")
            
            # 実際の検索実行
            result = search_engine.execute_search(mock_step2_result, mock_step1_result)
            
            print(f"✅ 検索実行成功:")
            print(f"   - 総結果数: {result.get('total_results', 0)}件")
            
            # 結果の詳細分析
            search_results = result.get('search_results', {})
            for datasource, data in search_results.items():
                combined_results = data.get('combined_results', [])
                if combined_results:
                    first_result = combined_results[0]
                    print(f"   - {datasource}: {len(combined_results)}件")
                    print(f"     サンプルタイトル: {first_result.get('title', 'N/A')}")
                    
                    # APIかモックかの判定
                    if search_engine.use_real_api:
                        print(f"     🌐 実際のAPI結果")
                        print(f"     URL: {first_result.get('url', 'N/A')}")
                    else:
                        print(f"     🔶 モックデータ")
                        if 'mock' in first_result.get('id', '').lower() or 'dynamic' in first_result.get('id', '').lower():
                            print(f"     データID: {first_result.get('id', 'N/A')}")
            
        except Exception as e:
            print(f"❌ 検索テスト失敗: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 モード確認完了")
    print("=" * 60)

except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 予期しないエラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)