#!/usr/bin/env python3
"""
全文取得機能デバッグスクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.spec_bot_mvp.agents.response_generator import ResponseGenerationAgent
    
    print("=" * 60)
    print("🔍 全文取得機能デバッグ")
    print("=" * 60)
    
    # 実際の検索結果データ（ログから抽出）
    test_search_result = {
        "id": "703889475",
        "title": "042_【FIX】会員ログイン・ログアウト機能",
        "space": "",
        "type": "page",
        "url": "/spaces/CLIENTTOMO/pages/703889475/042_+FIX",
        "excerpt": """1. 目次
2. 概要
会員がサービスサイトにてログイン、ログアウトを行うための機能です。
3. 要求事項
3.1.1. ログイン機能
メールアドレスとパスワードを入力し、登録済み情報と一致すればログインすることができる。
メールアドレスの入力規制は に記載の内容に準ずる。
パスワードは以下の入力規制を設ける。
8文字以上50文字以下であること。（セキュリティの観点からログイン時の入力は文字数チェ""",
        "created": "",
        "strategy": "タイトル厳密検索",
        "weight": 3,
        "datasource": "confluence"
    }
    
    print(f"📊 検索結果データ分析:")
    print(f"   タイトル: {test_search_result['title']}")
    print(f"   ID: {test_search_result['id']}")
    print(f"   URL: {test_search_result['url']}")
    print(f"   excerpt長: {len(test_search_result['excerpt'])} 文字")
    print(f"   content存在: {'content' in test_search_result}")
    
    print(f"\n📄 excerpt内容:")
    print(f"「{test_search_result['excerpt']}」")
    
    # ResponseGenerationAgent初期化
    print(f"\n🔧 ResponseGenerationAgent テスト")
    try:
        agent = ResponseGenerationAgent()
        print("✅ ResponseGenerationAgent初期化成功")
        
        # 全文取得機能テスト
        print(f"\n🚀 全文取得機能テスト")
        enhanced_results = agent._enhance_content_with_full_fetch([test_search_result])
        
        print(f"📊 処理結果:")
        for i, result in enumerate(enhanced_results):
            print(f"   結果 {i+1}:")
            print(f"     content_enhanced: {result.get('content_enhanced', 'N/A')}")
            print(f"     content長: {len(result.get('content', ''))} 文字")
            print(f"     excerpt長: {len(result.get('excerpt', ''))} 文字")
            
            # 実際のcontentがexcerptと異なるかチェック
            content = result.get('content', '')
            excerpt = result.get('excerpt', '')
            
            if content and content != excerpt:
                print(f"     ✅ 全文取得成功: {len(excerpt)} → {len(content)} 文字")
                print(f"     📄 取得コンテンツ（最初の500文字）:")
                print(f"     「{content[:500]}...」")
            else:
                print(f"     ⚠️ 全文取得なし")
                
        # 実際の回答生成テスト
        print(f"\n🎯 回答生成テスト")
        test_query = "会員向けのログイン機能の詳細を教えて"
        response = agent.generate_response([test_search_result], test_query)
        
        print(f"📏 回答長: {len(response)} 文字")
        print(f"📄 回答内容（最初の800文字）:")
        print("-" * 50)
        print(response[:800])
        print("-" * 50)
        
        # コンテンツ取得状況の統計が含まれているかチェック
        if "コンテンツ取得状況" in response:
            print(f"✅ コンテンツ取得統計が含まれています")
        else:
            print(f"⚠️ コンテンツ取得統計が含まれていません")
            
    except Exception as e:
        print(f"❌ ResponseGenerationAgent処理失敗: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 全文取得デバッグ完了")
    print("=" * 60)

except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 予期しないエラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)