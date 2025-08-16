"""
Tests for OAuth authentication views
"""
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model

from unittest.mock import patch, MagicMock
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from allauth.account.models import EmailAddress

from tests.base import BaseAPITestCase

User = get_user_model()


class GoogleOAuth2LoginViewTest(BaseAPITestCase):
    """Test cases for Google OAuth2 login view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:google_oauth')
        
        # Create OAuth app for testing
        self.google_app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='test-google-client-id',
            secret='test-google-client-secret'
        )
    
    def tearDown(self):
        SocialApp.objects.all().delete()
        SocialAccount.objects.all().delete()
        SocialToken.objects.all().delete()
        EmailAddress.objects.all().delete()
        super().tearDown()
    
    def test_google_oauth_view_exists(self):
        """Test that Google OAuth view exists and is accessible"""
        response = self.client.get(self.url)
        # Should return method not allowed for GET, but view exists
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_google_oauth_post_requires_data(self):
        """Test that Google OAuth POST requires proper data"""
        response = self.client.post(self.url, {}, format='json')
        # Should return 400 for invalid data
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GitHubOAuth2LoginViewTest(BaseAPITestCase):
    """Test cases for GitHub OAuth2 login view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:github_oauth')
        
        # Create OAuth app for testing
        self.github_app = SocialApp.objects.create(
            provider='github',
            name='GitHub',
            client_id='test-github-client-id',
            secret='test-github-client-secret'
        )
    
    def tearDown(self):
        SocialApp.objects.all().delete()
        SocialAccount.objects.all().delete()
        SocialToken.objects.all().delete()
        EmailAddress.objects.all().delete()
        super().tearDown()
    
    def test_github_oauth_view_exists(self):
        """Test that GitHub OAuth view exists and is accessible"""
        response = self.client.get(self.url)
        # Should return method not allowed for GET, but view exists
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def test_github_oauth_post_requires_data(self):
        """Test that GitHub OAuth POST requires proper data"""
        response = self.client.post(self.url, {}, format='json')
        # Should return 400 for invalid data
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OAuthCallbackViewTest(BaseAPITestCase):
    """Test cases for OAuth callback view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:oauth_callback', kwargs={'provider': 'google'})
    
    def test_oauth_callback_missing_code(self):
        """Test OAuth callback with missing authorization code"""
        response = self.client.get(self.url)

        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error']['message'], 'Authorization code not provided')
    
    def test_oauth_callback_success(self):
        """Test successful OAuth callback"""
        response = self.client.get(f"{self.url}?code=test-code&state=test-state")
        
        # Assert success response with data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('provider', response.data['data'])
        self.assertIn('code', response.data['data'])
        self.assertIn('state', response.data['data'])
        self.assertEqual(response.data['data']['provider'], 'google')
    
    def test_oauth_callback_invalid_provider(self):
        """Test OAuth callback with invalid provider"""
        url = reverse('users:oauth_callback', kwargs={'provider': 'invalid'})
        response = self.client.get(f"{url}?code=test-code&state=test-state")
        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class OAuthURLViewTest(BaseAPITestCase):
    """Test cases for OAuth URL view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:oauth_url', kwargs={'provider': 'google'})
    
    @patch('django.conf.settings.SOCIALACCOUNT_PROVIDERS')
    def test_oauth_url_google_success(self, mock_providers):
        """Test successful Google OAuth URL generation"""
        # Mock the settings
        mock_providers.__getitem__.return_value = {
            'APP_ID': 'test-google-client-id',
            'SCOPE': ['openid', 'email', 'profile']
        }
        
        response = self.client.get(self.url)
        
        # Assert success response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('provider', response.data['data'])
        self.assertIn('auth_url', response.data['data'])
        self.assertIn('redirect_uri', response.data['data'])
        self.assertEqual(response.data['data']['provider'], 'google')
        self.assertIn('accounts.google.com', response.data['data']['auth_url'])
    
    @patch('django.conf.settings.SOCIALACCOUNT_PROVIDERS')
    def test_oauth_url_github_success(self, mock_providers):
        """Test successful GitHub OAuth URL generation"""
        # Mock the settings
        mock_providers.__getitem__.return_value = {
            'APP_ID': 'test-github-client-id',
            'SCOPE': ['read:user', 'user:email']
        }
        
        url = reverse('users:oauth_url', kwargs={'provider': 'github'})
        response = self.client.get(url)
        
        # Assert success response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('provider', response.data['data'])
        self.assertIn('auth_url', response.data['data'])
        self.assertIn('redirect_uri', response.data['data'])
        self.assertEqual(response.data['data']['provider'], 'github')
        self.assertIn('github.com', response.data['data']['auth_url'])
    
    def test_oauth_url_invalid_provider(self):
        """Test OAuth URL with invalid provider"""
        url = reverse('users:oauth_url', kwargs={'provider': 'invalid'})
        response = self.client.get(url)

        
        # Assert error response
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error']['message'], 'Unsupported OAuth provider')
    
    def test_oauth_url_unauthenticated(self):
        """Test OAuth URL without authentication (should work as it's public)"""
        response = self.client.get(self.url)
        
        # Should work without authentication
        self.assertEqual(response.status_code, status.HTTP_200_OK)
