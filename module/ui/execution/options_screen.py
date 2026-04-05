"""オプション選択画面"""

import logging
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import TYPE_CHECKING

from ...ui_text.execution_texts import options_texts

if TYPE_CHECKING:
    from azure_blob_rehydrator import AzureBlobRehydratorApp

logger = logging.getLogger(__name__)


class OptionsScreen(tk.Frame):
    """オプション選択画面"""
    
    def __init__(self, parent, controller: 'AzureBlobRehydratorApp'):
        super().__init__(parent)
        self.controller = controller
        
        # タイトル
        title = ttk.Label(self, text=options_texts.title, style='Title.TLabel')
        title.pack(pady=10)
        
        # オプション設定フレーム
        options_frame = ttk.LabelFrame(self, text=options_texts.download_settings_title, padding=10)
        options_frame.pack(pady=10, padx=40, fill="both")
        
        # ダウンロード先
        ttk.Label(options_frame, text=options_texts.download_dir_label).grid(
            row=0, column=0, sticky="w", padx=10, pady=5)
        
        download_frame = ttk.Frame(options_frame)
        download_frame.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        self.download_dir_var = tk.StringVar(value=controller.config.get('download_directory'))
        download_entry = ttk.Entry(download_frame, textvariable=self.download_dir_var, width=50)
        download_entry.pack(side="left", fill="x", expand=True)
        
        browse_button = ttk.Button(download_frame, text=options_texts.browse_button, command=self.browse_directory)
        browse_button.pack(side="right", padx=5)
        
        # パス構造オプション
        ttk.Label(options_frame, text=options_texts.path_structure_label).grid(
            row=1, column=0, sticky="w", padx=10, pady=5)
        
        path_frame = ttk.Frame(options_frame)
        path_frame.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        self.path_structure_var = tk.StringVar(value="preserve")
        ttk.Radiobutton(path_frame, text=options_texts.path_preserve, 
                       variable=self.path_structure_var, value="preserve").pack(anchor="w")
        ttk.Radiobutton(path_frame, text=options_texts.path_flatten, 
                       variable=self.path_structure_var, value="flatten").pack(anchor="w")
        self.single_file_radio = ttk.Radiobutton(path_frame, text=options_texts.path_single, 
                                                variable=self.path_structure_var, value="single")
        self.single_file_radio.pack(anchor="w")
        
        options_frame.grid_columnconfigure(1, weight=1)
        
        # リハイドレート設定フレーム
        rehydrate_frame = ttk.LabelFrame(self, text=options_texts.rehydrate_settings_title, padding=10)
        rehydrate_frame.pack(pady=10, padx=40, fill="both")
        
        # ターゲット層
        tk.Label(rehydrate_frame, text=options_texts.target_tier_label, font=controller.default_font).grid(
            row=0, column=0, sticky="w", padx=10, pady=5)
        
        self.target_tier_var = tk.StringVar(value=controller.config.get('target_tier'))
        tier_combo = ttk.Combobox(rehydrate_frame, textvariable=self.target_tier_var,
                                 values=['Hot', 'Cool'], state='readonly', width=15)
        tier_combo.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        # 優先度
        tk.Label(rehydrate_frame, text=options_texts.priority_label, font=controller.default_font).grid(
            row=1, column=0, sticky="w", padx=10, pady=5)
        
        self.priority_var = tk.StringVar(value=controller.config.get('priority'))
        priority_combo = ttk.Combobox(rehydrate_frame, textvariable=self.priority_var,
                                     values=['Standard', 'High'], state='readonly', width=15)
        priority_combo.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        rehydrate_frame.grid_columnconfigure(1, weight=1)
        
        # ボタンフレーム
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)
        
        # 戻るボタン
        back_button = ttk.Button(button_frame, text=options_texts.back_button, command=controller.go_back, width=15)
        back_button.pack(side="left", padx=5)
        
        # 開始ボタン
        self.start_button = ttk.Button(button_frame, text=options_texts.start_button_download,
                                 command=self.start_download, width=20)
        self.start_button.pack(side="left", padx=5)
    
    def on_show(self):
        """画面表示時の処理"""
        # Blob URLが1つの場合のみ単一ファイルオプションを有効化
        if len(self.controller.validated_blobs) == 1:
            self.single_file_radio.state(['!disabled'])
        else:
            self.single_file_radio.state(['disabled'])
            if self.path_structure_var.get() == "single":
                self.path_structure_var.set("preserve")
    
    def browse_directory(self):
        """ディレクトリ選択"""
        directory = filedialog.askdirectory(initialdir=self.download_dir_var.get())
        if directory:
            self.download_dir_var.set(directory)
    
    def start_download(self):
        """ダウンロード開始"""
        # ダウンロード先を検証
        download_dir = self.download_dir_var.get().strip()
        
        if not download_dir:
            logger.warning("ダウンロード先が未指定です")
            messagebox.showwarning("警告", "ダウンロード先を指定してください")
            return
        
        if not os.path.exists(download_dir):
            logger.warning(f"ダウンロード先が存在しません: {download_dir}")
            messagebox.showwarning("警告", f"ダウンロード先が存在しません:\n{download_dir}")
            return
        
        if not os.access(download_dir, os.W_OK):
            logger.error(f"ダウンロード先に書込権限がありません: {download_dir}")
            messagebox.showerror("エラー", f"ダウンロード先に書込権限がありません:\n{download_dir}")
            return
        
        # セッションID生成
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.controller.session_id = session_id
        
        # オプション設定保存
        options = {
            'download_directory': download_dir,
            'path_structure': self.path_structure_var.get(),
            'target_tier': self.target_tier_var.get(),
            'priority': self.priority_var.get()
        }
        
        # サブスクリプション情報チェック
        if not self.controller.current_subscription or not self.controller.current_tenant:
            logger.error(
                f"認証情報が不正です - "
                f"current_subscription={self.controller.current_subscription}, "
                f"current_tenant={self.controller.current_tenant}"
            )
            
            error_details = []
            if not self.controller.current_subscription:
                error_details.append("・サブスクリプション情報が設定されていません")
            if not self.controller.current_tenant:
                error_details.append("・テナント情報が設定されていません")
            
            # タイトルを不足している情報に応じて変更
            if not self.controller.current_subscription and not self.controller.current_tenant:
                error_title = "認証情報不足"
            elif not self.controller.current_subscription:
                error_title = "サブスクリプション情報不足"
            else:
                error_title = "テナント情報不足"
            
            error_msg = "以下の認証情報が設定されていません:\n\n" + "\n".join(error_details)
            error_msg += "\n\n認証画面に戻り、正しくサブスクリプションを選択してください。"
            
            messagebox.showerror(error_title, error_msg)
            return
        
        # ステートファイル作成
        self.controller.current_state_file = self.controller.state_manager.create_state_file(
            session_id=session_id,
            subscription_id=self.controller.current_subscription['id'],
            subscription_name=self.controller.current_subscription['name'],
            tenant_name=self.controller.current_tenant,
            options=options,
            blobs=self.controller.validated_blobs
        )
        
        # セッション情報をメモリに保存（以降はファイル読み込み不要）
        self.controller.session_options = options
        self.controller.session_subscription_id = self.controller.current_subscription['id']
        self.controller.session_subscription_name = self.controller.current_subscription['name']
        self.controller.session_tenant_name = self.controller.current_tenant
        
        logger.info(f"セッション開始: {session_id}")
        
        # 進捗画面へ遷移
        # Import moved to avoid circular dependency
        from azure_blob_rehydrator import ProgressScreen
        self.controller.show_frame(ProgressScreen)
