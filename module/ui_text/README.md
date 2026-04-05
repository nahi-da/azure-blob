# UI Text管理システム

このディレクトリには、GUIで表示されるすべてのテキストの定義が含まれています。

## 構造

```
module/ui_text/
├── __init__.py          # モジュールのエントリポイント
├── common.py            # 共通テキスト（ボタン、メッセージなど）
├── auth_texts.py        # 認証関連画面のテキスト
├── blob_texts.py        # Blob選択関連画面のテキスト
└── execution_texts.py   # 実行関連画面のテキスト
```

## 使用方法

### 1. インポート

各画面ファイルで必要なテキスト定義をインポートします：

```python
from ...ui_text.auth_texts import login_texts
from ...ui_text.common import common_texts
```

### 2. テキストの使用

テキスト定義から必要な文字列を取得します：

```python
# シンプルなテキスト
title = ttk.Label(self, text=login_texts.title)

# 動的テキスト（メソッドを使用）
message = login_texts.resume_session_message("session_123")
```

## テキストファイルの構成

各テキストファイルは以下のように構成されています：

### dataclassによる定義

```python
from dataclasses import dataclass

@dataclass
class LoginTexts:
    """User account login screen texts"""
    
    # Static texts
    title: str = "ユーザーアカウント認証"
    subtitle: str = "ユーザーアカウントでサインインします"
    
    # Methods for dynamic texts
    def resume_session_message(self, session_id: str) -> str:
        return f"⚠️ 未完了セッションの再開: {session_id}"

# Singleton instance
login_texts = LoginTexts()
```

## 利点

1. **一元管理**: すべてのテキストが専用ファイルに集約
2. **検索性**: IDEで簡単にテキストを検索・変更可能
3. **型安全性**: Pythonの型チェック機能が使える
4. **動的生成**: f-stringやメソッドで動的なテキストも生成可能
5. **構造化**: 画面のモジュールごとにファイルを分割
6. **拡張性**: 将来的に多言語対応も容易

## テキストの変更方法

### 例: ボタンのテキストを変更

1. 該当するテキストファイルを開く（例: `auth_texts.py`）
2. 対応するクラスとフィールドを見つける
3. 値を変更する

```python
@dataclass
class LoginTexts:
    signin_button: str = "ログイン"  # "サインイン" から変更
```

### 例: 新しいテキストを追加

```python
@dataclass
class LoginTexts:
    # 既存のフィールド...
    
    # 新しいフィールドを追加
    help_text: str = "ヘルプが必要な場合はこちら"
```

画面ファイルで使用：

```python
help_label = ttk.Label(self, text=login_texts.help_text)
```

## 多言語対応への拡張

将来的に多言語対応する場合は、以下のような構造に拡張できます：

```
module/ui_text/
├── ja/  # 日本語
│   ├── auth_texts.py
│   ├── blob_texts.py
│   └── execution_texts.py
└── en/  # 英語
    ├── auth_texts.py
    ├── blob_texts.py
    └── execution_texts.py
```

## 変換完了ステータス

✅ **全画面変換完了** (2026年2月)

すべてのGUI画面（14画面）でハードコードされていた日本語テキストをテキスト定義に変換しました。

### 変換済み画面一覧

#### 認証関連（5画面）
- ✅ [auth_method_screen.py](../ui/auth/auth_method_screen.py) - 認証方法選択
- ✅ [login_screen.py](../ui/auth/login_screen.py) - Azure CLIログイン  
- ✅ [existing_login_screen.py](../ui/auth/existing_login_screen.py) - 既存ログイン/サブスクリプション選択
- ✅ [sp_selection_screen.py](../ui/auth/sp_selection_screen.py) - サービスプリンシパル選択
- ✅ [profile_editor_screen.py](../ui/auth/profile_editor_screen.py) - プロファイル編集

#### Blob選択関連（6画面）
- ✅ [blob_selection_method_screen.py](../ui/blob_selection/blob_selection_method_screen.py) - Blob選択方法
- ✅ [blob_url_input_screen.py](../ui/blob_selection/blob_url_input_screen.py) - Blob URL入力
- ✅ [template_selection_screen.py](../ui/blob_selection/template_selection_screen.py) - テンプレート選択
- ✅ [template_editor_screen.py](../ui/blob_selection/template_editor_screen.py) - テンプレート編集（約90フィールド）
- ✅ [template_expansion_screen.py](../ui/blob_selection/template_expansion_screen.py) - プレースホルダー展開（約80フィールド）
- ✅ [template_search_result_screen.py](../ui/blob_selection/template_search_result_screen.py) - 検索結果

#### 実行関連（3画面）
- ✅ [options_screen.py](../ui/execution/options_screen.py) - オプション選択
- ✅ [progress_screen.py](../ui/execution/progress_screen.py) - 処理進捗
- ✅ [completion_screen.py](../ui/execution/completion_screen.py) - 処理完了

### 統計情報
- **変換されたテキスト総数**: 約350個以上
- **テキスト定義クラス数**: 14クラス
- **最大フィールド数クラス**: TemplateExpansionTexts（約80フィールド）、TemplateEditorTexts（約90フィールド）
- **変換完了率**: 100% （`text="[日本語]+"` パターンのgrep検索結果ゼロ）

### 変換対象となったウィジェットタイプ
- `ttk.Label` / `tk.Label` - すべてのラベルテキスト
- `ttk.Button` - すべてのボタンテキスト  
- `ttk.Radiobutton` - ラジオボタンのテキスト
- `ttk.Checkbutton` - チェックボックスのテキスト
- `ttk.LabelFrame` - フレームのタイトル
- `.config(text=...)` - 動的テキスト変更
- その他 - ダイアログメッセージなど

## サンプル変換済み画面

以下の画面ですでにテキスト定義を使用しています：

- [auth_method_screen.py](../ui/auth/auth_method_screen.py) - 認証方法選択画面
- [blob_selection_method_screen.py](../ui/blob_selection/blob_selection_method_screen.py) - Blob選択方法画面
- [options_screen.py](../ui/execution/options_screen.py) - オプション選択画面

これらを参考に、他の画面も順次変換していくことができます。
