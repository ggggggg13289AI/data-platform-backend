# 報告模組 (@report) 使用指南

完整的中文文檔規格化說明，遵循 pandas DataFrame 文檔風格。

## 目錄結構

```
report/
├── __init__.py           # 模組初始化
├── models.py             # 資料模型定義
├── schemas.py            # API Schema 定義
├── api.py                # API 端點定義
├── service.py            # 業務邏輯層
├── signals.py            # Django 信號定義
├── apps.py               # 應用配置
└── migrations/           # 資料庫遷移
```

## 核心概念

### 數據結構

報告模組實現了二維、大小可變、可能異質的表格式資料結構，類似 pandas DataFrame：

- **Report**: 主報告模型，儲存當前最新版本
- **ReportVersion**: 版本歷史，追蹤所有修改
- **ReportSummary**: 報告摘要，優化展示效能
- **ReportSearchIndex**: 搜尋索引，加速全文搜尋
- **AIAnnotation**: AI 註解，儲存分析結果
- **ExportTask**: 匯出任務，追蹤批量操作

### 關鍵特性

#### 1. 內容去重 (Content-based Deduplication)

使用 SHA256 雜湊進行智能去重：

```python
# 同一 UID，相同內容：保留最新版本
if existing_report.content_hash == content_hash:
    # 保留驗證時間戳較新的版本
    
# 同一 UID，不同內容：建立新版本
else:
    # 自動遞增版本號，舊版本標記為 is_latest=False
```

#### 2. 版本控制

每個報告更新都會：
- 遞增版本號
- 創建 ReportVersion 快照記錄
- 標記舊版本為 `is_latest=False`

#### 3. 全文搜尋

支援多個欄位的複合搜尋：

```python
# 搜尋範圍
- report_id: 內部報告編號
- uid: 爬蟲標識符
- title: 報告標題
- chr_no: 字符代碼
- mod: 模式類型
- content_processed: 處理內容
```

## 使用範例

### 導入報告

```python
from report.service import ReportService
from datetime import datetime

report, is_new, action = ReportService.import_or_update_report(
    uid='uid_001',
    report_id='exam_123',
    title='CT 掃描報告',
    content='報告完整內容...',
    report_type='CT',
    source_url='https://example.com/reports/001',
    verified_at=datetime.now()
)

print(f"新建: {is_new}, 操作: {action}")
```

### 搜尋報告

```python
# 簡單搜尋
reports = ReportService.search_reports(
    query='CT 掃描',
    limit=50
)

# 進階搜尋
queryset = ReportService.get_reports_queryset(
    q='關鍵字',
    report_type='CT',
    report_format=['PDF', 'HTML'],
    date_from='2024-01-01',
    date_to='2024-12-31',
    sort='verified_at_desc'
)
```

### 查詢版本歷史

```python
from report.models import ReportVersion

# 取得某報告的所有版本
versions = ReportVersion.objects.filter(
    report__report_id='exam_123'
).order_by('-version_number')

for v in versions:
    print(f"v{v.version_number}: {v.change_type} at {v.changed_at}")
```

### 匯出報告

```python
from report.models import ExportTask
from datetime import datetime, timedelta

# 建立匯出任務
task = ExportTask.objects.create(
    task_id='export_001',
    user_id='user_123',
    query_params={'filters': {'report_type': 'CT'}},
    export_format='csv',
    status='pending',
    expires_at=datetime.now() + timedelta(days=7)
)

# 查詢進度
print(f"進度: {task.get_progress_percent()}%")
```

### AI 註解

```python
from report.models import AIAnnotation

# 建立 NER 註解
annotation = AIAnnotation.objects.create(
    report_id='uid_001',
    annotation_type='NER',
    content='{"entities": [{"text": "患者", "type": "PERSON"}]}',
    metadata={'model': 'spacy_ner_v1', 'confidence': 0.95}
)

# 查詢報告的所有 NER 註解
annotations = report.annotations.filter(annotation_type='NER')
```

## API 端點

### 導入報告

```
POST /api/v1/reports/import
Content-Type: application/json

{
    "uid": "uid_001",
    "title": "CT 掃描報告",
    "content": "報告內容...",
    "report_type": "CT",
    "source_url": "https://example.com/reports/001",
    "report_id": "exam_123"
}

Response:
{
    "uid": "uid_001",
    "report_id": "exam_123",
    "is_new": true,
    "action": "create",
    "version_number": 1
}
```

### 搜尋報告

```
GET /api/v1/reports/search?q=CT&limit=20&sort=verified_at_desc

Response:
[
    {
        "uid": "uid_001",
        "report_id": "exam_123",
        "title": "CT 掃描報告",
        "report_type": "CT",
        "version_number": 1,
        "is_latest": true,
        "created_at": "2024-01-15T10:30:00",
        "verified_at": "2024-01-15T11:00:00",
        "content_preview": "報告概要...",
        "content_raw": "完整內容..."
    }
]
```

### 進階搜尋

```
POST /api/v1/reports/search/advanced
Content-Type: application/json

{
    "mode": "basic",
    "basic": {"text": "CT 掃描"},
    "filters": {
        "report_type": "CT",
        "date_from": "2024-01-01",
        "date_to": "2024-12-31"
    },
    "page": 1,
    "page_size": 20
}

Response:
{
    "items": [...],
    "total": 150,
    "page": 1,
    "page_size": 20,
    "pages": 8,
    "filters": {
        "report_types": ["CT", "MRI", "XRay"],
        "report_statuses": ["completed", "pending"],
        "mods": ["imaging", "lab"],
        "verified_date_range": {
            "start": "2024-01-01",
            "end": "2024-12-31"
        }
    }
}
```

### 獲取報告詳情

```
GET /api/v1/reports/{uid}

Response:
{
    "uid": "uid_001",
    "report_id": "exam_123",
    "title": "CT 掃描報告",
    "report_type": "CT",
    "version_number": 1,
    "is_latest": true,
    "created_at": "2024-01-15T10:30:00",
    "verified_at": "2024-01-15T11:00:00",
    "content_preview": "報告概要...",
    "content_raw": "完整內容...",
    "source_url": "https://example.com/reports/001"
}
```

### 獲取版本歷史

```
GET /api/v1/reports/{report_id}/versions

Response:
[
    {
        "version_number": 2,
        "changed_at": "2024-01-16T10:00:00",
        "verified_at": "2024-01-16T10:30:00",
        "change_type": "update",
        "change_description": "內容更新"
    },
    {
        "version_number": 1,
        "changed_at": "2024-01-15T10:00:00",
        "verified_at": "2024-01-15T11:00:00",
        "change_type": "create",
        "change_description": "初始建立"
    }
]
```

## 資料庫結構

### 索引策略

為了確保查詢效能，建立了以下索引：

#### Report 模型

| 索引名稱 | 欄位 | 用途 |
|---------|------|------|
| 主鍵 | uid | 快速 UID 查詢 |
| idx_content_hash_verified_at | (content_hash, verified_at) | 去重判定 |
| idx_source_url_verified_at | (source_url, verified_at) | 來源追蹤 |
| idx_is_latest_verified_at | (is_latest, -verified_at) | 最新版本查詢 |
| idx_report_type | report_type | 類型過濾 |
| idx_search_vector_gin | search_vector | 全文搜尋 |

#### ReportVersion 模型

| 索引名稱 | 欄位 | 用途 |
|---------|------|------|
| 複合唯一 | (report, version_number) | 版本唯一性 |
| idx_report_version_number | (report, -version_number) | 版本查詢 |
| idx_version_content_hash | content_hash | 內容查詢 |
| idx_version_verified_at | verified_at | 時間範圍 |

#### ExportTask 模型

| 索引名稱 | 欄位 | 用途 |
|---------|------|------|
| idx_user_created_at | (user_id, -created_at) | 用戶任務查詢 |
| idx_status_created_at | (status, created_at) | 狀態過濾 |
| idx_expires_at | expires_at | 過期清理 |
| idx_format_created_at | (export_format, -created_at) | 格式統計 |

## 設計原則

### 1. Good Taste 編碼

消除特殊情況處理，使用資料結構驅動邏輯：

```python
# ❌ 不推薦：多層 if-else
if status == 'pending':
    # ...
elif status == 'processing':
    # ...
elif status == 'completed':
    # ...

# ✅ 推薦：資料驅動
STATUS_HANDLERS = {
    'pending': handle_pending,
    'processing': handle_processing,
    'completed': handle_completed,
}
handler = STATUS_HANDLERS.get(status)
if handler:
    handler()
```

### 2. 原子性事務

使用 `@transaction.atomic` 保障多步操作的一致性：

```python
@transaction.atomic
def import_or_update_report(...):
    # 所有數據庫操作在一個事務中
    # 若任何步驟失敗，整個操作回滾
```

### 3. 延遲加載 (Lazy Loading)

QuerySet 是延遲執行的，避免不必要的數據庫查詢：

```python
# SQL 還未執行
queryset = Report.objects.filter(is_latest=True)

# 在此處 SQL 才被執行
results = list(queryset)
```

### 4. N+1 查詢優化

使用 `select_related` 和 `prefetch_related` 避免 N+1 問題：

```python
# ✅ 優化後：2 個查詢
reports = Report.objects.filter(is_latest=True)
study_map = _batch_load_studies(report_ids)
```

## 遺留系統相容性

報告模型保留了多個遺留系統欄位以確保向後相容性：

- `chr_no`: 字符代碼
- `mod`: 模式/類型代碼
- `report_date`: 報告日期字符串
- `metadata`: 通用元資料 JSON

這些欄位允許系統逐步遷移，而不需一次性更改所有代碼。

## 效能考量

### 查詢優化

- 複合索引支援 WHERE 和 ORDER BY 的多欄位條件
- `is_latest` 欄位在索引中優先，加速版本過濾
- 排序字段包含在複合索引中，支援 Index-Only Scan

### 儲存優化

- 使用去正規化設計減少 JOIN 操作
- `content_processed` 預計算供全文搜尋使用
- SearchIndex 表單獨維護，可異步更新

### 快取策略

- `get_filter_options()` 方法支援 Redis 快取
- 快取 TTL 設置為 24 小時
- Cache 不可用時自動 fallback 到數據庫

## 常見問題

### Q: 如何恢復到舊版本？

**A**: 查詢 ReportVersion 取得舊版本的內容，然後：

```python
from report.models import Report, ReportVersion

# 查詢舊版本
old_version = ReportVersion.objects.get(
    report__report_id='exam_123',
    version_number=1
)

# 建立新版本
report = old_version.report
report.content_raw = old_version.content_raw
report.content_hash = old_version.content_hash
report.version_number += 1
report.save()

# 創建版本記錄
ReportVersion.objects.create(
    report=report,
    version_number=report.version_number,
    content_raw=old_version.content_raw,
    content_hash=old_version.content_hash,
    change_type='update',
    change_description='恢復到舊版本'
)
```

### Q: 如何批量導入報告？

**A**: 使用 `migrate_from_legacy_db` 方法：

```python
stats = ReportService.migrate_from_legacy_db(
    legacy_db_path='/path/to/legacy.db',
    batch_size=500,
    skip_patient_info=False
)

print(f"成功: {stats['created']}, 更新: {stats['updated']}")
```

### Q: 搜尋效能如何優化？

**A**: 

1. 使用 `select_related()` 加載相關数據
2. 利用 PostgreSQL 全文搜尋而非 Python 過濾
3. 設置適當的 `limit` 和 `offset`
4. 針對常用查詢建立複合索引

## 參考資訊

- 模型定義: `models.py`
- API Schema: `schemas.py`
- API 端點: `api.py`
- 業務邏輯: `service.py`
- 信號定義: `signals.py`

