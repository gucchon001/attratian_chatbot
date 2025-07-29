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
        モック検索結果を返す（動的データ生成版）
        
        Args:
            cql: CQLクエリ
            
        Returns:
            List[Dict[str, Any]]: クエリに関連するモック検索結果
        """
        logger.debug(f"動的モックAPI実行: CQL='{cql}'")
        
        # CQLからキーワードを抽出
        keywords = self._extract_keywords_from_cql(cql)
        
        # キーワードに基づく動的データ生成
        if keywords:
            return self._generate_dynamic_mock_data(keywords)
        else:
            # キーワード抽出失敗時は基本データを返す
            return self._get_basic_mock_data()
    
    def _extract_keywords_from_cql(self, cql: str) -> List[str]:
        """CQLクエリからキーワードを抽出"""
        import re
        keywords = []
        
        # title ~ "keyword" パターンを抽出
        title_matches = re.findall(r'title\s*~\s*["\']([^"\']+)["\']', cql)
        keywords.extend(title_matches)
        
        # text ~ "keyword" パターンを抽出
        text_matches = re.findall(r'text\s*~\s*["\']([^"\']+)["\']', cql)
        keywords.extend(text_matches)
        
        return keywords
    
    def _generate_dynamic_mock_data(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """キーワードに基づく動的モックデータ生成"""
        mock_results = []
        
        for i, keyword in enumerate(keywords[:3]):  # 最大3件
            # キーワード別のタイトル・内容生成
            if "ログイン" in keyword:
                base_title = f"{keyword}機能"
                content = f"{keyword}に関する機能仕様です。認証フローやセキュリティ要件について詳細に記載されています。"
            elif "急募" in keyword:
                base_title = f"{keyword}機能"
                content = f"{keyword}に関する機能仕様です。申込み手続きや管理画面について詳細に記載されています。"
            elif "API" in keyword:
                base_title = f"{keyword}設計書"
                content = f"{keyword}の設計仕様です。エンドポイント定義やレスポンス形式について記載されています。"
            elif "設計" in keyword:
                base_title = f"{keyword}ドキュメント"
                content = f"システムの{keyword}に関する資料です。アーキテクチャや技術仕様について説明されています。"
            else:
                base_title = f"{keyword}仕様書"
                content = f"{keyword}に関する仕様書です。詳細な機能説明と実装要件が記載されています。"
            
            mock_results.append({
                'id': f'dynamic-{i+1}',
                'title': f'{i+1:03d}_【FIX】{base_title}',
                'type': 'page',
                'status': 'current',
                'url': f'https://example.com/pages/dynamic-{i+1}',
                'space': {'key': 'CLIENTTOMO', 'name': 'Client Tomo Space'},
                'body': content,
                'excerpt': f'{keyword}関連の詳細情報...',
                'lastModified': '2024-01-01T00:00:00.000Z',
                'author': {'username': 'system', 'displayName': 'System Generated'}
            })
        
        return mock_results
    
    def _get_basic_mock_data(self) -> List[Dict[str, Any]]:
        """基本的なモックデータ（キーワード抽出失敗時用）"""
        return [
            {
                'id': 'basic-001',
                'title': '001_【FIX】システム基本機能',
                'type': 'page',
                'status': 'current',
                'url': 'https://example.com/pages/basic-001',
                'space': {'key': 'CLIENTTOMO', 'name': 'Client Tomo Space'},
                'body': 'システムの基本機能に関する仕様書です。',
                'excerpt': 'システム基本機能の詳細...',
                'lastModified': '2024-01-01T00:00:00.000Z',
                'author': {'username': 'system', 'displayName': 'System Generated'}
            }
        ]
    
    def _default_mock_data(self) -> List[Dict[str, Any]]:
        """デフォルトのモックデータ（下位互換性のため残存）"""
        # 下位互換性のため残すが、実際にはexecute()で動的生成を使用
        return self._get_basic_mock_data() 