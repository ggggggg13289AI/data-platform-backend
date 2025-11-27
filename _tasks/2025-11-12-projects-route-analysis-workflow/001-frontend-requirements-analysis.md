# 前端需求分析 - Projects Feature
## Frontend Requirements Analysis - Projects Feature

**文件版本**: v1.0
**建立日期**: 2025-11-12
**專案**: Medical Imaging Data Platform
**功能模組**: Projects Management (專案管理)

---

## 一、Executive Summary (執行摘要)

### 1.1 Current Status (當前狀態)

**Frontend Implementation**: ✅ 100% Complete
**Backend Implementation**: ❌ 0% Complete (No API endpoints exist)

### 1.2 Gap Analysis (差距分析)

| Component | Status | Completion | Notes |
|-----------|--------|------------|-------|
| Frontend UI | ✅ Complete | 100% | Production-ready with Ant Design |
| Frontend Hooks | ✅ Complete | 100% | useProjects, useProjectFilters |
| Frontend Services | ✅ Complete | 100% | Full API client implementation |
| Frontend Types | ✅ Complete | 100% | Comprehensive TypeScript definitions |
| Backend Models | ❌ Missing | 0% | Need Django Project model |
| Backend API | ❌ Missing | 0% | Need Django Ninja endpoints |
| Backend Service | ❌ Missing | 0% | Need business logic layer |
| Integration | ❌ Blocked | 0% | Waiting for backend implementation |

---

## 二、Feature Overview (功能概覽)

### 2.1 Core Purpose (核心目的)

**English**:
Enable users to organize and manage medical imaging studies into projects for structured data analysis, collaboration, and workflow management.

**繁體中文**:
讓使用者能夠將醫學影像研究組織成專案，以進行結構化資料分析、協作和工作流程管理。

### 2.2 Key Features (主要功能)

1. **Project CRUD Operations** (專案基本操作)
   - Create new projects with metadata
   - Update project information
   - Delete projects with confirmation
   - View project details and statistics

2. **Project Lifecycle Management** (專案生命週期管理)
   - Archive inactive projects
   - Restore archived projects
   - Duplicate existing projects

3. **Study Assignment** (研究指派)
   - Batch add studies to projects
   - Remove studies from projects
   - View project's study collection

4. **Collaboration Features** (協作功能)
   - Add/remove project members
   - Assign member roles (Owner, Admin, Editor, Viewer)
   - Manage member permissions

5. **Advanced Features** (進階功能)
   - Filter projects by status, tags, members
   - Search projects by name/description
   - Sort by various criteria
   - Export project data
   - Grid/List view modes
   - Pagination support

---

## 三、Frontend Architecture Analysis (前端架構分析)

### 3.1 Component Structure (元件結構)

```
frontend/src/
├── pages/
│   ├── Projects/
│   │   └── index.tsx              ✅ Main page (330 lines)
│   └── ProjectDetail/
│       └── index.tsx              ⚠️ Exists but implementation unknown
├── components/
│   ├── Projects/
│   │   ├── ProjectList.tsx        ✅ Grid/List rendering
│   │   ├── ProjectFilters.tsx     ✅ Advanced filtering UI
│   │   ├── ProjectForm.tsx        ✅ Create/Edit modal
│   │   ├── ExportModal.tsx        ✅ Data export functionality
│   │   ├── ClearButton.tsx        ✅ Filter reset button
│   │   └── ProjectStats.tsx       ✅ Statistics display
│   └── Common/
│       └── ProjectSelectionModal.tsx  ✅ Batch selection UI
├── hooks/
│   └── projects/
│       ├── useProjects.ts         ✅ Main data management hook (300 lines)
│       └── useProjectFilters.ts   ✅ Filter state management
├── services/
│   └── project.ts                 ✅ API client (214 lines, 22 endpoints)
├── types/
│   └── project.ts                 ✅ Complete TypeScript definitions (175 lines)
└── utils/
    └── projectSelectionModalUtils.ts  ✅ Helper utilities
```

### 3.2 State Management (狀態管理)

**Hook-Based Architecture** (基於 Hook 的架構):

```typescript
// useProjects Hook - Main state container
interface UseProjectsResult {
  // Data State
  projects: ProjectListItem[]      // Current page data
  total: number                     // Total count for pagination
  loading: boolean                  // Loading indicator
  error: string | null             // Error messages

  // Pagination State
  page: number                      // Current page number
  pageSize: number                  // Items per page

  // CRUD Operations
  loadProjects: (params?) => Promise<void>
  createProject: (data) => Promise<Project | null>
  updateProject: (id, data) => Promise<Project | null>
  deleteProject: (id) => Promise<boolean>

  // Lifecycle Operations
  archiveProject: (id) => Promise<boolean>
  restoreProject: (id) => Promise<boolean>
  duplicateProject: (id) => Promise<Project | null>

  // Utility Operations
  refresh: () => Promise<void>
  setPage: (page) => void
  setPageSize: (size) => void
}
```

### 3.3 Data Flow (資料流)

```
User Interaction
    ↓
Component Event Handler
    ↓
useProjects Hook Method
    ↓
projectService API Call
    ↓
Axios HTTP Request
    ↓
[Backend API - NOT IMPLEMENTED]
    ↓
Response Processing
    ↓
State Update
    ↓
UI Re-render
```

---

## 四、API Contract Specification (API 契約規格)

### 4.1 Base Configuration (基礎配置)

```typescript
Base URL: http://localhost:8000/api/v1
Endpoint: /projects
Authorization: Bearer Token (from localStorage)
Content-Type: application/json
```

### 4.2 Complete API Endpoint List (完整 API 端點清單)

#### 4.2.1 Core CRUD Operations (基本 CRUD 操作)

**1. List Projects with Filters** (列出專案含篩選)

```http
GET /api/v1/projects
Query Parameters:
  - page?: number            // Page number (1-indexed)
  - pageSize?: number        // Items per page (default 20)
  - status?: string[]        // Filter by status (active, archived, completed, draft)
  - tags?: string[]          // Filter by tags
  - members?: string[]       // Filter by member IDs
  - search?: string          // Search in name/description
  - dateRange?: [string, string]  // Created date range
  - sortBy?: string          // Sort field (name, created_at, updated_at, study_count)
  - sortOrder?: string       // Sort order (asc, desc)

Response: 200 OK
{
  "total": 156,
  "projects": [
    {
      "id": "proj_123abc",
      "name": "Aorta CTA Analysis 2024",
      "description": "Comprehensive analysis of aortic CT angiography studies",
      "status": "active",
      "tags": ["cardiology", "cta", "research"],
      "study_count": 42,
      "created_at": "2024-01-15T08:30:00Z",
      "updated_at": "2024-11-12T14:22:00Z"
    }
  ],
  "page": 1,
  "pageSize": 20
}
```

**2. Get Project Detail** (取得專案詳情)

```http
GET /api/v1/projects/:projectId

Response: 200 OK
{
  "id": "proj_123abc",
  "name": "Aorta CTA Analysis 2024",
  "description": "...",
  "status": "active",
  "tags": ["cardiology"],
  "study_count": 42,
  "created_at": "2024-01-15T08:30:00Z",
  "updated_at": "2024-11-12T14:22:00Z",
  "created_by": "user_789",
  "members": [
    {
      "userId": "user_789",
      "username": "Dr. Chen",
      "role": "owner",
      "joinedAt": "2024-01-15T08:30:00Z"
    }
  ],
  "settings": {
    "isPublic": false,
    "allowGuestAccess": false,
    "notifications": {
      "onNewStudy": true,
      "onMemberJoin": true
    }
  },
  "statistics": {
    "studiesCount": 42,
    "imagesCount": 1280,
    "totalSize": 5368709120,
    "lastActivity": "2024-11-12T14:22:00Z",
    "activeMembers": 3
  }
}
```

**3. Create Project** (建立專案)

```http
POST /api/v1/projects
Request Body:
{
  "name": "New Research Project",
  "description": "Project description",
  "tags": ["research", "cardiology"],
  "status": "draft",  // Optional, defaults to 'active'
  "settings": {
    "isPublic": false,
    "allowGuestAccess": false
  }
}

Response: 201 Created
{
  "id": "proj_456def",
  "name": "New Research Project",
  ...
}
```

**4. Update Project** (更新專案)

```http
PUT /api/v1/projects/:projectId
Request Body:
{
  "name": "Updated Project Name",
  "description": "Updated description",
  "status": "completed",
  "tags": ["research", "completed"]
}

Response: 200 OK
{
  "id": "proj_123abc",
  "name": "Updated Project Name",
  ...
}
```

**5. Delete Project** (刪除專案)

```http
DELETE /api/v1/projects/:projectId

Response: 204 No Content
```

#### 4.2.2 Lifecycle Operations (生命週期操作)

**6. Archive Project** (封存專案)

```http
POST /api/v1/projects/:projectId/archive

Response: 200 OK
{
  "id": "proj_123abc",
  "status": "archived",
  ...
}
```

**7. Restore Project** (還原專案)

```http
POST /api/v1/projects/:projectId/restore

Response: 200 OK
{
  "id": "proj_123abc",
  "status": "active",
  ...
}
```

**8. Duplicate Project** (複製專案)

```http
POST /api/v1/projects/:projectId/duplicate

Response: 201 Created
{
  "id": "proj_789ghi",
  "name": "Copy of Original Project",
  "description": "...",
  "study_count": 0,  // New project starts empty
  "created_at": "2024-11-12T15:00:00Z"
}
```

#### 4.2.3 Statistics Operations (統計操作)

**9. Get Project Statistics** (取得專案統計)

```http
GET /api/v1/projects/:projectId/statistics

Response: 200 OK
{
  "studiesCount": 42,
  "imagesCount": 1280,
  "totalSize": 5368709120,  // bytes
  "lastActivity": "2024-11-12T14:22:00Z",
  "activeMembers": 3
}
```

#### 4.2.4 Study Management Operations (研究管理操作)

**10. Add Studies to Project** (將研究加入專案)

```http
POST /api/v1/projects/:projectId/studies
Request Body:
{
  "project_id": "proj_123abc",
  "exam_ids": ["exam_001", "exam_002", "exam_003"]
}

Response: 200 OK
{
  "success": true,
  "added_count": 3,
  "project_id": "proj_123abc",
  "project_name": "Aorta CTA Analysis 2024"
}
```

**11. Remove Studies from Project** (從專案移除研究)

```http
DELETE /api/v1/projects/:projectId/studies
Request Body:
{
  "exam_ids": ["exam_001", "exam_002"]
}

Response: 200 OK
{
  "success": true,
  "removed_count": 2
}
```

**12. Get Studies by Project** (取得專案的研究清單)

```http
GET /api/v1/projects/:projectId/studies

Response: 200 OK
{
  "studies": [
    {
      "exam_id": "exam_001",
      "patient_name": "Patient A",
      "exam_item": "Chest CT",
      "order_datetime": "2024-01-15T10:00:00Z"
    }
  ]
}
```

**13. Batch Assign Studies** (批次指派研究)

```http
POST /api/v1/projects/batch-assign
Request Body:
{
  "study_ids": ["exam_001", "exam_002"],
  "project_ids": ["proj_123", "proj_456"]
}

Response: 200 OK
{
  "assignments": [
    {
      "id": "assign_001",
      "studyId": "exam_001",
      "projectId": "proj_123",
      "assignedAt": "2024-11-12T15:00:00Z"
    }
  ]
}
```

#### 4.2.5 Member Management Operations (成員管理操作)

**14. Add Member to Project** (新增專案成員)

```http
POST /api/v1/projects/:projectId/members
Request Body:
{
  "user_id": "user_456",
  "role": "editor"  // owner, admin, editor, viewer
}

Response: 201 Created
```

**15. Remove Member from Project** (移除專案成員)

```http
DELETE /api/v1/projects/:projectId/members/:userId

Response: 204 No Content
```

**16. Update Member Role** (更新成員角色)

```http
PUT /api/v1/projects/:projectId/members/:userId
Request Body:
{
  "role": "admin"
}

Response: 200 OK
```

**17. Get Project Members** (取得專案成員清單)

```http
GET /api/v1/projects/:projectId/members

Response: 200 OK
{
  "members": [
    {
      "userId": "user_789",
      "username": "Dr. Chen",
      "role": "owner",
      "joinedAt": "2024-01-15T08:30:00Z"
    }
  ]
}
```

#### 4.2.6 Search Operations (搜尋操作)

**18. Search Projects** (搜尋專案)

```http
GET /api/v1/projects/search?q=aorta

Response: 200 OK
{
  "projects": [
    {
      "id": "proj_123",
      "name": "Aorta CTA Analysis",
      ...
    }
  ]
}
```

**19. Get Projects by Study** (取得研究所屬的專案)

```http
GET /api/v1/studies/:studyId/projects

Response: 200 OK
{
  "projects": [
    {
      "id": "proj_123",
      "name": "Aorta CTA Analysis",
      ...
    }
  ]
}
```

---

## 五、Data Models (資料模型)

### 5.1 Core Project Model (核心專案模型)

```typescript
interface Project {
  // Primary Identification
  id: string                        // UUID, Primary Key
  name: string                      // Project name, max 200 chars
  description?: string              // Optional description, max 2000 chars

  // Status Management
  status: ProjectStatus             // active | archived | completed | draft

  // Categorization
  tags: string[]                    // Array of tag strings

  // Metrics
  study_count: number              // Count of assigned studies

  // Timestamps
  created_at: string               // ISO 8601 datetime
  updated_at?: string              // ISO 8601 datetime

  // Ownership
  created_by?: string              // User ID of creator

  // Relationships (Optional, loaded on demand)
  members?: ProjectMember[]
  settings?: ProjectSettings
  statistics?: ProjectStatistics
  metadata?: Record<string, unknown>  // Flexible JSON field
}
```

### 5.2 Project Status Enum (專案狀態列舉)

```typescript
enum ProjectStatus {
  ACTIVE = 'active',        // Currently in use
  ARCHIVED = 'archived',    // Archived but can be restored
  COMPLETED = 'completed',  // Finished project
  DRAFT = 'draft'          // Work in progress
}
```

### 5.3 Project Member Model (專案成員模型)

```typescript
interface ProjectMember {
  userId: string
  username?: string
  role: ProjectRole         // owner | admin | editor | viewer
  joinedAt: string         // ISO 8601 datetime
  permissions?: Permission[]
}

enum ProjectRole {
  OWNER = 'owner',     // Full control, can delete project
  ADMIN = 'admin',     // Can manage members and settings
  EDITOR = 'editor',   // Can edit project and add/remove studies
  VIEWER = 'viewer'    // Read-only access
}
```

### 5.4 Project Settings Model (專案設定模型)

```typescript
interface ProjectSettings {
  isPublic: boolean                  // Public visibility
  allowGuestAccess: boolean         // Allow guest users
  autoArchiveDays?: number          // Auto-archive after N days of inactivity
  notifications?: NotificationSettings
  customFields?: CustomField[]
}

interface NotificationSettings {
  onNewStudy: boolean
  onMemberJoin: boolean
  onStatusChange: boolean
  emailDigest?: 'daily' | 'weekly' | 'never'
}
```

### 5.5 Project Statistics Model (專案統計模型)

```typescript
interface ProjectStatistics {
  studiesCount: number      // Total studies in project
  imagesCount: number       // Total images across all studies
  totalSize: number         // Total storage size in bytes
  lastActivity: string      // ISO 8601 datetime of last activity
  activeMembers: number     // Count of active members
}
```

---

## 六、UI/UX Requirements (UI/UX 需求)

### 6.1 View Modes (檢視模式)

1. **Grid View** (網格檢視)
   - Cards layout with project thumbnails
   - Show key metrics: name, status, study count
   - Quick actions on hover

2. **List View** (列表檢視)
   - Table-style compact layout
   - More columns visible
   - Sortable columns

### 6.2 Filter Panel (篩選面板)

**Available Filters**:
- Status (多選): Active, Archived, Completed, Draft
- Tags (多選): Dynamically populated from existing tags
- Members (多選): Filter by team members
- Date Range (日期範圍): Created date range picker
- Search (搜尋): Free text search in name/description

**Filter Persistence**:
- Filters saved to localStorage
- Restored on page reload
- Clear all filters button

### 6.3 Pagination (分頁)

- Page size options: 10, 20, 50, 100
- Total count display
- Quick jump to page number
- Show total: "Total 156 projects"

### 6.4 Action Buttons (操作按鈕)

**Toolbar Actions**:
- ➕ New Project (Primary button)
- 📥 Export (Secondary button, disabled if no projects)

**Per-Project Actions** (每個專案的操作):
- ✏️ Edit (編輯)
- 🗑️ Delete (刪除, with confirmation modal)
- 📋 Duplicate (複製)
- 📦 Archive/Restore (封存/還原)
- 👥 Manage Members (成員管理)
- 📊 View Statistics (統計資料)

### 6.5 Modal Dialogs (對話框)

1. **Project Form Modal** (專案表單對話框)
   - Create/Edit mode
   - Fields: Name (required), Description, Tags, Status
   - Form validation with real-time feedback
   - Save/Cancel buttons

2. **Export Modal** (匯出對話框)
   - Select export format (CSV, JSON, Excel)
   - Choose fields to include
   - Progress indicator
   - Download link on completion

3. **Confirmation Modals** (確認對話框)
   - Delete confirmation (danger style)
   - Archive confirmation
   - Destructive actions require explicit confirmation

---

## 七、User Workflows (使用者工作流程)

### 7.1 Create New Project (建立新專案)

```
1. User clicks "New Project" button
   ↓
2. Project Form Modal opens
   ↓
3. User fills in:
   - Name (required)
   - Description (optional)
   - Tags (optional, multi-select)
   - Status (optional, defaults to 'active')
   ↓
4. User clicks "Save"
   ↓
5. Form validation runs
   ↓
6. POST /api/v1/projects
   ↓
7. Success message shown
   ↓
8. Modal closes
   ↓
9. Project list refreshes
   ↓
10. New project appears in list
```

### 7.2 Add Studies to Project (將研究加入專案)

```
1. User navigates to Project Detail page
   ↓
2. Clicks "Add Studies" button
   ↓
3. Study Selection Modal opens
   ↓
4. User searches/filters studies
   ↓
5. User selects multiple studies (checkbox)
   ↓
6. User clicks "Add Selected"
   ↓
7. POST /api/v1/projects/:id/studies with exam_ids
   ↓
8. Success message: "3 studies added successfully"
   ↓
9. Study list refreshes
   ↓
10. study_count metric updates
```

### 7.3 Filter and Search Projects (篩選和搜尋專案)

```
1. User opens Filter Panel
   ↓
2. Selects filters:
   - Status: [Active, Completed]
   - Tags: [cardiology, research]
   - Date Range: Last 3 months
   ↓
3. User types search query: "aorta"
   ↓
4. Filter state updates (debounced)
   ↓
5. GET /api/v1/projects with query params
   ↓
6. Results filtered and displayed
   ↓
7. Result count shown: "12 projects found"
   ↓
8. Active filters badge shown (count: 4)
```

---

## 八、Error Handling (錯誤處理)

### 8.1 Error Scenarios (錯誤情境)

| Scenario | HTTP Status | User Message | Frontend Behavior |
|----------|-------------|--------------|-------------------|
| Network Error | - | "無法連接到伺服器，請檢查網路連線" | Show error notification, allow retry |
| Unauthorized | 401 | "登入已過期，請重新登入" | Redirect to login page |
| Forbidden | 403 | "您沒有權限執行此操作" | Show error notification, disable action |
| Not Found | 404 | "找不到指定的專案" | Show error notification, redirect to list |
| Validation Error | 400 | "請檢查輸入資料：{field} 欄位必填" | Highlight invalid fields in form |
| Conflict | 409 | "專案名稱已存在" | Show inline error in form |
| Server Error | 500 | "伺服器發生錯誤，請稍後再試" | Show error notification, log to monitoring |

### 8.2 User Feedback Mechanisms (使用者回饋機制)

1. **Toast Notifications** (通知訊息)
   - Success: Green, 3 seconds, auto-dismiss
   - Error: Red, 5 seconds, manual dismiss
   - Info: Blue, 3 seconds, auto-dismiss

2. **Inline Validation** (即時驗證)
   - Real-time field validation in forms
   - Error messages below invalid fields
   - Visual indicators (red border, error icon)

3. **Loading States** (載入狀態)
   - Skeleton screens for initial load
   - Spinning indicators for actions
   - Disabled buttons during operations

---

## 九、Performance Requirements (效能需求)

### 9.1 Performance Targets (效能目標)

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Initial Page Load | < 2 seconds | Time to interactive |
| API Response Time | < 500ms | 95th percentile |
| Filter/Search Response | < 300ms | Including debounce |
| Pagination Navigation | < 200ms | Page switch time |
| Create/Update Operation | < 1 second | Complete round trip |

### 9.2 Optimization Strategies (優化策略)

1. **Data Loading**
   - Lazy load project details
   - Load statistics on demand
   - Paginate large lists

2. **Caching**
   - Cache filter options
   - Store filter state in localStorage
   - Implement optimistic updates

3. **Network**
   - Debounce search input (300ms)
   - Batch multiple study assignments
   - Cancel in-flight requests on navigation

---

## 十、Accessibility Requirements (無障礙需求)

### 10.1 WCAG 2.1 AA Compliance (WCAG 2.1 AA 合規)

1. **Keyboard Navigation** (鍵盤導航)
   - All actions accessible via keyboard
   - Logical tab order
   - Visible focus indicators

2. **Screen Reader Support** (螢幕閱讀器支援)
   - ARIA labels on all interactive elements
   - Announce state changes
   - Descriptive button labels

3. **Color Contrast** (色彩對比)
   - Text contrast ratio ≥ 4.5:1
   - Interactive elements contrast ≥ 3:1
   - Status indicators use icons + text

4. **Responsive Design** (響應式設計)
   - Mobile-friendly (viewport ≥ 320px)
   - Touch-friendly tap targets (≥ 44x44px)
   - Readable text sizes

---

## 十一、Integration Points (整合點)

### 11.1 Integration with Existing Features (與現有功能整合)

1. **Study Search Integration**
   - Add "Add to Project" button in Study Search results
   - Batch selection mode
   - Show project assignments in study details

2. **Authentication Integration**
   - Use existing auth tokens
   - Enforce permission checks
   - Track user actions

3. **Dashboard Integration**
   - Show recent projects
   - Display project statistics widgets
   - Quick access to active projects

### 11.2 Future Integration Possibilities (未來整合可能性)

1. **AI Analysis Integration**
   - Assign AI analysis tasks to project studies
   - Track analysis progress per project
   - Project-level analysis reports

2. **Validation Workflow Integration**
   - Associate validation workflows with projects
   - Project-specific validation criteria
   - Batch validation on project studies

3. **Export Integration**
   - Export project data with studies
   - Include validation results
   - Generate project reports

---

## 十二、Testing Requirements (測試需求)

### 12.1 Unit Testing (單元測試)

**Coverage Target**: ≥ 80%

Test Suites:
- `useProjects` hook logic
- `projectService` API calls
- Filter state management
- Form validation logic

### 12.2 Integration Testing (整合測試)

Test Scenarios:
- Complete CRUD workflows
- Filter and search combinations
- Pagination edge cases
- Error handling flows

### 12.3 E2E Testing (端到端測試)

Critical User Journeys:
1. Create project → Add studies → View statistics
2. Filter projects → Edit project → Archive
3. Search projects → Duplicate → Verify data
4. Batch operations → Error recovery

---

## 十三、Security Considerations (安全性考量)

### 13.1 Authorization (授權)

1. **Permission Checks**
   - Owner: Full control
   - Admin: Manage members, settings
   - Editor: Edit project, manage studies
   - Viewer: Read-only access

2. **API Security**
   - Bearer token authentication
   - Validate user permissions server-side
   - Prevent unauthorized access

### 13.2 Data Validation (資料驗證)

1. **Input Sanitization**
   - Sanitize user input in forms
   - Prevent XSS attacks
   - Validate data types and formats

2. **Rate Limiting**
   - Limit API calls per user
   - Prevent abuse of batch operations
   - Implement exponential backoff on errors

---

## 十四、Conclusion (結論)

### 14.1 Implementation Priority (實作優先序)

**Phase 1: Core Functionality** (MVP)
1. ✅ Frontend UI (Already complete)
2. ⏳ Backend data models
3. ⏳ Core CRUD API endpoints
4. ⏳ Basic list/detail views

**Phase 2: Advanced Features**
1. ⏳ Study assignment
2. ⏳ Filter and search
3. ⏳ Statistics calculation

**Phase 3: Collaboration Features**
1. ⏳ Member management
2. ⏳ Permission system
3. ⏳ Notifications

**Phase 4: Polish**
1. ⏳ Export functionality
2. ⏳ Batch operations
3. ⏳ Performance optimization

### 14.2 Next Steps (下一步)

1. ✅ Frontend requirements documented
2. 📝 Create backend requirements document
3. 📝 Design database schema
4. 📝 Design API specification
5. 📝 Create implementation roadmap
6. ⏳ Implement backend (awaiting confirmation)

---

## 附錄 A: Frontend File References (前端檔案參考)

| File Path | Lines | Purpose |
|-----------|-------|---------|
| `frontend/src/pages/Projects/index.tsx` | 330 | Main projects page UI |
| `frontend/src/hooks/projects/useProjects.ts` | 300 | Data management hook |
| `frontend/src/services/project.ts` | 214 | API client with 22 endpoints |
| `frontend/src/types/project.ts` | 175 | TypeScript type definitions |
| `frontend/src/components/Projects/ProjectList.tsx` | - | Project grid/list rendering |
| `frontend/src/components/Projects/ProjectFilters.tsx` | - | Advanced filter UI |
| `frontend/src/components/Projects/ProjectForm.tsx` | - | Create/Edit modal form |
| `frontend/src/components/Projects/ExportModal.tsx` | - | Data export dialog |

---

**Document Status**: ✅ Complete and Ready for Backend Implementation
**Awaiting**: Backend requirements analysis and API implementation

