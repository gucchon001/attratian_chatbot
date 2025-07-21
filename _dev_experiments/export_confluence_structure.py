#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Confluenceスペース構造をファイルに出力するスクリプト
"""

from spec_bot.tools.confluence_tool import get_confluence_space_structure
import datetime
import os

def main():
    print('CLIENTTOMOスペース構造を取得中...')
    
    try:
        # スペース構造を取得
        result = get_confluence_space_structure('CLIENTTOMO')
        
        if not result or len(result.strip()) == 0:
            print('エラー: 構造データが取得できませんでした')
            return
        
        # タイムスタンプ付きファイル名
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'confluence_structure_{timestamp}.txt'
        
        # ファイルに保存
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('=' * 80 + '\n')
            f.write('CLIENTTOMO Confluenceスペース構造\n')
            f.write(f'取得日時: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write('=' * 80 + '\n\n')
            f.write(result)
        
        # 結果を表示
        file_size = os.path.getsize(filename)
        print(f'✅ 構造をファイルに保存しました: {filename}')
        print(f'📄 ファイルサイズ: {file_size} バイト')
        print(f'📝 データ長: {len(result)} 文字')
        
        # 先頭部分をプレビュー
        lines = result.split('\n')
        print(f'\n📋 構造プレビュー (先頭10行):')
        for i, line in enumerate(lines[:10]):
            print(f'  {i+1:2d}: {line}')
        
        if len(lines) > 10:
            print(f'  ... (他 {len(lines) - 10} 行)')
            
    except Exception as e:
        print(f'❌ エラーが発生しました: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main() 