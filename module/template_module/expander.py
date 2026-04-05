"""Placeholder expansion engine"""

from typing import Any, Dict, List, Optional


class PlaceholderExpander:
    """Placeholder expansion engine"""
    
    @staticmethod
    def expand_numeric(min_val: int, max_val: int, step: int = 1, 
                      padding: int = 0, mode: str = "fixed", 
                      fixed_value: Optional[int] = None) -> List[str]:
        """Expand numeric range
        
        Args:
            min_val: Minimum value
            max_val: Maximum value
            step: Step
            padding: Zero-padding digits
            mode: "fixed" or "range"
            fixed_value: Fixed value (when mode is "fixed")
            
        Returns:
            List of expanded values
        """
        if mode == "fixed" and fixed_value is not None:
            return [str(fixed_value).zfill(padding)]
        
        values = []
        current = min_val
        while current <= max_val:
            values.append(str(current).zfill(padding))
            current += step
        
        return values
    
    @staticmethod
    def expand_text(value: str, match_mode: str = "exact") -> List[str]:
        """Expand text value
        
        Args:
            value: Text value
            match_mode: "exact" or "partial"
            
        Returns:
            List containing the text value (single element)
        """
        if not value:
            # Empty value treated as wildcard
            return []
        return [value]
    
    @staticmethod
    def expand_enum(selected_values: List[str], multiple: bool = False) -> List[str]:
        """Expand enum values
        
        Args:
            selected_values: Selected values
            multiple: Multiple selection enabled
            
        Returns:
            List of selected values
        """
        return selected_values if selected_values else []
