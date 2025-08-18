from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.config.base_model import BaseModel

class TaskPriority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'

class TaskStatus(models.TextChoices):
    TODO = 'TODO', 'To Do'
    IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
    PAUSED = 'PAUSED', 'Paused'
    REVIEW = 'REVIEW', 'Under Review'
    DONE = 'DONE', 'Done'
    BLOCKED = 'BLOCKED', 'Blocked'
    CANCELLED = 'CANCELLED', 'Cancelled'

class Tag(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#007bff', help_text='Hex color code')
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class Task(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    due_reminder = models.DateTimeField(null=True, blank=True, help_text='When to send reminder notification')
    
    # Task management fields
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_tasks')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    priority = models.CharField(max_length=10, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)
    status = models.CharField(max_length=15, choices=TaskStatus.choices, default=TaskStatus.TODO)
    
    # Organization fields
    tags = models.ManyToManyField(Tag, blank=True, related_name='tasks')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Progress and time tracking
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Progress percentage (0-100)'
    )
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Audit fields
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_tasks')

    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        indexes = [
            models.Index(fields=['completed']),
            models.Index(fields=['due_date']),
            models.Index(fields=['priority']),
            models.Index(fields=['status']),
            models.Index(fields=['owner']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['progress']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def start_task(self):
        """Mark task as started"""
        if self.status == TaskStatus.TODO:
            self.status = TaskStatus.IN_PROGRESS
            self.started_at = timezone.now()
            self.save()

    def complete_task(self):
        """Mark task as completed"""
        if not self.completed:  # Only update if not already completed
            self.status = TaskStatus.DONE
            self.completed = True
            self.progress = 100
            self.completed_at = timezone.now()
            self.save()

    def cancel_task(self, cancelled_by_user):
        """Cancel the task"""
        if self.status != TaskStatus.CANCELLED:  # Only update if not already cancelled
            self.status = TaskStatus.CANCELLED
            self.cancelled_at = timezone.now()
            self.cancelled_by = cancelled_by_user
            self.save()

    def update_progress(self, new_progress):
        """Update task progress"""
        if 0 <= new_progress <= 100:
            self.progress = new_progress
            if new_progress == 100:
                self.status = TaskStatus.REVIEW
            elif new_progress > 0:
                self.status = TaskStatus.IN_PROGRESS
            self.save()

    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and not self.completed:
            return timezone.now() > self.due_date
        return False

    @property
    def has_subtasks(self):
        """Check if task has subtasks"""
        return self.subtasks.exists()

    @property
    def subtask_progress(self):
        """Calculate progress based on subtasks"""
        if not self.has_subtasks:
            return self.progress
        
        subtasks = self.subtasks.all()
        if not subtasks:
            return 0
        
        total_subtasks = len(subtasks)
        completed_subtasks = sum(1 for subtask in subtasks if subtask.completed)
        return int((completed_subtasks / total_subtasks) * 100)

class Subtask(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    title = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(max_length=1000, blank=True, null=True)
    completed = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)
    status = models.CharField(max_length=15, choices=TaskStatus.choices, default=TaskStatus.TODO)
    progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True, help_text='Due date for this subtask')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Subtask'
        verbose_name_plural = 'Subtasks'
        indexes = [
            models.Index(fields=['completed']),
            models.Index(fields=['priority']),
            models.Index(fields=['progress']),
            models.Index(fields=['due_date']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} (Subtask of {self.task.title})"

    def complete_subtask(self):
        """Mark subtask as completed"""
        self.completed = True
        self.progress = 100
        self.status = TaskStatus.DONE
        self.completed_at = timezone.now()
        self.save()
        # Update parent task progress
        self.task.update_progress(self.task.subtask_progress)

    def start_subtask(self):
        """Mark subtask as started"""
        if not self.started_at:
            self.status = TaskStatus.IN_PROGRESS
            self.started_at = timezone.now()
            self.save()

    @property
    def is_overdue(self):
        """Check if subtask is overdue"""
        if self.due_date and not self.completed:
            return timezone.now() > self.due_date
        return False

class Comment(BaseModel):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='comments')
    subtask = models.ForeignKey(Subtask, on_delete=models.CASCADE, null=True, blank=True, related_name='comments')
    content = models.TextField(max_length=2000)
    is_internal = models.BooleanField(default=False, help_text='Internal comment visible only to team members', null=True)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'
        indexes = [
            models.Index(fields=['author']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_internal']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        if self.task:
            target = self.task.title
        elif self.subtask:
            target = self.subtask.title
        else:
            target = "None"
        return f"Comment by {self.author.username} on {target}"

    def save(self, *args, **kwargs):
        if self.pk:  # If this is an update
            self.is_edited = True
            self.edited_at = timezone.now()
        super().save(*args, **kwargs)

class Attachment(BaseModel):
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attachments')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    subtask = models.ForeignKey(Subtask, on_delete=models.CASCADE, null=True, blank=True, related_name='attachments')
    file = models.FileField(upload_to='attachments/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text='File size in bytes')
    file_type = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=True, help_text='Whether this attachment is publicly visible')

    class Meta:
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'
        indexes = [
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['file_type']),
            models.Index(fields=['is_public']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        if self.task:
            target = self.task.title
        elif self.subtask:
            target = self.subtask.title
        else:
            target = "None"
        return f"{self.original_filename} on {target}"

    def save(self, *args, **kwargs):
        if not self.original_filename and self.file:
            self.original_filename = self.file.name.split('/')[-1]
        if not self.file_size and self.file:
            self.file_size = self.file.size
        if not self.file_type and self.file:
            self.file_type = self.file.name.split('.')[-1].upper()
        super().save(*args, **kwargs)
