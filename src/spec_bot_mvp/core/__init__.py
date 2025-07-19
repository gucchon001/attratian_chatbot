"""
コアモジュール

LangChainエージェントとその関連機能を提供します。
Step1-3統合パイプラインも含みます。
"""

from .agent import SpecBotAgent
# 削除されたコンポーネント: QuestionAnalyzer, ResultSynthesizer, IntegratedPipeline

__all__ = [
    "SpecBotAgent",
] 