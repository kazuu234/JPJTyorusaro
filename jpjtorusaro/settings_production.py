"""
Django settings for jpjtorusaro project - Production settings for ColorfulBox
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# 環境変数から取得（設定されていない場合は開発用キーを使用）
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-#kq28zdp0l#ru&g7@)&%qm2_9-#r&n$i93wb%t)w-t*@is&02#')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# ColorfulBoxのドメインを許可
# 実際のドメインに合わせて変更してください
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    # 以下に実際のドメインを追加
    # 'example.com',
    # 'www.example.com',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'application',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'jpjtorusaro.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'jpjtorusaro.wsgi.application'

# Database
# ColorfulBoxではMySQLまたはPostgreSQLを使用
# cPanelの「リモートMySQL」または「PostgreSQL」からデータベース情報を取得
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # または 'django.db.backends.postgresql'
        'NAME': os.environ.get('DB_NAME', ''),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),  # MySQL: 3306, PostgreSQL: 5432
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# ColorfulBoxでは、public_html配下にstaticフォルダを作成
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
# ColorfulBoxでは、public_html配下にmediaフォルダを作成
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 管理画面用パスワード
# 環境変数から取得（設定されていない場合はデフォルト値を使用）
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '11223456778899#JP')

# セキュリティ設定
# ColorfulBoxでSSL証明書を設定している場合のみ有効化
# SECURE_SSL_REDIRECT = True  # HTTPSリダイレクト
# SESSION_COOKIE_SECURE = True  # HTTPS接続のみでCookieを送信
# CSRF_COOKIE_SECURE = True  # HTTPS接続のみでCSRF Cookieを送信
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ログ設定
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

