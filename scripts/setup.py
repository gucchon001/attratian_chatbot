#!/usr/bin/env python3
"""
開発環境セットアップスクリプト

このスクリプトは、仕様書作成支援ボットの開発環境を自動でセットアップします。
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, check=True):
    """コマンドを実行"""
    print(f"実行中: {command}")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"エラー: {e}")
        if e.stderr:
            print(f"エラー詳細: {e.stderr}")
        return None


def setup_environment():
    """開発環境をセットアップ"""
    print("🚀 仕様書作成支援ボット - 開発環境セットアップを開始します")
    
    # プロジェクトルートに移動
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print(f"📁 プロジェクトディレクトリ: {project_root}")
    
    # 1. 仮想環境の確認/作成
    print("\n1️⃣ 仮想環境の確認...")
    venv_path = project_root / "venv"
    
    if not venv_path.exists():
        print("仮想環境を作成しています...")
        run_command(f"{sys.executable} -m venv venv")
    else:
        print("✅ 仮想環境は既に存在します")
    
    # 2. 依存関係のインストール
    print("\n2️⃣ 依存関係をインストールしています...")
    
    # 仮想環境のPythonパスを取得
    if sys.platform == "win32":
        python_path = venv_path / "Scripts" / "python.exe"
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:
        python_path = venv_path / "bin" / "python"
        pip_path = venv_path / "bin" / "pip"
    
    # 依存関係をインストール
    run_command(f"{pip_path} install --upgrade pip")
    run_command(f"{pip_path} install -r requirements.txt")
    
    # 3. 環境変数ファイルの確認
    print("\n3️⃣ 環境変数ファイルの確認...")
    env_file = project_root / ".env"
    env_example = project_root / "env.example"
    
    if not env_file.exists() and env_example.exists():
        print("環境変数ファイルをコピーしています...")
        run_command(f"cp {env_example} {env_file}")
        print("⚠️  .envファイルを編集してAPIキーを設定してください")
    else:
        print("✅ 環境変数ファイルは既に存在します")
    
    # 4. ディレクトリの作成確認
    print("\n4️⃣ 必要なディレクトリを確認...")
    directories = ["logs", ".streamlit"]
    for directory in directories:
        dir_path = project_root / directory
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            print(f"📁 {directory} ディレクトリを作成しました")
        else:
            print(f"✅ {directory} ディレクトリは既に存在します")
    
    # 5. 設定の検証
    print("\n5️⃣ 設定を検証しています...")
    try:
        # 基本的なインポートテスト
        result = run_command(f"{python_path} -c 'import sys; sys.path.insert(0, \"src\"); from spec_bot_mvp.config.settings import settings; print(\"設定読み込み成功\")'")
        if result and result.returncode == 0:
            print("✅ 基本設定の読み込みに成功しました")
        else:
            print("⚠️  設定の読み込みでエラーが発生しました")
    except Exception as e:
        print(f"⚠️  設定検証中にエラーが発生しました: {e}")
    
    print("\n🎉 セットアップが完了しました！")
    print("\n次のステップ:")
    print("1. .envファイルを編集してAPIキーを設定")
    print("2. 仮想環境を有効化:")
    if sys.platform == "win32":
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("3. アプリケーションを起動:")
    print("   streamlit run app.py")


if __name__ == "__main__":
    setup_environment() 