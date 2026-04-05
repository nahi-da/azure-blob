"""ステートファイル管理クラス"""

import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ConfigManager

logger = logging.getLogger(__name__)


class StateFileManager:
    """ステートファイル管理クラス"""
    
    def __init__(self, config: ConfigManager):
        """
        初期化
        
        Args:
            config: 設定管理クラス
        """
        self.config = config
        self.script_dir = Path(__file__).parent.parent
        state_directory = self.config.get('state_directory', 'data/state')
        self.state_dir = self.script_dir / state_directory
        self.archive_dir = self.state_dir / 'archive'
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # 古いステートファイル削除
        self._cleanup_old_states()
    
    def _cleanup_old_states(self):
        """古いステートファイルを削除"""
        try:
            max_files = self.config.get('max_state_files', 20)
            
            # state/ と state/archive/ の両方をチェック
            all_state_files = []
            all_state_files.extend(self.state_dir.glob('*.json'))
            all_state_files.extend(self.archive_dir.glob('*.json'))
            
            # 作成日時でソート
            all_state_files = sorted(all_state_files, key=lambda f: f.stat().st_ctime)
            
            if len(all_state_files) > max_files:
                for state_file in all_state_files[:len(all_state_files) - max_files]:
                    state_file.unlink()
                    logger.info(f"古いステートファイルを削除: {state_file.name}")
        except Exception as e:
            logger.error(f"ステートファイル削除エラー: {e}")
            logger.exception(e)
    
    def create_state_file(self, session_id: str, subscription_id: str, subscription_name: str,
                         tenant_name: str, options: Dict[str, Any], blobs: List[Dict[str, Any]]) -> Path:
        """
        ステートファイルを作成
        
        Args:
            session_id: セッションID
            subscription_id: サブスクリプションID
            subscription_name: サブスクリプション名
            tenant_name: テナント名
            options: オプション設定
            blobs: Blobリスト
            
        Returns:
            作成したステートファイルのパス
        """
        state_file = self.state_dir / f"{session_id}_state.json"
        
        state_data = {
            'session_id': session_id,
            'started_at': datetime.now().isoformat(),
            'subscription_id': subscription_id,
            'subscription_name': subscription_name,
            'tenant_name': tenant_name,
            'options': options,
            'blobs': blobs
        }
        
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            logger.info(f"ステートファイル作成: {state_file.name}")
            return state_file
        except Exception as e:
            logger.error(f"ステートファイル作成エラー: {e}")
            logger.exception(e)
            raise
    
    def update_blob_status(self, state_file: Path, blob_url: str, status: str, 
                          additional_data: Optional[Dict[str, Any]] = None):
        """
        Blobのステータスを更新（バッチ更新）
        
        Args:
            state_file: ステートファイルパス
            blob_url: Blob URL
            status: 新しいステータス
            additional_data: 追加データ
        """
        try:
            # ファイル読み込み
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # 該当Blobを検索して更新
            for blob in state_data['blobs']:
                if blob['url'] == blob_url:
                    blob['status'] = status
                    if additional_data:
                        blob.update(additional_data)
                    break
            
            # ファイル書き込み
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Blobステータス更新エラー: {e}")
            logger.exception(e)
    
    def load_state_file(self, state_file: Path) -> Dict[str, Any]:
        """
        ステートファイルを読み込み
        
        Args:
            state_file: ステートファイルパス
            
        Returns:
            ステートデータ
        """
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"ステートファイル読み込みエラー: {e}")
            logger.exception(e)
            return dict()
    
    def find_incomplete_state(self) -> Optional[Path]:
        """
        未完了のステートファイルを検索
        
        Returns:
            未完了のステートファイルパス（見つからない場合はNone）
        """
        try:
            for state_file in self.state_dir.glob('*_state.json'):
                state_data = self.load_state_file(state_file)
                if state_data and state_data.get('blobs'):
                    # 未完了のBlobが存在するかチェック
                    for blob in state_data['blobs']:
                        if blob.get('status') != 'completed':
                            logger.info(f"未完了のステートファイル発見: {state_file.name}")
                            return state_file
            return None
        except Exception as e:
            logger.error(f"未完了ステートファイル検索エラー: {e}")
            logger.exception(e)
            return None
    
    def archive_state_file(self, state_file: Path):
        """
        ステートファイルをアーカイブに移動
        
        Args:
            state_file: ステートファイルパス
        """
        try:
            import shutil
            dest = self.archive_dir / state_file.name
            shutil.move(str(state_file), str(dest))
            logger.info(f"ステートファイルをアーカイブ: {state_file.name}")
        except Exception as e:
            logger.error(f"ステートファイルアーカイブエラー: {e}")
            logger.exception(e)
