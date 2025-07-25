#!/usr/bin/env python3
"""
シンプル疎通確認テスト

絵文字を使わない、Windows環境対応の疎通確認テストです。
"""

import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from spec_bot_mvp.config.settings import settings
from atlassian import Jira, Confluence


def test_settings():
    """設定管理テスト"""
    print("\n" + "="*50)
    print("設定管理テスト")
    print("="*50)
    
    try:
        print("設定読み込み中...")
        print(f"Atlassian Domain: {settings.atlassian_domain}")
        print(f"Jira URL: {settings.jira_url}")
        print(f"Confluence URL: {settings.confluence_url}")
        print(f"ユーザー: {settings.jira_username}")
        
        settings.validate()
        print("OK: 設定検証成功")
        return True
        
    except Exception as e:
        print(f"ERROR: 設定テスト失敗 - {e}")
        return False


def test_jira():
    """Jira API接続テスト"""
    print("\n" + "="*50)
    print("Jira API接続テスト")
    print("="*50)
    
    try:
        print("Jira API接続中...")
        jira = Jira(
            url=settings.jira_url,
            username=settings.jira_username,
            password=settings.jira_api_token,
            cloud=True
        )
        
        projects = jira.get_all_projects(expand='description')
        print(f"OK: プロジェクト数 {len(projects)}")
        
        # 簡単な検索テスト
        jql = "project is not EMPTY ORDER BY created DESC"
        search_result = jira.jql(jql, limit=3)
        issues = search_result.get('issues', [])
        print(f"OK: 検索結果 {len(issues)} 件")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Jira接続失敗 - {e}")
        return False


def test_confluence():
    """Confluence API接続テスト"""
    print("\n" + "="*50)
    print("Confluence API接続テスト")
    print("="*50)
    
    try:
        print("Confluence API接続中...")
        confluence = Confluence(
            url=settings.confluence_url,
            username=settings.confluence_username,
            password=settings.confluence_api_token,
            cloud=True
        )
        
        spaces = confluence.get_all_spaces(limit=5)
        results = spaces.get('results', [])
        print(f"OK: スペース数 {len(results)}")
        
        # 特定スペースのテスト
        if settings.confluence_space_key:
            pages = confluence.get_all_pages_from_space(
                space=settings.confluence_space_key,
                limit=3
            )
            print(f"OK: スペース '{settings.confluence_space_key}' ページ数 {len(pages) if pages else 0}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Confluence接続失敗 - {e}")
        return False


def test_gemini():
    """Gemini API接続テスト"""
    print("\n" + "="*50)
    print("Gemini API接続テスト")
    print("="*50)
    
    # Gemini API設定確認
    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        print("SKIP: Gemini APIキーが設定されていません")
        return True
    
    try:
        # テスト用短文生成
        from langchain_google_genai import ChatGoogleGenerativeAI
        
        print("Gemini API接続中...")
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            api_key=settings.gemini_api_key,
            temperature=0
        )
        
        response = llm.invoke("テスト")
        print(f"OK: Gemini API応答成功")
        return True
        
    except ImportError:
        print("SKIP: langchain-google-genai がインストールされていません")
        return True
    except Exception as e:
        print(f"ERROR: Gemini接続失敗 - {e}")
        return False


def main():
    """メイン実行関数"""
    print("仕様書作成支援ボット - 疎通確認テスト")
    print("="*60)
    
    tests = [
        ("設定管理", test_settings, True),
        ("Jira API", test_jira, True),
        ("Confluence API", test_confluence, True),
        ("Gemini API", test_gemini, False),  # オプション
    ]
    
    results = []
    
    for test_name, test_func, required in tests:
        success = test_func()
        results.append((test_name, success, required))
        
        if required and not success:
            print(f"\n必須テスト '{test_name}' が失敗したため中断します")
            break
    
    # 結果サマリー
    print("\n" + "="*60)
    print("テスト結果サマリー")
    print("="*60)
    
    for test_name, success, required in results:
        status = "成功" if success else "失敗"
        req_text = "（必須）" if required else "（オプション）"
        print(f"{test_name}: {status} {req_text}")
    
    successful = sum(1 for _, success, _ in results if success)
    total = len(results)
    print(f"\n成功率: {successful}/{total} ({successful/total*100:.1f}%)")
    
    if all(success or not required for _, success, required in results):
        print("\nすべての必須テストが成功しました！")
        print("次のステップ:")
        print("1. ツール機能（Jira/Confluence検索）の実装")
        print("2. LangChainエージェントの実装")
        print("3. Streamlit UIの実装")
    else:
        print("\n一部のテストが失敗しています。")
        print("設定ファイル（secrets.env）を確認してください。")
    
    print("="*60)


if __name__ == "__main__":
    main() 