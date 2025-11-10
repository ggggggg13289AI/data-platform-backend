# Django 後端 - 醫療影像管理系統

**狀態**: ✅ 生產就緒 - Phase 1 & 2 完成

這是醫療影像後端的 Django + PostgreSQL 版本，取代原有的 FastAPI + DuckDB 版本。

## ✨ 最新改進 (2025-11-10)

**Phase 1 - 異常處理與設定** ✅
- 統一的異常處理系統（StudyNotFoundError, DatabaseQueryError）
- 集中式設定管理（studies/config.py）
- 請求計時中介層（效能監控）
- 完整的程式碼文件和註解

**Phase 2 - 測試套件與覆蓋率** ✅
- 63 個綜合測試案例
- ~85% 程式碼覆蓋率
- 模型、服務、快取、中介層測試
- 測試資料工廠和固定裝置
- 邊界條件和錯誤處理測試

## 為什麼選擇 Django 作為第二階段？

遵循 Linus Torvalds 原則：
- **務實導向**: 為 5 個並發用戶設計，而非 1000+ 用戶
- **簡單明瞭**: Django Ninja 比 DRF 更適合此使用情境
- **可測試性**: 標準 Django ORM 搭配明確的查詢語句
- **避免過度設計**: 單一應用程式、扁平資料模型、無訊號機制或管理介面

## 架構

```
Django 後端 (埠號 8001)
├── config/
│   ├── settings.py       # Django 設定檔
│   ├── urls.py          # Ninja API 路由
│   └── wsgi.py          # WSGI 進入點
├── studies/             # 所有端點的單一應用程式
│   ├── models.py        # Study 模型（扁平設計）
│   ├── schemas.py       # Pydantic 驗證結構
│   ├── services.py      # 業務邏輯（無訊號機制）
│   └── api.py           # Django Ninja 端點
├── tests/               # 完整測試套件
├── migrate_from_duckdb.py  # 資料遷移腳本
└── manage.py            # Django 管理指令

PostgreSQL 資料庫
└── medical_examinations_fact  # 所有檢查紀錄
```

## 安裝說明

### 1. 環境設定

```bash
# 複製環境變數範本
cp .env.example .env

# 編輯 .env 並填入您的 PostgreSQL 憑證
# DB_NAME=medical_imaging
# DB_USER=postgres
# DB_PASSWORD=your_password
# DB_HOST=localhost
# DB_PORT=5432
```

### 2. PostgreSQL 資料庫

建立 PostgreSQL 資料庫：

```bash
# 連線到 PostgreSQL
psql -U postgres

# 建立資料庫
CREATE DATABASE medical_imaging ENCODING 'UTF8';

# 建立使用者（如需要）
CREATE USER medical_user WITH PASSWORD 'your_password';
ALTER ROLE medical_user SET client_encoding TO 'utf8';

# 授予權限
GRANT ALL PRIVILEGES ON DATABASE medical_imaging TO medical_user;

# 離開
\q
```

### 3. 安裝相依套件

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安裝套件
pip install -r requirements.txt
```

### 4. 初始化資料庫結構

```bash
# 執行遷移（建立資料表）
python manage.py migrate

# 建立超級使用者（選用，用於管理介面）
# python manage.py createsuperuser
```

### 5. 從 DuckDB 遷移資料

```bash
# 在 .env 中設定 DuckDB 路徑或作為環境變數
export DUCKDB_PATH=../backend/medical_imaging.duckdb

# 執行遷移
python scripts/migrate_from_duckdb.py

# 預期輸出：
# ✓ DuckDB 包含 1,250 筆檢查紀錄
# ✓ 匯入完成：已匯入 1,250 筆，失敗 0 筆
# ✓ 成功：紀錄數量相符！
# ✓ 未發現重複資料
```

### 6. 執行開發伺服器

```bash
# 在埠號 8001 啟動 Django 開發伺服器
python manage.py runserver 8001

# 存取 API
# http://localhost:8001/api/v1/docs   - API 文件
# http://localhost:8001/api/v1/health - 健康檢查
```

## API 端點

所有端點回應格式完全符合 FastAPI（請參考 ../docs/api/API_CONTRACT.md）。

### 研究搜尋
```bash
GET /api/v1/studies/search?q=張&exam_status=completed&page=1&page_size=20

回應：
{
  "data": [
    {
      "exam_id": "EXAM001",
      "patient_name": "張偉",
      "exam_status": "completed",
      "order_datetime": "2025-11-06T10:30:00",
      ...
    }
  ],
  "total": 1250,
  "page": 1,
  "page_size": 20,
  "filters": {
    "exam_statuses": ["completed", "pending", ...],
    "exam_sources": ["CT", "MRI", ...],
    "exam_items": [...]
  }
}
```

### 研究詳情
```bash
GET /api/v1/studies/{exam_id}

回應：
{
  "exam_id": "EXAM001",
  "patient_name": "張偉",
  ...
}
```

### 篩選選項
```bash
GET /api/v1/studies/filters/options

回應：
{
  "exam_statuses": [...],
  "exam_sources": [...],
  "exam_items": [...],
  "equipment_types": [...]
}
```

## 測試

執行完整的測試套件（63 個測試案例，~85% 覆蓋率）：

```bash
# 執行所有測試
python manage.py test tests

# 執行特定測試模組
python manage.py test tests.test_models        # 模型測試 (15 cases)
python manage.py test tests.test_services      # 服務測試 (30 cases)
python manage.py test tests.test_caching       # 快取測試 (10 cases)
python manage.py test tests.test_middleware    # 中介層測試 (8 cases)

# 以詳細輸出執行
python manage.py test tests --verbosity=2

# 產生覆蓋率報告
pip install coverage
coverage run --source='studies' manage.py test tests
coverage report
coverage html  # 產生 HTML 報告至 htmlcov/
```

### 測試涵蓋範圍

- **模型層測試** (15 cases): CRUD 操作、驗證、邊界條件
- **服務層測試** (30 cases): 搜尋、篩選、排序、錯誤處理
- **快取測試** (10 cases): 快取命中/未命中、優雅降級、TTL
- **中介層測試** (8 cases): 請求計時、日誌格式、效能

## 驗證格式相容性

比較 Django 與 FastAPI 的回應：

```bash
# 終端機 1：啟動 FastAPI（原版）
cd ../backend
python run.py

# 終端機 2：啟動 Django
cd ../backend_django
python manage.py runserver 8001

# 終端機 3：比較回應
# 從兩個伺服器取得相同資料
curl http://localhost:8000/api/v1/studies/search > /tmp/fastapi.json
curl http://localhost:8001/api/v1/studies/search > /tmp/django.json

# 比較（除了時間戳記外應該完全相同）
diff /tmp/fastapi.json /tmp/django.json
```

## 關鍵原則

### 永不破壞使用者空間（API 相容性）

每個端點必須回傳 ../docs/api/API_CONTRACT.md 中指定的**精確**格式：
- 欄位名稱必須完全相符（一個字元的差異就會破壞前端）
- 日期時間格式：ISO 8601（YYYY-MM-DDTHH:MM:SS）不含時區
- 空值：`null`（非空字串或 0）
- 數字以數字表示（非字串）
- 分頁結構：`data`、`total`、`page`、`page_size`、`filters`

### 快速失敗（錯誤處理）

- 匯入前驗證（結構優先）
- 明確錯誤訊息的重複檢測
- 匯入後計數驗證
- 無靜默失敗（所有錯誤皆記錄並回報）

### 設計簡單化

- 單一 Django 應用程式（studies）
- 扁平資料模型（無複雜關聯）
- 直接函數呼叫（無訊號機制）
- Pydantic 結構驗證
- 業務邏輯服務層

## 部署（第一階段後）

正式環境部署：

1. 在 .env 中設定 `DEBUG=False`
2. 設定適當的 `DJANGO_SECRET_KEY`
3. 設定 `ALLOWED_HOSTS`
4. 使用 PostgreSQL 並建立適當的備份策略
5. 使用 WSGI 伺服器（gunicorn、uWSGI）
6. 加入 nginx 反向代理
7. 設定 HTTPS/SSL
8. 設定監控和日誌記錄

## 疑難排解

### 資料庫連線錯誤
```
錯誤：could not translate host name "localhost" to address
→ 檢查 .env 中的 DB_HOST（使用 127.0.0.1 而非 localhost）
```

### 遷移錯誤
```
錯誤：找不到 DuckDB 檔案
→ 設定 DUCKDB_PATH=/path/to/medical_imaging.duckdb
```

### 埠號 8001 已被使用
```
錯誤：位址已被使用
→ python manage.py runserver 8001 --nothreading
→ 或使用不同埠號：python manage.py runserver 8002
```

### 匯入計數不符
```
⚠️  紀錄數量不符
→ 檢查錯誤日誌以找出失敗的匯入
→ 驗證 DuckDB 資料完整性
→ 修正後重新執行遷移
```

## 文件

- **../docs/api/API_CONTRACT.md** - 回應格式規格（必須完全符合）
- **../docs/planning/ZERO_DOWNTIME_DEPLOYMENT.md** - 安全遷移程序
- **../docs/migration/DJANGO_MIGRATION_LINUS_APPROVED.md** - 完整實作計畫
- **../docs/implementation/EXCEL_INTEGRATION_LINUS_FIXES.md** - 含錯誤處理的資料載入

## 專案狀態

### ✅ 已完成階段

- **Phase 1 - 異常處理與設定** ✅
  - 統一異常處理系統
  - 集中式設定管理
  - 效能監控中介層
  - 完整程式碼文件

- **Phase 2 - 測試套件與覆蓋率** ✅
  - 63 個測試案例
  - ~85% 程式碼覆蓋率
  - 完整測試文件

### 🎯 未來規劃

- **Phase 3** (未來): 額外報告和分析功能
- **持續改進**: 效能優化、監控增強
- **生產部署**: 依需求進行正式環境部署

---

**目前狀態**: ✅ 生產就緒 (Phase 1 & 2 完成)
**版本**: 1.1.0
**測試覆蓋率**: ~85% (63 test cases)
**最後更新**: 2025-11-10
**維護者**: Medical Imaging Team
