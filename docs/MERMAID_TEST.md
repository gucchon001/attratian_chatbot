# Mermaid 図表示テスト

## 🧪 **VSCode Mermaid拡張機能テスト用サンプル**

### **1. シンプルなフローチャート**
```mermaid
flowchart TD
    A[開始] --> B{条件分岐}
    B -->|Yes| C[処理A]
    B -->|No| D[処理B]
    C --> E[終了]
    D --> E
```

### **2. クラス図サンプル**
```mermaid
classDiagram
    class SpecBotAgent {
        -llm: ChatGoogleGenerativeAI
        -tools: List[Tool]
        +process_request(input: str): str
        +get_history(): List[Dict]
    }
    
    class HybridSearchTool {
        +_run(query: str): str
    }
    
    SpecBotAgent --> HybridSearchTool : uses
```

### **3. シーケンス図サンプル**
```mermaid
sequenceDiagram
    participant User as 👤 ユーザー
    participant UI as 🎨 UI
    participant Agent as 🧠 Agent
    
    User->>UI: 質問入力
    UI->>Agent: process_request()
    Agent-->>UI: 回答
    UI-->>User: 結果表示
```

### **4. ガントチャート**
```mermaid
gantt
    title プロジェクトスケジュール
    dateFormat  YYYY-MM-DD
    section Phase 1
    設計書作成    :done, des1, 2025-01-20, 2025-01-24
    実装完了      :done, imp1, 2025-01-21, 2025-01-24
    section Phase 2
    実Confluence連携 :active, con1, 2025-01-25, 2025-01-31
```

## 📋 **表示確認チェックリスト**

- [ ] フローチャートが正しく表示される
- [ ] クラス図の関係線が描画される
- [ ] シーケンス図の参加者が表示される
- [ ] ガントチャートの期間が正しい
- [ ] 日本語テキストが正しく表示される
- [ ] 絵文字が正しく表示される

## 🎨 **スタイルテスト**

### **テーマ: Default**
```mermaid
graph LR
    A[開始] --> B[処理] --> C[終了]
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
```

### **カラーパレット確認**
```mermaid
pie title カラーテスト
    "青" : 42.96
    "緑" : 50.05
    "赤" : 10.01
```

---

**表示テスト手順:**
1. VSCodeでこのファイルを開く
2. `Ctrl+Shift+V` でプレビューを開く
3. 全ての図が正しく表示されることを確認
4. リアルタイム編集テスト（図を修正して即座に反映確認） 