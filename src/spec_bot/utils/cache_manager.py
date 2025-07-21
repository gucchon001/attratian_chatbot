"""
キャッシュ管理モジュール

SQLiteを使用してフィルター選択肢（Jiraステータス、Confluenceスペース等）を
キャッシュし、パフォーマンスを向上させるクラスを提供します。
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from ..config.settings import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """
    SQLiteベースのキャッシュ管理クラス
    
    フィルター選択肢のデータを一定期間キャッシュし、
    APIコール数を削減してパフォーマンスを向上させます。
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        キャッシュマネージャーを初期化
        
        Args:
            db_path: SQLiteデータベースファイルのパス。Noneの場合はデフォルトパスを使用
        """
        if db_path is None:
            # プロジェクトルートのcacheディレクトリにDBファイルを作成
            cache_dir = Path(__file__).parent.parent.parent.parent / "cache"
            cache_dir.mkdir(exist_ok=True)
            db_path = cache_dir / "filter_cache.db"
        
        self.db_path = str(db_path)
        self.cache_duration_hours = 24  # キャッシュの有効期間（時間）
        
        self._initialize_database()
        logger.info(f"キャッシュマネージャー初期化完了: {self.db_path}")
    
    def _initialize_database(self):
        """データベースとテーブルを初期化"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS filter_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """SQLite接続のコンテキストマネージャー"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 列名でアクセス可能にする
        try:
            yield conn
        finally:
            conn.close()
    
    def get(self, cache_key: str) -> Optional[Any]:
        """
        キャッシュからデータを取得
        
        Args:
            cache_key: キャッシュキー
            
        Returns:
            キャッシュされたデータ。期限切れまたは存在しない場合はNone
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT data, expires_at FROM filter_cache 
                    WHERE cache_key = ? AND expires_at > ?
                """, (cache_key, datetime.now().isoformat()))
                
                row = cursor.fetchone()
                if row:
                    data = json.loads(row['data'])
                    logger.debug(f"キャッシュヒット: {cache_key}")
                    return data
                else:
                    logger.debug(f"キャッシュミス: {cache_key}")
                    return None
                    
        except Exception as e:
            logger.error(f"キャッシュ取得エラー ({cache_key}): {e}")
            return None
    
    def set(self, cache_key: str, data: Any, duration_hours: Optional[int] = None) -> bool:
        """
        データをキャッシュに保存
        
        Args:
            cache_key: キャッシュキー
            data: 保存するデータ
            duration_hours: キャッシュの有効期間（時間）。Noneの場合はデフォルト値を使用
            
        Returns:
            保存に成功した場合True
        """
        try:
            if duration_hours is None:
                duration_hours = self.cache_duration_hours
            
            expires_at = datetime.now() + timedelta(hours=duration_hours)
            data_json = json.dumps(data, ensure_ascii=False)
            
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO filter_cache (cache_key, data, expires_at)
                    VALUES (?, ?, ?)
                """, (cache_key, data_json, expires_at.isoformat()))
                conn.commit()
            
            logger.debug(f"キャッシュ保存完了: {cache_key} (有効期限: {expires_at})")
            return True
            
        except Exception as e:
            logger.error(f"キャッシュ保存エラー ({cache_key}): {e}")
            return False
    
    def delete(self, cache_key: str) -> bool:
        """
        特定のキャッシュを削除
        
        Args:
            cache_key: 削除するキャッシュキー
            
        Returns:
            削除に成功した場合True
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM filter_cache WHERE cache_key = ?", (cache_key,))
                conn.commit()
                
                deleted_count = cursor.rowcount
                logger.debug(f"キャッシュ削除: {cache_key} ({deleted_count}件)")
                return deleted_count > 0
                
        except Exception as e:
            logger.error(f"キャッシュ削除エラー ({cache_key}): {e}")
            return False
    
    def clear_expired(self) -> int:
        """
        期限切れのキャッシュを削除
        
        Returns:
            削除したレコード数
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM filter_cache WHERE expires_at <= ?", 
                                    (datetime.now().isoformat(),))
                conn.commit()
                
                deleted_count = cursor.rowcount
                logger.info(f"期限切れキャッシュ削除: {deleted_count}件")
                return deleted_count
                
        except Exception as e:
            logger.error(f"期限切れキャッシュ削除エラー: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """
        全てのキャッシュを削除
        
        Returns:
            削除に成功した場合True
        """
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM filter_cache")
                conn.commit()
            
            logger.info("全キャッシュクリア完了")
            return True
            
        except Exception as e:
            logger.error(f"全キャッシュクリアエラー: {e}")
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        キャッシュの統計情報を取得
        
        Returns:
            キャッシュ統計情報の辞書
        """
        try:
            with self._get_connection() as conn:
                # 総レコード数
                total_count = conn.execute("SELECT COUNT(*) as count FROM filter_cache").fetchone()['count']
                
                # 有効なレコード数
                valid_count = conn.execute("""
                    SELECT COUNT(*) as count FROM filter_cache 
                    WHERE expires_at > ?
                """, (datetime.now().isoformat(),)).fetchone()['count']
                
                # 期限切れレコード数
                expired_count = total_count - valid_count
                
                return {
                    'total_records': total_count,
                    'valid_records': valid_count,
                    'expired_records': expired_count,
                    'cache_duration_hours': self.cache_duration_hours,
                    'database_path': self.db_path
                }
                
        except Exception as e:
            logger.error(f"キャッシュ情報取得エラー: {e}")
            return {}


class FilterCacheKeys:
    """フィルターキャッシュのキー定数"""
    
    # Jira関連
    JIRA_STATUSES = "jira_statuses"
    JIRA_PROJECTS = "jira_projects"
    JIRA_ISSUE_TYPES = "jira_issue_types"
    JIRA_ASSIGNEES = "jira_assignees"
    
    # Confluence関連
    CONFLUENCE_SPACES = "confluence_spaces"
    CONFLUENCE_AUTHORS = "confluence_authors"


# グローバルキャッシュマネージャーインスタンス
cache_manager = CacheManager() 