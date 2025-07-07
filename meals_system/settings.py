import os
from pathlib import Path
import dj_database_url
import django_admin_listfilter_dropdown
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'your-secret-key-very-secret'
DEBUG = True
ALLOWED_HOSTS = ["*"]
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
INSTALLED_APPS = [
    'django_admin_listfilter_dropdown',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'meals',                # Ứng dụng meals
    'crispy_forms',         # Crispy forms (tuỳ chọn)
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'meals_system.urls'
STATIC_ROOT = BASE_DIR / "staticfiles"
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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
CSRF_TRUSTED_ORIGINS = [
  'https://mealspj-production.up.railway.app',
  'https://meal.hoahuongduong.org/'
]
WSGI_APPLICATION = 'meals_system.wsgi.application'

if os.getenv("DATABASE_URL"):
    # Trên Railway: dùng Postgres với SSL
    DATABASES = {
        "default": dj_database_url.config(
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    # Chạy local: fallback về SQLite
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "site.db",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    # Cấu hình validator (tuỳ chọn)
]

LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
