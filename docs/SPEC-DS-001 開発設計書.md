# SPEC-DS-001 開発設計書

| バージョン | ステータス | 作成日 | 参照ドキュメント |
| :--- | :--- | :--- | :--- |
| **v4.0** | **段階開発方針版** | 2025/01/17 | SPEC-PL-001 v3.6 |

**v4.0更新内容:**
- 3段階開発方針の技術設計への反映
- Stage 1: Confluence専用Agent設計に特化
- ハイブリッドアーキテクチャの技術詳細更新

---

## 1. はじめに
本ドキュメントは、「仕様書作成支援ボット」を**3段階の段階開発**で確実に価値提供するための技術設計と開発手順を定義する。

### **段階開発方針の技術的反映**
- **Stage 1**: Confluence専用LangChain Agent + 3段階CQL検索最適化
- **Stage 2**: Jira統合Agent + 統合検索結果マージロジック
- **Stage 3**: エンタープライズレベル統合UI + 高度フィルター完全版

本設計書では主にStage 1の技術仕様を詳述し、Stage 2-3の拡張ポイントを明記する。

---

## 2. 新アーキテクチャ概要 (LangChainベース)

本システムは、LangChainの**Agent（エージェント）**を中核に据えたアーキテクチャを採用する。Agentはユーザーの指示を理解し、自律的に最適な「道具（Tool）」を選択・実行し、その結果を元に最終的な回答を生成する頭脳として機能する。

![LangChainアーキテクチャ図](https://i.imgur.com/r6b3g1M.png)
*(この図は概念を示しており、内部ではLangChain Agentが司令塔として動作します)*

* **UI (Streamlit):** ユーザーからの入力を受け取り、Agentの最終的な回答を表示する。
* **Agent (LangChain):** ユーザーの入力、会話履歴（Memory）、利用可能な道具（Tools）を考慮し、次に何をすべきかを判断する。
* **Tools (LangChain):** `Jira検索`や`Confluence検索`といった、私たちが実装する個別の機能をAgentが利用できる「道具」として定義したもの。
* **LLM (Gemini API):** Agentの思考エンジン。ユーザーの意図を解釈し、どの道具を使うべきか判断し、最終的な回答を生成するために使われる。
* **Memory (LangChain):** 過去の会話履歴を記憶し、Agentが文脈を理解した応答をするために利用される。

---

## 3. 技術選定
* **UIフレームワーク:** `Streamlit`
* **中核フレームワーク:** `LangChain`
* **LLM:** `Gemini API (via langchain-google-genai)`
* **外部連携API:** `Atlassian REST API (via atlassian-python-api)`

---

## 4. 機能一覧とモジュール設計 (LangChainベース)

### 4.1. 道具 (Tools) の設計
Agentが利用する「道具」として、以下のPython関数を実装し、LangChainの`Tool`クラスでラップする。

* **`search_jira_tool(query: str) -> str`**
    * **役割:** Jiraから関連チケットを検索する。
    * **Agentへの説明 (Description):** 「Jiraのチケット（タスク、バグ、ストーリー）に関する情報を検索したい場合に使う。ユーザーの質問から、検索キーワードを抽出して引数に渡すこと。」
    * **戻り値:** 見つかったチケット情報のサマリー文字列。

* **`search_confluence_tool(query: str) -> str`**
    * **役割:** Confluenceから関連ページを検索する。
    * **Agentへの説明 (Description):** 「Confluenceの仕様書や議事録など、ドキュメントに関する情報を検索したい場合に使う。ユーザーの質問から、検索キーワードを抽出して引数に渡すこと。」
    * **戻り値:** 見つかったページ情報のサマリー文字列。

### 4.2. AgentとMemoryの設計
* **LLMの初期化:** `langchain_google_genai`ライブラリの`ChatGoogleGenerativeAI`クラスを使い、Geminiモデルを初期化する。
* **Memoryの初期化:** `langchain.memory`の`ConversationBufferMemory`を使い、会話履歴を保持するコンポーネントを初期化する。
* **Agentの初期化:** 上記で定義した`Tools`、`LLM`、`Memory`を組み合わせ、**ReAct (Reasoning and Acting)** という思考プロセスを持つAgentを初期化する。このAgentが、ユーザーの質問に対して「思考→行動（ツール実行）→観察→次の思考...」というサイクルを回して答えを導き出す。

### 4.3. メインアプリケーション (`app.py`) の設計
* **役割:** StreamlitのUIを描画し、初期化されたLangChain Agentを実行する。
* **ロジック:**
    1.  アプリケーション起動時に一度だけ、LLM、Tools、Memory、Agentを初期化する。
    2.  UI（タイトル、説明、チャット履歴）を描画する。
    3.  `st.chat_input`でユーザーからの入力を受け取る。
    4.  入力をAgentの実行関数（`agent_executor.invoke()`）に渡す。
    5.  Agentからの最終的な回答をチャット履歴に追加し、画面を更新する。

---

## 5. 開発手順書 (LangChainベース)

### **フェーズ0: 環境構築 (0.5日)**
* **目的:** LangChainベースの開発環境を構築する。
* **手順:**
    1.  仮想環境を構築する。
    2.  必要なライブラリをインストールする。
        ```bash
        pip install streamlit atlassian-python-api python-dotenv langchain langchain-google-genai
        ```
    3.  `.env`ファイルに各種APIキーを設定する。

### **フェーズ1: Agentコア機能の実装とテスト (2.5日)**
* **目的:** UIを介さず、まずAgentが正しく思考し、道具を使えることを確認する。
* **手順:**
    1.  **Toolの実装:** `search_jira_tool`と`search_confluence_tool`関数を実装し、テストする。
    2.  **Toolの定義:** 上記関数をLangChainの`Tool`として定義する。この際、Agentが理解しやすいように**明確な`description`（説明文）**を記述することが極めて重要。
    3.  **Agentの初期化:** LLM、Memory、Toolsを組み合わせてAgentを初期化するコードを記述する。
    4.  **コマンドラインでのテスト:** Pythonスクリプトとして直接Agentを呼び出し、様々な質問（例：「ログイン機能について教えて」「そのチケットの担当者は？」）を投げかけ、Agentの思考プロセス（Thoughtプロセス）と最終的な回答が期待通りかを確認する。

### **フェーズ2: Streamlit UIとの統合 (1日)**
* **目的:** フェーズ1で作成したAgentを、StreamlitのチャットUIに接続する。
* **手順:**
    1.  基本的なチャットUI（タイトル、入力欄、履歴表示）を構築する。
    2.  `st.session_state`にLangChainの`Memory`オブジェクトを保存し、セッション間で会話履歴が維持されるようにする。
    3.  ユーザーの入力をAgentに渡し、その応答をチャット画面に表示するロジックを実装する。`st.spinner`で処理中であることを示す。

### **フェーズ3: 統合テストとプロンプトチューニング (1日)**
* **目的:** アプリケーション全体として、自然で実用的な会話体験が提供できているかを確認・改善する。
* **手順:**
    1.  **シナリオテスト:** 要件定義書のユースケースに基づき、一連の連続した会話を試す。
    2.  **プロンプトチューニング:** Agentが道具をうまく使えない、あるいは意図しない回答をする場合、**Toolの`description`**や、Agentに与える**システムメッセージ（役割設定）**を調整する。
    3.  エラーハンドリングを強化し、ユーザーフレンドリーなメッセージを表示するようにする。