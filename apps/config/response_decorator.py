from functools import wraps
from rest_framework.response import Response
from django.utils import timezone
from rest_framework import status as drf_status
import logging

logger = logging.getLogger(__name__)


def format_api_response(default_message_on_success=None, default_status_code_on_success=drf_status.HTTP_200_OK):
    """
    A decorator to format successful API responses according to a standard structure.
    
    The wrapped view function should return:
    1. The raw data payload (this will be put into the "data" field of the response).
    2. OR a tuple: (data_payload, "custom success message")
    3. OR a tuple: (data_payload, "custom success message", custom_status_code)
    4. OR a full `rest_framework.response.Response` object if it wants to bypass this decorator's formatting.
    
    Errors are expected to be raised as exceptions and handled by DRF's exception handler
    (ideally your `custom_exception_handler`).
    
    Args:
        default_message_on_success (str, optional): Default success message if none provided
        default_status_code_on_success (int): Default HTTP status code for success responses
        
    Returns:
        function: Decorated view function
        
    Example:
        @format_api_response("User created successfully", status.HTTP_201_CREATED)
        def create_user(request):
            # ... create user logic ...
            return user_data  # Will be wrapped in standard response format
            
        @format_api_response()
        def get_users(request):
            # ... get users logic ...
            return users, "Users retrieved successfully"  # Custom message
            
        @format_api_response()
        def delete_user(request):
            # ... delete user logic ...
            return None, "User deleted", status.HTTP_204_NO_CONTENT  # Custom status
    """

    def actual_decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(*args, **kwargs):
            try:
                # Execute the view function
                result = view_func(*args, **kwargs)

                # If the view returns a full Response object, pass it through (bypass decorator)
                if isinstance(result, Response):
                    return result

                # Initialize default values
                data_payload = None
                effective_message = default_message_on_success or "Operation completed successfully."
                effective_status_code = default_status_code_on_success

                # Parse the result based on its type
                if isinstance(result, tuple):
                    if len(result) == 3:  # (data, message, status_code)
                        data_payload, effective_message, effective_status_code = result
                    elif len(result) == 2:  # (data, message)
                        data_payload, effective_message = result
                    else:  # Assumes a tuple not matching the above is just complex data intended for the 'data' field
                        data_payload = result
                else:  # Assumes a non-tuple result is the data payload
                    data_payload = result

                # Handle HTTP 204 No Content responses
                if effective_status_code == drf_status.HTTP_204_NO_CONTENT:
                    return Response(None, status=drf_status.HTTP_204_NO_CONTENT)

                # Construct the standardized response
                response_dict = {
                    "success": True,
                    "data": data_payload if data_payload is not None else {},
                    "message": str(effective_message),
                    "timestamp": timezone.now().isoformat()
                }

                # Log successful responses for monitoring (optional)
                logger.debug(f"API Response: {effective_message} - Status: {effective_status_code}")

                return Response(response_dict, status=effective_status_code)

            except Exception as e:
                # Log unexpected errors that weren't caught by the view
                logger.error(f"Unexpected error in {view_func.__name__}: {str(e)}")
                # Re-raise to let DRF's exception handler deal with it
                raise

        return _wrapped_view

    return actual_decorator


def format_list_response(default_message="Items retrieved successfully"):
    """
    Specialized decorator for list views that automatically handles pagination.
    
    Args:
        default_message (str): Default success message for list operations
        
    Returns:
        function: Decorated view function
        
    Example:
        @format_list_response("Users retrieved successfully")
        def get_users(request):
            users = User.objects.all()
            return users  # Will be automatically paginated and formatted
    """
    return format_api_response(default_message)


def format_create_response(default_message="Item created successfully"):
    """
    Specialized decorator for create views.
    
    Args:
        default_message (str): Default success message for create operations
        
    Returns:
        function: Decorated view function
        
    Example:
        @format_create_response("User created successfully")
        def create_user(request):
            # ... create user logic ...
            return user_data, status.HTTP_201_CREATED
    """
    return format_api_response(default_message, drf_status.HTTP_201_CREATED)


def format_update_response(default_message="Item updated successfully"):
    """
    Specialized decorator for update views.
    
    Args:
        default_message (str): Default success message for update operations
        
    Returns:
        function: Decorated view function
        
    Example:
        @format_update_response("User updated successfully")
        def update_user(request):
            # ... update user logic ...
            return updated_user_data
    """
    return format_api_response(default_message)


def format_delete_response(default_message="Item deleted successfully"):
    """
    Specialized decorator for delete views.
    
    Args:
        default_message (str): Default success message for delete operations
        
    Returns:
        function: Decorated view function
        
    Example:
        @format_delete_response("User deleted successfully")
        def delete_user(request):
            # ... delete user logic ...
            return None, status.HTTP_204_NO_CONTENT
    """
    return format_api_response(default_message, drf_status.HTTP_204_NO_CONTENT)


def format_detail_response(default_message="Item retrieved successfully"):
    """
    Specialized decorator for detail/retrieve views.
    
    Args:
        default_message (str): Default success message for retrieve operations
        
    Returns:
        function: Decorated view function
        
    Example:
        @format_detail_response("User retrieved successfully")
        def get_user(request, user_id):
            user = get_object_or_404(User, id=user_id)
            return user_data
    """
    return format_api_response(default_message)


# Convenience decorators for common HTTP methods
def get_response(message="Items retrieved successfully"):
    """Decorator for GET requests."""
    return format_api_response(message)


def post_response(message="Item created successfully"):
    """Decorator for POST requests."""
    return format_api_response(message, drf_status.HTTP_201_CREATED)


def put_response(message="Item updated successfully"):
    """Decorator for PUT requests."""
    return format_api_response(message)


def patch_response(message="Item updated successfully"):
    """Decorator for PATCH requests."""
    return format_api_response(message)


def delete_response(message="Item deleted successfully"):
    """Decorator for DELETE requests."""
    return format_api_response(message, drf_status.HTTP_204_NO_CONTENT)
