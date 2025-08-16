"""
Tests for email-related views (verification, change, etc.)
"""
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

from tests.base import BaseAPITestCase

User = get_user_model()


@patch('apps.users.services.EmailService.send_email_change_confirmation')
class EmailChangeRequestViewTest(BaseAPITestCase):
    """Test cases for email change request view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:email_change_request')
        self.authenticate_user()
    
    def test_email_change_request_success(self, mock_email_service):
        """Test successful email change request"""
        mock_email_service.return_value = True
        
        change_data = {
            'new_email': 'newemail@example.com',
            'password': 'testpass123',
        }
        
        response = self.client.post(self.url, change_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert email service was called
        mock_email_service.assert_called_once()
    
    def test_email_change_request_email_service_failure(self, mock_email_service):
        """Test email change request when email service fails"""
        mock_email_service.return_value = False
        
        change_data = {
            'new_email': 'newemail@example.com',
            'password': 'testpass123',
        }
        
        response = self.client.post(self.url, change_data)
        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # Assert email service was called
        mock_email_service.assert_called_once()
    
    def test_email_change_request_wrong_password(self, mock_email_service):
        """Test email change request with wrong password"""
        change_data = {
            'new_email': 'newemail@example.com',
            'password': 'wrongpassword',
        }
        
        response = self.client.post(self.url, change_data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn('Password is incorrect', str(response.data['error']['details']['non_field_errors']))
        
        # Assert email service was not called
        mock_email_service.assert_not_called()
    
    def test_email_change_request_same_email(self, mock_email_service):
        """Test email change request with same email"""
        change_data = {
            'new_email': 'test@example.com',  # Same as current user email
            'password': 'testpass123',
        }
        
        response = self.client.post(self.url, change_data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn('New email must be different from current email', str(response.data['error']['details']['non_field_errors']))
        
        # Assert email service was not called
        mock_email_service.assert_not_called()
    
    def test_email_change_request_existing_email(self, mock_email_service):
        """Test email change request with existing email"""
        # Create another user with the email
        self.create_user(email='existing@example.com', username='existinguser')
        
        change_data = {
            'new_email': 'existing@example.com',
            'password': 'testpass123',
        }
        
        response = self.client.post(self.url, change_data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn('Email already exists', str(response.data['error']['details']['non_field_errors']))
        
        # Assert email service was not called
        mock_email_service.assert_not_called()
    
    def test_email_change_request_missing_new_email(self, mock_email_service):
        """Test email change request with missing new email"""
        change_data = {
            'password': 'testpass123',
        }
        
        response = self.client.post(self.url, change_data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_email', response.data['error']['details'])
        
        # Assert email service was not called
        mock_email_service.assert_not_called()
    
    def test_email_change_request_missing_password(self, mock_email_service):
        """Test email change request with missing password"""
        change_data = {
            'new_email': 'newemail@example.com',
        }
        
        response = self.client.post(self.url, change_data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['error']['details'])
        
        # Assert email service was not called
        mock_email_service.assert_not_called()
    
    def test_email_change_request_invalid_email_format(self, mock_email_service):
        """Test email change request with invalid email format"""
        change_data = {
            'new_email': 'invalid-email',
            'password': 'testpass123',
        }
        
        response = self.client.post(self.url, change_data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_email', response.data['error']['details'])
        
        # Assert email service was not called
        mock_email_service.assert_not_called()
    
    def test_email_change_request_unauthenticated(self, mock_email_service):
        """Test email change request without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.post(self.url, {})
        
        # Assert unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Assert email service was not called
        mock_email_service.assert_not_called()


class EmailChangeConfirmViewTest(BaseAPITestCase):
    """Test cases for email change confirmation view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:email_change_confirm', kwargs={'token': '12345678-1234-1234-1234-123456789abc'})
    
    def test_email_change_confirm_success(self):
        """Test successful email change confirmation"""
        # Create user with email change token
        user = self.create_user(email='oldemail@example.com', username='oldemailuser')
        user.email_change_token = '12345678-1234-1234-1234-123456789abc'
        user.email_change_token_expiration = timezone.now() + timezone.timedelta(hours=1)
        user.save()
        
        response = self.client.post(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert token was cleared
        user.refresh_from_db()
        self.assertIsNone(user.email_change_token)
        self.assertIsNone(user.email_change_token_expiration)
    
    def test_email_change_confirm_invalid_token(self):
        """Test email change confirmation with invalid token"""
        response = self.client.post(self.url)
        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_email_change_confirm_expired_token(self):
        """Test email change confirmation with expired token"""
        # Create user with expired email change token
        user = self.create_user(email='oldemail@example.com', username='expiredemailuser')
        user.email_change_token = '87654321-4321-4321-4321-cba987654321'
        user.email_change_token_expiration = timezone.now() - timedelta(hours=25)  # Expired
        user.save()
        
        response = self.client.post(self.url)
        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class PasswordResetConfirmViewTest(BaseAPITestCase):
    """Test cases for password reset confirmation view"""
    
    def setUp(self):
        super().setUp()
        # We'll set the token dynamically in each test
    
    def test_password_reset_confirm_success(self):
        """Test successful password reset confirmation"""
        # Create user with password reset token
        token = '11111111-2222-3333-4444-555555555555'
        user = self.create_user(email='reset@example.com', username='resetuser')
        user.password_reset_token = token
        user.password_reset_token_expiration = timezone.now() + timezone.timedelta(hours=1)
        user.save()
        
        # Create URL with the same token
        url = reverse('users:password_reset_confirm', kwargs={'token': token})
        
        reset_data = {
            'new_password': 'NewStrongPass123!',
            'new_password_confirm': 'NewStrongPass123!',
        }
        
        response = self.client.post(url, reset_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert password was changed
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewStrongPass123!'))
        
        # Assert token was cleared
        self.assertIsNone(user.password_reset_token)
        self.assertIsNone(user.password_reset_token_expiration)
    
    def test_password_reset_confirm_invalid_token(self):
        """Test password reset confirmation with invalid token"""
        # Use a token that doesn't exist in the database
        url = reverse('users:password_reset_confirm', kwargs={'token': '99999999-9999-9999-9999-999999999999'})
        
        reset_data = {
            'new_password': 'NewStrongPass123!',
            'new_password_confirm': 'NewStrongPass123!',
        }
        
        response = self.client.post(url, reset_data)
        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_password_reset_confirm_expired_token(self):
        """Test password reset confirmation with expired token"""
        # Create user with expired password reset token
        token = '22222222-3333-4444-5555-666666666666'
        user = self.create_user(email='reset@example.com', username='expiredresetuser')
        user.password_reset_token = token
        user.password_reset_token_expiration = timezone.now() - timedelta(hours=25)  # Expired
        user.save()
        
        # Create URL with the same token
        url = reverse('users:password_reset_confirm', kwargs={'token': token})
        
        reset_data = {
            'new_password': 'NewStrongPass123!',
            'new_password_confirm': 'NewStrongPass123!',
        }
        
        response = self.client.post(url, reset_data)
        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_password_reset_confirm_password_mismatch(self):
        """Test password reset confirmation with password mismatch"""
        # Create user with password reset token
        token = '44444444-5555-6666-7777-888888888888'
        user = self.create_user(email='reset@example.com', username='resetuser')
        user.password_reset_token = token
        user.password_reset_token_expiration = timezone.now()
        user.save()
        
        # Create URL with the same token
        url = reverse('users:password_reset_confirm', kwargs={'token': token})
        
        reset_data = {
            'new_password': 'NewStrongPass123!',
            'new_password_confirm': 'DifferentPass123!',
        }
        
        response = self.client.post(url, reset_data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data['error']['details'])
        self.assertIn("Passwords don't match", str(response.data['error']['details']['non_field_errors']))
    
    def test_password_reset_confirm_weak_password(self):
        """Test password reset confirmation with weak password"""
        # Create user with password reset token
        token = '44444444-5555-6666-7777-888888888888'
        user = self.create_user(email='reset@example.com', username='resetuser')
        user.password_reset_token = token
        user.password_reset_token_expiration = timezone.now()
        user.save()
        
        # Create URL with the same token
        url = reverse('users:password_reset_confirm', kwargs={'token': token})
        
        reset_data = {
            'new_password': 'weak',
            'new_password_confirm': 'weak',
        }
        
        response = self.client.post(url, reset_data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data['error']['details'])
    
    def test_password_reset_confirm_missing_new_password(self):
        """Test password reset confirmation with missing new password"""
        # Create user with password reset token
        token = '44444444-5555-6666-7777-888888888888'
        user = self.create_user(email='reset@example.com', username='resetuser')
        user.password_reset_token = token
        user.password_reset_token_expiration = timezone.now()
        user.save()
        
        # Create URL with the same token
        url = reverse('users:password_reset_confirm', kwargs={'token': token})
        
        reset_data = {
            'new_password_confirm': 'NewStrongPass123!',
        }
        
        response = self.client.post(url, reset_data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data['error']['details'])
    
    def test_password_reset_confirm_missing_new_password_confirm(self):
        """Test password reset confirmation with missing password confirmation"""
        # Create user with password reset token
        token = '44444444-5555-6666-7777-888888888888'
        user = self.create_user(email='reset_user', username='resetuser')
        user.password_reset_token = token
        user.password_reset_token_expiration = timezone.now()
        user.save()
        
        # Create URL with the same token
        url = reverse('users:password_reset_confirm', kwargs={'token': token})
        
        reset_data = {
            'new_password': 'NewStrongPass123!',
        }
        
        response = self.client.post(url, reset_data)
        
        # Assert validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password_confirm', response.data['error']['details'])
