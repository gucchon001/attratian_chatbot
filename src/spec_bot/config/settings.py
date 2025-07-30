"""
アプリケーション設定管理

環境変数やStreamlit Secretsからの設定読み込みを統一的に管理します。
"""

import os
import configparser
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

class Settings:
    """設定管理クラス"""
    
    def __init__(self):
        self._config = configparser.ConfigParser()
        self._load_config()
        self._load_secrets()
    
    def _load_config(self):
        """設定ファイル（非機密情報）を読み込み"""
        config_dir = Path(__file__).parent
        ini_file = config_dir / "settings.ini"
        
        if ini_file.exists():
            self._config.read(ini_file, encoding='utf-8')
        else:
            raise FileNotFoundError(f"設定ファイルが見つかりません: {ini_file}")
    
    def _load_secrets(self):
        """秘匿情報を環境変数またはsecrets.envから読み込み"""
        # configディレクトリのsecrets.envファイルを読み込み
        config_dir = Path(__file__).parent
        secrets_file = config_dir / "secrets.env"
        
        if secrets_file.exists():
            load_dotenv(secrets_file)
    
    # Atlassian設定
    @property
    def atlassian_domain(self) -> str:
        return self._config.get('atlassian', 'domain', fallback='')
    
    @property
    def atlassian_email(self) -> str:
        return self._config.get('atlassian', 'email', fallback='')
    
    @property
    def atlassian_api_token(self) -> str:
        """Atlassian API トークン（secrets.envまたは環境変数から取得）"""
        return os.getenv('ATLASSIAN_API_TOKEN', '')
    
    @property
    def confluence_space(self) -> str:
        return self._config.get('atlassian', 'confluence_space', fallback='')
    
    # Gemini設定
    @property
    def gemini_api_key(self) -> str:
        """Gemini API キー（secrets.envまたは環境変数から取得）"""
        return os.getenv('GEMINI_API_KEY', '')
    
    @property
    def gemini_model(self) -> str:
        return self._config.get('gemini', 'model', fallback='gemini-2.0-flash-exp')
    
    @property
    def gemini_temperature(self) -> float:
        return self._config.getfloat('gemini', 'temperature', fallback=0.7)
    
    @property
    def gemini_max_tokens(self) -> int:
        return self._config.getint('gemini', 'max_tokens', fallback=2048)
    
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
    
    # 除外フィルター設定（CQL検索用）
    @property
    def cql_exclusion_patterns(self) -> list:
        """CQLクエリレベルでの直接除外パターンリスト"""
        patterns_str = self._config.get('exclusion_filters', 'cql_exclusion_patterns', fallback='%%削除%%,%%廃止%%')
        return [pattern.strip() for pattern in patterns_str.split(',') if pattern.strip()]
    
    @property
    def hierarchy_exclusion_patterns(self) -> list:
        """階層管理での除外パターンリスト"""
        patterns_str = self._config.get('exclusion_filters', 'hierarchy_exclusion_patterns', fallback='【%%削除%%】,【%%廃止%%】,【%%クローズ%%】')
        return [pattern.strip() for pattern in patterns_str.split(',') if pattern.strip()]

# グローバル設定インスタンス
settings = Settings() 