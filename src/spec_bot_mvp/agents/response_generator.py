"""
回答生成Agent

仕様書定義 (SPEC-DS-001 4.1):
- 役割: 検索結果を統合・要約して最終回答を生成
- タイプ: LLMChain（外部ツール無し）
- 入力: 検索結果 + ユーザー質問
- 出力: 統合された最終回答
"""

import logging
from typing import Dict, List, Any
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from langchain.prompts import PromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.runnables import RunnableSequence
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from src.spec_bot_mvp.config.settings import Settings

logger = logging.getLogger(__name__)

class ResponseGenerationAgent:
    """
    回答生成Agent
    
    検索結果を統合・要約して、ユーザーに分かりやすい最終回答を生成する。
    外部ツールを使用せず、LLMChainによる純粋な文章生成に特化。
    """
    
    def __init__(self):
        """Agent初期化"""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError("LangChain関連パッケージが必要です: pip install langchain langchain-google-genai")
        
        self.settings = Settings()
        self._init_llm_chain()
        logger.info("✅ ResponseGenerationAgent初期化完了")
    
    def _init_llm_chain(self):
        """LLMChain初期化"""
        # Gemini LLM設定（settings.ini準拠）
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=self.settings.gemini_model,  # settings.iniから読み込み
                google_api_key=self.settings.google_api_key,
                temperature=self.settings.gemini_temperature,  # settings.iniから読み込み
                max_output_tokens=self.settings.gemini_max_tokens  # settings.iniから読み込み
            )
            logger.info(f"✅ Gemini LLM初期化成功: {self.settings.gemini_model}")
        except Exception as e:
            logger.error(f"❌ Gemini LLM初期化失敗: {e}")
            raise
        
        # プロンプトテンプレート
        self.prompt = PromptTemplate(
            input_variables=["search_results", "user_query"],
            template=self._get_response_prompt_template()
        )
        
        # RunnableSequence構築 (最新LangChain API)
        self.chain = self.prompt | self.llm
    
    def _get_response_prompt_template(self) -> str:
        """CLIENTTOMO仕様書特化 回答生成プロンプト（v2.1 - ドメイン知識強化版）"""
        return """あなたはCLIENTTOMOプロジェクト専用の上級仕様書作成支援AIアシスタントです。
開発者・PM・CSチームが、複雑な機能仕様を素早く理解し、実装やサポートに活用できる実用的な回答を生成してください。

【CLIENTTOMOプロジェクト詳細情報】
■ プロジェクト概要: 企業向けクライアント管理システム
■ 対象ユーザー: 
  - 会員（一般ユーザー）
  - クライアント企業（法人ユーザー）  
  - 全体管理者（システム管理者）
■ 主要機能領域:
  - ログイン・認証システム（多層認証、3ユーザータイプ対応）
  - UI/UX（レスポンシブ、モーダル、動的挙動）
  - データベース設計（ユーザー管理、権限制御）
  - API設計（RESTful、認証、レート制限）
  - 業務フロー（PM・CS・マーケティング連携）
■ 技術スタック:
  - UI: Streamlit（Python）
  - AI: LangChain + Gemini 2.0-flash
  - 検索: 3段階CQL検索戦略
  - インフラ: Confluence (CLIENTTOMOスペース), Jira
  - キャッシュ: SQLite（性能向上）

【ユーザー質問】
{user_query}

【検索結果（80%関連度達成の3段階CQL検索結果）】
{search_results}

【CLIENTTOMO専用回答生成ガイドライン（v2.1強化版）】
1. **機能理解重視**: 「なぜその仕様になったのか」プロジェクト背景・意図を説明
2. **実装指向**: 開発者が即座にコーディングに着手できる具体性（API仕様、データ構造等）
3. **業務連携**: PM・CS・マーケティングとの連携ポイントを明示
4. **動的仕様**: UI挙動・モーダル・フロー等の動的な仕様を重視
5. **関連性可視化**: 他機能・画面・データとの関連性を明確化
6. **品質基準**: CLIENTTOMOの品質基準・セキュリティ要件準拠
7. **ユーザータイプ考慮**: 会員・クライアント企業・管理者別の仕様差異を明記
8. **技術的実装**: 選定技術スタック（Streamlit, LangChain, Gemini等）に準拠した実装方針

【回答品質向上指針】
■ 具体性: 抽象的表現を避け、実装可能な具体的仕様を記載
■ 完全性: 関連する周辺機能・依存関係・制約条件を漏れなく説明
■ 実用性: チーム（開発・PM・CS）が実際の業務で即活用できる情報提供
■ 一貫性: CLIENTTOMOプロジェクトの命名規則・設計方針に準拠

【専用回答フォーマット（v2.1拡張版）】
## 🎯 機能概要
[該当機能の目的・役割・CLIENTTOMOにおけるユーザー価値を簡潔に説明]

## 👥 ユーザータイプ別仕様
[会員・クライアント企業・管理者それぞれの利用方法・権限・画面差異]

## 🔧 実装仕様
[開発者向け技術詳細：API仕様、データ構造、画面遷移、バリデーション、選定技術活用方法]

## 💼 業務フロー
[PM・CS向け業務観点：ユーザー操作手順、エラーケース、サポート時の注意点]

## 🔗 関連機能・依存関係
[この機能に関連する他のCLIENTTOMO機能・画面・データベースとの連携ポイント]

## ⚠️ 注意事項・制約
[実装時の制約、既知の課題、将来の改善予定、セキュリティ考慮事項、パフォーマンス要件]

## 📚 参考文献・情報源
[以下の形式で、回答の根拠となった具体的なページを明記:]
📄 **[ページタイトル]**
🔗 [完全なURL]

[検索結果から得られた各ページについて、上記形式で列挙]

## 🎯 さらなる深掘り・関連情報
[ユーザーが次に知りたそうなCLIENTTOMO関連キーワード・質問を提案:]
- 「[関連機能1]について詳しく知りたい」
- 「[関連技術2]の実装方法を確認したい」  
- 「[ユーザータイプ3]向けの仕様を見たい」

---
**信頼度**: [高/中/低] - [80%関連度CQL検索結果の品質と関連性に基づく判断理由]

回答:"""

    def generate_response(self, search_results: List[Dict], user_query: str, memory_context: str = "") -> str:
        """
        検索結果を統合して最終回答を生成
        
        Args:
            search_results: 検索結果リスト
            user_query: ユーザー質問
            memory_context: 前回の検索コンテキスト情報
            
        Returns:
            統合された最終回答
        """
        try:
            # 検索結果を構造化文字列に変換
            formatted_results = self._format_search_results(search_results)
            
            # メモリーコンテキストがある場合は質問を拡張
            enhanced_query = user_query
            if memory_context:
                enhanced_query = f"{user_query}\n\n【前回のコンテキスト】{memory_context}"
            
            logger.info("💡 回答生成開始: クエリ='%s', 結果数=%d, メモリー=%s", user_query, len(search_results), bool(memory_context))
            
            # RunnableSequenceで回答生成 (最新LangChain API)
            result = self.chain.invoke({
                "search_results": formatted_results,
                "user_query": enhanced_query
            })
            
            # AIMessageから文字列コンテンツを抽出
            response = result.content if hasattr(result, 'content') else str(result)
            
            # 参照元情報と深掘り提案を追加
            enhanced_response = self._enhance_response_with_sources(response, search_results, user_query)
            
            logger.info("✅ 回答生成完了: 文字数=%d", len(enhanced_response))
            return enhanced_response
            
        except Exception as e:
            logger.error("❌ 回答生成失敗: %s", str(e))
            return self._generate_error_response(user_query, str(e))
    
    def _enhance_response_with_sources(self, response: str, search_results: List[Dict], user_query: str) -> str:
        """
        回答に参照元情報と深掘り提案を追加
        
        Args:
            response: 生成された回答
            search_results: 検索結果リスト
            user_query: ユーザー質問
            
        Returns:
            拡張された回答
        """
        # 参照元情報を生成
        sources_section = self._generate_sources_section(search_results)
        
        # 深掘り提案を生成
        followup_section = self._generate_followup_suggestions(search_results, user_query)
        
        # 回答に追加
        if sources_section:
            response += f"\n\n{sources_section}"
        
        if followup_section:
            response += f"\n\n{followup_section}"
            
        return response
    
    def _generate_sources_section(self, search_results: List[Dict]) -> str:
        """
        参照元情報セクションを生成
        
        Args:
            search_results: 検索結果リスト
            
        Returns:
            参照元情報のマークダウン文字列
        """
        if not search_results:
            return ""
        
        sources_lines = ["## 📚 参考文献・情報源"]
        
        for i, result in enumerate(search_results, 1):
            title = result.get('title', f'文書 {i}')
            url = result.get('url', result.get('link', ''))
            source = result.get('source', 'Unknown')
            
            if url:
                sources_lines.append(f"📄 **{title}**")
                sources_lines.append(f"🔗 {url}")
                sources_lines.append("")  # 空行
            else:
                # URLがない場合はソース情報のみ
                sources_lines.append(f"📄 **{title}** ({source})")
                sources_lines.append("")
        
        return "\n".join(sources_lines)
    
    def _generate_followup_suggestions(self, search_results: List[Dict], user_query: str) -> str:
        """
        さらなる深掘り提案セクションを生成
        
        Args:
            search_results: 検索結果リスト  
            user_query: ユーザー質問
            
        Returns:
            深掘り提案のマークダウン文字列
        """
        # ユーザー質問から関連キーワードを抽出
        query_keywords = self._extract_query_keywords(user_query)
        
        # 検索結果から関連キーワードを抽出
        result_keywords = self._extract_result_keywords(search_results)
        
        # 関連提案を生成
        suggestions = []
        
        # 基本的な深掘り提案
        if "ログイン" in user_query:
            suggestions.extend([
                "ログイン機能の会員機能について知りたい",
                "ログイン認証のセキュリティ仕様を確認したい",
                "ログイン後の画面遷移フローを見たい"
            ])
        elif "API" in user_query:
            suggestions.extend([
                "API認証方式の詳細仕様について知りたい",
                "APIエラーハンドリングの実装方法を確認したい",
                "API利用制限・レート制限について確認したい"
            ])
        elif "UI" in user_query or "画面" in user_query:
            suggestions.extend([
                "UI設計ガイドラインについて知りたい",
                "画面遷移の全体フローを確認したい",
                "レスポンシブ対応の実装仕様を見たい"
            ])
        else:
            # 汎用的な提案
            suggestions.extend([
                f"{query_keywords[0] if query_keywords else '関連機能'}の技術仕様を詳しく知りたい",
                f"{query_keywords[0] if query_keywords else '該当機能'}の運用手順を確認したい",
                f"{query_keywords[0] if query_keywords else '関連システム'}との連携方法を見たい"
            ])
        
        if not suggestions:
            return ""
        
        lines = ["## 🎯 さらなる深掘り・関連情報"]
        for suggestion in suggestions[:3]:  # 最大3つに制限
            lines.append(f'- 「{suggestion}」')
        
        return "\n".join(lines)
    
    def _extract_query_keywords(self, user_query: str) -> List[str]:
        """ユーザー質問からキーワードを抽出"""
        keywords = []
        common_keywords = ["ログイン", "認証", "API", "UI", "画面", "機能", "仕様", "設計", "実装"]
        
        for keyword in common_keywords:
            if keyword in user_query:
                keywords.append(keyword)
        
        return keywords
    
    def _extract_result_keywords(self, search_results: List[Dict]) -> List[str]:
        """検索結果からキーワードを抽出"""
        keywords = set()
        
        for result in search_results:
            title = result.get('title', '')
            content = result.get('content', '')
            
            # タイトルと内容から簡単なキーワード抽出
            text = f"{title} {content}".lower()
            common_terms = ["認証", "セキュリティ", "データベース", "フロント", "バック", "テスト"]
            
            for term in common_terms:
                if term in text:
                    keywords.add(term)
        
        return list(keywords)
    
    def _format_search_results(self, search_results: List[Dict]) -> str:
        """
        検索結果を読みやすい形式にフォーマット
        
        Args:
            search_results: 検索結果リスト
            
        Returns:
            フォーマットされた結果文字列
        """
        if not search_results:
            return "検索結果が見つかりませんでした。"
        
        formatted_sections = []
        
        for i, result in enumerate(search_results, 1):
            source = result.get('source', 'Unknown')
            title = result.get('title', 'タイトルなし')
            content = result.get('content', result.get('summary', ''))
            url = result.get('url', '')
            relevance_score = result.get('relevance_score', 0)
            
            section = f"""
=== 検索結果 {i} ===
ソース: {source}
タイトル: {title}
関連度: {relevance_score:.2f}
URL: {url}
内容:
{content}
"""
            formatted_sections.append(section)
        
        return "\n".join(formatted_sections)
    
    def _generate_error_response(self, user_query: str, error_message: str) -> str:
        """
        エラー時のフォールバック応答生成
        
        Args:
            user_query: ユーザー質問
            error_message: エラーメッセージ
            
        Returns:
            エラー応答文字列
        """
        return f"""申し訳ございません。回答生成中にエラーが発生しました。

## ❌ エラー詳細
**質問**: {user_query}
**エラー**: {error_message}

## 🔧 対処方法
1. **再試行**: しばらく時間をおいてから再度お試しください
2. **質問の見直し**: より具体的なキーワードで質問を言い換えてみてください
3. **フィルター調整**: 検索フィルターを変更して対象範囲を広げてみてください

## 💬 サポート
問題が継続する場合は、システム管理者にお問い合わせください。
エラー情報を含めてご連絡いただけると、より迅速な対応が可能です。"""

    def validate_llm_connection(self) -> bool:
        """
        LLM接続の検証
        
        Returns:
            接続成功時True、失敗時False
        """
        try:
            test_response = self.llm.invoke("テスト")
            logger.info("✅ LLM接続検証成功")
            return True
        except Exception as e:
            logger.error("❌ LLM接続検証失敗: %s", str(e))
            return False 