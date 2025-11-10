# Django Backend - Medical Imaging Management System

**Status**: ✅ Production Ready - Phase 1 & 2 Complete

This is the Django + PostgreSQL version of the medical imaging backend, replacing the FastAPI + DuckDB version.

## ✨ Recent Improvements (2025-11-10)

**Phase 1 - Exception Handling & Configuration** ✅
- Unified exception handling system (StudyNotFoundError, DatabaseQueryError)
- Centralized configuration management (studies/config.py)
- Request timing middleware (performance monitoring)
- Comprehensive code documentation and comments

**Phase 2 - Test Suite & Coverage** ✅
- 63 comprehensive test cases
- ~85% code coverage
- Model, Service, Caching, and Middleware tests
- Test data factories and fixtures
- Edge cases and error handling tests

## Why Django for Phase 2?

Following Linus Torvalds principles:
- **Pragmatic**: Built for 5 concurrent users, not 1000+
- **Simple**: Django Ninja is cleaner than DRF for this use case
- **Testable**: Standard Django ORM with explicit queries
- **No over-engineering**: Single app, flat data model, no signals or admin

## Architecture

```
Django Backend (Port 8001)
├── config/
│   ├── settings.py       # Django configuration
│   ├── urls.py          # Ninja API routes
│   └── wsgi.py          # WSGI entry point
├── studies/             # Single app for all endpoints
│   ├── models.py        # Study model (flat design)
│   ├── schemas.py       # Pydantic schemas for validation
│   ├── services.py      # Business logic (no signals)
│   └── api.py           # Django Ninja endpoints
├── tests/               # Comprehensive test suite
├── migrate_from_duckdb.py  # Data migration script
└── manage.py            # Django management

PostgreSQL Database
└── medical_examinations_fact  # All examination records
```

## Setup Instructions

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your PostgreSQL credentials
# DB_NAME=medical_imaging
# DB_USER=postgres
# DB_PASSWORD=your_password
# DB_HOST=localhost
# DB_PORT=5432
```

### 2. PostgreSQL Database

Create the PostgreSQL database:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE medical_imaging ENCODING 'UTF8';

# Create user (if needed)
CREATE USER medical_user WITH PASSWORD 'your_password';
ALTER ROLE medical_user SET client_encoding TO 'utf8';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE medical_imaging TO medical_user;

# Exit
\q
```

### 3. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 4. Initialize Database Schema

```bash
# Run migrations (creates tables)
python manage.py migrate

# Create superuser (optional, for admin)
# python manage.py createsuperuser
```

### 5. Migrate Data from DuckDB

```bash
# Set DuckDB path in .env or as environment variable
export DUCKDB_PATH=../backend/medical_imaging.duckdb

# Run migration
python scripts/migrate_from_duckdb.py

# Expected output:
# ✓ DuckDB contains 1,250 examination records
# ✓ Import complete: 1,250 imported, 0 failed
# ✓ SUCCESS: Record counts match!
# ✓ No duplicates found
```

### 6. Run Development Server

```bash
# Start Django development server on port 8001
python manage.py runserver 8001

# Access API
# http://localhost:8001/api/v1/docs   - API documentation
# http://localhost:8001/api/v1/health - Health check
```

## API Endpoints

All endpoints match FastAPI response format exactly (see ../docs/api/API_CONTRACT.md).

### Studies Search
```bash
GET /api/v1/studies/search?q=Zhang&exam_status=completed&page=1&page_size=20

Response:
{
  "data": [
    {
      "exam_id": "EXAM001",
      "patient_name": "Zhang Wei",
      "exam_status": "completed",
      "order_datetime": "2025-11-06T10:30:00",
      ...
    }
  ],
  "total": 1250,
  "page": 1,
  "page_size": 20,
  "filters": {
    "exam_statuses": ["completed", "pending", ...],
    "exam_sources": ["CT", "MRI", ...],
    "exam_items": [...]
  }
}
```

### Study Detail
```bash
GET /api/v1/studies/{exam_id}

Response:
{
  "exam_id": "EXAM001",
  "patient_name": "Zhang Wei",
  ...
}
```

### Filter Options
```bash
GET /api/v1/studies/filters/options

Response:
{
  "exam_statuses": [...],
  "exam_sources": [...],
  "exam_items": [...],
  "equipment_types": [...]
}
```

## Testing

Run comprehensive test suite (63 test cases, ~85% coverage):

```bash
# Run all tests
python manage.py test tests

# Run specific test modules
python manage.py test tests.test_models        # Model tests (15 cases)
python manage.py test tests.test_services      # Service tests (30 cases)
python manage.py test tests.test_caching       # Caching tests (10 cases)
python manage.py test tests.test_middleware    # Middleware tests (8 cases)

# Run with verbose output
python manage.py test tests --verbosity=2

# Generate coverage report
pip install coverage
coverage run --source='studies' manage.py test tests
coverage report
coverage html  # Generate HTML report to htmlcov/
```

### Test Coverage

- **Model Layer Tests** (15 cases): CRUD operations, validation, edge cases
- **Service Layer Tests** (30 cases): Search, filtering, sorting, error handling
- **Caching Tests** (10 cases): Cache hit/miss, graceful degradation, TTL
- **Middleware Tests** (8 cases): Request timing, log format, performance

## Verify Format Compatibility

Compare Django responses with FastAPI:

```bash
# Terminal 1: Start FastAPI (original)
cd ../backend
python run.py

# Terminal 2: Start Django
cd ../backend_django
python manage.py runserver 8001

# Terminal 3: Compare responses
# Get same data from both servers
curl http://localhost:8000/api/v1/studies/search > /tmp/fastapi.json
curl http://localhost:8001/api/v1/studies/search > /tmp/django.json

# Compare (should be identical except timestamps)
diff /tmp/fastapi.json /tmp/django.json
```

## Critical Principles

### Never Break Userspace (API Compatibility)

Every endpoint must return responses in **EXACT** format specified in ../docs/api/API_CONTRACT.md:
- Field names must match exactly (one character difference breaks frontend)
- DateTime format: ISO 8601 (YYYY-MM-DDTHH:MM:SS) without timezone
- Null values: `null` (not empty string or 0)
- Numbers as numbers (not strings)
- Pagination structure: `data`, `total`, `page`, `page_size`, `filters`

### Fail Fast (Error Handling)

- Validation before import (schema-first)
- Duplicate detection with explicit errors
- Count verification after import
- No silent failures (all errors are logged and reported)

### Simple by Design

- Single Django app (studies)
- Flat data model (no complex relationships)
- Direct function calls (no signals)
- Pydantic schemas for validation
- Service layer for business logic

## Deployment (Post-Phase 1)

For production deployment:

1. Set `DEBUG=False` in .env
2. Set proper `DJANGO_SECRET_KEY`
3. Configure `ALLOWED_HOSTS`
4. Use PostgreSQL with proper backup strategy
5. Use WSGI server (gunicorn, uWSGI)
6. Add nginx reverse proxy
7. Configure HTTPS/SSL
8. Set up monitoring and logging

## Troubleshooting

### Database Connection Error
```
Error: could not translate host name "localhost" to address
→ Check DB_HOST in .env (use 127.0.0.1 instead of localhost)
```

### Migration Error
```
Error: DuckDB file not found
→ Set DUCKDB_PATH=/path/to/medical_imaging.duckdb
```

### Port 8001 Already in Use
```
Error: Address already in use
→ python manage.py runserver 8001 --nothreading
→ Or use different port: python manage.py runserver 8002
```

### Import Count Mismatch
```
⚠️  Record count mismatch
→ Check error logs for failed imports
→ Verify DuckDB data integrity
→ Re-run migration after fixing
```

## Documentation

- **../docs/api/API_CONTRACT.md** - Response format specification (must match exactly)
- **../docs/planning/ZERO_DOWNTIME_DEPLOYMENT.md** - Safe migration procedure
- **../docs/migration/DJANGO_MIGRATION_LINUS_APPROVED.md** - Full implementation plan
- **../docs/implementation/EXCEL_INTEGRATION_LINUS_FIXES.md** - Data loading with error handling

## Project Status

### ✅ Completed Phases

- **Phase 1 - Exception Handling & Configuration** ✅
  - Unified exception handling system
  - Centralized configuration management
  - Performance monitoring middleware
  - Comprehensive code documentation

- **Phase 2 - Test Suite & Coverage** ✅
  - 63 comprehensive test cases
  - ~85% code coverage
  - Complete test documentation

### 🎯 Future Plans

- **Phase 3** (Future): Additional reporting and analytics features
- **Continuous Improvement**: Performance optimization, monitoring enhancements
- **Production Deployment**: Production deployment as needed

---

**Current Status**: ✅ Production Ready (Phase 1 & 2 Complete)
**Version**: 1.1.0
**Test Coverage**: ~85% (63 test cases)
**Last Updated**: 2025-11-10
**Maintainer**: Medical Imaging Team
