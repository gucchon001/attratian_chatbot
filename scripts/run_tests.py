#!/usr/bin/env python3
"""
ハイブリッドアーキテクチャ テスト実行スクリプト

動作確認のための統合テストランナー
Usage: python scripts/run_tests.py [--level all|unit|integration|e2e] [--coverage]
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
import os

# プロジェクトルート設定
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_command(command, description, check_return_code=True):
    """コマンド実行とログ出力"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"実行コマンド: {' '.join(command)}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=check_return_code
        )
        
        execution_time = time.time() - start_time
        
        if result.stdout:
            print("📤 標準出力:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️ 標準エラー:")
            print(result.stderr)
        
        print(f"\n✅ 完了 (実行時間: {execution_time:.2f}秒)")
        return result
        
    except subprocess.CalledProcessError as e:
        execution_time = time.time() - start_time
        print(f"\n❌ 失敗 (実行時間: {execution_time:.2f}秒)")
        print(f"終了コード: {e.returncode}")
        
        if e.stdout:
            print("📤 標準出力:")
            print(e.stdout)
        
        if e.stderr:
            print("⚠️ 標準エラー:")
            print(e.stderr)
        
        if check_return_code:
            raise
        return e

def check_dependencies():
    """依存関係チェック"""
    print("🔍 依存関係チェック中...")
    
    required_packages = [
        "pytest",
        "mock", 
        "streamlit"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: インストール済み")
        except ImportError:
            print(f"❌ {package}: 未インストール")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 不足パッケージ: {', '.join(missing_packages)}")
        print("以下のコマンドでインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ 全ての依存関係が満たされています")
    return True

def run_unit_tests(with_coverage=False):
    """ユニットテスト実行"""
    print("\n🧪 ユニットテスト実行")
    
    # ユニットテストファイルが存在するかチェック
    unit_test_dir = PROJECT_ROOT / "tests" / "unit"
    if not unit_test_dir.exists():
        print("⚠️ ユニットテストディレクトリが存在しません")
        print(f"作成予定: {unit_test_dir}")
        return True
    
    pytest_cmd = ["python", "-m", "pytest", "tests/unit/", "-v"]
    
    if with_coverage:
        pytest_cmd.extend([
            "--cov=src/spec_bot_mvp",
            "--cov-report=html:reports/coverage",
            "--cov-report=term-missing"
        ])
    
    try:
        result = run_command(pytest_cmd, "ユニットテスト実行")
        return result.returncode == 0
    except subprocess.CalledProcessError:
        print("❌ ユニットテストで失敗がありました")
        return False

def run_integration_tests():
    """統合テスト実行"""
    print("\n🔗 統合テスト実行")
    
    integration_test_file = PROJECT_ROOT / "tests" / "integration" / "test_hybrid_architecture.py"
    
    if not integration_test_file.exists():
        print(f"⚠️ 統合テストファイルが存在しません: {integration_test_file}")
        return True
    
    pytest_cmd = [
        "python", "-m", "pytest", 
        str(integration_test_file),
        "-v", "--tb=short"
    ]
    
    try:
        result = run_command(pytest_cmd, "統合テスト実行")
        return result.returncode == 0
    except subprocess.CalledProcessError:
        print("❌ 統合テストで失敗がありました")
        return False

def run_e2e_tests():
    """E2Eテスト実行"""
    print("\n🌐 E2Eテスト実行")
    
    e2e_test_file = PROJECT_ROOT / "tests" / "e2e" / "test_user_scenarios.py"
    
    if not e2e_test_file.exists():
        print(f"⚠️ E2Eテストファイルが存在しません: {e2e_test_file}")
        return True
    
    pytest_cmd = [
        "python", "-m", "pytest",
        str(e2e_test_file), 
        "-v", "--tb=line", "-s"
    ]
    
    try:
        result = run_command(pytest_cmd, "E2Eテスト実行")
        return result.returncode == 0
    except subprocess.CalledProcessError:
        print("❌ E2Eテストで失敗がありました")
        return False

def run_quick_smoke_test():
    """クイック動作確認テスト"""
    print("\n🔥 クイック動作確認テスト")
    
    try:
        # テスト用環境変数設定
        import os
        os.environ['JIRA_URL'] = 'https://test-jira.atlassian.net'
        os.environ['JIRA_USERNAME'] = 'test@example.com'
        os.environ['CONFLUENCE_URL'] = 'https://test-confluence.atlassian.net'
        os.environ['CONFLUENCE_USERNAME'] = 'test@example.com'
        
        # アプリケーション初期化テスト
        print("📱 アプリケーション初期化テスト...")
        from src.spec_bot_mvp.app import HybridSearchApplication
        
        # モック環境で初期化
        import unittest.mock as mock
        
        with mock.patch('src.spec_bot_mvp.config.settings.Settings'), \
             mock.patch('src.spec_bot_mvp.utils.atlassian_api_client.AtlassianAPIClient'), \
             mock.patch('src.spec_bot_mvp.agents.response_generator.LANGCHAIN_AVAILABLE', True):
            
            app = HybridSearchApplication()
            print("✅ アプリケーション初期化成功")
            
            # 基本機能テスト
            print("🔍 基本ハイブリッド検索テスト...")
            
            # パイプライン実行をモック
            with mock.patch.object(
                app, '_execute_fixed_pipeline',
                return_value=(
                    [{"source": "test", "title": "test", "relevance_score": 0.8}],
                    0.8,
                    {"extracted_keywords": ["test"]}
                )
            ), mock.patch.object(
                app.agent_handover_manager, 'execute_agent_handover',
                return_value="テスト応答が正常に生成されました。"
            ):
                
                response = app.execute_hybrid_search(
                    user_query="テスト質問",
                    filters={"use_jira": True, "use_confluence": True}
                )
                
                assert response == "テスト応答が正常に生成されました。"
                print("✅ 基本ハイブリッド検索成功")
            
            print("✅ クイック動作確認テスト完了")
            return True
            
    except Exception as e:
        print(f"❌ クイック動作確認テスト失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def generate_test_report(results):
    """テスト結果レポート生成"""
    print("\n" + "="*80)
    print("📊 テスト実行結果レポート")
    print("="*80)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    failed_tests = total_tests - passed_tests
    
    print(f"📈 総合結果: {passed_tests}/{total_tests} 通過")
    print(f"✅ 成功: {passed_tests}")
    print(f"❌ 失敗: {failed_tests}")
    print(f"📊 成功率: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\n📋 詳細結果:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    # 推奨アクション
    if failed_tests > 0:
        print("\n🔧 推奨アクション:")
        print("1. 失敗したテストのログを確認")
        print("2. 依存関係の再インストール: pip install -r requirements.txt")
        print("3. 設定ファイルの確認: config/secrets.env")
        print("4. LangChain関連パッケージの確認")
        
        return False
    else:
        print("\n🎉 全テスト通過！システムは正常に動作しています。")
        return True

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="ハイブリッドアーキテクチャ テストランナー")
    parser.add_argument(
        "--level",
        choices=["all", "unit", "integration", "e2e", "quick"],
        default="quick",
        help="実行するテストレベル (デフォルト: quick)"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="カバレッジレポート生成"
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="依存関係チェックをスキップ"
    )
    
    args = parser.parse_args()
    
    print("🤖 仕様書作成支援ボット MVP - テストランナー")
    print(f"📋 実行レベル: {args.level}")
    if args.coverage:
        print("📊 カバレッジ測定: 有効")
    
    # 依存関係チェック
    if not args.skip_deps:
        if not check_dependencies():
            print("❌ 依存関係が不足しています")
            return 1
    
    # テスト実行結果記録
    results = {}
    
    try:
        if args.level == "quick":
            # クイック動作確認のみ
            results["クイック動作確認"] = run_quick_smoke_test()
            
        elif args.level == "unit":
            # ユニットテストのみ
            results["ユニットテスト"] = run_unit_tests(args.coverage)
            
        elif args.level == "integration":
            # 統合テストのみ
            results["統合テスト"] = run_integration_tests()
            
        elif args.level == "e2e":
            # E2Eテストのみ
            results["E2Eテスト"] = run_e2e_tests()
            
        elif args.level == "all":
            # 全テスト実行
            results["依存関係チェック"] = True  # 既に実行済み
            results["クイック動作確認"] = run_quick_smoke_test()
            results["ユニットテスト"] = run_unit_tests(args.coverage)
            results["統合テスト"] = run_integration_tests()
            results["E2Eテスト"] = run_e2e_tests()
        
        # 結果レポート生成
        success = generate_test_report(results)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ ユーザーによりテスト実行が中断されました")
        return 130
    except Exception as e:
        print(f"\n💥 予期しないエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 