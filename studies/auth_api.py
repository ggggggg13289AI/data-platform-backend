"""
Authentication API endpoints.

Provides user authentication functionality:
- POST /auth/login - User login with username/password
- POST /auth/logout - User logout
- GET /auth/me - Get current authenticated user information

Uses Django Session-based authentication for security.
"""

from ninja import Router, Form
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest
import logging

from .schemas import (
    LoginRequest,
    AuthResponse,
    UserResponse,
    StatusResponse,
    UserInfo,
)

logger = logging.getLogger(__name__)

# Create authentication router
auth_router = Router()


@auth_router.post('/login', response=AuthResponse)
def user_login(
    request: HttpRequest,
    username: str = Form(...),
    password: str = Form(...),
):
    """
    User login endpoint.

    Authenticates user with username and password, creates session on success.

    Args:
        request: Django HTTP request object
        username: User's username (form data)
        password: User's password (form data)

    Returns:
        AuthResponse with user information on success

    Status Codes:
        200: Login successful
        401: Invalid credentials

    Example:
        POST /api/v1/auth/login
        Form Data: username=user&password=user

        Response:
        {
            "status": "success",
            "message": "登入成功 / Login successful",
            "user": {
                "id": 1,
                "username": "user",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe"
            }
        }
    """
    try:
        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Authentication successful - create session
            login(request, user)

            logger.info(f'User login successful: {username}')

            return AuthResponse(
                status='success',
                message='登入成功 / Login successful',
                user=UserInfo(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                ),
            )
        else:
            # Authentication failed
            logger.warning(f'Login failed for user: {username}')

            return AuthResponse(
                status='error',
                message='帳號或密碼錯誤 / Invalid username or password',
                user=None,
            )

    except Exception as e:
        logger.error(f'Login error: {str(e)}')
        return AuthResponse(
            status='error',
            message='登入失敗，請稍後再試 / Login failed, please try again',
            user=None,
        )


@auth_router.post('/logout', response=StatusResponse)
def user_logout(request: HttpRequest):
    """
    User logout endpoint.

    Logs out the current user and destroys the session.

    Args:
        request: Django HTTP request object

    Returns:
        StatusResponse indicating logout success

    Status Codes:
        200: Logout successful

    Example:
        POST /api/v1/auth/logout

        Response:
        {
            "status": "success",
            "message": "登出成功 / Logout successful"
        }
    """
    try:
        username = request.user.username if request.user.is_authenticated else 'anonymous'

        # Logout user and clear session
        logout(request)

        logger.info(f'User logout successful: {username}')

        return StatusResponse(
            status='success',
            message='登出成功 / Logout successful',
        )

    except Exception as e:
        logger.error(f'Logout error: {str(e)}')
        return StatusResponse(
            status='error',
            message='登出失敗 / Logout failed',
        )


@auth_router.get('/me', response=UserResponse)
def get_current_user(request: HttpRequest):
    """
    Get current authenticated user information.

    Returns information about the currently logged-in user.

    Args:
        request: Django HTTP request object

    Returns:
        UserResponse with current user information or error

    Status Codes:
        200: User information retrieved successfully
        401: Not authenticated

    Example (authenticated):
        GET /api/v1/auth/me

        Response:
        {
            "status": "success",
            "user": {
                "id": 1,
                "username": "user",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe"
            }
        }

    Example (not authenticated):
        GET /api/v1/auth/me

        Response:
        {
            "status": "error",
            "message": "未登入 / Not authenticated",
            "user": null
        }
    """
    try:
        if request.user.is_authenticated:
            # User is authenticated - return user information
            user = request.user

            return UserResponse(
                status='success',
                user=UserInfo(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                ),
                message=None,
            )
        else:
            # User not authenticated
            return UserResponse(
                status='error',
                user=None,
                message='未登入 / Not authenticated',
            )

    except Exception as e:
        logger.error(f'Get current user error: {str(e)}')
        return UserResponse(
            status='error',
            user=None,
            message='取得使用者資訊失敗 / Failed to get user information',
        )
