"""Common text definitions used across multiple screens"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CommonTexts:
    """Common texts used in multiple screens"""
    
    # Common buttons
    back_button: str = "← 戻る"
    next_button: str = "次へ →"
    finish_button: str = "完了"
    cancel_button: str = "キャンセル"
    ok_button: str = "OK"
    close_button: str = "閉じる"
    save_button: str = "保存"
    delete_button: str = "削除"
    edit_button: str = "編集"
    add_button: str = "追加"
    select_button: str = "選択"
    refresh_button: str = "🔄 更新"
    browse_button: str = "参照"
    
    # Status messages
    status_ready: str = "準備完了"
    status_loading: str = "読み込み中..."
    status_processing: str = "処理中..."
    status_success: str = "成功"
    status_error: str = "エラー"
    status_cancelled: str = "キャンセルされました"
    
    # Common labels
    name_label: str = "名前:"
    description_label: str = "説明:"
    status_label: str = "状態:"
    
    # Error messages
    error_title: str = "エラー"
    error_generic: str = "エラーが発生しました"
    error_network: str = "ネットワークエラーが発生しました"
    error_authentication: str = "認証に失敗しました"
    error_file_not_found: str = "ファイルが見つかりません"
    error_permission_denied: str = "アクセス権限がありません"
    
    # Success messages
    success_title: str = "成功"
    success_saved: str = "保存しました"
    success_deleted: str = "削除しました"
    success_completed: str = "完了しました"
    
    # Confirmation messages
    confirm_title: str = "確認"
    confirm_delete: str = "削除してもよろしいですか？"
    confirm_cancel: str = "キャンセルしてもよろしいですか？"
    confirm_overwrite: str = "上書きしてもよろしいですか？"
    
    # Warning messages
    warning_title: str = "警告"
    warning_unsaved_changes: str = "保存されていない変更があります"
    
    # Info messages
    info_title: str = "情報"
    info_no_data: str = "データがありません"
    info_no_selection: str = "項目が選択されていません"
    
    # Common actions
    action_please_wait: str = "しばらくお待ちください..."
    action_select_item: str = "項目を選択してください"
    
    def format_error(self, error_message: str) -> str:
        """Format error message"""
        return f"エラー: {error_message}"
    
    def format_success(self, message: str) -> str:
        """Format success message"""
        return f"✓ {message}"
    
    def format_warning(self, message: str) -> str:
        """Format warning message"""
        return f"⚠️ {message}"
    
    def confirm_delete_item(self, item_name: str) -> str:
        """Confirmation message for deleting an item"""
        return f"「{item_name}」を削除してもよろしいですか？"


# Singleton instance
common_texts = CommonTexts()
