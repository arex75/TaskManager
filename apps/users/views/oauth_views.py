from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from rest_framework.exceptions import ValidationError
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from dj_rest_auth.registration.serializers import SocialLoginSerializer
from apps.config.response_decorator import format_api_response
from ..models import CustomUser
from ..serializers import UserProfileSerializer


class GoogleOAuth2LoginView(SocialLoginView):
    """Google OAuth2 login"""
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    serializer_class = SocialLoginSerializer
    
    def post(self, request, *args, **kwargs):
        try:
            # Generate JWT tokens first
            user = request.user
            refresh = RefreshToken.for_user(user)
            
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                response.data.update({
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    }
                })
            return response
        except Exception as e:
            raise ValidationError(f'Google OAuth authentication failed: {str(e)}')


class GitHubOAuth2LoginView(SocialLoginView):
    """GitHub OAuth2 login"""
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client
    serializer_class = SocialLoginSerializer
    
    def post(self, request, *args, **kwargs):
        try:
            # Generate JWT tokens first
            user = request.user
            refresh = RefreshToken.for_user(user)
            
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                response.data.update({
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    }
                })
            return response
        except Exception as e:
            raise ValidationError(f'GitHub OAuth authentication failed: {str(e)}')


class OAuthCallbackView(APIView):
    """Handle OAuth callback and token exchange"""
    permission_classes = [permissions.AllowAny]
    
    @format_api_response("OAuth callback processed successfully")
    def get(self, request, provider):
        """Handle OAuth callback"""
        code = request.GET.get('code')
        state = request.GET.get('state')
        
        if not code:
            raise ValidationError('Authorization code not provided')
        
        try:
            if provider == 'google':
                return self.handle_google_callback(request, code, state)
            elif provider == 'github':
                return self.handle_github_callback(request, code, state)
            else:
                raise ValidationError('Unsupported OAuth provider')
        except Exception as e:
            raise ValidationError(f'{provider.title()} OAuth callback failed: {str(e)}')
    
    def handle_google_callback(self, request, code, state):
        """Handle Google OAuth callback"""
        # This would typically involve exchanging the code for tokens
        # and then creating/authenticating the user
        # For now, we'll return data for testing purposes
        return {
            'provider': 'google',
            'code': code,
            'state': state,
            'status': 'callback_received'
        }
    
    def handle_github_callback(self, request, code, state):
        """Handle GitHub OAuth callback"""
        # This would typically involve exchanging the code for tokens
        # and then creating/authenticating the user
        # For now, we'll return data for testing purposes
        return {
            'provider': 'github',
            'code': code,
            'state': state,
            'status': 'callback_received'
        }


class OAuthURLView(APIView):
    """Get OAuth authorization URLs"""
    permission_classes = [permissions.AllowAny]
    
    @format_api_response("OAuth URL retrieved successfully")
    def get(self, request, provider):
        """Get OAuth authorization URL"""
        current_site = get_current_site(request)
        
        # Check if the provider is configured
        if provider not in settings.SOCIALACCOUNT_PROVIDERS:
            raise ValidationError('Unsupported OAuth provider')
        
        if provider == 'google':
            try:
                client_id = settings.SOCIALACCOUNT_PROVIDERS['google']['APP_ID']
                scope = ' '.join(settings.SOCIALACCOUNT_PROVIDERS['google']['SCOPE'])
            except KeyError:
                raise ValidationError('Google OAuth not properly configured')
                
            redirect_uri = f"http://{current_site.domain}/api/auth/oauth/callback/google/"
            
            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={client_id}&"
                f"redirect_uri={redirect_uri}&"
                f"scope={scope}&"
                f"response_type=code&"
                f"access_type=offline"
            )
            
        elif provider == 'github':
            try:
                client_id = settings.SOCIALACCOUNT_PROVIDERS['github']['APP_ID']
                scope = ' '.join(settings.SOCIALACCOUNT_PROVIDERS['github']['SCOPE'])
            except KeyError:
                raise ValidationError('GitHub OAuth not properly configured')
                
            redirect_uri = f"http://{current_site.domain}/api/auth/oauth/callback/github/"
            
            auth_url = (
                f"https://github.com/login/oauth/authorize?"
                f"client_id={client_id}&"
                f"redirect_uri={redirect_uri}&"
                f"scope={scope}&"
                f"response_type=code"
            )
            
        else:
            raise ValidationError('Unsupported OAuth provider')
        
        return {
            'provider': provider,
            'auth_url': auth_url,
            'redirect_uri': redirect_uri
        }
