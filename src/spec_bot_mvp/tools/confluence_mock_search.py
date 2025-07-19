"""
Confluence モック検索ツール

confluence_index.jsonのテストデータを使用して、
ハイブリッド検索システムの精度テストを行うためのモック機能
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from ..utils.log_config import get_logger

logger = get_logger(__name__)


class ConfluenceMockSearch:
    """
    confluence_index.jsonを使用したモック検索システム
    
    実際のConfluence検索の動作を模擬し、
    テストデータでの精度測定を可能にします。
    """
    
    def __init__(self, test_data_path: str = "cache/confluence_index.json"):
        """モック検索システムの初期化"""
        self.test_data_path = Path(test_data_path)
        self.test_data = self._load_test_data()
        logger.info(f"ConfluenceMockSearch初期化完了: {len(self.test_data.get('pages', {}))}ページ")
    
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
    
    def search_basic(self, query: str) -> Dict[str, Any]:
        """基本検索（タイトル・内容の部分一致）"""
        start_time = time.time()
        results = []
        
        if not self.test_data or "pages" not in self.test_data:
            return self._empty_result(query, time.time() - start_time)
        
        query_lower = query.lower().strip()
        
        for page_id, page_info in self.test_data["pages"].items():
            score = 0
            title = page_info.get("title", "").lower()
            content = page_info.get("content_preview", "").lower()
            labels = [label.lower() for label in page_info.get("labels", [])]
            
            # スコア計算
            if query_lower in title:
                score += 100  # タイトル完全一致は最高スコア
            elif any(word in title for word in query_lower.split()):
                score += 50   # タイトル部分一致
            
            if query_lower in content:
                score += 30   # 内容完全一致
            elif any(word in content for word in query_lower.split()):
                score += 10   # 内容部分一致
            
            # ラベル一致
            if any(query_lower in label for label in labels):
                score += 40
            
            if score > 0:
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "url": page_info.get("url", ""),
                    "score": score
                })
        
        # スコア順でソート
        results.sort(key=lambda x: x["score"], reverse=True)
        
        execution_time = time.time() - start_time
        
        return {
            "query": query,
            "results": results,
            "total_count": len(results),
            "execution_time": execution_time,
            "search_type": "basic"
        }
    
    def search_enhanced_cql(self, query: str) -> Dict[str, Any]:
        """高精度CQL検索の模擬（5段階戦略）"""
        start_time = time.time()
        
        # Strategy 1: タイトル優先検索
        title_results = self._strategy_title_priority(query)
        if title_results:
            return self._format_result(query, title_results, time.time() - start_time, "enhanced_cql_title")
        
        # Strategy 2: キーワード分割検索
        keyword_results = self._strategy_keyword_split(query)
        if keyword_results:
            return self._format_result(query, keyword_results, time.time() - start_time, "enhanced_cql_keyword")
        
        # Strategy 3: 完全フレーズ検索
        phrase_results = self._strategy_phrase_search(query)
        if phrase_results:
            return self._format_result(query, phrase_results, time.time() - start_time, "enhanced_cql_phrase")
        
        # Strategy 4: 部分一致検索
        partial_results = self._strategy_partial_match(query)
        if partial_results:
            return self._format_result(query, partial_results, time.time() - start_time, "enhanced_cql_partial")
        
        # Strategy 5: フォールバック
        fallback_results = self._strategy_fallback(query)
        return self._format_result(query, fallback_results, time.time() - start_time, "enhanced_cql_fallback")
    
    def _strategy_title_priority(self, query: str) -> List[Dict[str, Any]]:
        """Strategy 1: タイトル優先検索"""
        results = []
        query_lower = query.lower()
        
        for page_id, page_info in self.test_data.get("pages", {}).items():
            title = page_info.get("title", "").lower()
            if query_lower in title:
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "score": 100,
                    "strategy": "title_priority"
                })
        
        return results
    
    def _strategy_keyword_split(self, query: str) -> List[Dict[str, Any]]:
        """Strategy 2: キーワード分割検索"""
        results = []
        keywords = query.lower().split()
        
        for page_id, page_info in self.test_data.get("pages", {}).items():
            title = page_info.get("title", "").lower()
            content = page_info.get("content_preview", "").lower()
            
            # 複数キーワードのAND検索
            title_matches = sum(1 for kw in keywords if kw in title)
            content_matches = sum(1 for kw in keywords if kw in content)
            
            if title_matches >= len(keywords) * 0.5:  # 50%以上のキーワードがタイトルに含まれる
                score = 80 + title_matches * 5
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "score": score,
                    "strategy": "keyword_split"
                })
        
        return results
    
    def _strategy_phrase_search(self, query: str) -> List[Dict[str, Any]]:
        """Strategy 3: 完全フレーズ検索"""
        results = []
        query_lower = query.lower()
        
        for page_id, page_info in self.test_data.get("pages", {}).items():
            content = page_info.get("content_preview", "").lower()
            if query_lower in content:
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "score": 60,
                    "strategy": "phrase_search"
                })
        
        return results
    
    def _strategy_partial_match(self, query: str) -> List[Dict[str, Any]]:
        """Strategy 4: 部分一致検索"""
        results = []
        keywords = query.lower().split()
        
        for page_id, page_info in self.test_data.get("pages", {}).items():
            title = page_info.get("title", "").lower()
            content = page_info.get("content_preview", "").lower()
            labels = [label.lower() for label in page_info.get("labels", [])]
            
            score = 0
            for keyword in keywords:
                if keyword in title:
                    score += 20
                if keyword in content:
                    score += 10
                if any(keyword in label for label in labels):
                    score += 15
            
            if score > 0:
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "score": score,
                    "strategy": "partial_match"
                })
        
        return results
    
    def _strategy_fallback(self, query: str) -> List[Dict[str, Any]]:
        """Strategy 5: フォールバック（全検索）"""
        results = []
        query_lower = query.lower()
        
        for page_id, page_info in self.test_data.get("pages", {}).items():
            title = page_info.get("title", "").lower()
            content = page_info.get("content_preview", "").lower()
            
            if any(char in title + content for char in query_lower.split()):
                results.append({
                    "page_id": page_id,
                    "title": page_info.get("title", ""),
                    "content_preview": page_info.get("content_preview", ""),
                    "labels": page_info.get("labels", []),
                    "score": 10,
                    "strategy": "fallback"
                })
        
        return results
    
    def _format_result(self, query: str, results: List[Dict[str, Any]], execution_time: float, search_type: str) -> Dict[str, Any]:
        """検索結果のフォーマット"""
        # スコア順でソート
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
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
            "search_type": "empty"
        }
    
    def search_chain_prompts(self, query: str) -> str:
        """チェーンプロンプト検索の模擬"""
        search_result = self.search_enhanced_cql(query)
        
        if search_result["total_count"] == 0:
            return f"「{query}」に関する情報は見つかりませんでした。"
        
        # 結果を文字列形式で返す（実際のツールと同じ形式）
        response_parts = [f"「{query}」について以下の情報が見つかりました：\n"]
        
        for i, result in enumerate(search_result["results"][:3], 1):  # 上位3件
            title = result["title"]
            content = result["content_preview"][:200] + "..." if len(result["content_preview"]) > 200 else result["content_preview"]
            response_parts.append(f"\n**{i}. {title}**\n{content}\n")
        
        return "\n".join(response_parts)


# ツール関数（テスト用）
def search_confluence_mock_basic(query: str) -> str:
    """モック基本検索ツール"""
    mock_search = ConfluenceMockSearch()
    result = mock_search.search_basic(query)
    
    if result["total_count"] == 0:
        return f"「{query}」に関する情報は見つかりませんでした。"
    
    response_parts = [f"「{query}」について{result['total_count']}件の情報が見つかりました：\n"]
    
    for i, page in enumerate(result["results"][:5], 1):  # 上位5件
        title = page["title"]
        content = page["content_preview"][:150] + "..." if len(page["content_preview"]) > 150 else page["content_preview"]
        response_parts.append(f"\n**{i}. {title}** (スコア: {page['score']})\n{content}\n")
    
    return "\n".join(response_parts)


def search_confluence_mock_enhanced(query: str) -> str:
    """モック高精度検索ツール"""
    mock_search = ConfluenceMockSearch()
    result = mock_search.search_enhanced_cql(query)
    
    if result["total_count"] == 0:
        return f"「{query}」に関する情報は見つかりませんでした。"
    
    search_type = result["search_type"]
    response_parts = [f"「{query}」について{result['total_count']}件の情報が見つかりました (検索戦略: {search_type})：\n"]
    
    for i, page in enumerate(result["results"][:3], 1):  # 上位3件
        title = page["title"]
        strategy = page.get("strategy", "unknown")
        content = page["content_preview"][:200] + "..." if len(page["content_preview"]) > 200 else page["content_preview"]
        response_parts.append(f"\n**{i}. {title}** (戦略: {strategy})\n{content}\n")
    
    return "\n".join(response_parts)


def search_confluence_mock_chain(query: str) -> str:
    """モックチェーンプロンプト検索ツール"""
    mock_search = ConfluenceMockSearch()
    return mock_search.search_chain_prompts(query) 