# Django 後端 - 醫療影像管理系統

**狀態**: 第一階段 - 基礎建設（7 天務實實作計畫）

這是醫療影像後端的 Django + PostgreSQL 版本，取代原有的 FastAPI + DuckDB 版本。

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

執行完整的 API 契約測試：

```bash
# 執行所有測試
python manage.py test

# 執行特定測試模組
python manage.py test tests.test_api_contract

# 以詳細輸出執行
python manage.py test -v 2

# 執行並檢查覆蓋率（如已安裝 coverage）
coverage run --source='.' manage.py test
coverage report
```

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

## 下一步

第一階段（基礎建設）後：

- **第二階段**（第 4-5 天）：新增報告和分析端點
- **第三階段**（第 6 天）：資料遷移和前端切換
- **第四階段**（第 7 天）：錯誤處理、日誌記錄、正式環境驗證

每個階段都建立在第一階段建立的 Studies 模式之上。

---

**狀態**: 準備進行第一階段實作
**預估天數**: 3 天（7 天計畫的第 1-3 天）
**風險等級**: 低（務實、可測試、漸進式）
