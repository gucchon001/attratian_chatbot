#!/usr/bin/env python3
"""
ログファイル確認スクリプト

仕様書作成支援ボットのログファイルを確認・分析するためのユーティリティです。
"""

import argparse
import os
from pathlib import Path
import re
from datetime import datetime, timedelta


def read_log_file(log_file_path: Path, lines: int = 50):
    """
    ログファイルの末尾から指定行数を読み取る
    
    Args:
        log_file_path: ログファイルのパス
        lines: 読み取る行数
    """
    if not log_file_path.exists():
        print(f"❌ ログファイルが見つかりません: {log_file_path}")
        return
    
    print(f"📄 ログファイル: {log_file_path}")
    print(f"📏 ファイルサイズ: {log_file_path.stat().st_size / 1024:.1f} KB")
    print(f"🕒 最終更新: {datetime.fromtimestamp(log_file_path.stat().st_mtime)}")
    print("=" * 80)
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            
        if not all_lines:
            print("📝 ログファイルは空です")
            return
        
        # 末尾から指定行数を取得
        display_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        print(f"📊 総ログ行数: {len(all_lines)}行")
        print(f"📋 表示行数: {len(display_lines)}行 (末尾から{lines}行)")
        print("-" * 80)
        
        for line in display_lines:
            line = line.rstrip()
            if line:
                # ログレベルに応じて色分け（簡易版）
                if 'ERROR' in line:
                    print(f"🔴 {line}")
                elif 'WARNING' in line:
                    print(f"🟡 {line}")
                elif 'INFO' in line:
                    print(f"🔵 {line}")
                else:
                    print(f"⚪ {line}")
    
    except Exception as e:
        print(f"❌ ログファイル読み取りエラー: {e}")


def analyze_logs(log_file_path: Path, hours: int = 24):
    """
    ログファイルを分析して統計情報を表示
    
    Args:
        log_file_path: ログファイルのパス
        hours: 分析対象の時間（過去N時間）
    """
    if not log_file_path.exists():
        print(f"❌ ログファイルが見つかりません: {log_file_path}")
        return
    
    print(f"📊 ログ分析（過去{hours}時間）")
    print("=" * 80)
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 過去N時間のログを抽出
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_lines = []
        
        # ログの時刻パターン（例: 2024-01-01 12:00:00）
        time_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
        
        for line in lines:
            match = time_pattern.search(line)
            if match:
                try:
                    log_time = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                    if log_time >= cutoff_time:
                        recent_lines.append(line)
                except ValueError:
                    continue
        
        if not recent_lines:
            print(f"📝 過去{hours}時間のログはありません")
            return
        
        # 統計情報を計算
        stats = {
            'total_lines': len(recent_lines),
            'error_count': 0,
            'warning_count': 0,
            'info_count': 0,
            'search_count': 0,
            'user_queries': 0,
            'confluence_searches': 0,
            'jira_searches': 0
        }
        
        search_times = []
        
        for line in recent_lines:
            if 'ERROR' in line:
                stats['error_count'] += 1
            elif 'WARNING' in line:
                stats['warning_count'] += 1
            elif 'INFO' in line:
                stats['info_count'] += 1
            
            if 'ユーザー入力を処理開始' in line:
                stats['user_queries'] += 1
            elif 'Confluence検索実行' in line:
                stats['confluence_searches'] += 1
            elif 'JQL検索実行' in line:
                stats['jira_searches'] += 1
            
            # 実行時間を抽出
            time_match = re.search(r'実行時間[:\s]+(\d+\.?\d*)秒', line)
            if time_match:
                search_times.append(float(time_match.group(1)))
        
        # 結果表示
        print(f"📊 **ログ統計情報**")
        print(f"   • 総ログ行数: {stats['total_lines']:,}行")
        print(f"   • エラー: {stats['error_count']}件")
        print(f"   • 警告: {stats['warning_count']}件")
        print(f"   • 情報: {stats['info_count']}件")
        print()
        print(f"🔍 **検索統計**")
        print(f"   • ユーザー質問: {stats['user_queries']}件")
        print(f"   • Confluence検索: {stats['confluence_searches']}件")
        print(f"   • Jira検索: {stats['jira_searches']}件")
        
        if search_times:
            avg_time = sum(search_times) / len(search_times)
            max_time = max(search_times)
            min_time = min(search_times)
            print()
            print(f"⏱️ **実行時間統計**")
            print(f"   • 平均実行時間: {avg_time:.2f}秒")
            print(f"   • 最大実行時間: {max_time:.2f}秒")
            print(f"   • 最小実行時間: {min_time:.2f}秒")
    
    except Exception as e:
        print(f"❌ ログ分析エラー: {e}")


def main():
    parser = argparse.ArgumentParser(description="仕様書作成支援ボット ログ確認ツール")
    parser.add_argument(
        '--lines', '-n', 
        type=int, 
        default=50, 
        help="表示する行数（デフォルト: 50）"
    )
    parser.add_argument(
        '--analyze', '-a', 
        action='store_true', 
        help="ログを分析して統計情報を表示"
    )
    parser.add_argument(
        '--hours', 
        type=int, 
        default=24, 
        help="分析対象の時間（過去N時間、デフォルト: 24）"
    )
    parser.add_argument(
        '--file', '-f', 
        type=str, 
        help="ログファイルのパス（指定しない場合はデフォルトパスを使用）"
    )
    
    args = parser.parse_args()
    
    # ログファイルパスを決定
    if args.file:
        log_file_path = Path(args.file)
    else:
        # デフォルトパス
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        log_file_path = project_root / "logs" / "spec_bot.log"
    
    if args.analyze:
        analyze_logs(log_file_path, args.hours)
    else:
        read_log_file(log_file_path, args.lines)


if __name__ == "__main__":
    main() 