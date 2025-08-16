from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404

from .models import Tag, Task, Subtask, Comment, Attachment
from .serializers import (
    TagSerializer, TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer,
    SubtaskSerializer, SubtaskCreateSerializer, SubtaskUpdateSerializer,
    CommentSerializer, CommentCreateSerializer, CommentUpdateSerializer,
    AttachmentSerializer, AttachmentCreateSerializer, AttachmentUpdateSerializer,
    TaskDetailSerializer, TaskDashboardSerializer, UserTaskSummarySerializer
)


class TagViewSet(viewsets.ModelViewSet):
    """ViewSet for Tag model"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'color']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for Task model"""
    queryset = Task.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'completed', 'owner', 'assigned_to']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'due_date', 'created_at', 'priority', 'progress']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter tasks based on user permissions"""
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            # Admins can see all tasks
            return Task.objects.all()
        else:
            # Regular users can see tasks they own, are assigned to, or are public
            return Task.objects.filter(
                Q(owner=user) | Q(assigned_to=user) | Q(owner__isnull=False)
            ).distinct()
    
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
    
    def perform_create(self, serializer):
        """Set owner when creating task"""
        serializer.save(owner=self.request.user)
    
    def perform_update(self, serializer):
        """Handle task status changes"""
        task = self.get_object()
        old_status = task.status
        new_status = serializer.validated_data.get('status', old_status)
        
        # Update task
        serializer.save()
        
        # Handle status-specific actions
        if new_status != old_status:
            if new_status == 'IN_PROGRESS' and old_status == 'TODO':
                task.start_task()
            elif new_status == 'DONE' and not task.completed:
                task.complete_task()
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a task"""
        task = self.get_object()
        task.start_task()
        return Response({'message': 'Task started successfully'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a task"""
        task = self.get_object()
        task.complete_task()
        return Response({'message': 'Task completed successfully'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a task"""
        task = self.get_object()
        task.cancel_task(cancelled_by_user=request.user)
        return Response({'message': 'Task cancelled successfully'})
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update task progress"""
        task = self.get_object()
        progress = request.data.get('progress')
        
        if progress is not None and 0 <= progress <= 100:
            task.update_progress(progress)
            return Response({'message': 'Progress updated successfully'})
        else:
            return Response(
                {'error': 'Progress must be between 0 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get tasks for dashboard view"""
        tasks = self.get_queryset()
        serializer = TaskDashboardSerializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        """Get current user's tasks"""
        tasks = self.get_queryset().filter(
            Q(owner=request.user) | Q(assigned_to=request.user)
        )
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue tasks"""
        tasks = self.get_queryset().filter(
            due_date__lt=timezone.now(),
            completed=False
        )
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def due_soon(self, request):
        """Get tasks due soon (next 7 days)"""
        end_date = timezone.now() + timedelta(days=7)
        tasks = self.get_queryset().filter(
            due_date__lte=end_date,
            due_date__gte=timezone.now(),
            completed=False
        )
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)


class SubtaskViewSet(viewsets.ModelViewSet):
    """ViewSet for Subtask model"""
    queryset = Subtask.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['completed', 'priority', 'task']
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at', 'priority', 'progress']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter subtasks based on user permissions"""
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return Subtask.objects.all()
        else:
            return Subtask.objects.filter(
                Q(task__owner=user) | Q(task__assigned_to=user)
            )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return SubtaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SubtaskUpdateSerializer
        elif self.action == 'retrieve':
            return SubtaskDetailSerializer
        return SubtaskSerializer
    
    def perform_create(self, serializer):
        """Set task when creating subtask"""
        task_id = self.request.data.get('task')
        if task_id:
            task = get_object_or_404(Task, id=task_id)
            serializer.save(task=task)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a subtask"""
        subtask = self.get_object()
        subtask.complete_subtask()
        return Response({'message': 'Subtask completed successfully'})
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """Update subtask progress"""
        subtask = self.get_object()
        progress = request.data.get('progress')
        
        if progress is not None and 0 <= progress <= 100:
            subtask.progress = progress
            if progress == 100:
                subtask.completed = True
            subtask.save()
            return Response({'message': 'Progress updated successfully'})
        else:
            return Response(
                {'error': 'Progress must be between 0 and 100'},
                status=status.HTTP_400_BAD_REQUEST
            )


class CommentViewSet(viewsets.ModelViewSet):
    """ViewSet for Comment model"""
    queryset = Comment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task', 'subtask', 'is_internal', 'author']
    search_fields = ['content']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter comments based on user permissions"""
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return Comment.objects.all()
        else:
            # Regular users can see comments on tasks they have access to
            return Comment.objects.filter(
                Q(task__owner=user) | Q(task__assigned_to=user) |
                Q(subtask__task__owner=user) | Q(subtask__task__assigned_to=user)
            )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return CommentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CommentUpdateSerializer
        return CommentSerializer
    
    def perform_create(self, serializer):
        """Set author when creating comment"""
        serializer.save(author=self.request.user)
    
    def perform_update(self, serializer):
        """Only allow author to update comment"""
        comment = self.get_object()
        if comment.author != self.request.user:
            raise permissions.PermissionDenied("You can only edit your own comments")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only allow author or admin to delete comment"""
        if instance.author != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("You can only delete your own comments")
        instance.delete()


class AttachmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Attachment model"""
    queryset = Attachment.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task', 'subtask', 'file_type', 'uploaded_by']
    search_fields = ['original_filename', 'description']
    ordering_fields = ['original_filename', 'created_at', 'file_size']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter attachments based on user permissions"""
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return Attachment.objects.all()
        else:
            # Regular users can see attachments on tasks they have access to
            return Attachment.objects.filter(
                Q(task__owner=user) | Q(task__assigned_to=user) |
                Q(subtask__task__owner=user) | Q(subtask__task__assigned_to=user)
            )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return AttachmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AttachmentUpdateSerializer
        return AttachmentSerializer
    
    def perform_create(self, serializer):
        """Set uploaded_by when creating attachment"""
        serializer.save(uploaded_by=self.request.user)
    
    def perform_update(self, serializer):
        """Only allow uploader to update attachment"""
        attachment = self.get_object()
        if attachment.uploaded_by != self.request.user:
            raise permissions.PermissionDenied("You can only edit your own attachments")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only allow uploader or admin to delete attachment"""
        if instance.uploaded_by != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("You can only delete your own attachments")
        instance.delete()


# Dashboard and Analytics Views
class DashboardViewSet(viewsets.ViewSet):
    """ViewSet for dashboard and analytics"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get user task summary"""
        user = request.user
        
        # Get user's tasks
        user_tasks = Task.objects.filter(
            Q(owner=user) | Q(assigned_to=user)
        )
        
        # Calculate summary
        total_tasks = user_tasks.count()
        completed_tasks = user_tasks.filter(completed=True).count()
        overdue_tasks = user_tasks.filter(
            due_date__lt=timezone.now(),
            completed=False
        ).count()
        
        today = timezone.now().date()
        tasks_due_today = user_tasks.filter(
            due_date__date=today,
            completed=False
        ).count()
        
        end_of_week = today + timedelta(days=7)
        tasks_due_this_week = user_tasks.filter(
            due_date__date__lte=end_of_week,
            due_date__date__gte=today,
            completed=False
        ).count()
        
        # Calculate average progress
        progress_avg = user_tasks.aggregate(avg_progress=Avg('progress'))['avg_progress'] or 0
        
        summary = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'tasks_due_today': tasks_due_today,
            'tasks_due_this_week': tasks_due_this_week,
            'average_progress': round(progress_avg, 1)
        }
        
        serializer = UserTaskSummarySerializer(summary)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent_activity(self, request):
        """Get recent activity"""
        user = request.user
        
        # Get recent comments
        recent_comments = Comment.objects.filter(
            Q(task__owner=user) | Q(task__assigned_to=user) |
            Q(subtask__task__owner=user) | Q(subtask__task__assigned_to=user)
        ).order_by('-created_at')[:10]
        
        # Get recent attachments
        recent_attachments = Attachment.objects.filter(
            Q(task__owner=user) | Q(task__assigned_to=user) |
            Q(subtask__task__owner=user) | Q(subtask__task__assigned_to=user)
        ).order_by('-created_at')[:10]
        
        return Response({
            'recent_comments': CommentSerializer(recent_comments, many=True).data,
            'recent_attachments': AttachmentSerializer(recent_attachments, many=True).data
        })
