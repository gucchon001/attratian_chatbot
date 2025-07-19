"""
テスト用Confluenceインデックス構築スクリプト

最近の検索結果を使って小規模なテストインデックスを構築します。
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.spec_bot_mvp.tools.confluence_indexer import ConfluenceIndexer
from src.spec_bot_mvp.tools.confluence_tool import search_confluence_tool
from src.spec_bot_mvp.config.settings import settings
from src.spec_bot_mvp.utils.log_config import get_logger

logger = get_logger(__name__)

def create_test_index():
    """テスト用インデックスを作成"""
    print("🧪 テスト用Confluenceインデックスを構築中...")
    
    # サンプルページデータを作成
    test_data = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'space_key': 'TEST',
            'total_pages': 5,
            'last_update': datetime.now().isoformat(),
            'version': '2.0',
            'format': 'compressed_json',
            'compression_ratio': 0.0
        },
        'pages': {
            'page_1': {
                'id': 'page_1',
                'title': 'API設計仕様書 - 認証機能',
                'type': 'page',
                'space': 'TEST',
                'url': 'https://test.example.com/page_1',
                'created': '2025-01-18T01:00:00Z',
                'updated': '2025-01-18T01:00:00Z',
                'content_preview': 'このドキュメントでは、システムの認証機能に関するAPI設計仕様を説明します。ログイン処理、セッション管理、トークン認証について詳細に記載されています。',
                'labels': ['API', '認証', '設計書', 'セキュリティ']
            },
            'page_2': {
                'id': 'page_2',
                'title': 'データベース設計ドキュメント',
                'type': 'page',
                'space': 'TEST',
                'url': 'https://test.example.com/page_2',
                'created': '2025-01-18T01:00:00Z',
                'updated': '2025-01-18T01:00:00Z',
                'content_preview': 'データベーススキーマ設計とテーブル構造について説明します。ユーザーテーブル、権限テーブル、セッションテーブルの詳細設計を含みます。',
                'labels': ['データベース', '設計', 'スキーマ', 'テーブル']
            },
            'page_3': {
                'id': 'page_3',
                'title': 'セキュリティガイドライン',
                'type': 'page',
                'space': 'TEST',
                'url': 'https://test.example.com/page_3',
                'created': '2025-01-18T01:00:00Z',
                'updated': '2025-01-18T01:00:00Z',
                'content_preview': 'システムセキュリティに関するガイドラインです。パスワードポリシー、アクセス制御、データ暗号化の基準を定義しています。',
                'labels': ['セキュリティ', 'ガイドライン', 'パスワード', '暗号化']
            },
            'page_4': {
                'id': 'page_4',
                'title': 'デプロイ手順書',
                'type': 'page',
                'space': 'TEST',
                'url': 'https://test.example.com/page_4',
                'created': '2025-01-18T01:00:00Z',
                'updated': '2025-01-18T01:00:00Z',
                'content_preview': 'アプリケーションのデプロイ手順について説明します。開発環境、ステージング環境、本番環境へのデプロイプロセスを含みます。',
                'labels': ['デプロイ', '手順', '環境', 'プロセス']
            },
            'page_5': {
                'id': 'page_5',
                'title': 'テスト仕様書 - 統合テスト',
                'type': 'page',
                'space': 'TEST',
                'url': 'https://test.example.com/page_5',
                'created': '2025-01-18T01:00:00Z',
                'updated': '2025-01-18T01:00:00Z',
                'content_preview': '統合テストの仕様について説明します。APIテスト、UIテスト、パフォーマンステストの詳細な手順を記載しています。',
                'labels': ['テスト', '統合テスト', 'API', 'UI', 'パフォーマンス']
            }
        },
        'hierarchy': {},
        'content_map': {},
        'categories': {
            'specifications': ['page_1', 'page_5'],
            'designs': ['page_2'],
            'manuals': ['page_4'],
            'security': ['page_3'],
            'apis': ['page_1'],
            'ui_ux': [],
            'workflows': ['page_4']
        }
    }
    
    # コンテンツマップの生成
    for page_id, page_info in test_data['pages'].items():
        # タイトルと内容からキーワードを抽出
        text = f"{page_info['title']} {page_info['content_preview']}"
        words = text.lower().split()
        
        for word in words:
            if len(word) > 2:  # 2文字以上のワードのみ
                if word not in test_data['content_map']:
                    test_data['content_map'][word] = []
                test_data['content_map'][word].append({
                    'page_id': page_id,
                    'score': 0.8
                })
    
    # インデックサーに保存
    indexer = ConfluenceIndexer()
    indexer.index = test_data
    indexer.save_index()
    
    print("✅ テストインデックス作成完了")
    
    # 圧縮効果の確認
    cache_dir = Path("cache")
    for file_pattern, description in [
        ("confluence_index.json.gz", "圧縮JSON"),
        ("confluence_index.pkl", "キャッシュPickle"),
        ("confluence_index.json", "従来JSON")
    ]:
        file_path = cache_dir / file_pattern
        if file_path.exists():
            size_mb = file_path.stat().st_size / 1024 / 1024
            print(f"  • {description}: {size_mb:.3f}MB")
    
    return True

def test_search_functionality():
    """検索機能のテスト"""
    print("\n🔍 インデックス検索機能テスト")
    print("-" * 30)
    
    indexer = ConfluenceIndexer()
    
    # インデックス読み込み
    if not indexer.load_index():
        print("❌ インデックス読み込み失敗")
        return False
    
    test_queries = ["API", "設計", "セキュリティ", "テスト", "デプロイ"]
    
    for query in test_queries:
        start_time = time.time()
        results = indexer.search_indexed_content(query, max_results=3)
        search_time = time.time() - start_time
        
        print(f"🔎 '{query}': {len(results)}件 ({search_time*1000:.1f}ms)")
        
        for i, result in enumerate(results[:2], 1):
            title = result.get('title', 'タイトルなし')
            score = result.get('relevance_score', 0)
            print(f"  {i}. {title} (関連度: {score:.2f})")
    
    return True

def main():
    """メイン実行関数"""
    print("🚀 テスト用インデックス構築・テスト")
    print("=" * 40)
    
    try:
        # テストインデックス作成
        if create_test_index():
            # 検索機能テスト
            test_search_functionality()
            
            print(f"\n✅ テスト完了")
            print("💡 これで scripts/simple_search_evaluation.py でインデックス検索をテストできます")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        logger.error(f"テストインデックス構築エラー: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 