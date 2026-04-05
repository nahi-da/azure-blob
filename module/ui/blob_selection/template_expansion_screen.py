"""
テンプレート展開設定画面モジュール

プレースホルダーの展開条件を設定し、Blob検索を実行する。
"""

import copy
import itertools
import re
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Dict, List, Optional

from ...core.logging_manager import logger
from ...template_module.matcher import ConditionMatcher
from ...template_module.optimizer import PrefixOptimizer
from ...ui_text.blob_texts import template_expansion_texts

if TYPE_CHECKING:
    from azure_blob_rehydrator import AzureBlobRehydratorApp


class TemplateExpansionScreen(tk.Frame):
    """プレースホルダー展開設定画面"""
    
    def __init__(self, parent, controller: "AzureBlobRehydratorApp"):
        super().__init__(parent)
        self.controller = controller
        
        # タイトル
        self.title_label = ttk.Label(self, text=template_expansion_texts.title, style='Title.TLabel')
        self.title_label.pack(pady=10)
        
        # テンプレート進捗表示
        self.progress_label = tk.Label(
            self,
            text="",
            font=controller.default_font,
            fg='blue'
        )
        self.progress_label.pack(pady=5)
        
        # 説明
        desc = tk.Label(
            self,
            text=template_expansion_texts.subtitle,
            font=controller.default_font
        )
        desc.pack(pady=5)
        
        # ストレージアカウント・コンテナ設定
        settings_frame = ttk.LabelFrame(self, text=template_expansion_texts.match_frame_title, padding=10)
        settings_frame.pack(fill="x", padx=20, pady=10)
        
        # サブスクリプション
        tk.Label(settings_frame, text=template_expansion_texts.subscription_id_label, font=controller.default_font).grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        self.subscription_var = tk.StringVar()
        self.subscription_entry = ttk.Entry(settings_frame, textvariable=self.subscription_var, width=50, state='readonly')
        self.subscription_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # ストレージアカウント
        tk.Label(settings_frame, text=template_expansion_texts.storage_account_label, font=controller.default_font).grid(
            row=1, column=0, sticky="w", padx=5, pady=5
        )
        self.storage_account_var = tk.StringVar()
        self.storage_entry = ttk.Entry(settings_frame, textvariable=self.storage_account_var, width=50, state='readonly')
        self.storage_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # コンテナ
        self.container_label = tk.Label(settings_frame, text=template_expansion_texts.container_label, font=controller.default_font)
        self.container_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        
        self.container_var = tk.StringVar()
        self.container_entry = ttk.Entry(settings_frame, textvariable=self.container_var, width=50)
        self.container_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        self.container_info_label = tk.Label(settings_frame, text="", font=('Noto Sans JP', 9), fg='gray')
        self.container_info_label.grid(row=3, column=1, sticky="w", padx=5, pady=(0, 5))
        
        settings_frame.grid_columnconfigure(1, weight=1)
        
        # プレースホルダー設定エリア（スクロール可能）
        self.placeholder_frame = ttk.LabelFrame(self, text=template_expansion_texts.placeholder_label, padding=10)
        self.placeholder_frame.pack(fill="both", expand=True, padx=20, pady=10)

        
        # Canvas + Scrollbar
        self.canvas = tk.Canvas(self.placeholder_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.placeholder_frame, orient="vertical", command=self.canvas.yview)
        self.placeholder_container = tk.Frame(self.canvas)
        
        self.placeholder_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.placeholder_container, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # マウススクロール対応
        def on_mousewheel(event):
            bbox = self.canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = self.canvas.winfo_height()
                if content_height > canvas_height:
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Canvas、placeholder_container、およびその子ウィジェットすべてにバインド
        def bind_mousewheel_recursive(widget):
            """ウィジェットとその子ウィジェットすべてにマウススクロールをバインド"""
            widget.bind("<MouseWheel>", on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel_recursive(child)
        
        self.canvas.bind("<MouseWheel>", on_mousewheel)
        bind_mousewheel_recursive(self.placeholder_container)
        
        # プレースホルダーウィジェット作成後に再バインドするための関数を保存
        self.bind_mousewheel_to_new_widgets = lambda: bind_mousewheel_recursive(self.placeholder_container)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ボタンフレーム
        button_frame = tk.Frame(self)
        button_frame.pack(pady=20)
        
        # 戻るボタン
        back_button = ttk.Button(button_frame, text=template_expansion_texts.back_button,
                                command=self.go_back, width=15)
        back_button.pack(side="left", padx=5)
        
        # 次へボタン
        self.next_button = ttk.Button(button_frame, text=template_expansion_texts.expand_button,
                                      command=self.go_next, width=20)
        self.next_button.pack(side="left", padx=5)
        
        # データストレージ
        self.placeholder_widgets = {}  # 非推奨：後方互換性のため残す
        self.current_template: Optional[Dict] = None
        self.value_sets = []  # 複数の値セット（マトリクス展開用）
        self.current_value_set_index = 0  # 現在編集中の値セット
        self.saved_value_sets = {}  # テンプレートごとの値セット保存 {template_index: value_sets}
    
    def go_back(self):
        """前の画面に戻る"""
        # 現在の値セットをウィジェットから収集して保存
        if self.current_template:
            idx = self.controller.current_template_index
            for set_idx in range(len(self.value_sets)):
                expansions = {}
                for ph_name in self.current_template.get('placeholders', {}).keys():
                    widget_key = f"set_{set_idx}_{ph_name}"
                    widget_data = self.placeholder_widgets.get(widget_key)
                    if widget_data and 'get_value' in widget_data:
                        expansions[ph_name] = widget_data['get_value']()
                self.value_sets[set_idx] = expansions
            # ディープコピーで保存
            self.saved_value_sets[idx] = copy.deepcopy(self.value_sets)
        
        if self.controller.current_template_index == 0:
            # 1個目 → テンプレート選択画面
            # 履歴をクリア（テンプレート再選択時の想定外動作を防ぐ）
            self.saved_value_sets.clear()
            self.value_sets = []
            self.controller.show_frame('TemplateSelectionScreen')
        else:
            # 2個目以降 → 前の展開設定画面
            self.controller.current_template_index -= 1
            self.controller.show_frame('TemplateExpansionScreen')
    
    def on_show(self):
        """画面表示時"""
        # 現在のテンプレート取得
        if not self.controller.selected_templates:
            return
        
        idx = self.controller.current_template_index
        if idx >= len(self.controller.selected_templates):
            return
        
        self.current_template = self.controller.selected_templates[idx]
        
        # 値セットを復元または初期化（テンプレートごとに独立）
        if idx in self.saved_value_sets:
            # 保存済みの値セットを復元（ディープコピー）
            self.value_sets = copy.deepcopy(self.saved_value_sets[idx])
        else:
            # 新規の場合は初期化
            self.value_sets = [{}]
        self.current_value_set_index = 0
        
        # 進捗表示更新
        total = len(self.controller.selected_templates)
        current = idx + 1
        self.progress_label.config(
            text=f"テンプレート {current} / {total}: {self.current_template['name']}"
        )
        
        # 次へボタンのテキスト更新
        if current < total:
            self.next_button.config(text=f"次へ → ({current}/{total})")
        else:
            self.next_button.config(text=template_expansion_texts.expand_button)
        
        # サブスクリプション・ストレージアカウント設定
        self.subscription_var.set(self.current_template.get('subscription', ''))
        self.storage_account_var.set(self.current_template.get('storage_account', ''))
        
        # コンテナ設定
        container = self.current_template.get('container')
        if container:
            self.container_var.set(container)
            if '{' in container:
                self.container_entry.config(state='readonly')
                self.container_info_label.config(text=template_expansion_texts.container_info_placeholder)
            else:
                self.container_entry.config(state='readonly')
                self.container_info_label.config(text=template_expansion_texts.container_info_fixed)
        else:
            self.container_var.set('')
            self.container_entry.config(state='normal')
            self.container_info_label.config(text=template_expansion_texts.container_info_input)
        
        # プレースホルダー設定UI生成
        self.create_placeholder_widgets()
        
        # ウィジェット生成後、コンテナのサイズを更新
        self.placeholder_container.update_idletasks()
        self.update_idletasks()
        
        # コンテナの必要幅を取得してcanvas_frameに設定
        required_width = self.placeholder_container.winfo_reqwidth()
        self.canvas.itemconfig(self.canvas_frame, width=required_width)
        self.canvas.config(width=self.placeholder_container.winfo_reqwidth())
        
        # Canvasのスクロール領域を更新
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    
    def create_placeholder_widgets(self):
        """プレースホルダー設定UI生成（マトリクス展開モード対応）"""
        # 既存ウィジェットクリア
        for widget in self.placeholder_container.winfo_children():
            widget.destroy()
        
        self.placeholder_widgets.clear()
        
        if not self.current_template:
            return
        
        template = self.current_template
        
        # 値セット追加ボタンエリア
        add_set_frame = tk.Frame(self.placeholder_container)
        add_set_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        
        ttk.Button(
            add_set_frame,
            text=template_expansion_texts.add_value_set_button,
            command=self.add_value_set,
            width=20
        ).pack(side="left", padx=5)
        
        tk.Label(
            add_set_frame,
            text=template_expansion_texts.value_set_note,
            font=('Noto Sans JP', 9),
            fg='gray'
        ).pack(side="left", padx=10)
        
        # 全プレースホルダーを取得
        all_placeholders = {}
        
        # コンテナ名のプレースホルダーを抽出
        container_pattern = template.get('container', '')
        if container_pattern:
            container_placeholders = re.findall(r'\{([^}]+)\}', container_pattern)
            for ph_name in container_placeholders:
                if ph_name in template.get('placeholders', {}):
                    all_placeholders[ph_name] = template['placeholders'][ph_name]
        
        # パスのプレースホルダーを追加
        for ph_name, ph_config in template.get('placeholders', {}).items():
            if ph_name not in all_placeholders:
                all_placeholders[ph_name] = ph_config
        
        # 各値セットのUI生成
        row = 1
        for set_idx, value_set in enumerate(self.value_sets):
            row = self.create_value_set_ui(row, set_idx, all_placeholders, value_set)
        
        # 生成パターン数プレビュー
        preview_frame = tk.Frame(self.placeholder_container, relief=tk.GROOVE, borderwidth=2, bg='#f0f0f0')
        preview_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        
        preview_label = tk.Label(
            preview_frame,
            text=self.get_pattern_preview(),
            font=('Noto Sans JP', 9),
            bg='#f0f0f0',
            justify=tk.LEFT,
            anchor="w"
        )
        preview_label.pack(padx=10, pady=10, fill="x")
        
        # 定期的にプレビューを更新
        self.placeholder_container.after(500, lambda: self.update_pattern_preview(preview_label))
        
        # 全ての子ウィジェットにマウスホイールをバインド
        if hasattr(self, 'bind_mousewheel_to_new_widgets'):
            self.bind_mousewheel_to_new_widgets()
    
    def create_value_set_ui(self, start_row: int, set_idx: int, all_placeholders: Dict, value_set: Dict) -> int:
        """1つの値セットのUI生成
        
        Args:
            start_row: 開始行
            set_idx: 値セットのインデックス
            all_placeholders: 全プレースホルダー定義
            value_set: 値セットデータ
            
        Returns:
            次の開始行番号
        """
        row = start_row
        
        # 値セットヘッダー
        header_frame = tk.Frame(self.placeholder_container, relief=tk.RAISED, borderwidth=2, bg='#e0e0e0')
        header_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        row += 1
        
        header_label = tk.Label(
            header_frame,
            text=f"■ 値セット{set_idx + 1}",
            font=('Noto Sans JP', 10, 'bold'),
            bg='#e0e0e0'
        )
        header_label.pack(side="left", padx=10, pady=5)
        
        # 削除ボタン（値セットが2つ以上ある場合のみ表示）
        if len(self.value_sets) > 1:
            delete_button = ttk.Button(
                header_frame,
                text=template_expansion_texts.delete_button_text,
                command=lambda idx=set_idx: self.delete_value_set(idx),
                width=8
            )
            delete_button.pack(side="right", padx=10, pady=5)
        
        # 各プレースホルダーのUI生成
        for ph_name, ph_config in all_placeholders.items():
            row_result = self.create_placeholder_row_for_set(row, set_idx, ph_name, ph_config, value_set)
            row = row_result
        
        # 区切り線
        separator = ttk.Separator(self.placeholder_container, orient='horizontal')
        separator.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        row += 1
        
        return row
    
    def create_placeholder_row_for_set(self, row: int, set_idx: int, ph_name: str, ph_config: Dict, value_set: Dict) -> int:
        """値セット用のプレースホルダー1行分のUI生成
        
        Args:
            row: 配置行
            set_idx: 値セットインデックス
            ph_name: プレースホルダー名
            ph_config: プレースホルダー設定
            value_set: 値セットデータ
            
        Returns:
            次の行番号
        """
        frame_left = tk.Frame(self.placeholder_container, relief=tk.FLAT, borderwidth=1)
        frame_left.grid(row=row, column=0, sticky="e", padx=5, pady=5)
        frame_right = tk.Frame(self.placeholder_container, relief=tk.FLAT, borderwidth=1)
        frame_right.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        
        # ラベル
        label_text = ph_config.get('label', ph_name)
        label = tk.Label(frame_left, text=f"  {label_text}:", font=self.controller.default_font, anchor="e", justify=tk.RIGHT)
        label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        
        # 展開タイプ選択
        ph_type = ph_config.get('type', 'wildcard')
        saved_value = value_set.get(ph_name, {})
        if isinstance(saved_value, dict):
            saved_type = saved_value.get('type', ph_type)
        else:
            saved_type = ph_type
        
        type_var = tk.StringVar(value=saved_type)
        
        type_label = ttk.Label(
            frame_left,
            text=saved_type
        )
        type_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # 設定エリア
        settings_frame = tk.Frame(frame_right)
        settings_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        frame_right.grid_columnconfigure(0, weight=1)
        
        # ウィジェット保存（値セットごと）
        widget_key = f"set_{set_idx}_{ph_name}"
        self.placeholder_widgets[widget_key] = {
            'type_var': type_var,
            'settings_frame': settings_frame,
            'config': ph_config,
            'set_idx': set_idx,
            'ph_name': ph_name
        }
        
        # 初期設定UI生成
        self.update_settings_ui_for_set(set_idx, ph_name, saved_value)
        
        # 新しく作成したウィジェットにもマウスホイールをバインド
        if hasattr(self, 'bind_mousewheel_to_new_widgets'):
            self.placeholder_container.after(100, self.bind_mousewheel_to_new_widgets)
        
        return row + 1
    
    def add_value_set(self):
        """値セットを追加"""
        # 現在の値セットをウィジェットから収集
        if self.current_template:
            for set_idx in range(len(self.value_sets)):
                expansions = {}
                for ph_name in self.current_template.get('placeholders', {}).keys():
                    widget_key = f"set_{set_idx}_{ph_name}"
                    widget_data = self.placeholder_widgets.get(widget_key)
                    if widget_data and 'get_value' in widget_data:
                        expansions[ph_name] = widget_data['get_value']()
                self.value_sets[set_idx] = expansions
        
        # 新しい空の値セットを追加
        self.value_sets.append({})
        self.create_placeholder_widgets()
        
        # スクロール領域を更新
        self.placeholder_container.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def delete_value_set(self, set_idx: int):
        """値セットを削除"""
        if len(self.value_sets) <= 1:
            logger.warning("値セット削除: 最低1つの値セットが必要です")
            messagebox.showwarning("警告", "最低1つの値セットが必要です")
            return
        
        result = messagebox.askyesno("確認", f"値セット{set_idx + 1}を削除しますか？")
        if result:
            # 現在の値セットをウィジェットから収集（削除対象以外）
            if self.current_template:
                for idx in range(len(self.value_sets)):
                    if idx == set_idx:
                        continue  # 削除対象はスキップ
                    expansions = {}
                    for ph_name in self.current_template.get('placeholders', {}).keys():
                        widget_key = f"set_{idx}_{ph_name}"
                        widget_data = self.placeholder_widgets.get(widget_key)
                        if widget_data and 'get_value' in widget_data:
                            expansions[ph_name] = widget_data['get_value']()
                    self.value_sets[idx] = expansions
            
            # 値セットを削除
            del self.value_sets[set_idx]
            self.create_placeholder_widgets()
            
            # スクロール領域を更新
            self.placeholder_container.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def on_type_change_for_set(self, set_idx: int, ph_name: str):
        """値セット用の展開タイプ変更時"""
        widget_key = f"set_{set_idx}_{ph_name}"
        widget_data = self.placeholder_widgets.get(widget_key)
        if not widget_data:
            return
        
        # 値セットのデータをクリア
        if set_idx < len(self.value_sets):
            if ph_name in self.value_sets[set_idx]:
                del self.value_sets[set_idx][ph_name]
        
        self.update_settings_ui_for_set(set_idx, ph_name, {})
    
    def update_settings_ui_for_set(self, set_idx: int, ph_name: str, saved_value: Dict):
        """値セット用の設定UIを更新"""
        widget_key = f"set_{set_idx}_{ph_name}"
        widget_data = self.placeholder_widgets.get(widget_key)
        if not widget_data:
            return
        
        settings_frame = widget_data['settings_frame']
        ph_config = widget_data['config']
        ph_type = widget_data['type_var'].get()
        
        # 既存ウィジェットクリア
        for widget in settings_frame.winfo_children():
            widget.destroy()
        
        # タイプ別UI生成（saved_valueを使って復元）
        if ph_type == 'text':
            self._create_text_ui(settings_frame, ph_config, saved_value, widget_data)
            
        elif ph_type == 'numeric':
            self._create_numeric_ui(settings_frame, ph_config, saved_value, widget_data)
            
        elif ph_type == 'enum':
            self._create_enum_ui(settings_frame, ph_config, saved_value, widget_data, set_idx)
            
        elif ph_type == 'regex':
            self._create_regex_ui(settings_frame, ph_config, saved_value, widget_data)
    
    def _create_text_ui(self, settings_frame, ph_config, saved_value, widget_data):
        """テキストUI生成（ヘルパーメソッド）"""
        tk.Label(settings_frame, text=template_expansion_texts.value_label).pack(side="left", padx=(0, 5))
        # テンプレートのデフォルト値を初期値として使用
        template_default = ph_config.get('default_value', '')
        saved_val = saved_value.get('value', template_default) if isinstance(saved_value, dict) else template_default
        value_var = tk.StringVar(value=saved_val)
        entry = ttk.Entry(settings_frame, textvariable=value_var, width=20)
        entry.pack(side="left", padx=(0, 10))
        
        # マッチモード選択
        tk.Label(settings_frame, text=template_expansion_texts.match_label).pack(side="left")
        match_mode_default = ph_config.get('match_mode', 'exact')  # テンプレートのデフォルト
        saved_match_mode = saved_value.get('match_mode', match_mode_default) if isinstance(saved_value, dict) else match_mode_default
        match_mode_var = tk.StringVar(value=saved_match_mode)
        exact_radio = ttk.Radiobutton(settings_frame, text=template_expansion_texts.match_type_exact, variable=match_mode_var, value='exact')
        exact_radio.pack(side="left", padx=(0, 5))
        partial_radio = ttk.Radiobutton(settings_frame, text=template_expansion_texts.match_type_partial, variable=match_mode_var, value='partial')
        partial_radio.pack(side="left")
        
        widget_data['value_var'] = value_var
        widget_data['match_mode_var'] = match_mode_var
        widget_data['get_value'] = lambda: {
            'type': 'text',
            'value': widget_data['value_var'].get(),
            'match_mode': widget_data['match_mode_var'].get()
        }
    
    def _create_numeric_ui(self, settings_frame, ph_config, saved_value, widget_data):
        """数値範囲UI生成（ヘルパーメソッド）"""
        saved_mode = saved_value.get('mode', 'fixed') if isinstance(saved_value, dict) else 'fixed'
        mode_var = tk.StringVar(value=saved_mode)
        
        fixed_radio = ttk.Radiobutton(settings_frame, text=template_expansion_texts.fixed_value_label, variable=mode_var, value='fixed')
        fixed_radio.pack(side="left")
        
        template_min = ph_config.get('min', '')
        template_max = ph_config.get('max', '')
        
        saved_fixed = str(saved_value.get('fixed', template_min)) if isinstance(saved_value, dict) else str(template_min)
        fixed_var = tk.StringVar(value=saved_fixed if saved_fixed else '')
        fixed_entry = ttk.Entry(settings_frame, textvariable=fixed_var, width=8)
        fixed_entry.pack(side="left", padx=(0, 10))
        
        range_radio = ttk.Radiobutton(settings_frame, text=template_expansion_texts.range_label, variable=mode_var, value='range')
        range_radio.pack(side="left")
        
        saved_start = str(saved_value.get('start', template_min)) if isinstance(saved_value, dict) else str(template_min)
        start_var = tk.StringVar(value=saved_start if saved_start else '')
        tk.Label(settings_frame, text=template_expansion_texts.start_label).pack(side="left", padx=(5, 0))
        start_entry = ttk.Entry(settings_frame, textvariable=start_var, width=6)
        start_entry.pack(side="left", padx=(0, 5))
        
        saved_end = str(saved_value.get('end', template_max)) if isinstance(saved_value, dict) else str(template_max)
        end_var = tk.StringVar(value=saved_end if saved_end else '')
        tk.Label(settings_frame, text=template_expansion_texts.end_label).pack(side="left")
        end_entry = ttk.Entry(settings_frame, textvariable=end_var, width=6)
        end_entry.pack(side="left", padx=(0, 5))
        
        saved_step = str(saved_value.get('step', 1)) if isinstance(saved_value, dict) else "1"
        step_var = tk.StringVar(value=saved_step)
        tk.Label(settings_frame, text=template_expansion_texts.step_label_short).pack(side="left")
        step_entry = ttk.Entry(settings_frame, textvariable=step_var, width=4)
        step_entry.pack(side="left")
        
        widget_data['mode_var'] = mode_var
        widget_data['fixed_var'] = fixed_var
        widget_data['start_var'] = start_var
        widget_data['end_var'] = end_var
        widget_data['step_var'] = step_var
        
        padding = ph_config.get('padding', 0)
        
        def get_numeric_value():
            if widget_data['mode_var'].get() == 'fixed':
                try:
                    fixed_val = int(widget_data['fixed_var'].get())
                    return {
                        'type': 'numeric',
                        'mode': 'fixed',
                        'fixed': fixed_val,
                        'padding': padding
                    }
                except ValueError:
                    return {'type': 'numeric', 'mode': 'fixed', 'padding': padding}
            else:
                try:
                    start = int(widget_data['start_var'].get()) if widget_data['start_var'].get() else None
                    end = int(widget_data['end_var'].get()) if widget_data['end_var'].get() else None
                    step = int(widget_data['step_var'].get()) if widget_data['step_var'].get() else 1
                    
                    result = {'type': 'numeric', 'mode': 'range', 'padding': padding, 'step': step}
                    if start is not None:
                        result['start'] = start
                    if end is not None:
                        result['end'] = end
                    return result
                except ValueError:
                    return {'type': 'numeric', 'mode': 'range', 'padding': padding}
        
        widget_data['get_value'] = get_numeric_value
    
    def _create_enum_ui(self, settings_frame, ph_config, saved_value, widget_data, set_idx=0):
        """列挙型UI生成（ヘルパーメソッド）"""
        options = ph_config.get('options', [])
        multiple = ph_config.get('multiple', False)
        
        if not options:
            tk.Label(settings_frame, text=template_expansion_texts.option_undefined, fg="red").pack(side="left")
            widget_data['get_value'] = lambda: {'type': 'enum', 'multiple': multiple}
            return
        
        tk.Label(settings_frame, text=template_expansion_texts.selection_label).pack(side="left", padx=(0, 5))
        
        if multiple:
            # 複数選択モード: カスタムドロップダウン
            saved_selected = saved_value.get('selected_values', []) if isinstance(saved_value, dict) else []
            
            # Comboboxライクなコンテナ（EntryとButtonの組み合わせ）
            dropdown_container = tk.Frame(settings_frame, relief='solid', borderwidth=1)
            dropdown_container.pack(side="left", padx=(0, 5))
            
            # 選択状態を保持する辞書
            selection_vars = {}
            for opt in options:
                selection_vars[opt] = tk.BooleanVar(value=(opt in saved_selected))
            
            # 選択された項目を表示するEntry（readonly）
            display_var = tk.StringVar(value=self._format_selected_items(saved_selected))
            selected_entry = tk.Entry(
                dropdown_container, 
                textvariable=display_var, 
                state="readonly",
                width=20,
                relief='flat',
                bg='white',
                readonlybackground='white',
                borderwidth=0,
                highlightthickness=0
            )
            selected_entry.pack(side="left", padx=1, pady=1)
            
            # 下矢印ボタン（Combobox風のコンパクトなサイズ）
            arrow_button = tk.Button(
                dropdown_container,
                text="▼",
                relief='flat',
                bg='#f0f0f0',
                activebackground='#e0e0e0',
                borderwidth=0,
                padx=4,
                pady=0,
                cursor='hand2'
            )
            arrow_button.pack(side="left", padx=0, pady=1, fill='y')
            
            # ドロップダウンメニューを表示する関数
            def show_dropdown_menu(event=None):
                popup = tk.Toplevel(settings_frame)
                popup.overrideredirect(True)  # タイトルバーを非表示
                popup.attributes('-topmost', True)
                
                # ボタンの位置を取得してポップアップを配置
                x = dropdown_container.winfo_rootx()
                y = dropdown_container.winfo_rooty() + dropdown_container.winfo_height()
                popup.geometry(f"+{x}+{y}")
                
                # メインフレーム（境界線とシャドウ効果）
                main_frame = tk.Frame(popup, relief='solid', borderwidth=1, bg='#f0f0f0')
                main_frame.pack(fill='both', expand=True)
                
                inner_frame = tk.Frame(main_frame, bg='#f0f0f0')
                inner_frame.pack(fill='both', expand=True, padx=1, pady=1)
                
                # スクロール可能なフレーム
                canvas = tk.Canvas(inner_frame, height=min(300, len(options) * 25 + 40), width=250, 
                                  highlightthickness=0, bg='#f0f0f0')
                scrollbar = ttk.Scrollbar(inner_frame, orient="vertical", command=canvas.yview)
                scrollable_frame = tk.Frame(canvas, bg='#f0f0f0')
                
                scrollable_frame.bind(
                    "<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
                
                canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                
                # チェックボックスを配置
                for opt in options:
                    cb = ttk.Checkbutton(scrollable_frame, text=opt, variable=selection_vars[opt])
                    cb.pack(anchor="w", padx=10, pady=2)
                
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
                
                # OKボタン
                button_frame = tk.Frame(inner_frame, bg='#f0f0f0')
                button_frame.pack(pady=5)
                
                def on_ok():
                    selected = [opt for opt, var in selection_vars.items() if var.get()]
                    display_var.set(self._format_selected_items(selected))
                    popup.destroy()
                
                def on_cancel():
                    popup.destroy()
                
                ttk.Button(button_frame, text="OK", command=on_ok, width=10).pack(side="left", padx=5)
                ttk.Button(button_frame, text=template_expansion_texts.cancel_button_text, command=on_cancel, width=10).pack(side="left", padx=5)
                
                # ポップアップ外をクリックしたら閉じる（FocusOutイベントを使用）
                def on_focus_out(event):
                    # ポップアップが存在しない場合は何もしない
                    if not popup.winfo_exists():
                        return
                    
                    # 現在フォーカスを持っている要素を取得
                    try:
                        focused_widget = popup.focus_get()
                    except:
                        # フォーカスを取得できない場合は閉じる
                        popup.destroy()
                        return
                    
                    # フォーカスがNoneの場合は閉じる
                    if focused_widget is None:
                        popup.destroy()
                        return
                    
                    # フォーカスがポップアップ内の要素かチェック
                    widget = focused_widget
                    while widget:
                        if widget == popup:
                            # ポップアップ内の要素なので閉じない
                            return
                        try:
                            widget = widget.master
                        except:
                            break
                    
                    # ポップアップ外の要素にフォーカスが移動したので閉じる
                    popup.destroy()
                
                popup.bind('<FocusOut>', on_focus_out)
                
                # ポップアップを最前面に（grab_setは使用しない）
                popup.focus_force()
            
            # ボタンクリックでドロップダウンを表示
            arrow_button.config(command=show_dropdown_menu)
            # Entryクリックでもドロップダウンを表示
            selected_entry.bind('<Button-1>', show_dropdown_menu)
            
            widget_data['selection_vars'] = selection_vars
            widget_data['get_value'] = lambda: {
                'type': 'enum',
                'multiple': True,
                'selected_values': [opt for opt, var in widget_data['selection_vars'].items() if var.get()]
            }
        else:
            # 単一選択モード: Combobox
            default = ph_config.get('default', '')
            saved_selected = saved_value.get('selected_value', default) if isinstance(saved_value, dict) else default
            if saved_selected not in options:
                saved_selected = options[0] if options else ''
            selected_var = tk.StringVar(value=saved_selected)
            combo = ttk.Combobox(settings_frame, textvariable=selected_var, values=options, state='readonly', width=20)
            combo.pack(side="left")
            widget_data['selected_var'] = selected_var
            widget_data['get_value'] = lambda: {
                'type': 'enum',
                'multiple': False,
                'selected_value': widget_data['selected_var'].get()
            }
    
    def _format_selected_items(self, selected):
        """選択された項目を表示用にフォーマット"""
        if not selected:
            return "（未選択）"
        elif len(selected) <= 3:
            return ", ".join(selected)
        else:
            return f"{', '.join(selected[:3])}... 他{len(selected) - 3}件"
    
    def _create_regex_ui(self, settings_frame, ph_config, saved_value, widget_data):
        """正規表現UI生成（ヘルパーメソッド）"""
        tk.Label(settings_frame, text=template_expansion_texts.pattern_label).pack(side="left", padx=(0, 5))
        
        # テンプレートで定義されたデフォルトパターンを取得
        default_pattern = ph_config.get('pattern', '')
        saved_pattern = saved_value.get('pattern', default_pattern) if isinstance(saved_value, dict) else default_pattern
        
        pattern_var = tk.StringVar(value=saved_pattern)
        entry = ttk.Entry(settings_frame, textvariable=pattern_var, width=30)
        entry.pack(side="left", padx=(0, 5))
        
        # 検証ボタン
        def validate_regex():
            pattern = pattern_var.get()
            try:
                re.compile(pattern)
                messagebox.showinfo("検証成功", "正規表現パターンは正しい形式です")
            except re.error as e:
                logger.warning(f"regexパターン検証エラー: {str(e)} - pattern={pattern}")
                messagebox.showerror("検証エラー", f"正規表現パターンにエラーがあります:\n{str(e)}")
        
        validate_btn = ttk.Button(settings_frame, text=template_expansion_texts.validate_button, command=validate_regex, width=8)
        validate_btn.pack(side="left")
        
        widget_data['pattern_var'] = pattern_var
        widget_data['get_value'] = lambda: {
            'type': 'regex',
            'pattern': widget_data['pattern_var'].get()
        }
    
    def get_pattern_preview(self) -> str:
        """生成されるパターン数のプレビューテキストを取得"""
        try:
            total_patterns = 0
            details = []
            
            for set_idx, value_set in enumerate(self.value_sets):
                patterns = self._count_patterns_for_set(set_idx)
                total_patterns += patterns
                if patterns > 0:
                    details.append(f"  - 値セット{set_idx + 1}: {patterns}件")
            
            preview_text = f"生成されるパターン: {total_patterns}件"
            if details:
                preview_text += "\n" + "\n".join(details)
            
            if total_patterns > 1000:
                preview_text += "\n⚠ パターン数が多いため、検索に時間がかかる可能性があります"
            
            return preview_text
        except Exception as e:
            return f"プレビュー生成エラー: {str(e)}"
    
    def _count_patterns_for_set(self, set_idx: int) -> int:
        """指定された値セットのパターン数を計算"""
        if set_idx >= len(self.value_sets):
            return 0
        
        value_set = self.value_sets[set_idx]
        if not self.current_template:
            return 0
        
        # 各プレースホルダーの値数を取得
        count = 1
        for ph_name in self.current_template.get('placeholders', {}).keys():
            widget_key = f"set_{set_idx}_{ph_name}"
            widget_data = self.placeholder_widgets.get(widget_key)
            if not widget_data or 'get_value' not in widget_data:
                continue
            
            expansion = widget_data['get_value']()
            exp_type = expansion.get('type')
            
            if exp_type == 'enum':
                multiple = expansion.get('multiple', False)
                if multiple:
                    count *= len(expansion.get('selected_values', []))
                # 単一選択の場合は常に1
            elif exp_type == 'numeric':
                mode = expansion.get('mode', 'fixed')
                if mode == 'range':
                    start = expansion.get('start', 0)
                    end = expansion.get('end', 0)
                    step = expansion.get('step', 1)
                    if step > 0:
                        count *= max(1, (end - start) // step + 1)
        
        return count
    
    def update_pattern_preview(self, label_widget):
        """パターンプレビューを定期的に更新"""
        try:
            if label_widget.winfo_exists():
                label_widget.config(text=self.get_pattern_preview())
                self.placeholder_container.after(500, lambda: self.update_pattern_preview(label_widget))
        except:
            pass
    
    def on_type_change(self, ph_name: str):
        """展開タイプ変更時"""
        self.update_settings_ui(ph_name)
    
    def update_settings_ui(self, ph_name: str):
        """設定UIを更新"""
        widget_data = self.placeholder_widgets[ph_name]
        settings_frame = widget_data['settings_frame']
        ph_config = widget_data['config']
        ph_type = widget_data['type_var'].get()
        
        # 既存ウィジェットクリア
        for widget in settings_frame.winfo_children():
            widget.destroy()
        
        # タイプ別UI生成
        if ph_type == 'wildcard':
            tk.Label(settings_frame, text=template_expansion_texts.all_match, fg="gray").pack(side="left")
            widget_data['get_value'] = lambda: {'type': 'wildcard'}
            
        elif ph_type == 'fixed':
            tk.Label(settings_frame, text=template_expansion_texts.fixed_value_label).pack(side="left", padx=(0, 5))
            value_var = tk.StringVar()
            entry = ttk.Entry(settings_frame, textvariable=value_var, width=20)
            entry.pack(side="left")
            widget_data['value_var'] = value_var
            widget_data['get_value'] = lambda: {
                'type': 'fixed',
                'value': widget_data['value_var'].get()
            }
            
        elif ph_type == 'list':
            default_values = ph_config.get('default_values', [])
            
            if default_values:
                tk.Label(settings_frame, text=template_expansion_texts.selection_label).pack(side="left", padx=(0, 5))
                
                check_vars = {}
                for value in default_values:
                    var = tk.BooleanVar(value=True)
                    check = ttk.Checkbutton(settings_frame, text=value, variable=var)
                    check.pack(side="left", padx=5)
                    check_vars[value] = var
                
                widget_data['check_vars'] = check_vars
                widget_data['get_value'] = lambda: {
                    'type': 'list',
                    'selected_values': [v for v, var in widget_data['check_vars'].items() if var.get()]
                }
            else:
                tk.Label(settings_frame, text=template_expansion_texts.enum_comma_separated_label).pack(side="left", padx=(0, 5))
                value_var = tk.StringVar()
                entry = ttk.Entry(settings_frame, textvariable=value_var, width=30)
                entry.pack(side="left")
                widget_data['value_var'] = value_var
                widget_data['get_value'] = lambda: {
                    'type': 'list',
                    'selected_values': [v.strip() for v in widget_data['value_var'].get().split(',') if v.strip()]
                }
            
        elif ph_type == 'numeric_range':
            # 固定値 or 範囲選択
            mode_var = tk.StringVar(value='fixed')
            
            fixed_radio = ttk.Radiobutton(settings_frame, text=template_expansion_texts.fixed_value_label, variable=mode_var, value='fixed')
            fixed_radio.pack(side="left")
            
            template_min = ph_config.get('min', '')
            template_max = ph_config.get('max', '')
            
            fixed_var = tk.StringVar(value=str(template_min) if template_min != '' else '')
            fixed_entry = ttk.Entry(settings_frame, textvariable=fixed_var, width=8)
            fixed_entry.pack(side="left", padx=(0, 10))
            
            range_radio = ttk.Radiobutton(settings_frame, text=template_expansion_texts.range_label, variable=mode_var, value='range')
            range_radio.pack(side="left")
            
            start_var = tk.StringVar(value=str(template_min) if template_min != '' else '')
            tk.Label(settings_frame, text=template_expansion_texts.start_label).pack(side="left", padx=(5, 0))
            start_entry = ttk.Entry(settings_frame, textvariable=start_var, width=6)
            start_entry.pack(side="left", padx=(0, 5))
            
            end_var = tk.StringVar(value=str(template_max) if template_max != '' else '')
            tk.Label(settings_frame, text=template_expansion_texts.end_label).pack(side="left")
            end_entry = ttk.Entry(settings_frame, textvariable=end_var, width=6)
            end_entry.pack(side="left", padx=(0, 5))
            
            step_var = tk.StringVar(value="1")
            tk.Label(settings_frame, text=template_expansion_texts.step_label_short).pack(side="left")
            step_entry = ttk.Entry(settings_frame, textvariable=step_var, width=4)
            step_entry.pack(side="left")
            
            widget_data['mode_var'] = mode_var
            widget_data['fixed_var'] = fixed_var
            widget_data['start_var'] = start_var
            widget_data['end_var'] = end_var
            widget_data['step_var'] = step_var
            
            padding = ph_config.get('padding', 0)
            
            def get_numeric_value():
                if widget_data['mode_var'].get() == 'fixed':
                    try:
                        fixed_val = int(widget_data['fixed_var'].get())
                        return {
                            'type': 'numeric_range',
                            'mode': 'fixed',
                            'fixed': fixed_val,
                            'padding': padding
                        }
                    except ValueError:
                        return {'type': 'numeric_range', 'mode': 'fixed', 'padding': padding}
                else:
                    try:
                        start = int(widget_data['start_var'].get()) if widget_data['start_var'].get() else None
                        end = int(widget_data['end_var'].get()) if widget_data['end_var'].get() else None
                        step = int(widget_data['step_var'].get()) if widget_data['step_var'].get() else 1
                        
                        result = {'type': 'numeric_range', 'mode': 'range', 'padding': padding, 'step': step}
                        if start is not None:
                            result['start'] = start
                        if end is not None:
                            result['end'] = end
                        return result
                    except ValueError:
                        return {'type': 'numeric_range', 'mode': 'range', 'padding': padding}
            
            widget_data['get_value'] = get_numeric_value
        
        elif ph_type == 'date_range':
            # 日付範囲（YYYYMMDD形式）
            tk.Label(settings_frame, text=template_expansion_texts.start_date_label).pack(side="left", padx=(0, 5))
            start_var = tk.StringVar()
            start_entry = ttk.Entry(settings_frame, textvariable=start_var, width=10)
            start_entry.pack(side="left", padx=(0, 10))
            
            tk.Label(settings_frame, text=template_expansion_texts.end_date_label).pack(side="left")
            end_var = tk.StringVar()
            end_entry = ttk.Entry(settings_frame, textvariable=end_var, width=10)
            end_entry.pack(side="left", padx=(0, 10))
            
            weekdays_var = tk.BooleanVar(value=False)
            weekdays_check = ttk.Checkbutton(settings_frame, text=template_expansion_texts.weekdays_only_label, variable=weekdays_var)
            weekdays_check.pack(side="left")
            
            widget_data['start_var'] = start_var
            widget_data['end_var'] = end_var
            widget_data['weekdays_var'] = weekdays_var
            
            def get_date_value():
                result = {'type': 'date_range'}
                if widget_data['start_var'].get():
                    result['start_date'] = widget_data['start_var'].get()
                if widget_data['end_var'].get():
                    result['end_date'] = widget_data['end_var'].get()
                result['weekdays_only'] = widget_data['weekdays_var'].get()
                return result
            
            widget_data['get_value'] = get_date_value
        
        elif ph_type == 'enum':
            # 列挙型（単一選択）
            options = ph_config.get('options', [])
            default = ph_config.get('default', '')
            
            if options:
                tk.Label(settings_frame, text=template_expansion_texts.selection_label).pack(side="left", padx=(0, 5))
                selected_var = tk.StringVar(value=default if default in options else (options[0] if options else ''))
                combo = ttk.Combobox(settings_frame, textvariable=selected_var, values=options, state='readonly', width=20)
                combo.pack(side="left")
                widget_data['selected_var'] = selected_var
                widget_data['get_value'] = lambda: {
                    'type': 'enum',
                    'selected_value': widget_data['selected_var'].get()
                }
            else:
                tk.Label(settings_frame, text=template_expansion_texts.option_undefined, fg="red").pack(side="left")
                widget_data['get_value'] = lambda: {'type': 'enum'}
    
    def go_next(self):
        """次へボタン処理（マトリクス展開モード対応）"""
        if not self.current_template:
            logger.error("テンプレートが設定されていません - current_template is None")
            messagebox.showerror("エラー", "テンプレートが設定されていません")
            return
        
        # 入力検証
        subscription = self.subscription_var.get().strip()
        storage_account = self.storage_account_var.get().strip()
        container = self.container_var.get().strip()
        
        if not all([subscription, storage_account]):
            missing_fields = []
            if not subscription:
                missing_fields.append("サブスクリプションID")
            if not storage_account:
                missing_fields.append("ストレージアカウント")
            logger.warning(f"必須フィールド未入力: {', '.join(missing_fields)}")
            messagebox.showwarning(
                "警告",
                f"以下のフィールドが必要です:\n\n{', '.join(missing_fields)}"
            )
            return
        
        # コンテナチェック（プレースホルダーでない場合）
        if not container and not self.current_template.get('container'):
            logger.warning("コンテナ名が未入力です")
            messagebox.showwarning("警告", "コンテナ名を入力してください")
            return
        
        # マトリクス展開モード：値セットごとに設定を収集
        all_expansions = []
        for set_idx in range(len(self.value_sets)):
            expansions = {}
            for ph_name in self.current_template.get('placeholders', {}).keys():
                widget_key = f"set_{set_idx}_{ph_name}"
                widget_data = self.placeholder_widgets.get(widget_key)
                if widget_data and 'get_value' in widget_data:
                    expansions[ph_name] = widget_data['get_value']()
            
            # 検証: enum複数選択で選択なしの場合
            for ph_name, expansion in expansions.items():
                exp_type = expansion.get('type')
                ph_config = self.current_template['placeholders'].get(ph_name, {})
                ph_label = ph_config.get('label', ph_name)
                
                if exp_type == 'enum' and expansion.get('multiple', False):
                    # 複数選択モードの enum で選択がない場合
                    if not expansion.get('selected_values'):
                        logger.warning(f"値セット{set_idx + 1} - enum複数選択で選択なし: {ph_label}")
                        messagebox.showwarning(
                            "警告",
                            f"値セット{set_idx + 1} - プレースホルダー「{ph_label}」: 少なくとも1つ選択してください"
                        )
                        return
            
            # self.value_setsを更新（復元用）
            self.value_sets[set_idx] = expansions
            all_expansions.append(expansions)
        
        # 現在のテンプレートの値セットを保存（次回復元用）
        idx = self.controller.current_template_index
        self.saved_value_sets[idx] = copy.deepcopy(self.value_sets)
        
        # 現在のテンプレートの設定を保存（複数の値セットを含む）
        template_name = self.current_template['name']
        self.controller.template_expansion_settings[template_name] = {
            'subscription': subscription,
            'storage_account': storage_account,
            'container': container if container else self.current_template.get('container', ''),
            'expansion_sets': all_expansions,  # 複数の値セット
            'template': self.current_template
        }
        
        # 次のテンプレートへ
        self.controller.current_template_index += 1
        
        if self.controller.current_template_index < len(self.controller.selected_templates):
            # 次の展開設定画面
            self.controller.show_frame('TemplateExpansionScreen')
        else:
            # すべて完了 → 検索実行
            self.execute_search()
    
    def execute_search(self):
        """検索実行（マトリクス展開モード対応）"""
        # 進捗ダイアログ
        progress = tk.Toplevel(self)
        progress.title("検索中")
        progress.geometry("500x200")
        progress.transient(self.winfo_toplevel())
        progress.grab_set()
        
        # 中央配置
        progress.update_idletasks()
        x = (progress.winfo_screenwidth() // 2) - (progress.winfo_width() // 2)
        y = (progress.winfo_screenheight() // 2) - (progress.winfo_height() // 2)
        progress.geometry(f'+{x}+{y}')
        
        tk.Label(progress, text=template_expansion_texts.search_executing, font=self.controller.heading_font).pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress, mode='indeterminate')
        progress_bar.pack(pady=10, padx=20, fill='x')
        progress_bar.start(10)
        
        status_label = tk.Label(progress, text="", font=self.controller.default_font)
        status_label.pack(pady=10)
        
        def search_thread():
            try:
                all_matched = []
                
                # 各テンプレートの設定を使用して検索
                for template_name, settings in self.controller.template_expansion_settings.items():
                    template = settings['template']
                    subscription = settings['subscription']
                    storage_account = settings['storage_account']
                    container_pattern = settings['container']
                    expansion_sets = settings.get('expansion_sets', [settings.get('expansions', {})])  # 後方互換性
                    path_pattern = template['path_pattern']
                    placeholders = template['placeholders']
                    
                    self.after(0, lambda tn=template_name: status_label.config(
                        text=f"テンプレート「{tn}」で検索中..."
                    ))
                    
                    # アクセスキー取得
                    self.after(0, lambda: status_label.config(text=f"アクセスキー取得中... ({storage_account})"))
                    account_key = self.controller.storage_key_manager.get_key(storage_account, subscription)
                    
                    if not account_key:
                        raise Exception(f"アクセスキー取得失敗: {storage_account}")
                    
                    # マトリクス展開モード：各値セットを個別に検索（OR結合）
                    template_matched = []
                    for set_idx, expansions in enumerate(expansion_sets):
                        self.after(0, lambda si=set_idx, total=len(expansion_sets): status_label.config(
                            text=f"値セット {si + 1}/{total} を検索中..."
                        ))
                        
                        # コンテナ名展開
                        containers = []
                        if container_pattern and '{' in container_pattern:
                            # プレースホルダー展開
                            containers = self.expand_container_name(container_pattern, expansions)
                        else:
                            containers = [container_pattern]
                        
                        # 各コンテナで検索
                        for target_container in containers:
                            self.after(0, lambda c=target_container: status_label.config(
                                text=f"コンテナ「{c}」を検索中..."
                            ))
                            
                            # プレフィックス計算
                            prefix = PrefixOptimizer.calculate_prefix(path_pattern, expansions)
                            
                            self.after(0, lambda p=prefix: status_label.config(
                                text=f"Blob取得中... (prefix: {p})"
                            ))
                            
                            # Blob一覧取得（ページネーション対応）
                            retry_blob_fetch = True
                            while retry_blob_fetch:
                                success, blobs, error = self.controller.azure_cli.list_blobs_with_prefix(
                                    storage_account, target_container, prefix, account_key
                                )
                                
                                if not success:
                                    logger.warning(f"コンテナ「{target_container}」のBlob取得失敗: {error}")
                                    
                                    # エラーダイアログでリトライ・終了を選択
                                    user_choice: Dict[str, Optional[str]] = {'action': None}
                                    
                                    def show_error_dialog():
                                        dialog = tk.Toplevel(progress)
                                        dialog.title("エラー")
                                        dialog.geometry("500x180")
                                        dialog.transient(progress)
                                        dialog.grab_set()
                                        
                                        # 中央配置
                                        dialog.update_idletasks()
                                        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
                                        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
                                        dialog.geometry(f'+{x}+{y}')
                                        
                                        tk.Label(
                                            dialog,
                                            text=template_expansion_texts.blob_list_error,
                                            font=self.controller.heading_font,
                                            fg='red'
                                        ).pack(pady=10)
                                        
                                        error_text = tk.Text(dialog, height=3, width=60, wrap=tk.WORD)
                                        error_text.pack(pady=5, padx=10)
                                        error_text.insert('1.0', str(error))
                                        error_text.config(state='disabled')
                                        
                                        # 部分的な結果がある場合は通知
                                        if blobs:
                                            tk.Label(
                                                dialog,
                                                text=f"（部分的な結果: {len(blobs)}件は取得済み）",
                                                font=('Noto Sans JP', 9),
                                                fg='orange'
                                            ).pack(pady=2)
                                        
                                        button_frame = tk.Frame(dialog)
                                        button_frame.pack(pady=15)
                                        
                                        def on_retry():
                                            user_choice['action'] = 'retry'
                                            dialog.destroy()
                                        
                                        def on_abort():
                                            user_choice['action'] = 'abort'
                                            dialog.destroy()
                                        
                                        ttk.Button(button_frame, text=template_expansion_texts.retry_button, command=on_retry, width=12).pack(side='left', padx=5)
                                        ttk.Button(button_frame, text=template_expansion_texts.abort_search_button, command=on_abort, width=12).pack(side='left', padx=5)
                                        
                                        dialog.wait_window()
                                    
                                    self.after(0, show_error_dialog)
                                    
                                    # ダイアログの結果を待つ
                                    import time
                                    while user_choice['action'] is None:
                                        time.sleep(0.1)
                                    
                                    if user_choice['action'] == 'retry':
                                        logger.info("ユーザーがリトライを選択")
                                        continue
                                    else:
                                        logger.info("ユーザーが検索終了を選択")
                                        # 部分的な結果がある場合はそれを使用
                                        if blobs:
                                            retry_blob_fetch = False
                                        else:
                                            raise Exception("Blob一覧取得に失敗し、ユーザーが終了を選択しました")
                                else:
                                    # 成功
                                    retry_blob_fetch = False
                            
                            self.after(0, lambda c=len(blobs): status_label.config(
                                text=f"候補: {c}件 → 条件マッチング中..."
                            ))
                            
                            # 条件マッチング
                            matched = ConditionMatcher.filter_blobs(
                                blobs, path_pattern, placeholders, expansions
                            )
                            
                            # テンプレート情報とコンテナ情報を追加
                            for blob in matched:
                                blob['template_name'] = template_name
                                blob['container'] = target_container
                                blob['storage_account'] = storage_account
                                blob['subscription'] = subscription
                            
                            template_matched.extend(matched)
                    
                    # 重複排除（同じBlob名が複数の値セットで見つかった場合）
                    seen = set()
                    unique_matched = []
                    for blob in template_matched:
                        blob_key = (blob['storage_account'], blob['container'], blob['name'])
                        if blob_key not in seen:
                            seen.add(blob_key)
                            unique_matched.append(blob)
                    
                    all_matched.extend(unique_matched)
                
                self.controller.matched_blobs = all_matched
                
                # 完了
                self.after(0, progress.destroy)
                self.after(0, lambda: self.controller.show_frame('TemplateSearchResultScreen'))
                
            except Exception as e:
                error_msg = str(e)
                logger.exception(f"検索エラー: {error_msg}")
                self.after(0, progress.destroy)
                self.after(0, lambda msg=error_msg: messagebox.showerror("エラー", f"検索失敗:\n{msg}"))
        
        thread = threading.Thread(target=search_thread, daemon=True)
        thread.start()
    
    def expand_container_name(self, container_pattern: str, expansions: Dict[str, Dict]) -> List[str]:
        """
        コンテナ名パターンを展開
        
        Args:
            container_pattern: コンテナ名パターン（例: "{environment}-logs"）
            expansions: プレースホルダー展開設定
            
        Returns:
            展開されたコンテナ名のリスト
        """
        # プレースホルダーを抽出
        placeholders = re.findall(r'\{([^}]+)\}', container_pattern)
        
        if not placeholders:
            return [container_pattern]
        
        # 各プレースホルダーの値を取得
        placeholder_values = {}
        for ph in placeholders:
            expansion = expansions.get(ph, {})
            exp_type = expansion.get('type')
            
            if exp_type == 'text':
                value = expansion.get('value', '')
                if value:
                    placeholder_values[ph] = [value]
                else:
                    placeholder_values[ph] = [f'{{{ph}}}']
            elif exp_type == 'numeric':
                mode = expansion.get('mode', 'fixed')
                if mode == 'fixed' and 'fixed' in expansion:
                    padding = expansion.get('padding', 0)
                    value = str(expansion['fixed']).zfill(padding)
                    placeholder_values[ph] = [value]
                else:
                    # 範囲の場合は先頭値のみ
                    start = expansion.get('start', 0)
                    padding = expansion.get('padding', 0)
                    placeholder_values[ph] = [str(start).zfill(padding)]
            elif exp_type == 'enum':
                multiple = expansion.get('multiple', False)
                if multiple:
                    selected = expansion.get('selected_values', [])
                    placeholder_values[ph] = selected if selected else [f'{{{ph}}}']
                else:
                    selected = expansion.get('selected_value', '')
                    placeholder_values[ph] = [selected] if selected else [f'{{{ph}}}']
            elif exp_type == 'regex':
                # regexはコンテナ名に使えないのでパターンのまま
                placeholder_values[ph] = [f'{{{ph}}}']
            else:
                # 未定義の場合はパターンのまま
                placeholder_values[ph] = [f'{{{ph}}}']
        
        # 全組み合わせを生成
        if all(placeholder_values.values()):
            combinations = list(itertools.product(*[placeholder_values[ph] for ph in placeholders]))
            containers = []
            for combo in combinations:
                container_name = container_pattern
                for ph, value in zip(placeholders, combo):
                    container_name = container_name.replace(f'{{{ph}}}', value)
                containers.append(container_name)
            return containers
        else:
            return [container_pattern]
