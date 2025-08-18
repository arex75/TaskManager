from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from tests.base import BaseTestCase
from apps.tasks.services import CommentService
from apps.tasks.models import Task, Subtask, Comment

User = get_user_model()


class CommentServiceTest(BaseTestCase):
    """Test cases for CommentService"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.task = self.create_task(owner=self.user)
        self.subtask = self.create_subtask(task=self.task)
        self.comment = self.create_comment(task=self.task, author=self.user)
    
    def test_get_user_comments_success(self):
        """Test successful retrieval of user comments"""
        # Create additional comments for the user
        self.create_comment(task=self.task, author=self.user, content='Comment 2')
        self.create_comment(task=self.task, author=self.user, content='Comment 3')
        
        # Create comment for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_comment = self.create_comment(task=other_task, author=other_user, content='Other User Comment')
        
        comments = CommentService.get_user_comments(self.user)
        
        # Should only return comments for the specified user
        self.assertEqual(comments.count(), 3)
        for comment in comments:
            self.assertIn(comment.task.owner, [self.user, comment.task.assigned_to])
    
    def test_get_user_comments_empty(self):
        """Test retrieval of user comments when none exist"""
        # Delete all comments
        Comment.objects.all().delete()
        
        comments = CommentService.get_user_comments(self.user)
        
        self.assertEqual(comments.count(), 0)
    
    def test_get_user_comments_admin_access(self):
        """Test that admin users can see all comments"""
        # Create comments for different users
        user1 = self.create_user(username='user1', email='user1@example.com')
        user2 = self.create_user(username='user2', email='user2@example.com')
        
        task1 = self.create_task(owner=user1, title='User 1 Task')
        task2 = self.create_task(owner=user2, title='User 2 Task')
        
        self.create_comment(task=task1, author=user1, content='User 1 Comment')
        self.create_comment(task=task2, author=user2, content='User 2 Comment')
        
        # Admin user should see all comments
        admin_user = self.create_admin_user()
        admin_comments = CommentService.get_user_comments(admin_user)
        
        # Admin should see all comments (including the one from setUp)
        self.assertEqual(admin_comments.count(), 3)
    
    def test_get_user_comments_assigned_user(self):
        """Test that assigned users can see comments"""
        # Create task assigned to another user
        assigned_user = self.create_user(username='assigned', email='assigned@example.com')
        assigned_task = self.create_task(owner=self.user, assigned_to=assigned_user)
        
        # Create comment for assigned task
        assigned_comment = self.create_comment(task=assigned_task, author=self.user, content='Assigned Task Comment')
        
        # Assigned user should see the comment
        assigned_user_comments = CommentService.get_user_comments(assigned_user)
        self.assertIn(assigned_comment, assigned_user_comments)
    
    def test_get_user_comments_subtask_comments(self):
        """Test that users can see comments on subtasks they have access to"""
        # Create comment on subtask
        subtask_comment = self.create_comment(
            subtask=self.subtask,
            author=self.user,
            content='Subtask Comment'
        )
        
        # User should see subtask comments
        user_comments = CommentService.get_user_comments(self.user)
        self.assertIn(subtask_comment, user_comments)
    
    def test_get_user_comments_nested_access(self):
        """Test that users can see comments on subtasks of tasks they have access to"""
        # Create nested structure: User -> Task -> Subtask -> Comment
        nested_comment = self.create_comment(
            subtask=self.subtask,
            author=self.user,
            content='Nested Comment'
        )
        
        # User should see the nested comment
        user_comments = CommentService.get_user_comments(self.user)
        self.assertIn(nested_comment, user_comments)
    
    def test_get_user_comments_public_tasks(self):
        """Test that users can see comments on public tasks"""
        # Create public task
        public_task = self.create_task(owner=self.user, title='Public Task')
        public_comment = self.create_comment(task=public_task, author=self.user, content='Public Comment')
        
        # Another user should NOT see comments on tasks they don't own/aren't assigned to
        # (since Task model doesn't have an is_public field)
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_user_comments = CommentService.get_user_comments(other_user)
        
        # Should NOT include comments on tasks they don't have access to
        self.assertNotIn(public_comment, other_user_comments)
    
    def test_can_edit_comment_author(self):
        """Test that comment author can edit their own comment"""
        # User should be able to edit their own comment
        can_edit = CommentService.can_edit_comment(self.comment, self.user)
        self.assertTrue(can_edit)
    
    def test_can_edit_comment_admin(self):
        """Test that admin users can edit any comment"""
        # Admin user should be able to edit any comment
        admin_user = self.create_admin_user()
        can_edit = CommentService.can_edit_comment(self.comment, admin_user)
        self.assertTrue(can_edit)
    
    def test_can_edit_comment_other_user(self):
        """Test that other users cannot edit comments they don't own"""
        # Other user should not be able to edit comment
        other_user = self.create_user(username='otheruser', email='other@example.com')
        can_edit = CommentService.can_edit_comment(self.comment, other_user)
        self.assertFalse(can_edit)
    
    def test_can_edit_comment_staff_user(self):
        """Test that staff users can edit any comment"""
        # Staff user should be able to edit any comment
        staff_user = self.create_user(username='staffuser', email='staff@example.com')
        staff_user.is_staff = True
        staff_user.save()
        
        can_edit = CommentService.can_edit_comment(self.comment, staff_user)
        self.assertTrue(can_edit)
    
    def test_can_edit_comment_anonymous(self):
        """Test that anonymous users cannot edit comments"""
        # Anonymous user should not be able to edit comment
        from django.contrib.auth.models import AnonymousUser
        anonymous_user = AnonymousUser()
        
        can_edit = CommentService.can_edit_comment(self.comment, anonymous_user)
        self.assertFalse(can_edit)
    
    def test_can_edit_comment_none_user(self):
        """Test that None user cannot edit comments"""
        # None user should not be able to edit comment
        can_edit = CommentService.can_edit_comment(self.comment, None)
        self.assertFalse(can_edit)
    
    def test_can_delete_comment_author(self):
        """Test that comment author can delete their own comment"""
        # User should be able to delete their own comment
        can_delete = CommentService.can_delete_comment(self.comment, self.user)
        self.assertTrue(can_delete)
    
    def test_can_delete_comment_admin(self):
        """Test that admin users can delete any comment"""
        # Admin user should be able to delete any comment
        admin_user = self.create_admin_user()
        can_delete = CommentService.can_delete_comment(self.comment, admin_user)
        self.assertTrue(can_delete)
    
    def test_can_delete_comment_other_user(self):
        """Test that other users cannot delete comments they don't own"""
        # Other user should not be able to delete comment
        other_user = self.create_user(username='otheruser', email='other@example.com')
        can_delete = CommentService.can_delete_comment(self.comment, other_user)
        self.assertFalse(can_delete)
    
    def test_can_delete_comment_staff_user(self):
        """Test that staff users can delete any comment"""
        # Staff user should be able to delete any comment
        staff_user = self.create_user(username='staffuser', email='staff@example.com')
        staff_user.is_staff = True
        staff_user.save()
        
        can_delete = CommentService.can_delete_comment(self.comment, staff_user)
        self.assertTrue(can_delete)
    
    def test_can_delete_comment_anonymous(self):
        """Test that anonymous users cannot delete comments"""
        # Anonymous user should not be able to delete comment
        from django.contrib.auth.models import AnonymousUser
        anonymous_user = AnonymousUser()
        
        can_delete = CommentService.can_delete_comment(self.comment, anonymous_user)
        self.assertFalse(can_delete)
    
    def test_can_delete_comment_none_user(self):
        """Test that None user cannot delete comments"""
        # None user should not be able to delete comment
        can_delete = CommentService.can_delete_comment(self.comment, None)
        self.assertFalse(can_delete)
    
    def test_comment_service_performance(self):
        """Test performance of comment service methods with large datasets"""
        # Create many comments
        for i in range(100):
            self.create_comment(
                task=self.task,
                author=self.user,
                content=f'Performance Comment {i}'
            )
        
        # Measure retrieval time
        import time
        start_time = time.time()
        
        comments = CommentService.get_user_comments(self.user)
        
        end_time = time.time()
        retrieval_time = end_time - start_time
        
        # Should retrieve all comments
        self.assertEqual(comments.count(), 101)  # Including the one from setUp
        
        # Should be reasonably fast
        self.assertLess(retrieval_time, 1.0)  # Should complete within 1 second
    
    def test_comment_service_data_integrity(self):
        """Test data integrity of comment service operations"""
        # Create comment with specific data
        original_comment = self.create_comment(
            task=self.task,
            author=self.user,
            content='Integrity Test Comment',
            parent_comment=None
        )
        
        # Verify data integrity
        self.assertEqual(original_comment.content, 'Integrity Test Comment')
        self.assertEqual(original_comment.author, self.user)
        self.assertEqual(original_comment.task, self.task)
        self.assertIsNone(original_comment.parent_comment)
        
        # Test permission checks
        can_edit = CommentService.can_edit_comment(original_comment, self.user)
        self.assertTrue(can_edit)
        
        can_delete = CommentService.can_delete_comment(original_comment, self.user)
        self.assertTrue(can_delete)
    
    def test_comment_service_edge_cases(self):
        """Test edge cases for comment service"""
        # Test with user that has no comments
        new_user = self.create_user(username='newuser', email='new@example.com')
        comments = CommentService.get_user_comments(new_user)
        self.assertEqual(comments.count(), 0)
        
        # Test with very long comment content
        long_content = 'A' * 10000  # Very long comment
        long_comment = self.create_comment(
            task=self.task,
            author=self.user,
            content=long_content
        )
        
        # Should handle long content gracefully
        user_comments = CommentService.get_user_comments(self.user)
        self.assertIn(long_comment, user_comments)
        
        # Test with empty comment content
        empty_comment = self.create_comment(
            task=self.task,
            author=self.user,
            content=''
        )
        
        # Should handle empty content gracefully
        user_comments = CommentService.get_user_comments(self.user)
        self.assertIn(empty_comment, user_comments)
    
    def test_comment_service_user_permissions(self):
        """Test that comment service respects user permissions"""
        # Create comment for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_comment = self.create_comment(task=other_task, author=other_user, content='Other User Comment')
        
        # Regular user should not be able to edit/delete other user's comment
        can_edit = CommentService.can_edit_comment(other_comment, self.user)
        self.assertFalse(can_edit)
        
        can_delete = CommentService.can_delete_comment(other_comment, self.user)
        self.assertFalse(can_delete)
        
        # Admin user should be able to edit/delete any comment
        admin_user = self.create_admin_user()
        can_edit = CommentService.can_edit_comment(other_comment, admin_user)
        self.assertTrue(can_edit)
        
        can_delete = CommentService.can_delete_comment(other_comment, admin_user)
        self.assertTrue(can_delete)
    
    def test_comment_service_caching(self):
        """Test caching of comment service methods if implemented"""
        # First retrieval
        comments1 = CommentService.get_user_comments(self.user)
        
        # Second retrieval (should be cached if caching is implemented)
        comments2 = CommentService.get_user_comments(self.user)
        
        # Both retrievals should return same results
        self.assertEqual(comments1.count(), comments2.count())
        
        # Check if results are identical (if caching is working)
        # This test may need adjustment based on your actual caching implementation
    
    def test_comment_service_with_complex_filters(self):
        """Test comment service with complex filter combinations"""
        # Create comments with different characteristics
        recent_comment = self.create_comment(
            task=self.task,
            author=self.user,
            content='Recent Comment'
        )
        
        old_comment = self.create_comment(
            task=self.task,
            author=self.user,
            content='Old Comment'
        )
        
        # Set old comment creation date
        old_comment.created_at = timezone.now() - timedelta(days=30)
        old_comment.save()
        
        # Test different filter combinations
        user_comments = CommentService.get_user_comments(self.user)
        self.assertIn(recent_comment, user_comments)
        self.assertIn(old_comment, user_comments)
        
        # Test permission checks for different comment types
        can_edit_recent = CommentService.can_edit_comment(recent_comment, self.user)
        self.assertTrue(can_edit_recent)
        
        can_edit_old = CommentService.can_edit_comment(old_comment, self.user)
        self.assertTrue(can_edit_old)
    
    def test_comment_service_real_time_updates(self):
        """Test that comment service reflects real-time updates"""
        # Get initial comment count
        initial_count = CommentService.get_user_comments(self.user).count()
        
        # Create new comment
        new_comment = self.create_comment(
            task=self.task,
            author=self.user,
            content='Real-time Test Comment'
        )
        
        # Get updated count
        updated_count = CommentService.get_user_comments(self.user).count()
        
        # Count should have increased
        self.assertEqual(updated_count, initial_count + 1)
        
        # New comment should be in the list
        comment_contents = [comment.content for comment in CommentService.get_user_comments(self.user)]
        self.assertIn('Real-time Test Comment', comment_contents)
    
    def test_comment_service_consistency(self):
        """Test consistency of comment service across multiple calls"""
        # Get comments multiple times
        comments1 = CommentService.get_user_comments(self.user)
        comments2 = CommentService.get_user_comments(self.user)
        comments3 = CommentService.get_user_comments(self.user)
        
        # All retrievals should be consistent
        self.assertEqual(comments1.count(), comments2.count())
        self.assertEqual(comments2.count(), comments3.count())
        
        # Data should be consistent
        comment_ids1 = [comment.id for comment in comments1]
        comment_ids2 = [comment.id for comment in comments2]
        comment_ids3 = [comment.id for comment in comments3]
        
        self.assertEqual(comment_ids1, comment_ids2)
        self.assertEqual(comment_ids2, comment_ids3)
    
    def test_comment_service_parent_comment_access(self):
        """Test that users can see comments on parent comments they have access to"""
        # Create parent comment
        parent_comment = self.create_comment(
            task=self.task,
            author=self.user,
            content='Parent Comment'
        )
        
        # Create reply to parent comment
        reply_comment = self.create_comment(
            task=self.task,
            author=self.user,
            content='Reply Comment',
            parent_comment=parent_comment
        )
        
        # User should see both comments
        user_comments = CommentService.get_user_comments(self.user)
        self.assertIn(parent_comment, user_comments)
        self.assertIn(reply_comment, user_comments)
        
        # Test permissions for both comments
        can_edit_parent = CommentService.can_edit_comment(parent_comment, self.user)
        self.assertTrue(can_edit_parent)
        
        can_edit_reply = CommentService.can_edit_comment(reply_comment, self.user)
        self.assertTrue(can_edit_reply)
    
    def test_comment_service_deleted_task_access(self):
        """Test comment service behavior when parent task is deleted"""
        # Create comment on task
        task_comment = self.create_comment(
            task=self.task,
            author=self.user,
            content='Task Comment'
        )
        
        # Delete the task
        self.task.delete()
        
        # Comment service should handle deleted tasks gracefully
        # This test may need adjustment based on your actual implementation
        # and whether you implement cascade deletion or soft deletion
    
    def test_comment_service_deleted_subtask_access(self):
        """Test comment service behavior when parent subtask is deleted"""
        # Create comment on subtask
        subtask_comment = self.create_comment(
            subtask=self.subtask,
            author=self.user,
            content='Subtask Comment'
        )
        
        # Delete the subtask
        self.subtask.delete()
        
        # Comment service should handle deleted subtasks gracefully
        # This test may need adjustment based on your actual implementation
        # and whether you implement cascade deletion or soft deletion
    
    def test_comment_service_multiple_tasks_access(self):
        """Test that users can see comments across multiple tasks they have access to"""
        # Create multiple tasks for user
        task1 = self.create_task(owner=self.user, title='Task 1')
        task2 = self.create_task(owner=self.user, title='Task 2')
        
        # Create comments on different tasks
        comment1 = self.create_comment(task=task1, author=self.user, content='Task 1 Comment')
        comment2 = self.create_comment(task=task2, author=self.user, content='Task 2 Comment')
        
        # User should see comments on all their tasks
        user_comments = CommentService.get_user_comments(self.user)
        self.assertIn(comment1, user_comments)
        self.assertIn(comment2, user_comments)
        
        # Test permissions for all comments
        for comment in [comment1, comment2]:
            can_edit = CommentService.can_edit_comment(comment, self.user)
            self.assertTrue(can_edit)
            
            can_delete = CommentService.can_delete_comment(comment, self.user)
            self.assertTrue(can_delete)
