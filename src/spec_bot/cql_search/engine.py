"""
CQL検索エンジン

シンプルで再利用可能なCQL検索の核心機能。
外部依存を注入可能にし、純粋関数として設計。
"""

import re
import time
from typing import List, Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass, field
from ..config.settings import settings


@dataclass
class SearchStep:
    """検索ステップの情報"""
    step_number: int
    strategy_name: str
    query: str
    cql_queries: List[str] = field(default_factory=list)
    results_count: int = 0
    execution_time: float = 0.0
    keywords: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SearchResult:
    """検索結果とプロセス情報"""
    results: List[Dict[str, Any]] = field(default_factory=list)
    steps: List[SearchStep] = field(default_factory=list)
    total_time: float = 0.0
    total_results: int = 0
    strategy_breakdown: Dict[str, int] = field(default_factory=dict)


class CQLSearchEngine:
    """
    CQL検索エンジン
    
    外部依存を注入可能にし、プロセス情報を返すピュア関数として設計。
    """
    
    def __init__(self, api_executor: Callable[[str], List[Dict]] = None, keyword_extractor=None):
        """
        Args:
            api_executor: CQLクエリを実行する関数（APIアクセス部分）
            keyword_extractor: キーワード抽出器（デフォルトはルールベース）
        """
        self.api_executor = api_executor or self._mock_executor
        
        # キーワード抽出器の設定
        if keyword_extractor is not None:
            self.keyword_extractor = keyword_extractor
        else:
            # デフォルトはルールベース
            from .keyword_extractors import RuleBasedKeywordExtractor
            self.keyword_extractor = RuleBasedKeywordExtractor()
    
    def search(self, query: str, space_key: str = "CLIENTTOMO", 
               hierarchy_filters: List[str] = None, 
               include_deleted: bool = False,
               process_tracker=None) -> SearchResult:
        """
        3段階CQL検索の実行（フィルタ対応・XAI可視化）
        
        Args:
            query: 検索クエリ
            space_key: Confluenceスペースキー
            hierarchy_filters: 階層フィルタ（ancestor条件）
            include_deleted: 削除ページを含むかどうか
            process_tracker: プロセス追跡器（XAI可視化用）
            
        Returns:
            SearchResult: 検索結果とプロセス情報
        """
        result = SearchResult()
        start_time = time.time()
        all_results = []
        
        # フィルタ条件を正規化
        hierarchy_filters = hierarchy_filters or []
        
        # XAI対応: フィルタ条件をプロセス追跡器に記録
        if process_tracker:
            from ..utils.process_tracker import ProcessStage
            filter_conditions = {
                "space_key": space_key,
                "hierarchy_filters": hierarchy_filters,
                "include_deleted": include_deleted,
                "generated_cql_queries": []  # 後で追加
            }
            process_tracker.add_filter_conditions(ProcessStage.SEARCH_EXECUTION, filter_conditions)
        
        # キーワード抽出
        keywords = self.keyword_extractor.extract_keywords(query)
        
        # Step 1: タイトル優先検索（キーワードベース）
        step1 = self._execute_title_search(query, space_key, keywords, hierarchy_filters, include_deleted)
        step1.keywords = keywords  # キーワード情報を追加
        result.steps.append(step1)
        all_results.extend(step1.results if hasattr(step1, 'results') else [])
        
        # Step 2: キーワード分割検索
        step2 = self._execute_keyword_split_search(query, space_key, keywords, hierarchy_filters, include_deleted)
        result.steps.append(step2)
        new_results2 = self._deduplicate_results(
            step2.results if hasattr(step2, 'results') else [], 
            all_results
        )
        all_results.extend(new_results2)
        
        # Step 3: フレーズ検索（クリーンクエリ）
        step3 = self._execute_phrase_search(query, space_key, keywords, hierarchy_filters, include_deleted)
        step3.keywords = keywords  # キーワード情報を追加
        result.steps.append(step3)
        new_results3 = self._deduplicate_results(
            step3.results if hasattr(step3, 'results') else [], 
            all_results
        )
        all_results.extend(new_results3)
        
        # XAI対応: 生成されたCQLクエリをプロセス追跡器に追加
        if process_tracker:
            all_cql_queries = []
            for step in [step1, step2, step3]:
                all_cql_queries.extend(step.cql_queries)
            
            # フィルタ条件を更新
            filter_conditions = process_tracker.get_filter_conditions(ProcessStage.SEARCH_EXECUTION)
            filter_conditions["generated_cql_queries"] = all_cql_queries
            process_tracker.add_filter_conditions(ProcessStage.SEARCH_EXECUTION, filter_conditions)
        
        # 結果をまとめる
        result.results = all_results
        result.total_time = time.time() - start_time
        result.total_results = len(all_results)
        result.strategy_breakdown = {
            "title_search": step1.results_count,
            "keyword_split": len(new_results2),
            "phrase_search": len(new_results3)
        }
        
        return result
    
    def _execute_title_search(self, query: str, space_key: str, keywords: List[str] = None, 
                              hierarchy_filters: List[str] = None, include_deleted: bool = False) -> SearchStep:
        """タイトル優先検索の実行（キーワードベース、汎用句除去）"""
        step = SearchStep(
            step_number=1,
            strategy_name="title_priority",
            query=query
        )
        
        start_time = time.time()
        try:
            # 基本のCQL条件を構築
            if keywords and len(keywords) > 0:
                # 複数キーワードの場合はOR検索
                if len(keywords) == 1:
                    base_condition = f'title ~ "{keywords[0]}"'
                else:
                    keyword_conditions = ' OR '.join([f'title ~ "{kw}"' for kw in keywords])
                    base_condition = f'({keyword_conditions})'
            else:
                # フォールバック: 汎用句を除去したクリーンクエリ
                clean_query = self._clean_query_for_search(query)
                base_condition = f'title ~ "{clean_query}"'
            
            # CQLクエリを構築（フィルタ条件を統合）
            cql = self._build_cql_with_filters(base_condition, space_key, hierarchy_filters, include_deleted)
            step.cql_queries.append(cql)
            
            results = self.api_executor(cql)
            step.results_count = len(results)
            step.results = results  # Store results in step
            
        except Exception as e:
            step.error = str(e)
            step.results = []
        
        step.execution_time = time.time() - start_time
        return step
    
    def _build_cql_with_filters(self, base_condition: str, space_key: str, 
                                hierarchy_filters: List[str] = None, include_deleted: bool = False) -> str:
        """
        基本条件とフィルタ条件を統合してCQLクエリを構築
        
        Args:
            base_condition: 基本検索条件 (e.g., 'title ~ "keyword"')
            space_key: スペースキー
            hierarchy_filters: 階層フィルタリスト
            include_deleted: 削除ページを含むかどうか
            
        Returns:
            str: 完全なCQLクエリ
        """
        conditions = [base_condition]
        
        # スペース条件を追加
        conditions.append(f'space = "{space_key}"')
        
        # 階層フィルタを追加
        if hierarchy_filters:
            # 複数の階層フィルタをOR条件で結合
            hierarchy_conditions = []
            for filter_condition in hierarchy_filters:
                if filter_condition.strip():  # 空文字列を除外
                    hierarchy_conditions.append(filter_condition)
            
            if hierarchy_conditions:
                if len(hierarchy_conditions) == 1:
                    conditions.append(hierarchy_conditions[0])
                else:
                    combined_hierarchy = ' OR '.join(f'({condition})' for condition in hierarchy_conditions)
                    conditions.append(f'({combined_hierarchy})')
        
        # 削除ページフィルタを追加（設定ファイルから読み込み）
        if not include_deleted:
            # 設定ファイルから除外パターンを取得
            exclusion_patterns = settings.cql_exclusion_patterns
            for pattern in exclusion_patterns:
                conditions.append(f'title !~ "{pattern}"')
        
        # 全条件をAND条件で結合
        final_cql = ' AND '.join(conditions)
        
        return final_cql
    
    def _execute_keyword_split_search(self, query: str, space_key: str, keywords: List[str] = None, 
                                      hierarchy_filters: List[str] = None, include_deleted: bool = False) -> SearchStep:
        """キーワード分割検索の実行（抽出済みキーワードを使用）"""
        step = SearchStep(
            step_number=2,
            strategy_name="keyword_split",
            query=query
        )
        
        start_time = time.time()
        try:
            # 渡されたキーワードを使用、なければ内部で抽出
            if keywords is None:
                keywords = self.keyword_extractor.extract_keywords(query)
            
            step.keywords = keywords
            
            if len(keywords) >= 2:
                # AND検索
                and_conditions = " AND ".join([f'text ~ "{kw}"' for kw in keywords])
                and_base_condition = f'({and_conditions})'
                cql_and = self._build_cql_with_filters(and_base_condition, space_key, hierarchy_filters, include_deleted)
                step.cql_queries.append(f"CQL_AND: {cql_and}")
                
                # OR検索
                or_conditions = " OR ".join([f'text ~ "{kw}"' for kw in keywords])
                or_base_condition = f'({or_conditions})'
                cql_or = self._build_cql_with_filters(or_base_condition, space_key, hierarchy_filters, include_deleted)
                step.cql_queries.append(f"CQL_OR: {cql_or}")
                
                # 両方の検索を実行して結果を統合
                and_results = self.api_executor(cql_and)
                or_results = self.api_executor(cql_or)
                
                # 結果を統合（重複除去）
                combined_results = []
                seen_ids = set()
                
                # AND検索結果を優先
                for result in and_results:
                    if result.get('id') not in seen_ids:
                        combined_results.append(result)
                        seen_ids.add(result.get('id'))
                
                # OR検索結果を追加（重複は除外）
                for result in or_results:
                    if result.get('id') not in seen_ids:
                        combined_results.append(result)
                        seen_ids.add(result.get('id'))
                
                results = combined_results
                step.results_count = len(results)
            else:
                step.results = []
                
        except Exception as e:
            step.error = str(e)
            step.results = []
        
        step.execution_time = time.time() - start_time
        return step
    
    def _execute_phrase_search(self, query: str, space_key: str, keywords: List[str] = None, 
                               hierarchy_filters: List[str] = None, include_deleted: bool = False) -> SearchStep:
        """フレーズ検索の実行（クリーンクエリ）"""
        step = SearchStep(
            step_number=3,
            strategy_name="phrase_search", 
            query=query
        )
        
        start_time = time.time()
        try:
            # 基本のCQL条件を構築
            if keywords and len(keywords) > 0:
                # 複数キーワードの場合はOR検索
                if len(keywords) == 1:
                    base_condition = f'text ~ "{keywords[0]}"'
                else:
                    keyword_conditions = ' OR '.join([f'text ~ "{kw}"' for kw in keywords])
                    base_condition = f'({keyword_conditions})'
            else:
                # フォールバック: 汎用句を除去したクリーンクエリ
                clean_query = self._clean_query_for_search(query)
                base_condition = f'text ~ "{clean_query}"'
            
            # CQLクエリを構築（フィルタ条件を統合）
            cql = self._build_cql_with_filters(base_condition, space_key, hierarchy_filters, include_deleted)
            step.cql_queries.append(cql)
            
            results = self.api_executor(cql)
            step.results_count = len(results)
            step.results = results  # Store results in step
            
        except Exception as e:
            step.error = str(e)
            step.results = []
        
        step.execution_time = time.time() - start_time
        return step
    
    def _clean_query_for_search(self, query: str) -> str:
        """
        検索クエリから汎用句を除去してクリーンなクエリを生成
        
        Args:
            query: 元のクエリ
            
        Returns:
            str: クリーンなクエリ
        """
        # 除去する汎用句のリスト
        generic_phrases = [
            'について教えて', 'について', 'を教えて', 'について教えて下さい',
            'を整理して', 'を抽出して', 'の詳細', 'の仕様', 'に関して',
            'に関する', 'はどう', 'はどのよう', 'とは', 'です', 'ます', 
            'してください', 'ください', '下さい'
        ]
        
        clean_query = query
        
        # 汎用句を除去
        for phrase in generic_phrases:
            clean_query = clean_query.replace(phrase, '')
        
        # 余分な空白を除去
        clean_query = ' '.join(clean_query.split())
        
        # 空になった場合は元のクエリを返す
        if not clean_query.strip():
            return query
            
        return clean_query.strip()
    
    def _extract_keywords(self, query: str) -> List[str]:
        """キーワード抽出（レガシー互換性用）"""
        return self.keyword_extractor.extract_keywords(query)
    
    def _deduplicate_results(self, new_results: List[Dict], existing_results: List[Dict]) -> List[Dict]:
        """結果の重複除去"""
        existing_ids = {r.get('id') for r in existing_results if r.get('id')}
        return [r for r in new_results if r.get('id') not in existing_ids]
    
    def _mock_executor(self, cql: str) -> List[Dict[str, Any]]:
        """モック実行器（テスト用）"""
        return [
            {"id": f"mock_{hash(cql)}", "title": "Mock Result", "content": "Mock content"}
        ] 