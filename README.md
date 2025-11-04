# 夜遊びサロン申し込みシステム

Joy Journeyの定期購入利用者向けの夜遊びサロン申し込みフォームです。

## 機能

- **Webフォーム**: 夜遊びサロンへの申し込みフォーム
- **定期購入チェック**: Joy Journeyの定期購入の利用確認処理
- **アクセス付与**: 確認後、夜遊びサロンへのアクセスを付与
- **審査管理**: 確認できない場合の手動審査・承認機能
- **管理画面**: Django管理画面でデータの確認・管理

## セットアップ

### 1. 仮想環境の作成（推奨）

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. データベースのマイグレーション

```bash
python manage.py migrate
```

### 4. 管理者ユーザーの作成

```bash
python manage.py createsuperuser
```

### 5. 開発サーバーの起動

```bash
python manage.py runserver
```

ブラウザで `http://127.0.0.1:8000/` にアクセスしてください。

## 使用方法

### 定期購入ユーザーの登録

管理画面（`http://127.0.0.1:8000/admin/`）から、`SubscriptionUser`モデルにJoy Journeyの定期購入の利用者情報を登録してください。

- メールアドレス
- サブスクリプションID
- 有効フラグ（is_active）

### 申し込みフォーム

`http://127.0.0.1:8000/` にアクセスして、申し込みフォームから以下を入力：

1. お名前
2. メールアドレス
3. サブスクリプションID

### 処理フロー

1. **自動確認**: 入力されたメールアドレスとサブスクリプションIDで`SubscriptionUser`を検索
2. **確認成功**: 自動的にアクセストークンを生成し、アクセスを付与
3. **確認失敗**: 審査待ち状態となり、管理者が手動で確認・承認が必要

### 管理画面機能

- 申し込み一覧の確認（`/list/`）
- 申し込み詳細の確認（`/detail/<id>/`）
- 手動でのアクセス付与
- バッチ処理による一括アクセス付与

## モデル構成

### SubscriptionUser（定期購入ユーザー）
- Joy Journeyの定期購入の利用者情報を管理

### SalonApplication（サロン申し込み）
- 申し込み情報
- 定期購入確認結果
- アクセス付与情報
- ステータス管理

## カスタマイズ

### 定期購入チェック処理のカスタマイズ

`application/views.py`の`verify_subscription()`関数を修正して、外部APIとの連携などを追加できます。


## 注意事項

- 本番環境では`SECRET_KEY`を変更してください
- `DEBUG = False`に設定してください
- 適切なデータベース（PostgreSQL推奨）を使用してください
- CSRF保護、セキュリティ設定を確認してください

