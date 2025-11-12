# Client Migration Guide - API v1.1.0

**Pagination Model Migration**: limit/offset → page/page_size

**Status**: Complete
**Updated**: 2025-11-12
**API Version**: 1.1.0

---

## Overview

The Medical Imaging Data Platform Report API v1.1.0 introduces a new, more intuitive pagination model replacing the legacy limit/offset approach. This guide helps developers migrate existing client code to the new model.

### Why Change?

| Aspect | Old Model (limit/offset) | New Model (page/page_size) |
|--------|----------------------|------------------------|
| User Intuitive | ❌ Offset not user-facing | ✅ Pages are intuitive |
| UI Implementation | Requires math | Simple numbered buttons |
| Mobile-Friendly | Complex calculations | Natural pagination controls |
| Error-Prone | Easy to miscalculate offset | Automatic clamping |
| API Clarity | offset parameter confusing | page number clear |

### Key Changes

- **Old**: `GET /api/v1/reports/search?limit=20&offset=100`
- **New**: `GET /api/v1/reports/search/paginated?page=6&page_size=20`

Same data (items 100-119), clearer intent.

---

## Understanding the Models

### Old Model: limit/offset (Deprecated)

```
limit:  Number of items to return
offset: Starting position (0-indexed)

Example:
limit=20, offset=100
Returns: Items 100-119 (20 items starting at position 100)
```

**Problems**:
- UI needs to display offset (confusing for users)
- Users think in pages, not offsets
- Requires calculation: offset = (page - 1) * limit
- Error-prone: easy to skip items or create duplicates

### New Model: page/page_size (Recommended)

```
page:      Page number (1-indexed)
page_size: Items per page

Example:
page=6, page_size=20
Returns: Items 100-119 (6th page with 20 items per page)

Calculation: offset = (page - 1) * page_size = (6-1) * 20 = 100
```

**Advantages**:
- Natural pagination (Page 1, Page 2, Page 3...)
- Users understand page numbers
- Automatic validation and clamping
- Clearer intent in code

---

## Migration Formulas

### Convert offset to page

```
new_page = (old_offset / old_limit) + 1
new_page_size = old_limit
```

**Examples**:

| Old Parameters | New Parameters | Items Returned |
|---|---|---|
| limit=10, offset=0 | page=1, page_size=10 | 0-9 |
| limit=10, offset=10 | page=2, page_size=10 | 10-19 |
| limit=10, offset=50 | page=6, page_size=10 | 50-59 |
| limit=20, offset=100 | page=6, page_size=20 | 100-119 |
| limit=50, offset=0 | page=1, page_size=50 | 0-49 |

### Convert page to offset (reverse)

```
new_offset = (page - 1) * page_size
new_limit = page_size
```

---

## Language-Specific Migration Examples

### JavaScript / TypeScript

#### Old Code (Deprecated)
```javascript
// Using old limit/offset model
async function fetchReports(query, limit = 20, offset = 0) {
  const response = await fetch(
    `/api/v1/reports/search?q=${query}&limit=${limit}&offset=${offset}`
  );
  return response.json();
}

// Usage with pagination
let offset = 0;
const limit = 20;

// Get page 1 (offset 0)
let reports = await fetchReports('COVID', limit, offset);

// Get page 2 (offset 20)
offset += limit;
reports = await fetchReports('COVID', limit, offset);

// Get page 3 (offset 40)
offset += limit;
reports = await fetchReports('COVID', limit, offset);
```

#### New Code (Recommended)
```javascript
// Using new page/page_size model
async function fetchReports(query, page = 1, pageSize = 20) {
  const response = await fetch(
    `/api/v1/reports/search/paginated?q=${query}&page=${page}&page_size=${pageSize}`
  );
  const data = await response.json();
  return {
    items: data.items,
    totalPages: data.pages,
    currentPage: data.page,
    total: data.total
  };
}

// Usage with pagination
const pageSize = 20;

// Get page 1
let result = await fetchReports('COVID', 1, pageSize);
console.log(`Page 1 of ${result.totalPages}`);

// Get page 2
result = await fetchReports('COVID', 2, pageSize);
console.log(`Page 2 of ${result.totalPages}`);

// Get page 3
result = await fetchReports('COVID', 3, pageSize);
console.log(`Page 3 of ${result.totalPages}`);
```

#### React Component Migration

**Old Component**:
```javascript
import React, { useState, useEffect } from 'react';

export function ReportList({ query }) {
  const [reports, setReports] = useState([]);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  useEffect(() => {
    fetch(`/api/v1/reports/search?q=${query}&limit=${limit}&offset=${offset}`)
      .then(r => r.json())
      .then(setReports);
  }, [query, offset, limit]);

  return (
    <div>
      <ul>
        {reports.map(r => <li key={r.uid}>{r.title}</li>)}
      </ul>

      <button onClick={() => setOffset(offset - limit)}>← Previous</button>
      <span>Offset: {offset}</span>
      <button onClick={() => setOffset(offset + limit)}>Next →</button>
    </div>
  );
}
```

**New Component** (Much cleaner):
```javascript
import React, { useState, useEffect } from 'react';

export function ReportList({ query }) {
  const [data, setData] = useState({ items: [], page: 1, pages: 0 });
  const pageSize = 20;

  useEffect(() => {
    fetch(`/api/v1/reports/search/paginated?q=${query}&page=${data.page}&page_size=${pageSize}`)
      .then(r => r.json())
      .then(setData);
  }, [query, data.page, pageSize]);

  return (
    <div>
      <ul>
        {data.items.map(r => <li key={r.uid}>{r.title}</li>)}
      </ul>

      <button
        onClick={() => setData({...data, page: data.page - 1})}
        disabled={data.page === 1}
      >
        ← Previous
      </button>

      <span>Page {data.page} of {data.pages}</span>

      <button
        onClick={() => setData({...data, page: data.page + 1})}
        disabled={data.page === data.pages}
      >
        Next →
      </button>
    </div>
  );
}
```

**Key improvements**:
- Page number is clear in UI
- Disabled buttons when at first/last page
- Response includes total pages
- No manual offset calculations

---

### Python

#### Old Code (Deprecated)
```python
import requests

def fetch_reports(query, limit=20, offset=0):
    """Fetch reports with old limit/offset model."""
    params = {
        'q': query,
        'limit': limit,
        'offset': offset
    }
    response = requests.get('/api/v1/reports/search', params=params)
    return response.json()

# Usage
limit = 20
offset = 0

# Page 1
reports = fetch_reports('COVID', limit, offset)

# Page 2
offset += limit
reports = fetch_reports('COVID', limit, offset)

# Page 3
offset += limit
reports = fetch_reports('COVID', limit, offset)
```

#### New Code (Recommended)
```python
import requests

def fetch_reports(query, page=1, page_size=20):
    """Fetch reports with new page/page_size model."""
    params = {
        'q': query,
        'page': page,
        'page_size': page_size
    }
    response = requests.get('/api/v1/reports/search/paginated', params=params)
    data = response.json()
    return {
        'items': data['items'],
        'total_pages': data['pages'],
        'current_page': data['page'],
        'total': data['total']
    }

# Usage - Much cleaner
page_size = 20

# Page 1
result = fetch_reports('COVID', page=1, page_size=page_size)
print(f"Page 1 of {result['total_pages']}")

# Page 2
result = fetch_reports('COVID', page=2, page_size=page_size)
print(f"Page 2 of {result['total_pages']}")

# Page 3
result = fetch_reports('COVID', page=3, page_size=page_size)
print(f"Page 3 of {result['total_pages']}")
```

#### Django Integration

**Old Django view**:
```python
from django.http import JsonResponse

def search_reports(request):
    query = request.GET.get('q', '')
    limit = int(request.GET.get('limit', 50))
    offset = int(request.GET.get('offset', 0))

    # Calculate items
    start = offset
    end = offset + limit
    reports = Report.objects.filter(title__icontains=query)[start:end]

    return JsonResponse([...])
```

**New Django view** (or integrate directly with our API):
```python
from django.http import JsonResponse

def search_reports_paginated(request):
    query = request.GET.get('q', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))

    # Our API handles this now
    # Just use the new endpoint directly
    from studies.report_api import search_reports_paginated
    return search_reports_paginated(request, q=query, page=page, page_size=page_size)
```

---

### cURL Examples

#### Old API (Deprecated)
```bash
# Get first 20 items
curl "http://localhost:8000/api/v1/reports/search?q=COVID&limit=20&offset=0"

# Get next 20 items
curl "http://localhost:8000/api/v1/reports/search?q=COVID&limit=20&offset=20"

# Get items 40-59
curl "http://localhost:8000/api/v1/reports/search?q=COVID&limit=20&offset=40"
```

#### New API (Recommended)
```bash
# Get page 1 (same as offset 0, limit 20)
curl "http://localhost:8000/api/v1/reports/search/paginated?q=COVID&page=1&page_size=20"

# Get page 2 (same as offset 20, limit 20)
curl "http://localhost:8000/api/v1/reports/search/paginated?q=COVID&page=2&page_size=20"

# Get page 3 (same as offset 40, limit 20)
curl "http://localhost:8000/api/v1/reports/search/paginated?q=COVID&page=3&page_size=20"
```

---

## Pagination Implementation Patterns

### Pattern 1: Simple Sequential Navigation

**Use Case**: Basic previous/next buttons

```javascript
const [page, setPage] = useState(1);
const [totalPages, setTotalPages] = useState(0);

const fetchPage = async (pageNum) => {
  const response = await fetch(
    `/api/v1/reports/search/paginated?page=${pageNum}&page_size=20`
  );
  const data = await response.json();
  setPage(data.page);
  setTotalPages(data.pages);
};

return (
  <div>
    <button onClick={() => fetchPage(page - 1)} disabled={page === 1}>
      Previous
    </button>
    <span>Page {page} of {totalPages}</span>
    <button onClick={() => fetchPage(page + 1)} disabled={page === totalPages}>
      Next
    </button>
  </div>
);
```

### Pattern 2: Numbered Page Buttons

**Use Case**: Show multiple page numbers like Google

```javascript
const [page, setPage] = useState(1);
const [totalPages, setTotalPages] = useState(0);

const getPageNumbers = () => {
  const pages = [];
  const start = Math.max(1, page - 2);
  const end = Math.min(totalPages, page + 2);

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }
  return pages;
};

return (
  <div>
    {getPageNumbers().map(p => (
      <button
        key={p}
        onClick={() => setPage(p)}
        style={{fontWeight: p === page ? 'bold' : 'normal'}}
      >
        {p}
      </button>
    ))}
  </div>
);
```

### Pattern 3: Infinite Scroll

**Use Case**: Load more data as user scrolls

```javascript
const [page, setPage] = useState(1);
const [allReports, setAllReports] = useState([]);

const loadMore = async () => {
  const response = await fetch(
    `/api/v1/reports/search/paginated?page=${page + 1}&page_size=20`
  );
  const data = await response.json();

  setAllReports([...allReports, ...data.items]);
  setPage(data.page);
};

// Usage with Intersection Observer
useEffect(() => {
  const observer = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) {
      loadMore();
    }
  });

  observer.observe(loadMoreElement);
}, []);
```

---

## Common Migration Mistakes

### ❌ Mistake 1: Forgetting page is 1-indexed

```javascript
// WRONG - This won't work
const page = Math.floor(offset / pageSize); // Returns 0 for offset 0!

// CORRECT - Add 1 to convert from 0-indexed offset
const page = Math.floor(offset / pageSize) + 1;
```

### ❌ Mistake 2: Not clamping page_size

```javascript
// WRONG - Might request invalid page size
const response = await fetch(
  `/api/v1/reports/search/paginated?page=1&page_size=${userInput}`
);

// CORRECT - Clamp to valid range [1, 100]
const pageSize = Math.max(1, Math.min(userInput, 100));
const response = await fetch(
  `/api/v1/reports/search/paginated?page=1&page_size=${pageSize}`
);
```

### ❌ Mistake 3: Using page 0

```javascript
// WRONG - Page 0 doesn't exist
const response = await fetch(
  `/api/v1/reports/search/paginated?page=0&page_size=20`
); // Returns 422 error

// CORRECT - Page starts at 1
const page = Math.max(1, userPage);
```

### ❌ Mistake 4: Not checking totalPages before next

```javascript
// WRONG - Can request beyond last page
const nextPage = currentPage + 1;
fetch(`/api/v1/reports/search/paginated?page=${nextPage}`); // Might return 0 items

// CORRECT - Check against totalPages from response
const nextPage = currentPage + 1;
if (nextPage <= totalPages) {
  fetch(`/api/v1/reports/search/paginated?page=${nextPage}`);
}
```

---

## Backward Compatibility

### During Transition (v1.1.0)

Both endpoints are available:

| Endpoint | Status | Note |
|----------|--------|------|
| `/reports/search` | ⚠️ Deprecated | Legacy limit/offset |
| `/reports/search/paginated` | ✅ Recommended | New page/page_size |

### Timeline

- **Now (v1.1.0)**: Both endpoints work
- **v1.2.0 (planned)**: Legacy endpoint still available but deprecated warnings shown
- **v2.0.0 (planned)**: Legacy endpoint removed

### Migration Timeline Recommendation

1. **Week 1-2**: Test new paginated endpoint in development
2. **Week 3**: Update production to use new endpoint
3. **After v1.2.0**: No rush, legacy endpoint still works
4. **Before v2.0.0**: All clients should migrate

---

## Performance Comparison

### Response Times (Phase 5.3 Benchmarks)

Both models have identical performance - the calculation method doesn't affect API speed.

| Page Size | Old Model | New Model | Notes |
|-----------|-----------|-----------|-------|
| limit=10 | ~50ms | ~50ms | Same query |
| limit=50 | ~150ms | ~150ms | Same query |
| limit=100 | ~250ms | ~250ms | Same query |

**Conclusion**: Choose based on UX, not performance.

---

## Testing Your Migration

### Test Checklist

- [ ] First page loads correctly
- [ ] Pagination buttons appear
- [ ] Previous button disabled on page 1
- [ ] Next button disabled on last page
- [ ] Can navigate to middle pages
- [ ] Page number displays correctly
- [ ] Total count matches old API
- [ ] Items don't duplicate between pages
- [ ] Items don't skip between pages

### Test Cases

```javascript
// Test 1: Page 1 works
async function testPage1() {
  const response = await fetch(`/api/v1/reports/search/paginated?q=test&page=1&page_size=10`);
  const data = await response.json();
  assert(data.items.length === 10);
  assert(data.page === 1);
  assert(data.pages > 0);
}

// Test 2: Page 2 continues from page 1
async function testPageContinuity() {
  const page1 = await fetch(`/api/v1/reports/search/paginated?q=test&page=1&page_size=10`).then(r => r.json());
  const page2 = await fetch(`/api/v1/reports/search/paginated?q=test&page=2&page_size=10`).then(r => r.json());

  const page1LastId = page1.items[9].uid;
  const page2FirstId = page2.items[0].uid;

  // Should be different
  assert(page1LastId !== page2FirstId);
}

// Test 3: Page size clamping
async function testPageSizeClamping() {
  const response = await fetch(`/api/v1/reports/search/paginated?page=1&page_size=500`);
  const data = await response.json();

  // Should be clamped to 100
  assert(data.page_size === 100);
  assert(data.items.length <= 100);
}
```

---

## Support & Resources

### Documentation
- Full API Docs: `API_DOCUMENTATION.md`
- Performance Analysis: `claudedocs/PHASE_5.3_PERFORMANCE_BENCHMARKS.md`
- Test Suite: `studies/tests.py` (43 tests)

### Migration Support

**Questions?** Check the test suite in `studies/tests.py`:
- Integration tests show all valid pagination patterns
- Performance tests show performance characteristics

---

## Summary

### What Changed
- Old model: `limit` and `offset` parameters
- New model: `page` and `page_size` parameters

### Why It's Better
- More intuitive for users
- Simpler UI implementation
- Automatic validation and clamping
- Clearer code intent

### How to Migrate
1. Convert offset to page: `page = (offset / limit) + 1`
2. Replace `limit` with `page_size`
3. Use `/reports/search/paginated` endpoint

### When to Migrate
- **Now**: Start testing in development
- **v1.2.0**: Legacy warnings appear
- **v2.0.0**: Legacy endpoint removed

---

**Last Updated**: 2025-11-12
**API Version**: 1.1.0
**Status**: Complete and Ready for Production
