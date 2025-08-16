from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from .views import views, oauth_views

app_name = 'users'

urlpatterns = [
    # JWT Token endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Authentication endpoints
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    
    # Password management
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password/reset/<uuid:token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),
    
    # Email management
    path('email/verify/<uuid:token>/', views.EmailVerificationView.as_view(), name='email_verify'),
    path('email/change/', views.EmailChangeRequestView.as_view(), name='email_change_request'),
    path('email/change/<uuid:token>/', views.EmailChangeConfirmView.as_view(), name='email_change_confirm'),
    
    # OAuth endpoints
    path('oauth/google/', oauth_views.GoogleOAuth2LoginView.as_view(), name='google_oauth'),
    path('oauth/github/', oauth_views.GitHubOAuth2LoginView.as_view(), name='github_oauth'),
    path('oauth/url/<str:provider>/', oauth_views.OAuthURLView.as_view(), name='oauth_url'),
    path('oauth/callback/<str:provider>/', oauth_views.OAuthCallbackView.as_view(), name='oauth_callback'),
    
    # Admin endpoints
    path('admin/users/', views.AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/users/<int:pk>/', views.AdminUserDetailView.as_view(), name='admin_user_detail'),
    path('admin/users/<int:user_id>/block/', views.AdminBlockUserView.as_view(), name='admin_block_user'),
    
    # Include dj-rest-auth URLs for additional functionality
    path('', include('dj_rest_auth.urls')),
    path('registration/', include('dj_rest_auth.registration.urls')),
]
