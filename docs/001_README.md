# Image Data Platform - Documentation Portal

**Version**: v2.0.0  
**Last Updated**: 2025-11-07  
**Status**: Phase 1 Complete ✅

---

## 📚 Welcome to the Documentation Portal

This directory contains all documentation for the **Image Data Platform** - an AI-assisted medical report management and analysis system.

---

## 🎯 Quick Start by Role

### 👨‍💻 Frontend Developers
Start here: [`guides/FRONTEND_DEVELOPMENT_GUIDE.md`](guides/FRONTEND_DEVELOPMENT_GUIDE.md)
- How to build React components
- Adding new features
- Working with the API

### 🐍 Backend Developers
Start here: [`../backend_django/README.md`](../backend_django/README.md)
- Django project setup
- Creating API endpoints
- Database operations

### 🏗️ Architects & Team Leads
Start here: [`01_PROJECT_OVERVIEW.md`](01_PROJECT_OVERVIEW.md)
- Project vision and goals
- System architecture overview
- Technology decisions

### 🚀 DevOps & Operations
Start here: [`../ZERO_DOWNTIME_DEPLOYMENT.md`](../ZERO_DOWNTIME_DEPLOYMENT.md)
- Deployment procedures
- Docker configuration
- Infrastructure setup

### 🎓 New Team Members
Follow this path:
1. [`../README.md`](../README.md) - Project overview
2. [`01_PROJECT_OVERVIEW.md`](01_PROJECT_OVERVIEW.md) - Detailed background
3. [`architecture/02_TECHNICAL_ARCHITECTURE.md`](architecture/02_TECHNICAL_ARCHITECTURE.md) - How it works
4. Your role-specific guide (above)

---

## 📖 Main Documentation

### Core Documents

| Document | Purpose | For Whom |
|----------|---------|----------|
| **[Project Overview](01_PROJECT_OVERVIEW.md)** | Project background, goals, features | Everyone |
| **[Technical Architecture](architecture/02_TECHNICAL_ARCHITECTURE.md)** | System design, components, flow | Architects, Seniors |
| **[Database Design](database/03_DATABASE_DESIGN.md)** | Table schemas, relationships | Backend devs, DBAs |
| **[API Specification](api/04_API_SPECIFICATION.md)** | REST API documentation | Frontend & Backend devs |
| **[Development Workflow](workflow/05_DEVELOPMENT_WORKFLOW.md)** | Phase 1 planning and schedule | Project managers |

### Architecture & Integration

| Document | Focus |
|----------|-------|
| **[Frontend-Backend Integration](architecture/FRONTEND_BACKEND_INTEGRATION.md)** | API contracts, data flow, communication patterns |
| **[Technical Architecture](architecture/02_TECHNICAL_ARCHITECTURE.md)** | System design, components, tech stack |

### Developer Guides

| Document | Topic |
|----------|-------|
| **[Frontend Development Guide](guides/FRONTEND_DEVELOPMENT_GUIDE.md)** | Building React components, adding features |
| **[AI Integration Guide](guides/AI_INTEGRATION_GUIDE.md)** | Ollama setup, LLM integration, prompting |

### Requirements & Specifications

| Document | Content |
|----------|---------|
| **[User Requirements](requirements/USER_REQUIREMENTS.md)** | Functional requirements from users |
| **[Functional Specification](requirements/FUNCTIONAL_SPECIFICATION.md)** | Technical implementation details |

---

## 🗂️ Documentation Structure

```
docs/
├── README.md                        ← You are here
├── DOCUMENT_INDEX.md                ← Main documentation index (authoritative)
├── 01_PROJECT_OVERVIEW.md           ← Start here if new
│
├── architecture/                    ← System design documents
│   ├── 02_TECHNICAL_ARCHITECTURE.md
│   └── FRONTEND_BACKEND_INTEGRATION.md
│
├── database/                        ← Database schemas
│   └── 03_DATABASE_DESIGN.md
│
├── api/                             ← API specifications
│   └── 04_API_SPECIFICATION.md
│
├── requirements/                    ← Business requirements
│   ├── USER_REQUIREMENTS.md
│   └── FUNCTIONAL_SPECIFICATION.md
│
├── workflow/                        ← Development planning
│   └── 05_DEVELOPMENT_WORKFLOW.md
│
├── guides/                          ← How-to guides
│   ├── FRONTEND_DEVELOPMENT_GUIDE.md
│   └── AI_INTEGRATION_GUIDE.md
│
└── archive/                         ← Development artifacts
    ├── phase_1_planning/
    ├── phase_1_implementation/
    ├── django_migration/
    ├── analysis_reports/
    └── decisions_log/
```

---

## ✨ What's Included in Phase 1

### ✅ Implemented Features

- **Data Import**: Excel/CSV batch import of medical reports
- **Smart Search**: PostgreSQL full-text search with complex filtering
- **AI Analysis**: Ollama LLM for report annotation and classification
- **Project Management**: Multi-project organization of reports
- **Data Export**: Excel/CSV export with AI analysis results

### ✅ Technology Stack

- **Frontend**: React 18 + TypeScript + Ant Design
- **Backend**: Django + PostgreSQL (FastAPI deprecated after Phase 1)
- **AI Engine**: Ollama with qwen2.5:7b model
- **Database**: PostgreSQL with full-text search
- **Deployment**: Docker + Docker Compose

### ✅ Documentation

- Complete API specification (20+ endpoints)
- Database design with 5 core tables
- Frontend component library and patterns
- Architecture and integration guide
- Deployment procedures
- Developer guides and best practices

---

## 🔍 Finding What You Need

### Search by Topic

**Want to build a feature?**
→ [`guides/FRONTEND_DEVELOPMENT_GUIDE.md`](guides/FRONTEND_DEVELOPMENT_GUIDE.md)

**Need to understand the API?**
→ [`api/04_API_SPECIFICATION.md`](api/04_API_SPECIFICATION.md)

**Working on the database?**
→ [`database/03_DATABASE_DESIGN.md`](database/03_DATABASE_DESIGN.md)

**Setting up Ollama?**
→ [`guides/AI_INTEGRATION_GUIDE.md`](guides/AI_INTEGRATION_GUIDE.md)

**Deploying to production?**
→ [`../ZERO_DOWNTIME_DEPLOYMENT.md`](../ZERO_DOWNTIME_DEPLOYMENT.md)

**Understanding the system?**
→ [`architecture/FRONTEND_BACKEND_INTEGRATION.md`](architecture/FRONTEND_BACKEND_INTEGRATION.md)

### Search by Document

→ **[Complete Archive Index](ARCHIVE_INDEX.md)** - All documents with descriptions and locations

---

## 📊 Quick Reference

### Project Statistics

| Metric | Value |
|--------|-------|
| **Phase Status** | ✅ Complete |
| **API Endpoints** | 20+ documented |
| **Database Tables** | 5 core tables |
| **Frontend Components** | 10+ components |
| **Documentation Pages** | 15+ detailed guides |
| **Test Coverage** | 20+ API contract tests |
| **Development Time** | 3 days (accelerated plan) |

### Technology Versions

| Component | Version | Notes |
|-----------|---------|-------|
| React | 18+ | TypeScript enabled |
| Django | 4.2+ | With Django Ninja |
| PostgreSQL | 14+ | Full-text search enabled |
| Ollama | Latest | qwen2.5:7b model |
| Docker | 20.10+ | For container orchestration |

---

## 🚀 Common Tasks

### "I want to setup my development environment"

1. Read: [`../README.md`](../README.md)
2. Run: `docker-compose up -d`
3. Access: http://localhost:3000 (frontend), http://localhost:8000/docs (backend)

### "I want to understand how the frontend talks to the backend"

1. Read: [`architecture/FRONTEND_BACKEND_INTEGRATION.md`](architecture/FRONTEND_BACKEND_INTEGRATION.md)
2. Review: Data flow examples
3. Check: [`api/04_API_SPECIFICATION.md`](api/04_API_SPECIFICATION.md)

### "I want to add a new search filter"

1. Read: [`guides/FRONTEND_DEVELOPMENT_GUIDE.md`](guides/FRONTEND_DEVELOPMENT_GUIDE.md) (Task 1)
2. Follow: Step-by-step implementation guide
3. Test: In your local development environment

### "I want to create a new API endpoint"

1. Read: [`../backend_django/README.md`](../backend_django/README.md)
2. Study: [`../backend_django/studies/api.py`](../backend_django/studies/api.py)
3. Reference: [`api/04_API_SPECIFICATION.md`](api/04_API_SPECIFICATION.md)
4. Test: Using provided test suite

### "I want to migrate data from DuckDB to PostgreSQL"

1. Read: [`database/03_DATABASE_DESIGN.md`](database/03_DATABASE_DESIGN.md)
2. Run: [`../backend_django/migrate_from_duckdb.py`](../backend_django/migrate_from_duckdb.py)
3. Verify: Data counts and integrity
4. Reference: [`../DJANGO_MIGRATION_LINUS_APPROVED.md`](../DJANGO_MIGRATION_LINUS_APPROVED.md)

### "I want to understand the AI integration"

1. Read: [`guides/AI_INTEGRATION_GUIDE.md`](guides/AI_INTEGRATION_GUIDE.md)
2. Check: Ollama setup instructions
3. Review: Prompt engineering examples
4. Test: Using study analysis features

---

## 📚 Reading Paths by Experience Level

### Beginner (New Team Member)

**Week 1**: Learn the project
1. [`../README.md`](../README.md)
2. [`01_PROJECT_OVERVIEW.md`](01_PROJECT_OVERVIEW.md)
3. [`architecture/02_TECHNICAL_ARCHITECTURE.md`](architecture/02_TECHNICAL_ARCHITECTURE.md)

**Week 2**: Setup and contribute
1. [`../backend_django/README.md`](../backend_django/README.md) OR frontend equivalent
2. Your role-specific guide
3. Start with simple tasks

### Intermediate (Experienced Developer)

**Day 1**: Understand architecture
1. [`architecture/FRONTEND_BACKEND_INTEGRATION.md`](architecture/FRONTEND_BACKEND_INTEGRATION.md)
2. [`api/04_API_SPECIFICATION.md`](api/04_API_SPECIFICATION.md)
3. [`database/03_DATABASE_DESIGN.md`](database/03_DATABASE_DESIGN.md)

**Day 2+**: Start contributing
1. Your role-specific guide
2. [Archive Index](ARCHIVE_INDEX.md) for specific information
3. Reference existing code patterns

### Architect (System Design Focus)

**Priority 1**: Architecture & decisions
1. [`01_PROJECT_OVERVIEW.md`](01_PROJECT_OVERVIEW.md)
2. [`architecture/02_TECHNICAL_ARCHITECTURE.md`](architecture/02_TECHNICAL_ARCHITECTURE.md)
3. [`database/03_DATABASE_DESIGN.md`](database/03_DATABASE_DESIGN.md)
4. [`ARCHIVE_INDEX.md`](ARCHIVE_INDEX.md) → decisions_log

**Priority 2**: Integration & performance
1. [`architecture/FRONTEND_BACKEND_INTEGRATION.md`](architecture/FRONTEND_BACKEND_INTEGRATION.md)
2. [`api/04_API_SPECIFICATION.md`](api/04_API_SPECIFICATION.md)
3. Performance considerations section

---

## 🔗 Related Resources

### Official Documentation

- [React Documentation](https://react.dev/)
- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Ant Design Components](https://ant.design/components/overview/)
- [Ollama Documentation](https://ollama.com/)

### Internal Links

- **Root README**: [`../README.md`](../README.md)
- **Backend README**: [`../backend_django/README.md`](../backend_django/README.md)
- **Frontend Source**: [`../frontend/src/`](../frontend/src/)
- **Docker Configuration**: [`../docker-compose.yml`](../docker-compose.yml)

---

## ❓ FAQ

### Q: Where do I find API documentation?

A: [`api/04_API_SPECIFICATION.md`](api/04_API_SPECIFICATION.md) for detailed specs, or visit http://localhost:8000/docs for interactive Swagger UI.

### Q: How do I add a new feature?

A: Follow [`guides/FRONTEND_DEVELOPMENT_GUIDE.md`](guides/FRONTEND_DEVELOPMENT_GUIDE.md) for frontend, or [`../backend_django/README.md`](../backend_django/README.md) for backend.

### Q: What's the difference between Phase 1 and Phase 2?

A: Phase 1 (complete) covers report search, import, and AI analysis. Phase 2 (planned) will add DICOM image viewing and storage.

### Q: Where is the migration script?

A: [`../backend_django/migrate_from_duckdb.py`](../backend_django/migrate_from_duckdb.py)

### Q: How do I run tests?

A: Run `pytest` in the backend directory, or `npm test` in the frontend directory.

### Q: What Ollama model should I use?

A: `qwen2.5:7b` (recommended). See [`guides/AI_INTEGRATION_GUIDE.md`](guides/AI_INTEGRATION_GUIDE.md) for alternatives.

---

## 📝 Document Maintenance

### Keeping Documentation Updated

When you:
- **Add a feature** → Update `01_PROJECT_OVERVIEW.md`
- **Change API** → Update `api/04_API_SPECIFICATION.md`
- **Modify database** → Update `database/03_DATABASE_DESIGN.md`
- **Make architecture change** → Update `architecture/*.md` and this index

### Version Control

- **Version**: v2.0.0 (Phase 1)
- **Last Updated**: 2025-11-07
- **Maintained By**: Image Data Platform Team

---

## 🎓 Learning Resources by Role

### Frontend Developers
- [`guides/FRONTEND_DEVELOPMENT_GUIDE.md`](guides/FRONTEND_DEVELOPMENT_GUIDE.md) - How to build
- [`api/04_API_SPECIFICATION.md`](api/04_API_SPECIFICATION.md) - Available endpoints
- [`architecture/FRONTEND_BACKEND_INTEGRATION.md`](architecture/FRONTEND_BACKEND_INTEGRATION.md) - How backend works

### Backend Developers
- [`../backend_django/README.md`](../backend_django/README.md) - Setup and running
- [`database/03_DATABASE_DESIGN.md`](database/03_DATABASE_DESIGN.md) - Data model
- [`api/04_API_SPECIFICATION.md`](api/04_API_SPECIFICATION.md) - API contracts

### DevOps/Operations
- [`../ZERO_DOWNTIME_DEPLOYMENT.md`](../ZERO_DOWNTIME_DEPLOYMENT.md) - Deployment
- [`../docker-compose.yml`](../docker-compose.yml) - Service config
- [`../README.md`](../README.md) - Quick start

### Product Managers
- [`01_PROJECT_OVERVIEW.md`](01_PROJECT_OVERVIEW.md) - Features and goals
- [`requirements/USER_REQUIREMENTS.md`](requirements/USER_REQUIREMENTS.md) - Requirements
- [`workflow/05_DEVELOPMENT_WORKFLOW.md`](workflow/05_DEVELOPMENT_WORKFLOW.md) - Timeline

---

## ✅ Documentation Checklist

Before you proceed, verify you have:

- [ ] Cloned the repository
- [ ] Reviewed [`../README.md`](../README.md) (root)
- [ ] Selected your role-specific starting point (above)
- [ ] Bookmarked [`ARCHIVE_INDEX.md`](ARCHIVE_INDEX.md) for reference

---

## 🚀 Next Steps

### For Frontend Development
→ Go to: [`guides/FRONTEND_DEVELOPMENT_GUIDE.md`](guides/FRONTEND_DEVELOPMENT_GUIDE.md)

### For Backend Development
→ Go to: [`../backend_django/README.md`](../backend_django/README.md)

### For System Understanding
→ Go to: [`architecture/02_TECHNICAL_ARCHITECTURE.md`](architecture/02_TECHNICAL_ARCHITECTURE.md)

### For Complete Reference
→ Go to: [`ARCHIVE_INDEX.md`](ARCHIVE_INDEX.md)

---

**Happy coding! 🚀**

---

**Document Version**: v2.0.0  
**Last Updated**: 2025-11-07  
**Status**: Phase 1 Complete  
**Maintained By**: Image Data Platform Team
