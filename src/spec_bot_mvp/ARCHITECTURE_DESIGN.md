# 仕様書作成支援ボット MVP - アーキテクチャ設計書

| ドキュメント | バージョン | 作成日 | 参照仕様書 |
| :--- | :--- | :--- | :--- |
| **アーキテクチャ設計書** | **v1.0** | 2024/12/25 | SPEC-PL-001, SPEC-DS-001, SPEC-DS-002 |

---

## 🎯 1. アーキテクチャ方針

### 1.1. ハイブリッドモデル設計

**仕様書定義 (SPEC-PL-001 要件定義書.md):**
```
ハイブリッドモデル：
- 主系路：固定検索パイプライン (安定性重視)
- 副系路：フォールバックAgent (柔軟性重視)  
- 集約系：回答生成Agent
```

**実装方針:**
```python
# メインアプリケーション制御フロー
def main_application_flow(user_query: str, filters: dict) -> str:
    # 1. 固定検索パイプライン実行 (主系路)
    search_result = hybrid_search_pipeline(user_query, filters)
    
    # 2. 品質評価・結果判定
    quality_score = evaluate_search_quality(search_result)
    
    # 3. Agent選択と実行
    if quality_score >= HIGH_QUALITY_THRESHOLD:
        # 高品質結果 → 回答生成Agent
        return response_generation_agent(search_result, user_query)
    else:
        # 低品質結果 → フォールバック検索Agent
        fallback_result = fallback_search_agent(user_query, filters)
        return response_generation_agent(fallback_result, user_query)
```

### 1.2. Agent役割分担

**仕様書定義 (SPEC-DS-001 開発設計書.md 4.1):**

#### **回答生成Agent**
- **役割**: 検索結果を統合・要約して最終回答を生成
- **タイプ**: LLMChain（外部ツール無し）
- **入力**: 検索結果 + ユーザー質問
- **出力**: 統合された最終回答

#### **フォールバック検索Agent**  
- **役割**: 固定パイプライン失敗時の探索的検索
- **タイプ**: ReAct Agent（ツール有り）
- **ツール**: `fallback_jira_search`, `fallback_confluence_search`
- **特徴**: 創造的・試行錯誤的な検索実行

### 1.3. 固定検索パイプライン (主系路)

**仕様書定義 (SPEC-DS-002 ハイブリッド検索システム仕様書.md):**

```
Step1: フィルタ機能 (UIで処理済み)
Step2: キーワード抽出 (Gemini + ルールベース)
Step3: データソース判定 (Jira/Confluence自動選択)
Step4: CQL検索実行 (3段階検索戦略)
Step5: 品質評価・ランキング (3軸評価)
Step6: 後続Agent連携 (新規実装が必要)
```

---

## 🏗️ 2. コーディング方針

### 2.1. プロジェクト構造

```
src/spec_bot_mvp/
├── app.py                     # 【新規】メインアプリケーション
├── agents/                    # 【新規】Agent機能
│   ├── __init__.py
│   ├── response_generator.py  # 回答生成Agent
│   ├── fallback_searcher.py  # フォールバック検索Agent  
│   └── agent_selector.py     # Agent選択ロジック
├── steps/                     # 【既存】固定パイプライン
│   ├── step1_keyword_extraction.py    # ✅実装済み
│   ├── step2_datasource_judgment.py   # ✅実装済み  
│   ├── step3_cql_search.py            # ✅実装済み
│   ├── step4_quality_evaluation.py    # ✅実装済み
│   └── step5_agent_handover.py        # 【新規】Agent連携
├── tools/                     # 【既存】ツール群
│   ├── hybrid_search_tool.py          # ✅実装済み
│   ├── fallback_jira_tool.py          # 【新規】
│   └── fallback_confluence_tool.py    # 【新規】
├── ui/                        # 【既存】UI機能
│   ├── streamlit_app_integrated.py    # 【修正】独立性確保
│   └── hierarchy_filter_ui.py         # 【新規】独自実装
├── config/                    # 【既存】設定管理
│   └── settings.py                    # ✅実装済み
└── utils/                     # 【既存】ユーティリティ
    └── atlassian_api_client.py        # ✅実装済み
```

### 2.2. 実装優先順位

#### **🔴 Priority 1: アーキテクチャ基盤整備**

1. **メインアプリケーション (app.py)**
   ```python
   # 基本制御フロー
   def main():
       user_query = get_user_input()
       filters = get_active_filters()
       
       # ハイブリッド制御フロー実行
       response = hybrid_control_flow(user_query, filters)
       
       display_response(response)
   ```

2. **Agent機能実装**
   - `agents/response_generator.py`: LLMChain実装
   - `agents/fallback_searcher.py`: ReAct Agent実装
   - `agents/agent_selector.py`: 選択ロジック

3. **Step5実装**
   - `steps/step5_agent_handover.py`: Step4結果からAgent選択

#### **🟡 Priority 2: 統合・最適化**

1. **UI独立性確保**
   - `spec_bot` 依存排除
   - 独自フィルターUI実装

2. **フォールバックツール実装**
   - `fallback_jira_tool.py`
   - `fallback_confluence_tool.py`

#### **🟢 Priority 3: 品質向上**

1. **プロンプトチューニング**
2. **エラーハンドリング**
3. **パフォーマンス最適化**

### 2.3. コーディング規約

#### **2.3.1. 命名規約**

```python
# クラス名: パスカルケース
class ResponseGenerationAgent:
    pass

# 関数名: スネークケース  
def execute_hybrid_search():
    pass

# 定数名: アッパースネークケース
HIGH_QUALITY_THRESHOLD = 0.75

# ファイル名: スネークケース
# response_generator.py, fallback_searcher.py
```

#### **2.3.2. インポート規約**

```python
# 標準ライブラリ
import os
from typing import Dict, List, Optional

# サードパーティ
import streamlit as st
from langchain.agents import AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI

# プロジェクト内部
from src.spec_bot_mvp.config.settings import Settings
from src.spec_bot_mvp.steps.step4_quality_evaluation import QualityEvaluator
```

#### **2.3.3. ログ出力規約**

```python
import logging

logger = logging.getLogger(__name__)

# 成功ログ
logger.info("✅ 固定検索パイプライン実行完了: 結果数=%d", result_count)

# 警告ログ  
logger.warning("⚠️ 品質評価しきい値未達: スコア=%.2f", quality_score)

# エラーログ
logger.error("❌ Agent実行失敗: %s", str(error))
```

#### **2.3.4. 型ヒント規約**

```python
from typing import Dict, List, Optional, Union, Tuple

def hybrid_search_pipeline(
    user_query: str, 
    filters: Dict[str, Any]
) -> Tuple[List[Dict], float]:
    """
    ハイブリッド検索パイプライン実行
    
    Args:
        user_query: ユーザー入力クエリ
        filters: フィルター条件辞書
        
    Returns:
        Tuple[検索結果リスト, 品質スコア]
    """
    pass
```

---

## 🔧 3. 技術詳細仕様

### 3.1. LangChain Agent設計

#### **3.1.1. 回答生成Agent**

```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

class ResponseGenerationAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.3  # 安定性重視
        )
        
        self.prompt = PromptTemplate(
            input_variables=["search_results", "user_query"],
            template="""
            以下の検索結果を元に、ユーザーの質問に対する包括的な回答を生成してください。

            ユーザー質問: {user_query}
            
            検索結果:
            {search_results}
            
            回答:
            """
        )
        
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)
```

#### **3.1.2. フォールバック検索Agent**

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import Tool

class FallbackSearchAgent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            temperature=0.7  # 柔軟性重視
        )
        
        self.tools = [
            Tool(
                name="fallback_jira_search",
                description="より柔軟なJira検索を実行",
                func=self._fallback_jira_search
            ),
            Tool(
                name="fallback_confluence_search", 
                description="より柔軟なConfluence検索を実行",
                func=self._fallback_confluence_search
            )
        ]
        
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self._get_react_prompt()
        )
```

### 3.2. エラーハンドリング戦略

```python
class HybridSearchError(Exception):
    """ハイブリッド検索エラー基底クラス"""
    pass

class PipelineExecutionError(HybridSearchError):
    """固定パイプライン実行エラー"""
    pass

class AgentExecutionError(HybridSearchError):
    """Agent実行エラー"""
    pass

def safe_execute_with_fallback(primary_func, fallback_func, *args, **kwargs):
    """安全な実行（フォールバック付き）"""
    try:
        return primary_func(*args, **kwargs)
    except Exception as e:
        logger.warning("主系路実行失敗、フォールバックに切り替え: %s", e)
        return fallback_func(*args, **kwargs)
```

---

## 📊 4. 品質評価基準

### 4.1. コード品質

- **テストカバレッジ**: 85%以上
- **型ヒント適用率**: 100%（公開関数・メソッド）
- **docstring記述率**: 100%（公開関数・メソッド）

### 4.2. パフォーマンス目標

- **検索レスポンス時間**: 3秒以内
- **UI応答性**: 1秒以内
- **メモリ使用量**: 512MB以内

### 4.3. 仕様準拠度

- **機能要件充足率**: 100%（MVP scope）
- **アーキテクチャ適合率**: 100%（ハイブリッドモデル）
- **API仕様準拠率**: 100%（Atlassian REST API）

---

## 🔄 5. 開発フロー

### 5.1. 開発手順

1. **Phase 1**: メインアプリケーション実装
2. **Phase 2**: Agent機能実装
3. **Phase 3**: 統合テスト・調整
4. **Phase 4**: UI独立性確保
5. **Phase 5**: 品質向上・チューニング

### 5.2. 検証基準

各Phaseで以下を検証:
- ✅ 仕様書との整合性
- ✅ 既存実装との互換性  
- ✅ パフォーマンス目標達成
- ✅ エラーハンドリング動作

---

*最終更新: 2024年12月25日 - v1.0* 