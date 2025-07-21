#!/usr/bin/env python3
"""
詳細なAtlassian API接続診断スクリプト

具体的なエラー情報とレスポンス詳細を表示
"""

import os
import sys
import requests
import json
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def detailed_connection_test():
    """詳細な接続診断"""
    
    print("[INFO] 詳細なAtlassian API接続診断開始\n")
    
    try:
        from spec_bot.config.settings import settings
        
        print("=== 設定情報:")
        print(f"   - Atlassian Domain: {settings.atlassian_domain}")
        print(f"   - Atlassian Email: {settings.atlassian_email}")
        print(f"   - Confluence Space: {settings.confluence_space}")
        
        # APIトークンは一部のみ表示
        token = settings.atlassian_api_token
        if token:
            print(f"   - API Token: {'*' * 20}...{token[-10:] if len(token) > 10 else 'なし'}")
        else:
            print(f"   - API Token: 未設定")
        print()
        
        # Jira詳細テスト
        print("[INFO] Jira API詳細テスト")
        print("-" * 50)
        test_jira_detailed(settings)
        print()
        
        # Confluence詳細テスト  
        print("[INFO] Confluence API詳細テスト")
        print("-" * 50)
        test_confluence_detailed(settings)
        
    except Exception as e:
        print(f"[ERROR] 診断エラー: {e}")
        import traceback
        traceback.print_exc()


def test_jira_detailed(settings):
    """Jira API詳細テスト"""
    
    jira_url = f"https://{settings.atlassian_domain}"
    
    # Step 1: 基本的な認証テスト
    print("1. 基本認証テスト")
    auth = (settings.atlassian_email, settings.atlassian_api_token)
    
    try:
        # ユーザー情報取得
        response = requests.get(
            f"{jira_url}/rest/api/3/myself",
            auth=auth,
            headers={"Accept": "application/json"},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"   [OK] 認証成功")
            print(f"   ユーザー: {user_info.get('displayName', 'N/A')}")
            print(f"   アカウントID: {user_info.get('accountId', 'N/A')}")
        else:
            print(f"   [ERROR] 認証失敗")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   [ERROR] 接続エラー: {e}")
    
    # Step 2: プロジェクト一覧取得
    print("\n2. プロジェクト一覧取得")
    
    try:
        response = requests.get(
            f"{jira_url}/rest/api/3/project",
            auth=auth,
            headers={"Accept": "application/json"},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            projects = response.json()
            print(f"   [OK] プロジェクト数: {len(projects)}")
            
            # 最初の3プロジェクトの詳細表示
            for i, project in enumerate(projects[:3], 1):
                print(f"   {i}. {project['key']} - {project['name']}")
        else:
            print(f"   [ERROR] プロジェクト取得失敗")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   [ERROR] プロジェクト取得エラー: {e}")
    
    # Step 3: JQL検索テスト
    print("\n3. JQL検索テスト")
    
    try:
        jql_query = "project is not EMPTY ORDER BY created DESC"
        response = requests.get(
            f"{jira_url}/rest/api/3/search",
            auth=auth,
            headers={"Accept": "application/json"},
            params={
                "jql": jql_query,
                "maxResults": 5,
                "fields": "summary,status,assignee"
            },
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Query: {jql_query}")
        
        if response.status_code == 200:
            search_result = response.json()
            issues = search_result.get('issues', [])
            print(f"   [OK] 検索成功: {len(issues)} 件")
            
            for i, issue in enumerate(issues[:3], 1):
                summary = issue['fields']['summary'][:50]
                status = issue['fields']['status']['name']
                print(f"   {i}. {issue['key']}: {summary}... ({status})")
        else:
            print(f"   [ERROR] 検索失敗")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   [ERROR] 検索エラー: {e}")


def test_confluence_detailed(settings):
    """Confluence API詳細テスト"""
    
    confluence_url = f"https://{settings.atlassian_domain}"
    
    # Step 1: 基本的な認証テスト
    print("1. 基本認証テスト")
    auth = (settings.atlassian_email, settings.atlassian_api_token)
    
    try:
        # ユーザー情報取得
        response = requests.get(
            f"{confluence_url}/wiki/rest/api/user/current",
            auth=auth,
            headers={"Accept": "application/json"},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"   [OK] 認証成功")
            print(f"   ユーザー: {user_info.get('displayName', 'N/A')}")
            print(f"   ユーザーキー: {user_info.get('userKey', 'N/A')}")
        else:
            print(f"   [ERROR] 認証失敗")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   [ERROR] 接続エラー: {e}")
    
    # Step 2: スペース一覧取得
    print("\n2. スペース一覧取得")
    
    try:
        response = requests.get(
            f"{confluence_url}/wiki/rest/api/space",
            auth=auth,
            headers={"Accept": "application/json"},
            params={"limit": 10},
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            spaces_data = response.json()
            spaces = spaces_data.get('results', [])
            print(f"   [OK] スペース数: {len(spaces)}")
            
            # 最初の5スペースの詳細表示
            for i, space in enumerate(spaces[:5], 1):
                print(f"   {i}. {space['key']} - {space['name']}")
                
            # 指定スペースの確認
            if settings.confluence_space:
                target_space = next(
                    (s for s in spaces if s['key'] == settings.confluence_space),
                    None
                )
                if target_space:
                    print(f"   [OK] 対象スペース '{settings.confluence_space}' 確認済み")
                else:
                    print(f"   [WARN] 対象スペース '{settings.confluence_space}' が見つかりません")
        else:
            print(f"   [ERROR] スペース取得失敗")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   [ERROR] スペース取得エラー: {e}")
    
    # Step 3: ページ検索テスト
    print("\n3. ページ検索テスト")
    
    if settings.confluence_space:
        try:
            response = requests.get(
                f"{confluence_url}/wiki/rest/api/content",
                auth=auth,
                headers={"Accept": "application/json"},
                params={
                    "spaceKey": settings.confluence_space,
                    "limit": 5,
                    "expand": "history,space"
                },
                timeout=10
            )
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Space: {settings.confluence_space}")
            
            if response.status_code == 200:
                content_data = response.json()
                pages = content_data.get('results', [])
                print(f"   [OK] ページ数: {len(pages)}")
                
                for i, page in enumerate(pages[:3], 1):
                    title = page['title'][:50]
                    page_type = page['type']
                    print(f"   {i}. {page['id']}: {title}... ({page_type})")
            else:
                print(f"   [ERROR] ページ取得失敗")
                print(f"   Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"   [ERROR] ページ取得エラー: {e}")
    else:
        print("   [WARN] 対象スペースが設定されていません")


def main():
    """メイン実行"""
    print("=" * 70)
    print("Atlassian API 詳細接続診断")
    print("=" * 70)
    
    detailed_connection_test()
    
    print("\n" + "=" * 70)
    print("診断完了")
    print("=" * 70)
    print("上記の結果を参考に、接続エラーの原因を特定してください。")
    print("=" * 70)


if __name__ == "__main__":
    main() 