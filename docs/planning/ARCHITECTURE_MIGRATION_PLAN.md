# Architecture Migration Plan: FastAPI → Django + Django Ninja

**Status**: 🔄 PLANNED - Architecture redesign in progress
**User Requirement**: "後端改用django 與 django ninja 生態，先改變計畫內容，更新文件"
**Translation**: "Backend should use Django and Django Ninja ecosystem, first change the plan content, update documentation"

## Executive Summary

Migration from FastAPI/DuckDB microservices architecture to Django/Django Ninja ecosystem with integrated data management. This document outlines the strategic plan, technical changes, and implementation timeline.

## Current Architecture (Existing)

```
FastAPI Application
├── API Routes (study_routes, report_routes, analysis_routes, auth_routes)
├── Services (StudyService, ReportService, AnalysisService, AuthService)
├── Database Manager (DuckDB with singleton pattern)
├── Schemas (Pydantic-based validation)
└── Utils (ExcelDataLoader for Excel integration)

Frontend
├── React Components (pages, hooks, services)
├── API Clients (service layer with axios)
└── State Management (Zustand for auth, React Query for data)
```

## Target Architecture (Django Ninja)

```
Django Project
├── Django Apps (studies, reports, analysis, auth)
│   ├── Models (ORM-based data definition)
│   ├── Views (Function-based or class-based)
│   ├── Serializers (DRF serializers for validation/transformation)
│   ├── Managers & Querysets (Custom query logic)
│   └── Signals (Event handlers for business logic)
├── Django Ninja (Type-safe API layer)
│   ├── API Routes (Type-annotated endpoints)
│   ├── Schema (Pydantic integration for DRF compat)
│   └── Authentication (Django auth system)
├── Management Commands (Data loading, migrations, utilities)
├── Middleware (CORS, logging, error handling)
├── Settings & Configuration (Environment-based)
└── Database (PostgreSQL/SQLite with Django ORM)

Frontend (Unchanged)
├── React Components
├── API Clients (updated endpoints only)
└── State Management
```

## Rationale for Migration

### Advantages of Django Ninja

| Aspect | FastAPI | Django Ninja | Winner |
|--------|---------|--------------|--------|
| **Type Safety** | Pydantic | Pydantic + DRF | 🟰 Tie |
| **ORM Support** | SQLAlchemy (manual) | Django ORM (built-in) | ✅ Django |
| **Admin Interface** | None (manual) | Django Admin (built-in) | ✅ Django |
| **Authentication** | Custom or external | Django Auth (built-in) | ✅ Django |
| **Database Migrations** | Alembic (manual) | Django Migrations (auto) | ✅ Django |
| **Django Integration** | None | Native | ✅ Django |
| **Ecosystem** | Smaller | Larger, mature | ✅ Django |
| **Learning Curve** | Moderate | Moderate-High | ⚠️ FastAPI |
| **Performance** | High | High | 🟰 Tie |
| **Development Speed** | Fast | Very fast (scaffolding) | ✅ Django |

### Business Case

- **Scalability**: Django ecosystem maturity for enterprise features
- **Maintenance**: ORM and migrations reduce technical debt
- **Team Familiarity**: Django skills more common in job market
- **Admin Interface**: Built-in management system for data operations
- **Extensions**: Rich ecosystem (django-filters, django-rest-framework, etc.)

## Migration Strategy

### Phase 1: Planning & Preparation (Current)
- ✅ Identify all existing endpoints and services
- ✅ Map data models and relationships
- ✅ Plan database schema migrations
- ✅ Update all documentation
- ⏳ Create detailed technical specifications

### Phase 2: Django Project Setup
- Create new Django project structure
- Configure settings for development and production
- Setup database (PostgreSQL recommended)
- Implement authentication system
- Create custom user models if needed

### Phase 3: Data Models (ORM)
- Create Django models for all entities:
  - `studies.models.Study` (from medical_examinations_fact)
  - `reports.models.Report`
  - `analysis.models.AnalysisTask`
  - `auth.models.CustomUser`
- Define relationships and constraints
- Create model managers for complex queries
- Write data migrations

### Phase 4: Django Ninja API Layer
- Create API routers for each app
- Implement endpoints with type annotations
- Create Pydantic/DRF schemas
- Implement pagination, filtering, sorting
- Add proper error responses

### Phase 5: Business Logic
- Migrate service classes to Django models/managers
- Create signals for side effects
- Implement validation at model layer
- Create management commands for data operations

### Phase 6: Authentication & Authorization
- Implement Django authentication
- Create token system (JWT or DRF tokens)
- Implement permission system
- Create decorators for endpoint protection

### Phase 7: Excel Data Integration
- Create management command for data import
- Implement ExcelDataLoader as Django service
- Create periodic import task (Celery optional)
- Add data validation at model level

### Phase 8: Admin Interface
- Register models in Django admin
- Create custom admin actions
- Add list filters and search
- Customize display and permissions

### Phase 9: Frontend Integration
- Update API client URLs (minimal changes)
- Verify authentication flow
- Test all endpoints
- Update error handling if needed

### Phase 10: Testing & Deployment
- Create comprehensive test suite
- Setup CI/CD pipeline
- Performance testing and optimization
- Documentation and handover

## Key Implementation Details

### 1. Data Models

```python
# studies/models.py
from django.db import models

class Study(models.Model):
    exam_id = models.CharField(max_length=50, primary_key=True)
    medical_record_no = models.CharField(max_length=100, null=True)
    patient_name = models.CharField(max_length=200)
    patient_gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female')])
    patient_age = models.IntegerField(null=True)

    exam_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])

    exam_source = models.CharField(max_length=20)
    exam_item = models.CharField(max_length=100)
    exam_description = models.TextField(null=True)

    order_datetime = models.DateTimeField()
    check_in_datetime = models.DateTimeField(null=True)
    report_certification_datetime = models.DateTimeField(null=True)
    certified_physician = models.CharField(max_length=200, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order_datetime']
        indexes = [
            models.Index(fields=['exam_status']),
            models.Index(fields=['exam_source']),
        ]

    def __str__(self):
        return f"{self.exam_id} - {self.patient_name}"
```

### 2. Django Ninja API

```python
# studies/api.py
from ninja import Router, Query, Schema
from ninja.pagination import paginate, PageNumberPagination
from .models import Study
from .schemas import StudySchema, FilterOptionsSchema

router = Router()

@router.get("/search/", response=list[StudySchema])
@paginate(PageNumberPagination)
def search_studies(
    request,
    q: str = Query(""),
    exam_status: str = Query(None),
    exam_source: str = Query(None),
    exam_item: str = Query(None),
):
    studies = Study.objects.all()

    if q:
        studies = studies.filter(
            Q(patient_name__icontains=q) |
            Q(exam_description__icontains=q)
        )

    if exam_status:
        studies = studies.filter(exam_status=exam_status)

    if exam_source:
        studies = studies.filter(exam_source=exam_source)

    if exam_item:
        studies = studies.filter(exam_item=exam_item)

    return studies.order_by('-order_datetime')

@router.get("/filters/options/", response=FilterOptionsSchema)
def get_filter_options(request):
    return {
        'exam_statuses': list(Study.objects.values_list('exam_status', flat=True).distinct()),
        'exam_sources': list(Study.objects.values_list('exam_source', flat=True).distinct()),
        'exam_items': list(Study.objects.values_list('exam_item', flat=True).distinct()),
    }
```

### 3. Management Command for Data Import

```python
# studies/management/commands/import_excel.py
from django.core.management.base import BaseCommand
from studies.utils import import_studies_from_excel

class Command(BaseCommand):
    help = 'Import medical examination data from Excel file'

    def handle(self, *args, **options):
        self.stdout.write("Importing studies from Excel...")
        count = import_studies_from_excel('20251029130203.xlsx')
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} records'))
```

### 4. Settings Configuration

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'ninja',
    'studies',
    'reports',
    'analysis',
    'auth_app',  # Custom auth app
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'medical_imaging'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
```

## Comparison: Endpoint Migration

### Study Search Endpoints

| Endpoint | FastAPI | Django Ninja |
|----------|---------|--------------|
| Search | `GET /api/v1/studies/search` | `GET /api/v1/studies/search/` |
| Detail | `GET /api/v1/studies/{exam_id}` | `GET /api/v1/studies/{exam_id}/` |
| Filters | `GET /api/v1/studies/filters/options` | `GET /api/v1/studies/filters/options/` |
| Export | `GET /api/v1/studies/export` | `GET /api/v1/studies/export/` |

**Note**: Minimal frontend changes required (just trailing slashes in some cases)

## Technology Stack Comparison

### Current (FastAPI)
```
FastAPI 0.104.1
├── Pydantic 2.5.0
├── SQLAlchemy (if added)
├── DuckDB 0.9.2
├── Uvicorn 0.24.0
└── openpyxl 3.11.0
```

### Target (Django Ninja)
```
Django 4.2+
├── Django Ninja 0.21+
├── Django REST Framework 3.14+
├── Pydantic 2.5.0 (for schemas)
├── PostgreSQL driver (psycopg2)
├── Django Migrations (built-in)
├── Celery (optional, for async)
└── openpyxl 3.11.0 (unchanged)
```

## Frontend Changes

### Minimal Required Changes

1. **API URLs**: Update base URL (already using constants)
2. **Trailing Slashes**: Some endpoints might need `/` suffix
3. **Error Handling**: Django error responses slightly different format
4. **Authentication**: If switching to Django JWT, minor token handling updates

```typescript
// Before (FastAPI)
const API_BASE = 'http://localhost:8000/api/v1'

// After (Django Ninja)
const API_BASE = 'http://localhost:8000/api/v1'  // No change needed if properly configured
```

## Development Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: Planning | 1-2 days | Today | Tomorrow |
| Phase 2: Django Setup | 1-2 days | Tomorrow | +2 days |
| Phase 3: Data Models | 2-3 days | +2 days | +5 days |
| Phase 4: API Layer | 2-3 days | +5 days | +8 days |
| Phase 5: Business Logic | 1-2 days | +8 days | +10 days |
| Phase 6: Auth & Security | 1-2 days | +10 days | +12 days |
| Phase 7: Data Integration | 1 day | +12 days | +13 days |
| Phase 8: Admin Interface | 1 day | +13 days | +14 days |
| Phase 9: Frontend Integration | 2-3 days | +14 days | +17 days |
| Phase 10: Testing & Deploy | 2-3 days | +17 days | +20 days |

**Total Estimated Timeline**: 20-25 working days

## Risk Assessment

### 🟠 Medium Risks

1. **ORM Learning Curve**
   - Mitigation: Django ORM documentation is comprehensive
   - Fallback: Can use raw SQL if needed

2. **Data Migration**
   - Mitigation: Create comprehensive migration scripts
   - Fallback: Run old system in parallel

3. **Performance Differences**
   - Mitigation: Profile and optimize queries
   - Fallback: Add caching layer (Redis)

### 🟢 Low Risks

1. **Dependency Conflicts**: Django ecosystem is stable
2. **Community Support**: Excellent, large community
3. **Deployment**: Similar to FastAPI deployment

## Benefits of Migration

✅ **Faster Development**: Scaffolding, admin interface, built-in features
✅ **Better Maintenance**: ORM, migrations, clear app structure
✅ **Easier Debugging**: Django debug toolbar, comprehensive logging
✅ **Team Scalability**: More Django developers available
✅ **Feature Rich**: Auth, admin, forms, signals, testing utilities
✅ **Future-Proof**: Active development, long-term support

## Next Steps

1. ✅ **Approve Architecture Change** (Current)
2. ⏳ **Create Detailed Technical Specifications**
3. ⏳ **Setup Django Project**
4. ⏳ **Create Data Models**
5. ⏳ **Implement API Layer**
6. ⏳ **Migrate Business Logic**
7. ⏳ **Test & Validate**
8. ⏳ **Deploy**

## Rollback Plan

If issues arise during migration:
1. Keep existing FastAPI system running in parallel
2. Route traffic to FastAPI while debugging Django
3. Use database replication for data consistency
4. Switch back if Django approach proves problematic

## Questions & Decisions Needed

1. **Database Choice**: PostgreSQL (recommended) or MySQL?
2. **Authentication**: Django Auth or third-party (Auth0, etc.)?
3. **Async Support**: Include async views/tasks?
4. **Admin Interface**: Fully customized or default?
5. **Celery**: Include task queue for background jobs?
6. **Caching**: Add Redis for performance?
7. **CI/CD**: GitHub Actions, GitLab CI, or Jenkins?

---

**Prepared for**: User Architecture Review
**Status**: 📋 Ready for Implementation Planning
**Next Action**: Approve plan and proceed with Phase 2

