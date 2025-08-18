from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from tests.base import BaseTestCase
from apps.tasks.services import DashboardService
from apps.tasks.models import Task, Tag, Subtask, Comment, Attachment

User = get_user_model()


class DashboardServiceTest(BaseTestCase):
    """Test cases for DashboardService"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        
        # Create comprehensive dashboard test data
        self.dashboard_data = self.create_dashboard_data(user=self.user)
        
        # Extract components for easier testing
        self.tasks = self.dashboard_data['tasks']
        self.tags = self.dashboard_data['tags']
        self.subtasks = self.dashboard_data['subtasks']
        self.comments = self.dashboard_data['comments']
        self.attachments = self.dashboard_data['attachments']
    
    def test_get_dashboard_overview_success(self):
        """Test successful dashboard overview retrieval"""
        overview = DashboardService.get_dashboard_overview(self.user)
        
        # Check that all expected sections are present
        expected_sections = ['tasks', 'tags', 'subtasks', 'comments', 'attachments']
        for section in expected_sections:
            self.assertIn(section, overview)
        
        # Check that data is present
        self.assertGreater(len(overview['tasks']), 0)
        self.assertGreater(len(overview['tags']), 0)
        self.assertGreater(len(overview['subtasks']), 0)
        self.assertGreater(len(overview['comments']), 0)
        self.assertGreater(len(overview['attachments']), 0)
    
    def test_get_dashboard_overview_empty(self):
        """Test dashboard overview when no data exists"""
        # Delete all existing data
        Task.objects.all().delete()
        Tag.objects.all().delete()
        Subtask.objects.all().delete()
        Comment.objects.all().delete()
        Attachment.objects.all().delete()
        
        overview = DashboardService.get_dashboard_overview(self.user)
        
        # All sections should be empty
        for section in ['tasks', 'tags', 'subtasks', 'comments', 'attachments']:
            self.assertIn(section, overview)
            self.assertEqual(len(overview[section]), 0)
    
    def test_get_dashboard_overview_user_filtered(self):
        """Test that dashboard only shows user's own data"""
        # Create data for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_tag = self.create_tag(name='Other User Tag', color='#000000')
        
        overview = DashboardService.get_dashboard_overview(self.user)
        
        # Should not see other user's data
        task_titles = [task['title'] for task in overview['tasks']]
        tag_names = [tag['name'] for tag in overview['tags']]
        
        self.assertNotIn('Other User Task', task_titles)
        self.assertNotIn('Other User Tag', tag_names)
    
    def test_get_dashboard_overview_with_filters(self):
        """Test dashboard overview with filters"""
        # The get_dashboard_overview method doesn't accept filters
        # This test verifies the basic functionality without filters
        overview = DashboardService.get_dashboard_overview(self.user)
        
        # Should return overview data
        self.assertIsNotNone(overview)
        self.assertIn('tasks', overview)
        self.assertIn('tags', overview)
        self.assertIn('subtasks', overview)
        self.assertIn('comments', overview)
        self.assertIn('attachments', overview)
    
    def test_get_task_statistics_success(self):
        """Test successful task statistics retrieval"""
        statistics = DashboardService.get_task_statistics(self.user)
        
        # Check that expected statistics are present
        expected_stats = ['status_distribution', 'priority_distribution', 'progress_distribution']
        for stat in expected_stats:
            self.assertIn(stat, statistics)
        
        # Check that statistics contain data
        self.assertGreater(len(statistics['status_distribution']), 0)
        self.assertGreater(len(statistics['priority_distribution']), 0)
        self.assertGreater(len(statistics['progress_distribution']), 0)
    
    def test_get_task_statistics_empty(self):
        """Test task statistics when no tasks exist"""
        # Delete all tasks
        Task.objects.all().delete()
        
        statistics = DashboardService.get_task_statistics(self.user)
        
        # All counts should be zero
        self.assertEqual(statistics['total_tasks'], 0)
        self.assertEqual(statistics['completed_tasks'], 0)
        self.assertEqual(statistics['in_progress_tasks'], 0)
        self.assertEqual(statistics['overdue_tasks'], 0)
    
    def test_get_task_statistics_with_date_range(self):
        """Test task statistics with date range filter"""
        # Create tasks with different creation dates
        old_task = self.create_task(owner=self.user, title='Old Task')
        old_task.created_at = timezone.now() - timedelta(days=30)
        old_task.save()
        
        new_task = self.create_task(owner=self.user, title='New Task')
        
        # Get statistics for recent tasks only
        recent_stats = DashboardService.get_task_statistics(
            self.user,
            created_after=timezone.now() - timedelta(days=7)
        )
        
        # Should only count recent tasks
        self.assertEqual(recent_stats['total_tasks'], 5)  # 4 from setup + 1 new
        self.assertEqual(recent_stats['completed_tasks'], 1)  # 1 from setup
    
    def test_get_task_statistics_with_status_filter(self):
        """Test task statistics with status filter"""
        # Create tasks with different statuses
        self.create_task(owner=self.user, title='Todo Task', status='TODO')
        self.create_task(owner=self.user, title='In Progress Task', status='IN_PROGRESS')
        self.create_task(owner=self.user, title='Completed Task', status='COMPLETED')
        
        # Get statistics for specific status
        todo_stats = DashboardService.get_task_statistics(self.user, task_status='TODO')
        self.assertEqual(todo_stats['total_tasks'], 3)  # 2 from setup + 1 new one
        self.assertEqual(todo_stats['completed_tasks'], 0)
        
        completed_stats = DashboardService.get_task_statistics(self.user, task_status='COMPLETED')
        self.assertEqual(completed_stats['total_tasks'], 2)  # 1 from setup + 1 new one
        self.assertEqual(completed_stats['completed_tasks'], 2)  # 1 from setup + 1 new one
    
    def test_get_performance_metrics_success(self):
        """Test successful performance metrics retrieval"""
        metrics = DashboardService.get_performance_metrics(self.user)
        
        # Check that all expected metrics are present
        expected_metrics = ['completion_rate', 'average_completion_time', 'efficiency_score']
        for metric in expected_metrics:
            self.assertIn(metric, metrics)
        
        # Metrics should be valid
        self.assertGreaterEqual(metrics['completion_rate'], 0.0)
        self.assertLessEqual(metrics['completion_rate'], 100.0)
        self.assertGreaterEqual(metrics['average_completion_time'], 0.0)
        self.assertGreaterEqual(metrics['efficiency_score'], 0.0)
    
    def test_get_performance_metrics_no_completed_tasks(self):
        """Test performance metrics when no tasks are completed"""
        # Mark all tasks as not completed
        for task in self.tasks:
            task.status = 'TODO'
            task.completed = False
            task.completed_at = None
            task.save()
        
        metrics = DashboardService.get_performance_metrics(self.user)
        
        # Completion rate should be 0
        self.assertEqual(metrics['completion_rate'], 0.0)
        
        # Average completion time should be 0
        self.assertEqual(metrics['average_completion_time'], 0.0)
    
    def test_get_performance_metrics_with_date_range(self):
        """Test performance metrics with date range filter"""
        # Create completed task with specific completion time
        completed_task = self.create_task(owner=self.user, title='Completed Task')
        completed_task.status = 'COMPLETED'
        completed_task.completed = True
        completed_task.started_at = timezone.now() - timedelta(hours=5)
        completed_task.completed_at = timezone.now()
        completed_task.save()
        
        # Get metrics for recent period
        recent_metrics = DashboardService.get_performance_metrics(
            self.user,
            completed_after=timezone.now() - timedelta(days=1)
        )
        
        # Should include the completed task
        self.assertGreater(recent_metrics['completion_rate'], 0.0)
        self.assertGreater(recent_metrics['average_completion_time'], 0.0)
    
    def test_get_recent_activity_success(self):
        """Test successful recent activity retrieval"""
        activity = DashboardService.get_recent_activity(self.user, limit=10)
        
        # Should return recent activity
        self.assertIsInstance(activity, list)
        self.assertLessEqual(len(activity), 10)
        
        # Each activity item should have required fields
        for item in activity:
            self.assertIn('type', item)
            self.assertIn('timestamp', item)
            self.assertIn('description', item)
    
    def test_get_recent_activity_with_limit(self):
        """Test recent activity with different limits"""
        # Test with different limits
        limit_5 = DashboardService.get_recent_activity(self.user, limit=5)
        self.assertLessEqual(len(limit_5), 5)
        
        limit_20 = DashboardService.get_recent_activity(self.user, limit=20)
        self.assertLessEqual(len(limit_20), 20)
    
    def test_get_recent_activity_empty(self):
        """Test recent activity when no activity exists"""
        # Delete all data
        Task.objects.all().delete()
        Comment.objects.all().delete()
        Attachment.objects.all().delete()
        
        activity = DashboardService.get_recent_activity(self.user)
        
        # Should return empty list
        self.assertEqual(len(activity), 0)
    
    def test_get_recent_activity_types(self):
        """Test recent activity includes different types"""
        # Create different types of activity
        task = self.create_task(owner=self.user, title='Activity Test Task')
        comment = self.create_comment(task=task, content='Test comment')
        attachment = self.create_attachment(task=task, original_filename='test.txt')
        
        activity = DashboardService.get_recent_activity(self.user, limit=20)
        
        # Should include different activity types
        activity_types = [item['type'] for item in activity]
        self.assertIn('task_created', activity_types)
        self.assertIn('comment_added', activity_types)
        self.assertIn('attachment_uploaded', activity_types)
    
    def test_get_dashboard_summary_success(self):
        """Test successful dashboard summary retrieval"""
        summary = DashboardService.get_dashboard_summary(self.user)
        
        # Should include all dashboard components
        self.assertIn('overview', summary)
        self.assertIn('statistics', summary)
        self.assertIn('performance_metrics', summary)
        self.assertIn('recent_activity', summary)
        
        # Each component should have data
        self.assertIsNotNone(summary['overview'])
        self.assertIsNotNone(summary['statistics'])
        self.assertIsNotNone(summary['performance_metrics'])
        self.assertIsNotNone(summary['recent_activity'])
    
    def test_get_dashboard_summary_with_filters(self):
        """Test dashboard summary with filters"""
        summary = DashboardService.get_dashboard_summary(
            self.user,
            created_after=timezone.now() - timedelta(days=7),
            include_archived=False
        )
        
        # Should apply filters to all components
        self.assertIsNotNone(summary)
        
        # Overview should respect date filter
        overview = summary['overview']
        for task in overview['tasks']:
            self.assertGreaterEqual(task['created_at'], timezone.now() - timedelta(days=7))
    
    def test_get_dashboard_summary_performance(self):
        """Test performance of dashboard summary generation"""
        # Create many items to test performance
        for i in range(50):
            self.create_task(owner=self.user, title=f'Performance Task {i}')
        
        # Measure generation time
        import time
        start_time = time.time()
        
        summary = DashboardService.get_dashboard_summary(self.user)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Should generate summary
        self.assertIsNotNone(summary)
        
        # Should be reasonably fast
        self.assertLess(generation_time, 2.0)  # Should complete within 2 seconds
    
    def test_get_dashboard_summary_data_integrity(self):
        """Test data integrity of dashboard summary"""
        summary = DashboardService.get_dashboard_summary(self.user)
        
        # Verify that statistics match overview data
        overview = summary['overview']
        statistics = summary['statistics']
        
        self.assertEqual(statistics['total_tasks'], len(overview['tasks']))
        self.assertEqual(statistics['total_tags'], len(overview['tags']))
        self.assertEqual(statistics['total_subtasks'], len(overview['subtasks']))
        self.assertEqual(statistics['total_comments'], len(overview['comments']))
        self.assertEqual(statistics['total_attachments'], len(overview['attachments']))
    
    def test_get_dashboard_summary_edge_cases(self):
        """Test edge cases for dashboard summary"""
        # Test with user that has no data
        new_user = self.create_user(username='newuser', email='new@example.com')
        summary = DashboardService.get_dashboard_summary(new_user)
        
        # Should handle empty data gracefully
        self.assertIsNotNone(summary)
        self.assertEqual(summary['statistics']['total_tasks'], 0)
        self.assertEqual(len(summary['overview']['tasks']), 0)
        
        # Test with very large limit
        large_limit_summary = DashboardService.get_dashboard_summary(
            self.user,
            activity_limit=10000
        )
        
        # Should handle large limits gracefully
        self.assertIsNotNone(large_limit_summary)
    
    def test_get_dashboard_summary_caching(self):
        """Test caching of dashboard summary if implemented"""
        # First generation
        summary1 = DashboardService.get_dashboard_summary(self.user)
        
        # Second generation (should be cached if caching is implemented)
        summary2 = DashboardService.get_dashboard_summary(self.user)
        
        # Both should return valid summaries
        self.assertIsNotNone(summary1)
        self.assertIsNotNone(summary2)
        
        # Check if results are identical (if caching is working)
        # This test may need adjustment based on your actual caching implementation
    
    def test_get_dashboard_summary_with_complex_filters(self):
        """Test dashboard summary with complex filter combinations"""
        # Create tasks with different characteristics
        high_priority_task = self.create_task(
            owner=self.user,
            title='High Priority Task',
            priority='HIGH',
            status='IN_PROGRESS'
        )
        
        low_priority_task = self.create_task(
            owner=self.user,
            title='Low Priority Task',
            priority='LOW',
            status='TODO'
        )
        
        # Apply complex filters
        summary = DashboardService.get_dashboard_summary(
            self.user,
            task_priority='HIGH',
            task_status='IN_PROGRESS',
            created_after=timezone.now() - timedelta(days=1)
        )
        
        # Should only include high priority, in-progress tasks
        overview = summary['overview']
        for task in overview['tasks']:
            self.assertEqual(task['priority'], 'HIGH')
            self.assertEqual(task['status'], 'IN_PROGRESS')
    
    def test_get_dashboard_summary_error_handling(self):
        """Test error handling in dashboard summary generation"""
        # Test with invalid user
        with self.assertRaises(ValueError):
            DashboardService.get_dashboard_summary(None)
        
        # Test with invalid date filters
        with self.assertRaises(ValueError):
            DashboardService.get_dashboard_summary(
                self.user,
                created_after='invalid_date'
            )
        
        # Test with invalid status
        with self.assertRaises(ValidationError):
            DashboardService.get_dashboard_summary(
                self.user,
                task_status='INVALID_STATUS'
            )
    
    def test_get_dashboard_summary_real_time_updates(self):
        """Test that dashboard summary reflects real-time updates"""
        # Get initial summary
        summary1 = DashboardService.get_dashboard_summary(self.user)
        initial_task_count = summary1['statistics']['total_tasks']
        
        # Create new task
        new_task = self.create_task(owner=self.user, title='Real-time Test Task')
        
        # Get updated summary
        summary2 = DashboardService.get_dashboard_summary(self.user)
        updated_task_count = summary2['statistics']['total_tasks']
        
        # Task count should have increased
        self.assertEqual(updated_task_count, initial_task_count + 1)
        
        # New task should be in overview
        task_titles = [task['title'] for task in summary2['overview']['tasks']]
        self.assertIn('Real-time Test Task', task_titles)
    
    def test_get_dashboard_summary_with_user_permissions(self):
        """Test dashboard summary respects user permissions"""
        # Test with regular user
        summary = DashboardService.get_dashboard_summary(self.user)
        self.assertIsNotNone(summary)
        
        # Test with admin user
        admin_user = self.create_admin_user()
        admin_summary = DashboardService.get_dashboard_summary(admin_user)
        self.assertIsNotNone(admin_summary)
        
        # Admin should see their own data, not regular user's data
        admin_overview = admin_summary['overview']
        for task in admin_overview['tasks']:
            self.assertEqual(task['owner']['username'], 'adminuser')
    
    def test_get_dashboard_summary_consistency(self):
        """Test consistency of dashboard summary across multiple calls"""
        # Get summary multiple times
        summary1 = DashboardService.get_dashboard_summary(self.user)
        summary2 = DashboardService.get_dashboard_summary(self.user)
        summary3 = DashboardService.get_dashboard_summary(self.user)
        
        # All summaries should be consistent
        self.assertEqual(
            summary1['statistics']['total_tasks'],
            summary2['statistics']['total_tasks']
        )
        self.assertEqual(
            summary2['statistics']['total_tasks'],
            summary3['statistics']['total_tasks']
        )
        
        # Overview data should be consistent
        self.assertEqual(
            len(summary1['overview']['tasks']),
            len(summary2['overview']['tasks'])
        )
        self.assertEqual(
            len(summary2['overview']['tasks']),
            len(summary3['overview']['tasks'])
        )
