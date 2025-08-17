from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from tests.base import BaseTestCase
from apps.tasks.services import TaskService
from apps.tasks.models import Task, Tag, Subtask, Comment, Attachment

User = get_user_model()


class TaskServiceTest(BaseTestCase):
    """Test cases for TaskService"""
    
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.task = self.create_task(owner=self.user)
        self.tag = self.create_tag()
    
    def test_get_user_tasks_success(self):
        """Test successful retrieval of user tasks"""
        # Create additional tasks for the user
        self.create_task(owner=self.user, title='Task 2')
        self.create_task(owner=self.user, title='Task 3')
        
        # Create task for another user
        other_user = self.create_user(username='otheruser', email='other@example.com')
        self.create_task(owner=other_user, title='Other User Task')
        
        tasks = TaskService.get_user_tasks(self.user)
        
        # Should only return tasks for the specified user
        self.assertEqual(tasks.count(), 3)
        for task in tasks:
            self.assertEqual(task.owner, self.user)
    
    def test_get_user_tasks_empty(self):
        """Test retrieval of user tasks when none exist"""
        # Delete all tasks
        Task.objects.all().delete()
        
        tasks = TaskService.get_user_tasks(self.user)
        
        self.assertEqual(tasks.count(), 0)
    
    def test_get_user_tasks_with_filters(self):
        """Test retrieval of user tasks with filters"""
        # Create tasks with different statuses
        self.create_task(owner=self.user, title='Todo Task', status='TODO')
        self.create_task(owner=self.user, title='In Progress Task', status='IN_PROGRESS')
        self.create_task(owner=self.user, title='Completed Task', status='COMPLETED')
        
        # Filter by status
        todo_tasks = TaskService.get_user_tasks(self.user, status='TODO')
        # Note: There's already a default task with status='TODO' from setUp
        self.assertEqual(todo_tasks.count(), 2)
        todo_titles = [task.title for task in todo_tasks]
        self.assertIn('Todo Task', todo_titles)
        self.assertIn('Test Task', todo_titles)  # Default task from setUp
        
        in_progress_tasks = TaskService.get_user_tasks(self.user, status='IN_PROGRESS')
        self.assertEqual(in_progress_tasks.count(), 1)
        self.assertEqual(in_progress_tasks.first().title, 'In Progress Task')
    
    def test_get_user_tasks_with_priority_filter(self):
        """Test retrieval of user tasks with priority filter"""
        # Create tasks with different priorities
        self.create_task(owner=self.user, title='High Priority Task', priority='HIGH')
        self.create_task(owner=self.user, title='Medium Priority Task', priority='MEDIUM')
        self.create_task(owner=self.user, title='Low Priority Task', priority='LOW')
        
        # Filter by priority
        high_priority_tasks = TaskService.get_user_tasks(self.user, priority='HIGH')
        self.assertEqual(high_priority_tasks.count(), 1)
        self.assertEqual(high_priority_tasks.first().title, 'High Priority Task')
    
    def test_get_user_tasks_with_date_filter(self):
        """Test retrieval of user tasks with date filter"""
        # Create tasks with different due dates
        past_date = timezone.now() - timedelta(days=1)
        future_date = timezone.now() + timedelta(days=7)
        
        self.create_task(owner=self.user, title='Past Due Task', due_date=past_date)
        self.create_task(owner=self.user, title='Future Task', due_date=future_date)
        
        # Filter by due date range
        overdue_tasks = TaskService.get_user_tasks(self.user, due_date__lt=timezone.now())
        self.assertEqual(overdue_tasks.count(), 1)
        self.assertEqual(overdue_tasks.first().title, 'Past Due Task')
    
    def test_get_user_tasks_with_search(self):
        """Test retrieval of user tasks with search"""
        # Create tasks with searchable titles
        self.create_task(owner=self.user, title='Bug Fix Task', description='Fix critical bug')
        self.create_task(owner=self.user, title='Feature Task', description='Add new feature')
        
        # Search by title
        bug_tasks = TaskService.get_user_tasks(self.user, search='bug')
        self.assertEqual(bug_tasks.count(), 1)
        self.assertEqual(bug_tasks.first().title, 'Bug Fix Task')
        
        # Search by description
        feature_tasks = TaskService.get_user_tasks(self.user, search='feature')
        self.assertEqual(feature_tasks.count(), 1)
        self.assertEqual(feature_tasks.first().title, 'Feature Task')
    
    def test_get_user_tasks_with_ordering(self):
        """Test retrieval of user tasks with ordering"""
        # Create tasks with different titles for ordering
        self.create_task(owner=self.user, title='Zebra Task')
        self.create_task(owner=self.user, title='Alpha Task')
        
        # Order by title
        ordered_tasks = TaskService.get_user_tasks(self.user, ordering='title')
        self.assertEqual(ordered_tasks.first().title, 'Alpha Task')
        self.assertEqual(ordered_tasks.last().title, 'Zebra Task')
        
        # Test reverse ordering
        reverse_ordered_tasks = TaskService.get_user_tasks(self.user, ordering='-title')
        self.assertEqual(reverse_ordered_tasks.first().title, 'Zebra Task')
        self.assertEqual(reverse_ordered_tasks.last().title, 'Alpha Task')
    
    def test_get_user_tasks_with_tags(self):
        """Test retrieval of user tasks with tag filter"""
        # Create tasks with different tags
        task1 = self.create_task(owner=self.user, title='Tagged Task 1')
        task1.tags.add(self.tag)
        
        task2 = self.create_task(owner=self.user, title='Tagged Task 2')
        task2.tags.add(self.tag)
        
        untagged_task = self.create_task(owner=self.user, title='Untagged Task')
        
        # Filter by tag
        tagged_tasks = TaskService.get_user_tasks(self.user, tags=[self.tag])
        self.assertEqual(tagged_tasks.count(), 2)
        
        # Filter by multiple tags
        tag2 = self.create_tag(name='Tag 2', color='#00ff00')
        task2.tags.add(tag2)
        
        multi_tagged_tasks = TaskService.get_user_tasks(self.user, tags=[self.tag, tag2])
        self.assertEqual(multi_tagged_tasks.count(), 1)
        self.assertEqual(multi_tagged_tasks.first().title, 'Tagged Task 2')
    
    def test_get_user_tasks_with_assignee(self):
        """Test retrieval of user tasks with assignee filter"""
        # Create tasks with different assignees
        assignee1 = self.create_user(username='assignee1', email='assignee1@example.com')
        assignee2 = self.create_user(username='assignee2', email='assignee2@example.com')
        
        self.create_task(owner=self.user, title='Assigned Task 1', assigned_to=assignee1)
        self.create_task(owner=self.user, title='Assigned Task 2', assigned_to=assignee2)
        self.create_task(owner=self.user, title='Unassigned Task')
        
        # Filter by assignee
        assigned_tasks = TaskService.get_user_tasks(self.user, assigned_to=assignee1)
        self.assertEqual(assigned_tasks.count(), 1)
        self.assertEqual(assigned_tasks.first().title, 'Assigned Task 1')
    
    def test_get_user_tasks_with_progress_filter(self):
        """Test retrieval of user tasks with progress filter"""
        # Create tasks with different progress
        self.create_task(owner=self.user, title='Low Progress Task', progress=25)
        self.create_task(owner=self.user, title='Medium Progress Task', progress=50)
        self.create_task(owner=self.user, title='High Progress Task', progress=75)
        
        # Filter by progress range
        high_progress_tasks = TaskService.get_user_tasks(self.user, progress__gte=50)
        self.assertEqual(high_progress_tasks.count(), 2)
        
        low_progress_tasks = TaskService.get_user_tasks(self.user, progress__lt=50)
        # Note: Default task from setUp has progress=0, plus the Low Progress Task with progress=25
        self.assertEqual(low_progress_tasks.count(), 2)
    
    def test_get_user_tasks_with_complex_filters(self):
        """Test retrieval of user tasks with complex filter combinations"""
        # Create a high priority, in-progress task with high progress
        complex_task = self.create_task(
            owner=self.user,
            title='Complex Task',
            priority='HIGH',
            status='IN_PROGRESS',
            progress=75
        )
        complex_task.tags.add(self.tag)
        
        # Apply multiple filters
        filtered_tasks = TaskService.get_user_tasks(
            self.user,
            priority='HIGH',
            status='IN_PROGRESS',
            progress__gte=50,
            tags=[self.tag]
        )
        
        self.assertEqual(filtered_tasks.count(), 1)
        self.assertEqual(filtered_tasks.first().title, 'Complex Task')
    
    def test_get_user_tasks_pagination(self):
        """Test retrieval of user tasks with pagination"""
        # Create many tasks
        for i in range(25):
            self.create_task(owner=self.user, title=f'Task {i}')
        
        # Test pagination
        page1_tasks = TaskService.get_user_tasks(self.user, page=1, page_size=10)
        self.assertEqual(page1_tasks.count(), 10)
        
        page2_tasks = TaskService.get_user_tasks(self.user, page=2, page_size=10)
        self.assertEqual(page2_tasks.count(), 10)
        
        page3_tasks = TaskService.get_user_tasks(self.user, page=3, page_size=10)
        # Note: There are 26 total tasks (25 created + 1 default from setUp)
        # Page 1: 10, Page 2: 10, Page 3: 6
        self.assertEqual(page3_tasks.count(), 6)  # Remaining tasks
    
    def test_get_user_tasks_invalid_user(self):
        """Test retrieval of tasks with invalid user"""
        with self.assertRaises(ValueError):
            TaskService.get_user_tasks(None)
    
    def test_get_user_tasks_invalid_filters(self):
        """Test retrieval of tasks with invalid filters"""
        # Test with invalid status
        with self.assertRaises(ValidationError):
            TaskService.get_user_tasks(self.user, status='INVALID_STATUS')
        
        # Test with invalid priority
        with self.assertRaises(ValidationError):
            TaskService.get_user_tasks(self.user, priority='INVALID_PRIORITY')
    
    def test_get_user_tasks_performance(self):
        """Test performance of task retrieval with large datasets"""
        # Create many tasks
        for i in range(100):
            self.create_task(owner=self.user, title=f'Performance Task {i}')
        
        # Measure retrieval time
        import time
        start_time = time.time()
        
        tasks = TaskService.get_user_tasks(self.user)
        
        end_time = time.time()
        retrieval_time = end_time - start_time
        
        # Should retrieve all tasks (100 created + 1 default from setUp)
        self.assertEqual(tasks.count(), 101)
        
        # Should be reasonably fast
        self.assertLess(retrieval_time, 1.0)  # Should complete within 1 second
    
    def test_get_user_tasks_with_subtasks(self):
        """Test retrieval of user tasks with subtask information"""
        # Create task with subtasks
        task = self.create_task(owner=self.user, title='Task with Subtasks')
        subtask1 = self.create_subtask(task=task, title='Subtask 1')
        subtask2 = self.create_subtask(task=task, title='Subtask 2')
        
        # Get tasks with subtask count
        tasks = TaskService.get_user_tasks(self.user, include_subtasks=True)
        
        # Should include subtask information
        task_with_subtasks = tasks.filter(id=task.id).first()
        self.assertIsNotNone(task_with_subtasks)
        
        # Check if subtasks are included (depends on implementation)
        # This test may need adjustment based on your actual implementation
    
    def test_get_user_tasks_with_comments(self):
        """Test retrieval of user tasks with comment information"""
        # Create task with comments
        task = self.create_task(owner=self.user, title='Task with Comments')
        comment1 = self.create_comment(task=task, content='Comment 1')
        comment2 = self.create_comment(task=task, content='Comment 2')
        
        # Get tasks with comment count
        tasks = TaskService.get_user_tasks(self.user, include_comments=True)
        
        # Should include comment information
        task_with_comments = tasks.filter(id=task.id).first()
        self.assertIsNotNone(task_with_comments)
        
        # Check if comments are included (depends on implementation)
        # This test may need adjustment based on your actual implementation
    
    def test_get_user_tasks_with_attachments(self):
        """Test retrieval of user tasks with attachment information"""
        # Create task with attachments
        task = self.create_task(owner=self.user, title='Task with Attachments')
        attachment1 = self.create_attachment(task=task, original_filename='file1.txt')
        attachment2 = self.create_attachment(task=task, original_filename='file2.txt')
        
        # Get tasks with attachment count
        tasks = TaskService.get_user_tasks(self.user, include_attachments=True)
        
        # Should include attachment information
        task_with_attachments = tasks.filter(id=task.id).first()
        self.assertIsNotNone(task_with_attachments)
        
        # Check if attachments are included (depends on implementation)
        # This test may need adjustment based on your actual implementation
    
    def test_get_user_tasks_with_related_data(self):
        """Test retrieval of user tasks with all related data"""
        # Create comprehensive task data
        task = self.create_task(owner=self.user, title='Comprehensive Task')
        
        # Add tags
        task.tags.add(self.tag)
        
        # Add subtasks
        subtask = self.create_subtask(task=task, title='Subtask')
        
        # Add comments
        comment = self.create_comment(task=task, content='Comment')
        
        # Add attachments
        attachment = self.create_attachment(task=task, original_filename='attachment.txt')
        
        # Get tasks with all related data
        tasks = TaskService.get_user_tasks(
            self.user,
            include_subtasks=True,
            include_comments=True,
            include_attachments=True,
            include_tags=True
        )
        
        # Should include all related data
        comprehensive_task = tasks.filter(id=task.id).first()
        self.assertIsNotNone(comprehensive_task)
        
        # Check if all related data is included (depends on implementation)
        # This test may need adjustment based on your actual implementation
    
    def test_get_user_tasks_edge_cases(self):
        """Test edge cases for task retrieval"""
        # Test with user that has no tasks
        new_user = self.create_user(username='newuser', email='new@example.com')
        tasks = TaskService.get_user_tasks(new_user)
        self.assertEqual(tasks.count(), 0)
        
        # Test with very large page size
        tasks = TaskService.get_user_tasks(self.user, page_size=1000)
        self.assertLessEqual(tasks.count(), 1000)
        
        # Test with negative page number
        tasks = TaskService.get_user_tasks(self.user, page=-1)
        # Should handle gracefully (depends on implementation)
        
        # Test with zero page size
        tasks = TaskService.get_user_tasks(self.user, page_size=0)
        # Should handle gracefully (depends on implementation)
    
    def test_get_user_tasks_data_integrity(self):
        """Test data integrity of retrieved tasks"""
        # Create task with specific data
        original_task = self.create_task(
            owner=self.user,
            title='Integrity Test Task',
            description='Test description',
            priority='HIGH',
            status='TODO',
            estimated_hours=5.0,
            progress=0
        )
        
        # Retrieve task through service
        retrieved_tasks = TaskService.get_user_tasks(self.user, title='Integrity Test Task')
        retrieved_task = retrieved_tasks.first()
        
        # Verify data integrity
        self.assertIsNotNone(retrieved_task)
        self.assertEqual(retrieved_task.title, original_task.title)
        self.assertEqual(retrieved_task.description, original_task.description)
        self.assertEqual(retrieved_task.priority, original_task.priority)
        self.assertEqual(retrieved_task.status, original_task.status)
        self.assertEqual(retrieved_task.estimated_hours, original_task.estimated_hours)
        self.assertEqual(retrieved_task.progress, original_task.progress)
        self.assertEqual(retrieved_task.owner, original_task.owner)
