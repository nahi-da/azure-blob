"""
サービスプリンシパルプロファイル管理クラス
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ServicePrincipalProfileManager:
    """サービスプリンシパルプロファイルの管理クラス"""
    
    def __init__(self, profiles_dir: Path):
        """
        初期化
        
        Args:
            profiles_dir: プロファイル保存ディレクトリ
        """
        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """
        全プロファイルを取得
        
        Returns:
            プロファイルのリスト
        """
        profiles = []
        if not self.profiles_dir.exists():
            return profiles
        
        for file_path in self.profiles_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                    # ファイル名を保存
                    profile_data['file_name'] = file_path.stem
                    profiles.append(profile_data)
            except Exception as e:
                logger.warning(f"プロファイル読み込みスキップ: {file_path.name} - {e}")
                continue
        
        return profiles
    
    def save_profile(self, profile_data: Dict[str, Any]) -> bool:
        """
        プロファイルを保存
        
        Args:
            profile_data: プロファイルデータ
        
        Returns:
            成功時True
        """
        try:
            file_name = profile_data.get('file_name', '')
            if not file_name:
                raise ValueError("ファイル名が指定されていません")
            
            file_path = self.profiles_dir / f"{file_name}.json"
            
            # タイムスタンプ設定
            if 'created_at' not in profile_data:
                profile_data['created_at'] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"プロファイル保存成功: {file_name}")
            return True
            
        except Exception as e:
            logger.exception(f"プロファイル保存失敗: {e}")
            return False
    
    def delete_profile(self, file_name: str) -> bool:
        """
        プロファイルを削除
        
        Args:
            file_name: ファイル名（拡張子なし）
        
        Returns:
            成功時True
        """
        try:
            file_path = self.profiles_dir / f"{file_name}.json"
            if file_path.exists():
                file_path.unlink()
                logger.info(f"プロファイル削除成功: {file_name}")
                return True
            else:
                logger.warning(f"プロファイルが存在しません: {file_name}")
                return False
        except Exception as e:
            logger.exception(f"プロファイル削除失敗: {e}")
            return False
    
    def load_profile(self, file_name: str) -> Optional[Dict[str, Any]]:
        """
        プロファイルをロード
        
        Args:
            file_name: ファイル名（拡張子なし）
        
        Returns:
            プロファイルデータまたはNone
        """
        try:
            file_path = self.profiles_dir / f"{file_name}.json"
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
                profile_data['file_name'] = file_name
                return profile_data
                
        except Exception as e:
            logger.exception(f"プロファイル読み込み失敗: {e}")
            return None
    
    def update_last_used(self, file_name: str) -> bool:
        """
        最終使用日時を更新
        
        Args:
            file_name: ファイル名（拡張子なし）
        
        Returns:
            成功時True
        """
        try:
            profile_data = self.load_profile(file_name)
            if profile_data:
                profile_data['last_used'] = datetime.now().isoformat()
                return self.save_profile(profile_data)
            return False
        except Exception as e:
            logger.exception(f"最終使用日時更新失敗: {e}")
            return False
    
    def file_exists(self, file_name: str, exclude_file_name: Optional[str] = None) -> bool:
        """
        ファイル名の存在確認（大文字小文字を区別しない）
        
        Args:
            file_name: チェック対象のファイル名
            exclude_file_name: 除外するファイル名（編集時の自分自身の名前）
        
        Returns:
            存在する場合True
        """
        file_name_lower = file_name.lower()
        exclude_lower = exclude_file_name.lower() if exclude_file_name else None
        
        for existing_file in self.profiles_dir.glob("*.json"):
            existing_name_lower = existing_file.stem.lower()
            
            # 除外ファイルはスキップ
            if exclude_lower and existing_name_lower == exclude_lower:
                continue
            
            if existing_name_lower == file_name_lower:
                return True
        
        return False
