from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from tests.base import BaseTestCase
from apps.tasks.models import Tag, Task, Subtask, Comment, Attachment, TaskPriority, TaskStatus


class TagModelTest(BaseTestCase):
    """Test cases for Tag model"""
    
    def test_tag_creation(self):
        """Test creating a tag"""
        tag = self.create_tag()
        
        self.assertEqual(tag.name, 'Test Tag')
        self.assertEqual(tag.color, '#ff0000')
        self.assertEqual(tag.description, 'A test tag')
        self.assertIsNotNone(tag.created_at)
        self.assertIsNotNone(tag.updated_at)
    
    def test_tag_string_representation(self):
        """Test tag string representation"""
        tag = self.create_tag()
        self.assertEqual(str(tag), 'Test Tag')
    
    def test_tag_ordering(self):
        """Test tag ordering by name"""
        self.create_tag(name='Zebra', color='#000000')
        self.create_tag(name='Alpha', color='#ffffff')
        self.create_tag(name='Beta', color='#cccccc')
        
        tags = Tag.objects.all().order_by('name')
        self.assertEqual(tags[0].name, 'Alpha')
        self.assertEqual(tags[1].name, 'Beta')
        self.assertEqual(tags[2].name, 'Zebra')
    
    def test_tag_with_custom_data(self):
        """Test creating tag with custom data"""
        custom_tag = self.create_tag(
            name='Custom Tag',
            color='#00ff00',
            description='Custom description'
        )
        
        self.assertEqual(custom_tag.name, 'Custom Tag')
        self.assertEqual(custom_tag.color, '#00ff00')
        self.assertEqual(custom_tag.description, 'Custom description')


class TaskModelTest(BaseTestCase):
    """Test cases for Task model"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.tag = self.create_tag()
        self.task = self.create_task(owner=self.user)
    
    def test_task_creation(self):
        """Test creating a task"""
        self.assertEqual(self.task.title, 'Test Task')
        self.assertEqual(self.task.description, 'A test task description')
        self.assertEqual(self.task.owner, self.user)
        self.assertEqual(self.task.priority, TaskPriority.MEDIUM)
        self.assertEqual(self.task.status, TaskStatus.TODO)
        self.assertFalse(self.task.completed)
        self.assertEqual(self.task.progress, 0)
        self.assertIsNotNone(self.task.created_at)
        self.assertIsNotNone(self.task.updated_at)
    
    def test_task_string_representation(self):
        """Test task string representation"""
        expected = f"Test Task ({self.task.get_status_display()})"
        self.assertEqual(str(self.task), expected)
    
    def test_task_with_tags(self):
        """Test adding tags to a task"""
        self.task.tags.add(self.tag)
        self.assertIn(self.tag, self.task.tags.all())
    
    def test_task_start_task(self):
        """Test starting a task"""
        self.assertEqual(self.task.status, TaskStatus.TODO)
        self.assertIsNone(self.task.started_at)
        
        self.task.start_task()
        
        self.assertEqual(self.task.status, TaskStatus.IN_PROGRESS)
        self.assertIsNotNone(self.task.started_at)
    
    def test_task_complete_task(self):
        """Test completing a task"""
        self.assertFalse(self.task.completed)
        self.assertEqual(self.task.progress, 0)
        self.assertIsNone(self.task.completed_at)
        
        self.task.complete_task()
        
        self.assertTrue(self.task.completed)
        self.assertEqual(self.task.progress, 100)
        self.assertEqual(self.task.status, TaskStatus.DONE)
        self.assertIsNotNone(self.task.completed_at)
    
    def test_task_cancel_task(self):
        """Test cancelling a task"""
        self.assertNotEqual(self.task.status, TaskStatus.CANCELLED)
        self.assertIsNone(self.task.cancelled_at)
        self.assertIsNone(self.task.cancelled_by)
        
        self.task.cancel_task(self.user)
        
        self.assertEqual(self.task.status, TaskStatus.CANCELLED)
        self.assertIsNotNone(self.task.cancelled_at)
        self.assertEqual(self.task.cancelled_by, self.user)
    
    def test_task_update_progress(self):
        """Test updating task progress"""
        self.assertEqual(self.task.progress, 0)
        self.assertEqual(self.task.status, TaskStatus.TODO)
        
        # Update to 50%
        self.task.update_progress(50)
        self.assertEqual(self.task.progress, 50)
        self.assertEqual(self.task.status, TaskStatus.IN_PROGRESS)
        
        # Update to 100%
        self.task.update_progress(100)
        self.assertEqual(self.task.progress, 100)
        self.assertEqual(self.task.status, TaskStatus.REVIEW)
    
    def test_task_is_overdue_property(self):
        """Test task overdue property"""
        # Task with no due date
        self.assertFalse(self.task.is_overdue)
        
        # Task with future due date
        self.task.due_date = timezone.now() + timedelta(days=1)
        self.task.save()
        self.assertFalse(self.task.is_overdue)
        
        # Task with past due date
        self.task.due_date = timezone.now() - timedelta(days=1)
        self.task.save()
        self.assertTrue(self.task.is_overdue)
        
        # Completed task should not be overdue
        self.task.complete_task()
        self.assertFalse(self.task.is_overdue)
    
    def test_task_has_subtasks_property(self):
        """Test task has_subtasks property"""
        self.assertFalse(self.task.has_subtasks)
        
        # Create a subtask
        self.create_subtask(task=self.task)
        
        self.assertTrue(self.task.has_subtasks)
    
    def test_task_subtask_progress_property(self):
        """Test task subtask_progress property"""
        # Task with no subtasks should return its own progress
        self.assertEqual(self.task.subtask_progress, 0)
        
        # Create subtasks
        self.create_subtask(task=self.task, completed=True)
        self.create_subtask(task=self.task, completed=False)
        
        # Should calculate based on subtasks (1 out of 2 completed = 50%)
        self.assertEqual(self.task.subtask_progress, 50)
    
    def test_task_with_custom_data(self):
        """Test creating task with custom data"""
        custom_task = self.create_task(
            title='Custom Task',
            description='Custom description',
            priority=TaskPriority.HIGH,
            status=TaskStatus.IN_PROGRESS,
            progress=75
        )
        
        self.assertEqual(custom_task.title, 'Custom Task')
        self.assertEqual(custom_task.description, 'Custom description')
        self.assertEqual(custom_task.priority, TaskPriority.HIGH)
        self.assertEqual(custom_task.status, TaskStatus.IN_PROGRESS)
        self.assertEqual(custom_task.progress, 75)


class SubtaskModelTest(BaseTestCase):
    """Test cases for Subtask model"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.task = self.create_task(owner=self.user)
        self.subtask = self.create_subtask(task=self.task)
    
    def test_subtask_creation(self):
        """Test creating a subtask"""
        self.assertEqual(self.subtask.title, 'Test Subtask')
        self.assertEqual(self.subtask.description, 'A test subtask description')
        self.assertEqual(self.subtask.task, self.task)
        self.assertEqual(self.subtask.priority, TaskPriority.HIGH)
        self.assertFalse(self.subtask.completed)
        self.assertEqual(self.subtask.progress, 0)
        self.assertIsNotNone(self.subtask.created_at)
        self.assertIsNotNone(self.subtask.updated_at)
    
    def test_subtask_string_representation(self):
        """Test subtask string representation"""
        expected = f"Test Subtask (Subtask of {self.task.title})"
        self.assertEqual(str(self.subtask), expected)
    
    def test_subtask_complete_subtask(self):
        """Test completing a subtask"""
        self.assertFalse(self.subtask.completed)
        self.assertEqual(self.subtask.progress, 0)
        self.assertIsNone(self.subtask.completed_at)
        
        self.subtask.complete_subtask()
        
        self.assertTrue(self.subtask.completed)
        self.assertEqual(self.subtask.progress, 100)
        self.assertIsNotNone(self.subtask.completed_at)
    
    def test_subtask_start_subtask(self):
        """Test starting a subtask"""
        self.assertIsNone(self.subtask.started_at)
        
        self.subtask.start_subtask()
        
        self.assertIsNotNone(self.subtask.started_at)
    
    def test_subtask_is_overdue_property(self):
        """Test subtask overdue property"""
        # Subtask with no due date
        self.assertFalse(self.subtask.is_overdue)
        
        # Subtask with future due date
        self.subtask.due_date = timezone.now() + timedelta(days=1)
        self.subtask.save()
        self.assertFalse(self.subtask.is_overdue)
        
        # Subtask with past due date
        self.subtask.due_date = timezone.now() - timedelta(days=1)
        self.subtask.save()
        self.assertTrue(self.subtask.is_overdue)
        
        # Completed subtask should not be overdue
        self.subtask.complete_subtask()
        self.assertFalse(self.subtask.is_overdue)
    
    def test_subtask_with_custom_data(self):
        """Test creating subtask with custom data"""
        custom_subtask = self.create_subtask(
            title='Custom Subtask',
            description='Custom description',
            priority=TaskPriority.URGENT,
            progress=50
        )
        
        self.assertEqual(custom_subtask.title, 'Custom Subtask')
        self.assertEqual(custom_subtask.description, 'Custom description')
        self.assertEqual(custom_subtask.priority, TaskPriority.URGENT)
        self.assertEqual(custom_subtask.progress, 50)


class CommentModelTest(BaseTestCase):
    """Test cases for Comment model"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.task = self.create_task(owner=self.user)
        self.comment = self.create_comment(author=self.user, task=self.task)
    
    def test_comment_creation(self):
        """Test creating a comment"""
        self.assertEqual(self.comment.content, 'Test comment content')
        self.assertEqual(self.comment.author, self.user)
        self.assertEqual(self.comment.task, self.task)
        self.assertFalse(self.comment.is_internal)
        self.assertFalse(self.comment.is_edited)
        self.assertIsNone(self.comment.edited_at)
        self.assertIsNotNone(self.comment.created_at)
        self.assertIsNotNone(self.comment.updated_at)
    
    def test_comment_string_representation(self):
        """Test comment string representation"""
        expected = f"Comment by {self.user.username} on {self.task.title}"
        self.assertEqual(str(self.comment), expected)
    
    def test_comment_edit_tracking(self):
        """Test comment edit tracking"""
        self.assertFalse(self.comment.is_edited)
        self.assertIsNone(self.comment.edited_at)
        
        # Update the comment
        self.comment.content = 'Updated comment'
        self.comment.save()
        
        self.assertTrue(self.comment.is_edited)
        self.assertIsNotNone(self.comment.edited_at)
    
    def test_comment_with_subtask(self):
        """Test comment on subtask"""
        subtask = self.create_subtask(task=self.task)
        
        comment = self.create_comment(author=self.user, subtask=subtask)
        
        self.assertEqual(comment.subtask, subtask)
        self.assertIsNone(comment.task)
    
    def test_comment_replies(self):
        """Test comment replies"""
        reply = self.create_comment(
            author=self.user,
            task=self.task,
            content='Reply to comment'
        )
        reply.parent_comment = self.comment
        reply.save()
        
        self.assertEqual(reply.parent_comment, self.comment)
        self.assertIn(reply, self.comment.replies.all())
    
    def test_comment_with_custom_data(self):
        """Test creating comment with custom data"""
        custom_comment = self.create_comment(
            content='Custom comment content',
            is_internal=True
        )
        
        self.assertEqual(custom_comment.content, 'Custom comment content')
        self.assertTrue(custom_comment.is_internal)


class AttachmentModelTest(BaseTestCase):
    """Test cases for Attachment model"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.task = self.create_task(owner=self.user)
    
    def test_attachment_creation(self):
        """Test creating an attachment"""
        attachment = self.create_attachment(uploaded_by=self.user, task=self.task)
        
        self.assertEqual(attachment.uploaded_by, self.user)
        self.assertEqual(attachment.task, self.task)
        self.assertEqual(attachment.original_filename, 'test_file.txt')
        self.assertEqual(attachment.file_size, 1024)
        self.assertEqual(attachment.file_type, 'TXT')
        self.assertEqual(attachment.description, 'Test attachment')
        self.assertTrue(attachment.is_public)
        self.assertIsNotNone(attachment.created_at)
        self.assertIsNotNone(attachment.updated_at)
    
    def test_attachment_string_representation(self):
        """Test attachment string representation"""
        attachment = self.create_attachment(uploaded_by=self.user, task=self.task)
        
        expected = f"test_file.txt on {self.task.title}"
        self.assertEqual(str(attachment), expected)
    
    def test_attachment_with_subtask(self):
        """Test attachment on subtask"""
        subtask = self.create_subtask(task=self.task)
        
        attachment = self.create_attachment(
            uploaded_by=self.user,
            subtask=subtask,
            original_filename='subtask.txt'
        )
        
        self.assertEqual(attachment.subtask, subtask)
        self.assertIsNone(attachment.task)
    
    def test_attachment_with_custom_data(self):
        """Test creating attachment with custom data"""
        custom_attachment = self.create_attachment(
            original_filename='custom_file.pdf',
            file_size=2048,
            file_type='PDF',
            description='Custom attachment',
            is_public=False
        )
        
        self.assertEqual(custom_attachment.original_filename, 'custom_file.pdf')
        self.assertEqual(custom_attachment.file_size, 2048)
        self.assertEqual(custom_attachment.file_type, 'PDF')
        self.assertEqual(custom_attachment.description, 'Custom attachment')
        self.assertFalse(custom_attachment.is_public)


class TaskPriorityTest(BaseTestCase):
    """Test cases for TaskPriority choices"""
    
    def test_task_priority_choices(self):
        """Test task priority choices"""
        priorities = [choice[0] for choice in TaskPriority.choices]
        expected_priorities = ['LOW', 'MEDIUM', 'HIGH', 'URGENT']
        
        self.assertEqual(priorities, expected_priorities)
    
    def test_task_priority_labels(self):
        """Test task priority labels"""
        priority_labels = [choice[1] for choice in TaskPriority.choices]
        expected_labels = ['Low', 'Medium', 'High', 'Urgent']
        
        self.assertEqual(priority_labels, expected_labels)


class TaskStatusTest(BaseTestCase):
    """Test cases for TaskStatus choices"""
    
    def test_task_status_choices(self):
        """Test task status choices"""
        statuses = [choice[0] for choice in TaskStatus.choices]
        expected_statuses = ['TODO', 'IN_PROGRESS', 'REVIEW', 'DONE', 'BLOCKED', 'CANCELLED']
        
        self.assertEqual(statuses, expected_statuses)
    
    def test_task_status_labels(self):
        """Test task status labels"""
        status_labels = [choice[1] for choice in TaskStatus.choices]
        expected_labels = ['To Do', 'In Progress', 'Under Review', 'Done', 'Blocked', 'Cancelled']
        
        self.assertEqual(status_labels, expected_labels)


class TaskRelationshipsTest(BaseTestCase):
    """Test cases for task relationships and complex scenarios"""
    
    def test_task_with_multiple_subtasks(self):
        """Test task with multiple subtasks"""
        task, subtasks = self.create_task_with_subtasks(subtask_count=3)
        
        self.assertEqual(task.subtasks.count(), 3)
        self.assertEqual(task.has_subtasks, True)
        
        # Complete one subtask
        subtasks[0].complete_subtask()
        self.assertEqual(task.subtask_progress, 33)  # 1 out of 3 completed
    
    def test_task_with_comments_and_attachments(self):
        """Test task with comments and attachments"""
        # Create one task and add both comments and attachments to it
        task = self.create_task()
        
        # Add comments to the task
        comment1 = self.create_comment(task=task, content='Comment 1')
        comment2 = self.create_comment(task=task, content='Comment 2')
        
        # Add attachments to the task
        attachment1 = self.create_attachment(task=task, original_filename='file1.txt')
        attachment2 = self.create_attachment(task=task, original_filename='file2.txt')
        
        self.assertEqual(task.comments.count(), 2)
        self.assertEqual(task.attachments.count(), 2)
    
    def test_task_cascade_operations(self):
        """Test cascade operations when task is deleted"""
        task = self.create_task()
        subtask = self.create_subtask(task=task)
        comment = self.create_comment(task=task)
        attachment = self.create_attachment(task=task)
        
        # Delete the task
        task.delete()
        
        # Check that related objects are also deleted
        self.assertFalse(Subtask.objects.filter(id=subtask.id).exists())
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())
        self.assertFalse(Attachment.objects.filter(id=attachment.id).exists())
