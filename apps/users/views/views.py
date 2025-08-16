from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from ..models import CustomUser
from ..serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    UserUpdateSerializer, AdminUserSerializer, AdminUserUpdateSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    PasswordChangeSerializer, EmailVerificationSerializer,
    EmailChangeRequestSerializer, EmailChangeConfirmSerializer
)
from ..services import EmailService, TokenService, UserService
from apps.config.response_decorator import (
    format_api_response, format_detail_response, format_update_response,
    format_create_response, format_delete_response, format_list_response
)


class UserRegistrationView(APIView):
    """User registration endpoint"""
    permission_classes = [permissions.AllowAny]
    
    @format_create_response("User registered successfully. Please check your email for verification.")
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate email verification token
            user.generate_email_verification_token()
            
            # Send verification email using service
            email_sent = EmailService.send_verification_email(request, user)
            
            # Generate JWT tokens using service
            tokens = TokenService.generate_tokens(user)
            
            if not tokens:
                raise ValidationError('Failed to generate authentication tokens')
            
            response_data = {
                'user': UserProfileSerializer(user).data,
                'tokens': tokens,
            }
            
            if not email_sent:
                response_data['warning'] = 'Account created but verification email could not be sent'
            
            return response_data
        
        raise ValidationError(serializer.errors)


class UserLoginView(APIView):
    """User login endpoint"""
    permission_classes = [permissions.AllowAny]
    
    @format_api_response("Login successful")
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Update last login using service
            UserService.update_last_login(user)
            
            # Generate JWT tokens using service
            tokens = TokenService.generate_tokens(user)
            
            if not tokens:
                raise ValidationError('Failed to generate authentication tokens')
            
            return {
                'user': UserProfileSerializer(user).data,
                'tokens': tokens,
            }
        
        raise ValidationError(serializer.errors)


class UserLogoutView(APIView):
    """User logout endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    @format_api_response("Logout successful")
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                # Blacklist token using service
                TokenService.blacklist_token(refresh_token)
            
            logout(request)
            return {'status': 'logged_out'}
        except Exception as e:
            raise ValidationError('Logout failed')


class UserProfileView(APIView):
    """User profile management"""
    permission_classes = [permissions.IsAuthenticated]
    
    @format_detail_response("User profile retrieved successfully")
    def get(self, request):
        """Get user profile"""
        serializer = UserProfileSerializer(request.user)
        return {'user': serializer.data}
    
    @format_update_response("Profile updated successfully")
    def put(self, request):
        """Update user profile"""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return {
                'user': UserProfileSerializer(request.user).data
            }
        raise ValidationError(serializer.errors)
    
    @format_update_response("Profile updated successfully")
    def patch(self, request):
        """Partial update of user profile"""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return {
                'user': UserProfileSerializer(request.user).data
            }
        raise ValidationError(serializer.errors)


class PasswordResetRequestView(APIView):
    """Request password reset"""
    permission_classes = [permissions.AllowAny]
    
    @format_update_response("Password reset email sent successfully")
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = CustomUser.objects.get(email=email)
            
            # Generate password reset token
            user.generate_password_reset_token()
            
            # Send password reset email using service
            email_sent = EmailService.send_password_reset_email(request, user)
            
            if email_sent:
                return {'status': 'email_sent'}
            else:
                raise ValidationError('Failed to send password reset email. Please try again.')
        
        raise ValidationError(serializer.errors)


class PasswordResetConfirmView(APIView):
    """Confirm password reset"""
    permission_classes = [permissions.AllowAny]
    
    @format_update_response("Password reset successful")
    def post(self, request, token):
        # Add token to request data for serializer validation
        data = request.data.copy()
        data['token'] = token
        serializer = PasswordResetConfirmSerializer(data=data)
        if serializer.is_valid():
            try:
                user = CustomUser.objects.get(password_reset_token=token)
                
                if user.is_password_reset_token_expired():
                    raise ValidationError('Token expired')
                
                # Set new password
                user.set_password(serializer.validated_data['new_password'])
                user.password_reset_token = None
                user.password_reset_token_expiration = None
                user.save()
                
                return {'status': 'reset_successful'}
            
            except CustomUser.DoesNotExist:
                raise ValidationError('Invalid token')
        
        raise ValidationError(serializer.errors)


class PasswordChangeView(APIView):
    """Change password"""
    permission_classes = [permissions.IsAuthenticated]
    
    @format_update_response("Password changed successfully")
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return {'status': 'changed'}
        
        raise ValidationError(serializer.errors)


class EmailVerificationView(APIView):
    """Verify email address"""
    permission_classes = [permissions.AllowAny]
    
    @format_update_response("Email verified successfully")
    def post(self, request, token):
        serializer = EmailVerificationSerializer(data={'token': token})
        if serializer.is_valid():
            try:
                user = CustomUser.objects.get(email_verification_token=token)
                
                if user.is_email_verification_token_expired():
                    raise ValidationError('Token expired')
                
                user.is_verified = True
                user.email_verification_token = None
                user.email_verification_token_expiration = None
                user.save()
                
                return {'status': 'verified'}
            
            except CustomUser.DoesNotExist:
                raise ValidationError('Invalid token')
        
        raise ValidationError(serializer.errors)


class EmailChangeRequestView(APIView):
    """Request email change"""
    permission_classes = [permissions.IsAuthenticated]
    
    @format_update_response("Email change request sent successfully")
    def post(self, request):
        serializer = EmailChangeRequestSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            new_email = serializer.validated_data['new_email']
            
            # Generate email change token
            user.generate_email_change_token()
            
            # Send email change confirmation email using service
            email_sent = EmailService.send_email_change_confirmation(request, user, new_email)
            
            if email_sent:
                return {'status': 'email_sent'}, 'Email change request sent. Please check your new email for confirmation.'
            else:
                raise ValidationError('Failed to send email change confirmation. Please try again.')
        
        raise ValidationError(serializer.errors)
    
    def send_email_change_email(self, request, user, new_email):
        """Send email change confirmation email"""
        # Use the service instead
        return EmailService.send_email_change_confirmation(request, user, new_email)


class EmailChangeConfirmView(APIView):
    """Confirm email change"""
    permission_classes = [permissions.AllowAny]
    
    @format_update_response("Email change confirmed")
    def post(self, request, token):
        serializer = EmailChangeConfirmSerializer(data={'token': token})
        if serializer.is_valid():
            try:
                user = CustomUser.objects.get(email_change_token=token)
                
                if user.is_email_change_token_expired():
                    raise ValidationError('Token expired')
                
                # Update email using service
                # Note: You'll need to store the new email temporarily in your model
                # For now, we'll just clear the token
                user.email_change_token = None
                user.email_change_token_expiration = None
                user.save()
                
                return {'status': 'confirmed'}
            
            except CustomUser.DoesNotExist:
                raise ValidationError('Invalid token')
        
        raise ValidationError(serializer.errors)


# Admin Views
class AdminUserListView(generics.ListAPIView):
    """List all users (admin only)"""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminUserSerializer
    queryset = CustomUser.objects.all()
    filterset_fields = ['role', 'is_active', 'is_verified', 'is_deleted', 'is_blocked']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'date_joined', 'last_login']
    # Uses global pagination configuration (CustomPagination with 20 items per page)
    
    @format_list_response("Users retrieved successfully")
    def list(self, request, *args, **kwargs):
        """List all users with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return serializer.data


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin user management"""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminUserUpdateSerializer
    queryset = CustomUser.objects.all()
    
    def perform_destroy(self, instance):
        """Soft delete user"""
        instance.soft_delete(deleted_by_user=self.request.user)
    
    @format_detail_response("User retrieved successfully")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve user details"""
        instance = self.get_object()
        # Use AdminUserSerializer for full user data
        serializer = AdminUserSerializer(instance)
        return serializer.data
    
    @format_update_response("User updated successfully")
    def update(self, request, *args, **kwargs):
        """Update user details"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return full user data after update
        full_serializer = AdminUserSerializer(instance)
        return full_serializer.data
    
    @format_update_response("User updated successfully")
    def partial_update(self, request, *args, **kwargs):
        """Partially update user details"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    @format_delete_response("User deleted successfully")
    def delete(self, request, *args, **kwargs):
        """Soft delete user"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return None


class AdminBlockUserView(APIView):
    """Block/unblock user (admin only)"""
    permission_classes = [permissions.IsAdminUser]
    
    @format_update_response("User status updated successfully")
    def post(self, request, user_id):
        user = get_object_or_404(CustomUser, id=user_id)
        action = request.data.get('action')
        
        if action == 'block':
            user.block_user()
            return {'action': 'blocked', 'user_id': user_id}
        elif action == 'unblock':
            user.unblock_user()
            return {'action': 'unblocked', 'user_id': user_id}
        else:
            raise ValidationError('Invalid action')


class AdminUserExportView(generics.ListAPIView):
    """Export all users (admin only)"""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminUserSerializer
    queryset = CustomUser.objects.all()
    filterset_fields = ['role', 'is_active', 'is_verified', 'is_deleted', 'is_blocked']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'email', 'date_joined', 'last_login']
    # Uses global pagination configuration (CustomPagination with 20 items per page)
    
    @format_list_response("Users exported successfully")
    def list(self, request, *args, **kwargs):
        """Export all users with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return serializer.data
