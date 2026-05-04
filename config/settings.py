import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IS_FROZEN = getattr(sys, 'frozen', False)
FROZEN_BASE_DIR = Path(getattr(sys, '_MEIPASS', BASE_DIR))
RUNTIME_DIR = Path(os.getenv('MPT_RUNTIME_DIR', Path(os.getenv('LOCALAPPDATA', BASE_DIR)) / 'MPT Journal'))
if IS_FROZEN:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_DIR = FROZEN_BASE_DIR if IS_FROZEN else BASE_DIR

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key-change-me')
DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'core',
    'users',
    'grading',
    'reports',
    'integration',
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [PROJECT_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.role_flags',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

if os.getenv('DB_ENGINE', 'postgres').lower() == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'performance_db'),
            'USER': os.getenv('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', '1'),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': (RUNTIME_DIR if IS_FROZEN else BASE_DIR) / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = (RUNTIME_DIR if IS_FROZEN else BASE_DIR) / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = (RUNTIME_DIR if IS_FROZEN else BASE_DIR) / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': int(os.getenv('API_PAGE_SIZE', '25')),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Журнал МПТ API',
    'DESCRIPTION': 'API для учебного журнала, пользователей, курсов, оценок, посещаемости и чатов.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

MPT_SYNC_BASE_URL = os.getenv('MPT_SYNC_BASE_URL', 'https://mpt.ru')
MPT_SYNC_SCHEDULE_PATH = os.getenv('MPT_SYNC_SCHEDULE_PATH', '/raspisanie/')
MPT_SYNC_TIMEOUT = int(os.getenv('MPT_SYNC_TIMEOUT', '15'))
MPT_SYNC_DELAY_SECONDS = float(os.getenv('MPT_SYNC_DELAY_SECONDS', '0.5'))
MPT_SYNC_USER_AGENT = os.getenv('MPT_SYNC_USER_AGENT', 'mpt-progress-tracker/1.0 (educational project)')
MPT_DEFAULT_SEMESTER = os.getenv('MPT_DEFAULT_SEMESTER', '2025/2026-2')

