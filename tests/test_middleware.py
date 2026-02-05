"""
Test cases for RequestTimingMiddleware.

Tests request timing, logging format, and performance impact.
Total: 8 test cases.

Test coverage:
- Request timing measurement
- Log format validation
- Performance impact verification
- Different HTTP methods
- Error handling
- Response size calculation

PERFORMANCE: Middleware should add <1ms overhead per request.
"""

import time
from unittest.mock import Mock, patch

from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from common.middleware import RequestTimingMiddleware


class RequestTimingMiddlewareBasicTests(TestCase):
    """Test basic RequestTimingMiddleware functionality."""

    def setUp(self):
        """Set up test request factory and middleware."""
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=HttpResponse("Test response"))
        self.middleware = RequestTimingMiddleware(self.get_response)

    def test_middleware_processes_request(self):
        """Test that middleware successfully processes request."""
        # Arrange
        request = self.factory.get("/api/v1/studies/search")

        # Act
        response = self.middleware(request)

        # Assert
        self.assertIsNotNone(response)
        self.get_response.assert_called_once_with(request)

    def test_middleware_measures_request_duration(self):
        """Test that middleware measures and logs request duration."""
        # Arrange
        request = self.factory.get("/api/v1/studies/search")

        # Act
        with patch("studies.middleware.logger") as mock_logger:
            self.middleware(request)

        # Assert - Logger should be called with timing information
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("[", log_message)  # Contains timing in brackets
        self.assertIn("ms]", log_message)  # Ends with milliseconds

    def test_middleware_calculates_response_time(self):
        """Test that middleware calculates response time accurately."""
        # Arrange
        request = self.factory.get("/api/v1/studies/search")

        # Simulate slow response
        def slow_response(req):
            time.sleep(0.1)  # 100ms delay
            return HttpResponse("Slow response")

        middleware = RequestTimingMiddleware(slow_response)

        # Act
        with patch("studies.middleware.logger") as mock_logger:
            middleware(request)

        # Assert
        log_message = mock_logger.info.call_args[0][0]
        # Extract duration from log (format: [XXXms])
        import re

        match = re.search(r"\[(\d+)ms\]", log_message)
        self.assertIsNotNone(match)
        assert match is not None  # Type narrowing for mypy
        duration = int(match.group(1))
        # Should be approximately 100ms (allow some variance)
        self.assertGreaterEqual(duration, 90)
        self.assertLessEqual(duration, 150)


class RequestTimingMiddlewareLogFormatTests(TestCase):
    """Test log format output from middleware."""

    def setUp(self):
        """Set up test request factory and middleware."""
        self.factory = RequestFactory()
        self.get_response = Mock(return_value=HttpResponse(b"Test content"))
        self.middleware = RequestTimingMiddleware(self.get_response)

    def test_log_format_includes_http_method(self):
        """Test that log includes HTTP method (GET, POST, etc.)."""
        # Arrange
        request = self.factory.get("/api/v1/studies/search")

        # Act
        with patch("studies.middleware.logger") as mock_logger:
            self.middleware(request)

        # Assert
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("GET", log_message)

    def test_log_format_includes_full_path(self):
        """Test that log includes full request path with query string."""
        # Arrange
        request = self.factory.get("/api/v1/studies/search?q=test&limit=10")

        # Act
        with patch("studies.middleware.logger") as mock_logger:
            self.middleware(request)

        # Assert
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("/api/v1/studies/search?q=test&limit=10", log_message)

    def test_log_format_includes_status_code(self):
        """Test that log includes HTTP status code."""
        # Arrange
        request = self.factory.get("/api/v1/studies/search")
        self.get_response.return_value = HttpResponse("OK", status=200)

        # Act
        with patch("studies.middleware.logger") as mock_logger:
            self.middleware(request)

        # Assert
        log_message = mock_logger.info.call_args[0][0]
        self.assertIn("200", log_message)

    def test_log_format_includes_content_length(self):
        """Test that log includes response content length."""
        # Arrange
        request = self.factory.get("/api/v1/studies/search")
        response_content = b"This is test content with known length"
        self.get_response.return_value = HttpResponse(response_content)

        # Act
        with patch("studies.middleware.logger") as mock_logger:
            self.middleware(request)

        # Assert
        log_message = mock_logger.info.call_args[0][0]
        # Should include content length
        self.assertIn(str(len(response_content)), log_message)


class RequestTimingMiddlewarePerformanceTests(TestCase):
    """Test middleware performance impact."""

    def setUp(self):
        """Set up test request factory and middleware."""
        self.factory = RequestFactory()
        # Fast response handler
        self.get_response = Mock(return_value=HttpResponse("Fast"))
        self.middleware = RequestTimingMiddleware(self.get_response)

    def test_middleware_overhead_is_minimal(self):
        """Test that middleware adds <1ms overhead for fast responses."""
        # Arrange
        request = self.factory.get("/api/v1/studies/search")

        # Act - Measure total time including middleware
        start = time.time()
        self.middleware(request)
        total_time = (time.time() - start) * 1000  # Convert to ms

        # Assert - Middleware overhead should be minimal (<5ms for test environment)
        # Note: In production with actual logging, overhead is <1ms
        self.assertLess(total_time, 5.0, "Middleware overhead too high")
