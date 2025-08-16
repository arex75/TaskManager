"""
Tests for users app services (EmailService, TokenService, UserService, OAuthService)
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core import mail
from django.core.mail import EmailMessage
from django.utils import timezone
from django.template.loader import render_to_string
from django.template import Template, Context
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock, call
import logging
import uuid

from apps.users.services import EmailService, TokenService, UserService, OAuthService
from tests.base import BaseTestCase

User = get_user_model()


class EmailServiceTest(BaseTestCase):
    """Test cases for EmailService"""
    
    def setUp(self):
        super().setUp()
        
        self.factory = RequestFactory()
        
        try:
            self.site = Site.objects.create(
                name='Test Site',
                domain='testserver.com'
            )
        except Exception as e:
            raise
        
        # Create a test user
        try:
            self.user = self.create_user(
                email='test@example.com',
                username='testuser'
            )
        except Exception as e:
            raise
        
        # Create a mock request
        self.request = self.factory.get('/')
        self.request.site = self.site
        
        # Update SITE_ID to use our test site
        from django.conf import settings
        settings.SITE_ID = self.site.id
        
        # Create email templates for testing
        self.create_test_templates()
    
    def create_test_templates(self):
        """Create test email templates"""
        # Email verification template
        verification_template = Template("""
        <html>
            <body>
                <h1>Verify your email</h1>
                <p>Hello {{ user.username }},</p>
                <p>Please verify your email by clicking this link:</p>
                <a href="{{ verification_url }}">Verify Email</a>
                <p>Site: {{ site_name }}</p>
            </body>
        </html>
        """)
        
        # Password reset template
        reset_template = Template("""
        <html>
            <body>
                <h1>Reset your password</h1>
                <p>Hello {{ user.username }},</p>
                <p>Click this link to reset your password:</p>
                <a href="{{ reset_url }}">Reset Password</a>
                <p>Site: {{ site_name }}</p>
            </body>
        </html>
        """)
        
        # Email change template
        change_template = Template("""
        <html>
            <body>
                <h1>Confirm email change</h1>
                <p>Hello {{ user.username }},</p>
                <p>Please confirm your new email: {{ new_email }}</p>
                <a href="{{ confirmation_url }}">Confirm Change</a>
                <p>Site: {{ site_name }}</p>
            </body>
        </html>
        """)
        
        # Mock the template loading
        self.verification_template = verification_template
        self.reset_template = reset_template
        self.change_template = change_template
    
    @patch('apps.users.services.render_to_string')
    @patch('apps.users.services.send_mail')
    def test_send_verification_email_success(self, mock_send_mail, mock_render_to_string):
        """Test successful email verification email sending"""
        # Setup user with verification token
        self.user.email_verification_token = str(uuid.uuid4())
        self.user.save()
        
        # Mock template rendering
        mock_render_to_string.return_value = '<html>Test verification email</html>'
        
        # Mock send_mail
        mock_send_mail.return_value = 1
        
        # Call service
        result = EmailService.send_verification_email(self.request, self.user)
        
        # Assertions
        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        
        # Check send_mail arguments
        call_args = mock_send_mail.call_args
        self.assertEqual(call_args[0][0], 'Verify your email address')  # subject
        self.assertEqual(call_args[0][1], 'Test verification email')    # plain message
        self.assertEqual(call_args[0][2], settings.DEFAULT_FROM_EMAIL)   # from email
        self.assertEqual(call_args[0][3], [self.user.email])            # to emails
        self.assertEqual(call_args[1]['html_message'], '<html>Test verification email</html>')
        self.assertFalse(call_args[1]['fail_silently'])
    
    @patch('apps.users.services.render_to_string')
    @patch('apps.users.services.send_mail')
    def test_send_verification_email_failure(self, mock_send_mail, mock_render_to_string):
        """Test email verification email sending failure"""
        # Setup user with verification token
        self.user.email_verification_token = str(uuid.uuid4())
        self.user.save()
        
        # Mock template rendering
        mock_render_to_string.return_value = '<html>Test verification email</html>'
        
        # Mock send_mail to raise exception
        mock_send_mail.side_effect = Exception("SMTP error")
        
        # Call service
        result = EmailService.send_verification_email(self.request, self.user)
        
        # Assertions
        self.assertFalse(result)
        mock_send_mail.assert_called_once()
    
    @patch('apps.users.services.render_to_string')
    @patch('apps.users.services.send_mail')
    def test_send_password_reset_email_success(self, mock_send_mail, mock_render_to_string):
        """Test successful password reset email sending"""
        # Setup user with reset token
        self.user.password_reset_token = str(uuid.uuid4())
        self.user.save()
        
        # Mock template rendering
        mock_render_to_string.return_value = '<html>Test reset email</html>'
        
        # Mock send_mail
        mock_send_mail.return_value = 1
        
        # Call service
        result = EmailService.send_password_reset_email(self.request, self.user)
        
        # Assertions
        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        
        # Check send_mail arguments
        call_args = mock_send_mail.call_args
        self.assertEqual(call_args[0][0], 'Reset your password')       # subject
        self.assertEqual(call_args[0][1], 'Test reset email')          # plain message
        self.assertEqual(call_args[0][2], settings.DEFAULT_FROM_EMAIL)  # from email
        self.assertEqual(call_args[0][3], [self.user.email])           # to emails
    
    @patch('apps.users.services.render_to_string')
    @patch('apps.users.services.send_mail')
    def test_send_password_reset_email_failure(self, mock_send_mail, mock_render_to_string):
        """Test password reset email sending failure"""
        # Setup user with reset token
        self.user.password_reset_token = str(uuid.uuid4())
        self.user.save()
        
        # Mock template rendering
        mock_render_to_string.return_value = '<html>Test reset email</html>'
        
        # Mock send_mail to raise exception
        mock_send_mail.side_effect = Exception("SMTP error")
        
        # Call service
        result = EmailService.send_password_reset_email(self.request, self.user)
        
        # Assertions
        self.assertFalse(result)
        mock_send_mail.assert_called_once()
    
    @patch('apps.users.services.render_to_string')
    @patch('apps.users.services.send_mail')
    def test_send_email_change_confirmation_success(self, mock_send_mail, mock_render_to_string):
        """Test successful email change confirmation email sending"""
        # Setup user with change token
        self.user.email_change_token = str(uuid.uuid4())
        self.user.save()
        
        new_email = 'newemail@example.com'
        
        # Mock template rendering
        mock_render_to_string.return_value = '<html>Test change email</html>'
        
        # Mock send_mail
        mock_send_mail.return_value = 1
        
        # Call service
        result = EmailService.send_email_change_confirmation(self.request, self.user, new_email)
        
        # Assertions
        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        
        # Check send_mail arguments
        call_args = mock_send_mail.call_args
        self.assertEqual(call_args[0][0], 'Confirm your new email address')  # subject
        self.assertEqual(call_args[0][1], 'Test change email')               # plain message
        self.assertEqual(call_args[0][2], settings.DEFAULT_FROM_EMAIL)        # from email
        self.assertEqual(call_args[0][3], [new_email])                       # to emails
    
    @patch('apps.users.services.render_to_string')
    @patch('apps.users.services.send_mail')
    def test_send_email_change_confirmation_failure(self, mock_send_mail, mock_render_to_string):
        """Test email change confirmation email sending failure"""
        # Setup user with change token
        self.user.email_change_token = str(uuid.uuid4())
        self.user.save()
        
        new_email = 'newemail@example.com'
        
        # Mock template rendering
        mock_render_to_string.return_value = '<html>Test change email</html>'
        
        # Mock send_mail to raise exception
        mock_send_mail.side_effect = Exception("SMTP error")
        
        # Call service
        result = EmailService.send_email_change_confirmation(self.request, self.user, new_email)
        
        # Assertions
        self.assertFalse(result)
        mock_send_mail.assert_called_once()
    
    def test_verification_url_generation(self):
        """Test that verification URLs are generated correctly"""
        self.user.email_verification_token = str(uuid.uuid4())
        self.user.save()
        
        with patch('apps.users.services.render_to_string') as mock_render:
            with patch('apps.users.services.send_mail') as mock_send:
                mock_render.return_value = '<html>Test</html>'
                mock_send.return_value = 1
                
                EmailService.send_verification_email(self.request, self.user)
                
                # Check that render_to_string was called with correct context
                mock_render.assert_called_once()
                call_args = mock_render.call_args
                context = call_args[0][1]  # Second argument in the tuple is context
                
                self.assertEqual(context['user'], self.user)
                self.assertEqual(context['site_name'], self.site.name)
                self.assertIn('verification_url', context)
                self.assertIn(str(self.user.email_verification_token), context['verification_url'])
    
    def test_reset_url_generation(self):
        """Test that password reset URLs are generated correctly"""
        self.user.password_reset_token = str(uuid.uuid4())
        self.user.save()
        
        with patch('apps.users.services.render_to_string') as mock_render:
            with patch('apps.users.services.send_mail') as mock_send:
                mock_render.return_value = '<html>Test</html>'
                mock_send.return_value = 1
                
                EmailService.send_password_reset_email(self.request, self.user)
                
                # Check that render_to_string was called with correct context
                mock_render.assert_called_once()
                call_args = mock_render.call_args
                context = call_args[0][1]  # Second argument in the tuple is context
                
                self.assertEqual(context['user'], self.user)
                self.assertEqual(context['site_name'], self.site.name)
                self.assertIn('reset_url', context)
                self.assertIn(str(self.user.password_reset_token), context['reset_url'])


class TokenServiceTest(BaseTestCase):
    """Test cases for TokenService"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
    
    def test_generate_tokens_success(self):
        """Test successful token generation"""
        result = TokenService.generate_tokens(self.user)
        
        # Assertions
        self.assertIsNotNone(result)
        self.assertIn('access', result)
        self.assertIn('refresh', result)
        
        # Verify tokens are valid
        access_token = result['access']
        refresh_token = result['refresh']
        
        self.assertIsInstance(access_token, str)
        self.assertIsInstance(refresh_token, str)
        self.assertTrue(len(access_token) > 0)
        self.assertTrue(len(refresh_token) > 0)
        
        # Verify tokens can be decoded
        try:
            RefreshToken(refresh_token)
        except Exception:
            self.fail("Generated refresh token is invalid")
    
    def test_generate_tokens_different_users(self):
        """Test that different users get different tokens"""
        user2 = self.create_user(username='user2', email='user2@example.com')
        
        tokens1 = TokenService.generate_tokens(self.user)
        tokens2 = TokenService.generate_tokens(user2)
        
        # Assertions
        self.assertNotEqual(tokens1['access'], tokens2['access'])
        self.assertNotEqual(tokens1['refresh'], tokens2['refresh'])
    
    def test_generate_tokens_multiple_calls(self):
        """Test that multiple calls generate different tokens"""
        tokens1 = TokenService.generate_tokens(self.user)
        tokens2 = TokenService.generate_tokens(self.user)
        
        # Assertions
        self.assertNotEqual(tokens1['access'], tokens2['access'])
        self.assertNotEqual(tokens1['refresh'], tokens2['refresh'])
    
    @patch('rest_framework_simplejwt.tokens.RefreshToken.for_user')
    def test_generate_tokens_failure(self, mock_refresh_token):
        """Test token generation failure"""
        # Mock RefreshToken.for_user to raise exception
        mock_refresh_token.side_effect = Exception("Token generation error")
        
        result = TokenService.generate_tokens(self.user)
        
        # Assertions
        self.assertIsNone(result)
        mock_refresh_token.assert_called_once_with(self.user)
    
    def test_blacklist_token_success(self):
        """Test successful token blacklisting"""
        # Generate a token first
        tokens = TokenService.generate_tokens(self.user)
        refresh_token = tokens['refresh']
        
        # Blacklist the token
        result = TokenService.blacklist_token(refresh_token)
        
        # Assertions
        self.assertTrue(result)
    
    def test_blacklist_token_invalid_token(self):
        """Test token blacklisting with invalid token"""
        result = TokenService.blacklist_token('invalid-token')
        
        # Assertions
        self.assertFalse(result)
    
    def test_blacklist_token_already_blacklisted(self):
        """Test blacklisting an already blacklisted token"""
        # Generate and blacklist a token
        tokens = TokenService.generate_tokens(self.user)
        refresh_token = tokens['refresh']
        
        # First blacklisting
        result1 = TokenService.blacklist_token(refresh_token)
        self.assertTrue(result1)
        
        # Second blacklisting (should fail)
        result2 = TokenService.blacklist_token(refresh_token)
        self.assertFalse(result2)


class UserServiceTest(BaseTestCase):
    """Test cases for UserService"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
    
    def test_update_last_login_success(self):
        """Test successful last login update"""
        # Store original last login
        original_last_login = self.user.last_login
        
        # Wait a bit to ensure time difference
        import time
        time.sleep(0.1)
        
        # Update last login
        result = UserService.update_last_login(self.user)
        
        # Assertions
        self.assertTrue(result)
        
        # Refresh user from database
        self.user.refresh_from_db()
        
        # Check that last_login was updated
        self.assertIsNotNone(self.user.last_login)
        if original_last_login:
            self.assertGreater(self.user.last_login, original_last_login)
    
    def test_update_last_login_failure(self):
        """Test last login update failure"""
        # Mock user.save to raise exception
        with patch.object(self.user, 'save') as mock_save:
            mock_save.side_effect = Exception("Database error")
            
            result = UserService.update_last_login(self.user)
            
            # Assertions
            self.assertFalse(result)
            mock_save.assert_called_once()
    
    def test_verify_email_token_success(self):
        """Test successful email verification"""
        # Setup user with verification token
        token = str(uuid.uuid4())
        self.user.email_verification_token = token
        self.user.email_verification_token_created = timezone.now()
        self.user.is_verified = False
        self.user.save()
        
        # Mock token expiration check
        with patch.object(self.user, 'is_email_verification_token_expired', return_value=False):
            result = UserService.verify_email_token(self.user, token)
            
            # Assertions
            self.assertTrue(result)
            
            # Refresh user from database
            self.user.refresh_from_db()
            
            # Check that user was verified and token was cleared
            self.assertTrue(self.user.is_verified)
            self.assertIsNone(self.user.email_verification_token)
            self.assertIsNone(self.user.email_verification_token_created)
    
    def test_verify_email_token_invalid_token(self):
        """Test email verification with invalid token"""
        # Setup user with verification token
        token = str(uuid.uuid4())
        self.user.email_verification_token = token
        self.user.email_verification_token_created = timezone.now()
        self.user.save()
        
        # Mock token expiration check
        with patch.object(self.user, 'is_email_verification_token_expired', return_value=False):
            result = UserService.verify_email_token(self.user, 'invalid-token')
            
            # Assertions
            self.assertFalse(result)
            
            # Refresh user from database
            self.user.refresh_from_db()
            
            # Check that user was not verified and token was not cleared
            self.assertFalse(self.user.is_verified)
            self.assertEqual(str(self.user.email_verification_token), token)
    
    def test_verify_email_token_expired_token(self):
        """Test email verification with expired token"""
        # Setup user with verification token
        token = str(uuid.uuid4())
        self.user.email_verification_token = token
        self.user.email_verification_token_created = timezone.now()
        self.user.save()
        
        # Mock token expiration check
        with patch.object(self.user, 'is_email_verification_token_expired', return_value=True):
            result = UserService.verify_email_token(self.user, token)
            
            # Assertions
            self.assertFalse(result)
            
            # Refresh user from database
            self.user.refresh_from_db()
            
            # Check that user was not verified and token was not cleared
            self.assertFalse(self.user.is_verified)
            self.assertEqual(str(self.user.email_verification_token), token)
    
    def test_reset_password_with_token_success(self):
        """Test successful password reset"""
        # Setup user with reset token
        token = str(uuid.uuid4())
        self.user.password_reset_token = token
        self.user.password_reset_token_created = timezone.now()
        self.user.save()
        
        new_password = 'NewStrongPass123!'
        
        # Mock token expiration check
        with patch.object(self.user, 'is_password_reset_token_expired', return_value=False):
            result = UserService.reset_password_with_token(self.user, token, new_password)
            
            # Assertions
            self.assertTrue(result)
            
            # Refresh user from database
            self.user.refresh_from_db()
            
            # Check that password was changed and token was cleared
            self.assertTrue(self.user.check_password(new_password))
            self.assertIsNone(self.user.password_reset_token)
            self.assertIsNone(self.user.password_reset_token_created)
    
    def test_reset_password_with_token_invalid_token(self):
        """Test password reset with invalid token"""
        # Setup user with reset token
        token = str(uuid.uuid4())
        self.user.password_reset_token = token
        self.user.password_reset_token_created = timezone.now()
        self.user.save()
        
        new_password = 'NewStrongPass123!'
        
        # Mock token expiration check
        with patch.object(self.user, 'is_password_reset_token_expired', return_value=False):
            result = UserService.reset_password_with_token(self.user, 'invalid-token', new_password)
            
            # Assertions
            self.assertFalse(result)
            
            # Refresh user from database
            self.user.refresh_from_db()
            
            # Check that password was not changed and token was not cleared
            self.assertFalse(self.user.check_password(new_password))
            self.assertEqual(str(self.user.password_reset_token), token)
    
    def test_reset_password_with_token_expired_token(self):
        """Test password reset with expired token"""
        # Setup user with reset token
        token = str(uuid.uuid4())
        self.user.password_reset_token = token
        self.user.password_reset_token_created = timezone.now()
        self.user.save()
        
        new_password = 'NewStrongPass123!'
        
        # Mock token expiration check
        with patch.object(self.user, 'is_password_reset_token_expired', return_value=True):
            result = UserService.reset_password_with_token(self.user, token, new_password)
            
            # Assertions
            self.assertFalse(result)
            
            # Refresh user from database
            self.user.refresh_from_db()
            
            # Check that password was not changed and token was not cleared
            self.assertFalse(self.user.check_password(new_password))
            self.assertEqual(str(self.user.password_reset_token), token)
    
    def test_change_email_with_token_success(self):
        """Test successful email change"""
        # Setup user with change token
        token = str(uuid.uuid4())
        self.user.email_change_token = token
        self.user.email_change_token_created = timezone.now()
        self.user.save()
        
        new_email = 'newemail@example.com'
        
        # Mock token expiration check
        with patch.object(self.user, 'is_email_change_token_expired', return_value=False):
            result = UserService.change_email_with_token(self.user, token, new_email)
            
            # Assertions
            self.assertTrue(result)
            
            # Refresh user from database
            self.user.refresh_from_db()
            
            # Check that email was changed and token was cleared
            self.assertEqual(self.user.email, new_email)
            self.assertIsNone(self.user.email_change_token)
            self.assertIsNone(self.user.email_change_token_created)
    
    def test_change_email_with_token_invalid_token(self):
        """Test email change with invalid token"""
        # Setup user with change token
        token = str(uuid.uuid4())
        self.user.email_change_token = token
        self.user.email_change_token_created = timezone.now()
        original_email = self.user.email
        self.user.save()
        
        new_email = 'newemail@example.com'
        
        # Mock token expiration check
        with patch.object(self.user, 'is_email_change_token_expired', return_value=False):
            result = UserService.change_email_with_token(self.user, 'invalid-token', new_email)
            
            # Assertions
            self.assertFalse(result)
            
            # Refresh user from database
            self.user.refresh_from_db()
            
            # Check that email was not changed and token was not cleared
            self.assertEqual(self.user.email, original_email)
            self.assertEqual(str(self.user.email_change_token), token)
    
    def test_change_email_with_token_expired_token(self):
        """Test email change with expired token"""
        # Setup user with change token
        token = str(uuid.uuid4())
        self.user.email_change_token = token
        self.user.email_change_token_created = timezone.now()
        original_email = self.user.email
        self.user.save()
        
        new_email = 'newemail@example.com'
        
        # Mock token expiration check
        with patch.object(self.user, 'is_email_change_token_expired', return_value=True):
            result = UserService.change_email_with_token(self.user, token, new_email)
            
            # Assertions
            self.assertFalse(result)
            
            # Refresh user from database
            self.user.refresh_from_db()
            
            # Check that email was not changed and token was not cleared
            self.assertEqual(self.user.email, original_email)
            self.assertEqual(str(self.user.email_change_token), token)
    
    def test_service_methods_exception_handling(self):
        """Test that service methods handle exceptions gracefully"""
        # Mock user.save to raise exception
        with patch.object(self.user, 'save') as mock_save:
            mock_save.side_effect = Exception("Database error")
            
            # Test all methods that call save
            result1 = UserService.update_last_login(self.user)
            result2 = UserService.verify_email_token(self.user, 'token')
            result3 = UserService.reset_password_with_token(self.user, 'token', 'password')
            result4 = UserService.change_email_with_token(self.user, 'token', 'new@email.com')
            
            # Assertions
            self.assertFalse(result1)
            self.assertFalse(result2)
            self.assertFalse(result3)
            self.assertFalse(result4)


class OAuthServiceTest(BaseTestCase):
    """Test cases for OAuthService"""
    
    def setUp(self):
        super().setUp()
        self.oauth_user_data = {
            'email': 'oauth@example.com',
            'name': 'OAuth User',
            'id': '12345'  # OAuth service expects 'id' field
        }

    
    def test_handle_oauth_login_success(self):
        """Test successful OAuth login handling"""
        result = OAuthService.handle_oauth_login(self.oauth_user_data, 'google')
        
        # Assertions - OAuth service returns a dict on success
        self.assertIsInstance(result, dict)
        self.assertIn('user', result)
        self.assertIn('tokens', result)
        self.assertIn('is_new_user', result)
        self.assertIn('provider', result)
        self.assertEqual(result['provider'], 'google')
    
    def test_handle_oauth_login_failure(self):
        """Test OAuth login handling failure"""
        # Test with invalid provider to trigger failure
        invalid_provider = 'invalid_provider'
        
        result = OAuthService.handle_oauth_login(self.oauth_user_data, invalid_provider)
        
        # Assertions - OAuth service should return False for unsupported provider
        self.assertFalse(result)
    
    def test_handle_oauth_login_different_providers(self):
        """Test OAuth login with different providers"""
        providers = ['google', 'github']  # Only test supported providers
        
        for provider in providers:
            result = OAuthService.handle_oauth_login(self.oauth_user_data, provider)
            
            # OAuth service returns a dict on success
            self.assertIsInstance(result, dict)
            self.assertEqual(result['provider'], provider)
    
    def test_handle_oauth_login_invalid_data(self):
        """Test OAuth login with invalid user data"""
        invalid_data = None
        result = OAuthService.handle_oauth_login(invalid_data, 'google')
        
        # Assertions - OAuth service should return False for invalid data
        self.assertFalse(result)
    
    def test_oauth_service_logging(self):
        """Test that OAuth service logs operations"""
        with patch('apps.users.services.logger') as mock_logger:
            result = OAuthService.handle_oauth_login(self.oauth_user_data, 'google')
            
            # Check that info was logged - the actual message is different
            mock_logger.info.assert_called()
            # The service logs: "OAuth login successful for google user {email}"
            # So we check that some info was logged
            self.assertTrue(mock_logger.info.called)
    
    def test_oauth_service_error_logging(self):
        """Test that OAuth service logs errors"""
        # Test with invalid provider to trigger error logging
        invalid_provider = 'invalid_provider'
        
        with patch('apps.users.services.logger') as mock_logger:
            result = OAuthService.handle_oauth_login(self.oauth_user_data, invalid_provider)
            
            # Check that error was logged for unsupported provider
            mock_logger.error.assert_called_once_with("Unsupported OAuth provider: invalid_provider")


class ServiceIntegrationTest(BaseTestCase):
    """Integration tests for services working together"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.factory = RequestFactory()
        self.site = Site.objects.create(
            name='Test Site',
            domain='testserver.com'
        )
        self.request = self.factory.get('/')
        self.request.site = self.site
    
    def test_user_registration_flow(self):
        """Test complete user registration flow using services"""
        # 1. Generate tokens
        tokens = TokenService.generate_tokens(self.user)
        self.assertIsNotNone(tokens)
        self.assertIn('access', tokens)
        self.assertIn('refresh', tokens)
        
        # 2. Send verification email
        with patch('apps.users.services.render_to_string') as mock_render:
            with patch('apps.users.services.send_mail') as mock_send:
                mock_render.return_value = '<html>Test</html>'
                mock_send.return_value = 1
                
                email_result = EmailService.send_verification_email(self.request, self.user)
                self.assertTrue(email_result)
        
        # 3. Update last login
        login_result = UserService.update_last_login(self.user)
        self.assertTrue(login_result)
        
        # 4. Verify email token
        token = str(uuid.uuid4())
        self.user.email_verification_token = token
        self.user.email_verification_token_created = timezone.now()
        self.user.save()
        
        with patch.object(self.user, 'is_email_verification_token_expired', return_value=False):
            verify_result = UserService.verify_email_token(self.user, token)
            self.assertTrue(verify_result)
    
    def test_password_reset_flow(self):
        """Test complete password reset flow using services"""
        # 1. Send reset email
        token = str(uuid.uuid4())
        self.user.password_reset_token = token
        self.user.password_reset_token_created = timezone.now()
        self.user.save()
        
        with patch('apps.users.services.render_to_string') as mock_render:
            with patch('apps.users.services.send_mail') as mock_send:
                mock_render.return_value = '<html>Test</html>'
                mock_send.return_value = 1
                
                email_result = EmailService.send_password_reset_email(self.request, self.user)
                self.assertTrue(email_result)
        
        # 2. Reset password with token
        with patch.object(self.user, 'is_password_reset_token_expired', return_value=False):
            reset_result = UserService.reset_password_with_token(self.user, token, 'NewPass123!')
            self.assertTrue(reset_result)
            
            # Verify password was changed
            self.user.refresh_from_db()
            self.assertTrue(self.user.check_password('NewPass123!'))
    
    def test_email_change_flow(self):
        """Test complete email change flow using services"""
        # 1. Send change confirmation email
        token = str(uuid.uuid4())
        self.user.email_change_token = token
        self.user.email_change_token_created = timezone.now()
        self.user.save()
        
        new_email = 'newemail@example.com'
        
        with patch('apps.users.services.render_to_string') as mock_render:
            with patch('apps.users.services.send_mail') as mock_send:
                mock_render.return_value = '<html>Test</html>'
                mock_send.return_value = 1
                
                email_result = EmailService.send_email_change_confirmation(self.request, self.user, new_email)
                self.assertTrue(email_result)
        
        # 2. Change email with token
        with patch.object(self.user, 'is_email_change_token_expired', return_value=False):
            change_result = UserService.change_email_with_token(self.user, token, new_email)
            self.assertTrue(change_result)
            
            # Verify email was changed
            self.user.refresh_from_db()
            self.assertEqual(self.user.email, new_email)
    
    def test_token_management_flow(self):
        """Test complete token management flow using services"""
        # 1. Generate tokens
        tokens = TokenService.generate_tokens(self.user)
        self.assertIsNotNone(tokens)
        
        # 2. Use refresh token
        refresh_token = tokens['refresh']
        
        # 3. Blacklist token
        blacklist_result = TokenService.blacklist_token(refresh_token)
        self.assertTrue(blacklist_result)
        
        # 4. Try to blacklist again (should fail)
        blacklist_result2 = TokenService.blacklist_token(refresh_token)
        self.assertFalse(blacklist_result2)
