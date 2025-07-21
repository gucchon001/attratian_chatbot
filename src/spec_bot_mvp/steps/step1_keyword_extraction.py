"""
Step1: キーワード抽出機能

自然言語クエリからJQL/CQL検索キーワードを抽出する
- Gemini AI による高精度日本語解析
- フォールバック: ルールベースキーワード抽出
- 検索意図分析（仕様書、バグ報告、進捗確認等）
"""

import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

from src.spec_bot_mvp.config.settings import settings

logger = logging.getLogger(__name__)

class KeywordExtractor:
    """Step1: キーワード抽出エンジン"""
    
    def __init__(self):
        self.gemini_available = self._init_gemini()
        
    def _init_gemini(self) -> bool:
        """Gemini AI初期化"""
        if not ChatGoogleGenerativeAI or not settings.google_api_key:
            logger.warning("Gemini API利用不可 - ルールベース抽出にフォールバック")
            return False
            
        try:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=settings.google_api_key,
                temperature=0.1
            )
            logger.info("Gemini AI初期化成功")
            return True
        except Exception as e:
            logger.error(f"Gemini AI初期化失敗: {e}")
            return False
    
    def extract_keywords(self, user_query: str) -> Dict[str, Any]:
        """
        自然言語クエリからキーワードを抽出
        
        Args:
            user_query: ユーザーの自然言語クエリ
            
        Returns:
            Dict containing:
            - primary_keywords: 主要検索キーワード
            - secondary_keywords: 補助検索キーワード 
            - search_intent: 検索意図分析
            - extraction_method: 抽出手法 (gemini/rule_based)
        """
        logger.info(f"キーワード抽出開始: {user_query[:50]}...")
        
        if self.gemini_available:
            try:
                return self._extract_with_gemini(user_query)
            except Exception as e:
                logger.warning(f"Gemini抽出失敗、ルールベースにフォールバック: {e}")
                
        return self._extract_with_rules(user_query)
    
    def _extract_with_gemini(self, user_query: str) -> Dict[str, Any]:
        """Gemini AIによるキーワード抽出（仕様書準拠）"""
        prompt = f"""
あなたはJira/Confluence検索専門のキーワード抽出AIです。
仕様書に従って、ユーザーの自然言語クエリから効果的な検索キーワードを抽出してください。

入力クエリ: "{user_query}"

## 抽出ルール（仕様書準拠）:

### 1. 複合語分解
- 「ログイン機能」 → [ログイン機能, ログイン]
- 「会員登録フロー」 → [会員登録フロー, 会員登録]
- 「API設計書」 → [API設計書, API, 設計書]
- 「UI画面仕様」 → [UI画面仕様, UI, 画面, 仕様]

### 2. 助詞の自動除去
除去対象:
- 助詞: について、～は、を、が、に、で、から、まで、教えて
- 動詞: 教えて、整理して、抽出して、確認して、見つけて
- 冗長表現: ～について詳しく、～の内容を、～に関する情報

### 3. 最大4キーワード制限
重要度順で最大4つまで抽出してください。

### 4. 判定専用語も含める
以下の語も抽出対象に含めてください（後でデータソース判定に使用）:
- Confluence判定語: 仕様, 詳細, 設計書, API, 要件, 実装, フロー, 画面, UI
- Jira判定語: チケット, 進捗, バグ, 不具合, タスク, issue, 対応状況, 修正

以下の形式でJSONを出力してください:
{{
    "primary_keywords": ["抽出キーワード1", "抽出キーワード2", "抽出キーワード3", "抽出キーワード4"],
    "search_intent": "検索意図（仕様確認/バグ調査/進捗確認/機能理解等）",
    "extraction_method": "gemini",
    "compound_words_detected": ["検出された複合語1", "検出された複合語2"],
    "removed_particles": ["除去された助詞・動詞1", "除去された助詞・動詞2"]
}}

重要: primary_keywordsは必ず4個以下にしてください。
"""
        
        response = self.llm.invoke(prompt)
        
        # JSON解析
        import json
        try:
            # レスポンスからJSONを抽出
            json_start = response.content.find('{')
            json_end = response.content.rfind('}') + 1
            json_str = response.content[json_start:json_end]
            
            result = json.loads(json_str)
            
            # 4キーワード制限確保
            if len(result.get("primary_keywords", [])) > 4:
                result["primary_keywords"] = result["primary_keywords"][:4]
            
            # 仕様書準拠の戻り値形式に調整
            result["secondary_keywords"] = []  # 仕様書では主要キーワードのみ
            
            logger.info(f"Geminiキーワード抽出成功（仕様書準拠）: {result['primary_keywords']}")
            return result
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Gemini応答JSON解析失敗: {e}")
            raise
    
    def _extract_with_rules(self, user_query: str) -> Dict[str, Any]:
        """ルールベースキーワード抽出（フォールバック）"""
        
        # 基本的なキーワード抽出
        primary_keywords = []
        secondary_keywords = []
        
        # 技術用語辞書
        tech_terms = {
            r'ログイン|login': ['ログイン', 'login', '認証', 'authentication'],
            r'バグ|bug|不具合|エラー|error': ['バグ', 'bug', '不具合', 'エラー', 'issue'],
            r'API|api': ['API', 'インターフェース', 'endpoint'],
            r'UI|ui|画面|インターフェース': ['UI', 'interface', '画面', 'ユーザーインターフェース'],
            r'DB|database|データベース': ['データベース', 'database', 'DB'],
            r'仕様書|spec|specification': ['仕様書', 'specification', '仕様', 'spec'],
            r'設計書|design': ['設計書', 'design', '設計'],
            r'テスト|test': ['テスト', 'test', 'testing', '検証']
        }
        
        # 技術用語マッチング
        query_lower = user_query.lower()
        for pattern, keywords in tech_terms.items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                primary_keywords.extend(keywords[:2])  # 主要2つ
                secondary_keywords.extend(keywords[2:])  # 残りは補助
        
        # 名詞抽出（簡易版）
        nouns = re.findall(r'[ぁ-んァ-ヶ一-龯a-zA-Z]{2,10}', user_query)
        for noun in nouns:
            if len(noun) >= 2 and noun not in primary_keywords:
                if len(primary_keywords) < 3:
                    primary_keywords.append(noun)
                else:
                    secondary_keywords.append(noun)
        
        # 検索意図推定
        search_intent = self._infer_intent(user_query)
        
        # 重複除去
        primary_keywords = list(dict.fromkeys(primary_keywords))[:4]
        secondary_keywords = list(dict.fromkeys(secondary_keywords))[:3]
        
        result = {
            "primary_keywords": primary_keywords,
            "secondary_keywords": secondary_keywords,
            "search_intent": search_intent,
            "extraction_method": "rule_based"
        }
        
        logger.info(f"ルールベースキーワード抽出完了: {primary_keywords}")
        return result
    
    def _infer_intent(self, query: str) -> str:
        """検索意図の推定"""
        intent_patterns = {
            "仕様確認": [r'仕様', r'spec', r'どのように', r'機能', r'動作'],
            "バグ調査": [r'バグ', r'bug', r'エラー', r'不具合', r'原因', r'問題'],
            "進捗確認": [r'進捗', r'状況', r'進行', r'完了', r'予定', r'status'],
            "機能理解": [r'とは', r'について', r'方法', r'使い方', r'説明'],
            "設計確認": [r'設計', r'design', r'アーキテクチャ', r'構造']
        }
        
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return intent
                    
        return "一般検索" 