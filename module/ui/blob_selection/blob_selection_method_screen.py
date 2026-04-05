"""Blob選択方法選択画面"""

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from ...ui_text.blob_texts import blob_selection_method_texts

if TYPE_CHECKING:
    from azure_blob_rehydrator import AzureBlobRehydratorApp


class BlobSelectionMethodScreen(tk.Frame):
    """Blob指定方法選択画面"""
    
    def __init__(self, parent, controller: 'AzureBlobRehydratorApp'):
        super().__init__(parent)
        self.controller = controller
        
        # タイトル
        title_label = ttk.Label(self, text=blob_selection_method_texts.title, 
                               style='Title.TLabel')
        title_label.pack(pady=30)
        
        # 説明
        desc = ttk.Label(self, 
                        text=blob_selection_method_texts.subtitle,
                        font=controller.heading_font)
        desc.pack(pady=10)
        
        # ボタンフレーム
        button_frame = tk.Frame(self)
        button_frame.pack(pady=40, padx=40)
        
        # 方法1: URL直接入力
        url_frame = tk.Frame(button_frame, relief='solid', borderwidth=2, padx=30, pady=25)
        url_frame.pack(pady=15, fill='x')
        
        ttk.Label(url_frame, text=blob_selection_method_texts.method1_title,
                 font=controller.heading_font).pack()
        ttk.Label(url_frame, 
                 text=blob_selection_method_texts.method1_desc,
                 font=(controller.default_font[0], 9),
                 foreground='gray').pack(pady=5)
        ttk.Button(url_frame, text=blob_selection_method_texts.method1_button,
                  command=self.select_url_input,
                  width=25).pack(pady=10)
        
        # 方法2: テンプレート検索
        template_frame = tk.Frame(button_frame, relief='solid', borderwidth=2, padx=30, pady=25)
        template_frame.pack(pady=15, fill='x')
        
        ttk.Label(template_frame, text=blob_selection_method_texts.method2_title,
                 font=controller.heading_font).pack()
        ttk.Label(template_frame,
                 text=blob_selection_method_texts.method2_desc,
                 font=(controller.default_font[0], 9),
                 foreground='gray').pack(pady=5)
        ttk.Button(template_frame, text=blob_selection_method_texts.method2_button,
                  command=self.select_template_search,
                  width=25).pack(pady=10)
        
        # 戻るボタン（下部）
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)
        
        back_button = ttk.Button(button_frame, text=blob_selection_method_texts.back_button, 
                                command=self.go_back, width=15)
        back_button.pack()
    
    def go_back(self):
        """前の画面（認証後の画面）に戻る"""
        # 認証方法に応じて適切な画面に戻る
        if self.controller.auth_method == 'service_principal':
            self.controller.show_frame('ServicePrincipalSelectionScreen')
        elif self.controller.auth_method == 'existing':
            self.controller.show_frame('ExistingLoginScreen')
        else:
            # ユーザーアカウント認証の場合はLoginScreenに戻る
            self.controller.show_frame('LoginScreen')
    
    def select_url_input(self):
        """URL直接入力を選択"""
        # Import moved to avoid circular dependency
        from azure_blob_rehydrator import BlobURLInputScreen
        self.controller.show_frame(BlobURLInputScreen)
    
    def select_template_search(self):
        """テンプレート検索を選択"""
        self.controller.selected_templates = []
        self.controller.current_template_index = 0
        self.controller.template_expansion_settings = {}
        self.controller.matched_blobs = []
        self.controller.show_frame('TemplateSelectionScreen')
