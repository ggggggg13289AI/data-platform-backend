# Zero-Downtime Deployment Strategy
**Status**: 🎯 Plan to keep old API running while deploying new Django API
**Principle**: Never break existing sessions - switch gradually, verify compatibility

---

## The Problem

**Scenario**:
- FastAPI running on http://localhost:8000
- Building Django on same port
- Switch over → Frontend breaks for hours
- Users refresh → 404 errors
- Medical appointments missed

**Solution**: Keep both systems running during transition, route gradually.

---

## Architecture During Migration

```
┌─────────────────────────────────────────────────────────┐
│ Frontend (React)                                        │
│ - Cached API responses from FastAPI                     │
│ - Some users might have old token                       │
└────────┬────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────┐
│ API Router/Proxy (nginx)                                │
│ - Routes to FastAPI or Django based on request version  │
│ - Handles DNS/port switching                            │
└──┬──────────────────────────────────────────────────────┘
   │
   ├──────────────────┬─────────────────────────────┐
   ↓                  ↓                             ↓
FastAPI (8000)      Django (8001)            Fallback (8002)
Old API             New API                  If both fail
Ready               Staging
```

---

## Deployment Phases

### Phase 1: Prepare (Days 1-5)
**Goal**: Django ready on separate port, all endpoints implemented

**Steps**:
1. Build Django on http://localhost:8001
2. Migrate data from DuckDB → PostgreSQL (via `manage.py migrate_from_duckdb`)
3. Test all endpoints return EXACT same format as FastAPI
4. Verify no 404 errors

**User Impact**: None - FastAPI still running on 8000

### Phase 2: Validation (Day 6)
**Goal**: Verify Django handles all production traffic patterns

**Steps**:
1. Run both FastAPI and Django simultaneously
2. Run integration tests on BOTH:
   ```bash
   # Test FastAPI on 8000
   curl http://localhost:8000/api/v1/studies/search

   # Test Django on 8001
   curl http://localhost:8001/api/v1/studies/search

   # Compare responses - MUST be identical
   ```
3. Load test Django (100 concurrent requests)
4. Check performance (should be similar or better)

**User Impact**: None - Still using FastAPI

### Phase 3: Gradual Migration (Day 7)
**Goal**: Switch users gradually from FastAPI to Django

**Option A: Frontend Env Variable Switch** (Simplest)
```javascript
// config.js
const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api/v1';

// In .env:
// REACT_APP_API_BASE=http://localhost:8001/api/v1  ← Django
// REACT_APP_API_BASE=http://localhost:8000/api/v1  ← FastAPI
```

**Steps**:
1. Change frontend `.env`: `REACT_APP_API_BASE=http://localhost:8001`
2. Rebuild frontend: `npm run build`
3. Deploy frontend
4. Monitor for errors in real-time
5. If errors: Revert to 8000, fix, try again
6. If success: Keep running for 24 hours, monitor

**User Impact**: 30-second rebuild + new static files sent to browser

**Option B: API Gateway/Proxy** (More robust)

Use nginx to route requests, switch backend without frontend change:

```nginx
# /etc/nginx/sites-available/medical-api

upstream fastapi {
    server localhost:8000;
}

upstream django {
    server localhost:8001;
}

server {
    listen 8080;
    server_name localhost;

    location /api/v1/ {
        # Route to FastAPI by default
        proxy_pass http://fastapi;

        # Fallback to Django if FastAPI returns error
        proxy_next_upstream error timeout http_502 http_503;
        proxy_pass http://django;
    }

    # Monitoring endpoint
    location /health {
        return 200 "API Proxy OK";
    }
}
```

Frontend uses: `http://localhost:8080/api/v1/` (unchanged)

**Advantages**:
- Switch backend without rebuilding frontend
- Automatic fallback if one system fails
- Can weight traffic: 90% FastAPI, 10% Django, gradually shift

**Configuration for gradual switch**:
```nginx
upstream django {
    server localhost:8001 weight=10;  # 10% of traffic
    server localhost:8000 weight=90;  # 90% of traffic (FastAPI)
}

# Later: flip weights
upstream django {
    server localhost:8001 weight=90;  # 90% of traffic
    server localhost:8000 weight=10;  # 10% (FastAPI fallback)
}

# Finally:
upstream django {
    server localhost:8001;            # 100%
}
```

---

## Rollback Strategy

**If Django deployment fails:**

### Option 1: Quick Revert (< 1 minute)
```bash
# Stop Django
pkill -f "python manage.py runserver"

# Confirm FastAPI is responding
curl http://localhost:8000/api/v1/studies/search

# Switch frontend back to FastAPI
# Change: REACT_APP_API_BASE=http://localhost:8000/api/v1
# Rebuild: npm run build
```

### Option 2: DNS Switch (< 30 seconds)
If using nginx proxy, just change `upstream django` server back to FastAPI.

```nginx
# Revert: route all traffic to FastAPI
upstream django {
    server localhost:8000;
}

# Reload nginx
sudo systemctl reload nginx
```

### Option 3: Database Rollback (if data was corrupted)
```bash
# Keep DuckDB backup before migration
cp medical_imaging.duckdb medical_imaging.duckdb.backup

# If PostgreSQL import fails:
# 1. Restore from backup
# 2. Check data integrity
# 3. Re-run migration script
```

---

## Monitoring During Cutover

### Real-Time Error Tracking
```bash
# Watch FastAPI logs
tail -f /var/log/fastapi.log | grep ERROR

# Watch Django logs
tail -f /var/log/django.log | grep ERROR

# Monitor both systems
watch -n 1 'curl -s http://localhost:8000/health && curl -s http://localhost:8001/health'
```

### Application Monitoring
```javascript
// In frontend, log all API errors
const apiClient = axios.create({
  baseURL: API_BASE,
});

apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error(`API Error: ${error.response?.status} ${error.config.url}`);
    // Send to monitoring service (Sentry, DataDog, etc.)
    reportError(error);
    throw error;
  }
);
```

### Key Metrics to Monitor
- **Response time**: Should be <500ms (similar to FastAPI)
- **Error rate**: Should be 0% (no 404s, 500s)
- **Database queries**: Should be <100ms
- **Concurrent users**: Can system handle peak load?

---

## Data Consistency During Cutover

**Critical**: Users might be on old FastAPI while others are on new Django.

**Scenario**:
```
User A (FastAPI): Creates analysis task → saved to DuckDB
User B (Django): Lists analysis tasks → reads from PostgreSQL
→ User B doesn't see User A's task!
```

**Solution: Dual-write during transition**

Option 1: Keep both databases in sync
```python
# During migration, write to BOTH databases:
# 1. Write to PostgreSQL (Django)
# 2. Write to DuckDB (FastAPI)
# Read from PostgreSQL (single source of truth)
```

Option 2: Read from PostgreSQL even in FastAPI
```python
# Temporarily modify FastAPI to read from PostgreSQL
# while users are being migrated
# (Shows that data is consistent across systems)
```

**Simplest approach**: Complete migration in <1 hour
- Stop taking new data (freeze period)
- Migrate PostgreSQL
- Switch frontend
- Resume operations

Users see brief "updating" message but no confusion.

---

## Detailed Cutover Procedure

### 30 Minutes Before Cutover

```bash
# 1. Final data verification
duckdb medical_imaging.duckdb
SELECT COUNT(*) FROM medical_examinations_fact;  # Note: 1250 records

# 2. Start Django
cd medical_imaging_django
python manage.py runserver 8001

# 3. Run data migration
python manage.py migrate_from_duckdb

# 4. Verify counts match
python manage.py shell
>>> from studies.models import Study
>>> Study.objects.count()  # Should be 1250

# 5. Test endpoints
curl http://localhost:8001/api/v1/studies/search
# Should return same format as FastAPI 8000

# 6. Start nginx proxy (if using)
sudo systemctl reload nginx
```

### Cutover Time (5-10 minutes)

```bash
# Option A: Update frontend env and redeploy
# File: .env
REACT_APP_API_BASE=http://localhost:8001/api/v1

npm run build
npm run preview  # Test locally first

# Then deploy to production

# Option B: Update nginx and reload
# File: /etc/nginx/sites-available/medical-api
upstream django {
    server localhost:8001 weight=100;
    server localhost:8000 weight=0;   # Fallback only
}

sudo systemctl reload nginx
```

### Post-Cutover (Next 24 hours)

```bash
# Monitor continuously
watch -n 5 'curl http://localhost:8001/health'

# Check error logs
tail -f /var/log/django.log

# Monitor user feedback
# If errors: Revert to FastAPI
# If success: Keep Django running
```

### After 24 Hours (Cleanup)

```bash
# If Django is stable:
# 1. Stop FastAPI
pkill -f uvicorn

# 2. Free up port 8000 (if needed)

# 3. Update frontend to use Django directly (no proxy)
# Remove nginx, point to http://localhost:8001

# 4. Archive DuckDB database as backup
tar -czf medical_imaging.duckdb.backup.tar.gz medical_imaging.duckdb
```

---

## Failure Scenarios & Recovery

| Scenario | Issue | Recovery |
|----------|-------|----------|
| Django returns 500 error | Code bug | Stop Django, revert to FastAPI 8000 |
| Database query slow | N+1 queries | Check Django ORM, add select_related/prefetch_related |
| 404 on some endpoints | Endpoint not implemented | Check Django router configuration |
| Data mismatch | Migration failed | Restore DuckDB, re-run migration script |
| Token validation fails | Auth system incompatibility | Check JWT token format in both systems |
| Pagination broken | Different offset calculation | Verify page/page_size math matches FastAPI |

---

## Verification Checklist (Before Final Switch)

- [ ] All endpoints implemented in Django
- [ ] Response format identical to FastAPI (test with curl)
- [ ] All required records migrated from DuckDB
- [ ] No duplicate exam_ids in PostgreSQL
- [ ] Pagination works correctly
- [ ] Filter options return all available values
- [ ] 404 responses formatted correctly
- [ ] Null values returned as null (not empty string)
- [ ] DateTime format is ISO 8601 (YYYY-MM-DDTHH:MM:SS)
- [ ] Load test passed (100+ concurrent requests)
- [ ] Error logging works
- [ ] Monitoring/observability in place
- [ ] Rollback procedure tested
- [ ] Team trained on monitoring during cutover

---

## Summary: The Safe Way to Switch

1. **Build Django** on separate port (8001) - Users unaffected
2. **Verify** response format matches FastAPI exactly - Zero surprises
3. **Migrate** data from DuckDB to PostgreSQL - Validate counts match
4. **Test** both systems running simultaneously - Confidence check
5. **Route gradually** using env var or nginx - Minimize risk
6. **Monitor** continuously for 24 hours - Catch issues early
7. **Rollback quickly** if needed - Old system is still running
8. **Cleanup** after stable - Remove old FastAPI

**Total downtime: 0 minutes** (users never see broken state)

---

**This is "Never Break Userspace" in practice.**
