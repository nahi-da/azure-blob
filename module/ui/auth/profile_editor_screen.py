"""Profile editor screen for service principal credentials"""

import re
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional, Tuple

from ...core.logging_manager import logger
from ...ui_text.auth_texts import profile_editor_texts


class ProfileEditorScreen(tk.Frame):
    """Profile editor screen"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.mode = "add"  # "add" or "edit"
        self.original_profile = None
        
        # UUID validation pattern
        self.uuid_pattern = re.compile(
            r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        )
        
        # Title
        self.title_label = ttk.Label(self, text=profile_editor_texts.title_new, style='Title.TLabel')
        self.title_label.pack(pady=20)
        
        # Form frame
        form_frame = ttk.Frame(self)
        form_frame.pack(pady=10, padx=40, fill=tk.BOTH, expand=True)
        
        # Profile name
        ttk.Label(form_frame, text=profile_editor_texts.profile_name_label).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(form_frame, width=50)
        self.name_entry.grid(row=0, column=1, pady=5, padx=10, sticky=tk.EW)
        
        # File name
        ttk.Label(form_frame, text=profile_editor_texts.file_name_label).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.filename_entry = ttk.Entry(form_frame, width=50)
        self.filename_entry.grid(row=1, column=1, pady=5, padx=10, sticky=tk.EW)
        ttk.Label(form_frame, text=profile_editor_texts.file_name_note, foreground="gray").grid(row=1, column=2, sticky=tk.W)
        
        # Tenant ID
        ttk.Label(form_frame, text=profile_editor_texts.tenant_id_label).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.tenant_entry = ttk.Entry(form_frame, width=50)
        self.tenant_entry.grid(row=2, column=1, pady=5, padx=10, sticky=tk.EW)
        
        # Client ID
        ttk.Label(form_frame, text=profile_editor_texts.client_id_label).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.client_entry = ttk.Entry(form_frame, width=50)
        self.client_entry.grid(row=3, column=1, pady=5, padx=10, sticky=tk.EW)
        
        # Client secret
        ttk.Label(form_frame, text=profile_editor_texts.client_secret_label).grid(row=4, column=0, sticky=tk.W, pady=5)
        secret_frame = ttk.Frame(form_frame)
        secret_frame.grid(row=4, column=1, pady=5, padx=10, sticky=tk.EW)
        
        self.secret_entry = ttk.Entry(secret_frame, width=42, show="*")
        self.secret_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.show_secret_var = tk.BooleanVar(value=False)
        self.show_secret_btn = ttk.Checkbutton(
            secret_frame,
            text=profile_editor_texts.show_secret,
            variable=self.show_secret_var,
            command=self.toggle_secret_visibility
        )
        self.show_secret_btn.pack(side=tk.LEFT, padx=5)
        
        # Subscription ID
        ttk.Label(form_frame, text=profile_editor_texts.subscription_id_label).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.subscription_entry = ttk.Entry(form_frame, width=50)
        self.subscription_entry.grid(row=5, column=1, pady=5, padx=10, sticky=tk.EW)
        
        # Description
        ttk.Label(form_frame, text=profile_editor_texts.description_optional_label).grid(row=6, column=0, sticky=tk.W, pady=5)
        self.description_entry = ttk.Entry(form_frame, width=50)
        self.description_entry.grid(row=6, column=1, pady=5, padx=10, sticky=tk.EW)
        
        # Make column 1 expandable
        form_frame.columnconfigure(1, weight=1)
        
        # Button frame
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)
        
        self.save_button = ttk.Button(button_frame, text=profile_editor_texts.save_button, command=self.on_save, width=15)
        self.save_button.grid(row=0, column=0, padx=5)
        
        ttk.Button(button_frame, text=profile_editor_texts.cancel_button, command=self.on_cancel, width=15).grid(row=0, column=1, padx=5)
    
    def on_show(self):
        """Called when screen is shown"""
        # This method is called automatically by show_frame
        # Actual initialization is done in set_mode() which is called after show_frame
        pass
    
    def toggle_secret_visibility(self):
        """Toggle secret visibility"""
        if self.show_secret_var.get():
            self.secret_entry.config(show="")
        else:
            self.secret_entry.config(show="*")
    
    def set_mode(self, mode: str, profile: Optional[Dict[str, Any]] = None):
        """Set mode"""
        self.mode = mode
        self.original_profile = profile
        
        if mode == "add":
            self.title_label.config(text=profile_editor_texts.title_add)
            self.save_button.config(text=profile_editor_texts.save_button)
            self.clear_fields()
            self.filename_entry.config(state=tk.NORMAL)
        else:
            self.title_label.config(text=profile_editor_texts.title_edit)
            self.save_button.config(text=profile_editor_texts.update_button)
            if profile:
                self.load_profile(profile)
                self.filename_entry.config(state=tk.DISABLED)
    
    def clear_fields(self):
        """Clear all fields"""
        self.name_entry.delete(0, tk.END)
        self.filename_entry.delete(0, tk.END)
        self.tenant_entry.delete(0, tk.END)
        self.client_entry.delete(0, tk.END)
        self.secret_entry.delete(0, tk.END)
        self.subscription_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)
        self.show_secret_var.set(False)
        self.toggle_secret_visibility()
    
    def load_profile(self, profile: Dict[str, Any]):
        """Load profile data"""
        self.clear_fields()
        self.name_entry.insert(0, profile.get('name', ''))
        self.filename_entry.insert(0, profile.get('file_name', ''))
        self.tenant_entry.insert(0, profile.get('tenant_id', ''))
        self.client_entry.insert(0, profile.get('client_id', ''))
        self.secret_entry.insert(0, profile.get('client_secret', ''))
        self.subscription_entry.insert(0, profile.get('subscription_id', ''))
        self.description_entry.insert(0, profile.get('description', ''))
    
    def validate_fields(self) -> Tuple[bool, str]:
        """Validate fields"""
        name = self.name_entry.get().strip()
        if not name:
            return False, "プロファイル名を入力してください"
        
        file_name = self.filename_entry.get().strip()
        if not file_name:
            return False, "ファイル名を入力してください"
        
        # Check file name duplication (case-insensitive)
        exclude_name = self.original_profile.get('file_name') if self.original_profile else None
        if self.controller.sp_profile_manager.file_exists(file_name, exclude_name):
            return False, "このファイル名は既に使用されています（大文字小文字は区別されません）"
        
        tenant_id = self.tenant_entry.get().strip()
        if not tenant_id:
            return False, "テナントIDを入力してください"
        if not self.uuid_pattern.match(tenant_id):
            return False, "テナントIDの形式が不正です（UUID形式で入力してください）"
        
        client_id = self.client_entry.get().strip()
        if not client_id:
            return False, "クライアントIDを入力してください"
        if not self.uuid_pattern.match(client_id):
            return False, "クライアントIDの形式が不正です（UUID形式で入力してください）"
        
        client_secret = self.secret_entry.get().strip()
        if not client_secret:
            return False, "クライアントシークレットを入力してください"
        
        subscription_id = self.subscription_entry.get().strip()
        if not subscription_id:
            return False, "サブスクリプションIDを入力してください"
        if not self.uuid_pattern.match(subscription_id):
            return False, "サブスクリプションIDの形式が不正です（UUID形式で入力してください）"
        
        return True, ""
    
    def on_save(self):
        """Save button handler"""
        # Validate
        valid, error_msg = self.validate_fields()
        if not valid:
            logger.warning(f"プロファイル検証エラー: {error_msg}")
            messagebox.showerror("エラー", error_msg)
            return
        
        # Create profile data
        profile_data = {
            'name': self.name_entry.get().strip(),
            'file_name': self.filename_entry.get().strip(),
            'tenant_id': self.tenant_entry.get().strip(),
            'client_id': self.client_entry.get().strip(),
            'client_secret': self.secret_entry.get().strip(),
            'subscription_id': self.subscription_entry.get().strip(),
            'description': self.description_entry.get().strip(),
        }
        
        # Preserve existing timestamps
        if self.mode == "edit" and self.original_profile:
            profile_data['created_at'] = self.original_profile.get('created_at', '')
            profile_data['last_used'] = self.original_profile.get('last_used', '')
        
        # Save
        if self.controller.sp_profile_manager.save_profile(profile_data):
            messagebox.showinfo("成功", f"プロファイルを{'保存' if self.mode == 'add' else '更新'}しました")
            self.controller.show_frame("ServicePrincipalSelectionScreen")
            # Reload list
            selection_class = self.controller.frame_classes["ServicePrincipalSelectionScreen"]
            selection_screen = self.controller.frames[selection_class]
            selection_screen.load_profiles()
        else:
            logger.error("プロファイルの保存に失敗しました")
            messagebox.showerror("エラー", "プロファイルの保存に失敗しました")
    
    def on_cancel(self):
        """Cancel button handler"""
        self.controller.show_frame("ServicePrincipalSelectionScreen")
