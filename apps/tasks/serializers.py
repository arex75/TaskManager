import os
from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Tag, Task, Subtask, Comment, Attachment, TaskStatus, TaskPriority
from .utils import validate_hex_color
from apps.users.serializers import UserProfileSerializer


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model"""
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """Validate tag name uniqueness"""
        if Tag.objects.filter(name__iexact=value).exists():
            raise ValidationError("A tag with this name already exists.")
        return value
    
    def validate_color(self, value):
        """Validate hex color format"""
        if not validate_hex_color(value):
            raise ValidationError("Color must be a valid hex color code (e.g., #007bff)")
        return value


class TagCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tags"""
    
    class Meta:
        model = Tag
        fields = ['name', 'color', 'description']
    
    def validate_name(self, value):
        """Validate tag name uniqueness"""
        if Tag.objects.filter(name__iexact=value).exists():
            raise ValidationError("A tag with this name already exists.")
        return value
    
    def validate_color(self, value):
        """Validate hex color format"""
        if not validate_hex_color(value):
            raise ValidationError("Color must be a valid hex color code (e.g., #007bff)")
        return value


class TagUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tags"""
    
    class Meta:
        model = Tag
        fields = ['name', 'color', 'description']
    
    def validate_name(self, value):
        """Validate tag name uniqueness (excluding current instance)"""
        instance = self.instance
        if instance and Tag.objects.filter(name__iexact=value).exclude(pk=instance.pk).exists():
            raise ValidationError("A tag with this name already exists.")
        elif not instance and Tag.objects.filter(name__iexact=value).exists():
            raise ValidationError("A tag with this name already exists.")
        return value
    
    def validate_color(self, value):
        """Validate hex color format"""
        if not validate_hex_color(value):
            raise ValidationError("Color must be a valid hex color code (e.g., #007bff)")
        return value


class SubtaskSerializer(serializers.ModelSerializer):
    """Serializer for Subtask model"""
    
    class Meta:
        model = Subtask
        fields = ['id', 'title', 'description', 'completed', 'priority', 'status', 'progress', 
                 'estimated_hours', 'actual_hours', 'due_date', 'started_at', 'completed_at',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'started_at', 'completed_at', 'created_at', 'updated_at']


class SubtaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating subtasks"""
    
    class Meta:
        model = Subtask
        fields = ['title', 'description', 'priority', 'status', 'progress', 'estimated_hours', 'due_date']
    
    def validate_title(self, value):
        """Validate subtask title"""
        if not value.strip():
            raise ValidationError("Subtask title cannot be empty.")
        return value.strip()
    
    def validate_priority(self, value):
        """Validate priority value"""
        valid_priorities = [choice[0] for choice in TaskPriority.choices]
        if value not in valid_priorities:
            raise ValidationError(f"'{value}' is not a valid priority. Valid choices are: {valid_priorities}")
        return value
    
    def validate_estimated_hours(self, value):
        """Validate estimated hours"""
        if value is not None and value < 0:
            raise ValidationError("Estimated hours cannot be negative.")
        return value
    
    def validate_progress(self, value):
        """Validate progress value"""
        if value < 0 or value > 100:
            raise ValidationError("Progress must be between 0 and 100.")
        return value
    
    def validate_status(self, value):
        """Validate status value"""
        valid_statuses = [choice[0] for choice in TaskStatus.choices]
        if value not in valid_statuses:
            raise ValidationError(f"'{value}' is not a valid status. Valid choices are: {valid_statuses}")
        return value


class SubtaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating subtasks"""
    
    class Meta:
        model = Subtask
        fields = ['title', 'description', 'completed', 'priority', 'status', 'progress', 
                 'estimated_hours', 'actual_hours', 'due_date']
    
    def validate_title(self, value):
        """Validate subtask title"""
        if not value.strip():
            raise ValidationError("Subtask title cannot be empty.")
        return value.strip()
    
    def validate_priority(self, value):
        """Validate priority value"""
        valid_priorities = [choice[0] for choice in TaskPriority.choices]
        if value not in valid_priorities:
            raise ValidationError(f"'{value}' is not a valid priority. Valid choices are: {valid_priorities}")
        return value
    
    def validate_estimated_hours(self, value):
        """Validate estimated hours"""
        if value is not None and value < 0:
            raise ValidationError("Estimated hours cannot be negative.")
        return value
    
    def validate_progress(self, value):
        """Validate progress value"""
        if value < 0 or value > 100:
            raise ValidationError("Progress cannot be negative or greater than 100.")
        return value
    
    def validate_status(self, value):
        """Validate status value and transitions"""
        valid_statuses = [choice[0] for choice in TaskStatus.choices]
        if value not in valid_statuses:
            raise ValidationError(f"'{value}' is not a valid status. Valid choices are: {valid_statuses}")
        
        # Get the current instance to check current status
        instance = getattr(self, 'instance', None)
        if instance and hasattr(instance, 'status'):
            current_status = instance.status
            
            # Prevent invalid transitions to IN_PROGRESS
            if value == 'IN_PROGRESS' and current_status != 'PAUSED':
                raise ValidationError("Cannot transition to IN_PROGRESS directly. Use the start action instead.")
        
        return value


class SubtaskDetailSerializer(SubtaskSerializer):
    """Detailed serializer for subtasks"""
    task = serializers.SerializerMethodField()
    
    class Meta(SubtaskSerializer.Meta):
        fields = SubtaskSerializer.Meta.fields + ['task']
    
    def get_task(self, obj):
        """Serialize task as an object with id and title"""
        if obj.task:
            return {
                'id': obj.task.id,
                'title': obj.task.title
            }
        return None


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Comment model"""
    author = UserProfileSerializer(read_only=True)
    task = serializers.SerializerMethodField()
    subtask = serializers.SerializerMethodField()
    parent_comment = serializers.SerializerMethodField()
    edited = serializers.BooleanField(source='is_edited', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'content', 'is_internal', 'author', 'task', 'subtask', 'parent_comment', 
                 'is_edited', 'edited_at', 'edited', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'is_edited', 'edited_at', 'edited', 'created_at', 'updated_at']
    
    def get_task(self, obj):
        if obj.task:
            return { 'id': obj.task.id }
        return None
    
    def get_subtask(self, obj):
        if obj.subtask:
            return { 'id': obj.subtask.id }
        return None
    
    def get_parent_comment(self, obj):
        """Return parent comment data if it exists"""
        if obj.parent_comment:
            return {
                'id': obj.parent_comment.id,
                'content': obj.parent_comment.content[:50] + '...' if len(obj.parent_comment.content) > 50 else obj.parent_comment.content
            }
        return None


class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments"""
    
    class Meta:
        model = Comment
        fields = ['content', 'is_internal', 'task', 'subtask', 'parent_comment']
    
    def validate(self, data):
        """Validate that either task or subtask is provided, but not both"""
        task = data.get('task')
        subtask = data.get('subtask')
        
        if not task and not subtask:
            raise ValidationError("Either task or subtask must be specified.")
        
        if task and subtask:
            raise ValidationError("Cannot specify both task and subtask.")
        
        # Validate task ownership/assignment
        if task:
            user = self.context['request'].user
            if not (task.owner == user or task.assigned_to == user or user.is_staff):
                raise ValidationError("You can only create comments on tasks you own or are assigned to.")
        
        # Validate subtask ownership/assignment
        if subtask:
            user = self.context['request'].user
            if not (subtask.task.owner == user or subtask.task.assigned_to == user or user.is_staff):
                raise ValidationError("You can only create comments on subtasks from tasks you own or are assigned to.")
        
        return data


class CommentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating comments"""
    
    class Meta:
        model = Comment
        fields = ['content', 'is_internal']


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer for Attachment model"""
    uploaded_by = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = Attachment
        fields = ['id', 'file', 'original_filename', 'file_size', 'file_type', 
                 'description', 'is_public', 'uploaded_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'file_size', 'file_type', 'uploaded_by', 'created_at', 'updated_at']


class AttachmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating attachments"""
    
    class Meta:
        model = Attachment
        fields = ['file', 'description', 'is_public', 'task', 'subtask']
    
    def validate(self, data):
        """Validate that either task or subtask is provided, but not both"""
        task = data.get('task')
        subtask = data.get('subtask')
        
        if not task and not subtask:
            raise ValidationError("Either task or subtask must be specified.")
        
        if task and subtask:
            raise ValidationError("Cannot specify both task and subtask.")
        
        return data
    
    def validate_file(self, value):
        """Validate file size and type"""
        if value:
            # Check file size (10MB limit)
            if value.size > 10 * 1024 * 1024:  # 10MB
                raise ValidationError("File size cannot exceed 10MB.")
            
            # Check file extension
            allowed_extensions = ['.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.gif']
            file_extension = os.path.splitext(value.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError(f"File type '{file_extension}' is not allowed. Allowed types: {', '.join(allowed_extensions)}")
        
        return value
    
    def validate_description(self, value):
        """Validate description length"""
        if value and len(value) > 1000:
            raise ValidationError("Description cannot exceed 1000 characters.")
        return value


class AttachmentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating attachments"""
    
    class Meta:
        model = Attachment
        fields = ['description', 'is_public']
    
    def validate_description(self, value):
        """Validate description length"""
        if value and len(value) > 1000:
            raise ValidationError("Description cannot exceed 1000 characters.")
        return value


class TaskSerializer(serializers.ModelSerializer):
    """Basic serializer for Task model"""
    owner = UserProfileSerializer(read_only=True)
    assigned_to = UserProfileSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'completed', 'due_date', 'due_reminder',
                 'owner', 'assigned_to', 'priority', 'status', 'tags', 'progress',
                 'estimated_hours', 'actual_hours', 'started_at', 'completed_at',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'owner', 'started_at', 'completed_at', 'created_at', 'updated_at']


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tasks"""
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)
    
    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'due_reminder', 'assigned_to', 
                 'priority', 'status', 'tags', 'progress', 'estimated_hours']
    
    def validate_title(self, value):
        """Validate task title"""
        if not value.strip():
            raise ValidationError("Task title cannot be empty.")
        if len(value) > 255:
            raise ValidationError("Task title cannot exceed 255 characters.")
        return value.strip()
    
    def validate_description(self, value):
        """Validate task description"""
        if value and len(value) > 1000:
            raise ValidationError("Task description cannot exceed 1000 characters.")
        return value
    
    def validate_due_date(self, value):
        """Validate due date is not in the past"""
        if value and value < timezone.now():
            raise ValidationError("Due date cannot be in the past.")
        return value
    
    def validate_due_reminder(self, value):
        """Validate reminder is not after due date"""
        due_date = self.initial_data.get('due_date')
        if value and due_date and value > due_date:
            raise ValidationError("Reminder cannot be set after the due date.")
        return value
    
    def validate_progress(self, value):
        """Validate progress is between 0 and 100"""
        if value is not None and (value < 0 or value > 100):
            raise ValidationError("Progress must be between 0 and 100.")
        return value
    
    def validate_status(self, value):
        """Validate status is a valid choice"""
        valid_statuses = [choice[0] for choice in TaskStatus.choices]
        if value not in valid_statuses:
            raise ValidationError(f"'{value}' is not a valid status choice.")
        return value
    
    def validate_estimated_hours(self, value):
        """Validate estimated hours is positive"""
        if value is not None and value <= 0:
            raise ValidationError("Estimated hours must be positive.")
        return value


class TaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating tasks"""
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)
    
    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'due_reminder', 'assigned_to', 
                 'priority', 'status', 'tags', 'progress', 'estimated_hours', 'actual_hours']
    
    def validate_due_date(self, value):
        """Validate due date is not in the past"""
        if value and value < timezone.now():
            raise ValidationError("Due date cannot be in the past.")
        return value
    
    def validate_due_reminder(self, value):
        """Validate reminder is not after due date"""
        due_date = self.initial_data.get('due_date')
        if value and due_date and value > due_date:
            raise ValidationError("Reminder cannot be set after the due date.")
        return value
    
    def validate_status(self, value):
        """Validate status transitions"""
        # Get the current task instance
        task = self.instance
        if task:
            current_status = task.status
            # Prevent direct status changes that should use actions
            if current_status == 'TODO' and value == 'IN_PROGRESS':
                raise ValidationError("Task status cannot be changed from TODO to IN_PROGRESS. Use the start action instead.")
            if current_status == 'IN_PROGRESS' and value == 'PAUSED':
                raise ValidationError("Task status cannot be changed from IN_PROGRESS to PAUSED. Use the pause action instead.")
            if current_status == 'PAUSED' and value == 'IN_PROGRESS':
                raise ValidationError("Task status cannot be changed from PAUSED to IN_PROGRESS. Use the resume action instead.")
            # Allow IN_PROGRESS → DONE transition
            if current_status == 'IN_PROGRESS' and value == 'DONE':
                return value
        return value


class TaskDetailSerializer(TaskSerializer):
    """Detailed serializer for tasks with nested data"""
    subtasks = SubtaskSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    
    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ['subtasks', 'comments', 'attachments']


class TaskDashboardSerializer(serializers.ModelSerializer):
    """Serializer for dashboard view of tasks"""
    owner = UserProfileSerializer(read_only=True)
    assigned_to = UserProfileSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = Task
        fields = ['id', 'title', 'priority', 'status', 'progress', 'due_date', 
                 'owner', 'assigned_to', 'tags', 'is_overdue', 'has_subtasks']


class UserTaskSummarySerializer(serializers.Serializer):
    """Serializer for user task summary"""
    total_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    tasks_due_today = serializers.IntegerField()
    tasks_due_this_week = serializers.IntegerField()
    average_progress = serializers.FloatField()
