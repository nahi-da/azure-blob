"""Blob selection-related screen text definitions"""

from dataclasses import dataclass


@dataclass
class BlobSelectionMethodTexts:
    """Blob selection method screen texts"""
    
    title: str = "Blob指定方法選択"
    subtitle: str = "処理対象のBlobをどのように指定しますか？"
    
    # Method 1: URL input
    method1_title: str = "方法1: Blob URLを直接入力"
    method1_desc: str = "処理したいBlobのURLがわかっている場合"
    method1_button: str = "URLを入力する →"
    
    # Method 2: Template search
    method2_title: str = "方法2: テンプレートから検索"
    method2_desc: str = "パターンに基づいてBlobを検索し一覧から選択"
    method2_button: str = "テンプレートで検索 →"
    
    back_button: str = "← 戻る"


@dataclass
class BlobURLInputTexts:
    """Blob URL input screen texts"""
    
    title: str = "Blob URL入力"
    subtitle: str = "ダウンロードするBlobのURLを入力してください（複数可）"
    
    # Buttons
    add_url_button: str = "＋ URL追加"
    back_button: str = "← 戻る"
    next_button: str = "次へ →"
    delete_button: str = "×"
    
    # Context menu
    context_cut: str = "切り取り (Ctrl+X)"
    context_copy: str = "コピー (Ctrl+C)"
    context_paste: str = "貼り付け (Ctrl+V)"
    context_select_all: str = "全て選択 (Ctrl+A)"
    
    # Validation messages
    validation_checking: str = "検証中..."
    validation_valid: str = "✓ 有効"
    validation_success: str = "✓ 検証成功"
    validation_invalid_format: str = "✗ 無効なURL形式"
    validation_not_found: str = "✗ Blobが見つかりません"
    validation_not_archive: str = "✗ アーカイブ層ではありません"
    validation_error: str = "✗ 検証エラー"
    validating_dialog_message: str = "Blob URLを検証中..."
    
    # Error messages
    error_no_urls: str = "URLが入力されていません"
    error_invalid_urls: str = "無効なURLがあります"
    error_validation_failed: str = "URL検証に失敗しました"
    
    # Info messages
    info_validating: str = "URLを検証しています..."
    info_validation_complete: str = "検証が完了しました"
    
    def validation_progress(self, current: int, total: int) -> str:
        """Format validation progress message"""
        return f"検証中... ({current}/{total})"


@dataclass
class TemplateSelectionTexts:
    """Template selection screen texts"""
    
    title: str = "テンプレート選択"
    subtitle: str = "使用するテンプレートを選択してください（複数選択可）"
    
    # Buttons
    manage_button: str = "テンプレート管理"
    refresh_button: str = "🔄 更新"
    back_button: str = "← 戻る"
    search_button: str = "検索実行 →"
    next_button: str = "次へ →"
    
    # Labels
    template_list_label: str = "テンプレート（複数選択可）"
    template_detail_label: str = "テンプレート詳細"
    selected_count_label: str = "選択中"
    subscription_not_selected: str = "サブスクリプション: 未選択"
    subscription_not_selected_label: str = "サブスクリプション: 未選択"
    
    # Messages
    no_templates: str = "テンプレートがありません"
    no_selection: str = "テンプレートが選択されていません"
    loading_templates: str = "テンプレートを読み込んでいます..."
    
    # Error messages
    error_no_selection: str = "テンプレートを選択してください"
    error_load_failed: str = "テンプレートの読み込みに失敗しました"
    
    def filter_info(self, subscription_name: str) -> str:
        """Format filter info message"""
        return f"🔍 サブスクリプション: {subscription_name}"
    
    def selected_count(self, count: int) -> str:
        """Format selected count message"""
        return f"選択中: {count}個"


@dataclass
class TemplateEditorTexts:
    """Template editor screen texts"""
    
    title: str = "テンプレート管理"
    
    # Buttons
    new_button: str = "新規作成"
    edit_button: str = "編集"
    delete_button: str = "削除"
    delete_button_text: str = "削除"
    duplicate_button: str = "複製"
    close_button: str = "閉じる"
    save_button: str = "保存"
    cancel_button: str = "キャンセル"
    back_button: str = "← 戻る"
    test_button: str = "テスト"
    
    # Labels
    template_list_label: str = "テンプレート一覧"
    template_name_label: str = "名前:"
    category_label: str = "カテゴリ:"
    subscription_id_label: str = "サブスクリプションID:"
    storage_account_label: str = "ストレージアカウント:"
    description_label: str = "説明:"
    container_label: str = "コンテナ:"
    path_label: str = "パス:"
    placeholder_name_label: str = "プレースホルダー名:"
    placeholder_label_label: str = "ラベル:"
    placeholder_type_label: str = "タイプ:"
    default_value_label: str = "デフォルト値:"
    match_mode_label: str = "マッチモード:"
    match_exact: str = "完全一致"
    match_partial: str = "部分一致"
    min_value_label: str = "最小値:"
    max_value_label: str = "最大値:"
    zero_padding_label: str = "ゼロパディング:"
    padding_digits_label: str = "桁"
    options_label: str = "選択肢:"
    options_note: str = "(1行に1つ)"
    multiple_selection_label: str = "複数選択:"
    allow_multiple: str = "許可する"
    regex_pattern_label: str = "正規表現:"
    test_string_prompt: str = "テスト文字列を入力:"
    
    # Frame titles
    basic_info_frame: str = "基本情報"
    container_settings_frame: str = "コンテナ設定"
    path_pattern_frame: str = "パスパターン"
    placeholder_definition_frame: str = "プレースホルダー定義"
    example_paths_frame: str = "例パス"
    
    # Notes and hints
    placeholder_usage_note: str = "※ プレースホルダー使用可（例: {environment}-logs）"
    placeholder_format_note: str = "※ プレースホルダーは {name} 形式で記述"
    example_paths_note: str = "例パスを入力（1行1例）"
    add_placeholder_button: str = "+ プレースホルダーを追加"
    options_label: str = "選択肢:"
    options_note: str = "(1行に1つ)"
    
    # Messages
    save_success: str = "テンプレートを保存しました"
    delete_success: str = "テンプレートを削除しました"
    duplicate_prompt: str = "新しいテンプレート名を入力してください:"
    test_button_text: str = "テスト"
    
    # Error messages
    error_empty_name: str = "テンプレート名を入力してください"
    error_save_failed: str = "テンプレートの保存に失敗しました"
    error_delete_failed: str = "テンプレートの削除に失敗しました"
    error_load_failed: str = "テンプレートの読み込みに失敗しました"
    
    def confirm_delete(self, template_name: str) -> str:
        """Confirmation message for deleting a template"""
        return f"テンプレート「{template_name}」を削除してもよろしいですか？"


@dataclass
class TemplateExpansionTexts:
    """Template expansion screen texts"""
    
    title: str = "テンプレート展開"
    subtitle: str = "テンプレートの変数を設定してください"
    
    # Buttons
    back_button: str = "← 戻る"
    expand_button: str = "展開して検索 →"
    clear_button: str = "クリア"
    
    # Labels
    template_label: str = "テンプレート:"
    preview_label: str = "プレビュー:"
    subscription_id_label: str = "サブスクリプションID:"
    storage_account_label: str = "ストレージアカウント:"
    container_label: str = "コンテナ:"
    path_label: str = "パス:"
    
    # Placeholder labels
    placeholder_label: str = "プレースホルダー:"
    placeholder_info: str = "{name}"
    add_value_set_button: str = "+ 値セットを追加"
    value_set_note: str = "※複数の値セットを設定すると、それぞれの条件でパスを生成します"
    delete_button_text: str = "削除"
    
    # Match settings
    match_frame_title: str = "マッチ設定"
    match_type_label: str = "マッチ種別:"
    match_type_exact: str = "完全一致"
    match_type_prefix: str = "前方一致"
    match_type_partial: str = "部分一致"
    match_type_regex: str = "正規表現"
    value_label: str = "値:"
    match_label: str = "マッチ:"
    fixed_value_label: str = "固定値:"
    range_label: str = "範囲:"
    step_label_short: str = "ステップ:"
    selection_label: str = "選択:"
    pattern_label: str = "パターン:"
    validate_button: str = "検証"
    cancel_button_text: str = "キャンセル"
    retry_button: str = "リトライ"
    abort_search_button: str = "検索を終了"
    option_undefined: str = "（オプション未定義）"
    all_match: str = "（全てマッチ）"
    search_executing: str = "Blob検索実行中..."
    blob_list_error: str = "Blob一覧取得中にエラーが発生しました"
    
    # Numeric range settings
    range_frame_title: str = "数値範囲設定"
    start_label: str = "開始:"
    end_label: str = "終了:"
    step_label: str = "増分:"
    padding_label: str = "桁数:"
    
    # Enum settings
    enum_frame_title: str = "列挙設定"
    enum_values_label: str = "値（1行1値）:"
    enum_comma_separated_label: str = "値（カンマ区切り）:"
    
    # Date range settings
    date_frame_title: str = "日付範囲設定"
    date_format_label: str = "フォーマット:"
    start_date_label: str = "開始日(YYYYMMDD):"
    end_date_label: str = "終了日:"
    weekdays_only_label: str = "平日のみ"
    
    # Container info
    container_info_placeholder: str = "プレースホルダー展開により自動設定されます"
    container_info_fixed: str = "固定値"
    container_info_input: str = "コンテナ名を入力してください"
    
    # Messages
    expanding: str = "展開中..."
    expand_success: str = "展開が完了しました"
    
    # Error messages
    error_empty_value: str = "必須項目が入力されていません"
    error_invalid_value: str = "入力値が無効です"
    error_expand_failed: str = "展開に失敗しました"
    error_invalid_range: str = "範囲設定が無効です"
    error_invalid_format: str = "フォーマットが無効です"
    
    def value_set_title(self, index: int) -> str:
        """Format value set title"""
        return f"■ 値セット{index}"
    
    def required_field(self, field_name: str) -> str:
        """Format required field message"""
        return f"{field_name} (必須)"


@dataclass
class TemplateSearchResultTexts:
    """Template search result screen texts"""
    
    title: str = "検索結果"
    subtitle: str = "検索されたBlobから選択してください"
    
    # Column headers
    col_select: str = "選択"
    col_name: str = "Blob名"
    col_size: str = "サイズ"
    col_template: str = "テンプレート"
    col_template_alt: str = "テンプレート"
    col_last_modified: str = "最終更新"
    col_tier: str = "層"
    col_container: str = "コンテナ"
    
    # Buttons
    back_button: str = "← 戻る"
    select_all_button: str = "全選択"
    deselect_all_button: str = "全解除"
    next_button: str = "選択して続行 →"
    export_button: str = "エクスポート"
    
    # Messages
    searching: str = "検索中..."
    search_complete: str = "検索が完了しました"
    no_results: str = "検索結果がありません"
    
    # Error messages
    error_no_selection: str = "Blobが選択されていません"
    error_search_failed: str = "検索に失敗しました"
    
    def result_count(self, count: int) -> str:
        """Format result count message"""
        return f"検索結果: {count}個"
    
    def selected_count(self, count: int) -> str:
        """Format selected count message"""
        return f"選択中: {count}個"
    
    def search_progress(self, current: int, total: int) -> str:
        """Format search progress message"""
        return f"検索中... ({current}/{total})"


# Singleton instances
blob_selection_method_texts = BlobSelectionMethodTexts()
blob_url_input_texts = BlobURLInputTexts()
template_selection_texts = TemplateSelectionTexts()
template_editor_texts = TemplateEditorTexts()
template_expansion_texts = TemplateExpansionTexts()
template_search_result_texts = TemplateSearchResultTexts()
