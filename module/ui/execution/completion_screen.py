"""完了画面"""

import logging
import os
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from ...ui_text.execution_texts import completion_texts

if TYPE_CHECKING:
    from azure_blob_rehydrator import AzureBlobRehydratorApp

logger = logging.getLogger(__name__)


class CompletionScreen(tk.Frame):
    """完了画面"""
    
    def __init__(self, parent, controller: 'AzureBlobRehydratorApp'):
        super().__init__(parent)
        self.controller = controller
        
        # タイトル
        title = ttk.Label(self, text=completion_texts.title, style='Title.TLabel')
        title.pack(pady=20)
        
        # 結果サマリーフレーム
        summary_frame = tk.Frame(self, relief=tk.RIDGE, borderwidth=2, bg='white')
        summary_frame.pack(pady=10, padx=50, fill='x')
        
        # サマリー情報
        completed = sum(1 for b in controller.validated_blobs if b.get('status') == 'completed')
        errors = sum(1 for b in controller.validated_blobs if b.get('status') == 'error')
        total = len(controller.validated_blobs)
        
        summary_title = ttk.Label(summary_frame, text=completion_texts.summary_title, 
                                 font=(controller.default_font[0], 14, 'bold'),
                                 background='white')
        summary_title.pack(pady=10)
        
        result_text = f"""合計: {total}件  |  成功: {completed}件  |  エラー: {errors}件"""
        
        result_label = ttk.Label(summary_frame, text=result_text, 
                                font=(controller.default_font[0], 11),
                                background='white', justify='center')
        result_label.pack(pady=10, padx=20)
        
        # 保存先情報
        download_dir = controller.validated_blobs[0].get('options', {}).get('download_directory', '') if controller.validated_blobs else controller.config.get('download_directory')
        if download_dir and controller.session_id:
            try:
                session_folder = controller.session_id.split('_')[0]
                full_path = os.path.join(download_dir, session_folder)
                
                path_label = ttk.Label(summary_frame, text=f"ダウンロード先: {full_path}", 
                                      font=(controller.default_font[0], 9),
                                      background='white', foreground='blue')
                path_label.pack(pady=(0,10), padx=20)
            except Exception as e:
                logger.exception(f"ダウンロード先パス表示エラー: {e}")
        
        # 詳細リスト（Treeview）
        detail_frame = tk.Frame(self)
        detail_frame.pack(pady=10, padx=50, fill='both', expand=True)
        
        detail_label = ttk.Label(detail_frame, text=completion_texts.detail_title, font=(controller.default_font[0], 11, 'bold'))
        detail_label.pack(anchor='w', pady=(0,5))
        
        # Treeview + Scrollbar
        tree_container = tk.Frame(detail_frame)
        tree_container.pack(fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_container, orient="vertical")
        
        self.tree = ttk.Treeview(tree_container, 
                                 columns=('status', 'message'),
                                 show='tree headings',
                                 yscrollcommand=scrollbar.set,
                                 height=12)
        
        scrollbar.config(command=self.tree.yview)
        
        # カラム設定
        self.tree.heading('#0', text='Blob名')
        self.tree.heading('status', text='ステータス')
        self.tree.heading('message', text='メッセージ')
        
        self.tree.column('#0', width=300, minwidth=200, stretch=False)
        self.tree.column('status', width=80, anchor='center', stretch=False)
        self.tree.column('message', width=500, minwidth=150, stretch=False)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # データを追加
        self._populate_tree()
        
        # ボタンフレーム
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        
        # ダウンロードフォルダを開くボタン
        open_button = ttk.Button(button_frame, text=completion_texts.open_folder_button, 
                                command=self.open_download_folder, width=25)
        open_button.pack(side="left", padx=10)
        
        # 完了ボタン
        finish_button = ttk.Button(button_frame, text=completion_texts.finish_button,
                                  command=self.finish, width=15)
        finish_button.pack(side="right", padx=10)
    
    def _populate_tree(self):
        """Treeviewにデータを追加"""
        # ステータスごとにグループ化
        status_groups = {
            'completed': {'label': '完了', 'blobs': []},
            'error': {'label': 'エラー', 'blobs': []}
        }
        
        for blob in self.controller.validated_blobs:
            status = blob.get('status', 'pending')
            if status in status_groups:
                status_groups[status]['blobs'].append(blob)
        
        # Treeviewに追加
        for status_key, group in status_groups.items():
            if group['blobs']:
                # 親ノード（ステータスグループ）
                count = len(group['blobs'])
                parent_id = self.tree.insert('', 'end', text=f"{group['label']} ({count}件)", 
                                            values=('', ''), open=True)
                
                # 子ノード（各Blob）
                for blob in group['blobs']:
                    blob_name = blob.get('blob_name', 'Unknown')
                    message = blob.get('progress_message', '')
                    
                    # ステータス表示（日本語）
                    status_text = '完了' if status_key == 'completed' else 'エラー'
                    
                    self.tree.insert(parent_id, 'end', text=f"  {blob_name}", 
                                   values=(status_text, message))
    
    def open_download_folder(self):
        """ダウンロードフォルダを開く"""
        try:
            download_dir = self.controller.config.get('download_directory')
            if not download_dir:
                logger.warning("ダウンロードフォルダが設定されていません")
                messagebox.showwarning("警告", "ダウンロードフォルダが見つかりません")
                return
            
            if not self.controller.session_id:
                logger.warning("セッションIDが設定されていません")
                messagebox.showwarning("警告", "セッションIDが見つかりません")
                return
            
            session_folder = self.controller.session_id.split('_')[0]
            full_path = os.path.join(download_dir, session_folder)
            
            if not os.path.exists(full_path):
                logger.warning(f"ダウンロードフォルダが存在しません: {full_path}")
                messagebox.showwarning("警告", f"フォルダが存在しません:\n{full_path}")
                return
            
            subprocess.Popen(['explorer', os.path.abspath(full_path)])
        except Exception as e:
            logger.exception(f"フォルダオープンエラー: {e}")
            messagebox.showerror("エラー", f"フォルダを開けませんでした:\n{e}")
    
    def finish(self):
        """完了処理"""
        try:
            # ステートファイルをアーカイブ
            if self.controller.current_state_file:
                self.controller.state_manager.archive_state_file(self.controller.current_state_file)
            
            logger.info("処理完了 - アプリケーションを終了します")
            
            # アプリケーションを終了
            self.controller.quit()
        except Exception as e:
            logger.exception(f"完了処理エラー: {e}")
            messagebox.showerror("エラー", f"完了処理中にエラーが発生しました:\n{e}")
            # エラーが発生してもアプリケーションを終了
            try:
                self.controller.quit()
            except Exception as e2:
                logger.exception(f"アプリケーション終了エラー: {e2}")
