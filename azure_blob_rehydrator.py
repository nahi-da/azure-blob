# -*- coding: utf-8 -*-

# アプリケーション名定数
APP_NAME = "AzBlobDL"

# 標準ライブラリ
import logging
import platform
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Union

# コアモジュールのインポート
from module.core import (
    ConfigManager,
    LogManager,
    AzureCLIWrapper,
    StorageAccountKeyManager,
    StateFileManager,
    ServicePrincipalProfileManager,
)

# テンプレートモジュールのインポート
from module.template_module import TemplateManager

# 認証UIモジュールのインポート
from module.ui.auth import (
    AuthenticationMethodScreen, LoginScreen,
    ServicePrincipalSelectionScreen, ProfileEditorScreen,
    ExistingLoginScreen
)
from module.ui.blob_selection import (
    BlobSelectionMethodScreen, BlobURLInputScreen,
    TemplateSelectionScreen, TemplateExpansionScreen,
    TemplateSearchResultScreen, TemplateEditorScreen
)
from module.ui.execution import (
    OptionsScreen, ProgressScreen, CompletionScreen
)

# ロガー定義
logger = logging.getLogger(__name__)

# Windows高DPI対応
if platform.system() == 'Windows':
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)  # DPI_AWARENESS_SYSTEM_AWARE
    except Exception:
        pass  # Windows 8.1未満またはエラー時は無視


# ============================================================================
# メインアプリケーションクラス
# ============================================================================

class AzureBlobRehydratorApp(tk.Tk):
    """メインアプリケーションクラス"""
    
    def __init__(self, run_template_management: bool = False):
        super().__init__()
        
        # 基盤クラス初期化
        self.config = ConfigManager()
        self.log_manager = LogManager(self.config)
        self.azure_cli = AzureCLIWrapper(self.config)
        self.storage_key_manager = StorageAccountKeyManager(self.azure_cli)
        self.state_manager = StateFileManager(self.config)
        
        # サービスプリンシパル管理
        script_dir = Path(__file__).parent
        profiles_directory = self.config.get('profiles_directory', 'data/profiles')
        profiles_dir = script_dir / profiles_directory
        self.sp_profile_manager = ServicePrincipalProfileManager(profiles_dir)
        
        # テンプレート管理
        templates_directory = self.config.get('templates_directory', 'data/templates')
        templates_dir = script_dir / templates_directory
        self.template_manager = TemplateManager(templates_dir)
        
        # アプリケーション状態
        self.history = []  # 画面履歴スタック
        self.cancel_event = threading.Event()  # 中断イベント
        self.current_state_file = Path()  # 現在のステートファイル
        self.session_id = None  # 現在のセッションID
        self.current_subscription = None  # 現在のサブスクリプション
        self.current_tenant = None  # 現在のテナント
        self.blob_urls = []  # Blob URLリスト
        self.validated_blobs = []  # 検証済みBlobデータ
        self.resuming_session = False  # セッション復帰フラグ
        self.run_template_management = run_template_management  # テンプレート管理画面を開く場合のフラグ
        
        # セッション実行時の設定（メモリ管理）
        self.session_options: Dict[str, Any] = {}  # 実行オプション（target_tier, priority等）
        self.session_subscription_id: str = ""  # サブスクリプションID
        self.session_subscription_name: str = ""  # サブスクリプション名
        self.session_tenant_name: str = ""  # テナント名
        
        # テンプレート検索機能用データ
        self.selected_templates: List[Dict] = []
        self.current_template_index: int = 0
        self.template_expansion_settings: Dict[str, Dict[str, Any]] = {}
        self.matched_blobs: List[Dict] = []
        
        # 認証関連
        self.auth_method = str()  # 'user' or 'service_principal'
        self.selected_sp_profile = dict()  # 選択されたSPプロファイル
        
        # ウィンドウ設定
        self.title("AzBlobDL")
        self.geometry("600x500")  # 初期サイズを小さく
        self.resizable(True, True)  # リサイズ可能
        
        # フォント設定（Windowsで読みやすいフォント）
        if platform.system() == 'Windows':
            self.default_font = ('Noto Sans JP', 9)
            self.title_font = ('Noto Sans JP', 18, 'bold')
            self.heading_font = ('Noto Sans JP', 12)
            self.button_font = ('Noto Sans JP', 10)
        else:
            self.default_font = ('Arial', 9)
            self.title_font = ('Arial', 18, 'bold')
            self.heading_font = ('Arial', 12, 'bold')
            self.button_font = ('Arial', 10)
        
        # ttkスタイル設定
        style = ttk.Style()
        style.theme_use('vista' if platform.system() == 'Windows' else 'clam')
        style.configure('TButton', font=self.button_font, padding=6)
        style.configure('TLabel', font=self.default_font)
        style.configure('Title.TLabel', font=self.title_font)
        style.configure('Heading.TLabel', font=self.heading_font)
        style.configure('TEntry', font=self.default_font)
        style.configure('TCombobox', font=self.default_font)
        style.configure('White.TRadiobutton', background='white', font=self.default_font)
        
        # Tkinter例外ハンドラ設定
        self.report_callback_exception = self._handle_exception
        
        # コンテナフレーム
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        # 画面辞書
        self.frames = {}
        
        # 画面クラスマッピング（文字列でアクセス可能にする）
        self.frame_classes = {
            'AuthenticationMethodScreen': AuthenticationMethodScreen,
            'LoginScreen': LoginScreen,
            'ServicePrincipalSelectionScreen': ServicePrincipalSelectionScreen,
            'ProfileEditorScreen': ProfileEditorScreen,
            'ExistingLoginScreen': ExistingLoginScreen,
            'BlobSelectionMethodScreen': BlobSelectionMethodScreen,
            'TemplateSelectionScreen': TemplateSelectionScreen,
            'TemplateExpansionScreen': TemplateExpansionScreen,
            'TemplateSearchResultScreen': TemplateSearchResultScreen,
            'TemplateEditorScreen': TemplateEditorScreen,
            'BlobURLInputScreen': BlobURLInputScreen,
            'OptionsScreen': OptionsScreen,
            'ProgressScreen': ProgressScreen,
            'CompletionScreen': CompletionScreen,
        }
        
        # 起動時処理
        self.after(200, self.startup_process)
    
    def startup_process(self):
        """起動時処理（再開確認）"""
        # 未完了のステートファイル検索
        incomplete_state = self.state_manager.find_incomplete_state()
        
        if incomplete_state:
            # 再開確認
            session_id = incomplete_state.stem.replace('_state', '')
            result = messagebox.askyesno(
                "未完了処理の再開",
                f"前回の未完了処理（セッションID: {session_id}）が見つかりました。\n"
                "再開しますか？"
            )
            
            if result:
                # 再開処理
                self.resume_from_state(incomplete_state)
                return
        
        # 通常起動：認証方法選択画面表示
        if self.run_template_management:
            self.show_frame('TemplateEditorScreen')
        else:
            self.show_frame('AuthenticationMethodScreen')
    
    def resume_from_state(self, state_file: Path):
        """
        ステートファイルから処理を再開
        
        Args:
            state_file: ステートファイルパス
        """
        try:
            state_data = self.state_manager.load_state_file(state_file)
            if not state_data:
                logger.error(f"ステートファイルの読み込みに失敗しました: {state_file}")
                messagebox.showerror("エラー", f"ステートファイルの読み込みに失敗しました\n\nファイル: {state_file.name}")
                self.show_frame('AuthenticationMethodScreen')
                return
            
            # ステート情報を復元
            self.session_id = state_data['session_id']
            self.current_state_file = state_file
            self.current_subscription = {
                'id': state_data['subscription_id'],
                'name': state_data['subscription_name']
            }
            self.current_tenant = state_data['tenant_name']
            self.validated_blobs = state_data['blobs']
            
            # セッション情報をメモリに保存（以降はファイル読み込み不要）
            self.session_options = state_data.get('options', {})
            self.session_subscription_id = state_data['subscription_id']
            self.session_subscription_name = state_data['subscription_name']
            self.session_tenant_name = state_data['tenant_name']
            
            # 復帰フラグを立てて認証選択画面へ
            logger.info("セッション復帰：認証選択画面から開始")
            self.resuming_session = True
            messagebox.showinfo(
                "セッションの再開",
                f"未完了セッションを再開します。\n"
                f"認証方法を選択してください。\n\n"
                f"セッションID: {self.session_id}"
            )
            self.show_frame('AuthenticationMethodScreen')
            
        except Exception as e:
            logger.exception(f"ステートファイル復元エラー: {e}")
            messagebox.showerror("エラー", f"処理の再開に失敗しました: {e}")
            self.show_frame('AuthenticationMethodScreen')
    
    def show_frame(self, frame_class: Union[type, str], add_to_history: bool = True):
        """
        画面を表示
        
        Args:
            frame_class: 表示する画面クラスまたは画面名（文字列）
            add_to_history: 履歴に追加するか
        """
        try:
            # 文字列の場合はクラスに変換
            actual_class: type
            if isinstance(frame_class, str):
                if frame_class in self.frame_classes:
                    actual_class = self.frame_classes[frame_class]
                else:
                    raise ValueError(f"不明な画面名: {frame_class}")
            else:
                actual_class = frame_class
            
            # フレームが存在しない場合は作成
            if actual_class not in self.frames:
                # コンテナを取得
                container = self.winfo_children()[0]
                frame = actual_class(container, self)
                self.frames[actual_class] = frame
                frame.grid(row=0, column=0, sticky="nsew")
            
            # 履歴に追加
            if add_to_history:
                if not self.history or self.history[-1] != actual_class:
                    self.history.append(actual_class)
            
            # 画面を最前面に表示
            frame = self.frames[actual_class]
            frame.tkraise()
            
            # フレームの on_show メソッドがあれば呼び出し
            if hasattr(frame, 'on_show'):
                frame.on_show()
            
            # 画面サイズを調整（on_show後に実行）
            # 動的にウィジェットが生成される画面のために遅延実行
            # テンプレート編集画面など複雑な画面は50ms待機
            delay = 50 if actual_class.__name__ == 'TemplateEditorScreen' else 10
            self.after(delay, lambda: self._adjust_window_size(actual_class))
        except Exception as e:
            logger.exception(f"画面表示エラー: {frame_class} - {e}")
            messagebox.showerror("エラー", f"画面の表示に失敗しました:\n{frame_class}\n\n{e}")
    
    def _adjust_window_size(self, frame_class: type):
        """
        画面に合わせてウィンドウサイズを自動調整
        
        Args:
            frame_class: 画面クラス
        """
        # フレームの取得
        frame = self.frames.get(frame_class)
        if not frame:
            return
        
        # レイアウトを強制的に更新
        frame.update_idletasks()
        self.update_idletasks()
        
        # フレームの必要サイズを取得
        required_width = frame.winfo_reqwidth()
        required_height = frame.winfo_reqheight()
        
        # 画面サイズを取得
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 画面別の最小サイズ設定
        # テンプレート編集画面は多くのフィールドがあるため高さを大きめに
        if frame_class.__name__ == 'TemplateEditorScreen':
            min_width = 1200
            min_height = 750
            padding_width = 60
            padding_height = 80
        else:
            min_width = 600
            min_height = 350
            padding_width = 40
            padding_height = 30  # 小さめの画面用に削減
        
        # 最大サイズを設定（画面サイズの85%/80%、ディスプレイを超えない余裕を持たせる）
        max_width = int(screen_width * 0.85)
        max_height = int(screen_height * 0.80)
        
        target_width = max(min_width, min(required_width + padding_width, max_width))
        target_height = max(min_height, min(required_height + padding_height, max_height))
        
        # ウィンドウサイズを設定
        self.geometry(f"{target_width}x{target_height}")
        
        # ウィンドウを画面中央に配置
        x = (screen_width - target_width) // 2
        y = (screen_height - target_height) // 2
        self.geometry(f"{target_width}x{target_height}+{x}+{y}")
        
        # 最小サイズを設定（これ以下には縮小できないようにする）
        self.minsize(min_width, min_height)
        
        logger.debug(f"ウィンドウサイズ調整: {frame_class.__name__} -> {target_width}x{target_height} "
                    f"(要求サイズ: {required_width}x{required_height})")
    
    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """Tkinterコールバック内の例外をログに記録"""
        if exc_type == KeyboardInterrupt:
            # Ctrl+Cは通常通り処理
            sys.exit(1)
        
        # 例外をログに記録
        logger.exception(
            "Tkinterコールバック例外:",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # ユーザーにも通知
        try:
            messagebox.showerror(
                "エラー",
                f"予期しないエラーが発生しました:\n{exc_type.__name__}: {exc_value}"
            )
        except Exception:
            pass  # メッセージボックス表示失敗時は無視
    
    def go_back(self):
        """前の画面に戻る"""
        if len(self.history) > 1:
            self.history.pop()  # 現在の画面を削除
            previous = self.history[-1]
            frame = self.frames[previous]
            frame.tkraise()
            
            # フレームの on_show メソッドがあれば呼び出し
            if hasattr(frame, 'on_show'):
                frame.on_show()
            
            # 画面サイズを調整（on_show後に実行）
            self.after(10, lambda: self._adjust_window_size(previous))


# ============================================================================
if __name__ == '__main__':
    app = AzureBlobRehydratorApp()
    app.mainloop()
