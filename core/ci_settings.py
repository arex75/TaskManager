"""
CI/CD settings for GitHub Actions
"""

from .settings import *
from datetime import timedelta
import tempfile

# Use SQLite for CI/CD (faster and no external dependencies)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory database for faster tests
        'OPTIONS': {
            'timeout': 20,  # Increase timeout for in-memory DB
        }
    }
}

# Celery settings for CI/CD (if you use Celery)
CELERY_TASK_ALWAYS_EAGER = True  # Run tasks synchronously during tests
CELERY_TASK_EAGER_PROPAGATES = True

# Disable Celery Beat during tests
CELERY_BEAT_SCHEDULER = None

# Disable logging during tests for cleaner output
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    },
}

# Use a simple cache backend for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Disable static files collection during tests
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Test-specific settings
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Disable password hashing during tests for speed
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable debug toolbar and other development tools
DEBUG = False

# Use in-memory file storage for tests
DEFAULT_FILE_STORAGE = 'django.core.files.storage.InMemoryStorage'
MEDIA_ROOT = tempfile.mkdtemp()

# Disable email sending during tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Configure OAuth providers for testing
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP_ID': 'test-google-client-id',
        'APP_SECRET': 'test-google-client-secret',
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    },
    'github': {
        'APP_ID': 'test-github-client-id',
        'APP_SECRET': 'test-github-client-secret',
        'SCOPE': [
            'user:email',
            'read:user',
        ],
    }
}

# Use simple JWT settings for tests
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# Security settings for CI (fix warnings)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_SSL_REDIRECT = False  # Not needed for CI
SECRET_KEY = "a-test-secret-key-for-ci-that-is-long-enough-and-random-1234567890abcdefghijklmnopqrstuvwxyz"
SESSION_COOKIE_SECURE = False  # Not needed for CI
CSRF_COOKIE_SECURE = False  # Not needed for CI

# Disable password validation during tests for speed
AUTH_PASSWORD_VALIDATORS = []

# Use faster test settings
USE_TZ = False  # Disable timezone support for faster tests

# Disable CORS for tests
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = False

# Disable CSRF for tests
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = []

# Disable sites framework for tests
SITE_ID = 1 