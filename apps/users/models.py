from django.db import models
import uuid
from django.utils import timezone
from apps.config.base_model import BaseModel

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    USER = 'USER', 'User'
    MANAGER = 'MANAGER', 'Manager'

class CustomUserManager(models.Manager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        if not email:
            raise ValueError('The Email field must be set')
        
        # Hash the password manually
        if password:
            from django.contrib.auth.hashers import make_password
            extra_fields['password'] = make_password(password)
        
        user = self.model(username=username, email=email, **extra_fields)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)
    
    def get_by_natural_key(self, username):
        """Get user by natural key (username) - case sensitive"""
        return self.get(username=username)
    
    def get(self, **kwargs):
        """Override get to make username lookup case sensitive"""
        if 'username' in kwargs:
            # Use exact lookup for case-sensitive username matching
            return super().get(username__exact=kwargs['username'])
        return super().get(**kwargs)

class CustomUser(BaseModel):
    # Authentication fields
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    
    # Basic user fields
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=500, blank=True, null=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.USER)
    
    # Status fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    
    # Profile fields
    profile_image = models.ImageField(upload_to='profile_images/%Y/%m/%d/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Security and verification fields
    password_reset_token = models.UUIDField(null=True, blank=True, editable=False)
    password_reset_token_expiration = models.DateTimeField(null=True, blank=True)
    email_verification_token = models.UUIDField(null=True, blank=True, editable=False)
    email_verification_token_expiration = models.DateTimeField(null=True, blank=True)
    email_change_token = models.UUIDField(null=True, blank=True, editable=False)
    email_change_token_expiration = models.DateTimeField(null=True, blank=True)
    
    # Django auth fields
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    # Custom audit fields
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_users')

    # Custom manager
    objects = CustomUserManager()

    # Required for Django auth system
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['created_at']),
        ]
        # ordering is inherited from BaseModel

    def __str__(self):
        return f"{self.username} ({self.get_full_name()})"

    def get_full_name(self):
        if self.name:
            return f"{self.name} {self.last_name}".strip()
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.username

    def set_password(self, raw_password):
        """Set password with proper hashing"""
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Check if the provided password is correct"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)

    def has_perm(self, perm, obj=None):
        """Check if user has specific permission"""
        if self.is_superuser:
            return True
        if self.is_staff and perm in ['add', 'change', 'delete', 'view']:
            return True
        return False

    def has_module_perms(self, app_label):
        """Check if user has permissions for the app"""
        if self.is_superuser:
            return True
        if self.is_staff:
            return True
        return False

    def generate_password_reset_token(self):
        """Generate a new password reset token with expiration"""
        self.password_reset_token = uuid.uuid4()
        self.password_reset_token_expiration = timezone.now() + timezone.timedelta(hours=1)
        self.save()

    def generate_email_verification_token(self):
        """Generate a new email verification token with expiration"""
        self.email_verification_token = uuid.uuid4()
        self.email_verification_token_expiration = timezone.now() + timezone.timedelta(hours=24)
        self.save()

    def generate_email_change_token(self):
        """Generate a new email change token with expiration"""
        self.email_change_token = uuid.uuid4()
        self.email_change_token_expiration = timezone.now() + timezone.timedelta(hours=1)
        self.save()

    def is_password_reset_token_expired(self):
        """Check if password reset token is expired"""
        if not self.password_reset_token_expiration:
            return True
        return timezone.now() > self.password_reset_token_expiration

    def is_email_change_token_expired(self):
        """Check if email change token is expired"""
        if not self.email_change_token_expiration:
            return True
        return timezone.now() > self.email_change_token_expiration

    def is_email_verification_token_expired(self):
        """Check if email verification token is expired"""
        if not self.email_verification_token_expiration:
            return True
        return timezone.now() > self.email_verification_token_expiration

    def soft_delete(self, deleted_by_user=None):
        """Soft delete the user instead of hard deletion"""
        if not self.is_deleted:  # Only update if not already deleted
            self.is_deleted = True
            self.is_active = False
            self.deleted_at = timezone.now()
            if deleted_by_user:
                self.deleted_by = deleted_by_user
            self.save()

    def restore(self):
        """Restore a soft-deleted user"""
        self.is_deleted = False
        self.is_active = True
        self.deleted_at = None
        self.deleted_by = None
        self.save()

    def block_user(self):
        """Block a user from accessing the system"""
        self.is_blocked = True
        self.is_active = False
        self.save()

    def unblock_user(self):
        """Unblock a user"""
        self.is_blocked = False
        self.is_active = True
        self.save()

    @property
    def is_deleted_or_blocked(self):
        """Check if user is deleted or blocked"""
        return self.is_deleted or self.is_blocked

    # Django auth compatibility properties
    @property
    def is_anonymous(self):
        """Always False for authenticated users"""
        return False

    @property
    def is_authenticated(self):
        """Check if user is authenticated (not deleted/blocked)"""
        return not self.is_deleted_or_blocked

    def clean_tokens(self):
        """Clean expired tokens"""
        if self.is_password_reset_token_expired():
            self.password_reset_token = None
            self.password_reset_token_expiration = None
        
        if self.is_email_verification_token_expired():
            self.email_verification_token = None
            self.email_verification_token_expiration = None
        
        if self.is_email_change_token_expired():
            self.email_change_token = None
            self.email_change_token_expiration = None
        
        self.save()
