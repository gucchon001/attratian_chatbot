"""
Stage1 設定管理

環境変数とAPIキー管理、アプリケーション設定を統一的に管理
spec_bot/の成功パターンに合わせて修正
"""

import os
import configparser
from typing import Optional
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

class Settings:
    """Stage1アプリケーション設定管理"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self._config = configparser.ConfigParser()
        self._load_config()
        self._load_secrets()
        # _construct_atlassian_urls()を削除 - すべてプロパティで処理
    
    def _load_config(self):
        """設定ファイル（非機密情報）を読み込み"""
        settings_file = self.project_root / "config" / "settings.ini"
        
        if settings_file.exists():
            self._config.read(settings_file, encoding='utf-8')
            print(f"✅ settings.ini読み込み完了: {settings_file}")
        else:
            raise FileNotFoundError(f"設定ファイルが見つかりません: {settings_file}")
    
    def _load_secrets(self):
        """秘匿情報を環境変数またはsecrets.envから読み込み（spec_bot成功パターン）"""
        # configディレクトリのsecrets.envファイルを読み込み
        secrets_file = self.project_root / "config" / "secrets.env"
        
        if secrets_file.exists():
            load_dotenv(secrets_file)
            print(f"✅ 環境設定ファイル読み込み完了: {secrets_file}")
        else:
            print(f"⚠️ secrets.envファイルが見つかりません: {secrets_file}")
    
    # Atlassian設定（spec_bot互換）
    @property
    def atlassian_email(self) -> str:
        return self._config.get('atlassian', 'email', fallback='kanri@jukust.jp')
    
    @property
    def atlassian_api_token(self) -> str:
        """Atlassian API トークン（secrets.envまたは環境変数から取得）"""
        return os.getenv('ATLASSIAN_API_TOKEN', '')
    
    @property
    def atlassian_domain(self) -> str:
        return self._config.get('atlassian', 'domain', fallback='giginc.atlassian.net')
    
    @property
    def confluence_space(self) -> str:
        return self._config.get('atlassian', 'confluence_space', fallback='CLIENTTOMO')
    
    @property
    def jira_url(self) -> str:
        return f"https://{self.atlassian_domain}"
    
    @property
    def confluence_url(self) -> str:
        return f"https://{self.atlassian_domain}"
    
    # Gemini設定
    @property
    def gemini_model(self) -> str:
        """Gemini モデル名（settings.iniから取得）"""
        return self._config.get('gemini', 'model', fallback='gemini-2.5-flash')
    
    @property
    def gemini_temperature(self) -> float:
        return self._config.getfloat('gemini', 'temperature', fallback=0.3)
    
    @property
    def gemini_max_tokens(self) -> int:
        return self._config.getint('gemini', 'max_tokens', fallback=2048)
    
    @property
    def gemini_api_key(self) -> str:
        """Gemini API キー（secrets.envまたは環境変数から取得）"""
        return os.getenv('GEMINI_API_KEY', '')
    
    # アプリ設定
    @property
    def debug(self) -> bool:
        return self._config.getboolean('app', 'debug', fallback=False)
    
    @property
    def log_level(self) -> str:
        return self._config.get('app', 'log_level', fallback='INFO')
    
    @property
    def request_timeout(self) -> int:
        return self._config.getint('app', 'request_timeout', fallback=30)
    
    def validate_atlassian_config(self) -> bool:
        """Atlassian設定の検証"""
        required_fields = [
            self.atlassian_domain,
            self.atlassian_email,
            self.atlassian_api_token
        ]
        return all(field.strip() for field in required_fields)
    
    def validate_gemini_config(self) -> bool:
        """Gemini設定の検証"""
        return bool(self.gemini_api_key.strip()) 