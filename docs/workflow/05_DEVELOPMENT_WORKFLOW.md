# 开发工作流和里程碑 - Phase 1

## 项目开发路线图

### Phase 1总览时间线（8周）

```
Week 1-2: 基础架构和数据导入 ████████░░░░░░░░░░░░░░
Week 3-4: 报告检索和AI集成    ░░░░░░░░████████░░░░░░
Week 5-6: AI分析和项目管理    ░░░░░░░░░░░░░░░░████░░
Week 7:   测试和优化           ░░░░░░░░░░░░░░░░░░░███
Week 8:   部署和培训           ░░░░░░░░░░░░░░░░░░░░██
```

**Phase 1目标**：构建AI驱动的报告筛选和管理系统，专注于报告数据的导入、检索、AI辅助分析和项目管理功能。

**Phase 2规划**（未来扩展）：添加DICOM影像支持、Accssyn自动同步、高级分析功能

---

## Week 1-2: 基础架构和数据导入

### Week 1: 项目初始化与开发环境

#### 目标
- 搭建完整的Phase 1开发环境
- 建立项目代码结构
- 配置基础服务（PostgreSQL + Ollama）

#### 任务清单

**Day 1-2: 环境准备**
- [ ] **Docker环境配置**
  - 安装Docker和Docker Compose
  - 配置PostgreSQL 14
  - 安装Ollama服务
  - 创建项目Git仓库
  - 配置.gitignore和项目规范

- [ ] **后端框架初始化**
  - 使用FastAPI创建项目
  - 配置项目结构（app/, tests/, alembic/）
  - 设置环境变量管理（.env）
  - 配置日志系统

**Day 3-4: 前端框架和数据库**
- [ ] **前端项目搭建**
  - 使用Vite创建React项目
  - 配置TypeScript和ESLint
  - 安装Ant Design和基础依赖
  - 配置Zustand状态管理
  - 设置路由结构（react-router-dom v6）

- [ ] **数据库设计实施**
  - 创建5张核心表（users, reports, ai_annotations, projects, project_reports）
  - 设置外键关系和索引
  - 配置全文搜索索引（GIN）
  - 配置JSONB索引

**Day 5: Ollama模型配置**
- [ ] **Ollama部署**
  - Docker Compose配置Ollama服务
  - 下载qwen2.5:7b模型（4.4GB）
  - 测试Ollama API连接
  - 验证JSON格式输出

**交付物**

```
image_data_platform/
├── backend/
│   ├── app/
│   │   ├── api/              # API端点
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── reports.py
│   │   │   ├── ai_analysis.py
│   │   │   ├── projects.py
│   │   │   └── health.py
│   │   ├── core/             # 核心配置
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/           # 数据模型
│   │   │   ├── user.py
│   │   │   ├── report.py
│   │   │   ├── ai_annotation.py
│   │   │   └── project.py
│   │   ├── schemas/          # Pydantic模式
│   │   │   ├── user.py
│   │   │   ├── report.py
│   │   │   └── ai_annotation.py
│   │   ├── services/         # 业务逻辑
│   │   │   ├── ollama_client.py
│   │   │   ├── import_service.py
│   │   │   └── export_service.py
│   │   └── main.py           # 应用入口
│   ├── tests/
│   │   ├── test_ollama_client.py
│   │   ├── test_auth_api.py
│   │   └── test_reports_api.py
│   ├── alembic/              # 数据库迁移
│   │   ├── versions/
│   │   │   └── 001_create_initial_tables.py
│   │   └── env.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/       # 可复用组件
│   │   │   ├── Layout/
│   │   │   ├── ReportTable/
│   │   │   └── SearchFilters/
│   │   ├── pages/            # 页面组件
│   │   │   ├── Login/
│   │   │   ├── Dashboard/
│   │   │   ├── Reports/
│   │   │   └── Projects/
│   │   ├── services/         # API服务
│   │   │   ├── api.ts
│   │   │   ├── auth.ts
│   │   │   └── reports.ts
│   │   ├── store/            # Zustand状态
│   │   │   ├── authStore.ts
│   │   │   └── appStore.ts
│   │   ├── types/            # TypeScript类型
│   │   │   ├── report.ts
│   │   │   └── project.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml         # 4服务编排
├── .env.example
└── README.md
```

**代码示例**

**数据库迁移脚本** (`backend/alembic/versions/001_create_initial_tables.py`):

```python
"""create initial tables

Revision ID: 001
Create Date: 2024-12-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 创建用户表
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='researcher'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # 创建报告表
    op.create_table(
        'reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('patient_id', sa.String(50), nullable=False),
        sa.Column('patient_name', sa.String(100), nullable=False),
        sa.Column('gender', sa.String(10)),
        sa.Column('age', sa.Integer),
        sa.Column('exam_date', sa.Date, nullable=False),
        sa.Column('exam_type', sa.String(50), nullable=False),
        sa.Column('body_part', sa.String(100)),
        sa.Column('department', sa.String(100)),
        sa.Column('report_content', sa.Text, nullable=False),
        sa.Column('diagnosis', sa.Text),
        sa.Column('source_file', sa.String(255)),
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
    )

    # 创建AI标注表
    op.create_table(
        'ai_annotations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('report_id', UUID(as_uuid=True), sa.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('annotation_type', sa.String(50), nullable=False),
        sa.Column('content', JSONB, nullable=False),
        sa.Column('user_prompt', sa.Text, nullable=False),
        sa.Column('confidence', sa.Float),
        sa.Column('model_name', sa.String(50)),
        sa.Column('model_temperature', sa.Float),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
    )

    # 创建项目表
    op.create_table(
        'projects',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
    )

    # 创建项目-报告关联表
    op.create_table(
        'project_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('report_id', UUID(as_uuid=True), sa.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('added_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
        sa.UniqueConstraint('project_id', 'report_id', name='uq_project_report')
    )

    # 创建索引
    op.create_index('idx_reports_patient_id', 'reports', ['patient_id'])
    op.create_index('idx_reports_exam_date', 'reports', ['exam_date'])
    op.create_index('idx_reports_exam_type', 'reports', ['exam_type'])
    op.create_index('idx_reports_created_at', 'reports', ['created_at'])

    # 全文搜索索引
    op.execute("""
        CREATE INDEX idx_reports_content_fulltext
        ON reports USING gin(to_tsvector('simple', report_content || ' ' || COALESCE(diagnosis, '')))
        WHERE is_deleted = false
    """)

    # JSONB索引
    op.create_index('idx_ai_annotations_content_gin', 'ai_annotations', ['content'], postgresql_using='gin')

    op.create_index('idx_ai_annotations_report_id', 'ai_annotations', ['report_id'])
    op.create_index('idx_project_reports_project_id', 'project_reports', ['project_id'])
    op.create_index('idx_project_reports_report_id', 'project_reports', ['report_id'])


def downgrade():
    op.drop_table('project_reports')
    op.drop_table('projects')
    op.drop_table('ai_annotations')
    op.drop_table('reports')
    op.drop_table('users')
```

**Docker Compose配置** (`docker-compose.yml`):

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    container_name: postgres
    environment:
      POSTGRES_DB: imagedb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
      - OLLAMA_NUM_PARALLEL=4
      - OLLAMA_MAX_LOADED_MODELS=2
      - OLLAMA_KEEP_ALIVE=24h
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - backend
    # 取消注释以启用GPU加速
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: backend
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/imagedb
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=qwen2.5:7b
      - OLLAMA_TIMEOUT=60.0
      - OLLAMA_MAX_CONCURRENT=3
      - SECRET_KEY=change-this-secret-key-in-production
      - ACCESS_TOKEN_EXPIRE_MINUTES=30
    depends_on:
      postgres:
        condition: service_healthy
      ollama:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped
    networks:
      - backend
      - frontend

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: frontend
    environment:
      - VITE_API_URL=http://localhost:8000
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host 0.0.0.0
    restart: unless-stopped
    networks:
      - frontend

volumes:
  postgres_data:
    driver: local
  ollama_data:
    driver: local

networks:
  backend:
    driver: bridge
  frontend:
    driver: bridge
```

**Week 1 里程碑检查点**
- [ ] Docker环境完整运行（4个服务：PostgreSQL, Ollama, Backend, Frontend）
- [ ] 数据库表结构创建完成（5张核心表）
- [ ] Ollama模型下载完成（qwen2.5:7b）
- [ ] 前后端项目框架搭建完成
- [ ] 健康检查端点正常响应

---

### Week 2: 认证授权和数据导入

#### 目标
- 实现JWT认证授权系统
- 开发报告数据导入功能
- 完成基础前端页面

#### 任务清单

**Day 1-2: JWT认证系统**
- [ ] **后端认证API**
  - 实现JWT令牌生成和验证
  - 创建登录/登出端点
  - 实现密码哈希（bcrypt）
  - 基于角色的权限检查（admin/researcher）
  - 创建初始管理员账号脚本

- [ ] **前端认证**
  - 实现登录页面
  - 配置axios拦截器（自动添加token）
  - 实现路由守卫（Protected Routes）
  - Token过期自动刷新

**代码示例 - 认证系统**

**后端JWT实现** (`backend/app/core/security.py`):

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")

    return encoded_jwt


def verify_token(token: str) -> dict:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """获取当前登录用户"""
    payload = verify_token(token)
    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    return user


def require_role(required_role: str):
    """权限检查装饰器"""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return role_checker
```

**前端Axios配置** (`frontend/src/services/api.ts`):

```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理401错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

**Day 3-4: 报告导入功能**
- [ ] **后端导入API**
  - Excel/CSV文件解析（pandas）
  - 字段验证和清洗
  - 批量导入逻辑（事务处理）
  - 导入预览功能
  - 重复检测（patient_id + exam_date）

- [ ] **前端导入页面**
  - 文件上传组件（拖拽上传）
  - 字段映射配置界面
  - 数据预览表格
  - 导入进度显示
  - 导入结果报告

**代码示例 - 报告导入**

**后端导入服务** (`backend/app/services/import_service.py`):

```python
import pandas as pd
from typing import Dict, List, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.report import Report


class ReportImporter:
    """报告导入服务"""

    def __init__(self, file_path: str, mapping: Dict[str, str]):
        """
        Args:
            file_path: 文件路径
            mapping: 字段映射字典 {excel_column: db_field}
        """
        self.file_path = file_path
        self.mapping = mapping

    def parse_file(self) -> pd.DataFrame:
        """解析Excel/CSV文件"""
        if self.file_path.endswith('.csv'):
            df = pd.read_csv(self.file_path, encoding='utf-8-sig')
        elif self.file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(self.file_path)
        else:
            raise ValueError("Unsupported file format. Only CSV and Excel are supported.")

        return df

    def validate_data(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """验证数据完整性和格式

        Returns:
            错误列表
        """
        errors = []

        required_fields = ['patient_id', 'patient_name', 'exam_date', 'exam_type', 'report_content']

        for idx, row in df.iterrows():
            row_errors = []

            # 检查必填字段
            for field in required_fields:
                excel_col = self.mapping.get(field)
                if not excel_col or pd.isna(row.get(excel_col)):
                    row_errors.append(f"Missing required field: {field}")

            # 验证日期格式
            exam_date_col = self.mapping.get('exam_date')
            if exam_date_col and not pd.isna(row.get(exam_date_col)):
                try:
                    pd.to_datetime(row[exam_date_col])
                except:
                    row_errors.append(f"Invalid exam_date format")

            # 验证年龄范围
            age_col = self.mapping.get('age')
            if age_col and not pd.isna(row.get(age_col)):
                age = row[age_col]
                if not (0 <= age <= 150):
                    row_errors.append(f"Invalid age: {age}")

            if row_errors:
                errors.append({
                    "row": idx + 2,  # Excel行号（从1开始，标题行+1）
                    "errors": row_errors
                })

        return errors

    def check_duplicates(self, df: pd.DataFrame, db: Session) -> List[Dict[str, Any]]:
        """检查重复记录

        Returns:
            重复记录列表
        """
        duplicates = []

        patient_id_col = self.mapping.get('patient_id')
        exam_date_col = self.mapping.get('exam_date')

        for idx, row in df.iterrows():
            patient_id = row.get(patient_id_col)
            exam_date = pd.to_datetime(row.get(exam_date_col))

            existing = db.query(Report).filter(
                Report.patient_id == patient_id,
                Report.exam_date == exam_date.date(),
                Report.is_deleted == False
            ).first()

            if existing:
                duplicates.append({
                    "row": idx + 2,
                    "patient_id": patient_id,
                    "exam_date": exam_date.strftime('%Y-%m-%d'),
                    "existing_report_id": str(existing.id)
                })

        return duplicates

    def import_data(self, df: pd.DataFrame, db: Session, user_id: str, skip_duplicates: bool = True) -> Dict[str, Any]:
        """导入数据到数据库

        Returns:
            导入结果统计
        """
        results = {
            "total": len(df),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        for idx, row in df.iterrows():
            try:
                # 映射字段
                report_data = {}
                for db_field, excel_col in self.mapping.items():
                    value = row.get(excel_col)
                    if pd.notna(value):
                        # 特殊处理日期字段
                        if db_field == 'exam_date':
                            report_data[db_field] = pd.to_datetime(value).date()
                        else:
                            report_data[db_field] = value

                # 检查重复
                if skip_duplicates:
                    existing = db.query(Report).filter(
                        Report.patient_id == report_data['patient_id'],
                        Report.exam_date == report_data['exam_date'],
                        Report.is_deleted == False
                    ).first()

                    if existing:
                        results["skipped"] += 1
                        continue

                # 创建报告记录
                report = Report(
                    **report_data,
                    created_by=user_id
                )

                db.add(report)
                db.flush()  # 获取ID但不提交

                results["success"] += 1

                # 每100条提交一次
                if results["success"] % 100 == 0:
                    db.commit()

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "row": idx + 2,
                    "error": str(e)
                })

        # 最终提交
        db.commit()

        return results
```

**Day 5: 基础前端页面**
- [ ] **Dashboard页面**
  - 报告统计卡片
  - 最近导入记录
  - 快速操作入口

- [ ] **报告列表页面**
  - 基础表格展示
  - 简单搜索框
  - 分页组件

**前端Dashboard示例** (`frontend/src/pages/Dashboard/Dashboard.tsx`):

```typescript
import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import { FileTextOutlined, ProjectOutlined, RobotOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { getStatistics } from '@/services/dashboard';

export const Dashboard: React.FC = () => {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getStatistics,
  });

  return (
    <div className="dashboard">
      <h1>数据概览</h1>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="总报告数"
              value={stats?.total_reports || 0}
              prefix={<FileTextOutlined />}
              loading={isLoading}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="项目数"
              value={stats?.total_projects || 0}
              prefix={<ProjectOutlined />}
              loading={isLoading}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="AI分析数"
              value={stats?.total_annotations || 0}
              prefix={<RobotOutlined />}
              loading={isLoading}
            />
          </Card>
        </Col>
      </Row>

      {/* 最近导入记录、快速操作等其他组件 */}
    </div>
  );
};
```

**Week 2 里程碑检查点**
- [ ] 用户可以登录/登出
- [ ] JWT token自动刷新机制正常
- [ ] Excel/CSV文件可以上传和预览
- [ ] 报告数据可以批量导入
- [ ] Dashboard显示基础统计信息
- [ ] 报告列表页面可以查看导入的数据

---

## Week 3-4: 报告检索和AI集成

### Week 3: 报告搜索和筛选

#### 目标
- 实现强大的报告搜索功能
- 开发多维度筛选系统
- 优化查询性能

#### 任务清单

**Day 1-2: 全文搜索API**
- [ ] **后端搜索实现**
  - PostgreSQL全文搜索（to_tsvector）
  - 中文分词支持
  - 多字段搜索（report_content + diagnosis）
  - 搜索结果高亮
  - 搜索性能优化（GIN索引）

**代码示例 - 全文搜索**

```python
# backend/app/api/reports.py
from sqlalchemy import or_, func, text

@router.get("/reports", response_model=PaginatedResponse[ReportOut])
async def search_reports(
    q: Optional[str] = None,
    patient_id: Optional[str] = None,
    exam_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    department: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "exam_date",
    order: str = "desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """搜索报告

    支持全文搜索、多维度筛选、排序和分页
    """
    query = db.query(Report).filter(Report.is_deleted == False)

    # 全文搜索
    if q:
        search_vector = func.to_tsvector('simple',
            Report.report_content + ' ' + func.coalesce(Report.diagnosis, '')
        )
        search_query = func.to_tsquery('simple', q)

        query = query.filter(search_vector.match(search_query))

    # 精确筛选
    if patient_id:
        query = query.filter(Report.patient_id == patient_id)

    if exam_type:
        query = query.filter(Report.exam_type == exam_type)

    if date_from:
        query = query.filter(Report.exam_date >= date_from)

    if date_to:
        query = query.filter(Report.exam_date <= date_to)

    if department:
        query = query.filter(Report.department == department)

    # 排序
    if order == "asc":
        query = query.order_by(getattr(Report, sort).asc())
    else:
        query = query.order_by(getattr(Report, sort).desc())

    # 分页
    total = query.count()
    offset = (page - 1) * page_size
    reports = query.offset(offset).limit(page_size).all()

    # 搜索结果高亮（简化版）
    if q:
        for report in reports:
            report.report_content = highlight_text(report.report_content, q)

    return PaginatedResponse(
        items=reports,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )
```

**Day 3-4: 前端搜索界面**
- [ ] **高级搜索组件**
  - 搜索输入框（实时搜索）
  - 筛选器面板（日期范围、检查类型、部门）
  - 搜索历史
  - 保存搜索条件

- [ ] **搜索结果展示**
  - 表格展示（支持排序）
  - 高亮显示搜索关键词
  - 快速操作按钮（查看详情、添加到项目、AI分析）

**前端搜索组件示例** (`frontend/src/pages/Reports/ReportSearch.tsx`):

```typescript
import React, { useState } from 'react';
import { Input, Select, DatePicker, Button, Table, Space } from 'antd';
import { SearchOutlined, FilterOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { searchReports } from '@/services/reports';
import type { Report, ReportSearchParams } from '@/types/report';

const { RangePicker } = DatePicker;
const { Option } = Select;

export const ReportSearch: React.FC = () => {
  const [searchParams, setSearchParams] = useState<ReportSearchParams>({
    q: '',
    page: 1,
    page_size: 20,
  });

  const { data, isLoading } = useQuery({
    queryKey: ['reports', searchParams],
    queryFn: () => searchReports(searchParams),
    keepPreviousData: true,
  });

  const handleSearch = (values: Partial<ReportSearchParams>) => {
    setSearchParams({ ...searchParams, ...values, page: 1 });
  };

  const columns = [
    {
      title: '患者ID',
      dataIndex: 'patient_id',
      key: 'patient_id',
      width: 120,
    },
    {
      title: '患者姓名',
      dataIndex: 'patient_name',
      key: 'patient_name',
      width: 100,
    },
    {
      title: '检查日期',
      dataIndex: 'exam_date',
      key: 'exam_date',
      width: 120,
      sorter: true,
    },
    {
      title: '检查类型',
      dataIndex: 'exam_type',
      key: 'exam_type',
      width: 100,
    },
    {
      title: '报告内容',
      dataIndex: 'report_content',
      key: 'report_content',
      ellipsis: true,
      render: (text: string) => (
        <div dangerouslySetInnerHTML={{ __html: text }} />  {/* 高亮显示 */}
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (record: Report) => (
        <Space>
          <Button size="small">查看</Button>
          <Button size="small">AI分析</Button>
          <Button size="small">添加到项目</Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="report-search">
      <div className="search-filters">
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Input.Search
            placeholder="搜索报告内容..."
            size="large"
            prefix={<SearchOutlined />}
            onSearch={(value) => handleSearch({ q: value })}
            enterButton
          />

          <Space wrap>
            <Select
              placeholder="检查类型"
              style={{ width: 150 }}
              allowClear
              onChange={(value) => handleSearch({ exam_type: value })}
            >
              <Option value="CT">CT</Option>
              <Option value="MRI">MRI</Option>
              <Option value="X-Ray">X-Ray</Option>
              <Option value="超声">超声</Option>
            </Select>

            <Select
              placeholder="部门"
              style={{ width: 150 }}
              allowClear
              onChange={(value) => handleSearch({ department: value })}
            >
              <Option value="放射科">放射科</Option>
              <Option value="超声科">超声科</Option>
            </Select>

            <RangePicker
              placeholder={['开始日期', '结束日期']}
              onChange={(dates) => {
                if (dates) {
                  handleSearch({
                    date_from: dates[0]?.format('YYYY-MM-DD'),
                    date_to: dates[1]?.format('YYYY-MM-DD'),
                  });
                }
              }}
            />
          </Space>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={data?.items}
        loading={isLoading}
        rowKey="id"
        pagination={{
          current: searchParams.page,
          pageSize: searchParams.page_size,
          total: data?.total,
          showTotal: (total) => `共 ${total} 条`,
          onChange: (page, page_size) => {
            setSearchParams({ ...searchParams, page, page_size });
          },
        }}
        onChange={(pagination, filters, sorter) => {
          // 处理排序
          if (sorter && 'field' in sorter) {
            handleSearch({
              sort: sorter.field as string,
              order: sorter.order === 'ascend' ? 'asc' : 'desc',
            });
          }
        }}
      />
    </div>
  );
};
```

**Day 5: 报告详情页面**
- [ ] **详情展示**
  - 患者基本信息
  - 报告内容（格式化显示）
  - 历史AI分析记录
  - 所属项目列表

**Week 3 里程碑检查点**
- [ ] 全文搜索功能正常（中文支持）
- [ ] 多维度筛选正常工作
- [ ] 搜索性能满足要求（<2秒）
- [ ] 搜索结果高亮显示
- [ ] 报告详情页面完整

---

### Week 4: Ollama AI集成

#### 目标
- 集成Ollama本地LLM
- 实现4种AI标注功能
- 开发AI分析管理界面

#### 任务清单

**Day 1-2: OllamaClient实现**
- [ ] **Ollama客户端封装**
  - httpx异步客户端
  - 完整的OllamaClient类
  - 4种标注类型的system prompt
  - 并发控制（asyncio.Semaphore）
  - 错误处理和重试机制

**参考AI_INTEGRATION_GUIDE.md中的完整OllamaClient实现**

**Day 3-4: AI分析API**
- [ ] **AI分析端点**
  - 单报告分析（POST /api/v1/ai/analyze）
  - 批量分析（POST /api/v1/ai/batch-analyze）
  - 获取标注结果（GET /api/v1/ai/annotations/{report_id}）
  - 删除标注（DELETE /api/v1/ai/annotations/{id}）
  - FastAPI BackgroundTasks for batch processing

**Day 5: AI分析前端**
- [ ] **AI分析界面**
  - 分析对话框
  - 用户需求输入
  - 标注类型选择（highlight/classification/extraction/scoring）
  - 温度参数调整
  - 分析进度显示
  - 结果可视化展示

**前端AI分析组件示例** (`frontend/src/components/AIAnalysis/AnalysisModal.tsx`):

```typescript
import React, { useState } from 'react';
import { Modal, Form, Input, Select, Slider, Button, message } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { analyzeReport } from '@/services/ai';

const { TextArea } = Input;
const { Option } = Select;

interface AnalysisModalProps {
  reportId: string;
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const AnalysisModal: React.FC<AnalysisModalProps> = ({
  reportId,
  visible,
  onClose,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const [temperature, setTemperature] = useState(0.7);

  const { mutate: analyze, isLoading } = useMutation({
    mutationFn: analyzeReport,
    onSuccess: () => {
      message.success('AI分析完成！');
      onSuccess();
      onClose();
    },
    onError: (error: any) => {
      message.error(`分析失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleSubmit = () => {
    form.validateFields().then((values) => {
      analyze({
        report_id: reportId,
        user_prompt: values.user_prompt,
        annotation_type: values.annotation_type,
        temperature,
      });
    });
  };

  const annotationTypeDescriptions = {
    highlight: '标注报告中的关键信息（异常发现、测量数值、部位、诊断结论）',
    classification: '对报告进行多维度分类（紧急程度、检查部位、是否需要随访等）',
    extraction: '提取结构化信息（发现列表、测量数据、涉及部位、整体印象）',
    scoring: '对报告质量进行多维度评分（完整性、清晰度、详细度、临床价值）',
  };

  return (
    <Modal
      title={<><RobotOutlined /> AI辅助分析</>}
      open={visible}
      onCancel={onClose}
      onOk={handleSubmit}
      confirmLoading={isLoading}
      width={600}
      okText="开始分析"
      cancelText="取消"
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="annotation_type"
          label="标注类型"
          rules={[{ required: true, message: '请选择标注类型' }]}
        >
          <Select placeholder="请选择标注类型">
            <Option value="highlight">高亮标注 (Highlight)</Option>
            <Option value="classification">分类标注 (Classification)</Option>
            <Option value="extraction">信息提取 (Extraction)</Option>
            <Option value="scoring">质量评分 (Scoring)</Option>
          </Select>
        </Form.Item>

        <Form.Item noStyle shouldUpdate={(prev, curr) => prev.annotation_type !== curr.annotation_type}>
          {({ getFieldValue }) => {
            const type = getFieldValue('annotation_type');
            return type ? (
              <div style={{ marginBottom: 16, padding: 8, background: '#f5f5f5', borderRadius: 4 }}>
                <small>{annotationTypeDescriptions[type as keyof typeof annotationTypeDescriptions]}</small>
              </div>
            ) : null;
          }}
        </Form.Item>

        <Form.Item
          name="user_prompt"
          label="分析需求"
          rules={[{ required: true, message: '请输入分析需求' }]}
        >
          <TextArea
            rows={4}
            placeholder="例如：请提取报告中的所有关键发现和测量数值"
          />
        </Form.Item>

        <Form.Item label={`模型温度: ${temperature}`}>
          <Slider
            min={0.1}
            max={1.0}
            step={0.1}
            value={temperature}
            onChange={setTemperature}
            marks={{
              0.1: '精确',
              0.5: '平衡',
              1.0: '创意',
            }}
          />
          <small style={{ color: '#666' }}>
            温度越低，输出越稳定精确；温度越高，输出越富有变化
          </small>
        </Form.Item>
      </Form>
    </Modal>
  );
};
```

**Week 4 里程碑检查点**
- [ ] Ollama服务正常运行
- [ ] OllamaClient可以成功调用模型
- [ ] 4种AI标注功能全部可用
- [ ] 单报告和批量分析正常工作
- [ ] AI分析结果正确保存到数据库
- [ ] 前端可以触发AI分析并查看结果

---

## Week 5-6: AI分析优化和项目管理

### Week 5: AI分析结果可视化

#### 目标
- 优化AI分析结果展示
- 实现标注结果的交互式查看
- 开发AI分析历史管理

#### 任务清单

**Day 1-2: 标注结果可视化**
- [ ] **Highlight标注展示**
  - 文本高亮显示组件
  - 不同类别使用不同颜色
  - 鼠标悬停显示标注理由

- [ ] **Classification分类展示**
  - 分类标签展示
  - 置信度可视化（进度条）
  - 多维度分类分组显示

- [ ] **Extraction提取结果**
  - 结构化数据表格
  - 测量数据图表化
  - 部位信息可视化

- [ ] **Scoring评分展示**
  - 雷达图/柱状图
  - 各维度评分详情
  - 总体评分突出显示

**前端标注结果组件示例** (`frontend/src/components/AIAnalysis/AnnotationViewer.tsx`):

```typescript
import React from 'react';
import { Card, Tag, Progress, Table, Tooltip, Row, Col, Statistic } from 'antd';
import { Radar } from '@ant-design/plots';
import type { AIAnnotation } from '@/types/annotation';

interface AnnotationViewerProps {
  annotation: AIAnnotation;
}

export const AnnotationViewer: React.FC<AnnotationViewerProps> = ({ annotation }) => {
  const renderContent = () => {
    switch (annotation.annotation_type) {
      case 'highlight':
        return <HighlightViewer content={annotation.content} />;
      case 'classification':
        return <ClassificationViewer content={annotation.content} />;
      case 'extraction':
        return <ExtractionViewer content={annotation.content} />;
      case 'scoring':
        return <ScoringViewer content={annotation.content} />;
      default:
        return <pre>{JSON.stringify(annotation.content, null, 2)}</pre>;
    }
  };

  return (
    <Card
      title={`AI分析结果 - ${getTypeName(annotation.annotation_type)}`}
      extra={
        <Tag color="blue">
          置信度: {(annotation.confidence * 100).toFixed(1)}%
        </Tag>
      }
    >
      {renderContent()}

      <div style={{ marginTop: 16, padding: 12, background: '#f9f9f9', borderRadius: 4 }}>
        <small style={{ color: '#666' }}>
          用户需求: {annotation.user_prompt}
        </small>
        <br />
        <small style={{ color: '#666' }}>
          分析时间: {new Date(annotation.created_at).toLocaleString()}
        </small>
      </div>
    </Card>
  );
};

// Highlight标注查看器
const HighlightViewer: React.FC<{ content: any }> = ({ content }) => {
  const categoryColors = {
    abnormal: '#ff4d4f',
    measurement: '#1890ff',
    location: '#52c41a',
    diagnosis: '#faad14',
  };

  return (
    <div>
      {content.highlights.map((highlight: any, idx: number) => (
        <Tooltip key={idx} title={highlight.reason}>
          <Tag
            color={categoryColors[highlight.category as keyof typeof categoryColors]}
            style={{ margin: '4px', cursor: 'pointer' }}
          >
            {highlight.text}
          </Tag>
        </Tooltip>
      ))}
    </div>
  );
};

// Classification分类查看器
const ClassificationViewer: React.FC<{ content: any }> = ({ content }) => {
  return (
    <Row gutter={[16, 16]}>
      {content.classifications.map((cls: any, idx: number) => (
        <Col key={idx} xs={24} sm={12} md={8}>
          <Card size="small" title={cls.dimension}>
            <Tag color="blue" style={{ marginBottom: 8 }}>{cls.category}</Tag>
            <Progress
              percent={Math.round(cls.confidence * 100)}
              size="small"
              status="active"
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
};

// Extraction提取查看器
const ExtractionViewer: React.FC<{ content: any }> = ({ content }) => {
  const measurementColumns = [
    { title: '测量项目', dataIndex: 'item', key: 'item' },
    { title: '数值', dataIndex: 'value', key: 'value' },
    { title: '单位', dataIndex: 'unit', key: 'unit' },
  ];

  return (
    <div>
      <Card size="small" title="发现" style={{ marginBottom: 16 }}>
        {content.findings.map((finding: string, idx: number) => (
          <Tag key={idx} style={{ margin: 4 }}>{finding}</Tag>
        ))}
      </Card>

      {content.measurements && content.measurements.length > 0 && (
        <Card size="small" title="测量数据" style={{ marginBottom: 16 }}>
          <Table
            dataSource={content.measurements}
            columns={measurementColumns}
            size="small"
            pagination={false}
          />
        </Card>
      )}

      <Card size="small" title="涉及部位">
        {content.locations.map((location: string, idx: number) => (
          <Tag key={idx} color="green" style={{ margin: 4 }}>{location}</Tag>
        ))}
      </Card>

      {content.impression && (
        <Card size="small" title="整体印象" style={{ marginTop: 16 }}>
          <p>{content.impression}</p>
        </Card>
      )}
    </div>
  );
};

// Scoring评分查看器
const ScoringViewer: React.FC<{ content: any }> = ({ content }) => {
  const radarData = content.scores.map((score: any) => ({
    dimension: score.dimension,
    value: score.score,
  }));

  const radarConfig = {
    data: radarData,
    xField: 'dimension',
    yField: 'value',
    meta: {
      value: { min: 0, max: 100 },
    },
    point: { size: 2 },
    area: {},
  };

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card>
            <Statistic
              title="总体评分"
              value={content.overall_score}
              suffix="/ 100"
              valueStyle={{ color: content.overall_score >= 80 ? '#3f8600' : '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col xs={24} md={12}>
          <Radar {...radarConfig} height={300} />
        </Col>
        <Col xs={24} md={12}>
          {content.scores.map((score: any, idx: number) => (
            <Card key={idx} size="small" style={{ marginBottom: 8 }}>
              <Row justify="space-between" align="middle">
                <Col>{score.dimension}</Col>
                <Col>
                  <Tag color={score.score >= 80 ? 'green' : 'orange'}>
                    {score.score} / {score.max_score}
                  </Tag>
                </Col>
              </Row>
              <Progress percent={(score.score / score.max_score) * 100} showInfo={false} size="small" />
              <small style={{ color: '#666' }}>{score.reason}</small>
            </Card>
          ))}
        </Col>
      </Row>
    </div>
  );
};

function getTypeName(type: string): string {
  const names: Record<string, string> = {
    highlight: '高亮标注',
    classification: '分类标注',
    extraction: '信息提取',
    scoring: '质量评分',
  };
  return names[type] || type;
}
```

**Day 3-4: AI分析历史管理**
- [ ] **分析历史列表**
  - 按报告查看历史分析
  - 时间轴展示
  - 对比不同分析结果
  - 删除/导出分析结果

**Day 5: 批量分析监控**
- [ ] **批量分析进度**
  - 实时进度显示
  - 成功/失败统计
  - 错误报告
  - 取消批量任务

**Week 5 里程碑检查点**
- [ ] 4种标注类型都有专门的可视化组件
- [ ] 标注结果易于理解和交互
- [ ] 可以查看单个报告的所有历史分析
- [ ] 批量分析进度可以实时监控

---

### Week 6: 项目管理功能

#### 目标
- 实现完整的项目CRUD功能
- 开发报告与项目的关联管理
- 实现项目数据导出

#### 任务清单

**Day 1-2: 项目管理API**
- [ ] **项目CRUD端点**
  - 创建项目（POST /api/v1/projects）
  - 获取项目列表（GET /api/v1/projects）
  - 获取项目详情（GET /api/v1/projects/{id}）
  - 更新项目（PUT /api/v1/projects/{id}）
  - 删除项目（DELETE /api/v1/projects/{id}）

- [ ] **报告关联管理**
  - 添加报告到项目（POST /api/v1/projects/{id}/reports）
  - 从项目移除报告（DELETE /api/v1/projects/{id}/reports/{report_id}）
  - 批量添加报告

**Day 3-4: 项目前端页面**
- [ ] **项目列表页面**
  - 项目卡片展示
  - 创建项目对话框
  - 搜索和筛选项目

- [ ] **项目详情页面**
  - 项目基本信息
  - 包含报告列表（可移除）
  - 添加报告功能（从搜索结果添加）
  - 项目统计信息

**前端项目管理示例** (`frontend/src/pages/Projects/ProjectDetail.tsx`):

```typescript
import React, { useState } from 'react';
import { Card, Table, Button, Space, Modal, message, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, ExportOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getProject, removeReportFromProject, exportProject } from '@/services/projects';
import { AddReportsModal } from '@/components/Projects/AddReportsModal';

interface ProjectDetailProps {
  projectId: string;
}

export const ProjectDetail: React.FC<ProjectDetailProps> = ({ projectId }) => {
  const queryClient = useQueryClient();
  const [addModalVisible, setAddModalVisible] = useState(false);

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => getProject(projectId),
  });

  const { mutate: removeReport } = useMutation({
    mutationFn: ({ reportId }: { reportId: string }) =>
      removeReportFromProject(projectId, reportId),
    onSuccess: () => {
      message.success('报告已移除');
      queryClient.invalidateQueries(['project', projectId]);
    },
  });

  const handleExport = async (format: 'excel' | 'csv' | 'json') => {
    try {
      await exportProject(projectId, format);
      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
    }
  };

  const columns = [
    {
      title: '患者ID',
      dataIndex: 'patient_id',
      key: 'patient_id',
    },
    {
      title: '患者姓名',
      dataIndex: 'patient_name',
      key: 'patient_name',
    },
    {
      title: '检查日期',
      dataIndex: 'exam_date',
      key: 'exam_date',
    },
    {
      title: '检查类型',
      dataIndex: 'exam_type',
      key: 'exam_type',
    },
    {
      title: 'AI分析',
      key: 'ai_annotations',
      render: (record: any) => record.ai_annotations_count || 0,
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: any) => (
        <Space>
          <Button size="small">查看</Button>
          <Popconfirm
            title="确定移除此报告？"
            onConfirm={() => removeReport({ reportId: record.id })}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              移除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="project-detail">
      <Card
        title={project?.name}
        extra={
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setAddModalVisible(true)}
            >
              添加报告
            </Button>
            <Button.Group>
              <Button icon={<ExportOutlined />} onClick={() => handleExport('excel')}>
                导出Excel
              </Button>
              <Button onClick={() => handleExport('csv')}>CSV</Button>
              <Button onClick={() => handleExport('json')}>JSON</Button>
            </Button.Group>
          </Space>
        }
        loading={isLoading}
      >
        <p>{project?.description}</p>
        <p style={{ color: '#666' }}>
          创建时间: {new Date(project?.created_at).toLocaleString()}
        </p>
        <p style={{ color: '#666' }}>
          报告数量: {project?.reports?.length || 0}
        </p>
      </Card>

      <Card title="项目报告" style={{ marginTop: 16 }}>
        <Table
          columns={columns}
          dataSource={project?.reports}
          loading={isLoading}
          rowKey="id"
        />
      </Card>

      <AddReportsModal
        projectId={projectId}
        visible={addModalVisible}
        onClose={() => setAddModalVisible(false)}
        onSuccess={() => {
          setAddModalVisible(false);
          queryClient.invalidateQueries(['project', projectId]);
        }}
      />
    </div>
  );
};
```

**Day 5: 数据导出功能**
- [ ] **导出API实现**
  - Excel导出（openpyxl）
  - CSV导出
  - JSON导出
  - 包含AI分析结果选项

**后端导出服务示例** (`backend/app/services/export_service.py`):

```python
import pandas as pd
from typing import List, Dict, Any
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from app.models.report import Report
from app.models.ai_annotation import AIAnnotation


class ProjectExporter:
    """项目数据导出服务"""

    def __init__(self, project_id: str, include_ai_annotations: bool = True):
        self.project_id = project_id
        self.include_ai_annotations = include_ai_annotations

    def export_to_excel(self, file_path: str):
        """导出为Excel文件"""
        wb = Workbook()
        ws = wb.active
        ws.title = "报告数据"

        # 表头
        headers = [
            "患者ID", "患者姓名", "性别", "年龄", "检查日期",
            "检查类型", "检查部位", "科室", "报告内容", "诊断结论"
        ]

        if self.include_ai_annotations:
            headers.extend(["AI分析数", "最近AI分析"])

        # 写入表头
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # 获取报告数据
        reports = self._get_reports()

        # 写入数据
        for row_idx, report in enumerate(reports, start=2):
            ws.cell(row=row_idx, column=1).value = report['patient_id']
            ws.cell(row=row_idx, column=2).value = report['patient_name']
            ws.cell(row=row_idx, column=3).value = report['gender']
            ws.cell(row=row_idx, column=4).value = report['age']
            ws.cell(row=row_idx, column=5).value = report['exam_date'].strftime('%Y-%m-%d')
            ws.cell(row=row_idx, column=6).value = report['exam_type']
            ws.cell(row=row_idx, column=7).value = report['body_part']
            ws.cell(row=row_idx, column=8).value = report['department']
            ws.cell(row=row_idx, column=9).value = report['report_content']
            ws.cell(row=row_idx, column=10).value = report['diagnosis']

            if self.include_ai_annotations:
                annotations = report.get('ai_annotations', [])
                ws.cell(row=row_idx, column=11).value = len(annotations)
                if annotations:
                    latest = annotations[0]  # 假设已按时间倒序
                    ws.cell(row=row_idx, column=12).value = f"{latest['annotation_type']}: {latest['created_at']}"

        # 调整列宽
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width

        wb.save(file_path)

    def export_to_csv(self, file_path: str):
        """导出为CSV文件"""
        reports = self._get_reports()

        # 转换为DataFrame
        df = pd.DataFrame(reports)

        # 选择导出列
        columns = [
            'patient_id', 'patient_name', 'gender', 'age', 'exam_date',
            'exam_type', 'body_part', 'department', 'report_content', 'diagnosis'
        ]

        df = df[columns]
        df.to_csv(file_path, index=False, encoding='utf-8-sig')

    def export_to_json(self, file_path: str):
        """导出为JSON文件"""
        reports = self._get_reports()

        import json
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=2, default=str)

    def _get_reports(self) -> List[Dict[str, Any]]:
        """获取项目报告数据"""
        from app.core.database import SessionLocal

        db = SessionLocal()

        try:
            # 查询项目报告
            reports = db.query(Report).join(ProjectReport).filter(
                ProjectReport.project_id == self.project_id,
                Report.is_deleted == False
            ).all()

            result = []

            for report in reports:
                report_dict = {
                    'id': str(report.id),
                    'patient_id': report.patient_id,
                    'patient_name': report.patient_name,
                    'gender': report.gender,
                    'age': report.age,
                    'exam_date': report.exam_date,
                    'exam_type': report.exam_type,
                    'body_part': report.body_part,
                    'department': report.department,
                    'report_content': report.report_content,
                    'diagnosis': report.diagnosis,
                }

                if self.include_ai_annotations:
                    annotations = db.query(AIAnnotation).filter(
                        AIAnnotation.report_id == report.id
                    ).order_by(AIAnnotation.created_at.desc()).all()

                    report_dict['ai_annotations'] = [
                        {
                            'annotation_type': ann.annotation_type,
                            'content': ann.content,
                            'confidence': ann.confidence,
                            'created_at': ann.created_at.isoformat(),
                        }
                        for ann in annotations
                    ]

                result.append(report_dict)

            return result

        finally:
            db.close()
```

**Week 6 里程碑检查点**
- [ ] 可以创建、编辑、删除项目
- [ ] 可以添加/移除报告到项目
- [ ] 项目详情页面显示完整信息
- [ ] 可以导出项目数据（Excel/CSV/JSON）
- [ ] 导出的数据包含AI分析结果

---

## Week 7: 测试和优化

### Week 7: 全面测试和性能优化

#### 目标
- 完成单元测试和集成测试
- 进行性能优化
- 修复已知bug
- 准备生产部署

#### 任务清单

**Day 1-2: 测试覆盖**
- [ ] **后端测试**
  - 单元测试（pytest）
    - OllamaClient测试
    - 认证系统测试
    - 报告API测试
    - AI分析API测试
    - 项目管理API测试
  - 集成测试
    - 完整用户流程测试
    - API端到端测试
  - 测试覆盖率目标：> 80%

**pytest测试示例** (`backend/tests/test_ai_analysis.py`):

```python
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.main import app
from app.services.ollama_client import OllamaClient


@pytest.mark.asyncio
async def test_analyze_single_report_success():
    """测试单报告AI分析 - 成功场景"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Mock Ollama响应
        with patch.object(OllamaClient, 'analyze_report', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {
                "annotation_type": "extraction",
                "content": {
                    "findings": ["双肺纹理增多"],
                    "locations": ["双肺"]
                },
                "confidence": 0.92,
                "model_name": "qwen2.5:7b",
                "model_temperature": 0.7,
                "total_duration_seconds": 10.5,
                "eval_count": 50,
                "prompt_eval_count": 30,
            }

            # 发送请求
            response = await client.post(
                "/api/v1/ai/analyze",
                json={
                    "report_id": 1,
                    "user_prompt": "提取关键发现",
                    "annotation_type": "extraction",
                    "temperature": 0.7
                },
                headers={"Authorization": f"Bearer {test_token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "annotation_id" in data
            assert data["annotation_type"] == "extraction"
            assert data["confidence"] == 0.92


@pytest.mark.asyncio
async def test_ollama_unavailable():
    """测试Ollama服务不可用场景"""
    with patch.object(OllamaClient, 'health_check', return_value=False):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/ai/analyze",
                json={
                    "report_id": 1,
                    "user_prompt": "测试",
                    "annotation_type": "extraction"
                },
                headers={"Authorization": f"Bearer {test_token}"}
            )

            assert response.status_code == 503
            assert "unavailable" in response.json()["detail"].lower()
```

- [ ] **前端测试**
  - 组件单元测试（Vitest + React Testing Library）
  - E2E测试（Playwright）

**Day 3-4: 性能优化**
- [ ] **后端优化**
  - 数据库查询优化（explain analyze）
  - API响应时间优化
  - 添加Redis缓存（可选）
  - 优化Ollama并发控制

- [ ] **前端优化**
  - 代码分割（lazy loading）
  - 虚拟滚动（react-window）
  - 图片懒加载
  - 打包优化（生产build）

**性能基准测试**:
```bash
# API响应时间
- 报告列表查询: < 500ms
- 全文搜索: < 2s
- AI单报告分析: < 60s
- 报告详情: < 300ms

# 前端性能
- FCP (First Contentful Paint): < 1.5s
- TTI (Time to Interactive): < 3s
- Bundle size: < 500KB (gzip)
```

**Day 5: Bug修复和安全加固**
- [ ] **Bug修复**
  - 修复测试中发现的bug
  - 修复已知UI问题
  - 边界条件处理

- [ ] **安全加固**
  - SQL注入防护验证（使用ORM）
  - XSS防护检查
  - CORS配置
  - 密码强度要求
  - 敏感数据脱敏（日志）

**安全检查清单**:
```python
# backend/app/core/security.py

# ✅ 密码强度验证
def validate_password_strength(password: str) -> bool:
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

# ✅ SQL注入防护（使用ORM参数化查询）
query = db.query(Report).filter(Report.patient_id == patient_id)  # 安全

# ❌ 避免字符串拼接
# query = db.execute(f"SELECT * FROM reports WHERE patient_id = '{patient_id}'")  # 危险

# ✅ XSS防护（前端自动转义）
# Ant Design和React默认转义HTML
<div>{userInput}</div>  # 安全

# ❌ 避免dangerouslySetInnerHTML（除非必要且已清理）
# <div dangerouslySetInnerHTML={{ __html: userInput }} />  # 危险
```

**Week 7 里程碑检查点**
- [ ] 测试覆盖率达到80%+
- [ ] 所有核心功能通过集成测试
- [ ] API响应时间满足性能基准
- [ ] 前端性能指标达标
- [ ] 安全检查通过
- [ ] 已知bug全部修复

---

## Week 8: 部署和培训

### Week 8: 生产部署和用户培训

#### 目标
- 完成生产环境部署
- 配置监控和日志
- 完成用户培训
- 交付完整文档

#### 任务清单

**Day 1-2: 生产环境部署**
- [ ] **服务器配置**
  - 配置生产服务器（云服务器或本地服务器）
  - 安装Docker和Docker Compose
  - 配置防火墙规则
  - 配置域名和SSL证书（如果需要）

- [ ] **Docker生产部署**
  - 构建生产Docker镜像
  - 配置docker-compose.prod.yml
  - 配置环境变量（.env.prod）
  - 运行数据库迁移
  - 创建初始管理员账号

**生产部署清单**:
```bash
# 1. 克隆代码
git clone <repository_url>
cd image_data_platform

# 2. 配置环境变量
cp .env.example .env.prod
nano .env.prod  # 编辑生产环境变量

# 3. 构建镜像
docker-compose -f docker-compose.prod.yml build

# 4. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 5. 下载Ollama模型
docker exec ollama ollama pull qwen2.5:7b

# 6. 运行数据库迁移
docker exec backend alembic upgrade head

# 7. 创建管理员账号
docker exec backend python scripts/create_admin.py

# 8. 健康检查
curl http://localhost:8000/api/v1/health

# 9. 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

**Day 3: 监控和日志**
- [ ] **监控配置**
  - 配置系统监控（CPU、内存、磁盘）
  - 配置Ollama服务监控
  - 配置数据库监控
  - 设置告警规则

- [ ] **日志管理**
  - 配置日志轮转
  - 日志级别设置（生产环境INFO）
  - 关键操作日志记录
  - 错误日志聚合

**简单监控脚本** (`scripts/monitor.sh`):
```bash
#!/bin/bash

# 系统监控脚本

echo "=== System Health Check ==="
date

# 检查Docker容器状态
echo "--- Docker Containers ---"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 检查服务健康
echo "--- Service Health ---"
curl -s http://localhost:8000/api/v1/health | jq '.'

# 检查磁盘空间
echo "--- Disk Usage ---"
df -h | grep -E "/$|/var|/home"

# 检查内存使用
echo "--- Memory Usage ---"
free -h

# 检查Ollama模型
echo "--- Ollama Models ---"
docker exec ollama ollama list

# 检查数据库连接
echo "--- Database Connection ---"
docker exec postgres pg_isready -U user

echo "=== Health Check Complete ==="
```

**Day 4-5: 用户培训和文档交付**
- [ ] **用户培训**
  - 准备培训PPT
  - 系统功能演示
  - 数据导入演示
  - AI分析功能演示
  - 项目管理演示
  - 问题答疑

- [ ] **文档交付**
  - 用户操作手册
  - 管理员手册（部署和维护）
  - API文档（Swagger UI）
  - 常见问题FAQ
  - 故障排查指南

**用户培训内容大纲**:
```
1. 系统登录和基础操作（15分钟）
   - 登录/登出
   - 界面导航
   - 个人信息修改

2. 数据导入功能（30分钟）
   - Excel/CSV文件准备
   - 字段映射配置
   - 导入预览和执行
   - 导入结果查看
   - 常见导入问题处理

3. 报告检索功能（20分钟）
   - 全文搜索
   - 高级筛选
   - 搜索结果查看
   - 报告详情查看

4. AI分析功能（40分钟）
   - AI分析介绍（4种标注类型）
   - 单报告分析演示
   - 批量分析演示
   - 分析结果查看和解读
   - 分析历史管理
   - AI分析最佳实践

5. 项目管理功能（30分钟）
   - 创建项目
   - 添加报告到项目
   - 项目数据管理
   - 项目数据导出（Excel/CSV/JSON）

6. 问题答疑和实操练习（30分钟）
```

**简易用户手册目录**:
```
# 影像数据平台用户手册

## 1. 快速开始
- 1.1 系统登录
- 1.2 界面概览
- 1.3 基本操作

## 2. 数据导入
- 2.1 准备导入文件
- 2.2 上传和预览
- 2.3 字段映射
- 2.4 执行导入
- 2.5 查看导入结果

## 3. 报告检索
- 3.1 全文搜索
- 3.2 高级筛选
- 3.3 搜索技巧
- 3.4 报告详情

## 4. AI辅助分析
- 4.1 AI分析介绍
- 4.2 高亮标注
- 4.3 分类标注
- 4.4 信息提取
- 4.5 质量评分
- 4.6 批量分析
- 4.7 分析结果管理

## 5. 项目管理
- 5.1 创建项目
- 5.2 添加报告
- 5.3 管理项目
- 5.4 导出数据

## 6. 常见问题
- 6.1 导入问题
- 6.2 搜索问题
- 6.3 AI分析问题
- 6.4 其他问题

## 7. 技术支持
```

**Week 8 里程碑检查点**
- [ ] 生产环境成功部署并运行稳定
- [ ] 监控和日志系统正常工作
- [ ] 用户培训完成
- [ ] 所有文档交付完整
- [ ] 系统验收通过

---

## Phase 1 最终交付清单

### 代码交付
- [ ] 源代码（Git仓库）
- [ ] Docker镜像
- [ ] Docker Compose配置（开发和生产）
- [ ] 数据库迁移脚本
- [ ] 配置文件模板（.env.example）
- [ ] 部署脚本

### 文档交付
- [ ] 项目概述文档（PROJECT_OVERVIEW.md）
- [ ] 技术架构文档（TECHNICAL_ARCHITECTURE.md）
- [ ] 数据库设计文档（DATABASE_DESIGN.md）
- [ ] API接口文档（API_SPECIFICATION.md + Swagger UI）
- [ ] AI集成指南（AI_INTEGRATION_GUIDE.md）
- [ ] 开发工作流（本文档）
- [ ] 用户操作手册
- [ ] 管理员部署手册
- [ ] 常见问题FAQ

### 测试交付
- [ ] 单元测试代码
- [ ] 集成测试代码
- [ ] 测试报告（覆盖率>80%）
- [ ] 性能测试报告

### 培训交付
- [ ] 培训PPT
- [ ] 操作演示视频（可选）
- [ ] 快速入门指南
- [ ] 培训签到表

---

## 开发规范

### 代码规范

#### Python (后端)
```python
# 遵循PEP 8
# 使用类型提示
from typing import Optional, List

def get_report(report_id: str, db: Session) -> Optional[Report]:
    """获取报告

    Args:
        report_id: 报告ID
        db: 数据库会话

    Returns:
        报告对象，不存在返回None
    """
    return db.query(Report).filter(Report.id == report_id).first()

# 使用有意义的变量名
user_email = "user@example.com"  # ✅ Good
e = "user@example.com"  # ❌ Bad

# 函数应该做一件事
def create_and_send_report():  # ❌ Bad - 做了两件事
    pass

def create_report():  # ✅ Good
    pass

def send_report():  # ✅ Good
    pass
```

#### TypeScript (前端)
```typescript
// 使用接口定义类型
interface Report {
  id: string;
  patientId: string;
  patientName: string;
  examDate: string;
  reportContent: string;
}

// 使用函数组件和Hooks
const ReportList: React.FC<{ filters: Filters }> = ({ filters }) => {
  const [reports, setReports] = useState<Report[]>([]);

  useEffect(() => {
    fetchReports(filters).then(setReports);
  }, [filters]);

  return <div>{/* ... */}</div>;
};

// 避免any类型
const data: any = {};  // ❌ Bad
const data: ReportData = {};  // ✅ Good
```

### Git工作流

```bash
# 分支命名
main          # 生产环境代码
develop       # 开发主分支

# 功能分支
feature/patient-import
feature/ai-analysis
feature/project-export

# Bug修复
bugfix/login-token-issue
bugfix/search-crash

# 提交信息规范
<type>(<scope>): <subject>

# type类型
feat:     新功能
fix:      Bug修复
docs:     文档更新
style:    代码格式
refactor: 重构
test:     测试
chore:    构建/工具

# 示例
feat(ai): add batch analysis endpoint
fix(search): resolve fulltext search crash
docs(api): update API documentation
```

### 测试策略

```python
# 单元测试 - 测试单个函数
def test_hash_password():
    hashed = hash_password("Test@1234")
    assert hashed != "Test@1234"
    assert verify_password("Test@1234", hashed)

# 集成测试 - 测试API端点
@pytest.mark.asyncio
async def test_create_report_api():
    response = await client.post("/api/v1/reports", json=report_data)
    assert response.status_code == 201
    assert "id" in response.json()

# 端到端测试 - 测试完整流程
@pytest.mark.asyncio
async def test_complete_workflow():
    # 1. 登录
    login_response = await client.post("/api/v1/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    # 2. 创建报告
    report_response = await client.post(
        "/api/v1/reports",
        json=report_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    report_id = report_response.json()["id"]

    # 3. AI分析
    analysis_response = await client.post(
        "/api/v1/ai/analyze",
        json={"report_id": report_id, ...},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert analysis_response.status_code == 200
```

---

## 风险管理

### 技术风险

| 风险项 | 概率 | 影响 | 应对措施 |
|--------|------|------|----------|
| Ollama性能不足 | 中 | 高 | 使用GPU加速；考虑云API fallback |
| 中文分词问题 | 低 | 中 | 使用PostgreSQL simple词典；测试覆盖 |
| 数据导入兼容性 | 中 | 中 | 支持多种文件格式；详细错误提示 |
| 并发性能瓶颈 | 低 | 中 | 信号量限流；数据库连接池优化 |

### 项目风险

| 风险项 | 概率 | 影响 | 应对措施 |
|--------|------|------|----------|
| 需求变更 | 中 | 中 | 敏捷开发；MVP优先；定期沟通 |
| 时间延误 | 低 | 中 | 8周计划有缓冲；核心功能优先 |
| 资源不足 | 低 | 高 | 简化Phase 1范围；Phase 2扩展 |
| AI准确性不足 | 中 | 高 | Prompt优化；用户反馈迭代；温度调整 |

---

## Phase 2 规划（未来扩展）

Phase 1完成后，可以考虑以下Phase 2功能扩展：

### 功能扩展
1. **DICOM影像支持**
   - DICOM文件上传和存储（MinIO）
   - Cornerstone.js影像查看器
   - 影像与报告关联

2. **Accssyn自动同步**
   - Accssyn API集成
   - 定时任务同步（Celery Beat）
   - WebSocket实时进度

3. **高级分析功能**
   - AI模型微调（基于反馈数据）
   - 多模态分析（影像+报告）
   - 统计分析和数据可视化

4. **系统增强**
   - Redis缓存层
   - Elasticsearch全文搜索
   - 更多导出格式（PDF报告）
   - 移动端适配

### 时间估算
Phase 2预计需要额外8-12周开发时间。

---

## 总结

本8周Phase 1开发计划专注于构建AI驱动的报告筛选和管理系统核心功能：

**Week 1-2**: 基础架构、认证、数据导入
**Week 3-4**: 报告检索、Ollama AI集成
**Week 5-6**: AI结果可视化、项目管理
**Week 7**: 测试和优化
**Week 8**: 部署和培训

**关键成功因素**：
1. ✅ 聚焦Phase 1核心价值（报告+AI）
2. ✅ 简化技术栈（4服务：PostgreSQL + Ollama + Backend + Frontend）
3. ✅ 本地LLM保障数据隐私和成本控制
4. ✅ 清晰的里程碑检查点
5. ✅ 完整的文档和培训支持

遵循本工作流，您将能够在8周内交付一个功能完整、性能可靠的AI辅助医疗报告筛选系统！

---

**文档版本**：v2.0.0 (Phase 1)
**最后更新**：2024-12-01
**维护团队**：影像数据平台开发团队
