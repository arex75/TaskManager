from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Tag, Task, Subtask, Comment, Attachment
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


class SubtaskSerializer(serializers.ModelSerializer):
    """Serializer for Subtask model"""
    
    class Meta:
        model = Subtask
        fields = ['id', 'title', 'description', 'completed', 'priority', 'progress', 
                 'estimated_hours', 'actual_hours', 'due_date', 'started_at', 'completed_at',
                 'created_at', 'updated_at']
        read_only_fields = ['id', 'started_at', 'completed_at', 'created_at', 'updated_at']


class SubtaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating subtasks"""
    
    class Meta:
        model = Subtask
        fields = ['title', 'description', 'priority', 'estimated_hours', 'due_date']
    
    def validate_title(self, value):
        """Validate subtask title"""
        if not value.strip():
            raise ValidationError("Subtask title cannot be empty.")
        return value.strip()


class SubtaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating subtasks"""
    
    class Meta:
        model = Subtask
        fields = ['title', 'description', 'completed', 'priority', 'progress', 
                 'estimated_hours', 'actual_hours', 'due_date']


class SubtaskDetailSerializer(SubtaskSerializer):
    """Detailed serializer for subtasks"""
    
    class Meta(SubtaskSerializer.Meta):
        fields = SubtaskSerializer.Meta.fields + ['task']


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Comment model"""
    author = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'content', 'is_internal', 'author', 'is_edited', 'edited_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'is_edited', 'edited_at', 'created_at', 'updated_at']


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


class AttachmentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating attachments"""
    
    class Meta:
        model = Attachment
        fields = ['description', 'is_public']


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
                 'priority', 'tags', 'estimated_hours']
    
    def validate_title(self, value):
        """Validate task title"""
        if not value.strip():
            raise ValidationError("Task title cannot be empty.")
        return value.strip()
    
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
