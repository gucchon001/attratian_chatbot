#!/usr/bin/env python3
"""
現在のシステム（spec_bot）でAtlassian接続テスト

現在の設定システムでテスト実行
"""

import os
import sys
import requests
import logging
from pathlib import Path

# ログレベルを設定
logging.basicConfig(level=logging.INFO)

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_current_system_connection():
    """現在のシステムでAtlassian接続テスト"""
    
    print("[INFO] 現在のシステム（spec_bot）でAtlassian接続テスト開始\n")
    
    try:
        from spec_bot.config.settings import settings
        
        print("=== 現在のシステム設定情報:")
        print(f"   - Atlassian Domain: {settings.atlassian_domain}")
        print(f"   - Atlassian Email: {settings.atlassian_email}")
        print(f"   - Confluence Space: {settings.confluence_space}")
        
        # APIトークンは長さのみ表示（セキュリティ考慮）
        token = settings.atlassian_api_token
        if token:
            print(f"   - API Token: 設定済み (長さ: {len(token)} 文字)")
        else:
            print(f"   - API Token: 未設定")
        print()
        
        # 設定検証
        if not settings.validate_atlassian_config():
            print("[ERROR] 必要な設定情報が不足しています")
            return False
        
        print("[INFO] テスト実行:")
        
        # Atlassian API直接テスト
        print("1. Atlassian API直接接続テスト")
        
        # Jiraテスト
        print("   - Jira API テスト中...")
        from atlassian import Jira
        
        jira = Jira(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token,
            cloud=True
        )
        
        # プロジェクト取得テスト
        projects = jira.get_all_projects()
        print(f"   [OK] Jira接続成功: プロジェクト数 {len(projects)}")
        
        # Confluenceテスト
        print("   - Confluence API テスト中...")
        from atlassian import Confluence
        
        confluence = Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token,
            cloud=True
        )
        
        # スペース取得テスト
        spaces = confluence.get_all_spaces(limit=5)
        space_count = len(spaces.get('results', []))
        print(f"   [OK] Confluence接続成功: スペース数 {space_count}")
        
        # 指定スペーステスト
        if settings.confluence_space:
            try:
                pages = confluence.get_all_pages_from_space(settings.confluence_space, limit=1)
                page_count = len(pages) if pages else 0
                print(f"   [OK] 対象スペース '{settings.confluence_space}' 確認: ページ数 {page_count}")
            except Exception as e:
                print(f"   [WARN] スペース '{settings.confluence_space}' エラー: {e}")
        
        print("\n2. 基本検索テスト")
        
        # Jira検索テスト
        try:
            search_result = jira.jql("project is not EMPTY ORDER BY created DESC", limit=3)
            issue_count = len(search_result.get('issues', []))
            print(f"   [OK] Jira検索テスト成功: チケット {issue_count} 件")
        except Exception as e:
            print(f"   [WARN] Jira検索テストエラー: {e}")
        
        # Confluence検索テスト
        try:
            if settings.confluence_space:
                search_result = confluence.cql(f"space = {settings.confluence_space}", limit=3)
                result_count = len(search_result.get('results', []))
                print(f"   [OK] Confluence検索テスト成功: ページ {result_count} 件")
        except Exception as e:
            print(f"   [WARN] Confluence検索テストエラー: {e}")
        
        print("\n[OK] 全ての接続テストが完了しました！")
        return True
        
    except ImportError as e:
        print(f"[ERROR] ライブラリインポートエラー: {e}")
        print("   必要なライブラリをインストールしてください:")
        print("   pip install atlassian-python-api")
        return False
        
    except Exception as e:
        print(f"[ERROR] 接続テスト失敗: {e}")
        return False


def test_gemini_connection():
    """Gemini API接続テスト"""
    print("\n[INFO] Gemini API接続テスト")
    print("-" * 50)
    
    try:
        from spec_bot.config.settings import settings
        
        if not settings.validate_gemini_config():
            print("[WARN] Gemini APIキーが設定されていません - スキップ")
            return True
        
        print(f"   - Gemini APIキー: 設定済み (長さ: {len(settings.gemini_api_key)} 文字)")
        print(f"   - モデル: {settings.gemini_model}")
        
        # Gemini接続テスト
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(settings.gemini_model)
            
            response = model.generate_content("Hello")
            print(f"   [OK] Gemini API接続成功")
            return True
            
        except ImportError:
            print("   [WARN] google-generativeai ライブラリが未インストール - スキップ")
            return True
        except Exception as e:
            print(f"   [ERROR] Gemini API接続エラー: {e}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Gemini設定エラー: {e}")
        return False


def main():
    """メイン実行"""
    print("=" * 60)
    print("仕様書作成支援ボット - システム接続テスト")
    print("=" * 60)
    
    # Atlassian接続テスト
    atlassian_ok = test_current_system_connection()
    
    # Gemini接続テスト（オプション）
    gemini_ok = test_gemini_connection()
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    print(f"Atlassian接続: {'成功' if atlassian_ok else '失敗'}")
    print(f"Gemini接続: {'成功' if gemini_ok else '失敗'} (オプション)")
    
    if atlassian_ok:
        print("\n[SUCCESS] 必須テストが成功しました！")
        print("   システムは正常に動作する準備ができています。")
    else:
        print("\n[ERROR] 必須テストが失敗しました。")
        print("   config/settings.ini と config/secrets.env を確認してください。")
    
    print("=" * 60)


if __name__ == "__main__":
    main() 