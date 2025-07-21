"""
CQL検索のためのAPI実行器

Confluence REST APIへの実際のリクエスト実行を担当
依存性注入により、テスト時はモック実行器に切り替え可能
"""

import requests
import json
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import logging

from ..config.settings import settings
from ..utils.log_config import get_logger

logger = get_logger(__name__)


class APIExecutor(ABC):
    """API実行器の抽象基底クラス"""
    
    @abstractmethod
    def execute(self, cql: str) -> List[Dict[str, Any]]:
        """
        CQLクエリを実行してConfluence検索結果を取得
        
        Args:
            cql: Confluence Query Language文字列
            
        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        pass


class ConfluenceAPIExecutor(APIExecutor):
    """実際のConfluence REST APIを実行する実行器"""
    
    def __init__(self):
        """Confluence API実行器の初期化"""
        self.base_url = settings.CONFLUENCE_BASE_URL
        self.username = settings.CONFLUENCE_USERNAME
        self.token = settings.CONFLUENCE_TOKEN
        
        if not all([self.base_url, self.username, self.token]):
            raise ValueError("Confluence API設定が不完全です")
    
    def execute(self, cql: str) -> List[Dict[str, Any]]:
        """
        Confluence REST APIでCQLクエリを実行
        
        Args:
            cql: Confluence Query Language文字列
            
        Returns:
            List[Dict[str, Any]]: 検索結果のリスト
        """
        try:
            logger.debug(f"Confluence API実行: CQL='{cql}'")
            
            # Confluence REST API エンドポイント
            url = f"{self.base_url}/rest/api/search"
            
            # 認証ヘッダー
            auth = (self.username, self.token)
            
            # リクエストパラメータ
            params = {
                'cql': cql,
                'limit': 50,  # 適切な制限値
                'expand': 'content.body.storage,content.version,content.space'
            }
            
            # API実行
            response = requests.get(url, auth=auth, params=params, timeout=30)
            response.raise_for_status()
            
            # レスポンス解析
            data = response.json()
            results = data.get('results', [])
            
            logger.debug(f"Confluence API完了: {len(results)}件取得")
            
            # 結果を標準化
            standardized_results = self._standardize_results(results)
            
            return standardized_results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Confluence API実行エラー: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"予期しないエラー: {str(e)}")
            return []
    
    def _standardize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Confluence API結果を標準化
        
        Args:
            results: Confluence APIの生結果
            
        Returns:
            List[Dict[str, Any]]: 標準化された結果
        """
        standardized = []
        
        for result in results:
            try:
                content = result.get('content', {})
                
                # 基本情報の抽出
                item = {
                    'id': content.get('id', 'unknown'),
                    'title': content.get('title', 'タイトル不明'),
                    'type': content.get('type', 'page'),
                    'status': content.get('status', 'current'),
                    'url': self._build_url(content),
                    'space': self._extract_space_info(content),
                    'body': self._extract_body_content(content),
                    'excerpt': result.get('excerpt', ''),
                    'lastModified': self._extract_last_modified(content),
                    'author': self._extract_author(content)
                }
                
                standardized.append(item)
                
            except Exception as e:
                logger.warning(f"結果標準化エラー: {str(e)}")
                continue
        
        return standardized
    
    def _build_url(self, content: Dict[str, Any]) -> str:
        """ページURLを構築"""
        try:
            page_id = content.get('id')
            if page_id:
                return f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
            return self.base_url
        except Exception:
            return self.base_url
    
    def _extract_space_info(self, content: Dict[str, Any]) -> Dict[str, str]:
        """スペース情報を抽出"""
        try:
            space = content.get('space', {})
            return {
                'key': space.get('key', 'unknown'),
                'name': space.get('name', 'Unknown Space')
            }
        except Exception:
            return {'key': 'unknown', 'name': 'Unknown Space'}
    
    def _extract_body_content(self, content: Dict[str, Any]) -> str:
        """ボディコンテンツを抽出"""
        try:
            body = content.get('body', {})
            storage = body.get('storage', {})
            return storage.get('value', '')[:1000]  # 最初の1000文字のみ
        except Exception:
            return ''
    
    def _extract_last_modified(self, content: Dict[str, Any]) -> Optional[str]:
        """最終更新日を抽出"""
        try:
            version = content.get('version', {})
            return version.get('when')
        except Exception:
            return None
    
    def _extract_author(self, content: Dict[str, Any]) -> Dict[str, str]:
        """作成者情報を抽出"""
        try:
            version = content.get('version', {})
            by = version.get('by', {})
            return {
                'username': by.get('username', 'unknown'),
                'displayName': by.get('displayName', 'Unknown User')
            }
        except Exception:
            return {'username': 'unknown', 'displayName': 'Unknown User'}


class MockAPIExecutor(APIExecutor):
    """テスト用のモックAPI実行器"""
    
    def __init__(self, mock_data: Optional[List[Dict[str, Any]]] = None):
        """
        モックAPI実行器の初期化
        
        Args:
            mock_data: 返すモックデータ
        """
        self.mock_data = mock_data or self._default_mock_data()
    
    def execute(self, cql: str) -> List[Dict[str, Any]]:
        """
        モック検索結果を返す
        
        Args:
            cql: CQLクエリ（実際には使用されない）
            
        Returns:
            List[Dict[str, Any]]: モック検索結果
        """
        logger.debug(f"モックAPI実行: CQL='{cql}'")
        
        # CQLに応じて適切なモックデータをフィルタ
        if 'ログイン' in cql:
            return [item for item in self.mock_data if 'ログイン' in item.get('title', '')]
        elif 'title ~' in cql:
            return self.mock_data[:2]  # タイトル検索は少なめ
        else:
            return self.mock_data
    
    def _default_mock_data(self) -> List[Dict[str, Any]]:
        """デフォルトのモックデータ"""
        return [
            {
                'id': 'mock-001',
                'title': '042_【FIX】会員ログイン・ログアウト機能',
                'type': 'page',
                'status': 'current',
                'url': 'https://example.com/pages/001',
                'space': {'key': 'CLIENTTOMO', 'name': 'Client Tomo Space'},
                'body': '会員がサービスサイトにてログイン、ログアウトを行うための機能です。',
                'excerpt': 'ログイン機能の仕様書...',
                'lastModified': '2024-01-01T00:00:00.000Z',
                'author': {'username': 'test_user', 'displayName': 'Test User'}
            },
            {
                'id': 'mock-002',
                'title': '681_【FIX】クライアント企業ログイン・ログアウト機能',
                'type': 'page',
                'status': 'current',
                'url': 'https://example.com/pages/002',
                'space': {'key': 'CLIENTTOMO', 'name': 'Client Tomo Space'},
                'body': 'クライアント企業管理者が、クライアント企業管理画面にログイン/ログアウトするための機能。',
                'excerpt': 'クライアント企業向けログイン...',
                'lastModified': '2024-01-02T00:00:00.000Z',
                'author': {'username': 'test_user', 'displayName': 'Test User'}
            },
            {
                'id': 'mock-003',
                'title': '451_【FIX】全体管理者ログイン・ログアウト機能',
                'type': 'page',
                'status': 'current',
                'url': 'https://example.com/pages/003',
                'space': {'key': 'CLIENTTOMO', 'name': 'Client Tomo Space'},
                'body': '全体管理者が、全体管理画面にログイン/ログアウトするための機能。',
                'excerpt': '全体管理者向けログイン...',
                'lastModified': '2024-01-03T00:00:00.000Z',
                'author': {'username': 'test_user', 'displayName': 'Test User'}
            }
        ] 