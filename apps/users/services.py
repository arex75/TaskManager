from django.core.mail import send_mail
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from core.utils import generate_unique_username
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for handling all email operations"""
    
    @staticmethod
    def send_verification_email(request, user):
        """Send email verification email"""
        try:
            current_site = get_current_site(request)
            verification_url = f"http://{current_site.domain}/api/auth/verify-email/{user.email_verification_token}/"
            
            subject = 'Verify your email address'
            html_message = render_to_string('users/email_verification.html', {
                'user': user,
                'verification_url': verification_url,
                'site_name': current_site.name
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Verification email sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(request, user):
        """Send password reset email"""
        try:
            current_site = get_current_site(request)
            reset_url = f"http://{current_site.domain}/api/auth/reset-password/{user.password_reset_token}/"
            
            subject = 'Reset your password'
            html_message = render_to_string('users/password_reset.html', {
                'user': user,
                'reset_url': reset_url,
                'site_name': current_site.name
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Password reset email sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_email_change_confirmation(request, user, new_email):
        """Send email change confirmation email"""
        try:
            current_site = get_current_site(request)
            confirmation_url = f"http://{current_site.domain}/api/auth/change-email/{user.email_change_token}/"
            
            subject = 'Confirm your new email address'
            html_message = render_to_string('users/email_change_confirmation.html', {
                'user': user,
                'new_email': new_email,
                'confirmation_url': confirmation_url,
                'site_name': current_site.name
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [new_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Email change confirmation sent to {new_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email change confirmation to {new_email}: {str(e)}")
            return False


class TokenService:
    """Service for handling JWT tokens"""
    
    @staticmethod
    def generate_tokens(user):
        """Generate JWT access and refresh tokens"""
        try:
            refresh = RefreshToken.for_user(user)
            return {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        except Exception as e:
            logger.error(f"Failed to generate tokens for user {user.id}: {str(e)}")
            return None
    
    @staticmethod
    def blacklist_token(refresh_token):
        """Blacklist a refresh token"""
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("Token blacklisted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist token: {str(e)}")
            return False


class UserService:
    """Service for handling user operations"""
    
    @staticmethod
    def update_last_login(user):
        """Update user's last login timestamp"""
        try:
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            return True
        except Exception as e:
            logger.error(f"Failed to update last login for user {user.id}: {str(e)}")
            return False
    
    @staticmethod
    def verify_email_token(user, token):
        """Verify email verification token"""
        try:
            if user.email_verification_token == token and not user.is_email_verification_token_expired():
                user.is_verified = True
                user.email_verification_token = None
                user.email_verification_token_created = None
                user.save()
                logger.info(f"Email verified for user {user.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to verify email for user {user.id}: {str(e)}")
            return False
    
    @staticmethod
    def reset_password_with_token(user, token, new_password):
        """Reset password using reset token"""
        try:
            if user.password_reset_token == token and not user.is_password_reset_token_expired():
                user.set_password(new_password)
                user.password_reset_token = None
                user.password_reset_token_created = None
                user.save()
                logger.info(f"Password reset for user {user.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to reset password for user {user.id}: {str(e)}")
            return False
    
    @staticmethod
    def change_email_with_token(user, token, new_email):
        """Change email using change token"""
        try:
            if user.email_change_token == token and not user.is_email_change_token_expired():
                user.email = new_email
                user.email_change_token = None
                user.email_change_token_created = None
                user.save()
                logger.info(f"Email changed for user {user.id} to {new_email}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to change email for user {user.id}: {str(e)}")
            return False


class OAuthService:
    """Service for handling OAuth operations with dynamic provider support"""
    
    # Supported OAuth providers and their configurations
    SUPPORTED_PROVIDERS = {
        'google': {
            'user_info_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
            'email_field': 'email',
            'name_field': 'name',
            'first_name_field': 'given_name',
            'last_name_field': 'family_name',
            'picture_field': 'picture',
            'id_field': 'id',
        },
        'github': {
            'user_info_url': 'https://api.github.com/user',
            'email_url': 'https://api.github.com/user/emails',
            'email_field': 'email',
            'name_field': 'login',
            'first_name_field': 'name',
            'last_name_field': None,  # GitHub doesn't provide separate first/last names
            'picture_field': 'avatar_url',
            'id_field': 'id',
        }
    }
    
    @staticmethod
    def handle_oauth_login(oauth_user_data, provider):
        """Handle OAuth login/registration with dynamic provider support"""
        try:
            if provider not in OAuthService.SUPPORTED_PROVIDERS:
                logger.error(f"Unsupported OAuth provider: {provider}")
                return False
            
            # Extract user information based on provider
            user_info = OAuthService._extract_user_info(oauth_user_data, provider)
            if not user_info:
                logger.error(f"Failed to extract user info from {provider} OAuth data")
                return False
            
            # Find or create user
            user, is_new_user = OAuthService._find_or_create_user(user_info, provider)
            if not user:
                logger.error(f"Failed to find or create user for {provider} OAuth")
                return False
            
            # Generate authentication tokens
            tokens = TokenService.generate_tokens(user)
            if not tokens:
                logger.error(f"Failed to generate tokens for OAuth user {user.id}")
                return False
            
            # Update user's last login
            UserService.update_last_login(user)
            
            # Log the OAuth login
            logger.info(f"OAuth login successful for {provider} user {user.email}")
            
            return {
                'user': user,
                'tokens': tokens,
                'is_new_user': is_new_user,
                'provider': provider
            }
            
        except Exception as e:
            logger.error(f"Failed to handle OAuth login for provider {provider}: {str(e)}")
            return False
    
    @staticmethod
    def handle_oauth_callback(auth_code, provider, redirect_uri):
        """Handle OAuth callback with authorization code"""
        try:
            if provider not in OAuthService.SUPPORTED_PROVIDERS:
                logger.error(f"Unsupported OAuth provider: {provider}")
                return False
            
            # Exchange authorization code for access token
            access_token = OAuthService._exchange_code_for_token(auth_code, provider, redirect_uri)
            if not access_token:
                logger.error(f"Failed to exchange code for token with {provider}")
                return False
            
            # Get user information using access token
            user_info = OAuthService._get_user_info(access_token, provider)
            if not user_info:
                logger.error(f"Failed to get user info from {provider}")
                return False
            
            # Handle OAuth login with user info
            result = OAuthService.handle_oauth_login(user_info, provider)
            if result:
                result['access_token'] = access_token
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle OAuth callback for provider {provider}: {str(e)}")
            return False
    
    @staticmethod
    def _extract_user_info(oauth_user_data, provider):
        """Extract standardized user information from OAuth provider data"""
        try:
            provider_config = OAuthService.SUPPORTED_PROVIDERS[provider]
            
            # Extract basic user information
            user_info = {
                'provider': provider,
                'provider_user_id': oauth_user_data.get(provider_config['id_field']),
                'email': oauth_user_data.get(provider_config['email_field']),
                'username': oauth_user_data.get(provider_config['name_field']),
                'first_name': oauth_user_data.get(provider_config['first_name_field']),
                'last_name': oauth_user_data.get(provider_config['last_name_field']),
                'picture_url': oauth_user_data.get(provider_config['picture_field']),
                'raw_data': oauth_user_data
            }
            
            # Handle GitHub special case (no separate first/last names)
            if provider == 'github' and user_info['first_name']:
                # Split the name field into first and last names
                name_parts = user_info['first_name'].split(' ', 1)
                user_info['first_name'] = name_parts[0]
                user_info['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
            
            # Generate username if not provided
            if not user_info['username']:
                user_info['username'] = generate_unique_username(user_info['email'])
            
            # Validate required fields
            if not user_info['email'] or not user_info['provider_user_id']:
                logger.error(f"Missing required OAuth data: email={user_info['email']}, id={user_info['provider_user_id']}")
                return None
            
            return user_info
            
        except Exception as e:
            logger.error(f"Failed to extract user info from {provider} OAuth data: {str(e)}")
            return None
    
    @staticmethod
    def _find_or_create_user(user_info, provider):
        """Find existing user or create new one from OAuth data"""
        try:
            User = get_user_model()
            
            # First, try to find user by email
            user = User.objects.filter(email=user_info['email']).first()
            
            if user:
                # User exists, check if they have this OAuth provider connected
                if not OAuthService._is_oauth_provider_connected(user, provider, user_info['provider_user_id']):
                    # Connect the OAuth provider to existing user
                    OAuthService._connect_oauth_provider(user, provider, user_info['provider_user_id'])
                
                logger.info(f"OAuth login for existing user: {user.email}")
                return user, False
            
            # User doesn't exist, create new one
            user = OAuthService._create_user_from_oauth(user_info, provider)
            if user:
                logger.info(f"OAuth registration for new user: {user.email}")
                return user, True
            
            return None, False
            
        except Exception as e:
            logger.error(f"Failed to find or create user from OAuth: {str(e)}")
            return None, False
    
    @staticmethod
    def _create_user_from_oauth(user_info, provider):
        """Create new user from OAuth information"""
        try:
            User = get_user_model()
            
            # Generate unique username
            username = generate_unique_username(user_info['username'])
            
            # Create user with minimal required fields
            user = User.objects.create_user(
                username=username,
                email=user_info['email'],
                password=None,  # OAuth users don't have passwords initially
                first_name=user_info['first_name'] or '',
                last_name=user_info['last_name'] or '',
                name=f"{user_info['first_name'] or ''} {user_info['last_name'] or ''}".strip(),
                is_verified=True,  # OAuth users are pre-verified
                is_active=True
            )
            
            # Connect OAuth provider
            OAuthService._connect_oauth_provider(user, provider, user_info['provider_user_id'])
            
            # Set profile picture if available
            if user_info['picture_url']:
                user.profile_image = user_info['picture_url']
                user.save(update_fields=['profile_image'])
            
            logger.info(f"Created new user from OAuth: {user.email}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user from OAuth: {str(e)}")
            return None
    
    # This method has been moved to core.utils.generate_unique_username
    
    @staticmethod
    def _connect_oauth_provider(user, provider, provider_user_id):
        """Connect OAuth provider to user account"""
        try:
            from allauth.socialaccount.models import SocialAccount, SocialApp
            
            # Get or create social app
            social_app, created = SocialApp.objects.get_or_create(
                provider=provider,
                defaults={
                    'name': provider.title(),
                    'client_id': f'{provider}_client_id',  # You'll need to configure this
                    'secret': f'{provider}_client_secret'  # You'll need to configure this
                }
            )
            
            # Create or update social account
            social_account, created = SocialAccount.objects.get_or_create(
                user=user,
                provider=provider,
                defaults={'uid': str(provider_user_id)}
            )
            
            if not created:
                # Update existing social account
                social_account.uid = str(provider_user_id)
                social_account.save(update_fields=['uid'])
            
            logger.info(f"Connected {provider} OAuth provider to user {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect OAuth provider {provider} to user {user.id}: {str(e)}")
            return False
    
    @staticmethod
    def _is_oauth_provider_connected(user, provider, provider_user_id):
        """Check if user has specific OAuth provider connected"""
        try:
            from allauth.socialaccount.models import SocialAccount
            
            return SocialAccount.objects.filter(
                user=user,
                provider=provider,
                uid=str(provider_user_id)
            ).exists()
            
        except Exception as e:
            logger.error(f"Failed to check OAuth provider connection: {str(e)}")
            return False
    
    @staticmethod
    def _exchange_code_for_token(auth_code, provider, redirect_uri):
        """Exchange authorization code for access token"""
        try:
            # This is a placeholder - you'll need to implement the actual OAuth flow
            # based on your OAuth provider configuration
            
            if provider == 'google':
                return OAuthService._exchange_google_code(auth_code, redirect_uri)
            elif provider == 'github':
                return OAuthService._exchange_github_code(auth_code, redirect_uri)
            else:
                logger.error(f"Token exchange not implemented for provider: {provider}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to exchange code for token: {str(e)}")
            return None
    
    @staticmethod
    def _get_user_info(access_token, provider):
        """Get user information from OAuth provider using access token"""
        try:
            import requests
            
            provider_config = OAuthService.SUPPORTED_PROVIDERS[provider]
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Get basic user info
            response = requests.get(provider_config['user_info_url'], headers=headers)
            response.raise_for_status()
            user_data = response.json()
            
            # Handle GitHub special case - get email separately
            if provider == 'github':
                email_response = requests.get(provider_config['email_url'], headers=headers)
                if email_response.status_code == 200:
                    emails = email_response.json()
                    # Find primary email
                    primary_email = next((email['email'] for email in emails if email['primary']), None)
                    if primary_email:
                        user_data['email'] = primary_email
            
            return user_data
            
        except Exception as e:
            logger.error(f"Failed to get user info from {provider}: {str(e)}")
            return None
    
    @staticmethod
    def _exchange_google_code(auth_code, redirect_uri):
        """Exchange Google authorization code for access token"""
        try:
            import requests
            
            # You'll need to configure these in your settings
            client_id = settings.GOOGLE_OAUTH_CLIENT_ID
            client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET
            
            token_url = 'https://oauth2.googleapis.com/token'
            data = {
                'code': auth_code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            return token_data.get('access_token')
            
        except Exception as e:
            logger.error(f"Failed to exchange Google code for token: {str(e)}")
            return None
    
    @staticmethod
    def _exchange_github_code(auth_code, redirect_uri):
        """Exchange GitHub authorization code for access token"""
        try:
            import requests
            
            # You'll need to configure these in your settings
            client_id = settings.GITHUB_OAUTH_CLIENT_ID
            client_secret = settings.GITHUB_OAUTH_CLIENT_SECRET
            
            token_url = 'https://github.com/login/oauth/access_token'
            data = {
                'code': auth_code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri
            }
            
            headers = {'Accept': 'application/json'}
            response = requests.post(token_url, data=data, headers=headers)
            response.raise_for_status()
            token_data = response.json()
            
            return token_data.get('access_token')
            
        except Exception as e:
            logger.error(f"Failed to exchange GitHub code for token: {str(e)}")
            return None
    
    @staticmethod
    def disconnect_oauth_provider(user, provider):
        """Disconnect OAuth provider from user account"""
        try:
            from allauth.socialaccount.models import SocialAccount
            
            # Remove social account
            deleted_count = SocialAccount.objects.filter(
                user=user,
                provider=provider
            ).delete()[0]
            
            if deleted_count > 0:
                logger.info(f"Disconnected {provider} OAuth provider from user {user.email}")
                return True
            else:
                logger.warning(f"No {provider} OAuth provider found for user {user.email}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to disconnect OAuth provider {provider} from user {user.id}: {str(e)}")
            return False
    
    @staticmethod
    def get_connected_providers(user):
        """Get list of OAuth providers connected to user account"""
        try:
            from allauth.socialaccount.models import SocialAccount
            
            social_accounts = SocialAccount.objects.filter(user=user)
            providers = [account.provider for account in social_accounts]
            
            return providers
            
        except Exception as e:
            logger.error(f"Failed to get connected OAuth providers for user {user.id}: {str(e)}")
            return []
    
    @staticmethod
    def validate_oauth_provider(provider):
        """Validate if OAuth provider is supported"""
        return provider in OAuthService.SUPPORTED_PROVIDERS
    
    @staticmethod
    def get_provider_config(provider):
        """Get configuration for specific OAuth provider"""
        return OAuthService.SUPPORTED_PROVIDERS.get(provider, {})
