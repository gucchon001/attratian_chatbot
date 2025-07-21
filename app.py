"""
仕様書作成支援ボット - メインアプリケーション v2.0

新しいディレクトリ構造に対応したエントリーポイントです。

Usage:
    streamlit run app.py
    
New Structure:
    spec_bot/         # メインモジュール（旧src/spec_bot_mvp）
    config/           # 設定ファイル
"""

import sys
import os
from pathlib import Path

# プロジェクトルートを確実にPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from src.spec_bot.ui.streamlit_app import main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"モジュールのインポートに失敗しました: {e}")
    print("必要な依存関係がインストールされているか確認してください:")
    print("pip install -r requirements.txt")
    print(f"現在のPython Path: {sys.path}")
    sys.exit(1)
except Exception as e:
    print(f"アプリケーションの起動に失敗しました: {e}")
    sys.exit(1) 