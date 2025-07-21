"""
Confluence 改善版モック検索ツール

精度テストで発見された問題を解決する改善版：
1. 関連語辞書による関連検索
2. 自然言語前処理による不要語句除去
3. 厳密なスコアリングによる誤検出防止
4. 多段階フォールバック戦略
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Set
from ..utils.log_config import get_logger

logger = get_logger(__name__)


class ConfluenceImprovedMockSearch:
    """
    改善版モック検索システム
    
    精度テストで発見された問題を解決し、
    より高精度な検索を実現します。
    """
    
    def __init__(self, test_data_path: str = "cache/confluence_index.json"):
        """改善版モック検索システムの初期化"""
        self.test_data_path = Path(test_data_path)
        self.test_data = self._load_test_data()
        self.related_terms = self._initialize_related_terms()
        self.stop_words = self._initialize_stop_words()
        logger.info(f"ConfluenceImprovedMockSearch初期化完了: {len(self.test_data.get('pages', {}))}ページ")
    
    def _load_test_data(self) -> Dict[str, Any]:
        """テストデータの読み込み"""
        try:
            if self.test_data_path.exists():
                with open(self.test_data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"テストデータ読み込み完了: {self.test_data_path}")
                    return data
            else:
                logger.warning(f"テストデータファイルが見つかりません: {self.test_data_path}")
                return {}
        except Exception as e:
            logger.error(f"テストデータ読み込みエラー: {e}")
            return {}
    
    def _initialize_related_terms(self) -> Dict[str, List[str]]:
        """関連語辞書の初期化"""
        return {
            # セキュリティ関連
            "セキュリティ": ["認証", "パスワード", "暗号化", "アクセス制御", "ガイドライン"],
            "認証": ["セキュリティ", "ログイン", "パスワード", "セッション", "トークン"],
            "対策": ["ガイドライン", "手順", "仕様", "設計", "方針"],
            
            # 技術関連
            "API": ["設計", "仕様", "認証", "エンドポイント"],
            "データベース": ["設計", "スキーマ", "テーブル", "ユーザー", "権限"],
            "テスト": ["統合", "仕様", "パフォーマンス", "UI", "手順"],
            
            # プロセス関連
            "デプロイ": ["手順", "環境", "プロセス", "本番", "ステージング"],
            "手順": ["デプロイ", "テスト", "プロセス", "ガイドライン"],
            
            # 自然言語パターン
            "について": [],  # 除去対象
            "教えて": [],   # 除去対象
            "仕様": ["設計", "ドキュメント", "API"],
            "機能": ["設計", "仕様", "実装"]
        }
    
    def _initialize_stop_words(self) -> Set[str]:
        """ストップワード（除去対象語句）の初期化"""
        return {
            "について", "教えて", "ください", "です", "ます", "である", "に関する",
            "に関して", "とは", "の", "を", "が", "は", "で", "と", "から", "まで"
        }
    
    def _preprocess_query(self, query: str) -> List[str]:
        """クエリの前処理"""
        # 小文字化
        query = query.lower().strip()
        
        # 特殊文字の除去
        query = re.sub(r'[^\w\s]', ' ', query)
        
        # 単語分割
        words = query.split()
        
        # ストップワード除去
        filtered_words = [word for word in words if word not in self.stop_words]
        
        # 関連語展開
        expanded_words = set(filtered_words)
        for word in filtered_words:
            if word in self.related_terms:
                expanded_words.update(self.related_terms[word])
        
        result = list(expanded_words)
        logger.info(f"クエリ前処理: '{query}' → {result}")
        return result
    
    def search_improved_enhanced(self, query: str) -> Dict[str, Any]:
        """改善版高精度検索"""
        start_time = time.time()
        processed_keywords = self._preprocess_query(query)
        
        if not processed_keywords:
            return self._empty_result(query, time.time() - start_time)
        
        # 改善版5段階戦略
        strategies = [
            ("exact_title_match", self._strategy_exact_title_match),
            ("semantic_title_match", self._strategy_semantic_title_match),
            ("multi_keyword_content", self._strategy_multi_keyword_content),
            ("related_terms_search", self._strategy_related_terms_search),
            ("fuzzy_fallback", self._strategy_fuzzy_fallback)
        ]
        
        for strategy_name, strategy_func in strategies:
            results = strategy_func(processed_keywords, query)
            if results:
                execution_time = time.time() - start_time
                return self._format_result(query, results, execution_time, f"improved_{strategy_name}")
        
        # 全て失敗した場合
        execution_time = time.time() - start_time
        return self._empty_result(query, execution_time)
    
    def _strategy_exact_title_match(self, keywords: List[str], original_query: str) -> List[Dict[str, Any]]:
        """戦略1: 完全タイトル一致"""
        results = []
        original_lower = original_query.lower()
        
        for page_id, page_info in self.test_data.get("pages", {}).items():
            title = page_info.get("title", "").lower()
            
            # 原文クエリがタイトルに含まれるかチェック
            if original_lower in title or any(keyword in title for keyword in keywords):
                score = 100 if original_lower in title else 80
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "score": score,
                    "strategy": "exact_title_match",
                    "matched_keywords": [kw for kw in keywords if kw in title]
                })
        
        return sorted(results, key=lambda x: x["score"], reverse=True)
    
    def _strategy_semantic_title_match(self, keywords: List[str], original_query: str) -> List[Dict[str, Any]]:
        """戦略2: 意味的タイトル一致"""
        results = []
        
        for page_id, page_info in self.test_data.get("pages", {}).items():
            title = page_info.get("title", "").lower()
            labels = [label.lower() for label in page_info.get("labels", [])]
            
            score = 0
            matched_keywords = []
            
            # タイトルでのキーワード一致
            for keyword in keywords:
                if keyword in title:
                    score += 30
                    matched_keywords.append(keyword)
            
            # ラベルでのキーワード一致
            for keyword in keywords:
                if any(keyword in label for label in labels):
                    score += 20
                    matched_keywords.append(f"label:{keyword}")
            
            # 閾値以上のスコアの場合のみ結果に含める
            if score >= 20:  # 最低1つのキーワードは一致している必要
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "score": score,
                    "strategy": "semantic_title_match",
                    "matched_keywords": matched_keywords
                })
        
        return sorted(results, key=lambda x: x["score"], reverse=True)
    
    def _strategy_multi_keyword_content(self, keywords: List[str], original_query: str) -> List[Dict[str, Any]]:
        """戦略3: 複数キーワード内容検索"""
        results = []
        
        for page_id, page_info in self.test_data.get("pages", {}).items():
            title = page_info.get("title", "").lower()
            content = page_info.get("content_preview", "").lower()
            labels = [label.lower() for label in page_info.get("labels", [])]
            
            score = 0
            matched_keywords = []
            
            # 複数キーワードでの評価
            for keyword in keywords:
                keyword_score = 0
                if keyword in title:
                    keyword_score += 25
                    matched_keywords.append(f"title:{keyword}")
                if keyword in content:
                    keyword_score += 15
                    matched_keywords.append(f"content:{keyword}")
                if any(keyword in label for label in labels):
                    keyword_score += 10
                    matched_keywords.append(f"label:{keyword}")
                
                score += keyword_score
            
            # 複数キーワードボーナス
            unique_matches = len(set(kw.split(':')[1] if ':' in kw else kw for kw in matched_keywords))
            if unique_matches >= 2:
                score += unique_matches * 5
            
            # 閾値チェック
            if score >= 15:
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "score": score,
                    "strategy": "multi_keyword_content",
                    "matched_keywords": matched_keywords
                })
        
        return sorted(results, key=lambda x: x["score"], reverse=True)
    
    def _strategy_related_terms_search(self, keywords: List[str], original_query: str) -> List[Dict[str, Any]]:
        """戦略4: 関連語検索"""
        results = []
        
        # 関連語を展開
        all_related_terms = set(keywords)
        for keyword in keywords:
            if keyword in self.related_terms:
                all_related_terms.update(self.related_terms[keyword])
        
        for page_id, page_info in self.test_data.get("pages", {}).items():
            title = page_info.get("title", "").lower()
            content = page_info.get("content_preview", "").lower()
            labels = [label.lower() for label in page_info.get("labels", [])]
            
            score = 0
            matched_terms = []
            
            for term in all_related_terms:
                if term in title:
                    weight = 20 if term in keywords else 10  # 元キーワードは高重み
                    score += weight
                    matched_terms.append(f"title:{term}")
                if term in content:
                    weight = 12 if term in keywords else 6
                    score += weight
                    matched_terms.append(f"content:{term}")
                if any(term in label for label in labels):
                    weight = 8 if term in keywords else 4
                    score += weight
                    matched_terms.append(f"label:{term}")
            
            if score >= 10:
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "score": score,
                    "strategy": "related_terms_search",
                    "matched_keywords": matched_terms
                })
        
        return sorted(results, key=lambda x: x["score"], reverse=True)
    
    def _strategy_fuzzy_fallback(self, keywords: List[str], original_query: str) -> List[Dict[str, Any]]:
        """戦略5: あいまいフォールバック"""
        results = []
        
        for page_id, page_info in self.test_data.get("pages", {}).items():
            title = page_info.get("title", "").lower()
            content = page_info.get("content_preview", "").lower()
            
            score = 0
            for keyword in keywords:
                # 部分文字列マッチング
                for word in title.split() + content.split():
                    if keyword in word or word in keyword:
                        score += 3
            
            if score >= 5:  # 非常に低い閾値
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "score": score,
                    "strategy": "fuzzy_fallback",
                    "matched_keywords": []
                })
        
        return sorted(results, key=lambda x: x["score"], reverse=True)
    
    def _format_result(self, query: str, results: List[Dict[str, Any]], execution_time: float, search_type: str) -> Dict[str, Any]:
        """検索結果のフォーマット"""
        return {
            "query": query,
            "results": results,
            "total_count": len(results),
            "execution_time": execution_time,
            "search_type": search_type
        }
    
    def _empty_result(self, query: str, execution_time: float) -> Dict[str, Any]:
        """空の検索結果"""
        return {
            "query": query,
            "results": [],
            "total_count": 0,
            "execution_time": execution_time,
            "search_type": "no_results"
        }
    
    def search_chain_prompts_improved(self, query: str) -> str:
        """改善版チェーンプロンプト検索"""
        search_result = self.search_improved_enhanced(query)
        
        if search_result["total_count"] == 0:
            return f"「{query}」に関する情報は見つかりませんでした。"
        
        # 結果を文字列形式で返す
        response_parts = [f"「{query}」について{search_result['total_count']}件の情報が見つかりました (検索戦略: {search_result['search_type']})：\n"]
        
        for i, result in enumerate(search_result["results"][:3], 1):  # 上位3件
            title = result["title"]
            strategy = result.get("strategy", "unknown")
            matched_keywords = result.get("matched_keywords", [])
            content = result["content_preview"][:200] + "..." if len(result["content_preview"]) > 200 else result["content_preview"]
            
            response_parts.append(f"\n**{i}. {title}** (戦略: {strategy}, マッチ: {len(matched_keywords)}件)")
            response_parts.append(f"   {content}\n")
        
        return "\n".join(response_parts)


# 改善版ツール関数
def search_confluence_improved_enhanced(query: str) -> str:
    """改善版高精度検索ツール"""
    mock_search = ConfluenceImprovedMockSearch()
    result = mock_search.search_improved_enhanced(query)
    
    if result["total_count"] == 0:
        return f"「{query}」に関する情報は見つかりませんでした。"
    
    search_type = result["search_type"]
    response_parts = [f"「{query}」について{result['total_count']}件の情報が見つかりました (検索戦略: {search_type})：\n"]
    
    for i, page in enumerate(result["results"][:3], 1):  # 上位3件
        title = page["title"]
        strategy = page.get("strategy", "unknown")
        score = page.get("score", 0)
        matched_keywords = page.get("matched_keywords", [])
        content = page["content_preview"][:200] + "..." if len(page["content_preview"]) > 200 else page["content_preview"]
        
        response_parts.append(f"\n**{i}. {title}** (戦略: {strategy}, スコア: {score}, マッチ: {len(matched_keywords)}件)")
        response_parts.append(f"   マッチキーワード: {', '.join(matched_keywords[:5])}")
        response_parts.append(f"   {content}\n")
    
    return "\n".join(response_parts)


def search_confluence_improved_chain(query: str) -> str:
    """改善版チェーンプロンプト検索ツール"""
    mock_search = ConfluenceImprovedMockSearch()
    return mock_search.search_chain_prompts_improved(query) 