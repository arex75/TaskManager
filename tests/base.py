from django.test import TestCase, override_settings
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from apps.users.models import UserRole
import tempfile
import shutil
import os

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
        
        # Test media files setup
        self.test_media_root = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test data"""
        # Clean up test media files
        shutil.rmtree(self.test_media_root, ignore_errors=True)
    
    def create_user(self, **kwargs):
        """Helper method to create a test user"""
        user_data = self.user_data.copy()
        user_data.update(kwargs)
        return User.objects.create_user(**user_data)
    
    def create_admin_user(self, **kwargs):
        """Helper method to create a test admin user"""
        admin_data = self.admin_user_data.copy()
        admin_data.update(kwargs)
        return User.objects.create_user(**admin_data)

class BaseAPITestCase(APITestCase):
    """Base test case for API testing with enhanced functionality"""
    
    def setUp(self):
        """Set up test data and client"""
        super().setUp()
        
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
        
        # Test media files setup
        self.test_media_root = tempfile.mkdtemp()
        
        # Create test users
        self.user = self.create_user()
        self.admin_user = self.create_admin_user()
        
        # Get tokens for authenticated requests
        self.user_tokens = self.get_tokens_for_user(self.user)
        self.admin_tokens = self.get_tokens_for_user(self.admin_user)
    
    def tearDown(self):
        """Clean up test data"""
        # Clean up test media files
        shutil.rmtree(self.test_media_root, ignore_errors=True)
    
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
    
    def get_tokens_for_user(self, user):
        """Helper method to get JWT tokens for a user"""
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    
    def authenticate_user(self, user=None):
        """Helper method to authenticate a user for requests"""
        if user is None:
            user = self.user
        tokens = self.get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        return tokens
    
    def authenticate_admin(self):
        """Helper method to authenticate as admin user"""
        return self.authenticate_user(self.admin_user)
    
    def create_verified_user(self, **kwargs):
        """Helper method to create a verified user"""
        user = self.create_user(**kwargs)
        user.is_verified = True
        user.save()
        return user
    
    def create_blocked_user(self, **kwargs):
        """Helper method to create a blocked user"""
        user = self.create_user(**kwargs)
        user.is_blocked = True
        user.save()
        return user
    
    def create_deleted_user(self, **kwargs):
        """Helper method to create a soft-deleted user"""
        user = self.create_user(**kwargs)
        user.is_deleted = True
        user.save()
        return user
    
    def create_user_with_email_token(self, **kwargs):
        """Helper method to create a user with email verification token"""
        user = self.create_user(**kwargs)
        user.generate_email_verification_token()
        user.save()
        return user
    
    def create_user_with_password_reset_token(self, **kwargs):
        """Helper method to create a user with password reset token"""
        user = self.create_user(**kwargs)
        user.generate_password_reset_token()
        user.save()
        return user
    
    def create_user_with_email_change_token(self, **kwargs):
        """Helper method to create a user with email change token"""
        user = self.create_user(**kwargs)
        user.generate_email_change_token()
        user.save()
        return user
    
    def create_user_with_expired_token(self, token_type='password_reset', **kwargs):
        """Helper method to create a user with expired token"""
        user = self.create_user(**kwargs)
        if token_type == 'password_reset':
            user.password_reset_token = '11111111-2222-3333-4444-555555555555'
            user.password_reset_token_expiration = timezone.now() - timezone.timedelta(hours=25)
        elif token_type == 'email_change':
            user.email_change_token = '22222222-3333-4444-5555-666666666666'
            user.email_change_token_expiration = timezone.now() - timezone.timedelta(hours=25)
        elif token_type == 'email_verification':
            user.email_verification_token = '33333333-4444-5555-6666-777777777777'
        user.save()
        return user
    
    def assert_response_format(self, response, expected_status=status.HTTP_200_OK):
        """Helper method to assert standard API response format"""
        self.assertEqual(response.status_code, expected_status)
        self.assertIn('success', response.data)
        self.assertIn('data', response.data)
        self.assertIn('message', response.data)
        self.assertIn('timestamp', response.data)
    
    def assert_error_response(self, response, expected_status, error_code=None):
        """Helper method to assert error response format"""
        self.assertEqual(response.status_code, expected_status)
        self.assertIn('success', response.data)
        self.assertFalse(response.data['success'])
        self.assertIn('error', response.data)
        if error_code:
            self.assertEqual(response.data['error']['code'], error_code)
    
    def assert_pagination_format(self, response):
        """Helper method to assert pagination response format"""
        self.assert_response_format(response)
        self.assertIn('pagination', response.data['data'])
        pagination = response.data['data']['pagination']
        required_fields = ['page', 'per_page', 'total_pages', 'total_count', 
                          'has_next', 'has_previous']
        for field in required_fields:
            self.assertIn(field, pagination)




# Test media settings
TEST_MEDIA_SETTINGS = {
    'MEDIA_ROOT': tempfile.mkdtemp(),
    'MEDIA_URL': '/test-media/',
}
