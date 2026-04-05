"""Azure CLI wrapper class"""

import subprocess
import json
import time
import logging
from typing import List, Tuple, Any, Optional, Dict

from .exceptions import *
from .config import ConfigManager

logger = logging.getLogger(__name__)


class AzureCLIWrapper:
    """Azure CLI wrapper class with retry functionality"""
    
    def __init__(self, config: ConfigManager):
        """Initialize
        
        Args:
            config: Configuration manager
        """
        self.config = config
        self.max_retry = config.get('max_retry_count', 3)
        self.retry_delay = config.get('retry_delay_seconds', 10)
        self.default_timeout = config.get('azure_cli_default_timeout', 300)
        self.login_timeout = config.get('azure_cli_login_timeout', 60)
    
    @staticmethod
    def _quote_arg(arg: str) -> str:
        """Quote command argument appropriately
        
        Args:
            arg: Argument string
            
        Returns:
            Quoted argument
        """
        if ' ' in arg or '&' in arg or '|' in arg or '>' in arg or '<' in arg or '^' in arg or '(' in arg or ')' in arg:
            return f'"{arg.replace(chr(34), chr(34) + chr(34))}"'
        return arg
    
    def _build_command_string(self, args: List[str]) -> str:
        """Build command string
        
        Args:
            args: List of command arguments
            
        Returns:
            Executable command string
        """
        quoted_args = [self._quote_arg(arg) for arg in args]
        return 'az ' + ' '.join(quoted_args)
    
    def run(self, args: List[str], capture_json: bool = True, 
            timeout: Optional[int] = None, allow_retry: bool = True) -> Tuple[bool, Any, Optional[str]]:
        """Execute Azure CLI command with retry functionality
        
        Args:
            args: List of command arguments (e.g. ['account', 'list'])
            capture_json: Whether to parse as JSON
            timeout: Timeout in seconds (uses default if None)
            allow_retry: Whether to allow retry
            
        Returns:
            (success flag, result data, error message)
        """
        if timeout is None:
            timeout = self.default_timeout
        
        command_str = self._build_command_string(args)
        retry_count = 0
        
        while True:
            try:
                logger.info(f"Azure CLIコマンド実行: {command_str}")
                
                result = subprocess.run(
                    command_str,
                    capture_output=True,
                    text=True,
                    encoding='shift-jis',
                    timeout=timeout,
                    shell=True
                )
                
                if result.returncode == 0:
                    if capture_json and result.stdout.strip():
                        try:
                            data = json.loads(result.stdout)
                            logger.info(f"コマンド成功: {len(str(data))}バイトのデータ取得")
                            return True, data, None
                        except json.JSONDecodeError as e:
                            logger.warning(f"JSON解析失敗: {e}")
                            return True, result.stdout, None
                    else:
                        logger.info("コマンド成功")
                        return True, result.stdout, None
                else:
                    stderr = result.stderr
                    stdout = result.stdout
                    logger.error(f"コマンド失敗 (終了コード: {result.returncode}): {stderr}")
                    
                    error_message = stderr
                    if not error_message or not error_message.strip():
                        error_message = stdout
                    if not error_message or not error_message.strip():
                        error_message = f"コマンドが終了コード {result.returncode} で失敗しました"
                    
                    if allow_retry and retry_count < self.max_retry:
                        error = parse_azure_cli_error(error_message)
                        if isinstance(error, (NetworkError, TimeoutError, ServiceUnavailableError, InternalServerError)):
                            retry_count += 1
                            wait_time = self.retry_delay * (2 ** (retry_count - 1))
                            logger.warning(f"リトライ {retry_count}/{self.max_retry}... ({wait_time}秒後)")
                            time.sleep(wait_time)
                            continue
                    
                    return False, None, error_message
            
            except subprocess.TimeoutExpired:
                logger.error(f"コマンドがタイムアウトしました（{timeout}秒）")
                
                if allow_retry and retry_count < self.max_retry:
                    retry_count += 1
                    wait_time = self.retry_delay * (2 ** (retry_count - 1))
                    logger.warning(f"リトライ {retry_count}/{self.max_retry}... ({wait_time}秒後)")
                    time.sleep(wait_time)
                    continue
                
                return False, None, "コマンドがタイムアウトしました"
            
            except Exception as e:
                logger.error(f"コマンド実行エラー: {e}")
                return False, None, str(e)
    
    def run_with_realtime_output(self, args: List[str], output_callback=None, timeout: Optional[int] = None) -> Tuple[bool, str]:
        """Execute Azure CLI command with realtime output
        
        Args:
            args: List of command arguments
            output_callback: Callback function to receive output
            timeout: Timeout in seconds (uses default if None)
            
        Returns:
            (success flag, stdout)
        """
        if timeout is None:
            timeout = self.default_timeout
        
        command_str = self._build_command_string(args)
        logger.info(f"Azure CLIコマンド実行（リアルタイム出力）: {command_str}")
        
        process = None
        try:
            process = subprocess.Popen(
                command_str,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='shift-jis',
                bufsize=1,
                shell=True
            )
            
            output = []
            if process.stdout:
                for line in process.stdout:
                    if line:
                        output.append(line)
                        if output_callback:
                            output_callback(line)
            
            process.wait(timeout=timeout)
            
            full_output = ''.join(output)
            if process.returncode == 0:
                logger.info("コマンド成功")
                return True, full_output
            else:
                logger.error(f"コマンド失敗 (終了コード: {process.returncode})")
                return False, full_output
        
        except subprocess.TimeoutExpired:
            logger.error(f"コマンドがタイムアウトしました（{timeout}秒）")
            if process:
                try:
                    process.kill()
                    logger.info("タイムアウトしたプロセスを終了しました")
                except Exception as e:
                    logger.warning(f"プロセス終了時にエラー: {e}")
            raise  # Re-raise to be handled by caller
        
        except Exception as e:
            logger.error(f"コマンド実行エラー: {e}")
            return False, str(e)
    
    def login_with_service_principal(self, tenant_id: str, client_id: str, 
                                      client_secret: str, subscription_id: str) -> Tuple[bool, str]:
        """Login with service principal
        
        Args:
            tenant_id: Tenant ID
            client_id: Client ID (Application ID)
            client_secret: Client secret
            subscription_id: Subscription ID
        
        Returns:
            (success flag, message)
        """
        try:
            logger.info("既存のAzureセッションをクリア中...")
            logout_success, _, _ = self.run(['logout'], allow_retry=False, timeout=30)
            if logout_success:
                logger.info("ログアウト成功")
            else:
                logger.warning("ログアウトコマンドが失敗しましたが続行します")
            
            logger.info("アカウント設定をクリア中...")
            clear_success, _, _ = self.run(['account', 'clear'], allow_retry=False, timeout=30)
            if clear_success:
                logger.info("アカウントクリア成功")
            else:
                logger.warning("アカウントクリアが失敗しましたが続行します")
            
            logger.info("Azure CLI構成をリセット中...")
            self.run(['config', 'set', 'core.output=json'], allow_retry=False, timeout=30)
            self.run(['config', 'set', 'core.collect_telemetry=false'], allow_retry=False, timeout=30)
            
            logger.info("サービスプリンシパルでログイン中...")
            login_success, output, error = self.run([
                'login',
                '--service-principal',
                '--username', client_id,
                '--password', client_secret,
                '--tenant', tenant_id
            ], timeout=60)
            
            if not login_success:
                parsed_error = parse_azure_cli_error(error if error else "")
                error_msg = str(parsed_error)
                logger.error(f"サービスプリンシパルログイン失敗: {error_msg}")
                return False, error_msg
            
            logger.info("サービスプリンシパルログイン成功")
            
            logger.info(f"サブスクリプション設定中: {subscription_id}")
            sub_success, _, sub_error = self.run([
                'account', 'set',
                '--subscription', subscription_id
            ], timeout=30)
            
            if not sub_success:
                parsed_error = parse_azure_cli_error(sub_error if sub_error else "")
                error_msg = str(parsed_error)
                logger.error(f"サブスクリプション設定失敗: {error_msg}")
                return False, error_msg
            
            logger.info("サブスクリプション設定成功")
            return True, "サービスプリンシパル認証成功"
            
        except Exception as e:
            error_msg = f"サービスプリンシパルログイン中にエラー発生: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def list_blobs_with_prefix(self, storage_account: str, container: str, 
                               prefix: str, account_key: str) -> Tuple[bool, List[Dict], Optional[str]]:
        """Get blob list with prefix (with pagination support)
        
        Args:
            storage_account: Storage account name
            container: Container name
            prefix: Prefix
            account_key: Access key
            
        Returns:
            (success flag, complete blob list, error message)
        """
        logger.info(f"Blob一覧取得: {storage_account}/{container} (prefix: {prefix})")
        
        all_blobs = []
        marker = None
        page = 1
        
        while True:
            args = [
                'storage', 'blob', 'list',
                '--account-name', storage_account,
                '--container-name', container,
                '--account-key', account_key,
                '--output', 'json',
                '--show-next-marker'
            ]
            
            if prefix:
                args.extend(['--prefix', prefix])
            
            if marker:
                args.extend(['--marker', marker])
                logger.info(f"Blob一覧取得（ページ{page}、継続トークン使用）...")
            
            success, data, error = self.run(args, capture_json=True, timeout=300)
            
            if not success:
                error_msg = error if error else f"Blob一覧取得失敗（ページ{page}）"
                logger.error(error_msg)
                # 既に取得したBlobがあれば部分的な結果として返す
                if all_blobs:
                    logger.warning(f"部分的な結果を返します: {len(all_blobs)}件（{page-1}ページまで）")
                    return False, all_blobs, error_msg
                else:
                    return False, [], error_msg
            
            # レスポンスは配列形式で、最後の要素が {"nextMarker": "..."} というオブジェクト
            if not isinstance(data, list):
                logger.error(f"予期しないレスポンス形式: {type(data)}")
                return False, all_blobs if all_blobs else [], "予期しないレスポンス形式"
            
            # 最後の要素を確認
            if len(data) > 0 and isinstance(data[-1], dict) and 'nextMarker' in data[-1]:
                # nextMarkerが含まれている場合、最後の要素を除いた部分がBlob情報
                blobs = data[:-1]
                marker = data[-1].get('nextMarker')
            else:
                # nextMarkerがない場合、全体がBlob情報
                blobs = data
                marker = None
            
            all_blobs.extend(blobs)
            logger.info(f"ページ{page}: {len(blobs)}件取得（累計: {len(all_blobs)}件）")
            
            # nextMarkerがない、または空の場合は終了
            if not marker:
                break
            
            page += 1
        
        logger.info(f"Blob一覧取得完了: 合計{len(all_blobs)}件（{page}ページ）")
        return True, all_blobs, None
    
    def get_current_account(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Get current logged in account information
        
        Returns:
            (success flag, account info dict, error message)
            Account info contains: user/servicePrincipal info, subscription details, tenant
        """
        logger.info("現在のログイン状態を確認中...")
        
        success, data, error = self.run(['account', 'show'], capture_json=True, timeout=30, allow_retry=False)
        
        if success and isinstance(data, dict):
            user_info = data.get('user', {})
            user_name = user_info.get('name', 'Unknown')
            user_type = user_info.get('type', 'Unknown')
            subscription_name = data.get('name', 'Unknown')
            subscription_id = data.get('id', 'Unknown')
            tenant_id = data.get('tenantId', 'Unknown')
            
            logger.info(f"ログイン済み: {user_name} ({user_type}), Subscription: {subscription_name}")
            return True, data, None
        else:
            logger.info("ログインしていません")
            return False, None, error if error else "ログインしていません"
    
    def list_subscriptions(self) -> Tuple[bool, List[Dict], Optional[str]]:
        """Get list of available subscriptions for current logged in account
        
        Returns:
            (success flag, subscription list, error message)
            Each subscription dict contains: id, name, state, isDefault, tenantId
        """
        logger.info("サブスクリプション一覧を取得中...")
        
        success, data, error = self.run(['account', 'list'], capture_json=True, timeout=60, allow_retry=False)
        
        if success and isinstance(data, list):
            logger.info(f"サブスクリプション取得成功: {len(data)}件")
            return True, data, None
        else:
            error_msg = error if error else "サブスクリプション一覧取得失敗"
            logger.error(error_msg)
            return False, [], error_msg
    
    def set_subscription(self, subscription_id: str) -> Tuple[bool, Optional[str]]:
        """Set active subscription
        
        Args:
            subscription_id: Subscription ID to set as active
            
        Returns:
            (success flag, error message)
        """
        logger.info(f"サブスクリプション設定中: {subscription_id}")
        
        success, _, error = self.run([
            'account', 'set',
            '--subscription', subscription_id
        ], timeout=30, allow_retry=False)
        
        if success:
            logger.info("サブスクリプション設定成功")
            return True, None
        else:
            error_msg = error if error else "サブスクリプション設定失敗"
            logger.error(error_msg)
            return False, error_msg
