"""
Stage1 設定管理

環境変数とAPIキー管理、アプリケーション設定を統合管理
"""

import os
from typing import Optional
from pathlib import Path
import streamlit as st

class Settings:
    """Stage1アプリケーション設定管理"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent.parent
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
                self.jira_url = os.getenv("JIRA_URL")
                self.jira_username = os.getenv("JIRA_USERNAME")
                self.jira_api_token = os.getenv("JIRA_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN")
                self.confluence_url = os.getenv("CONFLUENCE_URL")
                self.confluence_username = os.getenv("CONFLUENCE_USERNAME")
                self.confluence_api_token = os.getenv("CONFLUENCE_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN")
        except:
            # フォールバック: 環境変数のみ
            self.google_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            self.jira_url = os.getenv("JIRA_URL")
            self.jira_username = os.getenv("JIRA_USERNAME")
            self.jira_api_token = os.getenv("JIRA_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN")
            self.confluence_url = os.getenv("CONFLUENCE_URL") 
            self.confluence_username = os.getenv("CONFLUENCE_USERNAME")
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