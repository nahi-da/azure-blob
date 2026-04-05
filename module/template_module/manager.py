"""Template manager class"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TemplateManager:
    """Template management class"""
    
    def __init__(self, templates_dir: str):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
    
    def load_templates(self) -> List[Dict]:
        """Load all templates
        
        Returns:
            List of templates
        """
        templates = []
        
        if not self.templates_dir.exists():
            logger.warning(f"テンプレートディレクトリが存在しません: {self.templates_dir}")
            return templates
        
        for template_file in self.templates_dir.glob('*.json'):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                    
                # Validate required fields
                if not self.validate_template(template)[0]:
                    logger.warning(f"無効なテンプレート: {template_file}")
                    continue
                
                # 元のファイル名を保存（編集時の上書き保存用）
                template['_filename'] = template_file.name
                
                templates.append(template)
                logger.debug(f"テンプレート読み込み: {template.get('name', template_file.stem)}")
                
            except Exception as e:
                logger.exception(f"テンプレート読み込みエラー ({template_file}): {e}")
        
        return templates
    
    def save_template(self, template: Dict) -> Tuple[bool, str]:
        """Save template
        
        Args:
            template: Template data
            
        Returns:
            (success flag, message)
        """
        try:
            # Validate
            valid, message = self.validate_template(template)
            if not valid:
                return False, message
            
            # Determine filename: use existing filename if available, otherwise generate from name
            if '_filename' in template and template['_filename']:
                # 既存テンプレートの場合は元のファイル名を使用
                template_file = self.templates_dir / template['_filename']
            else:
                # 新規テンプレートの場合はテンプレート名のみから生成
                name = template.get('name', 'unknown')
                safe_name = re.sub(r'[^\w\-_]', '_', name)
                template_file = self.templates_dir / f"{safe_name}.json"
            
            # _filenameは保存時に除外（内部管理用）
            template_to_save = {k: v for k, v in template.items() if k != '_filename'}
            
            # Save
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_to_save, f, ensure_ascii=False, indent=2)
            
            logger.info(f"テンプレート保存成功: {template_file}")
            return True, "保存しました"
            
        except Exception as e:
            logger.exception(f"テンプレート保存エラー: {e}")
            return False, f"保存エラー: {e}"
    
    def delete_template(self, template_name: str) -> Tuple[bool, str]:
        """Delete template
        
        Args:
            template_name: Template name
            
        Returns:
            (success flag, message)
        """
        try:
            # Search for matching file
            safe_name = re.sub(r'[^\w\-_]', '_', template_name)
            template_file = self.templates_dir / f"{safe_name}.json"
            
            if not template_file.exists():
                return False, "テンプレートファイルが見つかりません"
            
            template_file.unlink()
            logger.info(f"テンプレート削除成功: {template_file}")
            return True, "削除しました"
            
        except Exception as e:
            logger.exception(f"テンプレート削除エラー: {e}")
            return False, f"削除エラー: {e}"
    
    def get_template_by_name(self, name: str) -> Optional[Dict]:
        """Get template by name
        
        Args:
            name: Template name
            
        Returns:
            Template data (None if not found)
        """
        templates = self.load_templates()
        for template in templates:
            if template.get('name') == name:
                return template
        return None
    
    def validate_template(self, template: Dict) -> Tuple[bool, str]:
        """Validate template
        
        Args:
            template: Template data
            
        Returns:
            (validation result, error message)
        """
        # Required fields
        required_fields = ['name', 'category', 'subscription', 'storage_account', 
                          'path_pattern', 'placeholders']
        
        for field in required_fields:
            if field not in template:
                return False, f"必須フィールドがありません: {field}"
        
        # Validation success
        return True, ""
    
    def get_templates_by_category(self) -> Dict[str, List[Dict]]:
        """Get templates by category
        
        Returns:
            {category_name: [template, ...], ...}
        """
        categorized = {}
        templates = self.load_templates()
        
        for template in templates:
            category = template.get('category', 'その他')
            
            if category not in categorized:
                categorized[category] = []
            
            categorized[category].append(template)
        
        return categorized
