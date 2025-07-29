"""
Confluence 基本検索ツール - 正しいCQL検索実装

自然言語クエリから適切なキーワードを抽出し、
段階的なCQL検索戦略で高精度な結果を返します。
"""

import logging
import re
from typing import List, Dict, Any, Optional
from atlassian import Confluence

from ..config.settings import settings
from ..utils.log_config import get_logger

logger = get_logger(__name__)


class ConfluenceBasicSearch:
    """
    基本的で正確なConfluence検索システム
    
    1. 自然言語からキーワード抽出
    2. 段階的CQL検索戦略
    3. シンプルで確実な結果取得
    """
    
    def __init__(self):
        """基本検索システムの初期化"""
        self.confluence = self._initialize_confluence()
        self.space_key = settings.confluence_space or "TEST"
        logger.info("ConfluenceBasicSearch初期化完了")
    
    def _initialize_confluence(self) -> Confluence:
        """Confluence接続の初期化"""
        return Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
    
    def search(self, user_query: str) -> str:
        """
        基本的なConfluence検索の実行
        
        Args:
            user_query: ユーザーの自然言語クエリ
            
        Returns:
            str: 整形された検索結果
        """
        if not user_query or not user_query.strip():
            return "検索キーワードが指定されていません。"
        
        logger.info(f"基本Confluence検索開始: '{user_query}'")
        
        try:
            # 1. キーワード抽出
            keywords = self._extract_keywords(user_query)
            if not keywords:
                return f"検索可能なキーワードが見つかりませんでした: '{user_query}'"
            
            logger.info(f"抽出されたキーワード: {keywords}")
            
            # 2. 段階的検索実行
            search_result = self._execute_progressive_search(keywords)
            
            if not search_result['results'] or search_result['results'].get('totalSize', 0) == 0:
                return f"「{', '.join(keywords)}」に関する情報は見つかりませんでした。"
            
            # 3. ウェイト適用による結果の改良
            enhanced_results = self._apply_keyword_weighting(
                search_result['results']['results'],
                keywords
            )
            
            # 結果を元の形式に戻す
            enhanced_search_result = search_result['results'].copy()
            enhanced_search_result['results'] = enhanced_results
            
            # 4. 結果整形
            formatted_result = self._format_results(
                enhanced_search_result,
                keywords,
                user_query,
                search_result['strategy_used'] + " + Keyword Weighting",
                search_result['cql_query']
            )
            
            logger.info(f"基本検索完了: {search_result['strategy_used']} で {search_result['results'].get('totalSize', 0)}件")
            return formatted_result
            
        except Exception as e:
            logger.error(f"基本Confluence検索エラー: {str(e)}")
            return f"検索中にエラーが発生しました: {str(e)}"
    
    def _extract_keywords(self, user_query: str) -> List[str]:
        """
        自然言語クエリからCQL検索用キーワードを抽出
        
        Args:
            user_query: ユーザーの質問
            
        Returns:
            List[str]: 抽出されたキーワードリスト
        """
        # ストップワード定義
        stop_words = {
            "について", "教えて", "ください", "の", "を", "に", "は", "が", "で", "と", "から",
            "まで", "より", "など", "こと", "もの", "それ", "これ", "あれ", "どれ", "何",
            "どう", "どの", "いつ", "どこ", "なぜ", "どうして", "する", "した", "して",
            "います", "ます", "です", "である", "だ", "なる", "なった", "なり", "探して", 
            "見つけて", "確認", "調べて", "知りたい"
        }
        
        # 重要キーワード抽出
        keywords = []
        
        # 1. 助詞での分割を試行
        for delimiter in ["の", "について", "を", "に", "は", "が"]:
            user_query = user_query.replace(delimiter, " ")
        
        # 2. 文字列を単語候補に分割（改良版）
        # カタカナ、ひらがな、漢字、英数字の境界で分割
        words = re.findall(r'[ァ-ヶー]+|[一-龯]+|[A-Za-z0-9]+', user_query)
        
        # 3. スペースでも分割
        space_words = user_query.split()
        words.extend(space_words)
        
        # 4. 重要な単語パターンを特別処理
        important_patterns = [
            r'ログイン[機能]*',
            r'API[設計]*[書]*',
            r'データベース[設計]*',
            r'セキュリティ[ガイドライン]*',
            r'テスト[仕様書]*'
        ]
        
        for pattern in important_patterns:
            matches = re.findall(pattern, user_query)
            words.extend(matches)
        
        # 5. キーワード候補の整理
        for word in words:
            word = word.strip()
            # 長さ2文字以上、ストップワードでない、ひらがなのみでない
            if (len(word) >= 2 and 
                word not in stop_words and 
                not re.match(r'^[ぁ-ん]+$', word) and
                word not in ['機能の仕様について教えて', 'を探しています', 'ガイドラインの詳細', 'について']):
                keywords.append(word)
        
        # 重複除去と順序保持
        unique_keywords = []
        for keyword in keywords:
            if keyword not in unique_keywords:
                unique_keywords.append(keyword)
        
        return unique_keywords[:5]  # 最大5つまで
    
    def _execute_progressive_search(self, keywords: List[str]) -> Dict[str, Any]:
        """
        段階的検索戦略の実行
        
        Args:
            keywords: 検索キーワードリスト
            
        Returns:
            Dict: 検索結果と使用された戦略
        """
        if not keywords:
            return {'results': None, 'strategy_used': 'No keywords', 'cql_query': None}
        
        main_keyword = keywords[0]
        
        # 特定キーワードの特別処理（ログイン以外にも対応）
        special_keywords = {
            "ログイン": ["ログイン", "認証", "ユーザー登録", "権限"],
            "急募": ["急募", "申込", "オプション", "契約"],
            "API": ["API", "設計", "エンドポイント", "インターフェース"],
        }
        
        # 特別処理が必要なキーワードを検出
        special_keyword = None
        for keyword, related_terms in special_keywords.items():
            if keyword in main_keyword or any(keyword in kw for kw in keywords):
                special_keyword = keyword
                related_terms_list = related_terms
                break
        
        if special_keyword:
            logger.info(f"{special_keyword}機能検索の特別処理を実行")
            
            # 関連語を使った包括検索（OR演算子使用）
            related_conditions = " OR ".join([f'title ~ "{term}"' for term in related_terms_list])
            text_conditions = " OR ".join([f'text ~ "{term}"' for term in related_terms_list])
            special_cql = f'space = "{self.space_key}" AND ({related_conditions} OR {text_conditions})'
            logger.info(f"{special_keyword}包括検索実行: {special_cql}")
            
            try:
                results = self.confluence.cql(special_cql, limit=20)
                if results and results.get('totalSize', 0) > 0:
                    return {
                        'results': results,
                        'strategy_used': f'{special_keyword} Comprehensive Search',
                        'cql_query': special_cql
                    }
            except Exception as e:
                logger.warning(f"{special_keyword}包括検索エラー: {e}")
        
        # 戦略1: タイトル優先（全キーワード）
        if len(keywords) >= 2:
            title_all_cql = self._build_title_search_cql(keywords)
            logger.info(f"戦略1実行: {title_all_cql}")
            
            try:
                results = self.confluence.cql(title_all_cql, limit=20)
                if results and results.get('totalSize', 0) > 0:
                    return {
                        'results': results,
                        'strategy_used': 'Strategy 1: Title All Keywords',
                        'cql_query': title_all_cql
                    }
            except Exception as e:
                logger.warning(f"戦略1エラー: {e}")
        
        # 戦略2: タイトル主要キーワード
        title_main_cql = f'space = "{self.space_key}" AND title ~ "{main_keyword}"'
        logger.info(f"戦略2実行: {title_main_cql}")
        
        try:
            results = self.confluence.cql(title_main_cql, limit=20)
            if results and results.get('totalSize', 0) > 0:
                return {
                    'results': results,
                    'strategy_used': 'Strategy 2: Title Main Keyword',
                    'cql_query': title_main_cql
                }
        except Exception as e:
            logger.warning(f"戦略2エラー: {e}")
        
        # 戦略3: テキスト検索（全キーワード）
        if len(keywords) >= 2:
            text_all_cql = self._build_text_search_cql(keywords)
            logger.info(f"戦略3実行: {text_all_cql}")
            
            try:
                results = self.confluence.cql(text_all_cql, limit=20)
                if results and results.get('totalSize', 0) > 0:
                    return {
                        'results': results,
                        'strategy_used': 'Strategy 3: Text All Keywords',
                        'cql_query': text_all_cql
                    }
            except Exception as e:
                logger.warning(f"戦略3エラー: {e}")
        
        # 戦略4: 主要キーワード部分検索（改良版）
        # 主要キーワードを部分に分解して検索範囲を拡大
        primary_parts = []
        if len(main_keyword) > 2:
            import re
            parts = re.findall(r'[ァ-ヶー]+|[一-龯]+|[A-Za-z0-9]+', main_keyword)
            primary_parts = [part for part in parts if len(part) >= 2]
        
        if primary_parts:
            # 部分キーワードでOR検索（より広範囲）
            part_conditions = " OR ".join([f'title ~ "{part}"' for part in primary_parts])
            fallback_cql = f'space = "{self.space_key}" AND ({part_conditions})'
            logger.info(f"戦略4実行（部分キーワード）: {fallback_cql}")
        else:
            # 従来のフォールバック
            fallback_cql = f'space = "{self.space_key}" AND (title ~ "{main_keyword}" OR text ~ "{main_keyword}")'
            logger.info(f"戦略4実行（従来）: {fallback_cql}")
        
        try:
            results = self.confluence.cql(fallback_cql, limit=20)
            return {
                'results': results,
                'strategy_used': 'Strategy 4: Enhanced Fallback with Parts',
                'cql_query': fallback_cql
            }
        except Exception as e:
            logger.error(f"戦略4エラー: {e}")
            return {'results': None, 'strategy_used': 'All strategies failed', 'cql_query': None}
    
    def _build_title_search_cql(self, keywords: List[str]) -> str:
        """タイトル検索用CQLを構築"""
        title_conditions = " AND ".join([f'title ~ "{keyword}"' for keyword in keywords])
        return f'space = "{self.space_key}" AND ({title_conditions})'
    
    def _build_text_search_cql(self, keywords: List[str]) -> str:
        """テキスト検索用CQLを構築"""
        text_conditions = " AND ".join([f'text ~ "{keyword}"' for keyword in keywords])
        return f'space = "{self.space_key}" AND ({text_conditions})'
    
    def _apply_keyword_weighting(self, results: List[Dict], keywords: List[str]) -> List[Dict]:
        """
        検索結果にキーワードウェイトを適用してスコアリングを改良
        
        Args:
            results: 検索結果リスト
            keywords: 抽出されたキーワード
            
        Returns:
            List[Dict]: ウェイト適用後の結果（スコア順）
        """
        if not results or not keywords:
            return results
        
        # 主要キーワードを特定（最初のキーワードまたは最も重要と思われるもの）
        primary_keyword = keywords[0]
        
        # 主要キーワードを部分キーワードに分解
        primary_parts = []
        if len(primary_keyword) > 2:
            # 「急募機能」→「急募」「機能」に分解
            import re
            parts = re.findall(r'[ァ-ヶー]+|[一-龯]+|[A-Za-z0-9]+', primary_keyword)
            primary_parts = [part for part in parts if len(part) >= 2]
        
        weighted_results = []
        
        for result in results:
            title = self._safe_get_title(result)
            excerpt = self._safe_get_excerpt(result)
            
            # 基本スコア計算
            base_score = 0
            weighted_score = 0
            
            # キーワード別スコア計算
            for keyword in keywords:
                title_match = keyword in title
                content_match = keyword in excerpt
                
                if title_match:
                    base_score += 10
                if content_match:
                    base_score += 5
            
            # 主要キーワード部分の高ウェイト適用
            for part in primary_parts:
                title_match = part in title
                content_match = part in excerpt
                
                if title_match:
                    weighted_score += 50  # 主要部分タイトル一致（5倍ウェイト）
                if content_match:
                    weighted_score += 25  # 主要部分テキスト一致（5倍ウェイト）
            
            # 完全一致ボーナス
            if primary_keyword in title:
                weighted_score += 100  # 完全一致の超高ウェイト
            
            total_score = base_score + weighted_score
            
            # 結果にスコア情報を追加
            enhanced_result = result.copy()
            enhanced_result['weighted_score'] = total_score
            enhanced_result['base_score'] = base_score
            enhanced_result['weight_bonus'] = weighted_score
            
            weighted_results.append(enhanced_result)
        
        # ウェイト適用後のスコア順でソート
        weighted_results.sort(key=lambda x: x.get('weighted_score', 0), reverse=True)
        
        logger.info(f"ウェイト適用: {len(results)}件 → 主要キーワード '{primary_keyword}' 部分 {primary_parts}")
        
        return weighted_results

    def _format_results(self, results: Dict[str, Any], keywords: List[str], 
                       original_query: str, strategy_used: str, cql_query: str) -> str:
        """
        検索結果を読みやすい形式に整形
        
        Args:
            results: Confluence検索結果
            keywords: 使用されたキーワード
            original_query: 元の質問
            strategy_used: 使用された検索戦略
            cql_query: 実行されたCQLクエリ
            
        Returns:
            str: 整形された検索結果
        """
        pages = results.get('results', [])
        total_count = results.get('totalSize', 0)
        
        if not pages:
            return f"「{', '.join(keywords)}」に関する情報は見つかりませんでした。"
        
        # ヘッダー部分
        result_lines = [
            f"📚 **Confluence検索結果（基本検索）**",
            f"🔍 質問: 「{original_query}」",
            f"🔑 抽出キーワード: {', '.join(keywords)}",
            f"⚙️  検索戦略: {strategy_used}",
            f"📊 結果: {len(pages)}件表示（総数: {total_count}件）",
            "",
            f"💻 実行CQL: `{cql_query}`",
            ""
        ]
        
        # 各ページの詳細
        for i, page in enumerate(pages[:5], 1):  # 最大5件表示
            try:
                # ページ情報の取得
                title = self._safe_get_title(page)
                page_id = self._safe_get_page_id(page)
                space_info = self._safe_get_space_info(page)
                excerpt = self._safe_get_excerpt(page)
                
                # URL構築
                page_url = f"https://{settings.atlassian_domain}/wiki/spaces/{space_info['key']}/pages/{page_id}"
                
                # ウェイトスコア情報の取得
                weighted_score = page.get('weighted_score', 0)
                base_score = page.get('base_score', 0)
                weight_bonus = page.get('weight_bonus', 0)
                
                score_info = ""
                if weighted_score > 0:
                    score_info = f" (スコア: {weighted_score}"
                    if weight_bonus > 0:
                        score_info += f" = {base_score} + {weight_bonus}ボーナス"
                    score_info += ")"
                
                result_lines.extend([
                    f"📄 **{i}. {title}**{score_info}",
                    f"   🔗 リンク: {page_url}",
                ])
                
                if excerpt:
                    clean_excerpt = self._clean_html_tags(excerpt)[:200]
                    result_lines.append(f"   📝 抜粋: {clean_excerpt}...")
                
                result_lines.append("")
                
            except Exception as e:
                logger.warning(f"ページ {i} の処理エラー: {e}")
                result_lines.append(f"📄 **{i}. [処理エラー]**")
                result_lines.append("")
        
        # 残りの件数表示
        if total_count > 5:
            result_lines.append(f"📋 さらに {total_count - 5} 件のページがあります。")
            result_lines.append("")
        
        # 利用のヒント
        result_lines.extend([
            "💡 **利用のヒント:**",
            "- より具体的なキーワードで検索すると精度が向上します",
            "- 特定のページについて詳しく聞くことができます",
            "- 関連する別のキーワードでも検索してみてください"
        ])
        
        return "\n".join(result_lines)
    
    def _safe_get_title(self, page: Dict[str, Any]) -> str:
        """安全にページタイトルを取得"""
        return (page.get('title') or 
                page.get('content', {}).get('title', 'タイトルなし'))
    
    def _safe_get_page_id(self, page: Dict[str, Any]) -> str:
        """安全にページIDを取得"""
        return (page.get('id') or 
                page.get('content', {}).get('id', 'N/A'))
    
    def _safe_get_space_info(self, page: Dict[str, Any]) -> Dict[str, str]:
        """安全にスペース情報を取得"""
        space_info = (page.get('space') or 
                     page.get('content', {}).get('space', {}))
        
        if isinstance(space_info, dict):
            return {
                'name': space_info.get('name', self.space_key),
                'key': space_info.get('key', self.space_key)
            }
        else:
            return {'name': self.space_key, 'key': self.space_key}
    
    def _safe_get_excerpt(self, page: Dict[str, Any]) -> str:
        """安全に抜粋を取得"""
        return page.get('excerpt', '') or page.get('bodyExcerpt', '')
    
    def _clean_html_tags(self, text: str) -> str:
        """HTMLタグを除去してプレーンテキストにする"""
        if not text:
            return ""
        
        # HTMLタグを除去
        text = re.sub(r'<[^>]+>', '', text)
        
        # HTMLエンティティをデコード
        html_entities = {
            '&lt;': '<', '&gt;': '>', '&amp;': '&',
            '&quot;': '"', '&#39;': "'", '&nbsp;': ' '
        }
        
        for entity, char in html_entities.items():
            text = text.replace(entity, char)
        
        # 余分な空白を整理
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text


# エクスポート用の関数
def search_confluence_basic(query: str) -> str:
    """
    基本Confluence検索のエントリーポイント
    
    Args:
        query: ユーザーの検索クエリ
        
    Returns:
        str: 検索結果
    """
    searcher = ConfluenceBasicSearch()
    return searcher.search(query) 