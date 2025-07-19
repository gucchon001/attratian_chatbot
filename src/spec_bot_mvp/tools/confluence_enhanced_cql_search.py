"""
Confluence 高精度CQL検索ツール

根本的な検索精度問題を解決するため、複数のCQL戦略を組み合わせた検索システム。
タイトル優先、キーワード分割、段階的フォールバック戦略を実装。
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from atlassian import Confluence

from ..config.settings import settings
from ..utils.log_config import get_logger

logger = get_logger(__name__)


class ConfluenceEnhancedCQLSearch:
    """
    Confluence高精度CQL検索システム
    
    検索精度向上のための複数戦略:
    1. タイトル優先検索 (title ~)
    2. キーワード分割検索 (AND/OR組み合わせ)
    3. 完全フレーズ検索 (text ~)
    4. 部分一致検索 (含む、類似語)
    5. 段階的フォールバック戦略
    """
    
    def __init__(self):
        """CQL検索システムの初期化"""
        self.confluence = self._initialize_confluence()
        self.space_key = settings.confluence_space or "CLIENTTOMO"
        logger.info("ConfluenceEnhancedCQLSearch初期化完了")
    
    def _initialize_confluence(self) -> Confluence:
        """Confluence接続の初期化"""
        return Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
    
    def search_with_enhanced_cql(self, query: str, max_results: int = 20) -> Dict[str, Any]:
        """
        高精度CQL検索の実行
        
        Args:
            query: 検索クエリ
            max_results: 最大結果数
            
        Returns:
            検索結果と詳細メタデータ
        """
        logger.info(f"高精度CQL検索開始: '{query}'")
        start_time = time.time()
        
        try:
            # 段階的検索戦略の実行
            all_results = []
            search_strategies = [
                self._strategy_1_title_priority,
                self._strategy_2_keyword_split,
                self._strategy_3_phrase_search,
                self._strategy_4_partial_match,
                self._strategy_5_fallback_broad
            ]
            
            unique_page_ids = set()
            strategy_results = {}
            
            for i, strategy in enumerate(search_strategies, 1):
                strategy_name = strategy.__name__.replace('_strategy_', 'Strategy').replace('_', '')
                logger.info(f"実行中: {strategy_name}")
                
                try:
                    results = strategy(query, max_results // len(search_strategies))
                    if results:
                        new_results = []
                        for result in results:
                            page_id = result.get('content', {}).get('id') or result.get('id')
                            if page_id and page_id not in unique_page_ids:
                                unique_page_ids.add(page_id)
                                result['search_strategy'] = strategy_name
                                new_results.append(result)
                        
                        all_results.extend(new_results)
                        strategy_results[strategy_name] = len(new_results)
                        logger.info(f"{strategy_name}: {len(new_results)}件の新規結果")
                    
                    # 十分な結果が得られたら早期終了
                    if len(all_results) >= max_results:
                        logger.info(f"十分な結果数({len(all_results)})に達したため検索終了")
                        break
                        
                except Exception as e:
                    logger.warning(f"{strategy_name}でエラー: {e}")
                    continue
            
            # 結果のスコアリングと順位付け
            scored_results = self._score_and_rank_results(all_results, query)
            
            execution_time = time.time() - start_time
            
            # メタデータの構築
            metadata = {
                'total_results': len(scored_results),
                'unique_pages': len(unique_page_ids),
                'execution_time': execution_time,
                'strategies_used': strategy_results,
                'query': query
            }
            
            logger.info(f"高精度CQL検索完了: {len(scored_results)}件 | 実行時間: {execution_time:.2f}秒")
            
            return {
                'results': scored_results[:max_results],
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"高精度CQL検索エラー: {str(e)}")
            return {'results': [], 'metadata': {'error': str(e)}}
    
    def _strategy_1_title_priority(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """戦略1: タイトル優先検索"""
        try:
            # タイトルでの完全一致検索
            cql = f'title ~ "{query}" and space = "{self.space_key}"'
            results = self._execute_cql(cql, limit)
            
            if not results:
                # タイトルでのキーワード分割検索
                keywords = self._extract_keywords(query)
                if len(keywords) > 1:
                    keyword_conditions = ' AND '.join([f'title ~ "{kw}"' for kw in keywords])
                    cql = f'({keyword_conditions}) and space = "{self.space_key}"'
                    results = self._execute_cql(cql, limit)
            
            return results
            
        except Exception as e:
            logger.warning(f"タイトル優先検索エラー: {e}")
            return []
    
    def _strategy_2_keyword_split(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """戦略2: キーワード分割検索"""
        try:
            keywords = self._extract_keywords(query)
            if len(keywords) < 2:
                return []
            
            # AND検索（厳密）
            and_conditions = ' AND '.join([f'text ~ "{kw}"' for kw in keywords])
            cql = f'({and_conditions}) and space = "{self.space_key}"'
            results = self._execute_cql(cql, limit // 2)
            
            # OR検索（広範囲）- 残りの枠で実行
            if len(results) < limit:
                or_conditions = ' OR '.join([f'text ~ "{kw}"' for kw in keywords])
                cql = f'({or_conditions}) and space = "{self.space_key}"'
                or_results = self._execute_cql(cql, limit - len(results))
                
                # 重複除去
                existing_ids = {r.get('content', {}).get('id') or r.get('id') for r in results}
                for result in or_results:
                    result_id = result.get('content', {}).get('id') or result.get('id')
                    if result_id not in existing_ids:
                        results.append(result)
            
            return results
            
        except Exception as e:
            logger.warning(f"キーワード分割検索エラー: {e}")
            return []
    
    def _strategy_3_phrase_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """戦略3: 完全フレーズ検索"""
        try:
            # 従来の完全フレーズ検索
            cql = f'text ~ "{query}" and space = "{self.space_key}"'
            return self._execute_cql(cql, limit)
            
        except Exception as e:
            logger.warning(f"完全フレーズ検索エラー: {e}")
            return []
    
    def _strategy_4_partial_match(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """戦略4: 部分一致検索"""
        try:
            keywords = self._extract_keywords(query)
            results = []
            
            # 各キーワードの部分文字列検索
            for keyword in keywords:
                if len(keyword) >= 3:  # 3文字以上のキーワードのみ
                    # 部分文字列の生成
                    substrings = self._generate_substrings(keyword)
                    for substring in substrings:
                        if len(substring) >= 2:
                            cql = f'text ~ "{substring}" and space = "{self.space_key}"'
                            partial_results = self._execute_cql(cql, max(1, limit // len(keywords) // len(substrings)))
                            results.extend(partial_results)
                            
                            if len(results) >= limit:
                                break
                    
                    if len(results) >= limit:
                        break
            
            return results[:limit]
            
        except Exception as e:
            logger.warning(f"部分一致検索エラー: {e}")
            return []
    
    def _strategy_5_fallback_broad(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """戦略5: 幅広いフォールバック検索"""
        try:
            results = []
            
            # 類似語の検索
            related_terms = self._generate_related_terms(query)
            for term in related_terms:
                cql = f'text ~ "{term}" and space = "{self.space_key}"'
                term_results = self._execute_cql(cql, max(1, limit // len(related_terms)))
                results.extend(term_results)
                
                if len(results) >= limit:
                    break
            
            # 最後の手段：スペース内の最近更新されたページ
            if not results:
                cql = f'space = "{self.space_key}" order by lastModified desc'
                results = self._execute_cql(cql, min(5, limit))
                logger.info("フォールバック: 最近更新されたページを返却")
            
            return results[:limit]
            
        except Exception as e:
            logger.warning(f"フォールバック検索エラー: {e}")
            return []
    
    def _execute_cql(self, cql: str, limit: int) -> List[Dict[str, Any]]:
        """CQLクエリの実行"""
        try:
            logger.debug(f"CQL実行: {cql}")
            search_result = self.confluence.cql(cql, limit=limit)
            
            if search_result and 'results' in search_result:
                return search_result['results']
            return []
            
        except Exception as e:
            logger.warning(f"CQL実行エラー ({cql[:50]}...): {e}")
            return []
    
    def _extract_keywords(self, query: str) -> List[str]:
        """キーワード抽出"""
        # 基本的なキーワード抽出（日本語対応）
        # ノイズワードの除去
        noise_words = {'の', 'について', 'に関して', '仕様', '詳細', '情報', '教えて', 'を', 'が', 'は', 'で', 'から', 'まで'}
        
        # スペースと句読点で分割
        words = re.split(r'[\s　、。，．・]+', query.strip())
        
        # フィルタリング
        keywords = []
        for word in words:
            word = word.strip()
            if word and len(word) >= 2 and word not in noise_words:
                keywords.append(word)
        
        return keywords[:5]  # 最大5個のキーワード
    
    def _generate_substrings(self, keyword: str) -> List[str]:
        """キーワードの部分文字列生成"""
        substrings = []
        
        # 長いキーワードの場合、部分文字列を生成
        if len(keyword) >= 4:
            # 前半、後半の部分文字列
            mid = len(keyword) // 2
            substrings.append(keyword[:mid+1])  # 前半+1文字
            substrings.append(keyword[mid-1:])  # 後半+1文字
        
        # 部分語幹の抽出（日本語の語幹）
        if len(keyword) >= 3:
            substrings.append(keyword[:-1])  # 最後の1文字を除去
            if len(keyword) >= 4:
                substrings.append(keyword[1:])  # 最初の1文字を除去
        
        return list(set(substrings))  # 重複除去
    
    def _generate_related_terms(self, query: str) -> List[str]:
        """関連語の生成"""
        related_terms = []
        
        # 強化された関連語マッピング（固有名詞・業務特化語を追加）
        term_mapping = {
            'ログイン': ['認証', 'サインイン', 'login', 'auth', 'アカウント', 'AKI様', 'アカウント管理画面', 'ユーザー認証', '二段階認証'],
            '機能': ['仕様', 'フィーチャー', 'feature', '設計', '実装', '要件', 'specification'],
            '仕様': ['機能', 'spec', 'specification', '設計書', '要件定義', '実装'],
            '急募': ['緊急', '至急', '急ぎ', 'urgent'],
            'セキュリティ': ['安全', 'security', '認証', 'アクセス制御'],
            'API': ['インターフェース', 'エンドポイント', 'REST', 'JSON'],
            'AKI': ['AKI様', 'aki', 'アカウント管理', 'ログイン'],
            'アカウント': ['ログイン', '認証', 'AKI様', 'ユーザー', 'account'],
            '管理画面': ['管理', 'admin', 'アドミン', '管理者', 'マネジメント'],
            '認証': ['ログイン', 'auth', 'authentication', 'セキュリティ', '二段階認証'],
            '二段階認証': ['2FA', 'ログイン', '認証', 'パスコード', 'セキュリティ'],
            'パスワード': ['認証', 'ログイン', 'セキュリティ', 'パスコード'],
            'セッション': ['ログイン', '認証', 'セキュリティ', 'タイムアウト'],
        }
        
        keywords = self._extract_keywords(query)
        for keyword in keywords:
            # 完全一致検索
            if keyword in term_mapping:
                related_terms.extend(term_mapping[keyword])
            
            # 部分一致検索（より柔軟なマッピング）
            for key, values in term_mapping.items():
                if keyword in key or key in keyword:
                    related_terms.extend(values)
        
        # 重複除去と元のキーワードは除外
        unique_terms = []
        for term in related_terms:
            if term not in unique_terms and term not in keywords:
                unique_terms.append(term)
        
        return unique_terms[:5]  # 最大5個の関連語（拡張）
    
    def _score_and_rank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """結果のスコアリングと順位付け"""
        keywords = self._extract_keywords(query)
        
        for result in results:
            score = 0
            content = result.get('content', result)
            title = content.get('title', '')
            
            # タイトルマッチスコア（高優先度）
            for keyword in keywords:
                if keyword.lower() in title.lower():
                    score += 10
                    
            # 完全一致ボーナス
            if query.lower() in title.lower():
                score += 20
                
            # 戦略ボーナス
            strategy = result.get('search_strategy', '')
            if 'TitlePriority' in strategy:
                score += 15
            elif 'KeywordSplit' in strategy:
                score += 10
            elif 'PhraseSearch' in strategy:
                score += 5
                
            result['relevance_score'] = score
        
        # スコアでソート
        return sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    def format_enhanced_results(self, search_data: Dict[str, Any], query: str) -> str:
        """検索結果の整形"""
        results = search_data.get('results', [])
        metadata = search_data.get('metadata', {})
        
        if not results:
            return f"「{query}」に関する情報は見つかりませんでした。"
        
        # 結果の整形
        formatted_lines = []
        formatted_lines.append("🔍 **Confluence高精度CQL検索結果**")
        formatted_lines.append(f"📝 検索クエリ: 「{query}」")
        formatted_lines.append(f"📊 発見ページ: {metadata.get('total_results', 0)}件 | 実行時間: {metadata.get('execution_time', 0):.2f}秒")
        
        # 戦略別統計
        strategies = metadata.get('strategies_used', {})
        if strategies:
            strategy_stats = " | ".join([f"{k}: {v}件" for k, v in strategies.items() if v > 0])
            formatted_lines.append(f"🎯 戦略別結果: {strategy_stats}")
        
        formatted_lines.append("⭐ 関連度順に表示")
        formatted_lines.append("")
        
        # 各結果の表示
        for i, result in enumerate(results[:10], 1):
            content = result.get('content', result)
            title = content.get('title', 'タイトル不明')
            web_ui_url = content.get('_links', {}).get('webui')
            relevance = result.get('relevance_score', 0)
            strategy = result.get('search_strategy', '不明')
            
            if web_ui_url and not web_ui_url.startswith('http'):
                web_ui_url = f"https://{settings.atlassian_domain}{web_ui_url}"
            
            formatted_lines.append(f"📄 **{i}. {title}** (関連度: {relevance}点)")
            if web_ui_url:
                formatted_lines.append(f"   🔗 {web_ui_url}")
            formatted_lines.append(f"   🎯 検索戦略: {strategy}")
            formatted_lines.append("")
        
        formatted_lines.append("💡 **推奨アクション:**")
        formatted_lines.append("• 上位結果をクリックして詳細を確認してください")
        formatted_lines.append("• より詳細な情報が必要な場合は、具体的なキーワードで再検索してください")
        
        return "\n".join(formatted_lines)


# ツール関数（LangChainエージェントから呼び出し可能）
def search_confluence_with_enhanced_cql(query: str) -> str:
    """
    高精度CQLによるConfluence検索ツール
    
    Args:
        query: 検索クエリ（"ログイン機能の仕様について"形式）
        
    Returns:
        高精度検索による詳細な結果
    """
    try:
        # QueryからスペースキーとクエリテキストをパースS
        parts = query.split(",")
        search_query = parts[0].replace("query:", "").strip()
        
        # 高精度CQL検索を実行
        enhanced_search = ConfluenceEnhancedCQLSearch()
        search_data = enhanced_search.search_with_enhanced_cql(search_query)
        
        return enhanced_search.format_enhanced_results(search_data, search_query)
        
    except Exception as e:
        logger.error(f"高精度CQL検索ツールエラー: {e}")
        return f"検索エラー: {str(e)}" 