"""Prefix optimization helper"""

import re
from typing import Any, Dict


class PrefixOptimizer:
    """Prefix optimization class"""
    
    @staticmethod
    def calculate_prefix(path_pattern: str, expansions: Dict[str, Any]) -> str:
        """Calculate optimal prefix from path pattern and expansion settings
        
        Args:
            path_pattern: Path pattern (e.g. "data/{year}/{month}/{day}/")
            expansions: Placeholder expansion settings
            
        Returns:
            Prefix string
        """
        # Split pattern by slash
        parts = path_pattern.split('/')
        prefix_parts = []
        
        for part in parts:
            # Detect placeholders
            placeholders = re.findall(r'\{([^}]+)\}', part)
            
            if not placeholders:
                # No placeholders -> add as-is
                prefix_parts.append(part)
            else:
                # Has placeholders
                # Expand only if fixed value
                can_expand = True
                expanded_part = part
                
                for ph in placeholders:
                    expansion = expansions.get(ph, {})
                    exp_type = expansion.get('type')
                    
                    if exp_type == 'text':
                        # Replace with text value (only exact match mode)
                        value = expansion.get('value', '')
                        match_mode = expansion.get('match_mode', 'exact')
                        if value and match_mode == 'exact':
                            expanded_part = expanded_part.replace(f'{{{ph}}}', value)
                        else:
                            can_expand = False
                            break
                    elif exp_type == 'numeric' and expansion.get('mode') == 'fixed':
                        # Replace with numeric fixed value
                        padding = expansion.get('padding', 0)
                        fixed_val = expansion.get('fixed')
                        if fixed_val is not None:
                            value = str(fixed_val).zfill(padding)
                            expanded_part = expanded_part.replace(f'{{{ph}}}', value)
                        else:
                            can_expand = False
                            break
                    elif exp_type == 'enum':
                        # Replace with enum selected value (single selection only)
                        multiple = expansion.get('multiple', False)
                        if not multiple:
                            value = expansion.get('selected_value', '')
                            if value:
                                expanded_part = expanded_part.replace(f'{{{ph}}}', value)
                            else:
                                can_expand = False
                                break
                        else:
                            # Multiple selection cannot be expanded
                            can_expand = False
                            break
                    else:
                        # Other types (regex, range, etc.) cannot be expanded
                        can_expand = False
                        break
                
                if can_expand:
                    prefix_parts.append(expanded_part)
                else:
                    # If cannot expand, use up to this point as prefix
                    break
        
        return '/'.join(prefix_parts)
