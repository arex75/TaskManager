from django.test import TestCase
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from apps.users.models import UserRole

User = get_user_model()

class BaseTestCase(TestCase):
    """Base test case for model testing"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test',
            'last_name': 'User',
            'role': UserRole.USER,
        }
        
        self.admin_user_data = {
            'username': 'adminuser',
            'email': 'admin@example.com',
            'password': 'adminpass123',
            'name': 'Admin',
            'last_name': 'User',
            'role': UserRole.ADMIN,
            'is_staff': True,
            'is_superuser': True,
        }

class BaseAPITestCase(APITestCase):
    """Base test case for API testing"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test',
            'last_name': 'User',
            'role': UserRole.USER,
        }
        
        self.admin_user_data = {
            'username': 'adminuser',
            'email': 'admin@example.com',
            'password': 'adminpass123',
            'name': 'Admin',
            'last_name': 'User',
            'role': UserRole.ADMIN,
            'is_staff': True,
            'is_superuser': True,
        }
    
    def create_user(self, **kwargs):
        """Helper method to create a test user"""
        user_data = self.user_data.copy()
        user_data.update(kwargs)
        return User.objects.create_user(**user_data)
    
    def create_admin_user(self, **kwargs):
        """Helper method to create a test admin user"""
        admin_data = self.admin_user_data.copy()
        admin_data.update(kwargs)
        return User.objects.create_superuser(**admin_data)
