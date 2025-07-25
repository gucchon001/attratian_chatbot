"""
仕様書作成支援ボット - 統合版メインアプリケーション v3.0

統合版spec_bot_mvpのエントリーポイントです。
実データ統合、思考プロセス可視化、実行時間測定機能を含みます。

Usage:
    streamlit run app.py --server.port 8402
    
Structure:
    spec_bot_mvp/     # 統合版メインモジュール
    config/           # 設定ファイル（settings.ini, secrets.env）
"""

import sys
import os
from pathlib import Path

# プロジェクトルートを確実にPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # 統合版のstreamlit_app_integratedをインポート
    from src.spec_bot_mvp.ui.streamlit_app_integrated import main
    
    if __name__ == "__main__":
        print("🚀 統合版仕様書作成支援ボット起動中...")
        print("📊 実データ統合機能: ✅")
        print("🧠 思考プロセス可視化: ✅") 
        print("⏱️ 実行時間測定: ✅")
        main()
        
except ImportError as e:
    print(f"❌ 統合版モジュールのインポートに失敗しました: {e}")
    print("必要な依存関係がインストールされているか確認してください:")
    print("pip install -r requirements.txt")
    print(f"現在のPython Path: {sys.path}")
    sys.exit(1)
except Exception as e:
    print(f"❌ 統合版アプリケーションの起動に失敗しました: {e}")
    sys.exit(1) 