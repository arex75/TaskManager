from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from tests.base import BaseTestCase
from apps.tasks.services import TagService
from apps.tasks.models import Tag, Task

User = get_user_model()


class TagServiceTest(BaseTestCase):
    """Test cases for TagService"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.tag = self.create_tag()
        self.task = self.create_task(owner=self.user)
    
    def test_get_or_create_tag_new(self):
        """Test creating a new tag"""
        tag, created = TagService.get_or_create_tag(
            name='New Tag',
            color='#ff0000',
            description='A new tag'
        )
        
        self.assertTrue(created)
        self.assertEqual(tag.name, 'New Tag')
        self.assertEqual(tag.color, '#ff0000')
        self.assertEqual(tag.description, 'A new tag')
    
    def test_get_or_create_tag_existing(self):
        """Test getting an existing tag"""
        # Create a tag first
        existing_tag = self.create_tag(name='Existing Tag', color='#00ff00')
        
        # Try to get or create the same tag
        tag, created = TagService.get_or_create_tag(
            name='Existing Tag',
            color='#ff0000',  # Different color
            description='Different description'
        )
        
        self.assertFalse(created)
        self.assertEqual(tag.id, existing_tag.id)
        self.assertEqual(tag.name, 'Existing Tag')
        # Should keep original values, not update them
        self.assertEqual(tag.color, '#00ff00')
    
    def test_get_or_create_tag_case_insensitive(self):
        """Test that tag names are case insensitive"""
        # Create a tag with lowercase
        existing_tag = self.create_tag(name='lowercase tag', color='#00ff00')
        
        # Try to get or create with different case
        tag, created = TagService.get_or_create_tag(
            name='LOWERCASE TAG',
            color='#ff0000'
        )
        
        self.assertFalse(created)
        self.assertEqual(tag.id, existing_tag.id)
        self.assertEqual(tag.name, 'lowercase tag')  # Should keep original case
    
    def test_get_popular_tags_basic(self):
        """Test basic retrieval of popular tags"""
        # Create tags with different usage
        popular_tag = self.create_tag(name='Popular Tag', color='#ff0000')
        less_popular_tag = self.create_tag(name='Less Popular Tag', color='#00ff00')
        
        # Associate popular tag with more tasks
        for i in range(3):
            task = self.create_task(owner=self.user, title=f'Task with popular tag {i}')
            task.tags.add(popular_tag)
        
        # Associate less popular tag with fewer tasks
        task = self.create_task(owner=self.user, title='Task with less popular tag')
        task.tags.add(less_popular_tag)
        
        popular_tags = TagService.get_popular_tags(limit=10)
        
        # Should return tags ordered by popularity
        self.assertGreater(len(popular_tags), 0)
        
        # Popular tag should appear first
        first_tag = popular_tags.first()
        self.assertEqual(first_tag.name, 'Popular Tag')
        self.assertEqual(first_tag.task_count, 3)
    
    def test_get_popular_tags_with_limit(self):
        """Test retrieval of popular tags with limit"""
        # Create many tags
        for i in range(15):
            tag = self.create_tag(name=f'Tag {i}', color=f'#{i:06x}')
            task = self.create_task(owner=self.user, title=f'Task {i}')
            task.tags.add(tag)
        
        # Test with different limits
        limit_5 = TagService.get_popular_tags(limit=5)
        self.assertEqual(limit_5.count(), 5)
        
        limit_10 = TagService.get_popular_tags(limit=10)
        self.assertEqual(limit_10.count(), 10)
        
        limit_20 = TagService.get_popular_tags(limit=20)
        # Should return all available tags when limit > available
        self.assertGreaterEqual(limit_20.count(), 15)
    
    def test_get_popular_tags_empty(self):
        """Test retrieval of popular tags when none exist"""
        # Delete all tags
        Tag.objects.all().delete()
        
        popular_tags = TagService.get_popular_tags()
        
        self.assertEqual(popular_tags.count(), 0)
    
    def test_get_popular_tags_ordering(self):
        """Test that popular tags are properly ordered by usage count"""
        # Create tags with different usage counts
        tag_1 = self.create_tag(name='Tag 1', color='#ff0000')
        tag_2 = self.create_tag(name='Tag 2', color='#00ff00')
        tag_3 = self.create_tag(name='Tag 3', color='#0000ff')
        
        # Give tag_2 the most usage
        for i in range(5):
            task = self.create_task(owner=self.user, title=f'Task 2 {i}')
            task.tags.add(tag_2)
        
        # Give tag_1 medium usage
        for i in range(3):
            task = self.create_task(owner=self.user, title=f'Task 1 {i}')
            task.tags.add(tag_1)
        
        # Give tag_3 least usage
        task = self.create_task(owner=self.user, title='Task 3')
        task.tags.add(tag_3)
        
        popular_tags = TagService.get_popular_tags(limit=10)
        
        # Should be ordered by task_count descending
        self.assertEqual(popular_tags[0].name, 'Tag 2')
        self.assertEqual(popular_tags[0].task_count, 5)
        self.assertEqual(popular_tags[1].name, 'Tag 1')
        self.assertEqual(popular_tags[1].task_count, 3)
        self.assertEqual(popular_tags[2].name, 'Tag 3')
        self.assertEqual(popular_tags[2].task_count, 1)
    
    def test_get_popular_tags_unused_tags(self):
        """Test that unused tags are included with 0 task count"""
        # Create some unused tags
        unused_tag1 = self.create_tag(name='Unused Tag 1', color='#999999')
        unused_tag2 = self.create_tag(name='Unused Tag 2', color='#888888')
        
        # Create a used tag
        used_tag = self.create_tag(name='Used Tag', color='#ff0000')
        task = self.create_task(owner=self.user, title='Task with tag')
        task.tags.add(used_tag)
        
        popular_tags = TagService.get_popular_tags(limit=10)
        
        # Should include all tags
        self.assertGreaterEqual(popular_tags.count(), 3)
        
        # Find the unused tags
        unused_tags = [tag for tag in popular_tags if tag.task_count == 0]
        self.assertGreaterEqual(len(unused_tags), 2)
    
    def test_get_popular_tags_default_limit(self):
        """Test that default limit of 10 is applied"""
        # Create more than 10 tags
        for i in range(15):
            tag = self.create_tag(name=f'Default Limit Tag {i}', color=f'#{i:06x}')
            task = self.create_task(owner=self.user, title=f'Task {i}')
            task.tags.add(tag)
        
        popular_tags = TagService.get_popular_tags()  # No limit specified
        
        self.assertEqual(popular_tags.count(), 10)
    
    def test_validate_tag_data_valid(self):
        """Test validation of valid tag data"""
        errors = TagService.validate_tag_data('Valid Tag', '#ff0000')
        
        self.assertEqual(errors, {})
    
    def test_validate_tag_data_empty_name(self):
        """Test validation with empty name"""
        errors = TagService.validate_tag_data('', '#ff0000')
        
        self.assertIn('name', errors)
        self.assertEqual(errors['name'], ['Tag name is required.'])
    
    def test_validate_tag_data_whitespace_name(self):
        """Test validation with whitespace-only name"""
        errors = TagService.validate_tag_data('   ', '#ff0000')
        
        self.assertIn('name', errors)
        self.assertEqual(errors['name'], ['Tag name is required.'])
    
    def test_validate_tag_data_none_name(self):
        """Test validation with None name"""
        errors = TagService.validate_tag_data(None, '#ff0000')
        
        self.assertIn('name', errors)
        self.assertEqual(errors['name'], ['Tag name is required.'])
    
    def test_validate_tag_data_invalid_color_format(self):
        """Test validation with invalid color format"""
        errors = TagService.validate_tag_data('Valid Tag', 'red')
        
        self.assertIn('color', errors)
        self.assertEqual(errors['color'], ['Color must be a valid hex color code (e.g., #007bff).'])
    
    def test_validate_tag_data_invalid_color_length(self):
        """Test validation with invalid color length"""
        errors = TagService.validate_tag_data('Valid Tag', '#ff00')
        
        self.assertIn('color', errors)
        self.assertEqual(errors['color'], ['Color must be a valid hex color code (e.g., #007bff).'])
    
    def test_validate_tag_data_no_hash_prefix(self):
        """Test validation with color missing hash prefix"""
        errors = TagService.validate_tag_data('Valid Tag', 'ff0000')
        
        self.assertIn('color', errors)
        self.assertEqual(errors['color'], ['Color must be a valid hex color code (e.g., #007bff).'])
    
    def test_validate_tag_data_empty_color(self):
        """Test validation with empty color (should be valid)"""
        errors = TagService.validate_tag_data('Valid Tag', '')
        
        self.assertEqual(errors, {})
    
    def test_validate_tag_data_none_color(self):
        """Test validation with None color (should be valid)"""
        errors = TagService.validate_tag_data('Valid Tag', None)
        
        self.assertEqual(errors, {})
    
    def test_validate_tag_data_multiple_errors(self):
        """Test validation with multiple errors"""
        errors = TagService.validate_tag_data('', 'invalid')
        
        self.assertIn('name', errors)
        self.assertIn('color', errors)
        self.assertEqual(len(errors), 2)
    
    def test_get_popular_tags_with_deleted_tasks(self):
        """Test popular tags when some tasks are deleted"""
        # Create tag with multiple tasks
        tag = self.create_tag(name='Test Tag Deleted', color='#ff0000')
        
        for i in range(5):
            task = self.create_task(owner=self.user, title=f'Task {i}')
            task.tags.add(tag)
        
        # Verify initial task count
        popular_tags = TagService.get_popular_tags(limit=10)
        tag_in_list = next((t for t in popular_tags if t.id == tag.id), None)
        self.assertIsNotNone(tag_in_list)
        self.assertEqual(tag_in_list.task_count, 5)
        
        # Delete some tasks
        Task.objects.filter(title__startswith='Task').delete()
        
        # Get popular tags again
        popular_tags_after = TagService.get_popular_tags(limit=10)
        tag_in_list_after = next((t for t in popular_tags_after if t.id == tag.id), None)
        self.assertIsNotNone(tag_in_list_after)
        self.assertEqual(tag_in_list_after.task_count, 0)  # All tasks deleted
    
    def test_get_popular_tags_performance(self):
        """Test performance of popular tags retrieval with large datasets"""
        # Create many tags with many tasks
        for i in range(50):
            tag = self.create_tag(name=f'Performance Tag {i}', color=f'#{i:06x}')
            for j in range(10):  # Each tag gets 10 tasks
                task = self.create_task(owner=self.user, title=f'Task {i}-{j}')
                task.tags.add(tag)
        
        # Measure retrieval time
        import time
        start_time = time.time()
        
        popular_tags = TagService.get_popular_tags(limit=20)
        
        end_time = time.time()
        retrieval_time = end_time - start_time
        
        # Should retrieve tags within limit
        self.assertEqual(popular_tags.count(), 20)
        
        # Should be reasonably fast
        self.assertLess(retrieval_time, 1.0)  # Should complete within 1 second
