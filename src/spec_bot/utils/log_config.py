"""
ログ設定管理

アプリケーション全体のログ設定を統一的に管理します。
コンソール出力とファイル出力の両方をサポートします。
"""

import logging
import logging.handlers
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from ..config.constants import APP_CONSTANTS


class DetailedOutputLogger:
    """
    詳細な出力記録用ロガー
    
    各段階の結果を構造化してファイルに保存します。
    """
    
    def __init__(self, log_dir: str = "logs", session_id: str = None):
        """詳細出力ロガーの初期化"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # セッションIDを生成または使用
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = session_id
        
        # 出力ファイルパス
        self.session_log_file = self.log_dir / f"session_{session_id}.json"
        self.detailed_log_file = self.log_dir / f"detailed_{session_id}.log"
        
        # セッション開始ログ
        self.session_data = {
            "session_id": session_id,
            "start_time": datetime.now().isoformat(),
            "questions": []
        }
        
        self._save_session_data()
    
    def log_question_start(self, question: str, filters: Optional[Dict] = None) -> str:
        """質問処理開始をログ記録"""
        question_id = f"q_{len(self.session_data['questions']) + 1}"
        
        question_data = {
            "question_id": question_id,
            "question": question,
            "filters": filters,
            "start_time": datetime.now().isoformat(),
            "step1_analysis": None,
            "step2_search": None,
            "step3_synthesis": None,
            "performance": {},
            "end_time": None
        }
        
        self.session_data["questions"].append(question_data)
        self._save_session_data()
        
        # 詳細ログにも記録
        self._write_detailed_log(f"=== 質問処理開始: {question} ===")
        
        return question_id
    
    def log_step1_result(self, question_id: str, analysis_result: Dict[str, Any]):
        """Step1分析結果をログ記録（最適化版）"""
        question_data = self._get_question_data(question_id)
        if question_data:
            question_data["step1_analysis"] = analysis_result
            self._save_session_data()
            
            # 詳細ログ（要約版）
            search_strategy = analysis_result.get('search_strategy', {})
            keywords = analysis_result.get('keywords', {})
            primary_keywords = keywords.get('primary', [])[:3]  # 最初の3つのみ
            
            self._write_detailed_log(f"Step1分析結果 ({question_id}):")
            self._write_detailed_log(f"  戦略: {search_strategy.get('method', 'unknown')}")
            self._write_detailed_log(f"  主要キーワード: {', '.join(primary_keywords)}")
            self._write_detailed_log(f"  検索対象: {'Jira' if analysis_result.get('search_targets', {}).get('jira') else ''}{'Confluence' if analysis_result.get('search_targets', {}).get('confluence') else ''}")
    
    def log_step2_result(self, question_id: str, search_result: Dict[str, Any]):
        """Step2検索結果をログ記録（最適化版）"""
        question_data = self._get_question_data(question_id)
        if question_data:
            question_data["step2_search"] = search_result
            self._save_session_data()
            
            # 詳細ログ（要約版）- 安全なリスト処理
            jira_results = search_result.get('jira_results') or []
            confluence_results = search_result.get('confluence_results') or []
            
            jira_count = len(jira_results) if isinstance(jira_results, list) else 0
            confluence_count = len(confluence_results) if isinstance(confluence_results, list) else 0
            
            self._write_detailed_log(f"Step2検索結果 ({question_id}):")
            self._write_detailed_log(f"  Jira結果: {jira_count}件")
            self._write_detailed_log(f"  Confluence結果: {confluence_count}件")
            self._write_detailed_log(f"  総ソース数: {jira_count + confluence_count}件")
    
    def log_step3_result(self, question_id: str, synthesis_result: Dict[str, Any]):
        """Step3統合結果をログ記録（最適化版）"""
        question_data = self._get_question_data(question_id)
        if question_data:
            question_data["step3_synthesis"] = synthesis_result
            self._save_session_data()
            
            # 詳細ログ（要約版）- 安全なデータアクセス
            total_sources = synthesis_result.get('total_sources', 0) if synthesis_result else 0
            filtered_sources = synthesis_result.get('filtered_sources', 0) if synthesis_result else 0
            
            summary_data = synthesis_result.get('summary') or {} if synthesis_result else {}
            confidence = summary_data.get('confidence', 0) if isinstance(summary_data, dict) else 0
            summary_text = summary_data.get('summary_text', '') if isinstance(summary_data, dict) else ''
            summary_length = len(summary_text) if isinstance(summary_text, str) else 0
            
            self._write_detailed_log(f"Step3統合結果 ({question_id}):")
            self._write_detailed_log(f"  ソース: {total_sources}→{filtered_sources}件")
            self._write_detailed_log(f"  信頼度: {confidence*100:.1f}%")
            self._write_detailed_log(f"  要約長: {summary_length}文字")
    
    def log_performance(self, question_id: str, performance_data: Dict[str, Any]):
        """パフォーマンス情報をログ記録"""
        question_data = self._get_question_data(question_id)
        if question_data:
            question_data["performance"] = performance_data
            self._save_session_data()
    
    def log_question_end(self, question_id: str):
        """質問処理終了をログ記録"""
        question_data = self._get_question_data(question_id)
        if question_data:
            question_data["end_time"] = datetime.now().isoformat()
            self._save_session_data()
            
            # 詳細ログ
            self._write_detailed_log(f"=== 質問処理完了: {question_id} ===\n")
    
    def log_api_request(self, question_id: str, api_type: str, request_data: Dict[str, Any]):
        """API リクエストをログ記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self._write_detailed_log(f"=== {api_type} API リクエスト ({question_id}) ===")
        
        if api_type.lower() == "jira":
            jql_query = request_data.get("jql", "")
            max_results = request_data.get("max_results", 50)
            fields = request_data.get("fields", [])
            
            self._write_detailed_log(f"JQLクエリ: {jql_query}")
            self._write_detailed_log(f"最大取得件数: {max_results}")
            self._write_detailed_log(f"取得フィールド: {', '.join(fields) if fields else 'デフォルト'}")
            
        elif api_type.lower() == "confluence":
            cql_query = request_data.get("cql", "")
            limit = request_data.get("limit", 25)
            space_key = request_data.get("space_key", "")
            
            self._write_detailed_log(f"CQLクエリ: {cql_query}")
            self._write_detailed_log(f"最大取得件数: {limit}")
            self._write_detailed_log(f"検索スペース: {space_key}")
            
        elif api_type.lower() == "gemini":
            model = request_data.get("model", "")
            temperature = request_data.get("temperature", 0.1)
            max_tokens = request_data.get("max_tokens", 2048)
            prompt_preview = request_data.get("prompt", "")[:200] + "..." if len(request_data.get("prompt", "")) > 200 else request_data.get("prompt", "")
            
            self._write_detailed_log(f"モデル: {model}")
            self._write_detailed_log(f"Temperature: {temperature}")
            self._write_detailed_log(f"Max Tokens: {max_tokens}")
            self._write_detailed_log(f"プロンプト (先頭200文字): {prompt_preview}")
        
        self._write_detailed_log(f"リクエスト時刻: {timestamp}")
    
    def log_api_response(self, question_id: str, api_type: str, response_data: Dict[str, Any]):
        """API レスポンスをログ記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self._write_detailed_log(f"=== {api_type} API レスポンス ({question_id}) ===")
        
        if api_type.lower() == "jira":
            issues = response_data.get("issues", [])
            total = response_data.get("total", 0)
            
            self._write_detailed_log(f"取得チケット数: {len(issues)}/{total}")
            
            for i, issue in enumerate(issues[:3], 1):  # 最初の3件のみ詳細表示
                key = issue.get("key", "")
                summary = issue.get("fields", {}).get("summary", "")
                status = issue.get("fields", {}).get("status", {}).get("name", "")
                
                self._write_detailed_log(f"  チケット{i}: {key} - {summary} [{status}]")
                
            if len(issues) > 3:
                self._write_detailed_log(f"  ... 他{len(issues) - 3}件")
                
        elif api_type.lower() == "confluence":
            results = response_data.get("results", [])
            size = response_data.get("size", 0)
            
            self._write_detailed_log(f"取得ページ数: {len(results)}")
            
            for i, page in enumerate(results[:3], 1):  # 最初の3件のみ詳細表示
                title = page.get("title", "")
                page_id = page.get("id", "")
                space_key = page.get("space", {}).get("key", "")
                
                self._write_detailed_log(f"  ページ{i}: [{space_key}] {title} (ID: {page_id})")
                
            if len(results) > 3:
                self._write_detailed_log(f"  ... 他{len(results) - 3}件")
                
        elif api_type.lower() == "gemini":
            response_text = response_data.get("response", "")
            usage = response_data.get("usage", {})
            
            response_preview = response_text[:300] + "..." if len(response_text) > 300 else response_text
            self._write_detailed_log(f"レスポンス (先頭300文字): {response_preview}")
            
            if usage:
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                
                self._write_detailed_log(f"トークン使用量: プロンプト{prompt_tokens} + 生成{completion_tokens} = 合計{total_tokens}")
        
        self._write_detailed_log(f"レスポンス時刻: {timestamp}")
        self._write_detailed_log("")  # 空行で区切り
    
    def log_full_prompt(self, question_id: str, prompt_type: str, full_prompt: str):
        """完全なプロンプトをログ記録"""
        self._write_detailed_log(f"=== {prompt_type} フルプロンプト ({question_id}) ===")
        self._write_detailed_log(full_prompt)
        self._write_detailed_log("=== プロンプト終了 ===")
        self._write_detailed_log("")
    
    def log_final_output(self, question_id: str, final_answer: str, confidence: float, sources_count: int):
        """最終的なチャットボット出力をログ記録"""
        self._write_detailed_log(f"=== 最終出力 ({question_id}) ===")
        self._write_detailed_log(f"信頼度: {confidence*100:.1f}%")
        self._write_detailed_log(f"参照ソース数: {sources_count}件")
        self._write_detailed_log(f"最終回答:")
        self._write_detailed_log(final_answer)
        self._write_detailed_log("=== 最終出力終了 ===")
        self._write_detailed_log("")
    
    def _get_question_data(self, question_id: str) -> Optional[Dict]:
        """質問データを取得"""
        for q_data in self.session_data["questions"]:
            if q_data["question_id"] == question_id:
                return q_data
        return None
    
    def _save_session_data(self):
        """セッションデータをファイルに保存"""
        with open(self.session_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, ensure_ascii=False, indent=2)
    
    def _write_detailed_log(self, message: str):
        """詳細ログをファイルに書き込み"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.detailed_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def save_compact_session_summary(self) -> str:
        """コンパクトなセッション要約をファイルに保存"""
        summary_file = self.log_dir / f"session_summary_{self.session_id}.json"
        
        # コンパクトな要約データを作成
        compact_summary = {
            "session_id": self.session_id,
            "start_time": self.session_data["start_time"],
            "end_time": datetime.now().isoformat(),
            "total_questions": len(self.session_data["questions"]),
            "questions_summary": []
        }
        
        for q_data in self.session_data["questions"]:
            # 安全なデータアクセス
            step3_synthesis = q_data.get("step3_synthesis") or {}
            step1_analysis = q_data.get("step1_analysis") or {}
            search_strategy = step1_analysis.get("search_strategy") or {}
            summary_data = step3_synthesis.get("summary") or {}
            
            # 実行時間の安全な計算
            execution_time = 0
            if q_data.get("end_time") and q_data.get("start_time"):
                try:
                    end_time = datetime.fromisoformat(q_data["end_time"])
                    start_time = datetime.fromisoformat(q_data["start_time"])
                    execution_time = (end_time - start_time).total_seconds()
                except (ValueError, TypeError):
                    execution_time = 0
            
            question_summary = {
                "question_id": q_data.get("question_id", "unknown"),
                "question": q_data.get("question", ""),
                "success": step3_synthesis is not None and len(step3_synthesis) > 0,
                "execution_time": execution_time,
                "search_strategy": search_strategy.get("method", "unknown"),
                "total_sources": step3_synthesis.get("total_sources", 0),
                "filtered_sources": step3_synthesis.get("filtered_sources", 0),
                "confidence": summary_data.get("confidence", 0)
            }
            compact_summary["questions_summary"].append(question_summary)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(compact_summary, f, ensure_ascii=False, indent=2)
        
        return str(summary_file)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """セッション要約を取得"""
        total_questions = len(self.session_data["questions"])
        successful_questions = sum(1 for q in self.session_data["questions"] 
                                 if q.get("step3_synthesis") and not q.get("error"))
        
        # コンパクト要約も生成
        compact_file = self.save_compact_session_summary()
        
        return {
            "session_id": self.session_id,
            "total_questions": total_questions,
            "successful_questions": successful_questions,
            "success_rate": successful_questions / total_questions if total_questions > 0 else 0,
            "session_file": str(self.session_log_file),
            "detailed_file": str(self.detailed_log_file),
            "compact_summary_file": compact_file
        }


def setup_logging(
    log_level: str = "INFO",
    enable_file_logging: bool = True,
    log_file_path: str = None
) -> logging.Logger:
    """
    アプリケーション用のログ設定をセットアップ
    
    Args:
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        enable_file_logging: ファイル出力を有効にするかどうか
        log_file_path: ログファイルのパス（Noneの場合はデフォルトパスを使用）
        
    Returns:
        logging.Logger: 設定されたロガー
    """
    
    # ルートロガーを取得
    root_logger = logging.getLogger()
    
    # 既存のハンドラーをクリア（重複を避けるため）
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # ログレベルを設定
    log_level_obj = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level_obj)
    
    # フォーマッターを作成
    formatter = logging.Formatter(
        fmt=APP_CONSTANTS.LOGGING.FORMAT,
        datefmt=APP_CONSTANTS.LOGGING.DATE_FORMAT
    )
    
    # コンソールハンドラーを設定
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level_obj)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラーを設定
    if enable_file_logging:
        # ログファイルパスを決定
        if log_file_path is None:
            # プロジェクトルートからの相対パスを設定
            project_root = Path(__file__).parent.parent.parent.parent
            log_file_path = project_root / APP_CONSTANTS.LOGGING.LOG_FILE
        else:
            log_file_path = Path(log_file_path)
        
        # ログディレクトリを作成
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ローテーティングファイルハンドラーを作成
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file_path,
            maxBytes=APP_CONSTANTS.LOGGING.MAX_FILE_SIZE,
            backupCount=APP_CONSTANTS.LOGGING.BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level_obj)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # セットアップ完了ログを出力
        logger = logging.getLogger(__name__)
        logger.info(f"ログ設定完了 - ファイル出力: {log_file_path}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得
    
    Args:
        name: ロガー名（通常は__name__を使用）
        
    Returns:
        logging.Logger: ロガーインスタンス
    """
    return logging.getLogger(name)


def log_agent_activity(
    logger: logging.Logger,
    action: str,
    query: str = None,
    result_count: int = None,
    execution_time: float = None,
    error: Exception = None
):
    """
    エージェントの活動をログに記録
    
    Args:
        logger: ロガーインスタンス
        action: 実行されたアクション
        query: 実行されたクエリ
        result_count: 結果件数
        execution_time: 実行時間（秒）
        error: エラーが発生した場合のException
    """
    log_data = {
        'action': action,
        'query': query,
        'result_count': result_count,
        'execution_time': execution_time
    }
    
    # エラーがある場合
    if error:
        logger.error(f"エラー発生 - {action}: {str(error)}", extra=log_data)
    else:
        # 正常実行の場合
        message_parts = [f"実行完了 - {action}"]
        if query:
            message_parts.append(f"クエリ: '{query}'")
        if result_count is not None:
            message_parts.append(f"結果: {result_count}件")
        if execution_time is not None:
            message_parts.append(f"実行時間: {execution_time:.2f}秒")
        
        message = " | ".join(message_parts)
        logger.info(message, extra=log_data)


def log_search_results(
    logger: logging.Logger,
    search_type: str,
    query: str,
    results: list,
    total_count: int = None,
    execution_time: float = None
):
    """
    検索結果をログに記録
    
    Args:
        logger: ロガーインスタンス
        search_type: 検索タイプ（Jira, Confluence等）
        query: 検索クエリ
        results: 検索結果リスト
        total_count: 総件数
        execution_time: 実行時間（秒）
    """
    result_count = len(results) if results else 0
    
    log_data = {
        'search_type': search_type,
        'query': query,
        'result_count': result_count,
        'total_count': total_count,
        'execution_time': execution_time
    }
    
    message_parts = [f"{search_type}検索実行"]
    message_parts.append(f"クエリ: '{query}'")
    message_parts.append(f"結果: {result_count}件")
    if total_count and total_count != result_count:
        message_parts.append(f"（総数: {total_count}件）")
    if execution_time:
        message_parts.append(f"実行時間: {execution_time:.2f}秒")
    
    message = " | ".join(message_parts)
    logger.info(message, extra=log_data)
    
    # デバッグレベルで詳細情報をログ出力
    if results and logger.isEnabledFor(logging.DEBUG):
        for i, result in enumerate(results[:3], 1):  # 最初の3件のみ
            if isinstance(result, dict):
                title = result.get('title', result.get('summary', 'タイトルなし'))
                logger.debug(f"  {i}. {title}") 