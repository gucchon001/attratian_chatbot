"""
SpecBotAgent 単体テスト

LangChainエージェントの初期化から実際の質問処理まで、
全ての機能を包括的にテストします。
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# プロジェクトのルートパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.spec_bot_mvp.core.agent import SpecBotAgent
from src.spec_bot_mvp.config.settings import settings


class TestSpecBotAgentInitialization:
    """エージェント初期化関連のテスト"""
    
    def test_agent_basic_initialization(self):
        """エージェントの基本初期化テスト"""
        if not settings.validate_gemini_config():
            pytest.skip("Gemini API設定が無効です")
            
        agent = SpecBotAgent()
        
        # エージェント初期化の検証
        assert agent is not None
        assert agent.llm is not None
        assert agent.memory is not None
        assert agent.tools is not None
        assert agent.agent_executor is not None
        
        print("✅ エージェント基本初期化成功")
    
    def test_llm_initialization(self):
        """LLM初期化の個別テスト"""
        if not settings.validate_gemini_config():
            pytest.skip("Gemini API設定が無効です")
            
        agent = SpecBotAgent()
        
        # LLM設定の検証
        assert hasattr(agent.llm, 'model')
        # LangChainはmodelにmodels/プレフィックスを自動追加することがある
        assert settings.gemini_model in agent.llm.model
        assert hasattr(agent.llm, 'temperature')
        
        print(f"✅ LLM初期化成功 - モデル: {settings.gemini_model}")
    
    def test_memory_initialization(self):
        """メモリ初期化の個別テスト"""
        if not settings.validate_gemini_config():
            pytest.skip("Gemini API設定が無効です")
            
        agent = SpecBotAgent()
        
        # メモリ機能の検証
        assert agent.memory is not None
        assert hasattr(agent.memory, 'memory_key')
        assert agent.memory.memory_key == "chat_history"
        
        # 初期状態では会話履歴が空
        history = agent.get_conversation_history()
        assert isinstance(history, list)
        assert len(history) == 0
        
        print("✅ メモリ初期化成功")
    
    def test_tools_initialization(self):
        """ツール初期化の個別テスト"""
        if not settings.validate_gemini_config():
            pytest.skip("Gemini API設定が無効です")
            
        agent = SpecBotAgent()
        
        # ツールの検証
        assert len(agent.tools) == 6  # 期待されるツール数
        
        tool_names = [tool.name for tool in agent.tools]
        expected_tools = [
            "jira_search",
            "confluence_search", 
            "jira_filter_options",
            "jira_filtered_search",
            "confluence_filtered_search",
            "confluence_space_structure"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"ツール '{expected_tool}' が見つかりません"
        
        print(f"✅ ツール初期化成功 - {len(agent.tools)}個のツール登録")
    
    def test_agent_status(self):
        """エージェント状態取得テスト"""
        if not settings.validate_gemini_config():
            pytest.skip("Gemini API設定が無効です")
            
        agent = SpecBotAgent()
        status = agent.get_agent_status()
        
        # ステータス情報の検証
        assert isinstance(status, dict)
        assert 'llm_model' in status
        assert 'tools_count' in status
        assert 'memory_enabled' in status
        assert 'agent_initialized' in status
        assert 'conversation_length' in status
        
        assert status['llm_model'] == settings.gemini_model
        assert status['tools_count'] == 6
        assert status['memory_enabled'] is True
        assert status['agent_initialized'] is True
        assert status['conversation_length'] == 0
        
        print("✅ エージェント状態取得成功")


class TestSpecBotAgentConversation:
    """会話機能関連のテスト"""
    
    @pytest.fixture
    def agent(self):
        """テスト用エージェントインスタンス"""
        if not settings.validate_gemini_config():
            pytest.skip("Gemini API設定が無効です")
        return SpecBotAgent()
    
    def test_empty_input_handling(self, agent):
        """空入力のハンドリングテスト"""
        response = agent.process_user_input("")
        assert "質問内容が空です" in response
        
        response = agent.process_user_input("   ")
        assert "質問内容が空です" in response
        
        print("✅ 空入力ハンドリング成功")
    
    def test_conversation_memory(self, agent):
        """会話メモリ機能テスト"""
        # 最初の質問
        response1 = agent.process_user_input("ログイン機能について教えて")
        assert isinstance(response1, str)
        assert len(response1) > 0
        
        # 会話履歴の確認
        history = agent.get_conversation_history()
        assert len(history) >= 2  # ユーザー入力 + AI応答
        
        print("✅ 会話メモリ機能成功")
    
    def test_conversation_history_clear(self, agent):
        """会話履歴クリア機能テスト"""
        # 質問して履歴を作る
        agent.process_user_input("テスト質問")
        
        # 履歴があることを確認
        history_before = agent.get_conversation_history()
        assert len(history_before) > 0
        
        # 履歴をクリア
        agent.clear_conversation_history()
        
        # 履歴が空になったことを確認
        history_after = agent.get_conversation_history()
        assert len(history_after) == 0
        
        print("✅ 会話履歴クリア機能成功")


class TestSpecBotAgentToolSelection:
    """ツール選択機能のテスト"""
    
    @pytest.fixture
    def agent(self):
        """テスト用エージェントインスタンス"""
        if not settings.validate_gemini_config():
            pytest.skip("Gemini API設定が無効です")
        return SpecBotAgent()
    
    def test_jira_search_intent(self, agent):
        """Jira検索意図の認識テスト"""
        test_questions = [
            "Jiraでバグを検索して",
            "チケットの状況を教えて",
            "開発タスクを見せて"
        ]
        
        for question in test_questions:
            response = agent.process_user_input(question)
            assert isinstance(response, str)
            assert len(response) > 0
            # 何らかの応答が返ることを確認（具体的な内容は環境依存）
        
        print("✅ Jira検索意図認識テスト成功")
    
    def test_confluence_search_intent(self, agent):
        """Confluence検索意図の認識テスト"""
        test_questions = [
            "Confluenceで仕様書を検索して",
            "ドキュメントを探して",
            "議事録を見せて"
        ]
        
        for question in test_questions:
            response = agent.process_user_input(question)
            assert isinstance(response, str)
            assert len(response) > 0
        
        print("✅ Confluence検索意図認識テスト成功")
    
    def test_filter_options_intent(self, agent):
        """フィルター項目取得意図の認識テスト"""
        test_questions = [
            "利用可能なプロジェクトを教えて",
            "ステータス一覧を見せて",
            "フィルター条件を確認したい"
        ]
        
        for question in test_questions:
            response = agent.process_user_input(question)
            assert isinstance(response, str)
            assert len(response) > 0
        
        print("✅ フィルター項目取得意図認識テスト成功")


class TestSpecBotAgentErrorHandling:
    """エラーハンドリングのテスト"""
    
    @pytest.fixture
    def agent(self):
        """テスト用エージェントインスタンス"""
        if not settings.validate_gemini_config():
            pytest.skip("Gemini API設定が無効です")
        return SpecBotAgent()
    
    def test_special_characters_input(self, agent):
        """特殊文字入力のハンドリングテスト"""
        special_inputs = [
            "!@#$%^&*()",
            "こんにちは！？",
            "test with 'quotes' and \"double quotes\"",
            "テスト\n改行\nあり"
        ]
        
        for special_input in special_inputs:
            response = agent.process_user_input(special_input)
            assert isinstance(response, str)
            assert len(response) > 0
            # エラーで止まらないことを確認
        
        print("✅ 特殊文字入力ハンドリング成功")
    
    def test_long_input(self, agent):
        """長文入力のハンドリングテスト"""
        long_input = "これは非常に長い質問です。" * 100  # 約1000文字
        
        response = agent.process_user_input(long_input)
        assert isinstance(response, str)
        assert len(response) > 0
        
        print("✅ 長文入力ハンドリング成功")
    
    @patch('src.spec_bot_mvp.tools.jira_tool.search_jira_with_filters')
    def test_tool_error_handling(self, mock_jira_search, agent):
        """ツールエラー時のハンドリングテスト"""
        # ツールでエラーを発生させる
        mock_jira_search.side_effect = Exception("API接続エラー")
        
        response = agent.process_user_input("Jiraでチケットを検索して")
        assert isinstance(response, str)
        assert len(response) > 0
        # エージェントがエラーをキャッチして適切に処理することを確認
        
        print("✅ ツールエラーハンドリング成功")


class TestSpecBotAgentPerformance:
    """パフォーマンス関連のテスト"""
    
    @pytest.fixture
    def agent(self):
        """テスト用エージェントインスタンス"""
        if not settings.validate_gemini_config():
            pytest.skip("Gemini API設定が無効です")
        return SpecBotAgent()
    
    def test_response_time(self, agent):
        """応答時間テスト"""
        start_time = time.time()
        
        response = agent.process_user_input("簡単な質問です")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert response_time < 30  # 30秒以内に応答
        
        print(f"✅ 応答時間テスト成功 - {response_time:.2f}秒")
    
    def test_multiple_questions_performance(self, agent):
        """複数質問処理のパフォーマンステスト"""
        questions = [
            "プロジェクト一覧を教えて",
            "ステータスを確認したい", 
            "チケットを検索して"
        ]
        
        total_start = time.time()
        
        for question in questions:
            start_time = time.time()
            response = agent.process_user_input(question)
            end_time = time.time()
            
            assert isinstance(response, str)
            assert len(response) > 0
            assert (end_time - start_time) < 30  # 各質問30秒以内
        
        total_end = time.time()
        total_time = total_end - total_start
        
        assert total_time < 90  # 全体で90秒以内
        
        print(f"✅ 複数質問パフォーマンステスト成功 - 総時間: {total_time:.2f}秒")


class TestSpecBotAgentIntegration:
    """統合テスト"""
    
    @pytest.fixture
    def agent(self):
        """テスト用エージェントインスタンス"""
        if not settings.validate_gemini_config():
            pytest.skip("Gemini API設定が無効です")
        return SpecBotAgent()
    
    def test_realistic_conversation_flow(self, agent):
        """実用的な会話フローテスト"""
        # 実際のユースケースに近い会話の流れ
        conversation_steps = [
            "こんにちは",
            "CTJプロジェクトのチケットを検索して",
            "その中でバグに関するものはありますか？",
            "ありがとうございます"
        ]
        
        for i, step in enumerate(conversation_steps):
            response = agent.process_user_input(step)
            assert isinstance(response, str)
            assert len(response) > 0
            
            print(f"ステップ{i+1}: 質問「{step}」→ 応答取得成功")
        
        # 会話履歴の確認
        history = agent.get_conversation_history()
        assert len(history) >= len(conversation_steps) * 2  # 質問+応答のペア
        
        print("✅ 実用的な会話フローテスト成功")
    
    def test_agent_robustness(self, agent):
        """エージェントの堅牢性テスト"""
        # 様々な種類の質問を連続で投げる
        diverse_questions = [
            "利用可能なプロジェクトは？",
            "ログイン機能のドキュメントを探して",
            "優先度の高いバグはありますか？",
            "会議の議事録を検索して",
            "開発進捗を教えて"
        ]
        
        for question in diverse_questions:
            response = agent.process_user_input(question)
            assert isinstance(response, str)
            assert len(response) > 0
            # エラーで停止しないことを確認
        
        # エージェント状態が正常であることを確認
        status = agent.get_agent_status()
        assert status['agent_initialized'] is True
        assert status['memory_enabled'] is True
        
        print("✅ エージェント堅牢性テスト成功")


def test_agent_without_api_keys():
    """APIキー無しでの初期化エラーテスト"""
    with patch.object(settings, 'gemini_api_key', None):
        with pytest.raises(ValueError, match="Gemini APIキーが設定されていません"):
            SpecBotAgent()
    
    print("✅ APIキー無し初期化エラーテスト成功")


if __name__ == "__main__":
    print("SpecBotAgent 単体テスト実行中...")
    print("=" * 80)
    
    # 設定確認
    if not settings.validate_gemini_config():
        print("❌ Gemini API設定が無効です")
        print("   config/secrets.env に GEMINI_API_KEY を設定してください")
        exit(1)
    
    # pytest実行
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=False)
    
    if result.returncode == 0:
        print("\n🎉 全てのSpecBotAgentテストが成功しました！")
    else:
        print(f"\n❌ テストが失敗しました (終了コード: {result.returncode})")
        exit(result.returncode) 