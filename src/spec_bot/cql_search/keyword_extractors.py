"""
キーワード抽出器

ルールベースとGemini APIベースのキーワード抽出を提供。
依存性注入により切り替え可能。
"""

import re
import logging
from typing import List, Protocol, Optional
from abc import ABC, abstractmethod
import google.generativeai as genai

logger = logging.getLogger(__name__)


class KeywordExtractor(Protocol):
    """キーワード抽出器のインターフェース"""
    
    def extract_keywords(self, query: str) -> List[str]:
        """クエリからキーワードを抽出"""
        ...


class RuleBasedKeywordExtractor:
    """ルールベースキーワード抽出器（現在の実装）"""
    
    def extract_keywords(self, query: str) -> List[str]:
        """ルールベースでキーワードを抽出"""
        # 基本的なノイズワード除去（拡張版）
        noise_words = {
            'について', 'に関して', '詳細', '情報', '教えて', 'を', 'が', 'は', 'で', 'の', 'から', 'まで',
            'どの', 'その', 'この', 'それ', 'これ', 'する', 'した', 'される', 'して', 'なる', 'ある',
            'ください', 'ます', 'です', 'である', 'だ', 'と', 'に', 'へ', 'も', 'ついて', 'いて'
        }
        
        # Step 1: 複合語パターンの分割
        compound_patterns = [
            (r'(\w+)機能', r'\1 機能'),        # XX機能 → XX 機能
            (r'(\w+)設計書', r'\1 設計書'),    # XX設計書 → XX 設計書
            (r'(\w+)仕様書', r'\1 仕様書'),    # XX仕様書 → XX 仕様書
            (r'(\w+)システム', r'\1 システム'), # XXシステム → XX システム
            (r'(\w+)管理', r'\1 管理'),        # XX管理 → XX 管理
        ]
        
        processed_query = query
        for pattern, replacement in compound_patterns:
            processed_query = re.sub(pattern, replacement, processed_query)
        
        # Step 2: 助詞や一般的な区切り文字で分割
        split_patterns = r'[のをがはにへからまで、。！？\s]+'
        parts = re.split(split_patterns, processed_query)
        
        # Step 3: 各部分から有意なキーワードを抽出
        keywords = []
        for part in parts:
            if not part:
                continue
            
            # さらに単語分割
            words = re.findall(r'[ぁ-んァ-ヶー一-龯a-zA-Z]+', part)
            for word in words:
                if len(word) >= 2 and word not in noise_words:
                    # 特定の接尾辞を持つ場合は分割
                    if word.endswith('について'):
                        clean_word = word[:-3]
                        if len(clean_word) >= 2:
                            keywords.append(clean_word)
                    elif word.endswith('を教えて'):
                        clean_word = word[:-3]
                        if len(clean_word) >= 2:
                            keywords.append(clean_word)
                    else:
                        keywords.append(word)
        
        # 重複除去
        unique_keywords = []
        for keyword in keywords:
            if keyword not in unique_keywords:
                unique_keywords.append(keyword)
        
        return unique_keywords[:5]


class GeminiKeywordExtractor:
    """Gemini APIを使った高精度キーワード抽出器"""
    
    def __init__(self, api_key: str):
        """Gemini APIキーワード抽出器の初期化"""
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel('gemini-2.0-flash')

    def extract_keywords(self, query: str) -> List[str]:
        """Gemini APIを使用してキーワードを抽出"""
        if not query.strip():
            return []
        
        # Gemini用プロンプト
        prompt = f"""
以下のクエリから、Confluence検索に適した重要なキーワードを抽出してください。

【クエリ】
{query}

【抽出ルール】
1. 具体的で意味のあるキーワードのみ抽出
2. 助詞（を、が、は、に、で、の等）は除外
3. 動詞（教えて、整理して、抽出して等）は除外
4. 汎用語は除外（仕様、機能、詳細、システム、フロー、パターン等）
5. 複合語は保持しつつ、重要な構成要素も分けて抽出
   例：「急募機能」→「急募機能,急募」（「機能」は汎用語なので除外）
   例：「ログイン機能」→「ログイン機能,ログイン」（「機能」は除外）
   例：「会員登録フロー」→「会員登録フロー,会員登録」（「フロー」は除外）
6. 最大4個まで、重要度順で出力
7. 出力形式：カンマ区切りのキーワードのみ（説明文不要）

例：
クエリ「急募機能の仕様を教えて」→「急募機能,急募」
クエリ「ログイン機能の仕様について」→「ログイン機能,ログイン」
クエリ「API設計書について教えて」→「API設計書,API」
クエリ「教室コピーを使う際の仕様を整理して」→「教室コピー」
クエリ「会員登録フローのエラーパターンを抽出して」→「会員登録フロー,会員登録,エラーパターン」
"""

        try:
            response = self.client.generate_content(prompt)
            if response and response.text:
                # カンマ区切りで分割し、前後の空白を除去
                keywords = [kw.strip() for kw in response.text.strip().split(',') if kw.strip()]
                return keywords[:4]  # 最大4個に制限
            else:
                # フォールバック
                fallback = RuleBasedKeywordExtractor()
                return fallback.extract_keywords(query)
        except Exception as e:
            print(f"❌ Gemini API エラー: {e}")
            # フォールバック
            fallback = RuleBasedKeywordExtractor()
            return fallback.extract_keywords(query)


class MockGeminiKeywordExtractor:
    """テスト用モックGeminiキーワード抽出器"""
    
    def extract_keywords(self, query: str) -> List[str]:
        """モック実装：汎用語を除外し、具体的なキーワードのみを抽出する高精度な結果を返す"""
        # 実際のGemini APIが返すであろう高精度な結果をシミュレート（汎用語除外）
        mock_results = {
            "急募機能の仕様を教えて": ["急募機能", "急募"],  # 「仕様」「機能」除外
            "ログイン機能の仕様について": ["ログイン機能", "ログイン"],  # 「機能」「仕様」除外
            "API設計書について教えて": ["API設計書", "API"],  # 「設計書」は保持、具体的なため
            "教室コピーを使う際の仕様を整理して": ["教室コピー"],  # 「仕様」除外
            "会員登録フローのエラーパターンを抽出して": ["会員登録フロー", "会員登録", "エラーパターン"],  # 「フロー」は複合語としては保持
            "ユーザー管理システムの詳細": ["ユーザー管理システム", "ユーザー管理"],  # 「システム」「詳細」除外
            "データベース設計の仕様書": ["データベース設計", "データベース"],  # 「仕様書」除外
            "セキュリティガイドラインについて": ["セキュリティガイドライン", "セキュリティ"],  # 具体的なため保持
        }
        
        # 完全一致があればそれを返す
        if query in mock_results:
            return mock_results[query]
        
        # 部分一致を試す
        for key, value in mock_results.items():
            if any(word in query for word in key.split()):
                return value
        
        # フォールバック：ルールベース
        fallback = RuleBasedKeywordExtractor()
        return fallback.extract_keywords(query) 