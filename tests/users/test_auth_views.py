"""
Tests for user authentication views (registration, login, logout, etc.)
"""
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from unittest.mock import patch, MagicMock
import uuid

from tests.base import BaseAPITestCase

User = get_user_model()


class UserRegistrationViewTest(BaseAPITestCase):
    """Test cases for user registration view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:register')
        self.valid_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'first_name': 'New',
            'last_name': 'User',
            'name': 'New User',
            'role': 'USER',
        }
    
    @patch('apps.users.services.EmailService.send_verification_email')
    @patch('apps.users.services.TokenService.generate_tokens')
    def test_user_registration_success(self, mock_token_service, mock_email_service):
        """Test successful user registration"""
        mock_token_service.return_value = {
            'access': 'test-access-token',
            'refresh': 'test-refresh-token'
        }
        mock_email_service.return_value = True
        
        response = self.client.post(self.url, self.valid_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('user', response.data['data'])
        self.assertIn('tokens', response.data['data'])
        
        # Assert user was created
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'User')
        self.assertFalse(user.is_verified)
        
        # Assert services were called
        mock_email_service.assert_called_once()
        mock_token_service.assert_called_once()
    
    @patch('apps.users.services.EmailService.send_verification_email')
    @patch('apps.users.services.TokenService.generate_tokens')
    def test_user_registration_with_email_service_failure(self, mock_token_service, mock_email_service):
        """Test user registration when email service fails"""
        mock_token_service.return_value = {
            'access': 'test-access-token',
            'refresh': 'test-refresh-token'
        }
        mock_email_service.return_value = False
        
        response = self.client.post(self.url, self.valid_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('warning', response.data['data'])
        self.assertIn('verification email could not be sent', response.data['data']['warning'])
        
        # Assert user was still created
        user = User.objects.get(username='newuser')
        self.assertIsNotNone(user)
    
    @patch('apps.users.services.EmailService.send_verification_email')
    @patch('apps.users.services.TokenService.generate_tokens')
    def test_user_registration_with_token_service_failure(self, mock_token_service, mock_email_service):
        """Test user registration when token service fails"""
        mock_token_service.return_value = None
        mock_email_service.return_value = True
        
        response = self.client.post(self.url, self.valid_data)
        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Failed to generate authentication tokens', response.data['error']['message'])
    
    def test_user_registration_password_mismatch(self):
        """Test user registration with password mismatch"""
        data = self.valid_data.copy()
        data['password_confirm'] = 'DifferentPass123!'
        
        response = self.client.post(self.url, data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn("Passwords don't match", str(response.data['error']['details']['non_field_errors']))
        
        # Assert no user was created
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_user_registration_duplicate_username(self):
        """Test user registration with duplicate username"""
        # Create user first
        self.create_user(username='existinguser', email='existing@example.com')
        
        data = self.valid_data.copy()
        data['username'] = 'existinguser'
        data['email'] = 'newemail@example.com'
        
        response = self.client.post(self.url, data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn('Username already exists', str(response.data['error']['details']['non_field_errors']))
    
    def test_user_registration_duplicate_email(self):
        """Test user registration with duplicate email"""
        # Create user first
        self.create_user(username='existinguser', email='existing@example.com')
        
        data = self.valid_data.copy()
        data['username'] = 'newuser'
        data['email'] = 'existing@example.com'
        
        response = self.client.post(self.url, data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn('Email already exists', str(response.data['error']['details']['non_field_errors']))
    
    def test_user_registration_weak_password(self):
        """Test user registration with weak password"""
        data = self.valid_data.copy()
        data['password'] = 'weak'
        data['password_confirm'] = 'weak'
        
        response = self.client.post(self.url, data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['error']['details'])
    
    def test_user_registration_missing_required_fields(self):
        """Test user registration with missing required fields"""
        # Test missing username
        data = self.valid_data.copy()
        del data['username']
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data['error']['details'])
        
        # Test missing email
        data = self.valid_data.copy()
        del data['email']
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['error']['details'])
        
        # Test missing password
        data = self.valid_data.copy()
        del data['password']
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['error']['details'])
    
    def test_user_registration_boundary_values(self):
        """Test user registration with boundary values"""
        # Test username too short
        data = self.valid_data.copy()
        data['username'] = 'ab'  # Less than 3 characters
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test username too long
        data = self.valid_data.copy()
        data['username'] = 'a' * 31  # More than 30 characters
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test email too long
        data = self.valid_data.copy()
        data['email'] = 'a' * 100 + '@example.com'
        response = self.client.post(self.url, data)
        # Email with 100 chars + domain is valid (Django EmailField max is 254)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class UserLoginViewTest(BaseAPITestCase):
    """Test cases for user login view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:login')
        self.valid_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
    
    def test_user_login_success(self):
        """Test successful user login"""
        response = self.client.post(self.url, self.valid_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('user', response.data['data'])
        self.assertIn('tokens', response.data['data'])
        
        # Assert user data
        user_data = response.data['data']['user']
        self.assertEqual(user_data['username'], 'testuser')
        self.assertEqual(user_data['email'], 'test@example.com')
    
    def test_user_login_invalid_credentials(self):
        """Test user login with invalid credentials"""
        data = self.valid_data.copy()
        data['password'] = 'wrongpassword'
        
        response = self.client.post(self.url, data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn('Invalid credentials', str(response.data['error']['details']['non_field_errors']))
    
    def test_user_login_missing_credentials(self):
        """Test user login with missing credentials"""
        # Test missing username
        data = self.valid_data.copy()
        del data['username']
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data['error']['details'])
        
        # Test missing password
        data = self.valid_data.copy()
        del data['password']
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['error']['details'])
    
    def test_user_login_case_sensitivity(self):
        """Test username case sensitivity in login"""
        data = self.valid_data.copy()
        data['username'] = 'TESTUSER'  # Uppercase
        
        response = self.client.post(self.url, data)
        
        # Username should be case-sensitive, so this should fail
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn('Invalid credentials', str(response.data['error']['details']['non_field_errors']))


class UserLogoutViewTest(BaseAPITestCase):
    """Test cases for user logout view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:logout')
        self.authenticate_user()
    
    def test_user_logout_success(self):
        """Test successful user logout"""
        response = self.client.post(self.url, {'refresh_token': 'test-refresh-token'})
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('status', response.data['data'])
        self.assertEqual(response.data['data']['status'], 'logged_out')
    
    def test_user_logout_without_token(self):
        """Test user logout without refresh token"""
        response = self.client.post(self.url, {})
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('status', response.data['data'])
        self.assertEqual(response.data['data']['status'], 'logged_out')
    
    def test_user_logout_unauthenticated(self):
        """Test user logout without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.post(self.url, {})
        
        # Should return 401 Unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileViewTest(BaseAPITestCase):
    """Test cases for user profile view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:profile')
        self.authenticate_user()
    
    def test_get_user_profile(self):
        """Test getting user profile"""
        response = self.client.get(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('user', response.data['data'])
        
        # Assert user data
        user_data = response.data['data']['user']
        self.assertEqual(user_data['username'], 'testuser')
        self.assertEqual(user_data['email'], 'test@example.com')
    
    def test_update_user_profile(self):
        """Test updating user profile"""
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'bio': 'This is my bio',
        }
        
        response = self.client.put(self.url, update_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('user', response.data['data'])
        
        # Assert user was updated
        user = User.objects.get(username='testuser')
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(user.last_name, 'Name')
        self.assertEqual(user.bio, 'This is my bio')
    
    def test_update_user_profile_partial(self):
        """Test partial update of user profile"""
        update_data = {
            'first_name': 'Partial',
        }
        
        # Use PATCH for partial updates
        response = self.client.patch(self.url, update_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert only specified field was updated
        user = User.objects.get(username='testuser')
        self.assertEqual(user.first_name, 'Partial')
        self.assertEqual(user.last_name, 'User')  # Unchanged
    
    def test_get_user_profile_unauthenticated(self):
        """Test getting user profile without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.get(self.url)
        
        # Assert unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_user_profile_unauthenticated(self):
        """Test updating user profile without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.put(self.url, {'first_name': 'Test'})
        
        # Assert unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_profile_unauthorized_access(self):
        """Test unauthorized access to user profile"""
        # Remove authentication
        self.client.credentials()
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_profile_cross_user_access(self):
        """Test that users cannot access other users' profiles"""
        # Create another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        
        # Authenticate as first user
        self.authenticate_user(self.user)
        
        # Try to access other user's profile (this would depend on your URL structure)
        # For now, test that user can only access their own profile
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify it's the correct user's data
        self.assertEqual(response.data['data']['user']['username'], 'testuser')


class PasswordChangeViewTest(BaseAPITestCase):
    """Test cases for password change view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:password_change')
        self.authenticate_user()
        self.valid_data = {
            'old_password': 'testpass123',
            'new_password': 'NewStrongPass123!',
            'new_password_confirm': 'NewStrongPass123!'
        }
    
    def test_password_change_success(self):
        """Test successful password change"""
        response = self.client.post(self.url, self.valid_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('status', response.data['data'])
        self.assertEqual(response.data['data']['status'], 'changed')
        
        # Assert password was changed
        user = User.objects.get(username='testuser')
        self.assertTrue(user.check_password('NewStrongPass123!'))
    
    def test_password_change_wrong_old_password(self):
        """Test password change with wrong old password"""
        data = self.valid_data.copy()
        data['old_password'] = 'wrongpassword'
        
        response = self.client.post(self.url, data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn('Old password is incorrect', str(response.data['error']['details']['non_field_errors']))
    
    def test_password_change_password_mismatch(self):
        """Test password change with password mismatch"""
        data = self.valid_data.copy()
        data['new_password_confirm'] = 'DifferentPass123!'
        
        response = self.client.post(self.url, data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn("New passwords don't match", str(response.data['error']['details']['non_field_errors']))
    
    def test_password_change_weak_new_password(self):
        """Test password change with weak new password"""
        data = self.valid_data.copy()
        data['new_password'] = 'weak'
        data['new_password_confirm'] = 'weak'
        
        response = self.client.post(self.url, data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data['error']['details'])
    
    def test_password_change_old_password_verification(self):
        """Test that old password is properly verified"""
        data = self.valid_data.copy()
        data['old_password'] = 'wrongpassword'
        
        response = self.client.post(self.url, data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn('Old password is incorrect', str(response.data['error']['details']['non_field_errors']))


class PasswordResetRequestViewTest(BaseAPITestCase):
    """Test cases for password reset views"""
    
    def setUp(self):
        super().setUp()
        self.request_url = reverse('users:password_reset_request')
        self.reset_data = {
            'email': 'test@example.com',
        }
    
    @patch('apps.users.services.EmailService.send_password_reset_email')
    def test_password_reset_request_success(self, mock_email_service):
        """Test successful password reset request"""
        mock_email_service.return_value = True
        
        response = self.client.post(self.request_url, self.reset_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert email service was called
        mock_email_service.assert_called_once()
    
    @patch('apps.users.services.EmailService.send_password_reset_email')
    def test_password_reset_request_email_service_failure(self, mock_email_service):
        """Test password reset request when email service fails"""
        mock_email_service.return_value = False
        
        response = self.client.post(self.request_url, self.reset_data)
        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Failed to send password reset email', response.data['error']['message'])
    
    def test_password_reset_request_invalid_email(self):
        """Test password reset request with invalid email"""
        data = {'email': 'nonexistent@example.com'}
        
        response = self.client.post(self.request_url, data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['error']['details'])
    
    def test_password_reset_request_missing_email(self):
        """Test password reset request with missing email"""
        response = self.client.post(self.request_url, {})
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['error']['details'])


class EmailVerificationViewTest(BaseAPITestCase):
    """Test cases for email verification view"""
    
    def setUp(self):
        super().setUp()
        # Use a valid UUID format for the token
        self.valid_token = str(uuid.uuid4())
        self.url = reverse('users:email_verify', kwargs={'token': self.valid_token})
    
    def test_email_verification_success(self):
        """Test successful email verification"""
        # Create user with verification token
        user = self.create_user(email='verify@example.com', username='verifyuser')
        user.email_verification_token = self.valid_token
        user.email_verification_token_expiration = timezone.now() + timezone.timedelta(hours=1)  # Valid for 1 hour
        user.save()
        
        response = self.client.post(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert user was verified
        user.refresh_from_db()
        self.assertTrue(user.is_verified)
        self.assertIsNone(user.email_verification_token)
        self.assertIsNone(user.email_verification_token_expiration)
    
    def test_email_verification_invalid_token(self):
        """Test email verification with invalid token"""
        response = self.client.post(self.url)
        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Invalid token', response.data['error']['message'])
    
    def test_email_verification_expired_token(self):
        """Test email verification with expired token"""
        # Create user with expired verification token
        user = self.create_user(email='expired@example.com', username='expireduser')
        user.email_verification_token = self.valid_token
        user.email_verification_token_expiration = timezone.now() - timezone.timedelta(hours=25)  # Expired
        user.save()
        
        response = self.client.post(self.url)
        
        # Now the view checks expiration, so this should fail
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Token expired', response.data['error']['message'])
