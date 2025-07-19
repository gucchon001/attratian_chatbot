"""
インデックス化フォーマット パフォーマンステスト
JSON、TXT、Markdown、YAML、その他のフォーマットでのパフォーマンスを比較します。
"""

import json
import yaml
import pickle
import sqlite3
import time
import os
import gzip
import csv
from pathlib import Path
import pandas as pd
from typing import Dict, List, Any
import random
import string

class IndexFormatPerformanceTest:
    """
    インデックスフォーマットのパフォーマンステストクラス
    """
    
    def __init__(self, test_data_size: int = 1000):
        self.test_data_size = test_data_size
        self.test_dir = Path("test_index_formats")
        self.test_dir.mkdir(exist_ok=True)
        self.results = {}
        
    def generate_test_data(self) -> Dict[str, Any]:
        """
        テスト用のConfluenceインデックスデータを生成
        """
        print(f"🔧 {self.test_data_size}ページ分のテストデータを生成中...")
        
        data = {
            'metadata': {
                'created_at': '2025-01-18T01:00:00Z',
                'space_key': 'TEST',
                'total_pages': self.test_data_size,
                'last_update': '2025-01-18T01:00:00Z',
                'version': '1.0'
            },
            'pages': {},
            'hierarchy': {},
            'content_map': {},
            'categories': {
                'specifications': [],
                'designs': [],
                'manuals': [],
                'apis': [],
                'security': [],
                'ui_ux': [],
                'workflows': []
            }
        }
        
        # ページデータ生成
        for i in range(self.test_data_size):
            page_id = f"page_{i}"
            title = f"Test Page {i}: {self._random_title()}"
            content = self._random_content()
            
            data['pages'][page_id] = {
                'id': page_id,
                'title': title,
                'type': 'page',
                'space': 'TEST',
                'url': f"https://test.atlassian.net/wiki/spaces/TEST/pages/{i}",
                'created': '2025-01-18T01:00:00Z',
                'updated': '2025-01-18T01:00:00Z',
                'content_preview': content[:200],
                'labels': [f"label_{j}" for j in range(random.randint(1, 5))]
            }
            
            # 階層構造
            parent_id = f"page_{i//10}" if i > 10 else None
            if parent_id and parent_id in data['pages']:
                data['hierarchy'][page_id] = {
                    'parent_id': parent_id,
                    'children': []
                }
                if parent_id not in data['hierarchy']:
                    data['hierarchy'][parent_id] = {'parent_id': None, 'children': []}
                data['hierarchy'][parent_id]['children'].append(page_id)
            
            # コンテンツマップ
            keywords = content.split()[:10]  # 最初の10単語をキーワードとして使用
            for keyword in keywords:
                if keyword not in data['content_map']:
                    data['content_map'][keyword] = []
                data['content_map'][keyword].append(page_id)
            
            # カテゴリ分類
            category = random.choice(list(data['categories'].keys()))
            data['categories'][category].append(page_id)
        
        return data
    
    def _random_title(self) -> str:
        """ランダムなタイトルを生成"""
        titles = [
            "API設計仕様書", "ユーザーマニュアル", "システム要件定義",
            "データベース設計", "セキュリティガイドライン", "UI/UX設計",
            "テスト仕様書", "デプロイ手順", "運用マニュアル", "障害対応手順"
        ]
        return random.choice(titles)
    
    def _random_content(self) -> str:
        """ランダムなコンテンツを生成"""
        words = ["システム", "ユーザー", "データ", "機能", "設計", "仕様", "要件", 
                "テスト", "開発", "運用", "保守", "セキュリティ", "パフォーマンス",
                "インターフェース", "API", "データベース", "サーバー", "クライアント"]
        return " ".join(random.choices(words, k=100))
    
    def test_json_format(self, data: Dict[str, Any]) -> Dict[str, float]:
        """JSONフォーマットのテスト"""
        print("📝 JSONフォーマットをテスト中...")
        
        # 標準JSON
        json_file = self.test_dir / "index.json"
        
        # 書き込み時間
        start_time = time.time()
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        write_time = time.time() - start_time
        
        # ファイルサイズ
        file_size = json_file.stat().st_size
        
        # 読み込み時間
        start_time = time.time()
        with open(json_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        read_time = time.time() - start_time
        
        # 検索時間（ページ検索）
        start_time = time.time()
        search_results = []
        for page_id, page_info in loaded_data['pages'].items():
            if 'API' in page_info['title']:
                search_results.append(page_id)
        search_time = time.time() - start_time
        
        return {
            'write_time': write_time,
            'read_time': read_time,
            'search_time': search_time,
            'file_size': file_size,
            'search_results': len(search_results)
        }
    
    def test_json_compressed(self, data: Dict[str, Any]) -> Dict[str, float]:
        """圧縮JSONフォーマットのテスト"""
        print("🗜️ 圧縮JSONフォーマットをテスト中...")
        
        json_gz_file = self.test_dir / "index.json.gz"
        
        # 書き込み時間
        start_time = time.time()
        with gzip.open(json_gz_file, 'wt', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        write_time = time.time() - start_time
        
        # ファイルサイズ
        file_size = json_gz_file.stat().st_size
        
        # 読み込み時間
        start_time = time.time()
        with gzip.open(json_gz_file, 'rt', encoding='utf-8') as f:
            loaded_data = json.load(f)
        read_time = time.time() - start_time
        
        # 検索時間
        start_time = time.time()
        search_results = []
        for page_id, page_info in loaded_data['pages'].items():
            if 'API' in page_info['title']:
                search_results.append(page_id)
        search_time = time.time() - start_time
        
        return {
            'write_time': write_time,
            'read_time': read_time,
            'search_time': search_time,
            'file_size': file_size,
            'search_results': len(search_results)
        }
    
    def test_yaml_format(self, data: Dict[str, Any]) -> Dict[str, float]:
        """YAMLフォーマットのテスト"""
        print("📄 YAMLフォーマットをテスト中...")
        
        yaml_file = self.test_dir / "index.yaml"
        
        # 書き込み時間
        start_time = time.time()
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        write_time = time.time() - start_time
        
        # ファイルサイズ
        file_size = yaml_file.stat().st_size
        
        # 読み込み時間
        start_time = time.time()
        with open(yaml_file, 'r', encoding='utf-8') as f:
            loaded_data = yaml.safe_load(f)
        read_time = time.time() - start_time
        
        # 検索時間
        start_time = time.time()
        search_results = []
        for page_id, page_info in loaded_data['pages'].items():
            if 'API' in page_info['title']:
                search_results.append(page_id)
        search_time = time.time() - start_time
        
        return {
            'write_time': write_time,
            'read_time': read_time,
            'search_time': search_time,
            'file_size': file_size,
            'search_results': len(search_results)
        }
    
    def test_pickle_format(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Pickleフォーマットのテスト（バイナリ）"""
        print("🥒 Pickleフォーマットをテスト中...")
        
        pickle_file = self.test_dir / "index.pkl"
        
        # 書き込み時間
        start_time = time.time()
        with open(pickle_file, 'wb') as f:
            pickle.dump(data, f)
        write_time = time.time() - start_time
        
        # ファイルサイズ
        file_size = pickle_file.stat().st_size
        
        # 読み込み時間
        start_time = time.time()
        with open(pickle_file, 'rb') as f:
            loaded_data = pickle.load(f)
        read_time = time.time() - start_time
        
        # 検索時間
        start_time = time.time()
        search_results = []
        for page_id, page_info in loaded_data['pages'].items():
            if 'API' in page_info['title']:
                search_results.append(page_id)
        search_time = time.time() - start_time
        
        return {
            'write_time': write_time,
            'read_time': read_time,
            'search_time': search_time,
            'file_size': file_size,
            'search_results': len(search_results)
        }
    
    def test_sqlite_format(self, data: Dict[str, Any]) -> Dict[str, float]:
        """SQLiteフォーマットのテスト"""
        print("🗄️ SQLiteフォーマットをテスト中...")
        
        sqlite_file = self.test_dir / "index.db"
        
        # 書き込み時間
        start_time = time.time()
        conn = sqlite3.connect(sqlite_file)
        cursor = conn.cursor()
        
        # テーブル作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pages (
                id TEXT PRIMARY KEY,
                title TEXT,
                type TEXT,
                space TEXT,
                url TEXT,
                created TEXT,
                updated TEXT,
                content_preview TEXT,
                labels TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_map (
                keyword TEXT,
                page_id TEXT
            )
        ''')
        
        # データ挿入
        for page_id, page_info in data['pages'].items():
            cursor.execute('''
                INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                page_id,
                page_info['title'],
                page_info['type'],
                page_info['space'],
                page_info['url'],
                page_info['created'],
                page_info['updated'],
                page_info['content_preview'],
                ','.join(page_info['labels'])
            ))
        
        for keyword, page_ids in data['content_map'].items():
            for page_id in page_ids:
                cursor.execute('INSERT INTO content_map VALUES (?, ?)', (keyword, page_id))
        
        conn.commit()
        write_time = time.time() - start_time
        
        # ファイルサイズ
        file_size = sqlite_file.stat().st_size
        
        # 読み込み時間（全データ取得）
        start_time = time.time()
        cursor.execute('SELECT * FROM pages')
        all_pages = cursor.fetchall()
        read_time = time.time() - start_time
        
        # 検索時間（SQL検索）
        start_time = time.time()
        cursor.execute("SELECT id FROM pages WHERE title LIKE '%API%'")
        search_results = cursor.fetchall()
        search_time = time.time() - start_time
        
        conn.close()
        
        return {
            'write_time': write_time,
            'read_time': read_time,
            'search_time': search_time,
            'file_size': file_size,
            'search_results': len(search_results)
        }
    
    def test_csv_format(self, data: Dict[str, Any]) -> Dict[str, float]:
        """CSVフォーマットのテスト"""
        print("📊 CSVフォーマットをテスト中...")
        
        csv_file = self.test_dir / "pages.csv"
        content_map_file = self.test_dir / "content_map.csv"
        
        # 書き込み時間
        start_time = time.time()
        
        # ページデータをCSVに書き込み
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'title', 'type', 'space', 'url', 'created', 'updated', 'content_preview', 'labels'])
            for page_id, page_info in data['pages'].items():
                writer.writerow([
                    page_id,
                    page_info['title'],
                    page_info['type'],
                    page_info['space'],
                    page_info['url'],
                    page_info['created'],
                    page_info['updated'],
                    page_info['content_preview'],
                    ','.join(page_info['labels'])
                ])
        
        # コンテンツマップをCSVに書き込み
        with open(content_map_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['keyword', 'page_id'])
            for keyword, page_ids in data['content_map'].items():
                for page_id in page_ids:
                    writer.writerow([keyword, page_id])
        
        write_time = time.time() - start_time
        
        # ファイルサイズ
        file_size = csv_file.stat().st_size + content_map_file.stat().st_size
        
        # 読み込み時間
        start_time = time.time()
        df_pages = pd.read_csv(csv_file)
        df_content_map = pd.read_csv(content_map_file)
        read_time = time.time() - start_time
        
        # 検索時間
        start_time = time.time()
        search_results = df_pages[df_pages['title'].str.contains('API', na=False)]
        search_time = time.time() - start_time
        
        return {
            'write_time': write_time,
            'read_time': read_time,
            'search_time': search_time,
            'file_size': file_size,
            'search_results': len(search_results)
        }
    
    def run_all_tests(self):
        """すべてのフォーマットテストを実行"""
        print("🚀 インデックスフォーマット パフォーマンステストを開始...")
        print("=" * 60)
        
        # テストデータ生成
        test_data = self.generate_test_data()
        
        # 各フォーマットのテスト実行
        tests = [
            ("JSON", self.test_json_format),
            ("JSON圧縮", self.test_json_compressed),
            ("YAML", self.test_yaml_format),
            ("Pickle", self.test_pickle_format),
            ("SQLite", self.test_sqlite_format),
            ("CSV", self.test_csv_format),
        ]
        
        for format_name, test_func in tests:
            try:
                self.results[format_name] = test_func(test_data)
                print(f"✅ {format_name}テスト完了")
            except Exception as e:
                print(f"❌ {format_name}テストエラー: {e}")
                self.results[format_name] = None
        
        self.generate_report()
    
    def generate_report(self):
        """パフォーマンスレポートを生成"""
        print("\n" + "=" * 60)
        print("📊 パフォーマンステスト結果レポート")
        print("=" * 60)
        
        # ヘッダー
        print(f"{'フォーマット':<10} {'書込時間(s)':<12} {'読込時間(s)':<12} {'検索時間(s)':<12} {'ファイルサイズ(MB)':<15} {'検索結果数':<10}")
        print("-" * 80)
        
        # 結果表示
        for format_name, result in self.results.items():
            if result:
                print(f"{format_name:<10} "
                      f"{result['write_time']:<12.4f} "
                      f"{result['read_time']:<12.4f} "
                      f"{result['search_time']:<12.4f} "
                      f"{result['file_size']/1024/1024:<15.2f} "
                      f"{result['search_results']:<10}")
        
        # 最適フォーマットの推奨
        self.recommend_best_format()
    
    def recommend_best_format(self):
        """最適なフォーマットを推奨"""
        print("\n🎯 推奨フォーマット分析:")
        print("-" * 40)
        
        valid_results = {k: v for k, v in self.results.items() if v is not None}
        
        if not valid_results:
            print("❌ 有効な結果がありません")
            return
        
        # 各指標での最優秀フォーマット
        fastest_write = min(valid_results, key=lambda x: valid_results[x]['write_time'])
        fastest_read = min(valid_results, key=lambda x: valid_results[x]['read_time'])
        fastest_search = min(valid_results, key=lambda x: valid_results[x]['search_time'])
        smallest_size = min(valid_results, key=lambda x: valid_results[x]['file_size'])
        
        print(f"🚀 最速書き込み: {fastest_write} ({valid_results[fastest_write]['write_time']:.4f}s)")
        print(f"📖 最速読み込み: {fastest_read} ({valid_results[fastest_read]['read_time']:.4f}s)")
        print(f"🔍 最速検索: {fastest_search} ({valid_results[fastest_search]['search_time']:.4f}s)")
        print(f"💾 最小サイズ: {smallest_size} ({valid_results[smallest_size]['file_size']/1024/1024:.2f}MB)")
        
        # 総合スコア計算（正規化後の重み付け平均）
        print(f"\n🏆 総合パフォーマンススコア:")
        scores = {}
        for format_name, result in valid_results.items():
            # 各指標を正規化（0-1）し、重み付け
            write_score = 1 / (1 + result['write_time'])  # 小さいほど良い
            read_score = 1 / (1 + result['read_time'])    # 小さいほど良い
            search_score = 1 / (1 + result['search_time']) # 小さいほど良い
            size_score = 1 / (1 + result['file_size']/1024/1024)  # 小さいほど良い
            
            # 重み付け（検索速度を重視）
            total_score = (write_score * 0.2 + read_score * 0.3 + 
                          search_score * 0.4 + size_score * 0.1)
            scores[format_name] = total_score
        
        # スコア順にソート
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        for i, (format_name, score) in enumerate(sorted_scores, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"{medal} {i}. {format_name}: {score:.4f}")
        
        # 推奨事項
        best_format = sorted_scores[0][0]
        print(f"\n✨ 総合推奨フォーマット: {best_format}")
        
        # 用途別推奨
        print(f"\n📋 用途別推奨:")
        print(f"• 頻繁な検索が必要: {fastest_search}")
        print(f"• ストレージ容量重視: {smallest_size}")
        print(f"• 高速読み込み重視: {fastest_read}")
        print(f"• データ更新頻度高: {fastest_write}")


def main():
    """メイン実行関数"""
    print("🔬 Confluenceインデックス フォーマット パフォーマンステスト")
    print("=" * 60)
    
    # テストサイズを選択
    test_sizes = [100, 500, 1000, 2000]
    print("テストデータサイズを選択してください:")
    for i, size in enumerate(test_sizes, 1):
        print(f"{i}. {size}ページ")
    
    try:
        choice = int(input("選択 (1-4): "))
        if 1 <= choice <= len(test_sizes):
            test_size = test_sizes[choice - 1]
        else:
            test_size = 1000
            print("デフォルト: 1000ページ")
    except:
        test_size = 1000
        print("デフォルト: 1000ページ")
    
    # テスト実行
    tester = IndexFormatPerformanceTest(test_size)
    tester.run_all_tests()
    
    # クリーンアップの選択
    cleanup = input("\nテストファイルを削除しますか? (y/N): ").lower()
    if cleanup == 'y':
        import shutil
        shutil.rmtree(tester.test_dir)
        print("🗑️ テストファイルを削除しました")


if __name__ == "__main__":
    main() 