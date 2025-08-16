"""
Centralized utility functions for TaskManager project
"""
import re
import uuid
import secrets
import hashlib
import base64
import json
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.contrib.sessions.backends.db import SessionStore
from django.core.validators import validate_email

logger = logging.getLogger(__name__)

# ============================================================================
# USER VALIDATION UTILITIES
# ============================================================================

def validate_phone_number(value):
    """Validate phone number format"""
    if not value or not value.strip():
        raise ValidationError(_('Phone number cannot be empty'))
    
    # Check for extra characters that shouldn't be in phone numbers
    if re.search(r'[^\d\s\-\(\)\+\.]', value):
        raise ValidationError(_('Phone number contains invalid characters'))
    
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', value)
    
    # Check if it's a valid phone number (7-15 digits)
    if len(cleaned) < 7 or len(cleaned) > 15:
        raise ValidationError(_('Phone number must be between 7 and 15 digits'))
    
    # Check if it contains only digits
    if not cleaned.isdigit():
        raise ValidationError(_('Phone number must contain only digits'))

def validate_username_format(value):
    """Validate username format"""
    if not value or not value.strip():
        raise ValidationError(_('Username cannot be empty'))
    
    # Username must be 1-30 characters, alphanumeric, underscores, dots, and hyphens
    if len(value) < 1 or len(value) > 30:
        raise ValidationError(_('Username must be between 1 and 30 characters'))
    
    if not re.match(r'^[a-zA-Z0-9_.-]+$', value):
        raise ValidationError(_('Username can only contain letters, numbers, underscores, dots, and hyphens'))
    
    # Username cannot start with a number
    if value[0].isdigit():
        raise ValidationError(_('Username cannot start with a number'))
    
    # Username cannot start or end with special characters
    if value[0] in '._-' or value[-1] in '._-':
        raise ValidationError(_('Username cannot start or end with special characters'))

def validate_password_strength(password):
    """Validate password strength beyond Django's default validation"""
    if not password:
        return
    
    # Check minimum length
    if len(password) < 8:
        raise ValidationError(_('Password must be at least 8 characters long'))
    
    # Check for uppercase letters
    if not any(c.isupper() for c in password):
        raise ValidationError(_('Password must contain at least one uppercase letter'))
    
    # Check for lowercase letters
    if not any(c.islower() for c in password):
        raise ValidationError(_('Password must contain at least one lowercase letter'))
    
    # Check for numbers
    if not any(c.isdigit() for c in password):
        raise ValidationError(_('Password must contain at least one number'))
    
    # Check for special characters
    special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
    if not any(c in special_chars for c in password):
        raise ValidationError(_('Password must contain at least one special character'))
    
    # Check for common patterns
    if password.lower() in ['password', '123456', 'qwerty', 'admin']:
        raise ValidationError(_('Password is too common'))
    
    # Check for common patterns with numbers
    if password.lower() in ['password123', 'password1', 'admin123', 'admin1']:
        raise ValidationError(_('Password is too common'))
    
    # Check for sequential numbers
    if password.isdigit() and len(password) >= 6:
        # Check for sequential patterns like 123456, 654321
        if password in ['123456', '123456789', '987654321', '654321']:
            raise ValidationError(_('Password contains sequential numbers'))
    
    # Check for repeated characters
    if len(set(password)) == 1:
        raise ValidationError(_('Password contains only repeated characters'))
    
    # Check for user information in password (this would need user context)
    # For now, just basic validation

def validate_email_domain(email):
    """Validate email domain"""
    if not email or not email.strip():
        raise ValidationError(_('Email cannot be empty'))
    
    # Basic email format validation
    if '@' not in email or email.count('@') != 1:
        raise ValidationError(_('Invalid email format'))
    
    # Check for common disposable email domains
    disposable_domains = [
        'tempmail.com', 'tempmail.org', '10minutemail.com', 'guerrillamail.com',
        'mailinator.com', 'yopmail.com', 'throwaway.email', 'throwaway.com',
        'getnada.com', 'sharklasers.com', 'grr.la', 'pokemail.net'
    ]
    
    domain = email.split('@')[-1].lower()
    if domain in disposable_domains:
        raise ValidationError(_('Disposable email addresses are not allowed'))

def validate_name_format(value):
    """Validate name format"""
    if not value or not value.strip():
        raise ValidationError(_('Name cannot be empty'))
    
    # Name must be 2-50 characters, letters, spaces, hyphens, and apostrophes only
    if len(value) < 2 or len(value) > 50:
        raise ValidationError(_('Name must be between 2 and 50 characters'))
    
    # More restrictive regex to catch more special characters
    if not re.match(r'^[a-zA-ZÀ-ÿ\s\'\-\.]+$', value):
        raise ValidationError(_('Name can only contain letters, spaces, hyphens, apostrophes, and periods'))
    
    # Additional check for special characters that might slip through regex
    if re.search(r'[^a-zA-ZÀ-ÿ\s\'\-\.]', value):
        raise ValidationError(_('Name can only contain letters, spaces, hyphens, apostrophes, and periods'))

def validate_bio_length(value):
    """Validate bio length"""
    if not value:
        return
    
    if len(value) > 500:
        raise ValidationError(_('Bio cannot exceed 500 characters'))
    

def validate_profile_image_size(image):
    """Validate profile image file size"""
    if not image:
        return
    
    # Maximum file size: 5MB
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    
    if image.size > max_size:
        raise ValidationError(_('Profile image file size cannot exceed 5MB'))

def validate_profile_image_format(image):
    """Validate profile image format"""
    if not image:
        return
    
    # Check if image has content_type attribute
    if hasattr(image, 'content_type') and image.content_type:
        content_type = image.content_type
    else:
        # Fallback to checking file extension from name
        if hasattr(image, 'name'):
            file_extension = image.name.lower().split('.')[-1] if '.' in image.name else ''
            
            # Map extensions to content types
            extension_to_content_type = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif'
            }
            content_type = extension_to_content_type.get(file_extension, '')
            
            # If we have a valid extension, use it
            if content_type:
                pass
            else:
                raise ValidationError(_('Profile image must be in JPEG, PNG, or GIF format'))
        else:
            raise ValidationError(_('Profile image must be in JPEG, PNG, or GIF format'))
    
    # Allowed formats
    allowed_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
    
    if content_type not in allowed_formats:
        raise ValidationError(_('Profile image must be in JPEG, PNG, or GIF format'))
    

    # Allowed formats
    allowed_formats = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
    
    if content_type not in allowed_formats:
        raise ValidationError(_('Profile image must be in JPEG, PNG, or GIF format'))

def validate_profile_image_dimensions(image):
    """Validate profile image dimensions"""
    if not image:
        return
    
    # Check if image has width and height attributes
    if not hasattr(image, 'width') or not hasattr(image, 'height'):
        raise ValidationError(_('Profile image dimensions cannot be determined'))
    
    # Maximum dimensions: 1000x1000 pixels
    max_width = 1000
    max_height = 1000
    
    # Check for invalid dimensions (negative, zero, or too large)
    if image.width <= 0 or image.height <= 0:
        raise ValidationError(_('Profile image dimensions must be positive'))
    
    if image.width > max_width or image.height > max_height:
        raise ValidationError(_('Profile image dimensions cannot exceed 1000x1000 pixels'))

def validate_social_media_links(value):
    """Validate social media links"""
    if not value:
        return
    
    # Basic URL validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(value):
        raise ValidationError(_('Please enter a valid URL'))
    
    # Additional security checks for dangerous URLs
    dangerous_patterns = [
        r'javascript:', r'data:', r'file:', r'ftp://', r'vbscript:', r'data:text/html'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            raise ValidationError(_('Please enter a valid URL'))
    

def clean_phone_number(phone_number):
    """Clean and format phone number"""
    if not phone_number or not phone_number.strip():
        raise ValueError("Phone number cannot be empty")
    
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', phone_number)
    
    # Validate that we have a reasonable phone number
    if len(cleaned) < 7 or len(cleaned) > 15:
        raise ValueError("Invalid phone number length")
    
    # If it's a US/Canada number (10 digits), add +1 prefix
    if len(cleaned) == 10:
        result = '+1' + cleaned
        return result
    
    # If it already has a country code (11+ digits), add + prefix
    if len(cleaned) >= 11:
        result = '+' + cleaned
        return result
    
    # Otherwise return as is (for shorter international numbers)
    return cleaned

def generate_unique_username(base_username):
    """Generate unique username, handling duplicates"""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
            
            # Prevent infinite loop
            if counter > 100:
                # Generate random username as fallback
                username = f"user_{uuid.uuid4().hex[:8]}"
                break
        
        return username
        
    except Exception as e:
        logger.error(f"Failed to generate unique username: {str(e)}")
        # Fallback to random username
        return f"user_{uuid.uuid4().hex[:8]}"

# ============================================================================
# OAUTH UTILITIES
# ============================================================================

class OAuthStateManager:
    """Manages OAuth state parameters for CSRF protection"""
    
    CACHE_PREFIX = 'oauth_state_'
    CACHE_TIMEOUT = 600  # 10 minutes
    
    @classmethod
    def generate_state(cls, provider: str, user_id: Optional[int] = None) -> str:
        """Generate a secure state parameter for OAuth"""
        try:
            # Generate random state
            state = secrets.token_urlsafe(32)
            
            # Create state data
            state_data = {
                'provider': provider,
                'timestamp': timezone.now().isoformat(),
                'user_id': user_id,
                'nonce': secrets.token_hex(16)
            }
            
            # Store state in cache
            cache_key = f"{cls.CACHE_PREFIX}{state}"
            cache.set(cache_key, state_data, cls.CACHE_TIMEOUT)
            
            logger.debug(f"Generated OAuth state for provider {provider}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to generate OAuth state: {str(e)}")
            return None
    
    @classmethod
    def validate_state(cls, state: str, provider: str) -> Tuple[bool, Optional[Dict]]:
        """Validate OAuth state parameter"""
        try:
            if not state:
                return False, None
            
            # Get state from cache
            cache_key = f"{cls.CACHE_PREFIX}{state}"
            state_data = cache.get(cache_key)
            
            if not state_data:
                logger.warning(f"OAuth state not found or expired: {state}")
                return False, None
            
            # Validate provider
            if state_data.get('provider') != provider:
                logger.warning(f"OAuth state provider mismatch: expected {provider}, got {state_data.get('provider')}")
                return False, None
            
            # Validate timestamp (check if not too old)
            try:
                timestamp = timezone.datetime.fromisoformat(state_data['timestamp'])
                if timezone.now() - timestamp > timezone.timedelta(minutes=10):
                    logger.warning(f"OAuth state expired: {state}")
                    cache.delete(cache_key)
                    return False, None
            except (ValueError, TypeError):
                logger.warning(f"Invalid OAuth state timestamp: {state_data.get('timestamp')}")
                return False, None
            
            # Remove state from cache after validation
            cache.delete(cache_key)
            
            logger.debug(f"OAuth state validated successfully for provider {provider}")
            return True, state_data
            
        except Exception as e:
            logger.error(f"Failed to validate OAuth state: {str(e)}")
            return False, None
    
    @classmethod
    def cleanup_expired_states(cls):
        """Clean up expired OAuth states (can be called by a management command)"""
        try:
            # This is a simple cleanup - in production you might want to use a more sophisticated approach
            # For now, we rely on cache expiration
            logger.info("OAuth state cleanup completed (using cache expiration)")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup OAuth states: {str(e)}")
            return False


class OAuthURLBuilder:
    """Builds OAuth URLs with proper parameters"""
    
    @staticmethod
    def build_authorization_url(provider: str, redirect_uri: str, 
                               scope: str = None, state: str = None, 
                               additional_params: Dict = None) -> Optional[str]:
        """Build OAuth authorization URL"""
        try:
            # OAuth provider configurations
            oauth_configs = {
                'google': {
                    'authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                    'scope': 'openid email profile',
                    'access_type': 'offline',
                    'prompt': 'consent',
                    'include_granted_scopes': 'true'
                },
                'github': {
                    'authorization_url': 'https://github.com/login/oauth/authorize',
                    'scope': 'read:user user:email',
                    'allow_signup': 'true'
                }
            }
            
            if provider not in oauth_configs:
                logger.error(f"Unsupported OAuth provider: {provider}")
                return None
            
            config = oauth_configs[provider]
            
            # Base parameters
            params = {
                'client_id': getattr(settings, f'{provider.upper()}_OAUTH_CLIENT_ID', ''),
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': scope or config.get('scope', ''),
            }
            
            # Add state for CSRF protection
            if state:
                params['state'] = state
            
            # Add provider-specific parameters
            if provider == 'google':
                params.update({
                    'access_type': config['access_type'],
                    'prompt': config['prompt'],
                    'include_granted_scopes': config['include_granted_scopes']
                })
            elif provider == 'github':
                params.update({
                    'allow_signup': config['allow_signup']
                })
            
            # Add additional parameters
            if additional_params:
                params.update(additional_params)
            
            # Build URL
            url = f"{config['authorization_url']}?{urlencode(params)}"
            
            logger.debug(f"Built OAuth authorization URL for {provider}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to build OAuth authorization URL for {provider}: {str(e)}")
            return None
    
    @staticmethod
    def build_callback_url(provider: str, base_url: str, 
                          success_redirect: str = None, error_redirect: str = None) -> str:
        """Build OAuth callback URL"""
        try:
            # OAuth URL patterns
            oauth_url_patterns = {
                'google': {'callback': 'oauth/callback/google'},
                'github': {'callback': 'oauth/callback/github'}
            }
            
            if provider not in oauth_url_patterns:
                logger.error(f"Unknown OAuth provider: {provider}")
                return base_url
            
            callback_pattern = oauth_url_patterns[provider]['callback']
            callback_url = f"{base_url}/{callback_pattern}/"
            
            # Add query parameters if provided
            query_params = {}
            if success_redirect:
                query_params['success_redirect'] = success_redirect
            if error_redirect:
                query_params['error_redirect'] = error_redirect
            
            if query_params:
                callback_url += f"?{urlencode(query_params)}"
            
            return callback_url
            
        except Exception as e:
            logger.error(f"Failed to build OAuth callback URL for {provider}: {str(e)}")
            return base_url


class OAuthDataProcessor:
    """Processes and validates OAuth data"""
    
    @staticmethod
    def extract_user_data(oauth_data: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """Extract and standardize user data from OAuth response"""
        try:
            # OAuth user field mappings
            oauth_user_field_mappings = {
                'google': {
                    'email': 'email',
                    'first_name': 'given_name',
                    'last_name': 'family_name',
                    'name': 'name',
                    'picture': 'picture',
                    'id': 'id'
                },
                'github': {
                    'email': 'email',
                    'first_name': 'name',
                    'last_name': None,  # GitHub doesn't provide separate first/last names
                    'name': 'login',
                    'picture': 'avatar_url',
                    'id': 'id'
                }
            }
            
            field_mapping = oauth_user_field_mappings.get(provider, {})
            if not field_mapping:
                logger.error(f"No field mapping found for OAuth provider: {provider}")
                return {}
            
            user_data = {}
            
            # Map fields according to provider configuration
            for standard_field, oauth_field in field_mapping.items():
                if oauth_field and oauth_field in oauth_data:
                    user_data[standard_field] = oauth_data[oauth_field]
            
            # Handle special cases
            if provider == 'github' and 'first_name' in user_data:
                # Split GitHub name into first and last names
                name_parts = user_data['first_name'].split(' ', 1)
                user_data['first_name'] = name_parts[0]
                user_data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
            
            # Add provider information
            user_data['oauth_provider'] = provider
            user_data['oauth_user_id'] = oauth_data.get(field_mapping.get('user_id', 'id'))
            
            # Validate required fields
            required_fields = ['email', 'oauth_user_id']
            missing_fields = [field for field in required_fields if not user_data.get(field)]
            
            if missing_fields:
                logger.warning(f"Missing required OAuth fields for {provider}: {missing_fields}")
            
            logger.debug(f"Extracted user data from {provider} OAuth: {list(user_data.keys())}")
            return user_data
            
        except Exception as e:
            logger.error(f"Failed to extract user data from {provider} OAuth: {str(e)}")
            return {}
    
    @staticmethod
    def validate_oauth_data(oauth_data: Dict[str, Any], provider: str) -> Tuple[bool, list]:
        """Validate OAuth data for required fields and format"""
        try:
            errors = []
            
            # Check if data is not empty
            if not oauth_data:
                errors.append("OAuth data is empty")
                return False, errors
            
            # Check required fields based on provider
            if provider == 'google':
                required_fields = ['id', 'email']
            elif provider == 'github':
                required_fields = ['id', 'login']  # GitHub uses 'login' for username
            else:
                required_fields = ['id', 'email']
            
            for field in required_fields:
                if field not in oauth_data or not oauth_data[field]:
                    errors.append(f"Missing required field: {field}")
            
            # Validate email format if present
            if 'email' in oauth_data and oauth_data['email']:
                try:
                    validate_email(oauth_data['email'])
                except Exception:
                    errors.append("Invalid email format")
            
            # Validate ID format
            if 'id' in oauth_data and oauth_data['id']:
                try:
                    int(oauth_data['id'])
                except (ValueError, TypeError):
                    errors.append("Invalid user ID format")
            
            is_valid = len(errors) == 0
            if not is_valid:
                logger.warning(f"OAuth data validation failed for {provider}: {errors}")
            
            return is_valid, errors
            
        except Exception as e:
            logger.error(f"Failed to validate OAuth data for {provider}: {str(e)}")
            return False, [f"Validation error: {str(e)}"]
    
    @staticmethod
    def sanitize_oauth_data(oauth_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize OAuth data by removing sensitive or unnecessary fields"""
        try:
            # Fields to remove for security
            sensitive_fields = [
                'access_token', 'refresh_token', 'token_type', 'expires_in',
                'scope', 'state', 'code', 'client_id', 'client_secret'
            ]
            
            # Fields to keep (user profile information)
            safe_fields = [
                'id', 'email', 'name', 'given_name', 'family_name',
                'picture', 'avatar_url', 'login', 'bio', 'location',
                'company', 'blog', 'twitter_username', 'locale', 'timezone'
            ]
            
            sanitized_data = {}
            
            for field in safe_fields:
                if field in oauth_data:
                    sanitized_data[field] = oauth_data[field]
            
            logger.debug(f"Sanitized OAuth data: removed {len(sensitive_fields)} sensitive fields")
            return sanitized_data
            
        except Exception as e:
            logger.error(f"Failed to sanitize OAuth data: {str(e)}")
            return oauth_data


class OAuthErrorHandler:
    """Handles OAuth-specific errors and provides user-friendly messages"""
    
    @staticmethod
    def handle_oauth_error(error_type: str, provider: str, 
                          original_error: str = None) -> Dict[str, Any]:
        """Handle OAuth errors and return user-friendly response"""
        try:
            # OAuth error messages
            oauth_error_messages = {
                'invalid_provider': 'Invalid OAuth provider specified',
                'authorization_failed': 'OAuth authorization failed',
                'token_exchange_failed': 'Failed to exchange authorization code for access token',
                'user_info_failed': 'Failed to retrieve user information from OAuth provider',
                'user_creation_failed': 'Failed to create user account from OAuth data',
                'provider_connection_failed': 'Failed to connect OAuth provider to user account',
                'invalid_state': 'Invalid OAuth state parameter',
                'access_denied': 'OAuth access was denied by the user',
                'server_error': 'OAuth provider server error',
                'network_error': 'Network error while communicating with OAuth provider',
                'unknown_error': 'An unexpected OAuth error occurred'
            }
            
            error_message = oauth_error_messages.get(error_type, "An OAuth error occurred")
            
            error_response = {
                'error': {
                    'type': error_type,
                    'message': error_message,
                    'provider': provider,
                    'timestamp': timezone.now().isoformat()
                }
            }
            
            # Add original error for debugging (only in development)
            if settings.DEBUG and original_error:
                error_response['error']['debug_info'] = original_error
            
            # Log the error
            logger.error(f"OAuth error for {provider}: {error_type} - {original_error or 'No details'}")
            
            return error_response
            
        except Exception as e:
            logger.error(f"Failed to handle OAuth error: {str(e)}")
            return {
                'error': {
                    'type': 'unknown_error',
                    'message': 'An unexpected error occurred',
                    'provider': provider,
                    'timestamp': timezone.now().isoformat()
                }
            }
    
    @staticmethod
    def is_oauth_error(response_data: Dict[str, Any]) -> bool:
        """Check if response contains OAuth error"""
        return 'error' in response_data and 'type' in response_data['error']
    
    @staticmethod
    def get_oauth_error_type(response_data: Dict[str, Any]) -> Optional[str]:
        """Get OAuth error type from response"""
        if OAuthErrorHandler.is_oauth_error(response_data):
            return response_data['error'].get('type')
        return None


class OAuthSessionManager:
    """Manages OAuth-related session data"""
    
    SESSION_PREFIX = 'oauth_'
    
    @staticmethod
    def store_oauth_data(session: SessionStore, provider: str, 
                         data: Dict[str, Any], expires_in: int = 300) -> bool:
        """Store OAuth data in session"""
        try:
            session_key = f"{OAuthSessionManager.SESSION_PREFIX}{provider}"
            session_data = {
                'data': data,
                'created_at': timezone.now().isoformat(),
                'expires_at': (timezone.now() + timezone.timedelta(seconds=expires_in)).isoformat()
            }
            
            session[session_key] = session_data
            session.modified = True
            
            logger.debug(f"Stored OAuth data in session for {provider}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store OAuth data in session: {str(e)}")
            return False
    
    @staticmethod
    def get_oauth_data(session: SessionStore, provider: str) -> Optional[Dict[str, Any]]:
        """Get OAuth data from session"""
        try:
            session_key = f"{OAuthSessionManager.SESSION_PREFIX}{provider}"
            session_data = session.get(session_key)
            
            if not session_data:
                return None
            
            # Check expiration
            try:
                expires_at = timezone.datetime.fromisoformat(session_data['expires_at'])
                if timezone.now() > expires_at:
                    # Remove expired data
                    del session[session_key]
                    session.modified = True
                    logger.debug(f"Removed expired OAuth session data for {provider}")
                    return None
            except (ValueError, TypeError):
                # Invalid timestamp, remove data
                del session[session_key]
                session.modified = True
                return None
            
            return session_data['data']
            
        except Exception as e:
            logger.error(f"Failed to get OAuth data from session: {str(e)}")
            return None
    
    @staticmethod
    def clear_oauth_data(session: SessionStore, provider: str = None) -> bool:
        """Clear OAuth data from session"""
        try:
            if provider:
                # Clear specific provider data
                session_key = f"{OAuthSessionManager.SESSION_PREFIX}{provider}"
                if session_key in session:
                    del session[session_key]
                    session.modified = True
                    logger.debug(f"Cleared OAuth session data for {provider}")
            else:
                # Clear all OAuth data
                keys_to_remove = [key for key in session.keys() 
                                 if key.startswith(OAuthSessionManager.SESSION_PREFIX)]
                for key in keys_to_remove:
                    del session[key]
                session.modified = True
                logger.debug(f"Cleared all OAuth session data")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear OAuth session data: {str(e)}")
            return False


# ============================================================================
# CONVENIENCE FUNCTIONS FOR OAUTH OPERATIONS
# ============================================================================

def generate_oauth_state(provider: str, user_id: Optional[int] = None) -> str:
    """Generate OAuth state parameter"""
    return OAuthStateManager.generate_state(provider, user_id)


def validate_oauth_state(state: str, provider: str) -> Tuple[bool, Optional[Dict]]:
    """Validate OAuth state parameter"""
    return OAuthStateManager.validate_state(state, provider)


def build_oauth_url(provider: str, redirect_uri: str, **kwargs) -> Optional[str]:
    """Build OAuth authorization URL"""
    return OAuthURLBuilder.build_authorization_url(provider, redirect_uri, **kwargs)


def process_oauth_data(oauth_data: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """Process and standardize OAuth data"""
    return OAuthDataProcessor.extract_user_data(oauth_data, provider)


def validate_oauth_response(oauth_data: Dict[str, Any], provider: str) -> Tuple[bool, list]:
    """Validate OAuth response data"""
    return OAuthDataProcessor.validate_oauth_data(oauth_data, provider)


def handle_oauth_error(error_type: str, provider: str, original_error: str = None) -> Dict[str, Any]:
    """Handle OAuth error and return user-friendly response"""
    return OAuthErrorHandler.handle_oauth_error(error_type, provider, original_error)


def store_oauth_session(session: SessionStore, provider: str, data: Dict[str, Any], 
                       expires_in: int = 300) -> bool:
    """Store OAuth data in session"""
    return OAuthSessionManager.store_oauth_data(session, provider, data, expires_in)


def get_oauth_session(session: SessionStore, provider: str) -> Optional[Dict[str, Any]]:
    """Get OAuth data from session"""
    return OAuthSessionManager.get_oauth_data(session, provider)


def clear_oauth_session(session: SessionStore, provider: str = None) -> bool:
    """Clear OAuth data from session"""
    return OAuthSessionManager.clear_oauth_data(session, provider)
