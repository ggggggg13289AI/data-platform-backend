"""
Pydantic schemas for Django Ninja API.
CRITICAL: These must match FastAPI response format EXACTLY.
Type safety through Pydantic validation.
"""

from ninja import Field, Schema

# ============================================================================
# Authentication Schemas
# ============================================================================

class LoginRequest(Schema):
    """Login request schema.

    Used for POST /api/v1/auth/login endpoint.
    """
    username: str = Field(..., min_length=1, max_length=150, description='Username')
    password: str = Field(..., min_length=1, description='Password')


class UserInfo(Schema):
    """User information schema.

    Returned after successful authentication or when fetching current user.
    """
    id: int
    username: str
    email: str
    first_name: str = ""
    last_name: str = ""


class AuthResponse(Schema):
    """Authentication response with user information.

    Used for login endpoint responses.
    """
    status: str  # "success" | "error"
    message: str
    user: UserInfo | None = None


class UserResponse(Schema):
    """Current user information response.

    Used for /auth/me endpoint.
    """
    status: str  # "success" | "error"
    user: UserInfo | None = None
    message: str | None = None


class StatusResponse(Schema):
    """Simple status response.

    Used for logout and other status-only endpoints.
    """
    status: str  # "success" | "error"
    message: str
