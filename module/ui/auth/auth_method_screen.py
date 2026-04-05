"""Authentication method selection screen"""

import tkinter as tk
from tkinter import ttk

from ...ui_text.auth_texts import auth_method_texts


class AuthenticationMethodScreen(tk.Frame):
    """Authentication method selection screen"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Title
        title_label = ttk.Label(self, text=auth_method_texts.title, style='Title.TLabel')
        title_label.pack(pady=5)
        
        subtitle = ttk.Label(self, text=auth_method_texts.subtitle, 
                           font=controller.heading_font)
        subtitle.pack(pady=5)
        
        # Authentication method selection frame
        method_frame = ttk.LabelFrame(self, text=auth_method_texts.frame_title, padding=20)
        method_frame.pack(pady=10, padx=40, fill="x")
        
        self.auth_var = tk.StringVar(value="existing")
        
        # Existing login (Azure CLI)
        existing_radio = ttk.Radiobutton(
            method_frame,
            text=auth_method_texts.existing_radio,
            variable=self.auth_var,
            value="existing"
        )
        existing_radio.pack(anchor=tk.W, pady=10)
        
        existing_desc = ttk.Label(
            method_frame,
            text=auth_method_texts.existing_desc,
            foreground="gray"
        )
        existing_desc.pack(anchor=tk.W, padx=30, pady=(0, 20))
        
        # User ID authentication
        user_radio = ttk.Radiobutton(
            method_frame,
            text=auth_method_texts.user_radio,
            variable=self.auth_var,
            value="user"
        )
        user_radio.pack(anchor=tk.W, pady=10)
        
        user_desc = ttk.Label(
            method_frame,
            text=auth_method_texts.user_desc,
            foreground="gray"
        )
        user_desc.pack(anchor=tk.W, padx=30, pady=(0, 20))
        
        # Service principal authentication
        sp_radio = ttk.Radiobutton(
            method_frame,
            text=auth_method_texts.sp_radio,
            variable=self.auth_var,
            value="service_principal"
        )
        sp_radio.pack(anchor=tk.W, pady=10)
        
        sp_desc = ttk.Label(
            method_frame,
            text=auth_method_texts.sp_desc,
            foreground="gray"
        )
        sp_desc.pack(anchor=tk.W, padx=30)
        
        # Button frame
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=(20, 0))
        
        # 次へボタン
        next_button = ttk.Button(
            button_frame,
            text=auth_method_texts.next_button,
            command=self.on_next,
            style='Accent.TButton',
            width=20
        )
        next_button.pack()
    
    def on_next(self):
        """Next button handler"""
        auth_method = self.auth_var.get()
        self.controller.auth_method = auth_method
        
        if auth_method == "existing":
            self.controller.show_frame("ExistingLoginScreen")
        elif auth_method == "user":
            self.controller.show_frame("LoginScreen")
        else:
            self.controller.show_frame("ServicePrincipalSelectionScreen")
