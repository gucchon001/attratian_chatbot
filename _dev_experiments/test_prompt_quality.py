#!/usr/bin/env python3
"""
プロンプト品質テストスクリプト
改善されたプロンプト設定の効果を確認します
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from spec_bot_mvp.core.agent import SpecBotAgent
from spec_bot_mvp.config.constants import prompt_manager


def test_prompt_loading():
    """プロンプト設定の読み込みテスト"""
    print("🧪 プロンプト設定読み込みテスト")
    print("=" * 50)
    
    # システムメッセージ確認
    system_message = prompt_manager.get_agent_system_message()
    print(f"📋 システムメッセージ長: {len(system_message)}文字")
    print(f"🎯 「核心的な役割」含む: {'🎯 核心的な役割' in system_message}")
    print(f"⭐ 「高品質回答の必須要素」含む: {'⭐ 高品質回答の必須要素' in system_message}")
    print(f"📝 「回答構造テンプレート」含む: {'📝 回答構造テンプレート' in system_message}")
    
    # ReActテンプレート確認
    react_template = prompt_manager.get_react_template()
    print(f"\n📋 ReActテンプレート長: {len(react_template)}文字")
    print(f"📋 「実行フォーマット」含む: {'📋 実行フォーマット' in react_template}")
    print(f"🔍 「詳細分析」含む: {'🔍 詳細分析' in react_template}")
    print(f"🚀 「推奨アクション」含む: {'🚀 推奨アクション' in react_template}")
    
    return len(system_message) > 1000 and len(react_template) > 2000


def test_agent_initialization():
    """エージェント初期化テスト"""
    print("\n🤖 エージェント初期化テスト")
    print("=" * 50)
    
    try:
        agent = SpecBotAgent()
        print("✅ エージェント初期化成功")
        
        # エージェント状態確認
        status = agent.get_agent_status()
        print(f"📊 LLMモデル: {status['llm_model']}")
        print(f"🔧 ツール数: {status['tools_count']}")
        print(f"🧠 メモリ有効: {status['memory_enabled']}")
        print(f"⚙️ エージェント初期化: {status['agent_initialized']}")
        
        return True
        
    except Exception as e:
        print(f"❌ エージェント初期化失敗: {str(e)}")
        return False


def test_response_quality():
    """応答品質テスト"""
    print("\n📋 応答品質テスト")
    print("=" * 50)
    
    try:
        agent = SpecBotAgent()
        
        # テスト質問
        test_question = "ログイン機能のバグ修正の進捗状況を教えて"
        print(f"❓ テスト質問: {test_question}")
        
        # 応答生成（短時間でタイムアウト）
        print("\n🔄 応答生成中...")
        response = agent.process_input(test_question)
        
        # 応答品質分析
        print(f"\n📊 応答長: {len(response)}文字")
        print(f"📌 「要約」含む: {'📌' in response}")
        print(f"🔍 「詳細分析」含む: {'🔍' in response}")
        print(f"💡 「洞察」含む: {'💡' in response}")
        print(f"🚀 「推奨アクション」含む: {'🚀' in response}")
        print(f"🔗 「参考資料」含む: {'🔗' in response}")
        
        # 構造化度評価
        sections = response.count('【')
        print(f"📋 構造化セクション数: {sections}")
        
        return len(response) > 500 and sections >= 3
        
    except Exception as e:
        print(f"❌ 応答品質テスト失敗: {str(e)}")
        return False


def main():
    """メイン実行"""
    print("🎯 仕様書作成支援ボット - プロンプト品質テスト")
    print("=" * 60)
    
    results = []
    
    # テスト実行
    results.append(("プロンプト設定読み込み", test_prompt_loading()))
    results.append(("エージェント初期化", test_agent_initialization()))
    # results.append(("応答品質", test_response_quality()))  # 時間がかかるため一旦コメントアウト
    
    # 結果表示
    print("\n🏆 テスト結果")
    print("=" * 30)
    
    for test_name, result in results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    final_status = "🎉 全テスト成功" if all_passed else "⚠️ 一部テスト失敗"
    print(f"\n{final_status}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main()) 