"""
Atlassian API（Jira/Confluence）疎通確認テスト

このテストは、Jira と Confluence への接続と基本的な操作を確認します。
"""

import pytest
import sys
from pathlib import Path

# プロジェクトのルートパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.spec_bot_mvp.config.settings import settings

def test_atlassian_settings_validation():
    """Atlassian設定の検証テスト"""
    
    # 設定の検証
    is_valid = settings.validate_atlassian_config()
    
    if not is_valid:
        pytest.skip("Atlassian設定が不完全です - config/secrets.envでATLASSIAN_API_TOKENを設定してください")
    
    print(f"✅ Atlassian設定検証成功")
    print(f"   ドメイン: {settings.atlassian_domain}")
    print(f"   メール: {settings.atlassian_email}")
    print(f"   Confluenceスペース: {settings.confluence_space}")
    
    # APIトークンの設定確認（値の内容は表示しない）
    token = settings.atlassian_api_token
    if token and token != "your_atlassian_api_token_here":
        print(f"   APIトークン: 設定済み (長さ: {len(token)} 文字)")
    else:
        print(f"   APIトークン: 未設定 - config/secrets.envでATLASSIAN_API_TOKENを設定してください")

def test_jira_connection():
    """Jira API接続テスト"""
    
    if not settings.validate_atlassian_config():
        pytest.skip("Atlassian設定が無効です - config/secrets.envでATLASSIAN_API_TOKENを設定してください")
    
    try:
        from atlassian import Jira
        
        # Jira接続
        jira = Jira(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        
        # プロジェクト一覧取得テスト
        projects = jira.projects()
        
        assert projects is not None, "プロジェクト一覧の取得に失敗しました"
        assert isinstance(projects, list), "プロジェクト一覧がリスト形式ではありません"
        
        print(f"✅ Jira接続成功")
        print(f"   プロジェクト数: {len(projects)}")
        
        # 簡単なJQL検索テスト
        try:
            issues = jira.jql("project is not empty", limit=1)
            print(f"   JQL検索テスト: 成功 (結果数: {len(issues.get('issues', []))})")
        except Exception as e:
            print(f"   JQL検索テスト: 警告 - {e}")
        
    except ImportError as e:
        pytest.fail(f"Atlassian APIライブラリがインストールされていません: {e}")
    except Exception as e:
        pytest.fail(f"Jira接続エラー: {e}")

def test_confluence_connection():
    """Confluence API接続テスト"""
    
    if not settings.validate_atlassian_config():
        pytest.skip("Atlassian設定が無効です - config/secrets.envでATLASSIAN_API_TOKENを設定してください")
    
    try:
        from atlassian import Confluence
        
        # Confluence接続
        confluence = Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        
        # スペース一覧取得テスト
        spaces = confluence.get_all_spaces()
        
        assert spaces is not None, "スペース一覧の取得に失敗しました"
        assert 'results' in spaces, "スペース情報の形式が正しくありません"
        
        space_list = spaces['results']
        print(f"✅ Confluence接続成功")
        print(f"   スペース数: {len(space_list)}")
        
        # 指定されたスペースの確認
        target_space = settings.confluence_space
        if target_space:
            target_space_info = None
            for space in space_list:
                if space['key'] == target_space:
                    target_space_info = space
                    break
            
            if target_space_info:
                print(f"   対象スペース '{target_space}': 見つかりました")
                print(f"   スペース名: {target_space_info.get('name', 'N/A')}")
                
                # スペース内のページ数を取得
                try:
                    pages = confluence.get_all_pages_from_space(target_space, limit=1)
                    total_pages = pages.get('size', 0)
                    print(f"   ページ数: {total_pages}")
                except Exception as e:
                    print(f"   ページ数取得エラー: {e}")
            else:
                print(f"   警告: 対象スペース '{target_space}' が見つかりません")
        
    except ImportError as e:
        pytest.fail(f"Atlassian APIライブラリがインストールされていません: {e}")
    except Exception as e:
        pytest.fail(f"Confluence接続エラー: {e}")

if __name__ == "__main__":
    print("Atlassian API 接続テストを実行中...")
    
    try:
        test_atlassian_settings_validation()
        test_jira_connection()
        test_confluence_connection()
        print("\n🎉 全てのAtlassian API テストが完了しました！")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        sys.exit(1) 