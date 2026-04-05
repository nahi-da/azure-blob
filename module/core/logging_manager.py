"""
ログ管理クラス
"""

import logging
from datetime import datetime
from pathlib import Path

from .config import ConfigManager

logger = logging.getLogger(__name__)


class LogManager:
    """ログ管理クラス"""
    
    def __init__(self, config: ConfigManager):
        """
        初期化
        
        Args:
            config: 設定管理クラス
        """
        self.config = config
        self.script_dir = config.script_dir
        logs_directory = self.config.get('logs_directory', 'data/logs')
        self.log_dir = self.script_dir / logs_directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 古いログファイル削除
        self._cleanup_old_logs()
        
        # ロガー設定
        self._setup_logger()
    
    def _cleanup_old_logs(self):
        """古いログファイルを削除"""
        try:
            max_files = self.config.get('max_log_files', 50)
            log_files = sorted(self.log_dir.glob('*.log'), key=lambda f: f.stat().st_ctime)
            
            if len(log_files) > max_files:
                for log_file in log_files[:len(log_files) - max_files]:
                    log_file.unlink()
                    logger.info(f"古いログファイルを削除: {log_file.name}")
        except Exception as e:
            logger.exception(f"ログファイル削除エラー: {e}")
    
    def _setup_logger(self):
        """ロガーセットアップ"""
        log_level = self.config.get('log_level', 'INFO')
        log_file = self.log_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
        
        # ロガー設定
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        # モジュールロガーのレベルも設定
        logger.setLevel(getattr(logging, log_level))
        
        logger.info("=" * 80)
        logger.info("AzBlobDL 起動")
        logger.info("=" * 80)
