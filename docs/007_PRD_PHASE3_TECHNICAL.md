# Technical Requirements Document - Phase 3

**Medical Imaging Management System - Django Backend**

---

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Status** | Draft |
| **Date** | 2025-11-10 |
| **Author** | Engineering Team |
| **Related Documents** | PRD_PHASE3.md, API_REFERENCE.md, DEVELOPMENT_SETUP.md |
| **Document ID** | TRD-PHASE3-001 |
| **Creation Timestamp** | 2025-11-10T14:30:00Z |

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Technical Architecture](#technical-architecture)
3. [Security Architecture](#security-architecture)
4. [Database Schema Changes](#database-schema-changes)
5. [API Specifications](#api-specifications)
6. [Performance Specifications](#performance-specifications)
7. [Infrastructure Requirements](#infrastructure-requirements)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Strategy](#deployment-strategy)
10. [Monitoring and Observability](#monitoring-and-observability)
11. [Migration Plan](#migration-plan)
12. [Technical Constraints](#technical-constraints)
13. [Appendices](#appendices)

---

## 1. Executive Summary

### 1.1 Technical Vision

Transform the Medical Imaging Management System into a **secure, monitored, and operationally excellent platform** through systematic implementation of authentication, authorization, monitoring, and automation capabilities.

### 1.2 Technology Stack

**Current Stack (Phase 1&2)**:
```yaml
Backend:
  Framework: Django 5.0.x
  API: Django Ninja 1.3.x
  Database: PostgreSQL 15.x
  Cache: Redis 7.x / Local Memory
  Package Manager: UV (NOT pip)
  Python: 3.11+

Testing:
  Framework: pytest 7.x
  Coverage: pytest-cov (~85%)

Development:
  Linting: black, ruff
  Type Checking: mypy
  Documentation: Markdown
```

**Phase 3 Additions**:
```yaml
Security:
  Authentication: PyJWT 2.8.x
  Password Hashing: Django built-in (PBKDF2)
  CORS: django-cors-headers 4.3.x
  Rate Limiting: django-ratelimit 4.1.x

Monitoring:
  Metrics: django-prometheus 2.3.x
  APM: New Relic / DataDog (optional)
  Logging: structlog 23.x

Operations:
  Task Queue: Celery 5.3.x
  Message Broker: Redis 7.x
  CI/CD: GitHub Actions
  Container: Docker 24.x

Export/Reports:
  CSV: pandas 2.1.x
  Excel: openpyxl 3.1.x
  PDF: ReportLab 4.0.x
```

### 1.3 Design Principles

Following Linus Torvalds' principles:
- **Pragmatic**: Build for actual needs (5 concurrent users), not hypothetical scale
- **Simple**: Flat data structures, minimal relationships, explicit over implicit
- **Maintainable**: Clear code over clever abstractions
- **Testable**: ~90% test coverage target for Phase 3 code

---

## 2. Technical Architecture

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (React)                      │
└───────────────────┬─────────────────────────────────────────┘
                    │ HTTPS
┌───────────────────┴─────────────────────────────────────────┐
│                     Nginx (Reverse Proxy)                    │
│                   - SSL Termination                          │
│                   - Rate Limiting (Layer 7)                  │
│                   - Static Files                             │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────┴─────────────────────────────────────────┐
│                  Django Application (8001)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 Django Ninja API                      │  │
│  │  - Authentication Middleware (JWT)                    │  │
│  │  - RBAC Authorization                                │  │
│  │  - Request Timing Middleware                         │  │
│  │  - Audit Logging Middleware                          │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  Service Layer                        │  │
│  │  - StudyService (existing)                           │  │
│  │  - AuthService (new)                                 │  │
│  │  - ExportService (new)                               │  │
│  │  - AuditService (new)                                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   Model Layer                         │  │
│  │  - Study (existing)                                  │  │
│  │  - User, Role, Permission (new)                      │  │
│  │  - AuditLog (new)                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────┬────────────┬────────────────────────────┘
                    │            │
        ┌───────────┴──┐    ┌────┴──────┐
        │  PostgreSQL  │    │   Redis   │
        │              │    │  - Cache  │
        │  - Studies   │    │  - Queue  │
        │  - Users     │    │  - Session│
        │  - Audit     │    └───────────┘
        └──────────────┘
```

### 2.2 Component Architecture

```python
# Directory Structure (Phase 3 additions)
backend_django/
├── config/
│   ├── settings/
│   │   ├── base.py        # Common settings
│   │   ├── development.py # Dev overrides
│   │   ├── staging.py     # Staging config
│   │   └── production.py  # Prod config
│   └── celery.py          # Celery configuration (new)
├── authentication/        # New Django app
│   ├── models.py         # User, Role, Permission
│   ├── services.py       # AuthService
│   ├── api.py            # Auth endpoints
│   ├── middleware.py     # JWT middleware
│   └── permissions.py    # RBAC checks
├── monitoring/           # New Django app
│   ├── middleware.py     # Metrics collection
│   ├── api.py           # Health/metrics endpoints
│   └── alerts.py        # Alert definitions
├── exports/             # New Django app
│   ├── tasks.py         # Celery tasks
│   ├── generators.py    # CSV/Excel/PDF
│   └── api.py          # Export endpoints
└── studies/            # Existing app
    ├── bulk_operations.py  # New bulk features
    └── api.py              # Extended endpoints
```

---

## 3. Security Architecture

### 3.1 Authentication System

#### 3.1.1 JWT Implementation

```python
# JWT Token Structure
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": "USR-001",
    "username": "admin@hospital.com",
    "roles": ["medical_admin"],
    "exp": 1699632000,  # 8 hours from issued
    "iat": 1699603200,  # Issued at
    "jti": "550e8400-e29b-41d4-a716"  # JWT ID for revocation
  },
  "signature": "HMACSHA256(...)"
}

# Token Configuration
JWT_CONFIG = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': settings.SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': 'medical-imaging-system',
}
```

#### 3.1.2 Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant DB as Database
    participant R as Redis

    U->>F: Enter credentials
    F->>B: POST /auth/login
    B->>DB: Validate credentials
    DB-->>B: User verified
    B->>B: Generate JWT tokens
    B->>R: Store refresh token
    B-->>F: Return tokens + user info
    F->>F: Store tokens (httpOnly cookie)

    Note over F,B: Subsequent requests
    F->>B: Request with Authorization header
    B->>B: Validate JWT signature
    B->>R: Check revocation list
    R-->>B: Token valid
    B->>B: Extract user context
    B->>DB: Execute request
    DB-->>B: Return data
    B-->>F: Response
```

### 3.2 Authorization System (RBAC)

#### 3.2.1 Role Definitions

```python
ROLE_DEFINITIONS = {
    'medical_admin': {
        'name': 'Medical Administrator',
        'permissions': [
            'studies:read', 'studies:write', 'studies:delete',
            'exports:create', 'exports:download',
            'bulk:update', 'bulk:assign',
            'users:read', 'users:write',
            'audit:read'
        ]
    },
    'radiologist': {
        'name': 'Radiologist',
        'permissions': [
            'studies:read', 'studies:write',
            'exports:create', 'exports:download',
            'bulk:assign'
        ]
    },
    'viewer': {
        'name': 'Read-Only Viewer',
        'permissions': [
            'studies:read',
            'exports:download'
        ]
    },
    'system_admin': {
        'name': 'System Administrator',
        'permissions': ['*']  # All permissions
    }
}
```

#### 3.2.2 Permission Check Implementation

```python
# Permission decorator (pragmatic approach)
def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.has_permission(permission):
                raise PermissionDenied(f"Missing permission: {permission}")
            return func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage in API endpoint
@router.post('/studies/bulk/update-status')
@require_permission('bulk:update')
def bulk_update_status(request, data: BulkUpdateRequest):
    # Implementation
    pass
```

### 3.3 API Security

#### 3.3.1 Rate Limiting

```python
RATE_LIMIT_CONFIG = {
    'DEFAULT': '1000/hour',  # Per user
    'AUTH_LOGIN': '5/minute',  # Prevent brute force
    'EXPORTS': '10/hour',  # Resource intensive
    'BULK_OPERATIONS': '100/hour',
    'ANONYMOUS': '100/hour'  # For public endpoints
}

# Implementation
from django_ratelimit.decorators import ratelimit

@ratelimit(key='user', rate='5/m', method='POST')
def login(request):
    # Login logic
    pass
```

#### 3.3.2 CORS Configuration

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Development
    "https://medical.hospital.com",  # Production
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
```

### 3.4 Audit Logging

```python
class AuditLogger:
    """Centralized audit logging service."""

    @staticmethod
    def log_action(
        user: User,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        request: Optional[HttpRequest] = None
    ):
        """Log user action for audit trail."""
        AuditLog.objects.create(
            user_id=user.user_id,
            username=user.username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            details=details or {}
        )

# Audit events to track
AUDIT_EVENTS = {
    'AUTH_LOGIN': 'User login',
    'AUTH_LOGOUT': 'User logout',
    'AUTH_FAILED': 'Failed login attempt',
    'STUDY_READ': 'View study details',
    'STUDY_UPDATE': 'Update study',
    'STUDY_DELETE': 'Delete study',
    'EXPORT_CREATE': 'Generate data export',
    'BULK_UPDATE': 'Bulk update records',
    'USER_CREATE': 'Create new user',
    'USER_UPDATE': 'Update user',
    'USER_DELETE': 'Delete user',
    'PERMISSION_CHANGE': 'Change user permissions'
}
```

---

## 4. Database Schema Changes

### 4.1 New Tables

```sql
-- User Management Tables
CREATE TABLE auth_user (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,  -- Django's PBKDF2 hash
    full_name VARCHAR(200) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_superuser BOOLEAN DEFAULT false,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_auth_user_username ON auth_user(username);
CREATE INDEX idx_auth_user_email ON auth_user(email);

-- Role Management
CREATE TABLE auth_role (
    role_id VARCHAR(50) PRIMARY KEY,
    role_name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Permissions
CREATE TABLE auth_permission (
    permission_id VARCHAR(50) PRIMARY KEY,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description TEXT,
    UNIQUE(resource, action)
);

-- User-Role Mapping
CREATE TABLE auth_user_role (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES auth_user(user_id) ON DELETE CASCADE,
    role_id VARCHAR(50) REFERENCES auth_role(role_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by VARCHAR(50),
    UNIQUE(user_id, role_id)
);

CREATE INDEX idx_user_role_user ON auth_user_role(user_id);
CREATE INDEX idx_user_role_role ON auth_user_role(role_id);

-- Role-Permission Mapping
CREATE TABLE auth_role_permission (
    id SERIAL PRIMARY KEY,
    role_id VARCHAR(50) REFERENCES auth_role(role_id) ON DELETE CASCADE,
    permission_id VARCHAR(50) REFERENCES auth_permission(permission_id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);

-- Audit Log Table
CREATE TABLE audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50),
    username VARCHAR(150),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(100),
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);

-- Export Jobs Table
CREATE TABLE export_job (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(50) NOT NULL,
    export_type VARCHAR(20) NOT NULL, -- 'csv', 'excel', 'pdf'
    status VARCHAR(20) NOT NULL, -- 'pending', 'processing', 'completed', 'failed'
    query_params JSONB NOT NULL,
    file_path TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_export_job_user ON export_job(user_id);
CREATE INDEX idx_export_job_status ON export_job(status);
CREATE INDEX idx_export_job_created ON export_job(created_at DESC);
```

### 4.2 Django Models

```python
# authentication/models.py
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
import uuid

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        if not email:
            raise ValueError('Email is required')

        email = self.normalize_email(email)
        user = self.model(
            username=username,
            email=email,
            user_id=f"USR-{uuid.uuid4().hex[:8].upper()}",
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    user_id = models.CharField(max_length=50, primary_key=True)
    username = models.CharField(max_length=150, unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name']

    class Meta:
        db_table = 'auth_user'

class Role(models.Model):
    role_id = models.CharField(max_length=50, primary_key=True)
    role_name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auth_role'

class Permission(models.Model):
    permission_id = models.CharField(max_length=50, primary_key=True)
    resource = models.CharField(max_length=100)
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'auth_permission'
        unique_together = ['resource', 'action']

class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.CharField(max_length=50, null=True)

    class Meta:
        db_table = 'auth_user_role'
        unique_together = ['user', 'role']

class AuditLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    user_id = models.CharField(max_length=50, db_index=True)
    username = models.CharField(max_length=150)
    action = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=100, null=True)
    resource_id = models.CharField(max_length=100, null=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['resource_type', 'resource_id']),
        ]
```

---

## 5. API Specifications

### 5.1 Authentication Endpoints

#### 5.1.1 Login
```yaml
POST /api/v1/auth/login
Content-Type: application/json

Request:
{
  "username": "admin@hospital.com",
  "password": "SecurePassword123!"
}

Response 200:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 28800,  # seconds (8 hours)
  "user": {
    "user_id": "USR-001",
    "username": "admin@hospital.com",
    "full_name": "John Doe",
    "email": "admin@hospital.com",
    "roles": ["medical_admin"]
  }
}

Response 401:
{
  "detail": "Invalid credentials"
}

Response 429:
{
  "detail": "Too many login attempts. Try again in 60 seconds."
}
```

#### 5.1.2 Refresh Token
```yaml
POST /api/v1/auth/refresh
Content-Type: application/json

Request:
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response 200:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 28800
}
```

#### 5.1.3 Logout
```yaml
POST /api/v1/auth/logout
Authorization: Bearer {access_token}

Response 200:
{
  "message": "Successfully logged out"
}
```

### 5.2 User Management Endpoints

#### 5.2.1 List Users
```yaml
GET /api/v1/users?page=1&page_size=20
Authorization: Bearer {access_token}
Required Permission: users:read

Response 200:
{
  "data": [
    {
      "user_id": "USR-001",
      "username": "admin@hospital.com",
      "full_name": "John Doe",
      "email": "admin@hospital.com",
      "is_active": true,
      "roles": ["medical_admin"],
      "created_at": "2025-01-01T10:00:00",
      "last_login": "2025-01-15T14:30:00"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20
}
```

#### 5.2.2 Create User
```yaml
POST /api/v1/users
Authorization: Bearer {access_token}
Required Permission: users:write
Content-Type: application/json

Request:
{
  "username": "doctor@hospital.com",
  "email": "doctor@hospital.com",
  "full_name": "Jane Smith",
  "password": "InitialPassword123!",
  "roles": ["radiologist"]
}

Response 201:
{
  "user_id": "USR-002",
  "username": "doctor@hospital.com",
  "full_name": "Jane Smith",
  "email": "doctor@hospital.com",
  "roles": ["radiologist"],
  "created_at": "2025-01-15T15:00:00"
}
```

### 5.3 Export Endpoints

#### 5.3.1 Create Export Job
```yaml
POST /api/v1/studies/export
Authorization: Bearer {access_token}
Required Permission: exports:create
Content-Type: application/json

Request:
{
  "format": "excel",  # csv, excel, pdf
  "filters": {
    "exam_status": "completed",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  },
  "columns": [
    "exam_id", "patient_name", "exam_status",
    "exam_source", "order_datetime"
  ]
}

Response 202:
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "estimated_time": 30,  # seconds
  "message": "Export job created. Check status for progress."
}
```

#### 5.3.2 Check Export Status
```yaml
GET /api/v1/exports/{job_id}/status
Authorization: Bearer {access_token}

Response 200 (Processing):
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45,  # percentage
  "message": "Processing 4500 of 10000 records"
}

Response 200 (Completed):
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "download_url": "/api/v1/exports/550e8400.../download",
  "file_size": 2048576,  # bytes
  "expires_at": "2025-01-16T15:00:00"
}
```

### 5.4 Bulk Operations Endpoints

#### 5.4.1 Bulk Update Status
```yaml
POST /api/v1/studies/bulk/update-status
Authorization: Bearer {access_token}
Required Permission: bulk:update
Content-Type: application/json

Request:
{
  "exam_ids": ["EXAM001", "EXAM002", "EXAM003"],
  "new_status": "completed",
  "reason": "Batch processing completed"
}

Response 200:
{
  "updated": 3,
  "failed": 0,
  "errors": []
}
```

#### 5.4.2 Bulk Assign Physician
```yaml
POST /api/v1/studies/bulk/assign-physician
Authorization: Bearer {access_token}
Required Permission: bulk:assign
Content-Type: application/json

Request:
{
  "exam_ids": ["EXAM001", "EXAM002"],
  "physician_name": "Dr. Jane Smith",
  "notify": true
}

Response 200:
{
  "assigned": 2,
  "failed": 0,
  "errors": []
}
```

### 5.5 Audit Log Endpoints

#### 5.5.1 Query Audit Logs
```yaml
GET /api/v1/audit-logs?
  user_id=USR-001&
  action=STUDY_UPDATE&
  start_date=2025-01-01&
  end_date=2025-01-31&
  page=1&page_size=50

Authorization: Bearer {access_token}
Required Permission: audit:read

Response 200:
{
  "data": [
    {
      "log_id": 12345,
      "user_id": "USR-001",
      "username": "admin@hospital.com",
      "action": "STUDY_UPDATE",
      "resource_type": "study",
      "resource_id": "EXAM001",
      "ip_address": "192.168.1.100",
      "timestamp": "2025-01-15T14:30:00",
      "details": {
        "field_changed": "exam_status",
        "old_value": "pending",
        "new_value": "completed"
      }
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 50
}
```

---

## 6. Performance Specifications

### 6.1 Response Time Requirements

| Endpoint Type | P50 | P95 | P99 |
|--------------|-----|-----|-----|
| Authentication | <100ms | <200ms | <500ms |
| Study Search | <200ms | <300ms | <500ms |
| Study Detail | <100ms | <150ms | <300ms |
| Export (Async) | <50ms | <100ms | <200ms |
| Bulk Operations | <500ms | <1s | <2s |
| Audit Logs | <300ms | <500ms | <1s |

### 6.2 Throughput Requirements

```yaml
Concurrent Users: 5-10 (normal), 20 (peak)
Requests/Second: 50 (average), 100 (peak)

Operation Throughput:
  Study Search: 100 req/min
  Authentication: 20 req/min
  Exports: 10 concurrent jobs
  Bulk Updates: 1000 records/min
```

### 6.3 Database Performance

```sql
-- New indexes for performance
CREATE INDEX idx_study_search_composite
ON medical_examinations_fact(exam_status, order_datetime DESC)
WHERE exam_status IN ('pending', 'completed');

CREATE INDEX idx_audit_log_user_time
ON audit_log(user_id, timestamp DESC);

-- Query optimization targets
-- All queries should execute in <100ms
EXPLAIN ANALYZE
SELECT * FROM medical_examinations_fact
WHERE exam_status = 'completed'
AND order_datetime >= '2025-01-01'
ORDER BY order_datetime DESC
LIMIT 20;
```

### 6.4 Cache Strategy

```python
CACHE_CONFIGURATION = {
    'filter_options': {
        'timeout': 300,  # 5 minutes
        'key': 'filters:options:v1'
    },
    'user_permissions': {
        'timeout': 600,  # 10 minutes
        'key': 'user:{user_id}:permissions'
    },
    'export_jobs': {
        'timeout': 3600,  # 1 hour
        'key': 'export:{job_id}'
    },
    'study_detail': {
        'timeout': 60,  # 1 minute
        'key': 'study:{exam_id}'
    }
}
```

---

## 7. Infrastructure Requirements

### 7.1 Server Specifications

```yaml
Production Environment:
  Application Server:
    CPU: 4 cores
    RAM: 8GB
    Storage: 100GB SSD
    Network: 1Gbps

  Database Server:
    CPU: 4 cores
    RAM: 16GB
    Storage: 500GB SSD (RAID 10)
    Backup: Daily snapshots

  Redis Server:
    RAM: 4GB
    Persistence: AOF enabled

Staging Environment:
  # 50% of production resources

Development Environment:
  # Local Docker containers
```

### 7.2 Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with UV
RUN uv sync --frozen

# Copy application code
COPY . .

# Run migrations and collect static
RUN uv run python manage.py migrate
RUN uv run python manage.py collectstatic --noinput

# Expose port
EXPOSE 8001

# Start application
CMD ["uv", "run", "gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8001", \
     "--workers", "4", \
     "--threads", "2", \
     "--worker-class", "gthread", \
     "--worker-tmp-dir", "/dev/shm", \
     "--log-level", "info"]
```

### 7.3 Nginx Configuration

```nginx
upstream django_backend {
    server 127.0.0.1:8001 fail_timeout=0;
}

server {
    listen 443 ssl http2;
    server_name medical.hospital.com;

    # SSL configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Static files
    location /static/ {
        alias /var/www/static/;
        expires 30d;
    }

    # Media files
    location /media/ {
        alias /var/www/media/;
        expires 7d;
    }

    # API proxy
    location /api/ {
        proxy_pass http://django_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

---

## 8. Testing Strategy

### 8.1 Test Coverage Requirements

```yaml
Overall Coverage Target: 90%

By Component:
  Models: 95%
  Services: 90%
  API Endpoints: 85%
  Middleware: 90%
  Utilities: 80%
```

### 8.2 Unit Tests

```python
# tests/test_authentication.py
import pytest
from django.test import TestCase
from authentication.models import User, Role
from authentication.services import AuthService

class TestAuthService(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='test@hospital.com',
            email='test@hospital.com',
            password='TestPass123!'
        )

    def test_jwt_token_generation(self):
        """Test JWT token generation and validation."""
        tokens = AuthService.generate_tokens(self.user)

        assert 'access_token' in tokens
        assert 'refresh_token' in tokens
        assert tokens['expires_in'] == 28800

        # Validate token
        payload = AuthService.validate_token(tokens['access_token'])
        assert payload['user_id'] == self.user.user_id

    def test_invalid_credentials(self):
        """Test login with invalid credentials."""
        with pytest.raises(AuthenticationError):
            AuthService.authenticate('wrong@email.com', 'wrong')

    def test_rate_limiting(self):
        """Test rate limiting on login attempts."""
        for i in range(5):
            AuthService.authenticate('test@hospital.com', 'wrong')

        # 6th attempt should be rate limited
        with pytest.raises(RateLimitError):
            AuthService.authenticate('test@hospital.com', 'wrong')
```

### 8.3 Integration Tests

```python
# tests/test_integration.py
import pytest
from django.test import Client
from django.urls import reverse

class TestAuthenticationFlow:
    @pytest.fixture
    def api_client(self):
        return Client()

    def test_complete_auth_flow(self, api_client):
        """Test complete authentication flow."""
        # 1. Login
        response = api_client.post(
            reverse('auth:login'),
            {'username': 'admin@hospital.com', 'password': 'Admin123!'},
            content_type='application/json'
        )
        assert response.status_code == 200
        tokens = response.json()

        # 2. Access protected endpoint
        response = api_client.get(
            reverse('studies:search'),
            HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}"
        )
        assert response.status_code == 200

        # 3. Refresh token
        response = api_client.post(
            reverse('auth:refresh'),
            {'refresh_token': tokens['refresh_token']},
            content_type='application/json'
        )
        assert response.status_code == 200

        # 4. Logout
        response = api_client.post(
            reverse('auth:logout'),
            HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}"
        )
        assert response.status_code == 200
```

### 8.4 Performance Tests

```python
# tests/test_performance.py
import time
import concurrent.futures
from django.test import TestCase

class TestPerformance(TestCase):
    def test_search_response_time(self):
        """Test search endpoint response time."""
        start = time.time()
        response = self.client.get('/api/v1/studies/search?q=test')
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.3  # 300ms requirement

    def test_concurrent_requests(self):
        """Test system under concurrent load."""
        def make_request():
            return self.client.get('/api/v1/studies/search')

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [f.result() for f in futures]

        # All requests should succeed
        assert all(r.status_code == 200 for r in results)
```

### 8.5 Security Tests

```python
# tests/test_security.py
import jwt
from django.test import TestCase

class TestSecurity(TestCase):
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention."""
        malicious_input = "'; DROP TABLE medical_examinations_fact; --"
        response = self.client.get(
            f'/api/v1/studies/search?q={malicious_input}'
        )
        # Should handle safely, not execute SQL
        assert response.status_code in [200, 400]
        # Table should still exist
        assert Study.objects.count() >= 0

    def test_jwt_tampering(self):
        """Test JWT token tampering detection."""
        valid_token = AuthService.generate_tokens(self.user)['access_token']

        # Tamper with payload
        decoded = jwt.decode(valid_token, options={"verify_signature": False})
        decoded['user_id'] = 'HACKER'
        tampered = jwt.encode(decoded, 'wrong_secret', algorithm='HS256')

        with pytest.raises(InvalidTokenError):
            AuthService.validate_token(tampered)
```

---

## 9. Deployment Strategy

### 9.1 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install UV
      run: pip install uv

    - name: Install dependencies
      run: uv sync

    - name: Run linting
      run: |
        uv run black --check .
        uv run ruff check .
        uv run mypy .

    - name: Run tests
      run: |
        uv run pytest tests/ --cov=. --cov-report=xml

    - name: Check coverage
      run: |
        coverage report --fail-under=85

    - name: Security scan
      run: |
        uv run bandit -r . -ll
        uv run safety check

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Build Docker image
      run: |
        docker build -t medical-imaging:${{ github.sha }} .

    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USER }} --password-stdin
        docker push medical-imaging:${{ github.sha }}

  deploy_staging:
    needs: build
    runs-on: ubuntu-latest

    steps:
    - name: Deploy to staging
      run: |
        ssh staging@staging.hospital.com << 'EOF'
          docker pull medical-imaging:${{ github.sha }}
          docker stop medical-app || true
          docker run -d --name medical-app \
            -e DATABASE_URL=${{ secrets.STAGING_DB_URL }} \
            -e REDIS_URL=${{ secrets.STAGING_REDIS_URL }} \
            -p 8001:8001 \
            medical-imaging:${{ github.sha }}
        EOF

    - name: Run smoke tests
      run: |
        sleep 30
        curl -f https://staging.hospital.com/api/v1/health || exit 1

  deploy_production:
    needs: deploy_staging
    runs-on: ubuntu-latest
    environment: production

    steps:
    - name: Deploy to production
      run: |
        # Blue-green deployment
        ssh prod@prod.hospital.com << 'EOF'
          docker pull medical-imaging:${{ github.sha }}
          docker run -d --name medical-app-new \
            -e DATABASE_URL=${{ secrets.PROD_DB_URL }} \
            -e REDIS_URL=${{ secrets.PROD_REDIS_URL }} \
            -p 8002:8001 \
            medical-imaging:${{ github.sha }}

          # Health check
          sleep 30
          curl -f http://localhost:8002/api/v1/health || exit 1

          # Switch traffic
          docker stop medical-app || true
          docker rename medical-app-new medical-app

          # Update nginx
          nginx -s reload
        EOF
```

### 9.2 Zero-Downtime Deployment

```bash
#!/bin/bash
# deploy.sh - Zero-downtime deployment script

set -e

echo "Starting zero-downtime deployment..."

# 1. Build new version
docker build -t medical-imaging:new .

# 2. Run migrations (backward compatible)
docker run --rm \
  -e DATABASE_URL=$DATABASE_URL \
  medical-imaging:new \
  python manage.py migrate

# 3. Start new container on different port
docker run -d \
  --name medical-app-new \
  -p 8002:8001 \
  medical-imaging:new

# 4. Health check
echo "Waiting for health check..."
for i in {1..30}; do
  if curl -f http://localhost:8002/api/v1/health; then
    echo "Health check passed"
    break
  fi
  sleep 2
done

# 5. Update load balancer
echo "Switching traffic..."
# Update nginx upstream to point to :8002

# 6. Graceful shutdown old container
docker stop --time=30 medical-app
docker rm medical-app

# 7. Rename new container
docker rename medical-app-new medical-app

echo "Deployment completed successfully"
```

---

## 10. Monitoring and Observability

### 10.1 Metrics Collection

```python
# monitoring/middleware.py
from django_prometheus import PrometheusMiddleware
from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

active_users = Gauge(
    'active_users_total',
    'Number of active users'
)

class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        # Record metrics
        duration = time.time() - start_time
        http_requests_total.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()

        http_request_duration.labels(
            method=request.method,
            endpoint=request.path
        ).observe(duration)

        return response
```

### 10.2 Logging Configuration

```python
# config/settings/production.py
import structlog

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': structlog.stdlib.ProcessorFormatter,
            'processor': structlog.processors.JSONRenderer(),
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/medical-imaging/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'studies': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Structlog configuration
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### 10.3 Alert Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: medical_imaging_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow response time detected"
          description: "P95 response time is {{ $value }} seconds"

      - alert: DatabaseConnectionPoolExhausted
        expr: django_db_connections_in_use / django_db_connections_limit > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool nearly exhausted"

      - alert: CacheHitRateLow
        expr: rate(cache_hits_total[5m]) / rate(cache_gets_total[5m]) < 0.7
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate below 70%"
```

### 10.4 Dashboard Configuration

```json
// grafana/dashboard.json
{
  "dashboard": {
    "title": "Medical Imaging System",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Response Time (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, http_request_duration_seconds)"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~'5..'}[5m])"
          }
        ]
      },
      {
        "title": "Active Users",
        "targets": [
          {
            "expr": "active_users_total"
          }
        ]
      },
      {
        "title": "Database Connections",
        "targets": [
          {
            "expr": "django_db_connections_in_use"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "rate(cache_hits_total[5m]) / rate(cache_gets_total[5m])"
          }
        ]
      }
    ]
  }
}
```

---

## 11. Migration Plan

### 11.1 Database Migration Strategy

```python
# migrations/0001_phase3_security.py
from django.db import migrations, models
import uuid

def create_default_roles(apps, schema_editor):
    """Create default roles and permissions."""
    Role = apps.get_model('authentication', 'Role')
    Permission = apps.get_model('authentication', 'Permission')
    RolePermission = apps.get_model('authentication', 'RolePermission')

    # Create permissions
    permissions = [
        ('studies', 'read', 'View medical studies'),
        ('studies', 'write', 'Create/update studies'),
        ('studies', 'delete', 'Delete studies'),
        ('exports', 'create', 'Create data exports'),
        ('exports', 'download', 'Download exports'),
        ('bulk', 'update', 'Bulk update records'),
        ('bulk', 'assign', 'Bulk assign physicians'),
        ('users', 'read', 'View users'),
        ('users', 'write', 'Create/update users'),
        ('audit', 'read', 'View audit logs'),
    ]

    for resource, action, desc in permissions:
        Permission.objects.create(
            permission_id=f"PERM-{uuid.uuid4().hex[:8].upper()}",
            resource=resource,
            action=action,
            description=desc
        )

    # Create roles
    roles = {
        'medical_admin': ['studies:*', 'exports:*', 'bulk:*', 'users:*', 'audit:read'],
        'radiologist': ['studies:read', 'studies:write', 'exports:*', 'bulk:assign'],
        'viewer': ['studies:read', 'exports:download'],
    }

    for role_name, perms in roles.items():
        role = Role.objects.create(
            role_id=f"ROLE-{uuid.uuid4().hex[:8].upper()}",
            role_name=role_name,
            description=f"{role_name.replace('_', ' ').title()} role"
        )

        # Assign permissions
        for perm_pattern in perms:
            if ':*' in perm_pattern:
                resource = perm_pattern.split(':')[0]
                permissions = Permission.objects.filter(resource=resource)
            else:
                resource, action = perm_pattern.split(':')
                permissions = Permission.objects.filter(
                    resource=resource,
                    action=action
                )

            for permission in permissions:
                RolePermission.objects.create(
                    role=role,
                    permission=permission
                )

class Migration(migrations.Migration):
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('user_id', models.CharField(max_length=50, primary_key=True)),
                ('username', models.CharField(max_length=150, unique=True)),
                ('email', models.EmailField(unique=True)),
                ('password', models.CharField(max_length=128)),
                ('full_name', models.CharField(max_length=200)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'auth_user'},
        ),
        # ... other model creations ...
        migrations.RunPython(create_default_roles),
    ]
```

### 11.2 Feature Flag Implementation

```python
# config/feature_flags.py
import os
from typing import Dict, Any

class FeatureFlags:
    """Centralized feature flag management."""

    FLAGS = {
        'AUTHENTICATION_ENABLED': {
            'default': False,
            'env_var': 'FF_AUTH_ENABLED',
            'description': 'Enable JWT authentication'
        },
        'RBAC_ENABLED': {
            'default': False,
            'env_var': 'FF_RBAC_ENABLED',
            'description': 'Enable role-based access control'
        },
        'AUDIT_LOGGING_ENABLED': {
            'default': True,
            'env_var': 'FF_AUDIT_ENABLED',
            'description': 'Enable audit logging'
        },
        'EXPORT_ENABLED': {
            'default': False,
            'env_var': 'FF_EXPORT_ENABLED',
            'description': 'Enable data export functionality'
        },
        'MONITORING_ENABLED': {
            'default': True,
            'env_var': 'FF_MONITORING_ENABLED',
            'description': 'Enable Prometheus metrics'
        },
    }

    @classmethod
    def is_enabled(cls, flag_name: str) -> bool:
        """Check if a feature flag is enabled."""
        if flag_name not in cls.FLAGS:
            return False

        flag_config = cls.FLAGS[flag_name]
        env_value = os.getenv(flag_config['env_var'], '').lower()

        if env_value in ['true', '1', 'yes', 'on']:
            return True
        elif env_value in ['false', '0', 'no', 'off']:
            return False
        else:
            return flag_config['default']

    @classmethod
    def get_all_flags(cls) -> Dict[str, bool]:
        """Get status of all feature flags."""
        return {
            flag_name: cls.is_enabled(flag_name)
            for flag_name in cls.FLAGS
        }

# Usage in middleware
class AuthenticationMiddleware:
    def __call__(self, request):
        if FeatureFlags.is_enabled('AUTHENTICATION_ENABLED'):
            # Perform authentication
            pass
        else:
            # Skip authentication (backward compatible)
            request.user = AnonymousUser()

        return self.get_response(request)
```

### 11.3 Rollback Plan

```bash
#!/bin/bash
# rollback.sh - Emergency rollback script

set -e

echo "Starting emergency rollback..."

# 1. Check current version
CURRENT_VERSION=$(docker inspect medical-app --format='{{.Config.Image}}')
echo "Current version: $CURRENT_VERSION"

# 2. Get previous version from backup
PREVIOUS_VERSION=$(cat /var/backup/last_known_good_version.txt)
echo "Rolling back to: $PREVIOUS_VERSION"

# 3. Pull previous version
docker pull $PREVIOUS_VERSION

# 4. Stop current container
docker stop medical-app

# 5. Start previous version
docker run -d \
  --name medical-app-rollback \
  -e DATABASE_URL=$DATABASE_URL \
  -e REDIS_URL=$REDIS_URL \
  -p 8001:8001 \
  $PREVIOUS_VERSION

# 6. Health check
for i in {1..30}; do
  if curl -f http://localhost:8001/api/v1/health; then
    echo "Rollback successful"
    break
  fi
  sleep 2
done

# 7. Clean up failed version
docker rm medical-app
docker rename medical-app-rollback medical-app

# 8. Alert team
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Emergency rollback completed to version '$PREVIOUS_VERSION'"}'

echo "Rollback completed"
```

---

## 12. Technical Constraints

### 12.1 System Constraints

```yaml
Performance Constraints:
  - Maximum 5 concurrent users (normal operation)
  - Peak load: 20 concurrent users
  - Database connections: Max 50
  - Memory usage: <4GB per container
  - CPU usage: <80% sustained

Security Constraints:
  - HIPAA compliance required
  - GDPR compliance for EU patients
  - TLS 1.2 minimum
  - Password complexity: 8+ chars, mixed case, number, special
  - Session timeout: 8 hours
  - Failed login lockout: 5 attempts

Operational Constraints:
  - Deployment window: 2-4 AM UTC
  - Maximum downtime: 5 minutes/month
  - Backup retention: 30 days
  - Log retention: 90 days
  - Export file retention: 24 hours
```

### 12.2 Technology Constraints

```yaml
Framework Constraints:
  - Django 5.0 (latest stable version)
  - Python 3.11+ (no 3.12 yet - library compatibility)
  - PostgreSQL 15.x (no major version upgrades)
  - Redis 7.x (stable version)

Package Management:
  - UV package manager ONLY (no pip)
  - Lock file mandatory (uv.lock)
  - No direct GitHub dependencies
  - Security updates within 48 hours

Development Constraints:
  - No Django admin interface (security)
  - No signals (explicit service calls)
  - No complex ORM queries (use raw SQL if needed)
  - No monkey patching
  - Type hints mandatory for new code
```

### 12.3 Integration Constraints

```yaml
External Systems:
  - No direct database access from outside
  - API-only communication
  - Rate limiting on all endpoints
  - Webhook retry logic required

Data Constraints:
  - PHI data cannot leave database unencrypted
  - No patient names in logs
  - Export files must be temporary
  - Audit logs immutable

Browser Support:
  - Chrome 90+
  - Firefox 88+
  - Safari 14+
  - Edge 90+
  - No IE11 support
```

---

## 13. Appendices

### Appendix A: API Error Codes

| Code | Name | Description |
|------|------|-------------|
| 1001 | INVALID_CREDENTIALS | Username or password incorrect |
| 1002 | TOKEN_EXPIRED | JWT token has expired |
| 1003 | TOKEN_INVALID | JWT signature verification failed |
| 1004 | PERMISSION_DENIED | User lacks required permission |
| 1005 | RATE_LIMITED | Too many requests |
| 2001 | STUDY_NOT_FOUND | Study with given ID not found |
| 2002 | EXPORT_FAILED | Export generation failed |
| 2003 | BULK_OPERATION_FAILED | Some records failed to update |
| 3001 | DATABASE_ERROR | Database operation failed |
| 3002 | CACHE_ERROR | Cache operation failed |

### Appendix B: Environment Variables

```bash
# .env.production
# Database
DATABASE_URL=postgresql://user:pass@localhost/medical_imaging
DB_POOL_SIZE=50

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
JWT_SIGNING_KEY=your-jwt-key-here
ALLOWED_HOSTS=medical.hospital.com
CORS_ALLOWED_ORIGINS=https://medical.hospital.com

# Feature Flags
FF_AUTH_ENABLED=true
FF_RBAC_ENABLED=true
FF_AUDIT_ENABLED=true
FF_EXPORT_ENABLED=true
FF_MONITORING_ENABLED=true

# Monitoring
NEW_RELIC_LICENSE_KEY=your-key-here
SENTRY_DSN=https://key@sentry.io/project

# AWS (optional)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_S3_BUCKET=medical-exports

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=notifications@hospital.com
EMAIL_HOST_PASSWORD=your-password
```

### Appendix C: Monitoring Queries

```sql
-- Slow query analysis
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
WHERE mean_time > 100  -- queries taking >100ms
ORDER BY mean_time DESC
LIMIT 20;

-- Table size monitoring
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Connection monitoring
SELECT
    datname,
    count(*) as connections,
    count(*) FILTER (WHERE state = 'active') as active,
    count(*) FILTER (WHERE state = 'idle') as idle,
    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
FROM pg_stat_activity
GROUP BY datname;

-- Audit log analysis
SELECT
    action,
    COUNT(*) as count,
    COUNT(DISTINCT user_id) as unique_users
FROM audit_log
WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY action
ORDER BY count DESC;
```

### Appendix D: Dependency Versions

```toml
# pyproject.toml
[project]
name = "medical-imaging-system"
version = "1.2.0"
requires-python = ">=3.11"

dependencies = [
    # Core
    "django==5.0.0",
    "django-ninja==1.3.0",
    "psycopg2-binary==2.9.9",
    "python-decouple==3.8",

    # Authentication & Security
    "pyjwt==2.8.0",
    "django-cors-headers==4.3.1",
    "django-ratelimit==4.1.0",
    "cryptography==41.0.7",

    # Caching & Queue
    "redis==5.0.1",
    "django-redis==5.4.0",
    "celery==5.3.4",

    # Monitoring
    "django-prometheus==2.3.1",
    "structlog==23.2.0",

    # Export
    "pandas==2.1.4",
    "openpyxl==3.1.2",
    "reportlab==4.0.8",

    # Development
    "pytest==7.4.3",
    "pytest-django==4.7.0",
    "pytest-cov==4.1.0",
    "black==23.12.0",
    "ruff==0.1.8",
    "mypy==1.7.1",
    "django-debug-toolbar==4.2.0",
]

[tool.uv]
dev-dependencies = [
    "ipython==8.18.1",
    "django-extensions==3.2.3",
    "factory-boy==3.3.0",
    "faker==20.1.0",
]
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-11-10 | Engineering Team | Initial technical requirements for Phase 3 |

## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Technical Lead | _________ | _________ | _____ |
| Security Officer | _________ | _________ | _____ |
| DevOps Lead | _________ | _________ | _____ |
| Product Manager | _________ | _________ | _____ |

---

**END OF DOCUMENT**

Total Technical Specifications: 150+ requirements
Estimated Development Effort: 17 weeks
Technical Complexity: Medium-High
Risk Level: Moderate (mitigated through phased approach)