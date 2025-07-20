"""
アプリケーション定数定義

アプリケーション全体で使用する定数を集約管理します。
プロンプト設定はYAMLファイルから動的読み込みします。
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PromptManager:
    """プロンプト管理クラス - YAMLファイルからプロンプトを読み込み"""
    
    def __init__(self):
        self._prompts: Dict[str, Any] = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """プロンプトYAMLファイルを読み込み"""
        try:
            config_dir = Path(__file__).parent
            prompts_file = config_dir / "prompts.yaml"
            
            if prompts_file.exists():
                with open(prompts_file, 'r', encoding='utf-8') as f:
                    self._prompts = yaml.safe_load(f)
                logger.info(f"プロンプト設定を読み込みました: {prompts_file}")
            else:
                logger.warning(f"プロンプトファイルが見つかりません: {prompts_file}")
                self._use_fallback_prompts()
                
        except Exception as e:
            logger.error(f"プロンプト読み込みエラー: {e}")
            self._use_fallback_prompts()
    
    def _use_fallback_prompts(self):
        """フォールバック用のプロンプト（最小限）"""
        self._prompts = {
            'agent': {
                'system_message': '仕様書作成支援ボットです。JiraとConfluenceから情報を検索してお答えします。',
                'react_template': 'Question: {input}\nThought: {agent_scratchpad}'
            },
            'tools': {},
            'ui': {
                'welcome_message': 'こんにちは！仕様書作成支援ボットです。',
                'error_message': 'エラーが発生しました。'
            }
        }
    
    def get_agent_system_message(self) -> str:
        """エージェントシステムメッセージを取得"""
        return self._prompts.get('agent', {}).get('system_message', '')
    
    def get_react_template(self) -> str:
        """ReActテンプレートを取得"""
        return self._prompts.get('agent', {}).get('react_template', '')
    
    def get_tool_description(self, tool_name: str) -> str:
        """指定ツールの説明文を取得"""
        tools = self._prompts.get('tools', {})
        tool_config = tools.get(tool_name, {})
        return tool_config.get('description', f'{tool_name}ツール')
    
    def get_ui_message(self, message_key: str) -> str:
        """UI関連メッセージを取得"""
        ui_messages = self._prompts.get('ui', {})
        return ui_messages.get(message_key, '')
    
    def get_response_template(self, template_name: str) -> str:
        """応答テンプレートを取得"""
        templates = self._prompts.get('response_templates', {})
        return templates.get(template_name, '')
    
    def get_error_message(self, error_type: str) -> str:
        """エラーメッセージを取得"""
        error_messages = self._prompts.get('error_handling', {})
        return error_messages.get(error_type, 'エラーが発生しました。')
    
    def reload_prompts(self):
        """プロンプトを再読み込み（開発・テスト用）"""
        self._load_prompts()

# グローバルプロンプトマネージャー
prompt_manager = PromptManager()

class APP_CONSTANTS:
    """アプリケーション定数クラス"""
    
    # アプリケーション情報
    APP_NAME = "仕様書作成支援ボット"
    APP_VERSION = "1.0.0"
    APP_EMOJI = "📝"
    
    # UI関連
    class UI:
        @classmethod
        def get_welcome_message(cls):
            return (
                f"🤖 こんにちは！{APP_CONSTANTS.APP_NAME}です。\n\n"
                "JiraやConfluenceから仕様を検索・要約します。\n"
                "まずは検索したいソースを選んで、キーワードを入力してください。"
            )
        
        WELCOME_MESSAGE = "🤖 こんにちは！仕様書作成支援ボットです。\n\nJiraやConfluenceから仕様を検索・要約します。\nまずは検索したいソースを選んで、キーワードを入力してください。"
        
        PLACEHOLDER_TEXT = "検索したいキーワードを入力してください..."
        
        PROCESSING_MESSAGE = "🔍 {sources}から「{query}」について検索中です..."
        
        NO_RESULTS_MESSAGE = "関連する情報は見つかりませんでした。別のキーワードで試してみてください。"
        
        ERROR_MESSAGE = "エラーが発生しました。時間をおいて再試行してください。"
    
    # LangChain関連
    class LANGCHAIN:
        # エージェントのシステムメッセージ（YAMLから動的取得）
        @staticmethod
        def get_agent_system_message() -> str:
            return prompt_manager.get_agent_system_message()
        
        # ReActテンプレート（YAMLから動的取得）
        @staticmethod
        def get_react_template() -> str:
            return prompt_manager.get_react_template()
        
        # 後方互換性のための従来プロパティ
        @property
        def AGENT_SYSTEM_MESSAGE(self) -> str:
            return self.get_agent_system_message()
        
        # メモリ設定
        MEMORY_MAX_TOKEN_LIMIT = 2000
        MEMORY_RETURN_MESSAGES = True
    
    # API関連
    class API:
        # タイムアウト設定（秒）
        REQUEST_TIMEOUT = 30
        
        # リトライ設定
        MAX_RETRIES = 3
        RETRY_DELAY = 1
        
        # Jira検索設定
        JIRA_MAX_RESULTS = 20
        JIRA_SEARCH_FIELDS = "summary,description,status,assignee,created,updated"
        
        # Confluence検索設定
        CONFLUENCE_MAX_RESULTS = 20
        CONFLUENCE_SEARCH_EXPAND = "content.space,content.version"
    
    # ログ関連
    class LOGGING:
        FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
        
        # ログファイル設定
        LOG_FILE = "logs/spec_bot.log"
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        BACKUP_COUNT = 5
    
    # エラーメッセージ
    class ERROR_MESSAGES:
        API_CONNECTION_ERROR = "外部サービスへの接続に失敗しました"
        AUTHENTICATION_ERROR = "認証に失敗しました。設定を確認してください"
        TIMEOUT_ERROR = "処理がタイムアウトしました。時間をおいて再試行してください"
        GENERAL_ERROR = "予期しないエラーが発生しました" 