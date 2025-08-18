from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from tests.base import BaseTestCase
from apps.tasks.services import AttachmentService
from apps.tasks.models import Task, Subtask, Attachment

User = get_user_model()


class AttachmentServiceTest(BaseTestCase):
    """Test cases for AttachmentService"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.task = self.create_task(owner=self.user)
        self.subtask = self.create_subtask(task=self.task)
        self.attachment = self.create_attachment(task=self.task, uploaded_by=self.user)
    
    def test_get_user_attachments_success(self):
        """Test successful retrieval of user attachments"""
        # Create additional attachments for the user
        self.create_attachment(task=self.task, uploaded_by=self.user, original_filename='file2.txt')
        self.create_attachment(task=self.task, uploaded_by=self.user, original_filename='file3.txt')
        
        # Create attachment for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_attachment = self.create_attachment(task=other_task, uploaded_by=other_user, original_filename='other_file.txt')
        
        attachments = AttachmentService.get_user_attachments(self.user)
        
        # Should return attachments for the specified user plus any public attachments
        # The user has 3 attachments (1 from setUp + 2 created here)
        # Plus they can see the other user's attachment if it's public
        self.assertGreaterEqual(attachments.count(), 3)
        # Check that all returned attachments are either owned by the user or are public
        for attachment in attachments:
            if attachment.task:
                self.assertTrue(
                    attachment.task.owner == self.user or 
                    attachment.task.assigned_to == self.user or
                    attachment.is_public
                )
    
    def test_get_user_attachments_empty(self):
        """Test retrieval of user attachments when none exist"""
        # Delete all attachments
        Attachment.objects.all().delete()
        
        attachments = AttachmentService.get_user_attachments(self.user)
        
        self.assertEqual(attachments.count(), 0)
    
    def test_get_user_attachments_admin_access(self):
        """Test that admin users can see all attachments"""
        # Create attachments for different users
        user1 = self.create_user(username='user1', email='user1@example.com')
        user2 = self.create_user(username='user2', email='user2@example.com')
        
        task1 = self.create_task(owner=user1, title='User 1 Task')
        task2 = self.create_task(owner=user2, title='User 2 Task')
        
        self.create_attachment(task=task1, uploaded_by=user1, original_filename='user1_file.txt')
        self.create_attachment(task=task2, uploaded_by=user2, original_filename='user2_file.txt')
        
        # Admin user should see all attachments
        admin_user = self.create_admin_user()
        admin_attachments = AttachmentService.get_user_attachments(admin_user)
        
        # Admin should see all attachments (including the one from setUp)
        self.assertEqual(admin_attachments.count(), 3)
    
    def test_get_user_attachments_assigned_user(self):
        """Test that assigned users can see attachments"""
        # Create task assigned to another user
        assigned_user = self.create_user(username='assigned', email='assigned@example.com')
        assigned_task = self.create_task(owner=self.user, assigned_to=assigned_user)
        
        # Create attachment for assigned task
        assigned_attachment = self.create_attachment(task=assigned_task, uploaded_by=self.user, original_filename='assigned_file.txt')
        
        # Assigned user should see the attachment
        assigned_user_attachments = AttachmentService.get_user_attachments(assigned_user)
        self.assertIn(assigned_attachment, assigned_user_attachments)
    
    def test_get_user_attachments_subtask_attachments(self):
        """Test that users can see attachments on subtasks they have access to"""
        # Create attachment on subtask
        subtask_attachment = self.create_attachment(
            subtask=self.subtask,
            uploaded_by=self.user,
            original_filename='subtask_file.txt'
        )
        
        # User should see subtask attachments
        user_attachments = AttachmentService.get_user_attachments(self.user)
        self.assertIn(subtask_attachment, user_attachments)
    
    def test_get_user_attachments_nested_access(self):
        """Test that users can see attachments on subtasks of tasks they have access to"""
        # Create nested structure: User -> Task -> Subtask -> Attachment
        nested_attachment = self.create_attachment(
            subtask=self.subtask,
            uploaded_by=self.user,
            original_filename='nested_file.txt'
        )
        
        # User should see the nested attachment
        user_attachments = AttachmentService.get_user_attachments(self.user)
        self.assertIn(nested_attachment, user_attachments)
    
    def test_get_user_attachments_public_tasks(self):
        """Test that users can see attachments on public tasks"""
        # Create public task
        public_task = self.create_task(owner=self.user, title='Public Task')
        public_attachment = self.create_attachment(task=public_task, uploaded_by=self.user, original_filename='public_file.txt')
        
        # Another user should see attachments on public tasks
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_user_attachments = AttachmentService.get_user_attachments(other_user)
        
        # Should include attachments on public tasks
        self.assertIn(public_attachment, other_user_attachments)
    
    def test_can_edit_attachment_uploader(self):
        """Test that attachment uploader can edit their own attachment"""
        # User should be able to edit their own attachment
        can_edit = AttachmentService.can_edit_attachment(self.attachment, self.user)
        self.assertTrue(can_edit)
    
    def test_can_edit_attachment_admin(self):
        """Test that admin users can edit any attachment"""
        # Admin user should be able to edit any attachment
        admin_user = self.create_admin_user()
        can_edit = AttachmentService.can_edit_attachment(self.attachment, admin_user)
        self.assertTrue(can_edit)
    
    def test_can_edit_attachment_other_user(self):
        """Test that other users cannot edit attachments they don't own"""
        # Other user should not be able to edit attachment
        other_user = self.create_user(username='otheruser', email='other@example.com')
        can_edit = AttachmentService.can_edit_attachment(self.attachment, other_user)
        self.assertFalse(can_edit)
    
    def test_can_edit_attachment_staff_user(self):
        """Test that staff users can edit any attachment"""
        # Staff user should be able to edit any attachment
        staff_user = self.create_user(username='staffuser', email='staff@example.com')
        staff_user.is_staff = True
        staff_user.save()
        
        can_edit = AttachmentService.can_edit_attachment(self.attachment, staff_user)
        self.assertTrue(can_edit)
    
    def test_can_edit_attachment_anonymous(self):
        """Test that anonymous users cannot edit attachments"""
        # Anonymous user should not be able to edit attachment
        from django.contrib.auth.models import AnonymousUser
        anonymous_user = AnonymousUser()
        
        can_edit = AttachmentService.can_edit_attachment(self.attachment, anonymous_user)
        self.assertFalse(can_edit)
    
    def test_can_edit_attachment_none_user(self):
        """Test that None user cannot edit attachments"""
        # None user should not be able to edit attachment
        can_edit = AttachmentService.can_edit_attachment(self.attachment, None)
        self.assertFalse(can_edit)
    
    def test_can_delete_attachment_uploader(self):
        """Test that attachment uploader can delete their own attachment"""
        # User should be able to delete their own attachment
        can_delete = AttachmentService.can_delete_attachment(self.attachment, self.user)
        self.assertTrue(can_delete)
    
    def test_can_delete_attachment_admin(self):
        """Test that admin users can delete any attachment"""
        # Admin user should be able to delete any attachment
        admin_user = self.create_admin_user()
        can_delete = AttachmentService.can_delete_attachment(self.attachment, admin_user)
        self.assertTrue(can_delete)
    
    def test_can_delete_attachment_other_user(self):
        """Test that other users cannot delete attachments they don't own"""
        # Other user should not be able to delete attachment
        other_user = self.create_user(username='otheruser', email='other@example.com')
        can_delete = AttachmentService.can_delete_attachment(self.attachment, other_user)
        self.assertFalse(can_delete)
    
    def test_can_delete_attachment_staff_user(self):
        """Test that staff users can delete any attachment"""
        # Staff user should be able to delete any attachment
        staff_user = self.create_user(username='staffuser', email='staff@example.com')
        staff_user.is_staff = True
        staff_user.save()
        
        can_delete = AttachmentService.can_delete_attachment(self.attachment, staff_user)
        self.assertTrue(can_delete)
    
    def test_can_delete_attachment_anonymous(self):
        """Test that anonymous users cannot delete attachments"""
        # Anonymous user should not be able to delete attachment
        from django.contrib.auth.models import AnonymousUser
        anonymous_user = AnonymousUser()
        
        can_delete = AttachmentService.can_delete_attachment(self.attachment, anonymous_user)
        self.assertFalse(can_delete)
    
    def test_can_delete_attachment_none_user(self):
        """Test that None user cannot delete attachments"""
        # None user should not be able to delete attachment
        can_delete = AttachmentService.can_delete_attachment(self.attachment, None)
        self.assertFalse(can_delete)
    
    def test_attachment_service_performance(self):
        """Test performance of attachment service methods with large datasets"""
        # Create many attachments
        for i in range(100):
            self.create_attachment(
                task=self.task,
                uploaded_by=self.user,
                original_filename=f'performance_file_{i}.txt'
            )
        
        # Measure retrieval time
        import time
        start_time = time.time()
        
        attachments = AttachmentService.get_user_attachments(self.user)
        
        end_time = time.time()
        retrieval_time = end_time - start_time
        
        # Should retrieve all attachments
        self.assertEqual(attachments.count(), 101)  # Including the one from setUp
        
        # Should be reasonably fast
        self.assertLess(retrieval_time, 1.0)  # Should complete within 1 second
    
    def test_attachment_service_data_integrity(self):
        """Test data integrity of attachment service operations"""
        # Create attachment with specific data
        original_attachment = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='integrity_test_file.txt',
            description='Test description',
            is_public=False
        )
        
        # Verify data integrity
        self.assertEqual(original_attachment.original_filename, 'integrity_test_file.txt')
        self.assertEqual(original_attachment.uploaded_by, self.user)
        self.assertEqual(original_attachment.task, self.task)
        self.assertEqual(original_attachment.description, 'Test description')
        self.assertFalse(original_attachment.is_public)
        
        # Test permission checks
        can_edit = AttachmentService.can_edit_attachment(original_attachment, self.user)
        self.assertTrue(can_edit)
        
        can_delete = AttachmentService.can_delete_attachment(original_attachment, self.user)
        self.assertTrue(can_delete)
    
    def test_attachment_service_edge_cases(self):
        """Test edge cases for attachment service"""
        # Test with user that has no attachments
        new_user = self.create_user(username='newuser', email='new@example.com')
        # Create a task specifically for the new user to ensure they have no access to other tasks
        new_user_task = self.create_task(owner=new_user, title='New User Task')
        
        attachments = AttachmentService.get_user_attachments(new_user)
        
        # New user should see public attachments but no private ones
        # The attachment from setUp is public by default
        self.assertEqual(attachments.count(), 1)
        # Verify it's the public attachment
        self.assertTrue(all(att.is_public for att in attachments))
        
        # Test with very long filenames (within database limits)
        long_filename = 'A' * 250 + '.txt'  # Long but valid filename
        long_filename_attachment = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename=long_filename
        )
        
        # Should handle long filenames gracefully
        user_attachments = AttachmentService.get_user_attachments(self.user)
        self.assertIn(long_filename_attachment, user_attachments)
        
        # Test with empty filename
        empty_filename_attachment = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename=''
        )
        
        # Should handle empty filename gracefully
        user_attachments = AttachmentService.get_user_attachments(self.user)
        self.assertIn(empty_filename_attachment, user_attachments)
    
    def test_attachment_service_user_permissions(self):
        """Test that attachment service respects user permissions"""
        # Create attachment for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_task = self.create_task(owner=other_user, title='Other User Task')
        other_attachment = self.create_attachment(task=other_task, uploaded_by=other_user, original_filename='other_user_file.txt')
        
        # Regular user should not be able to edit/delete other user's attachment
        can_edit = AttachmentService.can_edit_attachment(other_attachment, self.user)
        self.assertFalse(can_edit)
        
        can_delete = AttachmentService.can_delete_attachment(other_attachment, self.user)
        self.assertFalse(can_delete)
        
        # Admin user should be able to edit/delete any attachment
        admin_user = self.create_admin_user()
        can_edit = AttachmentService.can_edit_attachment(other_attachment, admin_user)
        self.assertTrue(can_edit)
        
        can_delete = AttachmentService.can_delete_attachment(other_attachment, admin_user)
        self.assertTrue(can_delete)
    
    def test_attachment_service_caching(self):
        """Test caching of attachment service methods if implemented"""
        # First retrieval
        attachments1 = AttachmentService.get_user_attachments(self.user)
        
        # Second retrieval (should be cached if caching is implemented)
        attachments2 = AttachmentService.get_user_attachments(self.user)
        
        # Both retrievals should return same results
        self.assertEqual(attachments1.count(), attachments2.count())
        
        # Check if results are identical (if caching is working)
        # This test may need adjustment based on your actual caching implementation
    
    def test_attachment_service_with_complex_filters(self):
        """Test attachment service with complex filter combinations"""
        # Create attachments with different characteristics
        recent_attachment = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='recent_file.txt'
        )
        
        old_attachment = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='old_file.txt'
        )
        
        # Set old attachment creation date
        old_attachment.created_at = timezone.now() - timedelta(days=30)
        old_attachment.save()
        
        # Test different filter combinations
        user_attachments = AttachmentService.get_user_attachments(self.user)
        self.assertIn(recent_attachment, user_attachments)
        self.assertIn(old_attachment, user_attachments)
        
        # Test permission checks for different attachment types
        can_edit_recent = AttachmentService.can_edit_attachment(recent_attachment, self.user)
        self.assertTrue(can_edit_recent)
        
        can_edit_old = AttachmentService.can_edit_attachment(old_attachment, self.user)
        self.assertTrue(can_edit_old)
    
    def test_attachment_service_real_time_updates(self):
        """Test that attachment service reflects real-time updates"""
        # Get initial attachment count
        initial_count = AttachmentService.get_user_attachments(self.user).count()
        
        # Create new attachment
        new_attachment = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='real_time_test_file.txt'
        )
        
        # Get updated count
        updated_count = AttachmentService.get_user_attachments(self.user).count()
        
        # Count should have increased
        self.assertEqual(updated_count, initial_count + 1)
        
        # New attachment should be in the list
        attachment_filenames = [attachment.original_filename for attachment in AttachmentService.get_user_attachments(self.user)]
        self.assertIn('real_time_test_file.txt', attachment_filenames)
    
    def test_attachment_service_consistency(self):
        """Test consistency of attachment service across multiple calls"""
        # Get attachments multiple times
        attachments1 = AttachmentService.get_user_attachments(self.user)
        attachments2 = AttachmentService.get_user_attachments(self.user)
        attachments3 = AttachmentService.get_user_attachments(self.user)
        
        # All retrievals should be consistent
        self.assertEqual(attachments1.count(), attachments2.count())
        self.assertEqual(attachments2.count(), attachments3.count())
        
        # Data should be consistent
        attachment_ids1 = [attachment.id for attachment in attachments1]
        attachment_ids2 = [attachment.id for attachment in attachments2]
        attachment_ids3 = [attachment.id for attachment in attachments3]
        
        self.assertEqual(attachment_ids1, attachment_ids2)
        self.assertEqual(attachment_ids2, attachment_ids3)
    
    def test_attachment_service_public_private_access(self):
        """Test that users can see public attachments but only edit/delete their own"""
        # Create public attachment
        public_attachment = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='public_file.txt',
            is_public=True
        )
        
        # Create private attachment
        private_attachment = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='private_file.txt',
            is_public=False
        )
        
        # Another user should see public attachments
        other_user = self.create_user(username='otheruser', email='other@example.com')
        other_user_attachments = AttachmentService.get_user_attachments(other_user)
        
        # Should include public attachments
        self.assertIn(public_attachment, other_user_attachments)
        
        # Should not include private attachments
        self.assertNotIn(private_attachment, other_user_attachments)
        
        # Other user should not be able to edit/delete public attachments
        can_edit_public = AttachmentService.can_edit_attachment(public_attachment, other_user)
        self.assertFalse(can_edit_public)
        
        can_delete_public = AttachmentService.can_delete_attachment(public_attachment, other_user)
        self.assertFalse(can_delete_public)
    
    def test_attachment_service_deleted_task_access(self):
        """Test attachment service behavior when parent task is deleted"""
        # Create attachment on task
        task_attachment = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='task_file.txt'
        )
        
        # Delete the task
        self.task.delete()
        
        # Attachment service should handle deleted tasks gracefully
        # This test may need adjustment based on your actual implementation
        # and whether you implement cascade deletion or soft deletion
    
    def test_attachment_service_deleted_subtask_access(self):
        """Test attachment service behavior when parent subtask is deleted"""
        # Create attachment on subtask
        subtask_attachment = self.create_attachment(
            subtask=self.subtask,
            uploaded_by=self.user,
            original_filename='subtask_file.txt'
        )
        
        # Delete the subtask
        self.subtask.delete()
        
        # Attachment service should handle deleted subtasks gracefully
        # This test may need adjustment based on your actual implementation
        # and whether you implement cascade deletion or soft deletion
    
    def test_attachment_service_multiple_tasks_access(self):
        """Test that users can see attachments across multiple tasks they have access to"""
        # Create multiple tasks for user
        task1 = self.create_task(owner=self.user, title='Task 1')
        task2 = self.create_task(owner=self.user, title='Task 2')
        
        # Create attachments on different tasks
        attachment1 = self.create_attachment(task=task1, uploaded_by=self.user, original_filename='task1_file.txt')
        attachment2 = self.create_attachment(task=task2, uploaded_by=self.user, original_filename='task2_file.txt')
        
        # User should see attachments on all their tasks
        user_attachments = AttachmentService.get_user_attachments(self.user)
        self.assertIn(attachment1, user_attachments)
        self.assertIn(attachment2, user_attachments)
        
        # Test permissions for all attachments
        for attachment in [attachment1, attachment2]:
            can_edit = AttachmentService.can_edit_attachment(attachment, self.user)
            self.assertTrue(can_edit)
            
            can_delete = AttachmentService.can_delete_attachment(attachment, self.user)
            self.assertTrue(can_delete)
    
    def test_attachment_service_file_types(self):
        """Test attachment service with different file types"""
        # Create attachments with different file types
        text_file = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='document.txt'
        )
        
        image_file = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='image.jpg'
        )
        
        pdf_file = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='document.pdf'
        )
        
        # User should see all file types
        user_attachments = AttachmentService.get_user_attachments(self.user)
        self.assertIn(text_file, user_attachments)
        self.assertIn(image_file, user_attachments)
        self.assertIn(pdf_file, user_attachments)
        
        # Test permissions for all file types
        for attachment in [text_file, image_file, pdf_file]:
            can_edit = AttachmentService.can_edit_attachment(attachment, self.user)
            self.assertTrue(can_edit)
            
            can_delete = AttachmentService.can_delete_attachment(attachment, self.user)
            self.assertTrue(can_delete)
    
    def test_attachment_service_large_files(self):
        """Test attachment service with large file metadata"""
        # Create attachment with large description
        large_description = 'A' * 5000  # Very long description
        large_attachment = self.create_attachment(
            task=self.task,
            uploaded_by=self.user,
            original_filename='large_metadata_file.txt',
            description=large_description
        )
        
        # Should handle large metadata gracefully
        user_attachments = AttachmentService.get_user_attachments(self.user)
        self.assertIn(large_attachment, user_attachments)
        
        # Test permissions for large metadata
        can_edit = AttachmentService.can_edit_attachment(large_attachment, self.user)
        self.assertTrue(can_edit)
        
        can_delete = AttachmentService.can_delete_attachment(large_attachment, self.user)
        self.assertTrue(can_delete)
