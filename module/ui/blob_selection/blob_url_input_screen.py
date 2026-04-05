"""Blob URL入力画面"""

import logging
import re
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Dict, List, Tuple

from ...core import AccountKeyRetrievalError, InvalidFormatError, parse_azure_cli_error
from ...ui_text.blob_texts import blob_url_input_texts

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from azure_blob_rehydrator import AzureBlobRehydratorApp


class BlobURLInputScreen(tk.Frame):
    """Blob URL入力画面"""
    
    def __init__(self, parent, controller: 'AzureBlobRehydratorApp'):
        super().__init__(parent)
        self.controller = controller
        
        # タイトル
        title = ttk.Label(self, text=blob_url_input_texts.title, style='Title.TLabel')
        title.pack(pady=10)
        
        # 説明
        desc = ttk.Label(self, text=blob_url_input_texts.subtitle)
        desc.pack(pady=5)
        
        # 追加ボタン
        add_button = ttk.Button(self, text=blob_url_input_texts.add_url_button, command=self.add_url_entry)
        add_button.pack(pady=10)
        
        # スクロール可能なコンテナ
        scroll_frame = tk.Frame(self)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Canvas + Scrollbar
        self.canvas = tk.Canvas(scroll_frame, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Canvasの幅変更時にscrollable_frameの幅を追従させる
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_frame, width=e.width))
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # マウスホイールバインド
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # 入力欄リスト
        self.url_entries = []
        
        # 初期入力欄追加
        self.add_url_entry()
        
        # ボタンフレーム
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)
        
        # 戻るボタン
        back_button = ttk.Button(button_frame, text=blob_url_input_texts.back_button, command=controller.go_back, width=15)
        back_button.pack(side="left", padx=5)
        
        # 次へボタン
        next_button = ttk.Button(button_frame, text=blob_url_input_texts.next_button,
                                command=self.validate_and_next, width=15)
        next_button.pack(side="left", padx=5)
    
    def _on_mousewheel(self, event):
        """マウスホイールイベント"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def add_url_entry(self):
        """URL入力欄を追加"""
        entry_frame = tk.Frame(self.scrollable_frame, relief=tk.RIDGE, borderwidth=1)
        entry_frame.pack(fill="x", padx=5, pady=5)
        
        # Entry（幅を指定せずfillで伸縮させる）
        entry = ttk.Entry(entry_frame, font=self.controller.default_font)
        entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        # 右クリックメニューを追加
        self._add_context_menu(entry)
        
        # 削除ボタン
        delete_button = tk.Button(entry_frame, text="×", command=lambda: self.remove_url_entry(entry_frame),
                                 fg="red", font=("Arial", 10, "bold"))
        delete_button.pack(side="right", padx=5, pady=5)
        
        # 検証結果ラベル
        result_label = tk.Label(entry_frame, text="", fg="red", font=("Arial", 9))
        result_label.pack(side="bottom", anchor="w", padx=5)
        
        self.url_entries.append({
            'frame': entry_frame,
            'entry': entry,
            'result_label': result_label
        })
    
    def _add_context_menu(self, entry: tk.Entry):
        """右クリックメニュー追加"""
        menu = tk.Menu(entry, tearoff=0)
        menu.add_command(label="切り取り (Ctrl+X)", command=lambda: self._cut(entry))
        menu.add_command(label="コピー (Ctrl+C)", command=lambda: self._copy(entry))
        menu.add_command(label="貼り付け (Ctrl+V)", command=lambda: self._paste(entry))
        menu.add_separator()
        menu.add_command(label="全て選択 (Ctrl+A)", command=lambda: self._select_all(entry))
        
        def show_menu(event):
            menu.post(event.x_root, event.y_root)
        
        entry.bind("<Button-3>", show_menu)
        
        # キーボードショートカット（Ctrl+Vはデフォルト動作を使用）
        entry.bind("<Control-x>", lambda e: self._cut(entry))
        entry.bind("<Control-c>", lambda e: self._copy(entry))
        entry.bind("<Control-a>", lambda e: self._select_all(entry))
    
    def _cut(self, entry: tk.Entry):
        """切り取り"""
        try:
            if entry.selection_present():
                self.clipboard_clear()
                self.clipboard_append(entry.selection_get())
                entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass
    
    def _copy(self, entry: tk.Entry):
        """コピー"""
        try:
            if entry.selection_present():
                self.clipboard_clear()
                self.clipboard_append(entry.selection_get())
        except tk.TclError:
            pass
    
    def _paste(self, entry: tk.Entry):
        """貼り付け"""
        try:
            text = self.clipboard_get()
            if entry.selection_present():
                entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
            entry.insert(tk.INSERT, text)
            return 'break'  # デフォルト動作をキャンセル
        except tk.TclError:
            pass
    
    def _select_all(self, entry: tk.Entry):
        """全て選択"""
        entry.select_range(0, tk.END)
        entry.icursor(tk.END)
    
    def remove_url_entry(self, frame):
        """URL入力欄を削除"""
        # リストから削除
        self.url_entries = [e for e in self.url_entries if e['frame'] != frame]
        frame.destroy()
        
        # 最低1つは残す
        if not self.url_entries:
            self.add_url_entry()
    
    def validate_and_next(self):
        """検証して次へ"""
        # 入力されたURLを取得
        urls = []
        for entry_data in self.url_entries:
            url = entry_data['entry'].get().strip()
            if url:
                urls.append((url, entry_data))
        
        if not urls:
            messagebox.showwarning("警告", "少なくとも1つのBlob URLを入力してください")
            return
        
        # 進捗ダイアログ表示
        progress_dialog = tk.Toplevel(self)
        progress_dialog.title("検証中")
        progress_dialog.geometry("400x150")
        progress_dialog.transient(self.winfo_toplevel())
        progress_dialog.grab_set()
        
        # 中央配置
        progress_dialog.update_idletasks()
        x = (progress_dialog.winfo_screenwidth() // 2) - (progress_dialog.winfo_width() // 2)
        y = (progress_dialog.winfo_screenheight() // 2) - (progress_dialog.winfo_height() // 2)
        progress_dialog.geometry(f'+{x}+{y}')
        
        tk.Label(progress_dialog, text=blob_url_input_texts.validating_dialog_message, font=("Arial", 12)).pack(pady=20)
        progress_bar = ttk.Progressbar(progress_dialog, mode='indeterminate')
        progress_bar.pack(pady=10, padx=20, fill='x')
        progress_bar.start(10)
        
        status_label = tk.Label(progress_dialog, text="", font=("Arial", 10))
        status_label.pack(pady=10)
        
        # 別スレッドで検証
        thread = threading.Thread(target=self._validate_urls, args=(urls, progress_dialog))
        thread.daemon = True
        thread.start()
    
    def _validate_urls(self, urls: List[Tuple[str, Dict]], progress_dialog):
        """URL検証（別スレッド）"""
        validated = []
        error_count = 0
        
        def validate_single_url(url, entry_data):
            """単一URL検証"""
            nonlocal error_count
            
            try:
                # 正規表現チェック
                pattern = r'^https://([a-z0-9]+)\.blob\.core\.windows\.net/([^/]+)/(.+)$'
                match = re.match(pattern, url, re.IGNORECASE)
                
                if not match:
                    raise InvalidFormatError("不正なBlob URL形式です")
                
                storage_account = match.group(1)
                container = match.group(2)
                blob_name = match.group(3)
                
                # アクセスキー取得
                account_key = self.controller.storage_key_manager.get_key(storage_account)
                if not account_key:
                    raise AccountKeyRetrievalError(f"アクセスキー取得失敗: {storage_account}")
                
                # Blob存在確認
                success, data, error = self.controller.azure_cli.run([
                    'storage', 'blob', 'show',
                    '--account-name', storage_account,
                    '--container-name', container,
                    '--name', blob_name,
                    '--account-key', account_key
                ])
                
                if not success:
                    raise parse_azure_cli_error(error if error else "Blob情報取得失敗")
                
                # Blob情報取得
                blob_tier = data['properties']['blobTier']
                archive_status = data['properties'].get('archiveStatus')
                
                # 検証成功
                validated.append({
                    'url': url,
                    'storage_account': storage_account,
                    'container': container,
                    'blob_name': blob_name,
                    'blob_tier': blob_tier,
                    'archive_status': archive_status,
                    'status': 'pending'
                })
                
                self.after(0, lambda: entry_data['result_label'].config(text=blob_url_input_texts.validation_success, fg="green"))
                
            except Exception as e:
                error_count += 1
                error_msg = str(e)
                logger.exception(f"URL検証エラー: {url} - {error_msg}")
                self.after(0, lambda: entry_data['result_label'].config(text=f"✗ {error_msg}", fg="red"))
        
        # 並列検証
        max_workers = self.controller.config.get('max_url_validation_workers', 10)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(validate_single_url, url, entry_data) for url, entry_data in urls]
            
            for future in futures:
                future.result()
        
        # 進捗ダイアログを閉じる
        self.after(0, lambda: progress_dialog.destroy())
        
        # 結果確認
        if error_count > 0:
            self.after(0, lambda: messagebox.showwarning(
                "検証エラー", 
                f"{error_count}件のURLで検証エラーが発生しました。\n"
                "エラー内容を確認して修正してください。"
            ))
        else:
            # 全て成功：次の画面へ
            # Note: OptionsScreen import moved to avoid circular dependency
            from azure_blob_rehydrator import OptionsScreen
            self.controller.validated_blobs = validated
            self.after(0, lambda: self.controller.show_frame(OptionsScreen))
