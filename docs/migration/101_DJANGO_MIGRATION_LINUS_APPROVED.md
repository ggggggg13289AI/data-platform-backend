# Django Migration: Linus-Approved Implementation Plan
**Status**: 🔴 **REWRITTEN** - Stripped down to essentials
**Based on**: Linus Torvalds code review (Taste analysis)
**Timeline**: 7 working days (not 25)
**Principle**: Build for what exists (5 users, 5K records), not for what might exist (1000 concurrent users)

---

## 🎯 Core Philosophy

This plan eliminates:
- ~~DRF SerializerMethodField complexity~~ → Use only Pydantic schemas
- ~~Signals and decoupling~~ → Direct function calls
- ~~Management commands~~ → Inline endpoints
- ~~Admin interface~~ → Can't use at 2 users, add at Phase 2 if needed
- ~~Celery background tasks~~ → Tasks are synchronous and fast
- ~~Multiple apps~~ → Start with one monolithic `studies` app

This keeps:
- Django ORM (simpler than DuckDB for schema evolution)
- Django Ninja (type-safe, minimal code)
- PostgreSQL (optional - DuckDB works too, PostgreSQL teaches you real DB)

---

## 📋 Phase 1: Foundation (Days 1-3)
### Goal: Get ONE working API endpoint (Studies Search) in Django

**CRITICAL PRINCIPLE**: Before writing ANY code, lock down the API contract.

### Task 1.1: API Contract Definition ✅ (Day 1 - 2 hours)

**REQUIREMENT**: Response format MUST match FastAPI exactly, field-for-field.

**Current FastAPI Response** (what users see now):
```json
{
  "data": [
    {
      "exam_id": "EXAM001",
      "patient_name": "Zhang Wei",
      "patient_gender": "M",
      "patient_age": 45,
      "exam_status": "completed",
      "exam_source": "CT",
      "exam_item": "Chest CT",
      "order_datetime": "2025-11-06T10:30:00",
      "check_in_datetime": "2025-11-06T10:45:00",
      "report_certification_datetime": "2025-11-06T14:30:00"
    }
  ],
  "total": 1250,
  "page": 1,
  "page_size": 20,
  "filters": {
    "exam_statuses": ["pending", "completed", "failed"],
    "exam_sources": ["CT", "MRI", "X-ray"],
    "exam_items": ["Chest CT", "Abdominal CT"]
  }
}
```

**LOCK THIS IN**: This is your contract. Django MUST return this IDENTICALLY.

**Why**: One byte different = frontend breaks. No gradual migration possible.

**Document**: Create `API_CONTRACT.md` with every endpoint's request/response format.

### Task 1.2: Django Project Setup (Day 1 - 4 hours)

```bash
# Create project
mkdir medical_imaging_django
cd medical_imaging_django
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install minimal dependencies
pip install django==5.0.0 django-ninja==1.3.0 psycopg2-binary==2.9.9 pydantic==2.5.0 python-dotenv==1.0.0

# Create Django project
django-admin startproject config .
python manage.py startapp studies
```

**Project Structure** (minimal):
```
medical_imaging_django/
├── manage.py
├── requirements.txt
├── .env
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── studies/                    # Single app, not multiple
│   ├── models.py
│   ├── api.py                 # Django Ninja routes
│   ├── schemas.py             # Pydantic schemas
│   ├── services.py            # Business logic (search, filter)
│   └── admin.py
└── tests/
    └── test_api.py
```

### Task 1.3: Models Definition (Day 1-2 - 6 hours)

**File**: `studies/models.py`

```python
from django.db import models

class Study(models.Model):
    """Medical examination record - one table, no relationships (flat data)"""

    exam_id = models.CharField(max_length=50, primary_key=True)
    medical_record_no = models.CharField(max_length=100, null=True, blank=True)
    application_order_no = models.CharField(max_length=100, null=True, blank=True)

    patient_name = models.CharField(max_length=200)
    patient_gender = models.CharField(
        max_length=10,
        choices=[('M', 'Male'), ('F', 'Female'), ('U', 'Unknown')],
        null=True,
        blank=True
    )
    patient_age = models.IntegerField(null=True, blank=True)

    exam_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ]
    )
    exam_source = models.CharField(max_length=50)
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

**NO SIGNALS. NO CUSTOM MANAGERS. Just models.**

### Task 1.4: API Schemas (Day 2 - 3 hours)

**File**: `studies/schemas.py`

```python
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class StudySchema(BaseModel):
    """Response schema - MUST match FastAPI response exactly"""
    exam_id: str
    patient_name: str
    patient_gender: Optional[str] = None
    patient_age: Optional[int] = None
    exam_status: str
    exam_source: str
    exam_item: str
    order_datetime: datetime
    check_in_datetime: Optional[datetime] = None
    report_certification_datetime: Optional[datetime] = None

    class Config:
        from_attributes = True  # Convert ORM objects to schema

class FilterOptionsSchema(BaseModel):
    exam_statuses: List[str]
    exam_sources: List[str]
    exam_items: List[str]

class SearchResponseSchema(BaseModel):
    data: List[StudySchema]
    total: int
    page: int
    page_size: int
    filters: FilterOptionsSchema
```

### Task 1.5: API Endpoints (Day 2-3 - 8 hours)

**File**: `studies/api.py`

```python
from ninja import Router, Query
from typing import Optional
from django.db.models import Q
from .models import Study
from .schemas import StudySchema, FilterOptionsSchema, SearchResponseSchema

router = Router()

@router.get("/studies/search", response=SearchResponseSchema)
def search_studies(
    request,
    q: str = Query(""),
    exam_status: Optional[str] = Query(None),
    exam_source: Optional[str] = Query(None),
    exam_item: Optional[str] = Query(None),
    page: int = Query(1),
    page_size: int = Query(20),
):
    """Search studies with filters and pagination"""

    # Build query
    studies = Study.objects.all()

    # Text search
    if q:
        studies = studies.filter(
            Q(patient_name__icontains=q) |
            Q(exam_description__icontains=q) |
            Q(exam_item__icontains=q)
        )

    # Filter by status
    if exam_status:
        studies = studies.filter(exam_status=exam_status)

    # Filter by source
    if exam_source:
        studies = studies.filter(exam_source=exam_source)

    # Filter by item
    if exam_item:
        studies = studies.filter(exam_item=exam_item)

    # Get total count before pagination
    total = studies.count()

    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    paginated = studies.order_by('-order_datetime')[start:end]

    # Get filter options
    filter_options = FilterOptionsSchema(
        exam_statuses=list(Study.objects.values_list('exam_status', flat=True).distinct()),
        exam_sources=list(Study.objects.values_list('exam_source', flat=True).distinct()),
        exam_items=list(Study.objects.values_list('exam_item', flat=True).distinct()),
    )

    return SearchResponseSchema(
        data=[StudySchema.from_orm(s) for s in paginated],
        total=total,
        page=page,
        page_size=page_size,
        filters=filter_options
    )

@router.get("/studies/{exam_id}", response=StudySchema)
def get_study_detail(request, exam_id: str):
    """Get study detail"""
    study = Study.objects.get(pk=exam_id)
    return StudySchema.from_orm(study)

@router.get("/studies/filters/options", response=FilterOptionsSchema)
def get_filter_options(request):
    """Get available filter options"""
    return FilterOptionsSchema(
        exam_statuses=list(Study.objects.values_list('exam_status', flat=True).distinct()),
        exam_sources=list(Study.objects.values_list('exam_source', flat=True).distinct()),
        exam_items=list(Study.objects.values_list('exam_item', flat=True).distinct()),
    )
```

**CRITICAL**: This response format is LOCKED. Any change breaks frontend.

### Task 1.6: Configuration (Day 3 - 4 hours)

**File**: `config/settings.py` (key sections)

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ninja',
    'studies',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'medical_imaging',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

**File**: `config/urls.py`

```python
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from studies.api import router as studies_router

api = NinjaAPI(title="Medical Imaging API", version="1.1.0")
api.add_router("/", studies_router)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
]
```

### Task 1.7: Data Migration (Day 3 - 6 hours)

**CRITICAL**: How to get data from DuckDB into PostgreSQL WITHOUT losing records.

**File**: `studies/management/commands/migrate_from_duckdb.py`

```python
import os
import duckdb
from django.core.management.base import BaseCommand
from studies.models import Study

class Command(BaseCommand):
    help = 'Migrate data from DuckDB to PostgreSQL'

    def handle(self, *args, **options):
        # Connect to DuckDB (read-only)
        db_path = os.path.join(os.path.dirname(__file__), '../../../..', 'medical_imaging.duckdb')

        if not os.path.exists(db_path):
            self.stdout.write(self.style.ERROR(f"DuckDB file not found: {db_path}"))
            return

        conn = duckdb.connect(db_path, read_only=True)

        try:
            # Fetch all records
            result = conn.execute("SELECT * FROM medical_examinations_fact").fetchall()
            columns = [desc[0] for desc in conn.description]

            self.stdout.write(f"Found {len(result)} records in DuckDB")

            # Map DuckDB columns to Django fields
            for row in result:
                data = dict(zip(columns, row))

                # Convert datetime strings if needed
                if isinstance(data.get('order_datetime'), str):
                    data['order_datetime'] = datetime.fromisoformat(data['order_datetime'])

                # Check for duplicates
                exam_id = data.get('exam_id')
                if Study.objects.filter(pk=exam_id).exists():
                    self.stdout.write(self.style.WARNING(f"Study {exam_id} already exists, skipping"))
                    continue

                # Create Study
                Study.objects.create(**data)

            self.stdout.write(self.style.SUCCESS("Migration completed successfully"))

            # Verify
            count = Study.objects.count()
            self.stdout.write(f"Total records in PostgreSQL: {count}")

        finally:
            conn.close()
```

**Usage**:
```bash
# Run migration
python manage.py migrate_from_duckdb

# Verify
python manage.py shell
>>> from studies.models import Study
>>> Study.objects.count()  # Should match DuckDB count
```

### Task 1.8: Testing (Day 3 - 4 hours)

**File**: `tests/test_api.py`

```python
from django.test import TestCase, Client
from studies.models import Study
from datetime import datetime
import json

class StudyAPITest(TestCase):
    def setUp(self):
        # Create test data
        Study.objects.create(
            exam_id="TEST001",
            patient_name="Test Patient",
            patient_gender="M",
            patient_age=45,
            exam_status="completed",
            exam_source="CT",
            exam_item="Chest CT",
            order_datetime=datetime.now(),
        )
        self.client = Client()

    def test_search_endpoint(self):
        """Test /api/v1/studies/search returns correct format"""
        response = self.client.get('/api/v1/studies/search')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)

        # Verify response structure matches API contract
        self.assertIn('data', data)
        self.assertIn('total', data)
        self.assertIn('page', data)
        self.assertIn('page_size', data)
        self.assertIn('filters', data)

        # Verify data fields
        self.assertIn('exam_id', data['data'][0])
        self.assertIn('patient_name', data['data'][0])

    def test_filter_options(self):
        """Test filter options endpoint"""
        response = self.client.get('/api/v1/studies/filters/options')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertIn('exam_statuses', data)
        self.assertIn('exam_sources', data)
```

**Run tests**:
```bash
python manage.py test tests.test_api
```

---

## 📋 Phase 2: Complete API (Days 4-5)
### Goal: Add Reports and Analysis endpoints (same pattern as Studies)

**NO NEW ARCHITECTURE**: Copy the Studies pattern for Reports and Analysis.

Each endpoint:
1. Define schema (Pydantic)
2. Write endpoint (Django Ninja router)
3. Write tests
4. Lock down response format

---

## 📋 Phase 3: Data Migration & Cutover (Day 6)
### Goal: Switch frontend from FastAPI to Django

**Steps**:
1. Run `manage.py migrate_from_duckdb` (copy all records from DuckDB)
2. Verify counts match: `DuckDB count == Django count`
3. Update frontend `.env`: `REACT_APP_API_BASE=http://localhost:8000/api/v1`
4. Test all endpoints
5. Verify no 404 errors

---

## 📋 Phase 4: Polish & Deploy (Day 7)
### Goal: Production-ready code

**Add**:
- Error handling (try/except in endpoints)
- Logging
- CORS configuration
- Authentication (if needed)

**NO**: Admin interface, signals, management commands, Celery.

---

## 🔴 Critical Constraints (Never Break Userspace)

### 1. API Response Format is LOCKED
If Django response differs from FastAPI response by ONE field, frontend breaks.

**Before writing ANY endpoint**:
- Document current FastAPI response
- Ensure Django returns IDENTICAL format
- Write tests to verify this

### 2. Records Must Not Be Lost
If migration script loses even one record, medical data is corrupted.

**Validation**:
```bash
# DuckDB count
SELECT COUNT(*) FROM medical_examinations_fact;  # e.g., 1250

# PostgreSQL count
python manage.py shell
>>> from studies.models import Study
>>> Study.objects.count()  # MUST be 1250

# Verify no duplicates
>>> Study.objects.values('exam_id').annotate(count=Count('exam_id')).filter(count__gt=1)
# MUST be empty
```

### 3. All Endpoints Must Be Implemented
Can't cut features mid-migration. Users expect same functionality.

---

## ⏱️ Daily Breakdown

| Day | Phase | What | Hours |
|-----|-------|------|-------|
| 1 | 1.1-1.2 | API contract + Django setup | 6 |
| 2 | 1.3-1.4 | Models + schemas | 9 |
| 3 | 1.5-1.8 | Endpoints + migration + tests | 14 |
| 4 | 2 | Reports + Analysis endpoints | 8 |
| 5 | 2 | Finish remaining endpoints | 8 |
| 6 | 3 | Data migration + cutover | 8 |
| 7 | 4 | Error handling + deploy | 6 |

**Total: 59 hours = ~7.4 days**

---

## ✅ Success Criteria

- [ ] Phase 1 Studies endpoint returns IDENTICAL format to FastAPI
- [ ] All records migrated from DuckDB without loss
- [ ] No duplicate keys in PostgreSQL
- [ ] All endpoints return correct data
- [ ] Frontend works without modification
- [ ] All tests pass
- [ ] Zero 404 errors

---

## 🛑 What NOT to Do

- ❌ Don't add admin interface
- ❌ Don't create signals
- ❌ Don't use multiple apps (use single `studies` app)
- ❌ Don't add Celery
- ❌ Don't change response format mid-implementation
- ❌ Don't skip migration validation
- ❌ Don't deploy without verifying records match

---

**This plan is Linus-approved: Pragmatic, minimal scope, focused on real problems.**
