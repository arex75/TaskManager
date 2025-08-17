from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from tests.base import BaseTestCase
from apps.tasks.utils import (
    validate_hex_color,
    calculate_task_completion_time,
    calculate_estimated_vs_actual_hours,
    get_task_priority_color,
    get_task_status_color,
    format_duration,
    get_due_date_status,
    calculate_task_efficiency,
    generate_task_summary
)

from apps.tasks.models import Task, Tag
from django.contrib.auth import get_user_model

User = get_user_model()


class TasksUtilsTest(BaseTestCase):
    """Test cases for tasks utility functions"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.task = self.create_task(owner=self.user)
    
    def test_validate_hex_color_valid(self):
        """Test valid hex color validation"""
        valid_colors = [
            '#ff0000',  # 6 digits
            '#00ff00',  # 6 digits
            '#0000ff',  # 6 digits
            '#f0f0f0',  # 6 digits
            '#000',     # 3 digits
            '#fff',     # 3 digits
            '#123',     # 3 digits
            '#abc',     # 3 digits
        ]
        
        for color in valid_colors:
            with self.subTest(color=color):
                result = validate_hex_color(color)
                self.assertTrue(result)
    
    def test_validate_hex_color_invalid(self):
        """Test invalid hex color validation"""
        invalid_colors = [
            'red',           # Not hex
            '#gggggg',       # Invalid hex characters
            'ff0000',        # Missing #
            '#fffffff',      # Too long
            '#0000000',      # Too long
            '#',             # Just #
            '##ff0000',      # Double #
            '#ff000',        # 5 digits
            '#ff00',         # 4 digits
            '#ff',           # 2 digits
            '#f',            # 1 digit
            '',              # Empty string
            None,            # None
        ]
        
        for color in invalid_colors:
            with self.subTest(color=color):
                try:
                    result = validate_hex_color(color)
                except ValidationError as e:
                    print(f"Expected ValidationError: {e}")
                with self.assertRaises(ValidationError):
                    validate_hex_color(color)
    
    def test_validate_hex_color_edge_cases(self):
        """Test edge cases for hex color validation"""
        # Test with very long strings
        long_invalid = '#' + 'g' * 100
        with self.assertRaises(ValidationError):
            validate_hex_color(long_invalid)
        
        # Test with special characters
        special_chars = ['#@#$%^', '#!@#$%', '#123@#$']
        for color in special_chars:
            with self.subTest(color=color):
                with self.assertRaises(ValidationError):
                    validate_hex_color(color)
    
    def test_calculate_task_completion_time_success(self):
        """Test successful task completion time calculation"""
        # Create task with start and completion times
        start_time = timezone.now() - timedelta(hours=5)
        completion_time = timezone.now()
        
        task = self.create_task(
            owner=self.user,
            started_at=start_time,
            completed_at=completion_time
        )
        
        completion_time_hours = calculate_task_completion_time(
            task.started_at,
            task.completed_at
        )
        
        # Should be approximately 5 hours (allowing for test execution time)
        self.assertAlmostEqual(completion_time_hours, 5.0, delta=0.1)
    
    def test_calculate_task_completion_time_no_start(self):
        """Test completion time calculation when task hasn't started"""
        task = self.create_task(owner=self.user)
        
        with self.assertRaises(ValueError):
            calculate_task_completion_time(None, task.completed_at)
    
    def test_calculate_task_completion_time_no_completion(self):
        """Test completion time calculation when task hasn't completed"""
        start_time = timezone.now() - timedelta(hours=2)
        task = self.create_task(owner=self.user, started_at=start_time)
        
        with self.assertRaises(ValueError):
            calculate_task_completion_time(task.started_at, None)
    
    def test_calculate_task_completion_time_invalid_order(self):
        """Test completion time calculation with invalid time order"""
        start_time = timezone.now()
        completion_time = timezone.now() - timedelta(hours=1)  # Completion before start
        
        with self.assertRaises(ValueError):
            calculate_task_completion_time(start_time, completion_time)
    
    def test_calculate_task_completion_time_zero_duration(self):
        """Test completion time calculation with zero duration"""
        current_time = timezone.now()
        
        completion_time_hours = calculate_task_completion_time(
            current_time,
            current_time
        )
        
        self.assertEqual(completion_time_hours, 0.0)
    
    def test_calculate_task_completion_time_precision(self):
        """Test completion time calculation precision"""
        start_time = timezone.now() - timedelta(minutes=30)  # 30 minutes
        completion_time = timezone.now()
        
        completion_time_hours = calculate_task_completion_time(
            start_time,
            completion_time
        )
        
        # Should be approximately 0.5 hours
        self.assertAlmostEqual(completion_time_hours, 0.5, delta=0.01)
    
    def test_calculate_estimated_vs_actual_hours_success(self):
        """Test successful estimated vs actual hours calculation"""
        estimated_hours = 8.0
        actual_hours = 6.5
        
        result = calculate_estimated_vs_actual_hours(estimated_hours, actual_hours)
        
        
        self.assertIn('difference', result)
        self.assertIn('percentage', result)
        self.assertIn('status', result)
        
        # Difference should be 1.5 hours (estimated - actual)
        self.assertEqual(result['difference'], 1.5)
        
        # Percentage should be positive (underestimated)
        self.assertGreater(result['percentage'], 0)
        
        # Status should indicate underestimation
        self.assertIn('underestimated', result['status'].lower())
    
    def test_calculate_estimated_vs_actual_hours_overestimated(self):
        """Test calculation when estimated hours exceed actual hours"""
        estimated_hours = 5.0
        actual_hours = 7.0
        
        result = calculate_estimated_vs_actual_hours(estimated_hours, actual_hours)
        
        # Difference should be negative (estimated - actual)
        self.assertEqual(result['difference'], -2.0)
        
        # Percentage should be negative (overestimated)
        self.assertLess(result['percentage'], 0)
        
        # Status should indicate overestimation
        self.assertIn('overestimated', result['status'].lower())
    
    def test_calculate_estimated_vs_actual_hours_exact_match(self):
        """Test calculation when estimated equals actual hours"""
        estimated_hours = 6.0
        actual_hours = 6.0
        
        result = calculate_estimated_vs_actual_hours(estimated_hours, actual_hours)
        
        # Difference should be 0
        self.assertEqual(result['difference'], 0.0)
        
        # Percentage should be 0
        self.assertEqual(result['percentage'], 0.0)
        
        # Status should indicate exact match
        self.assertIn('exact', result['status'].lower())
    
    def test_calculate_estimated_vs_actual_hours_invalid_input(self):
        """Test calculation with invalid input"""
        # Test with negative values
        with self.assertRaises(ValueError):
            calculate_estimated_vs_actual_hours(-1.0, 5.0)
        
        with self.assertRaises(ValueError):
            calculate_estimated_vs_actual_hours(5.0, -1.0)
        
        # Test with zero values
        with self.assertRaises(ValueError):
            calculate_estimated_vs_actual_hours(0.0, 5.0)
        
        with self.assertRaises(ValueError):
            calculate_estimated_vs_actual_hours(5.0, 0.0)
        
        # Test with None values
        with self.assertRaises(ValueError):
            calculate_estimated_vs_actual_hours(None, 5.0)
        
        with self.assertRaises(ValueError):
            calculate_estimated_vs_actual_hours(5.0, None)
    
    def test_calculate_estimated_vs_actual_hours_edge_cases(self):
        """Test edge cases for estimated vs actual hours calculation"""
        # Test with very large numbers
        estimated_hours = 1000.0
        actual_hours = 1200.0
        
        result = calculate_estimated_vs_actual_hours(estimated_hours, actual_hours)
        
        self.assertEqual(result['difference'], -200.0)
        self.assertLess(result['percentage'], 0)
        
        # Test with very small numbers
        estimated_hours = 0.1
        actual_hours = 0.2
        
        result = calculate_estimated_vs_actual_hours(estimated_hours, actual_hours)
        
        self.assertEqual(result['difference'], -0.1)
        self.assertLess(result['percentage'], 0)
    
    def test_get_task_priority_color_success(self):
        """Test successful priority color retrieval"""
        priority_colors = {
            'LOW': '#28a745',      # Green
            'MEDIUM': '#ffc107',   # Yellow
            'HIGH': '#dc3545',     # Red
            'URGENT': '#6f42c1',   # Purple
        }
        
        for priority, expected_color in priority_colors.items():
            with self.subTest(priority=priority):
                color = get_task_priority_color(priority)
                self.assertEqual(color, expected_color)
    
    def test_get_task_priority_color_invalid_priority(self):
        """Test priority color retrieval with invalid priority"""
        invalid_priorities = ['INVALID', 'NONE', 'EXTREME', '']
        
        for priority in invalid_priorities:
            with self.subTest(priority=priority):
                color = get_task_priority_color(priority)
                # Should return default color or handle gracefully
                self.assertIsNotNone(color)
    
    def test_get_task_priority_color_case_sensitivity(self):
        """Test priority color retrieval case sensitivity"""
        # Test with different case variations
        priority_variations = ['low', 'Low', 'LOW', 'Low']
        
        for priority in priority_variations:
            with self.subTest(priority=priority):
                color = get_task_priority_color(priority)
                # Should handle case variations gracefully
                self.assertIsNotNone(color)
    
    def test_get_task_status_color_success(self):
        """Test successful status color retrieval"""
        status_colors = {
            'TODO': '#6c757d',           # Gray
            'IN_PROGRESS': '#007bff',    # Blue
            'PAUSED': '#ffc107',         # Yellow
            'COMPLETED': '#28a745',      # Green
            'CANCELLED': '#dc3545',      # Red
        }
        
        for status, expected_color in status_colors.items():
            with self.subTest(status=status):
                color = get_task_status_color(status)
                self.assertEqual(color, expected_color)
    
    def test_get_task_status_color_invalid_status(self):
        """Test status color retrieval with invalid status"""
        invalid_statuses = ['INVALID', 'NONE', 'DONE', '']
        
        for status in invalid_statuses:
            with self.subTest(status=status):
                color = get_task_status_color(status)
                # Should return default color or handle gracefully
                self.assertIsNotNone(color)
    
    def test_format_duration_success(self):
        """Test successful duration formatting"""
        # Test various durations
        test_cases = [
            (0.5, '30 minutes'),
            (1.0, '1 hour'),
            (1.5, '1 hour 30 minutes'),
            (2.0, '2 hours'),
            (2.25, '2 hours 15 minutes'),
            (24.0, '1 day'),
            (25.0, '1 day 1 hour'),
            (48.5, '2 days 30 minutes'),
        ]
        
        for hours, expected_format in test_cases:
            with self.subTest(hours=hours):
                formatted = format_duration(hours)
                self.assertEqual(formatted, expected_format)
    
    def test_format_duration_edge_cases(self):
        """Test edge cases for duration formatting"""
        # Test with zero
        self.assertEqual(format_duration(0), '0 minutes')
        
        # Test with very small values
        self.assertEqual(format_duration(0.01), '0.6 minutes')
        
        # Test with very large values
        self.assertEqual(format_duration(168.0), '1 week')  # 7 days
        
        # Test with negative values
        with self.assertRaises(ValueError):
            format_duration(-1.0)
    
    def test_format_duration_precision(self):
        """Test duration formatting precision"""
        # Test with fractional hours
        self.assertEqual(format_duration(1.33), '1 hour 20 minutes')
        self.assertEqual(format_duration(1.67), '1 hour 40 minutes')
        self.assertEqual(format_duration(0.17), '10 minutes')  # 0.17 * 60 = 10.2
    
    def test_get_due_date_status_success(self):
        """Test successful due date status retrieval"""
        now = timezone.now()
        
        # Test overdue task
        overdue_date = now - timedelta(days=1)
        status = get_due_date_status(overdue_date, completed=False)
        self.assertIn('overdue', status['status'].lower())
        self.assertLess(status['days_remaining'], 0)  # Should be negative for overdue tasks
        
        # Test due today
        due_today = now + timedelta(hours=12)
        status = get_due_date_status(due_today, completed=False)
        self.assertIn('today', status['status'].lower())
        
        # Test due soon
        due_soon = now + timedelta(days=2)
        status = get_due_date_status(due_soon, completed=False)
        self.assertIn('soon', status['status'].lower())
        
        # Test due later
        due_later = now + timedelta(days=10)
        status = get_due_date_status(due_later, completed=False)
        self.assertIn('later', status['status'].lower())
    
    def test_get_due_date_status_completed(self):
        """Test due date status for completed tasks"""
        now = timezone.now()
        due_date = now + timedelta(days=5)
        
        status = get_due_date_status(due_date, completed=True)
        self.assertIn('completed', status['status'].lower())
        self.assertEqual(status['days_remaining'], 0)
    
    def test_get_due_date_status_no_due_date(self):
        """Test due date status when no due date is set"""
        status = get_due_date_status(None, completed=False)
        self.assertIn('no due date', status['status'].lower())
        self.assertIsNone(status['days_remaining'])
    
    def test_get_due_date_status_edge_cases(self):
        """Test edge cases for due date status"""
        now = timezone.now()
        
        # Test with due date exactly now
        status = get_due_date_status(now, completed=False)
        self.assertIn('due', status['status'].lower())
        
        # Test with due date in the past by a few minutes
        past_minutes = now - timedelta(minutes=30)
        status = get_due_date_status(past_minutes, completed=False)
        self.assertIn('overdue', status['status'].lower())
        
        # Test with due date in the future by a few minutes
        future_minutes = now + timedelta(minutes=30)
        status = get_due_date_status(future_minutes, completed=False)
        self.assertIn('today', status['status'].lower())
    
    def test_calculate_task_efficiency_success(self):
        """Test successful task efficiency calculation"""
        # Create task with timing data
        start_time = timezone.now() - timedelta(hours=4)
        completion_time = timezone.now()
        estimated_hours = 6.0
        actual_hours = 4.0
        
        efficiency = calculate_task_efficiency(
            estimated_hours,
            actual_hours,
            completion_time,
            start_time
        )
        
        self.assertIn('efficiency_score', efficiency)
        self.assertIn('time_accuracy', efficiency)
        self.assertIn('productivity_rating', efficiency)
        
        # Efficiency should be positive (completed faster than estimated)
        self.assertGreater(efficiency['efficiency_score'], 0)
    
    def test_calculate_task_efficiency_overestimated(self):
        """Test efficiency calculation for overestimated tasks"""
        start_time = timezone.now() - timedelta(hours=8)
        completion_time = timezone.now()
        estimated_hours = 4.0
        actual_hours = 8.0
        
        efficiency = calculate_task_efficiency(
            estimated_hours,
            actual_hours,
            completion_time,
            start_time
        )
        
        # Efficiency should be negative (took longer than estimated)
        self.assertLess(efficiency['efficiency_score'], 0)
    
    def test_calculate_task_efficiency_invalid_input(self):
        """Test efficiency calculation with invalid input"""
        # Test with missing timing data
        with self.assertRaises(ValueError):
            calculate_task_efficiency(5.0, 6.0, None, timezone.now())
        
        with self.assertRaises(ValueError):
            calculate_task_efficiency(5.0, 6.0, timezone.now(), None)
        
        # Test with invalid hours
        with self.assertRaises(ValueError):
            calculate_task_efficiency(-1.0, 5.0, timezone.now(), timezone.now())
        
        with self.assertRaises(ValueError):
            calculate_task_efficiency(5.0, -1.0, timezone.now(), timezone.now())
    
    def test_calculate_task_efficiency_edge_cases(self):
        """Test edge cases for efficiency calculation"""
        now = timezone.now()
        
        # Test with zero estimated hours
        with self.assertRaises(ValueError):
            calculate_task_efficiency(0.0, 5.0, now, now - timedelta(hours=5))
        
        # Test with very small actual hours
        efficiency = calculate_task_efficiency(
            1.0, 0.1, now, now - timedelta(minutes=6)
        )
        self.assertIsNotNone(efficiency)
        
        # Test with very large hours
        efficiency = calculate_task_efficiency(
            1000.0, 1200.0, now, now - timedelta(hours=1200)
        )
        self.assertIsNotNone(efficiency)
    
    def test_generate_task_summary_success(self):
        """Test successful task summary generation"""
        # Clear existing tasks from setUp
        Task.objects.filter(owner=self.user).delete()
        
        # Create multiple tasks with different statuses
        self.create_task(owner=self.user, title='Task 1', status='TODO', priority='HIGH')
        self.create_task(owner=self.user, title='Task 2', status='IN_PROGRESS', priority='MEDIUM')
        self.create_task(owner=self.user, title='Task 3', status='COMPLETED', priority='LOW')
        
        tasks = Task.objects.filter(owner=self.user)
        summary = generate_task_summary(tasks)
        
        self.assertIn('total_tasks', summary)
        self.assertIn('status_breakdown', summary)
        self.assertIn('priority_breakdown', summary)
        self.assertIn('completion_rate', summary)
        
        # Should have 3 tasks
        self.assertEqual(summary['total_tasks'], 3)
        
        # Should have tasks in different statuses
        self.assertIn('TODO', summary['status_breakdown'])
        self.assertIn('IN_PROGRESS', summary['status_breakdown'])
        self.assertIn('COMPLETED', summary['status_breakdown'])
    
    def test_generate_task_summary_empty(self):
        """Test task summary generation with empty task list"""
        empty_tasks = Task.objects.none()
        summary = generate_task_summary(empty_tasks)
        
        self.assertEqual(summary['total_tasks'], 0)
        self.assertEqual(summary['completion_rate'], 0.0)
        self.assertEqual(len(summary['status_breakdown']), 0)
        self.assertEqual(len(summary['priority_breakdown']), 0)
    
    def test_generate_task_summary_single_task(self):
        """Test task summary generation with single task"""
        single_task = Task.objects.filter(owner=self.user)
        summary = generate_task_summary(single_task)
        
        self.assertEqual(summary['total_tasks'], 1)
        self.assertIn('TODO', summary['status_breakdown'])
        self.assertIn('MEDIUM', summary['priority_breakdown'])
    
    def test_generate_task_summary_with_tags(self):
        """Test task summary generation including tag information"""
        # Create tasks with tags
        tag1 = self.create_tag(name='Urgent', color='#ff0000')
        tag2 = self.create_tag(name='Bug', color='#ff6600')
        
        task1 = self.create_task(owner=self.user, title='Urgent Task')
        task1.tags.add(tag1)
        
        task2 = self.create_task(owner=self.user, title='Bug Task')
        task2.tags.add(tag2)
        
        tasks = Task.objects.filter(owner=self.user)
        summary = generate_task_summary(tasks, include_tags=True)
        
        self.assertIn('tag_breakdown', summary)
        self.assertIn('Urgent', summary['tag_breakdown'])
        self.assertIn('Bug', summary['tag_breakdown'])
    
    def test_generate_task_summary_performance(self):
        """Test performance of task summary generation with large datasets"""
        # Clear existing tasks from setUp
        Task.objects.filter(owner=self.user).delete()
        
        # Create many tasks
        for i in range(100):
            self.create_task(owner=self.user, title=f'Performance Task {i}')
        
        tasks = Task.objects.filter(owner=self.user)
        
        # Measure generation time
        import time
        start_time = time.time()
        
        summary = generate_task_summary(tasks)
        
        end_time = time.time()
        generation_time = end_time - start_time
        
        # Should generate summary for all tasks
        self.assertEqual(summary['total_tasks'], 100)
        
        # Should be reasonably fast
        self.assertLess(generation_time, 1.0)  # Should complete within 1 second
    
    def test_generate_task_summary_data_integrity(self):
        """Test data integrity of generated task summary"""
        # Clear existing tasks from setUp
        Task.objects.filter(owner=self.user).delete()
        
        # Create task with specific data
        task = self.create_task(
            owner=self.user,
            title='Summary Test Task',
            status='IN_PROGRESS',
            priority='HIGH',
            progress=50
        )
        
        tasks = Task.objects.filter(owner=self.user)
        summary = generate_task_summary(tasks)
        
        # Verify summary accuracy
        self.assertEqual(summary['total_tasks'], 1)
        self.assertEqual(summary['status_breakdown']['IN_PROGRESS'], 1)
        self.assertEqual(summary['priority_breakdown']['HIGH'], 1)
        
        # Completion rate should be 0% (no completed tasks)
        self.assertEqual(summary['completion_rate'], 0.0)
    
    def test_generate_task_summary_edge_cases(self):
        """Test edge cases for task summary generation"""
        # Clear existing tasks from setUp
        Task.objects.filter(owner=self.user).delete()
        
        # Test with tasks that have edge case values
        task = self.create_task(owner=self.user, title='Edge Case Task')
        task.progress = 0
        task.estimated_hours = 0
        task.save()
        
        tasks = Task.objects.filter(owner=self.user)
        summary = generate_task_summary(tasks)
        
        # Should handle edge case values gracefully
        self.assertIsNotNone(summary)
        self.assertEqual(summary['total_tasks'], 1)
        self.assertEqual(summary['average_progress'], 0.0)
        
        # Test with tasks that have very large values
        task.progress = 100
        task.estimated_hours = 999.99
        task.save()
        
        summary = generate_task_summary(tasks)
        
        # Should handle large values gracefully
        self.assertIsNotNone(summary)
        self.assertEqual(summary['average_progress'], 100.0)
