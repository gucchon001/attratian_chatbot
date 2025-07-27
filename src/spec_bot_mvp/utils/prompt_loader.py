"""
統一プロンプトローダー

全プロンプトを外部JSONファイルから一元管理するためのローダークラス
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    統一プロンプトローダー
    
    プロンプトファイルを一元管理し、各コンポーネントで使用できるよう提供
    """
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        初期化
        
        Args:
            prompts_dir: プロンプトディレクトリのパス（プロジェクトルートからの相対パス）
        """
        self.prompts_dir = Path(prompts_dir)
        self.prompts_cache: Dict[str, Dict] = {}
        self._load_all_prompts()
    
    def _load_all_prompts(self):
        """全プロンプトファイルを読み込み"""
        try:
            # プロジェクトルートを取得
            project_root = self._get_project_root()
            full_prompts_dir = project_root / self.prompts_dir
            
            if not full_prompts_dir.exists():
                logger.warning(f"プロンプトディレクトリが見つかりません: {full_prompts_dir}")
                return
            
            # 全JSONファイルを読み込み
            for json_file in full_prompts_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        file_key = json_file.stem  # ファイル名（拡張子なし）
                        self.prompts_cache[file_key] = file_data
                        logger.info(f"✅ プロンプトファイル読み込み: {json_file.name}")
                        
                except Exception as e:
                    logger.error(f"❌ プロンプトファイル読み込み失敗 {json_file}: {e}")
            
            logger.info(f"🎯 プロンプトローダー初期化完了: {len(self.prompts_cache)}ファイル")
            
        except Exception as e:
            logger.error(f"❌ プロンプト初期化エラー: {e}")
    
    def _get_project_root(self) -> Path:
        """プロジェクトルートディレクトリを取得"""
        current_path = Path(__file__).resolve()
        
        # pyproject.tomlまたはrequirements.txtを目印に上位に向かって検索
        for parent in current_path.parents:
            if (parent / "pyproject.toml").exists() or (parent / "requirements.txt").exists():
                return parent
        
        # 見つからない場合は3つ上の階層を返す（フォールバック）
        return current_path.parents[2]
    
    def get_prompt(self, file_key: str, category: str, prompt_key: str, **kwargs) -> str:
        """
        プロンプトを取得し、パラメータを埋め込み
        
        Args:
            file_key: プロンプトファイル名（拡張子なし）
            category: プロンプトカテゴリ
            prompt_key: プロンプトキー
            **kwargs: プロンプト内のプレースホルダーを置換するためのパラメータ
            
        Returns:
            パラメータが埋め込まれたプロンプト文字列
            
        Example:
            loader.get_prompt(
                "analysis_steps", 
                "step1_keyword_extraction", 
                "gemini_conservative_extraction",
                user_query="ログイン機能について"
            )
        """
        try:
            # プロンプトデータを取得
            if file_key not in self.prompts_cache:
                raise KeyError(f"プロンプトファイルが見つかりません: {file_key}")
            
            file_data = self.prompts_cache[file_key]
            
            if category not in file_data:
                raise KeyError(f"プロンプトカテゴリが見つかりません: {category}")
            
            category_data = file_data[category]
            
            if prompt_key not in category_data:
                raise KeyError(f"プロンプトキーが見つかりません: {prompt_key}")
            
            prompt_data = category_data[prompt_key]
            prompt_template = prompt_data.get("prompt", "")
            
            if not prompt_template:
                raise ValueError(f"プロンプトが空です: {file_key}.{category}.{prompt_key}")
            
            # パラメータの埋め込み
            formatted_prompt = prompt_template.format(**kwargs)
            
            logger.debug(f"✅ プロンプト取得成功: {file_key}.{category}.{prompt_key}")
            return formatted_prompt
            
        except Exception as e:
            logger.error(f"❌ プロンプト取得エラー {file_key}.{category}.{prompt_key}: {e}")
            # フォールバック：空のプロンプトを返す
            return f"# プロンプト取得エラー\n\n質問: {kwargs.get('user_query', 'N/A')}"
    
    def get_prompt_info(self, file_key: str, category: str, prompt_key: str) -> Dict[str, Any]:
        """
        プロンプトのメタ情報を取得
        
        Args:
            file_key: プロンプトファイル名
            category: プロンプトカテゴリ
            prompt_key: プロンプトキー
            
        Returns:
            プロンプトのメタ情報（description, parameters, version等）
        """
        try:
            file_data = self.prompts_cache[file_key]
            category_data = file_data[category]
            prompt_data = category_data[prompt_key]
            
            return {
                "description": prompt_data.get("description", ""),
                "parameters": prompt_data.get("parameters", []),
                "version": prompt_data.get("version", "1.0"),
                "file_key": file_key,
                "category": category,
                "prompt_key": prompt_key
            }
            
        except Exception as e:
            logger.error(f"❌ プロンプト情報取得エラー: {e}")
            return {}
    
    def list_available_prompts(self) -> Dict[str, Any]:
        """
        利用可能な全プロンプトの一覧を取得
        
        Returns:
            プロンプト構造の辞書
        """
        result = {}
        for file_key, file_data in self.prompts_cache.items():
            result[file_key] = {}
            for category, category_data in file_data.items():
                result[file_key][category] = list(category_data.keys())
        
        return result
    
    def reload_prompts(self):
        """プロンプトファイルを再読み込み"""
        logger.info("🔄 プロンプト再読み込み開始")
        self.prompts_cache.clear()
        self._load_all_prompts()


# グローバルインスタンス（シングルトンパターン）
_prompt_loader_instance: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """
    プロンプトローダーのグローバルインスタンスを取得
    
    Returns:
        PromptLoaderのシングルトンインスタンス
    """
    global _prompt_loader_instance
    
    if _prompt_loader_instance is None:
        _prompt_loader_instance = PromptLoader()
    
    return _prompt_loader_instance


# 便利関数
def load_prompt(file_key: str, category: str, prompt_key: str, **kwargs) -> str:
    """
    プロンプトを読み込む便利関数
    
    Args:
        file_key: プロンプトファイル名
        category: プロンプトカテゴリ  
        prompt_key: プロンプトキー
        **kwargs: プロンプトパラメータ
        
    Returns:
        フォーマット済みプロンプト
    """
    loader = get_prompt_loader()
    return loader.get_prompt(file_key, category, prompt_key, **kwargs)


def get_prompt_info(file_key: str, category: str, prompt_key: str) -> Dict[str, Any]:
    """
    プロンプト情報を取得する便利関数
    
    Args:
        file_key: プロンプトファイル名
        category: プロンプトカテゴリ
        prompt_key: プロンプトキー
        
    Returns:
        プロンプトメタ情報
    """
    loader = get_prompt_loader()
    return loader.get_prompt_info(file_key, category, prompt_key) 