"""
Confluence高精度CQL検索ツール (Gemini強化版)

新しいモジュール化されたCQL検索エンジンとGeminiキーワード抽出器を使用した
高精度検索機能。詳細なプロセス表示と共に、確実に関連ドキュメントを取得します。
"""

import time
import logging
import os
from typing import List, Dict, Any, Optional
from atlassian import Confluence

from ..cql_search.engine import CQLSearchEngine
from ..cql_search.keyword_extractors import GeminiKeywordExtractor, MockGeminiKeywordExtractor
from ..cql_search.formatters import StreamlitSearchFormatter
from ..config.settings import settings

logger = logging.getLogger(__name__)

# グローバル変数：ProcessDetailCallbackの共有
_global_callback = None
_search_engine = None
_search_formatter = None
_confluence_api = None

def set_global_callback(callback):
    """グローバルコールバックを設定"""
    global _global_callback
    _global_callback = callback

def get_global_callback():
    """グローバルコールバックを取得"""
    global _global_callback
    return _global_callback

def _get_confluence_api():
    """Confluence APIのシングルトンインスタンスを取得"""
    global _confluence_api
    
    if _confluence_api is None:
        _confluence_api = Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        logger.info("✅ Confluence API接続を初期化")
    
    return _confluence_api

def _confluence_api_executor(cql_query: str) -> List[Dict[str, Any]]:
    """
    実際のConfluence APIを呼び出してCQLクエリを実行
    
    Args:
        cql_query: 実行するCQLクエリ
        
    Returns:
        List[Dict]: 検索結果のリスト
    """
    try:
        confluence = _get_confluence_api()
        
        logger.info(f"🔍 CQLクエリ実行: {cql_query}")
        start_time = time.time()
        
        # Confluence検索の実行
        search_result = confluence.cql(cql_query, limit=10)
        execution_time = time.time() - start_time
        
        if not search_result or 'results' not in search_result:
            logger.warning(f"⚠️ CQLクエリ結果なし: {cql_query}")
            return []
        
        results = search_result['results']
        total_count = search_result.get('totalSize', 0)
        
        logger.info(f"✅ CQLクエリ完了: {len(results)}件取得 (総数: {total_count}) | 実行時間: {execution_time:.2f}秒")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Confluence API エラー: {str(e)} | クエリ: {cql_query}")
        return []

def _get_search_engine():
    """CQL検索エンジンのシングルトンインスタンスを取得"""
    global _search_engine, _search_formatter
    
    if _search_engine is None:
        # Gemini APIキーワード抽出器の初期化
        api_key = settings.gemini_api_key
        if api_key:
            try:
                keyword_extractor = GeminiKeywordExtractor(api_key)
                logger.info("✅ Gemini APIキーワード抽出器を初期化")
            except Exception as e:
                logger.warning(f"⚠️ Gemini API初期化失敗、モックを使用: {e}")
                keyword_extractor = MockGeminiKeywordExtractor()
        else:
            logger.warning("⚠️ Gemini APIキーなし、モックキーワード抽出器を使用")
            keyword_extractor = MockGeminiKeywordExtractor()
        
        # CQL検索エンジンの初期化（実際のConfluence API executor付き）
        _search_engine = CQLSearchEngine(
            api_executor=_confluence_api_executor,  # 実際のAPI executor
            keyword_extractor=keyword_extractor
        )
        _search_formatter = StreamlitSearchFormatter()
        logger.info("✅ CQL検索エンジン（実Confluence API付き）とフォーマッターを初期化")
    
    return _search_engine, _search_formatter

def search_confluence_with_enhanced_cql(query: str) -> str:
    """
    Gemini強化CQL検索のメイン関数
    
    Args:
        query: 検索クエリ
        
    Returns:
        str: フォーマットされた検索結果
    """
    try:
        logger.info(f"🔍 Gemini強化CQL検索開始: '{query}'")
        
        # 検索エンジンとフォーマッターを取得
        search_engine, formatter = _get_search_engine()
        
        # CQL検索実行
        search_result = search_engine.search(query)
        
        # Streamlit向けにフォーマット
        formatted_result = formatter.format_search_result(search_result)
        
        logger.info(f"✅ Gemini強化CQL検索完了: {search_result.total_results}件取得")
        
        return formatted_result
        
    except Exception as e:
        error_msg = f"❌ Gemini強化CQL検索エラー: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_detailed_process_info(query: str) -> Dict[str, Any]:
    """
    検索プロセスの詳細情報を取得（デバッグ・表示用）
    
    Args:
        query: 検索クエリ
        
    Returns:
        Dict: プロセス詳細情報
    """
    try:
        search_engine, _ = _get_search_engine()
        search_result = search_engine.search(query)
        
        # キーワード抽出器から直接キーワードを取得
        keywords = search_engine.keyword_extractor.extract_keywords(query)
        
        # ステップ情報をプロセス詳細形式に変換
        process_details = []
        for step in search_result.steps:
            process_details.append({
                "strategy": step.strategy_name,
                "cql_query": " | ".join(step.cql_queries) if step.cql_queries else "N/A",
                "result_count": step.results_count,
                "execution_time": step.execution_time,
                "error": step.error
            })
        
        return {
            "query": query,
            "extracted_keywords": keywords,
            "process_details": process_details,
            "total_results": search_result.total_results,
            "strategy_results": search_result.strategy_breakdown,
            "execution_time": search_result.total_time
        }
        
    except Exception as e:
        logger.error(f"プロセス詳細取得エラー: {e}")
        return {
            "query": query,
            "error": str(e)
        } 