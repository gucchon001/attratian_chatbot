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
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
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
        # Gemini LLM設定（安定性重視）
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.settings.google_api_key,
            temperature=0.3,  # 安定性重視
            max_output_tokens=2048
        )
        
        # プロンプトテンプレート
        self.prompt = PromptTemplate(
            input_variables=["search_results", "user_query"],
            template=self._get_response_prompt_template()
        )
        
        # LLMChain構築
        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            verbose=True
        )
    
    def _get_response_prompt_template(self) -> str:
        """回答生成用プロンプトテンプレート"""
        return """あなたは仕様書作成支援の専門AIアシスタントです。
ユーザーの質問に対して、提供された検索結果を元に包括的で実用的な回答を生成してください。

【ユーザー質問】
{user_query}

【検索結果】
{search_results}

【回答生成の指針】
1. **完全性**: 検索結果の重要な情報をもれなく統合する
2. **構造化**: 見出し、箇条書きを活用して読みやすく整理する  
3. **実用性**: 開発者が具体的にアクションを取れる情報を優先する
4. **文脈理解**: ユーザーの質問意図を正確に理解して回答する
5. **信頼性**: 検索結果に基づかない推測や憶測は避ける

【回答フォーマット】
## 📋 質問への回答

[ユーザー質問に対する直接的な回答]

## 🔍 詳細情報

[検索結果から得られた具体的な詳細]

## 📚 関連情報・参考資料

[関連するチケット、ページ、仕様書等の情報]

## 💡 推奨アクション

[この情報を基にユーザーが取るべき次のステップ]

回答:"""

    def generate_response(self, search_results: List[Dict], user_query: str) -> str:
        """
        検索結果を統合して最終回答を生成
        
        Args:
            search_results: 検索結果リスト
            user_query: ユーザー質問
            
        Returns:
            統合された最終回答
        """
        try:
            # 検索結果を構造化文字列に変換
            formatted_results = self._format_search_results(search_results)
            
            logger.info("💡 回答生成開始: クエリ='%s', 結果数=%d", user_query, len(search_results))
            
            # LLMChainで回答生成
            response = self.chain.run(
                search_results=formatted_results,
                user_query=user_query
            )
            
            logger.info("✅ 回答生成完了: 文字数=%d", len(response))
            return response
            
        except Exception as e:
            logger.error("❌ 回答生成失敗: %s", str(e))
            return self._generate_error_response(user_query, str(e))
    
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