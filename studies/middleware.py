"""
Custom middleware for request timing and logging.
Logs every API request with response time for performance monitoring.
"""

import time
import logging

logger = logging.getLogger('request_timing')


class RequestTimingMiddleware:
    """
    Middleware to measure and log request processing time.

    Logs format:
    "GET /api/v1/studies/search?q=... HTTP/1.1" 200 15053 [125ms]

    Performance impact: <1ms per request (negligible)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Record start time
        start_time = time.time()

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Get response size
        content_length = len(response.content) if hasattr(response, 'content') else 0

        # Log request with timing
        logger.info(
            f'"{request.method} {request.get_full_path()} '
            f'{request.META.get("SERVER_PROTOCOL", "HTTP/1.1")}" '
            f'{response.status_code} {content_length} '
            f'[{duration_ms:.0f}ms]'
        )

        return response
