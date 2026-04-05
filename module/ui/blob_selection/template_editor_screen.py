"""
テンプレート編集画面

このモジュールはテンプレート管理画面を提供します。
- テンプレート一覧表示（カテゴリ別折り畳み対応）
- テンプレート新規作成
- テンプレート詳細編集
- プレースホルダー定義管理
- テンプレート削除
"""

import json
import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Dict, Optional

from ...core.logging_manager import logger
from ...ui_text.blob_texts import template_editor_texts

if TYPE_CHECKING:
    from azure_blob_rehydrator import AzureBlobRehydratorApp


class TemplateEditorScreen(tk.Frame):
    """テンプレート管理画面"""
    
    def __init__(self, parent, controller: 'AzureBlobRehydratorApp'):
        super().__init__(parent)
        self.controller = controller
        
        # タイトル
        title = ttk.Label(self, text=template_editor_texts.title, style='Title.TLabel')
        title.pack(pady=10)
        
        # メインフレーム
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 左側: テンプレート一覧（カテゴリ別折り畳み可能）
        left_frame = tk.Frame(main_frame, width=450)
        left_frame.pack(side="left", fill="both", padx=(0, 10))
        left_frame.pack_propagate(False)
        
        list_label = ttk.Label(left_frame, text=template_editor_texts.template_list_label, style='Heading.TLabel')
        list_label.pack(anchor="w", pady=5)
        
        # Canvas + Scrollbarでスクロール可能なカテゴリリスト（縦横両方対応）
        list_canvas_frame = tk.Frame(left_frame)
        list_canvas_frame.pack(fill="both", expand=True)
        
        self.list_canvas = tk.Canvas(list_canvas_frame, bg='white', highlightthickness=0)
        
        # 縦スクロールバー
        list_vscroll = ttk.Scrollbar(
            list_canvas_frame,
            orient="vertical",
            command=self.list_canvas.yview
        )
        
        # 横スクロールバー
        list_hscroll = ttk.Scrollbar(
            list_canvas_frame,
            orient="horizontal",
            command=self.list_canvas.xview
        )
        
        self.list_container = tk.Frame(self.list_canvas, bg='white')
        
        self.list_canvas.grid(row=0, column=0, sticky="nsew")
        list_vscroll.grid(row=0, column=1, sticky="ns")
        list_hscroll.grid(row=1, column=0, sticky="ew")
        
        list_canvas_frame.grid_rowconfigure(0, weight=1)
        list_canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.list_canvas.configure(
            yscrollcommand=list_vscroll.set,
            xscrollcommand=list_hscroll.set
        )
        self.list_canvas_window = self.list_canvas.create_window(
            (0, 0),
            window=self.list_container,
            anchor='nw'
        )
        
        # Canvas幅に合わせてフレーム幅を調整
        def on_list_canvas_configure(event):
            # フレームの幅をCanvas幅とコンテンツ幅の大きい方に設定
            canvas_width = event.width
            self.list_container.update_idletasks()
            content_width = self.list_container.winfo_reqwidth()
            frame_width = max(canvas_width, content_width)
            self.list_canvas.itemconfig(self.list_canvas_window, width=frame_width)
        
        self.list_canvas.bind('<Configure>', on_list_canvas_configure)
        
        # スクロール領域の更新
        def update_list_scroll_region(event=None):
            self.list_canvas.configure(scrollregion=self.list_canvas.bbox('all'))
        
        self.list_container.bind('<Configure>', update_list_scroll_region)
        
        # マウススクロール対応（縦と横）
        def on_mousewheel(event):
            bbox = self.list_canvas.bbox("all")
            if not bbox:
                return "break"
            
            canvas_width = self.list_canvas.winfo_width()
            canvas_height = self.list_canvas.winfo_height()
            
            # Canvas のサイズが有効でない場合はスキップ
            if canvas_width <= 1 or canvas_height <= 1:
                return "break"
            
            # Shiftキー押下時は横スクロール
            if event.state & 0x1:  # Shift
                content_width = bbox[2] - bbox[0]
                if content_width > canvas_width:
                    self.list_canvas.xview_scroll(int(-1*(event.delta/120)), "units")
                    return "break"
            else:
                # 通常は縦スクロール
                content_height = bbox[3] - bbox[1]
                if content_height > canvas_height:
                    self.list_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                    return "break"
            
            return "break"
        
        # Canvasとlist_containerにバインド
        self.list_canvas.bind("<MouseWheel>", on_mousewheel)
        self.list_canvas.bind("<Shift-MouseWheel>", on_mousewheel)
        self.list_container.bind("<MouseWheel>", on_mousewheel)
        self.list_container.bind("<Shift-MouseWheel>", on_mousewheel)
        
        # スクロールバーにもバインド（コンテンツサイズチェックを適用）
        list_vscroll.bind("<MouseWheel>", on_mousewheel)
        list_hscroll.bind("<MouseWheel>", on_mousewheel)
        list_hscroll.bind("<Shift-MouseWheel>", on_mousewheel)
        
        # 全ての子ウィジェットにもマウススクロールをバインドするヘルパー関数
        def bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", on_mousewheel)
            widget.bind("<Shift-MouseWheel>", on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)
        
        # list_containerの全子孫にバインド（テンプレート読み込み後に実行）
        self.bind_list_mousewheel = lambda: bind_mousewheel_recursive(self.list_container)
        
        # 右側: 編集エリア
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        # ボタン群
        action_frame = tk.Frame(right_frame)
        action_frame.pack(fill="x", padx=10, pady=20)
        
        new_button = ttk.Button(action_frame, text=template_editor_texts.new_button, command=self.new_template, width=15)
        new_button.pack(side="left", padx=5)
        
        save_button = ttk.Button(action_frame, text=template_editor_texts.save_button, command=self.save_template, width=15)
        save_button.pack(side="left", padx=5)
        
        cancel_button = ttk.Button(action_frame, text=template_editor_texts.cancel_button, command=self.cancel_edit, width=15)
        cancel_button.pack(side="left", padx=5)
        
        duplicate_button = ttk.Button(action_frame, text=template_editor_texts.duplicate_button, command=self.duplicate_template, width=15)
        duplicate_button.pack(side="left", padx=5)
        
        delete_button = ttk.Button(action_frame, text=template_editor_texts.delete_button, command=self.delete_template, width=15)
        delete_button.pack(side="left", padx=5)
        
        # Canvas + Scrollbar for 編集エリア
        self.right_canvas = tk.Canvas(right_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.right_canvas.yview)
        self.edit_container = tk.Frame(self.right_canvas)
        
        self.edit_container.bind(
            "<Configure>",
            lambda e: self.right_canvas.configure(scrollregion=self.right_canvas.bbox("all"))
        )
        
        self.right_canvas_frame = self.right_canvas.create_window((0, 0), window=self.edit_container, anchor="nw")
        self.right_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.right_canvas.bind("<Configure>", lambda e: self.right_canvas.itemconfig(self.right_canvas_frame, width=e.width))
        
        # マウススクロール対応（編集エリア全体で動作するように）
        def on_mousewheel_edit(event):
            bbox = self.right_canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = self.right_canvas.winfo_height()
                if content_height > canvas_height:
                    self.right_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Canvas、edit_container、およびその子ウィジェットすべてにバインド
        def bind_mousewheel(widget):
            """ウィジェットとその子ウィジェットすべてにマウススクロールをバインド"""
            # スクロールバー（ph_scrollbar）は独自のスクロール処理を持つため除外
            # それ以外のプレースホルダー定義エリア内ウィジェットは親要素のスクロールに反応
            if hasattr(self, 'ph_scrollbar') and widget == self.ph_scrollbar:
                return
            widget.bind("<MouseWheel>", on_mousewheel_edit)
            for child in widget.winfo_children():
                bind_mousewheel(child)
        
        self.right_canvas.bind("<MouseWheel>", on_mousewheel_edit)
        self.edit_container.bind("<MouseWheel>", on_mousewheel_edit)
        
        # edit_containerへの子ウィジェット追加を監視してバインド
        original_pack = self.edit_container.pack
        def pack_with_bind(*args, **kwargs):
            result = original_pack(*args, **kwargs)
            bind_mousewheel(self.edit_container)
            return result
        
        self.right_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # edit_containerを保存（後でバインド更新用）
        self.edit_canvas = self.right_canvas
        self.bind_mousewheel = bind_mousewheel
        
        # 編集エリアのウィジェット
        self.create_edit_widgets()
        
        # 戻るボタン（左下）
        button_frame_bottom = ttk.Frame(self)
        button_frame_bottom.pack(side="bottom", anchor="w", padx=20, pady=10)
        
        back_button = ttk.Button(button_frame_bottom, text=template_editor_texts.back_button,
                                command=self.go_back, width=15)
        back_button.pack(side="left")
        
        # データストレージ
        self.current_template_id = None
        self.placeholder_rows = {}  # プレースホルダー名 -> row_dataのマッピング
        self.expanded_ph = None  # 現在展開中のプレースホルダー名
        self.category_states = {}  # カテゴリの展開・折り畳み状態
        self.template_buttons = {}  # テンプレートIDとボタンのマッピング
    
    def create_edit_widgets(self):
        """編集ウィジェット作成"""
        # 基本情報フレーム
        basic_frame = ttk.LabelFrame(self.edit_container, text=template_editor_texts.basic_info_frame, padding=10)
        basic_frame.pack(fill="x", padx=10, pady=10)
        
        # 名前
        tk.Label(basic_frame, text=template_editor_texts.template_name_label, font=self.controller.default_font).grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(basic_frame, textvariable=self.name_var, width=50)
        name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # カテゴリ
        tk.Label(basic_frame, text=template_editor_texts.category_label, font=self.controller.default_font).grid(
            row=1, column=0, sticky="w", padx=5, pady=5
        )
        self.category_var = tk.StringVar()
        category_entry = ttk.Entry(basic_frame, textvariable=self.category_var, width=50)
        category_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # サブスクリプションID
        tk.Label(basic_frame, text=template_editor_texts.subscription_id_label, font=self.controller.default_font).grid(
            row=2, column=0, sticky="w", padx=5, pady=5
        )
        self.subscription_var = tk.StringVar()
        subscription_entry = ttk.Entry(basic_frame, textvariable=self.subscription_var, width=50)
        subscription_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        # ストレージアカウント
        tk.Label(basic_frame, text=template_editor_texts.storage_account_label, font=self.controller.default_font).grid(
            row=3, column=0, sticky="w", padx=5, pady=5
        )
        self.storage_account_var = tk.StringVar()
        storage_entry = ttk.Entry(basic_frame, textvariable=self.storage_account_var, width=50)
        storage_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
        
        # 説明
        tk.Label(basic_frame, text=template_editor_texts.description_label, font=self.controller.default_font).grid(
            row=4, column=0, sticky="nw", padx=5, pady=5
        )
        self.description_text = tk.Text(basic_frame, height=3, width=50, wrap=tk.WORD, font=self.controller.default_font)
        self.description_text.grid(row=4, column=1, sticky="ew", padx=5, pady=5)
        
        basic_frame.grid_columnconfigure(1, weight=1)
        
        # コンテナ設定フレーム
        container_frame = ttk.LabelFrame(self.edit_container, text=template_editor_texts.container_settings_frame, padding=10)
        container_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(container_frame, text=template_editor_texts.container_label, font=self.controller.default_font).grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        self.container_var = tk.StringVar()
        container_entry = ttk.Entry(container_frame, textvariable=self.container_var, width=50)
        container_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        tk.Label(
            container_frame, 
            text=template_editor_texts.placeholder_usage_note,
            font=('Noto Sans JP', 9),
            fg='gray'
        ).grid(row=1, column=1, sticky="w", padx=5, pady=(0, 5))
        
        container_frame.grid_columnconfigure(1, weight=1)
        
        # パスパターンフレーム
        pattern_frame = ttk.LabelFrame(self.edit_container, text=template_editor_texts.path_pattern_frame, padding=10)
        pattern_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(pattern_frame, text=template_editor_texts.path_label, font=self.controller.default_font).grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        self.path_pattern_var = tk.StringVar()
        path_entry = ttk.Entry(pattern_frame, textvariable=self.path_pattern_var, width=50)
        path_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        tk.Label(
            pattern_frame,
            text=template_editor_texts.placeholder_format_note,
            font=('Noto Sans JP', 9),
            fg='gray'
        ).grid(row=1, column=1, sticky="w", padx=5, pady=(0, 5))
        
        pattern_frame.grid_columnconfigure(1, weight=1)
        
        # プレースホルダー定義フレーム
        self.placeholder_frame = ttk.LabelFrame(self.edit_container, text=template_editor_texts.placeholder_definition_frame, padding=10)
        self.placeholder_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 追加ボタン
        add_ph_button = ttk.Button(
            self.placeholder_frame,
            text=template_editor_texts.add_placeholder_button,
            command=self.add_placeholder_row
        )
        add_ph_button.pack(pady=5)
        
        # Canvas + Scrollbarでスクロール可能なアコーディオンリスト
        canvas_frame = tk.Frame(self.placeholder_frame)
        canvas_frame.pack(fill="both", expand=True)
        
        self.ph_canvas = tk.Canvas(canvas_frame, borderwidth=0, highlightthickness=0, bg='white')
        self.ph_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.ph_canvas.yview)
        self.placeholder_container = tk.Frame(self.ph_canvas, bg='white')
        
        # スクロールバー用のマウススクロール
        def on_mousewheel_scrollbar(event):
            bbox = self.ph_canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = self.ph_canvas.winfo_height()
                if content_height > canvas_height:
                    self.ph_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        
        self.ph_scrollbar.bind("<MouseWheel>", on_mousewheel_scrollbar)
        
        self.placeholder_container.bind(
            "<Configure>",
            lambda e: self.ph_canvas.configure(scrollregion=self.ph_canvas.bbox("all"))
        )
        
        self.ph_canvas_frame = self.ph_canvas.create_window((0, 0), window=self.placeholder_container, anchor="nw")
        self.ph_canvas.configure(yscrollcommand=self.ph_scrollbar.set)
        self.ph_canvas.bind("<Configure>", lambda e: self.ph_canvas.itemconfig(self.ph_canvas_frame, width=e.width))
        
        self.ph_canvas.pack(side="left", fill="both", expand=True)
        self.ph_scrollbar.pack(side="right", fill="y")
        
        # 例パスフレーム
        example_frame = ttk.LabelFrame(self.edit_container, text=template_editor_texts.example_paths_frame, padding=10)
        example_frame.pack(fill="x", padx=10, pady=10)
        
        example_header_frame = tk.Frame(example_frame)
        example_header_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        tk.Label(
            example_header_frame,
            text=template_editor_texts.example_paths_note,
            font=self.controller.default_font
        ).pack(side="left")
        
        test_button = ttk.Button(
            example_header_frame,
            text=template_editor_texts.test_button_text,
            command=self.test_example_paths,
            width=10
        )
        test_button.pack(side="right", padx=5)
        
        self.example_text = tk.Text(example_frame, height=4, width=50, wrap=tk.WORD, font=self.controller.default_font)
        self.example_text.pack(fill="x", padx=5, pady=5)
        
        # すべてのウィジェットにマウススクロールをバインド
        if hasattr(self, 'bind_mousewheel'):
            self.bind_mousewheel(self.edit_container)
    
    def on_show(self):
        """画面表示時"""
        self.load_template_list()
        self.clear_edit_area()
        
        # レイアウト更新後にウィンドウサイズを再調整
        # Canvas内のコンテンツが完全に読み込まれるのを待つ
        self.after(100, self._request_window_size_update)
    
    def _request_window_size_update(self):
        """ウィンドウサイズの再調整をcontrollerに要求"""
        # レイアウトを強制更新
        self.placeholder_container.update_idletasks()
        self.update_idletasks()

        # Canvasのスクロール領域を更新
        self.ph_canvas.configure(scrollregion=self.ph_canvas.bbox("all"))

        # controllerのウィンドウサイズ調整メソッドを呼び出し
        if hasattr(self.controller, '_adjust_window_size'):
            self.controller._adjust_window_size(self.__class__)

    def load_template_list(self):
        """テンプレート一覧読み込み（カテゴリ別折り畳み可能）"""
        # 既存のウィジェットをクリア
        for widget in self.list_container.winfo_children():
            widget.destroy()
        
        self.template_buttons.clear()
        
        # カテゴリごとにテンプレートをグループ化
        categorized = self.controller.template_manager.get_templates_by_category()
        
        # テンプレートIDを生成（nameから）
        categorized_with_id = {}
        for category, templates in categorized.items():
            categorized_with_id[category] = []
            for template in templates:
                template_id = re.sub(r'[^\w\-]', '_', template.get('name', '').lower())
                categorized_with_id[category].append((template_id, template))
        
        categorized = categorized_with_id
        
        # カテゴリをソート
        for category in sorted(categorized.keys()):
            # カテゴリの展開状態（初期値はTrue:展開）
            if category not in self.category_states:
                self.category_states[category] = True
            
            # カテゴリヘッダーフレーム
            header_frame = tk.Frame(self.list_container, bg='lightblue', cursor='hand2')
            header_frame.pack(fill='x', pady=(5, 0))
            
            # 展開・折り畳みアイコン
            icon = '▼' if self.category_states[category] else '▶'
            icon_label = tk.Label(
                header_frame,
                text=icon,
                font=('Noto Sans JP', 10),
                bg='lightblue',
                width=2
            )
            icon_label.pack(side='left')
            
            # カテゴリ名
            category_label = tk.Label(
                header_frame,
                text=f"{category} ({len(categorized[category])})",
                font=('Noto Sans JP', 10, 'bold'),
                bg='lightblue',
                anchor='w'
            )
            category_label.pack(side='left', fill='x', expand=True, padx=5)
            
            # クリックでトグル
            def toggle_category(cat=category):
                self.category_states[cat] = not self.category_states[cat]
                self.load_template_list()  # 再描画
            
            header_frame.bind('<Button-1>', lambda e, cat=category: toggle_category(cat))
            icon_label.bind('<Button-1>', lambda e, cat=category: toggle_category(cat))
            category_label.bind('<Button-1>', lambda e, cat=category: toggle_category(cat))
            
            # テンプレートリスト（展開されている場合のみ表示）
            if self.category_states[category]:
                templates_frame = tk.Frame(self.list_container, bg='white')
                templates_frame.pack(fill='x')
                
                for template_id, template in sorted(categorized[category], key=lambda x: x[1].get('name', '')):
                    template_name = template.get('name', template_id)
                    
                    btn = tk.Button(
                        templates_frame,
                        text=template_name,
                        font=self.controller.default_font,
                        bg='white',
                        fg='black',
                        anchor='w',
                        relief='flat',
                        cursor='hand2',
                        padx=20,
                        pady=3,
                        command=lambda tid=template_id: self.load_template(tid)
                    )
                    btn.pack(fill='x')
                    
                    # ホバーエフェクト
                    def on_enter(e, b=btn):
                        b.config(bg='lightgray')
                    def on_leave(e, b=btn):
                        b.config(bg='white')
                    
                    btn.bind('<Enter>', on_enter)
                    btn.bind('<Leave>', on_leave)
                    
                    self.template_buttons[template_id] = btn
        
        # 全ての子ウィジェットにマウスホイールをバインド
        if hasattr(self, 'bind_list_mousewheel'):
            self.bind_list_mousewheel()
    
    def load_template(self, template_id: str):
        """テンプレート読み込み"""
        # template_idは実際にはnameから生成されたIDなので、nameに戻して検索
        # まず全テンプレートから一致するものを探す
        template = None
        for tmpl in self.controller.template_manager.load_templates():
            if re.sub(r'[^\w\-]', '_', tmpl.get('name', '').lower()) == template_id:
                template = tmpl
                break
        
        if not template:
            return
        
        self.current_template_id = template_id
        self.current_template_filename = template.get('_filename')  # 元のファイル名を保存
        
        # すべてのボタンの選択状態をクリア
        for tid, btn in self.template_buttons.items():
            if tid == template_id:
                btn.config(bg='lightblue', relief='solid')
            else:
                btn.config(bg='white', relief='flat')
        
        # 基本情報
        self.name_var.set(template.get('name', ''))
        self.category_var.set(template.get('category', ''))
        self.subscription_var.set(template.get('subscription', ''))
        self.storage_account_var.set(template.get('storage_account', ''))
        
        self.description_text.delete('1.0', tk.END)
        self.description_text.insert('1.0', template.get('description', ''))
        
        # コンテナ
        self.container_var.set(template.get('container', ''))
        
        # パスパターン
        self.path_pattern_var.set(template.get('path_pattern', ''))
        
        # プレースホルダー
        self.clear_placeholder_rows()
        for ph_name, ph_config in template.get('placeholders', {}).items():
            self.add_placeholder_row(ph_name, ph_config)
        
        # 例パス
        self.example_text.delete('1.0', tk.END)
        examples = template.get('example_paths', [])
        self.example_text.insert('1.0', '\n'.join(examples))
    
    def clear_edit_area(self):
        """編集エリアクリア"""
        self.current_template_id = None
        self.current_template_filename = None
        
        self.name_var.set('')
        self.category_var.set('')
        self.subscription_var.set('')
        self.storage_account_var.set('')
        self.description_text.delete('1.0', tk.END)
        self.container_var.set('')
        self.path_pattern_var.set('')
        
        self.clear_placeholder_rows()
        
        self.example_text.delete('1.0', tk.END)
    
    def clear_placeholder_rows(self):
        """プレースホルダー行クリア"""
        for ph_name, row_data in self.placeholder_rows.items():
            if 'container' in row_data:
                row_data['container'].destroy()
        self.placeholder_rows.clear()
        self.expanded_ph = None
    
    def add_placeholder_row(self, ph_name: str = '', ph_config: Optional[Dict] = None):
        """プレースホルダー行追加（アコーディオン形式）"""
        if ph_config is None:
            ph_config = {'type': 'text', 'label': ''}
        
        if not ph_name:
            # 新規追加の場合、一意な名前を生成
            ph_name = f"placeholder{len(self.placeholder_rows) + 1}"
        
        # アコーディオンコンテナを作成
        container = tk.Frame(self.placeholder_container, relief='raised', borderwidth=1, bg='#f0f0f0')
        container.pack(fill='x', pady=5)
        
        # ヘッダー部分（常に表示）
        header = tk.Frame(container, bg='#e0e0e0', cursor='hand2')
        header.pack(fill='x')
        
        # 展開アイコン
        expand_icon = tk.Label(header, text="▶", bg='#e0e0e0', font=self.controller.heading_font, width=2)
        expand_icon.pack(side='left', padx=5, pady=5)
        
        # 情報表示
        info_frame = tk.Frame(header, bg='#e0e0e0')
        info_frame.pack(side='left', fill='x', expand=True, pady=5)
        
        name_label = tk.Label(info_frame, text=f"名前: {ph_name}", bg='#e0e0e0', font=self.controller.default_font)
        name_label.pack(side='left', padx=10)
        
        label_label = tk.Label(info_frame, text=f"ラベル: {ph_config.get('label', '')}", bg='#e0e0e0')
        label_label.pack(side='left', padx=10)
        
        type_label = tk.Label(info_frame, text=f"タイプ: {ph_config.get('type', '')}", bg='#e0e0e0')
        type_label.pack(side='left', padx=10)
        
        # 削除ボタン
        delete_btn = ttk.Button(header, text=template_editor_texts.delete_button_text, width=6, 
                               command=lambda: self.remove_placeholder_accordion(ph_name))
        delete_btn.pack(side='right', padx=5, pady=2)
        
        # 詳細設定エリア（初期は非表示）
        detail_frame = tk.Frame(container, bg='white')
        
        # データ保存
        self.placeholder_rows[ph_name] = {
            'container': container,
            'header': header,
            'expand_icon': expand_icon,
            'name_label': name_label,
            'label_label': label_label,
            'type_label': type_label,
            'detail_frame': detail_frame,
            'delete_btn': delete_btn,
            'config': ph_config.copy(),
            'expanded': False
        }
        
        # クリックで展開/折りたたみ
        def toggle():
            row_data = self.placeholder_rows[ph_name]
            if row_data['expanded']:
                # 折りたたむ
                row_data['detail_frame'].pack_forget()
                row_data['expand_icon'].config(text="▶")
                row_data['expanded'] = False
                self.expanded_ph = None
            else:
                # 他の展開中のものを閉じる
                if self.expanded_ph and self.expanded_ph in self.placeholder_rows:
                    old_row = self.placeholder_rows[self.expanded_ph]
                    old_row['detail_frame'].pack_forget()
                    old_row['expand_icon'].config(text="▶")
                    old_row['expanded'] = False
                
                # 展開
                row_data['detail_frame'].pack(fill='both', padx=10, pady=10)
                row_data['expand_icon'].config(text="▼")
                row_data['expanded'] = True
                self.expanded_ph = ph_name
                self.populate_detail_form(ph_name)
        
        # ヘッダー全体とアイコンをクリック可能に
        header.bind('<Button-1>', lambda e: toggle())
        expand_icon.bind('<Button-1>', lambda e: toggle())
        for child in [name_label, label_label, type_label]:
            child.bind('<Button-1>', lambda e: toggle())
    
    def remove_placeholder_accordion(self, ph_name: str):
        """プレースホルダー削除（アコーディオン形式）"""
        if ph_name not in self.placeholder_rows:
            return
        
        row_data = self.placeholder_rows[ph_name]
        row_data['container'].destroy()
        del self.placeholder_rows[ph_name]
        
        # 削除したものが展開中だった場合はクリア
        if self.expanded_ph == ph_name:
            self.expanded_ph = None
    
    def populate_detail_form(self, ph_name: str):
        """詳細設定フォームを生成"""
        if ph_name not in self.placeholder_rows:
            return
        
        row_data = self.placeholder_rows[ph_name]
        detail_frame = row_data['detail_frame']
        ph_config = row_data['config']
        
        # 既存の詳細フォームをクリア
        for widget in detail_frame.winfo_children():
            widget.destroy()
        
        # 名前入力（編集可）
        name_frame = tk.Frame(detail_frame, bg='white')
        name_frame.pack(fill='x', pady=5)
        tk.Label(name_frame, text=template_editor_texts.placeholder_name_label, bg='white', width=15, anchor='w').pack(side='left')
        name_var = tk.StringVar(value=ph_name)
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=30)
        name_entry.pack(side='left', padx=5)
        row_data['name_var'] = name_var
        
        # ラベル入力
        label_frame = tk.Frame(detail_frame, bg='white')
        label_frame.pack(fill='x', pady=5)
        tk.Label(label_frame, text=template_editor_texts.placeholder_label_label, bg='white', width=15, anchor='w').pack(side='left')
        label_var = tk.StringVar(value=ph_config.get('label', ''))
        label_entry = ttk.Entry(label_frame, textvariable=label_var, width=30)
        label_entry.pack(side='left', padx=5)
        row_data['label_var'] = label_var
        
        # タイプ選択
        type_frame = tk.Frame(detail_frame, bg='white')
        type_frame.pack(fill='x', pady=5)
        tk.Label(type_frame, text=template_editor_texts.placeholder_type_label, bg='white', width=15, anchor='w').pack(side='left')
        type_var = tk.StringVar(value=ph_config.get('type', 'text'))
        type_combo = ttk.Combobox(type_frame, textvariable=type_var, 
                                  values=['text', 'numeric', 'enum', 'regex'],
                                  state='readonly', width=28)
        type_combo.pack(side='left', padx=5)
        row_data['type_var'] = type_var
        
        # タイプ別設定エリア
        settings_frame = tk.Frame(detail_frame, bg='white')
        settings_frame.pack(fill='both', expand=True, pady=10)
        row_data['settings_frame'] = settings_frame
        
        # タイプに応じたフォームを生成
        def on_type_change(*args):
            self.render_type_specific_form(ph_name)
        
        type_var.trace('w', on_type_change)
        
        # 初回のフォーム生成
        self.render_type_specific_form(ph_name)
        
        # 変更内容をヘッダーに反映
        def update_header(*args):
            row_data['name_label'].config(text=f"名前: {name_var.get()}")
            row_data['label_label'].config(text=f"ラベル: {label_var.get()}")
            row_data['type_label'].config(text=f"タイプ: {type_var.get()}")
        
        name_var.trace('w', update_header)
        label_var.trace('w', update_header)
        type_var.trace('w', update_header)
    
    def render_type_specific_form(self, ph_name: str):
        """タイプ別の設定フォームを描画"""
        if ph_name not in self.placeholder_rows:
            return
        
        row_data = self.placeholder_rows[ph_name]
        settings_frame = row_data['settings_frame']
        ph_type = row_data['type_var'].get()
        
        # 既存のウィジェットをクリア
        for widget in settings_frame.winfo_children():
            widget.destroy()
        
        # タイプ別のフォームを生成
        if ph_type == 'text':
            self._create_text_form(settings_frame, row_data)
        elif ph_type == 'numeric':
            self._create_numeric_form(settings_frame, row_data)
        elif ph_type == 'enum':
            self._create_enum_form(settings_frame, row_data)
        elif ph_type == 'regex':
            self._create_regex_form(settings_frame, row_data)
    
    def _create_text_form(self, parent, row_data):
        """テキスト型のフォーム"""
        config = row_data['config']
        
        # デフォルト値
        default_frame = tk.Frame(parent, bg='white')
        default_frame.pack(fill='x', pady=5)
        tk.Label(default_frame, text=template_editor_texts.default_value_label, bg='white', width=15, anchor='w').pack(side='left')
        default_var = tk.StringVar(value=config.get('default_value', ''))
        default_entry = ttk.Entry(default_frame, textvariable=default_var, width=30)
        default_entry.pack(side='left', padx=5)
        row_data['default_value_var'] = default_var
        
        # マッチモード
        match_frame = tk.Frame(parent, bg='white')
        match_frame.pack(fill='x', pady=5)
        tk.Label(match_frame, text=template_editor_texts.match_mode_label, bg='white', width=15, anchor='w').pack(side='left')
        match_var = tk.StringVar(value=config.get('match_mode', 'exact'))
        match_radio_frame = tk.Frame(match_frame, bg='white')
        match_radio_frame.pack(side='left', padx=5)
        ttk.Radiobutton(match_radio_frame, text=template_editor_texts.match_exact, variable=match_var, value='exact', style='White.TRadiobutton').pack(side='left', padx=5)
        ttk.Radiobutton(match_radio_frame, text=template_editor_texts.match_partial, variable=match_var, value='partial', style='White.TRadiobutton').pack(side='left', padx=5)
        row_data['match_mode_var'] = match_var
    
    def _create_numeric_form(self, parent, row_data):
        """数値型のフォーム"""
        config = row_data['config']
        
        # 最小値
        min_frame = tk.Frame(parent, bg='white')
        min_frame.pack(fill='x', pady=5)
        tk.Label(min_frame, text=template_editor_texts.min_value_label, bg='white', width=15, anchor='w').pack(side='left')
        min_var = tk.IntVar(value=config.get('min', 0))
        min_spinbox = ttk.Spinbox(min_frame, from_=0, to=9999, textvariable=min_var, width=28)
        min_spinbox.pack(side='left', padx=5)
        row_data['min_var'] = min_var
        
        # 最大値
        max_frame = tk.Frame(parent, bg='white')
        max_frame.pack(fill='x', pady=5)
        tk.Label(max_frame, text=template_editor_texts.max_value_label, bg='white', width=15, anchor='w').pack(side='left')
        max_var = tk.IntVar(value=config.get('max', 100))
        max_spinbox = ttk.Spinbox(max_frame, from_=0, to=9999, textvariable=max_var, width=28)
        max_spinbox.pack(side='left', padx=5)
        row_data['max_var'] = max_var
        
        # ゼロパディング
        pad_frame = tk.Frame(parent, bg='white')
        pad_frame.pack(fill='x', pady=5)
        tk.Label(pad_frame, text=template_editor_texts.zero_padding_label, bg='white', width=15, anchor='w').pack(side='left')
        pad_var = tk.IntVar(value=config.get('padding', 0))
        pad_spinbox = ttk.Spinbox(pad_frame, from_=0, to=10, textvariable=pad_var, width=28)
        pad_spinbox.pack(side='left', padx=5)
        tk.Label(pad_frame, text=template_editor_texts.padding_digits_label, bg='white').pack(side='left', padx=5)
        row_data['padding_var'] = pad_var
    
    def _create_enum_form(self, parent, row_data):
        """列挙型のフォーム"""
        config = row_data['config']
        
        # 選択肢
        options_frame = tk.Frame(parent, bg='white')
        options_frame.pack(fill='x', pady=5)
        tk.Label(options_frame, text=template_editor_texts.options_label, bg='white', width=15, anchor='w').pack(side='left', anchor='n', pady=2)
        options_text = tk.Text(options_frame, width=30, height=5, wrap='word', font=self.controller.default_font)
        options_text.pack(side='left', padx=5)
        options_text.insert('1.0', '\n'.join(config.get('options', [])))
        tk.Label(options_frame, text=template_editor_texts.options_note, bg='white', font=self.controller.default_font).pack(side='left', padx=5)
        row_data['options_text'] = options_text
        
        # 複数選択
        multiple_frame = tk.Frame(parent, bg='white')
        multiple_frame.pack(fill='x', pady=5)
        tk.Label(multiple_frame, text=template_editor_texts.multiple_selection_label, bg='white', width=15, anchor='w').pack(side='left')
        multiple_var = tk.BooleanVar(value=config.get('multiple', False))
        ttk.Checkbutton(multiple_frame, text=template_editor_texts.allow_multiple, variable=multiple_var).pack(side='left', padx=5)
        row_data['multiple_var'] = multiple_var
        
        # デフォルト値
        default_frame = tk.Frame(parent, bg='white')
        default_frame.pack(fill='x', pady=5)
        tk.Label(default_frame, text=template_editor_texts.default_value_label, bg='white', width=15, anchor='w').pack(side='left')
        default_var = tk.StringVar(value=config.get('default', ''))
        default_entry = ttk.Entry(default_frame, textvariable=default_var, width=30)
        default_entry.pack(side='left', padx=5)
        row_data['default_var'] = default_var
    
    def _create_regex_form(self, parent, row_data):
        """正規表現型のフォーム"""
        config = row_data['config']
        
        # パターン
        pattern_frame = tk.Frame(parent, bg='white')
        pattern_frame.pack(fill='x', pady=5)
        tk.Label(pattern_frame, text=template_editor_texts.regex_pattern_label, bg='white', width=15, anchor='w').pack(side='left')
        pattern_var = tk.StringVar(value=config.get('pattern', ''))
        pattern_entry = ttk.Entry(pattern_frame, textvariable=pattern_var, width=30)
        pattern_entry.pack(side='left', padx=5)
        row_data['pattern_var'] = pattern_var
        
        # テストボタン
        def test_pattern():
            pattern = pattern_var.get()
            if not pattern:
                messagebox.showwarning("警告", "正規表現を入力してください")
                return
            
            # テスト用ダイアログ
            dialog = tk.Toplevel(parent)
            dialog.title("正規表現テスト")
            dialog.geometry("400x250")
            
            # 中央配置
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f'+{x}+{y}')
            
            tk.Label(dialog, text=template_editor_texts.test_string_prompt, font=self.controller.default_font).pack(pady=5)
            test_entry = ttk.Entry(dialog, width=50)
            test_entry.pack(pady=5, padx=10)
            
            result_label = tk.Label(dialog, text="", font=self.controller.default_font, wraplength=350)
            result_label.pack(pady=10)
            
            def do_test():
                test_str = test_entry.get()
                try:
                    import re
                    if re.match(pattern, test_str):
                        result_label.config(text=f"✓ マッチしました", fg='green')
                    else:
                        result_label.config(text=f"✗ マッチしません", fg='red')
                except Exception as e:
                    result_label.config(text=f"エラー: {str(e)}", fg='red')
            
            ttk.Button(dialog, text=template_editor_texts.test_button_text, command=do_test).pack(pady=5)
            ttk.Button(dialog, text=template_editor_texts.close_button, command=dialog.destroy).pack(pady=5)
        
        test_button = ttk.Button(pattern_frame, text=template_editor_texts.test_button_text, command=test_pattern, width=8)
        test_button.pack(side='left', padx=5)
    
    def new_template(self):
        """新規テンプレート作成"""
        self.clear_edit_area()
        # 選択状態をクリア（現在のテンプレートボタンの強調表示を解除）
        for btn in self.template_buttons.values():
            btn.config(bg='white', relief='flat')
    
    def get_unique_template_name(self, base_name: str) -> str:
        """重複しないテンプレート名を生成
        
        Args:
            base_name: 基本となるテンプレート名
            
        Returns:
            重複しないテンプレート名
        """
        existing_names = [t['name'] for t in self.controller.template_manager.load_templates()]
        
        # 基本名がまだ使われていなければそのまま返す
        if base_name not in existing_names:
            return base_name
        
        # 連番を付けて重複を回避
        counter = 2
        while f"{base_name}{counter}" in existing_names:
            counter += 1
        
        return f"{base_name}{counter}"
    
    def duplicate_template(self):
        """テンプレート複製"""
        if not self.current_template_id:
            logger.warning("テンプレート複製: テンプレートが選択されていません")
            messagebox.showwarning("警告", "テンプレートを選択してください")
            return
        
        # 現在のテンプレートを取得
        current_template = None
        for tmpl in self.controller.template_manager.load_templates():
            if re.sub(r'[^\w\-]', '_', tmpl.get('name', '').lower()) == self.current_template_id:
                current_template = tmpl
                break
        
        if not current_template:
            logger.error(f"テンプレート複製: テンプレートが見つかりません - template_id={self.current_template_id}")
            messagebox.showerror("エラー", f"テンプレートが見つかりません\n\nテンプレートID: {self.current_template_id}")
            return
        
        # デフォルトの複製名を生成（重複チェック済み）
        original_name = current_template.get('name', '')
        default_copy_name = f"{original_name}のコピー"
        unique_default_name = self.get_unique_template_name(default_copy_name)
        
        # 名前入力ダイアログ
        dialog = tk.Toplevel(self)
        dialog.title("テンプレートを複製")
        dialog.geometry("400x150")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        # 中央配置
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')
        
        tk.Label(dialog, text=template_editor_texts.duplicate_prompt, 
                font=self.controller.default_font).pack(pady=10)
        
        name_var = tk.StringVar(value=unique_default_name)
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=10, padx=20)
        name_entry.focus_set()
        name_entry.select_range(0, tk.END)
        
        result = {'confirmed': False, 'name': ''}
        
        def on_ok():
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("警告", "テンプレート名を入力してください")
                return
            result['confirmed'] = True
            result['name'] = new_name
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="OK", command=on_ok, width=10).pack(side="left", padx=5)
        ttk.Button(button_frame, text=template_editor_texts.cancel_button, command=on_cancel, width=10).pack(side="left", padx=5)
        
        # Enterキーでも実行
        name_entry.bind('<Return>', lambda e: on_ok())
        
        self.wait_window(dialog)
        
        if not result['confirmed']:
            return
        
        # 複製されたテンプレートデータを作成
        new_template = {k: v for k, v in current_template.items() if k != '_filename'}
        
        # 名前が重複する場合は自動で連番を付ける
        final_name = self.get_unique_template_name(result['name'])
        new_template['name'] = final_name
        
        # 保存
        success, message = self.controller.template_manager.save_template(new_template)
        
        if success:
            if final_name != result['name']:
                messagebox.showinfo("成功", 
                    f"テンプレート名が重複していたため、'{final_name}'として保存しました")
            else:
                messagebox.showinfo("成功", "テンプレートを複製しました")
            
            # 一覧再読み込み
            self.load_template_list()
            
            # 複製されたテンプレートを自動選択
            new_template_id = re.sub(r'[^\w\-]', '_', final_name.lower())
            self.load_template(new_template_id)
        else:
            logger.error(f"テンプレート複製失敗: {message}")
            messagebox.showerror("エラー", f"複製失敗: {message}")
    
    def delete_template(self):
        """テンプレート削除"""
        if not self.current_template_id:
            logger.warning("テンプレート削除: テンプレートが選択されていません")
            messagebox.showwarning("警告", "テンプレートを選択してください")
            return
        
        result = messagebox.askyesno(
            "確認",
            f"テンプレート「{self.current_template_id}」を削除しますか？"
        )
        
        if result:
            # テンプレート名を取得（IDから逆引き）
            template_name = None
            for tmpl in self.controller.template_manager.load_templates():
                if re.sub(r'[^\w\-]', '_', tmpl.get('name', '').lower()) == self.current_template_id:
                    template_name = tmpl.get('name')
                    break
            
            if not template_name:
                logger.error(f"テンプレート削除: テンプレートが見つかりません - template_id={self.current_template_id}")
                messagebox.showerror("エラー", f"テンプレートが見つかりません\n\nテンプレートID: {self.current_template_id}")
                return
            
            # TemplateManagerの削除メソッドを使用
            success, message = self.controller.template_manager.delete_template(template_name)
            
            if success:
                messagebox.showinfo("成功", "テンプレートを削除しました")
                # 再読み込み
                self.load_template_list()
                self.clear_edit_area()
            else:
                logger.error(f"テンプレート削除失敗: {message}")
                messagebox.showerror("エラー", f"削除失敗: {message}")
    
    def save_template(self):
        """テンプレート保存"""
        # 基本情報取得
        name = self.name_var.get().strip()
        category = self.category_var.get().strip()
        subscription = self.subscription_var.get().strip()
        storage_account = self.storage_account_var.get().strip()
        description = self.description_text.get('1.0', tk.END).strip()
        container = self.container_var.get().strip()
        path_pattern = self.path_pattern_var.get().strip()
        
        # 検証
        if not name:
            logger.warning("テンプレート保存: 名前が未入力です")
            messagebox.showwarning("警告", "名前を入力してください")
            return
        
        if not category:
            logger.warning("テンプレート保存: カテゴリが未入力です")
            messagebox.showwarning("警告", "カテゴリを入力してください")
            return
        
        if not subscription:
            logger.warning("テンプレート保存: サブスクリプションIDが未入力です")
            messagebox.showwarning("警告", "サブスクリプションIDを入力してください")
            return
        
        if not storage_account:
            logger.warning("テンプレート保存: ストレージアカウントが未入力です")
            messagebox.showwarning("警告", "ストレージアカウントを入力してください")
            return
        
        if not path_pattern:
            logger.warning("テンプレート保存: パスパターンが未入力です")
            messagebox.showwarning("警告", "パスパターンを入力してください")
            return
        
        # プレースホルダー取得
        placeholders = {}
        for ph_name, row_data in self.placeholder_rows.items():
            # 名前を取得（編集されている可能性がある）
            if 'name_var' in row_data:
                actual_name = row_data['name_var'].get().strip()
            else:
                actual_name = ph_name
            
            if not actual_name:
                continue
            
            # ラベルとタイプを取得
            ph_label = row_data.get('label_var', tk.StringVar()).get().strip()
            ph_type = row_data.get('type_var', tk.StringVar(value='text')).get()
            
            ph_config = {
                'type': ph_type,
                'label': ph_label if ph_label else actual_name
            }
            
            # タイプ別の設定を収集
            if ph_type == 'text':
                if 'default_value_var' in row_data:
                    ph_config['default_value'] = row_data['default_value_var'].get()
                if 'match_mode_var' in row_data:
                    ph_config['match_mode'] = row_data['match_mode_var'].get()
            
            elif ph_type == 'numeric':
                if 'min_var' in row_data:
                    ph_config['min'] = row_data['min_var'].get()
                if 'max_var' in row_data:
                    ph_config['max'] = row_data['max_var'].get()
                if 'padding_var' in row_data:
                    ph_config['padding'] = row_data['padding_var'].get()
            
            elif ph_type == 'enum':
                if 'options_text' in row_data:
                    options_str = row_data['options_text'].get('1.0', tk.END).strip()
                    ph_config['options'] = [opt.strip() for opt in options_str.split('\n') if opt.strip()]
                if 'multiple_var' in row_data:
                    ph_config['multiple'] = row_data['multiple_var'].get()
                if 'default_var' in row_data:
                    ph_config['default'] = row_data['default_var'].get()
            
            elif ph_type == 'regex':
                if 'pattern_var' in row_data:
                    ph_config['pattern'] = row_data['pattern_var'].get()
            
            placeholders[actual_name] = ph_config
        
        # 例パス取得
        example_lines = self.example_text.get('1.0', tk.END).strip().split('\n')
        example_paths = [line.strip() for line in example_lines if line.strip()]
        
        # テンプレートデータ構築
        template_data = {
            'name': name,
            'category': category,
            'subscription': subscription,
            'storage_account': storage_account,
            'description': description,
            'container': container if container else None,
            'path_pattern': path_pattern,
            'placeholders': placeholders,
            'example_paths': example_paths
        }
        
        # 既存テンプレートの場合は元のファイル名を含める
        if self.current_template_filename:
            template_data['_filename'] = self.current_template_filename
        
        # TemplateManagerの保存メソッドを使用
        success, message = self.controller.template_manager.save_template(template_data)
        
        if success:
            messagebox.showinfo("成功", "テンプレートを保存しました")
            
            # 一覧再読み込み
            self.load_template_list()
            
            # template_idを更新（nameから生成）
            template_id = re.sub(r'[^\w\-]', '_', name.lower())
            self.current_template_id = template_id
        else:
            logger.error(f"テンプレート保存失敗: {message}")
            messagebox.showerror("エラー", f"保存失敗: {message}")
    
    def cancel_edit(self):
        """編集キャンセル"""
        if self.current_template_id:
            self.load_template(self.current_template_id)
        else:
            self.clear_edit_area()
    
    def test_example_paths(self):
        """例パスの動作確認"""
        # 現在の入力値を取得
        container = self.container_var.get().strip()
        path_pattern = self.path_pattern_var.get().strip()
        
        if not path_pattern:
            messagebox.showwarning("警告", "パスパターンを入力してください")
            return
        
        # 例パスを取得
        example_lines = self.example_text.get('1.0', tk.END).strip().split('\n')
        example_paths = [line.strip() for line in example_lines if line.strip()]
        
        if not example_paths:
            messagebox.showwarning("警告", "例パスを入力してください")
            return
        
        # プレースホルダー情報を取得
        placeholders = {}
        for ph_name, row_data in self.placeholder_rows.items():
            # 名前を取得
            if 'name_var' in row_data:
                actual_name = row_data['name_var'].get().strip()
            else:
                actual_name = ph_name
            
            if actual_name:
                ph_type = row_data.get('type_var', tk.StringVar(value='text')).get()
                placeholders[actual_name] = {'type': ph_type}
        
        # テスト結果ウィンドウを作成
        result_window = tk.Toplevel(self)
        result_window.title("例パステスト結果")
        result_window.geometry("800x600")
        
        # 中央配置
        result_window.update_idletasks()
        x = (result_window.winfo_screenwidth() // 2) - (result_window.winfo_width() // 2)
        y = (result_window.winfo_screenheight() // 2) - (result_window.winfo_height() // 2)
        result_window.geometry(f'+{x}+{y}')
        
        # 結果表示用テキストエリア
        result_frame = ttk.Frame(result_window, padding=10)
        result_frame.pack(fill="both", expand=True)
        
        result_text = tk.Text(result_frame, wrap=tk.WORD, font=self.controller.default_font)
        result_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=result_text.yview)
        result_text.configure(yscrollcommand=result_scroll.set)
        
        result_text.pack(side="left", fill="both", expand=True)
        result_scroll.pack(side="right", fill="y")
        
        # 閉じるボタン
        close_button = ttk.Button(result_window, text=template_editor_texts.close_button, command=result_window.destroy)
        close_button.pack(pady=10)
        
        # テスト実行
        result_text.insert(tk.END, "=== 例パステスト結果 ===\n\n")
        result_text.insert(tk.END, f"テンプレートパターン:\n")
        if container:
            result_text.insert(tk.END, f"  コンテナ: {container}\n")
        result_text.insert(tk.END, f"  パス: {path_pattern}\n\n")
        
        # パターンを正規表現に変換
        container_pattern = self._convert_to_regex(container, placeholders) if container else None
        path_regex = self._convert_to_regex(path_pattern, placeholders)
        
        result_text.insert(tk.END, f"正規表現パターン:\n")
        if container_pattern:
            result_text.insert(tk.END, f"  コンテナ: {container_pattern}\n")
        result_text.insert(tk.END, f"  パス: {path_regex}\n\n")
        result_text.insert(tk.END, "=" * 80 + "\n\n")
        
        # 各例パスをテスト
        match_count = 0
        for i, example_path in enumerate(example_paths, 1):
            result_text.insert(tk.END, f"[例パス {i}]\n")
            result_text.insert(tk.END, f"{example_path}\n\n")
            
            # パスを分割（コンテナとパス）
            if '/' in example_path:
                parts = example_path.split('/', 1)
                if len(parts) == 2:
                    example_container, example_path_only = parts
                else:
                    example_container = ""
                    example_path_only = example_path
            else:
                example_container = ""
                example_path_only = example_path
            
            # コンテナのマッチテスト
            container_match = True
            container_values = {}
            if container and container_pattern:
                try:
                    container_regex_obj = re.compile(f"^{container_pattern}$")
                    container_match_obj = container_regex_obj.match(example_container)
                    if container_match_obj:
                        container_values = container_match_obj.groupdict()
                        result_text.insert(tk.END, f"✓ コンテナマッチ: {example_container}\n")
                        if container_values:
                            result_text.insert(tk.END, f"  抽出値:\n")
                            for key, value in container_values.items():
                                result_text.insert(tk.END, f"    {key} = {value}\n")
                    else:
                        container_match = False
                        result_text.insert(tk.END, f"✗ コンテナ不一致: {example_container}\n")
                except re.error as e:
                    result_text.insert(tk.END, f"✗ コンテナパターンエラー: {str(e)}\n")
                    container_match = False
            
            # パスのマッチテスト
            path_match = False
            path_values = {}
            try:
                path_regex_obj = re.compile(f"^{path_regex}$")
                path_match_obj = path_regex_obj.match(example_path_only)
                if path_match_obj:
                    path_match = True
                    path_values = path_match_obj.groupdict()
                    result_text.insert(tk.END, f"✓ パスマッチ: {example_path_only}\n")
                    if path_values:
                        result_text.insert(tk.END, f"  抽出値:\n")
                        for key, value in path_values.items():
                            result_text.insert(tk.END, f"    {key} = {value}\n")
                else:
                    result_text.insert(tk.END, f"✗ パス不一致: {example_path_only}\n")
            except re.error as e:
                result_text.insert(tk.END, f"✗ パスパターンエラー: {str(e)}\n")
            
            # 総合判定
            if container_match and path_match:
                result_text.insert(tk.END, f"\n結果: ✓ マッチ成功\n")
                match_count += 1
                
                # 全プレースホルダー値をまとめて表示
                all_values = {**container_values, **path_values}
                if all_values:
                    result_text.insert(tk.END, f"\n抽出されたプレースホルダー値:\n")
                    for key, value in all_values.items():
                        result_text.insert(tk.END, f"  {{{key}}} = {value}\n")
            else:
                result_text.insert(tk.END, f"\n結果: ✗ マッチ失敗\n")
            
            result_text.insert(tk.END, "\n" + "-" * 80 + "\n\n")
        
        # サマリー
        result_text.insert(tk.END, f"\n=== サマリー ===\n")
        result_text.insert(tk.END, f"テスト例数: {len(example_paths)}\n")
        result_text.insert(tk.END, f"マッチ成功: {match_count}\n")
        result_text.insert(tk.END, f"マッチ失敗: {len(example_paths) - match_count}\n")
        
        # 編集不可に設定
        result_text.configure(state='disabled')
    
    def _convert_to_regex(self, pattern: str, placeholders: Dict) -> str:
        """
        テンプレートパターンを正規表現に変換
        
        Args:
            pattern: テンプレートパターン（例: "y={year}/m={month}/d={day}"）
            placeholders: プレースホルダー定義
        
        Returns:
            正規表現パターン（例: "y=(?P<year>.+?)/m=(?P<month>.+?)/d=(?P<day>.+?)"）
        """
        if not pattern:
            return ""
        
        # エスケープが必要な正規表現特殊文字
        regex_pattern = re.escape(pattern)
        
        # プレースホルダーを正規表現グループに置き換え
        # {placeholder} -> (?P<placeholder>.+?)
        placeholder_regex = re.compile(r'\\{(\w+)\\}')
        
        def replace_placeholder(match):
            ph_name = match.group(1)
            # 名前付きキャプチャグループとして展開
            # wildcard以外のタイプに応じて適切なパターンを生成することも可能
            # ここではシンプルに.+?（最短マッチ）を使用
            return f'(?P<{ph_name}>.+?)'
        
        regex_pattern = placeholder_regex.sub(replace_placeholder, regex_pattern)
        
        return regex_pattern
    
    def go_back(self):
        """前の画面に戻る"""
        # 履歴を確認して適切な画面に戻る
        # AuthenticationMethodScreenから来た場合はそこに戻る
        # それ以外はTemplateSelectionScreenに戻る
        if hasattr(self.controller, 'history') and len(self.controller.history) >= 2:
            # 1つ前の画面を取得
            previous_screen = self.controller.history[-2]
            if previous_screen.__name__ == 'AuthenticationMethodScreen':
                self.controller.show_frame('AuthenticationMethodScreen')
                return

        if hasattr(self.controller, 'run_template_management') and self.controller.run_template_management:
            # 終了
            self.controller.destroy()
            return
        # デフォルトはTemplateSelectionScreenに戻る
        self.controller.show_frame('TemplateSelectionScreen')
