#!/usr/bin/env python3
"""
Enhanced CQL検索優先度テスト

エージェントが「ログイン機能の仕様を教えて」という質問に対して、
Enhanced CQL検索ツールを確実に選択するかテストします。
"""

import sys
import os
import time

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from spec_bot.core.agent import SpecBotAgent
from spec_bot.utils.log_config import setup_logging


def test_enhanced_cql_priority():
    """Enhanced CQL検索ツールの優先度テスト"""
    
    print("🎯 Enhanced CQL検索優先度テスト開始")
    print("=" * 60)
    
    try:
        # ログ設定
        setup_logging()
        
        # エージェント初期化
        print("🤖 エージェント初期化中...")
        agent = SpecBotAgent()
        
        # テストクエリ
        test_query = "ログイン機能の仕様を教えて"
        print(f"📝 テストクエリ: '{test_query}'")
        print("-" * 40)
        
        # エージェント実行
        start_time = time.time()
        response = agent.process_input(test_query)
        end_time = time.time()
        
        print(f"\n🏆 エージェント実行完了!")
        print(f"⏱️ 実行時間: {end_time - start_time:.2f}秒")
        print(f"📝 応答文字数: {len(response)}文字")
        print("-" * 40)
        
        # 応答内容の確認
        print("📋 【エージェント応答】")
        print(response[:500] + "..." if len(response) > 500 else response)
        
        # プロセストラッカーの詳細確認
        if hasattr(agent, 'process_tracker') and agent.process_tracker:
            tracker = agent.process_tracker
            print(f"\n📊 【プロセス詳細】")
            print(f"総実行時間: {tracker.get_total_duration():.2f}秒")
            
            # 段階別実行時間
            for stage, info in tracker.stages.items():
                duration = info.end_time - info.start_time if info.end_time else 0
                print(f"  {stage.value}: {duration:.2f}秒")
        
        print("\n✅ テスト完了!")
        
    except Exception as e:
        print(f"❌ テスト失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_enhanced_cql_priority() 