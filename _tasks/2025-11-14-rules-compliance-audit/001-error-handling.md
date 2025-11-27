# 001 錯誤處理與 HTTP 回應（Critical）

依據：`.cursor/rules/django-error-handling-rules.mdc`、`django-ninja-route-rules.mdc`

## 問題 1：report 詳情端點使用通用 Exception，且變數未定義
- 檔案：`studies/report_api.py`
- 位置：`get_report_detail` 與 `get_study_report_detail`
- 現況：
  - 捕捉 `Report.DoesNotExist` 時 `raise Exception(f'Report not found: {report_id}')`
  - 此處 `report_id` 未定義（`get_report_detail` 的參數是 `uid`；`get_study_report_detail` 的參數是 `exam_id`）
- 規則違反：
  - 不得使用模糊的 `Exception`；API 層應轉為 404（`Http404`）
  - 變數錯誤導致例外內容錯誤
- 風險：
  - 回傳 500 而非 404；混淆客戶端
  - 連續錯誤日誌與除錯成本上升
- 建議修正：
  - `except Report.DoesNotExist: raise Http404(f'Report not found: {uid}')`（或對 `exam_id`）
  - 補齊單元測試覆蓋 404 案例

## 問題 2：錯誤日誌一致性
- 建議：將 `error` 日誌統一包含 `error_type`、`message`、`traceback`，對齊 `django-error-handling-rules.mdc`。

## 建議變更清單
- report 詳情相關兩處改為 `Http404`
- 增加 404 測試與 API 合約測試（`tests/test_api_contract.py` 可擴充）
