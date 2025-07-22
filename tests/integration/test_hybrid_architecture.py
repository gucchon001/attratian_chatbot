"""
ハイブリッドアーキテクチャ統合テスト

テスト対象: src/spec_bot_mvp 全体のハイブリッド制御フロー
テストID: IT-HY-001 ~ IT-HY-005
"""

import pytest
import unittest.mock as mock
from pathlib import Path
import sys
import os

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.spec_bot_mvp.app import HybridSearchApplication

@pytest.fixture(autouse=True)
def setup_test_environment():
    """テスト用環境変数設定"""
    os.environ['JIRA_URL'] = 'https://test-jira.atlassian.net'
    os.environ['JIRA_USERNAME'] = 'test@example.com'
    os.environ['CONFLUENCE_URL'] = 'https://test-confluence.atlassian.net'
    os.environ['CONFLUENCE_USERNAME'] = 'test@example.com'
    yield
    # クリーンアップは不要（テスト環境なので）

class TestHybridArchitecture:
    """ハイブリッドアーキテクチャ統合テスト"""
    
    @pytest.fixture
    def mock_external_deps(self):
        """外部依存をモック"""
        with mock.patch.multiple(
            'src.spec_bot_mvp.config.settings',
            Settings=mock.DEFAULT
        ), mock.patch.multiple(
            'src.spec_bot_mvp.utils.atlassian_api_client',
            AtlassianAPIClient=mock.DEFAULT
        ), mock.patch('src.spec_bot_mvp.agents.response_generator.LANGCHAIN_AVAILABLE', True):
            yield
    
    @pytest.fixture
    def hybrid_app(self, mock_external_deps):
        """テスト用ハイブリッドアプリケーション"""
        app = HybridSearchApplication()
        return app
    
    @pytest.fixture
    def high_quality_pipeline_result(self):
        """高品質パイプライン結果"""
        search_results = [
            {
                "source": "Confluence",
                "title": "ログイン機能仕様書 v2.1",
                "content": "OAuth 2.0認証フローによるセキュアなログイン実装。PKCE拡張により...",
                "url": "https://test.atlassian.net/wiki/123",
                "relevance_score": 0.92
            },
            {
                "source": "Jira",
                "title": "ログイン機能実装チケット",
                "content": "OAuth認証フローの実装作業。セキュリティレビュー完了済み...",
                "url": "https://test.atlassian.net/browse/CTJ-456", 
                "relevance_score": 0.86
            }
        ]
        quality_score = 0.89
        pipeline_metadata = {
            "extracted_keywords": ["ログイン", "認証", "OAuth"],
            "search_intent": "specification_inquiry",
            "target_sources": ["confluence", "jira"],
            "execution_timestamp": "2024-12-25T10:30:00",
            "filters_applied": {"use_jira": True, "use_confluence": True}
        }
        return search_results, quality_score, pipeline_metadata
    
    @pytest.fixture
    def low_quality_pipeline_result(self):
        """低品質パイプライン結果"""
        search_results = [
            {
                "source": "Jira",
                "title": "その他の作業",
                "content": "関連性の低い内容...",
                "url": "https://test.atlassian.net/browse/OTHER-1",
                "relevance_score": 0.31
            }
        ]
        quality_score = 0.31
        pipeline_metadata = {
            "extracted_keywords": ["あいまい"],
            "search_intent": "general",
            "target_sources": ["jira", "confluence"],
            "execution_timestamp": "2024-12-25T10:35:00",
            "filters_applied": {}
        }
        return search_results, quality_score, pipeline_metadata
    
    def test_high_quality_direct_response_flow(self, hybrid_app, high_quality_pipeline_result):
        """IT-HY-001: 高品質結果での直接回答生成フロー"""
        # Given: 高品質検索結果
        search_results, quality_score, metadata = high_quality_pipeline_result
        
        # パイプライン実行をモック
        with mock.patch.object(
            hybrid_app, '_execute_fixed_pipeline',
            return_value=(search_results, quality_score, metadata)
        ), mock.patch.object(
            hybrid_app.agent_handover_manager, 'execute_agent_handover',
            return_value="高品質な回答が生成されました。"
        ) as mock_handover:
            
            # When: ハイブリッド検索実行
            response = hybrid_app.execute_hybrid_search(
                user_query="ログイン機能の仕様について",
                filters={"use_jira": True, "use_confluence": True}
            )
            
            # Then: Agent連携が適切に実行される
            assert response == "高品質な回答が生成されました。"
            mock_handover.assert_called_once()
            
            # Agent連携の引数確認
            call_args = mock_handover.call_args
            assert call_args[1]['search_results'] == search_results
            assert call_args[1]['quality_score'] == quality_score
            assert call_args[1]['user_query'] == "ログイン機能の仕様について"
    
    def test_low_quality_fallback_flow(self, hybrid_app, low_quality_pipeline_result):
        """IT-HY-002: 低品質結果でのフォールバック検索フロー"""
        # Given: 低品質検索結果
        search_results, quality_score, metadata = low_quality_pipeline_result
        
        # パイプライン実行をモック
        with mock.patch.object(
            hybrid_app, '_execute_fixed_pipeline',
            return_value=(search_results, quality_score, metadata)
        ), mock.patch.object(
            hybrid_app.agent_handover_manager, 'execute_agent_handover',
            return_value="拡張検索により関連情報を見つけました。"
        ) as mock_handover:
            
            # When: ハイブリッド検索実行
            response = hybrid_app.execute_hybrid_search(
                user_query="あいまいなキーワード",
                filters={}
            )
            
            # Then: フォールバック処理が実行される
            assert "拡張検索により関連情報を見つけました。" in response
            mock_handover.assert_called_once()
            
            # 低品質スコアが適切に渡される
            call_args = mock_handover.call_args
            assert call_args[1]['quality_score'] == 0.31
    
    def test_pipeline_execution_with_metadata(self, hybrid_app):
        """IT-HY-003: パイプライン実行とメタデータ生成"""
        # Given: 正常なコンポーネント状態
        user_query = "API仕様について教えて"
        filters = {"use_confluence": True, "date_range": "2024-01-01"}
        
        # 各ステップをモック
        with mock.patch.object(
            hybrid_app.keyword_extractor, 'extract_keywords',
            return_value={"keywords": ["API", "仕様"], "intent": "specification_inquiry"}
        ), mock.patch.object(
            hybrid_app.datasource_judge, 'judge_datasource',
            return_value={"target_sources": ["confluence"]}
        ), mock.patch.object(
            hybrid_app.cql_search_engine, 'execute_search',
            return_value=[{"source": "Confluence", "title": "API仕様書", "relevance_score": 0.8}]
        ), mock.patch.object(
            hybrid_app.quality_evaluator, 'evaluate_and_rank',
            return_value={"overall_quality_score": 0.8, "ranked_results": []}
        ):
            
            # When: 固定パイプライン実行
            results, score, metadata = hybrid_app._execute_fixed_pipeline(user_query, filters)
            
            # Then: 適切な結果とメタデータ生成
            assert len(results) == 1
            assert score == 0.8
            assert metadata["extracted_keywords"] == ["API", "仕様"]
            assert metadata["search_intent"] == "specification_inquiry"
            assert metadata["target_sources"] == ["confluence"]
            assert "execution_timestamp" in metadata
            assert metadata["filters_applied"] == filters
    
    def test_error_handling_in_pipeline(self, hybrid_app):
        """IT-HY-004: パイプラインエラーハンドリング"""
        # Given: ステップ実行時エラー
        with mock.patch.object(
            hybrid_app.keyword_extractor, 'extract_keywords',
            side_effect=Exception("キーワード抽出エラー")
        ):
            
            # When: ハイブリッド検索実行
            response = hybrid_app.execute_hybrid_search(
                user_query="テスト質問",
                filters={}
            )
            
            # Then: 適切なエラー応答
            assert "申し訳ございません。検索処理中にエラーが発生しました" in response
            assert "キーワード抽出エラー" in response
    
    def test_agent_handover_manager_integration(self, hybrid_app, high_quality_pipeline_result):
        """IT-HY-005: AgentHandoverManager統合テスト"""
        # Given: 高品質結果とモックAgent
        search_results, quality_score, metadata = high_quality_pipeline_result
        
        # AgentHandoverManagerの各Agentをモック
        mock_response_generator = mock.MagicMock()
        mock_response_generator.generate_response.return_value = "統合された詳細回答"
        mock_agent_selector = mock.MagicMock()
        mock_agent_selector.select_agent_strategy.return_value = ("direct_response_generation", {"confidence": "high"})
        
        with mock.patch.object(
            hybrid_app.agent_handover_manager, 'response_generator', mock_response_generator
        ), mock.patch.object(
            hybrid_app.agent_handover_manager, 'agent_selector', mock_agent_selector
        ):
            
            # When: Agent連携実行
            response = hybrid_app.agent_handover_manager.execute_agent_handover(
                search_results=search_results,
                quality_score=quality_score,
                user_query="テスト質問",
                filters={},
                pipeline_metadata=metadata
            )
            
            # Then: 適切なAgent選択と実行
            assert response == "統合された詳細回答"
            mock_agent_selector.select_agent_strategy.assert_called_once()
            mock_response_generator.generate_response.assert_called_once()
    
    def test_empty_results_handling(self, hybrid_app):
        """IT-HY-006: 検索結果なしの場合の処理"""
        # Given: 空の検索結果
        with mock.patch.object(
            hybrid_app, '_execute_fixed_pipeline',
            return_value=([], 0.0, {"extracted_keywords": []})
        ), mock.patch.object(
            hybrid_app.agent_handover_manager, 'execute_agent_handover',
            return_value="検索結果が見つかりませんでした。検索条件を変更してお試しください。"
        ):
            
            # When: ハイブリッド検索実行
            response = hybrid_app.execute_hybrid_search(
                user_query="存在しない機能",
                filters={}
            )
            
            # Then: 適切なフォールバック応答
            assert "検索結果が見つかりませんでした" in response
            assert "検索条件を変更して" in response
    
    def test_filter_application(self, hybrid_app):
        """IT-HY-007: フィルター適用の統合テスト"""
        # Given: 具体的なフィルター条件
        filters = {
            "use_jira": True,
            "use_confluence": False,
            "date_range": "2024-01-01",
            "project": "CTJ"
        }
        
        # パイプライン実行をモック
        with mock.patch.object(
            hybrid_app, '_execute_fixed_pipeline',
            return_value=([], 0.5, {"filters_applied": filters})
        ) as mock_pipeline:
            
            # When: フィルター付きハイブリッド検索
            hybrid_app.execute_hybrid_search(
                user_query="フィルターテスト",
                filters=filters
            )
            
            # Then: フィルターが適切に渡される
            mock_pipeline.assert_called_once_with("フィルターテスト", filters)

class TestAgentHandoverManager:
    """AgentHandoverManager詳細テスト"""
    
    @pytest.fixture
    def handover_manager(self):
        """テスト用AgentHandoverManager"""
        from src.spec_bot_mvp.steps.step5_agent_handover import AgentHandoverManager
        
        with mock.patch('src.spec_bot_mvp.agents.response_generator.LANGCHAIN_AVAILABLE', True):
            return AgentHandoverManager()
    
    def test_agent_availability_validation(self, handover_manager):
        """IT-AG-001: Agent利用可能性検証"""
        # When: Agent利用可能性チェック
        result = handover_manager._validate_agent_availability()
        
        # Then: 適切な判定
        assert isinstance(result, bool)
    
    def test_strategy_execution_routing(self, handover_manager):
        """IT-AG-002: 戦略実行ルーティング"""
        # Given: 各戦略のモック
        search_results = [{"source": "test", "title": "test", "relevance_score": 0.8}]
        
        with mock.patch.object(
            handover_manager, '_execute_direct_response',
            return_value="直接回答"
        ) as mock_direct, mock.patch.object(
            handover_manager, '_execute_fallback_flow',
            return_value="フォールバック回答"
        ) as mock_fallback:
            
            # When: 異なる戦略実行
            direct_result = handover_manager._execute_strategy(
                "direct_response_generation", {}, search_results, "test", {}
            )
            fallback_result = handover_manager._execute_strategy(
                "fallback_then_response", {}, search_results, "test", {}
            )
            
            # Then: 適切なルーティング
            assert direct_result == "直接回答"
            assert fallback_result == "フォールバック回答"
            mock_direct.assert_called_once()
            mock_fallback.assert_called_once()

# pytest実行用のエントリーポイント
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 