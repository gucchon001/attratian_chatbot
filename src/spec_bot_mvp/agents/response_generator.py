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

from ..config.settings import Settings

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
                api_key=self.settings.gemini_api_key,
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
        """CLIENTTOMO仕様書特化 回答生成プロンプト（v2.2 - 適応的詳細レベル版）"""
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

【回答詳細レベル判定】
以下の条件に基づいて、適切な詳細レベルを選択してください：

■ 簡潔版（基本回答）を選択する場合：
- 一般的な機能説明要求（「〜とは？」「〜について教えて」）
- 概要理解目的の質問
- 初心者向けの説明要求

■ 詳細版（包括的回答）を選択する場合：
- 実装詳細要求（「実装方法」「技術仕様」「API詳細」）
- 複数観点の統合説明要求
- PM・CS向けの業務フロー詳細要求

【簡潔版回答フォーマット】
## 🎯 機能概要
[該当機能の目的・役割・主要な特徴を200文字程度で簡潔に説明]

## 📋 主要仕様
[実装・運用に必要な重要仕様を要点のみ箇条書きで記載]
- 認証方法: [簡潔に]
- 入力制限: [主要なもののみ]
- 画面遷移: [基本フローのみ]

## 💡 重要なポイント
[開発・運用で特に注意すべき要点を3-4項目で]
- [セキュリティ上の注意点]
- [実装時の制約]
- [運用時の考慮事項]

---

【詳細版回答フォーマット】
## 🎯 機能概要
[該当機能の目的・役割・CLIENTTOMOにおけるユーザー価値を説明]

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

---

【重要指針】
1. **適応性**: 質問の複雑さと詳細要求レベルに応じてフォーマットを選択
2. **簡潔性**: 不要な情報は削除し、核心に集中
3. **実用性**: チームが即座に活用できる情報に焦点
4. **品質維持**: 簡潔版でも正確性と完全性は保持

回答:"""

    def generate_response(self, search_results: List[Dict], user_query: str, memory_context: str = "") -> str:
        """
        検索結果を統合して最終回答を生成（全文取得対応）
        
        Args:
            search_results: 検索結果リスト
            user_query: ユーザー質問
            memory_context: 前回の検索コンテキスト情報
            
        Returns:
            統合された最終回答
        """
        try:
            logger.info("💡 回答生成開始: クエリ='%s', 結果数=%d, メモリー=%s", user_query, len(search_results), bool(memory_context))
            
            # Step 1: 検索結果の全文取得で強化
            enhanced_results = self._enhance_content_with_full_fetch(search_results)
            enhanced_count = sum(1 for result in enhanced_results if result.get('content_enhanced', False))
            
            if enhanced_count > 0:
                logger.info(f"✅ コンテンツ強化完了: {enhanced_count}/{len(search_results)}件で全文取得成功")
            else:
                logger.info("ℹ️ 既存のexcerptを使用（全文取得は不要またはスキップ）")
            
            # Step 2: 強化された検索結果を構造化文字列に変換
            formatted_results = self._format_search_results(enhanced_results)
            
            # Step 3: メモリーコンテキストがある場合は質問を拡張
            enhanced_query = user_query
            if memory_context:
                enhanced_query = f"{user_query}\n\n【前回のコンテキスト】{memory_context}"
            
            # Step 4: RunnableSequenceで回答生成 (最新LangChain API)
            result = self.chain.invoke({
                "search_results": formatted_results,
                "user_query": enhanced_query
            })
            
            # Step 5: AIMessageから文字列コンテンツを抽出
            response = result.content if hasattr(result, 'content') else str(result)
            
            # Step 6: 参照元情報と深掘り提案を追加
            enhanced_response = self._enhance_response_with_sources(response, enhanced_results, user_query)
            
            # Step 7: コンテンツ強化の統計情報を追加
            confluence_enhanced = sum(1 for result in enhanced_results 
                                    if result.get('content_enhanced', False) and 
                                    (result.get('datasource') == 'confluence' or result.get('source') == 'confluence'))
            jira_enhanced = enhanced_count - confluence_enhanced
            
            if enhanced_count > 0:
                stats_parts = []
                if confluence_enhanced > 0:
                    stats_parts.append(f"Confluence: {confluence_enhanced}件（無制限全文取得）")
                if jira_enhanced > 0:
                    stats_parts.append(f"Jira: {jira_enhanced}件（詳細取得）")
                    
                stats_detail = " | ".join(stats_parts)
                stats_info = f"\n\n---\n**📄 コンテンツ取得状況**: {enhanced_count}/{len(search_results)}件で詳細ページ情報を取得\n**🔍 取得詳細**: {stats_detail}\n**💡 効果**: より包括的で詳細な回答を提供"
                enhanced_response += stats_info
            else:
                stats_info = f"\n\n---\n**📄 コンテンツ取得状況**: 既存の要約データを使用（{len(search_results)}件）"
                enhanced_response += stats_info
            
            logger.info("✅ 回答生成完了: 文字数=%d, 強化件数=%d", len(enhanced_response), enhanced_count)
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
        
        # 基本的な深掘り提案（動的キーワードベース）
        primary_keyword = query_keywords[0] if query_keywords else None
        
        # 汎用的な提案生成（固定パターンを廃止）
        if primary_keyword:
            suggestions.extend([
                f"{primary_keyword}の技術仕様を詳しく知りたい",
                f"{primary_keyword}の運用手順を確認したい",
                f"{primary_keyword}との連携方法を見たい"
            ])
        
        # 検索結果から動的に関連キーワードを抽出して提案
        if result_keywords and len(result_keywords) > 1:
            secondary_keyword = result_keywords[1] if result_keywords[1] != primary_keyword else result_keywords[0]
            suggestions.append(f"{secondary_keyword}について詳しく知りたい")
        
        # ユーザータイプ別の提案（検索結果から推測）
        if any("会員" in str(result) for result in search_results):
            suggestions.append("会員向け機能の詳細仕様を確認したい")
        if any("企業" in str(result) for result in search_results):
            suggestions.append("クライアント企業向け機能を確認したい")
        if any("管理者" in str(result) for result in search_results):
            suggestions.append("管理者向け機能の設定方法を見たい")
        
        if not suggestions:
            return ""
        
        lines = ["## 🎯 さらなる深掘り・関連情報"]
        for suggestion in suggestions[:3]:  # 最大3つに制限
            lines.append(f'- 「{suggestion}」')
        
        return "\n".join(lines)
    
    def _extract_query_keywords(self, user_query: str) -> List[str]:
        """ユーザー質問からキーワードを抽出（動的抽出版）"""
        keywords = []
        
        # 重要キーワードパターンを動的に検出
        import re
        
        # 具体的な技術・機能キーワードを抽出
        technical_patterns = [
            r'[ァ-ヶー一-龯]+機能',  # XX機能
            r'[ァ-ヶー一-龯]+設計',  # XX設計
            r'[ァ-ヶー一-龯]+管理',  # XX管理
            r'[ァ-ヶー一-龯]+認証',  # XX認証
            r'API[ァ-ヶー一-龯]*',   # API関連
            r'UI[ァ-ヶー一-龯]*',    # UI関連
            r'データベース[ァ-ヶー一-龯]*'  # DB関連
        ]
        
        for pattern in technical_patterns:
            matches = re.findall(pattern, user_query)
            keywords.extend(matches)
        
        # 基本的な機能キーワード
        basic_keywords = ["認証", "画面", "仕様", "設計", "実装", "機能", "システム"]
        for keyword in basic_keywords:
            if keyword in user_query and keyword not in keywords:
                keywords.append(keyword)
        
        # 重複除去と最大5個制限
        unique_keywords = list(dict.fromkeys(keywords))
        return unique_keywords[:5]
    
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
        検索結果を読みやすい形式にフォーマット（完全コンテンツ対応）
        
        Args:
            search_results: 検索結果リスト
            
        Returns:
            フォーマットされた結果文字列
        """
        if not search_results:
            return "検索結果が見つかりませんでした。"
        
        formatted_sections = []
        
        for i, result in enumerate(search_results, 1):
            source = result.get('source', result.get('datasource', 'Unknown'))
            title = result.get('title', 'タイトルなし')
            
            # コンテンツの優先順位: content > excerpt > summary
            content = result.get('content')
            if not content:
                content = result.get('excerpt', '')
            if not content:
                content = result.get('summary', '')
            
            url = result.get('url', '')
            relevance_score = result.get('relevance_score', result.get('final_score', 0))
            
            # より詳細な情報を取得可能な場合は追加
            created = result.get('created', '')
            result_type = result.get('type', '')
            space = result.get('space', '')
            
            # コンテンツが短すぎる場合の処理
            if content and len(content) > 500:
                # 長いコンテンツは適切に要約
                content_preview = content[:500] + "..."
                full_content_available = True
            else:
                content_preview = content
                full_content_available = False
            
            section = f"""
=== 検索結果 {i} ===
ソース: {source}
タイトル: {title}
関連度: {relevance_score:.3f}"""
            
            # 追加メタデータ
            if space:
                section += f"\nスペース: {space}"
            if result_type:
                section += f"\nタイプ: {result_type}"
            if created:
                section += f"\n作成日: {created}"
            
            section += f"\nURL: {url}"
            
            section += f"""
内容:
{content_preview}"""
            
            if full_content_available:
                section += "\n\n※ さらに詳細な情報が利用可能です"
            
            formatted_sections.append(section)
        
        # 検索結果サマリーを追加
        summary_section = f"""
=== 検索結果サマリー ===
総件数: {len(search_results)}件
平均関連度: {sum(result.get('relevance_score', result.get('final_score', 0)) for result in search_results) / len(search_results):.3f}
主要ソース: {', '.join(set(result.get('source', result.get('datasource', 'Unknown')) for result in search_results))}
"""
        
        formatted_sections.insert(0, summary_section)
        
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

    def _enhance_content_with_full_fetch(self, search_results: List[Dict]) -> List[Dict]:
        """
        検索結果のコンテンツを全文取得で強化
        
        300文字制限を撤廃し、Confluenceデータを無制限に取得
        
        Args:
            search_results: 検索結果リスト
            
        Returns:
            全文取得で強化された検索結果リスト
        """
        enhanced_results = []
        
        for result in search_results:
            enhanced_result = result.copy()
            
            # 現在のコンテンツを確認
            current_content = result.get('content') or result.get('excerpt', '')
            
            # Confluenceページの場合は常に全文取得を試行（無制限）
            if result.get('datasource') == 'confluence' or result.get('source') == 'confluence':
                logger.info(f"🔄 Confluence全文取得開始: {result.get('title', 'Unknown')}")
                full_content = self._fetch_full_page_content(result)
                if full_content and len(full_content) > len(current_content):
                    enhanced_result['content'] = full_content
                    enhanced_result['content_enhanced'] = True
                    logger.info(f"✅ Confluence全文取得成功: {result.get('title', 'Unknown')} ({len(current_content)}→{len(full_content)}文字)")
                else:
                    enhanced_result['content_enhanced'] = False
                    logger.warning(f"⚠️ Confluence全文取得失敗またはサイズ不変: {result.get('title', 'Unknown')}")
            
            # Jiraの場合は従来通り短い場合のみ全文取得
            elif (result.get('datasource') == 'jira' or result.get('source') == 'jira') and len(current_content) < 500:
                logger.info(f"🔄 Jira全文取得開始: {result.get('title', 'Unknown')}")
                full_content = self._fetch_full_page_content(result)
                if full_content and len(full_content) > len(current_content):
                    enhanced_result['content'] = full_content
                    enhanced_result['content_enhanced'] = True
                    logger.info(f"✅ Jira全文取得成功: {result.get('title', 'Unknown')} ({len(current_content)}→{len(full_content)}文字)")
                else:
                    enhanced_result['content_enhanced'] = False
            else:
                enhanced_result['content_enhanced'] = False
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def _fetch_full_page_content(self, result: Dict) -> str:
        """
        個別ページの全文コンテンツを取得
        
        Args:
            result: 検索結果辞書
            
        Returns:
            ページ全文 (取得失敗時は空文字列)
        """
        try:
            # Confluenceページの場合
            if result.get('source') == 'confluence' or result.get('datasource') == 'confluence':
                return self._fetch_confluence_page_content(result)
            
            # Jiraの場合
            elif result.get('source') == 'jira' or result.get('datasource') == 'jira':
                return self._fetch_jira_issue_content(result)
            
            else:
                logger.warning(f"⚠️ 不明なソース形式: {result.get('source', result.get('datasource', 'Unknown'))}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ 全文取得エラー: {e}")
            return ""
    
    def _fetch_confluence_page_content(self, result: Dict) -> str:
        """
        Confluenceページの全文取得
        
        Args:
            result: Confluence検索結果
            
        Returns:
            ページ全文
        """
        try:
            from atlassian import Confluence
            
            # API接続設定
            confluence = Confluence(
                url=f"https://{self.settings.atlassian_domain}",
                username=self.settings.atlassian_email,
                password=self.settings.atlassian_api_token
            )
            
            # ページIDを取得
            page_id = result.get('id')
            if not page_id:
                logger.warning("⚠️ ConfluenceページID不明")
                return ""
            
            # ページ詳細を取得（body.storage形式）
            page_content = confluence.get_page_by_id(
                page_id, 
                expand='body.storage,version,space'
            )
            
            if page_content and 'body' in page_content:
                storage_content = page_content['body']['storage']['value']
                
                # HTMLタグを除去してテキストのみ抽出
                import re
                clean_content = re.sub(r'<[^>]+>', '', storage_content)
                clean_content = re.sub(r'\s+', ' ', clean_content).strip()
                
                return clean_content
            else:
                logger.warning("⚠️ Confluenceページコンテンツ取得失敗")
                return ""
                
        except ImportError:
            logger.warning("⚠️ atlassian-python-api not available")
            return ""
        except Exception as e:
            logger.error(f"❌ Confluence全文取得エラー: {e}")
            return ""
    
    def _fetch_jira_issue_content(self, result: Dict) -> str:
        """
        Jiraイシューの全文取得
        
        Args:
            result: Jira検索結果
            
        Returns:
            イシュー全文
        """
        try:
            from atlassian import Jira
            
            # API接続設定
            jira = Jira(
                url=f"https://{self.settings.atlassian_domain}",
                username=self.settings.atlassian_email,
                password=self.settings.atlassian_api_token
            )
            
            # イシューキーまたはIDを取得
            issue_key = result.get('id') or result.get('key')
            if not issue_key:
                logger.warning("⚠️ JiraイシューID/キー不明")
                return ""
            
            # イシュー詳細を取得
            issue = jira.issue(issue_key, expand='renderedFields')
            
            if issue:
                # 要約、説明、コメントを統合
                content_parts = []
                
                # 要約
                summary = issue.get('fields', {}).get('summary', '')
                if summary:
                    content_parts.append(f"要約: {summary}")
                
                # 説明
                description = issue.get('fields', {}).get('description')
                if description:
                    content_parts.append(f"説明: {description}")
                
                # レンダリング済み説明があれば優先
                rendered_desc = issue.get('renderedFields', {}).get('description')
                if rendered_desc:
                    import re
                    clean_desc = re.sub(r'<[^>]+>', '', rendered_desc)
                    content_parts.append(f"詳細説明: {clean_desc}")
                
                return "\n\n".join(content_parts)
            else:
                logger.warning("⚠️ Jiraイシューコンテンツ取得失敗")
                return ""
                
        except ImportError:
            logger.warning("⚠️ atlassian-python-api not available")
            return ""
        except Exception as e:
            logger.error(f"❌ Jira全文取得エラー: {e}")
            return "" 