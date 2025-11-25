# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Medical Imaging Management System - Django Backend**

A pragmatic Django + PostgreSQL backend providing REST APIs for medical imaging examination and report management. Built with Django Ninja (FastAPI-style framework) for clean, type-safe APIs.

**Key Characteristics**:
- Single-app architecture (`studies`) for simplicity
- Flat database design (minimal normalization) focused on practicality
- Service layer pattern separating business logic from API/ORM
- Custom exception hierarchy for domain-specific error handling
- Comprehensive pagination system with page/page_size model (v1.1.0)

## Development Commands

### Running the Application
```bash
# Start development server (port 8001)
python manage.py runserver 8001

# Run all tests
python manage.py test

# Run specific test file
python manage.py test tests.test_pagination

# Run specific test class
python manage.py test tests.test_api_contract.ApiContractTestCase

# Run specific test method
python manage.py test tests.test_models.StudyModelTestCase.test_exam_id_unique
```

### Database Operations
```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration SQL without applying
python manage.py sqlmigrate studies 0001

# Rollback specific migration
python manage.py migrate studies 0006
```

### Development Workflow
```bash
# Refresh context for Cursor IDE (syncs _tasks, docs, claudedocs)
make refresh-context

# Check for issues
python manage.py check

# Create superuser for admin access
python manage.py createsuperuser

# Collect static files (required for admin)
python manage.py collectstatic
```

## Architecture

### Three-Layer Pattern

```
┌─────────────────────────────────────┐
│   API Layer (*_api.py)              │  ← Django Ninja endpoints, request/response handling
├─────────────────────────────────────┤
│   Service Layer (*_service.py)      │  ← Business logic, transaction management
├─────────────────────────────────────┤
│   Data Layer (models.py)            │  ← Django ORM models, database schema
└─────────────────────────────────────┘
```

**Responsibilities**:
- **API Layer**: HTTP handling, Pydantic schemas, input validation, error formatting
- **Service Layer**: Business rules, complex queries, cross-model operations, caching
- **Data Layer**: Database schema, constraints, model-level validation

### Core Modules

**studies/models.py**:
- `Study` - Medical examination records (main entity, uses `exam_id` as business key)
- `Report` - Diagnostic reports linked to studies
- `ReportVersion` - Version history for reports
- `ExportTask` - Async export job tracking
- `Project` - Project management for grouping studies
- `ProjectMember` - User roles in projects (Owner/Admin/Editor/Viewer)
- `StudyProjectAssignment` - Many-to-many relationship between studies and projects

**studies/services.py**: `StudyService` - Core business logic for study operations

**studies/report_service.py**: `ReportService` - Report management and search operations

**studies/project_service.py**: `ProjectService` - Project and member management with permission checks

**studies/pagination.py**:
- `StudyPagination` - Page/page_size pagination for studies
- `ProjectPagination` - Page/page_size pagination for projects

**studies/exceptions.py**: Domain-specific exception hierarchy
- `StudyServiceError` (base) → `StudyNotFoundError`, `InvalidSearchParameterError`, `BulkImportError`, etc.

### API Routing Structure

All endpoints under `/api/v1/` prefix (defined in `config/urls.py`):

```python
api.add_router('/studies', studies_router)     # Study/examination endpoints
api.add_router('/reports', report_router)      # Report search and management
api.add_router('', project_router)             # Project management (22 endpoints)
```

**Interactive API Docs**: http://localhost:8001/api/v1/docs

### Pagination System (v1.1.0)

**Current Model**: `page` and `page_size` parameters (1-indexed pages)

```python
# Request
GET /api/v1/reports/search/paginated?q=covid&page=2&page_size=50

# Response
{
  "items": [...],      # Array of results
  "total": 1234,       # Total matching items
  "page": 2,           # Current page (1-indexed)
  "page_size": 50,     # Items per page (auto-clamped to max 100)
  "pages": 25          # Total pages (ceil(total / page_size))
}
```

**Implementation**: Use `pagination.py` classes for consistent pagination across all endpoints.

**Legacy**: `/reports/search` endpoint uses deprecated limit/offset model (removal planned in v2.0.0).

## Testing Strategy

**Location**: `tests/` directory (not within app package)

**Test Files**:
- `test_models.py` - Model validation, constraints, relationships
- `test_services.py` - Service layer business logic
- `test_api_contract.py` - API endpoint contracts, HTTP responses
- `test_pagination.py` - Pagination logic (unit + integration)
- `test_caching.py` - Cache layer behavior
- `test_export.py` - Export functionality
- `test_project_api.py` - Project API endpoints
- `test_project_service.py` - Project service layer

**Coverage Target**: ≥80% for core logic, 100% for API contracts

**Run Pattern**:
```bash
# All tests
python manage.py test

# Specific module
python manage.py test tests.test_pagination

# Watch for model changes before testing
python manage.py makemigrations --check --dry-run
```

## Error Handling Philosophy

**Use Domain-Specific Exceptions**: Import from `studies.exceptions`, not generic Django exceptions.

```python
# ✅ Good
from studies.exceptions import StudyNotFoundError
raise StudyNotFoundError(exam_id)

# ❌ Avoid
raise Http404(f"Study {exam_id} not found")
```

**Service Layer**: Raise domain exceptions, let API layer translate to HTTP responses.

**API Layer**: Catch domain exceptions, return appropriate HTTP status codes with structured error bodies.

## Database Schema Key Points

**Primary Keys**:
- All models use Django's auto-incrementing `id` (BigAutoField)
- Business keys use unique fields (`exam_id` for Study, `report_id` for Report)

**Critical Indexes**:
- `Study.exam_id` - Unique index, used for all lookups
- `Report.report_id` - Unique index for report identification
- `StudyProjectAssignment` - Composite unique constraint on (study_id, project_id)

**Foreign Key Patterns**:
- Use `to_field='exam_id'` when referencing Study by business key
- Projects use standard Django `id` references

**Migrations**: Numbered sequentially (0001, 0002, etc.), never edit committed migrations.

## Current Project Status (2025-11-14)

**Active Branch**: `feature/bulk-search-export`

**Recently Completed**:
- ✅ Phase 5: Pagination unification (v1.1.0)
- ✅ Projects feature: 22 API endpoints with 4-role permissions
- ✅ Comprehensive test suite (43 tests)
- ✅ Authentication: JWT login/logout/verify

**Known Gaps** (from spec analysis 2025-11-14):
- ❌ AI Analysis features: 0% implemented (frontend ready, backend missing)
- ❌ Data Import API: 0% implemented (management commands exist only)
- ❌ Async task queue: Celery not configured
- ❌ Ollama integration: Not implemented

**Framework Note**:
- PRD originally specified FastAPI + SQLAlchemy
- **Actual implementation**: Django 4.2 + Django Ninja + Django ORM
- Decision rationale: See `docs/migration/101_DJANGO_MIGRATION_LINUS_APPROVED.md`
- Functionality equivalent, architecture differs

**Implementation Status**:
- ✅ FS-AUTH-001: Authentication (100%)
- ✅ FS-SEARCH-001: Advanced search (120% - exceeds spec)
- ✅ FS-PROJECT-001: Project management (120% - exceeds spec)
- ✅ FS-EXPORT-001: Export CSV/Excel (100%)
- ❌ FS-AI-001: Ollama AI service (0%)
- ❌ FS-AI-002: AI Analysis API (0%)
- ❌ FS-IMPORT-001: Import API (0%)

**Next Priority**: Implement AI analysis backend (3 weeks estimated) to match frontend capabilities.

## Important Files and Documentation

**API Documentation**:
- `API_DOCUMENTATION.md` - Complete OpenAPI-style API reference
- `CLIENT_MIGRATION_GUIDE.md` - Guide for pagination model migration
- `/api/v1/docs` - Interactive API documentation (Swagger UI)

**Planning Documents** (read before major changes):
- `_tasks/2025-11-12-projects-route-specification/` - Complete Projects feature spec
- `.cursor/rules/project-status.mdc` - Current project status and priorities
- `docs/migration/101_DJANGO_MIGRATION_LINUS_APPROVED.md` - FastAPI → Django migration rationale

**Configuration**:
- `config/settings.py` - Django settings, database, cache, CORS
- `config/urls.py` - URL routing, API versioning
- `.env` - Environment variables (not in repo, see `.env.example`)

## Code Style Guidelines

**Imports**: Group by stdlib → third-party → Django → local, alphabetized within groups

**Type Hints**: Use Pydantic schemas for API contracts, type hints for service layer methods

**Docstrings**: Google-style docstrings for services and complex functions

**Naming Conventions**:
- Models: PascalCase (e.g., `StudyProjectAssignment`)
- Functions/methods: snake_case (e.g., `get_study_detail`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_PAGE_SIZE`)
- Private methods: prefix with `_` (e.g., `_validate_filters`)

**Django Conventions**:
- Use `objects.get()` for single records (catches DoesNotExist)
- Use `objects.filter()` for querysets, add `.exists()` for boolean checks
- Prefer `select_related()` for foreign keys, `prefetch_related()` for many-to-many
- Use transactions (`@transaction.atomic`) for multi-model operations

## Common Patterns

### Adding a New API Endpoint

1. **Define Pydantic schemas** in `studies/schemas.py` or module-specific file
2. **Add service method** in appropriate `*_service.py` for business logic
3. **Create API endpoint** in `*_api.py` using `@router.get/post/put/delete`
4. **Add tests** in `tests/test_*_api.py` and `tests/test_*_service.py`
5. **Update documentation** in API_DOCUMENTATION.md if public-facing

### Adding a Database Model

1. **Define model** in `studies/models.py` with proper indexes and constraints
2. **Create migration**: `python manage.py makemigrations`
3. **Review migration SQL**: `python manage.py sqlmigrate studies XXXX`
4. **Apply migration**: `python manage.py migrate`
5. **Add model tests** in `tests/test_models.py`
6. **Update service layer** to include new model operations

### Handling New Exception Types

1. **Define exception class** in `studies/exceptions.py` inheriting from `StudyServiceError`
2. **Add error code** to `ERROR_CODES` dict
3. **Update API layer** to catch and translate to HTTP response
4. **Add test cases** for exception raising and handling

## Performance Considerations

**Caching**:
- Development: Local memory cache (django.core.cache.backends.locmem)
- Production: Redis cache (configured via CACHE_BACKEND env var)
- Cache keys should include version prefix for invalidation

**Query Optimization**:
- Always use `select_related()` for foreign key traversal
- Use `prefetch_related()` for reverse foreign keys and M2M
- Add database indexes for frequently filtered fields
- Avoid N+1 queries (check with Django Debug Toolbar)

**Pagination**:
- Default page_size: 20 items
- Maximum page_size: 100 items (auto-clamped)
- Use indexed columns for ordering to avoid full table scans

## Security Notes

- **CORS**: Configured for localhost:3000 and localhost:5173 (frontend dev servers)
- **Authentication**: Currently disabled in development; production requires implementation
- **SQL Injection**: Prevented by Django ORM; never use raw SQL without parameterization
- **Input Validation**: Always validate via Pydantic schemas at API boundary
