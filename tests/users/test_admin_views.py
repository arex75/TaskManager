"""
Tests for admin user management views
"""
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock

from tests.base import BaseAPITestCase

User = get_user_model()


class AdminUserListViewTest(BaseAPITestCase):
    """Test cases for admin user list view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:admin_user_list')
        self.authenticate_admin()
        
        # Create additional test users
        self.user1 = self.create_user(
            username='user1',
            email='user1@example.com',
            first_name='User',
            last_name='One'
        )
        self.user2 = self.create_user(
            username='user2',
            email='user2@example.com',
            first_name='User',
            last_name='Two'
        )
        self.user3 = self.create_user(
            username='user3',
            email='user3@example.com',
            first_name='User',
            last_name='Three'
        )
    
    def test_admin_user_list_success(self):
        """Test successful admin user list retrieval"""
        response = self.client.get(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assert_pagination_format(response)
        
        # Assert user data
        users = response.data['data']['results']
        self.assertEqual(len(users), 5)  # 2 from BaseAPITestCase + 3 created in setUp
        
        # Assert user fields
        user_fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                      'role', 'is_active', 'is_verified', 'is_deleted', 'is_blocked']
        for user in users:
            for field in user_fields:
                self.assertIn(field, user)
    
    def test_admin_user_list_filtering(self):
        """Test admin user list with filtering"""
        # Test role filtering
        response = self.client.get(f'{self.url}?role=USER')
        
        self.assert_response_format(response, status.HTTP_200_OK)
        users = response.data['data']['results']
        for user in users:
            self.assertEqual(user['role'], 'USER')
        
        # Test active status filtering
        response = self.client.get(f'{self.url}?is_active=true')
        
        self.assert_response_format(response, status.HTTP_200_OK)
        users = response.data['data']['results']
        for user in users:
            self.assertTrue(user['is_active'])
    
    def test_admin_user_list_searching(self):
        """Test admin user list with search"""
        response = self.client.get(f'{self.url}?search=user1')
        
        self.assert_response_format(response, status.HTTP_200_OK)
        users = response.data['data']['results']
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['username'], 'user1')
    
    def test_admin_user_list_ordering(self):
        """Test admin user list with ordering"""
        response = self.client.get(f'{self.url}?ordering=username')
        
        self.assert_response_format(response, status.HTTP_200_OK)
        users = response.data['data']['results']
        
        # Assert users are ordered by username
        usernames = [user['username'] for user in users]
        self.assertEqual(usernames, sorted(usernames))
    
    def test_admin_user_list_pagination(self):
        """Test admin user list pagination"""
        # Create more users to test pagination
        for i in range(25):
            self.create_user(
                username=f'pagination_user_{i}',
                email=f'pagination_user_{i}@example.com'
            )
        
        response = self.client.get(self.url)
        
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assert_pagination_format(response)
        
        # Assert pagination data
        pagination = response.data['data']['pagination']
        self.assertIn('page', pagination)
        self.assertIn('per_page', pagination)
        self.assertIn('total_pages', pagination)
        self.assertIn('total_count', pagination)
        self.assertIn('has_next', pagination)
        self.assertIn('has_previous', pagination)
        self.assertIn('results', response.data['data'])
        
        # Assert page size (default should be 20)
        self.assertEqual(len(response.data['data']['results']), 20)
    
    def test_admin_user_list_unauthenticated(self):
        """Test admin user list without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.get(self.url)
        
        # Assert unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_admin_user_list_non_admin(self):
        """Test admin user list with non-admin user"""
        self.authenticate_user()  # Authenticate as regular user
        
        response = self.client.get(self.url)
        
        # Assert forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserDetailViewTest(BaseAPITestCase):
    """Test cases for admin user detail view"""
    
    def setUp(self):
        super().setUp()
        
        # Create a test user for detailed operations
        self.test_user = self.create_user(
            username='detail_user',
            email='detail_user@example.com',
            first_name='Detail',
            last_name='User'
        )
        self.url = reverse('users:admin_user_detail', kwargs={'pk': self.test_user.pk})
        self.authenticate_admin()
    
    def test_admin_user_detail_retrieve(self):
        """Test successful admin user detail retrieval"""
        response = self.client.get(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert user data
        user = response.data['data']
        self.assertEqual(user['username'], 'detail_user')
        self.assertEqual(user['email'], 'detail_user@example.com')
        
        # Assert user fields
        user_fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                      'role', 'is_active', 'is_verified', 'is_deleted', 'is_blocked']
        for field in user_fields:
            self.assertIn(field, user)
    
    def test_admin_user_detail_update(self):
        """Test successful admin user detail update"""
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'role': 'MANAGER'
        }
        
        response = self.client.put(self.url, update_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert updated data
        user = response.data['data']
        self.assertEqual(user['first_name'], 'Updated')
        self.assertEqual(user['last_name'], 'Name')
        self.assertEqual(user['role'], 'MANAGER')
    
    def test_admin_user_detail_partial_update(self):
        """Test successful admin user detail partial update"""
        update_data = {
            'first_name': 'Partial'
        }
        
        response = self.client.patch(self.url, update_data)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert updated data
        user = response.data['data']
        self.assertEqual(user['first_name'], 'Partial')
        self.assertEqual(user['last_name'], 'User')  # Should remain unchanged
    
    def test_admin_user_detail_delete(self):
        """Test successful admin user detail delete (soft delete)"""
        response = self.client.delete(self.url)
        
        # Assert response format - DELETE returns 204 No Content
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Assert user is soft deleted
        user = User.objects.get(pk=self.test_user.pk)
        self.assertTrue(user.is_deleted)
    
    def test_admin_user_detail_unauthenticated(self):
        """Test admin user detail without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.get(self.url)
        
        # Assert unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_admin_user_detail_non_admin(self):
        """Test admin user detail with non-admin user"""
        self.authenticate_user()  # Authenticate as regular user
        
        response = self.client.get(self.url)
        
        # Assert forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_user_detail_nonexistent_user(self):
        """Test admin user detail with nonexistent user"""
        nonexistent_url = reverse('users:admin_user_detail', kwargs={'pk': 99999})
        
        response = self.client.get(nonexistent_url)
        
        # Assert not found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AdminBlockUserViewTest(BaseAPITestCase):
    """Test cases for admin user blocking view"""
    
    def setUp(self):
        super().setUp()
        self.test_user = self.create_user(
            username='block_user',
            email='block_user@example.com'
        )
        self.url = reverse('users:admin_block_user', kwargs={'user_id': self.test_user.pk})
        self.authenticate_admin()
    
    def test_admin_block_user_success(self):
        """Test successful user blocking"""
        response = self.client.post(self.url, {'action': 'block'})
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert user is blocked
        user = User.objects.get(pk=self.test_user.pk)
        self.assertTrue(user.is_blocked)
    
    def test_admin_unblock_user_success(self):
        """Test successful user unblocking"""
        # First block the user
        self.test_user.is_blocked = True
        self.test_user.save()
        
        response = self.client.post(self.url, {'action': 'unblock'})
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Assert user is unblocked
        user = User.objects.get(pk=self.test_user.pk)
        self.assertFalse(user.is_blocked)
    
    def test_admin_block_user_invalid_action(self):
        """Test user blocking with invalid action"""
        response = self.client.post(self.url, {'action': 'invalid_action'})
        
        # Assert bad request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_admin_block_user_missing_action(self):
        """Test user blocking with missing action"""
        response = self.client.post(self.url, {})
        
        # Assert bad request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_admin_block_user_nonexistent_user(self):
        """Test user blocking with nonexistent user"""
        nonexistent_url = reverse('users:admin_block_user', kwargs={'user_id': 99999})
        
        response = self.client.post(nonexistent_url, {'action': 'block'})
        
        # Assert not found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_admin_block_user_unauthenticated(self):
        """Test user blocking without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.post(self.url, {'action': 'block'})
        
        # Assert unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_admin_block_user_non_admin(self):
        """Test user blocking with non-admin user"""
        self.authenticate_user()  # Authenticate as regular user
        
        response = self.client.post(self.url, {'action': 'block'})
        
        # Assert forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserExportViewTest(BaseAPITestCase):
    """Test cases for admin user export view"""
    
    def setUp(self):
        super().setUp()
        self.url = reverse('users:admin_user_list')  # Use the existing admin user list view
        self.authenticate_admin()
        
        # Create additional test users
        for i in range(25):
            self.create_user(
                username=f'export_user_{i}',
                email=f'export_user_{i}@example.com'
            )
    
    def test_admin_user_export_success(self):
        """Test successful admin user export"""
        response = self.client.get(self.url)
        
        # Assert response format
        self.assert_response_format(response, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assert_pagination_format(response)
        
        # Assert user data
        users = response.data['data']['results']
        self.assertEqual(len(users), 20)  # Default page size
        
        # Assert user fields
        user_fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                      'role', 'is_active', 'is_verified', 'is_deleted', 'is_blocked']
        for user in users:
            for field in user_fields:
                self.assertIn(field, user)
    
    def test_admin_user_export_filtering(self):
        """Test admin user export with filtering"""
        response = self.client.get(f'{self.url}?role=USER')
        
        self.assert_response_format(response, status.HTTP_200_OK)
        users = response.data['data']['results']
        for user in users:
            self.assertEqual(user['role'], 'USER')
    
    def test_admin_user_export_searching(self):
        """Test admin user export with search"""
        response = self.client.get(f'{self.url}?search=export_user')
        
        self.assert_response_format(response, status.HTTP_200_OK)
        users = response.data['data']['results']
        self.assertTrue(len(users) > 0)
        for user in users:
            self.assertIn('export_user', user['username'])
    
    def test_admin_user_export_ordering(self):
        """Test admin user export with ordering"""
        response = self.client.get(f'{self.url}?ordering=username')
        
        self.assert_response_format(response, status.HTTP_200_OK)
        users = response.data['data']['results']
        
        # Assert users are ordered by username
        usernames = [user['username'] for user in users]
        self.assertEqual(usernames, sorted(usernames))
    
    def test_admin_user_export_unauthenticated(self):
        """Test admin user export without authentication"""
        self.client.credentials()  # Remove authentication
        
        response = self.client.get(self.url)
        
        # Assert unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_admin_user_export_non_admin(self):
        """Test admin user export with non-admin user"""
        self.authenticate_user()  # Authenticate as regular user
        
        response = self.client.get(self.url)
        
        # Assert forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
