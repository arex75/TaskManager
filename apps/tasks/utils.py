from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError
from datetime import timedelta
import re


def validate_hex_color(color):
    """
    Validate hex color format
    
    Args:
        color (str): Hex color string
        
    Returns:
        bool: True if valid
        
    Raises:
        ValidationError: If color is invalid
    """
    if not color:
        raise ValidationError("Color cannot be empty or None")
    
    # Check if it's a valid hex color (#RRGGBB or #RGB)
    hex_pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
    if not hex_pattern.match(color):
        raise ValidationError(f"'{color}' is not a valid hex color. Must be #RGB or #RRGGBB format.")
    
    return True


def calculate_task_completion_time(started_at, completed_at):
    """
    Calculate the time it took to complete a task
    
    Args:
        started_at: When the task was started
        completed_at: When the task was completed
        
    Returns:
        float: Hours taken
        
    Raises:
        ValueError: If input is invalid
    """
    if not started_at or not completed_at:
        raise ValueError("Both started_at and completed_at must be provided")
    
    if completed_at < started_at:
        raise ValueError("completed_at must be after or equal to started_at")
    
    time_diff = completed_at - started_at
    return time_diff.total_seconds() / 3600  # Convert to hours


def calculate_estimated_vs_actual_hours(estimated_hours, actual_hours):
    """
    Calculate the difference between estimated and actual hours
    
    Args:
        estimated_hours: Estimated hours (Decimal)
        actual_hours: Actual hours (Decimal)
        
    Returns:
        dict: Dictionary with difference, percentage, and status
        
    Raises:
        ValueError: If inputs are invalid (None, negative, or zero)
    """
    # Validate inputs
    if estimated_hours is None or actual_hours is None:
        raise ValueError("Both estimated_hours and actual_hours must be provided")
    
    if estimated_hours <= 0:
        raise ValueError("Estimated hours must be positive")
    
    if actual_hours <= 0:
        raise ValueError("Actual hours must be positive")
    
    difference = float(estimated_hours) - float(actual_hours)  # estimated - actual
    percentage = (difference / float(estimated_hours)) * 100
    
    if difference == 0:
        status = 'exact'
    elif difference > 0:
        status = 'underestimated'
    else:
        status = 'overestimated'
    
    return {
        'difference': difference,  # Keep sign for over/under estimation
        'percentage': percentage,
        'status': status
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
        'HIGH': '#dc3545',     # Red
        'URGENT': '#6f42c1',   # Purple
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
        'PAUSED': '#ffc107',         # Yellow
        'COMPLETED': '#28a745',      # Green
        'BLOCKED': '#dc3545',        # Red
        'CANCELLED': '#dc3545',      # Red
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
    if hours is None:
        return "0 minutes"
    
    if hours < 0:
        raise ValueError("Hours cannot be negative")
    
    if not hours:
        return "0 minutes"
    
    hours_float = float(hours)
    whole_hours = int(hours_float)
    # Don't round here for very small values
    if hours_float < 0.1:
        minutes = (hours_float - whole_hours) * 60
    else:
        minutes = round((hours_float - whole_hours) * 60)
    
    if hours_float >= 24:
        days = int(hours_float // 24)
        remaining_hours = hours_float % 24
        
        # Handle weeks (7 days)
        if days >= 7 and days % 7 == 0:
            weeks = days // 7
            if weeks == 1:
                return "1 week"
            else:
                return f"{weeks} weeks"
        
        if remaining_hours == 0:
            if days == 1:
                return "1 day"
            else:
                return f"{days} days"
        else:
            # Handle remaining hours and minutes
            whole_remaining_hours = int(remaining_hours)
            remaining_minutes = int((remaining_hours - whole_remaining_hours) * 60)
            
            if whole_remaining_hours == 0:
                if remaining_minutes == 0:
                    if days == 1:
                        return "1 day"
                    else:
                        return f"{days} days"
                else:
                    if days == 1:
                        if remaining_minutes == 1:
                            return "1 day 1 minute"
                        else:
                            return f"1 day {remaining_minutes} minutes"
                    else:
                        if remaining_minutes == 1:
                            return f"{days} days 1 minute"
                        else:
                            return f"{days} days {remaining_minutes} minutes"
            else:
                if remaining_minutes == 0:
                    if days == 1:
                        if whole_remaining_hours == 1:
                            return "1 day 1 hour"
                        else:
                            return f"1 day {whole_remaining_hours} hours"
                    else:
                        if whole_remaining_hours == 1:
                            return f"{days} days 1 hour"
                        else:
                            return f"{days} days {whole_remaining_hours} hours"
                else:
                    if days == 1:
                        if whole_remaining_hours == 1:
                            if remaining_minutes == 1:
                                return "1 day 1 hour 1 minute"
                            else:
                                return f"1 day 1 hour {remaining_minutes} minutes"
                        else:
                            if remaining_minutes == 1:
                                return f"1 day {whole_remaining_hours} hours 1 minute"
                            else:
                                return f"1 day {whole_remaining_hours} hours {remaining_minutes} minutes"
                    else:
                        if whole_remaining_hours == 1:
                            if remaining_minutes == 1:
                                return f"{days} days 1 hour 1 minute"
                            else:
                                return f"{days} days 1 hour {remaining_minutes} minutes"
                        else:
                            if remaining_minutes == 1:
                                return f"{days} days {whole_remaining_hours} hours 1 minute"
                            else:
                                return f"{days} days {whole_remaining_hours} hours {remaining_minutes} minutes"
    
    if minutes == 0:
        if whole_hours == 1:
            return "1 hour"
        else:
            return f"{whole_hours} hours"
    elif whole_hours == 0:
        if minutes == 1:
            return "1 minute"
        else:
            # For very small values, show decimal minutes
            if hours_float < 0.1:  # Less than 6 minutes
                decimal_minutes = round(hours_float * 60, 1)
                if decimal_minutes == 1.0:
                    return "1.0 minute"
                else:
                    return f"{decimal_minutes} minutes"
            else:
                return f"{minutes} minutes"
    else:
        if whole_hours == 1:
            if minutes == 1:
                return "1 hour 1 minute"
            else:
                return f"1 hour {minutes} minutes"
        else:
            if minutes == 1:
                return f"{whole_hours} hours 1 minute"
            else:
                return f"{whole_hours} hours {minutes} minutes"


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
            'message': 'Completed',
            'days_remaining': 0
        }
    
    if not due_date:
        return {
            'status': 'no due date',
            'color': '#6c757d',
            'message': 'No due date',
            'days_remaining': None
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
            'days': days_overdue,
            'days_remaining': -days_overdue
        }
    
    elif time_diff.total_seconds() < 86400:  # Less than 1 day
        return {
            'status': 'due_today',
            'color': '#fd7e14',
            'message': 'Due today',
            'days_remaining': 0
        }
    
    elif time_diff.total_seconds() < 604800:  # Less than 1 week
        days_until = time_diff.days
        return {
            'status': 'due_soon',
            'color': '#ffc107',
            'message': f'Due in {days_until} days',
            'days_remaining': days_until
        }
    
    else:
        days_until = time_diff.days
        return {
            'status': 'due_later',
            'color': '#28a745',
            'message': f'Due in {days_until} days',
            'days_remaining': days_until
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
        
    Raises:
        ValueError: If input is invalid
    """
    # Validate input
    if estimated_hours is not None and estimated_hours <= 0:
        raise ValueError("Estimated hours must be positive")
    if actual_hours is not None and actual_hours <= 0:
        raise ValueError("Actual hours must be positive")
    if completed_at is None:
        raise ValueError("completed_at is required")
    if started_at is None:
        raise ValueError("started_at is required")
    
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
                'is_over_estimate': time_diff['difference'] > 0,
                'difference': time_diff['difference'],
                'status': time_diff['status']
            }
    
    # Completion speed
    if started_at and completed_at:
        completion_time = calculate_task_completion_time(started_at, completed_at)
        if completion_time is not None:
            metrics['completion_speed'] = {
                'duration': timedelta(hours=completion_time),
                'hours': completion_time
            }
    
    # Efficiency score (-100 to 100)
    score = 0
    
    # Base score for completion
    if metrics['completion_speed']:
        score += 30  # Task was completed
    
    # Time estimation accuracy
    if metrics['time_accuracy']:
        percentage_abs = abs(metrics['time_accuracy']['percentage'])
        if percentage_abs <= 20:
            score += 40  # Excellent time estimation
        elif percentage_abs <= 50:
            score += 20  # Good time estimation
        elif percentage_abs <= 100:
            score += 10  # Acceptable time estimation
        else:
            score -= 20  # Poor time estimation
        
        # Penalty for overestimation (taking longer than estimated)
        if metrics['time_accuracy']['status'] == 'overestimated':
            score -= 50  # Stronger penalty for overestimation
        elif metrics['time_accuracy']['status'] == 'underestimated':
            score += 20  # Bonus for completing early
    
    metrics['efficiency_score'] = max(-100, min(score, 100))
    
    # Add productivity rating
    if score >= 80:
        metrics['productivity_rating'] = 'Excellent'
    elif score >= 60:
        metrics['productivity_rating'] = 'Good'
    elif score >= 40:
        metrics['productivity_rating'] = 'Fair'
    else:
        metrics['productivity_rating'] = 'Poor'
    
    return metrics


def generate_task_summary(tasks, include_tags=False):
    """
    Generate a summary of tasks
    
    Args:
        tasks: QuerySet of tasks
        include_tags: Whether to include tag breakdown
        
    Returns:
        dict: Task summary statistics
    """
    if not tasks:
        return {
            'total_tasks': 0,
            'completed': 0,
            'in_progress': 0,
            'overdue': 0,
            'due_soon': 0,
            'average_progress': 0,
            'completion_rate': 0.0,
            'priority_breakdown': {},
            'status_breakdown': {},
            'tag_breakdown': {} if include_tags else None
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
    
    # Completion rate
    completion_rate = (completed / total * 100) if total > 0 else 0.0
    
    # Priority breakdown
    priority_breakdown = {}
    for priority_data in tasks.values('priority').annotate(count=models.Count('id')):
        priority_breakdown[priority_data['priority']] = priority_data['count']
    
    # Status breakdown
    status_breakdown = {}
    for status_data in tasks.values('status').annotate(count=models.Count('id')):
        status_breakdown[status_data['status']] = status_data['count']
    
    # Tag breakdown (if requested)
    tag_breakdown = {}
    if include_tags:
        for tag_data in tasks.values('tags__name').annotate(count=models.Count('id')):
            if tag_data['tags__name']:
                tag_breakdown[tag_data['tags__name']] = tag_data['count']
    
    return {
        'total_tasks': total,
        'completed': completed,
        'in_progress': in_progress,
        'overdue': overdue,
        'due_soon': due_soon,
        'average_progress': round(progress_avg, 1),
        'completion_rate': round(completion_rate, 1),
        'priority_breakdown': priority_breakdown,
        'status_breakdown': status_breakdown,
        'tag_breakdown': tag_breakdown if include_tags else None
    }
