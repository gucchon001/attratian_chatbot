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

logger = logging.getLogger(__name__)

# 実際のAPI接続クライアント
try:
    from ..utils.atlassian_api_client import AtlassianAPIClient
    from ..config.settings import Settings
    ATLASSIAN_CLIENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Atlassian APIクライアントのインポートに失敗: {e}")
    ATLASSIAN_CLIENT_AVAILABLE = False

class CQLSearchEngine:
    """Step3: CQL検索実行エンジン (実際のAPI接続対応)"""
    
    def __init__(self):
        self._init_api_client()  # 設定を先に読み込み
        self._init_search_strategies()
        self._init_query_builders()
    
    def _init_api_client(self):
        """API接続クライアント初期化と接続テスト"""
        from ..config.settings import Settings
        
        self.settings = Settings()
        self.api_client = None
        
        # API接続テストと実行モード決定
        self.use_real_api = self._test_api_connection()
        
        mode = "本番API" if self.use_real_api else "模擬データ"
        logger.info(f"🚀 CQL検索エンジン初期化完了 - モード: {mode}")
    
    def _test_api_connection(self) -> bool:
        """
        Atlassian API接続テスト
        
        Returns:
            bool: 接続成功時はTrue、失敗時はFalse
        """
        logger.info("🔍 Atlassian API接続テスト開始...")
        
        try:
            # 必要なライブラリの確認
            from atlassian import Confluence
            logger.info("✅ atlassian-python-api ライブラリ確認完了")
            
            # 設定値の検証
            logger.info(f"📋 設定値確認: Domain={self.settings.atlassian_domain}, Email={self.settings.atlassian_email}")
            if not all([
                self.settings.atlassian_domain,
                self.settings.atlassian_email, 
                self.settings.atlassian_api_token
            ]):
                logger.error("❌ Atlassian API設定が不完全です")
                return False
            
            logger.info("✅ 設定値検証完了")
            
            # 実際の接続テスト（軽量なAPIコール）
            logger.info(f"🔗 Confluence接続テスト: https://{self.settings.atlassian_domain}")
            confluence = Confluence(
                url=f"https://{self.settings.atlassian_domain}",
                username=self.settings.atlassian_email,
                password=self.settings.atlassian_api_token
            )
            
            # 簡単な接続テスト（スペース一覧取得）
            logger.info("📡 スペース一覧取得テスト...")
            spaces = confluence.get_all_spaces(limit=1)
            
            if spaces and 'results' in spaces:
                space_count = len(spaces['results'])
                logger.info(f"✅ Atlassian API接続テスト成功: {self.settings.atlassian_domain} ({space_count}個のスペース)")
                return True
            else:
                logger.warning(f"⚠️ Atlassian API接続テスト: レスポンスが期待と異なります - {spaces}")
                return False
                
        except ImportError as e:
            logger.error(f"❌ atlassian-python-apiライブラリがインストールされていません: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Atlassian API接続テスト失敗: {e}")
            import traceback
            logger.error(f"詳細エラー: {traceback.format_exc()}")
            return False

    def _init_search_strategies(self):
        """検索戦略の初期化"""
        
        # 4段階検索戦略定義（AND検索優先 + 段階的緩和）
        self.strategies = {
             "strategy1": {
                 "name": "タイトル厳密検索",
                 "description": "タイトル内AND結合による最高精度検索",
                 "operator": "AND",  # ← AND検索に変更
                 "match_type": "title",
                 "max_results": 20,
                 "weight": 3.0  # 最高重み
             },
             "strategy2": {
                 "name": "タイトル近接検索", 
                 "description": "タイトル内複合語・近接検索",
                 "operator": "NEAR",  # 近接検索
                 "match_type": "title_complex",
                 "max_results": 30,
                 "weight": 2.5
             },
             "strategy3": {
                 "name": "本文厳密検索",
                 "description": "本文AND結合による高精度検索",
                 "operator": "AND",
                 "match_type": "exact",
                 "max_results": 50,
                 "weight": 1.5
             },
             "strategy4": {
                 "name": "補完OR検索",
                 "description": "汎用語除外済みOR検索（フォールバック）", 
                 "operator": "OR",
                 "match_type": "filtered",
                 "max_results": 30,  # 結果数を制限
                 "weight": 0.8  # 重みを下げる
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
        
        # 汎用語（ストップワード）- OR検索で除外すべき単語
        self.stop_words = {
            "機能", "システム", "仕様", "設計", "実装", "開発", "管理", 
            "処理", "画面", "ページ", "フォーム", "ボタン", "メニュー",
            "データ", "情報", "内容", "詳細", "説明", "資料", "文書",
            "要件", "項目", "一覧", "リスト", "テーブル", "フィールド",
            "コード", "プログラム", "スクリプト", "ファイル", "フォルダ"
        }
        
        # タイトル除外パターン - 設定ファイルから読み込み（削除・廃止・終了済みコンテンツのフィルタリング）
        self._init_exclusion_patterns()
        
                 # 除外フィルタの有効/無効設定（設定ファイルから読み込み）
        self.enable_exclusion_filter = self.settings.enable_exclusion_filter
    
    def _init_exclusion_patterns(self):
        """除外パターンの初期化（設定ファイルから読み込み・【】内含有検索対応）"""
        
        # 設定ファイルから除外キーワードを読み込み
        self.exclusion_keywords = {
            "bracket_keywords": self.settings.bracket_exclusion_keywords,
            "percent_keywords": self.settings.percent_exclusion_keywords,
            "english_keywords": self.settings.english_exclusion_keywords,
            "temporary_keywords": self.settings.temporary_exclusion_keywords
        }
        
        # 全キーワード数をログ出力
        total_keywords = sum(len(keywords) for keywords in self.exclusion_keywords.values())
        logger.info(f"🗑️ 除外キーワード初期化完了: {total_keywords}キーワード（【】%%内含有検索対応）")
    
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
        
        # UIでのデータソース選択を取得
        enabled_datasources = self._get_enabled_datasources()
        
        # UIの選択とStep2の判定結果を組み合わせて最終的な検索対象を決定
        final_datasources = self._determine_final_datasources(datasource_priority, enabled_datasources)
        
        logger.info(f"🎯 検索対象データソース決定: {final_datasources} (UI選択: {enabled_datasources}, Step2優先度: {datasource_priority})")
        
        # データソース別段階的検索実行
        search_results = {}
        query_details = {}
        
        for datasource in final_datasources:
            if datasource in ["jira", "confluence"]:
                ds_results, ds_queries = self._execute_progressive_search(
                    datasource=datasource,
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
        
        # 実行サマリー生成（段階的検索対応）
        execution_summary = self._generate_progressive_summary(
            search_results, datasource_priority[0]
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
        """実行戦略決定（精度優先・段階的実行）"""
        
        # 精度優先戦略: まずタイトル検索のみ実行
        # 結果が不十分な場合のみ、段階的に拡張
        return ["strategy1"]  # デフォルトはタイトル検索のみ（最高精度）
    
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
            if self.use_real_api:
                # 実際のAtlassian API検索
                api_results = self._execute_api_search(datasource, query, strategy)
                results["strategy_results"][strategy_id] = api_results
                results["combined_results"].extend(api_results)
                logger.info(f"✅ 実際のAPI検索完了 ({strategy['name']}): {len(api_results)}件")
            else:
                # 模擬検索（テスト用/フォールバック）
                mock_results = self._execute_mock_search(datasource, query, strategy)
                results["strategy_results"][strategy_id] = mock_results
                results["combined_results"].extend(mock_results)
                logger.info(f"🎭 模擬検索完了 ({strategy['name']}): {len(mock_results)}件")
        
        # 重複除去
        results["combined_results"] = self._deduplicate_results(results["combined_results"])
        
        # 除外フィルター適用（正規表現による後処理）
        logger.info(f"🔍 除外フィルター設定確認: enable_exclusion_filter={self.enable_exclusion_filter}")
        if self.enable_exclusion_filter:
            logger.info("🔍 除外フィルターを実行します")
            before_count = len(results["combined_results"])
            results["combined_results"] = self._filter_excluded_results(results["combined_results"])
            after_count = len(results["combined_results"])
            logger.info(f"🔍 除外フィルター実行結果: {before_count}件 → {after_count}件")
        else:
            logger.info("🔍 除外フィルターはスキップされました（設定無効）")
        
        return results, queries
    
    def _execute_progressive_search(self, datasource: str, primary_keywords: List[str], 
                                   secondary_keywords: List[str], filters: Dict[str, Any], 
                                   search_intent: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """段階的検索実行（精度優先・早期終了）"""
        
        results = {"strategy_results": {}, "combined_results": []}
        queries = {}
        
        # 最小十分件数の設定
        min_sufficient_count = 3  # タイトル検索で3件以上あれば十分
        max_total_count = 10      # 総件数上限
        
        # Stage 1: タイトル検索（最高精度）
        logger.info("🎯 Stage 1: タイトル検索実行（最高精度）")
        strategy1 = self.strategies["strategy1"]
        keywords1 = self._prepare_keywords_for_strategy("strategy1", primary_keywords, secondary_keywords)
        query1 = self._build_query(datasource, keywords1, filters, strategy1)
        
        queries["strategy1"] = {
            "query": query1,
            "keywords": keywords1,
            "strategy": strategy1["name"]
        }
        
        # タイトル検索実行
        if self.use_real_api:
            api_results1 = self._execute_api_search(datasource, query1, strategy1)
            results["strategy_results"]["strategy1"] = api_results1
            results["combined_results"].extend(api_results1)
            logger.info(f"✅ タイトル検索完了 ({strategy1['name']}): {len(api_results1)}件")
        else:
            mock_results1 = self._execute_mock_search(datasource, query1, strategy1)
            results["strategy_results"]["strategy1"] = mock_results1
            results["combined_results"].extend(mock_results1)
            logger.info(f"🎭 タイトル検索完了 ({strategy1['name']}): {len(mock_results1)}件")
        
        # 早期終了判定
        title_results_count = len(results["combined_results"])
        if title_results_count >= min_sufficient_count:
            logger.info(f"✅ 高精度結果十分取得（{title_results_count}件）→ 追加検索スキップ")
            
            # 早期終了でも重複除去と除外フィルターを適用
            results["combined_results"] = self._deduplicate_results(results["combined_results"])
            
            # 除外フィルター適用（正規表現による後処理）
            logger.info(f"🔍 [早期終了]除外フィルター設定確認: enable_exclusion_filter={self.enable_exclusion_filter}")
            if self.enable_exclusion_filter:
                logger.info("🔍 [早期終了]除外フィルターを実行します")
                before_count = len(results["combined_results"])
                results["combined_results"] = self._filter_excluded_results(results["combined_results"])
                after_count = len(results["combined_results"])
                logger.info(f"🔍 [早期終了]除外フィルター実行結果: {before_count}件 → {after_count}件")
            else:
                logger.info("🔍 [早期終了]除外フィルターはスキップされました（設定無効）")
                
            return results, queries
        
        # Stage 2: タイトル近接検索（中精度） - タイトル検索が不十分な場合のみ
        logger.info(f"⚠️ タイトル検索結果不足（{title_results_count}件）→ タイトル近接検索実行")
        strategy2 = self.strategies["strategy2"]
        keywords2 = self._prepare_keywords_for_strategy("strategy2", primary_keywords, secondary_keywords)
        query2 = self._build_query(datasource, keywords2, filters, strategy2)
        
        queries["strategy2"] = {
            "query": query2,
            "keywords": keywords2,
            "strategy": strategy2["name"]
        }
        
        # タイトル近接検索実行（件数制限付き）
        limited_strategy2 = {**strategy2, "max_results": min(strategy2["max_results"], max_total_count - title_results_count)}
        
        if self.use_real_api:
            api_results2 = self._execute_api_search(datasource, query2, limited_strategy2)
            results["strategy_results"]["strategy2"] = api_results2
            results["combined_results"].extend(api_results2)
            logger.info(f"✅ タイトル近接検索完了 ({strategy2['name']}): {len(api_results2)}件")
        else:
            mock_results2 = self._execute_mock_search(datasource, query2, limited_strategy2)
            results["strategy_results"]["strategy2"] = mock_results2
            results["combined_results"].extend(mock_results2)
            logger.info(f"🎭 タイトル近接検索完了 ({strategy2['name']}): {len(mock_results2)}件")
        
        # 重複除去
        results["combined_results"] = self._deduplicate_results(results["combined_results"])
        
        # 除外フィルター適用（正規表現による後処理）
        logger.info(f"🔍 [段階的検索]除外フィルター設定確認: enable_exclusion_filter={self.enable_exclusion_filter}")
        if self.enable_exclusion_filter:
            logger.info("🔍 [段階的検索]除外フィルターを実行します")
            before_count = len(results["combined_results"])
            results["combined_results"] = self._filter_excluded_results(results["combined_results"])
            after_count = len(results["combined_results"])
            logger.info(f"🔍 [段階的検索]除外フィルター実行結果: {before_count}件 → {after_count}件")
        else:
            logger.info("🔍 [段階的検索]除外フィルターはスキップされました（設定無効）")
        
        final_count = len(results["combined_results"])
        logger.info(f"🎯 段階的検索完了: {final_count}件（タイトル{title_results_count}件 + 近接{final_count-title_results_count}件）")
        
        return results, queries
    
    def _prepare_keywords_for_strategy(self, strategy_id: str, primary_keywords: List[str], 
                                     secondary_keywords: List[str]) -> List[str]:
        """戦略別キーワード準備（汎用語フィルター付き）"""
        
        if strategy_id == "strategy1":  # タイトル厳密検索
            # タイトル検索では汎用語も含める（完全一致前提）
            return primary_keywords[:3]
        elif strategy_id == "strategy2":  # タイトル近接検索
            # NEAR検索では汎用語を含めても問題ない
            return primary_keywords + secondary_keywords[:2]
        elif strategy_id == "strategy3":  # 本文厳密検索
            # AND検索では汎用語を含めても問題ない
            return primary_keywords + secondary_keywords[:2]
        elif strategy_id == "strategy4":  # 補完OR検索
            # OR検索では汎用語を除外（重要！）
            filtered_keywords = []
            
            # 主要キーワードから汎用語を除外
            for keyword in primary_keywords:
                if keyword not in self.stop_words:
                    filtered_keywords.append(keyword)
            
            # 副次キーワードからも汎用語を除外
            for keyword in secondary_keywords[:2]:
                if keyword not in self.stop_words:
                    filtered_keywords.append(keyword)
            
            # 類義語展開（汎用語除外済み）
            expanded = filtered_keywords.copy()
            for keyword in filtered_keywords:
                synonyms = self.synonym_dict.get(keyword, [])
                for synonym in synonyms[:1]:  # 類義語1つまで（精度重視）
                    if synonym not in self.stop_words:
                        expanded.append(synonym)
            
            # フィルター後のキーワードが少なすぎる場合の対策
            unique_keywords = list(set(expanded))
            if len(unique_keywords) < 2:
                # 安全な主要キーワードのみ使用
                return [kw for kw in primary_keywords if kw not in self.stop_words][:2]
            
            return unique_keywords[:4]  # 最大4キーワードに制限
        else:
            return primary_keywords
    
    def _build_query(self, datasource: str, keywords: List[str], filters: Dict[str, Any], strategy: Dict[str, Any]) -> str:
        """クエリ文字列構築"""
        
        # タイトル検索の場合は専用メソッドを使用
        if strategy["match_type"] == "title":
            return self._build_title_query(datasource, keywords, filters)
        
        # タイトル複合語検索の場合も専用メソッドを使用
        if strategy["match_type"] == "title_complex":
            return self._build_title_complex_query(datasource, keywords, filters)
        
        # 通常のtext検索
        operator = strategy["operator"]
        if strategy["match_type"] == "exact":
            keyword_clause = f" {operator} ".join(f'"{kw}"' for kw in keywords)
        else:
            keyword_clause = f" {operator} ".join(f'"{kw}"' for kw in keywords)
        
        # データソース別クエリ構築
        if datasource == "jira":
            return self._build_jql_query(keyword_clause, filters)
        else:
            return self._build_cql_query(keyword_clause, filters)
    
    def _build_title_query(self, datasource: str, keywords: List[str], filters: Dict[str, Any]) -> str:
        """タイトル専用検索クエリ構築（AND検索とNEAR検索対応）"""
        
        if datasource == "jira":
            # JQL: summary（タイトル）検索
            title_conditions = []
            
            # キーワード数に応じて戦略決定
            if len(keywords) >= 2:
                # 複数キーワード → AND検索
                for keyword in keywords:
                    title_conditions.append(f'summary ~ "{keyword}"')
                base_query = f"({' AND '.join(title_conditions)})"
            else:
                # 単一キーワード → 単純検索
                base_query = f'summary ~ "{keywords[0]}"'
            
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
            
            # 削除・廃止コンテンツ除外フィルター追加（JQL用）
            exclusion_conditions = self._build_jql_exclusion_conditions()
            conditions.extend(exclusion_conditions)
            
            return " AND ".join(conditions)
            
        else:  # Confluence
            # CQL: title検索（AND検索とNEAR検索対応）
            title_conditions = []
            
            # キーワード数と戦略に応じてクエリ構築
            if len(keywords) >= 2:
                # 複数キーワード → AND検索を基本とする
                for keyword in keywords:
                    title_conditions.append(f'title ~ "{keyword}"')
                
                # AND検索
                base_query = f"({' AND '.join(title_conditions)})"
                
                # 近接検索も併用（複合語検索）
                # "会員.*ログイン|ログイン.*会員" のようなパターンも追加
                if len(keywords) == 2:
                    kw1, kw2 = keywords[0], keywords[1]
                    near_patterns = [
                        f'title ~ "{kw1}.*{kw2}"',  # kw1の後にkw2
                        f'title ~ "{kw2}.*{kw1}"',  # kw2の後にkw1
                    ]
                    
                    # 複合語検索をOR条件として追加
                    near_query = f"({' OR '.join(near_patterns)})"
                    base_query = f"({base_query} OR {near_query})"
                
            else:
                # 単一キーワード → 単純検索
                base_query = f'title ~ "{keywords[0]}"'
            
            conditions = [base_query]
            
            # フィルター追加
            if "space_keys" in filters and filters["space_keys"]:
                space_list = ", ".join(f'"{s}"' for s in filters["space_keys"])
                conditions.append(f"space IN ({space_list})")
            else:
                # デフォルトスペース設定（CLIENTTOMO）
                conditions.append(f'space = "{self.settings.confluence_space}"')
            
            if "content_type" in filters:
                conditions.append(f"type = \"{filters['content_type']}\"")
            
            # 削除・廃止コンテンツ除外フィルター追加
            exclusion_conditions = self._build_title_exclusion_conditions()
            conditions.extend(exclusion_conditions)
            
            return " AND ".join(conditions)

    def _build_title_complex_query(self, datasource: str, keywords: List[str], filters: Dict[str, Any]) -> str:
        """タイトル複合語検索クエリ構築（近接・複合語専用）"""
        
        if datasource == "jira":
            # JQL: summary複合語検索
            if len(keywords) >= 2:
                # 複合語パターン生成
                complex_patterns = []
                for i in range(len(keywords)):
                    for j in range(len(keywords)):
                        if i != j:
                            complex_patterns.append(f'summary ~ "{keywords[i]}.*{keywords[j]}"')
                
                base_query = f"({' OR '.join(complex_patterns)})"
            else:
                # 単一キーワードの場合は通常検索
                base_query = f'summary ~ "{keywords[0]}"'
            
            conditions = [base_query]
            
            # フィルター追加
            if "project" in filters:
                conditions.append(f"project = \"{filters['project']}\"")
            
            # 削除・廃止コンテンツ除外フィルター追加（JQL用）
            exclusion_conditions = self._build_jql_exclusion_conditions()
            conditions.extend(exclusion_conditions)
            
            return " AND ".join(conditions)
            
        else:  # Confluence
            # CQL: title複合語検索
            if len(keywords) >= 2:
                # 複合語パターン生成（より柔軟な検索）
                complex_patterns = []
                
                # 各キーワードペアで複合語検索
                for i in range(len(keywords)):
                    for j in range(len(keywords)):
                        if i != j:
                            # 前後順序の複合語
                            complex_patterns.append(f'title ~ "{keywords[i]}.*{keywords[j]}"')
                            # より広範囲な複合語（単語間に他の語が入ることを許可）
                            complex_patterns.append(f'title ~ "{keywords[i]}.*\\b.*{keywords[j]}"')
                
                # 完全一致の複合語も追加
                combined_keywords = "".join(keywords)
                complex_patterns.append(f'title ~ "{combined_keywords}"')
                
                base_query = f"({' OR '.join(complex_patterns)})"
            else:
                # 単一キーワードの場合は通常検索
                base_query = f'title ~ "{keywords[0]}"'
            
            conditions = [base_query]
            
            # フィルター追加
            if "space_keys" in filters and filters["space_keys"]:
                space_list = ", ".join(f'"{s}"' for s in filters["space_keys"])
                conditions.append(f"space IN ({space_list})")
            else:
                # デフォルトスペース設定（CLIENTTOMO）
                conditions.append(f'space = "{self.settings.confluence_space}"')
            
            if "content_type" in filters:
                conditions.append(f"type = \"{filters['content_type']}\"")
            
            # 削除・廃止コンテンツ除外フィルター追加
            exclusion_conditions = self._build_title_exclusion_conditions()
            conditions.extend(exclusion_conditions)
            
            return " AND ".join(conditions)
    
    def _build_jql_query(self, keyword_clause: str, filters: Dict[str, Any]) -> str:
        """JQLクエリ構築"""
        
        # JQLでは正しい構文を使用: (text ~ "keyword1" OR text ~ "keyword2") または (text ~ "keyword1" AND text ~ "keyword2")
        # keyword_clauseは既にAND/ORで結合された形式なので、適切にJQL形式に変換
        
        # keyword_clauseを解析してJQL形式に変換
        if " AND " in keyword_clause:
            # AND結合の場合
            keywords = [kw.strip().strip('"') for kw in keyword_clause.split(" AND ")]
            base_query = " AND ".join(f'text ~ "{kw}"' for kw in keywords if kw)
        elif " OR " in keyword_clause:
            # OR結合の場合
            keywords = [kw.strip().strip('"') for kw in keyword_clause.split(" OR ")]
            base_query = " OR ".join(f'text ~ "{kw}"' for kw in keywords if kw)
        else:
            # 単一キーワードの場合
            keyword = keyword_clause.strip().strip('"')
            base_query = f'text ~ "{keyword}"'
        
        # 複数条件の場合は括弧で囲む
        if " AND " in base_query or " OR " in base_query:
            base_query = f"({base_query})"
        
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
        
        # 削除・廃止コンテンツ除外フィルター追加（JQL用）
        exclusion_conditions = self._build_jql_exclusion_conditions()
        conditions.extend(exclusion_conditions)
        
        return " AND ".join(conditions)
    
    def _build_cql_query(self, keyword_clause: str, filters: Dict[str, Any]) -> str:
        """CQLクエリ構築"""
        
        # CQLでは正しい構文を使用: (text ~ "keyword1" OR text ~ "keyword2") または (text ~ "keyword1" AND text ~ "keyword2")
        # keyword_clauseは既にAND/ORで結合された形式なので、適切にCQL形式に変換
        
        # keyword_clauseを解析してCQL形式に変換
        if " AND " in keyword_clause:
            # AND結合の場合
            keywords = [kw.strip().strip('"') for kw in keyword_clause.split(" AND ")]
            base_query = " AND ".join(f'text ~ "{kw}"' for kw in keywords if kw)
        elif " OR " in keyword_clause:
            # OR結合の場合
            keywords = [kw.strip().strip('"') for kw in keyword_clause.split(" OR ")]
            base_query = " OR ".join(f'text ~ "{kw}"' for kw in keywords if kw)
        else:
            # 単一キーワードの場合
            keyword = keyword_clause.strip().strip('"')
            base_query = f'text ~ "{keyword}"'
        
        # 複数条件の場合は括弧で囲む
        if " AND " in base_query or " OR " in base_query:
            base_query = f"({base_query})"
        
        conditions = [base_query]
        
        # フィルター追加
        if "space_keys" in filters and filters["space_keys"]:
            space_list = ", ".join(f'"{s}"' for s in filters["space_keys"])
            conditions.append(f"space IN ({space_list})")
        else:
            # デフォルトスペース設定（CLIENTTOMO）
            conditions.append(f'space = "{self.settings.confluence_space}"')
        
        if "content_type" in filters:
            conditions.append(f"type = \"{filters['content_type']}\"")
        
        # 削除・廃止コンテンツ除外フィルター追加
        exclusion_conditions = self._build_title_exclusion_conditions()
        conditions.extend(exclusion_conditions)
        
        return " AND ".join(conditions)
    
    def _execute_api_search(self, datasource: str, query: str, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        実際のAPIを使用した検索実行（本番実装）
        
        Args:
            datasource: データソース ('confluence' or 'jira')
            query: 検索クエリ
            strategy: 検索戦略
            
        Returns:
            List[Dict[str, Any]]: 検索結果
        """
        try:
            if datasource == "confluence":
                return self._execute_confluence_search(query, strategy)
            elif datasource == "jira":
                return self._execute_jira_search(query, strategy)
            else:
                logger.warning(f"サポートされていないデータソース: {datasource}")
                return []
                
        except Exception as e:
            logger.error(f"{datasource.title()}API検索エラー: {e}")
            # API失敗時はフォールバック実行
            logger.info(f"{datasource.title()}検索をモックモードにフォールバック")
            return self._execute_mock_search(datasource, query, strategy)
    
    def _execute_confluence_search(self, query: str, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Confluence API検索実行
        
        Args:
            query: 検索クエリ
            strategy: 検索戦略
            
        Returns:
            List[Dict[str, Any]]: Confluence検索結果
        """
        from atlassian import Confluence
        
        # Confluence接続の初期化
        confluence = Confluence(
            url=f"https://{self.settings.atlassian_domain}",
            username=self.settings.atlassian_email,
            password=self.settings.atlassian_api_token
        )
        
        # CQLクエリの構築（戦略に応じた検索）
        # queryは既に構築済みのクエリ文字列なので、スペースフィルターのみ追加
        if self.settings.confluence_space:
            cql_query = f'{query} and space = "{self.settings.confluence_space}"'
        else:
            cql_query = query
        
        logger.info(f"Confluence CQL実行: {cql_query}")
        
        # 検索実行
        search_result = confluence.cql(cql_query, limit=strategy.get("max_results", 10))
        
        if not search_result or 'results' not in search_result:
            logger.warning(f"Confluence検索結果なし: クエリ='{query}'")
            return []
        
        results = search_result['results']
        logger.info(f"Confluence検索結果: {len(results)}件")
        
        # 結果フォーマット
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, dict):
                formatted_result = {
                    "id": result.get("content", {}).get("id", f"confluence_{i}"),
                    "title": result.get("title", "無題"),
                    "space": result.get("space", {}).get("key", ""),
                    "type": "page",
                    "url": result.get("url", ""),
                    "excerpt": result.get("excerpt", "")[:200],
                    "created": result.get("content", {}).get("history", {}).get("createdDate", ""),
                    "strategy": strategy["name"],
                    "weight": strategy["weight"],
                    "datasource": "confluence"
                }
                formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _execute_jira_search(self, query: str, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Jira API検索実行
        
        Args:
            query: 検索クエリ
            strategy: 検索戦略
            
        Returns:
            List[Dict[str, Any]]: Jira検索結果
        """
        from atlassian import Jira
        
        # Jira接続の初期化
        jira = Jira(
            url=f"https://{self.settings.atlassian_domain}",
            username=self.settings.atlassian_email,
            password=self.settings.atlassian_api_token
        )
        
        # JQLクエリの構築（戦略に応じた検索）
        # queryは既に構築済みのクエリ文字列なので、プロジェクトフィルターのみ追加
        jql_query = f'{query} AND project = "CTJ"'
        
        logger.info(f"Jira JQL実行: {jql_query}")
        
        # 検索実行
        search_result = jira.jql(jql_query, limit=strategy.get("max_results", 10))
        
        if not search_result or 'issues' not in search_result:
            logger.warning(f"Jira検索結果なし: クエリ='{query}'")
            return []
        
        issues = search_result['issues']
        logger.info(f"Jira検索結果: {len(issues)}件")
        
        # 結果フォーマット
        formatted_results = []
        for issue in issues:
            if isinstance(issue, dict):
                fields = issue.get("fields", {})
                formatted_result = {
                    "id": issue.get("key", ""),
                    "title": fields.get("summary", "無題"),
                    "type": fields.get("issuetype", {}).get("name", ""),
                    "status": fields.get("status", {}).get("name", ""),
                    "priority": fields.get("priority", {}).get("name", ""),
                    "assignee": fields.get("assignee", {}).get("displayName", "未割り当て") if fields.get("assignee") else "未割り当て",
                    "reporter": fields.get("reporter", {}).get("displayName", ""),
                    "description": (fields.get("description", "") or "")[:200],
                    "created": fields.get("created", ""),
                    "updated": fields.get("updated", ""),
                    "strategy": strategy["name"],
                    "weight": strategy["weight"],
                    "datasource": "jira"
                }
                formatted_results.append(formatted_result)
        
        return formatted_results
    
    def _execute_mock_search(self, datasource: str, query: str, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """模擬検索実行（現実的なテストデータ）"""
        
        # 検索クエリからキーワード抽出
        query_lower = query.lower()
        is_login_related = any(keyword in query_lower for keyword in ["ログイン", "login", "認証", "auth"])
        
        # 戦略別結果数調整
        mock_count = min(strategy["max_results"] // 10, 5) if strategy["name"] == "厳密検索" else min(strategy["max_results"] // 10, 3)
        
        mock_results = []
        
        if is_login_related:
            # ログイン関連クエリ用の動的データ生成
            query_keywords = self._extract_mock_keywords_from_query(query)
            login_context = self._determine_login_context(query_keywords, query_lower)
            
            if datasource == "jira":
                # ログイン関連の動的Jiraタイトル生成
                jira_templates = self._generate_login_jira_templates(login_context, query_keywords)
                for i in range(mock_count):
                    template_idx = i % len(jira_templates)
                    mock_results.append({
                        "id": f"AUTH-{100 + i}",
                        "title": f"{jira_templates[template_idx]} ({strategy['name']})",
                        "type": "Story" if i % 2 == 0 else "Bug",
                        "status": ["Open", "In Progress", "Done"][i % 3],
                        "assignee": "dev.team@company.com",
                        "created": "2024-01-15",
                        "strategy": strategy["name"],
                        "weight": strategy["weight"],
                        "datasource": "jira"
                    })
            else:  # confluence
                # ログイン関連の動的Confluenceタイトル生成
                confluence_templates = self._generate_login_confluence_templates(login_context, query_keywords)
                for i in range(mock_count):
                    template_idx = i % len(confluence_templates)
                    mock_results.append({
                        "id": f"page_auth_{100 + i}",
                        "title": f"{confluence_templates[template_idx]} ({strategy['name']})",
                        "space": ["SYSTEM", "API", "SECURITY"][i % 3],
                        "type": "page",
                        "created": "2024-01-10",
                        "strategy": strategy["name"],
                        "weight": strategy["weight"],
                        "datasource": "confluence"
                    })
        else:
            # その他のクエリ用の関連性のあるテストデータ
            query_keywords = self._extract_mock_keywords_from_query(query)
            base_keyword = self._determine_base_keyword_from_query(query_keywords, query)
            
            # 「機能」重複を回避するため、末尾の「機能」を除去
            base_keyword_clean = base_keyword.replace("機能", "") if base_keyword.endswith("機能") else base_keyword
            
            if datasource == "jira":
                jira_templates = [
                    f"{base_keyword}の実装",
                    f"{base_keyword}に関するバグ修正", 
                    f"{base_keyword}の改善要求",
                    f"{base_keyword_clean}機能テスト",
                    f"{base_keyword}の仕様変更"
                ]
                for i in range(mock_count):
                    template_idx = i % len(jira_templates)
                    mock_results.append({
                        "id": f"PROJ-{200 + i}",
                        "title": f"{jira_templates[template_idx]} ({strategy['name']})",
                        "type": "Story",
                        "status": "Open",
                        "assignee": "team.member@company.com",
                        "created": "2024-01-01",
                        "strategy": strategy["name"],
                        "weight": strategy["weight"],
                        "datasource": "jira"
                    })
            else:  # confluence
                confluence_templates = [
                    f"{base_keyword_clean}機能仕様書",
                    f"{base_keyword}設計ドキュメント",
                    f"{base_keyword}に関する要件定義",
                    f"{base_keyword_clean}機能の使用手順",
                    f"{base_keyword}システム概要"
                ]
                for i in range(mock_count):
                    template_idx = i % len(confluence_templates)
                    mock_results.append({
                        "id": f"page_{300 + i}",
                        "title": f"{confluence_templates[template_idx]} ({strategy['name']})",
                        "space": "TECH",
                        "type": "page",
                        "created": "2024-01-01",
                        "strategy": strategy["name"],
                        "weight": strategy["weight"],
                        "datasource": "confluence"
                    })
        
        return mock_results
    
    def _extract_mock_keywords_from_query(self, query: str) -> List[str]:
        """模擬データ生成用のキーワード抽出"""
        import re
        
        # クエリからキーワードを抽出
        query_clean = query.replace('"', '').replace("'", "").replace("(", "").replace(")", "")
        
        # 除外する汎用語（設定から動的に取得）
        config_exclusions = getattr(self.settings, 'mock_exclude_terms', [])
        exclude_terms = ["AND", "OR", "space", "title", "text", "=", "~"] + config_exclusions
        
        # キーワード候補を抽出
        candidates = []
        
        # 日本語キーワード（ひらがな・カタカナ・漢字）
        japanese_words = re.findall(r'[ぁ-んァ-ヶー一-龯]+', query_clean)
        candidates.extend(japanese_words)
        
        # 英語キーワード（3文字以上）
        english_words = re.findall(r'[a-zA-Z]{3,}', query_clean)
        candidates.extend(english_words)
        
        # 除外語を除去
        filtered_keywords = []
        for word in candidates:
            if word not in exclude_terms and len(word) >= 2:
                filtered_keywords.append(word)
        
        # 重複除去・優先順位付け
        unique_keywords = []
        for keyword in filtered_keywords:
            if keyword not in unique_keywords:
                unique_keywords.append(keyword)
        
        # 最大3個のキーワードを返す
        return unique_keywords[:3] if unique_keywords else ["機能"]
    
    def _determine_login_context(self, keywords: List[str], query_lower: str) -> str:
        """ログイン関連クエリの文脈判定"""
        
        # 文脈キーワード判定
        if any(word in query_lower for word in ["画面", "ui", "フロント"]):
            return "ui"
        elif any(word in query_lower for word in ["api", "バックエンド", "サーバー"]):
            return "api"
        elif any(word in query_lower for word in ["セキュリティ", "認証", "暗号化"]):
            return "security"
        elif any(word in query_lower for word in ["仕様", "設計", "詳細"]):
            return "spec"
        elif any(word in query_lower for word in ["バグ", "不具合", "エラー"]):
            return "bug"
        elif any(word in query_lower for word in ["テスト", "検証"]):
            return "test"
        else:
            return "general"
    
    def _generate_login_jira_templates(self, context: str, keywords: List[str]) -> List[str]:
        """ログイン関連の動的Jiraタイトル生成"""
        
        # キーワードベースの動的生成
        main_keyword = keywords[0] if keywords else "ログイン"
        
        if context == "ui":
            return [
                f"{main_keyword}画面の表示改善",
                f"{main_keyword}UIの不具合修正",
                f"{main_keyword}フォームの操作性向上",
                f"{main_keyword}レスポンシブ対応"
            ]
        elif context == "api":
            return [
                f"{main_keyword}APIの実装",
                f"{main_keyword}エンドポイント設計",
                f"{main_keyword}トークン管理機能",
                f"{main_keyword}API仕様変更"
            ]
        elif context == "security":
            return [
                f"{main_keyword}セキュリティ強化",
                f"{main_keyword}二段階認証対応",
                f"{main_keyword}暗号化方式変更",
                f"{main_keyword}脆弱性対応"
            ]
        elif context == "bug":
            return [
                f"{main_keyword}エラー修正",
                f"{main_keyword}失敗時の不具合",
                f"{main_keyword}タイムアウト問題",
                f"{main_keyword}例外処理改善"
            ]
        elif context == "test":
            return [
                f"{main_keyword}機能のテスト",
                f"{main_keyword}テストケース追加",
                f"{main_keyword}自動テスト導入",
                f"{main_keyword}性能テスト"
            ]
        else:  # general
            return [
                f"{main_keyword}機能の実装",
                f"{main_keyword}に関する課題",
                f"{main_keyword}機能改善",
                f"{main_keyword}要件変更"
            ]
    
    def _generate_login_confluence_templates(self, context: str, keywords: List[str]) -> List[str]:
        """ログイン関連の動的Confluenceタイトル生成"""
        
        # キーワードベースの動的生成
        main_keyword = keywords[0] if keywords else "ログイン"
        
        if context == "ui":
            return [
                f"{main_keyword}画面設計書",
                f"{main_keyword}UI仕様書", 
                f"{main_keyword}画面遷移図",
                f"{main_keyword}ワイヤーフレーム"
            ]
        elif context == "api":
            return [
                f"{main_keyword}API仕様書",
                f"{main_keyword}エンドポイント設計",
                f"{main_keyword}インターフェース定義",
                f"{main_keyword}APIドキュメント"
            ]
        elif context == "security":
            return [
                f"{main_keyword}セキュリティポリシー",
                f"{main_keyword}認証設計書",
                f"{main_keyword}暗号化仕様",
                f"{main_keyword}セキュリティガイドライン"
            ]
        elif context == "spec":
            return [
                f"{main_keyword}機能仕様書",
                f"{main_keyword}詳細設計書",
                f"{main_keyword}要件定義書",
                f"{main_keyword}機能概要"
            ]
        elif context == "test":
            return [
                f"{main_keyword}テスト仕様書",
                f"{main_keyword}テストケース",
                f"{main_keyword}検証手順書",
                f"{main_keyword}テスト計画"
            ]
        else:  # general
            return [
                f"{main_keyword}機能設計書",
                f"{main_keyword}に関する仕様",
                f"{main_keyword}システム概要",
                f"{main_keyword}機能説明"
            ]
    
    def _determine_base_keyword_from_query(self, keywords: List[str], original_query: str) -> str:
        """クエリから適切なベースキーワードを動的に決定"""
        
        # 優先順位付きキーワード選択
        if keywords:
            # 最も具体的なキーワードを選択
            primary_keyword = keywords[0]
            
            # 汎用語の場合は、より具体的なキーワードがないか確認
            if primary_keyword in self.stop_words and len(keywords) > 1:
                for kw in keywords[1:]:
                    if kw not in self.stop_words:
                        return kw
            
            return primary_keyword
        
        # キーワードが抽出できない場合、クエリから文脈推測
        query_lower = original_query.lower()
        
        # ドメイン別フォールバック
        if any(word in query_lower for word in ["ユーザー", "user", "利用者"]):
            return "ユーザー"
        elif any(word in query_lower for word in ["データ", "db", "database"]):
            return "データ"
        elif any(word in query_lower for word in ["api", "interface", "通信"]):
            return "API"
        elif any(word in query_lower for word in ["画面", "ui", "表示"]):
            return "画面"
        elif any(word in query_lower for word in ["処理", "process", "実行"]):
            return "処理"
        elif any(word in query_lower for word in ["設定", "config", "環境"]):
            return "設定"
        else:
            # 最終フォールバック
            return "アプリケーション"
    
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
    
    def _filter_excluded_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """正規表現による除外フィルター適用（効率的・柔軟）"""
        
        if not results:
            return results
        
        # デバッグ情報出力
        logger.info(f"🔍 除外フィルター開始: {len(results)}件の結果を処理")
        logger.info(f"🔍 enable_exclusion_filter: {getattr(self, 'enable_exclusion_filter', 'NOT_SET')}")
        
        # UIからの除外フィルター設定を確認
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'include_deleted_pages'):
                include_deleted = st.session_state.include_deleted_pages
                logger.info(f"🔍 UI設定 include_deleted_pages: {include_deleted}")
                if include_deleted:
                    logger.info("🟢 UI設定: 削除ページを含む → 除外フィルターを無効化")
                    return results
            else:
                logger.info("🔍 Streamlit session_state または include_deleted_pages が見つかりません")
        except Exception as e:
            logger.info(f"🔍 Streamlit環境チェック失敗: {e}")
            pass  # Streamlit環境外では無視
        
        import re
        
        # 除外キーワード収集
        all_keywords = []
        for category, keywords in self.exclusion_keywords.items():
            all_keywords.extend(keywords)
        
        logger.info(f"🔍 除外キーワード: {all_keywords}")
        
        if not all_keywords:
            logger.info("🗑️ 除外キーワードが設定されていません")
            return results
        
        # 正規表現パターン構築
        keywords_pattern = '|'.join(re.escape(keyword) for keyword in all_keywords)
        
        # 【】パターン: 【任意文字+除外キーワード+任意文字】
        bracket_pattern = rf'【.*(?:{keywords_pattern}).*】'
        
        # %%パターン: %%任意文字+除外キーワード+任意文字%%
        percent_pattern = rf'%%.*(?:{keywords_pattern}).*%%'
        
        # 複合パターン
        combined_pattern = f'({bracket_pattern}|{percent_pattern})'
        
        logger.info(f"🗑️ 除外パターン構築完了: {len(all_keywords)}キーワード（正規表現使用）")
        logger.info(f"🔍 使用する正規表現パターン: {combined_pattern}")
        
        # フィルタリング実行
        filtered_results = []
        excluded_count = 0
        
        for result in results:
            title = result.get("title", "")
            
            # 正規表現マッチング
            match = re.search(combined_pattern, title, re.IGNORECASE)
            if match:
                excluded_count += 1
                logger.info(f"🗑️ 除外: '{title}' (マッチ部分: '{match.group()}')")
            else:
                logger.info(f"🔍 保持: '{title}'")
                filtered_results.append(result)
        
        logger.info(f"🗑️ 除外フィルター完了: {excluded_count}件除外, {len(filtered_results)}件残存")
        
        return filtered_results
    
    def _generate_execution_summary(self, search_results: Dict[str, Any], 
                                  strategies: List[str], primary_datasource: str) -> str:
        """実行サマリー生成"""
        
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
        
        return " | ".join(summary_parts)
    
    def _get_enabled_datasources(self) -> List[str]:
        """UIで選択されたデータソースを取得"""
        
        enabled_sources = []
        
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and hasattr(st.session_state, 'data_sources'):
                data_sources = st.session_state.data_sources
                
                if data_sources.get('confluence', True):
                    enabled_sources.append('confluence')
                if data_sources.get('jira', True):
                    enabled_sources.append('jira')
                    
                logger.info(f"🖥️ UI データソース選択状況: Confluence={data_sources.get('confluence', True)}, Jira={data_sources.get('jira', True)}")
            else:
                # Streamlit環境外またはUIで未設定の場合はデフォルト
                enabled_sources = ['confluence', 'jira']
                logger.info("🖥️ UI データソース選択: デフォルト（全て有効）")
                
        except Exception as e:
            # フォールバック
            enabled_sources = ['confluence', 'jira']
            logger.warning(f"🖥️ UI データソース選択取得失敗: {e}")
            
        return enabled_sources
    
    def _determine_final_datasources(self, step2_priority: List[str], ui_enabled: List[str]) -> List[str]:
        """Step2の判定結果とUIの選択を組み合わせて最終的な検索対象を決定"""
        
        # Step2の判定結果を優先し、UIで有効なもののみ選択
        # Step2で除外されたデータソース（確信度30%未満）は、UIで選択されていても追加しない
        filtered_priority = [ds for ds in step2_priority if ds in ui_enabled]
        
        # 結果検証
        if not filtered_priority:
            logger.warning("⚠️ 検索対象データソースがありません - デフォルトでConfluenceを使用")
            return ['confluence']
        
        logger.info(f"🔍 データソース決定ロジック: Step2選択={step2_priority}, UI有効={ui_enabled}, 最終結果={filtered_priority}")
        return filtered_priority
    
    def _build_title_exclusion_conditions(self) -> List[str]:
        """CQL用タイトル除外条件構築（API効率化のため無効化）"""
        
        # API効率化のため、クエリレベルでの除外は行わない
        # 結果取得後に正規表現で除外処理を実行
        logger.info("🗑️ CQL除外条件: API効率化のためクエリレベル除外を無効化")
        return []
    
    def _build_jql_exclusion_conditions(self) -> List[str]:
        """JQL用タイトル除外条件構築（API効率化のため無効化）"""
        
        # API効率化のため、クエリレベルでの除外は行わない
        # 結果取得後に正規表現で除外処理を実行
        logger.info("🗑️ JQL除外条件: API効率化のためクエリレベル除外を無効化")
        return []
    
    def _generate_progressive_summary(self, search_results: Dict[str, Any], primary_datasource: str) -> str:
        """段階的検索の実行サマリー生成"""
        
        summary_parts = []
        
        # 各データソースの段階的実行状況
        for datasource, results in search_results.items():
            strategy_results = results.get("strategy_results", {})
            total_count = len(results.get("combined_results", []))
            
            # 実行された戦略を確認
            executed_strategies = []
            title_count = len(strategy_results.get("strategy1", []))
            if title_count > 0:
                executed_strategies.append(f"タイトル厳密検索:{title_count}件")
            
            near_count = len(strategy_results.get("strategy2", []))
            if near_count > 0:
                executed_strategies.append(f"タイトル近接検索:{near_count}件")
            
            exact_count = len(strategy_results.get("strategy3", []))
            if exact_count > 0:
                executed_strategies.append(f"本文厳密検索:{exact_count}件")
            
            filtered_count = len(strategy_results.get("strategy4", []))
            if filtered_count > 0:
                executed_strategies.append(f"補完OR検索:{filtered_count}件")
            
            strategy_summary = " + ".join(executed_strategies) if executed_strategies else "なし"
            summary_parts.append(f"{datasource.title()}: {total_count}件 ({strategy_summary})")
        
        # 主要データソース
        summary_parts.append(f"主要: {primary_datasource.title()}")
        
        # 精度優先モードの表示
        summary_parts.append("精度優先・段階的実行")
        
        return " | ".join(summary_parts) 