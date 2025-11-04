"""
WSGI config for jpjtorusaro project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# 本番環境では環境変数から設定モジュールを取得
# デフォルトは開発用設定
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'jpjtorusaro.settings')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)

application = get_wsgi_application()
