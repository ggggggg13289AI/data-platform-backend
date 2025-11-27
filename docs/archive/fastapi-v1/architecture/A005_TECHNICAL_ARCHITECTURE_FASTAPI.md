# 技术架构设计

**版本**: v2.0.0 (Phase 1)
**最后更新**: 2024-12-01
**状态**: AI辅助报告筛选系统

## 系统架构概览

### Phase 1 简化架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户层                                   │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  Web浏览器 (React + TypeScript)                      │        │
│  │  - 报告搜索和筛选界面                                │        │
│  │  - AI分析结果展示                                    │        │
│  │  - 项目管理                                          │        │
│  └──────────────────────┬──────────────────────────────┘        │
└────────────────────────┼─────────────────────────────────────────┘
                         │ HTTP/HTTPS
┌────────────────────────┼─────────────────────────────────────────┐
│              应用层 (Application Layer)                          │
│                        │                                          │
│  ┌─────────────────────▼─────────────────────────────────┐       │
│  │  FastAPI Backend (Python 3.10+)                       │       │
│  │  ──────────────────────────────────────────────       │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │       │
│  │  │ REST API     │  │ Ollama Client│  │ Background │  │       │
│  │  │ Endpoints    │  │ (httpx async)│  │ Tasks      │  │       │
│  │  └──────────────┘  └──────────────┘  └────────────┘  │       │
│  │                                                        │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │       │
│  │  │ Auth/AuthZ   │  │ Business     │  │ Data       │  │       │
│  │  │ (JWT)        │  │ Logic        │  │ Validation │  │       │
│  │  └──────────────┘  └──────────────┘  └────────────┘  │       │
│  └────────────────────┬───────────────────┬─────────────┘       │
└───────────────────────┼───────────────────┼──────────────────────┘
                        │                   │
┌───────────────────────┼───────────────────┼──────────────────────┐
│              数据层 (Data Layer)           │                      │
│                       │                   │                      │
│  ┌────────────────────▼──────┐  ┌─────────▼──────────────┐      │
│  │   PostgreSQL 14+          │  │   Ollama LLM           │      │
│  │   ───────────────          │  │   ─────────            │      │
│  │  - 5张核心表               │  │  - qwen2.5:7b          │      │
│  │  - 用户和报告数据           │  │  - 本地部署            │      │
│  │  - AI标注结果(JSONB)       │  │  - REST API            │      │
│  │  - 项目管理                │  │  - JSON响应格式        │      │
│  │  - 全文搜索(GIN索引)       │  │                        │      │
│  └───────────────────────────┘  └────────────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
```

### Phase 1 架构特点

**简化设计原则**：
- ✅ **单一后端**：FastAPI处理所有业务逻辑
- ✅ **本地LLM**：Ollama独立部署，通过REST API调用
- ✅ **PostgreSQL**：唯一数据存储，利用JSONB和全文搜索
- ✅ **无中间件**：移除Redis、Celery，使用FastAPI BackgroundTasks
- ✅ **无对象存储**：Phase 1不处理DICOM影像文件

**移除的组件**（Phase 2再引入）：
- ❌ Redis缓存层
- ❌ Celery任务队列
- ❌ MinIO对象存储
- ❌ Cornerstone.js DICOM查看器
- ❌ Elasticsearch全文搜索
- ❌ 外部系统集成（Accssyn、Red Report自动同步）

## 技术选型详解

### 前端技术栈

#### React生态系统（Phase 1）
```json
{
  "core": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "typescript": "^5.3.3"
  },
  "ui": {
    "antd": "^5.12.0",
    "@ant-design/icons": "^5.2.6"
  },
  "state": {
    "zustand": "^4.4.7"
  },
  "http": {
    "axios": "^1.6.2"
  },
  "utils": {
    "dayjs": "^1.11.10",
    "lodash-es": "^4.17.21"
  },
  "dev": {
    "vite": "^5.0.8",
    "eslint": "^8.56.0",
    "prettier": "^3.1.1"
  }
}
```

#### 核心库说明

**Ant Design 5.x** - 企业级UI组件库
- 完整的组件体系（Table、Form、Modal等）
- 中文优先支持
- TypeScript类型完善
- 自定义主题能力

**Zustand** - 轻量级状态管理
- 体积小（~1KB gzipped）
- 无需Provider包裹
- TypeScript友好
- 比Redux简单但足够强大
- 适合中小型应用

**Vite** - 现代构建工具
- 快速冷启动（ESM）
- 热更新（HMR）
- 优化的生产构建
- 开箱即用的TypeScript支持

**Phase 1移除的前端库**：
- ❌ React Query（服务端状态管理）- 使用Zustand + Axios足够
- ❌ Cornerstone.js（DICOM查看器）- Phase 2再引入
- ❌ dicom-parser - Phase 2再引入

### 后端技术栈（Python FastAPI）

#### 核心依赖（Phase 1）
```python
# requirements.txt
# Web框架
fastapi==0.104.1
uvicorn[standard]==0.25.0
pydantic==2.5.3
python-multipart==0.0.6

# 数据库
sqlalchemy==2.0.23
alembic==1.13.1
psycopg2-binary==2.9.9

# 认证授权
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# 异步HTTP客户端（调用Ollama）
httpx==0.26.0

# 数据处理
pandas==2.1.4
openpyxl==3.1.2  # Excel支持

# 工具库
python-dotenv==1.0.0
```

#### FastAPI优势

**为什么选择FastAPI**：
- **高性能**：基于Starlette和Pydantic，性能接近NodeJS/Go
- **异步支持**：原生async/await，适合调用Ollama等IO密集操作
- **自动文档**：Swagger UI和ReDoc开箱即用，便于前端对接
- **类型安全**：Pydantic数据验证，自动类型检查和错误提示
- **现代Python**：充分利用Python 3.10+特性（类型注解、match语句）
- **生产就绪**：被Uber、Netflix、Microsoft等公司使用

**FastAPI vs 其他框架**：
| 框架 | 性能 | 异步支持 | 学习曲线 | 文档质量 | 类型安全 |
|------|------|----------|----------|----------|----------|
| FastAPI | ⭐⭐⭐⭐⭐ | 原生 | 低 | 优秀 | ⭐⭐⭐⭐⭐ |
| Django | ⭐⭐⭐ | 部分 | 中 | 优秀 | ⭐⭐⭐ |
| Flask | ⭐⭐⭐ | 插件 | 低 | 良好 | ⭐⭐ |
| Node.js | ⭐⭐⭐⭐ | 原生 | 中 | 良好 | ⭐⭐⭐ |

**Phase 1移除的后端库**：
- ❌ celery（任务队列）- 使用FastAPI BackgroundTasks
- ❌ redis（缓存）- Phase 1不需要缓存
- ❌ boto3/minio（对象存储）- Phase 1不处理文件存储
- ❌ pydicom（DICOM处理）- Phase 2再引入

### Ollama本地LLM集成

#### Ollama架构

```
┌─────────────────────────────────────────────────┐
│  FastAPI Backend                                │
│                                                 │
│  ┌───────────────────────────────────────┐     │
│  │  OllamaClient (httpx AsyncClient)     │     │
│  │  ────────────────────────────────     │     │
│  │  async def chat()                     │     │
│  │  async def analyze_report()           │     │
│  │  async def batch_analyze()            │     │
│  └───────────────┬───────────────────────┘     │
└──────────────────┼─────────────────────────────┘
                   │ HTTP REST API
                   │ POST /api/chat
┌──────────────────▼─────────────────────────────┐
│  Ollama Service (Port 11434)                   │
│  ─────────────────────────────                 │
│  ┌─────────────────────────────────────┐       │
│  │  Model: qwen2.5:7b                  │       │
│  │  - 7B参数                            │       │
│  │  - 中文优化                          │       │
│  │  - 医学术语理解                      │       │
│  │  - JSON输出支持                      │       │
│  └─────────────────────────────────────┘       │
│                                                 │
│  GPU/CPU资源                                    │
│  - CPU模式：8GB RAM                             │
│  - GPU模式：4GB VRAM（推荐）                    │
└─────────────────────────────────────────────────┘
```

#### 推荐模型选择

**主推荐：qwen2.5:7b**（Alibaba开源）
- **参数量**：7B（约4.4GB模型文件）
- **中文能力**：针对中文优化，理解医学报告效果好
- **硬件要求**：最低8GB RAM（CPU模式），4GB VRAM（GPU模式）
- **推理速度**：CPU ~30-60秒/报告，GPU ~10-20秒/报告
- **部署命令**：`ollama pull qwen2.5:7b`

**备选模型**：
1. **llama3.1:8b** - 英文能力强，中文稍弱
2. **mistral:7b** - 平衡性能，推理速度快
3. **gemma2:9b** - Google开源，质量高但稍慢

**模型对比**：
| 模型 | 参数 | 文件大小 | 中文能力 | 推理速度 | 医学理解 |
|------|------|----------|----------|----------|----------|
| qwen2.5:7b | 7B | 4.4GB | ⭐⭐⭐⭐⭐ | 中 | ⭐⭐⭐⭐ |
| llama3.1:8b | 8B | 4.7GB | ⭐⭐⭐ | 中 | ⭐⭐⭐ |
| mistral:7b | 7B | 4.1GB | ⭐⭐ | 快 | ⭐⭐⭐ |
| gemma2:9b | 9B | 5.4GB | ⭐⭐⭐⭐ | 慢 | ⭐⭐⭐⭐ |

#### Ollama API调用流程

```python
# app/services/ollama_client.py
import httpx
from typing import Dict, Any, List

class OllamaClient:
    """Ollama本地LLM客户端"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen2.5:7b"
        self.timeout = httpx.Timeout(60.0, connect=5.0)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        format: str = "json",
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """与Ollama LLM对话"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "format": format,        # 强制JSON输出
                    "temperature": temperature,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()

    async def analyze_report(
        self,
        report_text: str,
        user_prompt: str,
        annotation_type: str
    ) -> Dict[str, Any]:
        """分析医学报告"""
        system_prompt = self._build_system_prompt(annotation_type)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
用户需求: {user_prompt}

报告内容:
{report_text}

请按照JSON格式返回分析结果。
"""}
        ]

        response = await self.chat(messages, format="json")

        # 解析JSON响应
        import json
        try:
            content = json.loads(response["message"]["content"])
        except json.JSONDecodeError:
            content = {"raw_text": response["message"]["content"]}

        return {
            "annotation_type": annotation_type,
            "content": content,
            "raw_response": response["message"]["content"]
        }

    def _build_system_prompt(self, annotation_type: str) -> str:
        """构建系统提示词"""
        prompts = {
            "highlight": """你是一个医学报告分析助手。请仔细阅读报告，标记出关键发现。
返回JSON格式: {"highlights": [{"text": "...", "reason": "..."}]}""",

            "classification": """你是一个医学报告分类助手。请判断报告的严重程度。
返回JSON格式: {"category": "normal|mild|moderate|severe", "reasoning": "..."}""",

            "extraction": """你是一个医学信息提取助手。请提取关键信息。
返回JSON格式: {"findings": [...], "measurements": [...]}""",

            "scoring": """你是一个医学报告评分助手。请评估报告的严重程度。
返回JSON格式: {"score": 1-5, "severity": "...", "reasoning": "..."}"""
        }
        return prompts.get(annotation_type, prompts["highlight"])
```

#### 并发控制和错误处理

```python
# app/api/ai_analysis.py
import asyncio
from fastapi import BackgroundTasks
from typing import List

# 控制并发数（避免Ollama过载）
semaphore = asyncio.Semaphore(3)  # 最多3个并发

async def analyze_one_report(
    report_id: int,
    user_prompt: str,
    annotation_type: str
):
    """单个报告分析（带并发控制）"""
    async with semaphore:
        try:
            report = await get_report(report_id)

            # 调用Ollama
            result = await ollama_client.analyze_report(
                report_text=report.content,
                user_prompt=user_prompt,
                annotation_type=annotation_type
            )

            # 保存AI标注
            await save_annotation(report_id, result)

            return {"status": "success", "report_id": report_id}

        except httpx.TimeoutException:
            # Ollama超时（模型加载或推理过慢）
            return {"status": "error", "report_id": report_id,
                    "error": "LLM timeout"}

        except httpx.ConnectError:
            # Ollama服务不可用
            return {"status": "error", "report_id": report_id,
                    "error": "LLM service unavailable"}

        except Exception as e:
            # 其他错误
            return {"status": "error", "report_id": report_id,
                    "error": str(e)}

@router.post("/ai/batch-analyze")
async def batch_analyze(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """批量分析（后台任务）"""

    # 创建异步任务
    async def process_batch():
        tasks = [
            analyze_one_report(rid, request.user_prompt, request.annotation_type)
            for rid in request.report_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        success_count = sum(1 for r in results if r.get("status") == "success")
        error_count = len(results) - success_count

        # 通知用户（可通过WebSocket或数据库状态）
        await notify_batch_completion(success_count, error_count)

    # 添加到后台任务
    background_tasks.add_task(process_batch)

    return {"message": "Batch analysis started", "total": len(request.report_ids)}
```

### 数据库设计（PostgreSQL）

#### 数据库配置（Phase 1）

```yaml
postgresql:
  version: "14.10"

  # Phase 1基础扩展
  extensions:
    - pg_trgm      # 模糊搜索优化
    - btree_gin    # 多列索引优化

  # 基础性能调优（本地部署）
  performance_tuning:
    shared_buffers: "1GB"
    effective_cache_size: "3GB"
    work_mem: "64MB"
    maintenance_work_mem: "256MB"
    max_connections: 50

  # 简单备份策略
  backup_strategy:
    type: "pg_dump"
    frequency: "daily"
    retention: "7 days"
```

#### 5张核心表设计

详见 [DATABASE_DESIGN.md](../database/03_DATABASE_DESIGN.md)

**表结构概览**：
1. **users** - 用户认证（简化设计，仅admin/researcher角色）
2. **reports** - 检查报告（嵌入患者信息）
3. **ai_annotations** - AI标注结果（JSONB存储）
4. **projects** - 项目管理
5. **project_reports** - 项目-报告关联（多对多）

**关键索引**：
```sql
-- 全文搜索索引
CREATE INDEX idx_reports_content_fulltext
ON reports USING gin(to_tsvector('simple', report_content));

-- JSONB索引（AI标注查询）
CREATE INDEX idx_ai_annotations_content_gin
ON ai_annotations USING gin(content);

-- 常用查询索引
CREATE INDEX idx_reports_exam_date ON reports(exam_date);
CREATE INDEX idx_reports_exam_type ON reports(exam_type);
```

**Phase 2扩展路径**：
- 提取独立patients表
- 添加studies表（检查级别）
- 添加images表（DICOM影像元数据）

## 核心模块设计

### 1. 认证授权模块 (Auth Module)

```python
# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录"""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(401, "Invalid credentials")

    access_token = create_access_token({"sub": user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@router.get("/me")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前用户信息"""
    user = await verify_token(token)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user
```

**权限模型（简化RBAC）**：
```python
roles = {
    "admin": ["*"],  # 所有权限
    "researcher": [
        "report:read",
        "report:search",
        "ai:analyze",
        "project:create",
        "project:manage",
        "export:data"
    ]
}
```

### 2. 数据导入模块 (Import Module)

```python
# app/api/import_data.py
import pandas as pd
from io import BytesIO

@router.post("/import/preview")
async def preview_import(file: UploadFile):
    """预览导入数据（前100行）"""
    content = await file.read()

    if file.filename.endswith('.csv'):
        df = pd.read_csv(BytesIO(content))
    else:
        df = pd.read_excel(BytesIO(content))

    return {
        "columns": df.columns.tolist(),
        "preview": df.head(100).to_dict('records'),
        "total_rows": len(df)
    }

@router.post("/import/execute")
async def execute_import(
    file: UploadFile,
    field_mapping: List[FieldMapping]
):
    """执行数据导入"""
    content = await file.read()
    df = pd.read_excel(BytesIO(content))

    # 应用字段映射
    mapping_dict = {m.source_field: m.target_field for m in field_mapping}
    df = df.rename(columns=mapping_dict)

    # 批量插入（100条/batch）
    imported_count = 0
    for idx, row in df.iterrows():
        report = Report(
            patient_id=row.get('patient_id'),
            patient_name=row.get('patient_name'),
            exam_date=pd.to_datetime(row.get('exam_date')),
            exam_type=row.get('exam_type'),
            report_content=row.get('report_content')
        )
        db.add(report)
        imported_count += 1

        if imported_count % 100 == 0:
            db.commit()

    db.commit()
    return {"imported_count": imported_count}
```

### 3. 报告检索模块 (Search Module)

```python
# app/api/reports.py
@router.get("/reports/search")
async def search_reports(
    q: str = None,                    # 全文搜索关键词
    exam_type: str = None,            # 检查类型
    date_from: date = None,           # 开始日期
    date_to: date = None,             # 结束日期
    department: str = None,           # 部门
    page: int = 1,
    page_size: int = 20
):
    """报告搜索和筛选"""
    query = db.query(Report).filter(Report.is_deleted == False)

    # 全文搜索
    if q:
        query = query.filter(
            func.to_tsvector('simple', Report.report_content)
            .op('@@')(func.plainto_tsquery('simple', q))
        )

    # 条件筛选
    if exam_type:
        query = query.filter(Report.exam_type == exam_type)
    if date_from:
        query = query.filter(Report.exam_date >= date_from)
    if date_to:
        query = query.filter(Report.exam_date <= date_to)
    if department:
        query = query.filter(Report.department == department)

    # 分页
    total = query.count()
    reports = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": reports,
        "total": total,
        "page": page,
        "page_size": page_size
    }
```

### 4. AI分析模块 (AI Analysis Module)

详见上文"Ollama本地LLM集成"章节

### 5. 项目管理模块 (Project Module)

```python
# app/api/projects.py
@router.post("/projects")
async def create_project(request: ProjectCreate, user: User = Depends(get_current_user)):
    """创建项目"""
    project = Project(
        name=request.name,
        description=request.description,
        tags=request.tags,
        created_by=user.id
    )
    db.add(project)
    db.commit()
    return project

@router.post("/projects/{project_id}/reports")
async def add_reports_to_project(
    project_id: int,
    report_ids: List[int],
    user: User = Depends(get_current_user)
):
    """添加报告到项目"""
    for report_id in report_ids:
        project_report = ProjectReport(
            project_id=project_id,
            report_id=report_id,
            added_by=user.id
        )
        db.add(project_report)

    db.commit()
    return {"added_count": len(report_ids)}
```

### 6. 数据导出模块 (Export Module)

```python
# app/api/export.py
@router.post("/export")
async def export_data(request: ExportRequest):
    """导出数据"""
    query = db.query(Report).join(ProjectReport).filter(
        ProjectReport.project_id == request.project_id
    )

    reports = query.all()

    if request.format == "excel":
        # 生成Excel
        df = pd.DataFrame([{
            'patient_id': r.patient_id,
            'patient_name': r.patient_name,
            'exam_date': r.exam_date,
            'exam_type': r.exam_type,
            'report_content': r.report_content
        } for r in reports])

        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=export.xlsx"}
        )
```

## 安全架构

### 认证流程（简化版）

```
┌──────────┐                ┌──────────┐
│  Client  │                │  Backend │
└────┬─────┘                └────┬─────┘
     │                           │
     │  1. POST /auth/login      │
     ├──────────────────────────►│
     │  (email + password)       │
     │                           │
     │                           │  2. 验证密码（bcrypt）
     │                           │
     │                           │  3. 生成JWT Token
     │                           │
     │  4. 返回Token             │
     │◄──────────────────────────┤
     │  {access_token}           │
     │                           │
     │  5. 后续请求携带Token      │
     ├──────────────────────────►│
     │  Authorization: Bearer... │
     │                           │
     │                           │  6. 验证Token
     │                           │
     │  7. 返回数据              │
     │◄──────────────────────────┤
```

### 数据安全措施（Phase 1）

1. **传输安全**
   - HTTPS/TLS（生产环境）
   - 本地开发可使用HTTP

2. **存储安全**
   - 密码bcrypt加密（cost=12）
   - JWT令牌（30分钟过期）
   - 数据库连接密码环境变量存储

3. **访问控制**
   - 基于角色的权限控制（admin/researcher）
   - API端点权限验证
   - 用户操作审计日志（created_by, created_at）

4. **数据隐私**
   - 本地部署，数据不出院内网络
   - 软删除策略（is_deleted标记）
   - AI分析结果可删除

## 性能优化策略（Phase 1）

### 数据库优化

```sql
-- 1. 全文搜索优化
CREATE INDEX idx_reports_content_fulltext
ON reports USING gin(to_tsvector('simple', report_content))
WHERE is_deleted = false;

-- 2. 常用查询索引
CREATE INDEX idx_reports_exam_date ON reports(exam_date) WHERE is_deleted = false;
CREATE INDEX idx_reports_exam_type ON reports(exam_type) WHERE is_deleted = false;

-- 3. JSONB查询优化
CREATE INDEX idx_ai_annotations_content_gin
ON ai_annotations USING gin(content);

-- 4. 复合索引
CREATE INDEX idx_reports_search
ON reports(patient_id, exam_date, exam_type)
WHERE is_deleted = false;
```

### 异步处理

```python
# FastAPI BackgroundTasks（替代Celery）
from fastapi import BackgroundTasks

@router.post("/ai/batch-analyze")
async def batch_analyze(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """批量AI分析（后台任务）"""

    async def process():
        # 使用asyncio.Semaphore控制并发
        semaphore = asyncio.Semaphore(3)

        async def analyze_one(report_id):
            async with semaphore:
                # 调用Ollama分析
                result = await ollama_client.analyze_report(...)
                # 保存结果
                await save_annotation(...)

        tasks = [analyze_one(rid) for rid in request.report_ids]
        await asyncio.gather(*tasks)

    background_tasks.add_task(process)
    return {"message": "Batch started"}
```

### 前端优化

```typescript
// 虚拟滚动（大数据列表）
import { List } from 'antd';

<List
  dataSource={reports}
  pagination={{
    pageSize: 20,
    total: totalReports,
    onChange: (page) => fetchReports(page)
  }}
  renderItem={(report) => <ReportCard report={report} />}
/>

// 防抖搜索
import { debounce } from 'lodash-es';

const debouncedSearch = debounce((keyword) => {
  fetchReports({ q: keyword });
}, 300);
```

## 容器化部署（Phase 1）

### Docker Compose配置

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: imagedb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    # GPU支持（可选）
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/imagedb
      OLLAMA_BASE_URL: http://ollama:11434
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      - postgres
      - ollama
    ports:
      - "8000:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  frontend:
    build: ./frontend
    environment:
      VITE_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
    command: npm run dev -- --host 0.0.0.0

volumes:
  postgres_data:
  ollama_data:
```

### 部署步骤

```bash
# 1. 启动所有服务
docker-compose up -d

# 2. 初始化数据库
docker exec -it backend alembic upgrade head

# 3. 下载Ollama模型
docker exec -it ollama ollama pull qwen2.5:7b

# 4. 创建管理员账号
docker exec -it backend python scripts/create_admin.py

# 5. 访问应用
# 前端: http://localhost:3000
# 后端: http://localhost:8000/docs
# Ollama: http://localhost:11434
```

## Phase 2扩展路径

### 待添加组件

**缓存层**：
- Redis（Session存储、API缓存）
- 缓存策略和失效机制

**任务队列**：
- Celery（长时间运行任务）
- Flower（任务监控）

**对象存储**：
- MinIO（DICOM影像存储）
- 生命周期管理

**影像处理**：
- pydicom（DICOM解析）
- Cornerstone.js（前端查看器）

**高级搜索**：
- Elasticsearch（全文搜索增强）
- 复杂查询优化

**系统集成**：
- Accssyn自动同步
- Red Report API对接
- PACS系统集成

### 数据库迁移

详见 [DATABASE_DESIGN.md - 数据迁移策略](../database/03_DATABASE_DESIGN.md#数据迁移策略)

## 监控与运维（Phase 1简化版）

### 健康检查

```python
# app/api/health.py
@router.get("/health")
async def health_check():
    """系统健康检查"""
    checks = {
        "database": await check_database(),
        "ollama": await check_ollama(),
        "disk": check_disk_space()
    }

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks
        }
    )

async def check_database():
    """检查数据库连接"""
    try:
        db.execute("SELECT 1")
        return True
    except:
        return False

async def check_ollama():
    """检查Ollama服务"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return response.status_code == 200
    except:
        return False
```

### 日志记录

```python
# app/core/logging.py
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 使用
logger.info("Report analyzed", extra={"report_id": 123})
logger.error("Ollama timeout", extra={"error": str(e)})
```

## 技术债务管理

### 代码质量工具

```yaml
linting:
  python:
    - ruff      # 快速linter（替代flake8 + isort）
    - mypy      # 类型检查
    - black     # 代码格式化

  javascript:
    - eslint    # 代码检查
    - prettier  # 代码格式化

testing:
  unit_test_coverage: "> 70%"
  integration_test: "核心流程"

  tools:
    - pytest（Python）
    - jest（TypeScript）
```

### 重构优先级

1. **安全性问题**：立即修复
2. **性能瓶颈**：高优先级
3. **代码异味**：中优先级（技术债务）
4. **代码美化**：低优先级

## 下一步

参考以下文档继续了解：
- [数据库设计](../database/03_DATABASE_DESIGN.md) - 5张核心表设计（v2.0.0）
- [API接口规范](../api/04_API_SPECIFICATION.md) - RESTful API详细文档
- [用户需求文档](../requirements/USER_REQUIREMENTS.md) - 9条Phase 1需求（v2.0.0）
- [功能规格说明](../requirements/FUNCTIONAL_SPECIFICATION.md) - 技术实现详细规格（v2.0.0）
- [开发工作流](../workflow/05_DEVELOPMENT_WORKFLOW.md) - 8周开发计划
- [AI集成指南](../guides/AI_INTEGRATION_GUIDE.md) - Ollama部署和调优（待创建）

---

**文档版本**: v2.0.0
**维护团队**: 影像数据平台开发团队
**最后审核**: 2024-12-01
