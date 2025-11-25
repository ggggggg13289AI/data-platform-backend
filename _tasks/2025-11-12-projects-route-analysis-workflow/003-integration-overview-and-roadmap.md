# 整合概覽與實作路線圖 - Projects Feature
## Integration Overview & Implementation Roadmap

**文件版本**: v1.0
**建立日期**: 2025-11-12
**專案**: Medical Imaging Data Platform
**總實作時間**: 7 working days
**文件目的**: 統整前後端需求，提供完整實作計畫供確認

---

## 🎯 Executive Summary (執行摘要)

### Current State (當前狀態)

```
Frontend Implementation:  ████████████████████ 100% (Production Ready)
Backend Implementation:   ░░░░░░░░░░░░░░░░░░░░   0% (Not Started)
Database Schema:          ░░░░░░░░░░░░░░░░░░░░   0% (Not Defined)
Integration Testing:      ░░░░░░░░░░░░░░░░░░░░   0% (Blocked)
```

### Implementation Scope (實作範圍)

**Work Required**:
- 🔴 **Backend Models**: 3 Django models (Project, ProjectMember, StudyProjectAssignment)
- 🔴 **API Endpoints**: 22 REST API endpoints with Django Ninja
- 🔴 **Service Layer**: Business logic and query optimization
- 🔴 **Permission System**: Role-based access control
- 🔴 **Database Migration**: PostgreSQL schema changes
- 🟡 **Integration Testing**: Frontend-backend integration validation
- 🟡 **Documentation**: API documentation and usage guides

**Estimated Effort**: 7 working days (1 developer, full-time)

---

## 📊 Gap Analysis (差距分析)

### Detailed Component Status

| Layer | Component | Status | LOC Required | Complexity | Priority |
|-------|-----------|--------|--------------|------------|----------|
| **Frontend** | React Components | ✅ Complete | ~800 | High | N/A |
| **Frontend** | Custom Hooks | ✅ Complete | ~300 | Medium | N/A |
| **Frontend** | API Service | ✅ Complete | ~214 | Low | N/A |
| **Frontend** | TypeScript Types | ✅ Complete | ~175 | Low | N/A |
| **Backend** | Django Models | ❌ Missing | ~300 | Medium | 🔴 Critical |
| **Backend** | Service Layer | ❌ Missing | ~400 | High | 🔴 Critical |
| **Backend** | API Router | ❌ Missing | ~800 | High | 🔴 Critical |
| **Backend** | Permissions | ❌ Missing | ~150 | High | 🟡 Important |
| **Backend** | Migrations | ❌ Missing | ~100 | Low | 🔴 Critical |
| **Backend** | Unit Tests | ❌ Missing | ~500 | Medium | 🟡 Important |
| **Integration** | E2E Tests | ❌ Missing | ~300 | Medium | 🟢 Nice-to-have |

**Total New Code Required**: ~3,650 lines

### Frontend API Contract (前端 API 契約)

**22 Endpoints Expected** by frontend service layer:

| Endpoint | Method | Purpose | Frontend File Reference |
|----------|--------|---------|-------------------------|
| `/projects` | GET | List with filters | `project.ts:25` |
| `/projects` | POST | Create project | `project.ts:41` |
| `/projects/:id` | GET | Get detail | `project.ts:33` |
| `/projects/:id` | PUT | Update project | `project.ts:49` |
| `/projects/:id` | DELETE | Delete project | `project.ts:57` |
| `/projects/:id/archive` | POST | Archive | `project.ts:64` |
| `/projects/:id/restore` | POST | Restore | `project.ts:71` |
| `/projects/:id/duplicate` | POST | Duplicate | `project.ts:78` |
| `/projects/:id/statistics` | GET | Get stats | `project.ts:86` |
| `/projects/:id/studies` | POST | Add studies | `project.ts:95` |
| `/projects/:id/studies` | DELETE | Remove studies | `project.ts:115` |
| `/projects/:id/studies` | GET | List studies | `project.ts:209` |
| `/projects/batch-assign` | POST | Batch assign | `project.ts:132` |
| `/projects/:id/members` | POST | Add member | `project.ts:150` |
| `/projects/:id/members/:userId` | DELETE | Remove member | `project.ts:164` |
| `/projects/:id/members/:userId` | PUT | Update role | `project.ts:170` |
| `/projects/:id/members` | GET | List members | `project.ts:182` |
| `/projects/search` | GET | Search projects | `project.ts:191` |
| `/studies/:studyId/projects` | GET | Get study's projects | `project.ts:201` |

---

## 🏗️ Technical Architecture (技術架構)

### System Integration Diagram (系統整合圖)

```
┌────────────────────────────────────────────────────────────┐
│                    Frontend (React + TS)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Projects   │  │  useProjects │  │  projectService │   │
│  │     Page     │→│     Hook     │→│   API Client    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────────────────────┬───────────────────┘
                                         │ HTTP/JSON
                                         │ Bearer Token
┌────────────────────────────────────────┴───────────────────┐
│              Backend API (Django + Ninja)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ project_api  │→│ ProjectService│→│  Django ORM  │     │
│  │   Router     │  │  (Business)   │  │  (Database)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────────────────────┬───────────────────┘
                                         │ SQL Queries
┌────────────────────────────────────────┴───────────────────┐
│                  PostgreSQL Database                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   projects   │  │project_members│  │study_project_│     │
│  │              │  │               │  │ assignments  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐                                          │
│  │   studies    │  ← Existing table                        │
│  │  (existing)  │                                           │
│  └──────────────┘                                          │
└────────────────────────────────────────────────────────────┘
```

### Data Flow Example: Create Project (資料流範例：建立專案)

```
1. User clicks "New Project" button
   ↓
2. React Component calls useProjects.createProject()
   ↓
3. Hook calls projectService.createProject()
   ↓
4. Service sends POST /api/v1/projects with JSON
   {
     "name": "Aorta CTA Project",
     "description": "Research project",
     "tags": ["cardiology", "research"],
     "status": "active"
   }
   ↓
5. Django Ninja router receives request
   ↓
6. Pydantic validates request schema
   ↓
7. API calls ProjectService.create_project()
   ↓
8. Service layer:
   - Creates Project in transaction
   - Adds creator as owner in ProjectMember
   - Returns Project instance
   ↓
9. API serializes response
   {
     "id": "uuid-123-456",
     "name": "Aorta CTA Project",
     ...
   }
   ↓
10. Frontend updates state and shows success message
```

---

## 📋 Implementation Roadmap (實作路線圖)

### Phase 1: Foundation (基礎建置) - 2 Days

#### Day 1: Data Models & Migrations

**Morning (4 hours)**
- [ ] Define `Project` model in `backend_django/studies/models.py`
  - Fields: id, name, description, status, tags, timestamps, etc.
  - Indexes: status, created_by, study_count
  - Methods: `__str__()`, `to_dict()`
- [ ] Define `ProjectMember` model
  - Through model for Project-User relationship
  - Fields: project, user, role, joined_at, permissions
  - Unique constraint: (project, user)
- [ ] Define `StudyProjectAssignment` model
  - Junction table for Study-Project relationship
  - Fields: id, project, study, assigned_by, assigned_at, metadata
  - Unique constraint: (project, study)

**Afternoon (4 hours)**
- [ ] Create migration file
  - Run `python manage.py makemigrations studies`
  - Review generated SQL with `sqlmigrate`
- [ ] Test migration in development
  - Run `python manage.py migrate`
  - Verify tables created
  - Check indexes and constraints
- [ ] Write model unit tests
  - Test model creation
  - Test relationships
  - Test `to_dict()` serialization

**Deliverables**:
- ✅ 3 Django models defined
- ✅ Migration file created and tested
- ✅ Model unit tests passing

#### Day 2: Service Layer

**Morning (4 hours)**
- [ ] Create `backend_django/studies/project_service.py`
- [ ] Implement `ProjectService` class
  - `get_projects_queryset()` - Query builder with filters
  - `create_project()` - Transaction-safe creation
  - `duplicate_project()` - Copy project without studies
  - `add_studies_to_project()` - Batch assignment
  - `remove_studies_from_project()` - Batch removal
  - `calculate_statistics()` - Aggregate stats

**Afternoon (4 hours)**
- [ ] Implement permission system in `permissions.py`
  - `ProjectPermissions` class
  - Permission check methods (can_view, can_edit, can_delete, etc.)
  - Role-based authorization logic
- [ ] Write service layer tests
  - Test query filters
  - Test transaction handling
  - Test permission checks

**Deliverables**:
- ✅ ProjectService with 10+ methods
- ✅ Permission system implemented
- ✅ Service tests passing

---

### Phase 2: API Core (核心 API) - 3 Days

#### Day 3: CRUD Endpoints

**Morning (4 hours)**
- [ ] Create `backend_django/studies/project_api.py`
- [ ] Define Pydantic schemas
  - Request schemas: CreateProjectRequest, UpdateProjectRequest
  - Response schemas: ProjectListItemResponse, ProjectDetailResponse, ProjectListResponse
- [ ] Implement core CRUD endpoints:
  - `GET /projects` - List with filters and pagination
  - `POST /projects` - Create new project
  - `GET /projects/:id` - Get project detail
  - `PUT /projects/:id` - Update project
  - `DELETE /projects/:id` - Delete project

**Afternoon (4 hours)**
- [ ] Add error handling and logging
- [ ] Implement request validation
- [ ] Write API tests for CRUD operations
- [ ] Manual testing with curl/Postman

**Deliverables**:
- ✅ 5 CRUD endpoints working
- ✅ Pydantic validation in place
- ✅ API tests passing

#### Day 4: Lifecycle & Study Management

**Morning (4 hours)**
- [ ] Implement lifecycle endpoints:
  - `POST /projects/:id/archive` - Archive project
  - `POST /projects/:id/restore` - Restore project
  - `POST /projects/:id/duplicate` - Duplicate project
- [ ] Implement statistics endpoint:
  - `GET /projects/:id/statistics` - Calculate stats

**Afternoon (4 hours)**
- [ ] Implement study management endpoints:
  - `POST /projects/:id/studies` - Add studies (batch)
  - `DELETE /projects/:id/studies` - Remove studies (batch)
  - `GET /projects/:id/studies` - List project studies
  - `POST /projects/batch-assign` - Batch assign to multiple projects
- [ ] Write integration tests
- [ ] Test with real Study data

**Deliverables**:
- ✅ 8 lifecycle & study endpoints working
- ✅ Batch operations tested
- ✅ Integration tests passing

#### Day 5: Member Management & Search

**Morning (4 hours)**
- [ ] Implement member management endpoints:
  - `POST /projects/:id/members` - Add member
  - `DELETE /projects/:id/members/:userId` - Remove member
  - `PUT /projects/:id/members/:userId` - Update role
  - `GET /projects/:id/members` - List members
- [ ] Enforce permission checks
- [ ] Write member management tests

**Afternoon (4 hours)**
- [ ] Implement search endpoints:
  - `GET /projects/search?q=query` - Search projects
  - `GET /studies/:studyId/projects` - Get study's projects
- [ ] Optimize search queries
- [ ] Write E2E tests for complete workflows:
  - Create → Add studies → View stats
  - Add member → Update role → Remove
  - Filter → Search → Sort → Paginate

**Deliverables**:
- ✅ All 22 endpoints implemented
- ✅ Permission system integrated
- ✅ E2E tests passing

---

### Phase 3: Integration & Polish (整合與完善) - 2 Days

#### Day 6: Frontend Integration

**Morning (4 hours)**
- [ ] Register `project_router` in `backend_django/config/api.py`
- [ ] Start backend server
- [ ] Test frontend against real API
  - Test all CRUD operations from UI
  - Test filters and search
  - Test pagination
  - Test member management
  - Test study assignment

**Afternoon (4 hours)**
- [ ] Fix any API contract mismatches
- [ ] Handle edge cases and error scenarios
- [ ] Test error handling in UI
- [ ] Verify loading states and optimistic updates
- [ ] Performance profiling with browser DevTools

**Deliverables**:
- ✅ Frontend fully integrated with backend
- ✅ All 22 endpoints working from UI
- ✅ Error handling validated

#### Day 7: Polish & Deployment

**Morning (4 hours)**
- [ ] Performance optimization
  - Add database query logging
  - Identify N+1 queries
  - Add `select_related()` / `prefetch_related()`
  - Verify all indexes are used
- [ ] Security audit
  - Review permission checks
  - Test unauthorized access attempts
  - Verify input validation
  - Check for SQL injection risks
- [ ] Add comprehensive logging
  - Log all API calls
  - Log permission denials
  - Log errors with stack traces

**Afternoon (4 hours)**
- [ ] Update API documentation
  - Generate OpenAPI schema
  - Document all endpoints
  - Add usage examples
- [ ] Production deployment preparation
  - Review migration rollback plan
  - Set up monitoring alerts
  - Configure logging levels
- [ ] Deploy to production
  - Run migrations
  - Restart services
  - Smoke test critical flows
  - Monitor error rates

**Deliverables**:
- ✅ Performance optimized (< 500ms response time)
- ✅ Security audit completed
- ✅ Documentation updated
- ✅ Production deployment successful

---

## ✅ Quality Gates (品質關卡)

### Before Proceeding to Next Phase (進入下一階段前)

**Phase 1 → Phase 2**:
- ✅ All 3 models created and migrated
- ✅ Model tests passing (coverage ≥ 80%)
- ✅ Service layer methods implemented
- ✅ Permission system functional

**Phase 2 → Phase 3**:
- ✅ All 22 API endpoints implemented
- ✅ API tests passing (coverage ≥ 80%)
- ✅ Manual API testing completed
- ✅ No critical bugs found

**Phase 3 → Production**:
- ✅ Frontend integration 100% functional
- ✅ E2E tests passing
- ✅ Performance targets met (< 500ms p95)
- ✅ Security audit passed
- ✅ Documentation complete

---

## 🎯 Success Metrics (成功指標)

### Performance Targets (效能目標)

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time (p95) | < 500ms | Django logging + monitoring |
| API Response Time (p50) | < 200ms | Django logging + monitoring |
| Database Query Time | < 100ms | Django Debug Toolbar |
| Frontend Load Time | < 2s | Lighthouse, DevTools |
| Memory Usage | < 512MB | Process monitoring |

### Quality Targets (品質目標)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Unit Test Coverage | ≥ 80% | pytest-cov |
| API Test Coverage | 100% endpoints | Manual checklist |
| Integration Test Coverage | ≥ 70% | pytest |
| Code Quality (SonarQube) | Grade A | Static analysis |
| Security Vulnerabilities | 0 critical | Security audit |

### User Experience Targets (使用者體驗目標)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Error Rate | < 1% | Error logging |
| Success Message Display | 100% operations | Manual testing |
| Loading State Indicators | 100% async operations | Manual testing |
| Accessibility (WCAG AA) | 100% compliance | Automated + manual |
| Mobile Responsiveness | ≥ 320px viewport | Browser testing |

---

## ⚠️ Risk Management (風險管理)

### Identified Risks (已識別風險)

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| **Performance degradation with large datasets** | Medium | High | - Implement proper indexing<br>- Use pagination<br>- Add database query optimization<br>- Set up monitoring alerts |
| **Permission system bugs leading to unauthorized access** | Low | Critical | - Comprehensive unit tests<br>- Security audit<br>- Penetration testing<br>- Code review |
| **Database migration failures in production** | Low | High | - Test migrations in staging<br>- Have rollback script ready<br>- Schedule during low traffic<br>- Monitor closely post-deployment |
| **API contract mismatch between frontend/backend** | Medium | Medium | - Strict Pydantic validation<br>- Integration testing<br>- OpenAPI schema validation<br>- Mock API during development |
| **Concurrent update conflicts** | Low | Medium | - Use database transactions<br>- Implement optimistic locking<br>- Add retry logic<br>- Test concurrent operations |
| **Timeline delay due to complexity** | Medium | Medium | - Break tasks into smaller chunks<br>- Daily progress tracking<br>- Identify blockers early<br>- Have contingency plan |

### Rollback Plan (回滾計畫)

**If Critical Issue Found Post-Deployment**:

1. **Immediate Actions** (< 5 minutes)
   - Disable project features in frontend (feature flag)
   - Redirect users to maintenance page if needed
   - Alert dev team

2. **Assessment** (5-15 minutes)
   - Identify root cause
   - Determine if quick fix possible
   - Decide: fix forward or rollback

3. **Rollback Procedure** (15-30 minutes)
   ```bash
   # Rollback database migration
   python manage.py migrate studies <previous_migration_number>

   # Revert code changes
   git revert <commit_hash>
   git push origin main

   # Restart services
   sudo systemctl restart gunicorn
   ```

4. **Validation** (5-10 minutes)
   - Verify system operational
   - Test critical paths
   - Monitor error rates

5. **Communication** (Immediate)
   - Notify users of temporary unavailability
   - Update status page
   - Document incident

---

## 📚 Documentation Requirements (文件需求)

### Technical Documentation (技術文件)

1. **API Documentation** (API 文件)
   - OpenAPI/Swagger schema
   - Request/response examples
   - Error codes and messages
   - Rate limiting policies

2. **Database Schema Documentation** (資料庫架構文件)
   - ER diagram
   - Table descriptions
   - Index rationale
   - Migration history

3. **Architecture Documentation** (架構文件)
   - System architecture diagram
   - Data flow diagrams
   - Security architecture
   - Scalability considerations

### User Documentation (使用者文件)

1. **Feature Guide** (功能指南)
   - How to create projects
   - How to add studies to projects
   - How to manage team members
   - How to use filters and search

2. **Permission Guide** (權限指南)
   - Role descriptions
   - Permission matrix
   - How to change roles
   - Security best practices

---

## 🚀 Deployment Strategy (部署策略)

### Pre-Deployment Checklist (部署前檢查清單)

**Code Quality**:
- [ ] All tests passing (unit, integration, E2E)
- [ ] Code review completed
- [ ] No TODOs or debug code
- [ ] Linting and formatting applied

**Database**:
- [ ] Migration tested in staging
- [ ] Rollback script prepared
- [ ] Backup completed
- [ ] Index creation reviewed

**Configuration**:
- [ ] Environment variables set
- [ ] Feature flags configured
- [ ] Monitoring alerts configured
- [ ] Logging levels appropriate

**Documentation**:
- [ ] API documentation updated
- [ ] User guide prepared
- [ ] Runbook created
- [ ] Changelog updated

### Deployment Steps (部署步驟)

**Stage 1: Database Migration** (15 minutes)
```bash
# 1. Backup database
pg_dump medical_imaging > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Run migration
python manage.py migrate studies

# 3. Verify tables
python manage.py dbshell
\dt projects*
```

**Stage 2: Code Deployment** (10 minutes)
```bash
# 1. Pull latest code
git pull origin main

# 2. Install dependencies
pip install -r requirements.txt

# 3. Collect static files
python manage.py collectstatic --noinput

# 4. Restart services
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

**Stage 3: Smoke Testing** (10 minutes)
- [ ] Health check endpoint responds
- [ ] List projects works
- [ ] Create project works
- [ ] Frontend loads correctly
- [ ] No errors in logs

**Stage 4: Monitoring** (Ongoing)
- [ ] Monitor error rates
- [ ] Monitor response times
- [ ] Monitor database queries
- [ ] Monitor user activity

---

## 🔍 Monitoring & Observability (監控與可觀察性)

### Metrics to Track (追蹤指標)

**Application Metrics**:
```python
# Request rate
projects_api_request_count{endpoint="/projects", method="GET"}

# Response time
projects_api_response_time_seconds{endpoint="/projects", method="GET"}

# Error rate
projects_api_error_count{endpoint="/projects", method="GET"}

# Active projects
projects_total_active{status="active"}
```

**Database Metrics**:
- Query execution time
- Connection pool usage
- Transaction rollback rate
- Table sizes and growth

**Business Metrics**:
- Projects created per day
- Active users per project
- Study assignments per day
- Feature adoption rate

### Alerting Rules (告警規則)

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| High Error Rate | Error rate > 5% for 5 min | Critical | Page on-call engineer |
| Slow API Response | p95 > 1s for 10 min | Warning | Investigate performance |
| Database Connection Issues | Connection failures > 10 | Critical | Check database health |
| Unusual Activity | Project creation spike > 10x | Warning | Check for abuse |
| Migration Failure | Migration status failed | Critical | Execute rollback plan |

---

## 📊 Project Timeline Overview (專案時程總覽)

### Gantt Chart (甘特圖)

```
Day 1 ████████ Data Models & Migrations
Day 2 ████████ Service Layer & Permissions
Day 3 ████████ CRUD API Endpoints
Day 4 ████████ Lifecycle & Study Management
Day 5 ████████ Member Management & Search
Day 6 ████████ Frontend Integration Testing
Day 7 ████████ Polish & Deployment
```

### Milestones (里程碑)

| Milestone | Date | Deliverables | Success Criteria |
|-----------|------|--------------|------------------|
| **M1: Foundation Complete** | Day 2 EOD | Models, migrations, service layer | Tests passing, no blockers |
| **M2: API Core Complete** | Day 5 EOD | All 22 endpoints implemented | API tests passing, manual testing OK |
| **M3: Integration Complete** | Day 6 EOD | Frontend fully working | E2E tests passing, no bugs |
| **M4: Production Ready** | Day 7 EOD | Deployed and monitored | Performance targets met, no critical issues |

---

## 🎓 Learning Resources (學習資源)

### For Implementation Team (給實作團隊)

**Django & Django Ninja**:
- Django ORM query optimization: https://docs.djangoproject.com/en/5.1/topics/db/optimization/
- Django Ninja tutorial: https://django-ninja.rest-framework.com/
- Pydantic schemas: https://docs.pydantic.dev/

**React & TypeScript**:
- Custom hooks patterns: https://react.dev/learn/reusing-logic-with-custom-hooks
- TypeScript best practices: https://www.typescriptlang.org/docs/handbook/

**Testing**:
- pytest documentation: https://docs.pytest.org/
- Django testing: https://docs.djangoproject.com/en/5.1/topics/testing/

---

## 📞 Support & Communication (支援與溝通)

### Communication Channels (溝通管道)

**Daily Standups**:
- Time: 10:00 AM daily
- Duration: 15 minutes
- Format: What did, what's next, blockers

**Progress Tracking**:
- Update GitHub project board daily
- Mark tasks as in-progress/completed
- Log blockers immediately

**Code Reviews**:
- All PRs require 1 approval
- Review within 4 business hours
- Use PR template for consistency

---

## 📝 Conclusion (結論)

### Summary (總結)

**Comprehensive Analysis Completed**:
1. ✅ Frontend requirements fully documented (30+ pages)
2. ✅ Backend requirements fully documented (40+ pages)
3. ✅ Integration strategy defined
4. ✅ 7-day implementation roadmap created
5. ✅ Risk mitigation plan prepared
6. ✅ Quality gates established
7. ✅ Deployment strategy ready

**Ready for Implementation**:
- All architectural decisions made
- All technical requirements specified
- All user stories documented
- All quality standards defined

### Next Action Required (下一步所需行動)

**⏸️ AWAITING USER CONFIRMATION** (等待使用者確認)

Please review this comprehensive analysis and implementation plan, then provide confirmation to proceed with implementation.

**Questions to Confirm**:
1. ✅ Are the technical requirements clear and acceptable?
2. ✅ Is the 7-day timeline reasonable for your project schedule?
3. ✅ Are there any additional requirements or constraints to consider?
4. ✅ Should we proceed with Phase 1 (Data Models & Migrations)?

**Once Confirmed, We Will**:
1. Begin Day 1: Data Models & Migrations
2. Follow the detailed roadmap
3. Provide daily progress updates
4. Deliver production-ready implementation in 7 days

---

**Document Status**: ✅ Complete - Ready for User Review
**Total Documentation**: 3 comprehensive documents (~120 pages)
**Implementation**: ⏸️ Awaiting confirmation to proceed

