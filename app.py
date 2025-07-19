"""
仕様書作成支援ボット - メインアプリケーション

Streamlitを使用したチャットボットのエントリーポイントです。

Usage:
    streamlit run app.py
"""

import sys
import os

# srcディレクトリをPythonパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from spec_bot_mvp.ui.streamlit_app import main
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"モジュールのインポートに失敗しました: {e}")
    print("必要な依存関係がインストールされているか確認してください:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"アプリケーションの起動に失敗しました: {e}")
    sys.exit(1) 