"""Login screen for user authentication"""

import logging
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from ...ui_text.auth_texts import login_texts

logger = logging.getLogger(__name__)


class LoginScreen(tk.Frame):
    """Login screen"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Title
        title_label = ttk.Label(self, text=login_texts.title, style='Title.TLabel')
        title_label.pack(pady=5)
        
        subtitle = ttk.Label(self, text=login_texts.subtitle, 
                           font=controller.heading_font)
        subtitle.pack(pady=5)
        
        # Resume session info label (initially hidden)
        self.resume_info_label = ttk.Label(self, text="", 
                                          font=(controller.default_font[0], 10),
                                          foreground="blue")
        self.resume_info_label.pack(pady=5)
        
        # Sign-in button
        self.signin_button = ttk.Button(self, text=login_texts.signin_button,
                                       command=self.start_signin, width=20)
        self.signin_button.pack(pady=10)
        
        # User info display area
        info_frame = ttk.LabelFrame(self, text=login_texts.info_frame_title, padding=10)
        info_frame.pack(pady=5, padx=40, fill="x")
        
        # User name
        ttk.Label(info_frame, text=login_texts.user_label).grid(
            row=0, column=0, sticky="w", padx=10, pady=5)
        self.user_label = ttk.Label(info_frame, text=login_texts.user_not_logged_in, font=controller.button_font)
        self.user_label.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        # Tenant
        ttk.Label(info_frame, text=login_texts.tenant_label).grid(
            row=1, column=0, sticky="w", padx=10, pady=5)
        self.tenant_label = ttk.Label(info_frame, text="")
        self.tenant_label.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Subscription selection
        ttk.Label(info_frame, text=login_texts.subscription_label).grid(
            row=2, column=0, sticky="w", padx=10, pady=5)
        self.subscription_combo = ttk.Combobox(info_frame, state="disabled", width=50)
        self.subscription_combo.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        self.subscription_combo.bind("<<ComboboxSelected>>", self.on_subscription_changed)
        
        info_frame.grid_columnconfigure(1, weight=1)
        
        # Button frame for Back and Next buttons
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        
        # Back button
        self.back_button = ttk.Button(button_frame, text=login_texts.back_button,
                                     command=self.go_back, width=15)
        self.back_button.pack(side="left", padx=5)
        
        # Next button
        self.next_button = ttk.Button(button_frame, text=login_texts.next_button,
                                     command=self.go_next, width=15)
        self.next_button.pack(side="left", padx=5)
        
        # Status bar
        self.status_bar = tk.Label(self, text=login_texts.status_signin_required, bd=1, relief=tk.SUNKEN, 
                                  anchor="w", bg="lightgray")
        self.status_bar.pack(side="bottom", fill="x")
        
        # Data storage
        self.subscriptions = []
        self.tenants = {}  # {tenant_id: tenant_name}
    
    def on_show(self):
        """Called when screen is shown"""
        # Show resume session info if available
        if hasattr(self.controller, 'resuming_session') and self.controller.resuming_session:
            session_id = getattr(self.controller, 'session_id', '不明')
            self.resume_info_label.config(
                text=login_texts.resume_session_message(session_id)
            )
        else:
            self.resume_info_label.config(text="")

    
    def start_signin(self):
        """Start sign-in process"""
        self.signin_button.state(['disabled'])
        self.update_status(login_texts.status_signing_in, "yellow")
        
        # Run in separate thread
        thread = threading.Thread(target=self.do_signin)
        thread.daemon = True
        thread.start()
    
    def do_signin(self):
        """Sign-in process"""
        try:
            # Logout
            logger.info("既存のログインをクリア中...")
            self.controller.azure_cli.run(['logout'], allow_retry=False)
            self.controller.azure_cli.run(['account', 'clear'], allow_retry=False)
            
            # Config commands (ignore errors)
            self.controller.azure_cli.run(['config', 'set', 'core.enable_broker_on_windows=false'], 
                                        allow_retry=False)
            self.controller.azure_cli.run(['config', 'set', 'core.login_experience_v2=off'], 
                                        allow_retry=False)
            
            # Login (with realtime output)
            logger.info("Azureログイン実行中...")
            login_timeout = self.controller.azure_cli.login_timeout
            self.after(0, lambda: self.update_status(
                f"ブラウザでログインしてください（{login_timeout}秒以内）...", "yellow"
            ))
            
            # Import AuthenticationError from core
            from ...core import AuthenticationError
            
            success, output = self.controller.azure_cli.run_with_realtime_output(
                ['login'], 
                timeout=login_timeout
            )
            
            if not success:
                raise AuthenticationError("ログインに失敗しました")
            
            # Get account info
            self.after(0, lambda: self.update_status("アカウント情報取得中...", "yellow"))
            success, data, error = self.controller.azure_cli.run(['account', 'list'])
            
            if not success:
                raise AuthenticationError(f"アカウント情報取得失敗: {error}")
            
            # Data validation
            if data is None:
                logger.error("アカウント情報取得: dataがNone")
                raise AuthenticationError("アカウント情報が取得できませんでした")
            
            if not isinstance(data, list):
                logger.error(f"アカウント情報取得: dataの型が不正: {type(data)}")
                raise AuthenticationError(f"アカウント情報の形式が不正です（{type(data).__name__}）")
            
            self.subscriptions = data
            
            if not self.subscriptions or len(self.subscriptions) == 0:
                logger.error("有効なサブスクリプションが見つかりません")
                raise AuthenticationError(
                    "有効なサブスクリプションが見つかりません。\n\n"
                    "考えられる原因:\n"
                    "• サブスクリプションが無効化されている\n"
                    "• サブスクリプションへのアクセス権限がない\n"
                    "• サブスクリプションが割り当てられていない\n\n"
                    "Azureポータルでサブスクリプションの状態を確認してください。"
                )
            
            logger.info(f"サブスクリプション取得成功: {len(self.subscriptions)}件")
            
            # Get user name
            user_name = self.subscriptions[0].get('user', {}).get('name', '不明')
            logger.info(f"ユーザー名: {user_name}")
            
            # Get tenant names (REST API)
            self.after(0, lambda: self.update_status("テナント情報取得中...", "yellow"))
            success, tenant_data, error = self.controller.azure_cli.run([
                'rest', '--method', 'get',
                '--url', 'https://management.azure.com/tenants?api-version=2022-12-01',
                '--query', 'value[].{Name: displayName, TenantID: tenantId}'
            ])
            
            if success and tenant_data:
                for tenant in tenant_data:
                    self.tenants[tenant['TenantID']] = tenant['Name']
            else:
                # Fallback: use tenantDisplayName from az account list
                for sub in self.subscriptions:
                    tenant_id = sub.get('tenantId')
                    tenant_name = sub.get('tenantDisplayName', tenant_id)
                    if tenant_id:
                        self.tenants[tenant_id] = tenant_name
            
            # Update GUI
            self.after(0, lambda: self.update_ui_after_signin(user_name))
            
        except subprocess.TimeoutExpired:
            login_timeout = self.controller.azure_cli.login_timeout
            error_msg = login_texts.timeout_message(login_timeout)
            logger.error(f"サインインタイムアウト（{login_timeout}秒）")
            self.after(0, lambda msg=error_msg: self.show_signin_timeout(msg))
        
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"サインインエラー: {error_msg}")
            self.after(0, lambda msg=error_msg: self.show_signin_error(msg))
    
    def update_ui_after_signin(self, user_name: str):
        """Update UI after successful sign-in"""
        # Data validation
        if not self.subscriptions or not isinstance(self.subscriptions, list):
            logger.error(f"update_ui_after_signin: subscriptionsが不正: {self.subscriptions}")
            messagebox.showerror(
                "エラー",
                "サブスクリプション情報が正しく取得できませんでした。\n"
                "再度サインインしてください。"
            )
            self.signin_button.state(['!disabled'])
            self.update_status("サインイン失敗: サブスクリプション情報不正", "red")
            return
        
        # Display user name
        self.user_label.config(text=user_name)
        
        # Display subscription list
        try:
            sub_names = [f"{sub['name']} ({sub['id']})" for sub in self.subscriptions]
        except (KeyError, TypeError) as e:
            logger.error(f"サブスクリプション名/ID取得エラー: {e}, subscriptions: {self.subscriptions}")
            messagebox.showerror(
                "エラー",
                "サブスクリプション情報の形式が不正です。\n"
                "Azureアカウントの設定を確認してください。"
            )
            self.signin_button.state(['!disabled'])
            self.update_status("サインイン失敗: データ形式不正", "red")
            return
        self.subscription_combo['values'] = sub_names
        self.subscription_combo.config(state="readonly")
        
        # Resume mode: auto-select saved subscription
        if hasattr(self.controller, 'resuming_session') and self.controller.resuming_session:
            # Search for saved subscription ID
            saved_sub_id = self.controller.current_subscription.get('id', '') if self.controller.current_subscription else ''
            matched_index = next((i for i, sub in enumerate(self.subscriptions) 
                                if sub['id'] == saved_sub_id), -1)
            
            if matched_index >= 0:
                self.subscription_combo.current(matched_index)
                self.on_subscription_changed(None)
                
                # After subscription setup, automatically transition to progress screen
                logger.info(f"セッション復帰: ログイン完了 - 進捗画面へ遷移")
                self.controller.resuming_session = False  # Clear flag
                self.after(1000, lambda: self.controller.show_frame("ProgressScreen", add_to_history=False))
                return
            else:
                # Subscription not found
                logger.warning(f"保存されたサブスクリプションが見つかりません: {saved_sub_id}")
                messagebox.showwarning(
                    "警告",
                    f"前回使用していたサブスクリプションが見つかりません。\n"
                    f"サブスクリプションを選択して「次へ」をクリックしてください。"
                )
                self.controller.resuming_session = False
        
        # Normal mode: select default subscription
        else:
            default_sub = next((i for i, sub in enumerate(self.subscriptions) if sub.get('isDefault')), 0)
            self.subscription_combo.current(default_sub)
            self.on_subscription_changed(None)
        
        # Enable buttons
        self.signin_button.state(['!disabled'])
        self.next_button.state(['!disabled'])
        
        # Update status
        self.update_status("サインイン成功", "lightgreen")
        
        logger.info(f"サインイン成功: {user_name}")
    
    def show_signin_timeout(self, error_msg: str):
        """Show sign-in timeout error"""
        logger.info("タイムアウトエラー表示")
        self.update_status(login_texts.error_signin_timeout, "orange")
        self.signin_button.state(['!disabled'])  # Re-enable sign-in button
        messagebox.showwarning(login_texts.error_signin_timeout, error_msg)
    
    def show_signin_error(self, error_msg: str):
        """Show sign-in error"""
        self.signin_button.state(['!disabled'])
        
        # Display failure message in status bar
        self.update_status(f"サインイン失敗", "red")
        messagebox.showerror("サインインエラー", f"サインインに失敗しました:\n{error_msg}")
    
    def on_subscription_changed(self, event):
        """Subscription selection change handler"""
        index = self.subscription_combo.current()
        if index >= 0 and index < len(self.subscriptions):
            subscription = self.subscriptions[index]
            tenant_id = subscription.get('tenantId', '')
            tenant_name = self.tenants.get(tenant_id, tenant_id)
            
            self.tenant_label.config(text=tenant_name)
            
            # Set subscription
            self.controller.current_subscription = subscription
            self.controller.current_tenant = tenant_name
            
            # Set subscription in Azure CLI
            thread = threading.Thread(target=self._set_subscription, args=(subscription['id'],))
            thread.daemon = True
            thread.start()
    
    def _set_subscription(self, subscription_id: str):
        """Set subscription (separate thread)"""
        try:
            self.controller.azure_cli.run(['account', 'set', '--subscription', subscription_id])
            logger.info(f"サブスクリプション設定: {subscription_id}")
        except Exception as e:
            logger.exception(f"サブスクリプション設定エラー: {e}")
    
    def update_status(self, message: str, color: str = "lightgray"):
        """Update status bar"""
        self.status_bar.config(text=message, bg=color)
    
    def go_back(self):
        """Go back to authentication method selection screen"""
        self.controller.show_frame("AuthenticationMethodScreen")
    
    def go_next(self):
        """Go to next screen"""
        if not self.controller.current_subscription:
            messagebox.showwarning("警告", "サブスクリプションを選択してください")
            return
        
        self.controller.show_frame("BlobSelectionMethodScreen")
