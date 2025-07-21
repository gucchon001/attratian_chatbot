#!/usr/bin/env python3
"""
Confluence URL調査スクリプト

一般的なConfluence URLパターンをテストして正しいURLを見つける
"""

import requests
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def check_confluence_urls():
    """一般的なConfluence URLパターンをテスト"""
    
    print("🔍 Confluence URL調査開始\n")
    
    try:
        from spec_bot.config.settings import settings
        
        base_domain = settings.atlassian_domain
        auth = (settings.atlassian_email, settings.atlassian_api_token)
        headers = {'Accept': 'application/json'}
        
        print(f"📋 基本情報:")
        print(f"   ドメイン: {base_domain}")
        print(f"   ユーザー: {settings.atlassian_email}")
        print(f"   対象スペース: {settings.confluence_space}")
        print()
        
        # 一般的なConfluence URLパターン
        url_patterns = [
            f"https://{base_domain}/wiki",  # 標準的なwikiパス
            f"https://{base_domain}/confluence", # confluenceパス
            f"https://{base_domain}",  # ルートパス
            f"https://wiki.{base_domain}",  # サブドメイン
            f"https://confluence.{base_domain}",  # サブドメイン
        ]
        
        print("📋 テスト対象URL:")
        for i, url in enumerate(url_patterns, 1):
            print(f"   {i}. {url}")
        print()
        
        successful_urls = []
        
        for i, base_url in enumerate(url_patterns, 1):
            print(f"🔍 テスト {i}: {base_url}")
            
            # API エンドポイントをテスト
            test_endpoints = [
                "/rest/api/space",
                "/rest/api/user/current", 
                "/rest/api/content"
            ]
            
            url_works = False
            
            for endpoint in test_endpoints:
                full_url = base_url + endpoint
                
                try:
                    print(f"   → {endpoint} をテスト中...")
                    response = requests.get(
                        full_url,
                        auth=auth,
                        headers=headers,
                        timeout=10
                    )
                    
                    print(f"      ステータス: {response.status_code}")
                    
                    if response.status_code == 200:
                        print(f"      ✅ 成功!")
                        url_works = True
                        
                        # スペース情報を取得してみる
                        if endpoint == "/rest/api/space":
                            try:
                                data = response.json()
                                spaces = data.get('results', [])
                                print(f"      スペース数: {len(spaces)}")
                                
                                # 対象スペースがあるか確認
                                if settings.confluence_space:
                                    target_found = any(
                                        space['key'] == settings.confluence_space 
                                        for space in spaces
                                    )
                                    if target_found:
                                        print(f"      ✅ 対象スペース '{settings.confluence_space}' 確認")
                                    else:
                                        print(f"      ⚠️ 対象スペース '{settings.confluence_space}' が見つかりません")
                            except:
                                print(f"      ⚠️ レスポンス解析エラー")
                        
                        break  # 成功したら次のURLへ
                    elif response.status_code == 401:
                        print(f"      ❌ 認証エラー")
                    elif response.status_code == 403:
                        print(f"      ❌ アクセス権限エラー")
                    elif response.status_code == 404:
                        print(f"      ❌ エンドポイントが存在しません")
                    else:
                        print(f"      ❌ その他のエラー")
                        
                except requests.exceptions.Timeout:
                    print(f"      ❌ タイムアウト")
                except requests.exceptions.ConnectionError:
                    print(f"      ❌ 接続エラー")
                except Exception as e:
                    print(f"      ❌ エラー: {e}")
            
            if url_works:
                successful_urls.append(base_url)
                print(f"   ✅ {base_url} は有効です！")
            else:
                print(f"   ❌ {base_url} は無効です")
            
            print()
        
        # 結果サマリー
        print("=" * 60)
        print("🎯 調査結果サマリー")
        print("=" * 60)
        
        if successful_urls:
            print(f"✅ 有効なURL ({len(successful_urls)} 個):")
            for url in successful_urls:
                print(f"   - {url}")
            
            print(f"\n💡 推奨設定:")
            print(f"   config/settings.ini の [atlassian] セクション:")
            print(f"   domain = {base_domain}")
            print(f"   email = {settings.atlassian_email}")
            
            if successful_urls:
                recommended_url = successful_urls[0]
                print(f"\n   動作確認済みURL: {recommended_url}")
        else:
            print("❌ 有効なURLが見つかりませんでした")
            print("\n🔧 確認事項:")
            print("   1. ドメイン名が正しいか")
            print("   2. APIトークンが有効か")
            print("   3. ユーザーにConfluenceへのアクセス権があるか")
            print("   4. ネットワーク接続に問題がないか")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 調査中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メイン実行"""
    print("=" * 60)
    print("Confluence URL 調査ツール")
    print("=" * 60)
    
    check_confluence_urls()

if __name__ == "__main__":
    main() 