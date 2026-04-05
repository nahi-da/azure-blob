"""
Azure CLI カスタムエラークラス群
"""


class AzureError(Exception):
    """Azure CLI エラー基底クラス"""
    pass


class AuthenticationError(AzureError):
    """認証エラー"""
    pass


class ResourceNotFoundError(AzureError):
    """リソース未検出"""
    pass


class InvalidCredentialsError(AuthenticationError):
    """無効な認証情報"""
    pass


class TenantNotFoundError(ResourceNotFoundError):
    """テナント未検出"""
    pass


class PermissionError(AzureError):
    """権限エラー"""
    pass


class BlobArchivedError(AzureError):
    """Blobがアーカイブ状態"""
    pass


class NetworkError(AzureError):
    """ネットワークエラー"""
    pass


class TimeoutError(AzureError):
    """タイムアウトエラー"""
    pass


class InvalidFormatError(AzureError):
    """不正な形式"""
    pass


class ContainerNotFoundError(ResourceNotFoundError):
    """コンテナ未検出"""
    pass


class StorageAccountNotFoundError(ResourceNotFoundError):
    """ストレージアカウント未検出"""
    pass


class SubscriptionNotFoundError(ResourceNotFoundError):
    """サブスクリプション未検出"""
    pass


class ConfigCommandError(AzureError):
    """設定コマンドエラー（無視可能）"""
    pass


class AccountKeyRetrievalError(AzureError):
    """アクセスキー取得エラー"""
    pass


class BlobNotFoundError(ResourceNotFoundError):
    """Blob未検出"""
    pass


class InvalidResourceNameError(AzureError):
    """不正なリソース名"""
    pass


class ServiceUnavailableError(AzureError):
    """サービス利用不可"""
    pass


class InternalServerError(AzureError):
    """内部サーバーエラー"""
    pass


class InvalidOperationError(AzureError):
    """不正な操作エラー"""
    pass


def parse_azure_cli_error(stderr: str) -> AzureError:
    """
    Azure CLIのstderrを解析して適切な例外を返す
    
    Args:
        stderr: Azure CLIの標準エラー出力
        
    Returns:
        適切なAzureErrorサブクラスのインスタンス
    """
    if not stderr:
        return AzureError("不明なエラー")
    
    stderr_lower = stderr.lower()
    
    # 認証関連
    if any(x in stderr_lower for x in ['not logged in', 'authenticationfailed', 'please run \'az login\'']):
        return AuthenticationError("Azureにログインしていません")
    
    # サービスプリンシパル関連の認証エラー
    if 'invalid_client' in stderr_lower:
        return AuthenticationError("無効なクライアントIDです。クライアントIDを確認してください")
    
    if 'invalid_secret' in stderr_lower or 'client secret' in stderr_lower:
        return AuthenticationError("無効なクライアントシークレットです。シークレットを確認してください")
    
    if 'invalid_tenant' in stderr_lower or 'tenant' in stderr_lower and 'not found' in stderr_lower:
        return AuthenticationError("無効なテナントIDです。テナントIDを確認してください")
    
    if 'aadsts' in stderr_lower and '7000215' in stderr_lower:
        return AuthenticationError("無効なクライアントシークレットです。シークレットの有効期限が切れている可能性があります")
    
    if 'aadsts' in stderr_lower and '700016' in stderr_lower:
        return AuthenticationError("アプリケーションが見つかりません。クライアントIDを確認してください")
    
    if 'aadsts' in stderr_lower and '90002' in stderr_lower:
        return AuthenticationError("テナントが見つかりません。テナントIDを確認してください")
    
    # 権限関連
    if 'authorizationpermissionmismatch' in stderr_lower or 'authorization failed' in stderr_lower:
        return PermissionError("アクセス権限がありません")
    
    # Blob関連
    if 'blobnotfound' in stderr_lower:
        return BlobNotFoundError("Blobが存在しません")
    
    if 'blobarchived' in stderr_lower:
        return BlobArchivedError("Blobがアーカイブ状態です。リハイドレートが必要です")
    
    # コンテナ関連
    if 'containernotfound' in stderr_lower:
        return ContainerNotFoundError("コンテナが存在しません")
    
    # サブスクリプション関連
    if 'subscription' in stderr_lower and ('not found' in stderr_lower or 'could not be found' in stderr_lower):
        return SubscriptionNotFoundError("サブスクリプションが見つかりません。サブスクリプションIDを確認してください")
    
    if 'subscription' in stderr_lower and 'no access' in stderr_lower:
        return PermissionError("サブスクリプションへのアクセス権限がありません")
    
    # リソース関連
    if 'resourcenotfound' in stderr_lower:
        return ResourceNotFoundError("リソースが見つかりません")
    
    if 'invalidresourcename' in stderr_lower:
        return InvalidResourceNameError("リソース名が不正です")
    
    # ネットワーク関連
    if any(x in stderr_lower for x in ['connectionerror', 'networkerror', 'connection refused', 'name resolution failed']):
        return NetworkError("ネットワークエラーが発生しました")
    
    if any(x in stderr_lower for x in ['timeout', 'timed out', 'requesttimeout']):
        return TimeoutError("タイムアウトしました")
    
    # サーバーエラー
    if 'serviceunavailable' in stderr_lower or '503' in stderr_lower:
        return ServiceUnavailableError("サービスが利用できません")
    
    if 'internalservererror' in stderr_lower or '500' in stderr_lower:
        return InternalServerError("内部サーバーエラーが発生しました")
    
    # その他
    return AzureError(f"Azure CLIエラー: {stderr}")
