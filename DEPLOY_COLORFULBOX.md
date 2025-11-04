# ColorfulBoxへのデプロイ手順

このDjangoアプリケーションをColorfulBoxに配置するための手順です。

## 前提条件

- ColorfulBoxのアカウントを取得済み
- SSHアクセス可能（推奨）
- cPanelにアクセス可能
- Python 3.xが利用可能

## デプロイ手順

### 1. 環境変数の設定

cPanelの「環境変数」設定で以下の変数を設定します：

```
DJANGO_SECRET_KEY=あなたの秘密鍵（ランダムな文字列）
ADMIN_PASSWORD=11223456778899#JP
DB_NAME=データベース名
DB_USER=データベースユーザー名
DB_PASSWORD=データベースパスワード
DB_HOST=localhost（またはリモートホスト）
DB_PORT=3306（MySQLの場合）または5432（PostgreSQLの場合）
```

### 2. データベースの作成

cPanelの「MySQLデータベース」または「PostgreSQLデータベース」から：
1. データベースを作成
2. ユーザーを作成してデータベースにアクセス権を付与
3. データベース情報を環境変数に設定

### 3. ファイルのアップロード

SSHまたはFTPで以下のファイルをアップロード：

```
jpjtorusaro/
  - settings_production.py  （本番用設定ファイル）
  - wsgi.py
application/
  - （すべてのアプリケーションファイル）
manage.py
requirements.txt
```

**推奨ディレクトリ構造：**
```
/home/ユーザー名/
  - project/          # Djangoプロジェクト
    - jpjtorusaro/
    - application/
    - manage.py
    - requirements.txt
  - public_html/       # Web公開ディレクトリ
    - static/          # 静的ファイル
    - media/           # メディアファイル
```

### 4. Python環境のセットアップ

SSHでサーバーに接続し、以下を実行：

```bash
cd ~/project
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 5. 設定ファイルの適用

`jpjtorusaro/wsgi.py`を以下のように変更：

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jpjtorusaro.settings_production')

application = get_wsgi_application()
```

### 6. データベースのマイグレーション

```bash
python manage.py migrate --settings=jpjtorusaro.settings_production
```

### 7. 静的ファイルの収集

```bash
python manage.py collectstatic --noinput --settings=jpjtorusaro.settings_production
```

### 8. cPanelでのPythonアプリケーション設定

cPanelの「Pythonアプリケーション」から：
1. 「Create Application」をクリック
2. 以下の設定：
   - Python Version: 3.x（利用可能な最新版）
   - Application Root: `/home/ユーザー名/project`
   - Application URL: `/`（またはサブディレクトリ）
   - Application Entry Point: `jpjtorusaro.wsgi:application`
   - Application Startup File: `passenger_wsgi.py`（自動生成）

### 9. passenger_wsgi.pyの作成

`public_html/`またはアプリケーションディレクトリに`passenger_wsgi.py`を作成：

```python
import sys
import os

# プロジェクトディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, '/home/ユーザー名/project')  # 実際のパスに変更

# 環境変数を設定
os.environ['DJANGO_SETTINGS_MODULE'] = 'jpjtorusaro.settings_production'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 10. ALLOWED_HOSTSの設定

`settings_production.py`の`ALLOWED_HOSTS`に実際のドメインを追加：

```python
ALLOWED_HOSTS = [
    'your-domain.com',
    'www.your-domain.com',
]
```

### 11. 静的ファイルとメディアファイルの設定

`.htaccess`ファイルを作成（Apacheの場合）またはcPanelの設定で：
- 静的ファイルを正しく配信
- メディアファイルへのアクセスを許可

### 12. パーミッションの設定

```bash
chmod 755 ~/project
chmod 755 ~/public_html
chmod 644 ~/project/manage.py
```

### 13. 動作確認

ブラウザでアクセスして動作確認：
- 申し込みフォームが表示されるか
- 管理画面にログインできるか
- CSVアップロードが動作するか

## トラブルシューティング

### エラー: ModuleNotFoundError
- Pythonパスが正しく設定されているか確認
- 仮想環境が有効化されているか確認

### エラー: Database connection failed
- データベースの認証情報が正しいか確認
- データベースホストが正しいか確認

### 静的ファイルが表示されない
- `collectstatic`が実行されているか確認
- `STATIC_ROOT`と`STATIC_URL`の設定を確認

### 500エラーの場合
- `django.log`ファイルを確認
- `DEBUG = False`の状態で詳細エラーを確認する場合は一時的に`True`に変更

## セキュリティに関する注意事項

1. **SECRET_KEY**: 必ず環境変数から取得し、本番環境では開発用の値を使用しない
2. **ADMIN_PASSWORD**: 強力なパスワードに変更することを推奨
3. **DEBUG**: 本番環境では必ず`False`に設定
4. **ALLOWED_HOSTS**: 実際のドメインのみを指定

## 追加の設定

### ログファイルの管理

定期的にログファイルを削除またはローテートしてください。

### バックアップ

ColorfulBoxの自動バックアップ機能を有効化し、定期的にデータベースとメディアファイルをバックアップしてください。

