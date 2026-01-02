# Study 模組 - 快速參考指南

## 🎯 快速導航

### 模組結構
```
Study Module
├── 數據模型 (models.py)
├── 序列化層 (schemas.py)  
├── 業務邏輯 (services.py)
└── API 端點 (api.py)
```

---

## 📚 關鍵概念速查

### 1. 數據模型 (models.py)

**主要特性**：
- ✅ 扁平結構設計（無 FK 關係）
- ✅ 21 個直接字段（包含所有搜尋所需）
- ✅ 5 個複合索引 + 1 個全文搜尋索引

**字段分組**：
```
主要識別碼          patient 字段           檢查詳情           時間戳
├─ exam_id           ├─ patient_name       ├─ exam_status    ├─ order_datetime
├─ medical_record_no  ├─ patient_gender    ├─ exam_source    ├─ check_in_datetime
└─ application_order_no ├─ patient_age     ├─ exam_item      └─ report_certification_datetime
                      └─ patient_birth_date ├─ exam_description
                                          └─ equipment_type
```

**關鍵方法**：
- `to_dict()`: 轉換為 API 響應格式（時間戳轉為 ISO 8601）

---

### 2. 序列化層 (schemas.py)

**響應模式**：
```
Request  →  (驗證)  →  Response
(JSON)      Pydantic   (JSON/Dict)
```

**核心 Schema**：
| Schema | 用途 | 字段數 |
|--------|------|-------|
| StudyDetail | 詳細查詢 | 19 |
| StudyListItem | 列表搜尋 | 14 |
| StudySearchResponse | 搜尋響應 | items + count + filters |
| FilterOptions | 過濾選項 | 6 (exam_statuses, exam_sources, ...) |

---

### 3. 業務邏輯 (services.py)

**核心方法**：

#### a. `get_studies_queryset()`
```python
# 最重要的方法：原始 SQL 查詢
query_result = StudyService.get_studies_queryset(
    q='chest',                    # 文本搜尋
    exam_status='completed',      # 單選過濾
    exam_equipment=['GE', 'Siemens'],  # 多選過濾
    start_date='2024-01-01',      # 日期範圍
    limit=20,                     # 分頁
    offset=0,
    sort='order_datetime_desc'    # 排序
)
# 性能: <100ms (LIMIT/OFFSET 在 DB 層應用)
```

#### b. `get_filter_options()`
```python
# 三級快取策略
options = StudyService.get_filter_options()
# Level 1: Redis (10ms) → Level 2: DB (100ms) → Level 3: Direct (無快取)
```

#### c. 搜尋條件構建
```python
where_clause, params, order_by = StudyService._build_search_conditions(
    q='chest',
    exam_status='completed'
)
# 返回: (WHERE 子句, 參數列表, ORDER BY 子句)
```

---

### 4. API 端點 (api.py)

**端點總覽**：
```
GET /api/v1/studies/search
    ├─ 文本搜尋 (q)
    ├─ 過濾器 (exam_status, exam_source, ...)
    ├─ 分頁 (limit, offset)
    └─ 返回: {items, count, filters}

GET /api/v1/studies/export
    ├─ 格式 (csv, xlsx)
    ├─ 所有搜尋參數適用
    └─ 返回: 二進制檔案

GET /api/v1/studies/{exam_id}
    └─ 返回: 完整詳細信息

GET /api/v1/studies/filters/options
    └─ 返回: 所有可用過濾值 (快取 24H)
```

---

## 🔍 常見查詢模式

### 模式 1: 簡單文本搜尋
```python
# 搜尋所有包含 "chest" 的記錄
GET /api/v1/studies/search?q=chest&limit=20

# 代碼層
queryset = StudyService.get_studies_queryset(q='chest')
```

### 模式 2: 過濾搜尋
```python
# 搜尋已完成的 CT 掃描
GET /api/v1/studies/search?exam_status=completed&exam_source=CT

# 代碼層
queryset = StudyService.get_studies_queryset(
    exam_status='completed',
    exam_source='CT'
)
```

### 模式 3: 日期範圍搜尋
```python
# 搜尋 2024 年的所有掃描
GET /api/v1/studies/search?start_date=2024-01-01&end_date=2024-12-31

# 代碼層
queryset = StudyService.get_studies_queryset(
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

### 模式 4: 多選過濾
```python
# 搜尋 GE 或 Siemens 設備的掃描
GET /api/v1/studies/search?exam_equipment=GE&exam_equipment=Siemens

# 代碼層
queryset = StudyService.get_studies_queryset(
    exam_equipment=['GE', 'Siemens']
)
```

### 模式 5: 複雜組合查詢
```python
# 搜尋 2024 年已完成的胸部 CT，患者年齡 18-65 歲
GET /api/v1/studies/search?exam_source=CT&exam_status=completed&start_date=2024-01-01&end_date=2024-12-31&patient_age_min=18&patient_age_max=65&limit=50

# 代碼層
queryset = StudyService.get_studies_queryset(
    exam_source='CT',
    exam_status='completed',
    start_date='2024-01-01',
    end_date='2024-12-31',
    patient_age_min=18,
    patient_age_max=65,
    limit=50,
    offset=0
)
```

### 模式 6: 導出功能
```python
# 導出已完成的掃描為 Excel
GET /api/v1/studies/export?format=xlsx&exam_status=completed

# 導出選定的記錄
GET /api/v1/studies/export?format=csv&exam_ids=EXAM_001&exam_ids=EXAM_002
```

---

## ⚡ 性能速查

| 操作 | 典型時間 | 最壞情況 | 優化方式 |
|------|--------|--------|--------|
| 主鍵查詢 | <10ms | <50ms | 自動索引 |
| 分頁搜尋 | <100ms | <500ms | LIMIT/OFFSET @DB |
| 過濾選項 (cache hit) | ~10ms | N/A | Redis 24H TTL |
| 過濾選項 (cache miss) | ~100ms | ~500ms | 原始 SQL DISTINCT |
| 文本搜尋 | ~200ms | ~1000ms | ILIKE + wildcards |
| 導出 1000 筆記錄 | ~2-3s | ~5-10s | CSV/XLSX 生成 |

---

## 🛡️ 安全特性

### SQL 注入防護
```python
# ✅ 正確：參數化查詢
cursor.execute("WHERE field = %s", [user_input])

# ❌ 錯誤：字串拼接
cursor.execute(f"WHERE field = '{user_input}'")  # 危險！
```

### 輸入驗證
```python
# Pydantic 自動驗證
page_size: int = Field(20, ge=1, le=100)  # 限制 1-100
q: str = Field(None, max_length=200)      # 最大 200 字
```

---

## 🔧 調試技巧

### 啟用查詢日誌
```python
# services.py 中的 logger.debug() 會記錄 SQL 查詢
logger.debug(f"Search Query: {sql} | Params: {params}")
```

### 常見錯誤與解決方案

| 錯誤 | 原因 | 解決方案 |
|------|------|--------|
| 404 Not Found | exam_id 不存在 | 檢查 exam_id 拼寫 |
| 422 Unprocessable Entity | 參數類型錯誤 | 檢查參數類型和範圍 |
| 500 Internal Server Error | 數據庫連接失敗 | 檢查 DB 連接配置 |
| 空搜尋結果 | 查詢太具體 | 嘗試寬鬆的過濾條件 |

---

## 📖 文檔查找速查

### 尋找...請查看

| 需求 | 位置 | 文件 | 行數 |
|------|------|------|------|
| 數據模型結構 | Study 類文檔 | models.py | 20-100 |
| 字段說明 | 字段 help_text | models.py | 80-150 |
| API 端點 | @router.get() | api.py | 26+ |
| 查詢參數 | search_studies() | api.py | 85+ |
| 過濾邏輯 | _build_search_conditions() | services.py | 356+ |
| 快取策略 | get_filter_options() | services.py | 254+ |
| 異常定義 | Raises 部分 | 各文件 | 文檔 |
| 性能特性 | Performance 部分 | 各文件 | 文檔 |

---

## 🎓 學習路徑

### 初級開發者
1. 讀 models.py → 了解數據模型
2. 讀 schemas.py → 了解 API 格式
3. 試 api.py 的示例請求
4. 讀 services.py → 了解邏輯

### 中級開發者
1. 了解 _build_search_conditions() 中的 SQL 構建
2. 學習快取策略（三級快取）
3. 了解性能優化（LIMIT/OFFSET @DB）
4. 研究錯誤處理模式

### 高級開發者
1. 分析 SORT_MAPPING 的設計原則
2. 研究扁平結構 vs 標準化 SQL 的權衡
3. 優化查詢計畫和索引策略
4. 考慮監控和日誌改進

---

## 💡 最佳實踐

### DO ✅
- 使用參數化查詢（防止 SQL 注入）
- 在 DB 層應用 LIMIT/OFFSET（分頁優化）
- 利用快取減少重複查詢（24H TTL）
- 提供有意義的錯誤消息
- 記錄複雜查詢的性能指標

### DON'T ❌
- 在 Python 中進行大規模記錄過濾
- 使用 f-string 拼接 SQL
- 忽略快取未命中的情況
- 返回未驗證的用戶輸入
- 在生產環境記錄過多調試信息

---

## 🔗 重要連結

- **API 契約**: ../docs/api/API_CONTRACT.md
- **配置**: common.config.ServiceConfig
- **異常**: common.exceptions
- **導出服務**: common.export_service.ExportService
- **分頁**: common.pagination.StudyPagination

---

## 📞 快速參考代碼片段

### 搜尋所有已完成的 CT 掃描
```python
from study.services import StudyService

queryset = StudyService.get_studies_queryset(
    exam_source='CT',
    exam_status='completed',
    limit=20,
    offset=0
)
```

### 獲取單個記錄詳情
```python
study_data = StudyService.get_study_detail('EXAM_001')
```

### 獲取過濾選項
```python
filter_options = StudyService.get_filter_options()
print(filter_options.exam_statuses)
print(filter_options.exam_sources)
```

### 計算匹配記錄數
```python
count = StudyService.count_studies(
    exam_status='completed'
)
```

---

## 🎯 一頁紙速記

```
Study Module: Medical Examination Records

架構層級：
  ├─ 數據層: models.Study (21 個字段)
  ├─ 序列化層: 5 個 Schema 類 (StudyDetail, ListItem, Response, Request, FilterOptions)
  ├─ 業務層: StudyService (搜尋/過濾/導出邏輯)
  └─ API 層: 4 個 RESTful 端點 (search, export, detail, filters)

核心方法：
  • get_studies_queryset() - 原始 SQL 查詢 (<100ms)
  • get_study_detail() - 主鍵查詢 (<10ms)
  • get_filter_options() - 三級快取 (10ms ~ 500ms)

性能優化：
  • LIMIT/OFFSET @數據庫層 (分頁)
  • Redis 快取 (24H TTL 過濾選項)
  • 原始 SQL (避免 ORM 開銷)
  • 複合索引 (5 個)

安全機制：
  • SQL 參數化 (防止注入)
  • Pydantic 驗證 (輸入檢查)
  • 異常映射 (404/500 狀態碼)

查詢模式：
  文本搜尋 → ILIKE 9 個字段
  過濾器 → IN 子句/精確匹配
  日期範圍 → >= / <= 比較
  多選 → 逗號分隔數組參數
```

---

## 📚 進一步閱讀

詳細文檔位置：
- **完整總結**: `./DOCUMENTATION_SUMMARY.md`
- **更新報告**: `../STUDY_MODULE_UPDATES.md`
- **類文檔**: 每個 .py 文件的模組/類級文檔
- **方法文檔**: 每個方法的完整文檔字符串

---

**最後更新**: 2024-12-17  
**版本**: 1.0  
**難度級別**: ⭐⭐⭐ (中等)

