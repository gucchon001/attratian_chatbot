#!/usr/bin/env python3
"""
疎通確認テスト一括実行スクリプト

このスクリプトは、プロジェクトの各種APIとの疎通確認を一括で実行します。
"""

import os
import sys
import subprocess
from pathlib import Path


def run_test(test_path, test_name):
    """個別テストを実行"""
    print(f"\n{'='*60}")
    print(f"🧪 {test_name} を実行中...")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        # 出力を表示
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print(f"エラー出力:\n{result.stderr}")
        
        if result.returncode == 0:
            print(f"✅ {test_name} 成功")
            return True
        else:
            print(f"❌ {test_name} 失敗 (Exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ {test_name} 実行中にエラー: {e}")
        return False


def main():
    """メイン実行関数"""
    print("🚀 仕様書作成支援ボット - 疎通確認テスト一括実行")
    print("=" * 60)
    
    # プロジェクトルートに移動
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # テスト対象の定義
    tests = [
        {
            "path": "tests/integration/test_settings_validation.py",
            "name": "設定管理統合テスト",
            "required": True
        },
        {
            "path": "tests/unit/test_atlassian_connection.py", 
            "name": "Atlassian API疎通確認テスト",
            "required": True
        },
        {
            "path": "tests/unit/test_gemini_connection.py",
            "name": "Gemini API疎通確認テスト", 
            "required": False  # APIキー設定がオプション
        }
    ]
    
    # テスト実行
    results = []
    
    for test in tests:
        test_path = project_root / test["path"]
        
        if not test_path.exists():
            print(f"⚠️  テストファイルが見つかりません: {test_path}")
            results.append(False)
            continue
        
        success = run_test(test_path, test["name"])
        results.append(success)
        
        # 必須テストが失敗した場合は中断
        if test["required"] and not success:
            print(f"\n❌ 必須テスト '{test['name']}' が失敗したため、テストを中断します")
            break
    
    # 結果サマリー
    print(f"\n{'='*60}")
    print("📊 テスト結果サマリー")
    print(f"{'='*60}")
    
    successful_tests = sum(results)
    total_tests = len([t for t in tests if Path(project_root / t["path"]).exists()])
    
    for i, test in enumerate(tests):
        if i < len(results):
            status = "✅ 成功" if results[i] else "❌ 失敗"
            required = "（必須）" if test["required"] else "（オプション）"
            print(f"  {test['name']}: {status} {required}")
    
    print(f"\n成功率: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
    
    # 次のステップの提案
    if successful_tests == total_tests:
        print(f"\n🎉 すべてのテストが成功しました！")
        print("次のステップ:")
        print("1. コア機能（LangChainエージェント）の実装")
        print("2. ツール機能（Jira/Confluence検索）の実装")
        print("3. UI機能（Streamlitチャット）の実装")
    else:
        print(f"\n⚠️  一部のテストが失敗しています。")
        print("設定ファイル（secrets.env）とAPIキーを確認してください。")
    
    print(f"{'='*60}")
    return successful_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 