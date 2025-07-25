#!/usr/bin/env python3
"""
API通信詳細ログミドルウェア

Atlassian API（Jira/Confluence）とGemini APIの入出力を
詳細にログ記録するためのミドルウェアクラスです。
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from src.spec_bot.config.settings import Settings


class ApiLoggingMiddleware:
    """API通信詳細ログミドルウェア"""
    
    def __init__(self, detailed_logger=None):
        """
        ミドルウェアの初期化
        
        Args:
            detailed_logger: DetailedOutputLoggerのインスタンス
        """
        self.detailed_logger = detailed_logger
        self.current_question_id = None
    
    def set_question_id(self, question_id: str):
        """現在処理中の質問IDを設定"""
        self.current_question_id = question_id
    
    # === Gemini API ログ記録 ===
    
    def log_gemini_request(
        self, 
        prompt: str, 
        model: str = None, 
        temperature: float = 0.1,
        max_tokens: int = 2048,
        request_type: str = "unknown"
    ):
        """Gemini APIリクエストをログ記録"""
        # settingsからモデル名を取得
        if model is None:
            from src.spec_bot.config.settings import Settings
            settings = Settings()
            model = settings.gemini_model
        if not self.detailed_logger or not self.current_question_id:
            return
        
        request_data = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "prompt": prompt
        }
        
        # 基本ログ
        self.detailed_logger.log_api_request(
            self.current_question_id, 
            "Gemini", 
            request_data
        )
        
        # フルプロンプトログ
        self.detailed_logger.log_full_prompt(
            self.current_question_id,
            f"Gemini_{response}",
            prompt
        )
    
    def log_gemini_response(
        self, 
        response_text: str, 
        execution_time: float = 0,
        token_usage: Optional[Dict[str, int]] = None,
        request_type: str = "unknown"
    ):
        """Gemini APIレスポンスをログ記録"""
        if not self.detailed_logger or not self.current_question_id:
            return
        
        response_data = {
            "response": response_text,
            "execution_time": execution_time,
            "usage": token_usage or {}
        }
        
        self.detailed_logger.log_api_response(
            self.current_question_id,
            "Gemini",
            response_data
        )
    
    # === Confluence API ログ記録 ===
    
    def log_confluence_request(
        self,
        cql_query: str,
        space_key: str = "",
        limit: int = 25,
        start: int = 0,
        expand: List[str] = None
    ):
        """Confluence APIリクエストをログ記録"""
        if not self.detailed_logger or not self.current_question_id:
            return
        
        request_data = {
            "cql": cql_query,
            "space_key": space_key,
            "limit": limit,
            "start": start,
            "expand": expand or []
        }
        
        self.detailed_logger.log_api_request(
            self.current_question_id,
            "Confluence",
            request_data
        )
    
    def log_confluence_response(
        self,
        pages: List[Dict[str, Any]],
        total_size: int = 0,
        execution_time: float = 0
    ):
        """Confluence APIレスポンスをログ記録"""
        if not self.detailed_logger or not self.current_question_id:
            return
        
        # ページ情報を整理
        page_summaries = []
        for page in pages[:5]:  # 最初の5件のみ詳細記録
            page_info = {
                "id": page.get("id", ""),
                "title": page.get("title", ""),
                "space_key": page.get("space", {}).get("key", ""),
                "content_preview": page.get("body", {}).get("storage", {}).get("value", "")[:100]
            }
            page_summaries.append(page_info)
        
        response_data = {
            "results": page_summaries,
            "size": len(pages),
            "total_size": total_size,
            "execution_time": execution_time
        }
        
        self.detailed_logger.log_api_response(
            self.current_question_id,
            "Confluence",
            response_data
        )
    
    # === Jira API ログ記録 ===
    
    def log_jira_request(
        self,
        jql_query: str,
        max_results: int = 50,
        start_at: int = 0,
        fields: List[str] = None,
        expand: List[str] = None
    ):
        """Jira APIリクエストをログ記録"""
        if not self.detailed_logger or not self.current_question_id:
            return
        
        request_data = {
            "jql": jql_query,
            "max_results": max_results,
            "start_at": start_at,
            "fields": fields or [],
            "expand": expand or []
        }
        
        self.detailed_logger.log_api_request(
            self.current_question_id,
            "Jira",
            request_data
        )
    
    def log_jira_response(
        self,
        issues: List[Dict[str, Any]],
        total: int = 0,
        execution_time: float = 0
    ):
        """Jira APIレスポンスをログ記録"""
        if not self.detailed_logger or not self.current_question_id:
            return
        
        # チケット情報を整理
        issue_summaries = []
        for issue in issues[:5]:  # 最初の5件のみ詳細記録
            fields = issue.get("fields", {})
            issue_info = {
                "key": issue.get("key", ""),
                "summary": fields.get("summary", ""),
                "status": fields.get("status", {}).get("name", ""),
                "priority": fields.get("priority", {}).get("name", ""),
                "assignee": fields.get("assignee", {}).get("displayName", "未割り当て") if fields.get("assignee") else "未割り当て",
                "created": fields.get("created", ""),
                "updated": fields.get("updated", "")
            }
            issue_summaries.append(issue_info)
        
        response_data = {
            "issues": issue_summaries,
            "total": total,
            "returned_count": len(issues),
            "execution_time": execution_time
        }
        
        self.detailed_logger.log_api_response(
            self.current_question_id,
            "Jira",
            response_data
        )
    
    # === ユーティリティメソッド ===
    
    def start_api_timing(self) -> float:
        """API呼び出し開始時刻を記録"""
        return time.time()
    
    def calculate_execution_time(self, start_time: float) -> float:
        """実行時間を計算"""
        return time.time() - start_time
    
    def is_logging_enabled(self) -> bool:
        """ログ記録が有効かどうかを確認"""
        return self.detailed_logger is not None and self.current_question_id is not None 