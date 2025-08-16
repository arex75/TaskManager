"""
Tests for users app utility functions
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from unittest.mock import patch, MagicMock

from core.utils import (
    validate_phone_number, validate_username_format, validate_password_strength,
    validate_email_domain, validate_name_format, validate_bio_length,
    validate_profile_image_size, validate_profile_image_format, clean_phone_number,
    validate_profile_image_dimensions, validate_social_media_links
)

from tests.base import BaseTestCase


class PhoneNumberValidationTest(TestCase):
    """Test cases for phone number validation utilities"""
    
    def test_validate_phone_number_valid_formats(self):
        """Test valid phone number formats"""
        valid_numbers = [
            '+1-555-123-4567',
            '+44 20 7946 0958',
            '+81-3-1234-5678',
            '+49 30 12345678',
            '+61 2 8765 4321',
            '555-123-4567',
            '(555) 123-4567',
            '555.123.4567',
            '555 123 4567',
            '+1234567890',
            '1234567890'
        ]
        
        for number in valid_numbers:
            with self.subTest(number=number):
                try:
                    validate_phone_number(number)
                except ValidationError as e:
                    self.fail(f"Phone number {number} should be valid")
    
    def test_validate_phone_number_invalid_formats(self):
        """Test invalid phone number formats"""
        invalid_numbers = [
            '123',  # Too short
            '12345678901234567890',  # Too long
            'abc-def-ghi',  # Contains letters
            '',  # Empty
            '   ',  # Whitespace only
            'invalid',
            '555-123-4567-extra',  # Extra characters
        ]
        
        for number in invalid_numbers:
            with self.subTest(number=number):
                with self.assertRaises(ValidationError):
                    validate_phone_number(number)
    
    def test_clean_phone_number(self):
        """Test phone number cleaning functionality"""
        test_cases = [
            ('+1-555-123-4567', '+15551234567'),
            ('(555) 123-4567', '+15551234567'),  # US numbers get +1 prefix
            ('555.123.4567', '+15551234567'),     # US numbers get +1 prefix
            ('555 123 4567', '+15551234567'),     # US numbers get +1 prefix
            ('+44 20 7946 0958', '+442079460958'),
            ('+81-3-1234-5678', '+81312345678'),
            ('+49 30 12345678', '+493012345678'),
        ]
        
        for input_number, expected_output in test_cases:
            with self.subTest(input=input_number):
                cleaned = clean_phone_number(input_number)
                self.assertEqual(cleaned, expected_output)
    
    def test_clean_phone_number_invalid_input(self):
        """Test phone number cleaning with invalid input"""
        invalid_inputs = [
            'invalid',
            '123',
            'abc',
            '',
            '   ',
        ]
        
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                
                with self.assertRaises(ValueError):
                    clean_phone_number(invalid_input)


class UsernameValidationTest(TestCase):
    """Test cases for username validation utilities"""
    
    def test_validate_username_format_valid(self):
        """Test valid username formats"""
        valid_usernames = [
            'john_doe',
            'john123',
            'john.doe',
            'john-doe',
            'johnDoe',
            'john_doe_123',
            'j',
            'a' * 30,  # Maximum length
            'user123',
            'test_user',
            'admin_2023',
        ]
        
        for username in valid_usernames:
            with self.subTest(username=username):
                try:
                    validate_username_format(username)
                except ValidationError as e:
                    self.fail(f"Username {username} should be valid")
    
    def test_validate_username_format_invalid(self):
        """Test invalid username formats"""
        invalid_usernames = [
            '',  # Empty
            '   ',  # Whitespace only
            'john doe',  # Contains space
            'john@doe',  # Contains @
            'john#doe',  # Contains #
            'john$doe',  # Contains $
            'john%doe',  # Contains %
            'john^doe',  # Contains ^
            'john&doe',  # Contains &
            'john*doe',  # Contains *
            'john(doe',  # Contains (
            'john)doe',  # Contains )
            'john+doe',  # Contains +
            'john=doe',  # Contains =
            'john[doe',  # Contains [
            'john]doe',  # Contains ]
            'john{doe',  # Contains {
            'john}doe',  # Contains }
            'john|doe',  # Contains |
            'john\\doe',  # Contains \
            'john/doe',  # Contains /
            'john<doe',  # Contains <
            'john>doe',  # Contains >
            'john?doe',  # Contains ?
            'john!doe',  # Contains !
            'john~doe',  # Contains ~
            'john`doe',  # Contains `
            'a' * 31,  # Too long
            '123',  # Starts with number
            '_john',  # Starts with underscore
            '-john',  # Starts with dash
            '.john',  # Starts with dot
            'john_',  # Ends with underscore
            'john-',  # Ends with dash
            'john.',  # Ends with dot
        ]
        
        for username in invalid_usernames:
            with self.subTest(username=username):
                with self.assertRaises(ValidationError):
                    validate_username_format(username)


class PasswordValidationTest(TestCase):
    """Test cases for password validation utilities"""
    
    def test_validate_password_strength_strong(self):
        """Test strong password validation"""
        strong_passwords = [
            'StrongPass123!',
            'MySecureP@ssw0rd',
            'C0mpl3x!P@ss',
            'Str0ng#P@ss',
            'S3cur3$P@ss',
            'P@ssw0rd!2023',
            'MyP@ss!sS3cur3',
            'C0mpl3x!P@ssw0rd',
        ]
        
        for password in strong_passwords:
            with self.subTest(password=password):
                try:
                    validate_password_strength(password)
                except ValidationError as e:
                    self.fail(f"Password {password} should be strong")
    
    def test_validate_password_strength_weak(self):
        """Test weak password validation"""
        weak_passwords = [
            'weak',  # Too short
            'password',  # Common word
            '123456',  # Only numbers
            'abcdef',  # Only letters
            'abc123',  # No special characters
            'pass',  # Too short
            'qwerty',  # Common pattern
            'admin',  # Common word
            'letmein',  # Common word
            'password123',  # Common pattern
            '123456789',  # Sequential numbers
            'aaaaaaaa',  # Repeated characters
        ]
        
        for password in weak_passwords:
            with self.subTest(password=password):
                with self.assertRaises(ValidationError):
                    validate_password_strength(password)
    
    def test_validate_password_strength_requirements(self):
        """Test password strength requirements"""
        # Test minimum length
        with self.assertRaises(ValidationError):
            validate_password_strength('Short1!')
        
        # Test uppercase requirement
        with self.assertRaises(ValidationError):
            validate_password_strength('lowercase123!')
        
        # Test lowercase requirement
        with self.assertRaises(ValidationError):
            validate_password_strength('UPPERCASE123!')
        
        # Test number requirement
        with self.assertRaises(ValidationError):
            validate_password_strength('NoNumbers!')
        
        # Test special character requirement
        with self.assertRaises(ValidationError):
            validate_password_strength('NoSpecialChars123')


class EmailDomainValidationTest(TestCase):
    """Test cases for email domain validation utilities"""
    
    def test_validate_email_domain_valid(self):
        """Test valid email domains"""
        valid_emails = [
            'user@gmail.com',
            'user@yahoo.com',
            'user@hotmail.com',
            'user@outlook.com',
            'user@company.com',
            'user@domain.org',
            'user@website.net',
            'user@business.co.uk',
            'user@startup.io',
            'user@tech.ai',
        ]
        
        for email in valid_emails:
            with self.subTest(email=email):
                try:
                    validate_email_domain(email)
                except ValidationError as e:
                    self.fail(f"Email {email} should be valid")
    
    def test_validate_email_domain_invalid(self):
        """Test invalid email domains"""
        invalid_emails = [
            'user@10minutemail.com',  # Disposable email
            'user@tempmail.org',  # Disposable email
            'user@throwaway.com',  # Disposable email
            'user@guerrillamail.com',  # Disposable email
            'user@mailinator.com',  # Disposable email
            'user@yopmail.com',  # Disposable email
            'user@getnada.com',  # Disposable email
            'user@sharklasers.com',  # Disposable email
            'user@grr.la',  # Disposable email
            'user@pokemail.net',  # Disposable email
        ]
        
        for email in invalid_emails:
            with self.subTest(email=email):
                with self.assertRaises(ValidationError):
                    validate_email_domain(email)
    
    def test_validate_email_domain_edge_cases(self):
        """Test email domain validation edge cases"""
        # Test with invalid email format
        with self.assertRaises(ValidationError):
            validate_email_domain('invalid-email')
        
        # Test with empty email
        with self.assertRaises(ValidationError):
            validate_email_domain('')
        
        # Test with None
        with self.assertRaises(ValidationError):
            validate_email_domain(None)


class NameValidationTest(TestCase):
    """Test cases for name validation utilities"""
    
    def test_validate_name_format_valid(self):
        """Test valid name formats"""
        valid_names = [
            'John',
            'Mary',
            'Jean-Pierre',
            'O\'Connor',
            'van der Berg',
            'McDonald',
            'Smith-Jones',
            'Li',
            'García',
            'Müller',
            'O\'Reilly',
            'van Gogh',
            'de la Cruz',
            'St. John',
            'MacLeod',
        ]
        
        for name in valid_names:
            with self.subTest(username=name):
                try:
                    validate_name_format(name)
                except ValidationError as e:
                    self.fail(f"Name {name} should be valid")
    
    def test_validate_name_format_invalid(self):
        """Test invalid name formats"""
        invalid_names = [
            '',  # Empty
            '   ',  # Whitespace only
            '123',  # Only numbers
            'John123',  # Contains numbers
            'John@Doe',  # Contains special characters
            'John#Doe',  # Contains special characters
            'John$Doe',  # Contains special characters
            'John%Doe',  # Contains special characters
            'John^Doe',  # Contains special characters
            'John&Doe',  # Contains special characters
            'John*Doe',  # Contains special characters
            'John(Doe',  # Contains special characters
            'John)Doe',  # Contains special characters
            'John+Doe',  # Contains special characters
            'John=Doe',  # Contains special characters
            'John[Doe',  # Contains special characters
            'John]Doe',  # Contains special characters
            'John{Doe',  # Contains special characters
            'John}Doe',  # Contains special characters
            'John|Doe',  # Contains special characters
            'John\\Doe',  # Contains special characters
            'John/Doe',  # Contains special characters
            'John<Doe',  # Contains special characters
            'John>Doe',  # Contains special characters
            'John?Doe',  # Contains special characters
            'John!Doe',  # Contains special characters
            'John~Doe',  # Contains special characters
            'John`Doe',  # Contains special characters
            'a' * 51,  # Too long
        ]
        
        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaises(ValidationError):
                    validate_name_format(name)


class BioValidationTest(TestCase):
    """Test cases for bio validation utilities"""
    
    def test_validate_bio_length_valid(self):
        """Test valid bio lengths"""
        valid_bios = [
            '',  # Empty bio is valid
            'Short bio',
            'This is a medium length bio that should be valid',
            'a' * 500,  # Maximum length
        ]
        
        for bio in valid_bios:
            with self.subTest(bio=bio):
                try:
                    validate_bio_length(bio)
                except ValidationError as e:
                    self.fail(f"Bio should be valid: {len(bio)} characters")
    
    def test_validate_bio_length_invalid(self):
        """Test invalid bio lengths"""
        invalid_bios = [
            'a' * 501,  # Too long
            'a' * 1000,  # Much too long
        ]
        
        for bio in invalid_bios:
            with self.subTest(bio=bio):
                with self.assertRaises(ValidationError):
                    validate_bio_length(bio)


class ProfileImageValidationTest(TestCase):
    """Test cases for profile image validation utilities"""
    
    def setUp(self):
        """Set up test data"""
        self.small_image = MagicMock()
        self.small_image.size = 1024 * 1024  # 1MB
        
        self.large_image = MagicMock()
        self.large_image.size = 10 * 1024 * 1024  # 10MB
        
        self.valid_format_image = MagicMock()
        self.valid_format_image.name = 'profile.jpg'
        
        self.invalid_format_image = MagicMock()
        self.invalid_format_image.name = 'profile.txt'
    
    def test_validate_profile_image_size_valid(self):
        """Test valid profile image sizes"""
        try:
            validate_profile_image_size(self.small_image)
        except ValidationError as e:
            self.fail("Small image should be valid")
    
    def test_validate_profile_image_size_invalid(self):
        """Test invalid profile image sizes"""
        with self.assertRaises(ValidationError):
            validate_profile_image_size(self.large_image)
    
    def test_validate_profile_image_format_valid(self):
        """Test valid profile image formats"""
        valid_formats = ['profile.jpg', 'profile.jpeg', 'profile.png', 'profile.gif']
        
        for format_name in valid_formats:
            with self.subTest(format=format_name):
                image = MagicMock()
                image.name = format_name
                # Don't set content_type so it falls back to extension checking
                image.content_type = None
                try:
                    validate_profile_image_format(image)
                except ValidationError as e:
                    self.fail(f"Image format {format_name} should be valid")
    
    def test_validate_profile_image_format_invalid(self):
        """Test invalid profile image formats"""
        invalid_formats = [
            'profile.txt', 'profile.pdf', 'profile.doc', 'profile.exe',
            'profile.bmp', 'profile.tiff', 'profile.webp'
        ]
        
        for format_name in invalid_formats:
            with self.subTest(format=format_name):
                image = MagicMock()
                image.name = format_name
                with self.assertRaises(ValidationError):
                    validate_profile_image_format(image)
    
    def test_validate_profile_image_dimensions_valid(self):
        """Test valid profile image dimensions"""
        valid_dimensions = [
            (100, 100),   # Square, minimum size
            (500, 500),   # Square, medium size
            (1000, 1000), # Square, large size
            (200, 300),   # Portrait
            (300, 200),   # Landscape
        ]
        
        for width, height in valid_dimensions:
            with self.subTest(dimensions=f"{width}x{height}"):
                image = MagicMock()
                image.width = width
                image.height = height
                try:
                    validate_profile_image_dimensions(image)
                except ValidationError as e:
                    self.fail(f"Image dimensions {width}x{height} should be valid")
    
    def test_validate_profile_image_dimensions_invalid(self):
        """Test invalid profile image dimensions"""
        invalid_dimensions = [
            (2000, 2000), # Too large
            (0, 100),     # Zero width
            (100, 0),     # Zero height
            (-100, 100),  # Negative width
            (100, -100),  # Negative height
        ]
        
        for width, height in invalid_dimensions:
            with self.subTest(dimensions=f"{width}x{height}"):
                image = MagicMock()
                image.width = width
                image.height = height
                with self.assertRaises(ValidationError):
                    validate_profile_image_dimensions(image)


class SocialMediaLinksValidationTest(TestCase):
    """Test cases for social media links validation utilities"""
    
    def test_validate_social_media_links_valid(self):
        """Test valid social media links"""
        valid_links = [
            'https://twitter.com/username',
            'https://facebook.com/username',
            'https://linkedin.com/in/username',
            'https://instagram.com/username',
            'https://github.com/username',
            'https://youtube.com/channel/username',
            'https://tiktok.com/@username',
            'https://snapchat.com/add/username',
            'https://pinterest.com/username',
            'https://reddit.com/user/username',
            '',  # Empty link is valid
            None,  # None is valid
        ]
        
        for link in valid_links:
            with self.subTest(link=link):
                try:
                    validate_social_media_links(link)
                except ValidationError as e:
                    self.fail(f"Social media link {link} should be valid")
    
    def test_validate_social_media_links_invalid(self):
        """Test invalid social media links"""
        invalid_links = [
            'not-a-url',
            'ftp://example.com',
            'javascript:alert("xss")',
            'data:text/html,<script>alert("xss")</script>',
            'file:///etc/passwd',
        ]
        
        for link in invalid_links:
            with self.subTest(link=link):
                with self.assertRaises(ValidationError):
                    validate_social_media_links(link)


class UtilityIntegrationTest(BaseTestCase):
    """Integration tests for utility functions working together"""
    
    def test_user_profile_validation_flow(self):
        """Test complete user profile validation flow"""
        # Valid user data
        valid_data = {
            'username': 'john_doe',
            'email': 'john.doe@gmail.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+1-555-123-4567',
            'bio': 'This is a valid bio for testing purposes.',
        }
        
        # Test all validations pass
        try:
            validate_username_format(valid_data['username'])
            validate_email_domain(valid_data['email'])
            validate_name_format(valid_data['first_name'])
            validate_name_format(valid_data['last_name'])
            validate_phone_number(valid_data['phone_number'])
            validate_bio_length(valid_data['bio'])
        except ValidationError as e:
            self.fail(f"Valid data should pass validation: {e}")
        
        # Test phone number cleaning
        cleaned_phone = clean_phone_number(valid_data['phone_number'])
        self.assertEqual(cleaned_phone, '+15551234567')
    
    def test_password_validation_integration(self):
        """Test password validation with Django's built-in validator"""
        strong_password = 'StrongPass123!'
        
        try:
            # Test our custom validator
            validate_password_strength(strong_password)
            
            # Test Django's built-in validator
            validate_password(strong_password)
        except ValidationError as e:
            self.fail(f"Strong password should pass all validations: {e}")
    
    def test_validation_error_messages(self):
        """Test that validation errors provide meaningful messages"""
        # Test username validation error message
        with self.assertRaises(ValidationError) as context:
            validate_username_format('john doe')
        
        self.assertIn('Username', str(context.exception))
        
        # Test phone validation error message
        with self.assertRaises(ValidationError) as context:
            validate_phone_number('invalid')
        
        self.assertIn('Phone number', str(context.exception))
        
        # Test email domain validation error message
        with self.assertRaises(ValidationError) as context:
            validate_email_domain('user@10minutemail.com')
        
        self.assertIn('Disposable email', str(context.exception))
    
    def test_edge_case_handling(self):
        """Test utility functions handle edge cases gracefully"""
        # Test with very long inputs
        long_string = 'a' * 1000
        
        with self.assertRaises(ValidationError):
            validate_bio_length(long_string)
        
        # Test with special characters in names
        special_name = 'Jean-Pierre O\'Connor'
        try:
            validate_name_format(special_name)
        except ValidationError as e:
            self.fail("Special characters in names should be allowed")
        
        # Test with international phone numbers
        international_phone = '+44 20 7946 0958'
        try:
            validate_phone_number(international_phone)
            cleaned = clean_phone_number(international_phone)
            # The function adds + prefix, so we expect +442079460958
            self.assertEqual(cleaned, '+442079460958')
        except (ValidationError, ValueError) as e:
            self.fail("International phone numbers should be supported")
