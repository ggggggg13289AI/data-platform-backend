"""
Authentication API endpoints with JWT token authentication.

Provides user authentication functionality:
- POST /auth/login - User login returning JWT tokens
- POST /auth/logout - User logout (token invalidation)
- GET /auth/me - Get current authenticated user via JWT
- POST /auth/refresh - Refresh access token

Uses JWT (JSON Web Tokens) for stateless authentication.
"""

import logging

from django.contrib.auth import authenticate
from django.http import HttpRequest
from ninja import Form, Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.schema import TokenRefreshInputSchema, TokenRefreshOutputSchema

from .auth_schemas import (
    CustomTokenObtainPairInputSchema,
    CustomTokenObtainPairOutSchema,
)
from .schemas import StatusResponse, UserInfo, UserResponse

logger = logging.getLogger(__name__)

# Create authentication router
auth_router = Router()


@auth_router.post('/login', response=CustomTokenObtainPairOutSchema)
def user_login(
    request: HttpRequest,
    username: Form[str],
    password: Form[str],
):
    """
    JWT login endpoint - Accepts form-data only.

    Authenticates user with username and password, returns JWT access and refresh tokens.

    Supports content types:
    - application/x-www-form-urlencoded
    - multipart/form-data

    Args:
        request: Django HTTP request object
        username: Username from form data (required)
        password: Password from form data (required)

    Returns:
        CustomTokenObtainPairOutSchema with tokens and user info

    Status Codes:
        200: Login successful
        400: Missing credentials
        401: Invalid credentials
        500: Server error

    Example (Form Data):
        POST /api/v1/auth/login
        Content-Type: application/x-www-form-urlencoded

        username=user&password=user

    Response:
        {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "user": {
                "id": 1,
                "username": "user",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe"
            },
            "status": "success",
            "message": "登入成功 / Login successful"
        }
    """
    try:
        # Validate form data
        if not username or not password:
            logger.warning('Login failed: Missing username or password')
            raise HttpError(400, '請提供用戶名和密碼 / Username and password required')

        logger.info(f'Login attempt for user: {username}')

        # Authenticate user using Django's authenticate
        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            logger.info(f'User login successful: {username}')

            # Generate JWT tokens and user info directly
            token_data = CustomTokenObtainPairInputSchema.get_token(user)

            # Return the complete token response
            return CustomTokenObtainPairOutSchema(**token_data)
        else:
            logger.warning(f'Login failed for user: {username}')
            raise HttpError(401, '帳號或密碼錯誤 / Invalid username or password')

    except HttpError:
        raise
    except Exception as e:
        logger.error(f'Login error: {str(e)}')
        raise HttpError(500, '登入失敗，請稍後再試 / Login failed, please try again') from e


@auth_router.post('/refresh', response=TokenRefreshOutputSchema)
def refresh_token(request: HttpRequest, refresh_data: TokenRefreshInputSchema):
    """
    Refresh access token using refresh token.

    Generates a new access token from a valid refresh token.

    Args:
        request: Django HTTP request object
        refresh_data: Refresh token data

    Returns:
        TokenRefreshOutputSchema with new access token

    Status Codes:
        200: Token refreshed successfully
        401: Invalid or expired refresh token

    Example:
        POST /api/v1/auth/refresh
        Content-Type: application/json

        {
            "refresh": "eyJ0eXAiOiJKV1Qi..."
        }

        Response:
        {
            "access": "eyJ0eXAiOiJKV1Qi..."
        }

    Note:
        Frontend should replace the old access_token with the new one.
    """
    return refresh_data.to_response_schema()


@auth_router.post('/logout', response=StatusResponse, auth=JWTAuth())
def user_logout(request: HttpRequest):
    """
    JWT logout endpoint.

    Logs out user by marking token for client-side deletion.
    With JWT, logout is primarily handled client-side (delete tokens).

    Args:
        request: Django HTTP request object with JWT authentication

    Returns:
        StatusResponse indicating logout success

    Status Codes:
        200: Logout successful
        401: Not authenticated

    Example:
        POST /api/v1/auth/logout
        Authorization: Bearer eyJ0eXAiOiJKV1Qi...

        Response:
        {
            "status": "success",
            "message": "登出成功 / Logout successful"
        }

    Note:
        Frontend should delete access_token and refresh_token from storage.
        Optional: Backend can blacklist refresh token if provided.
    """
    try:
        # Get username from JWT auth
        username = (
            request.auth.username if hasattr(request.auth, 'username') else 'unknown'  # type: ignore[attr-defined]
        )
        logger.info(f'User logout: {username}')

        # Note: With JWT, logout is primarily client-side
        # Token blacklisting can be added here if needed

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


@auth_router.get('/me', response=UserResponse, auth=JWTAuth())
def get_current_user(request: HttpRequest):
    """
    Get current authenticated user via JWT.

    Returns information about the currently authenticated user based on JWT token.

    Args:
        request: Django HTTP request object with JWT authentication

    Returns:
        UserResponse with current user information

    Status Codes:
        200: User information retrieved successfully
        401: Not authenticated or invalid token

    Example:
        GET /api/v1/auth/me
        Authorization: Bearer eyJ0eXAiOiJKV1Qi...

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

    Note:
        JWT authentication is required. If token is invalid or missing,
        returns 401 error automatically.
    """
    try:
        # request.auth is automatically populated by JWTAuth
        user = request.auth  # type: ignore[attr-defined]

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

    except Exception as e:
        logger.error(f'Get current user error: {str(e)}')
        return UserResponse(
            status='error',
            user=None,
            message='取得使用者資訊失敗 / Failed to get user information',
        )
