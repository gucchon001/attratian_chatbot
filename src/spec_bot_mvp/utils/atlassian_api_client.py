"""
実際のJira/Confluence APIに接続して検索を実行

spec_bot/の成功パターンに合わせて、atlassianライブラリを使用
"""

import logging
import time
from typing import Dict, List, Any, Optional
from atlassian import Confluence, Jira

logger = logging.getLogger(__name__)

class AtlassianAPIClient:
    """Atlassian (Jira/Confluence) API接続クライアント
    
    spec_bot/の成功パターンに合わせてatlassianライブラリを使用
    """
    
    def __init__(self, jira_url: str, jira_username: str, jira_token: str, 
                 confluence_url: str, confluence_username: str, confluence_token: str):
        """
        Atlassian API クライアントの初期化
        
        Args:
            jira_url: JiraインスタンスURL
            jira_username: Jiraユーザー名（通常はメールアドレス）
            jira_token: Jira APIトークン
            confluence_url: ConfluenceインスタンスURL
            confluence_username: Confluenceユーザー名（通常はメールアドレス）
            confluence_token: Confluence APIトークン
        """
        # Atlassianライブラリを使用したクライアント初期化（spec_bot成功パターン）
        try:
            self.jira = Jira(
                url=jira_url,
                username=jira_username,
                password=jira_token
            )
            
            self.confluence = Confluence(
                url=confluence_url,
                username=confluence_username,
                password=confluence_token
            )
            
            self.jira_url = jira_url
            self.confluence_url = confluence_url
            
            logger.info(f"AtlassianAPIClient初期化完了")
            logger.info(f"  - Jira URL: {jira_url}")
            logger.info(f"  - Confluence URL: {confluence_url}")
            
        except Exception as e:
            logger.error(f"AtlassianAPIClient初期化失敗: {e}")
            raise
    
    def test_connection(self) -> Dict[str, bool]:
        """API接続テスト（atlassianライブラリ使用）"""
        result = {
            "jira": False,
            "confluence": False
        }
        
        # Jira接続テスト
        try:
            myself = self.jira.myself()
            result["jira"] = bool(myself and isinstance(myself, dict))
            if result["jira"]:
                user_name = myself.get('displayName', 'Unknown')
                logger.info(f"Jira接続成功: {user_name}")
            else:
                logger.error("Jira接続失敗: 不正な応答")
        except Exception as e:
            logger.error(f"Jira接続エラー: {e}")
            
        # Confluence接続テスト
        try:
            # atlassianライブラリの正しいメソッドを使用
            spaces = self.confluence.get_all_spaces(start=0, limit=1)
            result["confluence"] = bool(spaces and 'results' in spaces)
            if result["confluence"]:
                logger.info(f"Confluence接続成功: スペース一覧取得")
            else:
                logger.error("Confluence接続失敗: 不正な応答")
        except Exception as e:
            logger.error(f"Confluence接続エラー: {e}")
            
        return result
    
    def search_jira(self, keywords: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
        """実際のJira検索実行（atlassianライブラリ使用）"""
        try:
            # JQLクエリ構築
            search_terms = []
            for keyword in keywords:
                if keyword.strip():
                    search_terms.append(f'text ~ "{keyword}"')
            
            if not search_terms:
                return []
                
            jql = " AND ".join(search_terms)
            jql += " ORDER BY updated DESC"
            
            logger.info(f"Jira検索実行: JQL='{jql}'")
            start_time = time.time()
            
            # atlassianライブラリでJQL検索実行
            search_results = self.jira.jql(jql, limit=max_results)
            search_time = time.time() - start_time
            
            if not search_results or 'issues' not in search_results:
                logger.warning(f"Jira検索結果なし: クエリ='{keywords}' | 実行時間: {search_time:.2f}秒")
                return []
            
            issues = search_results['issues']
            
            # 結果を統一フォーマットに変換
            formatted_results = []
            for issue in issues:
                fields = issue.get("fields", {})
                formatted_result = {
                    "id": issue.get("key"),
                    "title": fields.get("summary", ""),
                    "description": self._extract_description(fields),
                    "type": fields.get("issuetype", {}).get("name", ""),
                    "status": fields.get("status", {}).get("name", ""),
                    "priority": fields.get("priority", {}).get("name", ""),
                    "created": fields.get("created", ""),
                    "updated": fields.get("updated", ""),
                    "datasource": "jira",
                    "url": f"{self.jira_url}/browse/{issue.get('key')}"
                }
                formatted_results.append(formatted_result)
            
            logger.info(f"Jira検索完了: {len(formatted_results)}件取得 | 実行時間: {search_time:.2f}秒")
            return formatted_results
                
        except Exception as e:
            logger.error(f"Jira検索エラー: {e}")
            return []
    
    def search_confluence(self, keywords: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
        """実際のConfluence検索実行（atlassianライブラリ使用）"""
        try:
            # CQLクエリ構築（spec_bot成功パターン）
            search_terms = []
            for keyword in keywords:
                if keyword.strip():
                    search_terms.append(f'text ~ "{keyword}"')
            
            if not search_terms:
                return []
                
            cql = " AND ".join(search_terms)
            cql += " AND type = page"
            cql += " ORDER BY lastModified DESC"
            
            logger.info(f"Confluence検索実行: CQL='{cql}'")
            start_time = time.time()
            
            # atlassianライブラリでCQL検索実行
            search_results = self.confluence.cql(cql, limit=max_results)
            search_time = time.time() - start_time
            
            if not search_results or 'results' not in search_results:
                logger.warning(f"Confluence検索結果なし: クエリ='{keywords}' | 実行時間: {search_time:.2f}秒")
                return []
            
            results = search_results['results']
            total_count = search_results.get('totalSize', 0)
            
            # 結果を統一フォーマットに変換
            formatted_results = []
            for result in results:
                try:
                    content = result.get('content', {})
                    
                    formatted_result = {
                        "id": content.get("id"),
                        "title": content.get("title", ""),
                        "description": self._extract_confluence_body(content),
                        "space": content.get("space", {}).get("key", ""),
                        "space_name": content.get("space", {}).get("name", ""),
                        "type": "page",
                        "created": content.get("history", {}).get("createdDate", ""),
                        "updated": content.get("version", {}).get("when", ""),
                        "datasource": "confluence",
                        "url": f"{self.confluence_url}/pages/viewpage.action?pageId={content.get('id')}"
                    }
                    formatted_results.append(formatted_result)
                    
                except Exception as e:
                    logger.warning(f"Confluence結果変換エラー: {e}")
                    continue
            
            logger.info(f"Confluence検索完了: {len(formatted_results)}件取得 | 実行時間: {search_time:.2f}秒")
            return formatted_results
                
        except Exception as e:
            logger.error(f"Confluence検索エラー: {e}")
            return []
    
    def _extract_description(self, fields: Dict[str, Any]) -> str:
        """Jiraの説明フィールドを抽出"""
        try:
            description = fields.get("description")
            if isinstance(description, dict):
                # Atlassian Document Format
                content = description.get("content", [])
                if content and isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("content"):
                            for subitem in item["content"]:
                                if isinstance(subitem, dict) and subitem.get("text"):
                                    text_parts.append(subitem["text"])
                    return " ".join(text_parts)[:200]
            elif isinstance(description, str):
                return description[:200]
            return ""
        except Exception:
            return ""
    
    def _extract_confluence_body(self, content: Dict[str, Any]) -> str:
        """Confluenceのボディコンテンツを抽出"""
        try:
            # excerpt が利用可能な場合はそれを使用
            if 'excerpt' in content:
                return content['excerpt'][:200]
            
            # body から抽出
            body = content.get("body", {})
            if isinstance(body, dict):
                storage = body.get("storage", {})
                if isinstance(storage, dict):
                    import re
                    html_content = storage.get("value", "")
                    # HTMLタグを除去
                    text_content = re.sub(r'<[^>]+>', '', html_content)
                    return text_content[:200]
            
            return ""
        except Exception:
            return "" 