# 004 效能與快取（OK/建議）

依據：`.cursor/rules/django-performance-optimization-rules.mdc`

## OK
- Studies：DB 端 `LIMIT/OFFSET`、避免全量
- Filters：Django Cache（locmem/redis）與 TTL（24h）
- 報告列表：content 以 `safe_truncate(..., 500)` 回傳 preview，控制回應大小

## 建議
- 在 `RequestTimingMiddleware` 的ログ加入路由標籤與 page_size，便於查詢熱點與大頁面監控
- 在 Reports 查詢可考慮以 `.only()`/`.values()` 適度限制欄位（若不影響回應模型）
