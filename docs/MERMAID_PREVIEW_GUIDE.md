# VSCode Mermaid プレビューガイド

## 🎨 **VSCodeでのMermaid図表示方法**

### **必要な拡張機能**

#### **1. Mermaid Preview (推奨)**
```
名前: Mermaid Preview
ID: bierner.markdown-mermaid
インストール: VSCode Extensions > "mermaid preview" で検索
```

#### **2. Markdown Preview Enhanced (オプション)**
```
名前: Markdown Preview Enhanced
ID: shd101wyy.markdown-preview-enhanced
機能: より高機能なマークダウンプレビュー
```

---

## 📖 **使用方法**

### **1. 設計書ファイルを開く**
```
docs/SPEC-DS-005A クラス図設計書.md
docs/SPEC-DS-005B シーケンス図設計書.md
docs/SPEC-DS-005C コンポーネント図設計書.md
docs/SPEC-DS-005D アクティビティ図設計書.md
```

### **2. プレビューを開く**
```
方法1: Ctrl+Shift+P → "Markdown: Open Preview" 
方法2: エディタ右上の「プレビューボタン」をクリック
方法3: Ctrl+Shift+V (標準プレビュー)
```

### **3. Mermaid図の確認**
- マークダウンプレビューでMermaid図が自動レンダリング
- リアルタイム更新対応
- ズーム・パン操作可能

---

## 🛠️ **設定の最適化**

### **VSCode設定 (settings.json)**
```json
{
  "markdown.mermaid.theme": "default",
  "markdown-preview-enhanced.mermaidTheme": "default",
  "markdown.preview.fontSize": 14,
  "markdown.preview.lineHeight": 1.6
}
```

### **Mermaid図のテーマ設定**
```json
{
  "markdown-preview-enhanced.mermaidTheme": "dark",
  "markdown.mermaid.theme": "dark"
}
```

---

## 🎯 **プロジェクト固有の設定**

### **1. ワークスペース設定**
`.vscode/settings.json` に以下を追加：
```json
{
  "files.associations": {
    "*.md": "markdown"
  },
  "markdown.preview.fontSize": 13,
  "markdown.mermaid.theme": "default"
}
```

### **2. 推奨拡張機能リスト**
`.vscode/extensions.json` を作成：
```json
{
  "recommendations": [
    "bierner.markdown-mermaid",
    "shd101wyy.markdown-preview-enhanced",
    "yzhang.markdown-all-in-one"
  ]
}
```

---

## 🚀 **活用例**

### **設計書レビュー時**
1. 設計書ファイルを開く
2. プレビューを横に表示 (Ctrl+\)
3. コードとMermaid図を同時確認
4. リアルタイム編集・プレビュー

### **チーム共有時**
1. VSCodeでプレビュー表示
2. 画面共有でMermaid図を説明
3. その場での図の修正・更新
4. Git commit & push

---

## 📋 **トラブルシューティング**

### **Mermaid図が表示されない場合**
```
1. 拡張機能の再読み込み: F1 → "Developer: Reload Window"
2. Mermaid拡張機能の確認: Extensions → "Mermaid" で検索
3. マークダウンプレビューの再起動: プレビューを閉じて再度開く
```

### **図が正しく描画されない場合**
```
1. Mermaid記法の確認: ```mermaid で開始しているか
2. 構文エラーの確認: VSCode Problems パネルを確認
3. テーマの変更: settings.json でテーマを変更
```

---

*最終更新: 2025年1月24日 - VSCode Mermaid対応完了* 