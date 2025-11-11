# Django Migration - Detailed Task Breakdown

**Project**: Medical Imaging Data Platform Architecture Migration
**From**: FastAPI + DuckDB
**To**: Django + Django Ninja + PostgreSQL
**Status**: 🔄 Ready for Implementation

## Overview

This document provides granular task breakdown for migrating the medical imaging data platform from FastAPI to Django with Django Ninja API layer.

---

## PHASE 1: Planning & Preparation ✅ (CURRENT)

### Task 1.1: Architecture Documentation
- [x] Create migration plan document
- [x] Document current FastAPI architecture
- [x] Design target Django architecture
- [x] Compare technology stacks
- [x] Identify all endpoints to migrate
- [ ] **NEXT**: Get user approval to proceed

### Task 1.2: API Endpoint Inventory
**Endpoints to Migrate**:

**Studies (Study Search)**
- `GET /api/v1/studies/search` → Search with filters and pagination
- `GET /api/v1/studies/{exam_id}` → Get study detail
- `GET /api/v1/studies/filters/options` → Get filter options
- `GET /api/v1/studies/export` → Export to Excel

**Reports (Report Search)**
- `GET /api/v1/reports/search` → Search with filters
- `GET /api/v1/reports/{report_id}` → Get report detail
- `GET /api/v1/reports/filters/options` → Get filter options

**Analysis (AI Analysis)**
- `POST /api/v1/analysis/tasks` → Create analysis task
- `GET /api/v1/analysis/tasks` → List analysis tasks
- `GET /api/v1/analysis/tasks/{task_id}` → Get task detail
- `DELETE /api/v1/analysis/tasks/{task_id}` → Cancel analysis task
- `GET /api/v1/analysis/statistics` → Get statistics
- `GET /api/v1/analysis/options` → Get analysis options

**Authentication**
- `POST /api/v1/auth/login` → User login
- `POST /api/v1/auth/logout` → User logout
- `GET /api/v1/auth/me` → Get current user

**Data Import**
- `POST /api/v1/import/studies` → Import studies from Excel
- `POST /api/v1/import/reports` → Import reports from file

### Task 1.3: Data Model Mapping

**Current: medical_examinations_fact (DuckDB)**
```
exam_id, medical_record_no, application_order_no, patient_name,
patient_gender, patient_age, exam_status, exam_source, exam_item,
exam_description, order_datetime, check_in_datetime,
report_certification_datetime, certified_physician
```

**Target: Study Model (Django ORM)**
```python
class Study(models.Model):
    exam_id → CharField (primary_key=True)
    medical_record_no → CharField
    application_order_no → CharField
    patient_name → CharField
    patient_gender → CharField
    patient_age → IntegerField
    exam_status → CharField (with choices)
    exam_source → CharField
    exam_item → CharField
    exam_description → TextField
    order_datetime → DateTimeField
    check_in_datetime → DateTimeField
    report_certification_datetime → DateTimeField
    certified_physician → CharField
    created_at → DateTimeField (auto_now_add)
    updated_at → DateTimeField (auto_now)
```

### Task 1.4: Technology Selection
- [x] Identify primary database: **PostgreSQL 14+** (recommended)
- [x] Select authentication method: **Django Authentication + JWT**
- [x] Choose API documentation: **Django Ninja auto-documentation**
- [x] Async support decision: **Start without, add if needed**
- [ ] Decide on background tasks: **Celery optional for Phase 2**

---

## PHASE 2: Django Project Setup (1-2 days)

### Task 2.1: Project Structure Creation
```bash
mkdir medical_imaging_django
cd medical_imaging_django
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

**Create project structure**:
```
medical_imaging_django/
├── manage.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── config/                    # Settings & configuration
│   ├── __init__.py
│   ├── settings.py           # Django settings
│   ├── urls.py               # URL routing
│   ├── asgi.py
│   └── wsgi.py
├── apps/                      # Django apps
│   ├── studies/              # Study Search app
│   ├── reports/              # Report Search app
│   ├── analysis/             # AI Analysis app
│   └── users/                # Authentication app
├── api/                       # Django Ninja API configuration
│   ├── __init__.py
│   └── schema.py             # Shared schema definitions
├── utils/                     # Utilities & helpers
│   ├── excel_loader.py       # Excel import logic
│   └── validators.py
├── staticfiles/              # Static files
├── media/                    # Media files
├── tests/                    # Test suite
└── docs/                     # Documentation
```

### Task 2.2: Environment Configuration
**Create `.env.example`**:
```
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.postgresql
DB_NAME=medical_imaging
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

EXCEL_FILE_PATH=20251029130203.xlsx
```

### Task 2.3: Dependencies Installation
**Create `requirements.txt`**:
```
Django==4.2.7
django-ninja==0.21.0
djangorestframework==3.14.0
django-cors-headers==4.3.1
djangorestframework-simplejwt==5.3.2
psycopg2-binary==2.9.9
pydantic==2.5.0
openpyxl==3.11.0
python-dotenv==1.0.0
python-decouple==3.8
drf-spectacular==0.26.5
```

**Install**:
```bash
pip install -r requirements.txt
```

### Task 2.4: Django Configuration
**`config/settings.py`**:
- Configure database (PostgreSQL)
- Add installed apps (studies, reports, analysis, users)
- Setup CORS headers
- Configure JWT authentication
- Setup static/media files
- Configure logging

**`config/urls.py`**:
- Mount Django Ninja API router
- Add admin URLs
- Add API schema/documentation

### Task 2.5: Database Setup
```bash
# Create PostgreSQL database
createdb medical_imaging

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

---

## PHASE 3: Data Models (ORM) (2-3 days)

### Task 3.1: Users App
**`apps/users/models.py`**:
```python
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Tasks**:
- [x] Create User model
- [ ] Create custom user manager
- [ ] Add authentication signals
- [ ] Create user admin customization

### Task 3.2: Studies App
**`apps/studies/models.py`**:
```python
class Study(models.Model):
    exam_id = models.CharField(max_length=50, primary_key=True)
    medical_record_no = models.CharField(max_length=100, null=True, blank=True)
    application_order_no = models.CharField(max_length=100, null=True, blank=True)
    patient_name = models.CharField(max_length=200)
    patient_gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female')])
    patient_age = models.IntegerField(null=True, blank=True)

    EXAM_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    exam_status = models.CharField(max_length=20, choices=EXAM_STATUS_CHOICES)
    exam_source = models.CharField(max_length=20)
    exam_item = models.CharField(max_length=100)
    exam_description = models.TextField(null=True, blank=True)

    order_datetime = models.DateTimeField()
    check_in_datetime = models.DateTimeField(null=True, blank=True)
    report_certification_datetime = models.DateTimeField(null=True, blank=True)
    certified_physician = models.CharField(max_length=200, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order_datetime']
        indexes = [
            models.Index(fields=['exam_status']),
            models.Index(fields=['exam_source']),
            models.Index(fields=['order_datetime']),
        ]

    def __str__(self):
        return f"{self.exam_id} - {self.patient_name}"
```

**`apps/studies/managers.py`**:
```python
class StudyQuerySet(models.QuerySet):
    def search(self, q='', exam_status=None, exam_source=None, exam_item=None):
        qs = self.all()
        if q:
            qs = qs.filter(
                Q(patient_name__icontains=q) |
                Q(exam_description__icontains=q) |
                Q(exam_item__icontains=q)
            )
        if exam_status:
            qs = qs.filter(exam_status=exam_status)
        if exam_source:
            qs = qs.filter(exam_source=exam_source)
        if exam_item:
            qs = qs.filter(exam_item=exam_item)
        return qs

class StudyManager(models.Manager):
    def get_queryset(self):
        return StudyQuerySet(self.model, using=self._db)

    def search(self, **kwargs):
        return self.get_queryset().search(**kwargs)
```

**Tasks**:
- [ ] Create Study model with all fields
- [ ] Create custom manager and queryset
- [ ] Add database indexes
- [ ] Create model admin
- [ ] Create fixtures for testing

### Task 3.3: Reports App
**`apps/reports/models.py`**:
```python
class Report(models.Model):
    report_id = models.CharField(max_length=50, primary_key=True)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='reports')
    radiologist = models.CharField(max_length=200)
    content = models.TextField()

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('finalized', 'Finalized'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
```

**Tasks**:
- [ ] Create Report model
- [ ] Create relationship to Study
- [ ] Create custom queryset/manager
- [ ] Create model admin
- [ ] Add validation

### Task 3.4: Analysis App
**`apps/analysis/models.py`**:
```python
class AnalysisTask(models.Model):
    task_id = models.CharField(max_length=50, primary_key=True)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='analysis_tasks')

    ANALYSIS_TYPE_CHOICES = [
        ('general', 'General Analysis'),
        ('detailed', 'Detailed Analysis'),
        ('comparison', 'Comparison Analysis'),
    ]
    analysis_type = models.CharField(max_length=20, choices=ANALYSIS_TYPE_CHOICES)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0)  # 0-100

    description = models.TextField(null=True, blank=True)
    result = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
```

**Tasks**:
- [ ] Create AnalysisTask model
- [ ] Create relationships
- [ ] Create custom manager
- [ ] Add progress tracking
- [ ] Create model admin

### Task 3.5: Create & Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

**Tasks**:
- [ ] Generate initial migration
- [ ] Review migration files
- [ ] Test migration on fresh database
- [ ] Create migration documentation

---

## PHASE 4: Django Ninja API Layer (2-3 days)

### Task 4.1: Create API Schemas

**`api/schemas.py`**:
```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class StudySchema(BaseModel):
    exam_id: str
    medical_record_no: Optional[str]
    patient_name: str
    exam_status: str
    exam_source: str
    exam_item: str
    order_datetime: datetime

class FilterOptionsSchema(BaseModel):
    exam_statuses: List[str]
    exam_sources: List[str]
    exam_items: List[str]
```

**Tasks**:
- [ ] Create Pydantic schemas for all models
- [ ] Add validation
- [ ] Create nested schemas
- [ ] Document schema fields

### Task 4.2: Studies API Endpoints

**`apps/studies/api.py`**:
```python
from ninja import Router, Query
from ninja.pagination import paginate, PageNumberPagination
from .models import Study
from .schemas import StudySchema

router = Router()

@router.get("/search/", response=list[StudySchema])
@paginate(PageNumberPagination)
def search_studies(
    request,
    q: str = Query(""),
    exam_status: str = Query(None),
    exam_source: str = Query(None),
):
    return Study.objects.search(
        q=q,
        exam_status=exam_status,
        exam_source=exam_source,
    )

@router.get("/{exam_id}/", response=StudySchema)
def get_study(request, exam_id: str):
    return Study.objects.get(exam_id=exam_id)

@router.get("/filters/options/")
def filter_options(request):
    return {
        'exam_statuses': list(Study.objects.values_list('exam_status', flat=True).distinct()),
        'exam_sources': list(Study.objects.values_list('exam_source', flat=True).distinct()),
        'exam_items': list(Study.objects.values_list('exam_item', flat=True).distinct()),
    }
```

**Tasks**:
- [ ] Create Studies router
- [ ] Implement search endpoint
- [ ] Implement detail endpoint
- [ ] Implement filter options endpoint
- [ ] Add pagination
- [ ] Add filtering & sorting
- [ ] Add error handling

### Task 4.3: Reports API Endpoints
**Tasks**:
- [ ] Create Reports router
- [ ] Implement all CRUD endpoints
- [ ] Add relationships handling
- [ ] Add filtering & pagination

### Task 4.4: Analysis API Endpoints
**Tasks**:
- [ ] Create Analysis router
- [ ] Implement task creation
- [ ] Implement task listing
- [ ] Implement task detail
- [ ] Implement task cancellation
- [ ] Implement statistics endpoint

### Task 4.5: Authentication API
**`apps/users/api.py`**:
```python
@router.post("/login/")
def login(request, username: str, password: str):
    user = authenticate(request, username=username, password=password)
    if user:
        token = get_tokens_for_user(user)
        return {"access": token["access"], "refresh": token["refresh"]}
    raise HttpError(401, "Invalid credentials")

@router.get("/me/", auth=JWTAuth())
def get_user(request):
    return UserSchema.from_orm(request.auth)
```

**Tasks**:
- [ ] Implement login endpoint
- [ ] Implement logout endpoint
- [ ] Implement user detail endpoint
- [ ] Add JWT token generation
- [ ] Add refresh token handling

### Task 4.6: API Documentation
**Tasks**:
- [ ] Setup auto-documentation
- [ ] Document all endpoints
- [ ] Add request/response examples
- [ ] Create API documentation page

---

## PHASE 5: Business Logic Migration (1-2 days)

### Task 5.1: Migrate StudyService
**Current FastAPI**:
```python
class StudyService:
    @staticmethod
    def search_studies(request: StudySearchRequest) -> StudySearchResponse:
        # Build WHERE clause
        # Execute query
        # Return results
```

**Target Django Approach**:
```python
# Use models.Manager instead
class Study(models.Model):
    objects = StudyManager()

# Use in views/endpoints
def search_studies(request, q='', exam_status=None):
    return Study.objects.search(q=q, exam_status=exam_status)
```

**Tasks**:
- [ ] Convert StudyService methods to model managers
- [ ] Move query logic to QuerySet
- [ ] Add custom methods to models
- [ ] Remove FastAPI service classes

### Task 5.2: Create Model Signals
**`apps/studies/signals.py`**:
```python
@receiver(post_save, sender=AnalysisTask)
def on_analysis_task_created(sender, instance, created, **kwargs):
    if created:
        # Queue background job
        # Send notification
        # Log activity
        pass
```

**Tasks**:
- [ ] Create analysis task signals
- [ ] Add completion notifications
- [ ] Add audit logging
- [ ] Add cache invalidation

### Task 5.3: Validators & Utilities
**Tasks**:
- [ ] Create field validators
- [ ] Create business logic validators
- [ ] Create utility functions
- [ ] Add error handlers

---

## PHASE 6: Authentication & Authorization (1-2 days)

### Task 6.1: User Authentication
**Tasks**:
- [ ] Configure Django authentication
- [ ] Create JWT token system
- [ ] Implement token refresh
- [ ] Add password hashing
- [ ] Create user serializers

### Task 6.2: Authorization & Permissions
**`apps/users/permissions.py`**:
```python
class IsAuthenticated(BasePermission):
    def has_permission(self, request):
        return request.user and request.user.is_authenticated

class IsAdmin(BasePermission):
    def has_permission(self, request):
        return request.user and request.user.is_staff
```

**Tasks**:
- [ ] Create permission classes
- [ ] Implement role-based access
- [ ] Add endpoint protection
- [ ] Create permission checks

### Task 6.3: Security Settings
**Tasks**:
- [ ] Configure CORS properly
- [ ] Add CSRF protection
- [ ] Configure headers security
- [ ] Add rate limiting
- [ ] Setup SSL/HTTPS

---

## PHASE 7: Data Integration (1 day)

### Task 7.1: Create Management Command
**`apps/studies/management/commands/import_excel.py`**:
```python
from django.core.management.base import BaseCommand
from studies.services import import_studies_from_excel

class Command(BaseCommand):
    help = 'Import studies from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str)

    def handle(self, *args, **options):
        count = import_studies_from_excel(options['file_path'])
        self.stdout.write(f'Imported {count} studies')
```

**Tasks**:
- [ ] Migrate ExcelDataLoader to Django
- [ ] Create import management command
- [ ] Add data validation
- [ ] Create import error handling
- [ ] Add duplicate detection

### Task 7.2: Data Migration from DuckDB
**Tasks**:
- [ ] Export data from DuckDB
- [ ] Create import script
- [ ] Validate data integrity
- [ ] Test import process
- [ ] Document migration steps

---

## PHASE 8: Admin Interface (1 day)

### Task 8.1: Register Models in Admin
**`apps/studies/admin.py`**:
```python
@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ['exam_id', 'patient_name', 'exam_status', 'order_datetime']
    list_filter = ['exam_status', 'exam_source']
    search_fields = ['exam_id', 'patient_name']
    readonly_fields = ['created_at', 'updated_at']
```

**Tasks**:
- [ ] Register all models
- [ ] Add list displays
- [ ] Add filters
- [ ] Add search
- [ ] Add custom actions

### Task 8.2: Admin Customization
**Tasks**:
- [ ] Create custom admin site
- [ ] Add dashboard
- [ ] Add bulk actions
- [ ] Add export functionality
- [ ] Customize admin interface

---

## PHASE 9: Frontend Integration (2-3 days)

### Task 9.1: API Client Updates
**Frontend changes**:
```typescript
// Update API endpoints (minimal)
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api'

// Existing hooks should work with minimal changes
// useStudySearch() → no changes needed
// useAnalysisTaskList() → no changes needed
```

**Tasks**:
- [ ] Update API base URL if needed
- [ ] Verify endpoint compatibility
- [ ] Test authentication flow
- [ ] Update error handling
- [ ] Test all features

### Task 9.2: Frontend Testing
**Tasks**:
- [ ] Test login flow
- [ ] Test Study Search
- [ ] Test Report Search
- [ ] Test AI Analysis
- [ ] Test data export
- [ ] Test error scenarios

---

## PHASE 10: Testing & Deployment (2-3 days)

### Task 10.1: Create Test Suite
**`tests/test_studies.py`**:
```python
from django.test import TestCase
from apps.studies.models import Study

class StudyTestCase(TestCase):
    def setUp(self):
        self.study = Study.objects.create(
            exam_id="E001",
            patient_name="Test Patient",
            exam_status="completed"
        )

    def test_study_creation(self):
        self.assertEqual(self.study.exam_id, "E001")

    def test_study_search(self):
        results = Study.objects.search(q="Test")
        self.assertEqual(len(results), 1)
```

**Tasks**:
- [ ] Create unit tests for models
- [ ] Create API endpoint tests
- [ ] Create integration tests
- [ ] Create performance tests
- [ ] Achieve >80% code coverage

### Task 10.2: Setup CI/CD
**Tasks**:
- [ ] Configure GitHub Actions (or GitLab CI)
- [ ] Setup automated testing
- [ ] Setup code quality checks
- [ ] Setup deployment pipeline
- [ ] Configure staging environment

### Task 10.3: Deployment Preparation
**Tasks**:
- [ ] Setup production server
- [ ] Configure production database (PostgreSQL)
- [ ] Setup environment variables
- [ ] Configure static files serving
- [ ] Setup logging & monitoring
- [ ] Configure backups

### Task 10.4: Production Deployment
**Tasks**:
- [ ] Create deployment checklist
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Deploy to production
- [ ] Monitor for issues
- [ ] Create rollback plan

---

## Documentation Requirements

### Files to Create/Update
- [ ] Project README.md
- [ ] Architecture documentation
- [ ] API documentation (auto-generated by Django Ninja)
- [ ] Database schema documentation
- [ ] Deployment guide
- [ ] Troubleshooting guide
- [ ] Contributing guidelines

---

## Success Criteria

✅ All endpoints migrated and functional
✅ All tests passing (>80% coverage)
✅ API documentation complete
✅ Frontend integrated and tested
✅ Data imported successfully
✅ Admin interface functional
✅ Performance equivalent or better
✅ Production deployment successful

---

## Notes

- Keep FastAPI system running during migration for parallel testing
- Create database replication for data consistency
- Test extensively before full cutover
- Have rollback plan ready
- Document all changes and decisions

