# -*- coding: utf-8 -*-
"""
Progress Screen - 処理進捗画面

リハイドレートとダウンロード/コピー処理の進捗を表示する画面。
- マルチスレッドBLOB処理
- リアルタイム進捗トラッキング（TreeView）
- リハイドレート状態ポーリング
- ダウンロード＆コピー操作
- ステートファイル管理
- エラーハンドリングとリトライロジック
"""

import logging
import os
import threading
import time
import tkinter as tk
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from ...core import parse_azure_cli_error
from ...core.exceptions import (
    AccountKeyRetrievalError,
    AuthenticationError,
    AzureError,
    BlobArchivedError,
    BlobNotFoundError,
    ContainerNotFoundError,
    InvalidFormatError,
    InvalidResourceNameError,
    PermissionError,
    StorageAccountNotFoundError,
    SubscriptionNotFoundError,
)
from ...ui_text.execution_texts import progress_texts

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from azure_blob_rehydrator import AzureBlobRehydratorApp


# ============================================================================
# 進捗画面
# ============================================================================

class ProgressScreen(tk.Frame):
    """進捗画面"""
    
    def __init__(self, parent, controller: 'AzureBlobRehydratorApp'):
        super().__init__(parent)
        self.controller = controller
        
        # タイトル
        self.title_label = ttk.Label(self, text=progress_texts.title, style='Title.TLabel')
        self.title_label.pack(pady=10)
        
        # 経過時間＋プログレスバー
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=20, pady=10)
        
        self.elapsed_time_label = ttk.Label(top_frame, text=progress_texts.elapsed_time_label, font=controller.heading_font)
        self.elapsed_time_label.pack()
        
        self.progress_bar = ttk.Progressbar(top_frame, mode='indeterminate')
        self.progress_bar.pack(fill="x", pady=10)
        
        # Treeview（Blob一覧）
        tree_frame = tk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # ページング用フレーム（100件以上の場合）
        self.paging_frame = ttk.Frame(tree_frame)
        self.prev_button = ttk.Button(self.paging_frame, text=progress_texts.prev_button, command=self.prev_page)
        self.prev_button.pack(side="left", padx=5)
        self.page_label = ttk.Label(self.paging_frame, text=progress_texts.page_info(1, 1))
        self.page_label.pack(side="left", padx=10)
        self.next_button = ttk.Button(self.paging_frame, text=progress_texts.next_button, command=self.next_page)
        self.next_button.pack(side="left", padx=5)
        
        # Treeview
        columns = ('blob', 'storage', 'container', 'status', 'progress')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=8)
        
        self.tree.heading('blob', text=progress_texts.col_blob)
        self.tree.heading('storage', text=progress_texts.col_storage)
        self.tree.heading('container', text=progress_texts.col_container)
        self.tree.heading('status', text=progress_texts.col_status)
        self.tree.heading('progress', text=progress_texts.col_progress)
        
        self.tree.column('blob', width=300, minwidth=300, stretch=False)
        self.tree.column('storage', width=150, minwidth=150, stretch=False)
        self.tree.column('container', width=150, minwidth=150, stretch=False)
        self.tree.column('status', width=100, minwidth=100, stretch=False)
        self.tree.column('progress', width=200, minwidth=400, stretch=False)
        
        # スクロールバー（縦と横）
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # タグ設定（色分け）
        self.tree.tag_configure(progress_texts.status_waiting, background='lightgray')
        self.tree.tag_configure(progress_texts.status_processing, background='lightblue')
        self.tree.tag_configure(progress_texts.status_completed, background='lightgreen')
        self.tree.tag_configure(progress_texts.status_error, background='lightcoral')
        self.tree.tag_configure(progress_texts.status_skipped, background='lightyellow')
        
        # ログ表示
        log_frame = ttk.LabelFrame(self, text=progress_texts.log_title, padding=5)
        log_frame.pack(fill="both", padx=20, pady=10)
        
        self.log_text = tk.Text(log_frame, height=10, width=100, state='disabled', wrap=tk.WORD,
                               font=controller.default_font)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")
        
        # ボタンフレーム
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(pady=20)
        
        # 中断ボタン用スタイル
        style = ttk.Style()
        style.configure('Cancel.TButton', font=controller.button_font, padding=10)
        style.map('Cancel.TButton', background=[('active', '#ff8c00')])
        
        self.cancel_button = ttk.Button(self.button_frame, text=progress_texts.cancel_button,
                                       command=self.cancel_process, style='Cancel.TButton', width=15)
        self.cancel_button.pack()
        
        # 状態管理
        self.start_time = None
        self.timer_id = None
        self.current_page = 0
        self.items_per_page = 100
        self.tree_items = {}  # {blob_url: tree_item_id}
        self.executor = None
        self.is_completed = False
    
    def on_show(self):
        """画面表示時の処理"""
        if not self.start_time:
            # タイトル更新（動作モードに応じて）
            options = self.controller.validated_blobs[0].get('options', {}) if self.controller.validated_blobs else {}
            mode = options.get('operation_mode', 'download')
            if mode == 'download':
                self.title_label.config(text=progress_texts.title_download)
            else:
                self.title_label.config(text=progress_texts.title_copy)
            
            # 初回表示時のみ処理開始
            self.start_processing()
    
    def start_processing(self):
        """処理開始"""
        # ストレージアカウントのアクセスキーを事前取得
        self.prefetch_storage_keys()
        
        # バッチモードの確認
        batch_mode = self.controller.config.get('rehydrate_batch_mode', True)
        
        if batch_mode:
            # 2段階処理モード
            self.start_batch_processing()
        else:
            # 従来の処理モード（後方互換性）
            self.start_legacy_processing()
    
    def prefetch_storage_keys(self):
        """ストレージアカウントのアクセスキーを事前取得"""
        # 対象Blobからストレージアカウントのリストを抽出（重複排除）
        storage_accounts = set()
        for blob_data in self.controller.validated_blobs:
            storage_account = blob_data.get('storage_account', '')
            if storage_account:
                storage_accounts.add(storage_account)
        
        if not storage_accounts:
            return
        
        self.add_log(f"ストレージアカウント {len(storage_accounts)}個のアクセスキーを取得中...")
        
        # サブスクリプションID取得
        subscription_id = self.controller.current_subscription.get('id', '') if self.controller.current_subscription else None
        
        # 各ストレージアカウントのアクセスキーを事前取得
        success_count = 0
        for storage_account in storage_accounts:
            account_key = self.controller.storage_key_manager.get_key(storage_account, subscription_id)
            if account_key:
                success_count += 1
            else:
                self.add_log(f"警告: {storage_account} のアクセスキー取得失敗", level='warning')
        
        self.add_log(f"アクセスキー取得完了: {success_count}/{len(storage_accounts)}個")
        self.add_log("=" * 80)
    
    def start_batch_processing(self):
        """バッチ処理開始（2段階）"""
        self.start_time = time.time()
        self.is_completed = False
        self.controller.cancel_event.clear()
        
        # プログレスバー開始
        self.progress_bar.start(10)
        
        # 経過時間更新開始
        self.update_elapsed_time()
        
        # Treeviewにデータ追加
        self.populate_tree()
        
        # ログ追加
        self.add_log(f"処理開始: セッションID {self.controller.session_id}")
        self.add_log(f"対象Blob数: {len(self.controller.validated_blobs)}")
        self.add_log("=" * 80)
        self.add_log("Phase 1: 全Blobへリハイドレート要求")
        
        # Phase 1実行
        threading.Thread(target=self.execute_phase1, daemon=True).start()
    
    def start_legacy_processing(self):
        """従来の処理方式（1フェーズ）"""
        self.start_time = time.time()
        self.is_completed = False
        self.controller.cancel_event.clear()
        
        # プログレスバー開始
        self.progress_bar.start(10)
        
        # 経過時間更新開始
        self.update_elapsed_time()
        
        # Treeviewにデータ追加
        self.populate_tree()
        
        # ログ追加
        self.add_log(f"処理開始: セッションID {self.controller.session_id}")
        self.add_log(f"対象Blob数: {len(self.controller.validated_blobs)}")
        
        # 従来方式: 5並列で順次実行
        max_workers = self.controller.config.get('max_download_workers', 5)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        for blob_data in self.controller.validated_blobs:
            if self.controller.cancel_event.is_set():
                break
            self.executor.submit(self.process_blob, blob_data)
    
    def execute_phase1(self):
        """Phase 1: 全Blobにリハイドレート要求（並列数制限あり）"""
        max_workers = self.controller.config.get('max_rehydrate_workers', 10)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for blob_data in self.controller.validated_blobs:
                if self.controller.cancel_event.is_set():
                    break
                
                future = executor.submit(self.request_rehydrate, blob_data)
                futures.append((future, blob_data))
            
            # 全リハイドレート要求の完了を待つ
            completed = 0
            total = len(futures)
            
            for future, blob_data in futures:
                try:
                    future.result()  # 例外がある場合はここでキャッチ
                    completed += 1
                    
                    # 進捗ログ（10個ごと）
                    if completed % 10 == 0:
                        self.after(0, lambda c=completed, t=total: self.add_log(
                            f"リハイドレート要求進捗: {c}/{t}"
                        ))
                except Exception as e:
                    # エラーは既にrequest_rehydrateで処理済み
                    pass
        
        # Phase 1完了
        self.after(0, self.on_phase1_complete)
    
    def request_rehydrate(self, blob_data: Dict[str, Any]):
        """リハイドレート要求のみ実行（エラーハンドリング含む）"""
        blob_url = blob_data['url']
        blob_name = blob_data['blob_name']
        
        try:
            # 中断チェック
            if self.controller.cancel_event.is_set():
                return
            
            storage_account = blob_data['storage_account']
            container = blob_data['container']
            subscription_id = blob_data.get('subscription')
            
            # アクセスキー取得
            account_key = self.controller.storage_key_manager.get_key(storage_account, subscription_id)
            if not account_key:
                raise AccountKeyRetrievalError("アクセスキー取得失敗")
            
            # まずBlob層を確認
            self.after(0, lambda url=blob_url: self.update_blob_status(
                url, 'checking', 'Blob層確認中...'
            ))
            
            success, blob_info, error = self.controller.azure_cli.run([
                'storage', 'blob', 'show',
                '--account-name', storage_account,
                '--container-name', container,
                '--name', blob_name,
                '--account-key', account_key
            ])
            
            if not success:
                raise parse_azure_cli_error(error if error else "Blob情報取得失敗")
            
            blob_tier = blob_info.get('properties', {}).get('blobTier')
            archive_status = blob_info.get('properties', {}).get('archiveStatus')
            blob_type = blob_info.get('properties', {}).get('blobType', 'Unknown')
            
            # デバッグログ
            self.after(0, lambda name=blob_name, tier=blob_tier, status=archive_status, btype=blob_type: 
                      self.add_log(f"Blob層情報: {name} - 層={tier}, アーカイブ状態={status}, タイプ={btype}"))
            
            # AppendBlobの場合は層の概念がないためスキップ
            if blob_type == 'AppendBlob' or blob_tier is None:
                self.after(0, lambda url=blob_url: self.update_blob_status(
                    url, 'rehydrate_completed', 'AppendBlob（リハイドレート不要）'
                ))
                self.after(0, lambda name=blob_name: self.add_log(
                    f"AppendBlob検出: {name} - アクセス層の概念がないためスキップ"
                ))
                return
            
            # セッション情報をメモリから取得（ファイル読み込み不要）
            options = self.controller.session_options
            if not options:
                logger.warning("セッション情報にoptionsが存在しません")
                raise ValueError("optionsがセッション情報に存在しません")
            
            # リハイドレート処理の判定
            # 1. すでにリハイドレート中の場合はスキップ
            if archive_status and 'rehydrate-pending' in archive_status:
                self.after(0, lambda url=blob_url: self.update_blob_status(
                    url, 'rehydrating', 'リハイドレート中（既存処理）'
                ))
                self.after(0, lambda name=blob_name: self.add_log(f"既にリハイドレート中: {name}"))
                return
                
            # 2. Hot/Cool/Cold/Premium層の場合はリハイドレート不要
            elif blob_tier in ['Hot', 'Cool', 'Cold', 'Premium', 'P10', 'P20', 'P30', 'P40', 'P50', 'P60', 'P70', 'P80']:
                self.after(0, lambda url=blob_url, tier=blob_tier: self.update_blob_status(
                    url, 'rehydrate_completed', f'{tier}層（リハイドレート不要）'
                ))
                self.after(0, lambda name=blob_name, tier=blob_tier: self.add_log(
                    f"リハイドレート不要: {name} ({tier}層)"
                ))
                return
                
            # 3. Archive層の場合のみリハイドレート実行
            elif blob_tier == 'Archive':
                self.after(0, lambda url=blob_url: self.update_blob_status(
                    url, 'rehydrate_requested', 'リハイドレート要求中...'
                ))
                self.after(0, lambda name=blob_name: self.add_log(f"リハイドレート開始: {name}"))
                
                # リハイドレート要求実行（リトライ付き）
                target_tier = options['target_tier']
                priority = options['priority']
                max_retry = self.controller.config.get('max_retry_count', 3)
                retry_delay = self.controller.config.get('retry_delay_seconds', 10)
                
                for attempt in range(max_retry + 1):
                    success, data, error = self.controller.azure_cli.run([
                        'storage', 'blob', 'set-tier',
                        '--account-name', storage_account,
                        '--container-name', container,
                        '--name', blob_name,
                        '--tier', target_tier,
                        '--rehydrate-priority', priority,
                        '--account-key', account_key
                    ])
                    
                    if success:
                        # 成功
                        self.after(0, lambda url=blob_url: self.update_blob_status(
                            url, 'rehydrating', 'リハイドレート中...'
                        ))
                        return
                    
                    # エラー処理
                    parsed_error = parse_azure_cli_error(error if error else "")
                    
                    # リトライ不可能なエラー
                    if not self._is_retryable_error(parsed_error):
                        raise parsed_error
                    
                    # リトライ
                    if attempt < max_retry:
                        self.after(0, lambda url=blob_url, a=attempt+1, m=max_retry: 
                                  self.update_blob_status(
                                      url, 'rehydrate_requested', 
                                      f'リトライ中... ({a}/{m})'
                                  ))
                        time.sleep(retry_delay)
                    else:
                        # 最大リトライ回数超過
                        raise parsed_error
            
            # 4. 不明な層の場合はエラー
            else:
                raise AzureError(f"不明なBlob層: {blob_tier}。Blob情報の取得に失敗した可能性があります。")
            
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda url=blob_url, msg=error_msg: 
                      self.update_blob_status(url, 'error', f'エラー: {msg}'))
            logger.error(f"リハイドレート要求失敗 ({blob_name}): {error_msg}")
            logger.exception(e)
    
    def on_phase1_complete(self):
        """Phase 1完了時の処理"""
        self.add_log("=" * 80)
        self.add_log("Phase 1完了: 全Blobへのリハイドレート要求が完了しました")
        self.add_log("Phase 2: リハイドレート完了確認＋即時ダウンロード開始")
        self.add_log("=" * 80)
        
        # Phase 2開始
        threading.Thread(target=self.execute_phase2, daemon=True).start()
    
    def execute_phase2(self):
        """Phase 2: ローリング状態確認＋即時ダウンロード"""
        check_interval = self.controller.config.get('rehydrate_check_interval_seconds', 60)
        status_check_workers = self.controller.config.get('max_status_check_workers', 10)
        max_download_workers = self.controller.config.get('max_download_workers', 5)
        
        # ダウンロード用セマフォ（同時ダウンロード数を制限）
        download_semaphore = threading.Semaphore(max_download_workers)
        
        # ダウンロード用エグゼキュータ（制限なしで作成、セマフォで制御）
        download_executor = ThreadPoolExecutor(max_workers=max_download_workers * 2)
        
        # 未完了のBlob追跡（rehydrate_completedは既にリハイドレート完了済みなので除外）
        pending_blobs = [b for b in self.controller.validated_blobs 
                         if b.get('status') not in ['completed', 'error', 'skipped', 'rehydrate_completed']]
        
        # リハイドレート完了済みのBlobは即座にダウンロード開始
        ready_blobs = [b for b in self.controller.validated_blobs 
                       if b.get('status') == 'rehydrate_completed']
        
        if ready_blobs:
            self.after(0, lambda count=len(ready_blobs): self.add_log(
                f"リハイドレート不要: {count}件 → ダウンロード開始"
            ))
            for blob_data in ready_blobs:
                if self.controller.cancel_event.is_set():
                    break
                download_executor.submit(
                    self.download_blob_phase2, 
                    blob_data, 
                    download_semaphore
                )
        
        round_number = 1
        
        while pending_blobs and not self.controller.cancel_event.is_set():
            self.after(0, lambda r=round_number, p=len(pending_blobs): self.add_log(
                f"確認ラウンド {r}: 未完了 {p}件を確認中..."
            ))
            
            # 状態確認を並列実行
            ready_blobs = []
            
            with ThreadPoolExecutor(max_workers=status_check_workers) as status_executor:
                # 全未完了Blobの状態を確認
                future_to_blob = {
                    status_executor.submit(self.check_blob_status, blob): blob 
                    for blob in pending_blobs
                }
                
                for future in future_to_blob:
                    if self.controller.cancel_event.is_set():
                        break
                    
                    blob_data = future_to_blob[future]
                    
                    try:
                        is_ready = future.result()
                        
                        if is_ready:
                            ready_blobs.append(blob_data)
                            pending_blobs.remove(blob_data)
                            
                    except Exception as e:
                        # エラーは既にcheck_blob_statusで処理済み
                        # pending_blobsから削除（再試行しない）
                        if blob_data in pending_blobs:
                            pending_blobs.remove(blob_data)
            
            # 完了したBlobを即座にダウンロード（セマフォで同時数制限）
            if ready_blobs:
                self.after(0, lambda count=len(ready_blobs): self.add_log(
                    f"リハイドレート完了: {count}件 → ダウンロード開始"
                ))
                
                for blob_data in ready_blobs:
                    if self.controller.cancel_event.is_set():
                        break
                    
                    download_executor.submit(
                        self.download_blob_phase2, 
                        blob_data, 
                        download_semaphore
                    )
            
            # 次のラウンドまで待機
            if pending_blobs:
                self.after(0, lambda p=len(pending_blobs): self.add_log(
                    f"リハイドレート待機中... 残り {p}件"
                ))
                
                # 中断チェックしながら待機
                for _ in range(check_interval):
                    if self.controller.cancel_event.is_set():
                        break
                    time.sleep(1)
            
            round_number += 1
        
        # ダウンロードエグゼキュータのシャットダウン
        download_executor.shutdown(wait=True)
        
        # 完了チェック
        self.after(0, self.check_all_completed)
    
    def check_blob_status(self, blob_data: Dict[str, Any]) -> bool:
        """
        Blobの状態を確認
        
        Returns:
            リハイドレート完了ならTrue、未完了ならFalse
        """
        blob_url = blob_data['url']
        blob_name = blob_data['blob_name']
        storage_account = blob_data['storage_account']
        container = blob_data['container']
        subscription_id = blob_data.get('subscription')
        
        try:
            # アクセスキー取得
            account_key = self.controller.storage_key_manager.get_key(storage_account, subscription_id)
            if not account_key:
                raise AccountKeyRetrievalError("アクセスキー取得失敗")
            
            # Blob情報取得
            success, data, error = self.controller.azure_cli.run([
                'storage', 'blob', 'show',
                '--account-name', storage_account,
                '--container-name', container,
                '--name', blob_name,
                '--account-key', account_key
            ])
            
            if not success:
                raise parse_azure_cli_error(error if error else "Blob情報取得失敗")
            
            # リハイドレート完了チェック
            blob_tier = data.get('properties', {}).get('blobTier', '')
            archive_status = data.get('properties', {}).get('archiveStatus')
            
            # 完了条件: Hot/Coolでarchive_statusがNone
            is_ready = (
                blob_tier in ['Hot', 'Cool'] and 
                archive_status is None
            )
            
            if is_ready:
                self.after(0, lambda url=blob_url: self.update_blob_status(
                    url, 'rehydrated', 'リハイドレート完了 → ダウンロード待機'
                ))
            
            return is_ready
            
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda url=blob_url, msg=error_msg: 
                      self.update_blob_status(url, 'error', f'エラー: {msg}'))
            logger.error(f"状態確認失敗 ({blob_name}): {error_msg}")
            logger.exception(e)
            return False  # エラー時は再試行しない
    
    def download_blob_phase2(self, blob_data: Dict[str, Any], semaphore: threading.Semaphore):
        """Phase 2のダウンロード処理（セマフォで同時実行数制限）"""
        blob_url = blob_data['url']
        blob_name = blob_data['blob_name']
        
        # セマフォ取得（最大同時ダウンロード数に達していれば待機）
        with semaphore:
            try:
                # 中断チェック
                if self.controller.cancel_event.is_set():
                    self.after(0, lambda url=blob_url: self.update_blob_status(
                        url, 'skipped', 'ユーザーによりスキップ'
                    ))
                    return
                
                # ステータス更新
                self.after(0, lambda url=blob_url: self.update_blob_status(
                    url, 'downloading', 'ダウンロード中...'
                ))
                
                # セッション情報をメモリから取得（ファイル読み込み不要）
                options = self.controller.session_options
                if not options:
                    logger.warning("セッション情報にoptionsが存在しません")
                    raise ValueError("optionsがセッション情報に存在しません")
                
                storage_account = blob_data['storage_account']
                subscription_id = blob_data.get('subscription')
                
                # アクセスキー取得
                account_key = self.controller.storage_key_manager.get_key(storage_account, subscription_id)
                if not account_key:
                    raise AccountKeyRetrievalError("アクセスキー取得失敗")
                
                # ダウンロード実行
                self.download_blob(blob_data, account_key, options)
                
                # 完了
                self.after(0, lambda url=blob_url: self.update_blob_status(
                    url, 'completed', '完了'
                ))
                self.after(0, lambda name=blob_name: self.add_log(f"完了: {name}"))
                
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda url=blob_url, msg=error_msg: 
                          self.update_blob_status(url, 'error', f'エラー: {msg}'))
                self.after(0, lambda name=blob_name, msg=error_msg: 
                          self.add_log(f"エラー ({name}): {msg}"))
                logger.error(f"ダウンロード失敗 ({blob_name}): {error_msg}")
                logger.exception(e)
    
    def populate_tree(self):
        """Treeviewにデータ追加"""
        blobs = self.controller.validated_blobs
        
        # ページング判定
        if len(blobs) > self.items_per_page:
            self.paging_frame.pack(side="top", pady=5)
            total_pages = (len(blobs) + self.items_per_page - 1) // self.items_per_page
            self.page_label.config(text=f"ページ: 1/{total_pages}")
        
        # 初回ページ表示
        self.update_tree_page()
    
    def update_tree_page(self):
        """Treeviewのページ更新"""
        # 既存アイテム削除
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        blobs = self.controller.validated_blobs
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(blobs))
        
        # ページ内のアイテム表示
        for blob_data in blobs[start_idx:end_idx]:
            status = blob_data.get('status', '待機')
            status_text = self._get_status_text(status)
            
            item_id = self.tree.insert('', 'end', values=(
                blob_data['blob_name'],
                blob_data['storage_account'],
                blob_data['container'],
                status_text,
                blob_data.get('progress_message', '')
            ), tags=(status_text,))
            
            self.tree_items[blob_data['url']] = item_id
        
        # ページングボタン更新
        total_pages = (len(blobs) + self.items_per_page - 1) // self.items_per_page
        self.page_label.config(text=f"ページ: {self.current_page + 1}/{total_pages}")
        
        if self.current_page > 0:
            self.prev_button.state(['!disabled'])
        else:
            self.prev_button.state(['disabled'])
            
        if self.current_page < total_pages - 1:
            self.next_button.state(['!disabled'])
        else:
            self.next_button.state(['disabled'])
    
    def prev_page(self):
        """前のページ"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_tree_page()
    
    def next_page(self):
        """次のページ"""
        blobs = self.controller.validated_blobs
        total_pages = (len(blobs) + self.items_per_page - 1) // self.items_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_tree_page()
    
    def _get_status_text(self, status: str) -> str:
        """ステータステキスト変換"""
        status_map = {
            'pending': '待機',
            'rehydrate_requested': '処理中',
            'rehydrating': '処理中',
            'rehydrate_completed': '処理中',
            'downloading': '処理中',
            'completed': '完了',
            'error': 'エラー',
            'skipped': 'スキップ'
        }
        return status_map.get(status, '待機')
    
    def update_blob_status(self, blob_url: str, status: str, message: str = ""):
        """Blobステータス更新"""
        # メモリ上のBlob情報も更新
        for blob in self.controller.validated_blobs:
            if blob['url'] == blob_url:
                blob['status'] = status
                if message:
                    blob['progress_message'] = message
                break
        
        # Treeview更新
        if blob_url in self.tree_items:
            item_id = self.tree_items[blob_url]
            if self.tree.exists(item_id):
                status_text = self._get_status_text(status)
                current_values = self.tree.item(item_id, 'values')
                self.tree.item(item_id, values=(
                    current_values[0],
                    current_values[1],
                    current_values[2],
                    status_text,
                    message
                ), tags=(status_text,))
        
        # ステートファイル更新
        if self.controller.current_state_file:
            self.controller.state_manager.update_blob_status(
                self.controller.current_state_file,
                blob_url,
                status,
                {'progress_message': message}
            )
    
    def add_log(self, message: str, level: str = 'info'):
        """ログ追加
        
        Args:
            message: ログメッセージ
            level: ログレベル ('info', 'warning', 'error', 'debug')
        """
        self.log_text.config(state='normal')
        
        # 最大行数チェック
        max_lines = self.controller.config.get('log_text_max_lines', 10000)
        current_lines = int(self.log_text.index('end-1c').split('.')[0])
        
        if current_lines > max_lines:
            # 古い行を削除
            self.log_text.delete('1.0', '2.0')
        
        # 新しいログ追加
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
        self.log_text.config(state='disabled')
        
        # ファイルログにも出力（レベルに応じて）
        level_lower = level.lower()
        if level_lower == 'error':
            logger.error(message)
        elif level_lower == 'warning':
            logger.warning(message)
        elif level_lower == 'debug':
            logger.debug(message)
        else:  # 'info'またはその他
            logger.info(message)
    
    def update_elapsed_time(self):
        """経過時間更新"""
        if self.start_time and not self.is_completed:
            elapsed = int(time.time() - self.start_time)
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            
            self.elapsed_time_label.config(text=f"経過時間: {hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # 1秒後に再実行
            self.timer_id = self.after(1000, self.update_elapsed_time)
    
    def process_blob(self, blob_data: Dict[str, Any]):
        """Blob処理（リハイドレート＆ダウンロード）"""
        blob_url = blob_data['url']
        
        try:
            # 中断チェック
            if self.controller.cancel_event.is_set():
                return
            
            # セッション情報をメモリから取得（ファイル読み込み不要）
            options = self.controller.session_options
            if not options:
                logger.warning("セッション情報にoptionsが存在しません")
                raise ValueError("optionsがセッション情報に存在しません")
            
            storage_account = blob_data['storage_account']
            container = blob_data['container']
            blob_name = blob_data['blob_name']
            subscription_id = blob_data.get('subscription')
            
            # アクセスキー取得
            account_key = self.controller.storage_key_manager.get_key(storage_account, subscription_id)
            if not account_key:
                raise AccountKeyRetrievalError("アクセスキー取得失敗")
            
            # Blob層の確認
            self.after(0, lambda url=blob_url: self.update_blob_status(url, 'checking', 'Blob層確認中...'))
            success, blob_info, error = self.controller.azure_cli.run([
                'storage', 'blob', 'show',
                '--account-name', storage_account,
                '--container-name', container,
                '--name', blob_name,
                '--account-key', account_key
            ])
            
            if not success:
                raise parse_azure_cli_error(error if error else "Blob情報取得失敗")
            
            blob_tier = blob_info.get('properties', {}).get('blobTier')
            archive_status = blob_info.get('properties', {}).get('archiveStatus')
            blob_type = blob_info.get('properties', {}).get('blobType', 'Unknown')
            
            # デバッグログ追加
            self.after(0, lambda name=blob_name, tier=blob_tier, status=archive_status, btype=blob_type: 
                      self.add_log(f"Blob層情報: {name} - 層={tier}, アーカイブ状態={status}, タイプ={btype}"))
            
            # AppendBlobの場合は層の概念がないためスキップ
            if blob_type == 'AppendBlob' or blob_tier is None:
                self.after(0, lambda url=blob_url: self.update_blob_status(
                    url, 'rehydrate_completed', 'AppendBlob（リハイドレート不要）'
                ))
                self.after(0, lambda name=blob_name: self.add_log(
                    f"AppendBlob検出: {name} - アクセス層の概念がないためスキップ"
                ))
                # ダウンロード処理へ直接進む
            
            # リハイドレート処理の判定
            # 1. すでにリハイドレート中の場合は待機のみ
            elif archive_status and 'rehydrate-pending' in archive_status:
                self.after(0, lambda url=blob_url: self.update_blob_status(url, 'rehydrate_requested', 'リハイドレート中（既存処理）'))
                self.after(0, lambda name=blob_name: self.add_log(f"既にリハイドレート中: {name}"))
                # リハイドレート完了待機
                self.wait_for_rehydration(blob_data, account_key)
                
            # 2. Archive層の場合はリハイドレート実行
            elif blob_tier == 'Archive':
                self.after(0, lambda url=blob_url: self.update_blob_status(url, 'rehydrate_requested', 'リハイドレート要求中...'))
                self.after(0, lambda name=blob_name: self.add_log(f"リハイドレート開始: {name}"))
            
                target_tier = options['target_tier']
                priority = options['priority']
                
                # Set Tierでリハイドレート
                success, data, error = self.controller.azure_cli.run([
                    'storage', 'blob', 'set-tier',
                    '--account-name', storage_account,
                    '--container-name', container,
                    '--name', blob_name,
                    '--tier', target_tier,
                    '--rehydrate-priority', priority,
                    '--account-key', account_key
                ])
                
                if not success:
                    raise parse_azure_cli_error(error if error else "Tier変更失敗")
                
                # リハイドレート完了待機
                self.wait_for_rehydration(blob_data, account_key)
                
            # 3. Hot/Cool/Cold/Premium層の場合はリハイドレート不要
            elif blob_tier in ['Hot', 'Cool', 'Cold', 'Premium', 'P10', 'P20', 'P30', 'P40', 'P50', 'P60', 'P70', 'P80']:
                self.after(0, lambda url=blob_url: self.update_blob_status(url, 'rehydrate_completed', f'{blob_tier}層（リハイドレート不要）'))
                self.after(0, lambda name=blob_name, tier=blob_tier: self.add_log(f"リハイドレート不要: {name} ({tier}層)"))
                
            # 4. 不明な層の場合はエラー
            else:
                raise AzureError(f"不明なBlob層: {blob_tier}。Blob情報の取得に失敗した可能性があります。")
            
            # ダウンロード処理
            if self.controller.cancel_event.is_set():
                return
            
            self.download_blob(blob_data, account_key, options)
            
            # 完了
            self.after(0, lambda url=blob_url: self.update_blob_status(url, 'completed', 'ダウンロード完了'))
            self.after(0, lambda name=blob_name: self.add_log(f"完了: {name}"))
            
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Blob処理エラー: {blob_url} - {error_msg}")
            
            # リトライ不要なエラーかチェック
            is_retryable = self._is_retryable_error(e)
            
            if is_retryable:
                # リトライ可能なエラーは通常通りエラー表示
                self.after(0, lambda url=blob_url, msg=error_msg: self.update_blob_status(url, 'error', f"エラー: {msg}"))
            else:
                # リトライ不要なエラー（即座に失敗としてマーク）
                self.after(0, lambda url=blob_url, msg=error_msg: self.update_blob_status(url, 'error', f"失敗: {msg} (リトライ不可)"))
                self.after(0, lambda name=blob_name, msg=error_msg: self.add_log(f"リトライ不可エラー: {name} - {msg}"))
            
            self.after(0, lambda name=blob_name, msg=error_msg: self.add_log(f"エラー: {name} - {msg}"))
        
        finally:
            # 全Blob完了チェック（UIスレッドで実行）
            self.after(100, self.check_all_completed)
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        エラーがリトライ可能か判定
        
        Args:
            error: 発生した例外
            
        Returns:
            リトライ可能な場合True
        """
        # リトライ不要なエラーのリスト
        non_retryable_errors = (
            BlobArchivedError,  # Blobがアーカイブ状態（copy_blob方式で発生）
            InvalidFormatError,  # 不正なフォーマット
            BlobNotFoundError,  # Blobが見つからない
            ContainerNotFoundError,  # コンテナが見つからない
            StorageAccountNotFoundError,  # ストレージアカウントが見つからない
            SubscriptionNotFoundError,  # サブスクリプションが見つからない
            InvalidResourceNameError,  # 不正なリソース名
            AuthenticationError,  # 認証エラー
            PermissionError  # 権限エラー
        )
        
        # エラーの型をチェック
        if isinstance(error, non_retryable_errors):
            return False
        
        # エラーメッセージに「Blobがアーカイブ状態」が含まれる場合
        error_msg = str(error).lower()
        if 'アーカイブ' in error_msg or 'archived' in error_msg or 'blobarchived' in error_msg:
            return False
        
        # その他のエラーはリトライ可能
        return True
    
    def wait_for_rehydration(self, blob_data: Dict, account_key: str):
        """リハイドレート完了待機"""
        blob_url = blob_data['url']
        storage_account = blob_data['storage_account']
        container = blob_data['container']
        blob_name = blob_data['blob_name']
        
        check_interval = self.controller.config.get('rehydrate_check_interval_seconds', 60)
        
        # 最初に現在の状態を確認（既にリハイドレート済みかチェック）
        success, data, error = self.controller.azure_cli.run([
            'storage', 'blob', 'show',
            '--account-name', storage_account,
            '--container-name', container,
            '--name', blob_name,
            '--account-key', account_key
        ])
        
        if success:
            blob_tier = data['properties']['blobTier']
            archive_status = data['properties'].get('archiveStatus')
            
            if archive_status is None and blob_tier in ['Hot', 'Cool']:
                # 既にリハイドレート済み
                self.after(0, lambda url=blob_url, name=blob_name: self.update_blob_status(url, 'rehydrate_completed', 'リハイドレート済み（スキップ）'))
                self.after(0, lambda name=blob_name: self.add_log(f"リハイドレート済み: {name} (スキップ)"))
                return
        
        self.after(0, lambda url=blob_url: self.update_blob_status(url, 'rehydrating', 'リハイドレート中...'))
        
        while not self.controller.cancel_event.is_set():
            time.sleep(check_interval)
            
            # ステータス確認
            success, data, error = self.controller.azure_cli.run([
                'storage', 'blob', 'show',
                '--account-name', storage_account,
                '--container-name', container,
                '--name', blob_name,
                '--account-key', account_key
            ])
            
            if not success:
                raise parse_azure_cli_error(error if error else "Blob情報取得失敗")
            
            blob_tier = data['properties']['blobTier']
            archive_status = data['properties'].get('archiveStatus')
            
            if archive_status is None and blob_tier in ['Hot', 'Cool']:
                # リハイドレート完了
                self.after(0, lambda url=blob_url: self.update_blob_status(url, 'rehydrate_completed', 'リハイドレート完了'))
                break
    
    def wait_for_copy(self, blob_data: Dict, container: str, blob_name: str, account_key: str):
        """コピー完了待機"""
        blob_url = blob_data['url']
        storage_account = blob_data['storage_account']
        
        check_interval = self.controller.config.get('rehydrate_check_interval_seconds', 60)
        
        self.after(0, lambda url=blob_url: self.update_blob_status(url, 'rehydrating', 'コピー中...'))
        
        while not self.controller.cancel_event.is_set():
            time.sleep(check_interval)
            
            # コピーステータス確認
            success, data, error = self.controller.azure_cli.run([
                'storage', 'blob', 'show',
                '--account-name', storage_account,
                '--container-name', container,
                '--name', blob_name,
                '--account-key', account_key
            ])
            
            if not success:
                raise parse_azure_cli_error(error if error else "コピー状態取得失敗")
            
            copy_status = data['properties'].get('copy', {}).get('status')
            
            if copy_status == 'success':
                # コピー完了
                self.after(0, lambda url=blob_url: self.update_blob_status(url, 'rehydrate_completed', 'コピー完了'))
                break
            elif copy_status in ['aborted', 'failed']:
                raise AzureError(f"コピー失敗: {copy_status}")
    
    def download_blob(self, blob_data: Dict, account_key: str, options: Dict):
        """Blobダウンロード"""
        blob_url = blob_data['url']
        storage_account = blob_data['storage_account']
        container = blob_data['container']
        blob_name = blob_data['blob_name']
        
        self.after(0, lambda url=blob_url: self.update_blob_status(url, 'downloading', 'ダウンロード中...'))
        
        try:
            # ダウンロード先パス決定
            download_dir = options['download_directory']
            path_structure = options['path_structure']
            
            # 実行日時フォルダを作成（session_idから日時部分を取得）
            if self.controller.session_id:
                session_folder = self.controller.session_id.split('_')[0]  # YYYYMMDD-HHMMSS形式
            else:
                # session_idが無い場合は現在時刻を使用
                from datetime import datetime
                session_folder = datetime.now().strftime('%Y%m%d-%H%M%S')
            base_download_dir = os.path.join(download_dir, session_folder)
        except Exception as e:
            raise AzureError(f"ダウンロードパス設定エラー: {e}")
        
        if path_structure == 'preserve':
            # 構造維持
            local_path = os.path.join(base_download_dir, container, blob_name)
        elif path_structure == 'flatten':
            # パスをファイル名化
            flat_name = f"{container}_{blob_name.replace('/', '_')}"
            local_path = os.path.join(base_download_dir, flat_name)
        else:  # single
            # 単一ファイル
            local_path = os.path.join(base_download_dir, os.path.basename(blob_name))
        
        # ディレクトリ作成
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # 同名ファイル存在チェック
        if os.path.exists(local_path):
            base, ext = os.path.splitext(local_path)
            counter = 1
            while os.path.exists(f"{base}({counter}){ext}") and counter < 100:
                counter += 1
            local_path = f"{base}({counter}){ext}"
        
        # ダウンロード
        blob_download_timeout = self.controller.config.get('blob_download_timeout', 3600)
        success, data, error = self.controller.azure_cli.run([
            'storage', 'blob', 'download',
            '--account-name', storage_account,
            '--container-name', container,
            '--name', blob_name,
            '--file', local_path,
            '--account-key', account_key,
            '--no-progress'
        ], timeout=blob_download_timeout)
        
        if not success:
            raise parse_azure_cli_error(error if error else "ダウンロード失敗")
        
        blob_data['local_path'] = local_path
    
    def check_all_completed(self):
        """全Blob完了チェック"""
        all_done = True
        for blob in self.controller.validated_blobs:
            status = blob.get('status', 'pending')
            if status not in ['completed', 'error', 'skipped']:
                all_done = False
                break
        
        logger.info(f"check_all_completed: all_done={all_done}, is_completed={self.is_completed}")
        
        if all_done and not self.is_completed:
            logger.info("全処理完了 - on_all_completed()を呼び出します")
            self.after(0, self.on_all_completed)
    
    def on_all_completed(self):
        """全処理完了時"""
        logger.info("on_all_completed: 処理完了画面への遷移開始")
        self.is_completed = True
        
        # プログレスバー停止
        self.progress_bar.stop()
        
        # 経過時間更新停止
        if self.timer_id:
            self.after_cancel(self.timer_id)
        
        # サマリ表示
        completed = sum(1 for b in self.controller.validated_blobs if b.get('status') == 'completed')
        errors = sum(1 for b in self.controller.validated_blobs if b.get('status') == 'error')
        skipped = sum(1 for b in self.controller.validated_blobs if b.get('status') == 'skipped')
        
        self.add_log("=" * 80)
        self.add_log(f"処理完了: 成功 {completed}件、エラー {errors}件、スキップ {skipped}件")
        self.add_log("=" * 80)
        
        # 完了画面へ遷移
        from .completion_screen import CompletionScreen
        logger.info("完了画面への遷移を予約しました（500ms後）")
        self.after(500, lambda: self.controller.show_frame(CompletionScreen))
    
    def cancel_process(self):
        """処理中断"""
        # リハイドレート開始済みか確認
        rehydrate_started = any(
            blob.get('status') in ['rehydrate_requested', 'rehydrating', 'rehydrate_completed', 'downloading']
            for blob in self.controller.validated_blobs
        )
        
        if rehydrate_started:
            result = messagebox.askokcancel(
                "確認",
                "Azure側のリハイドレート処理は継続されます。\n"
                "このアプリの監視を停止しますか？"
            )
            if not result:
                return
        
        self.controller.cancel_event.set()
        self.add_log("処理を中断しました")
        
        # プログレスバー停止
        self.progress_bar.stop()
        
        self.cancel_button.state(['disabled'])
        self.cancel_button.config(text=progress_texts.cancel_button_text_cancelled_alt)
