from django.utils import timezone
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from datetime import timedelta
import logging

from .models import Task, Subtask, Comment, Attachment, Tag, TaskStatus, TaskPriority

logger = logging.getLogger(__name__)


class TaskService:
    """Service for handling task-related business logic"""
    
    @staticmethod
    def get_user_tasks(user, include_public=True, **kwargs):
        """
        Get tasks accessible to a user
        
        Args:
            user: The user requesting tasks
            include_public: Whether to include public tasks
            **kwargs: Additional filter parameters
            
        Returns:
            QuerySet of accessible tasks
        """
        logger.debug(f"get_user_tasks called with user={user}, include_public={include_public}, kwargs={kwargs}")
        
        if user is None:
            logger.error("get_user_tasks called with None user")
            raise ValueError("User cannot be None")
        
        if user.is_staff or user.is_superuser:
            logger.debug("User is staff/superuser, returning all tasks")
            queryset = Task.objects.all()
        else:
            logger.debug("User is regular user, filtering by ownership/assignment")
            query = Q(owner=user) | Q(assigned_to=user)
            if include_public:
                # Only include tasks that are explicitly marked as public
                # For now, we'll assume all tasks are private unless marked otherwise
                # This can be enhanced later with a public field in the Task model
                pass
            
            queryset = Task.objects.filter(query).distinct()
        
        # Apply additional filters from kwargs
        if kwargs:
            logger.debug(f"Applying additional filters: {kwargs}")
            # Handle special parameters
            page = kwargs.pop('page', None)
            page_size = kwargs.pop('page_size', None)
            ordering = kwargs.pop('ordering', None)
            search = kwargs.pop('search', None)
            include_comments = kwargs.pop('include_comments', False)
            include_subtasks = kwargs.pop('include_subtasks', False)
            include_attachments = kwargs.pop('include_attachments', False)
            tags = kwargs.pop('tags', None)
            
            # Apply field filters
            for key, value in kwargs.items():
                if hasattr(Task, key.split('__')[0]):  # Check if field exists
                    logger.debug(f"Applying filter {key}={value}")
                    
                    # Validate enum fields
                    if key == 'status' and hasattr(TaskStatus, 'choices'):
                        valid_statuses = [choice[0] for choice in TaskStatus.choices]
                        if value not in valid_statuses:
                            raise ValidationError(f"'{value}' is not a valid status. Valid choices are: {valid_statuses}")
                    
                    elif key == 'priority' and hasattr(TaskPriority, 'choices'):
                        valid_priorities = [choice[0] for choice in TaskPriority.choices]
                        if value not in valid_priorities:
                            raise ValidationError(f"'{value}' is not a valid priority. Valid choices are: {valid_priorities}")
                    
                    queryset = queryset.filter(**{key: value})
                else:
                    logger.warning(f"Unknown filter field: {key}")
            
            # Apply tags filter
            if tags:
                logger.debug(f"Applying tags filter: {tags}")
                if isinstance(tags, list):
                    # Filter by multiple tags - task must have ALL specified tags
                    for tag in tags:
                        queryset = queryset.filter(tags=tag)
                else:
                    queryset = queryset.filter(tags=tags)
            
            # Apply search
            if search:
                logger.debug(f"Applying search filter: {search}")
                queryset = queryset.filter(
                    Q(title__icontains=search) | 
                    Q(description__icontains=search)
                )
            
            # Apply ordering
            if ordering:
                logger.debug(f"Applying ordering: {ordering}")
                # Clear default ordering and apply custom ordering
                queryset = queryset.order_by().order_by(ordering)
            
            # Apply pagination
            if page_size:
                logger.debug(f"Applying pagination: page_size={page_size}")
                if page:
                    logger.debug(f"Applying pagination: page={page}")
                    start = (page - 1) * page_size
                    end = start + page_size
                    queryset = queryset[start:end]
                else:
                    queryset = queryset[:page_size]
            
            # Apply select_related for performance
            if include_comments or include_subtasks or include_attachments:
                logger.debug("Applying select_related for related data")
                queryset = queryset.select_related('owner', 'assigned_to')
        
        logger.debug(f"Final queryset count: {queryset.count()}")
        return queryset
    
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
        if task.status == TaskStatus.TODO:
            task.start_task()
            logger.info(f"Task {task.id} started by user {user.id}")
            return True
        return False
    
    @staticmethod
    def complete_task(task, user):
        """Complete a task"""
        if not task.completed and task.started_at is not None:
            task.complete_task()
            logger.info(f"Task {task.id} completed by user {user.id}")
            return True
        return False
    
    @staticmethod
    def cancel_task(task, user):
        """Cancel a task"""
        if task.status != TaskStatus.CANCELLED:
            task.cancel_task(cancelled_by_user=user)
            logger.info(f"Task {task.id} cancelled by user {user.id}")
            return True
        return False
    
    @staticmethod
    def update_task_progress(task, progress, user):
        """Update task progress"""
        # Convert progress to integer if it's a string
        try:
            progress = int(progress)
        except (ValueError, TypeError):
            return False
        
        if 0 <= progress <= 100:
            task.update_progress(progress)
            logger.info(f"Task {task.id} progress updated to {progress}% by user {user.id}")
            return True
        return False
    
    @staticmethod
    def pause_task(task, user):
        """Pause a task"""
        if task.status == TaskStatus.IN_PROGRESS:
            task.status = TaskStatus.PAUSED
            task.save()
            logger.info(f"Task {task.id} paused by user {user.id}")
            return True
        return False
    
    @staticmethod
    def resume_task(task, user):
        """Resume a task"""
        if task.status == TaskStatus.PAUSED:
            task.status = TaskStatus.IN_PROGRESS
            task.save()
            logger.info(f"Task {task.id} resumed by user {user.id}")
            return True
        return False
    
    @staticmethod
    def assign_task(task, assignee_id, user):
        """Assign a task to a user"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            assignee = User.objects.get(id=assignee_id)
            task.assigned_to = assignee
            task.save()
            logger.info(f"Task {task.id} assigned to user {assignee_id} by user {user.id}")
            return True
        except User.DoesNotExist:
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
