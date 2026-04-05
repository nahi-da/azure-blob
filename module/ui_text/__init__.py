"""UI text definitions module

This module contains text definitions for all UI screens.
Organized by UI module:
- common: Common texts used across multiple screens
- auth_texts: Authentication-related screens
- blob_texts: Blob selection-related screens
- execution_texts: Execution-related screens
"""

from .common import common_texts
from .auth_texts import (
    auth_method_texts,
    login_texts,
    existing_login_texts,
    sp_selection_texts,
    profile_editor_texts,
)
from .blob_texts import (
    blob_selection_method_texts,
    blob_url_input_texts,
    template_selection_texts,
    template_editor_texts,
    template_expansion_texts,
    template_search_result_texts,
)
from .execution_texts import (
    options_texts,
    progress_texts,
    completion_texts,
)

__all__ = [
    # Common
    'common_texts',
    # Auth
    'auth_method_texts',
    'login_texts',
    'existing_login_texts',
    'sp_selection_texts',
    'profile_editor_texts',
    # Blob Selection
    'blob_selection_method_texts',
    'blob_url_input_texts',
    'template_selection_texts',
    'template_editor_texts',
    'template_expansion_texts',
    'template_search_result_texts',
    # Execution
    'options_texts',
    'progress_texts',
    'completion_texts',
]
