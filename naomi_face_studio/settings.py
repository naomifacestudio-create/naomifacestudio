"""
Django settings for naomi_face_studio project.
"""

import os
from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False)
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', 'naomifacestudio.com', 'www.naomifacestudio.com'])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    
    # Third party apps
    'modeltranslation',
    'ckeditor',
    'ckeditor_uploader',
    'storages',
    'import_export',
    'honeypot',
    
    # Local apps
    'core',
    'treatments',
    'blogs',
    'reservations',
    'gift_vouchers',
    'contacts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'naomi_face_studio.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'naomi_face_studio.wsgi.application'

# Database
# Use DATABASE_URL if available (Render, Heroku, etc.), otherwise use individual variables or SQLite
if env('DATABASE_URL', default=None):
    # Parse DATABASE_URL (used by Render, Heroku, etc.)
    DATABASES = {
        'default': env.db()
    }
elif env.bool('USE_POSTGRES', default=False):
    # Fallback to individual database variables
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('DB_NAME', default='naomi_face_studio'),
            'USER': env('DB_USER', default='postgres'),
            'PASSWORD': env('DB_PASSWORD', default=''),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }
else:
    # SQLite for local development (no setup required)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
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
LANGUAGE_CODE = 'hr'
TIME_ZONE = 'Europe/Zagreb'
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('hr', 'Croatian'),
    ('en', 'English'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudflare R2 Storage Configuration
USE_R2 = env.bool('USE_R2', default=False)

if USE_R2:
    AWS_ACCESS_KEY_ID = env('R2_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = env('R2_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = env('R2_BUCKET_NAME', default='')
    AWS_S3_ENDPOINT_URL = env('R2_ENDPOINT_URL', default='')
    
    # Custom domain for R2 (should be just the domain name, e.g., 'media.naomifacestudio.com')
    # Our custom storage class will use this if set
    custom_domain = env('R2_CUSTOM_DOMAIN', default='')
    if custom_domain:
        # Remove https:// if accidentally included, and strip trailing slash
        AWS_S3_CUSTOM_DOMAIN = custom_domain.replace('https://', '').replace('http://', '').rstrip('/')
    else:
        AWS_S3_CUSTOM_DOMAIN = None  # Explicitly None when not set
    
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = 'public-read'
    AWS_LOCATION = 'media'
    AWS_S3_USE_SSL = True
    AWS_S3_VERIFY = True
    
    # Use R2 for media files with custom storage class that handles custom domains
    DEFAULT_FILE_STORAGE = 'naomi_face_studio.storage.R2Storage'
    # Keep static files local or use WhiteNoise
    # STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
    
    # Set MEDIA_URL for reference (storage backend generates URLs, but this helps with consistency)
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
    else:
        MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/{AWS_LOCATION}/'
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CKEditor Configuration
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'width': '100%',
        'extraPlugins': ','.join([
            'uploadimage',
            'div',
            'autolink',
            'autoembed',
            'embedsemantic',
            'autogrow',
            'widget',
            'lineutils',
            'clipboard',
            'dialog',
            'dialogui',
            'elementspath'
        ]),
        'filebrowserWindowHeight': 725,
        'filebrowserWindowWidth': 940,
        'toolbarCanCollapse': True,
        'mathJaxLib': '//cdn.ckeditor.com/4.6.1/standard/plugins/mathjax/lib/mathjax/2.7.0/MathJax.js?config=TeX-AMS_HTML',
        'tabSpaces': 4,
        'extraPlugins': ','.join([
            'uploadimage',
            'image2',
        ]),
    },
}

# Email Configuration (SendGrid)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = env('SENDGRID_API_KEY', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='info@naomifacestudio.com')
ADMIN_EMAIL = env('ADMIN_EMAIL', default='info@naomifacestudio.com')

# Honeypot Configuration
HONEYPOT_FIELD_NAME = 'website'

# Rate Limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Session Configuration
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Site Configuration
SITE_URL = env('SITE_URL', default='https://www.naomifacestudio.com')
SITE_NAME = 'Naomi Face Studio'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO' if not DEBUG else 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django_errors.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO' if not DEBUG else 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO' if not DEBUG else 'DEBUG',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',  # Set to DEBUG to see all SQL queries
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Application-specific loggers
        'core': {
            'handlers': ['console'],
            'level': 'INFO' if not DEBUG else 'DEBUG',
            'propagate': False,
        },
        'treatments': {
            'handlers': ['console'],
            'level': 'INFO' if not DEBUG else 'DEBUG',
            'propagate': False,
        },
        'blogs': {
            'handlers': ['console'],
            'level': 'INFO' if not DEBUG else 'DEBUG',
            'propagate': False,
        },
        'reservations': {
            'handlers': ['console'],
            'level': 'INFO' if not DEBUG else 'DEBUG',
            'propagate': False,
        },
        'gift_vouchers': {
            'handlers': ['console'],
            'level': 'INFO' if not DEBUG else 'DEBUG',
            'propagate': False,
        },
        'contacts': {
            'handlers': ['console'],
            'level': 'INFO' if not DEBUG else 'DEBUG',
            'propagate': False,
        },
        # Third-party loggers
        'boto3': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'botocore': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'storages': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Log startup configuration (after logging is configured)
import logging
startup_logger = logging.getLogger('django')
startup_logger.info("=" * 60)
startup_logger.info("Naomi Face Studio - Application Starting")
startup_logger.info("=" * 60)
startup_logger.info(f"DEBUG Mode: {DEBUG}")
db_engine = DATABASES['default']['ENGINE']
is_postgres = 'postgresql' in db_engine
startup_logger.info(f"Database: {'PostgreSQL' if is_postgres else 'SQLite'}")
if is_postgres:
    startup_logger.info(f"Database Name: {DATABASES['default']['NAME']}")
    startup_logger.info(f"Database Host: {DATABASES['default'].get('HOST', 'N/A')}")
    startup_logger.info(f"R2 Storage Enabled: {USE_R2}")
if USE_R2:
    startup_logger.info(f"R2 Bucket: {AWS_STORAGE_BUCKET_NAME}")
    startup_logger.info(f"R2 Endpoint: {AWS_S3_ENDPOINT_URL}")
    startup_logger.info(f"R2 Custom Domain: {AWS_S3_CUSTOM_DOMAIN if AWS_S3_CUSTOM_DOMAIN else 'Not set (using endpoint)'}")
    startup_logger.info(f"Media URL: {MEDIA_URL}")
    startup_logger.info(f"Default Storage: {DEFAULT_FILE_STORAGE}")
startup_logger.info(f"Email Backend: {EMAIL_BACKEND}")
startup_logger.info(f"From Email: {DEFAULT_FROM_EMAIL}")
startup_logger.info(f"Admin Email: {ADMIN_EMAIL}")
startup_logger.info(f"Site URL: {SITE_URL}")
startup_logger.info(f"Allowed Hosts: {', '.join(ALLOWED_HOSTS)}")
startup_logger.info("=" * 60)

