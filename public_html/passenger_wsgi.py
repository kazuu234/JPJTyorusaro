"""
Passenger WSGI file for ColorfulBox deployment
このファイルをpublic_html/jjyorusaro/に配置してください
サブドメイン用の設定です
"""

import sys
import os

# プロジェクトディレクトリをパスに追加
# 実際のパスに合わせて変更してください
project_dir = '/home/rhtkvdkh/project/jjyorusaro'
sys.path.insert(0, project_dir)

# 環境変数を設定
os.environ['DJANGO_SETTINGS_MODULE'] = 'jpjtorusaro.settings_production'

# 仮想環境のパスを追加（仮想環境を使用する場合）
venv_python = os.path.join(project_dir, 'venv', 'lib', 'python3.x', 'site-packages')
if os.path.exists(venv_python):
    sys.path.insert(0, venv_python)

# Django WSGIアプリケーションをインポート
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

