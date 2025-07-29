#!/usr/bin/env python3
"""
Step2・Step5 Gemini AI空応答デバッグスクリプト
"""

import sys
from pathlib import Path
import json

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent if Path(__file__).parent.name == 'spec_bot_mvp' else Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.spec_bot_mvp.steps.step1_keyword_extraction import KeywordExtractor
    from src.spec_bot_mvp.steps.step2_datasource_judgment import DataSourceJudge
    from src.spec_bot_mvp.agents.response_generator import ResponseGenerationAgent
    
    print("=" * 60)
    print("🔍 Step2・Step5 Gemini AI空応答デバッグ")
    print("=" * 60)
    
    # テストクエリ
    test_query = "急募機能の詳細"
    
    # Step1実行
    print(f"\n📝 テストクエリ: '{test_query}'")
    print("\n🔄 Step1: キーワード抽出実行")
    extractor = KeywordExtractor()
    step1_result = extractor.extract_keywords(test_query)
    print(f"✅ Step1成功: {step1_result.get('primary_keywords', [])}")
    
    # Step2実行とデバッグ
    print("\n🔄 Step2: データソース判定実行")
    try:
        judge = DataSourceJudge()
        print("✅ DataSourceJudge初期化成功")
        
        # Gemini利用可能性確認
        print(f"✅ Gemini利用可能: {judge.gemini_available}")
        
        # 実際のStep2実行
        step2_result = judge.judge_datasource(step1_result)
        print(f"✅ Step2成功:")
        print(f"   - 選択データソース: {step2_result.get('selected_datasources', [])}")
        print(f"   - 最適化キーワード: {step2_result.get('optimized_keywords', [])}")
        print(f"   - 判定理由: {step2_result.get('judgment_reasoning', 'なし')}")
        
        # Step2でのGemini応答詳細チェック
        if judge.gemini_available:
            print("\n🔍 Step2 Gemini詳細テスト")
            try:
                from src.spec_bot_mvp.utils.prompt_loader import load_prompt
                
                prompt = load_prompt(
                    "analysis_steps",
                    "step2_datasource_judgment", 
                    "keyword_optimization",
                    keywords=step1_result.get('primary_keywords', []),
                    selected_datasources=['confluence']
                )
                print(f"📋 Step2プロンプト長: {len(prompt)} 文字")
                
                response = judge.llm.invoke(prompt)
                print(f"📤 Step2 Gemini応答:")
                if response and hasattr(response, 'content'):
                    print(f"   内容: {response.content[:200]}...")
                    print(f"   長さ: {len(response.content)} 文字")
                    
                    # JSON解析テスト
                    try:
                        json_start = response.content.find('{')
                        json_end = response.content.rfind('}') + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = response.content[json_start:json_end]
                            result = json.loads(json_str)
                            print(f"✅ JSON解析成功: {result}")
                        else:
                            print("⚠️ JSON形式ではない応答")
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON解析失敗: {e}")
                else:
                    print("❌ Step2で空応答!")
                    
            except Exception as e:
                print(f"❌ Step2 Gemini詳細テスト失敗: {e}")
        
    except Exception as e:
        print(f"❌ Step2失敗: {e}")
        step2_result = {
            "selected_datasources": ["confluence"],
            "optimized_keywords": step1_result.get('primary_keywords', []),
            "judgment_reasoning": "Step2エラーのためデフォルト"
        }
    
    # Step5実行とデバッグ
    print("\n🔄 Step5: 回答生成実行")
    try:
        agent = ResponseGenerationAgent()
        print("✅ ResponseGenerationAgent初期化成功")
        
        # テスト用検索結果
        mock_search_results = [
            {
                "title": "急募機能仕様書",
                "content": "急募機能は企業が緊急で人材を募集する際に使用する機能です。申込みから公開まで迅速に対応できる設計になっています。",
                "url": "https://example.com/urgent-recruit-spec",
                "source": "confluence",
                "relevance_score": 0.95
            },
            {
                "title": "急募管理機能 - 申込機能",
                "content": "クライアント企業が急募オプションを申し込むための機能。管理画面から簡単に設定できます。",
                "url": "https://example.com/urgent-management",
                "source": "confluence", 
                "relevance_score": 0.87
            }
        ]
        
        # Step5実行
        response = agent.generate_response(mock_search_results, test_query)
        
        print(f"✅ Step5成功:")
        print(f"   - 応答長: {len(response)} 文字")
        print(f"   - 応答開始: {response[:200]}...")
        
        # Step5でのGemini詳細チェック
        print("\n🔍 Step5 Gemini詳細テスト")
        try:
            # プロンプトテンプレート生成
            formatted_results = agent._format_search_results(mock_search_results)
            
            test_result = agent.chain.invoke({
                "search_results": formatted_results,
                "user_query": test_query
            })
            
            print(f"📤 Step5 Gemini応答:")
            if test_result and hasattr(test_result, 'content'):
                print(f"   内容: {test_result.content[:200]}...")
                print(f"   長さ: {len(test_result.content)} 文字")
            else:
                print("❌ Step5で空応答!")
                print(f"   応答オブジェクト: {test_result}")
                
        except Exception as e:
            print(f"❌ Step5 Gemini詳細テスト失敗: {e}")
            
    except Exception as e:
        print(f"❌ Step5失敗: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Step2・Step5デバッグ完了")
    print("=" * 60)

except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 予期しないエラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)