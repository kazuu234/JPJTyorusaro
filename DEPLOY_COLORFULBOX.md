# ColorfulBoxへのデプロイ手順

このDjangoアプリケーションをColorfulBoxに配置するための手順です。

## 前提条件

- ColorfulBoxのアカウントを取得済み
- SSHアクセス可能（推奨）
- cPanelにアクセス可能
- Python 3.xが利用可能

## デプロイ手順

### 0. サブドメインの設定（WordPressと共存する場合）

既にWordPressが`public_html`に設定されている場合、サブドメインを作成してDjangoアプリケーションを配置します。

**cPanelの「サブドメイン」から：**
1. サブドメインを作成（例: `jjyorusaro.your-domain.com`）
2. ドキュメントルートを `/home/rhtkvdkh/public_html/jjyorusaro/` に設定
3. サブドメインの設定を保存

**ディレクトリ構造：**
```
/home/rhtkvdkh/
  - project/                    # Djangoプロジェクト
    - jjyorusaro/
      - jpjtorusaro/
        - settings_production.py
        - wsgi.py
      - application/
      - manage.py
      - requirements.txt
      - venv/                   # 仮想環境（オプション）
  - public_html/               # Web公開ディレクトリ（WordPress用）
    - (WordPressファイル)
    - jjyorusaro/              # サブドメイン用ディレクトリ
      - passenger_wsgi.py       # Passenger WSGI設定ファイル
      - .htaccess              # Apache設定ファイル（オプション）
      - static/                 # 静的ファイル（シンボリックリンク推奨）
      - media/                  # メディアファイル（シンボリックリンク推奨）
```

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
DJANGO_SETTINGS_MODULE=jpjtorusaro.settings_production
```

### 2. データベースの作成

cPanelの「MySQLデータベース」または「PostgreSQLデータベース」から：
1. データベースを作成
2. ユーザーを作成してデータベースにアクセス権を付与
3. データベース情報を環境変数に設定

### 3. ファイルのアップロード

SSHまたはFTPで以下のファイルをアップロード：

**Djangoプロジェクトを `/home/rhtkvdkh/project/jjyorusaro/` に配置：**
```
/home/rhtkvdkh/project/jjyorusaro/
  - jpjtorusaro/
    - settings_production.py  （本番用設定ファイル）
    - wsgi.py
  - application/
    - （すべてのアプリケーションファイル）
  - manage.py
  - requirements.txt
```

**サブドメイン用ディレクトリに設定ファイルを配置：**
```
/home/rhtkvdkh/public_html/jjyorusaro/
  - passenger_wsgi.py
  - .htaccess（オプション）
```

### 4. Python環境のセットアップ

SSHでサーバーに接続し、以下を実行：

```bash
cd ~/project/jjyorusaro
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. 設定ファイルの適用

`jpjtorusaro/wsgi.py`は既に設定されているはずですが、確認：

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jpjtorusaro.settings_production')

application = get_wsgi_application()
```

### 6. データベースのマイグレーション

```bash
cd ~/project/jjyorusaro
source venv/bin/activate  # 仮想環境を有効化
python manage.py migrate --settings=jpjtorusaro.settings_production
```

### 7. 静的ファイルの収集

```bash
python manage.py collectstatic --noinput --settings=jpjtorusaro.settings_production
```

これにより、`settings_production.py`で指定した`STATIC_ROOT`に静的ファイルが集約されます。

**静的ファイルとメディアファイルのシンボリックリンク作成（推奨）：**

```bash
# 静的ファイルのシンボリックリンク
ln -s ~/project/jjyorusaro/staticfiles ~/public_html/jjyorusaro/static

# メディアファイルのシンボリックリンク
ln -s ~/project/jjyorusaro/media ~/public_html/jjyorusaro/media
```

### 8. passenger_wsgi.pyの作成

`/home/rhtkvdkh/public_html/jjyorusaro/passenger_wsgi.py`を作成：

```python
import sys
import os

# プロジェクトディレクトリをパスに追加
project_dir = '/home/rhtkvdkh/project/jjyorusaro'  # 実際のパスに変更
sys.path.insert(0, project_dir)

# 環境変数を設定
os.environ['DJANGO_SETTINGS_MODULE'] = 'jpjtorusaro.settings_production'

# 仮想環境のパスを追加（仮想環境を使用する場合）
venv_python = os.path.join(project_dir, 'venv', 'lib', 'python3.x', 'site-packages')
if os.path.exists(venv_python):
    sys.path.insert(0, venv_python)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**注意:** `python3.x`の部分は実際のPythonバージョンに合わせて変更してください（例: `python3.11`, `python3.12`など）。

### 9. cPanelでのPythonアプリケーション設定

cPanelの「Pythonアプリケーション」から：
1. 「Create Application」をクリック
2. 以下の設定：
   - Python Version: 3.x（利用可能な最新版）
   - Application Root: `/home/rhtkvdkh/public_html/jjyorusaro`
   - Application URL: `/`（サブドメインのルート）
   - Application Entry Point: `passenger_wsgi:application`
   - Application Startup File: `passenger_wsgi.py`（自動生成される場合があります）

**重要:** Application Rootは`public_html/jjyorusaro`を指定し、`passenger_wsgi.py`がそのディレクトリにあることを確認してください。

### 10. ALLOWED_HOSTSの設定

`settings_production.py`の`ALLOWED_HOSTS`にサブドメインを追加：

```python
ALLOWED_HOSTS = [
    'jjyorusaro.your-domain.com',  # 実際のサブドメインに変更
    'www.jjyorusaro.your-domain.com',  # 必要に応じて
]
```

### 11. 静的ファイルとメディアファイルの設定

**settings_production.pyの確認：**

```python
# 静的ファイル
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# メディアファイル
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
```

**`.htaccess`ファイルの作成（オプション）：**

`/home/rhtkvdkh/public_html/jjyorusaro/.htaccess`を作成：

```apache
# Django静的ファイルとメディアファイルの配信
Alias /static /home/rhtkvdkh/public_html/jjyorusaro/static
Alias /media /home/rhtkvdkh/public_html/jjyorusaro/media

<Directory /home/rhtkvdkh/public_html/jjyorusaro/static>
    Require all granted
</Directory>

<Directory /home/rhtkvdkh/public_html/jjyorusaro/media>
    Require all granted
</Directory>

# DjangoのURLルーティング
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteBase /
    RewriteRule ^(static|media)/ - [L]
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule ^(.*)$ passenger_wsgi.py/$1 [L]
</IfModule>
```

### 12. パーミッションの設定

```bash
# プロジェクトディレクトリ
chmod 755 ~/project
chmod 755 ~/project/jjyorusaro
chmod 644 ~/project/jjyorusaro/manage.py

# サブドメイン用ディレクトリ
chmod 755 ~/public_html/jjyorusaro
chmod 644 ~/public_html/jjyorusaro/passenger_wsgi.py

# 静的ファイルとメディアファイル
chmod 755 ~/project/jjyorusaro/staticfiles
chmod 755 ~/project/jjyorusaro/media
```

### 13. 動作確認

ブラウザでサブドメイン（例: `https://jjyorusaro.your-domain.com`）にアクセスして動作確認：
- 申し込みフォームが表示されるか
- 管理画面にログインできるか（`https://jjyorusaro.your-domain.com/admin/login/`）
- CSVアップロードが動作するか
- 静的ファイル（CSS、JavaScript）が正しく読み込まれるか
- メディアファイルがアップロードできるか

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

