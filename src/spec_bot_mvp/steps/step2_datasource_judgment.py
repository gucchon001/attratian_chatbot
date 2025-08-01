"""
Step2: データソース判定機能（仕様書準拠）

キーワードと検索意図に基づいてJira/Confluenceの最適な選択を行う
- 仕様書準拠の判定専用キーワード
- 重み付きマッチ計算（確信度30%以上で選択）
- Geminiによる検索用キーワード最適化
- 判定後キーワード除去処理
"""

import logging
from typing import Dict, List, Any, Tuple
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

class DataSourceJudge:
    """Step2: データソース判定エンジン（仕様書準拠）"""
    
    def __init__(self):
        self.settings = Settings()  # Settingsインスタンス生成
        self.gemini_available = self._init_gemini()
        self._init_judgment_rules()
    
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
        logger.info(f"Gemini AI初期化成功（Step2）: {self.settings.gemini_model}")
        return True
    
    def _init_judgment_rules(self):
        """判定ルールの初期化（仕様書準拠）"""
        
        # 仕様書準拠の判定専用キーワード（重み付き）
        self.judgment_keywords = {
            # Confluence判定語（仕様書2.2.2）
            "confluence": {
                "仕様": 0.9, "詳細": 0.8, "設計書": 0.9, "API": 0.8, "要件": 0.8,
                "実装": 0.7, "フロー": 0.7, "画面": 0.6, "UI": 0.6, "UX": 0.6,
                "インターフェース": 0.7, "データベース": 0.7, "システム設計": 0.8, "機能仕様": 0.9,
                "機能": 0.5, "機能詳細": 0.85, "機能の詳細": 0.85
            },
            
            # Jira判定語（仕様書2.2.2）
            "jira": {
                "チケット": 0.9, "進捗": 0.8, "バグ": 0.9, "不具合": 0.9, "仕様変更": 0.7,
                "タスク": 0.8, "issue": 0.9, "対応状況": 0.8, "修正": 0.7, "改修": 0.7,
                "エラー": 0.8, "問題": 0.7, "課題": 0.7, "開発進捗": 0.8
            },
            
            # 議事録判定語（仕様書2.2.2）  
            "confluence_meeting": {
                "議事録": 0.9, "過去の経緯": 0.8, "会議": 0.8, "打ち合わせ": 0.8,
                "決定事項": 0.8, "合意": 0.7, "履歴": 0.7, "変更履歴": 0.8,
                "議論": 0.7, "MTG": 0.8, "相談": 0.6, "検討": 0.6
            }
        }
        
        # 除去対象キーワード（仕様書2.2.3）
        self.removal_keywords = {
            "判定専用語": ["仕様", "詳細", "機能", "チケット", "進捗", "議事録"],
            "動詞": ["教えて", "説明して", "整理して", "抽出して", "確認して", "見つけて"]
        }
    
    def judge_datasource(self, keyword_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        ハイブリッド型データソース判定を実行（ルールベース + Gemini）
        
        Args:
            keyword_result: Step1のキーワード抽出結果
            
        Returns:
            判定結果辞書（仕様書準拠）
        """
        logger.info(f"ハイブリッド型データソース判定開始: {keyword_result.get('search_intent', 'unknown')}")
        
        # Step1結果の抽出
        primary_keywords = keyword_result.get("primary_keywords", [])
        search_intent = keyword_result.get("search_intent", "一般検索")
        
        # Phase 1: 高速ルールベース判定
        rule_based_result = self._calculate_weighted_match(primary_keywords)
        rule_confidence = max(rule_based_result.values())
        
        logger.info(f"ルールベース判定: Confluence={rule_based_result['confluence']:.2f}, Jira={rule_based_result['jira']:.2f}, 最高信頼度={rule_confidence:.2f}")
        
        # Phase 2: 信頼度チェックとGemini判定
        if rule_confidence >= 0.8:
            # 高信頼度：ルールベース結果を採用（高速）
            datasource_scores = rule_based_result
            judgment_method = "rule_based_high_confidence"
            logger.info(f"✅ 高信頼度ルールベース判定採用: {judgment_method}")
        else:
            # 低信頼度：Gemini文脈理解判定
            gemini_result = self._gemini_datasource_judgment(primary_keywords, search_intent)
            if gemini_result:
                datasource_scores = self._integrate_judgments(rule_based_result, gemini_result)
                judgment_method = "hybrid_gemini_enhanced"
                logger.info(f"🤖 Gemini強化判定採用: {judgment_method}")
            else:
                # Gemini失敗時：ルールベースフォールバック
                datasource_scores = rule_based_result
                judgment_method = "rule_based_fallback"
                logger.warning(f"⚠️ Gemini判定失敗、ルールベース採用: {judgment_method}")
        
        # 3. 閾値判定（動的調整）
        keywords_str = " ".join(primary_keywords).lower()
        if any(pattern in keywords_str for pattern in ["機能.*詳細", "機能.*仕様", ".*仕様.*詳細"]):
            threshold = 0.7  # 複合キーワードは厳格
        elif any(keyword in keywords_str for keyword in ["機能", "詳細", "仕様"]):
            threshold = 0.5  # 単体キーワードは中程度
        else:
            threshold = 0.4  # 一般クエリ
        selected_datasources = self._apply_threshold_selection(datasource_scores, threshold=threshold)
        
        # 4. Geminiによる検索用キーワード最適化（仕様書2.2.3）
        optimized_keywords = self._optimize_keywords_with_gemini(primary_keywords, selected_datasources)
        
        # 5. データソース優先順序決定（選択されたデータソースのみ）
        datasource_priority = sorted(selected_datasources, key=lambda x: datasource_scores[x], reverse=True)
        
        # 6. 判定理由生成
        reasoning = self._generate_reasoning_spec_compliant(
            primary_keywords, datasource_scores, selected_datasources, search_intent
        )
        
        result = {
            "datasource_priority": datasource_priority,
            "priority_scores": datasource_scores,
            "selected_datasources": selected_datasources,
            "judgment_reasoning": reasoning,
            "judgment_method": judgment_method,  # 判定手法を追加
            "optimized_keywords": optimized_keywords,
            "original_keywords": primary_keywords,
            "keywords_removed": self._get_removed_keywords(primary_keywords, optimized_keywords)
        }
        
        logger.info(f"ハイブリッド判定完了 [{judgment_method}]: {selected_datasources} (最高スコア: {max(datasource_scores.values()):.2f})")
        return result
    
    def _calculate_weighted_match(self, keywords: List[str]) -> Dict[str, float]:
        """重み付きマッチ計算（仕様書2.2.2）"""
        scores = {"confluence": 0.0, "jira": 0.0}
        
        # 複合キーワード判定（優先）
        keywords_str = " ".join(keywords).lower()
        
        # 高確信度パターン（Confluence強め）
        high_confidence_confluence_patterns = [
            ("機能.*詳細", 0.9), ("機能.*仕様", 0.9), (".*詳細.*仕様", 0.85),
            ("[ァ-ヶー一-龯]+.*機能.*詳細", 0.95), ("api.*仕様", 0.9), ("設計.*詳細", 0.9)
        ]
        
        # 高確信度パターン（Jira強め）
        high_confidence_jira_patterns = [
            ("チケット.*進捗", 0.9), ("バグ.*修正", 0.95), ("不具合.*対応", 0.9),
            ("issue.*status", 0.9), ("タスク.*進捗", 0.85)
        ]
        
        import re
        
        # パターンマッチング
        for pattern, weight in high_confidence_confluence_patterns:
            if re.search(pattern, keywords_str):
                scores["confluence"] += weight
                logger.debug(f"Confluence複合パターンマッチ: '{pattern}' (重み: {weight})")
        
        for pattern, weight in high_confidence_jira_patterns:
            if re.search(pattern, keywords_str):
                scores["jira"] += weight
                logger.debug(f"Jira複合パターンマッチ: '{pattern}' (重み: {weight})")
        
        # 個別キーワード判定（従来通り）
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Confluence判定語マッチ
            for conf_word, weight in self.judgment_keywords["confluence"].items():
                if conf_word in keyword_lower:
                    scores["confluence"] += weight
                    logger.debug(f"Confluence判定語マッチ: '{keyword}' -> '{conf_word}' (重み: {weight})")
            
            # 議事録判定語もConfluenceに加算
            for meeting_word, weight in self.judgment_keywords["confluence_meeting"].items():
                if meeting_word in keyword_lower:
                    scores["confluence"] += weight
                    logger.debug(f"議事録判定語マッチ: '{keyword}' -> '{meeting_word}' (重み: {weight})")
            
            # Jira判定語マッチ
            for jira_word, weight in self.judgment_keywords["jira"].items():
                if jira_word in keyword_lower:
                    scores["jira"] += weight
                    logger.debug(f"Jira判定語マッチ: '{keyword}' -> '{jira_word}' (重み: {weight})")
        
        # 正規化（0-1の範囲）
        total_score = sum(scores.values())
        if total_score > 0:
            scores = {k: v / total_score for k, v in scores.items()}
        else:
            # 機能系クエリの場合はConfluence優先デフォルト
            has_function_keywords = any(keyword in str(keywords).lower() for keyword in ["機能", "詳細", "仕様"])
            if has_function_keywords:
                scores = {"confluence": 0.85, "jira": 0.15}  # 機能系デフォルト
            else:
                scores = {"confluence": 0.6, "jira": 0.4}  # 一般デフォルト
        
        return scores
    
    def _apply_threshold_selection(self, scores: Dict[str, float], threshold: float = 0.3) -> List[str]:
        """閾値判定（確信度30%以上で選択）"""
        selected = [datasource for datasource, score in scores.items() if score >= threshold]
        
        # 最低1つは選択必須
        if not selected:
            selected = [max(scores.keys(), key=lambda k: scores[k])]
        
        return selected
    
    def _optimize_keywords_with_gemini(self, keywords: List[str], selected_datasources: List[str]) -> List[str]:
        """Geminiによる検索用キーワード最適化（仕様書2.2.3）"""
        if not self.gemini_available:
            # Gemini利用不可時はルールベース除去
            return self._rule_based_keyword_optimization(keywords)
        
        try:
            prompt = load_prompt(
                "analysis_steps",
                "step2_datasource_judgment", 
                "keyword_optimization",
                keywords=keywords,
                selected_datasources=selected_datasources
            )
            
            response = self.llm.invoke(prompt)
            
            # JSON解析
            import json
            json_start = response.content.find('{')
            json_end = response.content.rfind('}') + 1
            json_str = response.content[json_start:json_end]
            
            result = json.loads(json_str)
            optimized = result.get("optimized_keywords", keywords)
            
            logger.info(f"Geminiキーワード最適化完了: {keywords} -> {optimized}")
            return optimized
            
        except Exception as e:
            logger.warning(f"Geminiキーワード最適化失敗、ルールベースに切替: {e}")
            return self._rule_based_keyword_optimization(keywords)
    
    def _rule_based_keyword_optimization(self, keywords: List[str]) -> List[str]:
        """ルールベースキーワード最適化（Geminiフォールバック）"""
        optimized = []
        
        for keyword in keywords:
            should_remove = False
            keyword_lower = keyword.lower()
            
            # 判定専用語の除去
            for removal_word in self.removal_keywords["判定専用語"]:
                if removal_word in keyword_lower and keyword_lower == removal_word:
                    should_remove = True
                    break
            
            # 動詞の除去
            for removal_word in self.removal_keywords["動詞"]:
                if removal_word in keyword_lower:
                    should_remove = True
                    break
            
            if not should_remove:
                optimized.append(keyword)
        
        # 最低1つは保持
        if not optimized and keywords:
            optimized = [keywords[0]]
        
        logger.info(f"ルールベースキーワード最適化完了: {keywords} -> {optimized}")
        return optimized
    
    def _get_removed_keywords(self, original: List[str], optimized: List[str]) -> List[str]:
        """除去されたキーワードの特定"""
        return [kw for kw in original if kw not in optimized]
    
    def _generate_reasoning_spec_compliant(self, keywords: List[str], scores: Dict[str, float], 
                                         selected: List[str], intent: str) -> str:
        """判定理由生成（仕様書準拠）"""
        reasoning_parts = []
        
        # キーワード分析
        reasoning_parts.append(f"入力キーワード: {', '.join(keywords)}")
        
        # 重み付きマッチ結果
        for datasource, score in scores.items():
            reasoning_parts.append(f"{datasource.title()}確信度: {score:.2f}")
        
        # 選択結果
        reasoning_parts.append(f"選択データソース: {', '.join(selected)}")
        
        # 検索意図
        reasoning_parts.append(f"検索意図: {intent}")
        
        return " | ".join(reasoning_parts)
    
    def _gemini_datasource_judgment(self, keywords: List[str], search_intent: str) -> Dict[str, float]:
        """
        Geminiによるデータソース判定（既存プロンプト活用）
        
        Args:
            keywords: 抽出されたキーワード
            search_intent: 検索意図
            
        Returns:
            Gemini判定スコア辞書 or None（失敗時）
        """
        if not self.gemini_available:
            logger.warning("Gemini利用不可、Gemini判定をスキップ")
            return None
        
        try:
            # 既存プロンプトの活用
            prompt = load_prompt(
                "analysis_steps",
                "step2_datasource_judgment", 
                "datasource_confidence_judgment",
                keywords=keywords,
                search_intent=search_intent
            )
            
            logger.info(f"🤖 Gemini文脈判定実行: キーワード={keywords}, 意図={search_intent}")
            response = self.llm.invoke(prompt)
            
            # JSON解析
            import json
            json_start = response.content.find('{')
            json_end = response.content.rfind('}') + 1
            json_str = response.content[json_start:json_end]
            
            result = json.loads(json_str)
            
            # 結果の抽出と検証
            confluence_conf = float(result.get("confluence_confidence", 0.5))
            jira_conf = float(result.get("jira_confidence", 0.5))
            reasoning = result.get("reasoning", "Gemini判定")
            
            # 正規化
            total = confluence_conf + jira_conf
            if total > 0:
                confluence_conf = confluence_conf / total
                jira_conf = jira_conf / total
            
            gemini_scores = {
                "confluence": confluence_conf,
                "jira": jira_conf
            }
            
            logger.info(f"✅ Gemini判定完了: Confluence={confluence_conf:.2f}, Jira={jira_conf:.2f}")
            logger.info(f"📝 Gemini判定理由: {reasoning}")
            
            return gemini_scores
            
        except Exception as e:
            logger.error(f"❌ Gemini判定エラー: {e}")
            return None
    
    def _integrate_judgments(self, rule_scores: Dict[str, float], gemini_scores: Dict[str, float]) -> Dict[str, float]:
        """
        ルールベースとGemini判定の統合
        
        Args:
            rule_scores: ルールベース判定スコア
            gemini_scores: Gemini判定スコア
            
        Returns:
            統合判定スコア
        """
        # 重み付き統合（Gemini優先だが、ルールベースも考慮）
        rule_weight = 0.3  # ルールベース重み
        gemini_weight = 0.7  # Gemini重み
        
        integrated_scores = {}
        for datasource in ["confluence", "jira"]:
            integrated_score = (
                rule_scores[datasource] * rule_weight + 
                gemini_scores[datasource] * gemini_weight
            )
            integrated_scores[datasource] = integrated_score
        
        logger.info(f"🔗 判定統合完了: ルール重み={rule_weight}, Gemini重み={gemini_weight}")
        logger.info(f"📊 統合結果: Confluence={integrated_scores['confluence']:.2f}, Jira={integrated_scores['jira']:.2f}")
        
        return integrated_scores 