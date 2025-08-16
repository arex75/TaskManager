from django.utils import timezone
from django.db import models
from datetime import timedelta
import re


def validate_hex_color(color):
    """
    Validate hex color format
    
    Args:
        color (str): Hex color string
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not color:
        return False
    
    # Check if it's a valid hex color (#RRGGBB)
    hex_pattern = re.compile(r'^#([A-Fa-f0-9]{6})$')
    return bool(hex_pattern.match(color))


def calculate_task_completion_time(started_at, completed_at):
    """
    Calculate the time it took to complete a task
    
    Args:
        started_at: When the task was started
        completed_at: When the task was completed
        
    Returns:
        timedelta: Time difference or None if invalid
    """
    if not started_at or not completed_at:
        return None
    
    if completed_at <= started_at:
        return None
    
    return completed_at - started_at


def calculate_estimated_vs_actual_hours(estimated_hours, actual_hours):
    """
    Calculate the difference between estimated and actual hours
    
    Args:
        estimated_hours: Estimated hours (Decimal)
        actual_hours: Actual hours (Decimal)
        
    Returns:
        dict: Dictionary with difference and percentage
    """
    if not estimated_hours or not actual_hours:
        return {
            'difference': None,
            'percentage': None,
            'is_over_estimate': None
        }
    
    difference = float(actual_hours) - float(estimated_hours)
    percentage = (difference / float(estimated_hours)) * 100
    
    return {
        'difference': abs(difference),
        'percentage': abs(percentage),
        'is_over_estimate': difference > 0
    }


def get_task_priority_color(priority):
    """
    Get color for task priority
    
    Args:
        priority (str): Task priority level
        
    Returns:
        str: Hex color code
    """
    priority_colors = {
        'LOW': '#28a745',      # Green
        'MEDIUM': '#ffc107',   # Yellow
        'HIGH': '#fd7e14',     # Orange
        'URGENT': '#dc3545',   # Red
    }
    
    return priority_colors.get(priority, '#6c757d')  # Default gray


def get_task_status_color(status):
    """
    Get color for task status
    
    Args:
        status (str): Task status
        
    Returns:
        str: Hex color code
    """
    status_colors = {
        'TODO': '#6c757d',           # Gray
        'IN_PROGRESS': '#007bff',    # Blue
        'REVIEW': '#ffc107',         # Yellow
        'DONE': '#28a745',           # Green
        'BLOCKED': '#dc3545',        # Red
        'CANCELLED': '#6c757d',      # Gray
    }
    
    return status_colors.get(status, '#6c757d')  # Default gray


def format_duration(hours):
    """
    Format hours into human-readable duration
    
    Args:
        hours (Decimal): Hours as decimal
        
    Returns:
        str: Formatted duration string
    """
    if not hours:
        return "0h"
    
    hours_float = float(hours)
    whole_hours = int(hours_float)
    minutes = int((hours_float - whole_hours) * 60)
    
    if minutes == 0:
        return f"{whole_hours}h"
    elif whole_hours == 0:
        return f"{minutes}m"
    else:
        return f"{whole_hours}h {minutes}m"


def get_due_date_status(due_date, completed=False):
    """
    Get the status of a due date
    
    Args:
        due_date: Due date datetime
        completed: Whether the task is completed
        
    Returns:
        dict: Status information
    """
    if completed:
        return {
            'status': 'completed',
            'color': '#28a745',
            'message': 'Completed'
        }
    
    if not due_date:
        return {
            'status': 'no_due_date',
            'color': '#6c757d',
            'message': 'No due date'
        }
    
    now = timezone.now()
    time_diff = due_date - now
    
    if time_diff.total_seconds() < 0:
        # Overdue
        days_overdue = abs(time_diff.days)
        if days_overdue == 0:
            message = "Overdue today"
        elif days_overdue == 1:
            message = "Overdue 1 day"
        else:
            message = f"Overdue {days_overdue} days"
        
        return {
            'status': 'overdue',
            'color': '#dc3545',
            'message': message,
            'days': days_overdue
        }
    
    elif time_diff.total_seconds() < 86400:  # Less than 1 day
        return {
            'status': 'due_today',
            'color': '#fd7e14',
            'message': 'Due today'
        }
    
    elif time_diff.total_seconds() < 604800:  # Less than 1 week
        days_until = time_diff.days
        return {
            'status': 'due_soon',
            'color': '#ffc107',
            'message': f'Due in {days_until} days'
        }
    
    else:
        days_until = time_diff.days
        return {
            'status': 'due_later',
            'color': '#28a745',
            'message': f'Due in {days_until} days'
        }


def calculate_task_efficiency(estimated_hours, actual_hours, completed_at, started_at):
    """
    Calculate task efficiency metrics
    
    Args:
        estimated_hours: Estimated hours
        actual_hours: Actual hours
        completed_at: When task was completed
        started_at: When task was started
        
    Returns:
        dict: Efficiency metrics
    """
    metrics = {
        'time_accuracy': None,
        'completion_speed': None,
        'efficiency_score': None
    }
    
    # Time accuracy (estimated vs actual)
    if estimated_hours and actual_hours:
        time_diff = calculate_estimated_vs_actual_hours(estimated_hours, actual_hours)
        if time_diff['percentage'] is not None:
            metrics['time_accuracy'] = {
                'percentage': time_diff['percentage'],
                'is_over_estimate': time_diff['is_over_estimate'],
                'difference': time_diff['difference']
            }
    
    # Completion speed
    if started_at and completed_at:
        completion_time = calculate_task_completion_time(started_at, completed_at)
        if completion_time:
            metrics['completion_speed'] = {
                'duration': completion_time,
                'hours': completion_time.total_seconds() / 3600
            }
    
    # Efficiency score (0-100)
    score = 0
    if metrics['time_accuracy'] and metrics['time_accuracy']['percentage'] <= 20:
        score += 40  # Good time estimation
    elif metrics['time_accuracy'] and metrics['time_accuracy']['percentage'] <= 50:
        score += 20  # Acceptable time estimation
    
    if metrics['completion_speed']:
        score += 30  # Task was completed
    
    # Bonus points for completing early
    if metrics['time_accuracy'] and not metrics['time_accuracy']['is_over_estimate']:
        score += 30
    
    metrics['efficiency_score'] = min(score, 100)
    
    return metrics


def generate_task_summary(tasks):
    """
    Generate a summary of tasks
    
    Args:
        tasks: QuerySet of tasks
        
    Returns:
        dict: Task summary statistics
    """
    if not tasks:
        return {
            'total': 0,
            'completed': 0,
            'in_progress': 0,
            'overdue': 0,
            'due_soon': 0,
            'average_progress': 0,
            'priority_distribution': {},
            'status_distribution': {}
        }
    
    total = tasks.count()
    completed = tasks.filter(completed=True).count()
    in_progress = tasks.filter(status='IN_PROGRESS').count()
    
    # Overdue tasks
    overdue = tasks.filter(
        due_date__lt=timezone.now(),
        completed=False
    ).count()
    
    # Tasks due soon (next 7 days)
    end_date = timezone.now() + timedelta(days=7)
    due_soon = tasks.filter(
        due_date__lte=end_date,
        due_date__gte=timezone.now(),
        completed=False
    ).count()
    
    # Average progress
    progress_avg = tasks.aggregate(avg_progress=models.Avg('progress'))['avg_progress'] or 0
    
    # Priority distribution
    priority_distribution = tasks.values('priority').annotate(
        count=models.Count('id')
    ).order_by('priority')
    
    # Status distribution
    status_distribution = tasks.values('status').annotate(
        count=models.Count('id')
    ).order_by('status')
    
    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'overdue': overdue,
        'due_soon': due_soon,
        'average_progress': round(progress_avg, 1),
        'priority_distribution': list(priority_distribution),
        'status_distribution': list(status_distribution)
    }
