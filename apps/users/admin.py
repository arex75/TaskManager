from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser, UserRole


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for CustomUser model"""
    
    list_display = [
        'username', 'email', 'first_name', 'last_name', 'role', 'is_active',
        'is_verified', 'is_staff', 'is_superuser', 'date_joined', 'last_login'
    ]
    
    list_filter = [
        'role', 'is_active', 'is_verified', 'is_staff', 'is_superuser',
        'is_deleted', 'is_blocked', 'date_joined'
    ]
    
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    ordering = ['-date_joined']
    
    list_per_page = 25
    
    # Override filter_horizontal to remove non-existent fields
    filter_horizontal = ()
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('username', 'email', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'name', 'profile_image', 'bio', 'phone_number')
        }),
        ('Account Settings', {
            'fields': ('role', 'is_active', 'is_verified')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser')
        }),
        ('Status', {
            'fields': ('is_deleted', 'is_blocked', 'deleted_at', 'deleted_by')
        }),
        ('Timestamps', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
        ('Tokens', {
            'fields': (
                'password_reset_token', 'password_reset_token_expiration',
                'email_verification_token', 'email_change_token', 'email_change_token_expiration'
            ),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )
    
    readonly_fields = [
        'date_joined', 'last_login', 'password_reset_token', 'email_verification_token',
        'email_change_token'
    ]
    
    def get_queryset(self, request):
        """Show deleted users in admin"""
        return CustomUser.objects.all()
    
    def get_list_display(self, request):
        """Customize list display based on user permissions"""
        list_display = list(super().get_list_display(request))
        
        if not request.user.is_superuser:
            # Remove sensitive fields for non-superusers
            sensitive_fields = ['is_superuser', 'deleted_at', 'deleted_by']
            list_display = [field for field in list_display if field not in sensitive_fields]
        
        return list_display
    
    def get_fieldsets(self, request, obj=None):
        """Customize fieldsets based on user permissions"""
        fieldsets = list(super().get_fieldsets(request, obj))
        
        if not request.user.is_superuser:
            # Remove sensitive fieldsets for non-superusers
            sensitive_fieldsets = ['Permissions', 'Status', 'Tokens']
            fieldsets = [
                fieldset for fieldset in fieldsets 
                if fieldset[0] not in sensitive_fieldsets
            ]
        
        return fieldsets
    
    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        if not change:  # Creating new user
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """Customize readonly fields"""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        
        if obj and obj == request.user:
            # Users can't edit their own role or superuser status
            readonly_fields.extend(['role', 'is_superuser'])
        
        return readonly_fields
    
    def has_delete_permission(self, request, obj=None):
        """Custom delete permission"""
        if obj and obj == request.user:
            return False  # Users can't delete themselves
        return super().has_delete_permission(request, obj)
    
    def has_change_permission(self, request, obj=None):
        """Custom change permission"""
        if obj and obj == request.user:
            return True  # Users can edit their own profile
        return super().has_change_permission(request, obj)
    
    def get_actions(self, request):
        """Customize available actions"""
        actions = super().get_actions(request)
        
        if not request.user.is_superuser:
            # Remove dangerous actions for non-superusers
            dangerous_actions = ['delete_selected']
            for action in dangerous_actions:
                if action in actions:
                    del actions[action]
        
        return actions


# UserRole is a TextChoices class, not a model, so it can't be registered in admin
# But we can create a custom admin action to manage user roles
