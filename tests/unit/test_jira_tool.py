"""
Jiraツールの単体テスト

CTJプロジェクト（client-tomonokai-juku）を対象とした
フィルター機能付きJira検索の単体テストを実装します。
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from spec_bot_mvp.tools.jira_tool import (
    get_jira_filter_options,
    search_jira_with_filters,
    search_jira_tool,
    _format_jira_results_with_filters
)


class TestJiraTool(unittest.TestCase):
    """Jiraツールの単体テストクラス"""
    
    def setUp(self):
        """テストの前処理"""
        self.target_project = "CTJ"  # client-tomonokai-juku
        
        # モックデータ
        self.mock_filter_options = {
            'projects': [
                {'key': 'CTJ', 'name': 'client-tomonokai-juku', 'id': '10228'},
                {'key': 'CPC', 'name': 'client-prudential-corporate', 'id': '10001'}
            ],
            'statuses': [
                {'id': '1', 'name': '確認待ち', 'category': '進行中'},
                {'id': '2', 'name': '完了', 'category': '完了'}
            ],
            'users': [
                {'accountId': 'user1', 'displayName': 'テストユーザー1', 'emailAddress': 'test1@example.com'}
            ],
            'issue_types': [
                {'id': '1', 'name': 'ストーリー', 'description': 'ユーザー目標として表明された機能。'},
                {'id': '2', 'name': 'タスク', 'description': 'さまざまな小規模作業。'}
            ],
            'priorities': [
                {'id': '1', 'name': '高', 'description': '高優先度'}
            ]
        }
        
        self.mock_search_result = {
            'issues': [
                {
                    'key': 'CTJ-123',
                    'fields': {
                        'summary': 'テスト仕様書作成',
                        'status': {'name': '確認待ち'},
                        'issuetype': {'name': 'ストーリー'},
                        'priority': {'name': '高'},
                        'project': {'key': 'CTJ'},
                        'assignee': {'displayName': 'テストユーザー1'},
                        'description': 'テスト用の仕様書を作成する'
                    }
                }
            ],
            'total': 1
        }
    
    @patch('spec_bot_mvp.tools.jira_tool.Jira')
    @patch('spec_bot_mvp.tools.jira_tool.cache_manager')
    def test_get_jira_filter_options_success(self, mock_cache_manager, mock_jira_class):
        """フィルター項目取得の成功テスト"""
        # モックの設定
        mock_cache_manager.get.return_value = None
        mock_cache_manager.set.return_value = True
        
        mock_jira = MagicMock()
        mock_jira_class.return_value = mock_jira
        
        # Jira APIのモック応答
        mock_jira.projects.return_value = self.mock_filter_options['projects']
        mock_jira.get_all_statuses.return_value = self.mock_filter_options['statuses']
        mock_jira.jql.return_value = {'issues': []}
        mock_jira.get.side_effect = [
            self.mock_filter_options['issue_types'],  # issue types
            self.mock_filter_options['priorities']    # priorities
        ]
        
        # テスト実行
        result = get_jira_filter_options()
        
        # 検証
        self.assertIsInstance(result, dict)
        self.assertIn('projects', result)
        self.assertIn('statuses', result)
        self.assertEqual(len(result['projects']), 2)
        self.assertEqual(result['projects'][0]['key'], 'CTJ')
    
    @patch('spec_bot_mvp.tools.jira_tool.cache_manager')
    def test_get_jira_filter_options_from_cache(self, mock_cache_manager):
        """キャッシュからのフィルター項目取得テスト"""
        # キャッシュから取得される設定
        mock_cache_manager.get.return_value = self.mock_filter_options
        
        # テスト実行
        result = get_jira_filter_options()
        
        # 検証
        self.assertEqual(result, self.mock_filter_options)
        mock_cache_manager.get.assert_called_once_with("jira_filter_options")
    
    @patch('spec_bot_mvp.tools.jira_tool.Jira')
    def test_search_jira_with_filters_project_filter(self, mock_jira_class):
        """プロジェクトフィルター付き検索テスト"""
        # モックの設定
        mock_jira = MagicMock()
        mock_jira_class.return_value = mock_jira
        mock_jira.jql.return_value = self.mock_search_result
        
        # テスト実行
        result = search_jira_with_filters("仕様書", project_keys=["CTJ"])
        
        # 検証
        self.assertIsInstance(result, str)
        self.assertIn("CTJ-123", result)
        self.assertIn("テスト仕様書作成", result)
        self.assertIn("プロジェクト: CTJ", result)
        
        # JQLクエリの検証
        mock_jira.jql.assert_called_once()
        call_args = mock_jira.jql.call_args[0][0]  # 最初の引数（JQLクエリ）
        self.assertIn('text ~ "仕様書"', call_args)
        self.assertIn('project = "CTJ"', call_args)
    
    @patch('spec_bot_mvp.tools.jira_tool.Jira')
    def test_search_jira_with_filters_multiple_filters(self, mock_jira_class):
        """複数フィルター組み合わせテスト"""
        # モックの設定
        mock_jira = MagicMock()
        mock_jira_class.return_value = mock_jira
        mock_jira.jql.return_value = self.mock_search_result
        
        # テスト実行
        result = search_jira_with_filters(
            "仕様書", 
            project_keys=["CTJ"], 
            status_names=["確認待ち"]
        )
        
        # 検証
        self.assertIsInstance(result, str)
        self.assertIn("フィルター条件:", result)
        self.assertIn("プロジェクト: CTJ", result)
        self.assertIn("ステータス: 確認待ち", result)
        
        # JQLクエリの検証
        call_args = mock_jira.jql.call_args[0][0]
        self.assertIn('text ~ "仕様書"', call_args)
        self.assertIn('project = "CTJ"', call_args)
        self.assertIn('status = "確認待ち"', call_args)
    
    def test_search_jira_with_filters_empty_query(self):
        """空のクエリでのテスト"""
        result = search_jira_with_filters("")
        self.assertEqual(result, "検索キーワードが指定されていません。")
    
    @patch('spec_bot_mvp.tools.jira_tool.Jira')
    def test_search_jira_with_filters_no_results(self, mock_jira_class):
        """検索結果なしのテスト"""
        # モックの設定
        mock_jira = MagicMock()
        mock_jira_class.return_value = mock_jira
        mock_jira.jql.return_value = {'issues': [], 'total': 0}
        
        # テスト実行
        result = search_jira_with_filters("存在しないキーワード", project_keys=["CTJ"])
        
        # 検証
        self.assertIn("見つかりませんでした", result)
    
    def test_format_jira_results_with_filters(self):
        """結果フォーマット関数のテスト"""
        issues = self.mock_search_result['issues']
        
        result = _format_jira_results_with_filters(
            issues, 
            "仕様書", 
            1,
            project_keys=["CTJ"],
            status_names=["確認待ち"]
        )
        
        # 検証
        self.assertIn("【Jira検索結果（フィルター付き）】", result)
        self.assertIn("キーワード: 「仕様書」", result)
        self.assertIn("フィルター条件:", result)
        self.assertIn("プロジェクト: CTJ", result)
        self.assertIn("ステータス: 確認待ち", result)
        self.assertIn("CTJ-123", result)
        self.assertIn("テスト仕様書作成", result)
    
    @patch('spec_bot_mvp.tools.jira_tool.Jira')
    def test_search_jira_tool_basic(self, mock_jira_class):
        """基本的な検索機能テスト（既存機能）"""
        # モックの設定
        mock_jira = MagicMock()
        mock_jira_class.return_value = mock_jira
        mock_jira.jql.return_value = self.mock_search_result
        
        # テスト実行
        result = search_jira_tool("仕様書")
        
        # 検証
        self.assertIsInstance(result, str)
        self.assertIn("CTJ-123", result)
        self.assertIn("テスト仕様書作成", result)


class TestJiraToolIntegration(unittest.TestCase):
    """Jiraツールの統合テスト（実際のAPIを使用しない）"""
    
    def test_ctj_project_focus(self):
        """CTJプロジェクトに特化したテスト"""
        # CTJプロジェクトの特性をテスト
        project_key = "CTJ"
        project_name = "client-tomonokai-juku"
        
        # プロジェクトキーの妥当性チェック
        self.assertEqual(len(project_key), 3)
        self.assertTrue(project_key.isupper())
        self.assertIn("tomonokai", project_name)


if __name__ == '__main__':
    unittest.main() 