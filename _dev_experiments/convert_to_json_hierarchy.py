#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Confluenceテキスト構造をJSONの階層構造に変換するスクリプト
"""

import re
import json
import datetime
import os

def parse_confluence_text_to_json(text_file_path):
    """
    Confluenceテキストファイルを階層JSONに変換
    """
    hierarchy = {
        "space_name": "client-tomonokai-juku",
        "space_key": "CLIENTTOMO", 
        "generated_at": datetime.datetime.now().isoformat(),
        "total_pages": 0,
        "folders": []
    }
    
    current_stack = []  # 現在の階層スタック
    
    with open(text_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.rstrip()
        
        # 総ページ数を抽出
        if "総ページ数:" in line:
            match = re.search(r'総ページ数: (\d+)件', line)
            if match:
                hierarchy["total_pages"] = int(match.group(1))
        
        # 階層を示す行をパース
        if '📁' in line or '📄' in line:
            # インデントレベルを計算
            indent_level = (len(line) - len(line.lstrip())) // 2
            
            # ページ情報を抽出
            # 例: 📁 ■要件定義 (page) | 更新: 2023-06-28 03:08
            pattern = r'[📁📄]\s*(.+?)\s*\(page\)(?:\s*\|\s*更新:\s*(.+?))?$'
            match = re.search(pattern, line.strip())
            
            if match:
                page_name = match.group(1).strip()
                updated_date = match.group(2).strip() if match.group(2) else None
                
                # フォルダか通常ページかを判定
                is_folder = '📁' in line
                
                # ページ情報を作成
                page_info = {
                    "name": page_name,
                    "type": "folder" if is_folder else "page",
                    "updated": updated_date,
                    "children": [] if is_folder else None
                }
                
                # IDを抽出（もしあれば）
                id_match = re.search(r'\(ID:\s*(\d+)\)', line)
                if id_match:
                    page_info["id"] = id_match.group(1)
                
                # 階層スタックを調整
                while len(current_stack) > indent_level:
                    current_stack.pop()
                
                # 適切な場所に追加
                if len(current_stack) == 0:
                    # ルートレベル
                    hierarchy["folders"].append(page_info)
                    if is_folder:
                        current_stack.append(page_info)
                else:
                    # 子要素として追加
                    parent = current_stack[-1]
                    if parent.get("children") is not None:
                        parent["children"].append(page_info)
                    
                    if is_folder:
                        current_stack.append(page_info)
    
    return hierarchy

def main():
    # 最新のConfluence構造ファイルを検索
    structure_files = [f for f in os.listdir('.') if f.startswith('confluence_structure_') and f.endswith('.txt')]
    
    if not structure_files:
        print("❌ confluence_structure_*.txt ファイルが見つかりません")
        return
    
    # 最新のファイルを選択
    latest_file = sorted(structure_files)[-1]
    print(f"📄 変換対象ファイル: {latest_file}")
    
    try:
        # JSONに変換
        json_hierarchy = parse_confluence_text_to_json(latest_file)
        
        # JSONファイルに保存
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        json_filename = f'confluence_hierarchy_{timestamp}.json'
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_hierarchy, f, ensure_ascii=False, indent=2)
        
        # 結果表示
        print(f"✅ JSON階層ファイルを作成: {json_filename}")
        print(f"📊 総ページ数: {json_hierarchy['total_pages']}")
        print(f"📁 ルートフォルダ数: {len(json_hierarchy['folders'])}")
        
        # 統計情報
        def count_items(items):
            folder_count = 0
            page_count = 0
            for item in items:
                if item['type'] == 'folder':
                    folder_count += 1
                    if item.get('children'):
                        child_folders, child_pages = count_items(item['children'])
                        folder_count += child_folders
                        page_count += child_pages
                else:
                    page_count += 1
            return folder_count, page_count
        
        total_folders, total_pages = count_items(json_hierarchy['folders'])
        print(f"📁 総フォルダ数: {total_folders}")
        print(f"📄 総ページ数: {total_pages}")
        
        # サンプル階層を表示
        print(f"\n📋 階層プレビュー (先頭3項目):")
        for i, folder in enumerate(json_hierarchy['folders'][:3]):
            print(f"  {i+1}. {folder['name']} ({folder['type']})")
            if folder.get('children'):
                for j, child in enumerate(folder['children'][:2]):
                    print(f"    - {child['name']} ({child['type']})")
                if len(folder['children']) > 2:
                    print(f"    ... (他 {len(folder['children']) - 2} 件)")
        
    except Exception as e:
        print(f"❌ 変換エラー: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 