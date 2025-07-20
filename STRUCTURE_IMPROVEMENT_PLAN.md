# 仕様書作成支援ボット - 構造改善計画

## 🎯 目標
安定した実行環境とメンテナンス性の向上

## 📁 推奨構造（長期）

```
attratian_chatbot/
├── app.py                    # 🚀 統一エントリーポイント
├── run.ps1                   # ✅ 安定起動スクリプト
├── requirements.txt          # 📦 依存関係
├── config/                   # ⚙️ 設定ファイル
│   ├── settings.py
│   └── prompts.yaml
├── spec_bot/                 # 📋 メインモジュール（シンプル化）
│   ├── __init__.py
│   ├── core/                 # 🧠 コア機能
│   │   └── agent.py
│   ├── tools/                # 🛠️ ツール
│   │   ├── confluence_tool.py
│   │   └── jira_tool.py
│   ├── utils/                # 🔧 ユーティリティ
│   │   ├── cache_manager.py
│   │   └── streaming_callback.py
│   └── ui/                   # 🖥️ UI（参照のみ）
│       └── hierarchy_filter_ui.py
├── tests/                    # 🧪 テスト
├── logs/                     # 📝 ログ
├── cache/                    # 💾 キャッシュ
└── docs/                     # 📚 ドキュメント
```

## ✅ 現在の修正完了項目

1. **統一実行**: `app.py`ベースで手動・スクリプト実行統一
2. **安定スクリプト**: `run.ps1`が`app.py`を使用
3. **パス問題解決**: 深いネスト回避

## 🔄 将来の改善項目

### Phase 1: モジュール名簡略化
```bash
# 現在
from src.spec_bot_mvp.core.agent import SpecBotAgent

# 改善後
from spec_bot.core.agent import SpecBotAgent
```

### Phase 2: 設定の外部化
```bash
# 設定ファイル分離
config/
├── settings.py        # アプリ設定
├── prompts.yaml       # プロンプトテンプレート
└── logging.yaml       # ログ設定
```

### Phase 3: エントリーポイント最適化
```python
# app.py の改良
"""
仕様書作成支援ボット - 統一エントリーポイント
"""
import sys
from pathlib import Path

# プロジェクトルートを確実にパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from spec_bot.ui.streamlit_app import main

if __name__ == "__main__":
    main()
```

## 🎯 メリット

1. **実行安定性**: パス問題の根本解決
2. **メンテナンス性**: シンプルな構造
3. **開発効率**: 直感的なモジュール構造
4. **デプロイ容易性**: 依存関係の明確化

## 📋 実行手順

### 即座に使える現在の方法
```powershell
# 推奨実行方法
.\run.ps1 --env prd     # 本番環境
.\run.ps1 --env dev     # 開発環境

# 手動実行（同等）
streamlit run app.py --server.port 8401
```

### 将来の改善実装
1. モジュール名の段階的変更
2. 設定ファイルの外部化
3. テストの整備
4. ドキュメントの更新

## 💡 推奨事項

**当面は現在の修正版で安定運用**
- `app.py`ベースの実行は十分安定
- 必要に応じて段階的に改善

**本格改善は開発余裕がある時に**
- 現在の動作に問題なし
- 改善はメンテナンス性向上が主目的 