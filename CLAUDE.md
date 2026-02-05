# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**專案名稱**: Medical Imaging Management System - Django Backend
**用途**: Django + PostgreSQL 後端，提供醫學影像報告管理 REST API
**技術棧**: Django 5.2, Django Ninja, PostgreSQL, Funboost (async tasks)

**Key Characteristics**:
- Three-layer architecture (API → Service → Data)
- Django Ninja for type-safe APIs
- Custom exception hierarchy for domain errors
- Page/page_size pagination model (v1.1.0)

---

## Development Commands

### 環境設定
```bash
# Windows (PowerShell)
python manage.py runserver 8001

# WSL (PostgreSQL connection required)
source .venv-linux/bin/activate && python manage.py migrate
```

### Git 工作流
```bash
git checkout -b feature/[name]
git commit -m "type(scope): description"
```

---

## Verification Commands

**🎯 核心原則**: 每次修改後，Claude 必須執行驗證

### 必執行驗證
```bash
# Replace <module> with: common | imports | project | report | study | ai | tests
uvx ty check <module>
uvx ruff check <module> --fix
uvx ruff format <module>

# 測試
python manage.py test

# 資料庫遷移檢查
python manage.py makemigrations --check --dry-run
```

### 驗證清單
修改程式碼後，依序執行：
- [ ] 型別檢查通過 (`uvx ty check`)
- [ ] Lint 無警告 (`uvx ruff check --fix`)
- [ ] 格式化完成 (`uvx ruff format`)
- [ ] 測試通過 (`python manage.py test`)

### 驗證失敗處理
```
驗證失敗 → 檢查錯誤訊息 → 修復問題 → 重新驗證 → 全部通過 ✅
```

---

## Anti-Patterns & Learnings

**📝 活文件規則**: Claude 犯錯時立即新增記錄

### 錯誤行為紀錄（持續更新）

| 日期 | ❌ 錯誤行為 | ✅ 正確做法 |
|------|------------|------------|
| 2026-02-05 | Migration 直接使用 `CreateModel` 建立已存在的表 | 使用 `ConditionalCreateModel` 先檢查 `information_schema.tables` |
| 2026-02-05 | Migration 直接使用 `AddField` 新增已存在的欄位 | 使用 `ConditionalAddField` 先檢查 `information_schema.columns` |
| 2026-02-05 | Migration 直接使用 `AddIndex` 建立已存在的索引 | 使用 `ConditionalAddIndex` 先檢查 `pg_indexes` |
| 2026-02-05 | Migration 使用 `RunSQL` 無條件執行 DDL | 改用 `RunPython` 搭配條件檢查函數 |

### 禁止事項

- ❌ 修改已提交的 migration 檔案
- ❌ Migration 中直接執行 DDL 而不檢查資料庫狀態
- ❌ 跳過品質檢查 (`uvx ty check`, `uvx ruff`)
- ❌ 在 main 分支直接開發
- ❌ 使用 pip（改用 uv）

### Migration 條件操作模式

當資料庫可能處於部分狀態時，使用以下模式：

```python
# 檢查表是否存在
def table_exists(connection, table_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            )
        """, [table_name])
        return cursor.fetchone()[0]

# 檢查欄位是否存在
def column_exists(connection, table_name, column_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s AND column_name = %s
            )
        """, [table_name, column_name])
        return cursor.fetchone()[0]

# 檢查索引是否存在
def index_exists(connection, index_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_indexes WHERE indexname = %s
            )
        """, [index_name])
        return cursor.fetchone()[0]
```

---

## Architecture

### 架構概覽
```
┌─────────────────────────────────────┐
│   API Layer (*_api.py)              │  ← Django Ninja endpoints
├─────────────────────────────────────┤
│   Service Layer (*_service.py)      │  ← Business logic
├─────────────────────────────────────┤
│   Data Layer (models.py)            │  ← Django ORM models
└─────────────────────────────────────┘
```

### 核心模組

| 目錄 | 用途 |
|------|------|
| `report/` | 報告搜尋和管理 (Report, AIAnnotation) |
| `ai/` | AI 分類工作流 (Guideline, BatchTask, Review) |
| `project/` | 專案管理 |
| `common/` | 共用工具、中介層 |
| `tests/` | 測試檔案 |

---

## Error Handling

### 例外類別
```
ServiceError (base)
├── StudyNotFoundError    → 報告不存在
├── ValidationError       → 驗證失敗
├── BulkImportError       → 批次匯入失敗
└── InvalidSearchParameterError → 搜尋參數錯誤
```

### 常見錯誤

| 錯誤 | 原因 | 解決 |
|------|------|------|
| `DuplicateTable` | Migration 建立已存在的表 | 使用 `ConditionalCreateModel` |
| `DuplicateColumn` | Migration 新增已存在的欄位 | 使用 `ConditionalAddField` |
| `relation already exists` | Index 已存在 | 使用 `ConditionalAddIndex` |
| `psycopg2.OperationalError` | PostgreSQL 未啟動 | 啟動 PostgreSQL 服務 |

### 除錯指令
```bash
# 查看 migration 狀態
python manage.py showmigrations

# 檢查資料庫連線
python manage.py dbshell

# 查看 migration SQL
python manage.py sqlmigrate <app> <migration_number>
```

---

## References

| 文件 | 說明 |
|------|------|
| `API_DOCUMENTATION.md` | API 完整文件 |
| `/api/v1/docs` | Swagger UI 互動文件 |
| `docs/migration/` | 架構遷移說明 |

---

**最後更新**: 2026-02-05
