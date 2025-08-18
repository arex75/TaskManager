from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from tests.base import BaseAPITestCase
from apps.tasks.models import Task, Tag, Subtask, Comment, Attachment

User = get_user_model()


class DashboardViewSetTest(BaseAPITestCase):
    """Test cases for DashboardViewSet"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('tasks:dashboard-list')
        
        # Authenticate the user for API requests
        self.authenticate_user()
        
        # Create comprehensive dashboard test data
        self.dashboard_data = self.create_dashboard_data(user=self.user)
        
        # Extract components for easier testing
        self.tasks = self.dashboard_data['tasks']
        self.tags = self.dashboard_data['tags']
        self.subtasks = self.dashboard_data['subtasks']
        self.comments = self.dashboard_data['comments']
        self.attachments = self.dashboard_data['attachments']
    
    def test_dashboard_overview_success(self):
        """Test successful dashboard overview retrieval"""
        response = self.client.get(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Dashboard overview retrieved successfully', response.data['message'])
        
        # Assert data content
        self.assertIn('data', response.data)
        dashboard_data = response.data['data']
        
        # Check that all expected sections are present
        expected_sections = ['tasks', 'tags', 'subtasks', 'comments', 'attachments']
        for section in expected_sections:
            self.assertIn(section, dashboard_data)
    
    def test_dashboard_overview_empty(self):
        """Test dashboard overview when no data exists"""
        # Delete all existing data
        Task.objects.all().delete()
        Tag.objects.all().delete()
        Subtask.objects.all().delete()
        Comment.objects.all().delete()
        Attachment.objects.all().delete()
        
        response = self.client.get(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert empty data
        self.assertIn('data', response.data)
        dashboard_data = response.data['data']
        
        # All sections should be empty
        for section in ['tasks', 'tags', 'subtasks', 'comments', 'attachments']:
            self.assertIn(section, dashboard_data)
            self.assertEqual(len(dashboard_data[section]), 0)
    
    def test_dashboard_tasks_summary(self):
        """Test dashboard tasks summary"""
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Check tasks section
        self.assertIn('tasks', dashboard_data)
        tasks_data = dashboard_data['tasks']
        
        # Should have tasks in different statuses
        task_statuses = [task['status'] for task in tasks_data]
        self.assertIn('TODO', task_statuses)
        self.assertIn('IN_PROGRESS', task_statuses)
        self.assertIn('COMPLETED', task_statuses)
    
    def test_dashboard_tags_summary(self):
        """Test dashboard tags summary"""
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Check tags section
        self.assertIn('tags', dashboard_data)
        tags_data = dashboard_data['tags']
        
        # Should have tags with different colors
        self.assertGreater(len(tags_data), 0)
        for tag in tags_data:
            self.assertIn('name', tag)
            self.assertIn('color', tag)
    
    def test_dashboard_subtasks_summary(self):
        """Test dashboard subtasks summary"""
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Check subtasks section
        self.assertIn('subtasks', dashboard_data)
        subtasks_data = dashboard_data['subtasks']
        
        # Should have subtasks
        self.assertGreater(len(subtasks_data), 0)
        for subtask in subtasks_data:
            self.assertIn('title', subtask)
            self.assertIn('status', subtask)
    
    def test_dashboard_comments_summary(self):
        """Test dashboard comments summary"""
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Check comments section
        self.assertIn('comments', dashboard_data)
        comments_data = dashboard_data['comments']
        
        # Should have comments with proper structure
        for comment in comments_data:
            self.assertIn('author_id', comment)
            self.assertIn('task_id', comment)
            self.assertIn('content', comment)
            self.assertIn('is_internal', comment)
    
    def test_dashboard_attachments_summary(self):
        """Test dashboard attachments summary"""
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Check attachments section
        self.assertIn('attachments', dashboard_data)
        attachments_data = dashboard_data['attachments']
        
        # Should have attachments with proper structure
        for attachment in attachments_data:
            self.assertIn('uploaded_by_id', attachment)
            self.assertIn('task_id', attachment)
            self.assertIn('original_filename', attachment)
            self.assertIn('file_type', attachment)
    
    def test_dashboard_user_filtered(self):
        """Test that dashboard only shows user's own data"""
        # Create data for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_tag = self.create_tag(name='Other User Tag', color='#000000')
        
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Should not see other user's data
        task_titles = [task['title'] for task in dashboard_data['tasks']]
        tag_names = [tag['name'] for tag in dashboard_data['tags']]
        
        self.assertNotIn('Other User Task', task_titles)
        self.assertNotIn('Other User Tag', tag_names)
    
    def test_dashboard_task_statistics(self):
        """Test dashboard task statistics"""
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Check if statistics are included (depends on serializer implementation)
        # This test may need adjustment based on your actual serializer
        if 'statistics' in dashboard_data:
            stats = dashboard_data['statistics']
            self.assertIn('total_tasks', stats)
            self.assertIn('completed_tasks', stats)
            self.assertIn('in_progress_tasks', stats)
            self.assertIn('overdue_tasks', stats)
    
    def test_dashboard_recent_activity(self):
        """Test dashboard recent activity"""
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Check if recent activity is included (depends on serializer implementation)
        # This test may need adjustment based on your actual serializer
        if 'recent_activity' in dashboard_data:
            activity = dashboard_data['recent_activity']
            self.assertIsInstance(activity, list)
    
    def test_dashboard_performance_metrics(self):
        """Test dashboard performance metrics"""
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Check if performance metrics are included (depends on serializer implementation)
        # This test may need adjustment based on your actual serializer
        if 'performance_metrics' in dashboard_data:
            metrics = dashboard_data['performance_metrics']
            self.assertIn('completion_rate', metrics)
            self.assertIn('average_completion_time', metrics)
    
    def test_dashboard_list_unauthenticated(self):
        """Test dashboard access without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_dashboard_data_integrity(self):
        """Test that dashboard data maintains referential integrity"""
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Check that tasks have proper structure
        for task in dashboard_data['tasks']:
            self.assertIn('owner_id', task)
            self.assertIn('title', task)
            self.assertIn('status', task)
            self.assertIn('priority', task)
        
        # Check that subtasks reference valid tasks
        task_ids = {task['id'] for task in dashboard_data['tasks']}
        for subtask in dashboard_data['subtasks']:
            self.assertIn('task_id', subtask)
            self.assertIn(subtask['task_id'], task_ids)
        
        # Check that comments reference valid tasks
        for comment in dashboard_data['comments']:
            self.assertIn('task_id', comment)
            self.assertIn(comment['task_id'], task_ids)
        
        # Check that attachments reference valid tasks
        for attachment in dashboard_data['attachments']:
            self.assertIn('task_id', attachment)
            self.assertIn(attachment['task_id'], task_ids)
    
    def test_dashboard_pagination(self):
        """Test dashboard pagination if implemented"""
        # Create many more items to test pagination
        for i in range(25):  # Create 25 more tasks
            self.create_task(owner=self.user, title=f'Task {i}')
        
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Check if pagination is implemented
        # This test may need adjustment based on your actual pagination implementation
        if 'pagination' in response.data['data']:
            pagination = response.data['data']['pagination']
            self.assertIn('page', pagination)
            self.assertIn('per_page', pagination)
            self.assertIn('total_count', pagination)
    
    def test_dashboard_filtering(self):
        """Test dashboard filtering if implemented"""
        # Test filtering by date range
        response = self.client.get(f"{self.url}?date_from={timezone.now().date()}")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Test filtering by status
        response = self.client.get(f"{self.url}?status=TODO")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Test filtering by priority
        response = self.client.get(f"{self.url}?priority=HIGH")
        
        self.assert_response_format(response, status.HTTP_200_OK)
    
    def test_dashboard_ordering(self):
        """Test dashboard ordering if implemented"""
        # Test ordering by creation date
        response = self.client.get(f"{self.url}?ordering=created_at")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Test ordering by title
        response = self.client.get(f"{self.url}?ordering=title")
        
        self.assert_response_format(response, status.HTTP_200_OK)
    
    def test_dashboard_search(self):
        """Test dashboard search if implemented"""
        # Test search functionality
        response = self.client.get(f"{self.url}?search=urgent")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Test search with no results
        response = self.client.get(f"{self.url}?search=nonexistent")
        
        self.assert_response_format(response, status.HTTP_200_OK)
    
    def test_dashboard_caching(self):
        """Test dashboard caching if implemented"""
        # First request
        response1 = self.client.get(self.url)
        self.assert_response_format(response1, status.HTTP_200_OK)
        
        # Second request (should be cached if caching is implemented)
        response2 = self.client.get(self.url)
        self.assert_response_format(response2, status.HTTP_200_OK)
        
        # Both responses should be identical if caching is working
        # This test may need adjustment based on your actual caching implementation
    
    def test_dashboard_error_handling(self):
        """Test dashboard error handling"""
        # Test with invalid parameters
        response = self.client.get(f"{self.url}?invalid_param=value")
        
        # Should still return a valid response
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Test with invalid date format
        response = self.client.get(f"{self.url}?date_from=invalid_date")
        
        # Should handle gracefully
        self.assert_response_format(response, status.HTTP_200_OK)
    
    def test_dashboard_performance(self):
        """Test dashboard performance with large datasets"""
        # Create a large number of items to test performance
        for i in range(100):  # Create 100 more tasks
            self.create_task(owner=self.user, title=f'Performance Task {i}')
        
        # Measure response time
        import time
        start_time = time.time()
        
        response = self.client.get(self.url)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Response should be reasonably fast (adjust threshold as needed)
        self.assertLess(response_time, 5.0)  # Should complete within 5 seconds
    
    def test_dashboard_data_consistency(self):
        """Test that dashboard data is consistent across requests"""
        # First request
        response1 = self.client.get(self.url)
        self.assert_response_format(response1, status.HTTP_200_OK)
        data1 = response1.data['data']
        
        # Second request
        response2 = self.client.get(self.url)
        self.assert_response_format(response2, status.HTTP_200_OK)
        data2 = response2.data['data']
        
        # Data should be consistent
        self.assertEqual(len(data1['tasks']), len(data2['tasks']))
        self.assertEqual(len(data1['tags']), len(data2['tags']))
        self.assertEqual(len(data1['subtasks']), len(data2['subtasks']))
        self.assertEqual(len(data1['comments']), len(data2['comments']))
        self.assertEqual(len(data1['attachments']), len(data2['attachments']))
    
    def test_dashboard_empty_sections(self):
        """Test dashboard with empty sections"""
        # Delete specific types of data
        Subtask.objects.all().delete()
        Comment.objects.all().delete()
        Attachment.objects.all().delete()
        
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        dashboard_data = response.data['data']
        
        # Check that empty sections are handled gracefully
        self.assertIn('subtasks', dashboard_data)
        self.assertEqual(len(dashboard_data['subtasks']), 0)
        
        self.assertIn('comments', dashboard_data)
        self.assertEqual(len(dashboard_data['comments']), 0)
        
        self.assertIn('attachments', dashboard_data)
        self.assertEqual(len(dashboard_data['attachments']), 0)
    
    def test_dashboard_authorization(self):
        """Test dashboard authorization for different user types"""
        # Test with regular user
        response = self.client.get(self.url)
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Create some data for admin user
        admin_task = self.create_task(owner=self.admin_user, title='Admin Task')
        admin_tag = self.create_tag(name='Admin Tag', color='#00ff00')
        admin_task.tags.add(admin_tag)
        
        # Test with admin user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_tokens["access"]}')
        response = self.client.get(self.url)
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Admin should see their own data, not regular user's data
        dashboard_data = response.data['data']
        for task in dashboard_data['tasks']:
            # Check that the task belongs to the admin user (owner_id should match admin user's ID)
            self.assertEqual(task['owner_id'], self.admin_user.id)
    
    def test_dashboard_real_time_updates(self):
        """Test dashboard real-time updates if implemented"""
        # Get initial dashboard state
        response1 = self.client.get(self.url)
        self.assert_response_format(response1, status.HTTP_200_OK)
        initial_task_count = len(response1.data['data']['tasks'])
        
        # Create a new task
        new_task = self.create_task(owner=self.user, title='Real-time Test Task')
        
        # Get updated dashboard state
        response2 = self.client.get(self.url)
        self.assert_response_format(response2, status.HTTP_200_OK)
        updated_task_count = len(response2.data['data']['tasks'])
        
        # Task count should have increased
        self.assertEqual(updated_task_count, initial_task_count + 1)
        
        # New task should be in the list
        task_titles = [task['title'] for task in response2.data['data']['tasks']]
        self.assertIn('Real-time Test Task', task_titles)
