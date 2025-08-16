#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Check if we're running tests
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Use test settings for tests
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.test_settings')
    else:
        # Use regular settings for other commands
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
