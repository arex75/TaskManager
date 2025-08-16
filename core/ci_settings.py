"""
CI-specific settings for TaskManager project.
"""
from .test_settings import *

# Override database settings for CI
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'testdb',
        'USER': 'testuser',
        'PASSWORD': 'testpassword',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# CI-specific settings
SECRET_KEY = 'a-test-secret-key-for-ci'
DEBUG = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Disable email backend for CI
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable external services
GOOGLE_OAUTH2_CLIENT_ID = 'test-client-id'
GOOGLE_OAUTH2_CLIENT_SECRET = 'test-client-secret'

# Use SQLite for CI/CD (faster and no external dependencies)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # Use in-memory database for faster tests
    }
}

# Celery settings for CI/CD
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

# Disable MinIO for tests (use mocks instead)
MINIO_ENDPOINT = 'localhost:9000'
MINIO_USERNAME = 'test'
MINIO_PASSWORD = 'test'
MINIO_USE_HTTPS = False
MINIO_TEMP_BUCKET = 'test-temp'
MINIO_PERMANENT_BUCKET = 'test-permanent'

# Mock MinIO Service for CI environment
class MockMinIOService:
    """Mock MinIO service for CI environment"""
    
    def __init__(self):
        self.temp_bucket = MINIO_TEMP_BUCKET
        self.permanent_bucket = MINIO_PERMANENT_BUCKET
    
    def ensure_buckets_exist(self):
        """Mock method - does nothing"""
        pass
    
    def upload_file_temporary(self, file, user_id):
        """Mock method - returns mock values"""
        import os
        import uuid
        file_extension = os.path.splitext(file.name)[1]
        object_key = f"temp/{user_id}/{uuid.uuid4()}{file_extension}"
        return self.temp_bucket, object_key
    
    def move_to_permanent(self, temp_bucket, temp_object_key, permanent_object_key):
        """Mock method - always returns True"""
        return True
    
    def get_presigned_url(self, bucket_name, object_key, expires=3600):
        """Mock method - returns mock URL"""
        return f"https://test-minio.example.com/{bucket_name}/{object_key}"

# Override the MinIO service import in CI environment
import sys
from unittest.mock import MagicMock

# Create a mock module that replaces the real MinIOService
mock_minio_module = MagicMock()
mock_minio_module.MinIOService = MockMinIOService

# Replace the real module with our mock
sys.modules['services.minio_service'] = mock_minio_module

# Use a simple cache backend for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable static files collection during tests
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage' 