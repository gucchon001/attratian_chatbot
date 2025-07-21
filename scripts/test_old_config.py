#!/usr/bin/env python3
"""
以前の動作設定でのAPI接続テスト

src/spec_bot の設定を使用して接続確認
"""

import os
import sys
import requests
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_old_confluence_config():
    """以前の設定でConfluence接続テスト"""
    
    print("🔍 以前の設定でConfluence接続テスト開始\n")
    
    try:
        # 以前の設定を読み込み
        from src.spec_bot.config.settings import settings as old_settings
        
        print("📋 以前の設定情報:")
        print(f"   - Domain: {old_settings.atlassian_domain}")
        print(f"   - Email: {old_settings.atlassian_email}")
        print(f"   - API Token: {'*' * 20}...{old_settings.atlassian_api_token[-10:] if old_settings.atlassian_api_token else 'なし'}")
        print(f"   - Space: {old_settings.confluence_space}")
        print()
        
        # ベースURL構築（以前の方式）
        base_url = f"https://{old_settings.atlassian_domain}"
        auth = (old_settings.atlassian_email, old_settings.atlassian_api_token)
        headers = {'Accept': 'application/json'}
        
        print(f"🔍 テスト対象: {base_url}")
        
        # テスト1: Confluence API Root
        print("テスト1: Confluence API Root (/rest/api/space)")
        try:
            url = f"{base_url}/rest/api/space"
            response = requests.get(url, auth=auth, headers=headers, timeout=10)
            
            print(f"   - ステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                spaces_data = response.json()
                spaces = spaces_data.get('results', [])
                print(f"   - ✅ 成功: {len(spaces)}個のスペース取得")
                for space in spaces[:3]:
                    print(f"     - {space.get('key', 'Unknown')}: {space.get('name', 'Unknown')}")
                return True
            elif response.status_code == 404:
                print(f"   - ❌ 404: API エンドポイントが見つからない")
                print("     → Confluenceがインストールされていない可能性")
            elif response.status_code == 403:
                print(f"   - ⚠️ 403: 権限不足")
                print("     → URLは正しいが、API権限が不足")
            elif response.status_code == 401:
                print(f"   - ❌ 401: 認証失敗")
                print("     → ユーザー名またはトークンが無効")
            else:
                print(f"   - ❌ 失敗: {response.text[:200]}")
                
        except Exception as e:
            print(f"   - ❌ 例外: {e}")
        
        # テスト2: /wiki パス
        print("\nテスト2: /wiki パス (/wiki/rest/api/space)")
        try:
            url = f"{base_url}/wiki/rest/api/space"
            response = requests.get(url, auth=auth, headers=headers, timeout=10)
            
            print(f"   - ステータスコード: {response.status_code}")
            
            if response.status_code == 200:
                spaces_data = response.json()
                spaces = spaces_data.get('results', [])
                print(f"   - ✅ 成功: {len(spaces)}個のスペース取得")
                for space in spaces[:3]:
                    print(f"     - {space.get('key', 'Unknown')}: {space.get('name', 'Unknown')}")
                return True
            else:
                print(f"   - ❌ 失敗: ステータス {response.status_code}")
                
        except Exception as e:
            print(f"   - ❌ 例外: {e}")
        
        # テスト3: 実際のAtlassian Python ライブラリを使用
        print("\nテスト3: Atlassian Pythonライブラリでの接続")
        try:
            from atlassian import Confluence
            
            confluence = Confluence(
                url=base_url,
                username=old_settings.atlassian_email,
                password=old_settings.atlassian_api_token
            )
            
            # スペース一覧取得
            spaces = confluence.get_all_spaces(limit=5)
            if spaces and 'results' in spaces:
                results = spaces['results']
                print(f"   - ✅ 成功: Atlassianライブラリで {len(results)}個のスペース取得")
                for space in results[:3]:
                    print(f"     - {space.get('key', 'Unknown')}: {space.get('name', 'Unknown')}")
                return True
            else:
                print(f"   - ⚠️ スペースが見つからない: {spaces}")
                
        except Exception as e:
            print(f"   - ❌ Atlassianライブラリエラー: {e}")
        
        print("\n❌ すべてのテストで接続失敗")
        return False
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_old_confluence_config()
    if success:
        print(f"\n✅ 以前の設定で接続成功！この設定を使用可能です")
    else:
        print(f"\n⚠️ 以前の設定でも接続できませんでした") 