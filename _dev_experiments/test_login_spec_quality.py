"""
ログイン機能仕様検索 - 出力品質テスト

「ログイン機能の仕様について教えて」という実際的な質問で、
改善版検索システムの出力品質を評価します。
"""

import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from spec_bot.tools.confluence_improved_mock_search import search_confluence_improved_chain
from spec_bot.utils.log_config import setup_logging, get_logger

def analyze_output_quality(response: str) -> dict:
    """出力品質の分析"""
    quality_metrics = {
        "関連ページ特定": 0,  # 0-5点
        "情報統合度": 0,      # 0-5点  
        "構造化": 0,          # 0-5点
        "透明性": 0,          # 0-5点
        "実用性": 0,          # 0-5点
        "総合評価": 0         # 0-5点
    }
    
    response_lower = response.lower()
    
    # 1. 関連ページ特定 (0-5点)
    page_scores = 0
    if "api設計仕様書" in response_lower:
        page_scores += 3  # 最重要ページ
    if "セキュリティガイドライン" in response_lower:
        page_scores += 2  # 関連ページ
    quality_metrics["関連ページ特定"] = min(5, page_scores)
    
    # 2. 情報統合度 (0-5点)
    integration_keywords = ["ログイン処理", "セッション管理", "トークン認証", "パスワードポリシー", "アクセス制御"]
    integration_score = sum(1 for keyword in integration_keywords if keyword in response_lower)
    quality_metrics["情報統合度"] = min(5, integration_score)
    
    # 3. 構造化 (0-5点)
    structure_elements = 0
    if "**" in response or "##" in response:  # 見出し
        structure_elements += 1
    if "1." in response or "2." in response:  # 番号付きリスト
        structure_elements += 1
    if "- " in response or "* " in response:  # 箇条書き
        structure_elements += 1
    if len(response.split('\n')) >= 5:  # 複数段落
        structure_elements += 1
    if "について" in response and "含まれています" in response:  # 要約文
        structure_elements += 1
    quality_metrics["構造化"] = min(5, structure_elements)
    
    # 4. 透明性 (0-5点)
    transparency_score = 0
    if "検索戦略" in response_lower or "戦略" in response_lower:
        transparency_score += 2
    if "マッチ" in response_lower or "キーワード" in response_lower:
        transparency_score += 2
    if "スコア" in response_lower:
        transparency_score += 1
    quality_metrics["透明性"] = min(5, transparency_score)
    
    # 5. 実用性 (0-5点)
    practical_elements = 0
    if "具体的" in response_lower or "詳細" in response_lower:
        practical_elements += 1
    if "設計" in response_lower or "仕様" in response_lower:
        practical_elements += 1
    if "実装" in response_lower or "開発" in response_lower:
        practical_elements += 1
    if len(response) >= 200:  # 十分な情報量
        practical_elements += 1
    if "関連" in response_lower or "密接" in response_lower:
        practical_elements += 1
    quality_metrics["実用性"] = min(5, practical_elements)
    
    # 6. 総合評価 (他の指標の平均)
    other_scores = [quality_metrics[key] for key in quality_metrics if key != "総合評価"]
    quality_metrics["総合評価"] = round(sum(other_scores) / len(other_scores), 1)
    
    return quality_metrics

def test_login_spec_output_quality():
    """ログイン機能仕様検索の出力品質テスト"""
    print("🎯 ログイン機能仕様検索 - 出力品質テスト")
    print("=" * 60)
    
    # ログ設定
    setup_logging(log_level="INFO", enable_file_logging=False)
    
    # テスト質問
    query = "ログイン機能の仕様について教えて"
    print(f"🔍 テスト質問: '{query}'")
    print("-" * 60)
    
    try:
        # 改善版検索実行
        print("🤖 改善版検索システムで検索中...")
        response = search_confluence_improved_chain(query)
        
        print("📄 **実際の出力:**")
        print("=" * 40)
        print(response)
        print("=" * 40)
        
        # 出力品質分析
        quality_metrics = analyze_output_quality(response)
        
        print(f"\n📊 **出力品質分析結果:**")
        print("-" * 40)
        for metric_name, score in quality_metrics.items():
            stars = "★" * int(score) + "☆" * (5 - int(score))
            print(f"{metric_name}: {score}/5 {stars}")
        
        # 品質判定
        total_score = quality_metrics["総合評価"]
        if total_score >= 4.5:
            quality_level = "🏆 最高品質"
            color = "🟢"
        elif total_score >= 3.5:
            quality_level = "🥇 高品質"
            color = "🟡"
        elif total_score >= 2.5:
            quality_level = "🥈 中品質"
            color = "🟠"
        else:
            quality_level = "🥉 要改善"
            color = "🔴"
        
        print(f"\n{color} **総合判定: {quality_level}** (総合スコア: {total_score}/5)")
        
        # 改善提案
        print(f"\n💡 **改善提案:**")
        low_scores = [name for name, score in quality_metrics.items() if score < 3 and name != "総合評価"]
        if low_scores:
            for low_metric in low_scores:
                if low_metric == "関連ページ特定":
                    print("   - 関連語辞書の拡充（ログイン→認証→セキュリティの関連性強化）")
                elif low_metric == "情報統合度":
                    print("   - 複数ページからの情報統合アルゴリズム改善")
                elif low_metric == "構造化":
                    print("   - 出力フォーマットテンプレートの改善")
                elif low_metric == "透明性":
                    print("   - 検索過程の詳細表示機能追加")
                elif low_metric == "実用性":
                    print("   - より具体的で実装に役立つ情報の抽出強化")
        else:
            print("   - 全指標が良好です！素晴らしい出力品質です。")
        
        # 理想的な出力例の提示
        print(f"\n📋 **理想的な出力例:**")
        print("-" * 40)
        print(show_ideal_output_example())
        
    except Exception as e:
        print(f"❌ テストエラー: {str(e)}")

def show_ideal_output_example() -> str:
    """理想的な出力例を返す"""
    return """「ログイン機能の仕様について教えて」について以下の情報が見つかりました (検索戦略: improved_related_terms_search)：

**1. API設計仕様書 - 認証機能** (戦略: related_terms_search, マッチ: 6件)
   マッチキーワード: title:認証, content:ログイン, content:セッション, label:API, label:セキュリティ
   このドキュメントでは、システムの認証機能に関するAPI設計仕様を説明します。ログイン処理、セッション管理、トークン認証について詳細に記載されており、具体的な実装方法とセキュリティ要件が含まれています...

**2. セキュリティガイドライン** (戦略: related_terms_search, マッチ: 4件)
   マッチキーワード: title:セキュリティ, content:パスワード, content:アクセス制御, label:ガイドライン
   システムセキュリティに関するガイドラインです。パスワードポリシー、アクセス制御、データ暗号化の基準を定義しており、ログイン機能のセキュリティ要件と密接に関連しています...

**統合された仕様要約:**
ログイン機能は認証APIとセキュリティガイドラインの両方で規定されており、技術実装とセキュリティポリシーの両面から詳細に設計されています。"""

if __name__ == "__main__":
    test_login_spec_output_quality() 