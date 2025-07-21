"""
ツール単体テスト

Jira検索ツールとConfluence検索ツールの単体テストを実行します。
"""

import pytest
import sys
from pathlib import Path

# プロジェクトのルートパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.spec_bot.tools.jira_tool import search_jira_with_filters
from src.spec_bot.tools.confluence_tool import search_confluence_tool
from src.spec_bot.config.settings import settings


def test_jira_tool_basic_search():
    """Jira検索ツールの基本動作テスト"""
    
    if not settings.validate_atlassian_config():
        pytest.skip("Atlassian設定が無効です - API接続が必要です")
    
    # 基本的な検索テスト
    result = search_jira_with_filters("login")
    
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0
    
    print(f"✅ Jira検索テスト成功")
    print(f"   検索結果（最初の200文字）: {result[:200]}...")


def test_jira_tool_empty_query():
    """Jira検索ツールの空クエリテスト"""
    
    # 空文字列のテスト
    result = search_jira_with_filters("")
    assert "検索キーワードが指定されていません" in result
    
    # None のテスト
    result = search_jira_tool(None)
    assert "検索キーワードが指定されていません" in result
    
    print(f"✅ Jira空クエリテスト成功")


def test_jira_tool_no_results():
    """Jira検索ツールの結果ゼロ件テスト"""
    
    if not settings.validate_atlassian_config():
        pytest.skip("Atlassian設定が無効です - API接続が必要です")
    
    # 存在しないキーワードで検索
    result = search_jira_tool("非常にレアなキーワード12345")
    
    assert result is not None
    assert isinstance(result, str)
    assert "見つかりませんでした" in result
    
    print(f"✅ Jira結果ゼロ件テスト成功")


def test_confluence_tool_basic_search():
    """Confluence検索ツールの基本動作テスト"""
    
    if not settings.validate_atlassian_config():
        pytest.skip("Atlassian設定が無効です - API接続が必要です")
    
    # 基本的な検索テスト
    result = search_confluence_tool("仕様")
    
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0
    
    print(f"✅ Confluence検索テスト成功")
    print(f"   検索結果（最初の200文字）: {result[:200]}...")


def test_confluence_tool_empty_query():
    """Confluence検索ツールの空クエリテスト"""
    
    # 空文字列のテスト
    result = search_confluence_tool("")
    assert "検索キーワードが指定されていません" in result
    
    # None のテスト
    result = search_confluence_tool(None)
    assert "検索キーワードが指定されていません" in result
    
    print(f"✅ Confluence空クエリテスト成功")


def test_confluence_tool_no_results():
    """Confluence検索ツールの結果ゼロ件テスト"""
    
    if not settings.validate_atlassian_config():
        pytest.skip("Atlassian設定が無効です - API接続が必要です")
    
    # 存在しないキーワードで検索
    result = search_confluence_tool("非常にレアなキーワード54321")
    
    assert result is not None
    assert isinstance(result, str)
    assert "見つかりませんでした" in result
    
    print(f"✅ Confluence結果ゼロ件テスト成功")


def test_tools_integration():
    """両ツールの統合テスト"""
    
    if not settings.validate_atlassian_config():
        pytest.skip("Atlassian設定が無効です - API接続が必要です")
    
    # 同じキーワードで両方検索
    keyword = "login"
    
    jira_result = search_jira_tool(keyword)
    confluence_result = search_confluence_tool(keyword)
    
    assert jira_result is not None
    assert confluence_result is not None
    assert isinstance(jira_result, str)
    assert isinstance(confluence_result, str)
    
    print(f"✅ ツール統合テスト成功")
    print(f"   Jira結果: {'見つかりました' if '見つかりませんでした' not in jira_result else '結果なし'}")
    print(f"   Confluence結果: {'見つかりました' if '見つかりませんでした' not in confluence_result else '結果なし'}")


if __name__ == "__main__":
    print("ツール単体テストを実行中...")
    
    try:
        test_jira_tool_empty_query()
        test_confluence_tool_empty_query()
        
        test_jira_tool_basic_search()
        test_jira_tool_no_results()
        
        test_confluence_tool_basic_search()
        test_confluence_tool_no_results()
        
        test_tools_integration()
        
        print("\n🎉 全てのツールテストが完了しました！")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        sys.exit(1) 