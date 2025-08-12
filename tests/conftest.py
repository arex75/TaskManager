import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from apps.users.models import UserRole

User = get_user_model()

@pytest.fixture
def user_data():
    """Fixture for user test data"""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass123',
        'name': 'Test',
        'last_name': 'User',
        'role': UserRole.USER,
    }

@pytest.fixture
def admin_user_data():
    """Fixture for admin user test data"""
    return {
        'username': 'adminuser',
        'email': 'admin@example.com',
        'password': 'adminpass123',
        'name': 'Admin',
        'last_name': 'User',
        'role': UserRole.ADMIN,
        'is_staff': True,
        'is_superuser': True,
    }

@pytest.fixture
def test_user(user_data):
    """Fixture for creating a test user"""
    return User.objects.create_user(**user_data)

@pytest.fixture
def admin_user(admin_user_data):
    """Fixture for creating an admin user"""
    return User.objects.create_superuser(**admin_user_data)
