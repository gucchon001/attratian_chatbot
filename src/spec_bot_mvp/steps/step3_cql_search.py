"""
Step3: CQL検索実行機能（CLIENTTOMO特化最適化版）

3段階検索戦略による効果的な結果取得（精度向上版）
- Strategy1: 厳密検索（AND結合、完全一致重視）+ CLIENTTOMO特化フィルター
- Strategy2: 緩和検索（OR結合、部分一致許可）+ ドメイン知識活用
- Strategy3: 拡張検索（類義語展開、関連語追加）+ 業務文脈考慮

88% → 92%+精度向上のためのCLIENTTOMO特化最適化
外部インターフェース設計書に基づくJQL/CQLクエリ生成
実際のAtlassian API接続対応 (設定により自動切り替え)
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 実際のAPI接続クライアント
try:
    from src.spec_bot_mvp.utils.atlassian_api_client import AtlassianAPIClient
    from src.spec_bot_mvp.config.settings import Settings
    ATLASSIAN_CLIENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Atlassian APIクライアントのインポートに失敗: {e}")
    ATLASSIAN_CLIENT_AVAILABLE = False

logger = logging.getLogger(__name__)

class CQLSearchEngine:
    """Step3: CQL検索実行エンジン (実際のAPI接続対応)"""
    
    def __init__(self):
        self._init_search_strategies()
        self._init_query_builders()
        self._init_api_client()
    
    def _init_api_client(self):
        """API接続クライアント初期化（本番API対応）"""
        try:
            # Settings読み込み
            settings = Settings()
            
            # API設定確認
            if all([
                settings.jira_base_url, settings.jira_username, settings.jira_token,
                settings.confluence_base_url, settings.confluence_username, settings.confluence_token
            ]):
                # 実際のAPI接続を有効化
                self.api_client = AtlassianAPIClient(
                    jira_url=settings.jira_base_url,
                    jira_username=settings.jira_username,
                    jira_token=settings.jira_token,
                    confluence_url=settings.confluence_base_url,
                    confluence_username=settings.confluence_username,
                    confluence_token=settings.confluence_token
                )
                self.use_real_api = True
                logger.info("✅ 本番API接続を有効化")
                
                # 接続テスト
                connection_status = self.api_client.test_connection()
                logger.info(f"🔍 API接続テスト結果: {connection_status}")
                
            else:
                logger.warning("⚠️ API設定が不完全のため模擬データを使用")
                self.api_client = None
                self.use_real_api = False
                
        except Exception as e:
            logger.error(f"❌ API接続初期化失敗: {e}")
            logger.info("🎭 フォールバック: 模擬データを使用")
            self.api_client = None
            self.use_real_api = False
    
    def _init_search_strategies(self):
        """検索戦略の初期化"""
        
        # 3段階検索戦略定義
        self.strategies = {
            "strategy1": {
                "name": "厳密検索",
                "description": "AND結合による高精度検索",
                "operator": "AND",
                "match_type": "exact",
                "max_results": 50,
                "weight": 1.0
            },
            "strategy2": {
                "name": "緩和検索", 
                "description": "OR結合による範囲拡張検索",
                "operator": "OR",
                "match_type": "partial",
                "max_results": 100,
                "weight": 0.8
            },
            "strategy3": {
                "name": "拡張検索",
                "description": "類義語・関連語による包括検索", 
                "operator": "OR",
                "match_type": "expanded",
                "max_results": 150,
                "weight": 0.6
            }
        }
        
        # 類義語・関連語辞書
        self.synonym_dict = {
            "ログイン": ["login", "認証", "サインイン", "authentication"],
            "バグ": ["bug", "不具合", "エラー", "issue", "問題"],
            "API": ["interface", "endpoint", "インターフェース"],
            "UI": ["画面", "ユーザーインターフェース", "フロントエンド"],
            "DB": ["データベース", "database"],
            "テスト": ["test", "testing", "検証", "verification"],
            "仕様": ["spec", "specification", "要件"],
            "設計": ["design", "アーキテクチャ", "architecture"]
        }
    
    def _init_query_builders(self):
        """クエリビルダーの初期化"""
        
        # JQLクエリテンプレート
        self.jql_templates = {
            "basic": "text ~ \"{keywords}\"",
            "with_project": "text ~ \"{keywords}\" AND project = \"{project}\"",
            "with_status": "text ~ \"{keywords}\" AND status IN ({status})",
            "with_type": "text ~ \"{keywords}\" AND issuetype IN ({issuetype})",
            "complex": "text ~ \"{keywords}\" AND project = \"{project}\" AND status IN ({status}) AND issuetype IN ({issuetype})"
        }
        
        # CQLクエリテンプレート
        self.cql_templates = {
            "basic": "text ~ \"{keywords}\"",
            "with_space": "text ~ \"{keywords}\" AND space = \"{space}\"",
            "with_type": "text ~ \"{keywords}\" AND type = \"{content_type}\"",
            "with_date": "text ~ \"{keywords}\" AND created >= \"{date}\"",
            "complex": "text ~ \"{keywords}\" AND space IN ({spaces}) AND type = \"{content_type}\""
        }
    
    def execute_search(self, step2_result: Dict[str, Any], step1_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        CQL検索を実行
        
        Args:
            step2_result: Step2のデータソース判定結果
            step1_result: Step1のキーワード抽出結果
            
        Returns:
            検索結果辞書 {
                "search_results": {データソース別結果},
                "strategies_executed": [実行戦略リスト],
                "query_details": {クエリ詳細},
                "total_results": 総件数,
                "execution_summary": "実行サマリー"
            }
        """
        logger.info("Step3: CQL検索実行開始")
        
        # 検索パラメータ準備
        datasource_priority = step2_result.get("datasource_priority", ["confluence", "jira"])
        search_strategy = step2_result.get("search_strategy", "parallel")
        recommended_filters = step2_result.get("recommended_filters", {})
        
        primary_keywords = step1_result.get("primary_keywords", [])
        secondary_keywords = step1_result.get("secondary_keywords", [])
        search_intent = step1_result.get("search_intent", "一般検索")
        
        # 実行戦略決定
        strategies_to_execute = self._determine_execution_strategies(search_strategy, step2_result)
        
        # データソース別検索実行
        search_results = {}
        query_details = {}
        
        for datasource in datasource_priority:
            if datasource in ["jira", "confluence"]:
                ds_results, ds_queries = self._execute_datasource_search(
                    datasource=datasource,
                    strategies=strategies_to_execute,
                    primary_keywords=primary_keywords,
                    secondary_keywords=secondary_keywords,
                    filters=recommended_filters.get(datasource, {}),
                    search_intent=search_intent
                )
                search_results[datasource] = ds_results
                query_details[datasource] = ds_queries
        
        # 結果統計計算
        total_results = sum(
            len(results.get("combined_results", []))
            for results in search_results.values()
        )
        
        # 実行サマリー生成
        execution_summary = self._generate_execution_summary(
            search_results, strategies_to_execute, datasource_priority[0]
        )
        
        result = {
            "search_results": search_results,
            "strategies_executed": strategies_to_execute,
            "query_details": query_details,
            "total_results": total_results,
            "execution_summary": execution_summary
        }
        
        logger.info(f"Step3完了: {total_results}件の結果を取得")
        return result
    
    def _determine_execution_strategies(self, search_strategy: str, step2_result: Dict[str, Any]) -> List[str]:
        """実行戦略決定"""
        
        if search_strategy == "parallel":
            return ["strategy1", "strategy2"]  # 厳密＋緩和
        elif search_strategy in ["jira_primary", "confluence_primary"]:
            # 優先データソースでは全戦略、補助では厳密のみ
            return ["strategy1", "strategy2", "strategy3"]
        else:
            return ["strategy1"]  # デフォルト
    
    def _execute_datasource_search(self, datasource: str, strategies: List[str], 
                                 primary_keywords: List[str], secondary_keywords: List[str],
                                 filters: Dict[str, Any], search_intent: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """データソース別検索実行"""
        
        results = {"strategy_results": {}, "combined_results": []}
        queries = {}
        
        for strategy_id in strategies:
            strategy = self.strategies[strategy_id]
            
            # キーワード準備
            keywords = self._prepare_keywords_for_strategy(
                strategy_id, primary_keywords, secondary_keywords
            )
            
            # クエリ生成
            query = self._build_query(datasource, keywords, filters, strategy)
            queries[strategy_id] = {
                "query": query,
                "keywords": keywords,
                "strategy": strategy["name"]
            }
            
            # 実際の検索実行（API設定により自動切り替え）
            if self.use_real_api and self.api_client:
                # 実際のAtlassian API検索
                api_results = self._execute_real_api_search(datasource, keywords, strategy)
                results["strategy_results"][strategy_id] = api_results
                results["combined_results"].extend(api_results)
                logger.info(f"✅ 実際のAPI検索完了 ({strategy['name']}): {len(api_results)}件")
            else:
                # 模擬検索（テスト用）
                mock_results = self._execute_mock_search(datasource, query, strategy)
                results["strategy_results"][strategy_id] = mock_results
                results["combined_results"].extend(mock_results)
                logger.info(f"🎭 模擬検索完了 ({strategy['name']}): {len(mock_results)}件")
        
        # 重複除去
        results["combined_results"] = self._deduplicate_results(results["combined_results"])
        
        return results, queries
    
    def _prepare_keywords_for_strategy(self, strategy_id: str, primary_keywords: List[str], 
                                     secondary_keywords: List[str]) -> List[str]:
        """戦略別キーワード準備"""
        
        if strategy_id == "strategy1":  # 厳密検索
            return primary_keywords[:3]  # 主要キーワードのみ
        elif strategy_id == "strategy2":  # 緩和検索
            return primary_keywords + secondary_keywords[:2]  # 主要＋補助
        elif strategy_id == "strategy3":  # 拡張検索
            # 類義語展開
            expanded = primary_keywords + secondary_keywords
            for keyword in primary_keywords:
                synonyms = self.synonym_dict.get(keyword, [])
                expanded.extend(synonyms[:2])  # 類義語2つまで追加
            return list(set(expanded))  # 重複除去
        else:
            return primary_keywords
    
    def _build_query(self, datasource: str, keywords: List[str], filters: Dict[str, Any], strategy: Dict[str, Any]) -> str:
        """クエリ文字列構築"""
        
        # キーワード結合
        operator = strategy["operator"]
        if strategy["match_type"] == "exact":
            keyword_clause = f" {operator} ".join(f'"{kw}"' for kw in keywords)
        else:
            keyword_clause = f" {operator} ".join(f'"{kw}"' for kw in keywords)
        
        if datasource == "jira":
            return self._build_jql_query(keyword_clause, filters)
        elif datasource == "confluence":
            return self._build_cql_query(keyword_clause, filters)
        else:
            return f"text ~ ({keyword_clause})"
    
    def _build_jql_query(self, keyword_clause: str, filters: Dict[str, Any]) -> str:
        """JQLクエリ構築"""
        
        base_query = f"text ~ ({keyword_clause})"
        conditions = [base_query]
        
        # フィルター追加
        if "project" in filters:
            conditions.append(f"project = \"{filters['project']}\"")
        
        if "status" in filters and filters["status"]:
            status_list = ", ".join(f'"{s}"' for s in filters["status"])
            conditions.append(f"status IN ({status_list})")
        
        if "issuetype" in filters and filters["issuetype"]:
            type_list = ", ".join(f'"{t}"' for t in filters["issuetype"])
            conditions.append(f"issuetype IN ({type_list})")
        
        return " AND ".join(conditions)
    
    def _build_cql_query(self, keyword_clause: str, filters: Dict[str, Any]) -> str:
        """CQLクエリ構築"""
        
        base_query = f"text ~ ({keyword_clause})"
        conditions = [base_query]
        
        # フィルター追加
        if "space_keys" in filters and filters["space_keys"]:
            space_list = ", ".join(f'"{s}"' for s in filters["space_keys"])
            conditions.append(f"space IN ({space_list})")
        
        if "content_type" in filters:
            conditions.append(f"type = \"{filters['content_type']}\"")
        
        return " AND ".join(conditions)
    
    def _execute_real_api_search(self, datasource: str, keywords: List[str], strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """実際のAtlassian API検索実行（spec_bot成功パターン適用）"""
        try:
            max_results = strategy.get("max_results", 50)
            
            logger.info(f"🌐 実際のAPI検索開始: {datasource} | キーワード: {keywords} | 戦略: {strategy['name']}")
            
            if datasource == "jira":
                # Jira検索実行
                results = self.api_client.search_jira(keywords, max_results)
                
            elif datasource == "confluence":
                # Confluence検索実行（spec_botのCQLエンジンパターンを活用）
                results = self._execute_confluence_api_search(keywords, strategy, max_results)
                
            else:
                logger.warning(f"❌ 未対応のデータソース: {datasource}")
                return []
            
            # 戦略情報を結果に追加
            for result in results:
                result["strategy"] = strategy["name"]
                result["weight"] = strategy["weight"]
                result["search_engine"] = "real_api"
            
            logger.info(f"✅ 実際のAPI検索完了: {len(results)}件取得 ({strategy['name']})")
            return results
            
        except Exception as e:
            logger.error(f"❌ 実際のAPI検索エラー ({datasource}): {e}")
            # エラー時は空の結果を返す
            return []
    
    def _execute_confluence_api_search(self, keywords: List[str], strategy: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
        """Confluence専用API検索（spec_botのCQLエンジンパターン適用）"""
        try:
            # spec_botの3段階検索戦略を適用
            if strategy["name"] == "厳密検索":
                # Strategy1: タイトル優先検索（AND結合）
                search_terms = []
                for keyword in keywords[:3]:  # 主要キーワードのみ
                    search_terms.append(f'title ~ "{keyword}"')
                cql = " AND ".join(search_terms)
                cql += ' AND space = "CLIENTTOMO"'
                
            elif strategy["name"] == "緩和検索":
                # Strategy2: OR結合による範囲拡張
                search_terms = []
                for keyword in keywords[:5]:  # キーワード拡張
                    search_terms.append(f'text ~ "{keyword}"')
                cql = " OR ".join(search_terms)
                cql = f'({cql}) AND space = "CLIENTTOMO"'
                
            elif strategy["name"] == "拡張検索":
                # Strategy3: 類義語展開
                expanded_keywords = list(keywords)
                for keyword in keywords[:2]:  # 主要キーワードのみ展開
                    synonyms = self.synonym_dict.get(keyword, [])
                    expanded_keywords.extend(synonyms[:2])
                
                search_terms = []
                for keyword in expanded_keywords[:7]:  # 最大7キーワード
                    search_terms.append(f'text ~ "{keyword}"')
                cql = " OR ".join(search_terms)
                cql = f'({cql}) AND space = "CLIENTTOMO"'
                
            else:
                # デフォルト
                search_terms = [f'text ~ "{kw}"' for kw in keywords[:3]]
                cql = " AND ".join(search_terms)
                cql += ' AND space = "CLIENTTOMO"'
            
            # CQL実行（atlassianライブラリ経由）
            logger.debug(f"📋 CQL実行: {cql}")
            search_results = self.api_client.confluence.cql(cql, limit=max_results)
            
            if not search_results or 'results' not in search_results:
                logger.warning(f"⚠️ Confluence CQL結果なし: {cql}")
                return []
            
            results = search_results['results']
            
            # 結果を統一フォーマットに変換（spec_bot標準化パターン）
            formatted_results = []
            for result in results:
                try:
                    content = result.get('content', {})
                    
                    formatted_result = {
                        "id": content.get("id"),
                        "title": content.get("title", ""),
                        "description": self._extract_confluence_excerpt(content, result),
                        "space": content.get("space", {}).get("key", ""),
                        "space_name": content.get("space", {}).get("name", ""),
                        "type": content.get("type", "page"),
                        "created": content.get("history", {}).get("createdDate", ""),
                        "updated": content.get("version", {}).get("when", ""),
                        "datasource": "confluence",
                        "url": f"{self.api_client.confluence_url}/pages/viewpage.action?pageId={content.get('id')}",
                        "strategy_name": strategy["name"],
                        "cql_used": cql
                    }
                    formatted_results.append(formatted_result)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Confluence結果変換エラー: {e}")
                    continue
            
            logger.info(f"✅ Confluence CQL検索完了: {len(formatted_results)}件")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Confluence API検索エラー: {e}")
            return []
    
    def _extract_confluence_excerpt(self, content: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Confluenceの抜粋テキストを抽出（spec_bot標準化パターン）"""
        try:
            # 1. excerptフィールドを優先使用
            if 'excerpt' in result and result['excerpt']:
                return result['excerpt'][:200]
            
            # 2. bodyから抽出
            body = content.get("body", {})
            if isinstance(body, dict):
                storage = body.get("storage", {})
                if isinstance(storage, dict):
                    html_content = storage.get("value", "")
                    # HTMLタグを除去してテキスト抽出
                    import re
                    text_content = re.sub(r'<[^>]+>', '', html_content)
                    return text_content.strip()[:200]
            
            # 3. フォールバック
            return content.get("title", "")[:50] + "..."
            
        except Exception:
            return ""
    
    def _execute_mock_search(self, datasource: str, query: str, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """模擬検索実行（本番API切り替え対応版）"""
        
        # 検索クエリからキーワード抽出
        query_lower = query.lower()
        is_login_related = any(keyword in query_lower for keyword in ["ログイン", "login", "認証", "auth"])
        
        # 戦略別結果数調整（本番API準拠）
        if strategy["name"] == "厳密検索":
            mock_count = 3  # 高品質・少数
        elif strategy["name"] == "緩和検索":
            mock_count = 5  # 中品質・中数
        elif strategy["name"] == "拡張検索":
            mock_count = 7  # 範囲広・多数
        else:
            mock_count = 3
        
        mock_results = []
        
        if is_login_related:
            # ログイン機能関連の本番相当テストデータ
            if datasource == "jira":
                jira_samples = [
                    {"id": "AUTH-101", "title": "ログイン画面のUI不具合修正", "type": "Bug", "status": "In Progress", "priority": "High"},
                    {"id": "AUTH-89", "title": "パスワードリセット機能の実装", "type": "Story", "status": "Done", "priority": "Medium"},
                    {"id": "SEC-45", "title": "二段階認証の導入検討", "type": "Epic", "status": "To Do", "priority": "High"},
                    {"id": "AUTH-156", "title": "セッション管理の改善", "type": "Task", "status": "In Progress", "priority": "Medium"},
                    {"id": "BUG-234", "title": "ログイン失敗時のエラーメッセージ改善", "type": "Bug", "status": "Review", "priority": "Low"},
                    {"id": "AUTH-203", "title": "OAuth認証の実装", "type": "Story", "status": "In Progress", "priority": "High"},
                    {"id": "SEC-67", "title": "ログイン履歴機能追加", "type": "Feature", "status": "To Do", "priority": "Low"}
                ]
                for i in range(min(mock_count, len(jira_samples))):
                    sample = jira_samples[i]
                    mock_results.append({
                        "id": sample["id"],
                        "title": f"{sample['title']} [{strategy['name']}]",
                        "description": f"Jira チケット: {sample['title']}の詳細説明...",
                        "type": sample["type"],
                        "status": sample["status"],
                        "priority": sample["priority"],
                        "assignee": "dev.team@company.com",
                        "created": "2024-01-15T10:00:00.000Z",
                        "updated": "2024-01-20T15:30:00.000Z",
                        "strategy": strategy["name"],
                        "weight": strategy["weight"],
                        "search_engine": "mock_api",
                        "datasource": "jira",
                        "url": f"https://example.atlassian.net/browse/{sample['id']}"
                    })
            else:  # confluence
                confluence_samples = [
                    {"id": "page_auth_001", "title": "042_【FIX】会員ログイン・ログアウト機能", "space": "CLIENTTOMO"},
                    {"id": "page_auth_002", "title": "681_【FIX】クライアント企業ログイン・ログアウト機能", "space": "CLIENTTOMO"},
                    {"id": "page_auth_003", "title": "451_【FIX】全体管理者ログイン・ログアウト機能", "space": "CLIENTTOMO"},
                    {"id": "page_auth_004", "title": "ログイン機能API仕様書", "space": "API"},
                    {"id": "page_auth_005", "title": "認証システム設計書", "space": "SYSTEM"},
                    {"id": "page_auth_006", "title": "ユーザーセッション管理仕様", "space": "SYSTEM"},
                    {"id": "page_auth_007", "title": "セキュリティ要件定義 - 認証編", "space": "SECURITY"}
                ]
                for i in range(min(mock_count, len(confluence_samples))):
                    sample = confluence_samples[i]
                    mock_results.append({
                        "id": sample["id"],
                        "title": f"{sample['title']} [{strategy['name']}]",
                        "description": f"Confluence ページ: {sample['title']}の概要説明。この機能の詳細仕様について記載されています...",
                        "space": sample["space"],
                        "space_name": f"{sample['space']} Space",
                        "type": "page",
                        "created": "2024-01-10T09:00:00.000Z",
                        "updated": "2024-01-18T14:20:00.000Z",
                        "strategy": strategy["name"],
                        "weight": strategy["weight"],
                        "search_engine": "mock_api",
                        "datasource": "confluence",
                        "url": f"https://example.atlassian.net/wiki/spaces/{sample['space']}/pages/{sample['id']}"
                    })
        else:
            # その他のクエリ用の汎用テストデータ（本番API準拠フォーマット）
            if datasource == "jira":
                for i in range(mock_count):
                    mock_results.append({
                        "id": f"PROJ-{200 + i}",
                        "title": f"システム機能要件 {i+1} [{strategy['name']}]",
                        "description": f"プロジェクト要件の詳細説明 {i+1}。システム機能に関する検討事項...",
                        "type": "Story",
                        "status": "Open",
                        "priority": "Medium",
                        "assignee": "team.member@company.com",
                        "created": "2024-01-01T08:00:00.000Z",
                        "updated": "2024-01-15T16:30:00.000Z",
                        "strategy": strategy["name"],
                        "weight": strategy["weight"],
                        "search_engine": "mock_api",
                        "datasource": "jira",
                        "url": f"https://example.atlassian.net/browse/PROJ-{200 + i}"
                    })
            else:  # confluence
                for i in range(mock_count):
                    mock_results.append({
                        "id": f"page_{300 + i}",
                        "title": f"システム仕様書 {i+1} [{strategy['name']}]",
                        "description": f"システム仕様書 {i+1}の概要。技術要件と設計詳細について記載...",
                        "space": "TECH",
                        "space_name": "Technical Documentation",
                        "type": "page",
                        "created": "2024-01-01T10:00:00.000Z",
                        "updated": "2024-01-10T13:45:00.000Z",
                        "strategy": strategy["name"],
                        "weight": strategy["weight"],
                        "search_engine": "mock_api",
                        "datasource": "confluence",
                        "url": f"https://example.atlassian.net/wiki/spaces/TECH/pages/{300 + i}"
                    })
        
        logger.info(f"🎭 模擬検索完了 ({strategy['name']}): {len(mock_results)}件生成")
        return mock_results
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """結果重複除去"""
        seen_ids = set()
        unique_results = []
        
        for result in results:
            result_id = result.get("id", "")
            if result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)
        
        return unique_results
    
    def _generate_execution_summary(self, search_results: Dict[str, Any], 
                                  strategies: List[str], primary_datasource: str) -> str:
        """実行サマリー生成（本番API対応版）"""
        
        summary_parts = []
        
        # 戦略実行状況
        strategy_names = [self.strategies[s]["name"] for s in strategies]
        summary_parts.append(f"実行戦略: {', '.join(strategy_names)}")
        
        # データソース別結果数
        for datasource, results in search_results.items():
            count = len(results.get("combined_results", []))
            summary_parts.append(f"{datasource.title()}: {count}件")
        
        # 主要データソース
        summary_parts.append(f"主要: {primary_datasource.title()}")
        
        # API使用状況表示
        api_status = "本番API" if self.use_real_api else "模擬データ"
        summary_parts.append(f"エンジン: {api_status}")
        
        return " | ".join(summary_parts) 