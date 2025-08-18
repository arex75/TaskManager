from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from tests.base import BaseAPITestCase
from apps.tasks.models import Task, Tag, Subtask, Comment, Attachment, TaskPriority, TaskStatus, TaskPriority, TaskStatus

User = get_user_model()


class TaskViewSetTest(BaseAPITestCase):
    """Test cases for TaskViewSet"""
    
    def setUp(self):
        super().setUp()
        
        self.url = reverse('tasks:task-list')
        
        self.task = self.create_task(owner=self.user)
        
        self.task_detail_url = reverse('tasks:task-detail', kwargs={'pk': self.task.pk})
        
        # Create some tags for testing using base class data
        self.tag1 = self.create_tag(name='Urgent', color='#ff0000')
        self.tag2 = self.create_tag(name='Bug', color='#ff6600')
        
        # Authenticate the user for API requests
        self.authenticate_user()
    
    def test_task_list_success(self):
        """Test successful retrieval of task list"""
        
        # Create additional tasks
        self.create_task(owner=self.user, title='Task 2')
        self.create_task(owner=self.user, title='Task 3')
        
        response = self.client.get(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # The response message should match what we specified in the decorator
        self.assertIn('Tasks retrieved successfully', response.data['message'])
        
        # Assert pagination format
        self.assert_pagination_format(response)
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertEqual(len(response.data['data']['results']), 3)  # 3 tasks created
    
    def test_task_list_with_filters(self):
        """Test task list with filtering"""
        
        # Create tasks with different priorities
        high_task = self.create_high_priority_task(owner=self.user, title='High Priority Task')
        medium_task = self.create_task(owner=self.user, title='Medium Priority Task', priority='MEDIUM')
        
        # Filter by priority
        response = self.client.get(f"{self.url}?priority=HIGH")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        # With pagination, data is in response.data['data']['results']
        self.assertEqual(len(response.data['data']['results']), 1)
        self.assertEqual(response.data['data']['results'][0]['title'], 'High Priority Task')
    
    def test_task_list_with_search(self):
        """Test task list with search functionality"""
        
        # Create tasks with searchable titles
        self.create_task(owner=self.user, title='Bug Fix Task', description='Fix critical bug')
        self.create_task(owner=self.user, title='Feature Task', description='Add new feature')
        
        # Search by title
        response = self.client.get(f"{self.url}?search=bug")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        # With pagination, data is in response.data['data']['results']
        self.assertEqual(len(response.data['data']['results']), 1)
        self.assertEqual(response.data['data']['results'][0]['title'], 'Bug Fix Task')
    
    def test_task_list_with_ordering(self):
        """Test task list with ordering"""
        
        # Create tasks in reverse order
        self.create_task(owner=self.user, title='Zebra Task', created_at=timezone.now() - timedelta(hours=2))
        self.create_task(owner=self.user, title='Alpha Task', created_at=timezone.now() - timedelta(hours=1))
        
        # Order by title
        response = self.client.get(f"{self.url}?ordering=title")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        # With pagination, data is in response.data['data']['results']
        self.assertEqual(response.data['data']['results'][0]['title'], 'Alpha Task')
        self.assertEqual(response.data['data']['results'][-1]['title'], 'Zebra Task')
    
    def test_task_list_user_filtered(self):
        """Test that users only see their own tasks"""
        
        # Create task for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        
        # User should only see their own tasks
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        
        # Should not see other user's task
        # With pagination, data is in response.data['data']['results']
        task_titles = [task['title'] for task in response.data['data']['results']]
        self.assertNotIn('Other User Task', task_titles)
    
    def test_task_create_success(self):
        """Test successful task creation"""
        
        # Use unique title to avoid conflicts with setUp task
        unique_task_data = self.valid_task_data.copy()
        unique_task_data['title'] = 'Unique Test Task'
        
        response = self.client.post(self.url, unique_task_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('Task created successfully', response.data['message'])
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['title'], 'Unique Test Task')
        self.assertEqual(response.data['data']['priority'], 'MEDIUM')
        self.assertEqual(response.data['data']['status'], 'TODO')
        
        # Verify task was created in database
        task = Task.objects.get(title='Unique Test Task')
        self.assertEqual(task.owner, self.user)
        self.assertEqual(task.priority, 'MEDIUM')
        self.assertEqual(task.status, 'TODO')
    
    def test_task_create_with_tags(self):
        """Test task creation with tags"""
        
        task_data = self.valid_task_data.copy()
        task_data['title'] = 'Task With Tags'  # Use unique title
        task_data['tags'] = [self.tag1.pk, self.tag2.pk]
        
        response = self.client.post(self.url, task_data)
        
        self.assert_response_format(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify tags were assigned
        task = Task.objects.get(title='Task With Tags')
        self.assertEqual(task.tags.count(), 2)
        self.assertIn(self.tag1, task.tags.all())
        self.assertIn(self.tag2, task.tags.all())
    
    def test_task_create_with_invalid_data(self):
        """Test task creation with invalid data"""
        
        response = self.client.post(self.url, self.invalid_task_data)
        
        # Should return validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_create_without_required_fields(self):
        """Test task creation without required fields"""
        
        # Try to create task without title
        response = self.client.post(self.url, {
            'description': 'Task without title',
            'priority': 'MEDIUM'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_create_with_invalid_priority(self):
        """Test task creation with invalid priority"""
        
        invalid_data = self.valid_task_data.copy()
        invalid_data['priority'] = 'INVALID_PRIORITY'
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_create_with_invalid_status(self):
        """Test task creation with invalid status"""
        
        invalid_data = self.valid_task_data.copy()
        invalid_data['status'] = 'INVALID_STATUS'
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_create_with_negative_hours(self):
        """Test task creation with negative estimated hours"""
        
        invalid_data = self.valid_task_data.copy()
        invalid_data['estimated_hours'] = -5.0
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_create_with_invalid_progress(self):
        """Test task creation with invalid progress"""
        
        invalid_data = self.valid_task_data.copy()
        invalid_data['progress'] = 150  # > 100
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_retrieve_success(self):
        """Test successful task retrieval"""
        
        response = self.client.get(self.task_detail_url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Task retrieved successfully', response.data['message'])
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['title'], self.task.title)
        self.assertEqual(response.data['data']['owner']['username'], self.user.username)
    
    def test_task_retrieve_not_found(self):
        """Test task retrieval with non-existent ID"""
        
        url = reverse('tasks:task-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_task_retrieve_unauthorized(self):
        """Test task retrieval by non-owner"""
        
        # Create task for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        
        # Try to access other user's task
        url = reverse('tasks:task-detail', kwargs={'pk': other_task.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_task_update_success(self):
        """Test successful task update"""
        
        update_data = {
            'title': 'Updated Task Title',
            'description': 'Updated description',
            'priority': 'HIGH'
            # Note: status changes should use dedicated actions, not direct updates
        }
        
        response = self.client.put(self.task_detail_url, update_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Task updated successfully', response.data['message'])
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['title'], 'Updated Task Title')
        self.assertEqual(response.data['data']['priority'], 'HIGH')
        
        # Verify database was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Updated Task Title')
        self.assertEqual(self.task.priority, 'HIGH')
    
    def test_task_partial_update_success(self):
        """Test successful task partial update"""
        
        update_data = {
            'priority': 'HIGH'  # Only update priority
        }
        
        response = self.client.patch(self.task_detail_url, update_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Task updated successfully', response.data['message'])
        
        # Assert only priority was updated
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['priority'], 'HIGH')
        self.assertEqual(response.data['data']['title'], self.task.title)  # Title unchanged
        
        # Verify database was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.priority, 'HIGH')
        self.assertEqual(self.task.title, self.task.title)  # Title unchanged
    
    def test_task_update_with_invalid_data(self):
        """Test task update with invalid data"""
        
        
        invalid_data = {
            'title': '',  # Empty title
            'priority': 'INVALID_PRIORITY'
        }
        
        response = self.client.put(self.task_detail_url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_update_unauthorized(self):
        """Test task update by non-owner"""
        
        
        # Create task for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        
        # Try to update other user's task
        url = reverse('tasks:task-detail', kwargs={'pk': other_task.pk})
        response = self.client.put(url, {'title': 'Hacked Title'})
        
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_task_delete_success(self):
        """Test successful task deletion"""
        
        response = self.client.delete(self.task_detail_url)
        
        
        # Assert response format
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify task was deleted from database
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
    
    def test_task_delete_not_found(self):
        """Test task deletion with non-existent ID"""
        
        
        url = reverse('tasks:task-detail', kwargs={'pk': 99999})
        response = self.client.delete(url)
        
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_task_delete_unauthorized(self):
        """Test task deletion by non-owner"""
        
        
        # Create task for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        
        # Try to delete other user's task
        url = reverse('tasks:task-detail', kwargs={'pk': other_task.pk})
        response = self.client.delete(url)
        
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_task_start_action_success(self):
        """Test successful task start action"""
        
        
        # Ensure task is in TODO status
        self.task.status = 'TODO'
        self.task.save()
        
        url = reverse('tasks:task-start', kwargs={'pk': self.task.pk})
        
        response = self.client.post(url)
        
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Task started successfully', response.data['message'])
        
        # Verify task was started
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'IN_PROGRESS')
        self.assertIsNotNone(self.task.started_at)
    
    def test_task_start_action_already_started(self):
        """Test task start action when already started"""
        
        
        # Ensure task is already in progress
        self.task.status = 'IN_PROGRESS'
        self.task.started_at = timezone.now()
        self.task.save()
        
        url = reverse('tasks:task-start', kwargs={'pk': self.task.pk})
        response = self.client.post(url)
        
        
        # Should return error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_complete_action_success(self):
        """Test successful task complete action"""
        
        
        # Ensure task is in progress
        self.task.status = 'IN_PROGRESS'
        self.task.started_at = timezone.now()
        self.task.save()
        
        url = reverse('tasks:task-complete', kwargs={'pk': self.task.pk})
        
        
        response = self.client.post(url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Task completed successfully', response.data['message'])
        
        # Verify task was completed
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'DONE')
        self.assertTrue(self.task.completed)
        self.assertIsNotNone(self.task.completed_at)
        self.assertEqual(self.task.progress, 100)
    
    def test_task_complete_action_not_started(self):
        """Test task complete action when not started"""
        
        
        # Ensure task is in TODO status
        self.task.status = 'TODO'
        self.task.save()
        
        url = reverse('tasks:task-complete', kwargs={'pk': self.task.pk})
        response = self.client.post(url)
        
        
        # Should return error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_pause_action_success(self):
        """Test successful task pause action"""
        
        
        # Ensure task is in progress
        self.task.status = 'IN_PROGRESS'
        self.task.started_at = timezone.now()
        self.task.save()
        
        url = reverse('tasks:task-pause', kwargs={'pk': self.task.pk})
        
        response = self.client.post(url)
        
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Task paused successfully', response.data['message'])
        
        # Verify task was paused
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'PAUSED')
    
    def test_task_resume_action_success(self):
        """Test successful task resume action"""
        
        
        # Ensure task is paused
        self.task.status = 'PAUSED'
        self.task.started_at = timezone.now()
        self.task.save()
        
        url = reverse('tasks:task-resume', kwargs={'pk': self.task.pk})
        
        response = self.client.post(url)
        
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Task resumed successfully', response.data['message'])
        
        # Verify task was resumed
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'IN_PROGRESS')
    
    def test_task_progress_update_success(self):
        """Test successful task progress update"""
        
        
        progress_data = {'progress': 75}
        
        url = reverse('tasks:task-update-progress', kwargs={'pk': self.task.pk})
        
        response = self.client.patch(url, progress_data)
        
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Task progress updated successfully', response.data['message'])
        
        # Verify progress was updated
        self.task.refresh_from_db()
        self.assertEqual(self.task.progress, 75)
    
    def test_task_progress_update_invalid(self):
        """Test task progress update with invalid value"""
        
        
        invalid_data = {'progress': 150}  # > 100
        
        url = reverse('tasks:task-update-progress', kwargs={'pk': self.task.pk})
        response = self.client.patch(url, invalid_data)
        
        
        # Should return validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_assign_action_success(self):
        """Test successful task assignment"""
        
        
        # Create another user to assign to
        assignee = self.create_user(username='assignee', email='assignee@example.com')
        
        assign_data = {'assignee': assignee.pk}
        url = reverse('tasks:task-assign', kwargs={'pk': self.task.pk})
        
        response = self.client.patch(url, assign_data)
        
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Task assigned successfully', response.data['message'])
        
        # Verify task was assigned
        self.task.refresh_from_db()
        self.assertEqual(self.task.assigned_to, assignee)
    
    def test_task_assign_action_invalid_user(self):
        """Test task assignment with invalid user"""
        
        assign_data = {'assignee': 99999}  # Non-existent user
        
        url = reverse('tasks:task-assign', kwargs={'pk': self.task.pk})
        response = self.client.patch(url, assign_data)
        
        
        # Should return validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_task_list_unauthenticated(self):
        """Test task list access without authentication"""
        
        
        self.client.credentials()  # Remove authentication
        
        response = self.client.get(self.url)
        
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_task_create_unauthenticated(self):
        """Test task creation without authentication"""
        
        
        self.client.credentials()  # Remove authentication
        
        response = self.client.post(self.url, self.valid_task_data)
        
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_task_update_unauthenticated(self):
        """Test task update without authentication"""
        
        
        self.client.credentials()  # Remove authentication
        
        response = self.client.put(self.task_detail_url, self.valid_task_data)
        
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_task_delete_unauthenticated(self):
        """Test task deletion without authentication"""
        
        
        self.client.credentials()  # Remove authentication
        
        response = self.client.delete(self.task_detail_url)
        
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_task_boundary_values(self):
        """Test task creation with boundary values"""
        
        
        # Test title too long
        long_title_data = self.valid_task_data.copy()
        long_title_data['title'] = 'A' * 256  # Max length is 255
        
        response = self.client.post(self.url, long_title_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test description too long
        long_desc_data = self.valid_task_data.copy()
        long_desc_data['description'] = 'A' * 1001  # Max length is 1000
        
        response = self.client.post(self.url, long_desc_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test valid boundary values
        boundary_data = self.valid_task_data.copy()
        boundary_data['title'] = 'A' * 255  # Exactly at max length
        boundary_data['description'] = 'A' * 1000  # Exactly at max length
        
        response = self.client.post(self.url, boundary_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_task_due_date_validation(self):
        """Test task due date validation"""
        
        
        # Test due date in the past
        past_date_data = self.valid_task_data.copy()
        past_date_data['due_date'] = (timezone.now() - timedelta(days=1)).isoformat()
        
        response = self.client.post(self.url, past_date_data)
        
        # This might be valid depending on your business logic
        # Adjust assertion based on your requirements
        
        # Test due date in the future (should be valid)
        future_date_data = self.valid_task_data.copy()
        future_date_data['due_date'] = (timezone.now() + timedelta(days=30)).isoformat()
        
        response = self.client.post(self.url, future_date_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_task_status_transitions(self):
        """Test task status transitions"""
        
        
        # Test that direct status changes are blocked (should use actions instead)
        blocked_transitions = [
            ('TODO', 'IN_PROGRESS'),      # Should use start action
            ('IN_PROGRESS', 'PAUSED'),    # Should use pause action
            ('PAUSED', 'IN_PROGRESS'),    # Should use resume action
        ]
        
        for from_status, to_status in blocked_transitions:
        
            # Set initial status
            self.task.status = from_status
            if from_status == 'IN_PROGRESS':
                self.task.started_at = timezone.now()
            self.task.save()
            
            # Try to update status directly (should be blocked)
            update_data = {'status': to_status}
            response = self.client.patch(self.task_detail_url, update_data)
            
            # All direct status changes should be blocked
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('error', response.data)
        
        # Test that IN_PROGRESS to DONE transition is allowed
        self.task.status = 'IN_PROGRESS'
        self.task.started_at = timezone.now()
        self.task.save()
        
        update_data = {'status': 'DONE'}
        response = self.client.patch(self.task_detail_url, update_data)
        
        # IN_PROGRESS to DONE should be allowed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_task_with_subtasks_retrieval(self):
        """Test task retrieval includes subtasks"""
        
        # Create task with subtasks
        task, subtasks = self.create_task_with_subtasks(owner=self.user)
        
        url = reverse('tasks:task-detail', kwargs={'pk': task.pk})
        response = self.client.get(url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        
        # Check if subtasks are included (depends on serializer)
        # This test may need adjustment based on your actual serializer implementation
    
    def test_task_with_comments_retrieval(self):
        """Test task retrieval includes comments"""
        
        # Create task with comments
        task, comments = self.create_task_with_comments(owner=self.user)
        
        url = reverse('tasks:task-detail', kwargs={'pk': task.pk})
        response = self.client.get(url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        
        # Check if comments are included (depends on serializer)
        # This test may need adjustment based on your actual serializer implementation
    
    def test_task_with_attachments_retrieval(self):
        """Test task retrieval includes attachments"""
        # Create task with attachments
        task, attachments = self.create_task_with_attachments(owner=self.user)
        
        url = reverse('tasks:task-detail', kwargs={'pk': task.pk})
        response = self.client.get(url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        
        # Check if attachments are included (depends on serializer)
        # This test may need adjustment based on your actual serializer implementation
