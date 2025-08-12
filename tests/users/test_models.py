from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
from apps.users.models import UserRole
from tests.base import BaseTestCase

User = get_user_model()

class CustomUserModelTest(BaseTestCase):
    """Test cases for CustomUser model"""
    
    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.role, UserRole.USER)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_verified)
        self.assertFalse(user.is_deleted)
        self.assertFalse(user.is_blocked)
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        user = User.objects.create_superuser(**self.admin_user_data)
        self.assertEqual(user.username, 'adminuser')
        self.assertEqual(user.role, UserRole.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
    
    def test_user_string_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.user_data)
        expected = f"{user.username} ({user.get_full_name()})"
        self.assertEqual(str(user), expected)
    
    def test_get_full_name(self):
        """Test get_full_name method"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.get_full_name(), 'Test User')
    
    def test_generate_password_reset_token(self):
        """Test password reset token generation"""
        user = User.objects.create_user(**self.user_data)
        user.generate_password_reset_token()
        
        self.assertIsNotNone(user.password_reset_token)
        self.assertIsNotNone(user.password_reset_token_expiration)
        self.assertFalse(user.is_password_reset_token_expired())
    
    def test_password_reset_token_expiration(self):
        """Test password reset token expiration"""
        user = User.objects.create_user(**self.user_data)
        user.generate_password_reset_token()
        
        # Set expiration to past
        user.password_reset_token_expiration = timezone.now() - timedelta(hours=2)
        user.save()
        
        self.assertTrue(user.is_password_reset_token_expired())
    
    def test_generate_email_verification_token(self):
        """Test email verification token generation"""
        user = User.objects.create_user(**self.user_data)
        user.generate_email_verification_token()
        
        self.assertIsNotNone(user.email_verification_token)
    
    def test_generate_email_change_token(self):
        """Test email change token generation"""
        user = User.objects.create_user(**self.user_data)
        user.generate_email_change_token()
        
        self.assertIsNotNone(user.email_change_token)
        self.assertIsNotNone(user.email_change_token_expiration)
        self.assertFalse(user.is_email_change_token_expired())
    
    def test_email_change_token_expiration(self):
        """Test email change token expiration"""
        user = User.objects.create_user(**self.user_data)
        user.generate_email_change_token()
        
        # Set expiration to past
        user.email_change_token_expiration = timezone.now() - timedelta(hours=2)
        user.save()
        
        self.assertTrue(user.is_email_change_token_expired())
    
    def test_soft_delete(self):
        """Test soft delete functionality"""
        user = User.objects.create_user(**self.user_data)
        admin_user = User.objects.create_superuser(**self.admin_user_data)
        
        user.soft_delete(deleted_by_user=admin_user)
        
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deleted_at)
        self.assertEqual(user.deleted_by, admin_user)
    
    def test_restore_user(self):
        """Test user restoration"""
        user = User.objects.create_user(**self.user_data)
        admin_user = User.objects.create_superuser(**self.admin_user_data)
        
        user.soft_delete(deleted_by_user=admin_user)
        user.restore()
        
        self.assertFalse(user.is_deleted)
        self.assertTrue(user.is_active)
        self.assertIsNone(user.deleted_at)
        self.assertIsNone(user.deleted_by)
    
    def test_block_user(self):
        """Test user blocking"""
        user = User.objects.create_user(**self.user_data)
        user.block_user()
        
        self.assertTrue(user.is_blocked)
        self.assertFalse(user.is_active)
    
    def test_unblock_user(self):
        """Test user unblocking"""
        user = User.objects.create_user(**self.user_data)
        user.block_user()
        user.unblock_user()
        
        self.assertFalse(user.is_blocked)
        self.assertTrue(user.is_active)
    
    def test_is_deleted_or_blocked_property(self):
        """Test is_deleted_or_blocked property"""
        user = User.objects.create_user(**self.user_data)
        
        # Initially not deleted or blocked
        self.assertFalse(user.is_deleted_or_blocked)
        
        # Test when deleted
        user.soft_delete()
        self.assertTrue(user.is_deleted_or_blocked)
        
        # Test when blocked
        user.restore()
        user.block_user()
        self.assertTrue(user.is_deleted_or_blocked)
    
    def test_clean_tokens(self):
        """Test token cleaning"""
        user = User.objects.create_user(**self.user_data)
        user.generate_password_reset_token()
        user.generate_email_change_token()
        
        # Set tokens to expired
        user.password_reset_token_expiration = timezone.now() - timedelta(hours=2)
        user.email_change_token_expiration = timezone.now() - timedelta(hours=2)
        user.save()
        
        user.clean_tokens()
        
        self.assertIsNone(user.password_reset_token)
        self.assertIsNone(user.password_reset_token_expiration)
        self.assertIsNone(user.email_change_token)
        self.assertIsNone(user.email_change_token_expiration)
    
    def test_clean_tokens_with_no_tokens(self):
        """Test token cleaning when no tokens exist"""
        user = User.objects.create_user(**self.user_data)
        user.clean_tokens()  # Should not raise any errors
        
        self.assertIsNone(user.password_reset_token)
        self.assertIsNone(user.email_change_token)
    
    def test_clean_tokens_with_valid_tokens(self):
        """Test token cleaning with valid (non-expired) tokens"""
        user = User.objects.create_user(**self.user_data)
        user.generate_password_reset_token()
        user.generate_email_change_token()
        
        user.clean_tokens()  # Should not clean valid tokens
        
        self.assertIsNotNone(user.password_reset_token)
        self.assertIsNotNone(user.email_change_token)
    
    def test_soft_delete_without_deleted_by(self):
        """Test soft delete without specifying who deleted the user"""
        user = User.objects.create_user(**self.user_data)
        user.soft_delete()
        
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deleted_at)
        self.assertIsNone(user.deleted_by)
    
    def test_soft_delete_already_deleted_user(self):
        """Test soft delete on already deleted user"""
        user = User.objects.create_user(**self.user_data)
        user.soft_delete()
        original_deleted_at = user.deleted_at
        
        # Try to soft delete again
        user.soft_delete()
        
        self.assertTrue(user.is_deleted)
        self.assertEqual(user.deleted_at, original_deleted_at)  # Should not change
    
    def test_restore_not_deleted_user(self):
        """Test restore on user that is not deleted"""
        user = User.objects.create_user(**self.user_data)
        user.restore()  # Should not raise any errors
        
        self.assertFalse(user.is_deleted)
        self.assertTrue(user.is_active)
    
    def test_block_already_blocked_user(self):
        """Test block on already blocked user"""
        user = User.objects.create_user(**self.user_data)
        user.block_user()
        user.block_user()  # Should not raise any errors
        
        self.assertTrue(user.is_blocked)
        self.assertFalse(user.is_active)
    
    def test_unblock_not_blocked_user(self):
        """Test unblock on user that is not blocked"""
        user = User.objects.create_user(**self.user_data)
        user.unblock_user()  # Should not raise any errors
        
        self.assertFalse(user.is_blocked)
        self.assertTrue(user.is_active)
    
    def test_token_generation_multiple_times(self):
        """Test generating tokens multiple times"""
        user = User.objects.create_user(**self.user_data)
        
        # Generate tokens multiple times
        user.generate_password_reset_token()
        first_token = user.password_reset_token
        first_expiration = user.password_reset_token_expiration
        
        user.generate_password_reset_token()
        second_token = user.password_reset_token
        second_expiration = user.password_reset_token_expiration
        
        # Tokens should be different
        self.assertNotEqual(first_token, second_token)
        self.assertNotEqual(first_expiration, second_expiration)
    
    def test_token_expiration_edge_cases(self):
        """Test token expiration edge cases"""
        user = User.objects.create_user(**self.user_data)
        user.generate_password_reset_token()
        
        # Test exactly expired (edge case)
        user.password_reset_token_expiration = timezone.now()
        user.save()
        
        # Should be considered expired
        self.assertTrue(user.is_password_reset_token_expired())
    
    def test_user_role_validation(self):
        """Test user role validation"""
        user = User.objects.create_user(**self.user_data)
        
        # Test invalid role
        with self.assertRaises(ValidationError):
            user.role = 'INVALID_ROLE'
            user.full_clean()
    
    def test_user_fields_after_soft_delete_and_restore(self):
        """Test user fields after soft delete and restore cycle"""
        user = User.objects.create_user(**self.user_data)
        original_created_at = user.created_at
        original_updated_at = user.updated_at
        
        user.soft_delete()
        user.restore()
        
        # Timestamps should remain the same
        self.assertEqual(user.created_at, original_created_at)
        self.assertGreater(user.updated_at, original_updated_at)  # Should be updated
    
    def test_user_fields_after_block_and_unblock(self):
        """Test user fields after block and unblock cycle"""
        user = User.objects.create_user(**self.user_data)
        original_created_at = user.created_at
        original_updated_at = user.updated_at
        
        user.block_user()
        user.unblock_user()
        
        # Timestamps should remain the same
        self.assertEqual(user.created_at, original_created_at)
        self.assertGreater(user.updated_at, original_updated_at)  # Should be updated
    
    def test_user_role_choices(self):
        """Test user role choices"""
        self.assertEqual(UserRole.ADMIN, 'ADMIN')
        self.assertEqual(UserRole.USER, 'USER')
        self.assertEqual(UserRole.MANAGER, 'MANAGER')
    
    def test_user_creation_with_required_fields(self):
        """Test user creation with minimal required fields"""
        minimal_user_data = {
            'username': 'minimaluser',
            'email': 'minimal@example.com',
            'password': 'minimalpass123',
        }
        
        user = User.objects.create_user(**minimal_user_data)
        self.assertEqual(user.username, 'minimaluser')
        self.assertEqual(user.email, 'minimal@example.com')
        self.assertEqual(user.role, UserRole.USER)  # Default role
    
    def test_user_creation_with_all_fields(self):
        """Test user creation with all optional fields"""
        full_user_data = self.user_data.copy()
        full_user_data.update({
            'bio': 'This is a test bio',
            'phone_number': '+1234567890',
            'role': UserRole.MANAGER,
        })
        
        user = User.objects.create_user(**full_user_data)
        self.assertEqual(user.bio, 'This is a test bio')
        self.assertEqual(user.phone_number, '+1234567890')
        self.assertEqual(user.role, UserRole.MANAGER)
    
    # Negative and Edge Cases
    
    def test_user_creation_without_required_fields(self):
        """Test user creation fails without required fields"""
        # Test without username - should fail
        with self.assertRaises(TypeError):
            User.objects.create_user(
                email='test@example.com',
                password='testpass123'
            )
        
        # Test without email - should fail
        with self.assertRaises(TypeError):
            User.objects.create_user(
                username='testuser',
                password='testpass123'
            )
        
        # Test without password - should work (password is optional in our manager)
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
    
    def test_user_creation_with_invalid_email(self):
        """Test user creation with invalid email format"""
        invalid_email_data = self.user_data.copy()
        invalid_email_data['email'] = 'invalid-email'
        
        with self.assertRaises(ValidationError):
            user = User.objects.create_user(**invalid_email_data)
            user.full_clean()
    
    def test_user_creation_with_duplicate_username(self):
        """Test user creation fails with duplicate username"""
        User.objects.create_user(**self.user_data)
        
        duplicate_data = self.user_data.copy()
        duplicate_data['email'] = 'different@example.com'
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(**duplicate_data)
    
    def test_user_creation_with_duplicate_email(self):
        """Test user creation fails with duplicate email"""
        User.objects.create_user(**self.user_data)
        
        duplicate_data = self.user_data.copy()
        duplicate_data['username'] = 'differentuser'
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(**duplicate_data)
    
    def test_user_creation_with_empty_strings(self):
        """Test user creation with empty string values"""
        empty_data = self.user_data.copy()
        empty_data.update({
            'name': '',
            'last_name': '',
            'bio': '',
            'phone_number': '',
        })
        
        user = User.objects.create_user(**empty_data)
        self.assertEqual(user.name, '')
        self.assertEqual(user.last_name, '')
        self.assertEqual(user.bio, '')
        self.assertEqual(user.phone_number, '')
    
    def test_user_creation_with_very_long_fields(self):
        """Test user creation with maximum length fields"""
        long_data = self.user_data.copy()
        long_data.update({
            'name': 'A' * 255,  # Max length for CharField
            'last_name': 'B' * 255,
            'bio': 'C' * 500,  # Max length for bio
            'phone_number': 'D' * 15,  # Max length for phone
        })
        
        user = User.objects.create_user(**long_data)
        self.assertEqual(len(user.name), 255)
        self.assertEqual(len(user.last_name), 255)
        self.assertEqual(len(user.bio), 500)
        self.assertEqual(len(user.phone_number), 15)
    
    def test_user_creation_with_special_characters(self):
        """Test user creation with special characters in fields"""
        special_data = self.user_data.copy()
        special_data.update({
            'name': 'José María',
            'last_name': 'O\'Connor-Smith',
            'bio': 'User with special chars: @#$%^&*()',
            'phone_number': '+1-234-567-8900',
        })
        
        user = User.objects.create_user(**special_data)
        self.assertEqual(user.name, 'José María')
        self.assertEqual(user.last_name, 'O\'Connor-Smith')
        self.assertEqual(user.bio, 'User with special chars: @#$%^&*()')
        self.assertEqual(user.phone_number, '+1-234-567-8900')
    
    def test_user_creation_with_unicode_characters(self):
        """Test user creation with unicode characters"""
        unicode_data = self.user_data.copy()
        unicode_data.update({
            'name': '张三',
            'last_name': '李四',
            'bio': '用户使用中文',
        })
        
        user = User.objects.create_user(**unicode_data)
        self.assertEqual(user.name, '张三')
        self.assertEqual(user.last_name, '李四')
        self.assertEqual(user.bio, '用户使用中文')
    
    def test_user_creation_with_none_values(self):
        """Test user creation with None values for optional fields"""
        none_data = self.user_data.copy()
        none_data.update({
            'bio': None,
            'phone_number': None,
        })
        
        user = User.objects.create_user(**none_data)
        self.assertIsNone(user.bio)
        self.assertIsNone(user.phone_number)
    
    def test_user_creation_with_whitespace_only(self):
        """Test user creation with whitespace-only values"""
        whitespace_data = self.user_data.copy()
        whitespace_data.update({
            'name': '   ',
            'last_name': '\t\n',
            'bio': '   ',
        })
        
        user = User.objects.create_user(**whitespace_data)
        self.assertEqual(user.name, '   ')
        self.assertEqual(user.last_name, '\t\n')
        self.assertEqual(user.bio, '   ')
    
    def test_user_creation_with_extreme_values(self):
        """Test user creation with extreme field values"""
        extreme_data = self.user_data.copy()
        extreme_data.update({
            'name': 'A',  # Single character
            'last_name': 'B',
            'bio': 'Single char bio',  # Very short bio
        })
        
        user = User.objects.create_user(**extreme_data)
        self.assertEqual(user.name, 'A')
        self.assertEqual(user.last_name, 'B')
        self.assertEqual(user.bio, 'Single char bio')
    
    def test_user_creation_with_mixed_case(self):
        """Test user creation with mixed case in fields"""
        mixed_case_data = self.user_data.copy()
        mixed_case_data.update({
            'name': 'JoHn',
            'last_name': 'dOe',
            'email': 'John.Doe@EXAMPLE.COM',
        })
        
        user = User.objects.create_user(**mixed_case_data)
        self.assertEqual(user.name, 'JoHn')
        self.assertEqual(user.last_name, 'dOe')
        self.assertEqual(user.email, 'John.Doe@EXAMPLE.COM')
    
    def test_user_creation_with_numbers_in_text_fields(self):
        """Test user creation with numbers in text fields"""
        number_data = self.user_data.copy()
        number_data.update({
            'name': 'User123',
            'last_name': '456',
            'bio': 'Bio with numbers 789',
        })
        
        user = User.objects.create_user(**number_data)
        self.assertEqual(user.name, 'User123')
        self.assertEqual(user.last_name, '456')
        self.assertEqual(user.bio, 'Bio with numbers 789')
    
    def test_user_creation_with_sql_injection_attempts(self):
        """Test user creation with SQL injection attempt strings"""
        sql_data = self.user_data.copy()
        sql_data.update({
            'name': "'; DROP TABLE users; --",
            'last_name': "'; DELETE FROM users; --",
            'bio': "'; UPDATE users SET is_active = 0; --",
        })
        
        user = User.objects.create_user(**sql_data)
        self.assertEqual(user.name, "'; DROP TABLE users; --")
        self.assertEqual(user.last_name, "'; DELETE FROM users; --")
        self.assertEqual(user.bio, "'; UPDATE users SET is_active = 0; --")
    
    def test_user_creation_with_html_tags(self):
        """Test user creation with HTML tags in fields"""
        html_data = self.user_data.copy()
        html_data.update({
            'name': '<script>alert("xss")</script>',
            'last_name': '<b>Bold</b>',
            'bio': '<p>Paragraph</p>',
        })
        
        user = User.objects.create_user(**html_data)
        self.assertEqual(user.name, '<script>alert("xss")</script>')
        self.assertEqual(user.last_name, '<b>Bold</b>')
        self.assertEqual(user.bio, '<p>Paragraph</p>')
    
    def test_user_creation_with_very_long_username(self):
        """Test user creation with very long username"""
        long_username_data = self.user_data.copy()
        long_username_data['username'] = 'a' * 150  # Django's default max length
        
        user = User.objects.create_user(**long_username_data)
        self.assertEqual(len(user.username), 150)
    
    def test_user_creation_with_very_long_email(self):
        """Test user creation with very long email"""
        long_email_data = self.user_data.copy()
        long_email_data['email'] = 'a' * 200 + '@example.com'
        
        user = User.objects.create_user(**long_email_data)
        self.assertEqual(len(user.email), 200 + len('@example.com'))
    
    def test_user_creation_with_complex_password(self):
        """Test user creation with complex password"""
        complex_password_data = self.user_data.copy()
        complex_password_data['password'] = 'ComplexP@ssw0rd123!@#$%^&*()'
        
        user = User.objects.create_user(**complex_password_data)
        # Password should be hashed, so we can't check the exact value
        self.assertNotEqual(user.password, 'ComplexP@ssw0rd123!@#$%^&*()')
    
    def test_user_creation_with_minimal_password(self):
        """Test user creation with minimal password"""
        minimal_password_data = self.user_data.copy()
        minimal_password_data['password'] = '123'  # Very short password
        
        user = User.objects.create_user(**minimal_password_data)
        self.assertNotEqual(user.password, '123')  # Should be hashed
