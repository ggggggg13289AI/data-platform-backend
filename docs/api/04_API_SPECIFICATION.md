# API接口规范文档

**版本**: v2.0.0 (Phase 1)
**最后更新**: 2024-12-01
**状态**: AI辅助报告筛选系统

## API设计原则

### RESTful设计规范
1. **资源导向**：URL表示资源，HTTP方法表示操作
2. **无状态**：每个请求包含所有必要信息
3. **统一接口**：标准化的请求/响应格式
4. **层次结构**：清晰的资源层级关系

### 版本控制
```
格式：/api/v1/{resource}
示例：/api/v1/reports
```

### 通用约定
- **基础URL**：`http://localhost:8000/api/v1`
- **编码**：UTF-8
- **时间格式**：ISO 8601 (YYYY-MM-DDTHH:mm:ss.sssZ)
- **分页参数**：`page`, `page_size`
- **排序参数**：`sort`, `order` (asc/desc)

## 通用响应格式

### 成功响应（FastAPI默认）
```json
{
  "id": 1,
  "patient_name": "张三",
  "exam_date": "2024-11-30",
  // ... 其他字段
}
```

### 错误响应（FastAPI默认）
```json
{
  "detail": "报告不存在"
}
```

或带验证错误：
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

### 分页响应
```json
{
  "items": [ /* 数据列表 */ ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

## 认证授权

### JWT认证流程

#### 1. 登录
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=secure_password
```

**注意**：FastAPI OAuth2PasswordBearer使用表单格式，不是JSON

**响应**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "张三",
    "role": "researcher"
  }
}
```

#### 2. 获取当前用户
```http
GET /api/v1/auth/me
Authorization: Bearer {access_token}
```

**响应**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "张三",
  "role": "researcher",
  "is_active": true,
  "last_login_at": "2024-12-01T10:30:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### 3. 登出（客户端清除token）
```http
POST /api/v1/auth/logout
Authorization: Bearer {access_token}
```

**响应**
```json
{
  "message": "Logged out successfully"
}
```

### 请求头示例
```http
Authorization: Bearer {access_token}
Content-Type: application/json
Accept: application/json
```

## Phase 1 API端点列表

### 1. 认证模块 (Authentication)
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录 | 公开 |
| GET | `/api/v1/auth/me` | 获取当前用户 | 需认证 |
| POST | `/api/v1/auth/logout` | 用户登出 | 需认证 |

### 2. 数据导入模块 (Import)
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/import/preview` | 预览导入数据 | researcher |
| POST | `/api/v1/import/execute` | 执行数据导入 | researcher |

### 3. 报告管理模块 (Reports)
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/reports` | 获取报告列表（带搜索筛选） | researcher |
| GET | `/api/v1/reports/{id}` | 获取报告详情 | researcher |
| DELETE | `/api/v1/reports/{id}` | 删除报告（软删除） | admin |

### 4. AI分析模块 (AI Analysis)
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/ai/analyze` | 单个报告AI分析 | researcher |
| POST | `/api/v1/ai/batch-analyze` | 批量报告分析（后台任务） | researcher |
| GET | `/api/v1/ai/annotations/{report_id}` | 获取报告的所有AI标注 | researcher |
| DELETE | `/api/v1/ai/annotations/{id}` | 删除AI标注 | researcher |

### 5. 项目管理模块 (Projects)
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/projects` | 获取项目列表 | researcher |
| POST | `/api/v1/projects` | 创建项目 | researcher |
| GET | `/api/v1/projects/{id}` | 获取项目详情 | researcher |
| PUT | `/api/v1/projects/{id}` | 更新项目 | researcher |
| DELETE | `/api/v1/projects/{id}` | 删除项目（软删除） | researcher |
| POST | `/api/v1/projects/{id}/reports` | 添加报告到项目 | researcher |
| DELETE | `/api/v1/projects/{id}/reports/{report_id}` | 从项目移除报告 | researcher |

### 6. 数据导出模块 (Export)
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/export/project` | 导出项目报告（Excel/CSV/JSON） | researcher |
| POST | `/api/v1/export/search` | 导出搜索结果 | researcher |

### 7. 系统健康检查 (Health)
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/health` | 系统健康检查 | 公开 |

**总计**：约20个API端点

## API端点详细设计

### 1. 认证模块 (Authentication)

#### 1.1 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=researcher@example.com&password=SecurePassword123
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户邮箱 |
| password | string | 是 | 用户密码 |

**响应示例**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJyZXNlYXJjaGVyQGV4YW1wbGUuY29tIiwiZXhwIjoxNzAxNDM2MjAwfQ.abc123",
  "token_type": "bearer",
  "user": {
    "id": 2,
    "email": "researcher@example.com",
    "full_name": "研究员A",
    "role": "researcher",
    "is_active": true
  }
}
```

**错误响应**
```json
{
  "detail": "Invalid credentials"
}
```

#### 1.2 获取当前用户
```http
GET /api/v1/auth/me
Authorization: Bearer {access_token}
```

**响应示例**
```json
{
  "id": 2,
  "email": "researcher@example.com",
  "full_name": "研究员A",
  "role": "researcher",
  "is_active": true,
  "last_login_at": "2024-12-01T10:30:00Z",
  "created_at": "2024-06-01T00:00:00Z",
  "updated_at": "2024-12-01T10:30:00Z"
}
```

### 2. 数据导入模块 (Import)

#### 2.1 预览导入数据
```http
POST /api/v1/import/preview
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: [Excel/CSV文件]
```

**响应示例**
```json
{
  "columns": [
    "patient_id",
    "patient_name",
    "exam_date",
    "exam_type",
    "report_content"
  ],
  "preview": [
    {
      "patient_id": "P2024001",
      "patient_name": "张三",
      "exam_date": "2024-11-30",
      "exam_type": "CT",
      "report_content": "胸部CT检查：双肺纹理增多..."
    },
    // ... 前100行
  ],
  "total_rows": 5000,
  "suggested_mapping": {
    "patient_id": "patient_id",
    "patient_name": "patient_name",
    "exam_date": "exam_date",
    "exam_type": "exam_type",
    "report_content": "report_content"
  }
}
```

#### 2.2 执行数据导入
```http
POST /api/v1/import/execute
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: [Excel/CSV文件]
field_mapping: [
  {
    "source_field": "患者ID",
    "target_field": "patient_id"
  },
  {
    "source_field": "患者姓名",
    "target_field": "patient_name"
  }
]
```

**请求体（JSON部分）**
```json
{
  "field_mapping": [
    {"source_field": "患者ID", "target_field": "patient_id"},
    {"source_field": "患者姓名", "target_field": "patient_name"},
    {"source_field": "检查日期", "target_field": "exam_date"},
    {"source_field": "检查类型", "target_field": "exam_type"},
    {"source_field": "报告内容", "target_field": "report_content"}
  ]
}
```

**响应示例**
```json
{
  "imported_count": 4850,
  "skipped_count": 150,
  "error_count": 0,
  "errors": [],
  "duration_seconds": 45.2
}
```

### 3. 报告管理模块 (Reports)

#### 3.1 获取报告列表（带搜索筛选）
```http
GET /api/v1/reports?q=肺部&exam_type=CT&date_from=2024-01-01&date_to=2024-12-31&page=1&page_size=20
Authorization: Bearer {token}
```

**查询参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| q | string | 否 | 全文搜索关键词（报告内容、患者姓名） |
| patient_id | string | 否 | 患者ID精确匹配 |
| exam_type | string | 否 | 检查类型（CT、MRI、X-Ray等） |
| date_from | date | 否 | 开始日期（YYYY-MM-DD） |
| date_to | date | 否 | 结束日期（YYYY-MM-DD） |
| department | string | 否 | 部门筛选 |
| page | integer | 否 | 页码（默认1） |
| page_size | integer | 否 | 每页数量（默认20，最大100） |
| sort | string | 否 | 排序字段（exam_date, created_at） |
| order | string | 否 | 排序方向（asc, desc，默认desc） |

**响应示例**
```json
{
  "items": [
    {
      "id": 1,
      "patient_id": "P2024001",
      "patient_name": "张三",
      "patient_age": 45,
      "patient_gender": "M",
      "exam_date": "2024-11-30",
      "exam_type": "CT",
      "exam_description": "胸部CT平扫+增强",
      "department": "放射科",
      "report_content": "胸部CT检查：双肺纹理增多，未见明显实质性病变...",
      "findings": "双肺纹理增多",
      "diagnosis": "慢性支气管炎",
      "impression": "建议随访",
      "icd_codes": ["J42"],
      "source": "import",
      "imported_by": 1,
      "imported_at": "2024-12-01T09:00:00Z",
      "created_at": "2024-12-01T09:00:00Z",
      "updated_at": "2024-12-01T09:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

#### 3.2 获取报告详情
```http
GET /api/v1/reports/1
Authorization: Bearer {token}
```

**响应示例**
```json
{
  "id": 1,
  "patient_id": "P2024001",
  "patient_name": "张三",
  "patient_age": 45,
  "patient_gender": "M",
  "exam_date": "2024-11-30",
  "exam_type": "CT",
  "exam_description": "胸部CT平扫+增强",
  "department": "放射科",
  "report_content": "胸部CT检查：双肺纹理增多，心影不大，纵隔未见肿大淋巴结...",
  "findings": "双肺纹理增多，心影不大",
  "diagnosis": "慢性支气管炎",
  "impression": "建议随访",
  "icd_codes": ["J42"],
  "source": "import",
  "source_reference": "papa_2024_batch1.xlsx",
  "imported_by": 1,
  "imported_at": "2024-12-01T09:00:00Z",
  "created_at": "2024-12-01T09:00:00Z",
  "updated_at": "2024-12-01T09:00:00Z",
  "is_deleted": false,
  "ai_annotations": [
    {
      "id": 1,
      "annotation_type": "classification",
      "user_prompt": "请判断报告的严重程度",
      "content": {
        "category": "mild",
        "confidence": 0.85,
        "reasoning": "存在轻度异常但无严重病变"
      },
      "confidence": 0.85,
      "model_name": "qwen2.5:7b",
      "created_at": "2024-12-01T10:00:00Z"
    }
  ],
  "projects": [
    {
      "id": 1,
      "name": "肺部疾病研究2024",
      "added_at": "2024-12-01T11:00:00Z"
    }
  ]
}
```

#### 3.3 删除报告（软删除）
```http
DELETE /api/v1/reports/1
Authorization: Bearer {token}
```

**响应示例**
```json
{
  "message": "Report deleted successfully",
  "id": 1
}
```

### 4. AI分析模块 (AI Analysis)

#### 4.1 单个报告AI分析
```http
POST /api/v1/ai/analyze
Authorization: Bearer {token}
Content-Type: application/json

{
  "report_id": 1,
  "user_prompt": "请提取报告中的所有关键发现和测量数值",
  "annotation_type": "extraction"
}
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| report_id | integer | 是 | 报告ID |
| user_prompt | string | 是 | 用户自定义提示词 |
| annotation_type | string | 是 | 标注类型：highlight, classification, extraction, scoring |

**响应示例**
```json
{
  "annotation_id": 5,
  "report_id": 1,
  "annotation_type": "extraction",
  "content": {
    "findings": [
      "双肺纹理增多",
      "心影不大",
      "纵隔未见肿大淋巴结"
    ],
    "measurements": [
      {
        "item": "心胸比例",
        "value": "0.48",
        "unit": "ratio"
      }
    ],
    "locations": [
      "双肺",
      "心脏",
      "纵隔"
    ]
  },
  "confidence": 0.92,
  "model_name": "qwen2.5:7b",
  "model_temperature": 0.7,
  "created_at": "2024-12-01T10:30:00Z",
  "duration_seconds": 35.2
}
```

**错误响应**
```json
{
  "detail": "Ollama service unavailable"
}
```

#### 4.2 批量报告分析（后台任务）
```http
POST /api/v1/ai/batch-analyze
Authorization: Bearer {token}
Content-Type: application/json

{
  "report_ids": [1, 2, 3, 4, 5],
  "user_prompt": "请判断报告的严重程度",
  "annotation_type": "classification"
}
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| report_ids | array | 是 | 报告ID列表（最多50个） |
| user_prompt | string | 是 | 用户自定义提示词 |
| annotation_type | string | 是 | 标注类型 |

**响应示例**
```json
{
  "message": "Batch analysis started",
  "task_id": "batch_20241201_103000",
  "total_reports": 5,
  "estimated_duration_minutes": 3
}
```

**说明**：批量分析在后台执行，客户端需轮询或通过WebSocket获取进度

#### 4.3 获取报告的所有AI标注
```http
GET /api/v1/ai/annotations/1?annotation_type=classification
Authorization: Bearer {token}
```

**查询参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| annotation_type | string | 否 | 筛选标注类型 |

**响应示例**
```json
{
  "report_id": 1,
  "annotations": [
    {
      "id": 1,
      "annotation_type": "classification",
      "user_prompt": "请判断报告的严重程度",
      "content": {
        "category": "mild",
        "confidence": 0.85,
        "reasoning": "存在轻度异常但无严重病变"
      },
      "confidence": 0.85,
      "model_name": "qwen2.5:7b",
      "is_edited": false,
      "created_at": "2024-12-01T10:00:00Z"
    },
    {
      "id": 5,
      "annotation_type": "extraction",
      "user_prompt": "请提取关键发现",
      "content": {
        "findings": ["双肺纹理增多", "心影不大"]
      },
      "confidence": 0.92,
      "model_name": "qwen2.5:7b",
      "created_at": "2024-12-01T10:30:00Z"
    }
  ],
  "total": 2
}
```

#### 4.4 删除AI标注
```http
DELETE /api/v1/ai/annotations/1
Authorization: Bearer {token}
```

**响应示例**
```json
{
  "message": "Annotation deleted successfully",
  "id": 1
}
```

### 5. 项目管理模块 (Projects)

#### 5.1 获取项目列表
```http
GET /api/v1/projects?status=active&page=1&page_size=20
Authorization: Bearer {token}
```

**查询参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 项目状态：active, archived, completed |
| search | string | 否 | 搜索项目名称 |
| page | integer | 否 | 页码（默认1） |
| page_size | integer | 否 | 每页数量（默认20） |

**响应示例**
```json
{
  "items": [
    {
      "id": 1,
      "name": "肺部疾病研究2024",
      "description": "针对肺部CT影像的回顾性研究",
      "tags": ["肺部", "CT", "回顾性研究"],
      "status": "active",
      "report_count": 150,
      "created_by": 2,
      "creator_name": "研究员A",
      "created_at": "2024-11-01T00:00:00Z",
      "updated_at": "2024-12-01T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

#### 5.2 创建项目
```http
POST /api/v1/projects
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "心脏疾病研究2024",
  "description": "针对心脏MRI影像的前瞻性研究",
  "tags": ["心脏", "MRI", "前瞻性研究"]
}
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 项目名称（2-200字符） |
| description | string | 否 | 项目描述 |
| tags | array | 否 | 标签列表 |

**响应示例**
```json
{
  "id": 2,
  "name": "心脏疾病研究2024",
  "description": "针对心脏MRI影像的前瞻性研究",
  "tags": ["心脏", "MRI", "前瞻性研究"],
  "status": "active",
  "report_count": 0,
  "created_by": 2,
  "creator_name": "研究员A",
  "created_at": "2024-12-01T11:00:00Z",
  "updated_at": "2024-12-01T11:00:00Z"
}
```

#### 5.3 获取项目详情
```http
GET /api/v1/projects/1
Authorization: Bearer {token}
```

**响应示例**
```json
{
  "id": 1,
  "name": "肺部疾病研究2024",
  "description": "针对肺部CT影像的回顾性研究",
  "tags": ["肺部", "CT", "回顾性研究"],
  "status": "active",
  "report_count": 150,
  "created_by": 2,
  "creator_name": "研究员A",
  "created_at": "2024-11-01T00:00:00Z",
  "updated_at": "2024-12-01T10:00:00Z",
  "reports_summary": {
    "total": 150,
    "by_exam_type": {
      "CT": 150
    },
    "by_department": {
      "放射科": 150
    },
    "date_range": {
      "earliest": "2024-01-01",
      "latest": "2024-11-30"
    }
  }
}
```

#### 5.4 更新项目
```http
PUT /api/v1/projects/1
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "肺部疾病研究2024（更新）",
  "description": "扩展研究范围",
  "tags": ["肺部", "CT", "回顾性研究", "扩展"],
  "status": "active"
}
```

**响应示例**
```json
{
  "id": 1,
  "name": "肺部疾病研究2024（更新）",
  "description": "扩展研究范围",
  "tags": ["肺部", "CT", "回顾性研究", "扩展"],
  "status": "active",
  "updated_at": "2024-12-01T11:30:00Z"
}
```

#### 5.5 删除项目（软删除）
```http
DELETE /api/v1/projects/1
Authorization: Bearer {token}
```

**响应示例**
```json
{
  "message": "Project deleted successfully",
  "id": 1
}
```

#### 5.6 添加报告到项目
```http
POST /api/v1/projects/1/reports
Authorization: Bearer {token}
Content-Type: application/json

{
  "report_ids": [1, 2, 3, 4, 5],
  "notes": "初步筛选的符合标准的报告"
}
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| report_ids | array | 是 | 报告ID列表 |
| notes | string | 否 | 备注说明 |

**响应示例**
```json
{
  "project_id": 1,
  "added_count": 5,
  "skipped_count": 0,
  "total_reports": 155
}
```

#### 5.7 从项目移除报告
```http
DELETE /api/v1/projects/1/reports/5
Authorization: Bearer {token}
```

**响应示例**
```json
{
  "message": "Report removed from project",
  "project_id": 1,
  "report_id": 5,
  "total_reports": 154
}
```

### 6. 数据导出模块 (Export)

#### 6.1 导出项目报告
```http
POST /api/v1/export/project
Authorization: Bearer {token}
Content-Type: application/json

{
  "project_id": 1,
  "format": "excel",
  "include_ai_annotations": true,
  "fields": [
    "patient_id",
    "patient_name",
    "exam_date",
    "exam_type",
    "report_content",
    "diagnosis"
  ]
}
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| project_id | integer | 是 | 项目ID |
| format | string | 是 | 导出格式：excel, csv, json |
| include_ai_annotations | boolean | 否 | 是否包含AI标注（默认false） |
| fields | array | 否 | 指定导出字段（不指定则全部） |

**响应**：返回文件下载流

```http
HTTP/1.1 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="project_1_export_20241201.xlsx"

[Binary Excel file content]
```

#### 6.2 导出搜索结果
```http
POST /api/v1/export/search
Authorization: Bearer {token}
Content-Type: application/json

{
  "search_params": {
    "q": "肺部",
    "exam_type": "CT",
    "date_from": "2024-01-01",
    "date_to": "2024-12-31"
  },
  "format": "csv",
  "include_ai_annotations": false
}
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| search_params | object | 是 | 搜索参数（与GET /reports相同） |
| format | string | 是 | 导出格式 |
| include_ai_annotations | boolean | 否 | 是否包含AI标注 |

**响应**：返回文件下载流

### 7. 系统健康检查 (Health)

#### 7.1 健康检查
```http
GET /api/v1/health
```

**响应示例（正常）**
```json
{
  "status": "healthy",
  "checks": {
    "database": true,
    "ollama": true,
    "disk": true
  },
  "version": "2.0.0",
  "timestamp": "2024-12-01T12:00:00Z"
}
```

**响应示例（异常）**
```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "status": "unhealthy",
  "checks": {
    "database": true,
    "ollama": false,
    "disk": true
  },
  "errors": [
    "Ollama service unavailable at http://localhost:11434"
  ],
  "version": "2.0.0",
  "timestamp": "2024-12-01T12:00:00Z"
}
```

## 错误码定义

### HTTP状态码
| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 删除成功 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证或token无效 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务不可用（如Ollama宕机） |

### 业务错误码（FastAPI自定义）
| 错误码 | 说明 |
|--------|------|
| INVALID_CREDENTIALS | 用户名或密码错误 |
| REPORT_NOT_FOUND | 报告不存在 |
| PROJECT_NOT_FOUND | 项目不存在 |
| OLLAMA_UNAVAILABLE | Ollama服务不可用 |
| OLLAMA_TIMEOUT | AI分析超时 |
| IMPORT_FAILED | 数据导入失败 |
| EXPORT_FAILED | 数据导出失败 |
| INVALID_FILE_FORMAT | 不支持的文件格式 |
| DUPLICATE_REPORT | 重复的报告 |
| BATCH_SIZE_EXCEEDED | 批量操作超过限制 |

## API使用示例

### Python示例（使用requests）
```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# 1. 登录获取token
response = requests.post(
    f"{BASE_URL}/auth/login",
    data={
        "username": "researcher@example.com",
        "password": "SecurePassword123"
    }
)
token = response.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 2. 搜索报告
response = requests.get(
    f"{BASE_URL}/reports",
    params={
        "q": "肺部",
        "exam_type": "CT",
        "page": 1,
        "page_size": 20
    },
    headers=headers
)
reports = response.json()["items"]

# 3. AI分析报告
response = requests.post(
    f"{BASE_URL}/ai/analyze",
    json={
        "report_id": reports[0]["id"],
        "user_prompt": "请提取关键发现",
        "annotation_type": "extraction"
    },
    headers=headers
)
annotation = response.json()

# 4. 创建项目
response = requests.post(
    f"{BASE_URL}/projects",
    json={
        "name": "肺部疾病研究2024",
        "description": "回顾性研究",
        "tags": ["肺部", "CT"]
    },
    headers=headers
)
project = response.json()

# 5. 添加报告到项目
report_ids = [r["id"] for r in reports[:10]]
response = requests.post(
    f"{BASE_URL}/projects/{project['id']}/reports",
    json={"report_ids": report_ids},
    headers=headers
)

# 6. 导出项目数据
response = requests.post(
    f"{BASE_URL}/export/project",
    json={
        "project_id": project["id"],
        "format": "excel",
        "include_ai_annotations": True
    },
    headers=headers
)

with open("export.xlsx", "wb") as f:
    f.write(response.content)
```

### TypeScript示例（使用axios）
```typescript
import axios from 'axios';

const BASE_URL = 'http://localhost:8000/api/v1';

// 创建axios实例
const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器（添加token）
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 1. 登录
async function login(email: string, password: string) {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);

  const response = await axios.post(`${BASE_URL}/auth/login`, formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  const { access_token } = response.data;
  localStorage.setItem('access_token', access_token);
  return response.data;
}

// 2. 搜索报告
async function searchReports(params: {
  q?: string;
  exam_type?: string;
  page?: number;
  page_size?: number;
}) {
  const response = await api.get('/reports', { params });
  return response.data;
}

// 3. AI分析
async function analyzeReport(
  reportId: number,
  userPrompt: string,
  annotationType: string
) {
  const response = await api.post('/ai/analyze', {
    report_id: reportId,
    user_prompt: userPrompt,
    annotation_type: annotationType,
  });
  return response.data;
}

// 4. 创建项目
async function createProject(name: string, description: string, tags: string[]) {
  const response = await api.post('/projects', {
    name,
    description,
    tags,
  });
  return response.data;
}

// 5. 导出项目
async function exportProject(projectId: number, format: 'excel' | 'csv' | 'json') {
  const response = await api.post(
    '/export/project',
    {
      project_id: projectId,
      format,
      include_ai_annotations: true,
    },
    {
      responseType: 'blob',
    }
  );

  // 触发下载
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `project_${projectId}.${format === 'excel' ? 'xlsx' : format}`);
  document.body.appendChild(link);
  link.click();
  link.remove();
}
```

## API测试

### 使用FastAPI自动文档
访问 `http://localhost:8000/docs` 可以看到自动生成的Swagger UI，可以直接在浏览器测试所有API。

### 使用curl测试
```bash
# 1. 登录
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=researcher@example.com&password=SecurePassword123"

# 保存token
TOKEN="your_access_token_here"

# 2. 搜索报告
curl -X GET "http://localhost:8000/api/v1/reports?q=肺部&page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"

# 3. AI分析
curl -X POST "http://localhost:8000/api/v1/ai/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": 1,
    "user_prompt": "请提取关键发现",
    "annotation_type": "extraction"
  }'

# 4. 创建项目
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试项目",
    "description": "API测试",
    "tags": ["test"]
  }'
```

## 速率限制（Phase 2）

Phase 1暂不实现速率限制，Phase 2可考虑添加：
- 每用户 100 请求/分钟
- AI分析 10 次/分钟
- 导出操作 5 次/小时

## 版本更新日志

### v2.0.0 (2024-12-01) - Phase 1
- 完全重写API规范
- 从50+端点简化到20个核心端点
- 移除所有DICOM影像相关API
- 添加AI分析API（单个和批量）
- 添加项目管理API
- 添加数据导入和导出API
- 简化认证流程（仅JWT，移除refresh token）

### v1.0.0 (之前版本)
- 完整影像平台API（50+端点）
- DICOM上传下载
- 影像查看器集成
- 复杂权限管理

## 下一步

参考以下文档继续了解：
- [数据库设计](../database/03_DATABASE_DESIGN.md) - 5张核心表设计（v2.0.0）
- [技术架构设计](../architecture/02_TECHNICAL_ARCHITECTURE.md) - 系统架构（v2.0.0）
- [功能规格说明](../requirements/FUNCTIONAL_SPECIFICATION.md) - 实现细节（v2.0.0）
- [开发工作流](../workflow/05_DEVELOPMENT_WORKFLOW.md) - 8周开发计划
- [AI集成指南](../guides/AI_INTEGRATION_GUIDE.md) - Ollama部署（待创建）

---

**文档版本**: v2.0.0
**维护团队**: 影像数据平台开发团队
**最后审核**: 2024-12-01
