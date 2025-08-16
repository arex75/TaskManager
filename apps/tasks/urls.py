from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TagViewSet,
    TaskViewSet,
    SubtaskViewSet,
    CommentViewSet,
    AttachmentViewSet,
    DashboardViewSet
)

app_name = 'tasks'

# Create a router and register our ViewSets with it
router = DefaultRouter()

# Tag endpoints
router.register(r'tags', TagViewSet, basename='tag')

# Task endpoints
router.register(r'tasks', TaskViewSet, basename='task')

# Subtask endpoints
router.register(r'subtasks', SubtaskViewSet, basename='subtask')

# Comment endpoints
router.register(r'comments', CommentViewSet, basename='comment')

# Attachment endpoints
router.register(r'attachments', AttachmentViewSet, basename='attachment')

# Dashboard endpoints
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

# The API URLs are now determined automatically by the router
urlpatterns = [
    # Include the router URLs
    path('', include(router.urls)),
]

# Additional custom URL patterns can be added here if needed
# For example, if you want to add specific endpoints that don't fit the ViewSet pattern
# urlpatterns += [
#     path('custom-endpoint/', views.custom_view, name='custom_endpoint'),
# ]
