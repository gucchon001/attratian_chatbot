"""
インデックス検索機能 直接テスト
"""

import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 直接インポート
sys.path.append(str(project_root / "src"))

def main():
    try:
        from spec_bot_mvp.tools.confluence_indexer import ConfluenceIndexer
        
        print("🔍 インデックス検索機能 直接テスト")
        print("=" * 40)
        
        # インデックサー初期化
        indexer = ConfluenceIndexer()
        
        # インデックス読み込み
        print("📂 インデックス読み込み中...")
        if not indexer.load_index():
            print("❌ インデックス読み込み失敗")
            return False
        
        print(f"✅ インデックス読み込み成功: {indexer.index['metadata']['total_pages']}ページ")
        
        # 検索テスト
        test_queries = ["API", "設計", "認証", "セキュリティ", "デプロイ"]
        
        print("\n🔎 検索テスト:")
        for query in test_queries:
            start_time = time.time()
            
            # 検索実行
            results = indexer.search_by_keyword(query, max_results=3)
            
            search_time = time.time() - start_time
            
            print(f"\n'{query}': {len(results)}件 ({search_time*1000:.1f}ms)")
            
            for i, result in enumerate(results, 1):
                title = result.get('title', 'タイトルなし')
                score = result.get('relevance_score', 0)
                print(f"  {i}. {title} (関連度: {score:.3f})")
        
        # ファイルサイズ確認
        print(f"\n💾 圧縮効果:")
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
        
        print(f"\n✅ テスト完了")
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main() 