from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count, Avg
from .models import Tag, Task, Subtask, Comment, Attachment
from .utils import get_task_priority_color, get_task_status_color, get_due_date_status


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_display', 'description', 'task_count', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    def color_display(self, obj):
        """Display color as a colored square"""
        if obj.color:
            return format_html(
                '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
                obj.color, obj.color
            )
        return '-'
    color_display.short_description = 'Color'
    
    def task_count(self, obj):
        """Show number of tasks using this tag"""
        return obj.tasks.count()
    task_count.short_description = 'Tasks'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'owner', 'assigned_to', 'priority_display', 'status_display', 
        'progress_display', 'due_date_display', 'completed', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'completed', 'owner', 'assigned_to', 
        'created_at', 'due_date', 'tags'
    ]
    search_fields = ['title', 'description', 'owner__username', 'assigned_to__username']
    ordering = ['-created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'started_at', 'completed_at', 
        'cancelled_at', 'cancelled_by', 'subtask_progress'
    ]
    filter_horizontal = ['tags']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'owner', 'assigned_to', 'tags')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'completed', 'progress')
        }),
        ('Timing', {
            'fields': ('due_date', 'due_reminder', 'estimated_hours', 'actual_hours')
        }),
        ('Audit Information', {
            'fields': ('started_at', 'completed_at', 'cancelled_at', 'cancelled_by'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def priority_display(self, obj):
        """Display priority with color"""
        color = get_task_priority_color(obj.priority)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_display.short_description = 'Priority'
    
    def status_display(self, obj):
        """Display status with color"""
        color = get_task_status_color(obj.status)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def progress_display(self, obj):
        """Display progress as a progress bar"""
        color = '#28a745' if obj.progress == 100 else '#007bff'
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; '
            'display: flex; align-items: center; justify-content: center; color: white; font-size: 12px;">'
            '{}%</div></div>',
            obj.progress, color, obj.progress
        )
    progress_display.short_description = 'Progress'
    
    def due_date_display(self, obj):
        """Display due date with status"""
        if not obj.due_date:
            return '-'
        
        status_info = get_due_date_status(obj.due_date, obj.completed)
        return format_html(
            '<span style="color: {};">{}</span><br><small>{}</small>',
            status_info['color'], obj.due_date.strftime('%Y-%m-%d %H:%M'), status_info['message']
        )
    due_date_display.short_description = 'Due Date'
    
    def subtask_progress(self, obj):
        """Show subtask progress"""
        return f"{obj.subtask_progress}%"
    subtask_progress.short_description = 'Subtask Progress'
    
    def get_queryset(self, request):
        """Optimize queryset with related fields"""
        return super().get_queryset(request).select_related(
            'owner', 'assigned_to', 'cancelled_by'
        ).prefetch_related('tags', 'subtasks')
    
    def save_model(self, request, obj, form, change):
        """Handle special logic when saving"""
        if not change:  # New task
            if not obj.owner:
                obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(Subtask)
class SubtaskAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'task_link', 'priority_display', 'progress_display', 
        'completed', 'due_date_display', 'created_at'
    ]
    list_filter = [
        'completed', 'priority', 'task__status', 'created_at', 'due_date'
    ]
    search_fields = ['title', 'description', 'task__title']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'task')
        }),
        ('Status & Priority', {
            'fields': ('priority', 'completed', 'progress')
        }),
        ('Timing', {
            'fields': ('due_date', 'estimated_hours', 'actual_hours')
        }),
        ('System', {
            'fields': ('started_at', 'completed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def task_link(self, obj):
        """Link to parent task"""
        if obj.task:
            url = reverse('admin:tasks_task_change', args=[obj.task.id])
            return format_html('<a href="{}">{}</a>', url, obj.task.title)
        return '-'
    task_link.short_description = 'Parent Task'
    
    def priority_display(self, obj):
        """Display priority with color"""
        color = get_task_priority_color(obj.priority)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_display.short_description = 'Priority'
    
    def progress_display(self, obj):
        """Display progress as a progress bar"""
        color = '#28a745' if obj.progress == 100 else '#007bff'
        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; '
            'display: flex; align-items: center; justify-content: center; color: white; font-size: 12px;">'
            '{}%</div></div>',
            obj.progress, color, obj.progress
        )
    progress_display.short_description = 'Progress'
    
    def due_date_display(self, obj):
        """Display due date with status"""
        if not obj.due_date:
            return '-'
        
        status_info = get_due_date_status(obj.due_date, obj.completed)
        return format_html(
            '<span style="color: {};">{}</span><br><small>{}</small>',
            status_info['color'], obj.due_date.strftime('%Y-%m-%d %H:%M'), status_info['message']
        )
    due_date_display.short_description = 'Due Date'
    
    def get_queryset(self, request):
        """Optimize queryset with related fields"""
        return super().get_queryset(request).select_related('task')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        'content_preview', 'author', 'task_link', 'subtask_link', 
        'is_internal', 'is_edited', 'created_at'
    ]
    list_filter = [
        'is_internal', 'is_edited', 'author', 'created_at', 'edited_at'
    ]
    search_fields = ['content', 'author__username', 'task__title', 'subtask__title']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'is_edited', 'edited_at']
    
    fieldsets = (
        ('Content', {
            'fields': ('content', 'author', 'is_internal')
        }),
        ('Related Items', {
            'fields': ('task', 'subtask', 'parent_comment')
        }),
        ('System', {
            'fields': ('is_edited', 'edited_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def content_preview(self, obj):
        """Show content preview"""
        preview = obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
        return preview
    content_preview.short_description = 'Content'
    
    def task_link(self, obj):
        """Link to related task"""
        if obj.task:
            url = reverse('admin:tasks_task_change', args=[obj.task.id])
            return format_html('<a href="{}">{}</a>', url, obj.task.title)
        return '-'
    task_link.short_description = 'Task'
    
    def subtask_link(self, obj):
        """Link to related subtask"""
        if obj.subtask:
            url = reverse('admin:tasks_subtask_change', args=[obj.subtask.id])
            return format_html('<a href="{}">{}</a>', url, obj.subtask.title)
        return '-'
    subtask_link.short_description = 'Subtask'
    
    def get_queryset(self, request):
        """Optimize queryset with related fields"""
        return super().get_queryset(request).select_related(
            'author', 'task', 'subtask', 'parent_comment'
        )


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = [
        'original_filename', 'file_type', 'file_size_display', 'uploaded_by',
        'task_link', 'subtask_link', 'is_public', 'created_at'
    ]
    list_filter = [
        'file_type', 'is_public', 'uploaded_by', 'created_at'
    ]
    search_fields = [
        'original_filename', 'description', 'uploaded_by__username',
        'task__title', 'subtask__title'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'file_size', 'file_type'
    ]
    
    fieldsets = (
        ('File Information', {
            'fields': ('file', 'original_filename', 'description', 'is_public')
        }),
        ('Related Items', {
            'fields': ('task', 'subtask', 'uploaded_by')
        }),
        ('System', {
            'fields': ('file_size', 'file_type', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        if obj.file_size:
            size_kb = obj.file_size / 1024
            if size_kb < 1024:
                return f"{size_kb:.1f} KB"
            else:
                size_mb = size_kb / 1024
                return f"{size_mb:.1f} MB"
        return '-'
    file_size_display.short_description = 'File Size'
    
    def task_link(self, obj):
        """Link to related task"""
        if obj.task:
            url = reverse('admin:tasks_task_change', args=[obj.task.id])
            return format_html('<a href="{}">{}</a>', url, obj.task.title)
        return '-'
    task_link.short_description = 'Task'
    
    def subtask_link(self, obj):
        """Link to related subtask"""
        if obj.subtask:
            url = reverse('admin:tasks_subtask_change', args=[obj.subtask.id])
            return format_html('<a href="{}">{}</a>', url, obj.subtask.title)
        return '-'
    subtask_link.short_description = 'Subtask'
    
    def get_queryset(self, request):
        """Optimize queryset with related fields"""
        return super().get_queryset(request).select_related(
            'uploaded_by', 'task', 'subtask'
        )


# Custom admin site configuration
admin.site.site_header = "TaskManager Administration"
admin.site.site_title = "TaskManager Admin"
admin.site.index_title = "Welcome to TaskManager Administration"
