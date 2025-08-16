from django.test import TestCase, override_settings
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from apps.users.models import UserRole
import tempfile
import shutil
import os

# Import task models
from apps.tasks.models import Tag, Task, Subtask, Comment, Attachment, TaskPriority, TaskStatus

User = get_user_model()

class BaseTestCase(TestCase):
    """Base test case for model testing"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test',
            'last_name': 'User',
            'role': UserRole.USER,
        }
        
        self.admin_user_data = {
            'username': 'adminuser',
            'email': 'admin@example.com',
            'password': 'adminpass123',
            'name': 'Admin',
            'last_name': 'User',
            'role': UserRole.ADMIN,
            'is_staff': True,
            'is_superuser': True,
        }
        
        # Test media files setup
        self.test_media_root = tempfile.mkdtemp()
        
        # Task-specific test data
        self.tag_data = {
            'name': 'Test Tag',
            'color': '#ff0000',
            'description': 'A test tag'
        }
        
        self.task_data = {
            'title': 'Test Task',
            'description': 'A test task description',
            'priority': TaskPriority.MEDIUM,
            'status': TaskStatus.TODO,
        }
        
        self.subtask_data = {
            'title': 'Test Subtask',
            'description': 'A test subtask description',
            'priority': TaskPriority.HIGH,
        }
        
        self.comment_data = {
            'content': 'Test comment content',
            'is_internal': False,
        }
        
        self.attachment_data = {
            'original_filename': 'test_file.txt',
            'file_size': 1024,
            'file_type': 'TXT',
            'description': 'Test attachment',
            'is_public': True,
        }
        
        # Debug prints
        print(f"BaseTestCase.setUp() called")
        print(f"Available methods: {[m for m in dir(self) if m.startswith('create_')]}")
        print(f"tag_data: {self.tag_data}")
        print(f"task_data: {self.task_data}")
        print(f"subtask_data: {self.subtask_data}")
        print(f"comment_data: {self.comment_data}")
        print(f"attachment_data: {self.attachment_data}")
        
    def tearDown(self):
        """Clean up test data"""
        # Clean up test media files
        shutil.rmtree(self.test_media_root, ignore_errors=True)
    
    def create_user(self, **kwargs):
        """Helper method to create a test user"""
        user_data = self.user_data.copy()
        user_data.update(kwargs)
        
        # Make username unique if not provided
        if 'username' not in kwargs:
            import uuid
            user_data['username'] = f"testuser_{uuid.uuid4().hex[:8]}"
            user_data['email'] = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        return User.objects.create_user(**user_data)
    
    def create_admin_user(self, **kwargs):
        """Helper method to create a test admin user"""
        admin_data = self.admin_user_data.copy()
        admin_data.update(kwargs)
        return User.objects.create_user(**admin_data)
    
    # Task-related helper methods
    def create_tag(self, **kwargs):
        """Helper method to create a test tag"""
        print(f"create_tag() called with kwargs: {kwargs}")
        tag_data = self.tag_data.copy()
        tag_data.update(kwargs)
        print(f"Creating tag with data: {tag_data}")
        return Tag.objects.create(**tag_data)
    
    def create_task(self, owner=None, **kwargs):
        """Helper method to create a test task"""
        print(f"create_task() called with owner: {owner}, kwargs: {kwargs}")
        if owner is None:
            owner = self.create_user()
            print(f"Created default owner: {owner}")
        
        task_data = self.task_data.copy()
        task_data.update(kwargs)
        task_data['owner'] = owner
        print(f"Creating task with data: {task_data}")
        return Task.objects.create(**task_data)
    
    def create_subtask(self, task=None, **kwargs):
        """Helper method to create a test subtask"""
        print(f"create_subtask() called with task: {task}, kwargs: {kwargs}")
        if task is None:
            task = self.create_task()
            print(f"Created default task: {task}")
        
        subtask_data = self.subtask_data.copy()
        subtask_data.update(kwargs)
        subtask_data['task'] = task
        print(f"Creating subtask with data: {subtask_data}")
        return Subtask.objects.create(**subtask_data)
    
    def create_comment(self, author=None, task=None, subtask=None, **kwargs):
        """Helper method to create a test comment"""
        print(f"create_comment() called with author: {author}, task: {task}, subtask: {subtask}, kwargs: {kwargs}")
        if author is None:
            author = self.create_user()
            print(f"Created default author: {author}")
        
        comment_data = self.comment_data.copy()
        comment_data.update(kwargs)
        comment_data['author'] = author
        
        if task:
            comment_data['task'] = task
        elif subtask:
            comment_data['subtask'] = subtask
        else:
            # Create a default task if neither is provided
            comment_data['task'] = self.create_task(owner=author)
            print(f"Created default task for comment: {comment_data['task']}")
        
        print(f"Creating comment with data: {comment_data}")
        return Comment.objects.create(**comment_data)
    
    def create_attachment(self, uploaded_by=None, task=None, subtask=None, **kwargs):
        """Helper method to create a test attachment"""
        print(f"create_attachment() called with uploaded_by: {uploaded_by}, task: {task}, subtask: {subtask}, kwargs: {kwargs}")
        if uploaded_by is None:
            uploaded_by = self.create_user()
            print(f"Created default uploaded_by: {uploaded_by}")
        
        attachment_data = self.attachment_data.copy()
        attachment_data.update(kwargs)
        attachment_data['uploaded_by'] = uploaded_by
        
        if task:
            attachment_data['task'] = task
        elif subtask:
            attachment_data['subtask'] = subtask
        else:
            # Create a default task if neither is provided
            attachment_data['task'] = self.create_task(owner=uploaded_by)
            print(f"Created default task for attachment: {attachment_data['task']}")
        
        print(f"Creating attachment with data: {attachment_data}")
        return Attachment.objects.create(**attachment_data)
    
    def create_task_with_subtasks(self, owner=None, subtask_count=2, **kwargs):
        """Helper method to create a task with multiple subtasks"""
        print(f"create_task_with_subtasks() called with owner: {owner}, subtask_count: {subtask_count}, kwargs: {kwargs}")
        task = self.create_task(owner=owner, **kwargs)
        subtasks = []
        for i in range(subtask_count):
            subtask = self.create_subtask(task=task, title=f'Subtask {i+1}')
            subtasks.append(subtask)
        print(f"Created task with {len(subtasks)} subtasks")
        return task, subtasks
    
    def create_task_with_comments(self, owner=None, comment_count=3, **kwargs):
        """Helper method to create a task with multiple comments"""
        print(f"create_task_with_comments() called with owner: {owner}, comment_count: {comment_count}, kwargs: {kwargs}")
        task = self.create_task(owner=owner, **kwargs)
        comments = []
        for i in range(comment_count):
            comment = self.create_comment(task=task, content=f'Comment {i+1}')
            comments.append(comment)
        print(f"Created task with {len(comments)} comments")
        return task, comments
    
    def create_task_with_attachments(self, owner=None, attachment_count=2, **kwargs):
        """Helper method to create a task with multiple attachments"""
        print(f"create_task_with_attachments() called with owner: {owner}, attachment_count: {attachment_count}, kwargs: {kwargs}")
        task = self.create_task(owner=owner, **kwargs)
        attachments = []
        for i in range(attachment_count):
            attachment = self.create_attachment(
                task=task, 
                original_filename=f'test_file_{i+1}.txt'
            )
            attachments.append(attachment)
        print(f"Created task with {len(attachments)} attachments")
        return task, attachments

class BaseAPITestCase(APITestCase):
    """Base test case for API testing with enhanced functionality"""
    
    def setUp(self):
        """Set up test data and client"""
        super().setUp()
        
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'name': 'Test',
            'last_name': 'User',
            'role': UserRole.USER,
        }
        
        self.admin_user_data = {
            'username': 'adminuser',
            'email': 'admin@example.com',
            'password': 'adminpass123',
            'name': 'Admin',
            'last_name': 'User',
            'role': UserRole.ADMIN,
            'is_staff': True,
            'is_superuser': True,
        }
        
        # Test media files setup
        self.test_media_root = tempfile.mkdtemp()
        
        # Create test users
        self.user = self.create_user()
        self.admin_user = self.create_admin_user()
        
        # Get tokens for authenticated requests
        self.user_tokens = self.get_tokens_for_user(self.user)
        self.admin_tokens = self.get_tokens_for_user(self.admin_user)
    
    def tearDown(self):
        """Clean up test data"""
        # Clean up test media files
        shutil.rmtree(self.test_media_root, ignore_errors=True)
    
    def create_user(self, **kwargs):
        """Helper method to create a test user"""
        user_data = self.user_data.copy()
        user_data.update(kwargs)
        
        # Make username unique if not provided
        if 'username' not in kwargs:
            import uuid
            user_data['username'] = f"testuser_{uuid.uuid4().hex[:8]}"
            user_data['email'] = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        return User.objects.create_user(**user_data)
    
    def create_admin_user(self, **kwargs):
        """Helper method to create a test admin user"""
        admin_data = self.admin_user_data.copy()
        admin_data.update(kwargs)
        return User.objects.create_superuser(**admin_data)
    
    def get_tokens_for_user(self, user):
        """Helper method to get JWT tokens for a user"""
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    
    def authenticate_user(self, user=None):
        """Helper method to authenticate a user for requests"""
        if user is None:
            user = self.user
        tokens = self.get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        return tokens
    
    def authenticate_admin(self):
        """Helper method to authenticate as admin user"""
        return self.authenticate_user(self.admin_user)
    
    def create_verified_user(self, **kwargs):
        """Helper method to create a verified user"""
        user = self.create_user(**kwargs)
        user.is_verified = True
        user.save()
        return user
    
    def create_blocked_user(self, **kwargs):
        """Helper method to create a blocked user"""
        user = self.create_user(**kwargs)
        user.is_blocked = True
        user.save()
        return user
    
    def create_deleted_user(self, **kwargs):
        """Helper method to create a soft-deleted user"""
        user = self.create_user(**kwargs)
        user.is_deleted = True
        user.save()
        return user
    
    def create_user_with_email_token(self, **kwargs):
        """Helper method to create a user with email verification token"""
        user = self.create_user(**kwargs)
        user.generate_email_verification_token()
        user.save()
        return user
    
    def create_user_with_password_reset_token(self, **kwargs):
        """Helper method to create a user with password reset token"""
        user = self.create_user(**kwargs)
        user.generate_password_reset_token()
        user.save()
        return user
    
    def create_user_with_email_change_token(self, **kwargs):
        """Helper method to create a user with email change token"""
        user = self.create_user(**kwargs)
        user.generate_email_change_token()
        user.save()
        return user
    
    def create_user_with_expired_token(self, token_type='password_reset', **kwargs):
        """Helper method to create a user with expired token"""
        user = self.create_user(**kwargs)
        if token_type == 'password_reset':
            user.password_reset_token = '11111111-2222-3333-4444-555555555555'
            user.password_reset_token_expiration = timezone.now() - timezone.timedelta(hours=25)
        elif token_type == 'email_change':
            user.email_change_token = '22222222-3333-4444-5555-666666666666'
            user.email_change_token_expiration = timezone.now() - timezone.timedelta(hours=25)
        elif token_type == 'email_verification':
            user.email_verification_token = '33333333-4444-5555-6666-777777777777'
        user.save()
        return user
    
    # Task-related helper methods
    def create_tag(self, **kwargs):
        """Helper method to create a test tag"""
        tag_data = self.tag_data.copy()
        tag_data.update(kwargs)
        return Tag.objects.create(**tag_data)
    
    def create_task(self, owner=None, **kwargs):
        """Helper method to create a test task"""
        if owner is None:
            owner = self.create_user()
        
        task_data = self.task_data.copy()
        task_data.update(kwargs)
        task_data['owner'] = owner
        return Task.objects.create(**task_data)
    
    def create_subtask(self, task=None, **kwargs):
        """Helper method to create a test subtask"""
        if task is None:
            task = self.create_task()
        
        subtask_data = self.subtask_data.copy()
        subtask_data.update(kwargs)
        subtask_data['task'] = task
        return Subtask.objects.create(**subtask_data)
    
    def create_comment(self, author=None, task=None, subtask=None, **kwargs):
        """Helper method to create a test comment"""
        if author is None:
            author = self.create_user()
        
        comment_data = self.comment_data.copy()
        comment_data.update(kwargs)
        comment_data['author'] = author
        
        if task:
            comment_data['task'] = task
        elif subtask:
            comment_data['subtask'] = subtask
        else:
            # Create a default task if neither is provided
            comment_data['task'] = self.create_task(owner=author)
        
        return Comment.objects.create(**comment_data)
    
    def create_attachment(self, uploaded_by=None, task=None, subtask=None, **kwargs):
        """Helper method to create a test attachment"""
        if uploaded_by is None:
            uploaded_by = self.create_user()
        
        attachment_data = self.attachment_data.copy()
        attachment_data.update(kwargs)
        attachment_data['uploaded_by'] = uploaded_by
        
        if task:
            attachment_data['task'] = task
        elif subtask:
            attachment_data['subtask'] = subtask
        else:
            # Create a default task if neither is provided
            attachment_data['task'] = self.create_task(owner=uploaded_by)
        
        return Attachment.objects.create(**attachment_data)
    
    def create_task_with_subtasks(self, owner=None, subtask_count=2, **kwargs):
        """Helper method to create a task with multiple subtasks"""
        task = self.create_task(owner=owner, **kwargs)
        subtasks = []
        for i in range(subtask_count):
            subtask = self.create_subtask(task=task, title=f'Subtask {i+1}')
            subtasks.append(subtask)
        return task, subtasks
    
    def create_task_with_comments(self, owner=None, comment_count=3, **kwargs):
        """Helper method to create a task with multiple comments"""
        task = self.create_task(owner=owner, **kwargs)
        comments = []
        for i in range(comment_count):
            comment = self.create_comment(task=task, content=f'Comment {i+1}')
            comments.append(comment)
        return task, comments
    
    def create_task_with_attachments(self, owner=None, attachment_count=2, **kwargs):
        """Helper method to create a task with multiple attachments"""
        task = self.create_task(owner=owner, **kwargs)
        attachments = []
        for i in range(attachment_count):
            attachment = self.create_attachment(
                task=task, 
                original_filename=f'test_file_{i+1}.txt'
            )
            attachments.append(attachment)
        return task, attachments
    
    def assert_response_format(self, response, expected_status=status.HTTP_200_OK):
        """Helper method to assert standard API response format"""
        self.assertEqual(response.status_code, expected_status)
        self.assertIn('success', response.data)
        self.assertIn('data', response.data)
        self.assertIn('message', response.data)
        self.assertIn('timestamp', response.data)
    
    def assert_error_response(self, response, expected_status, error_code=None):
        """Helper method to assert error response format"""
        self.assertEqual(response.status_code, expected_status)
        self.assertIn('success', response.data)
        self.assertFalse(response.data['success'])
        self.assertIn('error', response.data)
        if error_code:
            self.assertEqual(response.data['error']['code'], error_code)
    
    def assert_pagination_format(self, response):
        """Helper method to assert pagination response format"""
        self.assert_response_format(response)
        self.assertIn('pagination', response.data['data'])
        pagination = response.data['data']['pagination']
        required_fields = ['page', 'per_page', 'total_pages', 'total_count', 
                          'has_next', 'has_previous']
        for field in required_fields:
            self.assertIn(field, pagination)




# Test media settings
TEST_MEDIA_SETTINGS = {
    'MEDIA_ROOT': tempfile.mkdtemp(),
    'MEDIA_URL': '/test-media/',
}
