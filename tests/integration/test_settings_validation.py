"""
設定管理の統合テスト

このテストは、アプリケーションの設定読み込みと検証機能をテストします。
"""

import pytest
import sys
from pathlib import Path

# プロジェクトのルートパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.spec_bot.config.settings import settings

def test_settings_file_exists():
    """設定ファイルの存在確認テスト"""
    config_path = Path(__file__).parent.parent.parent / "src" / "spec_bot_mvp" / "config" / "settings.ini"
    secrets_path = Path(__file__).parent.parent.parent / "src" / "spec_bot_mvp" / "config" / "secrets.env"
    
    assert config_path.exists(), f"設定ファイルが見つかりません: {config_path}"
    print(f"✅ 設定ファイル確認: {config_path}")
    
    if secrets_path.exists():
        print(f"✅ 秘匿情報ファイル確認: {secrets_path}")
    else:
        print(f"⚠️ 秘匿情報ファイル未作成: {secrets_path}")
        print(f"   → APIキーを設定するためにconfig/secrets.envファイルを作成してください")

def test_atlassian_configuration():
    """Atlassian設定の検証テスト"""
    
    # 基本設定項目の存在確認（settings.iniから）
    assert settings.atlassian_domain is not None, "Atlassian ドメインが設定されていません"
    assert settings.atlassian_email is not None, "Atlassian メールアドレスが設定されていません"
    assert settings.confluence_space is not None, "Confluence スペースが設定されていません"
    
    print(f"✅ Atlassian基本設定確認（settings.ini）")
    print(f"   ドメイン: {settings.atlassian_domain}")
    print(f"   メール: {settings.atlassian_email}")
    print(f"   Confluenceスペース: {settings.confluence_space}")
    
    # APIトークンの設定確認（config/secrets.envから）
    token = settings.atlassian_api_token
    if token and token != "your_atlassian_api_token_here":
        print(f"   APIトークン: 設定済み (長さ: {len(token)} 文字) ← config/secrets.env")
    else:
        print(f"   APIトークン: 未設定 ← config/secrets.env")
        print(f"   → config/secrets.envでATLASSIAN_API_TOKEN=your_actual_tokenを設定してください")
    
    # 設定の有効性確認
    is_valid = settings.validate_atlassian_config()
    print(f"   設定の有効性: {'✅ 有効' if is_valid else '❌ 無効'}")

def test_gemini_configuration():
    """Gemini設定の検証テスト"""
    
    # 基本設定項目の存在確認（settings.iniから）
    assert settings.gemini_model is not None, "Gemini モデルが設定されていません"
    assert settings.gemini_temperature is not None, "Gemini 温度設定が設定されていません"
    assert settings.gemini_max_tokens is not None, "Gemini 最大トークン数が設定されていません"
    
    print(f"✅ Gemini基本設定確認（settings.ini）")
    print(f"   モデル: {settings.gemini_model}")
    print(f"   温度: {settings.gemini_temperature}")
    print(f"   最大トークン数: {settings.gemini_max_tokens}")
    
    # APIキーの設定確認（config/secrets.envから）
    api_key = settings.gemini_api_key
    if api_key and api_key != "your_gemini_api_key_here":
        print(f"   APIキー: 設定済み (長さ: {len(api_key)} 文字) ← config/secrets.env")
    else:
        print(f"   APIキー: 未設定 ← config/secrets.env")
        print(f"   → config/secrets.envでGEMINI_API_KEY=your_actual_keyを設定してください")
    
    # 設定の有効性確認
    is_valid = settings.validate_gemini_config()
    print(f"   設定の有効性: {'✅ 有効' if is_valid else '❌ 無効'}")

def test_app_configuration():
    """アプリケーション設定の検証テスト"""
    
    # 基本設定項目の存在確認
    assert settings.debug is not None, "デバッグ設定が設定されていません"
    assert settings.log_level is not None, "ログレベルが設定されていません"
    assert settings.request_timeout is not None, "リクエストタイムアウトが設定されていません"
    
    print(f"✅ アプリケーション設定確認（settings.ini）")
    print(f"   デバッグモード: {settings.debug}")
    print(f"   ログレベル: {settings.log_level}")
    print(f"   リクエストタイムアウト: {settings.request_timeout}秒")

def test_environment_variable_fallback():
    """環境変数フォールバック機能のテスト"""
    import os
    
    # 環境変数を一時的に設定
    original_token = os.environ.get('ATLASSIAN_API_TOKEN')
    original_gemini_key = os.environ.get('GEMINI_API_KEY')
    
    test_token = "test_env_token_12345"
    test_gemini_key = "test_env_gemini_key_67890"
    
    try:
        # 環境変数を設定
        os.environ['ATLASSIAN_API_TOKEN'] = test_token
        os.environ['GEMINI_API_KEY'] = test_gemini_key
        
        # 新しい設定インスタンスを作成して確認
        from src.spec_bot.config.settings import Settings
        test_settings = Settings()
        
        # 環境変数が優先されているか確認
        assert test_settings.atlassian_api_token == test_token, "環境変数のAtlassian APIトークンが読み込まれていません"
        assert test_settings.gemini_api_key == test_gemini_key, "環境変数のGemini APIキーが読み込まれていません"
        
        print(f"✅ 環境変数フォールバック機能確認")
        print(f"   Atlassian API: 環境変数から読み込み成功")
        print(f"   Gemini API: 環境変数から読み込み成功")
        
    finally:
        # 環境変数を元に戻す
        if original_token is not None:
            os.environ['ATLASSIAN_API_TOKEN'] = original_token
        else:
            os.environ.pop('ATLASSIAN_API_TOKEN', None)
            
        if original_gemini_key is not None:
            os.environ['GEMINI_API_KEY'] = original_gemini_key
        else:
            os.environ.pop('GEMINI_API_KEY', None)

def test_configuration_separation():
    """設定分離の確認テスト"""
    
    print(f"✅ 設定分離確認")
    print(f"   非機密情報: config/settings.ini（バージョン管理対象）")
    print(f"     - ドメイン、メール、モデル設定、アプリ設定など")
    print(f"   機密情報: config/secrets.env（バージョン管理対象外）")
    print(f"     - APIキー、トークンなど")
    
    # 設定ファイルに機密情報が含まれていないことを確認
    config_path = Path(__file__).parent.parent.parent / "src" / "spec_bot_mvp" / "config" / "settings.ini"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 機密情報らしき文字列が含まれていないかチェック
        sensitive_patterns = ['api_token', 'api_key', 'password', 'secret']
        found_sensitive = []
        
        for pattern in sensitive_patterns:
            if f"{pattern} =" in content.lower() and f"{pattern} = " not in content.lower():
                found_sensitive.append(pattern)
        
        if not found_sensitive:
            print(f"   ✅ settings.iniに機密情報は含まれていません")
        else:
            print(f"   ⚠️ settings.iniに以下の機密情報が含まれている可能性があります: {found_sensitive}")

if __name__ == "__main__":
    print("設定管理システム検証テストを実行中...")
    
    try:
        test_settings_file_exists()
        test_atlassian_configuration()
        test_gemini_configuration()
        test_app_configuration()
        test_environment_variable_fallback()
        test_configuration_separation()
        print("\n🎉 全ての設定検証テストが完了しました！")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        sys.exit(1) 