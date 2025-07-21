"""
実際のJira/Confluence APIに接続して検索を実行

以前の動作設定と互換性を保つため、
基本URLから適切なAPIエンドポイントを自動構築
"""

import logging
import requests
import base64
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class AtlassianAPIClient:
    """Atlassian (Jira/Confluence) API接続クライアント
    
    以前の動作設定と互換性を保つため、基本URLから適切なAPIパスを自動構築
    """
    
    def __init__(self, jira_url: str, jira_username: str, jira_token: str, 
                 confluence_url: str, confluence_username: str, confluence_token: str):
        """
        Atlassian API クライアントの初期化
        
        Args:
            jira_url: JiraインスタンスURL（基本URL）
            jira_username: Jiraユーザー名（通常はメールアドレス）
            jira_token: Jira APIトークン
            confluence_url: ConfluenceインスタンスURL（基本URL）
            confluence_username: Confluenceユーザー名（通常はメールアドレス）
            confluence_token: Confluence APIトークン
        """
        # URLの正規化（末尾スラッシュ除去）
        self.jira_url = jira_url.rstrip('/')
        self.jira_username = jira_username
        self.jira_token = jira_token
        
        # Confluence URL処理：以前の動作設定と互換性を保つ
        self.confluence_base_url = confluence_url.rstrip('/')
        # /wiki パスが含まれていない場合は自動追加
        if not self.confluence_base_url.endswith('/wiki'):
            self.confluence_url = f"{self.confluence_base_url}/wiki"
        else:
            self.confluence_url = self.confluence_base_url
            
        self.confluence_username = confluence_username
        self.confluence_token = confluence_token
        
        # 認証ヘッダーの作成
        self.jira_auth = self._create_auth_header(jira_username, jira_token)
        self.confluence_auth = self._create_auth_header(confluence_username, confluence_token)
        
        logger.info(f"AtlassianAPIClient初期化完了")
        logger.info(f"  - Jira URL: {self.jira_url}")
        logger.info(f"  - Confluence URL: {self.confluence_url}")  # /wiki付きのURLをログ出力
    
    def _create_auth_header(self, username: str, token: str) -> str:
        """Basic認証ヘッダーを作成"""
        credentials = f"{username}:{token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"
    
    def test_connection(self) -> Dict[str, bool]:
        """API接続テスト"""
        result = {
            "jira": False,
            "confluence": False
        }
        
        # Jira接続テスト
        try:
            jira_response = requests.get(
                f"{self.jira_url}/rest/api/3/myself",
                headers={
                    "Authorization": self.jira_auth,
                    "Accept": "application/json"
                },
                timeout=10
            )
            result["jira"] = jira_response.status_code == 200
            if result["jira"]:
                user_info = jira_response.json()
                logger.info(f"Jira接続成功: {user_info.get('displayName', 'Unknown')}")
            else:
                logger.error(f"Jira接続失敗: {jira_response.status_code}")
        except Exception as e:
            logger.error(f"Jira接続エラー: {e}")
            
        # Confluence接続テスト
        try:
            confluence_response = requests.get(
                f"{self.confluence_url}/rest/api/user/current",
                headers={
                    "Authorization": self.confluence_auth,
                    "Accept": "application/json"
                },
                timeout=10
            )
            result["confluence"] = confluence_response.status_code == 200
            if result["confluence"]:
                user_info = confluence_response.json()
                logger.info(f"Confluence接続成功: {user_info.get('displayName', 'Unknown')}")
            else:
                logger.error(f"Confluence接続失敗: {confluence_response.status_code}")
        except Exception as e:
            logger.error(f"Confluence接続エラー: {e}")
            
        return result
    
    def search_jira(self, keywords: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
        """実際のJira検索実行"""
        try:
            # JQLクエリ構築
            search_terms = []
            for keyword in keywords:
                if keyword.strip():
                    # テキスト検索：タイトル、説明、コメントから検索
                    search_terms.append(f'text ~ "{keyword}"')
            
            if not search_terms:
                return []
                
            jql = " AND ".join(search_terms)
            # 最近更新されたものを優先
            jql += " ORDER BY updated DESC"
            
            # Jira Search API呼び出し
            search_payload = {
                "jql": jql,
                "maxResults": max_results,
                "fields": ["key", "summary", "description", "status", "priority", "issuetype", "created", "updated"],
                "expand": ["renderedFields"]
            }
            
            response = requests.post(
                f"{self.jira_url}/rest/api/3/search",
                headers={
                    "Authorization": self.jira_auth,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json=search_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                search_results = response.json()
                issues = search_results.get("issues", [])
                
                # 結果を統一フォーマットに変換
                formatted_results = []
                for issue in issues:
                    fields = issue.get("fields", {})
                    formatted_result = {
                        "id": issue.get("key"),
                        "title": fields.get("summary", ""),
                        "description": fields.get("description", {}).get("content", [{}])[0].get("content", [{}])[0].get("text", "")[:200] if fields.get("description") else "",
                        "type": fields.get("issuetype", {}).get("name", ""),
                        "status": fields.get("status", {}).get("name", ""),
                        "priority": fields.get("priority", {}).get("name", ""),
                        "created": fields.get("created", ""),
                        "updated": fields.get("updated", ""),
                        "datasource": "jira",
                        "url": f"{self.jira_url}/browse/{issue.get('key')}"
                    }
                    formatted_results.append(formatted_result)
                
                logger.info(f"Jira検索完了: {len(formatted_results)}件取得")
                return formatted_results
            else:
                logger.error(f"Jira検索失敗: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Jira検索エラー: {e}")
            return []
    
    def search_confluence(self, keywords: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
        """実際のConfluence検索実行"""
        try:
            # CQLクエリ構築
            search_terms = []
            for keyword in keywords:
                if keyword.strip():
                    # テキスト検索：タイトル、本文から検索
                    search_terms.append(f'text ~ "{keyword}"')
            
            if not search_terms:
                return []
                
            cql = " AND ".join(search_terms)
            cql += " AND type = page"  # ページのみ検索
            cql += " ORDER BY lastModified DESC"  # 最近更新されたものを優先
            
            # Confluence Search API呼び出し
            search_params = {
                "cql": cql,
                "limit": max_results,
                "expand": "body.storage,space,history.lastUpdated"
            }
            
            response = requests.get(
                f"{self.confluence_url}/rest/api/content/search",
                headers={
                    "Authorization": self.confluence_auth,
                    "Accept": "application/json"
                },
                params=search_params,
                timeout=30
            )
            
            if response.status_code == 200:
                search_results = response.json()
                pages = search_results.get("results", [])
                
                # 結果を統一フォーマットに変換
                formatted_results = []
                for page in pages:
                    # 本文の最初の200文字を抽出
                    body_content = ""
                    if page.get("body", {}).get("storage", {}).get("value"):
                        import re
                        html_content = page["body"]["storage"]["value"]
                        # HTMLタグを除去して本文のみ抽出
                        text_content = re.sub(r'<[^>]+>', '', html_content)
                        body_content = text_content[:200] + "..." if len(text_content) > 200 else text_content
                    
                    space_info = page.get("space", {})
                    history_info = page.get("history", {})
                    
                    formatted_result = {
                        "id": page.get("id"),
                        "title": page.get("title", ""),
                        "description": body_content,
                        "space": space_info.get("key", ""),
                        "space_name": space_info.get("name", ""),
                        "type": "page",
                        "created": page.get("history", {}).get("createdDate", ""),
                        "updated": history_info.get("lastUpdated", {}).get("when", ""),
                        "datasource": "confluence",
                        "url": f"{self.confluence_url}/pages/viewpage.action?pageId={page.get('id')}"
                    }
                    formatted_results.append(formatted_result)
                
                logger.info(f"Confluence検索完了: {len(formatted_results)}件取得")
                return formatted_results
            else:
                logger.error(f"Confluence検索失敗: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Confluence検索エラー: {e}")
            return [] 