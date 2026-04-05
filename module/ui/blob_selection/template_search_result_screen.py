"""テンプレート検索結果画面"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from typing import TYPE_CHECKING

from ...core.logging_manager import logger
from ...ui_text.blob_texts import template_search_result_texts

if TYPE_CHECKING:
    from azure_blob_rehydrator import AzureBlobRehydratorApp


class TemplateSearchResultScreen(tk.Frame):
    """テンプレート検索結果画面"""
    
    def __init__(self, parent, controller: 'AzureBlobRehydratorApp'):
        super().__init__(parent)
        self.controller = controller
        
        # タイトル
        title = ttk.Label(self, text=template_search_result_texts.title, style='Title.TLabel')
        title.pack(pady=10)
        
        # 統計情報
        self.stats_label = tk.Label(
            self,
            text="",
            font=controller.heading_font,
            fg="blue"
        )
        self.stats_label.pack()
        
        # TreeView
        tree_frame = tk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        columns = ('select', 'container', 'name', 'template', 'size', 'last_modified')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        self.tree.heading('select', text=template_search_result_texts.col_select)
        self.tree.heading('container', text=template_search_result_texts.col_container)
        self.tree.heading('name', text=template_search_result_texts.col_name)
        self.tree.heading('template', text=template_search_result_texts.col_template_alt)
        self.tree.heading('size', text=template_search_result_texts.col_size)
        self.tree.heading('last_modified', text=template_search_result_texts.col_last_modified)
        
        self.tree.column('select', width=40, minwidth=40, anchor='center', stretch=False)
        self.tree.column('container', width=250, minwidth=100, stretch=False)
        self.tree.column('name', width=800, minwidth=100, stretch=False)
        self.tree.column('template', width=250, minwidth=100, stretch=False)
        self.tree.column('size', width=50, minwidth=50, anchor='e', stretch=False)
        self.tree.column('last_modified', width=130, minwidth=50, stretch=False)
        
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # チェックボックスのための選択管理
        self.tree.bind('<Button-1>', self.on_tree_click)
        
        # ボタンエリア
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        
        # 戻るボタン
        back_button = ttk.Button(button_frame, text=template_search_result_texts.back_button, command=self.go_back, width=12)
        back_button.pack(side="left", padx=5)
        
        select_all_button = ttk.Button(button_frame, text=template_search_result_texts.select_all_button, command=self.select_all, width=12)
        select_all_button.pack(side="left", padx=5)
        
        deselect_all_button = ttk.Button(button_frame, text=template_search_result_texts.deselect_all_button, command=self.deselect_all, width=12)
        deselect_all_button.pack(side="left", padx=5)
        
        continue_button = ttk.Button(
            button_frame,
            text=template_search_result_texts.next_button,
            command=self.continue_to_options,
            width=25
        )
        continue_button.pack(side="left", padx=20)
        
        # データストレージ
        self.selected_items = set()
    
    def on_tree_click(self, event):
        """TreeViewクリック時（チェックボックス切り替え）"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == '#1':  # select列
                item = self.tree.identify_row(event.y)
                if item:
                    if item in self.selected_items:
                        self.selected_items.remove(item)
                        self.tree.set(item, 'select', '☐')
                    else:
                        self.selected_items.add(item)
                        self.tree.set(item, 'select', '☑')
    
    def select_all(self):
        """全選択"""
        for item in self.tree.get_children():
            self.selected_items.add(item)
            self.tree.set(item, 'select', '☑')
    
    def deselect_all(self):
        """全解除"""
        for item in self.tree.get_children():
            self.selected_items.discard(item)
            self.tree.set(item, 'select', '☐')
    
    def go_back(self):
        """最後の展開設定画面に戻る"""
        if self.controller.selected_templates:
            self.controller.current_template_index = len(
                self.controller.selected_templates
            ) - 1
            self.controller.show_frame('TemplateExpansionScreen')
        else:
            self.controller.show_frame('TemplateSelectionScreen')
    
    def on_show(self):
        """画面表示時"""
        # TreeViewクリア
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.selected_items.clear()
        
        # 統計情報
        count = len(self.controller.matched_blobs)
        self.stats_label.config(text=f"検索結果: {count}件のBlobが見つかりました")
        
        # Blobデータ表示
        for blob in self.controller.matched_blobs:
            blob_name = blob.get('name', '')
            container_name = blob.get('container', '')
            template_name = blob.get('template_name', '')
            
            properties = blob.get('properties', {})
            size = properties.get('contentLength', 0)
            last_modified = properties.get('lastModified', '')
            
            size_str = self.format_size(size)
            date_str = last_modified[:19].replace('T', ' ') if last_modified else ''
            
            item_id = self.tree.insert('', 'end', values=(
                '☐',
                container_name,
                blob_name,
                template_name,
                size_str,
                date_str
            ))
            
            # Blobデータを保持
            self.tree.item(item_id, tags=(blob_name,))
        
        # 結果が0件の場合
        if count == 0:
            self.tree.insert('', 'end', values=('', '', '（検索結果なし）', '', '', ''))
    
    def format_size(self, size: int) -> str:
        """サイズフォーマット"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 ** 3:
            return f"{size / 1024 ** 2:.2f} MB"
        else:
            return f"{size / 1024 ** 3:.2f} GB"
    
    def continue_to_options(self):
        """オプション画面へ"""
        if not self.selected_items:
            logger.warning("オプション画面への遷移: Blobが選択されていません")
            messagebox.showwarning("警告", "Blobを選択してください")
            return
        
        # 選択されたBlobのURLを構築し、validated_blobsに設定
        blob_urls = []
        validated_blobs = []
        
        for item_id in self.selected_items:
            # matched_blobsから該当するBlobを検索
            item_values = self.tree.item(item_id, 'values')
            blob_name = item_values[2]  # name列
            container_name = item_values[1]  # container列
            
            # matched_blobsから該当Blobを取得
            for blob in self.controller.matched_blobs:
                if blob.get('name') == blob_name and blob.get('container') == container_name:
                    storage_account = blob.get('storage_account', '')
                    blob_url = f"https://{storage_account}.blob.core.windows.net/{container_name}/{blob_name}"
                    blob_urls.append(blob_url)
                    
                    # validated_blobsに追加（ProgressScreenで使用される）
                    validated_blobs.append({
                        'url': blob_url,
                        'storage_account': storage_account,
                        'container': container_name,
                        'blob_name': blob_name,
                        'properties': blob.get('properties', {}),
                        'status': 'pending',
                        'message': ''
                    })
                    break
        
        if not blob_urls:
            logger.error(f"選択されたBlobのURL構築に失敗しました - selected_items={len(self.selected_items)}, validated_blobs={len(validated_blobs)}")
            messagebox.showerror("エラー", "選択されたBlobのURL構築に失敗しました\n\n選択されたBlobが見つかりませんでした。")
            return
        
        # blob_urlsとvalidated_blobsを設定してOptionsScreenへ
        self.controller.blob_urls = blob_urls
        self.controller.validated_blobs = validated_blobs
        self.controller.show_frame('OptionsScreen')
