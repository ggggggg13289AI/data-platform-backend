# 006 程式風格與可維護性（Medium）

依據：`.cursor/rules/code-quality-linus.mdc`、`django-pydantic-schemas-rules.mdc`

## 未使用匯入
- `studies/report_api.py`：`from django.utils import timezone` 未使用（可移除）

## 文件/註解一致性
- `studies/api.py` 的 docstring 仍以舊制 `limit/offset` 為主，建議更新為新制為主、舊制相容為輔

## Pydantic/Ninja Schemas
- 目前結構符合 v1 風格；回應形狀符合分頁規則

## 建議
- 保持函數短小（>20 行考慮拆分）、早期返回、以資料結構消除 if/else 鏈
- 建立簡短 PR 模板欄位強制填寫「為何要改」和「使用者可見影響」以符合 Linus 實用主義