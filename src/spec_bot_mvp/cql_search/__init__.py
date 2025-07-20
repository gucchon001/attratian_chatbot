"""
CQL検索専用モジュール

シンプルで再利用可能なCQL検索機能を提供します。
外部依存を最小限に抑え、単体テスト可能な設計です。

Version: 1.0.0
"""

from .engine import CQLSearchEngine, SearchResult, SearchStep
from .formatters import CQLResultFormatter, ProcessMessageFormatter
from .keyword_extractors import (
    RuleBasedKeywordExtractor, 
    GeminiKeywordExtractor, 
    MockGeminiKeywordExtractor
)
from .api_executors import APIExecutor, ConfluenceAPIExecutor, MockAPIExecutor

__all__ = [
    "CQLSearchEngine",
    "SearchResult",
    "SearchStep",
    "CQLResultFormatter",
    "ProcessMessageFormatter",
    "RuleBasedKeywordExtractor",
    "GeminiKeywordExtractor", 
    "MockGeminiKeywordExtractor",
    "APIExecutor",
    "ConfluenceAPIExecutor",
    "MockAPIExecutor"
]

__version__ = "1.0.0" 