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
from src.spec_bot_mvp.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

class KeywordExtractor:
    """Step1: キーワード抽出エンジン（CLIENTTOMO特化版）"""
    
    def __init__(self):
        self.settings = Settings()  # Settingsインスタンス生成
        self.gemini_available = self._init_gemini()
        self._init_clienttomo_dictionary()
        
    def _init_gemini(self) -> bool:
        """Gemini AI初期化"""
        # Gemini API設定チェック
        if not ChatGoogleGenerativeAI or not self.settings.gemini_api_key:
            raise ValueError("Gemini API設定またはライブラリが利用できません")
        
        # Gemini初期化
        self.llm = ChatGoogleGenerativeAI(
            api_key=self.settings.gemini_api_key,
            model=self.settings.gemini_model,  # settings.iniから読み込み
            temperature=self.settings.gemini_temperature  # settings.iniから読み込み
        )
        logger.info(f"Gemini AI初期化成功: {self.settings.gemini_model}")
        return True
    
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
            "ログイン機能": ["ログイン機能", "ログイン"],  # 認証を除去
            "会員登録": ["会員登録", "会員", "登録"],  # アカウントを除去
            "クライアント企業": ["クライアント企業", "クライアント", "企業"],  # 法人を除去
            "全体管理者": ["全体管理者", "管理者"],  # アドミンを除去
            "UI画面": ["UI画面", "UI", "画面"],  # インターフェースを除去
            "API設計": ["API設計", "API", "設計"],  # インターフェースを除去
            "データベース": ["データベース", "DB"],  # データ、テーブルを除去
            # 新しい保守的ルール
            "パスワード機能": ["パスワード機能", "パスワード"],
            "認証機能": ["認証機能", "認証"],
            "セッション管理": ["セッション管理", "セッション"]
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
        """Gemini AIによるキーワード抽出（保守的抽出版v3.0）"""
        
        # 保守的抽出プロンプト（外部化済み）
        prompt = load_prompt(
            "analysis_steps",
            "step1_keyword_extraction", 
            "gemini_conservative_extraction",
            user_query=user_query
        )
        
        logger.info(f"Gemini抽出実行: {user_query}")
        
        response = self.llm.invoke(prompt)
        
        # JSON解析
        import json
        try:
            # レスポンスからJSONを抽出
            json_start = response.content.find('{')
            json_end = response.content.rfind('}') + 1
            json_str = response.content[json_start:json_end]
            
            logger.debug(f"Gemini応答JSON: {json_str}")
            
            result = json.loads(json_str)
            
            # 保守的抽出のため、3キーワード上限
            if len(result.get("keywords", [])) > 3:
                result["keywords"] = result["keywords"][:3]
            
            # 仕様書準拠の戻り値形式に調整
            formatted_result = {
                "primary_keywords": result.get("keywords", []),
                "secondary_keywords": [],  # 仕様書では主要キーワードのみ
                "search_intent": self._infer_intent(user_query),
                "extraction_method": result.get("extraction_method", "gemini_conservative_v3"),
                "confidence_score": result.get("confidence", 0.85),
                "reasoning": result.get("reasoning", ""),
                "user_query": user_query,  # ★ 追加: ユーザークエリを結果に含める
                "original_query": user_query  # ★ 追加: 互換性のため
            }
            
            logger.info(f"Gemini保守的抽出成功: {formatted_result['primary_keywords']} (元クエリ: {user_query})")
            return formatted_result
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Gemini応答JSON解析失敗: {e}")
            logger.error(f"レスポンス内容: {response.content}")
            raise
    
    def _extract_with_rules(self, user_query: str) -> Dict[str, Any]:
        """ルールベースキーワード抽出（保守的フォールバック）"""
        
        logger.info(f"保守的ルールベース抽出実行: {user_query}")
        
        # 前処理: 汎用語除去
        cleaned_query = self._remove_generic_terms(user_query)
        
        # 直接抽出（最優先）
        direct_keywords = self._extract_direct_keywords(cleaned_query)
        
        # 複合語分解処理（保守的）
        expanded_keywords = self._expand_compound_words_conservative(direct_keywords, cleaned_query)
        
        # 最大3キーワード制限（保守的）
        final_keywords = expanded_keywords[:3]
        
        # 検索意図分析
        search_intent = self._analyze_search_intent_rules(user_query)
        
        result = {
            "primary_keywords": final_keywords,
            "secondary_keywords": [],
            "search_intent": search_intent,
            "extraction_method": "rule_based_conservative",
            "domain_category": self._categorize_domain(final_keywords),
            "confidence_score": 0.80,  # 保守的ルールベースの信頼度
            "compound_words_detected": self._detect_compounds(user_query),
            "removed_particles": self._get_removed_terms(user_query, cleaned_query),
            "conservative_note": "入力に忠実な保守的抽出を実行",
            "user_query": user_query,  # ★ 追加: ユーザークエリを結果に含める
            "original_query": user_query  # ★ 追加: 互換性のため
        }
        
        logger.info(f"ルールベース抽出成功: {result['primary_keywords']} (元クエリ: {user_query})")
        return result
    
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
    
    def _extract_direct_keywords(self, query: str) -> List[str]:
        """直接キーワード抽出（入力文字列に忠実）"""
        keywords = []
        
        # 重要な複合語を最優先で検出
        for compound in self.compound_rules.keys():
            if compound in query:
                keywords.append(compound)
        
        # 単一キーワード検出（複合語と重複しない場合のみ）
        for domain, domain_keywords in self.clienttomo_keywords.items():
            for keyword in domain_keywords:
                if keyword in query and not any(keyword in comp for comp in keywords):
                    keywords.append(keyword)
        
        return keywords
    
    def _expand_compound_words_conservative(self, keywords: List[str], query: str) -> List[str]:
        """保守的複合語分解"""
        expanded = []
        
        # 入力にある複合語のみ分解
        for keyword in keywords:
            if keyword in self.compound_rules:
                # 分解結果の最初の2つのみ追加（保守的）
                expansions = self.compound_rules[keyword][:2]
                for expansion in expansions:
                    if expansion not in expanded:
                        expanded.append(expansion)
            else:
                if keyword not in expanded:
                    expanded.append(keyword)
        
        return expanded
    
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