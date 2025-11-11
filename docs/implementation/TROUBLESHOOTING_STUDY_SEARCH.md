# Study Search Frontend - Troubleshooting Guide

**Date**: 2025-11-07  
**Issue**: HTTP 404 errors when loading Study Search page  
**Status**: **Diagnosed and Solution Provided**

---

## 🔴 Issues Identified

### Primary Issue: Backend API Not Found (404)

**Error**: 
```
Failed to load resource: the server responded with a status of 404 (Not Found)
Endpoint: :8000/api/v1/studies/filters/options
Location: useStudySearch.ts:81
```

**Cause Analysis**:
1. ✅ Frontend is running (http://localhost:3000)
2. ✅ Frontend trying to reach backend (http://localhost:8000)
3. ❌ **Backend is NOT running or endpoint doesn't exist**

**Why This Happens**:
- Backend service (FastAPI or Django) is not started
- OR the `/api/v1/studies/filters/options` endpoint is not implemented
- `useFilterOptions` hook tries to load filter options on component mount
- No error handling fallback → entire page fails

### Secondary Issues: Deprecation Warnings

```
1. Ant Design Card: `bordered` is deprecated → use `variant` instead
2. React 19 compatibility: "antd v5 support React is 16 ~ 18"
3. Disabled prop with empty array
```

---

## 🛠️ Solution Steps

### Step 1: Start the Backend Service

**Check if backend is running**:
```bash
curl http://localhost:8000/api/v1/health
```

**If it returns `{"detail":"Not Found"}`, backend IS running but endpoint missing.**

**Start backend if not running**:

**Option A: FastAPI Backend**
```bash
cd backend
pip install -r requirements.txt
python run.py
# Should start on http://localhost:8000
```

**Option B: Django Backend**
```bash
cd backend_django
pip install -r requirements.txt
python manage.py runserver 8000
# Should start on http://localhost:8001 (different port!)
```

**Option C: Docker Compose (All Services)**
```bash
docker-compose up -d
# All services start automatically
```

### Step 2: Verify the Endpoint Exists

**Check if endpoint is implemented**:
```bash
# This should return filter options, not 404
curl http://localhost:8000/api/v1/studies/filters/options

# Expected response:
{
  "exam_statuses": ["completed", "pending", ...],
  "exam_sources": ["PAPA", "Red", ...],
  "exam_items": ["CT", "MRI", ...],
  "equipment_types": [...]
}
```

**If endpoint missing**: Check backend implementation

### Step 3: Update API Configuration (if needed)

**If Django is on port 8001 (not 8000)**:

Edit: `frontend/.env.local`
```env
VITE_API_BASE_URL=http://localhost:8001/api/v1
```

Then restart frontend:
```bash
cd frontend
npm run dev
```

### Step 4: Fix Deprecation Warnings

**Issue 1: Ant Design Card `bordered` deprecated**

**File**: `frontend/src/components/StudySearch/StudyDetailModal.tsx` or similar

```typescript
// ❌ OLD (deprecated)
<Card bordered={false}>
  Content
</Card>

// ✅ NEW (recommended)
<Card variant="borderless">
  Content
</Card>
```

**Issue 2: React 19 with Ant Design v5**

This is a version compatibility warning. Options:
1. Keep as-is (works fine, just warning)
2. Upgrade Ant Design to v6 (when stable)
3. Downgrade React to 18 (if needed for other reasons)

**Issue 3: Disabled prop with empty array**

Find the Select/Button with empty disabled array:
```typescript
// ❌ OLD
<Select disabled={[]}>

// ✅ NEW  
<Select disabled={false}>
// OR
<Select disabled={someCondition}>
```

---

## 🔍 Verification Checklist

After applying fixes, verify:

### Backend Status
- [ ] Backend service is running
  ```bash
  curl http://localhost:8000/api/v1/health
  # Should return: {"status":"ok"}
  ```

- [ ] Filter options endpoint works
  ```bash
  curl http://localhost:8000/api/v1/studies/filters/options
  # Should return JSON with exam_statuses, exam_sources, etc.
  ```

### Frontend Status
- [ ] Frontend loads without 404 errors
  - Open http://localhost:3000/study-search
  - Check browser console (F12)
  - Should see NO "Failed to load resource: 404" errors

- [ ] Study Search page renders
  - Should show search form with filters
  - Dropdown selects should be populated
  - No error messages in red alert box

- [ ] Search works
  - Enter search query
  - Click "Search" button
  - Results should load (or show "No studies found" if no data)

---

## 📋 Common Scenarios

### Scenario 1: "Backend not running on port 8000"

**Symptoms**:
- Connection refused errors
- Page hangs when loading

**Fix**:
```bash
# Start backend
docker-compose up -d backend

# OR
cd backend
python run.py

# OR
cd backend_django
python manage.py runserver
```

### Scenario 2: "Backend running but endpoint returns 404"

**Symptoms**:
- Backend is running (can reach health endpoint)
- Filter options endpoint returns 404

**Fix**:
```bash
# Check if endpoint is implemented in backend
# Look for: /api/v1/studies/filters/options

# Backend might be using different API structure
# Check documentation: docs/api/04_API_SPECIFICATION.md

# Or check actual backend code
cat backend/api/study_routes.py  # FastAPI
cat backend_django/studies/api.py  # Django
```

### Scenario 3: "Backend on different port (8001)"

**Symptoms**:
- 404 errors on :8000
- Backend actually running on :8001

**Fix**:
```env
# frontend/.env.local
VITE_API_BASE_URL=http://localhost:8001/api/v1
```

### Scenario 4: "Ant Design warnings"

**Symptoms**:
- Warnings in browser console
- Page still works fine

**Fix**:
- Replace deprecated props (see Step 4 above)
- These are just warnings, not breaking errors

---

## 🚀 Quick Start (All at Once)

If you want to get everything running quickly:

```bash
# Terminal 1: Start all Docker services
docker-compose up -d

# Wait 30 seconds for services to start

# Terminal 2: Verify backend
curl http://localhost:8000/api/v1/studies/filters/options

# Terminal 3: Start frontend dev server (if not in Docker)
cd frontend
npm run dev

# Access: http://localhost:3000/study-search
```

---

## 🔧 Debugging Steps

If still having issues, try these debugging steps:

### 1. Check Browser Console (F12)

Look for exact error messages:
```
Failed to load resource: :8000/api/v1/studies/filters/options
```

### 2. Check Backend Logs

```bash
# Docker
docker-compose logs backend

# OR direct Python
# Look for error messages when requests come in
```

### 3. Test API Manually

```bash
# Test each endpoint
curl http://localhost:8000/api/v1/studies/search?q=test
curl http://localhost:8000/api/v1/studies/filters/options
curl http://localhost:8000/api/v1/health
```

### 4. Check Frontend Code

**File**: `frontend/src/hooks/useStudySearch.ts` (line 81)

```typescript
const loadOptions = async () => {
  try {
    const result = await studyService.getFilterOptions()
    // This call fails with 404
  } catch (err) {
    console.error(errorMsg)  // ← Error logged here
  }
}
```

The error is caught and logged, then the component renders with empty filters.

---

## 📊 Network Request Flow

### How the page works:

```
1. Frontend loads (http://localhost:3000/study-search)
   ↓
2. StudySearch component mounts
   ↓
3. useFilterOptions hook runs
   ↓
4. Makes API call: GET /api/v1/studies/filters/options
   ↓
5. Backend receives request (should be on :8000 or :8001)
   ↓
6. Backend returns filter options (exam_statuses, exam_sources, etc.)
   ↓
7. Frontend renders dropdowns with options
   ↓
8. User can search

If ANY step fails:
→ 404 error
→ Filters not loaded
→ Page shows error
```

---

## 🎯 What Should Work After Fixing

✅ **Frontend**
- Study Search page loads without errors
- All dropdowns populated with filter options
- Search form functional

✅ **Backend**
- API endpoints respond with 200 status
- Filter options endpoint returns correct data
- Search endpoint accepts queries

✅ **Integration**
- Frontend and backend communicate successfully
- Data flows from backend to frontend
- No console errors

---

## 📚 Reference Documents

- **API Specification**: `docs/api/04_API_SPECIFICATION.md`
- **Frontend-Backend Integration**: `docs/architecture/FRONTEND_BACKEND_INTEGRATION.md`
- **Backend Setup**: `backend_django/README.md` or `backend/README.md`
- **Docker Setup**: `docker-compose.yml`

---

## 🆘 If Still Not Working

1. **Check Docker logs**: `docker-compose logs`
2. **Check API manually**: `curl http://localhost:8000/api/v1/health`
3. **Check environment**: `echo $VITE_API_BASE_URL`
4. **Check firewall**: Ensure ports 3000, 8000, 8001 are accessible
5. **Check code**: Review backend implementation of filter endpoint

---

## 📝 Summary

| Issue | Cause | Solution |
|-------|-------|----------|
| 404 on /studies/filters/options | Backend not running | Start backend service |
| Page shows error message | Endpoint missing in backend | Implement endpoint OR check port |
| Deprecation warnings | Old Ant Design syntax | Update component props |
| No data in dropdowns | Filter options not loaded | Verify API returns correct data |

---

**Status**: ✅ **Diagnosed**  
**Severity**: 🔴 **High** (blocks page from working)  
**Priority**: 🔥 **Urgent** (fix before proceeding)

**Quick Fix**: Start backend service with `docker-compose up -d` or appropriate startup command.

---

**Created**: 2025-11-07  
**For**: Image Data Platform Team  
**Purpose**: Guide for resolving Study Search page 404 errors
