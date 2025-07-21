"""
Jira検索ツール

JQLクエリを使用してJiraチケットを検索し、LangChainエージェントが利用可能な
構造化された結果を返すツールを提供します。
"""

import logging
import time
from typing import Optional, List, Dict, Any
from atlassian import Jira

from ..config.settings import settings
from ..utils.cache_manager import CacheManager
from ..utils.log_config import get_logger, log_search_results

logger = get_logger(__name__)
cache_manager = CacheManager()


def get_jira_filter_options() -> Dict[str, Any]:
    """
    Jira APIから現在利用可能なフィルター項目を取得する
    
    Returns:
        Dict[str, Any]: プロジェクト、ステータス、担当者などの情報
    """
    cache_key = "jira_filter_options"
    
    # キャッシュから取得を試行（1時間有効）
    try:
        cached_options = cache_manager.get(cache_key)
        if cached_options:
            logger.info("Jiraフィルター項目をキャッシュから取得")
            return cached_options
    except Exception as e:
        logger.warning(f"キャッシュ取得エラー (キーをクリアします): {str(e)}")
        # キャッシュが破損している場合はクリアして継続
        try:
            cache_manager.delete(cache_key)
        except:
            pass
    
    try:
        # Jira接続の初期化
        jira = Jira(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        
        logger.info("Jira APIからフィルター項目を取得中...")
        
        # 各種フィルター項目を並行して取得（プロジェクトはCTJ固定のため除外）
        filter_options = {
            'statuses': _get_statuses(jira),
            'users': _get_users(jira),
            'issue_types': _get_issue_types(jira),
            'priorities': _get_priorities(jira)
        }
        
        # キャッシュに保存（1時間有効）
        try:
            cache_manager.set(cache_key, filter_options, duration_hours=1)
        except Exception as e:
            logger.warning(f"キャッシュ保存エラー: {str(e)}")
        
        logger.info("Jiraフィルター項目の取得完了")
        return filter_options
        
    except Exception as e:
        logger.error(f"Jiraフィルター項目取得エラー: {str(e)}")
        # エラー時は空の辞書を返す（プロジェクトはCTJ固定のため除外）
        return {
            'statuses': [],
            'users': [],
            'issue_types': [],
            'priorities': []
        }



def _get_statuses(jira: Jira) -> List[str]:
    """ステータス一覧を取得（表示用文字列リスト）"""
    try:
        statuses = jira.get_all_statuses()
        status_list = []
        for status in statuses:
            name = status.get('name', '')
            if name:
                # 表示用: ステータス名のみ（カテゴリ表示は削除）
                status_list.append(name)
        return sorted(list(set(status_list)))  # 重複除去してソート
    except Exception as e:
        logger.warning(f"ステータス取得エラー: {str(e)}")
        return []


def _get_users(jira: Jira) -> List[str]:
    """アクティブなユーザー一覧を取得（表示用文字列リスト）"""
    try:
        # 最近更新されたチケットから担当者を取得する方法
        recent_issues = jira.jql('updated >= -30d', limit=100, fields='assignee')
        users_set = set()
        users_list = []
        
        # データ型検証を追加
        if not isinstance(recent_issues, dict) or 'issues' not in recent_issues:
            logger.warning("Jira JQL結果が期待される形式ではありません")
            return []
        
        for issue in recent_issues.get('issues', []):
            # 各issueが辞書形式かチェック
            if not isinstance(issue, dict):
                continue
                
            fields = issue.get('fields')
            if not isinstance(fields, dict):
                continue
                
            assignee = fields.get('assignee')
            if assignee and isinstance(assignee, dict) and assignee.get('accountId'):
                display_name = assignee.get('displayName', '')
                email = assignee.get('emailAddress', '')
                
                # 表示用: "表示名 (email)" 形式
                if display_name:
                    display_text = f"{display_name} ({email})" if email else display_name
                    if display_text not in users_set:
                        users_set.add(display_text)
                        users_list.append(display_text)
        
        return sorted(users_list[:50])  # 最大50人に制限してソート
    except Exception as e:
        logger.warning(f"ユーザー取得エラー: {str(e)}")
        return []


def _get_issue_types(jira: Jira) -> List[str]:
    """チケットタイプ一覧を取得（表示用文字列リスト）"""
    try:
        # REST APIを直接呼び出し
        response = jira.get('rest/api/2/issuetype')
        if isinstance(response, list):
            type_list = []
            for issue_type in response:
                # 各issue_typeが辞書形式かチェック
                if isinstance(issue_type, dict):
                    name = issue_type.get('name', '')
                    if name:
                        type_list.append(name)
            return sorted(list(set(type_list)))  # 重複除去してソート
        return []
    except Exception as e:
        logger.warning(f"チケットタイプ取得エラー: {str(e)}")
        return []


def _get_priorities(jira: Jira) -> List[str]:
    """優先度一覧を取得（表示用文字列リスト）"""
    try:
        # REST APIを直接呼び出し
        response = jira.get('rest/api/2/priority')
        if isinstance(response, list):
            priority_list = []
            for priority in response:
                # 各priorityが辞書形式かチェック
                if isinstance(priority, dict):
                    name = priority.get('name', '')
                    if name:
                        priority_list.append(name)
            return sorted(list(set(priority_list)))  # 重複除去してソート
        return []
    except Exception as e:
        logger.warning(f"優先度取得エラー: {str(e)}")
        return []


def get_custom_field_options(jira: Jira, project_key: str) -> Dict[str, List[str]]:
    """CTJプロジェクトのカスタムフィールドの選択肢を取得"""
    try:
        # 最新のチケットからカスタムフィールド値を収集
        jql = f'project = "{project_key}" ORDER BY updated DESC'
        result = jira.jql(jql, limit=100, fields='customfield_10277,customfield_10291')
        
        custom_options = {
            'custom_tantou': set(),      # 担当 (customfield_10277)
            'custom_eikyou_gyoumu': set()  # 影響業務 (customfield_10291)
        }
        
        # データ型検証を追加
        if isinstance(result, dict) and 'issues' in result:
            for issue in result['issues']:
                # 各issueが辞書形式かチェック
                if not isinstance(issue, dict):
                    continue
                    
                fields = issue.get('fields')
                if not isinstance(fields, dict):
                    continue
                
                # 担当 (customfield_10277)
                tantou = fields.get('customfield_10277')
                if tantou and isinstance(tantou, dict) and 'value' in tantou:
                    custom_options['custom_tantou'].add(tantou['value'])
                
                # 影響業務 (customfield_10291)
                eikyou = fields.get('customfield_10291')
                if eikyou and isinstance(eikyou, dict) and 'value' in eikyou:
                    custom_options['custom_eikyou_gyoumu'].add(eikyou['value'])
        
        # setをlistに変換
        return {
            'custom_tantou': sorted(list(custom_options['custom_tantou'])),
            'custom_eikyou_gyoumu': sorted(list(custom_options['custom_eikyou_gyoumu']))
        }
        
    except Exception as e:
        logger.warning(f"カスタムフィールド選択肢取得エラー: {str(e)}")
        return {
            'custom_tantou': [],
            'custom_eikyou_gyoumu': []
        }


def search_jira_with_filters(
    query: str, 
    project_keys: Optional[List[str]] = None,
    status_names: Optional[List[str]] = None,
    assignee_ids: Optional[List[str]] = None,
    issue_types: Optional[List[str]] = None,
    priorities: Optional[List[str]] = None,
    reporter_ids: Optional[List[str]] = None,
    custom_tantou: Optional[List[str]] = None,  # 担当 (customfield_10277)
    custom_eikyou_gyoumu: Optional[List[str]] = None,  # 影響業務 (customfield_10291)
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    updated_after: Optional[str] = None,
    updated_before: Optional[str] = None
) -> str:
    """
    フィルター条件付きでJiraチケットを検索し、構造化された結果を返す
    
    Args:
        query (str): 検索キーワード
        project_keys (Optional[List[str]]): プロジェクトキーのリスト
        status_names (Optional[List[str]]): ステータス名のリスト
        assignee_ids (Optional[List[str]]): 担当者IDのリスト
        issue_types (Optional[List[str]]): チケットタイプのリスト
        priorities (Optional[List[str]]): 優先度のリスト
        reporter_ids (Optional[List[str]]): 報告者IDのリスト
        custom_tantou (Optional[List[str]]): 担当カスタムフィールド値のリスト
        custom_eikyou_gyoumu (Optional[List[str]]): 影響業務カスタムフィールド値のリスト
        created_after (Optional[str]): 作成日以降（YYYY-MM-DD形式）
        created_before (Optional[str]): 作成日以前（YYYY-MM-DD形式）
        updated_after (Optional[str]): 更新日以降（YYYY-MM-DD形式）
        updated_before (Optional[str]): 更新日以前（YYYY-MM-DD形式）
        
    Returns:
        str: 検索結果のサマリー（チケット情報を整形したもの）
    """
    if not query or not query.strip():
        return "検索キーワードが指定されていません。"
    
    try:
        # Jira接続の初期化
        jira = Jira(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        
        # JQLクエリの構築
        # クエリから余分な演算子や引用符を除去して基本的なキーワードのみ抽出
        clean_query = query.strip()
        # ANDやORが含まれている場合は最初の部分のみを使用
        if ' AND ' in clean_query or ' OR ' in clean_query:
            clean_query = clean_query.split(' AND ')[0].split(' OR ')[0]
        # 引用符を除去
        clean_query = clean_query.replace('"', '').strip()
        
        jql_parts = [f'text ~ "{clean_query}"']
        
        # プロジェクトフィルター（CTJに固定）
        jql_parts.append('project = "CTJ"')
        
        # ステータスフィルター
        if status_names:
            status_filter = " OR ".join([f'status = "{status}"' for status in status_names])
            jql_parts.append(f"({status_filter})")
        
        # 担当者フィルター
        if assignee_ids:
            assignee_filter = " OR ".join([f'assignee = "{assignee_id}"' for assignee_id in assignee_ids])
            jql_parts.append(f"({assignee_filter})")
        
        # チケットタイプフィルター
        if issue_types:
            type_filter = " OR ".join([f'issuetype = "{issue_type}"' for issue_type in issue_types])
            jql_parts.append(f"({type_filter})")
        
        # 優先度フィルター
        if priorities:
            priority_filter = " OR ".join([f'priority = "{priority}"' for priority in priorities])
            jql_parts.append(f"({priority_filter})")
        
        # 報告者フィルター
        if reporter_ids:
            reporter_filter = " OR ".join([f'reporter = "{reporter_id}"' for reporter_id in reporter_ids])
            jql_parts.append(f"({reporter_filter})")
        
        # 担当カスタムフィールドフィルター (customfield_10277)
        if custom_tantou:
            tantou_filter = " OR ".join([f'cf[10277] = "{tantou}"' for tantou in custom_tantou])
            jql_parts.append(f"({tantou_filter})")
        
        # 影響業務カスタムフィールドフィルター (customfield_10291)
        if custom_eikyou_gyoumu:
            eikyou_filter = " OR ".join([f'cf[10291] = "{eikyou}"' for eikyou in custom_eikyou_gyoumu])
            jql_parts.append(f"({eikyou_filter})")
        
        # 作成日フィルター
        if created_after:
            jql_parts.append(f'created >= "{created_after}"')
        if created_before:
            jql_parts.append(f'created <= "{created_before}"')
        
        # 更新日フィルター
        if updated_after:
            jql_parts.append(f'updated >= "{updated_after}"')
        if updated_before:
            jql_parts.append(f'updated <= "{updated_before}"')
        
        jql_query = " AND ".join(jql_parts)
        
        logger.info(f"フィルター付きJira検索実行: {jql_query}")
        
        # Jira検索の実行
        search_result = jira.jql(jql_query, limit=10, expand='')
        
        if not search_result or 'issues' not in search_result:
            return f"Jiraで「{query}」（フィルター条件付き）に関する情報は見つかりませんでした。"
        
        issues = search_result['issues']
        total_count = search_result.get('total', 0)
        
        if total_count == 0:
            return f"Jiraで「{query}」（フィルター条件付き）に関する情報は見つかりませんでした。"
        
        # 結果の整形（フィルター条件も含める）
        result_summary = _format_jira_results_with_filters(
            issues, query, total_count, 
            project_keys, status_names, assignee_ids, issue_types, priorities,
            reporter_ids, custom_tantou, custom_eikyou_gyoumu,
            created_after, created_before, updated_after, updated_before
        )
        
        logger.info(f"フィルター付きJira検索完了: {len(issues)}件の結果を取得")
        return result_summary
        
    except Exception as e:
        logger.error(f"フィルター付きJira検索エラー: {str(e)}")
        return f"Jiraの検索中にエラーが発生しました: {str(e)}"


def _format_jira_results_with_filters(
    issues: List[Dict[str, Any]], 
    query: str, 
    total_count: int,
    project_keys: Optional[List[str]] = None,
    status_names: Optional[List[str]] = None,
    assignee_ids: Optional[List[str]] = None,
    issue_types: Optional[List[str]] = None,
    priorities: Optional[List[str]] = None,
    reporter_ids: Optional[List[str]] = None,
    custom_tantou: Optional[List[str]] = None,
    custom_eikyou_gyoumu: Optional[List[str]] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    updated_after: Optional[str] = None,
    updated_before: Optional[str] = None
) -> str:
    """
    フィルター条件付きJira検索結果を読みやすい形式に整形する
    
    Args:
        issues: Jira検索結果のissues配列
        query: 検索キーワード
        total_count: 総件数
        project_keys: プロジェクトキーフィルター
        status_names: ステータス名フィルター
        assignee_ids: 担当者IDフィルター
        issue_types: チケットタイプフィルター
        priorities: 優先度フィルター
        reporter_ids: 報告者IDフィルター
        custom_tantou: 担当カスタムフィールドフィルター
        custom_eikyou_gyoumu: 影響業務カスタムフィールドフィルター
        created_after: 作成日以降フィルター
        created_before: 作成日以前フィルター
        updated_after: 更新日以降フィルター
        updated_before: 更新日以前フィルター
        
    Returns:
        str: 整形された検索結果
    """
    if not issues:
        return f"Jiraで「{query}」（フィルター条件付き）に関する情報は見つかりませんでした。"
    
    # ヘッダー部分
    result_lines = [
        f"【Jira検索結果（フィルター付き）】キーワード: 「{query}」",
        f"見つかったチケット: {len(issues)}件（総数: {total_count}件）"
    ]
    
    # フィルター条件の表示
    filter_conditions = []
    # プロジェクトは常にCTJ固定
    filter_conditions.append("プロジェクト: CTJ")
    if status_names:
        filter_conditions.append(f"ステータス: {', '.join(status_names)}")
    if assignee_ids:
        filter_conditions.append(f"担当者: {', '.join(assignee_ids)}")
    if issue_types:
        filter_conditions.append(f"チケットタイプ: {', '.join(issue_types)}")
    if priorities:
        filter_conditions.append(f"優先度: {', '.join(priorities)}")
    if reporter_ids:
        filter_conditions.append(f"報告者: {', '.join(reporter_ids)}")
    if custom_tantou:
        filter_conditions.append(f"担当(カスタム): {', '.join(custom_tantou)}")
    if custom_eikyou_gyoumu:
        filter_conditions.append(f"影響業務: {', '.join(custom_eikyou_gyoumu)}")
    if created_after or created_before:
        date_range = []
        if created_after:
            date_range.append(f"{created_after}以降")
        if created_before:
            date_range.append(f"{created_before}以前")
        filter_conditions.append(f"作成日: {', '.join(date_range)}")
    if updated_after or updated_before:
        date_range = []
        if updated_after:
            date_range.append(f"{updated_after}以降")
        if updated_before:
            date_range.append(f"{updated_before}以前")
        filter_conditions.append(f"更新日: {', '.join(date_range)}")
    
    if filter_conditions:
        result_lines.append(f"フィルター条件: {' | '.join(filter_conditions)}")
    
    result_lines.append("")
    
    # 各チケットの詳細
    for i, issue in enumerate(issues[:5], 1):  # 最大5件表示
        try:
            fields = issue.get('fields', {})
            key = issue.get('key', 'N/A')
            summary = fields.get('summary', 'タイトルなし')
            status = fields.get('status', {}).get('name', '不明')
            issue_type = fields.get('issuetype', {}).get('name', '不明')
            priority = fields.get('priority', {}).get('name', '不明') if fields.get('priority') else '不明'
            project = fields.get('project', {}).get('key', '不明')
            assignee = fields.get('assignee')
            assignee_name = assignee.get('displayName', '未割り当て') if assignee else '未割り当て'
            
            # 説明文の抜粋（ADF形式の場合は簡略化）
            description = fields.get('description', {})
            description_text = _extract_description_text(description)
            
            result_lines.extend([
                f"{i}. [{key}] {summary}",
                f"   プロジェクト: {project} | ステータス: {status} | タイプ: {issue_type}",
                f"   優先度: {priority} | 担当者: {assignee_name}",
            ])
            
            if description_text:
                # 説明文が長い場合は最初の100文字のみ表示
                desc_preview = description_text[:100] + "..." if len(description_text) > 100 else description_text
                result_lines.append(f"   説明: {desc_preview}")
            
            # Jiraチケットへのリンク
            result_lines.append(f"   リンク: https://{settings.atlassian_domain}/browse/{key}")
            result_lines.append("")
            
        except Exception as e:
            logger.warning(f"チケット {issue.get('key', 'Unknown')} の処理中にエラー: {str(e)}")
            continue
    
    # 残りの件数表示
    if total_count > 5:
        result_lines.append(f"※ さらに {total_count - 5} 件のチケットがあります。")
    
    return "\n".join(result_lines)


def search_jira_tool(query: str) -> str:
    """
    JQLクエリでJiraチケットを検索し、構造化された結果を返す
    
    Args:
        query (str): 検索キーワード
        
    Returns:
        str: 検索結果のサマリー（チケット情報を整形したもの）
    """
    if not query or not query.strip():
        return "検索キーワードが指定されていません。"
    
    try:
        # Jira接続の初期化
        jira = Jira(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        
        # JQLクエリの構築 - text検索でキーワードを含むチケットを検索
        jql_query = f'text ~ "{query.strip()}"'
        
        logger.info(f"Jira検索実行: {jql_query}")
        start_time = time.time()
        
        # Jira検索の実行
        search_result = jira.jql(jql_query, limit=10, expand='')
        search_time = time.time() - start_time
        
        if not search_result or 'issues' not in search_result:
            logger.warning(f"Jira検索結果なし: クエリ='{query}' | 実行時間: {search_time:.2f}秒")
            return f"Jiraで「{query}」に関する情報は見つかりませんでした。"
        
        issues = search_result['issues']
        total_count = search_result.get('total', 0)
        
        if total_count == 0:
            logger.warning(f"Jira検索結果0件: クエリ='{query}' | 実行時間: {search_time:.2f}秒")
            return f"Jiraで「{query}」に関する情報は見つかりませんでした。"
        
        # 検索結果をログに記録
        log_search_results(logger, "Jira", query, issues, total_count, search_time)
        
        # 結果の整形
        result_summary = _format_jira_results(issues, query, total_count)
        
        logger.info(f"Jira検索処理完了: {len(issues)}件取得 | 実行時間: {search_time:.2f}秒")
        return result_summary
        
    except Exception as e:
        logger.error(f"Jira検索エラー: {str(e)}")
        return f"Jiraの検索中にエラーが発生しました: {str(e)}"


def _format_jira_results(issues: List[Dict[str, Any]], query: str, total_count: int) -> str:
    """
    Jira検索結果を読みやすい形式に整形する
    
    Args:
        issues: Jira検索結果のissues配列
        query: 検索キーワード
        total_count: 総件数
        
    Returns:
        str: 整形された検索結果
    """
    if not issues:
        return f"Jiraで「{query}」に関する情報は見つかりませんでした。"
    
    # ヘッダー部分
    result_lines = [
        f"【Jira検索結果】キーワード: 「{query}」",
        f"見つかったチケット: {len(issues)}件（総数: {total_count}件）",
        ""
    ]
    
    # 各チケットの詳細
    for i, issue in enumerate(issues[:5], 1):  # 最大5件表示
        try:
            fields = issue.get('fields', {})
            key = issue.get('key', 'N/A')
            summary = fields.get('summary', 'タイトルなし')
            status = fields.get('status', {}).get('name', '不明')
            issue_type = fields.get('issuetype', {}).get('name', '不明')
            assignee = fields.get('assignee')
            assignee_name = assignee.get('displayName', '未割り当て') if assignee else '未割り当て'
            
            # 説明文の抜粋（ADF形式の場合は簡略化）
            description = fields.get('description', {})
            description_text = _extract_description_text(description)
            
            result_lines.extend([
                f"{i}. [{key}] {summary}",
                f"   ステータス: {status} | タイプ: {issue_type} | 担当者: {assignee_name}",
            ])
            
            if description_text:
                # 説明文が長い場合は最初の100文字のみ表示
                desc_preview = description_text[:100] + "..." if len(description_text) > 100 else description_text
                result_lines.append(f"   説明: {desc_preview}")
            
            # Jiraチケットへのリンク
            result_lines.append(f"   リンク: https://{settings.atlassian_domain}/browse/{key}")
            result_lines.append("")
            
        except Exception as e:
            logger.warning(f"チケット {issue.get('key', 'Unknown')} の処理中にエラー: {str(e)}")
            continue
    
    # 残りの件数表示
    if total_count > 5:
        result_lines.append(f"※ さらに {total_count - 5} 件のチケットがあります。")
    
    return "\n".join(result_lines)


def _extract_description_text(description: Any) -> str:
    """
    Jiraの説明フィールドからプレーンテキストを抽出する
    
    Args:
        description: Jiraの説明フィールド（ADF形式またはプレーンテキスト）
        
    Returns:
        str: 抽出されたテキスト
    """
    if not description:
        return ""
    
    # プレーンテキストの場合
    if isinstance(description, str):
        return description.strip()
    
    # ADF（Atlassian Document Format）形式の場合
    if isinstance(description, dict):
        try:
            content = description.get('content', [])
            text_parts = []
            
            def extract_text_from_adf(node):
                if isinstance(node, dict):
                    # テキストノードの場合
                    if node.get('type') == 'text':
                        return node.get('text', '')
                    
                    # 子ノードがある場合は再帰的に処理
                    if 'content' in node:
                        return ' '.join(extract_text_from_adf(child) for child in node['content'])
                
                return ''
            
            for content_node in content:
                text = extract_text_from_adf(content_node)
                if text.strip():
                    text_parts.append(text.strip())
            
            return ' '.join(text_parts)
            
        except Exception as e:
            logger.warning(f"ADF形式の説明文解析エラー: {str(e)}")
            return str(description)
    
    return str(description) 