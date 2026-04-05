"""
設定ファイル管理クラス
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """設定ファイル管理クラス"""
    
    DEFAULT_CONFIG = {
        'rehydrate_check_interval_seconds': 60,
        'max_log_files': 30,
        'max_state_files': 20,
        'max_retry_count': 3,
        'retry_delay_seconds': 10,
        'log_text_max_lines': 5000,
        'download_directory': '~/Downloads',  # ~/ はホームディレクトリ、./ はスクリプトディレクトリ基準
        'target_tier': 'Hot',  # Hot or Cool
        'priority': 'High',  # Standard or High
        'log_level': 'INFO',
        'azure_cli_default_timeout': 300,  # Azure CLIコマンドのデフォルトタイムアウト（秒）
        'azure_cli_login_timeout': 60,  # Azure CLIログインのタイムアウト（秒）
        'blob_download_timeout': 3600,  # Blobダウンロードのタイムアウト（秒）
        'rehydrate_batch_mode': True,  # 2段階処理モードの有効化
        'max_rehydrate_workers': 10,  # リハイドレート要求の並列数
        'max_status_check_workers': 10,  # Blob状態確認の並列数
        'max_download_workers': 5,  # ダウンロードの並列数
        'max_url_validation_workers': 5,  # Blob URL検証の並列数
        'logs_directory': 'data/logs',  # ログディレクトリ
        'state_directory': 'data/state',  # ステートディレクトリ
        'templates_directory': 'data/templates',  # テンプレートディレクトリ
        'profiles_directory': 'data/profiles',  # プロファイルディレクトリ
    }
    
    def __init__(self, config_file: str = 'config.json'):
        """
        初期化
        
        Args:
            config_file: 設定ファイルパス（スクリプト直下）
        """
        # スクリプトディレクトリを取得（module/core/config.py から3階層上がプロジェクトルート）
        self.script_dir = Path(__file__).parent.parent.parent
        self.config_file = self.script_dir / config_file
        self.config = self.load()
    
    def load(self) -> Dict[str, Any]:
        """設定ファイル読み込み"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # デフォルト値とマージ
                config = self.DEFAULT_CONFIG.copy()
                config.update(user_config)
                return config
            except Exception as e:
                logger.warning(f"設定ファイル読み込みエラー: {e}、デフォルト値を使用します")
                return self.DEFAULT_CONFIG.copy()
        else:
            # 初回起動時はデフォルト値で設定ファイル作成
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()
            return self.config
    
    def save(self):
        """設定ファイル保存"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.exception(f"設定ファイル保存エラー: {e}")
    
    def _expand_path(self, path_str: str) -> str:
        """
        パス文字列を展開
        
        Args:
            path_str: パス文字列（~/ または ./ で始まる相対パス対応）
            
        Returns:
            展開された絶対パス
        """
        if not isinstance(path_str, str):
            return path_str
        
        # ~ をホームディレクトリに展開
        if path_str.startswith('~/'):
            return str(Path.home() / path_str[2:])
        elif path_str == '~':
            return str(Path.home())
        
        # ./ をスクリプトディレクトリ基準に展開
        if path_str.startswith('./'):
            return str(self.script_dir / path_str[2:])
        
        # それ以外はそのまま返す（絶対パス想定）
        return path_str
    
    def get(self, key: str, default=None) -> Any:
        """
        設定値取得（download_directory等のパスは自動展開）
        
        Args:
            key: 設定キー
            default: デフォルト値
            
        Returns:
            設定値（パスキーの場合は展開済み）
        """
        value = self.config.get(key, default)
        
        # パス系キーは自動展開
        if key == 'download_directory' and value:
            return self._expand_path(value)
        
        return value
    
    def set(self, key: str, value: Any):
        """設定値設定"""
        self.config[key] = value
        self.save()
