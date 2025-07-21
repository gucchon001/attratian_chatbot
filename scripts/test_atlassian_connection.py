#!/usr/bin/env python3
"""
Atlassian API接続テストスクリプト

設定の検証と実際のAPI接続テストを実行
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_atlassian_connection():
    """Atlassian API接続の総合テスト"""
    
    print("[INFO] Atlassian API接続テスト開始\n")
    
    # Step 1: 設定ファイル確認
    print("=== Step 1: 設定ファイル確認")
    print("-" * 40)
    
    try:
        from spec_bot.config.settings import settings
        
        print(f"[OK] 設定ファイル読み込み完了")
        print(f"   - Gemini API Key: {'設定済み' if settings.gemini_api_key else '[ERROR]未設定'}")
        print(f"   - Atlassian Domain: {settings.atlassian_domain or '[ERROR]未設定'}")
        print(f"   - Atlassian Email: {settings.atlassian_email or '[ERROR]未設定'}")
        print(f"   - Atlassian Token: {'設定済み' if settings.atlassian_api_token else '[ERROR]未設定'}")
        print(f"   - Confluence Space: {settings.confluence_space or '[ERROR]未設定'}")
        
    except Exception as e:
        print(f"[ERROR] 設定ファイル読み込みエラー: {e}")
        return False
    
    print()
    
    # Step 2: 設定検証
    print("[INFO] Step 2: 設定検証")
    print("-" * 40)
    
    atlassian_valid = settings.validate_atlassian_config()
    gemini_valid = settings.validate_gemini_config()
    
    print(f"   - Atlassian API: {'[OK]' if atlassian_valid else '[ERROR]'}")
    print(f"   - Gemini API: {'[OK]' if gemini_valid else '[ERROR]'}")
    
    if not atlassian_valid:
        print("\n[ERROR] Atlassian設定が不完全です")
        print("   config/settings.ini と config/secrets.env を確認してください")
        return False
    
    print()
    
    # Step 3: Jira API接続テスト
    print("[INFO] Step 3: Jira API接続テスト")
    print("-" * 40)
    
    try:
        from atlassian import Jira
        
        jira = Jira(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token,
            cloud=True
        )
        
        # プロジェクト一覧取得
        projects = jira.get_all_projects()
        print(f"[OK] Jira接続成功: プロジェクト数 {len(projects)}")
        
        # 最初の3プロジェクトを表示
        for i, project in enumerate(projects[:3], 1):
            print(f"   {i}. {project['key']} - {project['name']}")
        
        # JQL検索テスト
        search_result = jira.jql("project is not EMPTY ORDER BY created DESC", limit=5)
        issue_count = len(search_result.get('issues', []))
        print(f"[OK] JQL検索テスト: {issue_count} 件のチケット取得")
        
    except ImportError:
        print("[ERROR] atlassian-python-api ライブラリが見つかりません")
        print("   pip install atlassian-python-api を実行してください")
        return False
    except Exception as e:
        print(f"[ERROR] Jira接続エラー: {e}")
        return False
    
    print()
    
    # Step 4: Confluence API接続テスト
    print("[INFO] Step 4: Confluence API接続テスト")
    print("-" * 40)
    
    try:
        from atlassian import Confluence
        
        confluence = Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token,
            cloud=True
        )
        
        # スペース一覧取得
        spaces = confluence.get_all_spaces(limit=10)
        space_list = spaces.get('results', [])
        print(f"[OK] Confluence接続成功: スペース数 {len(space_list)}")
        
        # 最初の5スペースを表示
        for i, space in enumerate(space_list[:5], 1):
            print(f"   {i}. {space['key']} - {space['name']}")
        
        # 指定スペースのページ検索
        if settings.confluence_space:
            try:
                pages = confluence.get_all_pages_from_space(settings.confluence_space, limit=5)
                page_count = len(pages) if pages else 0
                print(f"[OK] 対象スペース '{settings.confluence_space}': {page_count} ページ")
            except Exception as e:
                print(f"[WARN] スペース '{settings.confluence_space}' エラー: {e}")
        
    except Exception as e:
        print(f"[ERROR] Confluence接続エラー: {e}")
        return False
    
    print()
    
    # Step 5: Gemini API接続テスト（オプション）
    print("[INFO] Step 5: Gemini API接続テスト（オプション）")
    print("-" * 40)
    
    if gemini_valid:
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(settings.gemini_model)
            
            response = model.generate_content("Hello, this is a test.")
            print(f"[OK] Gemini API接続成功")
            print(f"   モデル: {settings.gemini_model}")
            
        except ImportError:
            print("[WARN] google-generativeai ライブラリが見つかりません（オプション）")
        except Exception as e:
            print(f"[ERROR] Gemini API接続エラー: {e}")
    else:
        print("[WARN] Gemini APIキーが未設定（オプション）")
    
    print()
    print("[SUCCESS] 全ての必須テストが完了しました！")
    return True

def main():
    """メイン実行"""
    print("=" * 60)
    print("Atlassian API 総合接続テスト")
    print("=" * 60)
    
    success = test_atlassian_connection()
    
    print("\n" + "=" * 60)
    print("テスト結果")
    print("=" * 60)
    
    if success:
        print("[SUCCESS] 全ての接続テストが成功しました！")
        print("   システムは正常に動作する準備ができています。")
    else:
        print("[ERROR] 接続テストが失敗しました。")
        print("   設定を確認して再度実行してください。")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 