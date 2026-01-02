# @report 模組 - 快速參考指南

## 模型快速查詢

### Report (報告主模型)
```python
from report.models import Report

# 查詢最新版本
report = Report.objects.get(uid='uid_001', is_latest=True)

# 搜尋報告
reports = Report.objects.filter(
    title__icontains='CT',
    is_latest=True
).order_by('-verified_at')

# 列出所有報告類型
types = Report.objects.values_list('report_type', flat=True).distinct()
```

### ReportVersion (版本歷史)
```python
from report.models import ReportVersion

# 查詢某報告的版本歷史
versions = ReportVersion.objects.filter(
    report__report_id='exam_123'
).order_by('-version_number')

# 取得特定版本
v1 = ReportVersion.objects.get(report_id='uid_001', version_number=1)
```

### ReportSummary (報告摘要)
```python
from report.models import ReportSummary

# 從報告存取摘要
summary = report.summary
print(summary.short_summary)
print(summary.key_points)

# 建立摘要
ReportSummary.objects.create(
    report=report,
    short_summary='簡短摘要...',
    long_summary='詳細摘要...',
    key_points=['要點1', '要點2']
)
```

### AIAnnotation (AI 註解)
```python
from report.models import AIAnnotation

# 查詢報告的 NER 註解
annotations = report.annotations.filter(annotation_type='NER')

# 建立註解
AIAnnotation.objects.create(
    report=report,
    annotation_type='NER',
    content='{"entities": [...]}',
    metadata={'model': 'spacy_v1', 'confidence': 0.95}
)

# 轉換為字典
data = annotation.to_dict()
```

### ExportTask (匯出任務)
```python
from report.models import ExportTask
from datetime import datetime, timedelta

# 建立匯出任務
task = ExportTask.objects.create(
    task_id='export_001',
    user_id='user_123',
    query_params={'filters': {}},
    export_format='csv',
    status='pending',
    expires_at=datetime.now() + timedelta(days=7)
)

# 查詢進度
print(f"進度: {task.get_progress_percent()}%")
print(f"狀態: {task.get_status_display_zh()}")

# 更新進度
task.processed_records = 50
task.save(update_fields=['processed_records'])
```

## Service 快速查詢

### ReportService 常用方法

```python
from report.service import ReportService

# 導入或更新報告
report, is_new, action = ReportService.import_or_update_report(
    uid='uid_001',
    title='報告標題',
    content='報告內容',
    report_type='CT',
    source_url='https://...'
)

# 搜尋報告
results = ReportService.search_reports(query='關鍵字', limit=50)

# 取得過濾選項
filters = ReportService.get_filter_options()

# 進階搜尋
queryset = ReportService.get_reports_queryset(
    q='關鍵字',
    report_type='CT',
    date_from='2024-01-01'
)

# 計算內容雜湊
hash_val = ReportService.calculate_content_hash('內容')

# 處理內容 (正規化)
processed = ReportService.process_content('原始內容')

# 安全截斷文本
preview = ReportService.safe_truncate(content, max_length=500)
```

## API 端點快速參考

### 導入報告
```bash
POST /api/v1/reports/import
Content-Type: application/json

{
    "uid": "uid_001",
    "title": "CT 掃描報告",
    "content": "報告內容...",
    "report_type": "CT",
    "source_url": "https://..."
}
```

### 搜尋報告
```bash
GET /api/v1/reports/search?q=CT&limit=20&sort=verified_at_desc

# 過濾選項
GET /api/v1/reports/search?q=CT&report_type=CT&date_from=2024-01-01

# 分頁搜尋
GET /api/v1/reports/search/paginated?q=CT&page=1&page_size=20
```

### 進階搜尋
```bash
POST /api/v1/reports/search/advanced
Content-Type: application/json

{
    "mode": "basic",
    "basic": {"text": "CT 掃描"},
    "page": 1,
    "page_size": 20
}
```

### 獲取報告詳情
```bash
GET /api/v1/reports/{uid}
GET /api/v1/reports/study/{exam_id}
GET /api/v1/reports/{report_id}/versions
GET /api/v1/reports/{uid}/annotations
```

### 獲取最新報告
```bash
GET /api/v1/reports/latest?limit=20
```

### 獲取過濾選項
```bash
GET /api/v1/reports/filters/options
```

## 常用查詢模式

### 查詢最新版本
```python
# ✅ 推薦
reports = Report.objects.filter(is_latest=True)

# ❌ 不推薦 (可能包含舊版本)
reports = Report.objects.all()
```

### 按修改時間排序
```python
# ✅ 推薦 (考慮到 NULL 值)
reports = Report.objects.order_by('-verified_at', '-created_at')

# ❌ 不推薦 (可能排序不正確)
reports = Report.objects.order_by('-updated_at')
```

### 全文搜尋
```python
from django.db.models import Q

# ✅ 推薦 (多欄位搜尋)
results = Report.objects.filter(
    Q(title__icontains=query) |
    Q(content_processed__icontains=query) |
    Q(report_id__icontains=query)
)

# ✅ 備選 (使用 SearchVector)
from django.contrib.postgres.search import SearchQuery
results = Report.objects.filter(
    search_vector=SearchQuery(query)
)
```

### 批量操作
```python
# ✅ 推薦 (事務保證一致性)
from django.db import transaction

@transaction.atomic
def batch_process():
    for item in items:
        # 處理每個項目
        pass

# ✅ 備選 (批量創建)
Report.objects.bulk_create([report1, report2, ...])
```

## 狀態和類型常數

### ExportTask 狀態
```python
'pending'      # 待處理
'processing'   # 處理中
'completed'    # 已完成
'failed'       # 失敗
'cancelled'    # 已取消
```

### ExportTask 格式
```python
'csv'   # CSV
'json'  # JSON
'xlsx'  # Excel
'xml'   # XML
```

### ReportVersion 變更類型
```python
'create'       # 初始建立
'update'       # 內容更新
'verify'       # 驗證確認
'deduplicate'  # 去重合併
```

## 錯誤處理

### 常見異常

```python
# 報告不存在
try:
    report = Report.objects.get(uid='unknown')
except Report.DoesNotExist:
    # 處理不存在的情況
    pass

# 多個版本存在 (應不會發生)
try:
    report = Report.objects.get(report_id='exam_123', is_latest=True)
except Report.MultipleObjectsReturned:
    # 數據一致性錯誤，應通知管理員
    pass

# 驗證錯誤
from report.services import AdvancedQueryValidationError
try:
    result = ReportService.advanced_search(payload)
except AdvancedQueryValidationError as e:
    # 提示用戶查詢格式錯誤
    pass
```

## 效能最佳實踐

### 1. 使用 select_related 和 prefetch_related
```python
# ❌ N+1 查詢問題
reports = Report.objects.filter(is_latest=True)
for report in reports:
    print(report.summary.short_summary)  # 每行都查詢一次

# ✅ 優化後
reports = Report.objects.filter(is_latest=True).select_related('summary')
```

### 2. 利用索引
```python
# ✅ 利用 idx_is_latest_verified_at 索引
reports = Report.objects.filter(is_latest=True).order_by('-verified_at')

# ❌ 索引不適用
reports = Report.objects.filter(is_latest=False).order_by('-created_at')
```

### 3. 限制結果集
```python
# ✅ 只取需要的欄位
reports = Report.objects.only('uid', 'title', 'created_at')

# ✅ 分頁查詢
reports = Report.objects.filter(is_latest=True)[0:20]

# ❌ 取所有欄位和所有記錄
reports = Report.objects.all().values()
```

## 調試技巧

### 查看生成的 SQL
```python
from django.db import connection
from django.test.utils import CaptureQueriesContext

with CaptureQueriesContext(connection) as queries:
    results = Report.objects.filter(is_latest=True)[:10]
    print(f"執行了 {len(queries)} 個查詢")
    for q in queries:
        print(q['sql'])
```

### 檢查模型定義
```python
# 查看所有字段
from django.apps import apps
Report = apps.get_model('report', 'Report')
for field in Report._meta.get_fields():
    print(f"{field.name}: {field}")
```

### 查看 ORM 翻譯
```python
qs = Report.objects.filter(title__icontains='test')
print(qs.query)  # 查看生成的 SQL SELECT 語句
```

## 常見陷阱

### 1. ✓ 記得過濾 is_latest
```python
# ✓ 正確
report = Report.objects.get(uid='uid_001', is_latest=True)

# ✗ 錯誤 (可能返回舊版本)
report = Report.objects.get(uid='uid_001')
```

### 2. ✓ NULL 值排序
```python
# ✓ 考慮 NULL 值
Report.objects.order_by('-verified_at', '-created_at')

# ✗ 可能遺漏未驗證的報告
Report.objects.filter(verified_at__isnull=False).order_by('-verified_at')
```

### 3. ✓ 事務保護
```python
# ✓ 使用事務
@transaction.atomic
def create_with_version():
    report = Report.objects.create(...)
    ReportVersion.objects.create(...)

# ✗ 可能出現不一致狀態
report = Report.objects.create(...)
ReportVersion.objects.create(...)  # 若失敗，Report 已建立
```

---

**快速參考版本**: 1.0
**最後更新**: 2024年12月

