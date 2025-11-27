# API 分頁統一需求文件

**版本**: 2.0.0  
**日期**: 2025-11-12  
**狀態**: 核准待實作  
**適用範圍**: 報告 API 與 研究 API  

---

## 1. 問題陳述

### 1.1 當前狀況

醫學影像資料平台的 API 分頁機制存在不一致：

| 端點 | 分頁模式 | 參數 | 回應格式 |
|------|---------|------|---------|
| `/api/v1/reports/search` | Offset/Limit | `offset`, `limit` | `{items, total, offset, limit, page, pages}` |
| `/api/v1/reports/search/paginated` | Offset/Limit | `offset`, `limit` | `{items, total, offset, limit, page, pages}` |
| `/api/v1/studies/search` | Page/Size | `page`, `page_size` | `{items, count, filters}` |

### 1.2 面臨的挑戰

1. **客戶端混淆**: 開發者須學習兩套不同的分頁邏輯
2. **前端複雜性**: 分別實作頁碼←→位移的轉換邏輯
3. **效能差異**: 研究 API 在深分頁時性能欠佳
4. **可維護性**: 兩套系統增加技術債

### 1.3 業務影響

- 開發時間成本增加
- 缺陷風險提升 (邊界情況處理複雜)
- 文件維護負擔加重

---

## 2. 設計目標

### 2.1 功能目標

✅ **統一分頁介面**  
所有 API 端點採用相同的分頁模式

✅ **提升查詢效能**  
支援 100,000+ 記錄的高效分頁

✅ **簡化客戶端**  
單一分頁邏輯實作，無須端點特殊處理

### 2.2 非功能目標

✅ **可擴展性**: 支援未來的分頁演進 (光標分頁、搜尋光標等)  
✅ **向後相容性**: 提供遷移期支援  
✅ **文件完整性**: 清晰的 API 合約定義  

---

## 3. 功能需求

### 3.1 分頁參數規格

採用 **Offset/Limit** 分頁模式

#### 請求參數

```http
GET /api/v1/[reports|studies]/search?offset=0&limit=20&q=...
```

| 參數 | 類型 | 預設 | 最大 | 必需 | 說明 |
|------|------|------|------|------|------|
| `offset` | int | 0 | - | ✓ | 跳過的項目數量 (0-索引) |
| `limit` | int | 20 | 100 | ✓ | 每頁返回的項目數 |

#### 參數驗證規則

```python
# 驗證邏輯
offset = max(0, offset)              # 不得為負
limit = max(1, min(limit, 100))      # 範圍: [1, 100]

# 邊界情況處理
if offset >= total_count:
    return empty results (HTTP 200, items=[])
```

### 3.2 回應格式規格

#### 統一響應格式

```json
{
  "items": [
    {
      "uid": "unique_id",
      "title": "Item Title",
      "created_at": "2025-11-12T10:30:00Z",
      ...
    }
  ],
  "pagination": {
    "total": 1000,
    "offset": 0,
    "limit": 20,
    "page": 1,
    "pages": 50
  }
}
```

#### 響應欄位定義

| 欄位 | 類型 | 說明 |
|------|------|------|
| `items` | Array | 當前頁面的項目列表 |
| `pagination.total` | int | 總項目數 |
| `pagination.offset` | int | 當前位移 (重複請求參數以便客戶端驗證) |
| `pagination.limit` | int | 當前限制 (重複請求參數) |
| `pagination.page` | int | 計算的頁碼 (1-索引) |
| `pagination.pages` | int | 計算的總頁數 |

#### 計算公式

```python
page = (offset // limit) + 1
pages = (total + limit - 1) // limit  # 向上取整
```

### 3.3 端點列表

#### 報告 API (已現存)

| 端點 | 現狀 | 調整 |
|------|------|------|
| `GET /api/v1/reports/search` | Offset/Limit | ✅ 保留不變 |
| `GET /api/v1/reports/search/paginated` | Offset/Limit | ✅ 保留不變 |
| `GET /api/v1/reports/latest` | 有分頁 | ✅ 統一為 Offset/Limit |
| `GET /api/v1/reports/filters/options` | 無分頁 | 保留不變（舊路徑 /options/filters 已標記為 Deprecated） |

#### 研究 API (需調整)

| 端點 | 現狀 | 調整 |
|------|------|------|
| `GET /api/v1/studies/search` | Page/Size | ⚠️ 改為 Offset/Limit |
| `GET /api/v1/studies/export` | Page/Size | ⚠️ 改為 Offset/Limit |

---

## 4. 非功能需求

### 4.1 效能需求

**查詢時間**:
- 第 1 頁 (offset=0): ≤ 100ms
- 第 500 頁 (offset=10,000): ≤ 200ms
- 末頁 (offset=99,000): ≤ 300ms

**資料庫操作**:
- 使用 SQL `LIMIT` 和 `OFFSET` 優化查詢
- 避免全表掃描

**內存使用**:
- 單頁面最大返回 100 項 < 1MB

### 4.2 可靠性需求

**錯誤處理**:

```python
# 無效參數
if offset < 0 or limit < 1:
    HTTP 400 Bad Request
    {
      "error": "Invalid pagination parameters",
      "details": "offset must be >= 0, limit must be >= 1"
    }

# 超出範圍
if offset >= total_count:
    HTTP 200 OK
    {
      "items": [],
      "pagination": {...}
    }
```

**日誌記錄**:
- 慢查詢警告 (>500ms)
- 無效參數錯誤
- 分頁邊界情況

### 4.3 相容性需求

**版本管理**:
- 報告 API: v1.0 → v1.1 (向後相容)
- 研究 API: v1.0 → v2.0 (破壞性變更)

**遷移策略**:
- v2.0 發佈後 6 個月內支援 v1.0
- 提供文件與遷移指南
- API 廢棄警告標頭

---

## 5. 實作約束

### 5.1 技術棧

- **框架**: Django Ninja REST
- **ORM**: Django ORM
- **資料庫**: PostgreSQL (假設)
- **快取**: Redis (filter options)

### 5.2 不在本次範圍內

❌ 光標分頁實作  
❌ GraphQL 支援  
❌ 前端客戶端庫開發  
❌ 向後相容性 API 維護 (超過 6 個月)  

---

## 6. 成功標準

### 6.1 功能驗收

- [ ] 報告 API `/search` 和 `/search/paginated` 使用相同分頁格式
- [ ] 研究 API `/search` 改為 Offset/Limit 參數
- [ ] 所有端點回應格式標準化
- [ ] 邊界情況正確處理 (offset >= total, invalid params)
- [ ] 錯誤回應包含描述性訊息

### 6.2 效能驗收

- [ ] 深分頁 (offset=50,000) 查詢時間 ≤ 300ms
- [ ] 無全表掃描
- [ ] 記憶體使用 < 1MB/請求

### 6.3 文件驗收

- [ ] API 合約更新完整
- [ ] 參數與回應範例清楚
- [ ] 遷移指南提供
- [ ] 廢棄計劃說明

### 6.4 測試驗收

- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] 整合測試涵蓋邊界情況
- [ ] 手動端點測試通過

---

## 7. 利益相關者與責任

| 角色 | 責任 |
|------|------|
| **後端開發** | 實作分頁邏輯與 API 端點 |
| **QA** | 測試邊界情況與效能 |
| **文件** | 更新 API 文件與遷移指南 |
| **前端** | 更新客戶端分頁邏輯 (後續) |

---

## 8. 時程規劃

| 階段 | 任務 | 預期期限 |
|------|------|---------|
| 分析 | ✅ 完成 | 2025-11-12 |
| 設計 | ⏳ 進行中 | 2025-11-12 |
| 實作 | 待開始 | 2025-11-13 |
| 測試 | 待開始 | 2025-11-14 |
| 發佈 | 待開始 | 2025-11-15 |

---

## 附錄 A: API 呼叫範例

### 報告 API

```bash
# 第 1 頁
curl "http://localhost:8001/api/v1/reports/search?offset=0&limit=20"

# 第 3 頁
curl "http://localhost:8001/api/v1/reports/search?offset=40&limit=20"

# 搭配篩選
curl "http://localhost:8001/api/v1/reports/search?q=covid&offset=0&limit=20&report_type=PDF"
```

### 研究 API (遷移後)

```bash
# 第 1 頁
curl "http://localhost:8001/api/v1/studies/search?offset=0&limit=20"

# 搭配篩選
curl "http://localhost:8001/api/v1/studies/search?exam_status=completed&offset=0&limit=20"
```

---

**文件狀態**: 核准  
**審閱人**: -  
**核准日期**: 待核准
