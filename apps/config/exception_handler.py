from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ErrorDetail, ValidationError as DRFValidationError
from django.http import Http404 as DjangoHttp404
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied
from django.utils import timezone
from rest_framework import status
from django.conf import settings
from django.db import IntegrityError, DatabaseError
from django.core.exceptions import ObjectDoesNotExist
import traceback
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Global exception handler for Django REST Framework.
    Formats error responses according to the specified API documentation structure.
    
    Args:
        exc: The exception that was raised
        context: Dictionary containing the request, view, and other context
        
    Returns:
        Response: Formatted error response
    """
    # Call REST framework's default exception handler first
    response = drf_exception_handler(exc, context)
    
    # Initialize default error response values
    error_code = "INTERNAL_ERROR"
    error_message = "An unexpected error occurred."
    error_details = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    should_log = True
    log_level = logging.ERROR
    
    # Get request and view information for logging
    request = context.get('request')
    view = context.get('view')
    view_name = view.__class__.__name__ if view else 'Unknown'
    
    try:
        # Handle different types of exceptions
        if response is not None:
            # DRF handled the exception
            status_code = response.status_code
            data = response.data
            
            # Map DRF exception codes to our error codes
            if hasattr(exc, 'default_code'):
                error_code = _map_drf_error_code(exc.default_code)
            
            # Extract error message and details from DRF response
            error_message, error_details = _extract_drf_error_info(data)
            
        elif isinstance(exc, DjangoValidationError):
            # Django model validation errors
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = "VALIDATION_ERROR"
            error_message, error_details = _extract_django_validation_error(exc)
            should_log = False  # Don't log validation errors as they're expected
            
        elif isinstance(exc, DjangoHttp404):
            # Django 404 errors
            status_code = status.HTTP_404_NOT_FOUND
            error_code = "NOT_FOUND"
            error_message = str(exc) if str(exc) else "The requested resource was not found."
            should_log = False
            
        elif isinstance(exc, DjangoPermissionDenied):
            # Django permission errors
            status_code = status.HTTP_403_FORBIDDEN
            error_code = "PERMISSION_DENIED"
            error_message = str(exc) if str(exc) else "You don't have permission to perform this action."
            should_log = False
            
        elif isinstance(exc, IntegrityError):
            # Database integrity errors
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = "INTEGRITY_ERROR"
            error_message = "Data integrity constraint violated."
            error_details = {"detail": str(exc)}
            should_log = True
            log_level = logging.WARNING
            
        elif isinstance(exc, DatabaseError):
            # Database errors
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_code = "DATABASE_ERROR"
            error_message = "A database error occurred."
            error_details = {"detail": str(exc)}
            should_log = True
            log_level = logging.ERROR
            
        elif isinstance(exc, ObjectDoesNotExist):
            # Object not found errors
            status_code = status.HTTP_404_NOT_FOUND
            error_code = "NOT_FOUND"
            error_message = "The requested object was not found."
            should_log = False
            
        elif isinstance(exc, ValueError):
            # Value errors
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = "INVALID_VALUE"
            error_message = str(exc) if str(exc) else "Invalid value provided."
            should_log = False
            
        elif isinstance(exc, TypeError):
            # Type errors
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = "TYPE_ERROR"
            error_message = "Invalid data type provided."
            error_details = {"detail": str(exc)}
            should_log = False
            
        else:
            # Unhandled exceptions
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_code = "INTERNAL_ERROR"
            error_message = str(exc) if str(exc) else "An unexpected error occurred."
            should_log = True
            log_level = logging.ERROR
        
        # Log the error if needed
        if should_log:
            _log_error(exc, context, error_code, error_message, log_level)
        
        # Construct the standardized error response
        error_response = _build_error_response(
            error_code, error_message, error_details, status_code, context
        )
        
        return error_response
        
    except Exception as handler_error:
        # If our exception handler fails, log it and return a basic error
        logger.error(f"Exception handler failed: {str(handler_error)}")
        logger.error(f"Original exception: {str(exc)}")
        
        return Response({
            "success": False,
            "error": {
                "code": "HANDLER_ERROR",
                "message": "An error occurred while processing your request.",
            },
            "timestamp": timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _map_drf_error_code(drf_code):
    """Map DRF exception codes to our standardized error codes."""
    error_code_map = {
        "invalid": "VALIDATION_ERROR",
        "parse_error": "PARSE_ERROR",
        "authentication_failed": "UNAUTHORIZED",
        "not_authenticated": "UNAUTHORIZED",
        "permission_denied": "FORBIDDEN",
        "not_found": "NOT_FOUND",
        "method_not_allowed": "METHOD_NOT_ALLOWED",
        "unsupported_media_type": "UNSUPPORTED_MEDIA_TYPE",
        "throttled": "TOO_MANY_REQUESTS",
        "server_error": "INTERNAL_ERROR",
        "error": "INTERNAL_ERROR",
    }
    return error_code_map.get(drf_code, "INTERNAL_ERROR")


def _extract_drf_error_info(data):
    """Extract error message and details from DRF response data."""
    error_message = "An error occurred."
    error_details = None
    
    if isinstance(data, dict):
        if 'detail' in data and isinstance(data['detail'], (str, ErrorDetail)):
            error_message = str(data['detail'])
        else:
            # Handle field-specific validation errors
            error_messages = []
            for field, errors in data.items():
                if isinstance(errors, list):
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
                else:
                    error_messages.append(f"{field}: {errors}")
            
            if error_messages:
                error_message = "Validation failed: " + "; ".join(error_messages)
            else:
                error_message = "Validation failed. Please check the details."
            error_details = data
            
    elif isinstance(data, list):
        error_message = "; ".join(map(str, data))
        error_details = data
        
    elif isinstance(data, (str, ErrorDetail)):
        error_message = str(data)
        
    return error_message, error_details


def _extract_django_validation_error(exc):
    """Extract error message and details from Django ValidationError."""
    if hasattr(exc, 'message_dict'):
        # Field-specific errors
        error_messages = []
        for field, errors in exc.message_dict.items():
            if isinstance(errors, list):
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            else:
                error_messages.append(f"{field}: {errors}")
        error_message = "Validation failed: " + "; ".join(error_messages)
        error_details = exc.message_dict
        
    elif hasattr(exc, 'message_list'):
        # Non-field errors
        error_message = "; ".join(exc.message_list)
        error_details = {"__all__": exc.message_list}
        
    else:
        # Single error message
        error_message = str(exc)
        error_details = {"__all__": [str(exc)]}
        
    return error_message, error_details


def _log_error(exc, context, error_code, error_message, log_level):
    """Log error information for debugging and monitoring."""
    request = context.get('request')
    view = context.get('view')
    
    # Check if we're in test mode
    import sys
    is_test_mode = 'test' in sys.argv or 'pytest' in sys.modules
    
    log_data = {
        "error_code": error_code,
        "error_message": error_message,
        "exception_type": type(exc).__name__,
        "view": view.__class__.__name__ if view else None,
        "request_method": request.method if request else None,
        "request_path": request.path if request else None,
        "user": request.user.username if request and request.user.is_authenticated else 'Anonymous',
    }
    
    # In test mode, be more selective about logging
    if is_test_mode:
        # Don't log expected test scenarios
        if error_code in ['UNAUTHORIZED', 'FORBIDDEN', 'NOT_FOUND']:
            # These are expected during tests, don't log them
            return
        
        # For validation errors in tests, only log if they're unexpected
        if error_code == 'VALIDATION_ERROR' and 'Invalid action' in error_message:
            # This is expected during tests, don't log it
            return
    
    if log_level == logging.ERROR:
        logger.error(f"API Error: {log_data}")
    elif log_level == logging.WARNING:
        logger.warning(f"API Warning: {log_data}")
    else:
        logger.info(f"API Info: {log_data}")


def _build_error_response(error_code, error_message, error_details, status_code, context):
    """Build the standardized error response."""
    request = context.get('request')
    
    # Base error response
    error_response_data = {
        "success": False,
        "error": {
            "code": error_code,
            "message": error_message,
        },
        "timestamp": timezone.now().isoformat()
    }
    
    # Add error details if available
    if error_details:
        error_response_data["error"]["details"] = error_details
    
    # Add debug information when DEBUG is True
    if settings.DEBUG:
        debug_info = _build_debug_info(context, error_code)
        error_response_data["error"]["debug"] = debug_info
    
    # Add request ID if available (useful for tracking)
    if request and hasattr(request, 'id'):
        error_response_data["request_id"] = request.id
    
    return Response(error_response_data, status=status_code)


def _build_debug_info(context, error_code):
    """Build debug information for development."""
    request = context.get('request')
    view = context.get('view')
    
    debug_info = {
        "exception_type": context.get('exception_type', 'Unknown'),
        "view": view.__class__.__name__ if view else None,
        "request_method": request.method if request else None,
        "request_path": request.path if request else None,
        "user_agent": request.META.get('HTTP_USER_AGENT', 'Unknown') if request else None,
    }
    
    # Add request data for validation errors to help with debugging
    if error_code == "VALIDATION_ERROR" and request and hasattr(request, 'data'):
        try:
            debug_info["request_data"] = request.data
        except Exception:
            debug_info["request_data"] = "Unable to serialize request data"
    
    # Add traceback for internal errors
    if error_code == "INTERNAL_ERROR":
        debug_info["traceback"] = traceback.format_exc()
    
    return debug_info


def create_error_response(message, error_code="BAD_REQUEST", status_code=status.HTTP_400_BAD_REQUEST, details=None):
    """
    Creates a standardized error response object for manual error handling in views.
    Its structure matches the global exception handler.
    
    Args:
        message (str): Error message
        error_code (str): Error code
        status_code (int): HTTP status code
        details (dict, optional): Additional error details
        
    Returns:
        Response: Formatted error response
        
    Example:
        return create_error_response(
            "User not found", 
            "NOT_FOUND", 
            status.HTTP_404_NOT_FOUND
        )
    """
    error_data = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        },
        "timestamp": timezone.now().isoformat()
    }
    
    if details:
        error_data["error"]["details"] = details
    
    return Response(error_data, status=status_code)


def create_validation_error_response(field_errors, message="Validation failed"):
    """
    Creates a standardized validation error response.
    
    Args:
        field_errors (dict): Field-specific validation errors
        message (str): General validation error message
        
    Returns:
        Response: Formatted validation error response
        
    Example:
        return create_validation_error_response({
            "email": ["This field is required."],
            "password": ["Password is too short."]
        })
    """
    return create_error_response(
        message=message,
        error_code="VALIDATION_ERROR",
        status_code=status.HTTP_400_BAD_REQUEST,
        details=field_errors
    )


def create_not_found_response(message="Resource not found"):
    """Creates a standardized not found error response."""
    return create_error_response(
        message=message,
        error_code="NOT_FOUND",
        status_code=status.HTTP_404_NOT_FOUND
    )


def create_permission_error_response(message="Permission denied"):
    """Creates a standardized permission denied error response."""
    return create_error_response(
        message=message,
        error_code="PERMISSION_DENIED",
        status_code=status.HTTP_403_FORBIDDEN
    )


def create_unauthorized_response(message="Authentication required"):
    """Creates a standardized unauthorized error response."""
    return create_error_response(
        message=message,
        error_code="UNAUTHORIZED",
        status_code=status.HTTP_401_UNAUTHORIZED
    )
