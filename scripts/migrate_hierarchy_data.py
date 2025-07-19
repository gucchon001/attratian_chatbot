#!/usr/bin/env python3
"""
Confluence階層データ移行スクリプト

既存のJSONファイルを新しいConfluenceHierarchyManager構造に移行し、
削除ページの検出・カウント・フィルタリング機能を追加する。

使用方法:
    python scripts/migrate_hierarchy_data.py
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# プロジェクトルートを追加
sys.path.append(str(Path(__file__).parent.parent))

from src.spec_bot_mvp.utils.confluence_hierarchy_manager import ConfluenceHierarchyManager


def migrate_existing_json():
    """既存のJSONファイルを新構造に移行"""
    
    print("🚀 Confluence階層データ移行を開始します...")
    
    # 既存ファイルのパス
    old_json_files = [
        "confluence_hierarchy_20250717_162759.json",
        "confluence_structure_20250717_161346.txt"
    ]
    
    manager = ConfluenceHierarchyManager()
    
    # 既存JSONファイルを探す
    source_file = None
    for filename in old_json_files:
        if os.path.exists(filename):
            source_file = filename
            break
    
    if not source_file:
        print("❌ 既存のJSONファイルが見つかりません")
        return False
    
    print(f"📄 既存ファイルを移行: {source_file}")
    
    try:
        # 既存データを読み込み
        with open(source_file, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        
        print(f"✅ 既存データ読み込み完了")
        print(f"   - 総ページ数: {old_data.get('total_pages', '不明')}")
        print(f"   - 生成日時: {old_data.get('generated_at', '不明')}")
        
        # 削除ページ数をカウント
        folders = old_data.get('folders', [])
        deleted_count = manager.count_deleted_pages(folders)
        
        print(f"🗑️ 削除・廃止ページ検出: {deleted_count}件")
        
        # 新しい構造でデータを再構築
        new_data = {
            "space_name": old_data.get('space_name', 'client-tomonokai-juku'),
            "space_key": old_data.get('space_key', 'CLIENTTOMO'),
            "generated_at": datetime.now().isoformat(),
            "total_pages": old_data.get('total_pages', len(manager._count_all_pages(folders))),
            "deleted_pages_count": deleted_count,
            "version": manager.version,
            "folders": folders
        }
        
        # 新構造で保存
        if manager.save_hierarchy_data(new_data):
            print(f"✅ 新構造でのデータ保存完了")
            print(f"   - 保存先: {manager.hierarchy_file}")
            print(f"   - バックアップ: {manager.backup_file}")
            print(f"   - メタデータ: {manager.metadata_file}")
            
            # 統計情報表示
            stats = manager.get_hierarchy_stats()
            print(f"\n📊 移行後統計:")
            print(f"   - 総ページ数: {stats.get('total_pages', 0)}")
            print(f"   - 削除ページ数: {stats.get('deleted_pages_count', 0)}")
            print(f"   - ファイルサイズ: {stats.get('file_size', 0):,} bytes")
            print(f"   - バックアップ存在: {stats.get('backup_exists', False)}")
            
            return True
        else:
            print("❌ データ保存に失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ 移行中にエラーが発生: {e}")
        return False


def test_hierarchy_functions():
    """階層フィルター機能のテスト"""
    
    print("\n🧪 階層フィルター機能テストを開始...")
    
    manager = ConfluenceHierarchyManager()
    
    # データ読み込みテスト
    print("\n1. データ読み込みテスト")
    data_normal = manager.load_hierarchy_data(include_deleted=False)
    data_with_deleted = manager.load_hierarchy_data(include_deleted=True)
    
    if data_normal and data_with_deleted:
        print("✅ データ読み込み成功")
        
        # 削除ページフィルタリングテスト
        normal_count = len(manager._count_all_pages(data_normal.get('folders', [])))
        deleted_count = len(manager._count_all_pages(data_with_deleted.get('folders', [])))
        
        print(f"   - 通常ページ数: {normal_count}")
        print(f"   - 削除ページ含む: {deleted_count}")
        print(f"   - 削除ページ数: {deleted_count - normal_count}")
    else:
        print("❌ データ読み込み失敗")
        return False
    
    # 更新チェックテスト
    print("\n2. 更新チェックテスト")
    should_update, reason = manager.should_update()
    print(f"   - 更新要否: {should_update}")
    print(f"   - 理由: {reason}")
    
    # 統計情報テスト
    print("\n3. 統計情報テスト")
    stats = manager.get_hierarchy_stats()
    for key, value in stats.items():
        print(f"   - {key}: {value}")
    
    print("\n✅ 全テスト完了")
    return True


def main():
    """メイン実行関数"""
    print("=" * 60)
    print("🏗️  Confluence階層データ移行 & テスト")
    print("=" * 60)
    
    # Step 1: 既存データ移行
    if migrate_existing_json():
        print("\n✅ 移行完了")
    else:
        print("\n❌ 移行失敗")
        return
    
    # Step 2: 機能テスト
    if test_hierarchy_functions():
        print("\n🎉 移行とテストがすべて正常に完了しました！")
    else:
        print("\n⚠️ 一部のテストで問題が発生しました")


if __name__ == "__main__":
    main() 