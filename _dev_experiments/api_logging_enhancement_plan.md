# API通信詳細ログ完全実装計画

## 🎯 目標
Atlassian APIとGemini APIの入出力を完全にログ記録し、システムの透明性を最大化する

## 📋 実装が必要な項目

### 1. Atlassian API詳細ログ

#### Jira API
- **リクエスト記録**:
  - JQLクエリの完全なテキスト
  - 検索パラメータ（max_results、fields等）
  - API呼び出し時刻とURL
  
- **レスポンス記録**:
  - 取得チケットの詳細情報（キー、サマリー、ステータス、担当者）
  - 総件数と実取得件数
  - APIレスポンス時間

#### Confluence API
- **リクエスト記録**:
  - CQLクエリの完全なテキスト
  - 検索スペースとパラメータ
  - API呼び出し詳細
  
- **レスポンス記録**:
  - 取得ページの詳細情報（タイトル、ID、スペース、作成者）
  - ページ内容のプレビュー
  - 検索スコアと関連度

### 2. Gemini API詳細ログ

#### プロンプト記録
- **質問分析プロンプト** (Step1):
  - ユーザー質問の分析用プロンプト全文
  - 分析ルールと判定基準
  
- **結果統合プロンプト** (Step3):
  - 検索結果を含む統合用プロンプト全文
  - 要約指示とフィルタリング条件

#### レスポンス記録
- **LLM応答**:
  - 生成された応答の全文
  - トークン使用量（プロンプト・生成・合計）
  - レスポンス時間と処理時間

### 3. 実装方法

#### Phase 1: ミドルウェア作成
```python
# api_logging_middleware.py
class ApiLoggingMiddleware:
    def __init__(self, detailed_logger):
        self.detailed_logger = detailed_logger
    
    def log_jira_request(self, question_id, jql, params):
        # Jira APIリクエストをログ記録
    
    def log_confluence_request(self, question_id, cql, params):
        # Confluence APIリクエストをログ記録
    
    def log_gemini_request(self, question_id, prompt, params):
        # Gemini APIリクエストをログ記録
```

#### Phase 2: 既存ツールの修正
- `confluence_tool.py`: API呼び出し箇所にログ機能を追加
- `jira_tool.py`: API呼び出し箇所にログ機能を追加
- `question_analyzer.py`: LLM呼び出し箇所にログ機能を追加
- `result_synthesizer.py`: LLM呼び出し箇所にログ機能を追加

#### Phase 3: 統合パイプライン拡張
- `integrated_pipeline.py`: ミドルウェアの初期化と各ツールへの渡し

### 4. 期待される出力例

```log
=== Confluence API リクエスト (q_1) ===
CQLクエリ: text ~ "急募機能 仕様" and space = "CLIENTTOMO"
最大取得件数: 25
検索スペース: CLIENTTOMO
リクエスト時刻: 2025-07-18 16:00:00

=== Confluence API レスポンス (q_1) ===
取得ページ数: 12
  ページ1: [CLIENTTOMO] 112_【FIX】契約新規追加機能 (ID: 123456)
  ページ2: [CLIENTTOMO] 急募機能要件定義 (ID: 123457)
  ... 他10件
レスポンス時刻: 2025-07-18 16:00:01

=== Gemini フルプロンプト (q_1) ===
あなたはAtlassian検索結果を統合する専門AIです。
以下の検索結果から「急募機能の仕様書を教えて」という質問に対する回答を生成してください。

【検索結果】
[Confluence] 112_【FIX】契約新規追加機能
内容: 契約の新規追加に関する機能仕様...
=== プロンプト終了 ===

=== Gemini API レスポンス (q_1) ===
レスポンス (先頭300文字): お問い合わせいただいた「急募機能の仕様書」について...
トークン使用量: プロンプト1234 + 生成567 = 合計1801
```

### 5. 実装優先度

1. **高優先度**: Gemini APIプロンプト/レスポンス記録
2. **中優先度**: Confluence API詳細記録  
3. **低優先度**: Jira API詳細記録

### 6. 検証方法

- 新しい詳細ログテストスクリプト作成
- API通信量とレスポンス時間の分析
- ログファイルサイズの最適化（10KB以下目標）

## ⏰ 実装スケジュール

- **Week 1**: ミドルウェア作成とGemini API詳細ログ
- **Week 2**: Confluence API詳細ログ実装
- **Week 3**: 統合テストと最適化
- **Week 4**: パフォーマンス調整とドキュメント整備

---

*現在のStep3統合システムは基本機能として85%完成済み。この計画により100%の透明性を実現可能。* 