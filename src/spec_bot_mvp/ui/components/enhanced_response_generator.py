"""
Enhanced Response Generator

NotebookLMスタイルの高品質な回答生成エンジン
複数の検索結果を統合・分析して包括的な回答を生成
"""

import logging
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

# Gemini AI クライアント
try:
    import google.generativeai as genai
    from ...config.settings import Settings
from ...utils.prompt_loader import load_prompt
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class EnhancedResponseGenerator:
    """
    高品質回答生成エンジン
    
    NotebookLMスタイルの包括的な回答を生成：
    - 複数結果の統合・分析
    - 構造化された説明
    - 詳細な仕様値の抽出
    - 比較・差異分析
    - 関連機能への言及
    """
    
    def __init__(self):
        """初期化"""
        self.settings = Settings()
        self._init_gemini()
        logger.info("✅ EnhancedResponseGenerator初期化完了（プロンプト外部化対応）")
    
    def _init_gemini(self):
        """Gemini AI初期化"""
        if GEMINI_AVAILABLE and self.settings.gemini_api_key:
            try:
                genai.configure(api_key=self.settings.gemini_api_key)
                self.model = genai.GenerativeModel("gemini-2.5-flash")
                self.gemini_ready = True
                logger.info("✅ Gemini AI初期化成功")
            except Exception as e:
                logger.error(f"❌ Gemini AI初期化失敗: {e}")
                self.gemini_ready = False
        else:
            logger.warning("⚠️ Gemini AI利用不可")
            self.gemini_ready = False
    

    
    def generate_comprehensive_response(self, 
                                      query: str, 
                                      search_results: List[Dict],
                                      search_metadata: Dict) -> str:
        """
        包括的な回答生成
        
        Args:
            query: ユーザーの質問
            search_results: Step4の品質評価済み結果
            search_metadata: 検索メタデータ
            
        Returns:
            NotebookLMスタイルの包括的回答
        """
        try:
            logger.info(f"🧠 包括的回答生成開始: {len(search_results)}件の結果を分析")
            
            if not search_results:
                return self._generate_no_results_response(query)
            
            # Gemini AI利用可能性チェック
            if not self.gemini_ready:
                return self._generate_fallback_response(query, search_results)
            
            # 検索結果の前処理
            processed_results = self._preprocess_search_results(search_results)
            
            # Gemini AIによる包括的分析
            comprehensive_response = self._generate_with_gemini(
                query, processed_results, search_metadata
            )
            
            # 後処理（フォーマット調整、関連情報追加）
            final_response = self._postprocess_response(comprehensive_response, search_metadata)
            
            logger.info("✅ 包括的回答生成完了")
            return final_response
            
        except Exception as e:
            logger.error(f"❌ 包括的回答生成エラー: {e}")
            return self._generate_fallback_response(query, search_results)
    
    def _preprocess_search_results(self, search_results: List[Dict]) -> str:
        """検索結果の前処理"""
        
        formatted_results = []
        
        for i, result in enumerate(search_results, 1):
            title = result.get("title", "タイトルなし")
            excerpt = result.get("excerpt", "")
            datasource = result.get("datasource", "unknown")
            score = result.get("final_score", 0)
            
            # excerptから有用な情報を抽出
            clean_excerpt = self._clean_excerpt(excerpt)
            
            formatted_result = f"""
【文書{i}】
タイトル: {title}
データソース: {datasource}
品質スコア: {score:.3f}
内容抜粋:
{clean_excerpt}
"""
            formatted_results.append(formatted_result)
        
        return "\n".join(formatted_results)
    
    def _clean_excerpt(self, excerpt: str) -> str:
        """excerpt内容のクリーニング"""
        if not excerpt:
            return "内容情報なし"
        
        # HTMLタグの除去
        clean_text = re.sub(r'<[^>]+>', '', excerpt)
        
        # 余分な空白・改行の整理
        clean_text = re.sub(r'\s+', ' ', clean_text.strip())
        
        # 長すぎる場合は切り詰め
        if len(clean_text) > 500:
            clean_text = clean_text[:497] + "..."
        
        return clean_text
    
    def _generate_with_gemini(self, 
                             query: str, 
                             processed_results: str, 
                             search_metadata: Dict) -> str:
        """Gemini AIを使用した回答生成"""
        
        # プロンプト構築（外部化されたプロンプトを使用）
        full_prompt = load_prompt(
            "response_generation",
            "enhanced_response_generator", 
            "comprehensive_analysis",
            query=query,
            search_results=processed_results
        )
        
        try:
            # Gemini AIによる生成
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2000,
                    temperature=0.3,  # 一貫性重視
                    top_p=0.8
                )
            )
            
            if response and response.text:
                return response.text
            else:
                logger.warning("⚠️ Gemini AIの応答が空です")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Gemini AI生成エラー: {e}")
            raise
    
    def _postprocess_response(self, response: str, search_metadata: Dict) -> str:
        """回答の後処理"""
        
        if not response:
            return ""
        
        # メタデータ情報の追加
        total_results = search_metadata.get("total_results", 0)
        execution_summary = search_metadata.get("execution_summary", "")
        
        # フッター情報の追加
        footer = f"""

---
**🔍 検索情報**
- 検索結果: {total_results}件から高品質な結果を分析
- 実行概要: {execution_summary}
- 生成方式: AI統合分析（NotebookLMスタイル）
"""
        
        return response + footer
    
    def _generate_no_results_response(self, query: str) -> str:
        """結果なしの場合の回答"""
        return f"""
# {query}について

申し訳ございません。「{query}」に関する情報が見つかりませんでした。

## 🔍 検索のヒント

- **キーワードの見直し**: より具体的なキーワードをお試しください
- **表記の変更**: ひらがな・カタカナ・英語での表記を試してみてください
- **フィルター調整**: データソースやフォルダフィルターを調整してみてください
- **関連用語**: 類義語や関連用語での検索もお試しください

## 💡 推奨アクション

1. キーワードを少し変更して再検索
2. フィルター条件をリセット
3. より一般的な用語で検索後、詳細化

何かご不明な点がございましたら、お気軽にお尋ねください。
"""
    
    def _generate_fallback_response(self, query: str, search_results: List[Dict]) -> str:
        """フォールバック回答（AI利用不可時）"""
        
        output = [
            f"# {query}について",
            "",
            f"**{len(search_results)}件**の関連情報が見つかりました。以下に詳細をご案内します：",
            ""
        ]
        
        # 結果の要約
        for i, result in enumerate(search_results[:5], 1):
            title = result.get("title", "タイトルなし")
            excerpt = result.get("excerpt", "")[:200]
            datasource = result.get("datasource", "unknown").capitalize()
            score = result.get("final_score", 0)
            
            output.extend([
                f"## {i}. {title}",
                f"**データソース**: {datasource} | **品質スコア**: {score:.3f}",
                "",
                excerpt + ("..." if len(result.get("excerpt", "")) > 200 else ""),
                ""
            ])
        
        output.extend([
            "---",
            "**⚠️ 注意**: 現在は基本表示モードです。より詳細な分析にはAI機能の設定が必要です。"
        ])
        
        return "\n".join(output) 