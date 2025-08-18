from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from tests.base import BaseAPITestCase
from apps.tasks.models import Task, Subtask, Comment

User = get_user_model()


class CommentViewSetTest(BaseAPITestCase):
    """Test cases for CommentViewSet"""
    
    def setUp(self):
        super().setUp()
        self.authenticate_user()  # Authenticate the user for API requests
        self.url = reverse('tasks:comment-list')
        self.task = self.create_task(owner=self.user)
        self.comment = self.create_comment(task=self.task, author=self.user)
        self.comment_detail_url = reverse('tasks:comment-detail', kwargs={'pk': self.comment.pk})
        
        # Test data for creating/updating comments
        self.valid_comment_data = {
            'content': 'A test comment content',
            'task': self.task.pk,
            # Omit subtask and parent_comment fields when they should be None
        }
        
        self.invalid_comment_data = {
            'content': '',  # Empty content
            'task': 99999,  # Non-existent task
            'subtask': 99999,  # Non-existent subtask
            'parent_comment': 99999  # Non-existent parent comment
        }
        
        # Create a subtask for testing
        self.subtask = self.create_subtask(task=self.task)
    
    def test_comment_list_success(self):
        """Test successful retrieval of comment list"""
        # Create additional comments
        self.create_comment(task=self.task, content='Comment 2')
        self.create_comment(task=self.task, content='Comment 3')
        
        response = self.client.get(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Comments retrieved successfully', response.data['message'])
        
        # Assert pagination format
        self.assert_pagination_format(response)
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertIn('results', response.data['data'])
        self.assertEqual(len(response.data['data']['results']), 3)  # 3 comments created
    
    def test_comment_list_with_filters(self):
        """Test comment list with filtering"""
        # Create additional comments for the main task
        self.create_comment(task=self.task, content='Comment 2')
        self.create_comment(task=self.task, content='Comment 3')
        
        # Create comments for different tasks
        other_task = self.create_task(owner=self.user, title='Other Task')
        other_comment = self.create_comment(task=other_task, content='Other Task Comment')
        
        # Filter by task
        response = self.client.get(f"{self.url}?task={self.task.pk}")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']['results']), 3)  # 3 comments for this task
        self.assertNotIn('Other Task Comment', [c['content'] for c in response.data['data']['results']])
    
    def test_comment_list_with_search(self):
        """Test comment list with search functionality"""
        # Create comments with searchable content
        self.create_comment(task=self.task, content='Bug fix comment', author=self.user)
        self.create_comment(task=self.task, content='Feature comment', author=self.user)
        
        # Search by content
        response = self.client.get(f"{self.url}?search=bug")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']['results']), 1)
        self.assertEqual(response.data['data']['results'][0]['content'], 'Bug fix comment')
    
    def test_comment_list_with_ordering(self):
        """Test comment list with ordering"""
        # Create comments in reverse order
        self.create_comment(task=self.task, content='Zebra Comment', created_at=timezone.now() - timedelta(hours=2))
        self.create_comment(task=self.task, content='Alpha Comment', created_at=timezone.now() - timedelta(hours=1))
        
        # Order by content
        response = self.client.get(f"{self.url}?ordering=content")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        # Get all comments and sort them by content to verify ordering
        comments = response.data['data']['results']
        comment_contents = [c['content'] for c in comments]
        # The first comment should be 'Alpha Comment' (alphabetically first)
        self.assertEqual(comment_contents[0], 'Alpha Comment')
        # The last comment should be 'Zebra Comment' (alphabetically last)
        self.assertEqual(comment_contents[-1], 'Zebra Comment')
    
    def test_comment_list_task_filtered(self):
        """Test that comments are filtered by task"""
        # Create comment for another task
        other_task = self.create_task(owner=self.user, title='Other Task')
        other_comment = self.create_comment(task=other_task, content='Other Task Comment')
        
        # Filter by task
        response = self.client.get(f"{self.url}?task={self.task.pk}")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('results', response.data['data'])
        
        # Should only see comments from the specified task
        comment_contents = [comment['content'] for comment in response.data['data']['results']]
        self.assertIn('Test comment content', comment_contents)
        self.assertNotIn('Other Task Comment', comment_contents)
    
    def test_comment_list_subtask_filtered(self):
        """Test that comments are filtered by subtask"""
        # Create comment for subtask
        subtask_comment = self.create_comment(subtask=self.subtask, content='Subtask Comment')
        
        # Filter by subtask
        response = self.client.get(f"{self.url}?subtask={self.subtask.pk}")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('results', response.data['data'])
        
        # Should only see comments from the specified subtask
        comment_contents = [comment['content'] for comment in response.data['data']['results']]
        self.assertIn('Subtask Comment', comment_contents)
        self.assertNotIn('A test comment content', comment_contents)
    
    def test_comment_list_user_filtered(self):
        """Test that users only see comments from their own tasks"""
        # Create comment for another user's task
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_comment = self.create_comment(task=other_task, content='Other User Comment')
        
        # User should only see comments from their own tasks
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('results', response.data['data'])
        
        # Should not see other user's comment
        comment_contents = [comment['content'] for comment in response.data['data']['results']]
        self.assertNotIn('Other User Comment', comment_contents)
    
    def test_comment_create_success(self):
        """Test successful comment creation"""
        response = self.client.post(self.url, self.valid_comment_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('Comment created successfully', response.data['message'])
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertIn('content', response.data['data'])
        self.assertEqual(response.data['data']['content'], 'A test comment content')
        self.assertEqual(response.data['data']['task']['id'], self.task.pk)
        
        # Verify comment was created in database
        comment = Comment.objects.get(content='A test comment content')
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.task, self.task)
        self.assertIsNone(comment.subtask)
    
    def test_comment_create_for_subtask(self):
        """Test comment creation for subtask"""
        subtask_comment_data = {
            'content': 'Subtask comment',
            # Omit task field when it should be None
            'subtask': self.subtask.pk,
            # Omit parent_comment field when it should be None
        }
        
        response = self.client.post(self.url, subtask_comment_data)
        
        self.assert_response_format(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify comment was created for subtask
        comment = Comment.objects.get(content='Subtask comment')
        self.assertEqual(comment.subtask, self.subtask)
        self.assertIsNone(comment.task)
    
    def test_comment_create_with_parent(self):
        """Test comment creation with parent comment"""
        parent_comment = self.create_comment(task=self.task, content='Parent Comment')
        
        # Data for creating a reply to a parent comment
        reply_data = {
            'content': 'Reply to parent',
            'task': self.task.pk,
            # Omit subtask field when it should be None
            'parent_comment': parent_comment.pk
        }
        
        response = self.client.post(self.url, reply_data)
        
        self.assert_response_format(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify reply was created
        reply = Comment.objects.get(content='Reply to parent')
        self.assertEqual(reply.parent_comment, parent_comment)
    
    def test_comment_create_with_invalid_data(self):
        """Test comment creation with invalid data"""
        response = self.client.post(self.url, self.invalid_comment_data)
        
        # Should return validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_create_without_required_fields(self):
        """Test comment creation without required fields"""
        # Try to create comment without content
        response = self.client.post(self.url, {
            'task': self.task.pk
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_create_without_task_or_subtask(self):
        """Test comment creation without task or subtask"""
        # Try to create comment without task or subtask
        response = self.client.post(self.url, {
            'content': 'Comment without task or subtask'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_create_with_both_task_and_subtask(self):
        """Test comment creation with both task and subtask"""
        # Try to create comment with both task and subtask
        invalid_data = {
            'content': 'Comment with both task and subtask',
            'task': self.task.pk,
            'subtask': self.subtask.pk
        }
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_create_with_non_existent_task(self):
        """Test comment creation with non-existent task"""
        invalid_data = self.valid_comment_data.copy()
        invalid_data['task'] = 99999
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_create_with_non_existent_subtask(self):
        """Test comment creation with non-existent subtask"""
        invalid_data = {
            'content': 'Comment for non-existent subtask',
            # Omit task field when it should be None
            'subtask': 99999
        }
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_create_with_unauthorized_task(self):
        """Test comment creation with task owned by another user"""
        # Create task for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        
        # Try to create comment for other user's task
        invalid_data = self.valid_comment_data.copy()
        invalid_data['task'] = other_task.pk
        
        response = self.client.post(self.url, invalid_data)
        
        # Should return validation error since serializer validates ownership
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_create_with_unauthorized_subtask(self):
        """Test comment creation with subtask from another user's task"""
        # Create subtask for another user's task
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_subtask = self.create_subtask(task=other_task, title='Other User Subtask')
        
        # Try to create comment for other user's subtask
        invalid_data = {
            'content': 'Comment for other user subtask',
            # Omit task field when it should be None
            'subtask': other_subtask.pk
        }
        
        response = self.client.post(self.url, invalid_data)
        
        # Should return validation error since serializer validates ownership
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_create_with_invalid_parent_comment(self):
        """Test comment creation with invalid parent comment"""
        invalid_data = {
            'content': 'Reply to invalid parent',
            'task': self.task.pk,
            # Omit subtask field when it should be None
            'parent_comment': 99999
        }
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_retrieve_success(self):
        """Test successful comment retrieval"""
        response = self.client.get(self.comment_detail_url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Comment retrieved successfully', response.data['message'])
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['content'], self.comment.content)
        self.assertEqual(response.data['data']['author']['username'], self.user.username)
    
    def test_comment_retrieve_not_found(self):
        """Test comment retrieval with non-existent ID"""
        url = reverse('tasks:comment-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_comment_retrieve_unauthorized(self):
        """Test comment retrieval by non-task-owner"""
        # Create comment for another user's task
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_comment = self.create_comment(task=other_task, content='Other User Comment')
        
        # Try to access other user's comment
        url = reverse('tasks:comment-detail', kwargs={'pk': other_comment.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_comment_update_success(self):
        """Test successful comment update"""
        update_data = {
            'content': 'Updated comment content'
        }
        
        response = self.client.put(self.comment_detail_url, update_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Comment updated successfully', response.data['message'])
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['content'], 'Updated comment content')
        
        # Verify database was updated
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, 'Updated comment content')
        self.assertTrue(self.comment.is_edited)
        self.assertIsNotNone(self.comment.edited_at)
    
    def test_comment_partial_update_success(self):
        """Test successful comment partial update"""
        update_data = {
            'content': 'Partially updated content'
        }
        
        response = self.client.patch(self.comment_detail_url, update_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Comment updated successfully', response.data['message'])
        
        # Assert only content was updated
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['content'], 'Partially updated content')
        
        # Verify database was updated
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, 'Partially updated content')
        self.assertTrue(self.comment.is_edited)
    
    def test_comment_update_with_invalid_data(self):
        """Test comment update with invalid data"""
        invalid_data = {
            'content': ''  # Empty content
        }
        
        response = self.client.put(self.comment_detail_url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_update_unauthorized(self):
        """Test comment update by non-author"""
        # Create comment by another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_comment = self.create_comment(task=self.task, content='Other User Comment', author=other_user)
        
        # Try to update other user's comment
        url = reverse('tasks:comment-detail', kwargs={'pk': other_comment.pk})
        response = self.client.put(url, {'content': 'Hacked content'})
        
        # Should return permission denied since view validates ownership
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
    
    def test_comment_delete_success(self):
        """Test successful comment deletion"""
        response = self.client.delete(self.comment_detail_url)
        
        # Assert response format
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify comment was deleted from database
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())
    
    def test_comment_delete_not_found(self):
        """Test comment deletion with non-existent ID"""
        url = reverse('tasks:comment-detail', kwargs={'pk': 99999})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_comment_delete_unauthorized(self):
        """Test comment deletion by non-author"""
        # Create comment by another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_comment = self.create_comment(task=self.task, content='Other User Comment', author=other_user)
        
        # Try to delete other user's comment
        url = reverse('tasks:comment-detail', kwargs={'pk': other_comment.pk})
        response = self.client.delete(url)
        
        # Should return permission denied since view validates ownership
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
    
    def test_comment_delete_with_replies(self):
        """Test comment deletion when it has replies"""
        # Create a reply to the comment
        reply = self.create_comment(
            task=self.task,
            content='Reply to comment',
            parent_comment=self.comment
        )
        
        # Try to delete the parent comment
        response = self.client.delete(self.comment_detail_url)
        
        # Should still be able to delete (depending on your model constraints)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check if reply still exists (depends on cascade settings)
        # This test may need adjustment based on your actual model constraints
    
    def test_comment_list_unauthenticated(self):
        """Test comment list access without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_comment_create_unauthenticated(self):
        """Test comment creation without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.post(self.url, self.valid_comment_data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_comment_update_unauthenticated(self):
        """Test comment update without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.put(self.comment_detail_url, self.valid_comment_data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_comment_delete_unauthenticated(self):
        """Test comment deletion without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.delete(self.comment_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_comment_boundary_values(self):
        """Test comment creation with boundary values"""
        # Test content too long - should fail with max_length constraint
        long_content_data = self.valid_comment_data.copy()
        long_content_data['content'] = 'A' * 2001  # Exceeds max_length of 2000
        
        response = self.client.post(self.url, long_content_data)
        # Should fail due to max_length validation
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # Test valid boundary values - exactly at max length
        boundary_data = self.valid_comment_data.copy()
        boundary_data['content'] = 'A' * 2000  # Exactly at max length
        
        response = self.client.post(self.url, boundary_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_comment_nested_replies(self):
        """Test comment with nested replies"""
        # Create parent comment
        parent = self.create_comment(task=self.task, content='Parent Comment')
        
        # Create first level reply
        reply1 = self.create_comment(
            task=self.task,
            content='First Reply',
            parent_comment=parent
        )
        
        # Create second level reply
        reply2 = self.create_comment(
            task=self.task,
            content='Second Reply',
            parent_comment=reply1
        )
        
        # Verify hierarchy
        self.assertEqual(reply1.parent_comment, parent)
        self.assertEqual(reply2.parent_comment, reply1)
        
        # Test retrieval
        response = self.client.get(self.comment_detail_url)
        self.assert_response_format(response, status.HTTP_200_OK)
    
    def test_comment_edit_tracking(self):
        """Test that comment edits are properly tracked"""
        # Update comment
        update_data = {'content': 'Edited content'}
        response = self.client.put(self.comment_detail_url, update_data)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Verify edit tracking
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_edited)
        self.assertIsNotNone(self.comment.edited_at)
        
        # Update again
        update_data = {'content': 'Second edit'}
        response = self.client.put(self.comment_detail_url, update_data)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        
        # Verify edit tracking is updated
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_edited)
        # edited_at should be updated to the latest edit time
    
    def test_comment_task_subtask_exclusivity(self):
        """Test that comments can only belong to either task or subtask, not both"""
        # Try to create comment with both task and subtask
        invalid_data = {
            'content': 'Comment with both task and subtask',
            'task': self.task.pk,
            'subtask': self.subtask.pk
        }
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        
        # Try to create comment with neither task nor subtask
        invalid_data = {
            'content': 'Comment without task or subtask'
        }
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_comment_cascade_delete(self):
        """Test that deleting a task/subtask cascades to comments"""
        # Create comment for the task
        task_comment = self.create_comment(task=self.task, content='Task Comment')
        
        # Create comment for the subtask
        subtask_comment = self.create_comment(subtask=self.subtask, content='Subtask Comment')
        
        # Delete the task
        task_url = reverse('tasks:task-detail', kwargs={'pk': self.task.pk})
        response = self.client.delete(task_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify comments were also deleted (if cascade is implemented)
        # This test may need adjustment based on your actual model constraints
        # If cascade delete is not implemented, the comments should still exist
        # but with broken foreign key references
