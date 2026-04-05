"""Existing login screen - use current Azure CLI login"""

import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from ...ui_text.auth_texts import existing_login_texts

logger = logging.getLogger(__name__)


class ExistingLoginScreen(tk.Frame):
    """Screen to use existing Azure CLI login"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Title
        title_label = ttk.Label(self, text=existing_login_texts.title, style='Title.TLabel')
        title_label.pack(pady=20)
        
        subtitle = ttk.Label(self, text=existing_login_texts.subtitle, 
                           font=controller.heading_font)
        subtitle.pack(pady=5)
        
        # Current login info display
        info_frame = ttk.LabelFrame(self, text=existing_login_texts.info_frame_title, padding=10)
        info_frame.pack(pady=20, padx=40, fill="x")
        
        # User name
        ttk.Label(info_frame, text=existing_login_texts.user_label).grid(
            row=0, column=0, sticky="w", padx=10, pady=5)
        self.user_label = ttk.Label(info_frame, text="", font=controller.button_font)
        self.user_label.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        # User type
        ttk.Label(info_frame, text=existing_login_texts.user_type_label).grid(
            row=1, column=0, sticky="w", padx=10, pady=5)
        self.user_type_label = ttk.Label(info_frame, text="")
        self.user_type_label.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Tenant
        ttk.Label(info_frame, text=existing_login_texts.tenant_label).grid(
            row=2, column=0, sticky="w", padx=10, pady=5)
        self.tenant_label = ttk.Label(info_frame, text="")
        self.tenant_label.grid(row=2, column=1, sticky="w", padx=10, pady=5)
        
        info_frame.grid_columnconfigure(1, weight=1)
        
        # Subscription selection frame
        sub_frame = ttk.LabelFrame(self, text=existing_login_texts.subscription_frame_title, padding=10)
        sub_frame.pack(pady=10, padx=40, fill="both", expand=True)
        
        # Subscription treeview
        tree_container = tk.Frame(sub_frame)
        tree_container.pack(fill="both", expand=True)
        
        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        tree_scroll_x = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL)
        
        # Treeview
        columns = ('name', 'id', 'state')
        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show='headings',
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            selectmode='browse',
            height=3
        )
        
        # Column settings
        self.tree.heading('name', text='サブスクリプション名')
        self.tree.heading('id', text='サブスクリプションID')
        self.tree.heading('state', text='状態')
        
        self.tree.column('name', width=300, anchor=tk.W, stretch=False)
        self.tree.column('id', width=250, anchor=tk.W, stretch=False)
        self.tree.column('state', width=75, anchor=tk.W, stretch=False)
        
        # Scrollbar placement
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind selection change
        self.tree.bind('<<TreeviewSelect>>', self.on_subscription_selected)
        
        # Bind double-click
        self.tree.bind('<Double-Button-1>', lambda e: self.on_continue())
        
        # Button frame
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        
        # Back button
        self.back_button = ttk.Button(button_frame, text=existing_login_texts.back_button,
                                     command=self.go_back, width=15)
        self.back_button.pack(side="left", padx=5)
        
        # Refresh button
        self.refresh_button = ttk.Button(button_frame, text=existing_login_texts.refresh_button,
                                        command=self.load_subscriptions, width=15)
        self.refresh_button.pack(side="left", padx=5)
        
        # Continue button
        self.continue_button = ttk.Button(button_frame, text=existing_login_texts.next_button_text,
                                         command=self.on_continue, width=15,
                                         state='disabled')
        self.continue_button.pack(side="left", padx=5)
        
        # Status bar
        self.status_bar = tk.Label(self, text="", bd=1, relief=tk.SUNKEN, 
                                  anchor="w", bg="lightgray")
        self.status_bar.pack(side="bottom", fill="x")
        
        # Data storage
        self.subscriptions = []
        self.current_account = None
        self.tenants = {}  # {tenant_id: tenant_name}
    
    def on_show(self):
        """Called when screen is shown"""
        self.continue_button.state(['disabled'])
        self.refresh_button.state(['disabled'])
        self.update_status("ログイン情報を確認中...", "yellow")
        self.load_account_info()
    
    def update_status(self, message: str, color: str = "lightgray"):
        """Update status bar"""
        self.status_bar.config(text=message, bg=color)
        self.update_idletasks()
    
    def load_account_info(self):
        """Load current account information"""
        def load_thread():
            success, account, error = self.controller.azure_cli.get_current_account()
            self.after(0, lambda: self.on_account_loaded(success, account, error))
        
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def on_account_loaded(self, success: bool, account: dict, error: str):
        """Callback when account info is loaded"""
        if not success or not account:
            messagebox.showerror("エラー", 
                               f"ログイン情報の取得に失敗しました\n\n{error or '不明なエラー'}\n\n"
                               "Azure CLIで事前にログインしてください (az login)")
            self.update_status("ログイン情報の取得に失敗", "orange")
            self.continue_button.state(['disabled'])
            return
        
        self.current_account = account
        
        # Display user info
        user_info = account.get('user', {})
        user_name = user_info.get('name', '不明')
        user_type = user_info.get('type', '不明')
        tenant_id = account.get('tenantId', '不明')
        
        # Translate user type
        type_display = {
            'user': 'ユーザーアカウント',
            'servicePrincipal': 'サービスプリンシパル'
        }.get(user_type, user_type or '不明')
        
        self.user_label.config(text=user_name)
        self.user_type_label.config(text=type_display)
        
        # Display tenant ID temporarily (name will be fetched with subscriptions)
        self.tenant_label.config(text=tenant_id)
        
        # Save to controller
        self.controller.current_tenant = tenant_id
        logger.info(f"ログイン情報取得: user={user_name}, type={type_display}, tenant_id={tenant_id}")
        
        self.update_status("サブスクリプション一覧を取得中...", "yellow")
        self.load_subscriptions()
    
    def load_subscriptions(self):
        """Load subscription list"""
        def load_thread():
            success, subs, error = self.controller.azure_cli.list_subscriptions()
            self.after(0, lambda: self.on_subscriptions_loaded(success, subs, error))
        
        self.refresh_button.state(['disabled'])
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def on_subscriptions_loaded(self, success: bool, subs: list, error: str):
        """Callback when subscriptions are loaded"""
        self.refresh_button.state(['!disabled'])
        
        if not success or not subs:
            messagebox.showerror("エラー", 
                               f"サブスクリプション一覧の取得に失敗しました\n\n{error or '不明なエラー'}")
            self.update_status("サブスクリプション取得失敗", "orange")
            return
        
        self.subscriptions = subs
        
        # Get tenant names using REST API (same as LoginScreen)
        success, tenant_data, error = self.controller.azure_cli.run([
            'rest', '--method', 'get',
            '--url', 'https://management.azure.com/tenants?api-version=2022-12-01',
            '--query', 'value[].{Name: displayName, TenantID: tenantId}'
        ])
        
        if success and tenant_data:
            for tenant in tenant_data:
                tenant_id = tenant.get('TenantID', '')
                tenant_name = tenant.get('Name')
                # displayNameがNoneまたは空の場合は、tenant_idを使用
                if not tenant_name:
                    tenant_name = tenant_id
                    logger.warning(f"テナント名が取得できないため、IDを使用: {tenant_id}")
                if tenant_id:
                    self.tenants[tenant_id] = tenant_name
        else:
            # Fallback: use tenantDisplayName from subscriptions
            logger.warning(f"テナント情報のREST API取得に失敗、サブスクリプション情報から取得します")
            for sub in subs:
                tenant_id = sub.get('tenantId')
                tenant_name = sub.get('tenantDisplayName')
                # tenantDisplayNameがNoneまたは空の場合は、tenant_idを使用
                if not tenant_name:
                    tenant_name = tenant_id
                if tenant_id:
                    self.tenants[tenant_id] = tenant_name
        
        # Update current tenant display
        if self.current_account:
            current_tenant_id = self.current_account.get('tenantId', '')
            if current_tenant_id:
                tenant_name = self.tenants.get(current_tenant_id, current_tenant_id)
                # tenant_nameがNoneの場合は、tenant_idを使用
                if not tenant_name:
                    tenant_name = current_tenant_id
                    logger.warning(f"テナント名がNoneのため、IDを使用: {current_tenant_id}")
                self.tenant_label.config(text=f"{tenant_name} ({current_tenant_id})" if tenant_name != current_tenant_id else current_tenant_id)
                self.controller.current_tenant = tenant_name
                logger.info(f"テナント情報更新: tenant_id={current_tenant_id}, tenant_name={tenant_name}, tenants_count={len(self.tenants)}")
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Populate tree
        default_sub = None
        for sub in subs:
            sub_name = sub.get('name', '不明')
            sub_id = sub.get('id', '不明')
            sub_state = sub.get('state', '不明')
            is_default = sub.get('isDefault', False)
            
            # Translate state
            state_display = {
                'Enabled': '有効',
                'Disabled': '無効',
                'Warned': '警告',
                'PastDue': '期限切れ',
                'Deleted': '削除済み'
            }.get(sub_state, sub_state)
            
            # Add tag for default
            display_name = f"⭐ {sub_name}" if is_default else sub_name
            
            item_id = self.tree.insert('', tk.END, values=(display_name, sub_id, state_display))
            
            if is_default:
                default_sub = item_id
        
        # Select default subscription
        if default_sub:
            self.tree.selection_set(default_sub)
            self.tree.see(default_sub)
            self.continue_button.state(['!disabled'])
        elif len(subs) > 0:
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item)
            self.tree.see(first_item)
            self.continue_button.state(['!disabled'])
        
        self.update_status(f"サブスクリプション {len(subs)}件を取得しました", "lightgreen")
    
    def on_subscription_selected(self, event):
        """Handle subscription selection change"""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get subscription ID
        sub_id = self.tree.item(selection[0])['values'][1]  # ID is the second column
        
        # Find subscription details
        selected_sub = None
        for sub in self.subscriptions:
            if sub.get('id') == sub_id:
                selected_sub = sub
                break
        
        if not selected_sub:
            return
        
        # Update tenant display for the selected subscription
        tenant_id = selected_sub.get('tenantId', '')
        if not tenant_id and self.current_account:
            # Fallback: サブスクリプションにtenant_idがない場合、アカウント情報から取得
            tenant_id = self.current_account.get('tenantId', '')
        
        if tenant_id:
            tenant_name = self.tenants.get(tenant_id, tenant_id)
            # tenant_nameがNoneの場合は、tenant_idを使用
            if not tenant_name:
                tenant_name = tenant_id
                logger.warning(f"サブスクリプション選択時にテナント名がNoneのため、IDを使用: {tenant_id}")
            self.tenant_label.config(text=f"{tenant_name} ({tenant_id})" if tenant_name != tenant_id else tenant_id)
            self.controller.current_tenant = tenant_name
            logger.info(f"サブスクリプション選択時のテナント情報更新: tenant_id={tenant_id}, tenant_name={tenant_name}")
    
    def on_continue(self):
        """Continue button handler"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "サブスクリプションを選択してください")
            return
        
        # Get selected subscription
        item = selected[0]
        values = self.tree.item(item, 'values')
        sub_id = values[1]  # ID column
        
        # Find subscription details
        selected_sub = None
        for sub in self.subscriptions:
            if sub.get('id') == sub_id:
                selected_sub = sub
                break
        
        if not selected_sub:
            messagebox.showerror("エラー", "サブスクリプション情報の取得に失敗しました")
            return
        
        # Update tenant display for the selected subscription
        tenant_id = selected_sub.get('tenantId', '')
        if not tenant_id and self.current_account:
            # Fallback: サブスクリプションにtenant_idがない場合、アカウント情報から取得
            tenant_id = self.current_account.get('tenantId', '')
            logger.warning(f"サブスクリプション情報にtenant_idが含まれていないため、アカウント情報から取得: {tenant_id}")
        
        if tenant_id:
            tenant_name = self.tenants.get(tenant_id, tenant_id)
            # tenant_nameがNoneの場合は、tenant_idを使用
            if not tenant_name:
                tenant_name = tenant_id
                logger.warning(f"続行時にテナント名がNoneのため、IDを使用: {tenant_id}")
            self.tenant_label.config(text=f"{tenant_name} ({tenant_id})" if tenant_name != tenant_id else tenant_id)
            self.controller.current_tenant = tenant_name
            logger.info(f"続行時のテナント情報更新: tenant_id={tenant_id}, tenant_name={tenant_name}")
        else:
            logger.error("テナントIDが取得できませんでした")
            messagebox.showerror("エラー", "テナント情報の取得に失敗しました\n\nサブスクリプションとアカウント情報の両方にtenant_idが含まれていません。")
            return
        
        # Set subscription if not already active
        if not selected_sub.get('isDefault', False):
            self.update_status(f"サブスクリプションを設定中...", "yellow")
            self.set_active_subscription(sub_id, selected_sub)
        else:
            # Already active - proceed directly
            self.save_and_continue(selected_sub)
    
    def set_active_subscription(self, sub_id: str, sub_info: dict):
        """Set active subscription"""
        def set_thread():
            success, error = self.controller.azure_cli.set_subscription(sub_id)
            self.after(0, lambda: self.on_subscription_set(success, error, sub_info))
        
        thread = threading.Thread(target=set_thread, daemon=True)
        thread.start()
    
    def on_subscription_set(self, success: bool, error: str, sub_info: dict):
        """Callback when subscription is set"""
        if not success:
            messagebox.showerror("エラー", 
                               f"サブスクリプションの設定に失敗しました\n\n{error or '不明なエラー'}")
            self.update_status("サブスクリプション設定失敗", "orange")
            return
        
        self.save_and_continue(sub_info)
    
    def save_and_continue(self, sub_info: dict):
        """Save subscription info and continue to next screen"""
        # Save subscription info to controller
        self.controller.current_subscription = {
            'id': sub_info.get('id', ''),
            'name': sub_info.get('name', '')
        }
        
        # テナント情報が設定されているか確認
        if not self.controller.current_tenant:
            logger.error(f"current_tenantが未設定です - サブスクリプション: {sub_info.get('name')}")
            # フォールバック: サブスクリプションからテナントIDを取得
            tenant_id = sub_info.get('tenantId', '')
            if not tenant_id and self.current_account:
                tenant_id = self.current_account.get('tenantId', '')
            
            if tenant_id:
                tenant_name = self.tenants.get(tenant_id, tenant_id)
                # tenant_nameがNoneの場合は、tenant_idを使用
                if not tenant_name:
                    tenant_name = tenant_id
                    logger.warning(f"save_and_continueでテナント名がNoneのため、IDを使用: {tenant_id}")
                self.controller.current_tenant = tenant_name
                logger.info(f"save_and_continueでテナント情報を復元: tenant_id={tenant_id}, tenant_name={tenant_name}")
            else:
                logger.error(f"テナント情報を取得できません - sub_info={sub_info}, current_account={self.current_account}")
                messagebox.showerror("エラー", "テナント情報が設定されていません\n\n認証画面からやり直してください。")
                return
        
        # Set auth method
        self.controller.auth_method = 'existing'
        
        logger.info(f"既存ログイン使用: Subscription={sub_info.get('name')}, Tenant={self.controller.current_tenant}")
        
        self.update_status("認証完了", "lightgreen")
        
        # Check if resuming incomplete session
        if hasattr(self.controller, 'resuming_session') and self.controller.resuming_session:
            # Resume incomplete session
            logger.info("未完了セッションを再開します")
            
            # Navigate to progress screen after delay
            self.after(1000, lambda: self.controller.show_frame("ProgressScreen"))
            
            # Clear resuming flag
            self.controller.resuming_session = False
        else:
            # Normal flow - go to blob selection
            self.controller.show_frame("BlobSelectionMethodScreen")
    
    def go_back(self):
        """Back button handler"""
        self.controller.show_frame("AuthenticationMethodScreen")
