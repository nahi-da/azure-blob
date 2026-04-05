"""テンプレート選択画面"""

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Dict, List

from ...ui_text.blob_texts import template_selection_texts

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from azure_blob_rehydrator import AzureBlobRehydratorApp


class TemplateSelectionScreen(tk.Frame):
    """テンプレート選択画面"""
    
    def __init__(self, parent, controller: 'AzureBlobRehydratorApp'):
        super().__init__(parent)
        self.controller = controller
        
        # タイトル
        title = ttk.Label(self, text=template_selection_texts.title, style='Title.TLabel')
        title.pack(pady=10)
        
        # 説明
        desc = tk.Label(
            self,
            text=template_selection_texts.subtitle,
            font=controller.default_font
        )
        desc.pack(pady=5)
        
        # サブスクリプション情報
        filter_frame = tk.Frame(self)
        filter_frame.pack(fill="x", padx=20, pady=5)
        
        self.filter_info_label = tk.Label(
            filter_frame,
            text="",
            font=controller.default_font,
            fg='blue'
        )
        self.filter_info_label.pack()
        
        # ボタンフレーム（テンプレート管理・更新）
        action_frame = tk.Frame(self)
        action_frame.pack(fill="x", padx=20, pady=5)
        
        # テンプレート管理ボタン
        manage_button = ttk.Button(action_frame,
                                   text=template_selection_texts.manage_button,
                                   command=self.open_template_editor)
        manage_button.pack(side="left", padx=5)
        
        # 更新ボタン
        refresh_button = ttk.Button(action_frame,
                                    text=template_selection_texts.refresh_button,
                                    command=self.refresh_templates)
        refresh_button.pack(side="left", padx=5)
        
        # メインフレーム
        main_frame = tk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # 左側: テンプレート一覧
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True)
        
        template_label = ttk.Label(left_frame, text=template_selection_texts.template_list_label, style='Heading.TLabel')
        template_label.pack(anchor="w", pady=5)
        
        # Canvas + Scrollbar（縦横両方対応）
        template_canvas_frame = tk.Frame(left_frame)
        template_canvas_frame.pack(fill="both", expand=True)
        
        self.template_canvas = tk.Canvas(template_canvas_frame, bg='white', highlightthickness=0)
        
        # 縦スクロールバー
        template_vscroll = ttk.Scrollbar(
            template_canvas_frame,
            orient="vertical",
            command=self.template_canvas.yview
        )
        
        # 横スクロールバー
        template_hscroll = ttk.Scrollbar(
            template_canvas_frame,
            orient="horizontal",
            command=self.template_canvas.xview
        )
        
        self.template_frame = tk.Frame(self.template_canvas, bg='white')
        
        self.template_canvas.grid(row=0, column=0, sticky="nsew")
        template_vscroll.grid(row=0, column=1, sticky="ns")
        template_hscroll.grid(row=1, column=0, sticky="ew")
        
        template_canvas_frame.grid_rowconfigure(0, weight=1)
        template_canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.template_canvas.configure(
            yscrollcommand=template_vscroll.set,
            xscrollcommand=template_hscroll.set
        )
        self.canvas_window = self.template_canvas.create_window(
            (0, 0),
            window=self.template_frame,
            anchor='nw'
        )
        
        # Canvas幅に合わせてフレーム幅を調整
        def on_canvas_configure(event):
            # フレームの幅をCanvas幅とコンテンツ幅の大きい方に設定
            canvas_width = event.width
            self.template_frame.update_idletasks()
            content_width = self.template_frame.winfo_reqwidth()
            frame_width = max(canvas_width, content_width)
            self.template_canvas.itemconfig(self.canvas_window, width=frame_width)
        
        self.template_canvas.bind('<Configure>', on_canvas_configure)
        
        # スクロール領域の更新
        def update_scroll_region(event=None):
            self.template_canvas.configure(scrollregion=self.template_canvas.bbox('all'))
        
        self.template_frame.bind('<Configure>', update_scroll_region)
        
        # マウススクロール（縦と横）
        def on_mousewheel_template(event):
            bbox = self.template_canvas.bbox("all")
            if not bbox:
                return "break"
            
            canvas_width = self.template_canvas.winfo_width()
            canvas_height = self.template_canvas.winfo_height()
            
            # Canvas のサイズが有効でない場合はスキップ
            if canvas_width <= 1 or canvas_height <= 1:
                return "break"
            
            # Shiftキー押下時は横スクロール
            if event.state & 0x1:  # Shift
                content_width = bbox[2] - bbox[0]
                if content_width > canvas_width:
                    self.template_canvas.xview_scroll(int(-1*(event.delta/120)), "units")
                    return "break"
            else:
                # 通常は縦スクロール
                content_height = bbox[3] - bbox[1]
                if content_height > canvas_height:
                    self.template_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                    return "break"
            
            return "break"
        
        # Canvasとtemplate_frameにバインド
        self.template_canvas.bind("<MouseWheel>", on_mousewheel_template)
        self.template_canvas.bind("<Shift-MouseWheel>", on_mousewheel_template)
        self.template_frame.bind("<MouseWheel>", on_mousewheel_template)
        self.template_frame.bind("<Shift-MouseWheel>", on_mousewheel_template)
        
        # スクロールバーにもバインド（コンテンツサイズチェックを適用）
        template_vscroll.bind("<MouseWheel>", on_mousewheel_template)
        template_hscroll.bind("<MouseWheel>", on_mousewheel_template)
        template_hscroll.bind("<Shift-MouseWheel>", on_mousewheel_template)
        
        # 全ての子ウィジェットにもマウススクロールをバインドするヘルパー関数
        def bind_mousewheel_recursive(widget):
            widget.bind("<MouseWheel>", on_mousewheel_template)
            widget.bind("<Shift-MouseWheel>", on_mousewheel_template)
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)
        
        # template_frameの全子孫にバインド（テンプレート読み込み後に実行）
        self.bind_template_mousewheel = lambda: bind_mousewheel_recursive(self.template_frame)
        
        # 右側: テンプレート詳細
        right_frame = tk.Frame(main_frame, width=400)
        right_frame.pack(side="right", fill="both", padx=(20, 0))
        right_frame.pack_propagate(False)
        
        detail_label = ttk.Label(right_frame, text=template_selection_texts.template_detail_label, style='Heading.TLabel')
        detail_label.pack(anchor="w", pady=5)
        
        self.detail_text = tk.Text(
            right_frame,
            font=controller.default_font,
            wrap=tk.WORD,
            state='disabled'
        )
        self.detail_text.pack(fill="both", expand=True)
        
        # ボタンフレーム
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)
        
        # 戻るボタン
        from azure_blob_rehydrator import BlobSelectionMethodScreen
        back_button = ttk.Button(
            button_frame,
            text=template_selection_texts.back_button,
            command=lambda: controller.show_frame(BlobSelectionMethodScreen),
            width=15
        )
        back_button.pack(side="left", padx=5)
        
        # 次へボタン
        next_button = ttk.Button(
            button_frame,
            text=template_selection_texts.next_button,
            command=self.go_next,
            width=15
        )
        next_button.pack(side="left", padx=5)
        
        # データストレージ
        self.all_templates = []
        self.template_vars = []
        self.category_states = {}
    
    def on_show(self):
        """画面表示時"""
        # サブスクリプション情報表示
        if self.controller.current_subscription:
            sub_id = self.controller.current_subscription.get('id', '')
            # ARMリソースID形式の場合はGUID部分のみ抽出
            if sub_id.startswith('/subscriptions/'):
                display_id = sub_id.split('/')[-1]
            else:
                display_id = sub_id
            self.filter_info_label.config(
                text=f"サブスクリプション: {display_id}",
                fg='blue'
            )
        else:
            self.filter_info_label.config(
                text=template_selection_texts.subscription_not_selected_label,
                fg='gray'
            )
        
        # テンプレート読み込み
        self.all_templates = self.get_filtered_templates_list()
        self.create_template_checkboxes()
    
    def get_filtered_templates_list(self) -> List[Dict]:
        """サブスクリプションでフィルタリングされたテンプレートを取得"""
        current_sub_id = None
        if self.controller.current_subscription:
            full_id = self.controller.current_subscription.get('id', '')
            # ARMリソースID（/subscriptions/GUID）からGUID部分のみを抽出
            if full_id.startswith('/subscriptions/'):
                current_sub_id = full_id.split('/')[2]
            else:
                current_sub_id = full_id
        
        templates = self.controller.template_manager.load_templates()
        filtered = []
        
        for template in templates:
            # サブスクリプションフィルタ
            if current_sub_id:
                template_sub = template.get('subscription', '')
                # テンプレートのサブスクリプションIDを正規化（GUIDのみ抽出）
                if template_sub.startswith('/subscriptions/'):
                    template_sub = template_sub.split('/')[2]
                
                if template_sub and template_sub != current_sub_id:
                    continue
            
            filtered.append(template)
        
        # カテゴリ順、名前順でソート
        filtered.sort(key=lambda t: (t.get('category', 'その他'), t.get('name', '')))
        return filtered
    
    def create_template_checkboxes(self):
        """チェックボックスリスト作成（折り畳み可能）"""
        # クリア
        for widget in self.template_frame.winfo_children():
            widget.destroy()
        
        self.template_vars = []
        
        # カテゴリごとにグループ化
        categorized = {}
        for template in self.all_templates:
            category = template.get('category', 'その他')
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(template)
        
        # カテゴリごとに表示
        for category in sorted(categorized.keys()):
            templates = categorized[category]
            
            # カテゴリの展開状態
            if category not in self.category_states:
                self.category_states[category] = True
            
            # カテゴリヘッダー
            header_frame = tk.Frame(self.template_frame, bg='lightblue', cursor='hand2')
            header_frame.pack(fill='x', pady=(5, 0))
            
            icon = '▼' if self.category_states[category] else '▶'
            icon_label = tk.Label(
                header_frame,
                text=icon,
                font=('Noto Sans JP', 10),
                bg='lightblue',
                width=2
            )
            icon_label.pack(side='left')
            
            category_label = tk.Label(
                header_frame,
                text=f"{category} ({len(templates)})",
                font=('Noto Sans JP', 10, 'bold'),
                bg='lightblue',
                anchor='w'
            )
            category_label.pack(side='left', fill='x', expand=True, padx=5)
            
            # トグル
            def toggle_category(cat=category):
                self.category_states[cat] = not self.category_states[cat]
                self.create_template_checkboxes()
            
            header_frame.bind('<Button-1>', lambda e, cat=category: toggle_category(cat))
            icon_label.bind('<Button-1>', lambda e, cat=category: toggle_category(cat))
            category_label.bind('<Button-1>', lambda e, cat=category: toggle_category(cat))
            
            # チェックボックス（展開時のみ）
            if self.category_states[category]:
                checkboxes_frame = tk.Frame(self.template_frame, bg='lightgray')
                checkboxes_frame.pack(fill='x')
                
                for template in templates:
                    var = tk.BooleanVar(value=False)
                    self.template_vars.append((var, template))
                    
                    style = ttk.Style()
                    style.configure('Template.TCheckbutton', 
                                  background='lightgray',
                                  font=('Noto Sans JP', 10))
                    
                    cb = ttk.Checkbutton(
                        checkboxes_frame,
                        text=template['name'],
                        variable=var,
                        style='Template.TCheckbutton',
                        command=lambda t=template: self.show_template_detail(t)
                    )
                    cb.pack(anchor='w', padx=(20, 0), pady=1, fill='x')
        
        # 全ての子ウィジェットにマウスホイールをバインド
        if hasattr(self, 'bind_template_mousewheel'):
            self.bind_template_mousewheel()
    
    def show_template_detail(self, template: Dict):
        """テンプレート詳細表示"""
        self.detail_text.config(state='normal')
        self.detail_text.delete('1.0', tk.END)
        
        details = f"名前: {template['name']}\n\n"
        details += f"カテゴリ: {template['category']}\n\n"
        
        if 'subscription' in template and template['subscription']:
            sub_id = template['subscription']
            # ARMリソースID形式の場合はGUID部分のみ抽出
            if sub_id.startswith('/subscriptions/'):
                sub_id = sub_id.split('/')[-1]
            details += f"サブスクリプション:\n{sub_id}\n"
        
        if 'storage_account' in template and template['storage_account']:
            details += f"ストレージアカウント: {template['storage_account']}\n\n"
        
        if 'description' in template:
            details += f"説明:\n{template['description']}\n\n"
        
        if 'container' in template and template['container']:
            details += f"コンテナ: {template['container']}\n\n"
        
        details += f"パスパターン:\n{template['path_pattern']}\n\n"
        
        details += "プレースホルダー:\n"
        for ph_name, ph_config in template.get('placeholders', {}).items():
            label = ph_config.get('label', ph_name)
            ph_type = ph_config.get('type', 'unknown')
            details += f"  • {label} ({ph_name}): {ph_type}\n"
        
        if 'example_paths' in template:
            details += "\nパス例:\n"
            for example in template['example_paths'][:3]:
                details += f"  {example}\n"
        
        self.detail_text.insert('1.0', details)
        self.detail_text.config(state='disabled')
    
    def open_template_editor(self):
        """テンプレート管理画面を開く"""
        self.controller.show_frame('TemplateEditorScreen')
    
    def refresh_templates(self):
        """テンプレート一覧を再読み込み"""
        self.all_templates = self.get_filtered_templates_list()
        self.create_template_checkboxes()
        messagebox.showinfo("更新完了", "テンプレート一覧を更新しました")
    
    def go_next(self):
        """次へ"""
        # 選択されたテンプレートを取得
        selected_templates = [
            template for var, template in self.template_vars if var.get()
        ]
        
        if not selected_templates:
            logger.warning("テンプレートが選択されていません")
            messagebox.showwarning("警告", "テンプレートを選択してください")
            return
        
        self.controller.selected_templates = selected_templates
        logger.info(f"選択されたテンプレート: {[t['name'] for t in selected_templates]}")
        
        # 初期化
        self.controller.current_template_index = 0
        self.controller.template_expansion_settings = {}
        
        # 展開設定画面へ
        self.controller.show_frame('TemplateExpansionScreen')
