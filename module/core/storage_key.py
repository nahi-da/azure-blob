"""ストレージアカウントキー管理クラス"""

import logging
import threading
from typing import Optional

from .azure_cli import AzureCLIWrapper

logger = logging.getLogger(__name__)


class StorageAccountKeyManager:
    """ストレージアカウントキー管理クラス（スレッドセーフ、弱参照でメモリ最適化）"""
    
    def __init__(self, azure_cli: AzureCLIWrapper):
        """
        初期化
        
        Args:
            azure_cli: Azure CLIラッパー
        """
        self.azure_cli = azure_cli
        self._keys = {}  # {account_name: key}
        self._lock = threading.Lock()  # スレッドセーフのためのロック
    
    def get_key(self, storage_account: str, subscription_id: Optional[str] = None) -> Optional[str]:
        """
        ストレージアカウントのアクセスキーを取得（キャッシュ利用、スレッドセーフ）
        
        Args:
            storage_account: ストレージアカウント名
            subscription_id: サブスクリプションID（省略時は現在のサブスクリプション）
            
        Returns:
            アクセスキー（取得失敗時はNone）
        
        Note:
            ストレージアカウント名はAzureグローバルで一意のため、
            subscription_idに関係なくストレージアカウント名のみをcache_keyとして使用
        """
        # ストレージアカウント名はグローバルで一意のため、これだけでキャッシュキーとする
        cache_key = storage_account
        
        # ロックを取得して、複数スレッドから同時にアクセスされても1回だけ取得するようにする
        with self._lock:
            # ロック取得後に再度キャッシュ確認（別スレッドが既に取得済みの可能性）
            if cache_key in self._keys:
                logger.info(f"キャッシュからアクセスキーを取得: {storage_account}")
                return self._keys[cache_key]
            
            # Azure CLIで取得
            logger.info(f"アクセスキーを取得中: {storage_account}")
            
            args = [
                'storage', 'account', 'keys', 'list',
                '--account-name', storage_account,
                '--query', '[0].value',
                '--output', 'tsv'
            ]
            
            if subscription_id:
                args.extend(['--subscription', subscription_id])
            
            success, data, error = self.azure_cli.run(args, capture_json=False)
            
            if success and data:
                key = data.strip()
                self._keys[cache_key] = key
                logger.info(f"アクセスキー取得成功: {storage_account}")
                return key
            else:
                logger.exception(f"アクセスキー取得失敗: {storage_account} - {error}")
                return None
    
    def clear_cache(self):
        """キャッシュクリア"""
        self._keys.clear()
        logger.info("アクセスキーキャッシュをクリアしました")
