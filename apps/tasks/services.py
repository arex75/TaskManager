from django.utils import timezone
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404
from datetime import timedelta
import logging

from .models import Task, Subtask, Comment, Attachment, Tag

logger = logging.getLogger(__name__)


class TaskService:
    """Service for handling task-related business logic"""
    
    @staticmethod
    def get_user_tasks(user, include_public=True):
        """
        Get tasks accessible to a user
        
        Args:
            user: The user requesting tasks
            include_public: Whether to include public tasks
            
        Returns:
            QuerySet of accessible tasks
        """
        if user.is_staff or user.is_superuser:
            return Task.objects.all()
        
        query = Q(owner=user) | Q(assigned_to=user)
        if include_public:
            query |= Q(owner__isnull=False)  # Include public tasks
        
        return Task.objects.filter(query).distinct()
    
    @staticmethod
    def get_overdue_tasks(user):
        """Get overdue tasks for a user"""
        user_tasks = TaskService.get_user_tasks(user)
        return user_tasks.filter(
            due_date__lt=timezone.now(),
            completed=False
        )
    
    @staticmethod
    def get_tasks_due_soon(user, days=7):
        """Get tasks due soon for a user"""
        user_tasks = TaskService.get_user_tasks(user)
        end_date = timezone.now() + timedelta(days=days)
        return user_tasks.filter(
            due_date__lte=end_date,
            due_date__gte=timezone.now(),
            completed=False
        )
    
    @staticmethod
    def get_tasks_due_today(user):
        """Get tasks due today for a user"""
        user_tasks = TaskService.get_user_tasks(user)
        today = timezone.now().date()
        return user_tasks.filter(
            due_date__date=today,
            completed=False
        )
    
    @staticmethod
    def start_task(task, user):
        """Start a task"""
        if task.status == Task.TaskStatus.TODO:
            task.start_task()
            logger.info(f"Task {task.id} started by user {user.id}")
            return True
        return False
    
    @staticmethod
    def complete_task(task, user):
        """Complete a task"""
        if not task.completed:
            task.complete_task()
            logger.info(f"Task {task.id} completed by user {user.id}")
            return True
        return False
    
    @staticmethod
    def cancel_task(task, user):
        """Cancel a task"""
        if task.status != Task.TaskStatus.CANCELLED:
            task.cancel_task(cancelled_by_user=user)
            logger.info(f"Task {task.id} cancelled by user {user.id}")
            return True
        return False
    
    @staticmethod
    def update_task_progress(task, progress, user):
        """Update task progress"""
        if 0 <= progress <= 100:
            task.update_progress(progress)
            logger.info(f"Task {task.id} progress updated to {progress}% by user {user.id}")
            return True
        return False
    
    @staticmethod
    def get_user_task_summary(user):
        """Get comprehensive task summary for a user"""
        user_tasks = TaskService.get_user_tasks(user)
        
        total_tasks = user_tasks.count()
        completed_tasks = user_tasks.filter(completed=True).count()
        overdue_tasks = TaskService.get_overdue_tasks(user).count()
        tasks_due_today = TaskService.get_tasks_due_today(user).count()
        tasks_due_this_week = TaskService.get_tasks_due_soon(user, 7).count()
        
        # Calculate average progress
        progress_avg = user_tasks.aggregate(avg_progress=Avg('progress'))['avg_progress'] or 0
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'tasks_due_today': tasks_due_today,
            'tasks_due_this_week': tasks_due_this_week,
            'average_progress': round(progress_avg, 1)
        }


class SubtaskService:
    """Service for handling subtask-related business logic"""
    
    @staticmethod
    def get_user_subtasks(user):
        """Get subtasks accessible to a user"""
        if user.is_staff or user.is_superuser:
            return Subtask.objects.all()
        
        return Subtask.objects.filter(
            Q(task__owner=user) | Q(task__assigned_to=user)
        )
    
    @staticmethod
    def get_overdue_subtasks(user):
        """Get overdue subtasks for a user"""
        user_subtasks = SubtaskService.get_user_subtasks(user)
        return user_subtasks.filter(
            due_date__lt=timezone.now(),
            completed=False
        )
    
    @staticmethod
    def get_subtasks_due_soon(user, days=7):
        """Get subtasks due soon for a user"""
        user_subtasks = SubtaskService.get_user_subtasks(user)
        end_date = timezone.now() + timedelta(days=days)
        return user_subtasks.filter(
            due_date__lte=end_date,
            due_date__gte=timezone.now(),
            completed=False
        )
    
    @staticmethod
    def complete_subtask(subtask, user):
        """Complete a subtask and update parent task progress"""
        if not subtask.completed:
            subtask.complete_subtask()
            logger.info(f"Subtask {subtask.id} completed by user {user.id}")
            return True
        return False
    
    @staticmethod
    def start_subtask(subtask, user):
        """Start a subtask"""
        if not subtask.started_at:
            subtask.start_subtask()
            logger.info(f"Subtask {subtask.id} started by user {user.id}")
            return True
        return False
    
    @staticmethod
    def update_subtask_progress(subtask, progress, user):
        """Update subtask progress"""
        if 0 <= progress <= 100:
            subtask.progress = progress
            if progress == 100:
                subtask.completed = True
                subtask.completed_at = timezone.now()
            elif progress > 0 and not subtask.started_at:
                subtask.start_subtask()
            subtask.save()
            
            # Update parent task progress
            subtask.task.update_progress(subtask.task.subtask_progress)
            
            logger.info(f"Subtask {subtask.id} progress updated to {progress}% by user {user.id}")
            return True
        return False


class CommentService:
    """Service for handling comment-related business logic"""
    
    @staticmethod
    def get_user_comments(user):
        """Get comments accessible to a user"""
        if user.is_staff or user.is_superuser:
            return Comment.objects.all()
        
        return Comment.objects.filter(
            Q(task__owner=user) | Q(task__assigned_to=user) |
            Q(subtask__task__owner=user) | Q(subtask__task__assigned_to=user)
        )
    
    @staticmethod
    def can_edit_comment(comment, user):
        """Check if user can edit a comment"""
        return comment.author == user or user.is_staff
    
    @staticmethod
    def can_delete_comment(comment, user):
        """Check if user can delete a comment"""
        return comment.author == user or user.is_staff


class AttachmentService:
    """Service for handling attachment-related business logic"""
    
    @staticmethod
    def get_user_attachments(user):
        """Get attachments accessible to a user"""
        if user.is_staff or user.is_superuser:
            return Attachment.objects.all()
        
        return Attachment.objects.filter(
            Q(task__owner=user) | Q(task__assigned_to=user) |
            Q(subtask__task__owner=user) | Q(subtask__task__assigned_to=user)
        )
    
    @staticmethod
    def can_edit_attachment(attachment, user):
        """Check if user can edit an attachment"""
        return attachment.uploaded_by == user or user.is_staff
    
    @staticmethod
    def can_delete_attachment(attachment, user):
        """Check if user can delete an attachment"""
        return attachment.uploaded_by == user or user.is_staff


class DashboardService:
    """Service for handling dashboard and analytics"""
    
    @staticmethod
    def get_recent_activity(user, limit=10):
        """Get recent activity for a user"""
        # Get recent comments
        recent_comments = CommentService.get_user_comments(user).order_by('-created_at')[:limit]
        
        # Get recent attachments
        recent_attachments = AttachmentService.get_user_attachments(user).order_by('-created_at')[:limit]
        
        return {
            'recent_comments': recent_comments,
            'recent_attachments': recent_attachments
        }
    
    @staticmethod
    def get_task_statistics(user):
        """Get task statistics for dashboard"""
        user_tasks = TaskService.get_user_tasks(user)
        
        # Status distribution
        status_stats = user_tasks.values('status').annotate(count=Count('id'))
        
        # Priority distribution
        priority_stats = user_tasks.values('priority').annotate(count=Count('id'))
        
        # Progress distribution
        progress_ranges = [
            (0, 25, '0-25%'),
            (26, 50, '26-50%'),
            (51, 75, '51-75%'),
            (76, 99, '76-99%'),
            (100, 100, '100%')
        ]
        
        progress_stats = []
        for min_progress, max_progress, label in progress_ranges:
            count = user_tasks.filter(progress__gte=min_progress, progress__lte=max_progress).count()
            progress_stats.append({'range': label, 'count': count})
        
        return {
            'status_distribution': status_stats,
            'priority_distribution': priority_stats,
            'progress_distribution': progress_stats
        }


class TagService:
    """Service for handling tag-related business logic"""
    
    @staticmethod
    def get_or_create_tag(name, color='#007bff', description=''):
        """Get existing tag or create new one"""
        tag, created = Tag.objects.get_or_create(
            name__iexact=name,
            defaults={'name': name, 'color': color, 'description': description}
        )
        return tag, created
    
    @staticmethod
    def get_popular_tags(limit=10):
        """Get most used tags"""
        return Tag.objects.annotate(
            task_count=Count('tasks')
        ).order_by('-task_count')[:limit]
    
    @staticmethod
    def validate_tag_data(name, color):
        """Validate tag data"""
        errors = {}
        
        if not name or not name.strip():
            errors['name'] = ['Tag name is required.']
        
        if color and (not color.startswith('#') or len(color) != 7):
            errors['color'] = ['Color must be a valid hex color code (e.g., #007bff).']
        
        return errors
