# Troubleshooting Guide - Medical Imaging Management System

**Version**: 1.1.0
**Last Updated**: 2025-11-10

This guide helps resolve common issues encountered during development, testing, and deployment of the Django backend.

---

## Table of Contents

- [Setup Issues](#setup-issues)
- [Database Issues](#database-issues)
- [API Issues](#api-issues)
- [Performance Issues](#performance-issues)
- [Testing Issues](#testing-issues)
- [Deployment Issues](#deployment-issues)
- [UV Package Manager Issues](#uv-package-manager-issues)
- [Cache Issues](#cache-issues)
- [Debug Mode](#debug-mode)

---

## Setup Issues

### Issue: UV Not Found

**Symptoms**:
```bash
$ uv sync
'uv' is not recognized as an internal or external command
```

**Cause**: UV package manager not installed

**Solution**:

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

**Alternative**: Install via pipx
```bash
pipx install uv
```

---

### Issue: Environment Variables Not Loaded

**Symptoms**:
```
django.core.exceptions.ImproperlyConfigured: Set the DB_NAME environment variable
```

**Cause**: `.env` file missing or not being loaded

**Solution**:

1. **Check `.env` file exists**:
```bash
# Windows
if exist .env (echo .env found) else (echo .env missing)

# macOS / Linux
test -f .env && echo ".env found" || echo ".env missing"
```

2. **Create from template**:
```bash
cp .env.example .env
```

3. **Edit `.env` with your credentials**:
```bash
# Required settings
DB_NAME=medical_imaging
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Optional settings
DEBUG=True
DJANGO_SECRET_KEY=your-secret-key-change-in-production
CACHE_BACKEND=locmem
```

4. **Verify loading**:
```python
# Django shell
python manage.py shell

>>> import os
>>> print(os.getenv('DB_NAME'))
medical_imaging
```

---

### Issue: Python Version Mismatch

**Symptoms**:
```
This project requires Python 3.11+
```

**Cause**: Incompatible Python version

**Solution**:

```bash
# Check Python version
python --version

# Create virtual environment with specific Python version
uv venv --python 3.11

# Or specify Python path
uv venv --python /path/to/python3.11
```

**Recommended**: Python 3.11 or higher for best compatibility

---

### Issue: Dependencies Installation Fails

**Symptoms**:
```
error: Failed to download distributions
```

**Cause**: Network issues, package conflicts, or corrupted lock file

**Solution**:

```bash
# 1. Clear UV cache
uv cache clean

# 2. Remove existing virtual environment
rm -rf .venv  # macOS/Linux
rmdir /s .venv  # Windows

# 3. Reinstall from scratch
uv sync

# 4. If still fails, update UV itself
pipx upgrade uv

# 5. Try with verbose output
uv sync -v
```

---

## Database Issues

### Issue: PostgreSQL Connection Failed

**Symptoms**:
```
django.db.utils.OperationalError: could not connect to server: Connection refused
```

**Cause**: PostgreSQL not running or incorrect connection settings

**Solution**:

1. **Check PostgreSQL status**:
```bash
# Windows
sc query postgresql-x64-14

# macOS
brew services list | grep postgresql

# Linux
sudo systemctl status postgresql
```

2. **Start PostgreSQL**:
```bash
# Windows
net start postgresql-x64-14

# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql
```

3. **Verify connection settings** in `.env`:
```bash
# Try 127.0.0.1 instead of localhost
DB_HOST=127.0.0.1
```

4. **Test connection directly**:
```bash
psql -h localhost -U postgres -d medical_imaging
```

---

### Issue: Database Does Not Exist

**Symptoms**:
```
django.db.utils.OperationalError: database "medical_imaging" does not exist
```

**Cause**: Database not created yet

**Solution**:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE medical_imaging ENCODING 'UTF8';

# Create user (if needed)
CREATE USER medical_user WITH PASSWORD 'your_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE medical_imaging TO medical_user;

# Exit
\q

# Run Django migrations
python manage.py migrate
```

---

### Issue: Migration Conflicts

**Symptoms**:
```
django.db.migrations.exceptions.InconsistentMigrationHistory
```

**Cause**: Migration history mismatch between code and database

**Solution**:

```bash
# 1. Check migration status
python manage.py showmigrations

# 2. If in development, reset database
python manage.py migrate studies zero

# 3. Re-run migrations
python manage.py migrate

# 4. If in production, use --fake carefully
python manage.py migrate --fake studies 0001_initial
python manage.py migrate
```

**Warning**: Never use `--fake` in production without understanding the consequences!

---

### Issue: Database Performance Slow

**Symptoms**:
- Queries taking >1 second
- Pagination slow on large datasets

**Cause**: Missing indexes or inefficient queries

**Solution**:

1. **Check indexes exist**:
```sql
-- Connect to database
psql -U postgres -d medical_imaging

-- List indexes
\di

-- Expected indexes:
-- studies_study_exam_status_order_datetime_idx
-- studies_study_exam_source_order_datetime_idx
-- studies_study_patient_name_idx
-- studies_study_exam_item_idx
```

2. **Recreate indexes if missing**:
```bash
python manage.py migrate studies --fake
python manage.py sqlmigrate studies 0001 | psql -U postgres -d medical_imaging
```

3. **Analyze query performance**:
```python
# Django shell
python manage.py shell

>>> from django.db import connection
>>> from django.test.utils import CaptureQueriesContext
>>> with CaptureQueriesContext(connection) as ctx:
...     # Your query here
...     pass
>>> for q in ctx.captured_queries:
...     print(q['sql'])
...     print(q['time'])
```

4. **Enable PostgreSQL query logging**:
```sql
-- In psql
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();

-- Check logs
tail -f /var/log/postgresql/postgresql-14-main.log
```

---

## API Issues

### Issue: 404 Study Not Found

**Symptoms**:
```json
{
  "detail": "Study with exam_id 'EXAM001' not found"
}
```

**Cause**: Study doesn't exist or exam_id is incorrect

**Solution**:

1. **Verify exam_id exists**:
```bash
# Django shell
python manage.py shell

>>> from studies.models import Study
>>> Study.objects.filter(exam_id='EXAM001').exists()
False  # Not found

>>> # List all exam_ids
>>> Study.objects.values_list('exam_id', flat=True)[:10]
```

2. **Check database directly**:
```sql
psql -U postgres -d medical_imaging

SELECT exam_id, patient_name
FROM medical_examinations_fact
WHERE exam_id LIKE 'EXAM%'
LIMIT 10;
```

3. **Import data if empty**:
```bash
# Run DuckDB migration
export DUCKDB_PATH=../backend/medical_imaging.duckdb
python scripts/migrate_from_duckdb.py
```

---

### Issue: 422 Validation Error

**Symptoms**:
```json
{
  "detail": [
    {
      "loc": ["query", "patient_age_min"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

**Cause**: Invalid query parameter type or value

**Solution**:

1. **Check parameter types**:
```bash
# Correct
GET /api/v1/studies/search?patient_age_min=30

# Incorrect
GET /api/v1/studies/search?patient_age_min=thirty
```

2. **Common validation rules**:
- `patient_age_min/max`: Integer, 0-150
- `limit`: Integer, 1-100
- `offset`: Integer, ≥0
- `start_date/end_date`: String, YYYY-MM-DD format
- Array parameters: Use bracket notation `patient_gender[]=M`

3. **Test with cURL**:
```bash
curl -X GET "http://localhost:8001/api/v1/studies/search?patient_age_min=30&patient_age_max=50"
```

---

### Issue: Empty Search Results

**Symptoms**:
```json
{
  "items": [],
  "count": 0,
  "filters": {...}
}
```

**Cause**: Filters too restrictive or no matching data

**Solution**:

1. **Remove filters one by one**:
```bash
# Start broad
GET /api/v1/studies/search

# Add filters incrementally
GET /api/v1/studies/search?exam_status=completed
GET /api/v1/studies/search?exam_status=completed&exam_source=CT
```

2. **Check available filter values**:
```bash
GET /api/v1/studies/filters/options

# Response shows all available values
{
  "exam_statuses": ["completed", "pending", "cancelled"],
  "exam_sources": ["CT", "MRI", "X-ray"],
  ...
}
```

3. **Verify text search**:
```bash
# Text search is case-insensitive and partial
GET /api/v1/studies/search?q=張  # Finds "張偉", "張三"
```

---

### Issue: CORS Errors in Browser

**Symptoms**:
```
Access to fetch at 'http://localhost:8001/api/v1/studies/search' from origin
'http://localhost:3000' has been blocked by CORS policy
```

**Cause**: Frontend origin not in CORS_ALLOWED_ORIGINS

**Solution**:

1. **Check current CORS settings** in `config/settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5173',
]
```

2. **Add your frontend origin**:
```python
# For development
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:8080',  # Add your frontend port
]
```

3. **For development only** (not production):
```python
# In settings.py
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
```

4. **Restart Django server** after changes:
```bash
python manage.py runserver 8001
```

---

## Performance Issues

### Issue: Slow API Response Times

**Symptoms**:
- API requests taking >1 second
- Pagination slow
- Frontend feels sluggish

**Cause**: Database queries not optimized or cache not working

**Solution**:

1. **Check query performance**:
```bash
# Enable request timing logging (already enabled in middleware)
# Check logs for request duration
tail -f debug.log | grep "Request processed"

# Example output:
# INFO Request processed in 1234.56ms: GET /api/v1/studies/search
```

2. **Verify cache is working**:
```python
# Django shell
python manage.py shell

>>> from django.core.cache import cache
>>> cache.set('test', 'value', 60)
>>> cache.get('test')
'value'  # Should return 'value', not None
```

3. **Check cache backend** in `.env`:
```bash
# Development: local memory (fast)
CACHE_BACKEND=locmem

# Production: Redis (scalable)
CACHE_BACKEND=redis
REDIS_URL=redis://127.0.0.1:6379/1
```

4. **Enable PostgreSQL query analysis**:
```sql
-- In psql
EXPLAIN ANALYZE
SELECT * FROM medical_examinations_fact
WHERE exam_status = 'completed'
ORDER BY order_datetime DESC
LIMIT 20;
```

5. **Optimize specific slow queries**:
```python
# Use select_related for foreign keys (if added in future)
# Use prefetch_related for many-to-many (if added in future)
# Use .only() to fetch fewer fields
# Use .values() for raw data without model overhead
```

---

### Issue: High Memory Usage

**Symptoms**:
- Python process using >1GB RAM
- Server becomes unresponsive
- Out of memory errors

**Cause**: Large result sets or memory leaks

**Solution**:

1. **Limit query result sizes**:
```python
# In services.py
from .config import ServiceConfig

# Max limit enforced
if limit > ServiceConfig.MAX_PAGE_SIZE:
    limit = ServiceConfig.MAX_PAGE_SIZE  # 100
```

2. **Use pagination properly**:
```bash
# Good: Paginated requests
GET /api/v1/studies/search?limit=20&offset=0

# Bad: Requesting all data
GET /api/v1/studies/search?limit=10000
```

3. **Monitor memory usage**:
```bash
# Linux/macOS
ps aux | grep python

# Windows
tasklist | findstr python
```

4. **Use iterator for large datasets**:
```python
# If processing many records
for study in Study.objects.iterator(chunk_size=1000):
    process(study)
```

---

## Testing Issues

### Issue: Tests Failing After Code Changes

**Symptoms**:
```
FAILED tests/test_services.py::TestStudyService::test_search_with_filters
```

**Cause**: Code changes broke existing functionality

**Solution**:

1. **Run tests with verbose output**:
```bash
python manage.py test tests --verbosity=2
```

2. **Run specific test module**:
```bash
python manage.py test tests.test_services
```

3. **Run single test**:
```bash
python manage.py test tests.test_services.TestStudyService.test_search_with_filters
```

4. **Check test database**:
```python
# In test file
def test_example(self):
    from django.db import connection
    print(f"Using database: {connection.settings_dict['NAME']}")
    # Should be: test_medical_imaging
```

5. **Reset test database** if corrupted:
```bash
python manage.py flush --database=test
python manage.py migrate --database=test
```

---

### Issue: Tests Pass Locally But Fail in CI

**Symptoms**:
- Tests pass on developer machine
- Tests fail in GitHub Actions or CI/CD

**Cause**: Environment differences (Python version, database, dependencies)

**Solution**:

1. **Match CI environment locally**:
```bash
# Use same Python version as CI
uv venv --python 3.11

# Use same dependencies (frozen versions)
uv sync
```

2. **Check CI logs**:
```bash
# Look for version mismatches
python --version
uv pip list
```

3. **Use same database version**:
```bash
# CI might use PostgreSQL 14, ensure local matches
psql --version
```

4. **Run tests in Docker** (matches CI):
```bash
docker run --rm -it \
  -v $(pwd):/app \
  -w /app \
  python:3.11 \
  bash -c "pip install uv && uv sync && python manage.py test"
```

---

### Issue: Coverage Reports Incorrect

**Symptoms**:
```
Coverage: 45% (expected ~85%)
```

**Cause**: Not measuring correct source directory

**Solution**:

```bash
# Correct: Specify source directory
coverage run --source='studies' manage.py test tests
coverage report

# Generate HTML report
coverage html
# Open htmlcov/index.html in browser

# Check which files are included
coverage report --skip-covered
```

---

## Deployment Issues

### Issue: Static Files Not Found (404)

**Symptoms**:
```
GET /static/admin/css/base.css 404
```

**Cause**: Static files not collected

**Solution**:

```bash
# Collect static files
python manage.py collectstatic --noinput

# Verify STATIC_ROOT in settings.py
python manage.py shell
>>> from django.conf import settings
>>> print(settings.STATIC_ROOT)
/app/staticfiles
```

---

### Issue: DEBUG=False Causes 500 Errors

**Symptoms**:
- Works fine with DEBUG=True
- Returns generic 500 error with DEBUG=False

**Cause**: Missing ALLOWED_HOSTS or SECRET_KEY

**Solution**:

1. **Set ALLOWED_HOSTS** in `.env`:
```bash
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

2. **Generate secure SECRET_KEY**:
```python
# Django shell
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

3. **Update `.env`**:
```bash
DJANGO_SECRET_KEY=your-generated-secret-key
DEBUG=False
```

4. **Check logs** for actual error:
```bash
tail -f /var/log/django/error.log
```

---

### Issue: Port 8001 Already in Use

**Symptoms**:
```
Error: That port is already in use.
```

**Cause**: Another process using port 8001

**Solution**:

```bash
# Find process using port
# Windows
netstat -ano | findstr :8001

# macOS/Linux
lsof -i :8001

# Kill process
# Windows
taskkill /PID <process_id> /F

# macOS/Linux
kill -9 <process_id>

# Or use different port
python manage.py runserver 8002
```

---

## UV Package Manager Issues

### Issue: "uv sync" vs "pip install"

**Important**: This project uses UV, not pip!

**Symptoms**:
```
# User mistakenly uses pip
pip install django

# Pollutes local environment
```

**Solution**:

```bash
# ❌ WRONG - Don't use pip
pip install package

# ✅ CORRECT - Use UV
uv add package

# ✅ Install all dependencies
uv sync

# ✅ Add development dependency
uv add --dev pytest

# ✅ Remove package
uv remove package
```

**If you already used pip**:
```bash
# Remove pip-installed packages
pip freeze > to_remove.txt
pip uninstall -r to_remove.txt -y

# Clean environment
rm -rf .venv  # Remove virtual environment

# Reinstall with UV
uv sync
```

---

### Issue: UV Lock File Conflicts

**Symptoms**:
```
error: Failed to resolve dependencies
Caused by: conflicting requirements
```

**Cause**: `uv.lock` out of sync with `pyproject.toml`

**Solution**:

```bash
# Update lock file
uv lock

# Force reinstall
uv sync --reinstall

# If still fails, remove lock and regenerate
rm uv.lock
uv sync
```

---

### Issue: UV Cache Corruption

**Symptoms**:
```
error: Failed to download: checksum mismatch
```

**Cause**: Corrupted UV cache

**Solution**:

```bash
# Clear UV cache
uv cache clean

# Reinstall
uv sync

# If needed, clear specific package
uv cache clean <package-name>
```

---

## Cache Issues

### Issue: Cache Not Working

**Symptoms**:
- Filter options query database every time
- No performance improvement from caching

**Cause**: Cache backend misconfigured or Redis not running

**Solution**:

1. **Test cache manually**:
```python
# Django shell
python manage.py shell

>>> from django.core.cache import cache
>>> cache.set('test_key', 'test_value', 60)
>>> result = cache.get('test_key')
>>> print(result)
test_value  # Should print 'test_value', not None
```

2. **Check cache backend** in settings:
```python
# Development
CACHE_BACKEND = 'locmem'  # Local memory

# Production
CACHE_BACKEND = 'redis'
REDIS_URL = 'redis://127.0.0.1:6379/1'
```

3. **If using Redis, verify it's running**:
```bash
# Check Redis status
redis-cli ping
# Should return: PONG

# If not running
# Windows: Start Redis service
net start Redis

# macOS
brew services start redis

# Linux
sudo systemctl start redis
```

4. **Clear cache manually**:
```python
# Django shell
from django.core.cache import cache
cache.clear()
```

---

### Issue: Stale Cache Data

**Symptoms**:
- Filter options don't update after data changes
- New studies not appearing in searches

**Cause**: Cache TTL too long or cache not invalidated

**Solution**:

1. **Check cache TTL** in `services.py`:
```python
# Cache timeout for filter options
cache.set(cache_key, options, timeout=86400)  # 24 hours
```

2. **Clear cache after data changes**:
```python
# Django shell or management command
from django.core.cache import cache
cache.delete('filter_options')
```

3. **Implement cache invalidation**:
```python
# In services.py, after bulk import
def import_studies_from_duckdb(conn):
    # ... import logic ...
    # Invalidate filter cache after import
    cache.delete('filter_options')
```

---

## Debug Mode

### Enable Debug Logging

**For API Issues**:

1. **Edit `config/settings.py`**:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG',
    },
    'loggers': {
        'studies': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',  # Log all SQL queries
        },
    },
}
```

2. **View logs**:
```bash
# Real-time monitoring
tail -f debug.log

# Filter for specific errors
grep ERROR debug.log

# Filter for slow queries
grep "Request processed" debug.log | awk '$5 > 1000'
```

---

### Django Shell Debugging

```python
# Start Django shell
python manage.py shell

# Import models and services
from studies.models import Study
from studies.services import StudyService

# Test queries
studies = StudyService.get_studies_queryset(exam_status='completed')
print(studies.query)  # See generated SQL

# Check database connection
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM medical_examinations_fact")
    print(cursor.fetchone())
```

---

### Interactive Debugging with pdb

```python
# Add to code where you want to debug
import pdb; pdb.set_trace()

# Or use ipdb for better interface (add to dev dependencies)
# uv add --dev ipdb
import ipdb; ipdb.set_trace()

# When breakpoint hits:
# n - next line
# s - step into
# c - continue
# p variable - print variable
# l - list code
# q - quit
```

---

## Getting Help

If you can't resolve an issue:

1. **Check logs**:
   - `debug.log` - Application logs
   - PostgreSQL logs - Database errors
   - Browser console - Frontend errors

2. **Enable verbose mode**:
   ```bash
   python manage.py runserver 8001 --verbosity 3
   ```

3. **Run health check**:
   ```bash
   curl http://localhost:8001/api/v1/health
   ```

4. **Review documentation**:
   - `docs/DEVELOPMENT_SETUP.md` - Setup guide
   - `docs/API_REFERENCE.md` - API documentation
   - `docs/README.zh-TW.md` or `docs/README.en.md` - Project overview

5. **Report issue**:
   - Include: Django version, Python version, OS
   - Provide: Error message, steps to reproduce
   - Attach: Relevant log excerpts

---

**Last Updated**: 2025-11-10
**Maintained By**: Medical Imaging Team
**Version**: 1.1.0
