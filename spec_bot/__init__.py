"""
仕様書作成支援ボット - メインモジュール

シンプル化されたディレクトリ構造でのメインモジュールです。
Atlassian（Confluence/Jira）連携によるドキュメント検索と仕様書作成支援を提供します。

Version: 2.0 (Refactored Structure)
"""

__version__ = "2.0.0"
__author__ = "Specification Support Bot Team"

# メインコンポーネントの公開
from .core.agent import SpecBotAgent

__all__ = [
    "SpecBotAgent",
] 