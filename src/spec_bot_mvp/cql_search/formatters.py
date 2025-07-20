"""
CQL検索結果フォーマッター

検索結果とプロセス情報を人間が読みやすい形式に変換。
"""

from typing import List, Dict, Any
from .engine import SearchResult, SearchStep


class CQLResultFormatter:
    """CQL検索結果フォーマッター"""
    
    def format_detailed_process(self, result: SearchResult) -> str:
        """
        詳細プロセス情報をフォーマット
        
        Args:
            result: 検索結果
            
        Returns:
            フォーマットされた詳細プロセス文字列
        """
        lines = []
        lines.append("🔍 **CQL検索詳細プロセス**")
        lines.append("=" * 50)
        
        # 全体サマリー
        lines.append(f"📊 **総実行時間**: {result.total_time:.2f}秒")
        lines.append(f"📊 **総結果件数**: {result.total_results}件")
        lines.append("")
        
        # 各ステップの詳細
        for step in result.steps:
            lines.append(f"🔍 **Step {step.step_number}: {step.strategy_name}**")
            lines.append(f"   📝 入力クエリ: '{step.query}'")
            
            if step.keywords:
                lines.append(f"   🔤 抽出キーワード: {step.keywords}")
            
            for cql in step.cql_queries:
                lines.append(f"   📝 {cql}")
            
            if step.error:
                lines.append(f"   ❌ エラー: {step.error}")
            else:
                lines.append(f"   📊 結果: {step.results_count}件")
            
            lines.append(f"   ⏱️ 実行時間: {step.execution_time:.2f}秒")
            lines.append("")
        
        # 戦略別サマリー
        lines.append("🎯 **戦略別結果**")
        for strategy, count in result.strategy_breakdown.items():
            lines.append(f"   {strategy}: {count}件")
        
        return "\n".join(lines)
    
    def format_compact_process(self, result: SearchResult) -> List[str]:
        """
        コンパクトなプロセス情報をリスト形式で返す（UI表示用）
        
        Args:
            result: 検索結果
            
        Returns:
            プロセス情報のリスト
        """
        messages = []
        
        # 開始メッセージ
        messages.append("🔍 CQL検索開始")
        
        # 各ステップ
        for step in result.steps:
            if step.keywords:
                messages.append(f"🔤 キーワード抽出: {step.keywords}")
            
            for cql in step.cql_queries:
                messages.append(f"📝 {cql}")
            
            if step.error:
                messages.append(f"❌ {step.strategy_name}: エラー")
            else:
                messages.append(f"📊 {step.strategy_name}: {step.results_count}件")
        
        # 完了メッセージ
        messages.append(f"✅ 検索完了: {result.total_results}件 ({result.total_time:.1f}秒)")
        
        return messages
    
    def format_summary(self, result: SearchResult) -> str:
        """
        検索結果のサマリーをフォーマット
        
        Args:
            result: 検索結果
            
        Returns:
            サマリー文字列
        """
        strategy_summary = ", ".join([
            f"{k}: {v}件" for k, v in result.strategy_breakdown.items() if v > 0
        ])
        
        return (
            f"🎯 CQL検索完了: {result.total_results}件 | "
            f"実行時間: {result.total_time:.1f}秒 | "
            f"戦略別結果: {strategy_summary}"
        )


class ProcessMessageFormatter:
    """プロセスメッセージのフォーマッター（UI統合用）"""
    
    def create_realtime_messages(self, result: SearchResult) -> List[Dict[str, str]]:
        """
        リアルタイム表示用のメッセージを生成
        
        Args:
            result: 検索結果
            
        Returns:
            タイムスタンプ付きメッセージのリスト
        """
        import datetime
        
        messages = []
        base_time = datetime.datetime.now()
        
        for i, step in enumerate(result.steps):
            timestamp = (base_time + datetime.timedelta(seconds=i*2)).strftime("%H:%M:%S")
            
            # ステップ開始
            messages.append({
                "time": timestamp,
                "message": f"🔍 Step {step.step_number}: {step.strategy_name}開始",
                "level": "info"
            })
            
            # キーワード情報
            if step.keywords:
                messages.append({
                    "time": timestamp,
                    "message": f"🔤 キーワード抽出: {step.keywords}",
                    "level": "info"
                })
            
            # CQLクエリ
            for cql in step.cql_queries:
                messages.append({
                    "time": timestamp,
                    "message": f"📝 {cql}",
                    "level": "info"
                })
            
            # 結果
            if step.error:
                messages.append({
                    "time": timestamp,
                    "message": f"❌ エラー: {step.error}",
                    "level": "error"
                })
            else:
                messages.append({
                    "time": timestamp,
                    "message": f"📊 結果: {step.results_count}件",
                    "level": "success"
                })
        
        # 最終結果
        final_time = (base_time + datetime.timedelta(seconds=len(result.steps)*2)).strftime("%H:%M:%S")
        messages.append({
            "time": final_time,
            "message": f"✅ 検索完了: {result.total_results}件 ({result.total_time:.1f}秒)",
            "level": "success"
        })
        
        return messages 

class StreamlitSearchFormatter:
    """Streamlit向けの検索結果フォーマッター"""
    
    def format_search_result(self, result: SearchResult) -> str:
        """
        Streamlit表示用に検索結果をフォーマット
        
        Args:
            result: 検索結果
            
        Returns:
            Streamlit表示用フォーマット文字列
        """
        lines = []
        
        # 検索結果サマリー
        lines.append(f"## 🔍 検索結果: {result.total_results}件")
        lines.append("")
        
        if result.total_results > 0:
            lines.append(f"**実行時間**: {result.total_time:.2f}秒")
            lines.append("")
            
            # 戦略別結果件数
            lines.append("### 📊 戦略別結果")
            for strategy, count in result.strategy_breakdown.items():
                lines.append(f"- **{strategy}**: {count}件")
            lines.append("")
            
            # 上位結果の表示
            lines.append("### 📄 検索結果")
            for i, item in enumerate(result.results[:5], 1):  # 上位5件
                title = item.get('title', '無題')
                url = item.get('_links', {}).get('webui', '#')
                
                lines.append(f"**{i}. [{title}]({url})**")
                
                # 内容の一部を表示
                excerpt = item.get('excerpt', '').strip()
                if excerpt:
                    # HTMLタグを除去して表示
                    import re
                    clean_excerpt = re.sub(r'<[^>]+>', '', excerpt)
                    if len(clean_excerpt) > 100:
                        clean_excerpt = clean_excerpt[:100] + "..."
                    lines.append(f"   - {clean_excerpt}")
                lines.append("")
        else:
            lines.append("検索結果が見つかりませんでした。")
        
        return "\n".join(lines) 