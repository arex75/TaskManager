"""
Django management command for OAuth setup and management
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.google.provider import GoogleProvider
from allauth.socialaccount.providers.github.provider import GitHubProvider
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup and manage OAuth providers for the TaskManager application'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            choices=['google', 'github', 'all'],
            default='all',
            help='OAuth provider to setup (default: all)'
        )
        
        parser.add_argument(
            '--client-id',
            type=str,
            help='OAuth client ID for the provider'
        )
        
        parser.add_argument(
            '--client-secret',
            type=str,
            help='OAuth client secret for the provider'
        )
        
        parser.add_argument(
            '--redirect-uri',
            type=str,
            help='OAuth redirect URI for the provider'
        )
        
        parser.add_argument(
            '--check',
            action='store_true',
            help='Check OAuth configuration status'
        )
        
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up expired OAuth states and sessions'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing OAuth configuration'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution"""
        try:
            if options['check']:
                self.check_oauth_configuration()
            elif options['cleanup']:
                self.cleanup_oauth_data()
            else:
                self.setup_oauth_providers(options)
                
        except Exception as e:
            logger.error(f"OAuth setup command failed: {str(e)}")
            raise CommandError(f"OAuth setup failed: {str(e)}")
    
    def check_oauth_configuration(self):
        """Check OAuth configuration status"""
        self.stdout.write(self.style.SUCCESS("Checking OAuth configuration..."))
        
        # Check settings
        self.stdout.write("\n=== OAuth Settings ===")
        oauth_enabled = getattr(settings, 'OAUTH_ENABLED', False)
        self.stdout.write(f"OAuth Enabled: {'✅' if oauth_enabled else '❌'}")
        
        if not oauth_enabled:
            self.stdout.write(self.style.WARNING("OAuth is not enabled in settings"))
            return
        
        # Check Google OAuth
        self.stdout.write("\n=== Google OAuth ===")
        google_client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
        google_client_secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', None)
        google_redirect_uri = getattr(settings, 'GOOGLE_OAUTH_REDIRECT_URI', None)
        
        self.stdout.write(f"Client ID: {'✅' if google_client_id else '❌'}")
        self.stdout.write(f"Client Secret: {'✅' if google_client_secret else '❌'}")
        self.stdout.write(f"Redirect URI: {'✅' if google_redirect_uri else '❌'}")
        
        # Check GitHub OAuth
        self.stdout.write("\n=== GitHub OAuth ===")
        github_client_id = getattr(settings, 'GITHUB_OAUTH_CLIENT_ID', None)
        github_client_secret = getattr(settings, 'GITHUB_OAUTH_CLIENT_SECRET', None)
        github_redirect_uri = getattr(settings, 'GITHUB_OAUTH_REDIRECT_URI', None)
        
        self.stdout.write(f"Client ID: {'✅' if github_client_id else '❌'}")
        self.stdout.write(f"Client Secret: {'✅' if github_client_secret else '❌'}")
        self.stdout.write(f"Redirect URI: {'✅' if github_redirect_uri else '❌'}")
        
        # Check SocialApp models
        self.stdout.write("\n=== SocialApp Models ===")
        try:
            google_app = SocialApp.objects.filter(provider='google').first()
            github_app = SocialApp.objects.filter(provider='github').first()
            
            self.stdout.write(f"Google SocialApp: {'✅' if google_app else '❌'}")
            if google_app:
                self.stdout.write(f"  - Name: {google_app.name}")
                self.stdout.write(f"  - Client ID: {'✅' if google_app.client_id else '❌'}")
                self.stdout.write(f"  - Secret: {'✅' if google_app.secret else '❌'}")
            
            self.stdout.write(f"GitHub SocialApp: {'✅' if github_app else '❌'}")
            if github_app:
                self.stdout.write(f"  - Name: {github_app.name}")
                self.stdout.write(f"  - Client ID: {'✅' if github_app.client_id else '❌'}")
                self.stdout.write(f"  - Secret: {'✅' if github_app.secret else '❌'}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking SocialApp models: {str(e)}"))
        
        # Check required packages
        self.stdout.write("\n=== Required Packages ===")
        try:
            import requests
            self.stdout.write("requests: ✅")
        except ImportError:
            self.stdout.write("requests: ❌ (Required for OAuth)")
        
        try:
            from allauth.socialaccount.models import SocialAccount
            self.stdout.write("django-allauth: ✅")
        except ImportError:
            self.stdout.write("django-allauth: ❌ (Required for OAuth)")
        
        # Summary
        self.stdout.write("\n=== Summary ===")
        if oauth_enabled and google_client_id and google_client_secret and github_client_id and github_client_secret:
            self.stdout.write(self.style.SUCCESS("OAuth is fully configured! 🎉"))
        else:
            self.stdout.write(self.style.WARNING("OAuth configuration is incomplete. Use --setup to configure."))
    
    def setup_oauth_providers(self, options):
        """Setup OAuth providers"""
        provider = options['provider']
        
        if provider in ['google', 'all']:
            self.setup_google_oauth(options)
        
        if provider in ['github', 'all']:
            self.setup_github_oauth(options)
        
        self.stdout.write(self.style.SUCCESS("OAuth setup completed successfully!"))
    
    def setup_google_oauth(self, options):
        """Setup Google OAuth provider"""
        self.stdout.write("Setting up Google OAuth...")
        
        # Get configuration
        client_id = options['client_id'] or getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
        client_secret = options['client_secret'] or getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', None)
        redirect_uri = options['redirect_uri'] or getattr(settings, 'GOOGLE_OAUTH_REDIRECT_URI', None)
        
        if not all([client_id, client_secret, redirect_uri]):
            self.stdout.write(self.style.WARNING("Google OAuth configuration incomplete. Skipping..."))
            return
        
        # Create or update SocialApp
        try:
            social_app, created = SocialApp.objects.get_or_create(
                provider='google',
                defaults={
                    'name': 'Google',
                    'client_id': client_id,
                    'secret': client_secret,
                }
            )
            
            if not created and options['force']:
                social_app.client_id = client_id
                social_app.secret = client_secret
                social_app.save()
                self.stdout.write("Updated existing Google OAuth configuration")
            elif created:
                self.stdout.write("Created new Google OAuth configuration")
            else:
                self.stdout.write("Google OAuth configuration already exists (use --force to update)")
            
            # Add sites
            sites = Site.objects.all()
            if sites:
                social_app.sites.set(sites)
                self.stdout.write(f"Added {sites.count()} site(s) to Google OAuth")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to setup Google OAuth: {str(e)}"))
    
    def setup_github_oauth(self, options):
        """Setup GitHub OAuth provider"""
        self.stdout.write("Setting up GitHub OAuth...")
        
        # Get configuration
        client_id = options['client_id'] or getattr(settings, 'GITHUB_OAUTH_CLIENT_ID', None)
        client_secret = options['client_secret'] or getattr(settings, 'GITHUB_OAUTH_CLIENT_SECRET', None)
        redirect_uri = options['redirect_uri'] or getattr(settings, 'GITHUB_OAUTH_REDIRECT_URI', None)
        
        if not all([client_id, client_secret, redirect_uri]):
            self.stdout.write(self.style.WARNING("GitHub OAuth configuration incomplete. Skipping..."))
            return
        
        # Create or update SocialApp
        try:
            social_app, created = SocialApp.objects.get_or_create(
                provider='github',
                defaults={
                    'name': 'GitHub',
                    'client_id': client_id,
                    'secret': client_secret,
                }
            )
            
            if not created and options['force']:
                social_app.client_id = client_id
                social_app.secret = client_secret
                social_app.save()
                self.stdout.write("Updated existing GitHub OAuth configuration")
            elif created:
                self.stdout.write("Created new GitHub OAuth configuration")
            else:
                self.stdout.write("GitHub OAuth configuration already exists (use --force to update)")
            
            # Add sites
            sites = Site.objects.all()
            if sites:
                social_app.sites.set(sites)
                self.stdout.write(f"Added {sites.count()} site(s) to GitHub OAuth")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to setup GitHub OAuth: {str(e)}"))
    
    def cleanup_oauth_data(self):
        """Clean up expired OAuth data"""
        self.stdout.write("Cleaning up OAuth data...")
        
        try:
            from core.utils import OAuthStateManager
            
            # Clean up expired states
            result = OAuthStateManager.cleanup_expired_states()
            if result:
                self.stdout.write("✅ OAuth state cleanup completed")
            else:
                self.stdout.write("❌ OAuth state cleanup failed")
            
            # Clean up expired sessions (this would require a custom implementation)
            self.stdout.write("ℹ️  OAuth session cleanup relies on Django session cleanup")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to cleanup OAuth data: {str(e)}"))
    
    def get_oauth_urls(self):
        """Get OAuth URLs for configuration"""
        self.stdout.write("\n=== OAuth URLs for Configuration ===")
        
        # Get current site
        try:
            current_site = Site.objects.get_current()
            base_url = f"https://{current_site.domain}"
        except:
            base_url = "http://localhost:8000"
        
        self.stdout.write(f"Base URL: {base_url}")
        self.stdout.write(f"Google OAuth Redirect URI: {base_url}/oauth/google/callback/")
        self.stdout.write(f"GitHub OAuth Redirect URI: {base_url}/oauth/github/callback/")
        
        self.stdout.write("\n=== OAuth Provider URLs ===")
        self.stdout.write("Google OAuth: https://console.developers.google.com/")
        self.stdout.write("GitHub OAuth: https://github.com/settings/developers")
