"""Authentication-related screen text definitions"""

from dataclasses import dataclass


@dataclass
class AuthMethodTexts:
    """Authentication method selection screen texts"""
    
    title: str = "AzBlobDL"
    subtitle: str = "認証方法を選択してください"
    frame_title: str = "認証方法"
    
    # Existing login option
    existing_radio: str = "既存のログイン情報を使用"
    existing_desc: str = "Azure CLIの既存ログイン情報を使用します"
    
    # User account option
    user_radio: str = "ユーザーアカウント認証"
    user_desc: str = "ユーザーアカウントで認証します"
    
    # Service principal option
    sp_radio: str = "サービスプリンシパル認証"
    sp_desc: str = "サービスプリンシパルを使用して認証します"
    
    next_button: str = "次へ"


@dataclass
class LoginTexts:
    """User account login screen texts"""
    
    title: str = "ユーザーアカウント認証"
    subtitle: str = "ユーザーアカウントでサインインします"
    
    # Sign-in button
    signin_button: str = "サインイン"
    
    # Info frame
    info_frame_title: str = "ログイン情報"
    user_label: str = "ユーザー:"
    user_not_logged_in: str = "（未ログイン）"
    tenant_label: str = "テナント:"
    subscription_label: str = "サブスクリプション:"
    
    # Navigation buttons
    back_button: str = "← 戻る"
    next_button: str = "次へ →"
    
    # Status messages
    status_signin_required: str = "サインインしてください"
    status_signing_in: str = "サインイン中..."
    status_signed_in: str = "サインインしました"
    status_getting_subscriptions: str = "サブスクリプション情報取得中..."
    status_subscription_selected: str = "サブスクリプションが選択されました"
    status_please_select_subscription: str = "サブスクリプションを選択してください"
    
    # Error messages
    error_signin_failed: str = "サインインに失敗しました"
    error_signin_timeout: str = "サインインがタイムアウトしました"
    error_subscription_fetch_failed: str = "サブスクリプション情報の取得に失敗しました"
    error_please_signin: str = "サインインが完了していません"
    error_please_select_subscription: str = "サブスクリプションを選択してください"
    
    def resume_session_message(self, session_id: str) -> str:
        """Format resume session message"""
        return f"⚠️ 未完了セッションの再開: {session_id}"
    
    def timeout_message(self, timeout_seconds: int) -> str:
        """Format timeout message"""
        return (
            f"サインイン操作が {timeout_seconds}秒以内に完了しませんでした。\n\n"
            f"ブラウザでの認証操作が時間内に完了しなかった可能性があります。\n"
            f"もう一度サインインボタンを押してやり直してください。"
        )
    
    def error_message(self, error: str) -> str:
        """Format error message"""
        return f"エラー: {error}"


@dataclass
class ExistingLoginTexts:
    """Existing login screen texts"""
    
    title: str = "既存ログイン確認"
    subtitle: str = "Azure CLI の既存ログイン情報を使用します"
    
    # Info frame
    info_frame_title: str = "ログイン情報"
    user_label: str = "ユーザー:"
    user_type_label: str = "認証タイプ:"
    tenant_label: str = "テナント:"
    subscription_frame_title: str = "サブスクリプション選択"
    next_button_text: str = "次へ →"
    
    # Column headers
    col_subscription_name: str = "サブスクリプション名"
    col_subscription_id: str = "サブスクリプションID"
    col_state: str = "状態"
    
    # Navigation buttons
    back_button: str = "← 戻る"
    refresh_button: str = "🔄 更新"
    next_button: str = "次へ →"
    
    # Status messages
    status_checking: str = "ログイン状態を確認中..."
    status_ready: str = "ログイン情報を確認しました"
    status_not_logged_in: str = "ログインしていません"
    status_getting_subscriptions: str = "サブスクリプション情報取得中..."
    
    # Error messages
    error_not_logged_in: str = "Azure CLI にログインしていません"
    error_subscription_fetch_failed: str = "サブスクリプション情報の取得に失敗しました"
    error_please_select_subscription: str = "サブスクリプションを選択してください"
    
    not_logged_in_label: str = "（ログインしていません）"
    
    def error_message(self, error: str) -> str:
        """Format error message"""
        return f"エラー: {error}"


@dataclass
class SPSelectionTexts:
    """Service principal selection screen texts"""
    
    title: str = "サービスプリンシパル選択"
    subtitle: str = "保存済みのサービスプリンシパルプロファイルを選択してください"
    
    # Frame title
    profile_list_title: str = "プロファイル一覧"
    
    # Column headers
    col_name: str = "プロファイル名"
    col_last_used: str = "最終使用"
    col_tenant_id: str = "テナントID"
    col_client_id: str = "クライアントID"
    col_subscription_id: str = "サブスクリプションID"
    
    # Buttons
    back_button: str = "← 戻る"
    refresh_button: str = "🔄 更新"
    add_button: str = "➕ 新規追加"
    edit_button: str = "✏️ 編集"
    delete_button: str = "🗑️ 削除"
    select_button: str = "選択して続行 →"
    
    # Status messages
    status_ready: str = "プロファイルを選択してください"
    status_loading: str = "プロファイルを読み込んでいます..."
    status_loaded: str = "プロファイルを読み込みました"
    status_authenticating: str = "認証中..."
    status_authenticated: str = "認証が完了しました"
    authenticating_message: str = "サービスプリンシパルでログインしています..."
    authenticating_dialog_message: str = "サービスプリンシパルでログインしています..."
    
    # Messages
    no_profiles: str = "プロファイルがありません。新規追加してください。"
    no_selection: str = "プロファイルが選択されていません"
    never_used: str = "未使用"
    
    # Error messages
    error_no_selection: str = "プロファイルを選択してください"
    error_auth_failed: str = "認証に失敗しました"
    error_load_failed: str = "プロファイルの読み込みに失敗しました"
    
    def confirm_delete(self, profile_name: str) -> str:
        """Confirmation message for deleting a profile"""
        return f"プロファイル「{profile_name}」を削除してもよろしいですか？"
    
    def error_message(self, error: str) -> str:
        """Format error message"""
        return f"エラー: {error}"


@dataclass
class ProfileEditorTexts:
    """Service principal profile editor screen texts"""
    
    title_new: str = "新規プロファイル作成"
    title_edit: str = "プロファイル編集"
    title_add: str = "プロファイル追加"
    
    # Field labels
    profile_name_label: str = "プロファイル名:"
    file_name_label: str = "ファイル名:"
    file_name_note: str = "(.json は不要)"
    description_optional_label: str = "説明 (任意):"
    tenant_id_label: str = "テナントID:"
    client_id_label: str = "クライアントID:"
    client_secret_label: str = "クライアントシークレット:"
    subscription_id_label: str = "サブスクリプションID:"
    description_label: str = "説明 (任意):"
    
    # Buttons
    save_button: str = "保存"
    save_button_edit: str = "更新"
    update_button: str = "更新"
    test_button: str = "接続テスト"
    cancel_button: str = "キャンセル"
    show_secret: str = "表示"
    
    # Placeholders
    profile_name_placeholder: str = "例: production-sp"
    tenant_id_placeholder: str = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    client_id_placeholder: str = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    client_secret_placeholder: str = "クライアントシークレット"
    subscription_id_placeholder: str = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    
    # Messages
    save_success: str = "プロファイルを保存しました"
    test_success: str = "接続テストに成功しました"
    test_in_progress: str = "接続テスト中..."
    
    # Error messages
    error_empty_field: str = "すべてのフィールドを入力してください"
    error_save_failed: str = "プロファイルの保存に失敗しました"
    error_test_failed: str = "接続テストに失敗しました"
    error_invalid_format: str = "入力形式が正しくありません"
    
    def error_message(self, error: str) -> str:
        """Format error message"""
        return f"エラー: {error}"


# Singleton instances
auth_method_texts = AuthMethodTexts()
login_texts = LoginTexts()
existing_login_texts = ExistingLoginTexts()
sp_selection_texts = SPSelectionTexts()
profile_editor_texts = ProfileEditorTexts()
