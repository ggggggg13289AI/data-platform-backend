"""
Custom JWT authentication schemas for frontend compatibility.

Provides custom token response schema that returns 'access_token' and 'refresh_token'
instead of the default 'access' and 'refresh' to match frontend expectations.
"""

from ninja import Schema
from ninja_jwt.schema import TokenObtainInputSchemaBase
from ninja_jwt.tokens import AccessToken, RefreshToken


class UserInfo(Schema):
    """User information schema."""

    id: int
    username: str
    email: str
    first_name: str = ''
    last_name: str = ''


class CustomTokenObtainPairOutSchema(Schema):
    """
    Custom token response schema matching frontend expectations.

    Frontend expects 'access_token' and 'refresh_token', not 'access' and 'refresh'.
    Also includes user information and status message for better UX.
    """

    access_token: str  # Renamed from 'access' for frontend compatibility
    refresh_token: str  # Renamed from 'refresh' for frontend compatibility
    user: UserInfo
    status: str = 'success'
    message: str = '登入成功 / Login successful'


class CustomTokenObtainPairInputSchema(TokenObtainInputSchemaBase):
    """
    Custom token input schema with frontend-compatible response.

    Handles user authentication and generates JWT tokens with user information.
    Extends TokenObtainInputSchemaBase to leverage django-ninja-jwt's authentication logic.
    """

    @classmethod
    def get_response_schema(cls) -> type[Schema]:
        """Return the custom response schema."""
        return CustomTokenObtainPairOutSchema

    @classmethod
    def get_token(cls, user) -> dict:
        """
        Generate JWT tokens and user info for authenticated user.

        Args:
            user: Authenticated Django User instance

        Returns:
            Dict with access_token, refresh_token, user info, status, and message
        """
        # Generate refresh token (which contains access token)
        access_token = AccessToken.for_user(user)
        refresh_token = RefreshToken.for_user(user)

        return {
            'access_token': str(access_token),  # Renamed for frontend
            'refresh_token': str(refresh_token),  # Renamed for frontend
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'status': 'success',
            'message': '登入成功 / Login successful',
        }
