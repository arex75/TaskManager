"""
Test-specific settings for TaskManager project.
This file overrides logging levels to reduce noise during test execution.
"""

from .settings import *

# Override logging configuration for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',  # Simpler format for tests
        },
    },
    'loggers': {
        'apps.config.exception_handler': {
            'handlers': ['console'],
            'level': 'WARNING',  # Only show WARNING and above during tests
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',  # Reduce Django logging during tests
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',  # Only show request errors during tests
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'ERROR',  # Only show database errors during tests
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'ERROR',  # Only show security errors during tests
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',  # Root level set to WARNING for tests
    },
}

# Additional test-specific settings
DEBUG = False  # Disable debug mode during tests
TEMPLATES[0]['OPTIONS']['debug'] = False

# Disable file logging during tests
LOGGING['handlers'].pop('file', None)
