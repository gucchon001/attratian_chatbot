"""
Gemini API 疎通確認テスト

このテストは、Google Gemini API への接続と基本的な動作を確認します。
"""

import pytest
import os
from unittest.mock import patch, MagicMock

# プロジェクトのルートパスを追加
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.spec_bot.config.settings import settings

def test_gemini_api_connection():
    """Gemini API接続テスト"""
    
    # Gemini API設定が無効な場合はスキップ
    if not settings.validate_gemini_config():
        pytest.skip("Gemini API設定が無効です - config/secrets.envにGEMINI_API_KEYを設定してください")
    
    try:
        import google.generativeai as genai
        
        # API設定
        genai.configure(api_key=settings.gemini_api_key)
        
        # モデルのテスト
        model = genai.GenerativeModel(settings.gemini_model)
        
        # 簡単なテストプロンプト
        response = model.generate_content("Hello, this is a connection test.")
        
        # レスポンスの検証
        assert response is not None
        assert response.text is not None
        assert len(response.text) > 0
        
        print(f"✅ Gemini API接続成功")
        print(f"   モデル: {settings.gemini_model}")
        print(f"   温度設定: {settings.gemini_temperature}")
        print(f"   最大トークン数: {settings.gemini_max_tokens}")
        print(f"   レスポンス: {response.text[:100]}...")
        
    except ImportError as e:
        pytest.fail(f"Gemini API ライブラリがインストールされていません: {e}")
    except Exception as e:
        pytest.fail(f"Gemini API接続エラー: {e}")

def test_gemini_settings_validation():
    """Gemini設定の検証テスト"""
    
    # API キーが設定されているかチェック
    api_key = settings.gemini_api_key
    
    if api_key and api_key != "your_gemini_api_key_here":
        assert len(api_key.strip()) > 0, "Gemini API キーが空です"
        print(f"✅ Gemini API キー設定済み (長さ: {len(api_key)} 文字)")
    else:
        print("⏭️ Gemini API キー未設定 - 実際のAPIテストをスキップします")
        print("   → config/secrets.envファイルでGEMINI_API_KEY=your_actual_api_keyを設定してください")
    
    # 設定項目の検証
    model = settings.gemini_model
    assert model is not None, "Gemini モデル名が設定されていません"
    assert len(model.strip()) > 0, "Gemini モデル名が空です"
    
    temperature = settings.gemini_temperature
    assert 0.0 <= temperature <= 2.0, f"温度設定が範囲外です: {temperature}"
    
    max_tokens = settings.gemini_max_tokens
    assert max_tokens > 0, f"最大トークン数が無効です: {max_tokens}"
    
    print(f"✅ Gemini設定検証成功")
    print(f"   モデル: {model}")
    print(f"   温度: {temperature}")
    print(f"   最大トークン数: {max_tokens}")

if __name__ == "__main__":
    print("Gemini API 接続テストを実行中...")
    
    try:
        test_gemini_settings_validation()
        test_gemini_api_connection()
        print("\n🎉 全てのGemini API テストが完了しました！")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        sys.exit(1) 