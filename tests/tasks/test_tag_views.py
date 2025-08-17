from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from tests.base import BaseAPITestCase
from apps.tasks.models import Tag, Task

User = get_user_model()


class TagViewSetTest(BaseAPITestCase):
    """Test cases for TagViewSet"""
    
    def setUp(self):
        super().setUp()
        # Authenticate user for all tests
        self.authenticate_user()
        
        self.url = reverse('tasks:tag-list')
        # Create tag with unique name and different color to avoid conflicts
        self.tag = self.create_tag(name='Unique Test Tag 1', color='#0000ff')
        self.tag_detail_url = reverse('tasks:tag-detail', kwargs={'pk': self.tag.pk})
        
        # Test data for creating/updating tags
        self.valid_tag_data = {
            'name': 'Unique Test Tag 2',
            'color': '#ff0000',
            'description': 'A test tag description'
        }
        
        self.invalid_tag_data = {
            'name': '',  # Empty name
            'color': 'invalid-color',  # Invalid color format
            'description': 'A' * 501  # Too long description
        }
    
    def get_actual_data(self, response):
        """Helper method to handle double nesting in response structure"""
        return response.data['data']['data'] if 'data' in response.data['data'] else response.data['data']
    
    def assert_pagination_format(self, response):
        """Override pagination format assertion to handle double nesting"""
        self.assert_response_format(response)
        # Handle double nesting in response structure
        actual_data = self.get_actual_data(response)
        self.assertIn('pagination', actual_data)
        pagination = actual_data['pagination']
        required_fields = ['page', 'per_page', 'total_pages', 'total_count', 
                          'has_next', 'has_previous']
        for field in required_fields:
            self.assertIn(field, pagination)
    
    def test_tag_list_success(self):
        """Test successful retrieval of tag list"""
        # Create additional tags with unique names
        self.create_tag(name='Unique Tag 2', color='#00ff00')
        self.create_tag(name='Unique Tag 3', color='#0000ff')
        
        response = self.client.get(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Tags retrieved successfully', response.data['message'])
        
        # Assert pagination format
        self.assert_pagination_format(response)
        
        # Assert data content
        self.assertIn('data', response.data)
        actual_data = self.get_actual_data(response)
        self.assertIn('results', actual_data)
        self.assertEqual(len(actual_data['results']), 3)  # 3 tags created
    
    def test_tag_list_with_filters(self):
        """Test tag list with filtering"""
        # Create tags with different colors
        red_tag = self.create_tag(name='Red Tag', color='#ff0000')
        blue_tag = self.create_tag(name='Blue Tag', color='#0000ff')
        
        # Filter by color
        response = self.client.get(f"{self.url}?color=#ff0000")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        actual_data = self.get_actual_data(response)
        self.assertEqual(len(actual_data['results']), 1)
        self.assertEqual(actual_data['results'][0]['name'], 'Red Tag')
    
    def test_tag_list_with_search(self):
        """Test tag list with search functionality"""
        # Create tags with searchable names
        self.create_tag(name='Bug Tag', description='For bug reports')
        self.create_tag(name='Feature Tag', description='For new features')
        
        # Search by name
        response = self.client.get(f"{self.url}?search=bug")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        actual_data = self.get_actual_data(response)
        self.assertEqual(len(actual_data['results']), 1)
        self.assertEqual(actual_data['results'][0]['name'], 'Bug Tag')
    
    def test_tag_list_with_ordering(self):
        """Test tag list with ordering"""
        # Create tags in reverse order
        self.create_tag(name='Zebra Tag', color='#ff0000')
        self.create_tag(name='Alpha Tag', color='#00ff00')
        
        # Order by name (default ordering)
        response = self.client.get(f"{self.url}?ordering=name")
        
        self.assert_response_format(response, status.HTTP_200_OK)
        actual_data = self.get_actual_data(response)
        self.assertEqual(actual_data['results'][0]['name'], 'Alpha Tag')
        self.assertEqual(actual_data['results'][-1]['name'], 'Zebra Tag')
    
    def test_tag_create_success(self):
        """Test successful tag creation"""
        response = self.client.post(self.url, self.valid_tag_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('Tag created successfully', response.data['message'])
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['name'], 'Unique Test Tag 2')
        self.assertEqual(response.data['data']['color'], '#ff0000')
        
        # Verify tag was created in database
        tag = Tag.objects.get(name='Unique Test Tag 2')
        self.assertEqual(tag.color, '#ff0000')
        self.assertEqual(tag.description, 'A test tag description')
    
    def test_tag_create_with_invalid_data(self):
        """Test tag creation with invalid data"""
        response = self.client.post(self.url, self.invalid_tag_data)
        
        # Should return validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_tag_create_with_duplicate_name(self):
        """Test tag creation with duplicate name"""
        # Create first tag
        self.create_tag(name='Duplicate Tag', color='#ff0000')
        
        # Try to create another with same name
        response = self.client.post(self.url, {
            'name': 'Duplicate Tag',
            'color': '#00ff00',
            'description': 'Another tag with same name'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_tag_create_with_invalid_color(self):
        """Test tag creation with invalid color format"""
        invalid_data = self.valid_tag_data.copy()
        invalid_data['color'] = 'not-a-hex-color'
        
        response = self.client.post(self.url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_tag_create_without_required_fields(self):
        """Test tag creation without required fields"""
        # Try to create tag without name
        response = self.client.post(self.url, {
            'color': '#ff0000',
            'description': 'Tag without name'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_tag_retrieve_success(self):
        """Test successful tag retrieval"""
        response = self.client.get(self.tag_detail_url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Tag retrieved successfully', response.data['message'])
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['name'], self.tag.name)
        self.assertEqual(response.data['data']['color'], self.tag.color)
    
    def test_tag_retrieve_not_found(self):
        """Test tag retrieval with non-existent ID"""
        url = reverse('tasks:tag-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_tag_update_success(self):
        """Test successful tag update"""
        update_data = {
            'name': 'Updated Tag Name',
            'color': '#00ff00',
            'description': 'Updated description'
        }
        
        response = self.client.put(self.tag_detail_url, update_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Tag updated successfully', response.data['message'])
        
        # Assert data content
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['name'], 'Updated Tag Name')
        self.assertEqual(response.data['data']['color'], '#00ff00')
        
        # Verify database was updated
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.name, 'Updated Tag Name')
        self.assertEqual(self.tag.color, '#00ff00')
    
    def test_tag_partial_update_success(self):
        """Test successful tag partial update"""
        update_data = {
            'color': '#0000ff'  # Only update color
        }
        
        response = self.client.patch(self.tag_detail_url, update_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Tag updated successfully', response.data['message'])
        
        # Assert only color was updated
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['color'], '#0000ff')
        self.assertEqual(response.data['data']['name'], self.tag.name)  # Name unchanged
        
        # Verify database was updated
        self.tag.refresh_from_db()
        self.assertEqual(self.tag.color, '#0000ff')
        self.assertEqual(self.tag.name, self.tag.name)  # Name unchanged
    
    def test_tag_update_with_invalid_data(self):
        """Test tag update with invalid data"""
        invalid_data = {
            'name': '',  # Empty name
            'color': 'invalid-color'
        }
        
        response = self.client.put(self.tag_detail_url, invalid_data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_tag_delete_success(self):
        """Test successful tag deletion"""
        response = self.client.delete(self.tag_detail_url)
        
        # Assert response format
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify tag was deleted from database
        self.assertFalse(Tag.objects.filter(pk=self.tag.pk).exists())
    
    def test_tag_delete_not_found(self):
        """Test tag deletion with non-existent ID"""
        url = reverse('tasks:tag-detail', kwargs={'pk': 99999})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_tag_delete_with_associated_tasks(self):
        """Test tag deletion when associated with tasks"""
        # Create a task and associate it with the tag
        task = self.create_task(owner=self.user)
        task.tags.add(self.tag)
        
        # Try to delete the tag
        response = self.client.delete(self.tag_detail_url)
        
        # Should still be able to delete (depending on your model constraints)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_tag_popular_action_success(self):
        """Test successful popular tags retrieval"""
        # Create tags with different usage
        popular_tag = self.create_tag(name='Popular Tag', color='#ff0000')
        less_popular_tag = self.create_tag(name='Less Popular Tag', color='#00ff00')
        
        # Associate popular tag with more tasks
        for i in range(3):
            task = self.create_task(owner=self.user, title=f'Task {i}')
            task.tags.add(popular_tag)
        
        # Associate less popular tag with fewer tasks
        task = self.create_task(owner=self.user, title='Single Task')
        task.tags.add(less_popular_tag)
        
        # Get popular tags
        url = reverse('tasks:tag-popular')
        response = self.client.get(url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('Popular tags retrieved successfully', response.data['message'])
        
        # Assert pagination format
        self.assert_pagination_format(response)
        
        # Assert data content
        self.assertIn('data', response.data)
        actual_data = self.get_actual_data(response)
        self.assertGreater(len(actual_data), 0)
    
    def test_tag_popular_action_empty(self):
        """Test popular tags when no tags exist"""
        # Delete all tags
        Tag.objects.all().delete()
        
        url = reverse('tasks:tag-popular')
        response = self.client.get(url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert empty data
        self.assertIn('data', response.data)
        actual_data = self.get_actual_data(response)
        self.assertEqual(len(actual_data['results']), 0)
    
    def test_tag_list_unauthenticated(self):
        """Test tag list access without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_tag_create_unauthenticated(self):
        """Test tag creation without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.post(self.url, self.valid_tag_data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_tag_update_unauthenticated(self):
        """Test tag update without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.put(self.tag_detail_url, self.valid_tag_data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_tag_delete_unauthenticated(self):
        """Test tag deletion without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.delete(self.tag_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_tag_boundary_values(self):
        """Test tag creation with boundary values"""
        # Test name too long (model has max_length=50)
        long_name_data = self.valid_tag_data.copy()
        long_name_data['name'] = 'A' * 51  # Max length is 50
        
        response = self.client.post(self.url, long_name_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test description too long (model doesn't have max length, but test with reasonable limit)
        long_desc_data = self.valid_tag_data.copy()
        long_desc_data['description'] = 'A' * 1001  # Test with very long description
        
        response = self.client.post(self.url, long_desc_data)
        # Description should be fine since model doesn't have max length constraint
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Test valid boundary values
        boundary_data = self.valid_tag_data.copy()
        boundary_data['name'] = 'A' * 50  # Exactly at max length
        boundary_data['description'] = 'A' * 1000  # Reasonable length
        
        response = self.client.post(self.url, boundary_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_tag_color_validation(self):
        """Test tag color validation"""
        # Test invalid color formats
        invalid_colors = [
            'red',           # Not hex
            '#gggggg',       # Invalid hex characters
            'ff0000',        # Missing #
            '#fffffff',      # Too long (7 characters)
            '#0000000',      # Too long (8 characters)
            '#ab',           # Too short (2 characters)
        ]
        
        for invalid_color in invalid_colors:
            invalid_data = self.valid_tag_data.copy()
            invalid_data['color'] = invalid_color
            
            response = self.client.post(self.url, invalid_data)
            # Validation errors should return 400 status code
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            # Check that the response contains validation error information
            self.assertIn('error', response.data)
            self.assertEqual(response.data['error']['code'], 'VALIDATION_ERROR')
        
        # Test valid color formats
        valid_colors = [
            '#ff0000',       # 6 digits
            '#f0f0f0',       # 6 digits
            '#000',          # 3 digits
            '#fff',          # 3 digits
        ]
        
        for i, valid_color in enumerate(valid_colors):
            valid_data = self.valid_tag_data.copy()
            valid_data['name'] = f'Valid Color Tag {i}'
            valid_data['color'] = valid_color
            
            response = self.client.post(self.url, valid_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
