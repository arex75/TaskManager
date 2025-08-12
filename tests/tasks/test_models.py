from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.tasks.models import Task, Subtask, Comment, Attachment, Tag, TaskPriority, TaskStatus
from tests.base import BaseTestCase

User = get_user_model()

class TagModelTest(BaseTestCase):
    """Test cases for Tag model"""
    
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(**self.user_data)
    
    def test_create_tag(self):
        """Test creating a tag"""
        tag = Tag.objects.create(
            name='Test Tag',
            color='#ff0000',
            description='A test tag'
        )
        self.assertEqual(tag.name, 'Test Tag')
        self.assertEqual(tag.color, '#ff0000')
        self.assertEqual(tag.description, 'A test tag')
        self.assertIsNotNone(tag.created_at)
        self.assertIsNotNone(tag.updated_at)
    
    def test_tag_string_representation(self):
        """Test tag string representation"""
        tag = Tag.objects.create(name='Test Tag')
        self.assertEqual(str(tag), 'Test Tag')
    
    def test_tag_unique_name(self):
        """Test tag name uniqueness"""
        Tag.objects.create(name='Test Tag')
        with self.assertRaises(Exception):  # Should raise IntegrityError
            Tag.objects.create(name='Test Tag')

class TaskModelTest(BaseTestCase):
    """Test cases for Task model"""
    
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(**self.user_data)
        self.tag = Tag.objects.create(name='Test Tag')
    
    def test_create_task(self):
        """Test creating a task"""
        task = Task.objects.create(
            title='Test Task',
            description='A test task description',
            owner=self.user,
            priority=TaskPriority.HIGH,
            status=TaskStatus.TODO
        )
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.description, 'A test task description')
        self.assertEqual(task.owner, self.user)
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertEqual(task.status, TaskStatus.TODO)
        self.assertFalse(task.completed)
        self.assertEqual(task.progress, 0)
        self.assertIsNotNone(task.created_at)
        self.assertIsNotNone(task.updated_at)
    
    def test_task_string_representation(self):
        """Test task string representation"""
        task = Task.objects.create(
            title='Test Task',
            owner=self.user,
            status=TaskStatus.IN_PROGRESS
        )
        expected = f"Test Task (In Progress)"
        self.assertEqual(str(task), expected)
    
    def test_task_with_due_date(self):
        """Test task with due date"""
        due_date = timezone.now() + timedelta(days=7)
        task = Task.objects.create(
            title='Test Task',
            owner=self.user,
            due_date=due_date
        )
        self.assertEqual(task.due_date, due_date)
    
    def test_task_with_tags(self):
        """Test task with tags"""
        task = Task.objects.create(
            title='Test Task',
            owner=self.user
        )
        task.tags.add(self.tag)
        self.assertIn(self.tag, task.tags.all())
    
    def test_task_assignment(self):
        """Test task assignment to another user"""
        assigned_user = User.objects.create_user(
            username='assigneduser',
            email='assigned@example.com',
            password='assignedpass123'
        )
        task = Task.objects.create(
            title='Test Task',
            owner=self.user,
            assigned_to=assigned_user
        )
        self.assertEqual(task.assigned_to, assigned_user)
    
    def test_task_progress_update(self):
        """Test task progress update"""
        task = Task.objects.create(
            title='Test Task',
            owner=self.user
        )
        task.update_progress(50)
        self.assertEqual(task.progress, 50)
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)
    
    def test_task_completion(self):
        """Test task completion"""
        task = Task.objects.create(
            title='Test Task',
            owner=self.user
        )
        task.complete_task()
        self.assertTrue(task.completed)
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.status, TaskStatus.DONE)
        self.assertIsNotNone(task.completed_at)
    
    def test_task_start(self):
        """Test task start"""
        task = Task.objects.create(
            title='Test Task',
            owner=self.user,
            status=TaskStatus.TODO
        )
        task.start_task()
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)
        self.assertIsNotNone(task.started_at)
    
    def test_task_cancellation(self):
        """Test task cancellation"""
        task = Task.objects.create(
            title='Test Task',
            owner=self.user
        )
        task.cancel_task(self.user)
        self.assertEqual(task.status, TaskStatus.CANCELLED)
        self.assertIsNotNone(task.cancelled_at)
        self.assertEqual(task.cancelled_by, self.user)
    
    def test_task_overdue_property(self):
        """Test task overdue property"""
        # Task not overdue
        task = Task.objects.create(
            title='Test Task',
            owner=self.user,
            due_date=timezone.now() + timedelta(days=1)
        )
        self.assertFalse(task.is_overdue)
        
        # Task overdue
        overdue_task = Task.objects.create(
            title='Overdue Task',
            owner=self.user,
            due_date=timezone.now() - timedelta(days=1)
        )
        self.assertTrue(overdue_task.is_overdue)
    
    def test_task_with_subtasks(self):
        """Test task with subtasks"""
        task = Task.objects.create(
            title='Test Task',
            owner=self.user
        )
        subtask = Subtask.objects.create(
            title='Test Subtask',
            task=task
        )
        self.assertTrue(task.has_subtasks)
        self.assertIn(subtask, task.subtasks.all())
    
    def test_subtask_progress_calculation(self):
        """Test subtask progress calculation"""
        task = Task.objects.create(
            title='Test Task',
            owner=self.user
        )
        
        # Create subtasks
        Subtask.objects.create(title='Subtask 1', task=task)
        Subtask.objects.create(title='Subtask 2', task=task)
        
        # Initially 0% progress
        self.assertEqual(task.subtask_progress, 0)
        
        # Complete one subtask
        subtask = task.subtasks.first()
        subtask.complete_subtask()
        
        # Should be 50% progress
        self.assertEqual(task.subtask_progress, 50)

class SubtaskModelTest(BaseTestCase):
    """Test cases for Subtask model"""
    
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(**self.user_data)
        self.task = Task.objects.create(
            title='Test Task',
            owner=self.user
        )
    
    def test_create_subtask(self):
        """Test creating a subtask"""
        subtask = Subtask.objects.create(
            title='Test Subtask',
            description='A test subtask description',
            task=self.task,
            priority=TaskPriority.MEDIUM
        )
        self.assertEqual(subtask.title, 'Test Subtask')
        self.assertEqual(subtask.task, self.task)
        self.assertEqual(subtask.priority, TaskPriority.MEDIUM)
        self.assertFalse(subtask.completed)
        self.assertEqual(subtask.progress, 0)
    
    def test_subtask_string_representation(self):
        """Test subtask string representation"""
        subtask = Subtask.objects.create(
            title='Test Subtask',
            task=self.task
        )
        expected = f"Test Subtask (Subtask of Test Task)"
        self.assertEqual(str(subtask), expected)
    
    def test_subtask_completion(self):
        """Test subtask completion"""
        subtask = Subtask.objects.create(
            title='Test Subtask',
            task=self.task
        )
        subtask.complete_subtask()
        self.assertTrue(subtask.completed)
        self.assertEqual(subtask.progress, 100)
    
    # Negative and Edge Cases for Subtask Model
    
    def test_subtask_creation_without_required_fields(self):
        """Test subtask creation fails without required fields"""
        # Test without title - Django allows empty strings, so this should work
        subtask = Subtask.objects.create(task=self.task)
        self.assertEqual(subtask.title, '')
        
        # Test without task - should fail as task is required
        with self.assertRaises(IntegrityError):
            Subtask.objects.create(title='Test Subtask')
    
    def test_subtask_creation_with_empty_title(self):
        """Test subtask creation with empty title"""
        subtask = Subtask.objects.create(title='', task=self.task)
        self.assertEqual(subtask.title, '')
    
    def test_subtask_creation_with_very_long_title(self):
        """Test subtask creation with maximum length title"""
        long_title = 'A' * 255  # Max length for title field
        subtask = Subtask.objects.create(title=long_title, task=self.task)
        self.assertEqual(len(subtask.title), 255)
    
    def test_subtask_creation_with_very_long_description(self):
        """Test subtask creation with very long description"""
        long_desc = 'A' * 1000
        subtask = Subtask.objects.create(
            title='Long Desc Subtask',
            description=long_desc,
            task=self.task
        )
        self.assertEqual(len(subtask.description), 1000)
    
    def test_subtask_progress_validation(self):
        """Test subtask progress validation"""
        # Test valid progress values
        valid_progress = [0, 25, 50, 75, 100]
        for progress in valid_progress:
            subtask = Subtask.objects.create(
                title=f'Progress {progress} Subtask',
                task=self.task,
                progress=progress
            )
            self.assertEqual(subtask.progress, progress)
        
        # Test invalid progress values
        invalid_progress = [-1, 101, 150, -50]
        for progress in invalid_progress:
            with self.assertRaises(ValidationError):
                subtask = Subtask.objects.create(
                    title=f'Invalid Progress {progress} Subtask',
                    task=self.task,
                    progress=progress
                )
                subtask.full_clean()
    
    def test_subtask_hours_validation(self):
        """Test subtask hours validation"""
        # Test valid hour values
        valid_hours = [Decimal('0.5'), Decimal('1.0'), Decimal('8.5'), Decimal('24.0')]
        for hours in valid_hours:
            subtask = Subtask.objects.create(
                title=f'Hours {hours} Subtask',
                task=self.task,
                estimated_hours=hours
            )
            self.assertEqual(subtask.estimated_hours, hours)
        
        # Test negative hours
        negative_hours = [Decimal('-1.0'), Decimal('-8.5')]
        for hours in negative_hours:
            subtask = Subtask.objects.create(
                title=f'Negative Hours {hours} Subtask',
                task=self.task,
                estimated_hours=hours
            )
            self.assertEqual(subtask.estimated_hours, hours)
    
    def test_subtask_completion_multiple_times(self):
        """Test subtask completion multiple times"""
        subtask = Subtask.objects.create(
            title='Multiple Completion Subtask',
            task=self.task
        )
        
        subtask.complete_subtask()
        first_completion_time = subtask.updated_at
        
        # Complete again
        subtask.complete_subtask()
        second_completion_time = subtask.updated_at
        
        # Should still be completed
        self.assertTrue(subtask.completed)
        self.assertEqual(subtask.progress, 100)
        # Updated time should change
        self.assertGreater(second_completion_time, first_completion_time)
    
    def test_subtask_with_extreme_values(self):
        """Test subtask with extreme field values"""
        max_subtask = Subtask.objects.create(
            title='A' * 255,  # Max title length
            description='A' * 10000,  # Very long description
            task=self.task,
            priority=TaskPriority.URGENT,
            progress=100,
            estimated_hours=Decimal('999.99'),
            actual_hours=Decimal('999.99')
        )
        
        self.assertEqual(len(max_subtask.title), 255)
        self.assertEqual(len(max_subtask.description), 10000)
        self.assertEqual(max_subtask.priority, TaskPriority.URGENT)
        self.assertEqual(max_subtask.progress, 100)
        self.assertEqual(max_subtask.estimated_hours, Decimal('999.99'))
        self.assertEqual(max_subtask.actual_hours, Decimal('999.99'))
    
    def test_subtask_with_special_characters(self):
        """Test subtask with special characters"""
        special_subtask = Subtask.objects.create(
            title='Subtask with @#$%^&*() chars',
            description='Description with <script>alert("xss")</script>',
            task=self.task
        )
        
        self.assertEqual(special_subtask.title, 'Subtask with @#$%^&*() chars')
        self.assertEqual(special_subtask.description, 'Description with <script>alert("xss")</script>')
    
    def test_subtask_with_unicode_characters(self):
        """Test subtask with unicode characters"""
        unicode_subtask = Subtask.objects.create(
            title='子任务标题',
            description='子任务描述使用中文',
            task=self.task
        )
        
        self.assertEqual(unicode_subtask.title, '子任务标题')
        self.assertEqual(unicode_subtask.description, '子任务描述使用中文')
    
    def test_subtask_with_none_values(self):
        """Test subtask with None values for optional fields"""
        none_subtask = Subtask.objects.create(
            title='None Values Subtask',
            task=self.task,
            description=None,
            estimated_hours=None,
            actual_hours=None
        )
        
        self.assertIsNone(none_subtask.description)
        self.assertIsNone(none_subtask.estimated_hours)
        self.assertIsNone(none_subtask.actual_hours)

class CommentModelTest(BaseTestCase):
    """Test cases for Comment model"""
    
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(**self.user_data)
        self.task = Task.objects.create(
            title='Test Task',
            owner=self.user
        )
    
    def test_create_comment_on_task(self):
        """Test creating a comment on a task"""
        comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='This is a test comment'
        )
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.task, self.task)
        self.assertEqual(comment.content, 'This is a test comment')
        self.assertFalse(comment.is_internal)
        self.assertIsNone(comment.subtask)
    
    def test_create_internal_comment(self):
        """Test creating an internal comment"""
        comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='Internal comment',
            is_internal=True
        )
        self.assertTrue(comment.is_internal)
    
    def test_comment_string_representation(self):
        """Test comment string representation"""
        comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='Test comment'
        )
        expected = f"Comment by {self.user.username} on Test Task"
        self.assertEqual(str(comment), expected)
    
    # Negative and Edge Cases for Comment Model
    
    def test_comment_creation_without_required_fields(self):
        """Test comment creation fails without required fields"""
        # Test without author
        with self.assertRaises(IntegrityError):
            Comment.objects.create(
                task=self.task,
                content='Test comment'
            )
    
    def test_comment_creation_with_empty_content(self):
        """Test comment creation with empty content"""
        comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content=''
        )
        self.assertEqual(comment.content, '')
    
    def test_comment_creation_with_very_long_content(self):
        """Test comment creation with very long content"""
        long_content = 'A' * 10000
        comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content=long_content
        )
        self.assertEqual(len(comment.content), 10000)
    
    def test_comment_creation_without_task_or_subtask(self):
        """Test comment creation without task or subtask"""
        # Should work as both fields are optional
        comment = Comment.objects.create(
            author=self.user,
            content='Comment without task or subtask'
        )
        self.assertIsNone(comment.task)
        self.assertIsNone(comment.subtask)
    
    def test_comment_creation_with_both_task_and_subtask(self):
        """Test comment creation with both task and subtask"""
        subtask = Subtask.objects.create(
            title='Test Subtask',
            task=self.task
        )
        
        comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            subtask=subtask,
            content='Comment with both task and subtask'
        )
        self.assertEqual(comment.task, self.task)
        self.assertEqual(comment.subtask, subtask)
    
    def test_comment_with_special_characters(self):
        """Test comment with special characters"""
        special_comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='Comment with @#$%^&*() chars and <script>alert("xss")</script>'
        )
        
        self.assertEqual(special_comment.content, 'Comment with @#$%^&*() chars and <script>alert("xss")</script>')
    
    def test_comment_with_unicode_characters(self):
        """Test comment with unicode characters"""
        unicode_comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='评论使用中文和特殊字符：@#$%^&*()'
        )
        
        self.assertEqual(unicode_comment.content, '评论使用中文和特殊字符：@#$%^&*()')
    
    def test_comment_with_html_tags(self):
        """Test comment with HTML tags"""
        html_comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='<b>Bold comment</b> with <p>paragraph</p>'
        )
        
        self.assertEqual(html_comment.content, '<b>Bold comment</b> with <p>paragraph</p>')
    
    def test_comment_with_sql_injection_attempts(self):
        """Test comment with SQL injection attempt strings"""
        sql_comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content="'; DROP TABLE comments; --"
        )
        
        self.assertEqual(sql_comment.content, "'; DROP TABLE comments; --")
    
    def test_comment_with_whitespace_only(self):
        """Test comment with whitespace-only content"""
        whitespace_comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='   \t\n   '
        )
        
        self.assertEqual(whitespace_comment.content, '   \t\n   ')
    
    def test_comment_with_none_values(self):
        """Test comment with None values for optional fields"""
        none_comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='None Values Comment',
            is_internal=None,
            parent_comment=None
        )
        
        self.assertIsNone(none_comment.is_internal)
        self.assertIsNone(none_comment.parent_comment)
    
    def test_comment_threading(self):
        """Test comment threading functionality"""
        # Create parent comment
        parent_comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='Parent comment'
        )
        
        # Create reply comment
        reply_comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='Reply to parent',
            parent_comment=parent_comment
        )
        
        self.assertEqual(reply_comment.parent_comment, parent_comment)
        self.assertIn(reply_comment, parent_comment.replies.all())
    
    def test_comment_threading_deep_nesting(self):
        """Test comment threading with deep nesting"""
        # Create nested comments
        level1 = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='Level 1'
        )
        
        level2 = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='Level 2',
            parent_comment=level1
        )
        
        level3 = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='Level 3',
            parent_comment=level2
        )
        
        self.assertEqual(level3.parent_comment, level2)
        self.assertEqual(level2.parent_comment, level1)
        self.assertIsNone(level1.parent_comment)
    
    def test_comment_string_representation_edge_cases(self):
        """Test comment string representation edge cases"""
        # Comment on task
        task_comment = Comment.objects.create(
            author=self.user,
            task=self.task,
            content='Task comment'
        )
        expected_task = f"Comment by {self.user.username} on Test Task"
        self.assertEqual(str(task_comment), expected_task)
        
        # Comment on subtask
        subtask = Subtask.objects.create(
            title='Test Subtask',
            task=self.task
        )
        subtask_comment = Comment.objects.create(
            author=self.user,
            subtask=subtask,
            content='Subtask comment'
        )
        expected_subtask = f"Comment by {self.user.username} on Test Subtask"
        self.assertEqual(str(subtask_comment), expected_subtask)
        
        # Comment without task or subtask
        orphan_comment = Comment.objects.create(
            author=self.user,
            content='Orphan comment'
        )
        expected_orphan = f"Comment by {self.user.username} on None"
        self.assertEqual(str(orphan_comment), expected_orphan)

class AttachmentModelTest(BaseTestCase):
    """Test cases for Attachment model"""
    
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(**self.user_data)
        self.task = Task.objects.create(
            title='Test Task',
            owner=self.user
        )
    
    def test_create_attachment(self):
        """Test creating an attachment"""
        # Note: In real tests, you'd use a mock file or create a temporary file
        # For now, we'll test the model structure
        attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='test.txt',
            file_size=1024,
            file_type='TXT',
            description='Test attachment'
        )
        self.assertEqual(attachment.uploaded_by, self.user)
        self.assertEqual(attachment.task, self.task)
        self.assertEqual(attachment.original_filename, 'test.txt')
        self.assertEqual(attachment.file_size, 1024)
        self.assertEqual(attachment.file_type, 'TXT')
        self.assertEqual(attachment.description, 'Test attachment')
    
    def test_attachment_string_representation(self):
        """Test attachment string representation"""
        attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='test.txt',
            file_size=1024,
            file_type='TXT'
        )
        expected = f"test.txt on Test Task"
        self.assertEqual(str(attachment), expected)
    
    # Negative and Edge Cases for Attachment Model
    
    def test_attachment_creation_without_required_fields(self):
        """Test attachment creation fails without required fields"""
        # Test without uploaded_by - should fail
        with self.assertRaises(IntegrityError):
            Attachment.objects.create(
                task=self.task,
                original_filename='test.txt',
                file_size=1024,
                file_type='TXT'
            )
    
    def test_attachment_creation_with_empty_filename(self):
        """Test attachment creation with empty filename"""
        attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='',
            file_size=1024,
            file_type='TXT'
        )
        self.assertEqual(attachment.original_filename, '')
    
    def test_attachment_creation_with_very_long_filename(self):
        """Test attachment creation with maximum length filename"""
        long_filename = 'A' * 255  # Max length for filename field
        attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename=long_filename,
            file_size=1024,
            file_type='TXT'
        )
        self.assertEqual(len(attachment.original_filename), 255)
    
    def test_attachment_creation_with_very_long_description(self):
        """Test attachment creation with very long description"""
        long_desc = 'A' * 10000
        attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='Long Desc File.txt',
            file_size=1024,
            file_type='TXT',
            description=long_desc
        )
        self.assertEqual(len(attachment.description), 10000)
    
    def test_attachment_creation_without_task_or_subtask(self):
        """Test attachment creation without task or subtask"""
        # Should work as both fields are optional
        attachment = Attachment.objects.create(
            uploaded_by=self.user,
            original_filename='Orphan File.txt',
            file_size=1024,
            file_type='TXT'
        )
        self.assertIsNone(attachment.task)
        self.assertIsNone(attachment.subtask)
    
    def test_attachment_creation_with_both_task_and_subtask(self):
        """Test attachment creation with both task and subtask"""
        subtask = Subtask.objects.create(
            title='Test Subtask',
            task=self.task
        )
        
        attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            subtask=subtask,
            original_filename='Both File.txt',
            file_size=1024,
            file_type='TXT'
        )
        self.assertEqual(attachment.task, self.task)
        self.assertEqual(attachment.subtask, subtask)
    
    def test_attachment_with_extreme_values(self):
        """Test attachment with extreme field values"""
        # Test with maximum values
        max_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='A' * 255,  # Max filename length
            file_size=2147483647,  # Max PositiveIntegerField value
            file_type='A' * 100,  # Max file_type length
            description='A' * 10000  # Very long description
        )
        
        self.assertEqual(len(max_attachment.original_filename), 255)
        self.assertEqual(max_attachment.file_size, 2147483647)
        self.assertEqual(len(max_attachment.file_type), 100)
        self.assertEqual(len(max_attachment.description), 10000)
    
    def test_attachment_with_special_characters(self):
        """Test attachment with special characters"""
        special_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='File with @#$%^&*() chars.txt',
            file_type='SPECIAL_TYPE',
            description='Description with <script>alert("xss")</script>',
            file_size=1024
        )
        
        self.assertEqual(special_attachment.original_filename, 'File with @#$%^&*() chars.txt')
        self.assertEqual(special_attachment.file_type, 'SPECIAL_TYPE')
        self.assertEqual(special_attachment.description, 'Description with <script>alert("xss")</script>')
    
    def test_attachment_with_unicode_characters(self):
        """Test attachment with unicode characters"""
        unicode_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='文件名称.txt',
            file_type='UNICODE_TYPE',
            description='文件描述使用中文',
            file_size=1024
        )
        
        self.assertEqual(unicode_attachment.original_filename, '文件名称.txt')
        self.assertEqual(unicode_attachment.file_type, 'UNICODE_TYPE')
        self.assertEqual(unicode_attachment.description, '文件描述使用中文')
    
    def test_attachment_with_html_tags(self):
        """Test attachment with HTML tags"""
        html_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='<b>Bold File</b>.txt',
            file_type='HTML_TYPE',
            description='<p>HTML description</p>',
            file_size=1024
        )
        
        self.assertEqual(html_attachment.original_filename, '<b>Bold File</b>.txt')
        self.assertEqual(html_attachment.file_type, 'HTML_TYPE')
        self.assertEqual(html_attachment.description, '<p>HTML description</p>')
    
    def test_attachment_with_sql_injection_attempts(self):
        """Test attachment with SQL injection attempt strings"""
        sql_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename="'; DROP TABLE attachments; --.txt",
            file_type="'; DELETE FROM attachments; --",
            description="'; UPDATE attachments SET file_size = 0; --",
            file_size=1024
        )
        
        self.assertEqual(sql_attachment.original_filename, "'; DROP TABLE attachments; --.txt")
        self.assertEqual(sql_attachment.file_type, "'; DELETE FROM attachments; --")
        self.assertEqual(sql_attachment.description, "'; UPDATE attachments SET file_size = 0; --")
    
    def test_attachment_with_numbers_in_text_fields(self):
        """Test attachment with numbers in text fields"""
        number_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='File123.txt',
            file_type='TYPE456',
            description='Description with numbers 789',
            file_size=1024
        )
        
        self.assertEqual(number_attachment.original_filename, 'File123.txt')
        self.assertEqual(number_attachment.file_type, 'TYPE456')
        self.assertEqual(number_attachment.description, 'Description with numbers 789')
    
    def test_attachment_with_whitespace_only(self):
        """Test attachment with whitespace-only values"""
        whitespace_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='   ',
            file_type='\t\n',
            description='   ',
            file_size=1024
        )
        
        self.assertEqual(whitespace_attachment.original_filename, '   ')
        self.assertEqual(whitespace_attachment.file_type, '\t\n')
        self.assertEqual(whitespace_attachment.description, '   ')
    
    def test_attachment_with_none_values(self):
        """Test attachment with None values for optional fields"""
        none_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='None Values File.txt',
            file_size=1024,
            file_type='NONE_TYPE',
            description=None
        )
        
        self.assertIsNone(none_attachment.description)
    
    def test_attachment_file_size_edge_cases(self):
        """Test attachment file size edge cases"""
        # Test with zero file size
        zero_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='Zero Size File.txt',
            file_size=0,
            file_type='ZERO'
        )
        self.assertEqual(zero_attachment.file_size, 0)
        
        # Test with very large file size
        large_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='Large File.txt',
            file_size=1000000000,  # 1GB
            file_type='LARGE'
        )
        self.assertEqual(large_attachment.file_size, 1000000000)
    
    def test_attachment_string_representation_edge_cases(self):
        """Test attachment string representation edge cases"""
        # Attachment on task
        task_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            task=self.task,
            original_filename='Task File.txt',
            file_size=1024,
            file_type='TASK'
        )
        expected_task = f"Task File.txt on Test Task"
        self.assertEqual(str(task_attachment), expected_task)
        
        # Attachment on subtask
        subtask = Subtask.objects.create(
            title='Test Subtask',
            task=self.task
        )
        subtask_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            subtask=subtask,
            original_filename='Subtask File.txt',
            file_size=1024,
            file_type='SUBTASK'
        )
        expected_subtask = f"Subtask File.txt on Test Subtask"
        self.assertEqual(str(subtask_attachment), expected_subtask)
        
        # Attachment without task or subtask
        orphan_attachment = Attachment.objects.create(
            uploaded_by=self.user,
            original_filename='Orphan File.txt',
            file_size=1024,
            file_type='ORPHAN'
        )
        expected_orphan = f"Orphan File.txt on None"
        self.assertEqual(str(orphan_attachment), expected_orphan)

class TaskPriorityAndStatusTest(BaseTestCase):
    """Test cases for TaskPriority and TaskStatus choices"""
    
    def setUp(self):
        """Set up test data"""
        super().setUp()
        self.user = User.objects.create_user(**self.user_data)
    
    def test_task_priority_choices(self):
        """Test task priority choices"""
        self.assertEqual(TaskPriority.LOW, 'LOW')
        self.assertEqual(TaskPriority.MEDIUM, 'MEDIUM')
        self.assertEqual(TaskPriority.HIGH, 'HIGH')
        self.assertEqual(TaskPriority.URGENT, 'URGENT')
    
    def test_task_status_choices(self):
        """Test task status choices"""
        self.assertEqual(TaskStatus.TODO, 'TODO')
        self.assertEqual(TaskStatus.IN_PROGRESS, 'IN_PROGRESS')
        self.assertEqual(TaskStatus.REVIEW, 'REVIEW')
        self.assertEqual(TaskStatus.DONE, 'DONE')
        self.assertEqual(TaskStatus.BLOCKED, 'BLOCKED')
        self.assertEqual(TaskStatus.CANCELLED, 'CANCELLED')
    
    # Negative and Edge Cases for Tag Model
    
    def test_tag_creation_without_name(self):
        """Test tag creation fails without name"""
        # Tag name field is required (not null), so this should fail
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name=None)
    
    def test_tag_creation_with_empty_name(self):
        """Test tag creation with empty name"""
        tag = Tag.objects.create(name='')
        self.assertEqual(tag.name, '')
    
    def test_tag_creation_with_very_long_name(self):
        """Test tag creation with maximum length name"""
        long_name = 'A' * 50  # Max length for name field
        tag = Tag.objects.create(name=long_name)
        self.assertEqual(len(tag.name), 50)
    
    def test_tag_creation_with_special_characters(self):
        """Test tag creation with special characters"""
        special_name = 'Tag with @#$%^&*() chars'
        tag = Tag.objects.create(name=special_name)
        self.assertEqual(tag.name, 'Tag with @#$%^&*() chars')
    
    def test_tag_creation_with_unicode_characters(self):
        """Test tag creation with unicode characters"""
        unicode_name = '标签名称'
        tag = Tag.objects.create(name=unicode_name)
        self.assertEqual(tag.name, '标签名称')
    
    def test_tag_creation_with_numbers(self):
        """Test tag creation with numbers"""
        number_name = 'Tag123'
        tag = Tag.objects.create(name=number_name)
        self.assertEqual(tag.name, 'Tag123')
    
    def test_tag_creation_with_whitespace(self):
        """Test tag creation with whitespace"""
        whitespace_name = '  Tag with spaces  '
        tag = Tag.objects.create(name=whitespace_name)
        self.assertEqual(tag.name, '  Tag with spaces  ')
    
    def test_tag_color_validation(self):
        """Test tag color validation"""
        # Test valid hex colors
        valid_colors = ['#ff0000', '#00ff00', '#0000ff', '#ffffff', '#000000']
        for color in valid_colors:
            tag = Tag.objects.create(name=f'Tag {color}', color=color)
            self.assertEqual(tag.color, color)
        
        # Test invalid hex colors (should still work as CharField doesn't validate format)
        invalid_colors = ['red', 'invalid', '#gggggg', '123456']
        for color in invalid_colors:
            tag = Tag.objects.create(name=f'Tag {color}', color=color)
            self.assertEqual(tag.color, color)
    
    def test_tag_description_edge_cases(self):
        """Test tag description edge cases"""
        # Test very long description
        long_desc = 'A' * 1000
        tag = Tag.objects.create(name='Long Desc Tag', description=long_desc)
        self.assertEqual(tag.description, long_desc)
        
        # Test empty description
        tag = Tag.objects.create(name='Empty Desc Tag', description='')
        self.assertEqual(tag.description, '')
        
        # Test None description
        tag = Tag.objects.create(name='None Desc Tag', description=None)
        self.assertIsNone(tag.description)
    
    def test_tag_uniqueness_violation(self):
        """Test tag name uniqueness constraint"""
        Tag.objects.create(name='Unique Tag')
        
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name='Unique Tag')
    
    def test_tag_case_sensitivity(self):
        """Test tag name case sensitivity"""
        Tag.objects.create(name='Case Tag')
        Tag.objects.create(name='case tag')  # Should work as different names
        
        self.assertEqual(Tag.objects.filter(name__icontains='case').count(), 2)
    
    # Negative and Edge Cases for Task Model
    
    def test_task_creation_without_required_fields(self):
        """Test task creation fails without required fields"""
        # Test without title - Django allows empty strings, so this should work
        task = Task.objects.create(owner=self.user)
        self.assertEqual(task.title, '')
        
        # Test without owner - should fail as owner is required
        with self.assertRaises(IntegrityError):
            Task.objects.create(title='Test Task')
    
    def test_task_creation_with_empty_title(self):
        """Test task creation with empty title"""
        task = Task.objects.create(title='', owner=self.user)
        self.assertEqual(task.title, '')
    
    def test_task_creation_with_very_long_title(self):
        """Test task creation with maximum length title"""
        long_title = 'A' * 255  # Max length for title field
        task = Task.objects.create(title=long_title, owner=self.user)
        self.assertEqual(len(task.title), 255)
    
    def test_task_creation_with_very_long_description(self):
        """Test task creation with very long description"""
        long_desc = 'A' * 1000
        task = Task.objects.create(
            title='Long Desc Task',
            description=long_desc,
            owner=self.user
        )
        self.assertEqual(len(task.description), 1000)
    
    def test_task_creation_with_invalid_priority(self):
        """Test task creation with invalid priority"""
        with self.assertRaises(ValidationError):
            task = Task.objects.create(
                title='Invalid Priority Task',
                owner=self.user,
                priority='INVALID'
            )
            task.full_clean()
    
    def test_task_creation_with_invalid_status(self):
        """Test task creation with invalid status"""
        with self.assertRaises(ValidationError):
            task = Task.objects.create(
                title='Invalid Status Task',
                owner=self.user,
                status='INVALID'
            )
            task.full_clean()
    
    def test_task_progress_validation(self):
        """Test task progress validation"""
        # Test valid progress values
        valid_progress = [0, 25, 50, 75, 100]
        for progress in valid_progress:
            task = Task.objects.create(
                title=f'Progress {progress} Task',
                owner=self.user,
                progress=progress
            )
            self.assertEqual(task.progress, progress)
        
        # Test invalid progress values
        invalid_progress = [-1, 101, 150, -50]
        for progress in invalid_progress:
            with self.assertRaises(ValidationError):
                task = Task.objects.create(
                    title=f'Invalid Progress {progress} Task',
                    owner=self.user,
                    progress=progress
                )
                task.full_clean()
    
    def test_task_hours_validation(self):
        """Test task hours validation"""
        # Test valid hour values
        valid_hours = [Decimal('0.5'), Decimal('1.0'), Decimal('8.5'), Decimal('24.0')]
        for hours in valid_hours:
            task = Task.objects.create(
                title=f'Hours {hours} Task',
                owner=self.user,
                estimated_hours=hours
            )
            self.assertEqual(task.estimated_hours, hours)
        
        # Test negative hours (should work as DecimalField doesn't validate range)
        negative_hours = [Decimal('-1.0'), Decimal('-8.5')]
        for hours in negative_hours:
            task = Task.objects.create(
                title=f'Negative Hours {hours} Task',
                owner=self.user,
                estimated_hours=hours
            )
            self.assertEqual(task.estimated_hours, hours)
    
    def test_task_due_date_edge_cases(self):
        """Test task due date edge cases"""
        # Test past due date
        past_date = timezone.now() - timedelta(days=1)
        task = Task.objects.create(
            title='Past Due Task',
            owner=self.user,
            due_date=past_date
        )
        self.assertEqual(task.due_date, past_date)
        self.assertTrue(task.is_overdue)
        
        # Test future due date
        future_date = timezone.now() + timedelta(days=365)
        task = Task.objects.create(
            title='Future Due Task',
            owner=self.user,
            due_date=future_date
        )
        self.assertEqual(task.due_date, future_date)
        self.assertFalse(task.is_overdue)
        
        # Test due date in the past
        very_past_date = timezone.now() - timedelta(days=1000)
        task = Task.objects.create(
            title='Very Past Due Task',
            owner=self.user,
            due_date=very_past_date
        )
        self.assertEqual(task.due_date, very_past_date)
        self.assertTrue(task.is_overdue)
    
    def test_task_due_reminder_edge_cases(self):
        """Test task due reminder edge cases"""
        # Test reminder before due date
        due_date = timezone.now() + timedelta(days=7)
        reminder = timezone.now() + timedelta(days=3)
        task = Task.objects.create(
            title='Reminder Task',
            owner=self.user,
            due_date=due_date,
            due_reminder=reminder
        )
        self.assertEqual(task.due_reminder, reminder)
        
        # Test reminder after due date (should still work)
        reminder_after = timezone.now() + timedelta(days=10)
        task = Task.objects.create(
            title='Late Reminder Task',
            owner=self.user,
            due_date=due_date,
            due_reminder=reminder_after
        )
        self.assertEqual(task.due_reminder, reminder_after)
    
    def test_task_assignment_edge_cases(self):
        """Test task assignment edge cases"""
        # Test self-assignment
        task = Task.objects.create(
            title='Self Assigned Task',
            owner=self.user,
            assigned_to=self.user
        )
        self.assertEqual(task.assigned_to, self.user)
        
        # Test assignment to deleted user
        deleted_user = User.objects.create_user(
            username='deleteduser',
            email='deleted@example.com',
            password='deletedpass123'
        )
        deleted_user.soft_delete()
        
        task = Task.objects.create(
            title='Deleted User Task',
            owner=self.user,
            assigned_to=deleted_user
        )
        self.assertEqual(task.assigned_to, deleted_user)
    
    def test_task_parent_edge_cases(self):
        """Test task parent edge cases"""
        # Test self-referencing parent
        task = Task.objects.create(title='Parent Task', owner=self.user)
        task.parent = task  # Self-referencing
        task.save()
        
        self.assertEqual(task.parent, task)
        self.assertIn(task, task.children.all())
    
    def test_task_start_edge_cases(self):
        """Test task start edge cases"""
        # Test starting already started task
        task = Task.objects.create(
            title='Already Started Task',
            owner=self.user,
            status=TaskStatus.IN_PROGRESS
        )
        task.started_at = timezone.now()
        task.save()
        
        original_started_at = task.started_at
        task.start_task()
        
        # Should not change already started task
        self.assertEqual(task.started_at, original_started_at)
        
        # Test starting completed task
        completed_task = Task.objects.create(
            title='Completed Task',
            owner=self.user,
            status=TaskStatus.DONE
        )
        completed_task.start_task()
        
        # Should not change completed task status
        self.assertEqual(completed_task.status, TaskStatus.DONE)
    
    def test_task_completion_edge_cases(self):
        """Test task completion edge cases"""
        # Test completing already completed task
        task = Task.objects.create(
            title='Already Completed Task',
            owner=self.user,
            status=TaskStatus.DONE
        )
        task.completed = True
        task.progress = 100
        original_completed_at = task.completed_at
        task.save()
        
        task.complete_task()
        
        # Should not change already completed task
        self.assertEqual(task.completed_at, original_completed_at)
        
        # Test completing cancelled task
        cancelled_task = Task.objects.create(
            title='Cancelled Task',
            owner=self.user,
            status=TaskStatus.CANCELLED
        )
        cancelled_task.complete_task()
        
        # Should change status to DONE
        self.assertEqual(cancelled_task.status, TaskStatus.DONE)
        self.assertTrue(cancelled_task.completed)
    
    def test_task_cancellation_edge_cases(self):
        """Test task cancellation edge cases"""
        # Test cancelling already cancelled task
        task = Task.objects.create(
            title='Already Cancelled Task',
            owner=self.user,
            status=TaskStatus.CANCELLED
        )
        task.cancelled_at = timezone.now()
        original_cancelled_at = task.cancelled_at
        task.save()
        
        task.cancel_task(self.user)
        
        # Should not change already cancelled task
        self.assertEqual(task.cancelled_at, original_cancelled_at)
        
        # Test cancelling without specifying who cancelled
        task2 = Task.objects.create(
            title='No Canceller Task',
            owner=self.user
        )
        task2.cancel_task(None)
        
        self.assertEqual(task2.status, TaskStatus.CANCELLED)
        self.assertIsNotNone(task2.cancelled_at)
        self.assertIsNone(task2.cancelled_by)
    
    def test_task_progress_update_edge_cases(self):
        """Test task progress update edge cases"""
        # Test progress update with invalid values
        task = Task.objects.create(title='Progress Task', owner=self.user)
        
        invalid_progress = [-10, 150, 200, -50]
        for progress in invalid_progress:
            original_progress = task.progress
            task.update_progress(progress)
            
            # Should not change progress for invalid values
            self.assertEqual(task.progress, original_progress)
        
        # Test progress update with boundary values
        task.update_progress(0)
        self.assertEqual(task.progress, 0)
        self.assertEqual(task.status, TaskStatus.TODO)
        
        task.update_progress(100)
        self.assertEqual(task.progress, 100)
        self.assertEqual(task.status, TaskStatus.REVIEW)
    
    def test_task_subtask_progress_edge_cases(self):
        """Test task subtask progress edge cases"""
        # Test task with no subtasks
        task = Task.objects.create(title='No Subtasks Task', owner=self.user)
        self.assertEqual(task.subtask_progress, 0)
        
        # Test task with all completed subtasks
        subtask1 = Subtask.objects.create(title='Subtask 1', task=task)
        subtask2 = Subtask.objects.create(title='Subtask 2', task=task)
        
        subtask1.complete_subtask()
        subtask2.complete_subtask()
        
        self.assertEqual(task.subtask_progress, 100)
        
        # Test task with mixed progress subtasks
        task2 = Task.objects.create(title='Mixed Progress Task', owner=self.user)
        subtask3 = Subtask.objects.create(title='Subtask 3', task=task2)
        subtask4 = Subtask.objects.create(title='Subtask 4', task=task2)
        
        subtask3.complete_subtask()
        # subtask4 not completed
        
        self.assertEqual(task2.subtask_progress, 50)
    
    def test_task_overdue_edge_cases(self):
        """Test task overdue edge cases"""
        # Test task with no due date
        task = Task.objects.create(title='No Due Date Task', owner=self.user)
        self.assertFalse(task.is_overdue)
        
        # Test completed task with past due date
        completed_task = Task.objects.create(
            title='Completed Overdue Task',
            owner=self.user,
            due_date=timezone.now() - timedelta(days=1)
        )
        completed_task.complete_task()
        self.assertFalse(completed_task.is_overdue)  # Completed tasks are not overdue
        
        # Test task with due date exactly now
        now_task = Task.objects.create(
            title='Due Now Task',
            owner=self.user,
            due_date=timezone.now() + timedelta(seconds=1)  # Slightly in future to avoid timing issues
        )
        self.assertFalse(now_task.is_overdue)  # Due now is not overdue
    
    def test_task_with_extreme_values(self):
        """Test task with extreme field values"""
        # Test with maximum values
        max_task = Task.objects.create(
            title='A' * 255,  # Max title length
            description='A' * 10000,  # Very long description
            owner=self.user,
            priority=TaskPriority.URGENT,
            status=TaskStatus.BLOCKED,
            progress=100,
            estimated_hours=Decimal('999.99'),  # Max decimal places
            actual_hours=Decimal('999.99')
        )
        
        self.assertEqual(len(max_task.title), 255)
        self.assertEqual(len(max_task.description), 10000)
        self.assertEqual(max_task.priority, TaskPriority.URGENT)
        self.assertEqual(max_task.status, TaskStatus.BLOCKED)
        self.assertEqual(max_task.progress, 100)
        self.assertEqual(max_task.estimated_hours, Decimal('999.99'))
        self.assertEqual(max_task.actual_hours, Decimal('999.99'))
    
    def test_task_with_special_characters(self):
        """Test task with special characters"""
        special_task = Task.objects.create(
            title='Task with @#$%^&*() chars',
            description='Description with <script>alert("xss")</script>',
            owner=self.user
        )
        
        self.assertEqual(special_task.title, 'Task with @#$%^&*() chars')
        self.assertEqual(special_task.description, 'Description with <script>alert("xss")</script>')
    
    def test_task_with_sql_injection_attempts(self):
        """Test task with SQL injection attempt strings"""
        sql_task = Task.objects.create(
            title="'; DROP TABLE tasks; --",
            description="'; DELETE FROM tasks; --",
            owner=self.user
        )
        
        self.assertEqual(sql_task.title, "'; DROP TABLE tasks; --")
        self.assertEqual(sql_task.description, "'; DELETE FROM tasks; --")
    
    def test_task_with_html_tags(self):
        """Test task with HTML tags"""
        html_task = Task.objects.create(
            title='<b>Bold Task</b>',
            description='<p>Paragraph description</p>',
            owner=self.user
        )
        
        self.assertEqual(html_task.title, '<b>Bold Task</b>')
        self.assertEqual(html_task.description, '<p>Paragraph description</p>')
    
    def test_task_with_unicode_characters(self):
        """Test task with unicode characters"""
        unicode_task = Task.objects.create(
            title='任务标题',
            description='任务描述使用中文',
            owner=self.user
        )
        
        self.assertEqual(unicode_task.title, '任务标题')
        self.assertEqual(unicode_task.description, '任务描述使用中文')
    
    def test_task_with_numbers_in_text_fields(self):
        """Test task with numbers in text fields"""
        number_task = Task.objects.create(
            title='Task 123',
            description='Description with numbers 456 and 789',
            owner=self.user
        )
        
        self.assertEqual(number_task.title, 'Task 123')
        self.assertEqual(number_task.description, 'Description with numbers 456 and 789')
    
    def test_task_with_whitespace_only(self):
        """Test task with whitespace-only values"""
        whitespace_task = Task.objects.create(
            title='   ',
            description='\t\n',
            owner=self.user
        )
        
        self.assertEqual(whitespace_task.title, '   ')
        self.assertEqual(whitespace_task.description, '\t\n')
    
    def test_task_with_none_values(self):
        """Test task with None values for optional fields"""
        none_task = Task.objects.create(
            title='None Values Task',
            owner=self.user,
            description=None,
            due_date=None,
            due_reminder=None,
            assigned_to=None,
            parent=None,
            estimated_hours=None,
            actual_hours=None
        )
        
        self.assertIsNone(none_task.description)
        self.assertIsNone(none_task.due_date)
        self.assertIsNone(none_task.due_reminder)
        self.assertIsNone(none_task.assigned_to)
        self.assertIsNone(none_task.parent)
        self.assertIsNone(none_task.estimated_hours)
        self.assertIsNone(none_task.actual_hours)
