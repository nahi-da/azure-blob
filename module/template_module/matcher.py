"""Condition matching for blob filtering"""

import re
from typing import Any, Dict, List
import logging

from .expander import PlaceholderExpander

logger = logging.getLogger(__name__)

class ConditionMatcher:
    """Condition matching class"""
    
    @staticmethod
    def filter_blobs(blobs: List[Dict], path_pattern: str, 
                    placeholders: Dict[str, Any], 
                    expansions: Dict[str, Any]) -> List[Dict]:
        """Filter blob list by conditions
        
        Args:
            blobs: Blob list
            path_pattern: Path pattern
            placeholders: Placeholder definitions
            expansions: Expansion settings
            
        Returns:
            List of matched blobs
        """
        # Generate regex pattern from pattern
        regex_pattern = ConditionMatcher._build_regex_pattern(
            path_pattern, placeholders, expansions
        )
        
        # デバッグログ追加
        logger.info(f"生成された正規表現パターン: {regex_pattern}")
        
        if not regex_pattern:
            return []
        
        compiled_pattern = re.compile(regex_pattern)
        matched = []
        
        for blob in blobs:
            blob_name = blob.get('name', '')
            if compiled_pattern.match(blob_name):
                matched.append(blob)
        
        # デバッグログ追加
        logger.info(f"フィルタリング結果: {len(matched)}/{len(blobs)} 件がマッチ")
        
        return matched
    
    @staticmethod
    def _build_regex_pattern(path_pattern: str, 
                            placeholders: Dict[str, Any],
                            expansions: Dict[str, Any]) -> str:
        """Build regex pattern"""
        # Replace placeholders with regex
        pattern = path_pattern
        
        # Extract placeholders
        ph_list = re.findall(r'\{([^}]+)\}', path_pattern)
        
        for ph_name in ph_list:
            expansion = expansions.get(ph_name, {})
            exp_type = expansion.get('type')
            ph_config = placeholders.get(ph_name, {})
            
            if exp_type == 'text':
                # Text: exact or partial match
                value = expansion.get('value', '')
                match_mode = expansion.get('match_mode', 'exact')
                
                if not value:
                    # Empty value treated as wildcard
                    pattern = pattern.replace(f'{{{ph_name}}}', '[^/]+')
                elif match_mode == 'partial':
                    # Partial match: .*value.*
                    pattern = pattern.replace(f'{{{ph_name}}}', f'.*{re.escape(value)}.*')
                else:
                    # Exact match (default)
                    pattern = pattern.replace(f'{{{ph_name}}}', re.escape(value))
            
            elif exp_type == 'numeric':
                # Numeric range
                padding = ph_config.get('padding', 0)
                mode = expansion.get('mode', 'fixed')
                
                if mode == 'fixed':
                    fixed_val = expansion.get('fixed')
                    if fixed_val is not None:
                        value = str(fixed_val).zfill(padding)
                        pattern = pattern.replace(f'{{{ph_name}}}', re.escape(value))
                    else:
                        pattern = pattern.replace(f'{{{ph_name}}}', r'\d+')
                else:
                    # Range specification
                    start = expansion.get('start')
                    end = expansion.get('end')
                    step = expansion.get('step', 1)
                    
                    if start is not None and end is not None:
                        # Expand numbers and create OR condition
                        values = PlaceholderExpander.expand_numeric(
                            start, end, step, padding, mode="range"
                        )
                        escaped_values = [re.escape(v) for v in values]
                        pattern = pattern.replace(f'{{{ph_name}}}', f"({'|'.join(escaped_values)})")
                    else:
                        pattern = pattern.replace(f'{{{ph_name}}}', r'\d+')
            
            elif exp_type == 'enum':
                # Enumeration: single or multiple selection
                multiple = ph_config.get('multiple', False)
                
                if multiple:
                    # Multiple selection
                    selected = expansion.get('selected_values', [])
                    if selected:
                        escaped_values = [re.escape(v) for v in selected]
                        pattern = pattern.replace(f'{{{ph_name}}}', f"({'|'.join(escaped_values)})")
                    else:
                        pattern = pattern.replace(f'{{{ph_name}}}', '[^/]+')
                else:
                    # Single selection
                    selected = expansion.get('selected_value', '')
                    if selected:
                        pattern = pattern.replace(f'{{{ph_name}}}', re.escape(selected))
                    else:
                        pattern = pattern.replace(f'{{{ph_name}}}', '[^/]+')
            
            elif exp_type == 'regex':
                # Regex: use pattern from user input (expansion), fallback to template default
                regex_pattern = expansion.get('pattern', ph_config.get('pattern', '[^/]+'))
                pattern = pattern.replace(f'{{{ph_name}}}', regex_pattern)
            
            else:
                # Unknown type: wildcard
                pattern = pattern.replace(f'{{{ph_name}}}', '[^/]+')
        
        return f'^{pattern}$'
