# 005 認證與權限（OK/備註）

依據：`.cursor/rules/django-application-rules.mdc`、`django-ninja-route-rules.mdc`

## OK
- Projects 路由透過 `require_*` 裝飾器驗證權限；未附 `auth=JWTAuth()` 時，`request.user` 未授權則落為 `PermissionDenied`（403）
- `auth_api.py` 實作登入/刷新/登出/取用 `me`，與 `ninja_jwt` 設定一致

## 備註
- 如需區分 401 與 403（未認證 vs 無權限），可在列表與檢視端點上明確加上 `auth=JWTAuth()`（目前多數已加，個別端點依需求決定）
