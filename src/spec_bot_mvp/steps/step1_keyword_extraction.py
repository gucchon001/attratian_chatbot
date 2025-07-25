"""
Step1: キーワード抽出機能

自然言語クエリからJQL/CQL検索キーワードを抽出する
- Gemini AI による高精度日本語解析
- CLIENTTOMO特化辞書による精度向上
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

from src.spec_bot_mvp.config.settings import Settings

logger = logging.getLogger(__name__)

class KeywordExtractor:
    """Step1: キーワード抽出エンジン（CLIENTTOMO特化版）"""
    
    def __init__(self):
        self.settings = Settings()  # Settingsインスタンス生成
        self.gemini_available = self._init_gemini()
        self._init_clienttomo_dictionary()
        
    def _init_gemini(self) -> bool:
        """Gemini AI初期化"""
        if not ChatGoogleGenerativeAI or not self.settings.google_api_key:
            logger.warning("Gemini API利用不可 - ルールベース抽出にフォールバック")
            return False
            
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=self.settings.gemini_model,  # settings.iniから読み込み
                google_api_key=self.settings.google_api_key,
                temperature=self.settings.gemini_temperature  # settings.iniから読み込み
            )
            logger.info(f"Gemini AI初期化成功: {self.settings.gemini_model}")
            return True
        except Exception as e:
            logger.error(f"Gemini AI初期化失敗: {e}")
            return False
    
    def _init_clienttomo_dictionary(self):
        """CLIENTTOMO特化辞書初期化（精度向上）"""
        
        # CLIENTTOMO専用キーワード辞書
        self.clienttomo_keywords = {
            # 認証・ログイン関連
            "認証系": ["ログイン", "ログアウト", "認証", "パスワード", "セッション", "トークン", "OAuth"],
            "会員系": ["会員", "ユーザー", "アカウント", "プロフィール", "登録", "退会"],
            "企業系": ["クライアント企業", "法人", "組織", "管理者", "全体管理者"],
            
            # 機能系キーワード
            "UI系": ["画面", "フォーム", "ボタン", "モーダル", "ポップアップ", "メニュー", "ナビゲーション"],
            "データ系": ["データベース", "API", "JSON", "CSV", "エクスポート", "インポート"],
            "通知系": ["メール", "通知", "アラート", "リマインダー", "配信"],
            
            # 業務系キーワード
            "決済系": ["決済", "支払い", "課金", "料金", "プラン", "サブスクリプション"],
            "レポート系": ["レポート", "統計", "分析", "ダッシュボード", "グラフ", "集計"],
            "設定系": ["設定", "配置", "パラメータ", "環境", "デプロイ", "リリース"]
        }
        
        # 除外すべき汎用語（検索精度低下要因）
        self.excluded_terms = {
            "汎用動詞": ["教えて", "確認", "調べて", "見つけて", "探して", "検索して"],
            "汎用助詞": ["について", "に関する", "の件", "の内容", "の詳細"],
            "汎用名詞": ["情報", "データ", "内容", "詳細", "状況", "方法"],
            "質問表現": ["どうやって", "なぜ", "いつ", "どこで", "どれ", "何"]
        }
        
        # 複合語分解辞書
        self.compound_rules = {
            "ログイン機能": ["ログイン機能", "ログイン", "認証"],
            "会員登録": ["会員登録", "会員", "登録", "アカウント"],
            "クライアント企業": ["クライアント企業", "クライアント", "企業", "法人"],
            "全体管理者": ["全体管理者", "管理者", "アドミン"],
            "UI画面": ["UI画面", "UI", "画面", "インターフェース"],
            "API設計": ["API設計", "API", "設計", "インターフェース"],
            "データベース": ["データベース", "DB", "データ", "テーブル"]
        }
    
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
        """Gemini AIによるキーワード抽出（CLIENTTOMO特化版v2.0）"""
        
        # CLIENTTOMO特化プロンプト（精度向上版）
        prompt = f"""
あなたはCLIENTTOMOプロジェクト専用の上級キーワード抽出AIです。
88%の検索精度を92%+に向上させるため、CLIENTTOMO特化の高精度抽出を実行してください。

入力クエリ: "{user_query}"

## CLIENTTOMO専用抽出ルール（v2.0強化版）:

### 1. CLIENTTOMO専用複合語分解
以下の優先ルールで分解してください:
- 「ログイン機能」 → [ログイン機能, ログイン, 認証]
- 「会員登録」 → [会員登録, 会員, 登録, アカウント]
- 「クライアント企業」 → [クライアント企業, クライアント, 企業, 法人]
- 「全体管理者」 → [全体管理者, 管理者, アドミン]
- 「UI画面」 → [UI画面, UI, 画面, インターフェース]
- 「API設計」 → [API設計, API, 設計, インターフェース]

### 2. 高精度除外処理
以下は検索精度を下げるため厳格に除去:
- 汎用動詞: 教えて、確認、調べて、見つけて、探して、検索して
- 汎用助詞: について、に関する、の件、の内容、の詳細  
- 汎用名詞: 情報、データ、内容、詳細、状況、方法
- 質問表現: どうやって、なぜ、いつ、どこで、どれ、何

### 3. CLIENTTOMO業務ドメイン強化
以下のドメイン知識を活用してキーワード拡張:
- 認証系: ログイン、ログアウト、認証、パスワード、セッション、トークン
- 会員系: 会員、ユーザー、アカウント、プロフィール、登録、退会
- 企業系: クライアント企業、法人、組織、管理者、全体管理者
- UI系: 画面、フォーム、ボタン、モーダル、ポップアップ、メニュー
- データ系: データベース、API、JSON、CSV、エクスポート、インポート
- 決済系: 決済、支払い、課金、料金、プラン、サブスクリプション

### 4. 最適化された4キーワード選択
重要度順で最大4つ、以下の優先順位で選択:
1. 業務固有キーワード（最高優先度）
2. 機能特定キーワード
3. 技術キーワード
4. 補完キーワード

### 5. 検索意図高精度分析
以下の6カテゴリで分類:
- 機能照会: 特定機能の仕様・動作確認
- 手順確認: 実装・操作手順の確認
- 設計詳細: アーキテクチャ・技術詳細
- トラブル対応: バグ・不具合の調査
- 仕様変更: 変更・更新に関する情報
- 全般質問: 概要・一般的な質問

以下の形式でJSONを出力してください:
{{
    "primary_keywords": ["最重要キーワード1", "重要キーワード2", "補完キーワード3", "技術キーワード4"],
    "search_intent": "具体的な検索意図（6カテゴリから選択）",
    "extraction_method": "gemini_clienttomo_v2",
    "domain_category": "該当する業務ドメイン",
    "confidence_score": 0.95,
    "compound_words_detected": ["検出された複合語1", "検出された複合語2"],
    "removed_particles": ["除去された汎用語1", "除去された汎用語2"]
}}

重要: CLIENTTOMO業務ドメインの専門知識を最大限活用し、検索精度92%+を目指してください。
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
        """ルールベースキーワード抽出（CLIENTTOMO特化フォールバック）"""
        
        logger.info("CLIENTTOMO特化ルールベース抽出実行")
        
        # 前処理: 汎用語除去
        cleaned_query = self._remove_generic_terms(user_query)
        
        # CLIENTTOMO特化キーワード抽出
        primary_keywords = self._extract_clienttomo_keywords(cleaned_query)
        
        # 複合語分解処理
        expanded_keywords = self._expand_compound_words(primary_keywords, cleaned_query)
        
        # 最大4キーワード制限
        final_keywords = expanded_keywords[:4]
        
        # 検索意図分析
        search_intent = self._analyze_search_intent_rules(user_query)
        
        return {
            "primary_keywords": final_keywords,
            "secondary_keywords": [],
            "search_intent": search_intent,
            "extraction_method": "rule_based_clienttomo",
            "domain_category": self._categorize_domain(final_keywords),
            "confidence_score": 0.75,  # ルールベースの信頼度
            "compound_words_detected": self._detect_compounds(user_query),
            "removed_particles": self._get_removed_terms(user_query, cleaned_query)
        }
    
    def _remove_generic_terms(self, query: str) -> str:
        """汎用語の除去"""
        cleaned = query
        for category, terms in self.excluded_terms.items():
            for term in terms:
                cleaned = cleaned.replace(term, "")
        return cleaned.strip()
    
    def _extract_clienttomo_keywords(self, query: str) -> List[str]:
        """CLIENTTOMO特化キーワード抽出"""
        keywords = []
        
        # 各ドメインからキーワード検出
        for domain, domain_keywords in self.clienttomo_keywords.items():
            for keyword in domain_keywords:
                if keyword in query:
                    keywords.append(keyword)
        
        # 重複除去・重要度順ソート
        unique_keywords = list(dict.fromkeys(keywords))
        
        # CLIENTTOMO重要度順でソート
        priority_order = ["ログイン", "会員", "クライアント企業", "管理者", "API", "UI", "データベース"]
        sorted_keywords = []
        
        for priority_word in priority_order:
            for keyword in unique_keywords:
                if priority_word in keyword and keyword not in sorted_keywords:
                    sorted_keywords.append(keyword)
        
        # 残りのキーワード追加
        for keyword in unique_keywords:
            if keyword not in sorted_keywords:
                sorted_keywords.append(keyword)
        
        return sorted_keywords
    
    def _expand_compound_words(self, keywords: List[str], query: str) -> List[str]:
        """複合語分解による拡張"""
        expanded = keywords.copy()
        
        for compound, expansions in self.compound_rules.items():
            if compound in query:
                for expansion in expansions:
                    if expansion not in expanded:
                        expanded.append(expansion)
        
        return expanded
    
    def _analyze_search_intent_rules(self, query: str) -> str:
        """ルールベース検索意図分析"""
        intent_patterns = {
            "機能照会": ["機能", "動作", "仕様", "どう", "何"],
            "手順確認": ["手順", "方法", "やり方", "操作", "実装"],
            "設計詳細": ["設計", "アーキテクチャ", "構造", "API", "データベース"],
            "トラブル対応": ["エラー", "バグ", "不具合", "問題", "トラブル"],
            "仕様変更": ["変更", "更新", "修正", "改善", "リリース"],
            "全般質問": ["概要", "全体", "一般", "基本", "について"]
        }
        
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    return intent
        
        return "全般質問"
    
    def _categorize_domain(self, keywords: List[str]) -> str:
        """業務ドメイン分類"""
        domain_scores = {}
        
        for domain, domain_keywords in self.clienttomo_keywords.items():
            score = sum(1 for keyword in keywords if keyword in domain_keywords)
            if score > 0:
                domain_scores[domain] = score
        
        return max(domain_scores.items(), key=lambda x: x[1])[0] if domain_scores else "一般"
    
    def _detect_compounds(self, query: str) -> List[str]:
        """複合語検出"""
        detected = []
        for compound in self.compound_rules.keys():
            if compound in query:
                detected.append(compound)
        return detected
    
    def _get_removed_terms(self, original: str, cleaned: str) -> List[str]:
        """除去された語の取得"""
        removed = []
        for category, terms in self.excluded_terms.items():
            for term in terms:
                if term in original and term not in cleaned:
                    removed.append(term)
        return removed
        
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