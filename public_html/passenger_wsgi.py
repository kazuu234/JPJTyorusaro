"""
Passenger WSGI file for ColorfulBox deployment
このファイルをpublic_html/またはアプリケーションのルートディレクトリに配置してください
"""

import sys
import os

# プロジェクトディレクトリをパスに追加
# 実際のパスに合わせて変更してください
project_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(project_dir)
project_path = os.path.join(parent_dir, 'project')  # Djangoプロジェクトのパス

sys.path.insert(0, project_path)
sys.path.insert(0, project_dir)

# 環境変数を設定
os.environ['DJANGO_SETTINGS_MODULE'] = 'jpjtorusaro.settings_production'

# Django WSGIアプリケーションをインポート
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

