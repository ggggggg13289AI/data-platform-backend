# Projects Route 功能需求規格書

**文件版本**：1.0  
**建立日期**：2025-11-12  
**文件狀態**：✅ 規劃完成，等待實作  
**作者**：Claude Code  
**專案**：醫學影像資料管理平台

---

## 📋 文件目的

本文件定義醫學影像資料平台的**專案管理功能（Projects）**完整需求規格，包含：

1. 功能需求與使用案例
2. API 端點規格（22個端點）
3. 資料模型設計
4. 權限系統架構
5. 驗收標準與測試策略

---

## 🎯 專案概述

### 背景

目前平台已具備：
- ✅ 醫學影像研究（Studies）管理功能
- ✅ 報告（Reports）管理功能
- ✅ 使用者認證與基礎權限

需要新增：
- ❌ 專案（Projects）組織管理功能
- ❌ 多人協作與權限控制
- ❌ 研究分組與批量操作

### 目標

提供完整的專案管理能力，讓使用者能夠：

1. **組織研究資料**：將相關研究歸類到專案中
2. **團隊協作**：邀請成員加入專案，分配不同角色
3. **權限管理**：細粒度控制成員對專案的操作權限
4. **批量操作**：高效管理大量研究資料
5. **統計分析**：查看專案進度與統計資訊

### 範圍

**包含功能**：
- ✅ 專案 CRUD 操作（建立、讀取、更新、刪除）
- ✅ 專案生命週期管理（封存、恢復、複製）
- ✅ 成員管理（新增、移除、角色變更）
- ✅ 研究分配（批量新增、移除、跨專案查詢）
- ✅ 搜尋與篩選（多條件搜尋）
- ✅ 統計資訊（研究數、成員數等）
- ✅ 4層權限系統（Owner/Admin/Editor/Viewer）

**不包含功能**（Phase 4+ 實作）：
- ❌ 通知系統
- ❌ 活動日誌與稽核追蹤
- ❌ 專案匯出功能
- ❌ 專案範本功能
- ❌ 進階統計儀表板

---

## 👥 利害關係人

| 角色 | 需求 | 優先級 |
|------|------|--------|
| **研究人員** | 組織自己的研究資料，快速查找相關案例 | 🔴 高 |
| **專案管理者** | 管理團隊專案，分配任務與權限 | 🔴 高 |
| **醫療機構管理員** | 監督多個專案，確保資料安全與合規 | 🟡 中 |
| **系統管理員** | 維護平台運作，監控效能與安全性 | 🟢 低 |

---

## 📊 功能需求

### FR-1：專案基礎管理

#### FR-1.1：建立專案
**描述**：使用者可建立新專案以組織研究資料

**前置條件**：
- 使用者已登入系統
- 使用者具有建立專案的權限

**輸入**：
- 專案名稱（必填，長度 1-200 字元）
- 專案描述（選填，最多 5000 字元）
- 標籤列表（選填，陣列格式）
- 狀態（選填，預設為 'active'）
- 設定（選填，JSON 物件）

**輸出**：
- 建立成功：返回完整專案資訊，HTTP 201
- 建立失敗：返回錯誤訊息，HTTP 400/500

**業務規則**：
- BR-1.1.1：專案名稱不可為空白
- BR-1.1.2：建立者自動成為專案 Owner
- BR-1.1.3：初始 study_count 為 0
- BR-1.1.4：自動記錄建立時間與更新時間

**驗收標準**：
- ✅ 可成功建立包含中文名稱的專案
- ✅ 建立者自動獲得 Owner 角色
- ✅ 輸入驗證正確攔截無效資料
- ✅ 返回包含 UUID 的完整專案資訊

#### FR-1.2：查看專案列表
**描述**：使用者可查看有權限存取的專案列表

**前置條件**：
- 使用者已登入系統

**篩選參數**：
- `q`：關鍵字搜尋（搜尋名稱、描述）
- `status`：狀態篩選（active/archived/completed/draft）
- `tags`：標籤篩選（支援多選）
- `created_by`：建立者篩選
- `sort`：排序方式（預設：-updated_at）

**分頁參數**：
- `page`：頁碼（1-indexed，預設 1）
- `page_size`：每頁筆數（預設 20，最大 100）

**輸出**：
```json
{
  "total": 50,
  "page": 1,
  "page_size": 20,
  "projects": [
    {
      "id": "uuid",
      "name": "專案名稱",
      "description": "專案描述",
      "status": "active",
      "tags": ["標籤1", "標籤2"],
      "study_count": 15,
      "member_count": 3,
      "created_at": "2025-11-01T10:00:00Z",
      "updated_at": "2025-11-12T15:30:00Z",
      "created_by": {"id": "user-uuid", "name": "使用者名稱"},
      "user_role": "owner"
    }
  ]
}
```

**業務規則**：
- BR-1.2.1：只顯示使用者有權限的專案（成員或建立者）
- BR-1.2.2：預設按更新時間降冪排序
- BR-1.2.3：關鍵字搜尋不區分大小寫
- BR-1.2.4：支援多條件組合篩選

**驗收標準**：
- ✅ 分頁功能正常運作
- ✅ 篩選條件正確套用
- ✅ 排序邏輯正確
- ✅ 權限檢查生效（只看到有權限的專案）
- ✅ 效能符合標準（< 500ms for 100 項目）

#### FR-1.3：查看專案詳情
**描述**：使用者可查看單一專案的完整資訊

**前置條件**：
- 使用者已登入
- 使用者對該專案有讀取權限

**輸入**：
- 專案 ID（UUID）

**輸出**：
```json
{
  "id": "uuid",
  "name": "專案名稱",
  "description": "專案描述",
  "status": "active",
  "tags": ["標籤1", "標籤2"],
  "study_count": 15,
  "member_count": 3,
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-12T15:30:00Z",
  "created_by": {
    "id": "user-uuid",
    "name": "使用者名稱",
    "email": "user@example.com"
  },
  "user_role": "owner",
  "user_permissions": ["view", "edit", "delete", "manage_members"],
  "settings": {
    "is_public": false,
    "allow_guest_access": false
  },
  "metadata": {}
}
```

**業務規則**：
- BR-1.3.1：返回使用者在專案中的角色
- BR-1.3.2：返回使用者的具體權限列表
- BR-1.3.3：專案不存在時返回 404
- BR-1.3.4：無權限時返回 403

**驗收標準**：
- ✅ 返回完整專案資訊
- ✅ 權限檢查正確
- ✅ user_role 與 user_permissions 正確計算
- ✅ 錯誤處理正確（404/403）

#### FR-1.4：更新專案
**描述**：有編輯權限的使用者可更新專案資訊

**前置條件**：
- 使用者已登入
- 使用者對該專案有編輯權限（Editor/Admin/Owner）

**可更新欄位**：
- 專案名稱
- 專案描述
- 標籤列表
- 狀態
- 設定

**業務規則**：
- BR-1.4.1：只有 Editor 以上角色可更新
- BR-1.4.2：更新時自動更新 updated_at
- BR-1.4.3：部分更新支援（PATCH 語意）
- BR-1.4.4：記錄修改歷史（未來功能）

**驗收標準**：
- ✅ 權限檢查正確（Viewer 無法更新）
- ✅ 欄位驗證正確
- ✅ updated_at 自動更新
- ✅ 部分更新正常運作

#### FR-1.5：刪除專案
**描述**：Owner 可刪除專案

**前置條件**：
- 使用者已登入
- 使用者是該專案的 Owner

**刪除行為**：
- 軟刪除（標記為已刪除，保留資料 30 天）
- 同時刪除所有研究分配關聯
- 通知所有成員（未來功能）

**業務規則**：
- BR-1.5.1：只有 Owner 可刪除專案
- BR-1.5.2：刪除前需確認（前端實作）
- BR-1.5.3：刪除是軟刪除，可在 30 天內恢復
- BR-1.5.4：30 天後自動永久刪除（排程任務）

**驗收標準**：
- ✅ 只有 Owner 可刪除
- ✅ 刪除後無法直接存取
- ✅ 研究分配關聯正確移除
- ✅ 可恢復已刪除專案（30天內）

---

### FR-2：專案生命週期管理

#### FR-2.1：封存專案
**描述**：將不再活躍的專案標記為封存狀態

**前置條件**：
- 使用者有編輯權限
- 專案當前狀態不是 'archived'

**業務規則**：
- BR-2.1.1：Editor 以上可封存
- BR-2.1.2：封存不影響已分配的研究
- BR-2.1.3：封存後專案預設不顯示在列表（需篩選）
- BR-2.1.4：記錄封存時間與操作者

**驗收標準**：
- ✅ 狀態正確更新為 'archived'
- ✅ 權限檢查正確
- ✅ 不影響研究資料

#### FR-2.2：恢復專案
**描述**：將封存的專案恢復為活躍狀態

**前置條件**：
- 使用者有編輯權限
- 專案當前狀態是 'archived'

**業務規則**：
- BR-2.2.1：Editor 以上可恢復
- BR-2.2.2：恢復後狀態變為 'active'
- BR-2.2.3：記錄恢復時間與操作者

**驗收標準**：
- ✅ 狀態正確更新為 'active'
- ✅ 專案重新出現在預設列表
- ✅ 所有功能恢復正常

#### FR-2.3：複製專案
**描述**：基於現有專案建立副本

**前置條件**：
- 使用者對原專案有讀取權限

**複製內容**：
- ✅ 專案名稱（加上 "副本" 後綴）
- ✅ 專案描述
- ✅ 標籤
- ✅ 設定
- ❌ 成員（不複製）
- ❌ 研究分配（不複製）

**業務規則**：
- BR-2.3.1：複製後建立者成為新專案 Owner
- BR-2.3.2：新專案狀態為 'draft'
- BR-2.3.3：不複製原專案的成員與研究

**驗收標準**：
- ✅ 成功建立新專案
- ✅ 基本資訊正確複製
- ✅ 不複製成員與研究
- ✅ 建立者成為 Owner

---

### FR-3：研究分配管理

#### FR-3.1：新增研究到專案
**描述**：將研究批量新增到專案中

**前置條件**：
- 使用者對專案有編輯權限
- 研究存在於系統中

**輸入**：
```json
{
  "exam_ids": ["exam_001", "exam_002", "exam_003"],
  "metadata": {}
}
```

**業務規則**：
- BR-3.1.1：Editor 以上可新增研究
- BR-3.1.2：自動過濾已分配的研究
- BR-3.1.3：批量操作使用事務（全成功或全失敗）
- BR-3.1.4：自動更新 project.study_count
- BR-3.1.5：記錄分配者與分配時間

**輸出**：
```json
{
  "success": true,
  "added_count": 3,
  "skipped_count": 0,
  "project_name": "專案名稱",
  "current_study_count": 18
}
```

**驗收標準**：
- ✅ 批量新增成功
- ✅ 自動過濾重複
- ✅ study_count 正確更新
- ✅ 事務完整性（失敗時全部回滾）
- ✅ 效能符合標準（1000筆 < 2秒）

#### FR-3.2：從專案移除研究
**描述**：批量移除專案中的研究

**前置條件**：
- 使用者對專案有編輯權限

**輸入**：
```json
{
  "exam_ids": ["exam_001", "exam_002"]
}
```

**業務規則**：
- BR-3.2.1：Editor 以上可移除研究
- BR-3.2.2：移除不影響研究本身（只移除關聯）
- BR-3.2.3：自動更新 project.study_count
- BR-3.2.4：批量操作使用事務

**驗收標準**：
- ✅ 批量移除成功
- ✅ study_count 正確更新
- ✅ 研究資料不受影響

#### FR-3.3：列出專案研究
**描述**：查看專案中的所有研究

**前置條件**：
- 使用者對專案有讀取權限

**分頁參數**：
- `page`：頁碼
- `page_size`：每頁筆數
- `sort`：排序（預設：-assigned_at）

**輸出**：
```json
{
  "total": 15,
  "page": 1,
  "page_size": 20,
  "studies": [
    {
      "exam_id": "exam_001",
      "patient_name": "患者姓名",
      "exam_date": "2025-11-01",
      "modality": "CT",
      "assigned_at": "2025-11-10T10:00:00Z",
      "assigned_by": {"id": "user-uuid", "name": "使用者名稱"}
    }
  ]
}
```

**業務規則**：
- BR-3.3.1：返回完整研究資訊
- BR-3.3.2：包含分配資訊（時間、分配者）
- BR-3.3.3：支援排序與分頁

**驗收標準**：
- ✅ 正確列出所有研究
- ✅ 分頁與排序正常
- ✅ 包含分配資訊

#### FR-3.4：批量分配研究到多個專案
**描述**：將研究批量分配到多個專案

**前置條件**：
- 使用者對所有目標專案有編輯權限

**輸入**：
```json
{
  "exam_ids": ["exam_001", "exam_002"],
  "project_ids": ["project-uuid-1", "project-uuid-2"]
}
```

**業務規則**：
- BR-3.4.1：驗證所有專案權限
- BR-3.4.2：使用事務確保一致性
- BR-3.4.3：自動過濾已存在的分配
- BR-3.4.4：批量更新所有專案的 study_count

**輸出**：
```json
{
  "success": true,
  "total_assignments": 4,
  "projects_updated": 2,
  "details": [
    {
      "project_id": "uuid-1",
      "project_name": "專案1",
      "added_count": 2
    },
    {
      "project_id": "uuid-2",
      "project_name": "專案2",
      "added_count": 2
    }
  ]
}
```

**驗收標準**：
- ✅ 批量分配成功
- ✅ 權限檢查完整
- ✅ 事務完整性
- ✅ 所有 study_count 正確更新

#### FR-3.5：查詢研究所屬專案
**描述**：查看特定研究被分配到哪些專案

**前置條件**：
- 使用者已登入
- 研究存在於系統中

**輸入**：
- Study ID (exam_id)

**輸出**：
```json
{
  "exam_id": "exam_001",
  "projects": [
    {
      "id": "project-uuid-1",
      "name": "專案1",
      "status": "active",
      "user_role": "editor",
      "assigned_at": "2025-11-10T10:00:00Z"
    }
  ],
  "total_projects": 1
}
```

**業務規則**：
- BR-3.5.1：只返回使用者有權限的專案
- BR-3.5.2：包含使用者在各專案的角色
- BR-3.5.3：按分配時間降冪排序

**驗收標準**：
- ✅ 正確返回所有相關專案
- ✅ 權限過濾正確
- ✅ 包含角色資訊

---

### FR-4：成員管理

#### FR-4.1：新增成員
**描述**：邀請使用者加入專案

**前置條件**：
- 操作者有管理成員權限（Admin/Owner）
- 被邀請者為系統有效使用者

**輸入**：
```json
{
  "user_id": "user-uuid",
  "role": "editor"
}
```

**業務規則**：
- BR-4.1.1：只有 Admin/Owner 可新增成員
- BR-4.1.2：不可重複新增同一成員
- BR-4.1.3：預設角色為 Viewer（如未指定）
- BR-4.1.4：記錄加入時間
- BR-4.1.5：發送通知（未來功能）

**驗收標準**：
- ✅ 成功新增成員
- ✅ 權限檢查正確
- ✅ 不允許重複新增
- ✅ 預設角色正確

#### FR-4.2：移除成員
**描述**：將成員從專案中移除

**前置條件**：
- 操作者有管理成員權限
- 目標成員不是專案 Owner

**業務規則**：
- BR-4.2.1：只有 Admin/Owner 可移除成員
- BR-4.2.2：Owner 不可被移除
- BR-4.2.3：成員可自行退出（移除自己）
- BR-4.2.4：發送通知（未來功能）

**驗收標準**：
- ✅ 成功移除成員
- ✅ 不允許移除 Owner
- ✅ 成員可自行退出

#### FR-4.3：更新成員角色
**描述**：變更成員在專案中的角色

**前置條件**：
- 操作者有管理成員權限
- 目標成員不是專案 Owner

**輸入**：
```json
{
  "role": "admin"
}
```

**業務規則**：
- BR-4.3.1：只有 Owner 可變更角色
- BR-4.3.2：Owner 角色不可變更
- BR-4.3.3：不可將自己的 Owner 角色轉讓（需專用轉讓功能）
- BR-4.3.4：記錄角色變更歷史（未來功能）

**驗收標準**：
- ✅ 成功變更角色
- ✅ Owner 限制正確
- ✅ 權限檢查正確

#### FR-4.4：列出專案成員
**描述**：查看專案所有成員及其角色

**前置條件**：
- 使用者對專案有讀取權限

**輸出**：
```json
{
  "total": 5,
  "members": [
    {
      "user_id": "user-uuid",
      "name": "使用者名稱",
      "email": "user@example.com",
      "role": "owner",
      "joined_at": "2025-11-01T10:00:00Z",
      "permissions": ["view", "edit", "delete", "manage_members"]
    }
  ]
}
```

**業務規則**：
- BR-4.4.1：返回所有成員資訊
- BR-4.4.2：包含角色與權限
- BR-4.4.3：Owner 排序優先

**驗收標準**：
- ✅ 正確列出所有成員
- ✅ 角色與權限正確
- ✅ 排序邏輯正確

---

### FR-5：搜尋與統計

#### FR-5.1：搜尋專案
**描述**：跨專案全文搜尋

**搜尋欄位**：
- 專案名稱
- 專案描述
- 標籤

**篩選條件**：
- 狀態
- 標籤
- 建立時間範圍
- 建立者

**排序選項**：
- 名稱（升冪/降冪）
- 建立時間（升冪/降冪）
- 更新時間（升冪/降冪）
- 研究數量（升冪/降冪）

**業務規則**：
- BR-5.1.1：不區分大小寫搜尋
- BR-5.1.2：支援部分匹配
- BR-5.1.3：只搜尋有權限的專案
- BR-5.1.4：高亮搜尋關鍵字（前端實作）

**驗收標準**：
- ✅ 搜尋結果正確
- ✅ 權限過濾正確
- ✅ 效能符合標準（< 500ms）

#### FR-5.2：專案統計資訊
**描述**：查看專案的統計資料

**統計指標**：
- 研究總數
- 成員總數
- 建立時間
- 最後更新時間
- 最後活動時間
- 研究按檢查類型分布（Modality）
- 研究按時間分布（月份統計）

**輸出**：
```json
{
  "project_id": "uuid",
  "project_name": "專案名稱",
  "study_count": 15,
  "member_count": 3,
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-12T15:30:00Z",
  "last_activity_at": "2025-11-12T14:00:00Z",
  "modality_distribution": {
    "CT": 8,
    "MRI": 5,
    "X-Ray": 2
  },
  "monthly_study_distribution": {
    "2025-11": 10,
    "2025-10": 5
  }
}
```

**業務規則**：
- BR-5.2.1：即時計算統計（不快取）
- BR-5.2.2：只有成員可查看統計
- BR-5.2.3：統計資料可用於圖表展示

**驗收標準**：
- ✅ 統計數據正確
- ✅ 效能可接受（< 1秒）
- ✅ 權限檢查正確

---

## 🔐 權限系統需求

### 角色定義

| 角色 | 英文名稱 | 說明 | 人數限制 |
|------|---------|------|---------|
| **擁有者** | Owner | 專案建立者，具有最高權限 | 1人（不可變更） |
| **管理員** | Admin | 協助管理專案，可管理成員 | 無限制 |
| **編輯者** | Editor | 可編輯專案與研究，不可管理成員 | 無限制 |
| **檢視者** | Viewer | 只能查看，不可修改 | 無限制 |

### 權限矩陣

| 操作 | Owner | Admin | Editor | Viewer |
|------|-------|-------|--------|--------|
| **查看專案** | ✅ | ✅ | ✅ | ✅ |
| **查看專案列表** | ✅ | ✅ | ✅ | ✅ |
| **查看研究列表** | ✅ | ✅ | ✅ | ✅ |
| **查看成員列表** | ✅ | ✅ | ✅ | ✅ |
| **查看統計資訊** | ✅ | ✅ | ✅ | ✅ |
| **編輯專案資訊** | ✅ | ✅ | ✅ | ❌ |
| **新增研究** | ✅ | ✅ | ✅ | ❌ |
| **移除研究** | ✅ | ✅ | ✅ | ❌ |
| **封存/恢復專案** | ✅ | ✅ | ✅ | ❌ |
| **新增成員** | ✅ | ✅ | ❌ | ❌ |
| **移除成員** | ✅ | ✅ | ❌ | ❌ |
| **變更成員角色** | ✅ | ❌ | ❌ | ❌ |
| **刪除專案** | ✅ | ❌ | ❌ | ❌ |
| **轉讓 Owner** | ✅ | ❌ | ❌ | ❌ |

### 權限實作需求

**PR-1：權限檢查機制**
- 所有 API 端點必須進行權限檢查
- 使用裝飾器統一處理權限驗證
- 權限不足時返回 HTTP 403

**PR-2：角色繼承**
- Owner 自動擁有所有權限
- Admin 繼承 Editor 權限
- Editor 繼承 Viewer 權限

**PR-3：特殊規則**
- 成員可自行退出專案（移除自己）
- Owner 不可被移除或降級
- 只有 Owner 可刪除專案

---

## 🎨 API 端點規格

### 端點總覽（22個端點）

| 編號 | 方法 | 路徑 | 說明 | 權限要求 |
|------|------|------|------|---------|
| 1 | GET | `/api/v1/projects` | 列出專案 | 已登入 |
| 2 | POST | `/api/v1/projects` | 建立專案 | 已登入 |
| 3 | GET | `/api/v1/projects/:id` | 取得專案詳情 | Viewer+ |
| 4 | PUT | `/api/v1/projects/:id` | 更新專案 | Editor+ |
| 5 | DELETE | `/api/v1/projects/:id` | 刪除專案 | Owner |
| 6 | POST | `/api/v1/projects/:id/archive` | 封存專案 | Editor+ |
| 7 | POST | `/api/v1/projects/:id/restore` | 恢復專案 | Editor+ |
| 8 | POST | `/api/v1/projects/:id/duplicate` | 複製專案 | Viewer+ |
| 9 | GET | `/api/v1/projects/:id/statistics` | 專案統計 | Viewer+ |
| 10 | POST | `/api/v1/projects/:id/studies` | 新增研究 | Editor+ |
| 11 | DELETE | `/api/v1/projects/:id/studies` | 移除研究 | Editor+ |
| 12 | GET | `/api/v1/projects/:id/studies` | 列出專案研究 | Viewer+ |
| 13 | POST | `/api/v1/projects/batch-assign` | 批量分配 | Editor+ |
| 14 | GET | `/api/v1/studies/:studyId/projects` | 研究所屬專案 | 已登入 |
| 15 | POST | `/api/v1/projects/:id/members` | 新增成員 | Admin+ |
| 16 | DELETE | `/api/v1/projects/:id/members/:userId` | 移除成員 | Admin+ |
| 17 | PUT | `/api/v1/projects/:id/members/:userId` | 更新角色 | Owner |
| 18 | GET | `/api/v1/projects/:id/members` | 列出成員 | Viewer+ |
| 19 | GET | `/api/v1/projects/search` | 搜尋專案 | 已登入 |

### 詳細端點規格

#### API-1: GET /api/v1/projects

**用途**：列出使用者有權限的專案

**Query Parameters**：
```
?page=1
&page_size=20
&q=關鍵字
&status=active
&tags=標籤1,標籤2
&created_by=user-uuid
&sort=-updated_at
```

**Response 200**：
```json
{
  "total": 50,
  "page": 1,
  "page_size": 20,
  "projects": [
    {
      "id": "uuid",
      "name": "專案名稱",
      "description": "專案描述",
      "status": "active",
      "tags": ["tag1"],
      "study_count": 15,
      "member_count": 3,
      "created_at": "2025-11-01T10:00:00Z",
      "updated_at": "2025-11-12T15:30:00Z",
      "created_by": {
        "id": "user-uuid",
        "name": "使用者"
      },
      "user_role": "owner"
    }
  ]
}
```

**錯誤回應**：
- 401：未認證
- 400：參數錯誤

---

#### API-2: POST /api/v1/projects

**用途**：建立新專案

**Request Body**：
```json
{
  "name": "專案名稱",
  "description": "專案描述",
  "tags": ["tag1", "tag2"],
  "status": "active",
  "settings": {
    "is_public": false
  }
}
```

**Response 201**：
```json
{
  "id": "uuid",
  "name": "專案名稱",
  "description": "專案描述",
  "status": "active",
  "tags": ["tag1", "tag2"],
  "study_count": 0,
  "member_count": 1,
  "created_at": "2025-11-12T15:30:00Z",
  "updated_at": "2025-11-12T15:30:00Z",
  "created_by": {
    "id": "user-uuid",
    "name": "使用者"
  },
  "user_role": "owner",
  "settings": {
    "is_public": false
  }
}
```

**錯誤回應**：
- 401：未認證
- 400：驗證錯誤（名稱為空等）
- 500：伺服器錯誤

---

#### API-3: GET /api/v1/projects/:id

**用途**：取得專案詳細資訊

**Response 200**：
```json
{
  "id": "uuid",
  "name": "專案名稱",
  "description": "專案描述",
  "status": "active",
  "tags": ["tag1"],
  "study_count": 15,
  "member_count": 3,
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-12T15:30:00Z",
  "created_by": {
    "id": "user-uuid",
    "name": "使用者",
    "email": "user@example.com"
  },
  "user_role": "owner",
  "user_permissions": ["view", "edit", "delete", "manage_members"],
  "settings": {},
  "metadata": {}
}
```

**錯誤回應**：
- 401：未認證
- 403：無權限
- 404：專案不存在

---

#### API-10: POST /api/v1/projects/:id/studies

**用途**：批量新增研究到專案

**Request Body**：
```json
{
  "exam_ids": ["exam_001", "exam_002", "exam_003"],
  "metadata": {}
}
```

**Response 200**：
```json
{
  "success": true,
  "added_count": 3,
  "skipped_count": 0,
  "project_name": "專案名稱",
  "current_study_count": 18
}
```

**錯誤回應**：
- 401：未認證
- 403：無編輯權限
- 404：專案或研究不存在
- 400：exam_ids 為空或格式錯誤

---

#### API-15: POST /api/v1/projects/:id/members

**用途**：新增成員到專案

**Request Body**：
```json
{
  "user_id": "user-uuid",
  "role": "editor"
}
```

**Response 200**：
```json
{
  "success": true,
  "member": {
    "user_id": "user-uuid",
    "name": "使用者名稱",
    "email": "user@example.com",
    "role": "editor",
    "joined_at": "2025-11-12T15:30:00Z"
  }
}
```

**錯誤回應**：
- 401：未認證
- 403：無管理成員權限
- 404：使用者或專案不存在
- 409：使用者已是成員

---

## 📊 資料模型需求

### 資料庫表設計

#### 表：projects
```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    tags JSONB DEFAULT '[]',
    study_count INTEGER DEFAULT 0,
    created_by_id UUID NOT NULL REFERENCES auth_user(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    settings JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_projects_status_updated ON projects(status, updated_at DESC);
CREATE INDEX idx_projects_created_by ON projects(created_by_id, created_at DESC);
CREATE INDEX idx_projects_study_count ON projects(study_count DESC);
```

#### 表：project_members
```sql
CREATE TABLE project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL,
    permissions JSONB DEFAULT '[]',
    UNIQUE (project_id, user_id)
);

CREATE INDEX idx_project_members_project ON project_members(project_id);
CREATE INDEX idx_project_members_user ON project_members(user_id);
```

#### 表：study_project_assignments
```sql
CREATE TABLE study_project_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    study_id VARCHAR(255) NOT NULL REFERENCES studies(exam_id) ON DELETE CASCADE,
    assigned_by_id UUID NOT NULL REFERENCES auth_user(id),
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB DEFAULT '{}',
    UNIQUE (project_id, study_id)
);

CREATE INDEX idx_spa_project_assigned ON study_project_assignments(project_id, assigned_at DESC);
CREATE INDEX idx_spa_study_project ON study_project_assignments(study_id, project_id);
```

### 資料完整性約束

**DI-1：外鍵約束**
- project_members.project_id → projects.id (CASCADE DELETE)
- project_members.user_id → auth_user.id (CASCADE DELETE)
- study_project_assignments.project_id → projects.id (CASCADE DELETE)
- study_project_assignments.study_id → studies.exam_id (CASCADE DELETE)

**DI-2：唯一性約束**
- (project_id, user_id) 在 project_members 中唯一
- (project_id, study_id) 在 study_project_assignments 中唯一

**DI-3：檢查約束**
- projects.status 只能是 'active', 'archived', 'completed', 'draft'
- project_members.role 只能是 'owner', 'admin', 'editor', 'viewer'
- projects.study_count >= 0

---

## 🧪 測試需求

### 單元測試

**UT-1：模型測試**
- ✅ Project 模型建立與驗證
- ✅ ProjectMember 模型建立與驗證
- ✅ StudyProjectAssignment 模型建立與驗證
- ✅ 模型方法測試（to_dict, get_user_role 等）

**UT-2：服務層測試**
- ✅ ProjectService.create_project
- ✅ ProjectService.get_projects_queryset
- ✅ ProjectService.add_studies_to_project
- ✅ ProjectService.remove_studies_from_project
- ✅ ProjectService.add_member
- ✅ ProjectService.remove_member
- ✅ ProjectService.update_member_role

**UT-3：權限測試**
- ✅ 權限檢查邏輯正確性
- ✅ 角色繼承正確性
- ✅ 特殊規則（Owner 不可移除等）

**測試覆蓋率目標**：≥ 80%

### 整合測試

**IT-1：API 端點測試**
- ✅ 每個 API 端點的正常流程
- ✅ 每個 API 端點的錯誤處理
- ✅ 權限控制正確性
- ✅ 輸入驗證正確性

**IT-2：業務流程測試**
- ✅ 建立專案 → 新增成員 → 分配研究 → 查看統計
- ✅ 封存專案 → 恢復專案
- ✅ 複製專案流程
- ✅ 批量操作流程

**IT-3：併發測試**
- ✅ 多人同時編輯專案
- ✅ 同時新增/移除研究
- ✅ study_count 更新一致性

**測試覆蓋率目標**：100% API 端點

### 效能測試

**PT-1：回應時間測試**
- ✅ 列出專案（100項）< 300ms
- ✅ 建立專案 < 200ms
- ✅ 批量新增研究（100筆）< 1s
- ✅ 搜尋專案 < 500ms
- ✅ 專案統計 < 1s

**PT-2：壓力測試**
- ✅ 1000 專案資料查詢效能
- ✅ 100 併發請求處理
- ✅ 大量研究分配效能（1000+筆）

**PT-3：資料庫效能測試**
- ✅ 查詢計畫分析（EXPLAIN ANALYZE）
- ✅ 索引效能驗證
- ✅ N+1 查詢檢測

---

## ✅ 驗收標準

### Phase 1：資料模型與服務層

**驗收標準**：
- [ ] 3個資料模型通過 code review
- [ ] 遷移檔案可正常執行
- [ ] 遷移可正常回滾
- [ ] 服務層單元測試覆蓋率 ≥ 80%
- [ ] 權限系統測試覆蓋率 ≥ 90%
- [ ] 所有模型方法有文件字串說明

### Phase 2：API 端點實作

**驗收標準**：
- [ ] 22個 API 端點全部實作完成
- [ ] 每個端點有完整 Pydantic schema
- [ ] API 測試覆蓋率 100%
- [ ] OpenAPI 文件自動生成
- [ ] 所有端點有錯誤處理
- [ ] 權限檢查在所有端點生效

### Phase 3：整合測試與部署

**驗收標準**：
- [ ] 前後端整合測試全部通過
- [ ] 效能測試達標（p95 < 500ms）
- [ ] 安全性審查無重大漏洞
- [ ] 併發測試通過（無資料不一致）
- [ ] 完整中文 API 文件
- [ ] 部署檢查清單完成

### 最終驗收標準

**功能性**：
- [ ] 所有 22 個端點正常運作
- [ ] 前端可正常呼叫所有 API
- [ ] 權限系統正確運作
- [ ] 資料一致性驗證通過

**效能**：
- [ ] p50 回應時間 < 200ms
- [ ] p95 回應時間 < 500ms
- [ ] 批量操作效能符合標準
- [ ] 資料庫查詢優化完成

**品質**：
- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] 整合測試覆蓋率 ≥ 70%
- [ ] 程式碼 review 通過
- [ ] 無 critical 或 high severity 問題

**文件**：
- [ ] API 使用文件（繁體中文）
- [ ] 資料模型架構圖
- [ ] 權限系統說明文件
- [ ] 部署與維運文件

---

## 📝 附錄

### A. 狀態定義

| 狀態 | 英文 | 說明 | 可見性 |
|------|------|------|--------|
| 進行中 | active | 正在進行的專案 | 預設顯示 |
| 已封存 | archived | 已封存不再活躍 | 需篩選才顯示 |
| 已完成 | completed | 已完成的專案 | 預設顯示 |
| 草稿 | draft | 草稿狀態 | 僅建立者可見 |

### B. 標籤系統

**標籤格式**：
- 字串陣列
- 每個標籤長度 1-50 字元
- 支援中英文
- 不區分大小寫（儲存時統一小寫）

**標籤用途**：
- 專案分類
- 快速篩選
- 統計分析

### C. 錯誤碼定義

| HTTP Code | 錯誤類型 | 說明 |
|-----------|---------|------|
| 400 | Bad Request | 請求參數錯誤或驗證失敗 |
| 401 | Unauthorized | 未認證（需登入） |
| 403 | Forbidden | 無權限執行操作 |
| 404 | Not Found | 資源不存在 |
| 409 | Conflict | 資源衝突（如重複新增成員） |
| 500 | Internal Server Error | 伺服器內部錯誤 |

### D. 技術決策紀錄

**TD-1：使用 UUID 作為主鍵**
- **原因**：安全性考量，避免可預測的 ID
- **優點**：分散式友善、不可預測
- **缺點**：儲存空間稍大、索引效能稍低

**TD-2：Denormalized study_count**
- **原因**：避免頻繁 COUNT 查詢
- **優點**：查詢效能大幅提升
- **缺點**：需確保更新一致性

**TD-3：使用 page/page_size 分頁**
- **原因**：與 Studies API 保持一致
- **優點**：API 一致性、易於理解
- **缺點**：需確保前後端配合

**TD-4：4層權限系統**
- **原因**：滿足企業級權限管理需求
- **優點**：彈性高、權限控制細緻
- **缺點**：實作複雜度較高

---

## 📚 參考文件

1. Studies API 實作（`studies/api.py`）
2. Reports API 實作（`studies/report_api.py`）
3. 分頁系統實作（`studies/pagination.py`）
4. 前端 API 契約（`project.ts`）
5. Django Ninja 官方文件
6. PostgreSQL JSON 欄位最佳實踐

---

**文件狀態**：✅ 需求規格完成，等待實作  
**下一步**：等待 pagination 分支合併後，建立 feat/projects-implementation 分支開始實作  
**預計開始時間**：pagination PR 合併後 1 個工作天內