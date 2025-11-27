# Frontend-Backend Integration Architecture

**Version**: v2.0.0  
**Last Updated**: 2025-11-07  
**Status**: Phase 1 - Study Search Implementation Complete

---

## 📋 Executive Summary

The Image Data Platform uses a **decoupled frontend-backend architecture** with:
- **Frontend**: React 18 + TypeScript + Ant Design (Port 3000)
- **Backend**: FastAPI + PostgreSQL or Django + PostgreSQL (Port 8000/8001)
- **AI Engine**: Ollama LLM service (Port 11434)
- **Data Source**: DuckDB (medical examination data) or PostgreSQL (persistent storage)

This document details the integration patterns, API contracts, and data flow between frontend and backend.

---

## 🏗️ System Architecture

### High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        User's Browser                             │
├──────────────────────────────────────────────────────────────────┤
│                  React Frontend (Port 3000)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐  │
│  │ Components  │  │ Pages        │  │ State Management        │  │
│  ├─ Auth       │  ├─ Login       │  │ (Zustand)               │  │
│  ├─ Search     │  ├─ Dashboard   │  └─────────────────────────┘  │
│  ├─ Table      │  ├─ StudySearch│                                │
│  ├─ Modal      │  └─ Projects    │  ┌─────────────────────────┐  │
│  └─ Forms      │                 │  │ HTTP Client (Axios)     │  │
│                │                 │  └──────────┬──────────────┘  │
└────────────────────────────────────────────────┼──────────────────┘
                                                │ HTTP/JSON
                                                │ (REST API)
                                                ▼
┌──────────────────────────────────────────────────────────────────┐
│          FastAPI Backend (Port 8000) OR Django (Port 8001)       │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ API Routes   │  │ Services     │  │ Data Validation         │ │
│  ├─ auth.py    │  ├─ study.py    │  │ (Pydantic schemas)      │ │
│  ├─ studies.py │  ├─ import.py   │  └─────────────────────────┘ │
│  ├─ export.py  │  └─ export.py   │                               │
│  └─ analysis.py│                 │  ┌─────────────────────────┐ │
│                │                 │  │ SQLAlchemy ORM           │ │
│                │                 │  │ (Model -> Query)         │ │
│                └─────────────────┼──┘                           │
└────────────────────────┬─────────────────────────────────────────┘
                         │ SQL
                         ▼
        ┌────────────────────────────────┐
        │  PostgreSQL Database           │
        │  ├─ studies                    │
        │  ├─ projects                   │
        │  ├─ users                      │
        │  └─ ai_annotations             │
        └────────────────────────────────┘

                         │ HTTP
                         ▼
        ┌────────────────────────────────┐
        │  Ollama LLM Service            │
        │  Port: 11434                   │
        │  Model: qwen2.5:7b             │
        └────────────────────────────────┘
```

---

## 📡 Communication Patterns

### 1. Request-Response Flow (Study Search Example)

```
1. User enters search query in React component
   ↓
2. Submit button triggers API call (Axios)
   POST /api/v1/studies/search
   {
     "q": "肺炎",
     "exam_status": "completed",
     "page": 1,
     "page_size": 20
   }
   ↓
3. Backend receives request (FastAPI route handler)
   ↓
4. Validate request (Pydantic schema)
   ↓
5. Call service method (StudyService.search_studies())
   ↓
6. Execute database query (SQLAlchemy)
   ↓
7. Return results to frontend
   {
     "data": [{ study1 }, { study2 }, ...],
     "total": 150,
     "page": 1,
     "page_size": 20,
     "filters": { ... }
   }
   ↓
8. Frontend receives JSON response
   ↓
9. React updates component state (Zustand store)
   ↓
10. UI re-renders with search results
```

### 2. Async Task Flow (AI Analysis Example)

```
Frontend                          Backend                    Ollama
   │                                │                          │
   ├─ POST /api/v1/analysis/  ──────>                          │
   │  { report_id, prompt }         │                          │
   │                                ├─ Start async task        │
   │                                │                          │
   │<─ 202 Accepted ────────────────┤                          │
   │  { task_id: "abc123" }         │                          │
   │                                ├─ Call Ollama API ───────>
   │                                │                          │
   │ (User sees loading state)      │                    (Process)
   │                                │                          │
   │ Poll: GET /api/v1/tasks/abc123 │                          │
   │                                │<─ Return result ────────┤
   │<─ { status: "complete", ... }──┤                          │
   │                                │                          │
   │ Update UI with results         │                          │
   ▼                                ▼                          ▼
```

---

## 🔌 API Endpoints

### Authentication

```
POST /api/v1/auth/login
  Input:  { email, password }
  Output: { access_token, token_type, user }

POST /api/v1/auth/logout
  Input:  (none)
  Output: { message: "Logged out successfully" }

GET /api/v1/auth/me
  Input:  (none, requires Authorization header)
  Output: { user_id, email, role, created_at }
```

### Studies (Search, Read, Filter)

```
GET /api/v1/studies/search
  Query Params:
    q (string, required): Search query
    exam_status (string, optional): Filter by status
    exam_source (string, optional): Filter by source
    exam_item (string, optional): Filter by exam type
    start_date (ISO8601, optional): Date range start
    end_date (ISO8601, optional): Date range end
    sort (string, default: order_datetime_desc)
    page (int, default: 1)
    page_size (int, default: 20, max: 100)
  
  Output: StudySearchResponse
    {
      "data": [StudyListItem, ...],
      "total": int,
      "page": int,
      "page_size": int,
      "filters": FilterOptions
    }

GET /api/v1/studies/{exam_id}
  Input:  exam_id (path parameter)
  Output: StudyDetail (complete study with all 19 fields)

GET /api/v1/studies/filters/options
  Input:  (none)
  Output: FilterOptions
    {
      "exam_statuses": [...],
      "exam_sources": [...],
      "exam_items": [...],
      "equipment_types": [...]
    }
```

### AI Analysis

```
POST /api/v1/analysis/single
  Input:  
    {
      "exam_id": "string",
      "analysis_type": "highlight|classification|extraction|scoring",
      "prompt": "string",
      "model": "qwen2.5:7b"
    }
  Output: AnalysisResult
    {
      "result": { ... },
      "confidence": float,
      "processing_time_ms": int,
      "model": "string"
    }

POST /api/v1/analysis/batch
  Input:
    {
      "exam_ids": [string, ...],
      "analysis_type": "highlight|classification|extraction|scoring",
      "prompt": "string"
    }
  Output: BulkAnalysisResponse
    {
      "task_id": "uuid",
      "status": "queued|processing|completed|failed",
      "total": int,
      "processed": int,
      "results": [...]
    }

GET /api/v1/analysis/tasks/{task_id}
  Input:  task_id (path parameter)
  Output: TaskStatus (poll for async results)
```

### Projects (Management)

```
GET /api/v1/projects
  Output: [Project, ...]

POST /api/v1/projects
  Input:  { name, description, tags }
  Output: Project

GET /api/v1/projects/{project_id}
  Output: ProjectDetail (with report count and stats)

PUT /api/v1/projects/{project_id}
  Input:  { name, description, tags }
  Output: Project

POST /api/v1/projects/{project_id}/studies
  Input:  { exam_ids: [string, ...], note: string }
  Output: { added_count: int }

GET /api/v1/projects/{project_id}/studies
  Output: [StudyListItem, ...]
```

### Data Export

```
GET /api/v1/export/studies
  Query Params:
    exam_ids: [string, ...] (optional - export selected)
    project_id: string (optional - export entire project)
    format: "excel|csv|json" (default: excel)
  
  Output: File download (Content-Disposition: attachment)
```

---

## 📊 Data Flow Examples

### Example 1: Study Search with Filters

**Frontend Code (React)**:
```typescript
// StudySearch.tsx
const [searchResults, setSearchResults] = useState([]);
const [loading, setLoading] = useState(false);

const handleSearch = async (filters) => {
  setLoading(true);
  try {
    const response = await axios.get('/api/v1/studies/search', {
      params: {
        q: filters.query,
        exam_status: filters.status,
        exam_source: filters.source,
        page: filters.page,
        page_size: 20
      }
    });
    setSearchResults(response.data);
  } finally {
    setLoading(false);
  }
};
```

**Backend Code (FastAPI)**:
```python
# api/study_routes.py
@router.get("/search")
async def search_studies(
    q: str,
    exam_status: Optional[str] = None,
    exam_source: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    service = StudyService(db)
    results = service.search_studies(
        q=q,
        exam_status=exam_status,
        exam_source=exam_source,
        page=page,
        page_size=page_size
    )
    return results
```

**Service Layer (Business Logic)**:
```python
# services/study_service.py
class StudyService:
    def search_studies(self, q, exam_status, exam_source, page, page_size):
        # Build query
        query = self.db.query(Study)
        
        # Full-text search
        if q:
            query = query.filter(
                or_(
                    Study.patient_name.ilike(f"%{q}%"),
                    Study.exam_description.ilike(f"%{q}%"),
                    Study.exam_item.ilike(f"%{q}%")
                )
            )
        
        # Filters
        if exam_status:
            query = query.filter(Study.exam_status == exam_status)
        if exam_source:
            query = query.filter(Study.exam_source == exam_source)
        
        # Pagination
        total = query.count()
        studies = query.offset((page - 1) * page_size).limit(page_size).all()
        
        return StudySearchResponse(
            data=[StudyListItem.from_orm(s) for s in studies],
            total=total,
            page=page,
            page_size=page_size,
            filters=self.get_filter_options()
        )
```

---

### Example 2: AI Analysis Flow

**Frontend (initiate analysis)**:
```typescript
// AIAnalysis.tsx
const analyzeReport = async (examId, prompt) => {
  try {
    // Single analysis (blocking)
    const response = await axios.post('/api/v1/analysis/single', {
      exam_id: examId,
      analysis_type: 'classification',
      prompt: prompt
    });
    
    // Show results
    setAnalysisResult(response.data.result);
    setConfidence(response.data.confidence);
  } catch (error) {
    notification.error({ message: 'Analysis failed' });
  }
};
```

**Backend (FastAPI handler)**:
```python
# api/analysis_routes.py
@router.post("/single")
async def analyze_single(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    try:
        # Fetch study
        study = db.query(Study).filter(Study.exam_id == request.exam_id).first()
        if not study:
            raise HTTPException(status_code=404, detail="Study not found")
        
        # Call Ollama
        ollama_client = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=request.model
        )
        result = ollama_client.analyze(
            text=study.exam_description,
            prompt=request.prompt,
            analysis_type=request.analysis_type
        )
        
        # Save to database (optional)
        annotation = AIAnnotation(
            exam_id=request.exam_id,
            analysis_type=request.analysis_type,
            result=result
        )
        db.add(annotation)
        db.commit()
        
        return AnalysisResult(
            result=result,
            confidence=0.85,  # From Ollama response
            processing_time_ms=1200
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Ollama Client (Service)**:
```python
# services/ollama_client.py
class OllamaClient:
    def analyze(self, text, prompt, analysis_type):
        # Construct full prompt
        full_prompt = f"{prompt}\n\n{text}"
        
        # Call Ollama API
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=settings.OLLAMA_TIMEOUT
        )
        
        # Parse response
        result = response.json()
        generated_text = result.get('response', '')
        
        # Parse analysis result (depends on analysis_type)
        return self._parse_analysis(generated_text, analysis_type)
```

---

## 🔐 Authentication & Authorization

### JWT Token Flow

```
1. Frontend: Send credentials (email, password)
   POST /api/v1/auth/login
   
2. Backend: Validate credentials
   - Check user exists
   - Verify password (bcrypt)
   - Generate JWT token
   
3. Backend: Return token
   {
     "access_token": "eyJhbGc...",
     "token_type": "bearer",
     "user": { id, email, role }
   }
   
4. Frontend: Store token (localStorage or sessionStorage)
   localStorage.setItem('access_token', token)
   
5. Frontend: Send token with every request
   Headers: { Authorization: "Bearer <token>" }
   
6. Backend: Verify token
   - Extract token from header
   - Decode and validate signature
   - Check expiration (30 minutes)
   - Extract user_id from payload
   
7. Backend: Check user permissions
   - Allow if admin
   - Check if owns resource
   
8. Backend: Process request or return 401/403
```

### Token Expiration

```
Access Token:
  - Lifetime: 30 minutes
  - Stored: Frontend localStorage
  - Used for: API requests
  
Expired Token:
  - Frontend: Catch 401 error
  - Frontend: Redirect to login
  - User: Must re-authenticate
```

---

## 📦 Data Models

### Study (From DuckDB to PostgreSQL)

```typescript
interface Study {
  exam_id: string;                          // UUID
  medical_record_no?: string;               // Patient ID
  patient_name: string;                     // Full name
  patient_gender?: string;                  // M/F
  patient_age?: number;                     // Age in years
  exam_status: string;                      // completed/pending/cancelled
  exam_source: string;                      // PAPA/Red/Other
  exam_item: string;                        // CT/MRI/X-Ray
  exam_description?: string;                // Full report text
  order_datetime: ISO8601;                  // Exam ordered
  check_in_datetime?: ISO8601;              // Patient checked in
  report_certification_datetime?: ISO8601;  // Report certified
  certified_physician?: string;             // Physician name
  created_at: ISO8601;                      // Record created
  updated_at: ISO8601;                      // Record updated
}
```

### AI Annotation

```typescript
interface AIAnnotation {
  id: UUID;
  exam_id: string;                    // FK to Study
  analysis_type: 'highlight' | 'classification' | 'extraction' | 'scoring';
  prompt_template: string;            // Template used
  result: JsonValue;                  // JSONB: varies by type
  confidence: number;                 // 0.0 - 1.0
  processing_time_ms: int;            // For monitoring
  model: string;                      // qwen2.5:7b, etc
  created_at: ISO8601;
  created_by: UUID;                   // FK to User
}
```

### Project

```typescript
interface Project {
  id: UUID;
  name: string;
  description?: string;
  tags: string[];
  status: 'active' | 'archived' | 'completed';
  created_by: UUID;                   // FK to User
  created_at: ISO8601;
  updated_at: ISO8601;
}

interface ProjectStudy {
  project_id: UUID;                   // FK
  exam_id: string;                    // FK
  note?: string;                      // Why this study is in project
  added_at: ISO8601;
  added_by: UUID;                     // FK to User
}
```

---

## 🔄 State Management (Zustand)

### Frontend Store Structure

```typescript
// store/studyStore.ts
interface StudyState {
  // Search state
  searchQuery: string;
  searchResults: Study[];
  totalResults: number;
  currentPage: number;
  filters: SearchFilters;
  loading: boolean;
  error?: string;
  
  // UI state
  selectedStudy?: Study;
  showDetailModal: boolean;
  showFilterPanel: boolean;
  
  // Actions
  setSearchQuery: (q: string) => void;
  search: () => Promise<void>;
  setFilters: (filters: SearchFilters) => void;
  clearFilters: () => void;
  setPage: (page: number) => void;
  selectStudy: (study: Study) => void;
  clearSelection: () => void;
}

// Usage in component
const store = useStudyStore();
const { searchQuery, setSearchQuery, search } = store;

// In render
<Input 
  value={searchQuery}
  onChange={(e) => setSearchQuery(e.target.value)}
  onPressEnter={search}
/>
```

---

## ⚠️ Error Handling

### HTTP Error Responses

```
400 Bad Request
  - Invalid query parameters
  - Malformed request body
  - Missing required fields
  
401 Unauthorized
  - Missing or invalid token
  - Token expired
  
403 Forbidden
  - User lacks permission
  - Cannot access resource
  
404 Not Found
  - Resource doesn't exist
  
500 Internal Server Error
  - Database error
  - Ollama service error
  - Unexpected error
```

### Frontend Error Handling

```typescript
try {
  const response = await axios.get('/api/v1/studies/search', { params });
  return response.data;
} catch (error) {
  if (error.response?.status === 401) {
    // Redirect to login
    window.location.href = '/login';
  } else if (error.response?.status === 400) {
    // Show validation error
    notification.error({ message: error.response.data.detail });
  } else {
    // Show generic error
    notification.error({ message: 'Request failed' });
  }
  throw error;
}
```

---

## 🚀 Performance Considerations

### Request Optimization

1. **Pagination**: Load 20-50 items per page, not all
2. **Lazy Loading**: Load details only when modal opens
3. **Caching**: Store filter options in frontend (valid for session)
4. **Debouncing**: Debounce search input 300ms before API call

### Response Optimization

1. **Selective Fields**: Only return needed fields
2. **Compression**: Use gzip compression (standard HTTP)
3. **Pagination Response**: Include total count for UI progress

### Database Optimization

1. **Indexes**: Index on search columns (patient_name, exam_item, exam_status)
2. **Query Efficiency**: Use prepared statements
3. **Connection Pooling**: Reuse database connections

---

## 🔌 Third-Party Integrations

### Ollama LLM Service

```
URL: http://localhost:11434
Model: qwen2.5:7b (Chinese-optimized)

Endpoint: POST /api/generate
Request:
  {
    "model": "qwen2.5:7b",
    "prompt": "full prompt with medical text",
    "stream": false,
    "temperature": 0.7,
    "top_k": 40,
    "top_p": 0.9
  }

Response:
  {
    "model": "qwen2.5:7b",
    "response": "generated analysis text",
    "done": true,
    "load_duration": 123456,
    "prompt_eval_count": 145,
    "prompt_eval_duration": 654321,
    "eval_count": 42,
    "eval_duration": 345678
  }
```

---

## 📝 API Documentation

### Interactive API Docs (Swagger)

```
FastAPI:  http://localhost:8000/docs
Django:   http://localhost:8001/api/schema/
```

Both provide:
- Endpoint documentation
- Request/response examples
- Try-it-out functionality
- Parameter descriptions

---

## 🔄 Deployment Considerations

### Development Setup

```bash
# Terminal 1: Frontend
cd frontend
npm install
npm run dev  # Port 3000

# Terminal 2: Backend
cd backend
pip install -r requirements.txt
python run.py  # Port 8000

# Terminal 3: Ollama
ollama serve  # Port 11434

# Terminal 4: Database
docker run -d postgres:14  # Port 5432
```

### Production Deployment

```bash
# Docker Compose (all services)
docker-compose up -d

# Environment variables must be set:
VITE_API_BASE_URL=https://api.example.com
DATABASE_URL=postgresql://user:pass@postgres:5432/imagedb
OLLAMA_BASE_URL=http://ollama:11434
CORS_ORIGINS=["https://example.com"]
SECRET_KEY=<strong-random-key>
```

---

## 📚 Related Documentation

- [Project Overview](../01_PROJECT_OVERVIEW.md) - High-level project description
- [Technical Architecture](./02_TECHNICAL_ARCHITECTURE.md) - System design and components
- [Database Design](../database/03_DATABASE_DESIGN.md) - Table schemas and relationships
- [API Specification](../api/04_API_SPECIFICATION.md) - Complete API documentation
- [AI Integration Guide](../guides/AI_INTEGRATION_GUIDE.md) - Ollama setup and usage

---

**Document Version**: v2.0.0  
**Last Updated**: 2025-11-07  
**Maintained By**: Image Data Platform Team
