"""
Confluence検索ツール

CQLクエリを使用してConfluenceページを検索し、LangChainエージェントが利用可能な
構造化された結果を返すツールを提供します。
"""

import logging
import time
from typing import Optional, List, Dict, Any
from atlassian import Confluence

from ..config.settings import settings
from ..utils.cache_manager import CacheManager
from ..utils.log_config import get_logger, log_search_results

# ログ設定
logger = get_logger(__name__)

# キャッシュマネージャーのインスタンス
cache_manager = CacheManager()


def search_confluence_tool(query: str, analyze_content: bool = True, api_logger=None) -> str:
    """
    CQLクエリでConfluenceページを検索し、構造化された結果を返す
    
    Args:
        query (str): 検索キーワード
        analyze_content (bool): ページ内容を詳細分析するかどうか
        
    Returns:
        str: 検索結果のサマリー（ページ情報を整形したもの）
    """
    if not query or not query.strip():
        return "検索キーワードが指定されていません。"
    
    try:
        # Confluence接続の初期化
        confluence = Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        
        # CQLクエリの構築 - タイトル検索とテキスト検索を併用（急募機能対応）
        # 特定のスペースがある場合はそれも条件に含める
        if settings.confluence_space:
            cql_query = f'(text ~ "{query.strip()}" OR title ~ "{query.strip()}") and space = "{settings.confluence_space}"'
        else:
            cql_query = f'(text ~ "{query.strip()}" OR title ~ "{query.strip()}")'
        
        logger.info(f"Confluence検索実行: {cql_query}")
        start_time = time.time()
        
        # APIログ: リクエスト記録
        if api_logger and api_logger.is_logging_enabled():
            api_logger.log_confluence_request(
                cql_query=cql_query,
                space_key=settings.confluence_space,
                limit=10
            )
        
        # Confluence検索の実行
        search_result = confluence.cql(cql_query, limit=10)
        search_time = time.time() - start_time
        
        # APIログ: レスポンス記録
        if api_logger and api_logger.is_logging_enabled():
            results = search_result.get('results', [])
            total_size = search_result.get('totalSize', 0)
            api_logger.log_confluence_response(
                pages=results,
                total_size=total_size,
                execution_time=search_time
            )
        
        if not search_result or 'results' not in search_result:
            logger.warning(f"Confluence検索結果なし: クエリ='{query}' | 実行時間: {search_time:.2f}秒")
            return f"Confluenceで「{query}」に関する情報は見つかりませんでした。"
        
        results = search_result['results']
        total_count = search_result.get('totalSize', 0)
        
        # 結果の型チェックとフィルタリング（エラー処理改善）
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, dict):
                valid_results.append(result)
            else:
                logger.warning(f"結果 {i+1} は辞書ではありません (type: {type(result).__name__}): {str(result)[:100]}...")
        
        results = valid_results
        
        if total_count == 0 or not results:
            logger.warning(f"Confluence検索結果0件: クエリ='{query}' | 実行時間: {search_time:.2f}秒")
            return f"Confluenceで「{query}」に関する情報は見つかりませんでした。"
        
        # 検索結果をログに記録
        log_search_results(logger, "Confluence", query, results, total_count, search_time)
        
        # 詳細分析が必要な場合、上位結果のページ内容を取得
        enhanced_results = results
        if analyze_content and results:
            logger.info(f"詳細分析開始: 上位{min(3, len(results))}件のページ内容を取得")
            analysis_start_time = time.time()
            enhanced_results = _enhance_results_with_content(confluence, results[:3])  # 上位3件のみ詳細分析
            analysis_time = time.time() - analysis_start_time
            logger.info(f"詳細分析完了: 実行時間 {analysis_time:.2f}秒")
        
        # 結果の整形
        result_summary = _format_confluence_results(enhanced_results, query, total_count, analyze_content)
        
        total_time = time.time() - start_time
        logger.info(f"Confluence検索処理完了: {len(results)}件取得 | 総実行時間: {total_time:.2f}秒")
        return result_summary
        
    except Exception as e:
        logger.error(f"Confluence検索エラー: {str(e)}")
        return f"Confluenceの検索中にエラーが発生しました: {str(e)}"


def _enhance_results_with_content(confluence: Confluence, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    検索結果にページの詳細内容を追加する
    
    Args:
        confluence: Confluence APIクライアント
        results: 検索結果のリスト
        
    Returns:
        List[Dict[str, Any]]: 詳細内容を含む検索結果
    """
    enhanced_results = []
    
    for result in results:
        try:
            # ページIDを取得
            page_id = None
            if 'id' in result:
                page_id = result['id']
            elif 'content' in result and isinstance(result['content'], dict) and 'id' in result['content']:
                page_id = result['content']['id']
            
            if page_id:
                # ページの詳細内容を取得
                page_content = confluence.get_page_by_id(
                    page_id, 
                    expand='body.storage,version,space'
                )
                
                if page_content and 'body' in page_content:
                    # 本文を抽出して分析（安全な型チェック付き）
                    body_obj = page_content.get('body', {})
                    if isinstance(body_obj, dict):
                        storage_obj = body_obj.get('storage', {})
                        if isinstance(storage_obj, dict):
                            body_content = storage_obj.get('value', '')
                            if body_content:
                                # HTMLタグを除去してテキスト抽出
                                text_content = _extract_text_from_html(body_content)
                                # 重要なセクションを抽出
                                key_sections = _extract_key_sections(text_content)
                                
                                # 元の結果に詳細内容を追加
                                result['detailed_content'] = text_content[:1000]  # 最初の1000文字
                                result['key_sections'] = key_sections
                                result['full_page_data'] = page_content
                
            enhanced_results.append(result)
            
        except Exception as e:
            logger.warning(f"ページ詳細取得エラー: {str(e)}")
            enhanced_results.append(result)  # 元の結果をそのまま追加
    
    return enhanced_results


def _extract_key_sections(text_content: str) -> Dict[str, str]:
    """
    テキストから重要なセクションを抽出する
    
    Args:
        text_content: ページのテキスト内容
        
    Returns:
        Dict[str, str]: 抽出されたキーセクション
    """
    sections = {}
    
    # 仕様、設計、実装、要件などのキーワードを含むセクションを抽出
    keywords = {
        'requirements': ['要件', '要求', 'requirement'],
        'specifications': ['仕様', '仕様書', 'specification', 'spec'],
        'design': ['設計', '設計書', 'design'],
        'implementation': ['実装', '実装方法', 'implementation'],
        'best_practices': ['ベストプラクティス', '推奨', 'best practice', '最適'],
        'security': ['セキュリティ', 'security', '認証', 'authentication'],
        'architecture': ['アーキテクチャ', 'architecture', '構成', '構造']
    }
    
    lines = text_content.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # セクションヘッダーを検出
        found_section = None
        for section_key, section_keywords in keywords.items():
            if any(keyword in line.lower() for keyword in section_keywords):
                found_section = section_key
                break
        
        if found_section:
            # 前のセクションを保存
            if current_section and current_content:
                sections[current_section] = ' '.join(current_content)[:300]  # 最初の300文字
            
            current_section = found_section
            current_content = [line]
        elif current_section and len(current_content) < 10:  # セクション内容を収集（最大10行）
            current_content.append(line)
    
    # 最後のセクションを保存
    if current_section and current_content:
        sections[current_section] = ' '.join(current_content)[:300]
    
    return sections


def _extract_text_from_html(html_content: str) -> str:
    """
    HTMLからテキストを抽出する
    
    Args:
        html_content: HTMLコンテンツ
        
    Returns:
        str: 抽出されたテキスト
    """
    import re
    
    # HTMLタグを除去
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # 連続する空白を1つに
    text = re.sub(r'\s+', ' ', text)
    # 改行を正規化
    text = text.replace('\n', ' ').strip()
    
    return text


def _format_confluence_results(results: List[Dict[str, Any]], query: str, total_count: int, analyze_content: bool = False) -> str:
    """
    Confluence検索結果を読みやすい形式に整形する
    
    Args:
        results: Confluence検索結果のresults配列
        query: 検索キーワード
        total_count: 総件数
        analyze_content: 詳細分析結果を含むかどうか
        
    Returns:
        str: 整形された検索結果
    """
    if not results:
        return f"Confluenceで「{query}」に関する情報は見つかりませんでした。"
    
    # ヘッダー部分
    analysis_note = " (詳細分析付き)" if analyze_content else ""
    result_lines = [
        f"📚 **Confluenceページ検索結果{analysis_note}**",
        f"🔍 キーワード: 「{query}」",
        f"📌 見つかったページ: {len(results)}件（総数: {total_count}件）",
        ""
    ]
    
    # 各ページの詳細
    for i, result in enumerate(results[:5], 1):  # 最大5件表示
        try:
            # resultが辞書でない場合はスキップ
            if not isinstance(result, dict):
                logger.warning(f"結果 {i} は辞書ではありません: {type(result)}")
                continue
            
            # CQL検索の場合、データ構造が異なることがある
            # result 直下にtitle, typeなどがある場合とcontent下にある場合を両方チェック
            
            # タイトルの取得
            title = 'タイトルなし'
            if 'title' in result:
                title = result['title']
            elif 'content' in result and isinstance(result['content'], dict) and 'title' in result['content']:
                title = result['content']['title']
            
            # ID とタイプの取得（検索結果の構造を考慮）
            page_id = 'N/A'
            if 'content' in result and isinstance(result['content'], dict) and 'id' in result['content']:
                page_id = result['content']['id']
            elif 'id' in result:
                page_id = result['id']
            
            page_type = 'page'
            if 'content' in result and isinstance(result['content'], dict) and 'type' in result['content']:
                page_type = result['content']['type']
            elif 'type' in result:
                page_type = result['type']
            
            # スペース情報の取得（複数のパターンを試行）
            space_name = 'CLIENTTOMO'
            space_key = 'CLIENTTOMO'
            
            space_info = None
            if 'content' in result and isinstance(result['content'], dict) and 'space' in result['content']:
                space_info = result['content']['space']
            elif 'space' in result:
                space_info = result['space']
            
            if isinstance(space_info, dict):
                space_name = space_info.get('name', 'CLIENTTOMO')
                space_key = space_info.get('key', 'CLIENTTOMO')
            elif space_info:
                space_name = str(space_info)
                space_key = str(space_info)
            
            # 検索結果の抜粋
            excerpt = result.get('excerpt', '') or result.get('bodyExcerpt', '')
            if excerpt:
                # HTMLタグを簡単に除去
                excerpt = _clean_html_tags(excerpt)
            
            # 作成者情報（複数のパターンを試行）
            created_by = 'システム'  # デフォルト値
            
            # 様々なパスで作成者情報を取得試行（安全な型チェック付き）
            creator_paths = []
            
            # createdBy.displayName
            created_by_obj = result.get('createdBy', {})
            if isinstance(created_by_obj, dict):
                creator_paths.append(created_by_obj.get('displayName'))
            
            # content.history.createdBy.displayName
            content_obj = result.get('content', {})
            if isinstance(content_obj, dict):
                history_obj = content_obj.get('history', {})
                if isinstance(history_obj, dict):
                    created_by_nested = history_obj.get('createdBy', {})
                    if isinstance(created_by_nested, dict):
                        creator_paths.append(created_by_nested.get('displayName'))
            
            # lastModified.by.displayName
            last_modified_obj = result.get('lastModified', {})
            if isinstance(last_modified_obj, dict):
                by_obj = last_modified_obj.get('by', {})
                if isinstance(by_obj, dict):
                    creator_paths.append(by_obj.get('displayName'))
            
            # version.by.displayName
            version_obj = result.get('version', {})
            if isinstance(version_obj, dict):
                by_obj = version_obj.get('by', {})
                if isinstance(by_obj, dict):
                    creator_paths.append(by_obj.get('displayName'))
            
            for creator in creator_paths:
                if creator:
                    created_by = creator
                    break
            
            # WebUI上でのページURL
            base_url = f"https://{settings.atlassian_domain}"
            
            # URL構築（IDが取得できている場合）
            if page_id and page_id != 'N/A':
                page_url = f"{base_url}/wiki/spaces/{space_key}/pages/{page_id}"
            else:
                # IDが取得できない場合は検索結果のURLを使用
                page_url = result.get('url', f"{base_url}/wiki/search?text={query}")
            
            result_lines.extend([
                f"📄 **{i}. {title}**",
                f"   📍 スペース: {space_name} ({space_key}) | タイプ: {page_type}",
                f"   👤 作成者: {created_by}",
            ])
            
            # 詳細分析結果がある場合はそれを優先表示
            if analyze_content and 'key_sections' in result and result['key_sections']:
                result_lines.append("   📋 **重要なセクション:**")
                key_sections = result['key_sections']
                
                # 日本語のセクション名に変換
                section_names = {
                    'requirements': '要件・要求',
                    'specifications': '仕様・仕様書', 
                    'design': '設計・設計書',
                    'implementation': '実装・実装方法',
                    'best_practices': 'ベストプラクティス・推奨事項',
                    'security': 'セキュリティ・認証',
                    'architecture': 'アーキテクチャ・構成'
                }
                
                for section_key, content in key_sections.items():
                    if content.strip():
                        section_name = section_names.get(section_key, section_key)
                        result_lines.append(f"     • {section_name}: {content[:200]}...")
                
                # 詳細内容がある場合はその一部も表示
                if 'detailed_content' in result and result['detailed_content']:
                    detailed_preview = result['detailed_content'][:300] + "..."
                    result_lines.append(f"   📖 **詳細内容抜粋**: {detailed_preview}")
            
            elif excerpt:
                # 詳細分析がない場合は従来の抜粋を表示
                excerpt_preview = excerpt[:150] + "..." if len(excerpt) > 150 else excerpt
                result_lines.append(f"   📝 内容抜粋: {excerpt_preview}")
            
            # ページへのリンク
            result_lines.append(f"   🔗 リンク: {page_url}")
            result_lines.append("")
            
        except Exception as e:
            # エラー処理の改善: resultの型チェック
            if isinstance(result, dict):
                page_id = result.get('id', 'Unknown')
                if page_id == 'Unknown':
                    # contentから取得を試行（安全な型チェック付き）
                    content = result.get('content', {})
                    if isinstance(content, dict):
                        page_id = content.get('id', 'Unknown')
            else:
                page_id = f"Unknown (type: {type(result).__name__})"
            
            logger.warning(f"ページ {page_id} の処理中にエラー: {str(e)}")
            # デバッグ用: 実際の結果構造をログ出力
            logger.debug(f"結果構造 (type: {type(result).__name__}): {str(result)[:200]}...")
            continue
    
    # 残りの件数表示
    if total_count > 5:
        result_lines.append(f"📊 さらに {total_count - 5} 件のページがあります。")
        result_lines.append("")
    
    # 詳細分析結果がある場合は総合分析を追加
    if analyze_content:
        result_lines.extend([
            "🎯 **分析結果サマリー:**",
            _generate_analysis_summary(results, query),
            "",
            "💡 **推奨事項:**",
            _generate_recommendations(results, query),
            ""
        ])
    
    result_lines.append("💬 より詳細な情報が必要な場合は、上記リンクから各ページをご確認ください。")
    
    return "\n".join(result_lines)


def _generate_analysis_summary(results: List[Dict[str, Any]], query: str) -> str:
    """
    検索結果から分析サマリーを生成する
    
    Args:
        results: 検索結果
        query: 検索キーワード
        
    Returns:
        str: 分析サマリー
    """
    sections_found = set()
    common_topics = []
    
    for result in results:
        if 'key_sections' in result:
            sections_found.update(result['key_sections'].keys())
            
    if 'specifications' in sections_found or 'requirements' in sections_found:
        common_topics.append("仕様・要件に関する情報")
    if 'security' in sections_found:
        common_topics.append("セキュリティ・認証に関する設計")
    if 'implementation' in sections_found:
        common_topics.append("実装方法・手順")
    if 'best_practices' in sections_found:
        common_topics.append("ベストプラクティス・推奨事項")
    if 'architecture' in sections_found:
        common_topics.append("アーキテクチャ・システム構成")
    
    if common_topics:
        topics_text = "、".join(common_topics)
        return f"「{query}」に関連して、{topics_text}が含まれるドキュメントが見つかりました。"
    else:
        return f"「{query}」に関連する基本的な情報が含まれるドキュメントが見つかりました。"


def _generate_recommendations(results: List[Dict[str, Any]], query: str) -> str:
    """
    検索結果から推奨事項を生成する
    
    Args:
        results: 検索結果
        query: 検索キーワード
        
    Returns:
        str: 推奨事項
    """
    recommendations = []
    
    # セキュリティ関連の質問の場合
    if any(keyword in query.lower() for keyword in ['ログイン', 'login', '認証', 'auth', 'セキュリティ']):
        has_security_docs = any(
            'key_sections' in result and ('security' in result['key_sections'] or 'best_practices' in result['key_sections'])
            for result in results
        )
        if has_security_docs:
            recommendations.append("• セキュリティ・認証に関する設計書を優先的に確認してください")
            recommendations.append("• ベストプラクティスの項目があれば参考にしてください")
        
        recommendations.append("• 実装前に要件定義書で必要な機能を確認してください")
        recommendations.append("• 既存システムとの連携方法について設計書を確認してください")
    
    # 一般的な推奨事項
    if not recommendations:
        recommendations.append("• 最も関連性の高いドキュメントから順に確認することをお勧めします")
        recommendations.append("• 実装方法が記載されている場合は、そちらを参考にしてください")
    
    recommendations.append("• 不明な点があれば、ドキュメント作成者に直接お問い合わせください")
    
    return "\n".join(recommendations)


def _clean_html_tags(text: str) -> str:
    """
    HTMLタグを除去してプレーンテキストにする簡易関数
    
    Args:
        text: HTMLを含む可能性のあるテキスト
        
    Returns:
        str: HTMLタグを除去したテキスト
    """
    if not text:
        return ""
    
    import re
    
    # HTMLタグを除去
    text = re.sub(r'<[^>]+>', '', text)
    
    # HTMLエンティティをデコード
    html_entities = {
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&#39;': "'",
        '&nbsp;': ' ',
    }
    
    for entity, char in html_entities.items():
        text = text.replace(entity, char)
    
    # 余分な空白を整理
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def search_confluence_with_filters(
    query: str,
    space_keys: Optional[List[str]] = None,
    content_type: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None
) -> str:
    """
    フィルター条件付きでConfluenceページを検索し、構造化された結果を返す
    
    Args:
        query (str): 検索キーワード
        space_keys (Optional[List[str]]): スペースキーのリスト
        content_type (Optional[str]): コンテンツタイプ（page または blogpost）
        created_after (Optional[str]): 作成日以降（YYYY-MM-DD形式）
        created_before (Optional[str]): 作成日以前（YYYY-MM-DD形式）
        
    Returns:
        str: 検索結果のサマリー（ページ情報を整形したもの）
    """
    if not query or not query.strip():
        return "検索キーワードが指定されていません。"
    
    try:
        # Confluence接続の初期化
        confluence = Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        
        # CQLクエリの構築
        # クエリから余分な演算子や引用符を除去して基本的なキーワードのみ抽出
        clean_query = query.strip()
        if ' AND ' in clean_query or ' OR ' in clean_query:
            clean_query = clean_query.split(' AND ')[0].split(' OR ')[0]
        clean_query = clean_query.replace('"', '').strip()
        
        cql_parts = [f'text ~ "{clean_query}"']
        
        # スペースフィルター
        if space_keys:
            space_filter = " OR ".join([f'space = "{space_key}"' for space_key in space_keys])
            cql_parts.append(f"({space_filter})")
        
        # コンテンツタイプフィルター
        if content_type and content_type in ['page', 'blogpost']:
            cql_parts.append(f'type = "{content_type}"')
        
        # 作成日フィルター
        if created_after:
            cql_parts.append(f'created >= "{created_after}"')
        if created_before:
            cql_parts.append(f'created <= "{created_before}"')
        
        cql_query = " AND ".join(cql_parts)
        
        logger.info(f"フィルター付きConfluence検索実行: {cql_query}")
        
        # Confluence検索の実行
        search_result = confluence.cql(cql_query, limit=10)
        
        if not search_result or 'results' not in search_result:
            return f"Confluenceで「{query}」（フィルター条件付き）に関する情報は見つかりませんでした。"
        
        results = search_result['results']
        total_count = search_result.get('totalSize', 0)
        
        if total_count == 0:
            return f"Confluenceで「{query}」（フィルター条件付き）に関する情報は見つかりませんでした。"
        
        # 結果の整形（フィルター条件も含める）
        result_summary = _format_confluence_results_with_filters(
            results, query, total_count,
            space_keys=space_keys,
            content_type=content_type,
            created_after=created_after,
            created_before=created_before
        )
        
        logger.info(f"フィルター付きConfluence検索完了: {len(results)}件のページを取得")
        return result_summary
        
    except Exception as e:
        error_msg = f"Confluenceの検索中にエラーが発生しました: {str(e)}"
        logger.error(error_msg)
        return error_msg


def _format_confluence_results_with_filters(
    results: List[Dict[str, Any]], 
    query: str, 
    total_count: int,
    space_keys: Optional[List[str]] = None,
    content_type: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None
) -> str:
    """
    Confluenceフィルター検索結果を読みやすい形式に整形する
    
    Args:
        results: Confluence検索結果のresults配列
        query: 検索キーワード
        total_count: 総件数
        space_keys: スペースキーフィルター
        content_type: コンテンツタイプフィルター
        created_after: 作成日以降フィルター
        created_before: 作成日以前フィルター
        
    Returns:
        str: 整形された検索結果
    """
    if not results:
        return f"Confluenceで「{query}」（フィルター条件付き）に関する情報は見つかりませんでした。"
    
    # ヘッダー部分
    result_lines = [
        f"【Confluence検索結果（フィルター付き）】キーワード: 「{query}」",
        f"見つかったページ: {len(results)}件（総数: {total_count}件）"
    ]
    
    # フィルター条件の表示
    filter_conditions = []
    if space_keys:
        filter_conditions.append(f"スペース: {', '.join(space_keys)}")
    if content_type:
        filter_conditions.append(f"コンテンツタイプ: {content_type}")
    if created_after or created_before:
        date_range = []
        if created_after:
            date_range.append(f"{created_after}以降")
        if created_before:
            date_range.append(f"{created_before}以前")
        filter_conditions.append(f"作成日: {', '.join(date_range)}")
    
    if filter_conditions:
        result_lines.append(f"フィルター条件: {' | '.join(filter_conditions)}")
    
    result_lines.append("")
    
    # 各ページの詳細
    for i, result in enumerate(results[:5], 1):  # 最大5件表示
        try:
            # データ構造に対応した堅牢な取得
            if isinstance(result, str):
                result_lines.append(f"{i}. 【解析エラー】結果の構造を正しく取得できませんでした")
                continue
            
            # タイトルの取得
            title = result.get('title') or result.get('content', {}).get('title', 'タイトルなし')
            
            # ID とタイプの取得
            page_id = result.get('id') or result.get('content', {}).get('id', 'N/A')
            page_type = result.get('type') or result.get('content', {}).get('type', 'page')
            
            # スペース情報の取得
            space_info = result.get('space') or result.get('content', {}).get('space', {})
            if isinstance(space_info, dict):
                space_name = space_info.get('name', 'CLIENTTOMO')
                space_key = space_info.get('key', 'CLIENTTOMO')
            else:
                space_name = 'CLIENTTOMO'
                space_key = 'CLIENTTOMO'
            
            # 作成者・作成日情報の取得
            created_by = result.get('lastModified', {}).get('by', {}).get('displayName', 'システム')
            created_date = result.get('lastModified', {}).get('when', '不明')
            
            # URLの生成
            if page_id and page_id != 'N/A':
                page_url = f"https://{settings.atlassian_domain}/wiki/spaces/{space_key}/pages/{page_id}"
            else:
                page_url = f"https://{settings.atlassian_domain}/wiki/spaces/{space_key}"
            
            # 抜粋やコンテンツの取得
            excerpt = result.get('excerpt', 'コンテンツの抜粋はありません')
            excerpt_cleaned = _clean_html_tags(excerpt)[:200]  # 200文字まで
            
            result_lines.append(f"{i}. **{title}**")
            result_lines.append(f"   📍 スペース: {space_name} ({space_key}) | タイプ: {page_type}")
            result_lines.append(f"   👤 作成者: {created_by} | 作成日: {created_date}")
            result_lines.append(f"   🔗 URL: {page_url}")
            
            if excerpt_cleaned:
                result_lines.append(f"   📝 概要: {excerpt_cleaned}...")
            
            result_lines.append("")
            
        except Exception as e:
            logger.warning(f"結果{i}の処理エラー: {str(e)}")
            result_lines.append(f"{i}. 【処理エラー】このページの情報を正しく取得できませんでした")
            result_lines.append("")
    
    # 残りのページ数を表示
    if total_count > 5:
        result_lines.append(f"📋 その他 {total_count - 5} 件のページがあります。")
        result_lines.append("")
    
    # 利用のヒント
    result_lines.extend([
        "💡 **利用のヒント:**",
        "- 「そのページについて詳しく」と聞くと、より詳細な情報を取得できます",
        "- 特定のページの内容について質問できます",
        "- 関連するページや類似の仕様について聞くことも可能です"
    ])
    
    return '\n'.join(result_lines)


def get_confluence_space_structure(space_key: str = "CLIENTTOMO") -> str:
    """
    指定されたConfluenceスペースのページ構造を取得する
    
    Args:
        space_key (str): 対象のスペースキー（デフォルト: CLIENTTOMO）
        
    Returns:
        str: スペースのページ構造情報
    """
    try:
        # Confluence接続の初期化
        confluence = Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        
        logger.info(f"Confluenceスペース構造取得開始: {space_key}")
        
        # スペース情報を取得
        try:
            space_info = confluence.get_space(space_key, expand='description,homepage')
        except Exception as e:
            logger.error(f"スペース情報取得エラー: {str(e)}")
            return f"スペース '{space_key}' の情報を取得できませんでした: {str(e)}"
        
        # ページ一覧を取得（階層構造も含む）
        try:
            # すべてのページを取得（ページネーション対応）
            all_pages = []
            start = 0
            limit = 50
            
            while True:
                pages_result = confluence.get_all_pages_from_space(
                    space_key, 
                    start=start, 
                    limit=limit,
                    expand='ancestors,children.page,history.lastUpdated,version,space'
                )
                
                if not pages_result:
                    break
                    
                all_pages.extend(pages_result)
                
                # 取得件数がlimitより少ない場合は最後のページ
                if len(pages_result) < limit:
                    break
                    
                start += limit
                
                # 安全のため最大500ページまで
                if len(all_pages) >= 500:
                    logger.warning(f"ページ数が500件を超えたため取得を制限しました")
                    break
        
        except Exception as e:
            logger.error(f"ページ一覧取得エラー: {str(e)}")
            return f"スペース '{space_key}' のページ一覧を取得できませんでした: {str(e)}"
        
        # 結果の整形
        result_lines = [
            f"【Confluenceスペース構造】スペース: {space_key}",
            f"スペース名: {space_info.get('name', 'N/A')}",
            f"総ページ数: {len(all_pages)}件",
            ""
        ]
        
        # スペースの説明があれば表示
        if space_info.get('description'):
            description = space_info['description'].get('plain', {}).get('value', '')
            if description:
                cleaned_desc = _clean_html_tags(description)[:200]
                result_lines.append(f"スペース説明: {cleaned_desc}")
                result_lines.append("")
        
        # ホームページ情報
        homepage = space_info.get('homepage')
        if homepage:
            homepage_title = homepage.get('title', 'N/A')
            homepage_id = homepage.get('id', 'N/A')
            result_lines.append(f"ホームページ: {homepage_title} (ID: {homepage_id})")
            result_lines.append("")
        
        # ページを階層構造で整理
        page_hierarchy = _build_page_hierarchy(all_pages)
        
        # 階層構造を表示
        result_lines.append("📁 **ページ階層構造:**")
        result_lines.append("")
        
        for root_page in page_hierarchy['roots']:
            _append_page_tree(result_lines, root_page, page_hierarchy['children'], 0)
        
        # 親を持たないページ（ルートページ以外）があれば表示
        orphaned_pages = page_hierarchy['orphaned']
        if orphaned_pages:
            result_lines.append("")
            result_lines.append("📄 **その他のページ（親ページなし）:**")
            result_lines.append("")
            for page in orphaned_pages[:10]:  # 最大10件
                title = page.get('title', 'タイトルなし')
                page_id = page.get('id', 'N/A')
                page_type = page.get('type', 'page')
                last_updated = _get_last_updated(page)
                result_lines.append(f"- {title} ({page_type}) | 更新: {last_updated}")
            
            if len(orphaned_pages) > 10:
                result_lines.append(f"  ... 他 {len(orphaned_pages) - 10} 件")
        
        # 統計情報
        result_lines.append("")
        result_lines.append("📊 **統計情報:**")
        page_types = {}
        recent_updates = []
        
        for page in all_pages:
            page_type = page.get('type', 'page')
            page_types[page_type] = page_types.get(page_type, 0) + 1
            
            last_updated = _get_last_updated_date(page)
            if last_updated:
                recent_updates.append((page.get('title', 'N/A'), last_updated))
        
        # ページタイプ別件数
        for page_type, count in sorted(page_types.items()):
            result_lines.append(f"- {page_type}: {count}件")
        
        # 最近更新されたページ（上位5件）
        if recent_updates:
            recent_updates.sort(key=lambda x: x[1], reverse=True)
            result_lines.append("")
            result_lines.append("🕒 **最近更新されたページ（上位5件）:**")
            for title, update_date in recent_updates[:5]:
                result_lines.append(f"- {title} | {update_date}")
        
        logger.info(f"Confluenceスペース構造取得完了: {len(all_pages)}ページ")
        return '\n'.join(result_lines)
        
    except Exception as e:
        logger.error(f"Confluenceスペース構造取得エラー: {str(e)}")
        return f"スペース構造の取得中にエラーが発生しました: {str(e)}"


def _build_page_hierarchy(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    ページリストから階層構造を構築する
    
    Args:
        pages: ページ情報のリスト
        
    Returns:
        Dict: 階層構造情報（roots, children, orphaned）
    """
    # ページIDをキーとした辞書を作成
    pages_by_id = {page['id']: page for page in pages}
    
    # 各ページの子ページリストを初期化
    children = {page_id: [] for page_id in pages_by_id.keys()}
    
    # ルートページと孤立ページを分類
    roots = []
    orphaned = []
    
    for page in pages:
        page_id = page['id']
        ancestors = page.get('ancestors', [])
        
        if not ancestors:
            # 祖先がない = ルートページ
            roots.append(page)
        elif ancestors:
            # 最も近い祖先（直接の親）を取得
            direct_parent = ancestors[-1] if ancestors else None
            if direct_parent and direct_parent['id'] in pages_by_id:
                parent_id = direct_parent['id']
                children[parent_id].append(page)
            else:
                # 親ページがスペース内に存在しない
                orphaned.append(page)
    
    return {
        'roots': roots,
        'children': children,
        'orphaned': orphaned
    }


def _append_page_tree(result_lines: List[str], page: Dict[str, Any], children_dict: Dict[str, List], depth: int):
    """
    ページツリーを再帰的に文字列リストに追加する
    
    Args:
        result_lines: 結果を格納するリスト
        page: 現在のページ情報
        children_dict: 子ページ辞書
        depth: 現在の階層の深さ
    """
    # インデント
    indent = "  " * depth
    icon = "📁" if children_dict.get(page['id']) else "📄"
    
    title = page.get('title', 'タイトルなし')
    page_id = page.get('id', 'N/A')
    page_type = page.get('type', 'page')
    last_updated = _get_last_updated(page)
    
    result_lines.append(f"{indent}{icon} {title} ({page_type}) | 更新: {last_updated}")
    
    # 子ページを再帰的に表示（最大深度5まで）
    if depth < 5:
        child_pages = children_dict.get(page['id'], [])
        for child_page in sorted(child_pages, key=lambda x: x.get('title', '')):
            _append_page_tree(result_lines, child_page, children_dict, depth + 1)
    elif children_dict.get(page['id']):
        # 深度制限により省略
        result_lines.append(f"{indent}  📁 ... (子ページ {len(children_dict[page['id']])}件 - 階層深度制限により省略)")


def _get_last_updated(page: Dict[str, Any]) -> str:
    """
    ページの最終更新日時を取得する
    
    Args:
        page: ページ情報
        
    Returns:
        str: 最終更新日時の文字列
    """
    try:
        # 複数のパスを試行
        paths = [
            page.get('history', {}).get('lastUpdated', {}).get('when'),
            page.get('version', {}).get('when'),
            page.get('lastModified', {}).get('when')
        ]
        
        for date_str in paths:
            if date_str:
                # ISO形式の日付を読みやすい形式に変換
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return dt.strftime('%Y-%m-%d %H:%M')
                except:
                    return date_str[:10]  # 日付部分のみ
        
        return '不明'
    except:
        return '不明'


def _get_last_updated_date(page: Dict[str, Any]) -> str:
    """
    ソート用の最終更新日時を取得する
    
    Args:
        page: ページ情報
        
    Returns:
        str: ISO形式の日時文字列（ソート可能）
    """
    try:
        paths = [
            page.get('history', {}).get('lastUpdated', {}).get('when'),
            page.get('version', {}).get('when'),
            page.get('lastModified', {}).get('when')
        ]
        
        for date_str in paths:
            if date_str:
                return date_str
        
        return ''
    except:
        return ''


def get_confluence_page_hierarchy(space_key: str = "CLIENTTOMO") -> Dict[str, Any]:
    """
    Confluenceスペースの階層構造をフィルター用データとして取得する
    
    Args:
        space_key (str): 対象のスペースキー
        
    Returns:
        Dict[str, Any]: 階層構造データ（フィルター用）
    """
    try:
        # Confluence接続の初期化
        confluence = Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        
        logger.info(f"Confluenceページ階層取得開始: {space_key}")
        
        # 最初の20ページ程度を取得（フィルター用なので軽量化）
        pages_result = confluence.get_all_pages_from_space(
            space_key, 
            start=0, 
            limit=20,
            expand='ancestors,space'  # children.pageを除外して軽量化
        )
        
        if not pages_result:
            return {'folders': [], 'error': 'ページが取得できませんでした'}
        
        # 階層構造を分析
        folders = set()
        parent_child_map = {}
        
        for page in pages_result:
            title = page.get('title', '')
            page_id = page.get('id', '')
            ancestors = page.get('ancestors', [])
            
            # ルートレベルのフォルダを特定
            if not ancestors:
                # ルートページ
                folders.add(title)
                parent_child_map[title] = {'id': page_id, 'children': set(), 'level': 0}
            elif len(ancestors) == 1:
                # レベル1フォルダ
                parent_title = ancestors[0].get('title', '')
                folders.add(parent_title)
                folders.add(title)
                
                if parent_title not in parent_child_map:
                    parent_child_map[parent_title] = {'id': ancestors[0].get('id', ''), 'children': set(), 'level': 0}
                if title not in parent_child_map:
                    parent_child_map[title] = {'id': page_id, 'children': set(), 'level': 1}
                
                parent_child_map[parent_title]['children'].add(title)
            elif len(ancestors) >= 2:
                # レベル2以上のフォルダ
                for i, ancestor in enumerate(ancestors):
                    ancestor_title = ancestor.get('title', '')
                    folders.add(ancestor_title)
                    
                    if ancestor_title not in parent_child_map:
                        parent_child_map[ancestor_title] = {
                            'id': ancestor.get('id', ''), 
                            'children': set(), 
                            'level': i
                        }
                
                # 現在のページも追加
                folders.add(title)
                if title not in parent_child_map:
                    parent_child_map[title] = {'id': page_id, 'children': set(), 'level': len(ancestors)}
                
                # 親子関係を設定
                if ancestors:
                    parent_title = ancestors[-1].get('title', '')
                    if parent_title in parent_child_map:
                        parent_child_map[parent_title]['children'].add(title)
        
        # フィルター用の構造化データを作成
        filter_hierarchy = []
        
        # ルートレベルのフォルダを特定
        root_folders = [folder for folder, data in parent_child_map.items() if data['level'] == 0]
        
        for root_folder in sorted(root_folders):
            if root_folder in parent_child_map:
                folder_data = {
                    'name': root_folder,
                    'id': parent_child_map[root_folder]['id'],
                    'level': 0,
                    'children': []
                }
                
                # 子フォルダを追加（レベル1）
                level1_children = [child for child in parent_child_map[root_folder]['children']]
                for child in sorted(level1_children):
                    if child in parent_child_map:
                        child_data = {
                            'name': child,
                            'id': parent_child_map[child]['id'],
                            'level': 1,
                            'children': []
                        }
                        
                        # 子の子フォルダを追加（レベル2）
                        level2_children = [grandchild for grandchild in parent_child_map[child]['children']]
                        for grandchild in sorted(level2_children):
                            if grandchild in parent_child_map:
                                grandchild_data = {
                                    'name': grandchild,
                                    'id': parent_child_map[grandchild]['id'],
                                    'level': 2,
                                    'children': []
                                }
                                child_data['children'].append(grandchild_data)
                        
                        folder_data['children'].append(child_data)
                
                filter_hierarchy.append(folder_data)
        
        logger.info(f"Confluenceページ階層取得完了: {len(filter_hierarchy)}個のルートフォルダ")
        return {
            'folders': filter_hierarchy,
            'total_folders': len(folders),
            'space_key': space_key
        }
        
    except Exception as e:
        logger.error(f"Confluenceページ階層取得エラー: {str(e)}")
        return {
            'folders': [],
            'error': str(e),
            'space_key': space_key
        }


def get_confluence_filter_options() -> Dict[str, Any]:
    """
    Confluence APIから現在利用可能なフィルター項目を取得する
    
    Returns:
        Dict[str, Any]: スペース一覧、作成者一覧などの情報
    """
    cache_key = "confluence_filter_options"
    
    # キャッシュから取得を試行（1時間有効）
    try:
        cached_options = cache_manager.get(cache_key)
        if cached_options:
            logger.info("Confluenceフィルター項目をキャッシュから取得")
            return cached_options
    except Exception as e:
        logger.warning(f"キャッシュ取得エラー (キーをクリアします): {str(e)}")
        # キャッシュが破損している場合はクリアして継続
        try:
            cache_manager.delete(cache_key)
        except:
            pass
    
    try:
        # Confluence接続の初期化
        confluence = Confluence(
            url=f"https://{settings.atlassian_domain}",
            username=settings.atlassian_email,
            password=settings.atlassian_api_token
        )
        
        logger.info("Confluence APIからフィルター項目を取得中...")
        
        # 各種フィルター項目を取得
        filter_options = {
            'spaces': _get_confluence_spaces(confluence),
            'content_types': ['page', 'blogpost'],  # 固定値
            'authors': _get_confluence_authors(confluence)
        }
        
        # キャッシュに保存（1時間有効）
        try:
            cache_manager.set(cache_key, filter_options, duration_hours=1)
        except Exception as e:
            logger.warning(f"キャッシュ保存エラー: {str(e)}")
        
        logger.info("Confluenceフィルター項目の取得完了")
        return filter_options
        
    except Exception as e:
        logger.error(f"Confluenceフィルター項目取得エラー: {str(e)}")
        # エラー時はデフォルト値を返す
        return {
            'spaces': ['CLIENTTOMO'],  # デフォルトスペース
            'content_types': ['page', 'blogpost'],
            'authors': []
        }


def _get_confluence_spaces(confluence: Confluence) -> List[str]:
    """
    Confluenceから利用可能なスペース一覧を取得する
    
    Args:
        confluence: Confluence APIクライアント
        
    Returns:
        List[str]: スペースキーのリスト
    """
    try:
        spaces = confluence.get_all_spaces()
        space_keys = [space.get('key', '') for space in spaces.get('results', [])]
        # 空文字列を除外
        space_keys = [key for key in space_keys if key]
        logger.info(f"Confluenceスペース取得: {len(space_keys)}個")
        return space_keys
    except Exception as e:
        logger.warning(f"Confluenceスペース取得エラー: {str(e)}")
        return ['CLIENTTOMO']  # デフォルトスペース


def _get_confluence_authors(confluence: Confluence) -> List[str]:
    """
    Confluenceページの作成者一覧を取得する（サンプルページから）
    
    Args:
        confluence: Confluence APIクライアント
        
    Returns:
        List[str]: 作成者のユーザー名またはアカウントIDのリスト
    """
    try:
        # 最近のページから作成者を収集（制限あり）
        cql_query = 'type = page order by created desc'
        search_result = confluence.cql(cql_query, limit=50)
        
        authors = set()
        if search_result and 'results' in search_result:
            for page in search_result['results']:
                creator = page.get('creator', {})
                if creator:
                    # displayNameまたはaccountIdを使用
                    author_name = creator.get('displayName') or creator.get('accountId', '')
                    if author_name:
                        authors.add(author_name)
        
        author_list = list(authors)
        logger.info(f"Confluence作成者取得: {len(author_list)}人")
        return author_list[:20]  # 最大20人まで
        
    except Exception as e:
        logger.warning(f"Confluence作成者取得エラー: {str(e)}")
        return []