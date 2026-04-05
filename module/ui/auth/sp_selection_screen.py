"""Service principal selection screen"""

import logging
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any, Dict

from ...ui_text.auth_texts import sp_selection_texts

logger = logging.getLogger(__name__)


class ServicePrincipalSelectionScreen(tk.Frame):
    """Service principal selection screen"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.sort_column = None
        self.sort_reverse = False
        
        # Title
        title_label = ttk.Label(self, text=sp_selection_texts.title, style='Title.TLabel')
        title_label.pack(pady=5)
        
        # Subtitle
        subtitle = ttk.Label(self, text=sp_selection_texts.subtitle, 
                           font=controller.heading_font)
        subtitle.pack(pady=5)
        
        # Treeview frame
        tree_frame = ttk.LabelFrame(self, text=sp_selection_texts.profile_list_title, padding=10)
        tree_frame.pack(pady=10, padx=40, fill=tk.BOTH, expand=True)
        
        # Scrollbars container
        tree_container = tk.Frame(tree_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        tree_scroll_x = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL)
        
        # Treeview
        columns = ('name', 'last_used', 'tenant_id', 'client_id', 'subscription_id')
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
        self.tree.heading('name', text=sp_selection_texts.col_name, command=lambda: self.sort_by_column('name'))
        self.tree.heading('last_used', text=sp_selection_texts.col_last_used, command=lambda: self.sort_by_column('last_used'))
        self.tree.heading('tenant_id', text=sp_selection_texts.col_tenant_id)
        self.tree.heading('client_id', text=sp_selection_texts.col_client_id)
        self.tree.heading('subscription_id', text=sp_selection_texts.col_subscription_id)
        
        self.tree.column('name', width=250, anchor=tk.W, stretch=False)
        self.tree.column('last_used', width=120, anchor=tk.W, stretch=False)
        self.tree.column('tenant_id', width=250, anchor=tk.W, stretch=False)
        self.tree.column('client_id', width=250, anchor=tk.W, stretch=False)
        self.tree.column('subscription_id', width=250, anchor=tk.W, stretch=False)
        
        # Scrollbar placement
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind double-click
        self.tree.bind('<Double-Button-1>', lambda e: self.on_select())
        
        # Button frame
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        
        # Back button
        ttk.Button(button_frame, text=sp_selection_texts.back_button, command=self.on_back, width=15).pack(side="left", padx=5)
        
        # Refresh button
        ttk.Button(button_frame, text=sp_selection_texts.refresh_button, command=self.load_profiles, width=15).pack(side="left", padx=5)
        
        # Management buttons
        ttk.Button(button_frame, text=sp_selection_texts.add_button, command=self.on_add, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text=sp_selection_texts.edit_button, command=self.on_edit, width=15).pack(side="left", padx=5)
        ttk.Button(button_frame, text=sp_selection_texts.delete_button, command=self.on_delete, width=15).pack(side="left", padx=5)
        
        # Select button
        ttk.Button(button_frame, text=sp_selection_texts.select_button, command=self.on_select, width=15, 
                  style='Accent.TButton').pack(side="left", padx=5)
        
        # Status bar
        self.status_bar = tk.Label(self, text="", bd=1, relief=tk.SUNKEN, 
                                  anchor="w", bg="lightgray")
        self.status_bar.pack(side="bottom", fill="x")
    
    def on_show(self):
        """Called when screen is shown"""
        self.update_status("プロファイル一覧を読み込み中...", "yellow")
        self.load_profiles()
    
    def update_status(self, message: str, color: str = "lightgray"):
        """Update status bar"""
        self.status_bar.config(text=message, bg=color)
        self.update_idletasks()
    
    def load_profiles(self):
        """Load profile list"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get profiles
        profiles = self.controller.sp_profile_manager.list_profiles()
        
        if not profiles:
            self.update_status("プロファイルが登録されていません。新規追加してください。", "orange")
            return
        
        # Default sort (name A->Z)
        profiles.sort(key=lambda p: p.get('name', '').lower())
        
        # Add to tree
        for profile in profiles:
            name = profile.get('name', '')
            last_used = profile.get('last_used', '')
            if last_used:
                try:
                    dt = datetime.fromisoformat(last_used)
                    last_used = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            tenant_id = profile.get('tenant_id', '')
            client_id = profile.get('client_id', '')
            subscription_id = profile.get('subscription_id', '')
            file_name = profile.get('file_name', '')
            
            self.tree.insert('', tk.END, iid=file_name, 
                           values=(name, last_used, tenant_id, client_id, subscription_id))
        
        # Update status
        self.update_status(f"プロファイル {len(profiles)}件を読み込みました", "lightgreen")
        
        # Select first item if exists
        if profiles:
            first_item = self.tree.get_children()[0]
            self.tree.selection_set(first_item)
            self.tree.see(first_item)
    
    def sort_by_column(self, column: str):
        """Sort by column"""
        # Toggle sort order if same column clicked
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        # Get data
        data = [(self.tree.set(item, column), item) for item in self.tree.get_children('')]
        
        # Sort
        if column == 'last_used':
            # Date sort (empty strings last)
            data.sort(key=lambda x: (x[0] == '', x[0]), reverse=self.sort_reverse)
        else:
            # String sort (case-insensitive)
            data.sort(key=lambda x: x[0].lower(), reverse=self.sort_reverse)
        
        # Reorder
        for index, (_, item) in enumerate(data):
            self.tree.move(item, '', index)
    
    def on_select(self):
        """Select button handler"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "プロファイルを選択してください")
            return
        
        self.update_status("プロファイルを読み込み中...", "yellow")
        
        file_name = selected[0]
        profile = self.controller.sp_profile_manager.load_profile(file_name)
        if not profile:
            logger.error(f"プロファイルの読み込みに失敗しました (ログイン時): {file_name}")
            messagebox.showerror("エラー", f"プロファイルの読み込みに失敗しました\n\nファイル名: {file_name}")
            self.update_status("プロファイル読み込み失敗", "orange")
            return
        
        # Update last used timestamp
        self.controller.sp_profile_manager.update_last_used(file_name)
        
        # Save profile info
        self.controller.selected_sp_profile = profile
        
        self.update_status("ログイン中...", "yellow")
        
        # Execute login
        self.do_login(profile)
    
    def do_login(self, profile: Dict[str, Any]):
        """Login with service principal"""
        tenant_id = profile.get('tenant_id', '')
        client_id = profile.get('client_id', '')
        client_secret = profile.get('client_secret', '')
        subscription_id = profile.get('subscription_id', '')
        
        # Show progress dialog
        progress_window = tk.Toplevel(self.winfo_toplevel())
        progress_window.title("ログイン中")
        progress_window.geometry("400x150")
        progress_window.transient(self.winfo_toplevel())
        progress_window.grab_set()
        
        # 中央配置
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (progress_window.winfo_width() // 2)
        y = (progress_window.winfo_screenheight() // 2) - (progress_window.winfo_height() // 2)
        progress_window.geometry(f'+{x}+{y}')
        
        ttk.Label(progress_window, text=sp_selection_texts.authenticating_dialog_message, 
                 font=self.controller.default_font).pack(pady=30)
        
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(pady=10, padx=40, fill=tk.X)
        progress_bar.start(10)
        
        def login_thread():
            success, message = self.controller.azure_cli.login_with_service_principal(
                tenant_id, client_id, client_secret, subscription_id
            )
            
            progress_window.after(0, lambda: self.on_login_complete(success, message, progress_window))
        
        thread = threading.Thread(target=login_thread, daemon=True)
        thread.start()
    
    def on_login_complete(self, success: bool, message: str, progress_window):
        """Login completion handler"""
        progress_window.destroy()
        
        if success:
            self.update_status("ログイン成功、サブスクリプション情報を取得中...", "yellow")
            
            # Set subscription and tenant info
            profile = self.controller.selected_sp_profile
            subscription_id = profile.get('subscription_id', '')
            tenant_id = profile.get('tenant_id', '')
            
            # Get subscription name
            success_sub, sub_data, error = self.controller.azure_cli.run([
                'account', 'subscription', 'show',
                '--subscription-id', subscription_id,
                '--query', '{id:id, name:name}'
            ], capture_json=True)
            
            if success_sub and sub_data:
                self.controller.current_subscription = {
                    'id': sub_data.get('id', subscription_id),
                    'name': sub_data.get('name', subscription_id)
                }
            else:
                # If subscription info cannot be retrieved, use ID only
                self.controller.current_subscription = {
                    'id': subscription_id,
                    'name': subscription_id
                }
            
            # Set tenant info
            self.controller.current_tenant = tenant_id
            
            logger.info(f"サービスプリンシパルログイン成功: Subscription={subscription_id}, Tenant={tenant_id}")
            
            self.update_status("認証完了", "lightgreen")
            messagebox.showinfo("成功", "ログインに成功しました")
            
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
        else:
            self.update_status("ログイン失敗", "orange")
            messagebox.showerror("エラー", f"ログインに失敗しました\n\n{message}")
    
    def on_add(self):
        """Add button handler"""
        self.update_status("新規プロファイルを作成中...", "yellow")
        self.controller.show_frame("ProfileEditorScreen")
        editor_class = self.controller.frame_classes["ProfileEditorScreen"]
        editor = self.controller.frames[editor_class]
        editor.set_mode("add")
    
    def on_edit(self):
        """Edit button handler"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "編集するプロファイルを選択してください")
            return
        
        self.update_status("プロファイルを編集中...", "yellow")
        
        file_name = selected[0]
        profile = self.controller.sp_profile_manager.load_profile(file_name)
        if not profile:
            logger.error(f"プロファイルの読み込みに失敗しました (編集時): {file_name}")
            messagebox.showerror("エラー", f"プロファイルの読み込みに失敗しました\n\nファイル名: {file_name}")
            self.update_status("プロファイル読み込み失敗", "orange")
            return
        
        self.controller.show_frame("ProfileEditorScreen")
        editor_class = self.controller.frame_classes["ProfileEditorScreen"]
        editor = self.controller.frames[editor_class]
        editor.set_mode("edit", profile)
    
    def on_delete(self):
        """Delete button handler"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "削除するプロファイルを選択してください")
            return
        
        file_name = selected[0]
        profile = self.controller.sp_profile_manager.load_profile(file_name)
        if not profile:
            logger.error(f"プロファイルの読み込みに失敗しました (削除時): {file_name}")
            messagebox.showerror("エラー", f"プロファイルの読み込みに失敗しました\n\nファイル名: {file_name}")
            return
        
        result = messagebox.askyesno(
            "確認",
            f"プロファイル「{profile.get('name', '')}」を削除しますか？\n\nこの操作は取り消せません。"
        )
        
        if result:
            self.update_status("プロファイルを削除中...", "yellow")
            if self.controller.sp_profile_manager.delete_profile(file_name):
                messagebox.showinfo("成功", "プロファイルを削除しました")
                self.load_profiles()
            else:
                logger.error(f"プロファイルの削除に失敗しました: {file_name}")
                messagebox.showerror("エラー", f"プロファイルの削除に失敗しました\n\nファイル名: {file_name}")
                self.update_status("プロファイル削除失敗", "orange")
    
    def on_back(self):
        """Back button handler"""
        self.update_status("認証方法選択画面に戻ります...", "yellow")
        self.controller.show_frame("AuthenticationMethodScreen")
