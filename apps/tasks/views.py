from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import Task, Subtask, Comment, Attachment, Tag
from .serializers import (
    TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer, TaskDetailSerializer,
    SubtaskSerializer, SubtaskCreateSerializer, SubtaskUpdateSerializer, SubtaskDetailSerializer,
    CommentSerializer, CommentCreateSerializer, CommentUpdateSerializer,
    AttachmentSerializer, AttachmentCreateSerializer, AttachmentUpdateSerializer,
    TagSerializer, TagCreateSerializer, TagUpdateSerializer
)
from .services import (
    TaskService, SubtaskService, CommentService, 
    AttachmentService, TagService, DashboardService
)
from apps.config.response_decorator import (
    format_list_response, format_detail_response, 
    format_create_response, format_update_response, format_delete_response,
    format_api_response
)
from apps.config.pagination import CustomPagination


class TagViewSet(viewsets.ModelViewSet):
    """ViewSet for Tag model"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'color']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return TagCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TagUpdateSerializer
        return TagSerializer
    
    @format_list_response("Tags retrieved successfully")
    def list(self, request, *args, **kwargs):
        """List all tags with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        # Return the paginated data structure with custom message
        return self.paginator.get_paginated_response(serializer.data, "Tags retrieved successfully")
    
    @format_create_response("Tag created successfully")
    def create(self, request, *args, **kwargs):
        """Create a new tag"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            tag = serializer.save()
            return TagSerializer(tag).data
        raise ValidationError(serializer.errors)
    
    @format_detail_response("Tag retrieved successfully")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific tag"""
        tag = self.get_object()
        serializer = self.get_serializer(tag)
        return serializer.data
    
    @format_update_response("Tag updated successfully")
    def update(self, request, *args, **kwargs):
        """Update a tag"""
        partial = kwargs.pop('partial', False)
        tag = self.get_object()
        serializer = self.get_serializer(tag, data=request.data, partial=partial)
        if serializer.is_valid():
            tag = serializer.save()
            return TagSerializer(tag).data
        raise ValidationError(serializer.errors)
    
    @format_delete_response("Tag deleted successfully")
    def destroy(self, request, *args, **kwargs):
        """Delete a tag"""
        tag = self.get_object()
        tag.delete()
        return None, status.HTTP_204_NO_CONTENT
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular tags"""
        popular_tags = TagService.get_popular_tags(limit=10)
        # Apply pagination to the result
        page = self.paginate_queryset(popular_tags)
        serializer = TagSerializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data, "Popular tags retrieved successfully")


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for Task model"""
    queryset = Task.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'completed', 'owner', 'assigned_to']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'due_date', 'created_at', 'priority', 'progress']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter tasks based on user permissions"""
        return TaskService.get_user_tasks(self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return TaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TaskUpdateSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        elif self.action == 'dashboard':
            return TaskDashboardSerializer
        return TaskSerializer
    
    @format_list_response("Tasks retrieved successfully")
    def list(self, request, *args, **kwargs):
        """List all tasks with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        # Return the paginated data structure with custom message
        return self.paginator.get_paginated_response(serializer.data, "Tasks retrieved successfully")
    
    @format_create_response("Task created successfully")
    def create(self, request, *args, **kwargs):
        """Create a new task"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            task = serializer.save(owner=request.user)
            return TaskDetailSerializer(task).data
        raise ValidationError(serializer.errors)
    
    @format_detail_response("Task retrieved successfully")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific task"""
        task = self.get_object()
        serializer = self.get_serializer(task)
        return serializer.data
    
    @format_update_response("Task updated successfully")
    def update(self, request, *args, **kwargs):
        """Update a task"""
        partial = kwargs.pop('partial', False)
        task = self.get_object()
        serializer = self.get_serializer(task, data=request.data, partial=partial)
        if serializer.is_valid():
            task = serializer.save()
            return TaskDetailSerializer(task).data
        raise ValidationError(serializer.errors)
    
    @format_delete_response("Task deleted successfully")
    def destroy(self, request, *args, **kwargs):
        """Delete a task"""
        task = self.get_object()
        task.delete()
        return None, status.HTTP_204_NO_CONTENT
    
    @action(detail=True, methods=['post'])
    @format_api_response("Task started successfully")
    def start(self, request, pk=None):
        """Start a task"""
        task = self.get_object()
        if TaskService.start_task(task, request.user):
            return TaskDetailSerializer(task).data
        raise ValidationError("Task cannot be started in its current status")
    
    @action(detail=True, methods=['post'])
    @format_api_response("Task completed successfully")
    def complete(self, request, pk=None):
        """Complete a task"""
        task = self.get_object()
        if TaskService.complete_task(task, request.user):
            return TaskDetailSerializer(task).data
        raise ValidationError("Task is already completed")
    
    @action(detail=True, methods=['post'])
    @format_api_response("Task cancelled successfully")
    def cancel(self, request, pk=None):
        """Cancel a task"""
        task = self.get_object()
        if TaskService.cancel_task(task, request.user):
            return TaskDetailSerializer(task).data
        raise ValidationError("Task cannot be cancelled in its current status")
    
    @action(detail=True, methods=['patch'])
    @format_api_response("Task progress updated successfully")
    def update_progress(self, request, pk=None):
        """Update task progress"""
        task = self.get_object()
        progress = request.data.get('progress')
        
        if progress is None:
            raise ValidationError("Progress value is required")
        
        if TaskService.update_task_progress(task, progress, request.user):
            return TaskDetailSerializer(task).data
        raise ValidationError("Progress must be between 0 and 100")
    
    @action(detail=True, methods=['post'])
    @format_api_response("Task paused successfully")
    def pause(self, request, pk=None):
        """Pause a task"""
        task = self.get_object()
        if TaskService.pause_task(task, request.user):
            return TaskDetailSerializer(task).data
        raise ValidationError("Task cannot be paused in its current status")
    
    @action(detail=True, methods=['post'])
    @format_api_response("Task resumed successfully")
    def resume(self, request, pk=None):
        """Resume a task"""
        task = self.get_object()
        if TaskService.resume_task(task, request.user):
            return TaskDetailSerializer(task).data
        raise ValidationError("Task cannot be resumed in its current status")
    
    @action(detail=True, methods=['patch'])
    @format_api_response("Task assigned successfully")
    def assign(self, request, pk=None):
        """Assign a task to a user"""
        task = self.get_object()
        assignee_id = request.data.get('assignee')
        
        if assignee_id is None:
            raise ValidationError("Assignee ID is required")
        
        if TaskService.assign_task(task, assignee_id, request.user):
            return TaskDetailSerializer(task).data
        raise ValidationError("Invalid assignee or task cannot be assigned")
    
    @action(detail=False, methods=['get'])
    @format_list_response("Dashboard tasks retrieved successfully")
    def dashboard(self, request):
        """Get tasks for dashboard view"""
        tasks = self.get_queryset()
        # Apply pagination to the result
        page = self.paginate_queryset(tasks)
        serializer = TaskDashboardSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'])
    @format_list_response("User tasks retrieved successfully")
    def my_tasks(self, request):
        """Get current user's tasks"""
        tasks = self.get_queryset().filter(
            Q(owner=request.user) | Q(assigned_to=request.user)
        )
        # Apply pagination to the result
        page = self.paginate_queryset(tasks)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'])
    @format_list_response("Overdue tasks retrieved successfully")
    def overdue(self, request):
        """Get overdue tasks"""
        overdue_tasks = TaskService.get_overdue_tasks(request.user)
        # Apply pagination to the result
        page = self.paginate_queryset(overdue_tasks)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'])
    @format_list_response("Tasks due soon retrieved successfully")
    def due_soon(self, request):
        """Get tasks due soon (next 7 days)"""
        due_soon_tasks = TaskService.get_tasks_due_soon(request.user, 7)
        # Apply pagination to the result
        page = self.paginate_queryset(due_soon_tasks)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class SubtaskViewSet(viewsets.ModelViewSet):
    """ViewSet for Subtask model"""
    queryset = Subtask.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['completed', 'priority', 'task']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at', 'priority', 'progress']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter subtasks based on user permissions"""
        return SubtaskService.get_user_subtasks(self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return SubtaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SubtaskUpdateSerializer
        elif self.action == 'retrieve':
            return SubtaskDetailSerializer
        return SubtaskSerializer
    
    @format_list_response("Subtasks retrieved successfully")
    def list(self, request, *args, **kwargs):
        """List all subtasks with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        # Return the paginated data structure with custom message
        return self.paginator.get_paginated_response(serializer.data, "Subtasks retrieved successfully")
    
    @format_create_response("Subtask created successfully")
    def create(self, request, *args, **kwargs):
        """Create a new subtask"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            task_id = request.data.get('task')
            if task_id:
                try:
                    task = Task.objects.get(id=task_id)
                except Task.DoesNotExist:
                    raise ValidationError("Task with the specified ID does not exist")
                
                # Check if user has permission to create subtasks for this task
                if not (task.owner == request.user or task.assigned_to == request.user or request.user.is_staff):
                    raise ValidationError("You don't have permission to create subtasks for this task")
                
                subtask = serializer.save(task=task)
                return SubtaskDetailSerializer(subtask).data
            raise ValidationError("Task ID is required")
        raise ValidationError(serializer.errors)
    
    @format_detail_response("Subtask retrieved successfully")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific subtask"""
        subtask = self.get_object()
        serializer = self.get_serializer(subtask)
        return serializer.data
    
    @format_update_response("Subtask updated successfully")
    def update(self, request, *args, **kwargs):
        """Update a subtask"""
        partial = kwargs.pop('partial', False)
        subtask = self.get_object()
        serializer = self.get_serializer(subtask, data=request.data, partial=partial)
        if serializer.is_valid():
            subtask = serializer.save()
            return SubtaskDetailSerializer(subtask).data
        raise ValidationError(serializer.errors)
    
    @format_delete_response("Subtask deleted successfully")
    def destroy(self, request, *args, **kwargs):
        """Delete a subtask"""
        subtask = self.get_object()
        subtask.delete()
        return None, status.HTTP_204_NO_CONTENT
    
    @action(detail=True, methods=['post'])
    @format_api_response("Subtask completed successfully")
    def complete(self, request, pk=None):
        """Complete a subtask"""
        subtask = self.get_object()
        if SubtaskService.complete_subtask(subtask, request.user):
            return SubtaskDetailSerializer(subtask).data
        raise ValidationError("Subtask is already completed")
    
    @action(detail=True, methods=['post'])
    @format_api_response("Subtask progress updated successfully")
    def update_progress(self, request, pk=None):
        """Update subtask progress"""
        subtask = self.get_object()
        progress = request.data.get('progress')
        
        if progress is None:
            raise ValidationError("Progress value is required")
        
        try:
            progress = int(progress)
        except (ValueError, TypeError):
            raise ValidationError("Progress must be a valid integer")
        
        if SubtaskService.update_subtask_progress(subtask, progress, request.user):
            return SubtaskDetailSerializer(subtask).data
        raise ValidationError("Progress must be between 0 and 100")
    
    @action(detail=True, methods=['post'])
    @format_api_response("Subtask started successfully")
    def start(self, request, pk=None):
        """Start a subtask"""
        subtask = self.get_object()
        if SubtaskService.start_subtask(subtask, request.user):
            return SubtaskDetailSerializer(subtask).data
        raise ValidationError("Subtask is already started")
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue subtasks"""
        overdue_subtasks = SubtaskService.get_overdue_subtasks(request.user)
        # Apply pagination to the result
        page = self.paginate_queryset(overdue_subtasks)
        serializer = self.get_serializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data, "Overdue subtasks retrieved successfully")
    
    @action(detail=False, methods=['get'])
    def due_soon(self, request):
        """Get subtasks due soon (next 7 days)"""
        due_soon_subtasks = SubtaskService.get_subtasks_due_soon(request.user, 7)
        # Apply pagination to the result
        page = self.paginate_queryset(due_soon_subtasks)
        serializer = self.get_serializer(page, many=True)
        return self.paginator.get_paginated_response(serializer.data, "Subtasks due soon retrieved successfully")
    
    @action(detail=True, methods=['post'])
    @format_api_response("Subtask paused successfully")
    def pause(self, request, pk=None):
        """Pause a subtask"""
        subtask = self.get_object()
        if SubtaskService.pause_subtask(subtask, request.user):
            return SubtaskDetailSerializer(subtask).data
        raise ValidationError("Subtask cannot be paused")
    
    @action(detail=True, methods=['post'])
    @format_api_response("Subtask resumed successfully")
    def resume(self, request, pk=None):
        """Resume a subtask"""
        subtask = self.get_object()
        if SubtaskService.resume_subtask(subtask, request.user):
            return SubtaskDetailSerializer(subtask).data
        raise ValidationError("Subtask cannot be resumed")


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet for Comment model"""
    queryset = Comment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task', 'subtask', 'is_internal', 'author']
    search_fields = ['content']
    ordering_fields = ['content', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter comments based on user permissions"""
        return CommentService.get_user_comments(self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return CommentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CommentUpdateSerializer
        return CommentSerializer
    
    @format_list_response("Comments retrieved successfully")
    def list(self, request, *args, **kwargs):
        """List all comments with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        # Return the paginated data structure with custom message
        return self.paginator.get_paginated_response(serializer.data, "Comments retrieved successfully")
    
    @format_create_response("Comment created successfully")
    def create(self, request, *args, **kwargs):
        """Create a new comment"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            comment = serializer.save(author=request.user)
            return CommentSerializer(comment).data
        raise ValidationError(serializer.errors)
    
    @format_detail_response("Comment retrieved successfully")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific comment"""
        comment = self.get_object()
        serializer = self.get_serializer(comment)
        return serializer.data
    
    @format_update_response("Comment updated successfully")
    def update(self, request, *args, **kwargs):
        """Update a comment"""
        partial = kwargs.pop('partial', False)
        comment = self.get_object()
        
        if not CommentService.can_edit_comment(comment, request.user):
            raise PermissionDenied("You can only edit your own comments")
        
        serializer = self.get_serializer(comment, data=request.data, partial=partial)
        if serializer.is_valid():
            comment = serializer.save()
            return CommentSerializer(comment).data
        raise DjangoValidationError(serializer.errors)
    
    @format_delete_response("Comment deleted successfully")
    def destroy(self, request, *args, **kwargs):
        """Delete a comment"""
        comment = self.get_object()
        
        if not CommentService.can_delete_comment(comment, request.user):
            raise PermissionDenied("You can only delete your own comments")
        
        comment.delete()
        return None, status.HTTP_204_NO_CONTENT


class AttachmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Attachment model"""
    queryset = Attachment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task', 'subtask', 'file_type', 'uploaded_by']
    search_fields = ['original_filename', 'description']
    ordering_fields = ['original_filename', 'created_at', 'file_size']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter attachments based on user permissions"""
        return AttachmentService.get_user_attachments(self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return AttachmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AttachmentUpdateSerializer
        return AttachmentSerializer
    
    @format_list_response("Attachments retrieved successfully")
    def list(self, request, *args, **kwargs):
        """List all attachments with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        # Return the paginated data structure with custom message
        return self.paginator.get_paginated_response(serializer.data, "Attachments retrieved successfully")
    
    @format_create_response("Attachment uploaded successfully")
    def create(self, request, *args, **kwargs):
        """Upload a new attachment"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Check permissions before saving
            task = serializer.validated_data.get('task')
            subtask = serializer.validated_data.get('subtask')
            
            if task and not (task.owner == request.user or task.assigned_to == request.user or request.user.is_staff):
                raise PermissionDenied("You can only create attachments for tasks you own or are assigned to")
            
            if subtask and not (subtask.task.owner == request.user or subtask.task.assigned_to == request.user or request.user.is_staff):
                raise PermissionDenied("You can only create attachments for subtasks from tasks you own or are assigned to")
            
            attachment = serializer.save(uploaded_by=request.user)
            return AttachmentSerializer(attachment).data
        raise ValidationError(serializer.errors)
    
    @format_detail_response("Attachment retrieved successfully")
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific attachment"""
        attachment = self.get_object()
        
        # Check if user has permission to view this attachment
        if not AttachmentService.can_download_attachment(attachment, request.user):
            raise PermissionDenied("You don't have permission to view this attachment")
        
        serializer = self.get_serializer(attachment)
        return serializer.data
    
    @format_update_response("Attachment updated successfully")
    def update(self, request, *args, **kwargs):
        """Update an attachment"""
        partial = kwargs.pop('partial', False)
        attachment = self.get_object()
        
        if not AttachmentService.can_edit_attachment(attachment, request.user):
            raise PermissionDenied("You can only edit your own attachments")
        
        serializer = self.get_serializer(attachment, data=request.data, partial=partial)
        if serializer.is_valid():
            attachment = serializer.save()
            return AttachmentSerializer(attachment).data
        raise ValidationError(serializer.errors)
    
    @format_delete_response("Attachment deleted successfully")
    def destroy(self, request, *args, **kwargs):
        """Delete an attachment"""
        attachment = self.get_object()
        
        if not AttachmentService.can_delete_attachment(attachment, request.user):
            raise PermissionDenied("You can only delete your own attachments")
        
        attachment.delete()
        return None, status.HTTP_204_NO_CONTENT
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download an attachment"""
        attachment = self.get_object()
        
        # Check if user has permission to download
        if not AttachmentService.can_download_attachment(attachment, request.user):
            raise PermissionDenied("You don't have permission to download this attachment")
        
        # Return file response
        from django.http import FileResponse
        
        try:
            response = FileResponse(attachment.file, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{attachment.original_filename}"'
            return response
        except (OSError, IOError):
            raise ValidationError("File not found or inaccessible")


class DashboardViewSet(viewsets.ViewSet):
    """ViewSet for dashboard and analytics"""
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination
    
    @format_list_response("Dashboard overview retrieved successfully")
    def list(self, request):
        """Get comprehensive dashboard overview"""
        dashboard_data = DashboardService.get_dashboard_overview(request.user)
        return dashboard_data
    
    @action(detail=False, methods=['get'])
    @format_detail_response("User task summary retrieved successfully")
    def summary(self, request):
        """Get user task summary"""
        summary = TaskService.get_user_task_summary(request.user)
        serializer = UserTaskSummarySerializer(summary)
        return serializer.data
    
    @action(detail=False, methods=['get'])
    @format_detail_response("Recent activity retrieved successfully")
    def recent_activity(self, request):
        """Get recent activity"""
        recent_activity = DashboardService.get_recent_activity(request.user, limit=10)
        
        # Apply pagination to comments
        comments_page = self.paginate_queryset(recent_activity['recent_comments'])
        comments_data = CommentSerializer(comments_page, many=True).data
        return self.get_paginated_response(comments_data)
    
    @action(detail=False, methods=['get'])
    @format_detail_response("Task statistics retrieved successfully")
    def statistics(self, request):
        """Get task statistics for dashboard"""
        stats = DashboardService.get_task_statistics(request.user)
        return stats
