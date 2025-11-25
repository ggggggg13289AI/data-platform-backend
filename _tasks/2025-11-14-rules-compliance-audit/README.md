# 規則稽核報告（2025-11-14）

本報告依據 `.cursor/rules/` 的 Django 專案規則（路由、分頁、資料庫、效能、錯誤處理、Pydantic/Ninja Schemas、Linus 風格程式碼品質、uv 工作流程）對程式碼進行檢查，彙整重點問題與建議。

- 狀態：完成初步自動檢查（靜態規則符合性），未跑測試
- 範圍：`config/`, `studies/`, `.cursor/rules/`, `rules/`
- 重要性：以 Critical → High → Medium 分級

## 摘要
- Critical
  - report API 錯誤處理不符合規範，且存取未定義變數（兩處）
- High
  - 版本資訊不一致（API 宣告 1.1.0，根與健康檢查回應 1.0.0）
  - 報告匯入端點忽略 `verified_at` 輸入（與 API 文件潛在不一致）
- Medium
  - Studies API 註解仍著重舊制參數（limit/offset），需更新為新制為主、舊制為相容
  - 未使用匯入（小型整潔度問題）
- OK（符合）
  - 分頁形狀與限制（Reports/Studies/Projects）
  - Studies 查詢原生 SQL 以參數化與 DB 端分頁
  - Filters 快取與 N+1 風險控制
  - Projects 權限裝飾器落地

## 明細
- 001-error-handling.md：錯誤處理與 HTTP 回應
- 002-pagination-and-routing.md：分頁模型、路由參數、文件一致性
- 003-database-interaction.md：ORM/原生 SQL、安全性、事務
- 004-performance-and-caching.md：N+1、DB 切片、快取
- 005-auth-and-permissions.md：JWT/權限裝飾器
- 006-style-and-maintainability.md：命名/未使用匯入/文件一致性

> 本報告著重「規則符合」與「可讀性/可靠性」。若需要我直接送出修正 PR，請告知優先級與範圍。