# 002 分頁與路由（High/Medium）

依據：`.cursor/rules/pagination-rules.mdc`、`django-ninja-route-rules.mdc`

## OK：分頁回應形狀
- Reports：`{items,total,page,page_size,pages}`（`ReportPagination`）
- Studies：`{items,count,filters}`（`StudyPagination`）
- Projects：`{items,count}`（`ProjectPagination`）

## High：版本資訊不一致
- `config/urls.py`：`NinjaAPI(version='1.1.0')`
- 但 `/api/v1/health` 與根路由回應 `version: '1.0.0'`
- 建議：
  - 統一以設定來源（如 `settings.APP_VERSION`）產出版本；避免硬編碼
  - Swagger 顯示與健康檢查一致

## Medium：Studies API 註釋仍以舊制為主
- `studies/api.py` 的 docstring 對分頁仍著重 `limit/offset`（雖程式已雙模相容）
- 建議：
  - 更新註解：新制 `page/page_size` 為主；舊制僅供相容（v2.0.0 移除）
  - 在 Swagger 說明中標註 deprecation

## Medium：查詢陣列參數
- 已針對 `param[]` 與重複鍵兩種格式做相容（佳）
- 建議：在 API 文件補註兩種格式的支援範例
