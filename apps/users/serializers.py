from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import CustomUser, UserRole
from core.utils import (
    validate_phone_number, validate_username_format, validate_password_strength,
    validate_email_domain, validate_name_format, validate_bio_length,
    validate_profile_image_size, validate_profile_image_format, clean_phone_number
)


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True, 
        validators=[validate_password, validate_password_strength]
    )
    password_confirm = serializers.CharField(write_only=True)
    username = serializers.CharField(validators=[validate_username_format])
    email = serializers.EmailField(validators=[validate_email_domain])
    first_name = serializers.CharField(required=False, validators=[validate_name_format])
    last_name = serializers.CharField(required=False, validators=[validate_name_format])
    name = serializers.CharField(required=False, validators=[validate_name_format])
    phone_number = serializers.CharField(required=False, validators=[validate_phone_number])
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'name', 'role', 'phone_number'
        ]
        extra_kwargs = {
            'role': {'required': False},
        }
    
    def validate(self, attrs):
        """Validate password confirmation and other business rules"""
        # Password confirmation
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Check if username already exists
        if CustomUser.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError("Username already exists")
        
        # Check if email already exists
        if CustomUser.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError("Email already exists")
        
        # Clean phone number if provided
        if attrs.get('phone_number'):
            attrs['phone_number'] = clean_phone_number(attrs['phone_number'])
        
        return attrs
    
    def create(self, validated_data):
        """Create new user"""
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate user credentials with case-sensitive username"""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Use case-sensitive lookup
            try:
                user = CustomUser.objects.get(username__exact=username)
                if user.check_password(password):
                    if not user.is_active:
                        raise serializers.ValidationError('User account is disabled')
                    attrs['user'] = user
                else:
                    raise serializers.ValidationError('Invalid credentials')
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError('Invalid credentials')
        else:
            raise serializers.ValidationError('Must include username and password')
        
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Validate email exists"""
        if not CustomUser.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError('No active user found with this email')
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    token = serializers.UUIDField()
    new_password = serializers.CharField(validators=[validate_password, validate_password_strength])
    new_password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password, validate_password_strength])
    new_password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        """Validate password confirmation and old password"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        
        user = self.context['request'].user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError("Old password is incorrect")
        
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'name',
            'role', 'is_active', 'is_verified', 'profile_image', 'bio',
            'phone_number', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'username', 'email', 'date_joined', 'last_login']


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    first_name = serializers.CharField(required=False, validators=[validate_name_format])
    last_name = serializers.CharField(required=False, validators=[validate_name_format])
    name = serializers.CharField(required=False, validators=[validate_name_format])
    bio = serializers.CharField(required=False, validators=[validate_bio_length])
    phone_number = serializers.CharField(required=False, validators=[validate_phone_number])
    profile_image = serializers.ImageField(required=False, validators=[validate_profile_image_size, validate_profile_image_format])
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'name', 'profile_image', 'bio', 'phone_number'
        ]
    
    def validate(self, attrs):
        """Validate update data"""
        # Clean phone number if provided
        if attrs.get('phone_number'):
            attrs['phone_number'] = clean_phone_number(attrs['phone_number'])
        
        return attrs


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management"""
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'name',
            'role', 'is_active', 'is_staff', 'is_superuser', 'is_verified',
            'is_deleted', 'is_blocked', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin updating users"""
    first_name = serializers.CharField(required=False, validators=[validate_name_format])
    last_name = serializers.CharField(required=False, validators=[validate_name_format])
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'is_superuser', 'is_verified', 'is_blocked'
        ]


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification"""
    token = serializers.UUIDField()


class EmailChangeRequestSerializer(serializers.Serializer):
    """Serializer for email change request"""
    new_email = serializers.EmailField(validators=[validate_email_domain])
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate password and new email"""
        user = self.context['request'].user
        
        # Check if password is correct
        if not user.check_password(attrs['password']):
            raise serializers.ValidationError("Password is incorrect")
        
        # Check if new email is different from current
        if attrs['new_email'] == user.email:
            raise serializers.ValidationError("New email must be different from current email")
        
        # Check if new email already exists
        if CustomUser.objects.filter(email=attrs['new_email']).exists():
            raise serializers.ValidationError("Email already exists")
        
        return attrs


class EmailChangeConfirmSerializer(serializers.Serializer):
    """Serializer for email change confirmation"""
    token = serializers.UUIDField()
