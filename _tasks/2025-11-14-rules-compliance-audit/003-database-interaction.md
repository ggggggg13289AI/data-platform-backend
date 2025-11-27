# 003 資料庫互動與安全（OK）

依據：`.cursor/rules/django-database-interaction-rules.mdc`

## OK：參數化原生 SQL 與 DB 端分頁
- `StudyService.get_studies_queryset`：
  - WHERE 條件以 `%s` 佔位（含 IN 子句多個 `%s`）
  - `LIMIT/OFFSET` 於 DB 端處理，避免全量載入
  - `sort` 僅允許白名單（`order_datetime_*` / `patient_name_asc`）

## OK：ORM 慣例
- 單筆 `get`、列表 `filter`、`select_related`/`prefetch_related` 在 Projects 服務/路由中落地

## 建議：
- 若長期維持 RawQuerySet，請在 `StudyPagination` 注記 Count 的 SQL 改寫策略（已實作，建議保留說明）
- 考慮將常用 WHERE 子句抽象成小型建構器，減少字串操作錯誤風險
