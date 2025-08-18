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
        
        # Always filter by ownership/assignment for security
        # Staff/superuser status doesn't give access to other users' personal data
        logger.debug("Filtering by ownership/assignment")
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
        if subtask.completed:
            return False
        
        if not subtask.started_at:
            return False
        
        subtask.complete_subtask()
        logger.info(f"Subtask {subtask.id} completed by user {user.id}")
        return True
    
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
    
    @staticmethod
    def pause_subtask(subtask, user):
        """Pause a subtask"""
        if subtask.status == 'IN_PROGRESS' and subtask.started_at:
            subtask.status = 'PAUSED'
            subtask.paused_at = timezone.now()
            subtask.save()
            logger.info(f"Subtask {subtask.id} paused by user {user.id}")
            return True
        return False
    
    @staticmethod
    def resume_subtask(subtask, user):
        """Resume a subtask"""
        if subtask.status == 'PAUSED':
            subtask.status = 'IN_PROGRESS'
            subtask.paused_at = None
            subtask.save()
            logger.info(f"Subtask {subtask.id} resumed by user {user.id}")
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
    
    @staticmethod
    def get_comments_by_task(task_id, user):
        """Get comments for a specific task"""
        return CommentService.get_user_comments(user).filter(task_id=task_id)
    
    @staticmethod
    def get_comments_by_subtask(subtask_id, user):
        """Get comments for a specific subtask"""
        return CommentService.get_user_comments(user).filter(subtask_id=subtask_id)


class AttachmentService:
    """Service for handling attachment-related business logic"""
    
    @staticmethod
    def get_user_attachments(user):
        """Get attachments accessible to a user"""
        if user.is_staff or user.is_superuser:
            return Attachment.objects.all()
        
        return Attachment.objects.filter(
            Q(task__owner=user) | Q(task__assigned_to=user) |
            Q(subtask__task__owner=user) | Q(subtask__task__assigned_to=user) |
            Q(is_public=True)  # Include public attachments
        )
    
    @staticmethod
    def can_edit_attachment(attachment, user):
        """Check if user can edit an attachment"""
        if user is None:
            return False
        return attachment.uploaded_by == user or user.is_staff
    
    @staticmethod
    def can_delete_attachment(attachment, user):
        """Check if user can delete an attachment"""
        if user is None:
            return False
        return attachment.uploaded_by == user or user.is_staff
    
    @staticmethod
    def can_download_attachment(attachment, user):
        """Check if user can download an attachment"""
        # Public attachments can be downloaded by anyone
        if attachment.is_public:
            return True
        
        # None users cannot download private attachments
        if user is None:
            return False
        
        # Private attachments can only be downloaded by:
        # - The uploader
        # - Task owner/assigned user
        # - Staff users
        if attachment.uploaded_by == user or user.is_staff:
            return True
        
        if attachment.task:
            return attachment.task.owner == user or attachment.task.assigned_to == user
        
        if attachment.subtask:
            return attachment.subtask.task.owner == user or attachment.subtask.task.assigned_to == user
        
        return False


class DashboardService:
    """Service for handling dashboard and analytics"""
    
    @staticmethod
    def get_dashboard_overview(user):
        """Get comprehensive dashboard overview for a user"""
        # Get user's tasks
        user_tasks = TaskService.get_user_tasks(user)
        
        # Get user's tags
        user_tags = Tag.objects.filter(tasks__owner=user).distinct()
        
        # Get user's subtasks
        user_subtasks = Subtask.objects.filter(task__owner=user)
        
        # Get user's comments
        user_comments = CommentService.get_user_comments(user)
        
        # Get user's attachments
        user_attachments = AttachmentService.get_user_attachments(user)
        
        return {
            'tasks': list(user_tasks.values()),
            'tags': list(user_tags.values()),
            'subtasks': list(user_subtasks.values()),
            'comments': list(user_comments.values()),
            'attachments': list(user_attachments.values())
        }
    
    @staticmethod
    def get_dashboard_summary(user, **kwargs):
        """Get dashboard summary with optional filters"""
        if user is None:
            raise ValueError("User cannot be None")
        
        # Get user's tasks
        user_tasks = TaskService.get_user_tasks(user)
        
        # Apply filters if provided
        if 'created_after' in kwargs:
            try:
                # Validate that created_after is a valid datetime
                if isinstance(kwargs['created_after'], str):
                    # Try to parse the date string
                    from django.utils.dateparse import parse_datetime
                    parsed_date = parse_datetime(kwargs['created_after'])
                    if parsed_date:
                        user_tasks = user_tasks.filter(created_at__gte=parsed_date)
                    else:
                        raise ValueError("Invalid date format")
                else:
                    user_tasks = user_tasks.filter(created_at__gte=kwargs['created_after'])
            except (ValueError, TypeError):
                # If date parsing fails, raise ValueError as expected by tests
                raise ValueError("Invalid date format")
        
        if 'task_status' in kwargs:
            # Validate status before filtering
            valid_statuses = ['TODO', 'IN_PROGRESS', 'COMPLETED', 'PAUSED', 'CANCELLED']
            if kwargs['task_status'] not in valid_statuses:
                from django.core.exceptions import ValidationError
                raise ValidationError(f"Invalid status: {kwargs['task_status']}")
            user_tasks = user_tasks.filter(status=kwargs['task_status'])
        elif 'status' in kwargs:
            # Validate status before filtering
            valid_statuses = ['TODO', 'IN_PROGRESS', 'COMPLETED', 'PAUSED', 'CANCELLED']
            if kwargs['status'] not in valid_statuses:
                from django.core.exceptions import ValidationError
                raise ValidationError(f"Invalid status: {kwargs['status']}")
            user_tasks = user_tasks.filter(status=kwargs['status'])
        
        if 'task_priority' in kwargs:
            user_tasks = user_tasks.filter(priority=kwargs['task_priority'])
        elif 'priority' in kwargs:
            user_tasks = user_tasks.filter(priority=kwargs['priority'])
        
        # Calculate summary statistics
        total_tasks = user_tasks.count()
        completed_tasks = user_tasks.filter(status='COMPLETED').count()
        in_progress_tasks = user_tasks.filter(status='IN_PROGRESS').count()
        todo_tasks = user_tasks.filter(status='TODO').count()
        
        # Calculate completion rate
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Get recent activity
        recent_comments = CommentService.get_user_comments(user).order_by('-created_at')[:5]
        recent_attachments = AttachmentService.get_user_attachments(user).order_by('-created_at')[:5]
        
        # Get user's tags and subtasks for overview
        user_tags = Tag.objects.filter(tasks__owner=user).distinct()
        user_subtasks = Subtask.objects.filter(task__owner=user)
        user_comments = CommentService.get_user_comments(user)
        user_attachments = AttachmentService.get_user_attachments(user)
        
        # Return structure expected by tests
        return {
            'overview': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'in_progress_tasks': in_progress_tasks,
                'todo_tasks': todo_tasks,
                'completion_rate': round(completion_rate, 2),
                'recent_comments_count': len(recent_comments),
                'recent_attachments_count': len(recent_attachments),
                'last_updated': timezone.now(),
                'tasks': list(user_tasks.values()[:10]),  # Include recent tasks
                'tags': list(user_tags.values()),
                'subtasks': list(user_subtasks.values()),
                'comments': list(user_comments.values()[:10]),
                'attachments': list(user_attachments.values()[:10])
            },
            'statistics': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'in_progress_tasks': in_progress_tasks,
                'todo_tasks': todo_tasks,
                'completion_rate': round(completion_rate, 2),
                'total_tags': user_tags.count(),
                'total_subtasks': user_subtasks.count(),
                'total_comments': user_comments.count(),
                'total_attachments': user_attachments.count()
            },
            'performance_metrics': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'completion_rate': round(completion_rate, 2)
            },
            'recent_activity': DashboardService.get_recent_activity(user, limit=5)
        }
    
    @staticmethod
    def get_performance_metrics(user, **kwargs):
        """Get performance metrics for a user"""
        if user is None:
            raise ValueError("User cannot be None")
        
        user_tasks = TaskService.get_user_tasks(user)
        
        # Apply date range filter if provided
        if 'created_after' in kwargs:
            user_tasks = user_tasks.filter(created_at__gte=kwargs['created_after'])
        
        if 'created_before' in kwargs:
            user_tasks = user_tasks.filter(created_at__lte=kwargs['created_before'])
        
        # Calculate performance metrics
        total_tasks = user_tasks.count()
        completed_tasks = user_tasks.filter(status='COMPLETED')
        
        # Average completion time for completed tasks
        avg_completion_time = None
        if completed_tasks.exists():
            completion_times = []
            for task in completed_tasks:
                if task.started_at and task.completed_at:
                    completion_times.append((task.completed_at - task.started_at).total_seconds() / 3600)  # hours
            
            if completion_times:
                avg_completion_time = sum(completion_times) / len(completion_times)
        
        # Tasks completed this week
        week_ago = timezone.now() - timedelta(days=7)
        tasks_this_week = completed_tasks.filter(completed_at__gte=week_ago).count()
        
        # Tasks completed this month
        month_ago = timezone.now() - timedelta(days=30)
        tasks_this_month = completed_tasks.filter(completed_at__gte=month_ago).count()
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks.count(),
            'completion_rate': (completed_tasks.count() / total_tasks * 100) if total_tasks > 0 else 0,
            'average_completion_time': avg_completion_time if avg_completion_time else 0.0,
            'avg_completion_time_hours': round(avg_completion_time, 2) if avg_completion_time else None,
            'tasks_completed_this_week': tasks_this_week,
            'tasks_completed_this_month': tasks_this_month,
            'productivity_score': min(100, (tasks_this_week * 20) + (tasks_this_month * 5)),  # Simple scoring
            'efficiency_score': min(100, (tasks_this_week * 15) + (tasks_this_month * 3))  # Efficiency scoring
        }
    
    @staticmethod
    def get_recent_activity(user, limit=10):
        """Get recent activity for a user"""
        # Get recent comments
        recent_comments = CommentService.get_user_comments(user).order_by('-created_at')[:limit]
        
        # Get recent attachments
        recent_attachments = AttachmentService.get_user_attachments(user).order_by('-created_at')[:limit]
        
        # Get recent task updates
        recent_tasks = TaskService.get_user_tasks(user).order_by('-updated_at')[:limit]
        
        # Combine and format activity items
        activity_items = []
        
        for comment in recent_comments:
            activity_items.append({
                'type': 'comment_added',
                'id': comment.id,
                'content': comment.content[:50] + '...' if len(comment.content) > 50 else comment.content,
                'description': comment.content[:100] + '...' if len(comment.content) > 100 else comment.content,
                'created_at': comment.created_at,
                'timestamp': comment.created_at,
                'task_title': comment.task.title if comment.task else None
            })
        
        for attachment in recent_attachments:
            activity_items.append({
                'type': 'attachment_uploaded',
                'id': attachment.id,
                'filename': attachment.original_filename,
                'description': attachment.description or 'No description',
                'created_at': attachment.created_at,
                'timestamp': attachment.created_at,
                'task_title': attachment.task.title if attachment.task else None
            })
        
        for task in recent_tasks:
            activity_items.append({
                'type': 'task_update',
                'id': task.id,
                'title': task.title,
                'description': task.description[:100] + '...' if len(task.description) > 100 else task.description,
                'updated_at': task.updated_at,
                'timestamp': task.updated_at,
                'status': task.status
            })
        
        # Add task creation events
        for task in recent_tasks:
            activity_items.append({
                'type': 'task_created',
                'id': task.id,
                'title': task.title,
                'description': task.description[:100] + '...' if len(task.description) > 100 else task.description,
                'created_at': task.created_at,
                'timestamp': task.created_at,
                'status': task.status
            })
        
        # Sort by creation/update time and return limited results
        activity_items.sort(key=lambda x: x['timestamp'], reverse=True)
        return activity_items[:limit]
    
    @staticmethod
    def get_task_statistics(user, **kwargs):
        """Get task statistics for dashboard with optional filters"""
        user_tasks = TaskService.get_user_tasks(user)
        
        # Apply filters if provided
        if 'created_after' in kwargs:
            user_tasks = user_tasks.filter(created_at__gte=kwargs['created_after'])
        
        if 'task_status' in kwargs:
            # Validate status before filtering
            valid_statuses = ['TODO', 'IN_PROGRESS', 'COMPLETED', 'PAUSED', 'CANCELLED']
            if kwargs['task_status'] not in valid_statuses:
                from django.core.exceptions import ValidationError
                raise ValidationError(f"Invalid status: {kwargs['task_status']}")
            user_tasks = user_tasks.filter(status=kwargs['task_status'])
        elif 'status' in kwargs:
            # Validate status before filtering
            valid_statuses = ['TODO', 'IN_PROGRESS', 'COMPLETED', 'PAUSED', 'CANCELLED']
            if kwargs['status'] not in valid_statuses:
                from django.core.exceptions import ValidationError
                raise ValidationError(f"Invalid status: {kwargs['status']}")
            user_tasks = user_tasks.filter(status=kwargs['status'])
        
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
        
        # Add total tasks count
        total_tasks = user_tasks.count()
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': user_tasks.filter(status='COMPLETED').count(),
            'in_progress_tasks': user_tasks.filter(status='IN_PROGRESS').count(),
            'todo_tasks': user_tasks.filter(status='TODO').count(),
            'overdue_tasks': user_tasks.filter(due_date__lt=timezone.now(), status__in=['TODO', 'IN_PROGRESS']).count(),
            'status_distribution': list(status_stats),
            'priority_distribution': list(priority_stats),
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
