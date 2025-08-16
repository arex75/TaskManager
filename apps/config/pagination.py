from rest_framework import pagination
from rest_framework.response import Response
from django.utils import timezone


class CustomPagination(pagination.PageNumberPagination):
    """
    Custom pagination class that provides a standardized response format
    with enhanced pagination metadata.
    """
    page_size = 20
    page_size_query_param = 'per_page'  # Allow client to specify 'per_page'
    max_page_size = 100
    page_query_param = 'page'  # Custom page parameter name

    def get_paginated_response(self, data):
        """
        Return a paginated response with enhanced metadata.
        
        Args:
            data: The serialized data for the current page
            
        Returns:
            Response: Formatted response with pagination metadata
        """
        # Get Django's Paginator object
        paginator = self.page.paginator
        
        # Calculate additional pagination info
        current_page = self.page.number
        per_page = self.get_page_size(self.request)
        total_pages = paginator.num_pages
        total_count = paginator.count
        
        # Calculate page ranges for navigation
        page_range = self._get_page_range(current_page, total_pages)
        
        # Calculate offset and limit info
        start_index = (current_page - 1) * per_page + 1
        end_index = min(current_page * per_page, total_count)
        
        return Response({
            "success": True,
            "data": {
                "results": data,  # The serialized data for the current page
                "pagination": {
                    "page": current_page,
                    "per_page": per_page,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "has_next": self.page.has_next(),
                    "has_previous": self.page.has_previous(),
                    "next_page": self.page.next_page_number() if self.page.has_next() else None,
                    "previous_page": self.page.previous_page_number() if self.page.has_previous() else None,
                    "start_index": start_index if total_count > 0 else 0,
                    "end_index": end_index if total_count > 0 else 0,
                    "page_range": page_range,  # Useful for pagination UI
                    "is_first_page": current_page == 1,
                    "is_last_page": current_page == total_pages,
                }
            },
            "message": "Items retrieved successfully",
            "timestamp": timezone.now().isoformat()
        })
    
    def _get_page_range(self, current_page, total_pages, window=2):
        """
        Generate a page range around the current page for navigation.
        
        Args:
            current_page: Current page number
            total_pages: Total number of pages
            window: Number of pages to show on each side of current page
            
        Returns:
            list: List of page numbers to display
        """
        if total_pages <= 1:
            return [1]
        
        start = max(1, current_page - window)
        end = min(total_pages, current_page + window)
        
        # Always include first and last page if they're not in the range
        pages = list(range(start, end + 1))
        
        if 1 not in pages:
            pages.insert(0, 1)
        if total_pages not in pages and total_pages > 1:
            pages.append(total_pages)
        
        return pages


class LargePagePagination(CustomPagination):
    """
    Pagination class for larger page sizes, useful for admin interfaces
    or data export scenarios.
    """
    page_size = 50
    max_page_size = 200


class SmallPagePagination(CustomPagination):
    """
    Pagination class for smaller page sizes, useful for mobile interfaces
    or when you want to minimize data transfer.
    """
    page_size = 10
    max_page_size = 50


class NoCountPagination(pagination.PageNumberPagination):
    """
    Pagination class that doesn't count total items, useful for large datasets
    where counting is expensive.
    """
    page_size = 20
    page_size_query_param = 'per_page'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        Return paginated response without total count for performance.
        """
        current_page = self.page.number
        per_page = self.get_page_size(self.request)
        has_next = self.page.has_next()
        has_previous = self.page.has_previous()
        
        return Response({
            "success": True,
            "data": {
                "results": data,
                "pagination": {
                    "page": current_page,
                    "per_page": per_page,
                    "has_next": has_next,
                    "has_previous": has_previous,
                    "next_page": self.page.next_page_number() if has_next else None,
                    "previous_page": self.page.previous_page_number() if has_previous else None,
                    "is_first_page": current_page == 1,
                    "is_last_page": not has_next,
                }
            },
            "message": "Items retrieved successfully",
            "timestamp": timezone.now().isoformat()
        })
