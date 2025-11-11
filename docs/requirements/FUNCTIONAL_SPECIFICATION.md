# 功能规格说明书 (Functional Specification Document)

**项目名称**: 影像数据平台 - AI辅助报告筛选系统 (Phase 1)
**文档版本**: v2.0.0 (Phase 1)
**最后更新**: 2024-12-01
**文档状态**: 正式版

---

## 文档概述

### 目的
本文档详细描述Phase 1的功能规格，重点说明AI辅助报告分析和项目管理系统的技术实现。文档面向开发团队、测试团队和技术管理者。

### Phase 1 核心定位
本文档聚焦于 **AI驱动的报告筛选工具**，不包含DICOM影像处理功能（Phase 2）。

### 范围
- ✅ 数据导入（Excel/CSV）
- ✅ 报告搜索和浏览
- ✅ **Ollama本地LLM集成**
- ✅ **AI报告分析和标记**
- ✅ 项目管理系统
- ✅ 数据导出
- ❌ DICOM影像处理（Phase 2）
- ❌ 影像查看器（Phase 2）
- ❌ 复杂系统集成（Phase 2）

---

## 目录

1. [系统架构概述](#1-系统架构概述)
2. [功能模块详细规格](#2-功能模块详细规格)
3. [AI集成规格](#3-ai集成规格)
4. [数据流程和状态机](#4-数据流程和状态机)
5. [界面设计规范](#5-界面设计规范)
6. [错误处理](#6-错误处理)
7. [附录](#7-附录)

---

## 1. 系统架构概述

### 1.1 Phase 1 简化架构

```
┌─────────────────────────────────────────────────────────┐
│                  用户界面层 (React + TypeScript)           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │  数据导入   │  │  AI分析界面 │  │ 项目管理    │        │
│  └────────────┘  └────────────┘  └────────────┘        │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API (HTTPS)
┌───────────────────────▼─────────────────────────────────┐
│                 应用服务层 (FastAPI)                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │  Auth API   │  │  Report API │  │ Project API│        │
│  └────────────┘  └────────────┘  └────────────┘        │
│  ┌─────────────────────────────────────────────┐        │
│  │           AI Analysis Service                │        │
│  │  (Async task processing with background)    │        │
│  └─────────────────────────────────────────────┘        │
└───────────────────────┬─────────────────────────────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
         ▼                             ▼
┌─────────────────┐          ┌──────────────────┐
│   PostgreSQL    │          │     Ollama       │
│  (主数据库)      │          │ (本地LLM服务)     │
│                 │          │  qwen2.5:7b      │
└─────────────────┘          └──────────────────┘
```

### 1.2 技术栈详细说明

#### 前端技术栈
```json
{
  "framework": "React 18+",
  "language": "TypeScript 5+",
  "stateManagement": "Zustand 4.4+",
  "routing": "React Router 6+",
  "uiLibrary": "Ant Design 5+",
  "httpClient": "Axios 1.6+",
  "buildTool": "Vite 5+"
}
```

**Phase 1 移除**:
- ❌ Cornerstone.js (DICOM viewer)
- ❌ 复杂状态管理

#### 后端技术栈
```json
{
  "framework": "FastAPI 0.108+",
  "language": "Python 3.11+",
  "orm": "SQLAlchemy 2.0+",
  "migration": "Alembic 1.13+",
  "validation": "Pydantic 2.5+",
  "llm": "Ollama (qwen2.5:7b)",
  "async": "asyncio + httpx"
}
```

**Phase 1 移除**:
- ❌ Celery (task queue)
- ❌ Redis (caching)
- ❌ MinIO/S3 (object storage)
- ❌ pydicom (DICOM processing)

---

## 2. 功能模块详细规格

### 2.1 认证授权模块 (简化版)

#### 2.1.1 登录功能 (FS-AUTH-001)

**前端实现**:

```typescript
// src/services/authService.ts
import axios from 'axios';
import { LoginCredentials, LoginResponse, User } from '@/types/auth';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const authAPI = {
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await axios.post<LoginResponse>(
      `${API_BASE}/auth/login`,
      credentials
    );
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const token = localStorage.getItem('access_token');
    if (!token) throw new Error('No token found');

    const response = await axios.get<User>(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  }
};
```

```typescript
// src/components/auth/LoginForm.tsx
import React, { useState } from 'react';
import { Form, Input, Button, message } from 'antd';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '@/services/authService';
import { useAuthStore } from '@/stores/authStore';

export const LoginForm: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const setUser = useAuthStore((state) => state.setUser);

  const handleSubmit = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      const response = await authAPI.login(values);

      // 保存token
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));

      // 更新全局状态
      setUser(response.user);

      message.success('登录成功');
      navigate('/dashboard');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form onFinish={handleSubmit} layout="vertical">
      <Form.Item
        label="邮箱"
        name="email"
        rules={[
          { required: true, message: '请输入邮箱' },
          { type: 'email', message: '请输入有效的邮箱地址' }
        ]}
      >
        <Input placeholder="your.email@example.com" />
      </Form.Item>

      <Form.Item
        label="密码"
        name="password"
        rules={[{ required: true, message: '请输入密码' }]}
      >
        <Input.Password placeholder="密码" />
      </Form.Item>

      <Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} block>
          登录
        </Button>
      </Form.Item>
    </Form>
  );
};
```

**后端实现**:

```python
# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

@router.post("/auth/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """用户登录"""
    # 查找用户
    user = db.query(User).filter(
        User.email == credentials.email,
        User.is_active == True
    ).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.commit()

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.from_orm(user)
    )

@router.get("/auth/me", response_model=UserOut)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """获取当前用户信息"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return UserOut.from_orm(user)
```

---

### 2.2 数据导入模块

#### 2.2.1 Excel/CSV导入功能 (FS-IMPORT-001)

**前端实现**:

```typescript
// src/components/import/DataImportForm.tsx
import React, { useState } from 'react';
import { Upload, Button, Table, message, Steps } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { importAPI } from '@/services/importService';

const { Dragger } = Upload;
const { Step } = Steps;

interface FieldMapping {
  sourceField: string;
  targetField: string;
}

export const DataImportForm: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [fieldMapping, setFieldMapping] = useState<FieldMapping[]>([]);
  const [importing, setImporting] = useState(false);

  const handleFileSelect = async (file: File) => {
    setFile(file);

    // 预览文件内容
    try {
      const preview = await importAPI.previewFile(file);
      setPreviewData(preview.data);
      setFieldMapping(preview.suggestedMapping);
      setCurrentStep(1);
      return false; // 阻止自动上传
    } catch (error) {
      message.error('文件解析失败');
    }
  };

  const handleImport = async () => {
    if (!file) return;

    setImporting(true);
    try {
      const result = await importAPI.importData(file, fieldMapping);
      message.success(`成功导入 ${result.imported_count} 条记录`);
      setCurrentStep(2);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '导入失败');
    } finally {
      setImporting(false);
    }
  };

  return (
    <div>
      <Steps current={currentStep}>
        <Step title="上传文件" />
        <Step title="配置字段映射" />
        <Step title="完成导入" />
      </Steps>

      {currentStep === 0 && (
        <Dragger
          accept=".xlsx,.xls,.csv"
          beforeUpload={handleFileSelect}
          showUploadList={false}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持 Excel (.xlsx, .xls) 和 CSV (.csv) 格式
          </p>
        </Dragger>
      )}

      {currentStep === 1 && (
        <div>
          <h3>数据预览（前5条）</h3>
          <Table
            dataSource={previewData.slice(0, 5)}
            pagination={false}
            scroll={{ x: true }}
          />

          <h3>字段映射配置</h3>
          {/* 字段映射表单 */}

          <Button
            type="primary"
            onClick={handleImport}
            loading={importing}
            style={{ marginTop: 16 }}
          >
            开始导入
          </Button>
        </div>
      )}

      {currentStep === 2 && (
        <div>
          <h3>导入完成</h3>
          {/* 导入结果统计 */}
        </div>
      )}
    </div>
  );
};
```

**后端实现**:

```python
# app/api/v1/endpoints/import.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import pandas as pd
from io import BytesIO
from typing import List, Dict

from app.db.session import get_db
from app.models.report import Report
from app.schemas.import_schema import ImportPreview, ImportResult, FieldMapping

router = APIRouter()

@router.post("/import/preview", response_model=ImportPreview)
async def preview_import_file(
    file: UploadFile = File(...),
):
    """预览导入文件内容"""
    try:
        # 读取文件
        content = await file.read()

        # 根据文件类型解析
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(BytesIO(content))
        else:
            raise HTTPException(400, "不支持的文件格式")

        # 生成预览数据
        preview_data = df.head(10).to_dict('records')

        # 智能字段映射建议
        suggested_mapping = suggest_field_mapping(df.columns.tolist())

        return ImportPreview(
            total_rows=len(df),
            preview_data=preview_data,
            source_columns=df.columns.tolist(),
            suggested_mapping=suggested_mapping
        )

    except Exception as e:
        raise HTTPException(400, f"文件解析失败: {str(e)}")

@router.post("/import/execute", response_model=ImportResult)
async def execute_import(
    file: UploadFile = File(...),
    field_mapping: List[FieldMapping] = ...,
    db: Session = Depends(get_db)
):
    """执行数据导入"""
    try:
        # 读取和解析文件
        content = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(content))
        else:
            df = pd.read_excel(BytesIO(content))

        # 应用字段映射
        mapping_dict = {m.source_field: m.target_field for m in field_mapping}
        df = df.rename(columns=mapping_dict)

        # 数据验证
        validate_import_data(df)

        # 批量插入数据库
        imported_count = 0
        skipped_count = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                # 检查重复数据
                existing = db.query(Report).filter(
                    Report.patient_id == row.get('patient_id'),
                    Report.exam_date == pd.to_datetime(row.get('exam_date'))
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                # 创建记录
                report = Report(
                    patient_id=row.get('patient_id'),
                    patient_name=row.get('patient_name'),
                    exam_date=pd.to_datetime(row.get('exam_date')),
                    exam_type=row.get('exam_type'),
                    report_content=row.get('report_content'),
                    department=row.get('department')
                )
                db.add(report)
                imported_count += 1

                # 每100条提交一次
                if imported_count % 100 == 0:
                    db.commit()

            except Exception as e:
                errors.append(f"第{idx+1}行: {str(e)}")

        db.commit()

        return ImportResult(
            imported_count=imported_count,
            skipped_count=skipped_count,
            error_count=len(errors),
            errors=errors[:10]  # 只返回前10个错误
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"导入失败: {str(e)}")

def suggest_field_mapping(source_columns: List[str]) -> List[FieldMapping]:
    """智能字段映射建议"""
    mapping_rules = {
        'patient_id': ['患者ID', '病历号', 'patient_id', 'ID'],
        'patient_name': ['患者姓名', '姓名', 'patient_name', 'name'],
        'exam_date': ['检查日期', '日期', 'exam_date', 'date'],
        'exam_type': ['检查类型', '类型', 'exam_type', 'modality'],
        'report_content': ['报告内容', '报告', 'report', 'content'],
        'department': ['科室', 'department', '病区']
    }

    suggested = []
    for target_field, patterns in mapping_rules.items():
        for col in source_columns:
            if any(pattern in col for pattern in patterns):
                suggested.append(FieldMapping(
                    source_field=col,
                    target_field=target_field
                ))
                break

    return suggested
```

---

## 3. AI集成规格

### 3.1 Ollama集成架构

#### 3.1.1 AI Service Layer (FS-AI-001)

**核心AI服务实现**:

```python
# app/services/ai_service.py
import httpx
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel

class AIAnalysisRequest(BaseModel):
    report_text: str
    user_prompt: str
    annotation_type: str  # 'highlight', 'classification', 'extraction', 'scoring'

class AIAnalysisResponse(BaseModel):
    annotation_type: str
    content: Dict[str, Any]
    confidence: Optional[float] = None
    raw_response: str

class OllamaClient:
    """Ollama本地LLM客户端"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen2.5:7b"

    async def chat(
        self,
        messages: list,
        format: str = "json",
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """与Ollama LLM对话"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "format": format,
                    "temperature": temperature,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()

    async def analyze_report(
        self,
        request: AIAnalysisRequest
    ) -> AIAnalysisResponse:
        """分析医学报告"""

        # 构建系统提示
        system_prompt = self._build_system_prompt(request.annotation_type)

        # 构建用户提示
        user_message = f"""
用户需求: {request.user_prompt}

报告内容:
{request.report_text}

请按照以下JSON格式返回分析结果:
{self._get_output_schema(request.annotation_type)}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        # 调用LLM
        response = await self.chat(messages, format="json")

        # 解析响应
        try:
            content = json.loads(response["message"]["content"])
        except json.JSONDecodeError:
            # 如果LLM返回的不是有效JSON，尝试修复
            content = {"raw_text": response["message"]["content"]}

        return AIAnalysisResponse(
            annotation_type=request.annotation_type,
            content=content,
            raw_response=response["message"]["content"]
        )

    def _build_system_prompt(self, annotation_type: str) -> str:
        """构建系统提示"""
        base_prompt = """你是一个专业的医学影像报告分析助手。
你的任务是帮助研究人员快速筛选和标记医学检查报告。

分析要求:
1. 仔细阅读报告内容
2. 准确理解用户的筛选需求
3. 返回结构化的JSON格式结果
4. 保持客观和专业性
"""

        type_specific = {
            'highlight': """
请标记报告中的关键信息，返回格式:
{
  "highlights": [
    {"text": "关键短语", "start": 起始位置, "end": 结束位置, "reason": "标记原因"}
  ]
}
""",
            'classification': """
请对报告进行分类，返回格式:
{
  "category": "类别名称",
  "confidence": 0.0-1.0,
  "reasoning": "分类依据"
}
""",
            'extraction': """
请提取报告中的结构化信息，返回格式:
{
  "findings": ["发现1", "发现2"],
  "measurements": [{"item": "项目", "value": "数值", "unit": "单位"}],
  "locations": ["位置1", "位置2"]
}
""",
            'scoring': """
请对报告进行评分，返回格式:
{
  "score": 1-10,
  "severity": "normal/mild/moderate/severe",
  "reasoning": "评分依据"
}
"""
        }

        return base_prompt + type_specific.get(annotation_type, "")

    def _get_output_schema(self, annotation_type: str) -> str:
        """获取输出schema示例"""
        schemas = {
            'highlight': '{"highlights": [{"text": "...", "start": 0, "end": 10}]}',
            'classification': '{"category": "...", "confidence": 0.9}',
            'extraction': '{"findings": [...], "measurements": [...]}',
            'scoring': '{"score": 8, "severity": "moderate"}'
        }
        return schemas.get(annotation_type, '{}')

# 全局实例
ollama_client = OllamaClient()
```

#### 3.1.2 AI Analysis API (FS-AI-002)

```python
# app/api/v1/endpoints/ai.py
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List
import asyncio

from app.db.session import get_db
from app.models.report import Report
from app.models.ai_annotation import AIAnnotation
from app.services.ai_service import ollama_client, AIAnalysisRequest
from app.schemas.ai import (
    AnalysisRequest,
    AnalysisResponse,
    BatchAnalysisRequest,
    BatchAnalysisStatus,
    AnnotationOut
)

router = APIRouter()

@router.post("/ai/analyze", response_model=AnalysisResponse)
async def analyze_single_report(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """单个报告AI分析"""

    # 获取报告
    report = db.query(Report).filter(Report.id == request.report_id).first()
    if not report:
        raise HTTPException(404, "报告不存在")

    # 调用AI分析
    try:
        ai_request = AIAnalysisRequest(
            report_text=report.content,
            user_prompt=request.user_prompt,
            annotation_type=request.annotation_type
        )

        ai_response = await ollama_client.analyze_report(ai_request)

        # 保存标记
        annotation = AIAnnotation(
            report_id=report.id,
            user_prompt=request.user_prompt,
            annotation_type=request.annotation_type,
            content=ai_response.content,
            confidence=ai_response.confidence,
            raw_response=ai_response.raw_response
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)

        return AnalysisResponse(
            annotation_id=annotation.id,
            annotation_type=annotation.annotation_type,
            content=annotation.content,
            confidence=annotation.confidence
        )

    except Exception as e:
        raise HTTPException(500, f"AI分析失败: {str(e)}")

@router.post("/ai/batch-analyze", response_model=BatchAnalysisStatus)
async def batch_analyze_reports(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """批量报告AI分析"""

    # 验证报告数量
    if len(request.report_ids) > 50:
        raise HTTPException(400, "单次批量分析最多50个报告")

    # 创建后台任务
    task_id = f"batch_{request.report_ids[0]}_{len(request.report_ids)}"

    background_tasks.add_task(
        process_batch_analysis,
        task_id=task_id,
        report_ids=request.report_ids,
        user_prompt=request.user_prompt,
        annotation_type=request.annotation_type,
        db=db
    )

    return BatchAnalysisStatus(
        task_id=task_id,
        status="processing",
        total=len(request.report_ids),
        completed=0,
        failed=0
    )

async def process_batch_analysis(
    task_id: str,
    report_ids: List[int],
    user_prompt: str,
    annotation_type: str,
    db: Session
):
    """处理批量分析（后台任务）"""

    # 并发处理（最多3个同时）
    semaphore = asyncio.Semaphore(3)

    async def analyze_one(report_id: int):
        async with semaphore:
            try:
                report = db.query(Report).filter(Report.id == report_id).first()
                if not report:
                    return None

                ai_request = AIAnalysisRequest(
                    report_text=report.content,
                    user_prompt=user_prompt,
                    annotation_type=annotation_type
                )

                ai_response = await ollama_client.analyze_report(ai_request)

                annotation = AIAnnotation(
                    report_id=report.id,
                    user_prompt=user_prompt,
                    annotation_type=annotation_type,
                    content=ai_response.content,
                    confidence=ai_response.confidence
                )
                db.add(annotation)
                db.commit()

                return annotation.id

            except Exception as e:
                print(f"Report {report_id} analysis failed: {e}")
                return None

    # 并发执行
    tasks = [analyze_one(rid) for rid in report_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 统计结果
    completed = sum(1 for r in results if r is not None)
    failed = len(results) - completed

    print(f"Batch analysis completed: {completed}/{len(report_ids)}")

@router.get("/ai/annotations/{report_id}", response_model=List[AnnotationOut])
async def get_report_annotations(
    report_id: int,
    db: Session = Depends(get_db)
):
    """获取报告的所有AI标记"""
    annotations = db.query(AIAnnotation).filter(
        AIAnnotation.report_id == report_id
    ).order_by(AIAnnotation.created_at.desc()).all()

    return [AnnotationOut.from_orm(a) for a in annotations]

@router.put("/ai/annotations/{annotation_id}", response_model=AnnotationOut)
async def update_annotation(
    annotation_id: int,
    content: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """更新AI标记内容"""
    annotation = db.query(AIAnnotation).filter(
        AIAnnotation.id == annotation_id
    ).first()

    if not annotation:
        raise HTTPException(404, "标记不存在")

    annotation.content = content
    annotation.is_edited = True
    db.commit()
    db.refresh(annotation)

    return AnnotationOut.from_orm(annotation)

@router.delete("/ai/annotations/{annotation_id}")
async def delete_annotation(
    annotation_id: int,
    db: Session = Depends(get_db)
):
    """删除AI标记"""
    annotation = db.query(AIAnnotation).filter(
        AIAnnotation.id == annotation_id
    ).first()

    if not annotation:
        raise HTTPException(404, "标记不存在")

    db.delete(annotation)
    db.commit()

    return {"message": "标记已删除"}
```

---

### 3.2 报告搜索模块

#### 3.2.1 高级搜索API (FS-SEARCH-001)

```python
# app/api/v1/endpoints/reports.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from datetime import date

from app.db.session import get_db
from app.models.report import Report
from app.models.ai_annotation import AIAnnotation
from app.schemas.report import ReportOut, ReportSearchParams, SearchResult

router = APIRouter()

@router.get("/reports/search", response_model=SearchResult)
async def search_reports(
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    exam_type: Optional[str] = Query(None, description="检查类型"),
    date_from: Optional[date] = Query(None, description="开始日期"),
    date_to: Optional[date] = Query(None, description="结束日期"),
    department: Optional[str] = Query(None, description="科室"),
    has_annotation: Optional[bool] = Query(None, description="是否有AI标记"),
    annotation_type: Optional[str] = Query(None, description="标记类型"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """高级报告搜索"""

    # 构建查询
    query = db.query(Report).filter(Report.is_deleted == False)

    # 关键词搜索（全文搜索）
    if keyword:
        query = query.filter(
            or_(
                Report.patient_id.contains(keyword),
                Report.patient_name.contains(keyword),
                Report.content.contains(keyword)
            )
        )

    # 检查类型筛选
    if exam_type:
        query = query.filter(Report.exam_type == exam_type)

    # 日期范围筛选
    if date_from:
        query = query.filter(Report.exam_date >= date_from)
    if date_to:
        query = query.filter(Report.exam_date <= date_to)

    # 科室筛选
    if department:
        query = query.filter(Report.department == department)

    # AI标记筛选
    if has_annotation is not None:
        if has_annotation:
            query = query.join(AIAnnotation)
        else:
            query = query.outerjoin(AIAnnotation).filter(AIAnnotation.id == None)

    if annotation_type:
        query = query.join(AIAnnotation).filter(
            AIAnnotation.annotation_type == annotation_type
        )

    # 总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    reports = query.offset(offset).limit(page_size).all()

    return SearchResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[ReportOut.from_orm(r) for r in reports]
    )

@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report_detail(
    report_id: int,
    db: Session = Depends(get_db)
):
    """获取报告详情"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "报告不存在")

    return ReportOut.from_orm(report)
```

---

### 3.3 项目管理模块

#### 3.3.1 项目CRUD (FS-PROJECT-001)

```python
# app/api/v1/endpoints/projects.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.project import Project, ProjectReport
from app.models.report import Report
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectOut,
    ProjectDetailOut
)

router = APIRouter()

@router.post("/projects", response_model=ProjectOut)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db)
):
    """创建项目"""
    db_project = Project(
        name=project.name,
        description=project.description,
        tags=project.tags
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return ProjectOut.from_orm(db_project)

@router.get("/projects", response_model=List[ProjectOut])
async def list_projects(
    db: Session = Depends(get_db)
):
    """获取项目列表"""
    projects = db.query(Project).filter(
        Project.is_deleted == False
    ).order_by(Project.created_at.desc()).all()

    return [ProjectOut.from_orm(p) for p in projects]

@router.get("/projects/{project_id}", response_model=ProjectDetailOut)
async def get_project_detail(
    project_id: int,
    db: Session = Depends(get_db)
):
    """获取项目详情"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "项目不存在")

    # 获取项目中的报告
    reports = db.query(Report).join(ProjectReport).filter(
        ProjectReport.project_id == project_id
    ).all()

    return ProjectDetailOut(
        **ProjectOut.from_orm(project).dict(),
        reports=[ReportOut.from_orm(r) for r in reports],
        report_count=len(reports)
    )

@router.post("/projects/{project_id}/reports")
async def add_reports_to_project(
    project_id: int,
    report_ids: List[int],
    db: Session = Depends(get_db)
):
    """添加报告到项目"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "项目不存在")

    added_count = 0
    for report_id in report_ids:
        # 检查是否已存在
        existing = db.query(ProjectReport).filter(
            ProjectReport.project_id == project_id,
            ProjectReport.report_id == report_id
        ).first()

        if not existing:
            db.add(ProjectReport(
                project_id=project_id,
                report_id=report_id
            ))
            added_count += 1

    db.commit()

    return {"message": f"成功添加 {added_count} 个报告"}

@router.get("/projects/{project_id}/export")
async def export_project(
    project_id: int,
    format: str = Query("xlsx", enum=["xlsx", "csv", "json"]),
    db: Session = Depends(get_db)
):
    """导出项目数据"""
    # 实现导出逻辑
    # 返回文件或下载链接
    pass
```

---

## 4. 数据流程和状态机

### 4.1 AI分析工作流

```
[用户选择报告] → [输入提示词] → [选择标记类型] → [发起AI分析]
                                                        ↓
                                              [调用Ollama LLM]
                                                        ↓
                                              [返回JSON结果]
                                                        ↓
                                              [解析并保存标记]
                                                        ↓
                                        [在UI中高亮显示/以卡片展示]
                                                        ↓
                              [用户可编辑/删除] ← [标记保存成功]
```

### 4.2 批量分析状态机

```
状态转换:
pending → processing → completed
                    → failed (with error message)
                    → partial (部分成功)
```

---

## 5. 界面设计规范

### 5.1 报告详情页布局

```
┌─────────────────────────────────────────────────────────┐
│  报告详情                                        [AI分析]  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  患者: 张三  ID: 12345          检查日期: 2024-11-15      │
│  检查类型: CT胸部              科室: 放射科                │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  报告内容:                                                │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 检查所见:                                           │ │
│  │ 双肺纹理增多,未见明显实质性病变...                    │ │
│  │                                                     │ │
│  │ [高亮文本示例: 双肺纹理增多]  ← AI标记               │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  AI分析结果 (2条标记)                                     │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 📍 高亮标记                          [编辑] [删除]  │ │
│  │ 提示词: 标记关键发现                                 │ │
│  │ 结果: "双肺纹理增多" (位置: 12-18)                   │ │
│  │ 时间: 2024-12-01 10:30                             │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ 🏷️ 分类标记                          [编辑] [删除]  │ │
│  │ 提示词: 判断报告严重程度                             │ │
│  │ 结果: 正常 (置信度: 0.92)                           │ │
│  │ 依据: 未见实质性病变，仅纹理增多...                  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 5.2 键盘快捷键

```
Ctrl + K: 快速搜索
Ctrl + N: 新建项目
Ctrl + A: AI分析当前报告
↑/↓: 浏览报告列表
Enter: 查看报告详情
Esc: 关闭弹窗
```

---

## 6. 错误处理

### 6.1 Ollama连接错误

```python
try:
    response = await ollama_client.chat(messages)
except httpx.ConnectError:
    raise HTTPException(
        503,
        "无法连接到Ollama服务，请确保Ollama已启动"
    )
except httpx.TimeoutException:
    raise HTTPException(
        504,
        "AI分析超时，请稍后重试"
    )
```

### 6.2 前端错误提示

```typescript
// 友好的错误提示
const ERROR_MESSAGES = {
  503: '❌ AI服务暂时不可用，请稍后再试',
  504: '⏱️ 分析超时，建议减少报告长度或降低并发数',
  400: '⚠️ 请求参数错误，请检查输入',
  401: '🔐 登录已过期，请重新登录',
  500: '💥 服务器内部错误，请联系管理员'
};
```

---

## 7. 附录

### 7.1 Ollama提示词模板库

```python
PROMPT_TEMPLATES = {
    "key_findings": "请提取报告中的关键发现和诊断结论，以结构化方式列出。",

    "lesion_info": "请标记报告中提到的所有病灶信息，包括位置、大小、性质。",

    "severity_classification": """
请根据报告内容判断严重程度，分为以下类别:
- normal: 正常
- mild: 轻度异常
- moderate: 中度异常
- severe: 重度异常
请说明分类依据。
""",

    "measurements": "请提取报告中的所有测量数值和单位。",

    "malignancy_check": "请判断报告中是否包含恶性肿瘤相关的描述或诊断。",

    "icd_suggestion": "请根据报告内容推荐合适的ICD疾病编码。"
}
```

### 7.2 Phase 1 vs Phase 2 对比

| 功能 | Phase 1 | Phase 2 |
|------|---------|---------|
| 数据导入 | ✅ Excel/CSV | ✅ + DICOM |
| 报告分析 | ✅ AI标记 | ✅ + 复杂报告工作流 |
| 项目管理 | ✅ 基础CRUD | ✅ + 高级协作 |
| 影像处理 | ❌ 无 | ✅ 上传/查看/下载 |
| 存储 | PostgreSQL | PostgreSQL + MinIO |
| 任务队列 | 简单async | Celery分布式 |
| 集成 | 无 | Accssyn + Red Report |

---

**变更历史**:

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.0.0 | 2024-12-01 | Phase 1重写：聚焦AI分析和项目管理 |
| v1.0.0 | 2024-12-01 | 初始版本（完整平台） |

---

**文档审批**:

| 角色 | 姓名 | 日期 |
|------|------|------|
| 技术负责人 | | |
| 开发团队负责人 | | |
| QA负责人 | | |
