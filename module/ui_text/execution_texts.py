"""Execution-related screen text definitions"""

from dataclasses import dataclass


@dataclass
class OptionsTexts:
    """Options screen texts"""
    
    title: str = "オプション選択"
    
    # Download settings frame
    download_settings_title: str = "ダウンロード設定"
    download_dir_label: str = "ダウンロード先:"
    browse_button: str = "参照"
    
    # Path structure
    path_structure_label: str = "パス構造:"
    path_preserve: str = "構造維持（コンテナ/パス/ファイル）"
    path_flatten: str = "パスをファイル名化（container_path_blob.ext）"
    path_single: str = "単一ファイル直接（ファイルのみ）"
    
    # Rehydrate settings frame
    rehydrate_settings_title: str = "リハイドレート設定"
    target_tier_label: str = "ターゲット層:"
    priority_label: str = "優先度:"
    
    # Priority options
    priority_standard: str = "Standard"
    priority_high: str = "High"
    
    # Operation mode
    mode_label: str = "動作モード:"
    mode_rehydrate_download: str = "リハイドレート＋ダウンロード"
    mode_rehydrate_only: str = "リハイドレートのみ"
    mode_copy_only: str = "コピーのみ（非アーカイブBlobをダウンロード）"
    
    # Polling settings
    polling_label: str = "ポーリング間隔:"
    polling_seconds: str = "秒"
    
    # Concurrent downloads
    concurrent_label: str = "同時ダウンロード数:"
    concurrent_files: str = "ファイル"
    
    # Buttons
    back_button: str = "← 戻る"
    start_button: str = "処理開始 →"
    start_button_download: str = "ダウンロード開始"
    
    # Messages
    validation_error: str = "設定内容にエラーがあります"
    
    # Error messages
    error_invalid_download_dir: str = "ダウンロード先が無効です"
    error_invalid_polling: str = "ポーリング間隔が無効です（10-600秒の範囲で指定してください）"
    error_invalid_concurrent: str = "同時ダウンロード数が無効です（1-10の範囲で指定してください）"


@dataclass
class ProgressTexts:
    """Progress screen texts"""
    
    title: str = "処理進捗"
    
    # Column headers
    col_blob: str = "Blob名"
    col_storage: str = "ストレージアカウント"
    col_container: str = "コンテナ"
    col_status: str = "状態"
    col_progress: str = "詳細"
    
    # Status values
    status_waiting: str = "待機"
    status_processing: str = "処理中"
    status_completed: str = "完了"
    status_error: str = "エラー"
    status_skipped: str = "スキップ"
    status_rehydrating: str = "リハイドレート中"
    status_downloading: str = "ダウンロード中"
    status_copying: str = "コピー中"
    
    # Buttons
    cancel_button: str = "中断"
    prev_button: str = "← 前へ"
    next_button: str = "次へ →"
    
    # Labels
    log_title: str = "ログ"
    elapsed_time_label: str = "経過時間: 00:00:00"
    page_label_format: str = "ページ: {current} / {total}"
    
    # Status-specific titles
    title_processing: str = "処理進捗"
    title_completed: str = "処理完了"
    title_cancelled: str = "処理中断"
    
    # Button text variations
    cancel_button_text_cancelled: str = "閉じる"
    cancel_button_text_cancelled_alt: str = "中断済み"
    
    # Titles
    title_download: str = "ダウンロード進捗"
    title_copy: str = "コピー進捗"
    
    # Messages
    processing_start: str = "処理を開始します"
    processing_complete: str = "すべての処理が完了しました"
    processing_cancelled: str = "処理が中断されました"
    processing_error: str = "処理中にエラーが発生しました"
    
    # Confirmation
    confirm_cancel: str = "処理を中断してもよろしいですか?"
    
    def elapsed_time(self, hours: int, minutes: int, seconds: int) -> str:
        """Format elapsed time"""
        return f"経過時間: {hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def page_info(self, current: int, total: int) -> str:
        """Format page info"""
        return f"ページ: {current}/{total}"
    
    def progress_info(self, completed: int, total: int) -> str:
        """Format progress info"""
        return f"進捗: {completed}/{total}"
    
    def log_message(self, blob_name: str, message: str) -> str:
        """Format log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] {blob_name}: {message}"


@dataclass
class CompletionTexts:
    """Completion screen texts"""
    
    title: str = "処理完了"
    
    # Summary frame
    summary_title: str = "処理結果"
    result_success: str = "✓ 処理が正常に完了しました"
    result_partial: str = "⚠ 処理が部分的に完了しました（一部エラーあり）"
    result_failed: str = "✗ 処理が失敗しました"
    result_cancelled: str = "中断されました"
    
    # Detail frame
    detail_title: str = "処理詳細"
    total_blobs: str = "総Blob数:"
    successful: str = "成功:"
    failed: str = "失敗:"
    skipped: str = "スキップ:"
    elapsed_time: str = "処理時間:"
    
    # Column headers for error list
    col_blob: str = "Blob名"
    col_error: str = "エラー内容"
    
    # Download info
    download_location: str = "ダウンロード先: {}"
    
    # Buttons
    open_folder_button: str = "ダウンロードフォルダを開く"
    finish_button: str = "完了"
    
    # Error list
    error_list_title: str = "エラー詳細"
    error_list_empty: str = "エラーはありません"
    
    def format_time(self, seconds: int) -> str:
        """Format elapsed time"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def blob_count(self, count: int) -> str:
        """Format blob count"""
        return f"{count}個"


# Need to import datetime for log_message method
from datetime import datetime

# Singleton instances
options_texts = OptionsTexts()
progress_texts = ProgressTexts()
completion_texts = CompletionTexts()
