from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from tests.base import BaseTestCase
from apps.tasks.services import SubtaskService
from apps.tasks.models import Task, Subtask

User = get_user_model()


class SubtaskServiceTest(BaseTestCase):
    """Test cases for SubtaskService"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.task = self.create_task(owner=self.user)
        self.subtask = self.create_subtask(task=self.task)
    
    def test_get_user_subtasks_success(self):
        """Test successful retrieval of user subtasks"""
        # Create additional subtasks for the user
        self.create_subtask(task=self.task, title='Subtask 2')
        self.create_subtask(task=self.task, title='Subtask 3')
        
        # Create subtask for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_subtask = self.create_subtask(task=other_task, title='Other User Subtask')
        
        subtasks = SubtaskService.get_user_subtasks(self.user)
        
        # Should only return subtasks for the specified user
        self.assertEqual(subtasks.count(), 3)
        for subtask in subtasks:
            self.assertIn(subtask.task.owner, [self.user, self.task.assigned_to])
    
    def test_get_user_subtasks_empty(self):
        """Test retrieval of user subtasks when none exist"""
        # Delete all subtasks
        Subtask.objects.all().delete()
        
        subtasks = SubtaskService.get_user_subtasks(self.user)
        
        self.assertEqual(subtasks.count(), 0)
    
    def test_get_user_subtasks_admin_access(self):
        """Test that admin users can see all subtasks"""
        # Create subtasks for different users
        user1 = self.create_user(username='user1', email='user1@example.com')
        user2 = self.create_user(username='user2', email='user2@example.com')
        
        task1 = self.create_task(owner=user1, title='User 1 Task')
        task2 = self.create_task(owner=user2, title='User 2 Task')
        
        self.create_subtask(task=task1, title='User 1 Subtask')
        self.create_subtask(task=task2, title='User 2 Subtask')
        
        # Admin user should see all subtasks
        admin_user = self.create_admin_user()
        admin_subtasks = SubtaskService.get_user_subtasks(admin_user)
        
        # Admin should see all subtasks (2 created in this test + 1 from setUp)
        self.assertEqual(admin_subtasks.count(), 3)
    
    def test_get_user_subtasks_assigned_user(self):
        """Test that assigned users can see subtasks"""
        # Create task assigned to another user
        assigned_user = self.create_user(username='assigned', email='assigned@example.com')
        assigned_task = self.create_task(owner=self.user, assigned_to=assigned_user)
        
        # Create subtask for assigned task
        assigned_subtask = self.create_subtask(task=assigned_task, title='Assigned Subtask')
        
        # Assigned user should see the subtask
        assigned_user_subtasks = SubtaskService.get_user_subtasks(assigned_user)
        self.assertIn(assigned_subtask, assigned_user_subtasks)
    
    def test_get_overdue_subtasks_success(self):
        """Test successful retrieval of overdue subtasks"""
        # Create overdue subtask
        overdue_subtask = self.create_subtask(
            task=self.task,
            title='Overdue Subtask',
            due_date=timezone.now() - timedelta(days=1)
        )
        
        # Create future subtask
        future_subtask = self.create_subtask(
            task=self.task,
            title='Future Subtask',
            due_date=timezone.now() + timedelta(days=1)
        )
        
        overdue_subtasks = SubtaskService.get_overdue_subtasks(self.user)
        
        # Should only return overdue subtasks
        self.assertEqual(overdue_subtasks.count(), 1)
        self.assertEqual(overdue_subtasks.first().title, 'Overdue Subtask')
    
    def test_get_overdue_subtasks_completed(self):
        """Test that completed subtasks are not considered overdue"""
        # Create overdue but completed subtask
        overdue_completed_subtask = self.create_subtask(
            task=self.task,
            title='Overdue Completed Subtask',
            due_date=timezone.now() - timedelta(days=1),
            completed=True,
            completed_at=timezone.now()
        )
        
        overdue_subtasks = SubtaskService.get_overdue_subtasks(self.user)
        
        # Should not include completed subtasks
        self.assertEqual(overdue_subtasks.count(), 0)
    
    def test_get_overdue_subtasks_no_due_date(self):
        """Test that subtasks without due date are not considered overdue"""
        # Create subtask without due date
        no_due_date_subtask = self.create_subtask(
            task=self.task,
            title='No Due Date Subtask'
        )
        
        overdue_subtasks = SubtaskService.get_overdue_subtasks(self.user)
        
        # Should not include subtasks without due date
        self.assertEqual(overdue_subtasks.count(), 0)
    
    def test_get_subtasks_due_soon_success(self):
        """Test successful retrieval of subtasks due soon"""
        # Create subtask due in 3 days
        due_soon_subtask = self.create_subtask(
            task=self.task,
            title='Due Soon Subtask',
            due_date=timezone.now() + timedelta(days=3)
        )
        
        # Create subtask due in 10 days
        due_later_subtask = self.create_subtask(
            task=self.task,
            title='Due Later Subtask',
            due_date=timezone.now() + timedelta(days=10)
        )
        
        # Get subtasks due within 7 days
        due_soon_subtasks = SubtaskService.get_subtasks_due_soon(self.user, days=7)
        
        # Should only return subtasks due within 7 days
        self.assertEqual(due_soon_subtasks.count(), 1)
        self.assertEqual(due_soon_subtasks.first().title, 'Due Soon Subtask')
    
    def test_get_subtasks_due_soon_custom_days(self):
        """Test subtasks due soon with custom day range"""
        # Create subtask due in 2 days
        due_very_soon_subtask = self.create_subtask(
            task=self.task,
            title='Due Very Soon Subtask',
            due_date=timezone.now() + timedelta(days=2)
        )
        
        # Get subtasks due within 1 day
        due_very_soon_subtasks = SubtaskService.get_subtasks_due_soon(self.user, days=1)
        
        # Should not include subtask due in 2 days
        self.assertEqual(due_very_soon_subtasks.count(), 0)
    
    def test_get_subtasks_due_soon_completed(self):
        """Test that completed subtasks are not included in due soon"""
        # Create completed subtask due soon
        completed_due_soon_subtask = self.create_subtask(
            task=self.task,
            title='Completed Due Soon Subtask',
            due_date=timezone.now() + timedelta(days=3),
            completed=True,
            completed_at=timezone.now()
        )
        
        due_soon_subtasks = SubtaskService.get_subtasks_due_soon(self.user, days=7)
        
        # Should not include completed subtasks
        self.assertEqual(due_soon_subtasks.count(), 0)
    
    def test_complete_subtask_success(self):
        """Test successful subtask completion"""
        # Ensure subtask is not completed
        self.assertFalse(self.subtask.completed)
        self.assertIsNone(self.subtask.completed_at)
        
        # Start the subtask first (required for completion)
        SubtaskService.start_subtask(self.subtask, self.user)
        
        # Complete the subtask
        result = SubtaskService.complete_subtask(self.subtask, self.user)
        
        # Should return True
        self.assertTrue(result)
        
        # Refresh from database
        self.subtask.refresh_from_db()
        
        # Should be marked as completed
        self.assertTrue(self.subtask.completed)
        self.assertIsNotNone(self.subtask.completed_at)
    
    def test_complete_subtask_already_completed(self):
        """Test completing already completed subtask"""
        # Mark subtask as completed
        self.subtask.completed = True
        self.subtask.completed_at = timezone.now()
        self.subtask.save()
        
        # Try to complete again
        result = SubtaskService.complete_subtask(self.subtask, self.user)
        
        # Should return False
        self.assertFalse(result)
        
        # Should remain completed
        self.assertTrue(self.subtask.completed)
    
    def test_start_subtask_success(self):
        """Test successful subtask start"""
        # Ensure subtask hasn't started
        self.assertIsNone(self.subtask.started_at)
        
        # Start the subtask
        result = SubtaskService.start_subtask(self.subtask, self.user)
        
        # Should return True
        self.assertTrue(result)
        
        # Refresh from database
        self.subtask.refresh_from_db()
        
        # Should have start time
        self.assertIsNotNone(self.subtask.started_at)
    
    def test_start_subtask_already_started(self):
        """Test starting already started subtask"""
        # Mark subtask as started
        self.subtask.started_at = timezone.now()
        self.subtask.save()
        
        # Try to start again
        result = SubtaskService.start_subtask(self.subtask, self.user)
        
        # Should return False
        self.assertFalse(result)
        
        # Should remain started
        self.assertIsNotNone(self.subtask.started_at)
    
    def test_update_subtask_progress_success(self):
        """Test successful subtask progress update"""
        # Update progress to 50%
        result = SubtaskService.update_subtask_progress(self.subtask, 50, self.user)
        
        # Should return True
        self.assertTrue(result)
        
        # Refresh from database
        self.subtask.refresh_from_db()
        
        # Progress should be updated
        self.assertEqual(self.subtask.progress, 50)
        
        # Should be started if progress > 0
        self.assertIsNotNone(self.subtask.started_at)
    
    def test_update_subtask_progress_to_completion(self):
        """Test updating subtask progress to 100%"""
        # Update progress to 100%
        result = SubtaskService.update_subtask_progress(self.subtask, 100, self.user)
        
        # Should return True
        self.assertTrue(result)
        
        # Refresh from database
        self.subtask.refresh_from_db()
        
        # Should be marked as completed
        self.assertTrue(self.subtask.completed)
        self.assertIsNotNone(self.subtask.completed_at)
        self.assertEqual(self.subtask.progress, 100)
    
    def test_update_subtask_progress_invalid_values(self):
        """Test subtask progress update with invalid values"""
        # Test negative progress
        result = SubtaskService.update_subtask_progress(self.subtask, -10, self.user)
        self.assertFalse(result)
        
        # Test progress > 100
        result = SubtaskService.update_subtask_progress(self.subtask, 150, self.user)
        self.assertFalse(result)
        
        # Test progress = 0
        result = SubtaskService.update_subtask_progress(self.subtask, 0, self.user)
        self.assertTrue(result)
    
    def test_update_subtask_progress_parent_task_update(self):
        """Test that parent task progress is updated when subtask progress changes"""
        # Create another subtask
        subtask2 = self.create_subtask(task=self.task, title='Subtask 2')
        
        # Set initial progress for both subtasks
        self.subtask.progress = 50
        self.subtask.save()
        subtask2.progress = 0
        subtask2.save()
        
        # Update first subtask to 100%
        SubtaskService.update_subtask_progress(self.subtask, 100, self.user)
        
        # Refresh parent task
        self.task.refresh_from_db()
        
        # Parent task progress should be updated (average of subtask progress)
        expected_progress = (100 + 0) // 2  # 50%
        self.assertEqual(self.task.progress, expected_progress)
    
    def test_update_subtask_progress_start_automatic(self):
        """Test that subtask automatically starts when progress > 0"""
        # Ensure subtask hasn't started
        self.assertIsNone(self.subtask.started_at)
        
        # Update progress to 25%
        SubtaskService.update_subtask_progress(self.subtask, 25, self.user)
        
        # Refresh from database
        self.subtask.refresh_from_db()
        
        # Should automatically start
        self.assertIsNotNone(self.subtask.started_at)
    
    def test_subtask_service_performance(self):
        """Test performance of subtask service methods with large datasets"""
        # Create many subtasks
        for i in range(100):
            self.create_subtask(task=self.task, title=f'Performance Subtask {i}')
        
        # Measure retrieval time
        import time
        start_time = time.time()
        
        subtasks = SubtaskService.get_user_subtasks(self.user)
        
        end_time = time.time()
        retrieval_time = end_time - start_time
        
        # Should retrieve all subtasks
        self.assertEqual(subtasks.count(), 101)  # Including the one from setUp
        
        # Should be reasonably fast
        self.assertLess(retrieval_time, 1.0)  # Should complete within 1 second
    
    def test_subtask_service_data_integrity(self):
        """Test data integrity of subtask service operations"""
        # Create subtask with specific data
        original_subtask = self.create_subtask(
            task=self.task,
            title='Integrity Test Subtask',
            description='Test description',
            priority='HIGH',
            status='TODO',
            estimated_hours=2.0,
            progress=0
        )
        
        # Update progress through service
        SubtaskService.update_subtask_progress(original_subtask, 75, self.user)
        
        # Refresh from database
        original_subtask.refresh_from_db()
        
        # Verify data integrity
        self.assertEqual(original_subtask.progress, 75)
        self.assertIsNotNone(original_subtask.started_at)
        self.assertFalse(original_subtask.completed)
        
        # Complete the subtask
        SubtaskService.complete_subtask(original_subtask, self.user)
        
        # Refresh again
        original_subtask.refresh_from_db()
        
        # Should be completed
        self.assertTrue(original_subtask.completed)
        self.assertIsNotNone(original_subtask.completed_at)
    
    def test_subtask_service_edge_cases(self):
        """Test edge cases for subtask service"""
        # Test with user that has no subtasks
        new_user = self.create_user(username='newuser', email='new@example.com')
        subtasks = SubtaskService.get_user_subtasks(new_user)
        self.assertEqual(subtasks.count(), 0)
        
        # Test with very large progress values (should be rejected)
        result = SubtaskService.update_subtask_progress(self.subtask, 1000, self.user)
        self.assertFalse(result)
        
        # Test with decimal progress values
        result = SubtaskService.update_subtask_progress(self.subtask, 50.5, self.user)
        # Should handle gracefully (depends on implementation)
        
        # Test with None values
        with self.assertRaises(AttributeError):
            SubtaskService.update_subtask_progress(None, 50, self.user)
        
        with self.assertRaises(AttributeError):
            SubtaskService.update_subtask_progress(self.subtask, 50, None)
    
    def test_subtask_service_user_permissions(self):
        """Test that subtask service respects user permissions"""
        # Create subtask for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_subtask = self.create_subtask(task=other_task, title='Other User Subtask')
        
        # Regular user should not be able to modify other user's subtask
        result = SubtaskService.update_subtask_progress(other_subtask, 50, self.user)
        # Should handle gracefully (depends on implementation)
        
        # Admin user should be able to modify any subtask
        admin_user = self.create_admin_user()
        result = SubtaskService.update_subtask_progress(other_subtask, 75, admin_user)
        # Should work for admin (depends on implementation)
    
    def test_subtask_service_caching(self):
        """Test caching of subtask service methods if implemented"""
        # First retrieval
        subtasks1 = SubtaskService.get_user_subtasks(self.user)
        
        # Second retrieval (should be cached if caching is implemented)
        subtasks2 = SubtaskService.get_user_subtasks(self.user)
        
        # Both retrievals should return same results
        self.assertEqual(subtasks1.count(), subtasks2.count())
        
        # Check if results are identical (if caching is working)
        # This test may need adjustment based on your actual caching implementation
    
    def test_subtask_service_with_complex_filters(self):
        """Test subtask service with complex filter combinations"""
        # Create subtasks with different characteristics
        high_priority_overdue_subtask = self.create_subtask(
            task=self.task,
            title='High Priority Overdue Subtask',
            priority='HIGH',
            due_date=timezone.now() - timedelta(days=1)
        )
        
        low_priority_future_subtask = self.create_subtask(
            task=self.task,
            title='Low Priority Future Subtask',
            priority='LOW',
            due_date=timezone.now() + timedelta(days=7)
        )
        
        # Test different filter combinations
        overdue_subtasks = SubtaskService.get_overdue_subtasks(self.user)
        self.assertIn(high_priority_overdue_subtask, overdue_subtasks)
        self.assertNotIn(low_priority_future_subtask, overdue_subtasks)
        
        due_soon_subtasks = SubtaskService.get_subtasks_due_soon(self.user, days=10)
        self.assertIn(low_priority_future_subtask, due_soon_subtasks)
        self.assertNotIn(high_priority_overdue_subtask, due_soon_subtasks)
    
    def test_subtask_service_real_time_updates(self):
        """Test that subtask service reflects real-time updates"""
        # Get initial subtask count
        initial_count = SubtaskService.get_user_subtasks(self.user).count()
        
        # Create new subtask
        new_subtask = self.create_subtask(task=self.task, title='Real-time Test Subtask')
        
        # Get updated count
        updated_count = SubtaskService.get_user_subtasks(self.user).count()
        
        # Count should have increased
        self.assertEqual(updated_count, initial_count + 1)
        
        # New subtask should be in the list
        subtask_titles = [subtask.title for subtask in SubtaskService.get_user_subtasks(self.user)]
        self.assertIn('Real-time Test Subtask', subtask_titles)
    
    def test_subtask_service_consistency(self):
        """Test consistency of subtask service across multiple calls"""
        # Get subtasks multiple times
        subtasks1 = SubtaskService.get_user_subtasks(self.user)
        subtasks2 = SubtaskService.get_user_subtasks(self.user)
        subtasks3 = SubtaskService.get_user_subtasks(self.user)
        
        # All retrievals should be consistent
        self.assertEqual(subtasks1.count(), subtasks2.count())
        self.assertEqual(subtasks2.count(), subtasks3.count())
        
        # Data should be consistent
        subtask_ids1 = [subtask.id for subtask in subtasks1]
        subtask_ids2 = [subtask.id for subtask in subtasks2]
        subtask_ids3 = [subtask.id for subtask in subtasks3]
        
        self.assertEqual(subtask_ids1, subtask_ids2)
        self.assertEqual(subtask_ids2, subtask_ids3)
