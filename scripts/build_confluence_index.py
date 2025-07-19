"""
Confluenceインデックス構築スクリプト

Confluenceスペース全体のインデックスを事前構築し、
高速検索を可能にします。
"""

import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.spec_bot_mvp.tools.confluence_indexer import ConfluenceIndexer
from src.spec_bot_mvp.config.settings import settings
from src.spec_bot_mvp.utils.log_config import get_logger

logger = get_logger(__name__)

def main():
    """メイン実行関数"""
    print("🚀 Confluenceインデックス構築を開始...")
    print("=" * 50)
    
    # インデックサーの初期化
    indexer = ConfluenceIndexer()
    
    # 設定確認
    if not settings.confluence_space:
        print("❌ CONFLUENCE_SPACEが設定されていません")
        print("settings.iniまたは環境変数を確認してください")
        return False
    
    print(f"📋 対象スペース: {settings.confluence_space}")
    print(f"🔗 Confluence URL: https://{settings.atlassian_domain}")
    
    # 既存インデックスの確認
    if indexer.is_index_fresh(max_age_hours=24):
        print("ℹ️ 新しいインデックスが既に存在します")
        choice = input("再構築しますか? (y/N): ").strip().lower()
        if choice != 'y':
            print("✅ インデックス構築をキャンセルしました")
            return True
    
    print("\n🔧 インデックス構築を開始...")
    start_time = time.time()
    
    try:
        # フルインデックス構築
        success = indexer.build_full_index(settings.confluence_space)
        
        if success:
            build_time = time.time() - start_time
            
            # 結果表示
            metadata = indexer.index.get('metadata', {})
            total_pages = metadata.get('total_pages', 0)
            compression_ratio = metadata.get('compression_ratio', 0)
            
            print(f"\n✅ インデックス構築完了!")
            print(f"📊 構築結果:")
            print(f"  • 処理ページ数: {total_pages:,}ページ")
            print(f"  • 構築時間: {build_time:.2f}秒")
            print(f"  • 圧縮率: {compression_ratio:.1f}%")
            print(f"  • 平均処理速度: {total_pages/build_time:.1f}ページ/秒")
            
            # インデックスサイズ表示
            cache_dir = Path("cache")
            for file_pattern, description in [
                ("confluence_index.json.gz", "圧縮JSON"),
                ("confluence_index.pkl", "キャッシュPickle"),
                ("confluence_index.json", "従来JSON")
            ]:
                file_path = cache_dir / file_pattern
                if file_path.exists():
                    size_mb = file_path.stat().st_size / 1024 / 1024
                    print(f"  • {description}: {size_mb:.2f}MB")
            
            # テスト検索実行
            print(f"\n🔍 インデックス検索テスト:")
            test_queries = ["API", "設計", "仕様書"]
            
            for query in test_queries:
                test_start = time.time()
                results = indexer.search_indexed_content(query, max_results=3)
                test_time = time.time() - test_start
                
                print(f"  • '{query}': {len(results)}件 ({test_time*1000:.1f}ms)")
            
            return True
            
        else:
            print("❌ インデックス構築に失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ インデックス構築エラー: {e}")
        logger.error(f"インデックス構築エラー: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 