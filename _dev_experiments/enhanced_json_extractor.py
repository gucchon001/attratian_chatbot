#!/usr/bin/env python3
"""
改善されたJSON抽出ロジック

軽微なsyntax errorを自動修正し、抽出精度を大幅に向上
"""

import json
import re
from typing import Optional, Dict, Any, List, Tuple


class EnhancedJsonExtractor:
    """改善されたJSON抽出クラス"""
    
    def __init__(self):
        self.extraction_attempts = []
        self.debug_mode = True
    
    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        レスポンステキストからJSONを抽出（改善版）
        
        Args:
            response_text: LLMからの生応答テキスト
            
        Returns:
            抽出されたJSON辞書、失敗時はNone
        """
        self.extraction_attempts = []
        
        if not response_text or not response_text.strip():
            self._log_attempt("empty_response", False, "応答テキストが空")
            return None
        
        # 手法1: 直接JSON.loads試行
        result = self._try_direct_json_loads(response_text)
        if result:
            return result
        
        # 手法2: マークダウンコードブロック抽出
        result = self._try_markdown_extraction(response_text)
        if result:
            return result
        
        # 手法3: 正規表現でJSON部分抽出
        result = self._try_regex_extraction(response_text)
        if result:
            return result
        
        # 手法4: JSON構文修復試行
        result = self._try_json_repair(response_text)
        if result:
            return result
        
        # 手法5: 部分JSON抽出
        result = self._try_partial_json_extraction(response_text)
        if result:
            return result
        
        self._log_attempt("all_methods_failed", False, "すべての手法が失敗")
        return None
    
    def _try_direct_json_loads(self, text: str) -> Optional[Dict[str, Any]]:
        """直接JSON.loads試行"""
        try:
            result = json.loads(text.strip())
            self._log_attempt("direct_json_loads", True, f"成功: {type(result)}")
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError as e:
            self._log_attempt("direct_json_loads", False, f"JSONDecodeError: {e}")
            return None
        except Exception as e:
            self._log_attempt("direct_json_loads", False, f"その他エラー: {e}")
            return None
    
    def _try_markdown_extraction(self, text: str) -> Optional[Dict[str, Any]]:
        """マークダウンコードブロックからの抽出"""
        patterns = [
            r'```json\n?(.*?)```',
            r'```\n?(.*?)```',
            r'`(.*?)`'
        ]
        
        for i, pattern in enumerate(patterns, 1):
            try:
                matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
                for j, match in enumerate(matches):
                    cleaned_match = match.strip()
                    if not cleaned_match:
                        continue
                    
                    try:
                        result = json.loads(cleaned_match)
                        if isinstance(result, dict):
                            self._log_attempt(f"markdown_pattern_{i}_match_{j}", True, 
                                            f"成功: {len(cleaned_match)}文字")
                            return result
                    except json.JSONDecodeError:
                        # JSON修復を試行
                        repaired = self._repair_json_string(cleaned_match)
                        if repaired:
                            try:
                                result = json.loads(repaired)
                                if isinstance(result, dict):
                                    self._log_attempt(f"markdown_pattern_{i}_match_{j}_repaired", True,
                                                    f"修復成功: {len(repaired)}文字")
                                    return result
                            except json.JSONDecodeError:
                                pass
                        
                        self._log_attempt(f"markdown_pattern_{i}_match_{j}", False, 
                                        f"JSON無効: {cleaned_match[:50]}...")
            except Exception as e:
                self._log_attempt(f"markdown_pattern_{i}", False, f"パターンエラー: {e}")
        
        return None
    
    def _try_regex_extraction(self, text: str) -> Optional[Dict[str, Any]]:
        """正規表現でJSON部分抽出"""
        patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # ネストした{}対応
            r'\{.*?\}',  # 基本的な{}抽出
            r'(\{(?:[^{}]|{[^{}]*})*\})',  # より柔軟な{}抽出
            r'分析結果:\s*(\{.*?\})',  # 分析結果ラベル後
            r'回答:\s*(\{.*?\})',  # 回答ラベル後
        ]
        
        for i, pattern in enumerate(patterns, 1):
            try:
                matches = re.findall(pattern, text, re.DOTALL)
                for j, match in enumerate(matches):
                    if not match.strip():
                        continue
                    
                    # 直接試行
                    try:
                        result = json.loads(match)
                        if isinstance(result, dict):
                            self._log_attempt(f"regex_pattern_{i}_match_{j}", True,
                                            f"成功: {len(match)}文字")
                            return result
                    except json.JSONDecodeError:
                        pass
                    
                    # JSON修復試行
                    repaired = self._repair_json_string(match)
                    if repaired:
                        try:
                            result = json.loads(repaired)
                            if isinstance(result, dict):
                                self._log_attempt(f"regex_pattern_{i}_match_{j}_repaired", True,
                                                f"修復成功: {len(repaired)}文字")
                                return result
                        except json.JSONDecodeError:
                            pass
                    
                    self._log_attempt(f"regex_pattern_{i}_match_{j}", False,
                                    f"JSON無効: {match[:50]}...")
            except Exception as e:
                self._log_attempt(f"regex_pattern_{i}", False, f"パターンエラー: {e}")
        
        return None
    
    def _try_json_repair(self, text: str) -> Optional[Dict[str, Any]]:
        """JSON構文修復試行"""
        # 最も大きな{}ブロックを探す
        json_candidates = self._find_json_candidates(text)
        
        for i, candidate in enumerate(json_candidates):
            repaired = self._repair_json_string(candidate)
            if repaired:
                try:
                    result = json.loads(repaired)
                    if isinstance(result, dict):
                        self._log_attempt(f"json_repair_candidate_{i}", True,
                                        f"修復成功: {len(repaired)}文字")
                        return result
                except json.JSONDecodeError:
                    pass
                
                self._log_attempt(f"json_repair_candidate_{i}", False,
                                f"修復失敗: {candidate[:50]}...")
        
        return None
    
    def _try_partial_json_extraction(self, text: str) -> Optional[Dict[str, Any]]:
        """部分JSON抽出（必要最小限の項目）"""
        # 最低限必要な項目を抽出して構築
        try:
            # search_targets の抽出
            search_targets = self._extract_search_targets(text)
            question_type = self._extract_question_type(text)
            keywords = self._extract_keywords(text)
            search_strategy = self._extract_search_strategy(text)
            
            if search_targets or question_type or keywords or search_strategy:
                result = {
                    "search_targets": search_targets or {
                        "jira": True,
                        "confluence": True,
                        "priority": "parallel"
                    },
                    "question_type": question_type or {
                        "category": "hybrid",
                        "confidence": 0.5
                    },
                    "keywords": keywords or {
                        "primary": ["未抽出"],
                        "synonyms": []
                    },
                    "search_strategy": search_strategy or {
                        "method": "basic_keyword",
                        "reason": "部分抽出のためフォールバック"
                    }
                }
                
                self._log_attempt("partial_extraction", True, "部分抽出成功")
                return result
        except Exception as e:
            self._log_attempt("partial_extraction", False, f"部分抽出エラー: {e}")
        
        return None
    
    def _repair_json_string(self, json_str: str) -> Optional[str]:
        """JSON文字列の修復"""
        if not json_str.strip():
            return None
        
        # 基本的なクリーニング
        cleaned = json_str.strip()
        
        # よくある問題の修正
        repairs = [
            # 末尾のカンマ削除
            (r',\s*}', '}'),
            (r',\s*]', ']'),
            # 不正な改行の修正
            (r'\n\s*}', '\n}'),
            (r'\n\s*]', '\n]'),
            # クォートの修正
            (r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":'),
            # 値のクォート修正（数値・boolean以外）
            (r':\s*([^",\[\]{}\s]+)(?=\s*[,}])', r': "\1"'),
        ]
        
        for pattern, replacement in repairs:
            try:
                cleaned = re.sub(pattern, replacement, cleaned)
            except Exception:
                continue
        
        # 修復後にJSONとして有効か確認
        try:
            json.loads(cleaned)
            return cleaned
        except json.JSONDecodeError:
            return None
    
    def _find_json_candidates(self, text: str) -> List[str]:
        """JSON候補文字列を探す"""
        candidates = []
        
        # {} で囲まれた部分をすべて抽出
        brace_stack = []
        start_idx = None
        
        for i, char in enumerate(text):
            if char == '{':
                if not brace_stack:
                    start_idx = i
                brace_stack.append(char)
            elif char == '}':
                if brace_stack and brace_stack[-1] == '{':
                    brace_stack.pop()
                    if not brace_stack and start_idx is not None:
                        candidate = text[start_idx:i+1]
                        if len(candidate) > 10:  # 最小長チェック
                            candidates.append(candidate)
        
        # 長い順にソート（より完全なJSONを優先）
        candidates.sort(key=len, reverse=True)
        return candidates[:5]  # 上位5候補
    
    def _extract_search_targets(self, text: str) -> Optional[Dict[str, Any]]:
        """search_targets部分の抽出"""
        pattern = r'"search_targets"\s*:\s*\{([^}]+)\}'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                content = '{' + match.group(1) + '}'
                # 簡易パース
                jira = 'true' in content.lower() if 'jira' in content else False
                confluence = 'true' in content.lower() if 'confluence' in content else True
                priority = "confluence_first" if confluence and not jira else "parallel"
                
                return {
                    "jira": jira,
                    "confluence": confluence,
                    "priority": priority
                }
            except Exception:
                pass
        return None
    
    def _extract_question_type(self, text: str) -> Optional[Dict[str, Any]]:
        """question_type部分の抽出"""
        pattern = r'"category"\s*:\s*"([^"]+)"'
        match = re.search(pattern, text)
        if match:
            category = match.group(1)
            confidence = 0.8 if category in ["specification", "feature_explanation"] else 0.5
            return {
                "category": category,
                "confidence": confidence
            }
        return None
    
    def _extract_keywords(self, text: str) -> Optional[Dict[str, Any]]:
        """keywords部分の抽出"""
        primary_pattern = r'"primary"\s*:\s*\[([^\]]+)\]'
        primary_match = re.search(primary_pattern, text)
        
        if primary_match:
            try:
                # 簡易的にキーワードを抽出
                primary_content = primary_match.group(1)
                keywords = [k.strip().strip('"') for k in primary_content.split(',')]
                keywords = [k for k in keywords if k]
                
                return {
                    "primary": keywords,
                    "synonyms": []
                }
            except Exception:
                pass
        return None
    
    def _extract_search_strategy(self, text: str) -> Optional[Dict[str, Any]]:
        """search_strategy部分の抽出"""
        method_pattern = r'"method"\s*:\s*"([^"]+)"'
        method_match = re.search(method_pattern, text)
        
        if method_match:
            method = method_match.group(1)
            return {
                "method": method,
                "reason": f"{method}戦略を選択"
            }
        return None
    
    def _log_attempt(self, method: str, success: bool, details: str):
        """抽出試行のログ記録"""
        self.extraction_attempts.append({
            "method": method,
            "success": success,
            "details": details
        })
        
        if self.debug_mode:
            status = "✅" if success else "❌"
            print(f"      {status} {method}: {details}")
    
    def get_extraction_report(self) -> Dict[str, Any]:
        """抽出処理のレポートを返す"""
        successful = [a for a in self.extraction_attempts if a["success"]]
        failed = [a for a in self.extraction_attempts if not a["success"]]
        
        return {
            "total_attempts": len(self.extraction_attempts),
            "successful_attempts": len(successful),
            "failed_attempts": len(failed),
            "success_rate": len(successful) / len(self.extraction_attempts) if self.extraction_attempts else 0,
            "attempts": self.extraction_attempts
        }


def test_enhanced_extractor():
    """改善された抽出器のテスト"""
    
    # テストケース
    test_cases = [
        {
            "name": "正常なJSON",
            "text": '''```json
{
  "search_targets": {
    "jira": false,
    "confluence": true,
    "priority": "confluence_first"
  },
  "question_type": {
    "category": "specification",
    "confidence": 0.9
  }
}```''',
            "expected_success": True
        },
        {
            "name": "末尾カンマエラー",
            "text": '''```json
{
  "search_targets": {
    "jira": false,
    "confluence": true,
    "priority": "confluence_first",
  },
  "question_type": {
    "category": "specification",
    "confidence": 0.9,
  },
}```''',
            "expected_success": True
        },
        {
            "name": "部分的なJSON",
            "text": '''回答として以下を分析します：
"search_targets": {
  "confluence": true,
  "priority": "confluence_first"
}
"question_type": {
  "category": "specification"
}''',
            "expected_success": True
        }
    ]
    
    extractor = EnhancedJsonExtractor()
    
    print("🧪 改善されたJSON抽出器のテスト")
    print("="*60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 テスト {i}: {test_case['name']}")
        print("-" * 40)
        
        result = extractor.extract_json_from_response(test_case["text"])
        success = result is not None
        
        print(f"結果: {'✅ 成功' if success else '❌ 失敗'}")
        print(f"期待: {'✅ 成功' if test_case['expected_success'] else '❌ 失敗'}")
        print(f"判定: {'🎯 PASS' if success == test_case['expected_success'] else '💥 FAIL'}")
        
        if result:
            print(f"抽出結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # レポート表示
        report = extractor.get_extraction_report()
        print(f"試行回数: {report['total_attempts']} (成功: {report['successful_attempts']})")


if __name__ == "__main__":
    test_enhanced_extractor() 