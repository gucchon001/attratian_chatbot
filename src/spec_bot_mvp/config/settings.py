"""
Stage1 設定管理

環境変数とAPIキー管理、アプリケーション設定を統合管理
"""

import os
import configparser
from typing import Optional
from pathlib import Path
import streamlit as st

class Settings:
    """Stage1アプリケーション設定管理"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
        self._load_settings_ini()  # settings.ini読み込み追加
        self._load_env_file()  # .envファイル読み込み追加
        self._load_environment()
    
    def _load_env_file(self):
        """config/secrets.envファイルの読み込み"""
        env_files = [
            self.project_root / "config" / "secrets.env",
            self.project_root / ".env"
        ]
        
        for env_file in env_files:
            if env_file.exists():
                try:
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                os.environ[key.strip()] = value.strip()
                    print(f"✅ 環境設定ファイル読み込み完了: {env_file}")
                except Exception as e:
                    print(f"⚠️ 環境設定ファイル読み込み失敗: {env_file} - {e}")
    
    def _load_settings_ini(self):
        """config/settings.iniファイルの読み込み（必須設定）"""
        settings_file = self.project_root / "config" / "settings.ini"
        
        # デフォルト値
        self.gemini_model = "gemini-1.5-flash"
        self.gemini_temperature = 0.3
        self.gemini_max_tokens = 2048
        self.confluence_space = "CLIENTTOMO"
        self.target_project = "CTJ"
        self.domain = "giginc.atlassian.net"
        self.email = "kanri@jukust.jp"
        self.debug = False
        self.log_level = "INFO"
        self.request_timeout = 30
        
        if settings_file.exists():
            try:
                config = configparser.ConfigParser()
                config.read(settings_file, encoding='utf-8')
                
                # Gemini設定
                if 'gemini' in config:
                    self.gemini_model = config.get('gemini', 'model', fallback=self.gemini_model)
                    self.gemini_temperature = config.getfloat('gemini', 'temperature', fallback=self.gemini_temperature)
                    self.gemini_max_tokens = config.getint('gemini', 'max_tokens', fallback=self.gemini_max_tokens)
                
                # Atlassian設定
                if 'atlassian' in config:
                    self.domain = config.get('atlassian', 'domain', fallback=self.domain)
                    self.email = config.get('atlassian', 'email', fallback=self.email)
                    self.confluence_space = config.get('atlassian', 'confluence_space', fallback=self.confluence_space)
                    self.target_project = config.get('atlassian', 'target_project', fallback=self.target_project)
                
                # アプリ設定
                if 'app' in config:
                    self.debug = config.getboolean('app', 'debug', fallback=self.debug)
                    self.log_level = config.get('app', 'log_level', fallback=self.log_level)
                    self.request_timeout = config.getint('app', 'request_timeout', fallback=self.request_timeout)
                
                print(f"✅ settings.ini読み込み完了: {settings_file}")
                print(f"🎯 Geminiモデル: {self.gemini_model} (温度: {self.gemini_temperature})")
                
                # settings.iniからJira/ConfluenceのURLを構築
                self._construct_atlassian_urls()
                
            except Exception as e:
                print(f"⚠️ settings.ini読み込み失敗: {e} - デフォルト値使用")
        else:
            print(f"⚠️ settings.iniが見つかりません: {settings_file} - デフォルト値使用")
    
    def _construct_atlassian_urls(self):
        """settings.iniの情報からAtlassian URLを構築"""
        if self.domain:
            # デフォルトのJira/Confluence URL構築
            if not hasattr(self, 'default_jira_url'):
                self.default_jira_url = f"https://{self.domain}"
            if not hasattr(self, 'default_confluence_url'):
                self.default_confluence_url = f"https://{self.domain}/wiki"
            if not hasattr(self, 'default_username'):
                self.default_username = self.email
            
            print(f"🔗 Atlassian URL構築: {self.default_jira_url}, {self.default_confluence_url}")
    
    def _load_environment(self):
        """環境変数の読み込み（ローカル .env / Streamlit Secrets対応）"""
        try:
            # Streamlit Secrets (本番環境)
            if hasattr(st, 'secrets'):
                self.google_api_key = st.secrets.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
                self.jira_url = st.secrets.get("JIRA_URL")
                self.jira_username = st.secrets.get("JIRA_USERNAME") 
                self.jira_api_token = st.secrets.get("JIRA_API_TOKEN") or st.secrets.get("ATLASSIAN_API_TOKEN")
                self.confluence_url = st.secrets.get("CONFLUENCE_URL")
                self.confluence_username = st.secrets.get("CONFLUENCE_USERNAME")
                self.confluence_api_token = st.secrets.get("CONFLUENCE_API_TOKEN") or st.secrets.get("ATLASSIAN_API_TOKEN")
            else:
                # 環境変数から読み込み（ローカル開発）
                self.google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
                self.jira_url = os.getenv("JIRA_URL") or getattr(self, 'default_jira_url', None)
                self.jira_username = os.getenv("JIRA_USERNAME") or getattr(self, 'default_username', None)
                self.jira_api_token = os.getenv("JIRA_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN")
                self.confluence_url = os.getenv("CONFLUENCE_URL") or getattr(self, 'default_confluence_url', None)
                self.confluence_username = os.getenv("CONFLUENCE_USERNAME") or getattr(self, 'default_username', None)
                self.confluence_api_token = os.getenv("CONFLUENCE_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN")
        except:
            # フォールバック: 環境変数のみ
            self.google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            self.jira_url = os.getenv("JIRA_URL") or getattr(self, 'default_jira_url', None)
            self.jira_username = os.getenv("JIRA_USERNAME") or getattr(self, 'default_username', None)
            self.jira_api_token = os.getenv("JIRA_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN")
            self.confluence_url = os.getenv("CONFLUENCE_URL") or getattr(self, 'default_confluence_url', None)
            self.confluence_username = os.getenv("CONFLUENCE_USERNAME") or getattr(self, 'default_username', None)
            self.confluence_api_token = os.getenv("CONFLUENCE_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN")
    
    def validate_api_keys(self) -> dict:
        """API接続に必要なキーの存在確認"""
        validation_result = {
            "gemini_api": bool(self.google_api_key),
            "jira_api": bool(self.jira_url and self.jira_username and self.jira_api_token),
            "confluence_api": bool(self.confluence_url and self.confluence_username and self.confluence_api_token)
        }
        return validation_result
    
    def get_missing_keys(self) -> list:
        """未設定のAPIキー一覧を取得"""
        missing = []
        if not self.google_api_key:
            missing.append("GOOGLE_API_KEY または GEMINI_API_KEY")
        if not (self.jira_url and self.jira_username and self.jira_api_token):
            missing.extend(["JIRA_URL", "JIRA_USERNAME", "JIRA_API_TOKEN または ATLASSIAN_API_TOKEN"])
        if not (self.confluence_url and self.confluence_username and self.confluence_api_token):
            missing.extend(["CONFLUENCE_URL", "CONFLUENCE_USERNAME", "CONFLUENCE_API_TOKEN または ATLASSIAN_API_TOKEN"])
        return missing

# グローバル設定インスタンス
settings = Settings() 