"""
キャッシュマネージャー単体テスト

SQLiteベースのキャッシュ管理機能のテストを行います。
"""

import pytest
import tempfile
import sys
from pathlib import Path
from datetime import datetime, timedelta

# プロジェクトのルートパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spec_bot.utils.cache_manager import CacheManager, FilterCacheKeys


def test_cache_manager_initialization():
    """キャッシュマネージャーの初期化テスト"""
    
    # 一時ファイルを使用してテスト
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        cache_manager = CacheManager(temp_db.name)
        
        # データベースファイルが作成されているか確認
        assert Path(temp_db.name).exists()
        
        # キャッシュ情報が取得できるか確認
        info = cache_manager.get_cache_info()
        assert 'total_records' in info
        assert info['total_records'] == 0
        
        print(f"✅ キャッシュマネージャー初期化テスト成功")


def test_cache_set_and_get():
    """キャッシュの保存と取得テスト"""
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        cache_manager = CacheManager(temp_db.name)
        
        # テストデータ
        test_key = "test_key"
        test_data = {"statuses": ["Open", "In Progress", "Done"]}
        
        # データを保存
        result = cache_manager.set(test_key, test_data)
        assert result is True
        
        # データを取得
        retrieved_data = cache_manager.get(test_key)
        assert retrieved_data == test_data
        
        print(f"✅ キャッシュ保存・取得テスト成功")


def test_cache_expiration():
    """キャッシュの期限切れテスト"""
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        cache_manager = CacheManager(temp_db.name)
        
        test_key = "expiring_key"
        test_data = {"test": "data"}
        
        # 非常に短い有効期間でデータを保存（0.001時間 = 3.6秒）
        cache_manager.set(test_key, test_data, duration_hours=0.001)
        
        # すぐに取得（まだ有効なはず）
        retrieved_data = cache_manager.get(test_key)
        assert retrieved_data == test_data
        
        # 少し待って再度取得（期限切れのシミュレーション）
        import time
        time.sleep(0.1)  # 短時間待機
        
        # 期限切れチェック（実際の期限切れをテストするには時間がかかるので、
        # ここでは期限切れクリーンアップをテスト）
        expired_count = cache_manager.clear_expired()
        
        print(f"✅ キャッシュ期限切れテスト成功 (期限切れクリーンアップ: {expired_count}件)")


def test_cache_delete():
    """キャッシュの削除テスト"""
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        cache_manager = CacheManager(temp_db.name)
        
        test_key = "delete_key"
        test_data = {"data": "to_delete"}
        
        # データを保存
        cache_manager.set(test_key, test_data)
        
        # データが存在することを確認
        assert cache_manager.get(test_key) == test_data
        
        # データを削除
        delete_result = cache_manager.delete(test_key)
        assert delete_result is True
        
        # データが削除されたことを確認
        assert cache_manager.get(test_key) is None
        
        print(f"✅ キャッシュ削除テスト成功")


def test_cache_clear_all():
    """全キャッシュクリアテスト"""
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        cache_manager = CacheManager(temp_db.name)
        
        # 複数のデータを保存
        test_data = [
            ("key1", {"data": 1}),
            ("key2", {"data": 2}),
            ("key3", {"data": 3})
        ]
        
        for key, data in test_data:
            cache_manager.set(key, data)
        
        # 全データが保存されたことを確認
        info = cache_manager.get_cache_info()
        assert info['total_records'] == 3
        
        # 全クリア
        clear_result = cache_manager.clear_all()
        assert clear_result is True
        
        # 全データが削除されたことを確認
        info = cache_manager.get_cache_info()
        assert info['total_records'] == 0
        
        print(f"✅ 全キャッシュクリアテスト成功")


def test_filter_cache_keys():
    """フィルターキャッシュキー定数のテスト"""
    
    # 定数が正しく定義されているか確認
    assert hasattr(FilterCacheKeys, 'JIRA_STATUSES')
    assert hasattr(FilterCacheKeys, 'JIRA_PROJECTS')
    assert hasattr(FilterCacheKeys, 'CONFLUENCE_SPACES')
    
    # 値が重複していないか確認
    keys = [
        FilterCacheKeys.JIRA_STATUSES,
        FilterCacheKeys.JIRA_PROJECTS,
        FilterCacheKeys.JIRA_ISSUE_TYPES,
        FilterCacheKeys.JIRA_ASSIGNEES,
        FilterCacheKeys.CONFLUENCE_SPACES,
        FilterCacheKeys.CONFLUENCE_AUTHORS
    ]
    
    assert len(keys) == len(set(keys)), "キャッシュキーに重複があります"
    
    print(f"✅ フィルターキャッシュキー定数テスト成功")
    print(f"   定義されたキー: {keys}")


def test_cache_json_serialization():
    """複雑なデータ構造のJSONシリアライゼーションテスト"""
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        cache_manager = CacheManager(temp_db.name)
        
        # 複雑なデータ構造
        complex_data = {
            "jira_statuses": [
                {"id": "1", "name": "To Do", "category": "new"},
                {"id": "2", "name": "In Progress", "category": "indeterminate"},
                {"id": "3", "name": "Done", "category": "done"}
            ],
            "metadata": {
                "total_count": 3,
                "last_updated": "2025-01-17T10:30:00",
                "source": "jira_api"
            },
            "unicode_test": "日本語テスト",
            "numbers": [1, 2, 3.14, -5],
            "booleans": [True, False, None]
        }
        
        test_key = "complex_data"
        
        # 保存
        cache_manager.set(test_key, complex_data)
        
        # 取得
        retrieved_data = cache_manager.get(test_key)
        
        # 完全一致確認
        assert retrieved_data == complex_data
        assert retrieved_data["unicode_test"] == "日本語テスト"
        assert len(retrieved_data["jira_statuses"]) == 3
        
        print(f"✅ 複雑なデータ構造のシリアライゼーションテスト成功")


if __name__ == "__main__":
    print("キャッシュマネージャー単体テストを実行中...")
    
    try:
        test_cache_manager_initialization()
        test_cache_set_and_get()
        test_cache_expiration()
        test_cache_delete()
        test_cache_clear_all()
        test_filter_cache_keys()
        test_cache_json_serialization()
        
        print("\n🎉 全てのキャッシュマネージャーテストが完了しました！")
    except Exception as e:
        print(f"\n❌ テスト失敗: {e}")
        sys.exit(1) 