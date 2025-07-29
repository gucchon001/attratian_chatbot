#!/usr/bin/env python3
"""
Step5 回答生成途中停止問題デバッグスクリプト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.spec_bot_mvp.agents.response_generator import ResponseGenerationAgent
    
    print("=" * 60)
    print("🔍 Step5 回答生成途中停止問題デバッグ")
    print("=" * 60)
    
    # テスト用検索結果（実際のログイン機能データ）
    test_search_results = [
        {
            "id": "703889475",
            "title": "042_【FIX】会員ログイン・ログアウト機能",
            "content": """1. 目次
2. 概要
会員がサービスサイトにてログイン、ログアウトを行うための機能です。
3. 要求事項
3.1.1. ログイン機能
メールアドレスとパスワードを入力し、登録済み情報と一致すればログインすることができる。
メールアドレスの入力規制は に記載の内容に準ずる。
パスワードは以下の入力規制を設ける。
8文字以上50文字以下であること。（セキュリティの観点からログイン時の入力は文字数チェック）
3.1.2. ログアウト機能
ログアウトボタンを押下することでログアウトできる。
ログアウト後はサービスサイトのトップページに遷移する。""",
            "url": "/spaces/CLIENTTOMO/pages/703889475/042_+FIX",
            "source": "confluence",
            "relevance_score": 1.0
        },
        {
            "id": "703824108", 
            "title": "681_【FIX】クライアント企業ログイン・ログアウト機能",
            "content": """1. 目次
2. 概要
クライアント企業管理者が、クライアント企業管理画面にログイン/ログアウトするための機能。
3. 要求事項
ログイン機能
メールアドレス、パスワード、企業コードを入力し登録済み情報と一致すれば、ログインに成功し、クライアント企業管理画面のTOPページへ遷移する。
「パスワードを忘れた」ボタンを押下すると に遷移する。
メールアドレス、パスワードの入力・登録規制は に記載の内容に準ずる。""",
            "url": "/spaces/CLIENTTOMO/pages/703824108/681_+FIX",
            "source": "confluence",
            "relevance_score": 0.95
        },
        {
            "id": "703529146",
            "title": "451_【FIX】全体管理者ログイン・ログアウト機能", 
            "content": """1. 目次
2. 概要
全体管理者が、全体管理画面にログイン/ログアウトするための機能。
3. 要求事項
ログイン機能
メールアドレスとパスワードを入力し登録済み情報と一致すれば、ログインに成功し、全体管理画面のTOPページへ遷移する。
メールアドレス・パスワードの入力・登録規制は に記載の内容に準ずる。
メールアドレスやパスワードの入力値に誤りがあった場合、エラーメッセージに具体的な箇所や内容は示さず、包括的なエラーメッセージを表示する。""",
            "url": "/spaces/CLIENTTOMO/pages/703529146/451_+FIX",
            "source": "confluence", 
            "relevance_score": 0.9
        }
    ]
    
    test_query = "ログイン機能の詳細を教えて"
    
    print(f"\n📝 テストクエリ: '{test_query}'")
    print(f"📊 検索結果数: {len(test_search_results)}件")
    
    # Step5回答生成実行
    print("\n🔄 Step5: 回答生成実行")
    try:
        agent = ResponseGenerationAgent()
        print("✅ ResponseGenerationAgent初期化成功")
        
        # 詳細デバッグ情報
        print(f"✅ Gemini設定:")
        print(f"   Model: {agent.settings.gemini_model}")
        print(f"   Temperature: {agent.settings.gemini_temperature}")
        print(f"   Max Tokens: {agent.settings.gemini_max_tokens}")
        
        # 実際の回答生成
        print(f"\n🚀 回答生成開始...")
        response = agent.generate_response(test_search_results, test_query)
        
        print(f"✅ 回答生成成功")
        print(f"📏 回答長: {len(response)} 文字")
        
        # 内容確認
        print(f"\n📄 回答内容（最初の500文字）:")
        print("-" * 50)
        print(response[:500])
        print("-" * 50)
        
        # 途中停止チェック
        lines = response.split('\n')
        if len(lines) < 10:
            print(f"⚠️ 回答が短すぎる可能性: {len(lines)}行")
        
        # 不完全終了パターンチェック
        incomplete_patterns = [
            "認証方法:",
            "ユーザーは",
            "入力された情報",
            "した場合に"
        ]
        
        for pattern in incomplete_patterns:
            if response.endswith(pattern):
                print(f"⚠️ 不完全終了を検出: '{pattern}'")
                break
        else:
            if len(response) > 1000:
                print(f"✅ 完全な回答が生成されました")
            else:
                print(f"⚠️ 回答が短い可能性があります")
        
        # 直接Gemini呼び出しテスト
        print(f"\n🔍 直接Gemini呼び出しテスト")
        formatted_results = agent._format_search_results(test_search_results)
        
        direct_result = agent.chain.invoke({
            "search_results": formatted_results,
            "user_query": test_query
        })
        
        if direct_result and hasattr(direct_result, 'content'):
            direct_content = direct_result.content
            print(f"📏 直接呼び出し結果長: {len(direct_content)} 文字")
            
            if len(direct_content) != len(response):
                print(f"⚠️ 処理過程で内容が変更されています")
                print(f"   直接呼び出し: {len(direct_content)}文字")
                print(f"   generate_response: {len(response)}文字")
            else:
                print(f"✅ 処理過程で内容は保持されています")
                
        else:
            print(f"❌ 直接Gemini呼び出しで空応答")
            
    except Exception as e:
        print(f"❌ Step5回答生成失敗: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 Step5デバッグ完了")
    print("=" * 60)

except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 予期しないエラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)