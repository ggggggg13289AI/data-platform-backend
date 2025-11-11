# 数据库设计方案 (Phase 1)

**项目名称**: 影像数据平台 - AI辅助报告筛选系统
**文档版本**: v2.0.0 (Phase 1)
**最后更新**: 2024-12-01
**数据库**: PostgreSQL 14+

---

## 文档概述

### Phase 1 设计原则
1. **简化优先**: 5张核心表，满足AI报告分析和项目管理需求
2. **聚焦功能**: 报告数据 + AI标记 + 项目组织
3. **扩展性**: 为Phase 2预留扩展空间（影像管理）
4. **性能优化**: 适当的索引和查询优化
5. **审计追踪**: 创建时间、更新时间、软删除

### Phase 1 vs 原设计对比

| 类别 | 原设计 (11表) | Phase 1 (5表) | 说明 |
|-----|-------------|--------------|------|
| 用户认证 | users, roles, permissions | users | 简化为基本认证 |
| 报告数据 | patients, studies, series, images, reports | reports | 只保留报告表 |
| AI功能 | - | ai_annotations | 新增AI标记表 |
| 项目管理 | - | projects, project_reports | 新增项目表 |
| 系统集成 | sync_jobs, sync_records | - | Phase 2 |
| 影像管理 | images, dicom_metadata | - | Phase 2 |

---

## ER图概览 (Phase 1)

```
┌─────────────┐
│   users     │
│  (用户表)    │
│   简化认证   │
└──────┬──────┘
       │ 创建
       │
       ▼
┌─────────────┐       1:N      ┌─────────────────┐
│   reports   │◄───────────────┤ ai_annotations  │
│  (报告表)    │                │  (AI标记表)      │
│  检查报告数据 │                │  AI分析结果      │
└──────┬──────┘                └─────────────────┘
       │
       │ N:M
       │
       ▼
┌─────────────┐                ┌─────────────────┐
│  projects   │◄──────────────►│ project_reports │
│  (项目表)    │       N:M       │ (项目-报告关联)  │
│  数据组织    │                └─────────────────┘
└─────────────┘
```

---

## 核心数据表设计

### 1. users (用户表)

**用途**: 简化的用户认证和基本权限管理

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),

    -- 角色（简化版）
    role VARCHAR(20) DEFAULT 'researcher' CHECK (role IN ('admin', 'researcher')),

    -- 状态
    is_active BOOLEAN DEFAULT true,

    -- 登录信息
    last_login_at TIMESTAMP WITH TIME ZONE,

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

-- 索引
CREATE INDEX idx_users_email ON users(email) WHERE is_active = true;
CREATE INDEX idx_users_role ON users(role);

-- 触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 初始管理员账号
INSERT INTO users (email, password_hash, full_name, role) VALUES
('admin@example.com', '$2b$12$KIXxLVQy7JZ5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5', '系统管理员', 'admin');
```

**字段说明**:
- `id`: 主键，自增ID
- `email`: 邮箱（唯一，作为登录用户名）
- `password_hash`: bcrypt加密的密码哈希
- `full_name`: 用户全名
- `role`: 角色（admin: 管理员, researcher: 研究人员）
- `is_active`: 账号是否激活
- `last_login_at`: 最后登录时间

**Phase 1 简化**:
- ❌ 移除复杂的roles和permissions表
- ✅ 只有2种角色：管理员和研究人员
- ✅ 权限硬编码在后端代码中

---

### 2. reports (报告表)

**用途**: 存储检查报告数据（不包含影像文件）

```sql
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,

    -- 患者基本信息（嵌入，Phase 1不需要单独患者表）
    patient_id VARCHAR(50) NOT NULL,
    patient_name VARCHAR(100),
    patient_age INTEGER,
    patient_gender VARCHAR(10) CHECK (patient_gender IN ('M', 'F', 'Other', 'Unknown')),

    -- 检查信息
    exam_date DATE NOT NULL,
    exam_type VARCHAR(50) NOT NULL, -- CT, MRI, X-Ray, Ultrasound, etc.
    exam_description TEXT,
    department VARCHAR(100),

    -- 报告内容（核心字段）
    report_content TEXT NOT NULL,
    findings TEXT,
    diagnosis TEXT,
    impression TEXT,

    -- ICD编码（可选）
    icd_codes JSONB,

    -- 数据来源
    source VARCHAR(50) DEFAULT 'import', -- import, manual, api
    source_reference VARCHAR(200), -- 原始数据源引用

    -- 导入信息
    imported_by INTEGER REFERENCES users(id),
    imported_at TIMESTAMP WITH TIME ZONE,

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 索引（优化搜索性能）
CREATE INDEX idx_reports_patient_id ON reports(patient_id) WHERE is_deleted = false;
CREATE INDEX idx_reports_patient_name ON reports(patient_name) WHERE is_deleted = false;
CREATE INDEX idx_reports_exam_date ON reports(exam_date DESC) WHERE is_deleted = false;
CREATE INDEX idx_reports_exam_type ON reports(exam_type) WHERE is_deleted = false;
CREATE INDEX idx_reports_department ON reports(department) WHERE is_deleted = false;

-- 全文搜索索引（PostgreSQL特性）
CREATE INDEX idx_reports_content_fulltext ON reports USING gin(to_tsvector('simple', report_content)) WHERE is_deleted = false;
CREATE INDEX idx_reports_patient_name_fulltext ON reports USING gin(to_tsvector('simple', patient_name)) WHERE is_deleted = false;

-- 复合索引（常用查询组合）
CREATE INDEX idx_reports_exam_date_type ON reports(exam_date DESC, exam_type) WHERE is_deleted = false;

-- 触发器：自动更新 updated_at
CREATE TRIGGER update_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**字段说明**:
- **患者信息**: 患者ID、姓名、年龄、性别（嵌入式设计，Phase 1足够）
- **检查信息**: 检查日期、类型、描述、科室
- **报告内容**: 完整报告文本（最重要字段）
- **结构化字段**: findings（发现）、diagnosis（诊断）、impression（印象）
- **ICD编码**: JSONB格式存储，灵活扩展
- **数据来源**: 追踪数据来源（Excel导入、手动输入、API）

**Phase 1 设计决策**:
- ✅ 患者信息直接嵌入（不需要单独患者表）
- ✅ 不存储DICOM影像引用（Phase 2添加）
- ✅ 全文搜索索引支持快速内容检索
- ✅ 软删除机制（is_deleted字段）

---

### 3. ai_annotations (AI标记表)

**用途**: 存储Ollama AI对报告的分析和标记结果

```sql
CREATE TABLE ai_annotations (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,

    -- 用户提示词
    user_prompt TEXT NOT NULL,

    -- 标记类型
    annotation_type VARCHAR(50) NOT NULL CHECK (
        annotation_type IN ('highlight', 'classification', 'extraction', 'scoring', 'custom')
    ),

    -- AI分析结果（JSON格式，灵活存储不同类型的标记）
    content JSONB NOT NULL,

    -- 置信度（可选）
    confidence DECIMAL(3, 2) CHECK (confidence >= 0 AND confidence <= 1),

    -- 原始LLM响应（用于调试和审计）
    raw_response TEXT,

    -- LLM配置信息
    model_name VARCHAR(50) DEFAULT 'qwen2.5:7b',
    model_temperature DECIMAL(3, 2) DEFAULT 0.7,

    -- 是否被用户编辑过
    is_edited BOOLEAN DEFAULT false,
    edited_at TIMESTAMP WITH TIME ZONE,

    -- 创建者
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_ai_annotations_report ON ai_annotations(report_id);
CREATE INDEX idx_ai_annotations_type ON ai_annotations(annotation_type);
CREATE INDEX idx_ai_annotations_created ON ai_annotations(created_at DESC);

-- JSONB字段索引（支持JSON查询）
CREATE INDEX idx_ai_annotations_content_gin ON ai_annotations USING gin(content);

-- 触发器
CREATE TRIGGER update_ai_annotations_updated_at
    BEFORE UPDATE ON ai_annotations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**字段说明**:
- `report_id`: 关联的报告ID（外键，级联删除）
- `user_prompt`: 用户输入的提示词（记录用户意图）
- `annotation_type`: 标记类型（高亮、分类、提取、评分、自定义）
- `content`: JSONB格式的分析结果（灵活存储各种结构）
- `confidence`: AI的置信度（0-1）
- `raw_response`: LLM的原始响应（调试用）
- `model_name`: 使用的模型名称
- `is_edited`: 是否被用户手动编辑

**content字段结构示例**:

```json
// highlight类型
{
  "highlights": [
    {
      "text": "双肺纹理增多",
      "start": 15,
      "end": 22,
      "reason": "关键发现"
    }
  ]
}

// classification类型
{
  "category": "normal",
  "confidence": 0.92,
  "reasoning": "未见明显实质性病变"
}

// extraction类型
{
  "findings": ["肺纹理增多", "心影不大"],
  "measurements": [
    {"item": "心胸比例", "value": "0.48", "unit": "ratio"}
  ],
  "locations": ["双肺", "心脏"]
}

// scoring类型
{
  "score": 3,
  "severity": "mild",
  "reasoning": "轻度异常，无严重病变"
}
```

---

### 4. projects (项目表)

**用途**: 组织和管理筛选出的报告数据

```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,

    -- 项目标签（JSONB数组，灵活扩展）
    tags JSONB DEFAULT '[]'::jsonb,

    -- 项目状态
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed')),

    -- 创建者
    created_by INTEGER NOT NULL REFERENCES users(id),

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- 约束
    CONSTRAINT chk_project_name_length CHECK (LENGTH(name) >= 2)
);

-- 索引
CREATE INDEX idx_projects_created_by ON projects(created_by) WHERE is_deleted = false;
CREATE INDEX idx_projects_status ON projects(status) WHERE is_deleted = false;
CREATE INDEX idx_projects_created_at ON projects(created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_projects_name ON projects(name) WHERE is_deleted = false;

-- JSONB标签索引
CREATE INDEX idx_projects_tags_gin ON projects USING gin(tags);

-- 触发器
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**字段说明**:
- `name`: 项目名称（必填）
- `description`: 项目描述
- `tags`: 项目标签（JSONB数组，如 `["肺部研究", "2024Q1"]`）
- `status`: 项目状态（active活跃, archived归档, completed完成）
- `created_by`: 项目创建者

**使用场景**:
- 研究人员创建项目"肺部CT筛查研究"
- 将符合条件的报告添加到项目
- 批量导出项目中的所有报告数据
- 追踪研究项目的进展

---

### 5. project_reports (项目-报告关联表)

**用途**: 多对多关系，一个项目包含多个报告，一个报告可以属于多个项目

```sql
CREATE TABLE project_reports (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,

    -- 添加到项目的时间和操作者
    added_by INTEGER REFERENCES users(id),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- 备注（可选）
    notes TEXT,

    -- 唯一约束：同一报告不能重复添加到同一项目
    CONSTRAINT uq_project_report UNIQUE (project_id, report_id)
);

-- 索引
CREATE INDEX idx_project_reports_project ON project_reports(project_id);
CREATE INDEX idx_project_reports_report ON project_reports(report_id);
CREATE INDEX idx_project_reports_added_at ON project_reports(added_at DESC);

-- 复合索引（优化常用查询）
CREATE INDEX idx_project_reports_project_added ON project_reports(project_id, added_at DESC);
```

**字段说明**:
- `project_id`: 项目ID（外键，级联删除）
- `report_id`: 报告ID（外键，级联删除）
- `added_by`: 添加操作的用户
- `added_at`: 添加时间
- `notes`: 备注信息（为什么将此报告加入项目）

**关系约束**:
- 唯一约束保证同一报告不会重复添加到同一项目
- 级联删除：删除项目或报告时，自动删除关联记录

---

## 数据库初始化脚本

### 完整建表脚本

```sql
-- =====================================================
-- Phase 1 数据库初始化脚本
-- 影像数据平台 - AI辅助报告筛选系统
-- =====================================================

-- 启用UUID扩展（如果需要）
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- 1. 通用触发器函数
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 2. 创建表
-- =====================================================

-- 2.1 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'researcher' CHECK (role IN ('admin', 'researcher')),
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email) WHERE is_active = true;
CREATE INDEX idx_users_role ON users(role);

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 2.2 报告表
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    patient_name VARCHAR(100),
    patient_age INTEGER,
    patient_gender VARCHAR(10) CHECK (patient_gender IN ('M', 'F', 'Other', 'Unknown')),
    exam_date DATE NOT NULL,
    exam_type VARCHAR(50) NOT NULL,
    exam_description TEXT,
    department VARCHAR(100),
    report_content TEXT NOT NULL,
    findings TEXT,
    diagnosis TEXT,
    impression TEXT,
    icd_codes JSONB,
    source VARCHAR(50) DEFAULT 'import',
    source_reference VARCHAR(200),
    imported_by INTEGER REFERENCES users(id),
    imported_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_reports_patient_id ON reports(patient_id) WHERE is_deleted = false;
CREATE INDEX idx_reports_patient_name ON reports(patient_name) WHERE is_deleted = false;
CREATE INDEX idx_reports_exam_date ON reports(exam_date DESC) WHERE is_deleted = false;
CREATE INDEX idx_reports_exam_type ON reports(exam_type) WHERE is_deleted = false;
CREATE INDEX idx_reports_department ON reports(department) WHERE is_deleted = false;
CREATE INDEX idx_reports_content_fulltext ON reports USING gin(to_tsvector('simple', report_content)) WHERE is_deleted = false;
CREATE INDEX idx_reports_patient_name_fulltext ON reports USING gin(to_tsvector('simple', patient_name)) WHERE is_deleted = false;
CREATE INDEX idx_reports_exam_date_type ON reports(exam_date DESC, exam_type) WHERE is_deleted = false;

CREATE TRIGGER update_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 2.3 AI标记表
CREATE TABLE ai_annotations (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    user_prompt TEXT NOT NULL,
    annotation_type VARCHAR(50) NOT NULL CHECK (
        annotation_type IN ('highlight', 'classification', 'extraction', 'scoring', 'custom')
    ),
    content JSONB NOT NULL,
    confidence DECIMAL(3, 2) CHECK (confidence >= 0 AND confidence <= 1),
    raw_response TEXT,
    model_name VARCHAR(50) DEFAULT 'qwen2.5:7b',
    model_temperature DECIMAL(3, 2) DEFAULT 0.7,
    is_edited BOOLEAN DEFAULT false,
    edited_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_annotations_report ON ai_annotations(report_id);
CREATE INDEX idx_ai_annotations_type ON ai_annotations(annotation_type);
CREATE INDEX idx_ai_annotations_created ON ai_annotations(created_at DESC);
CREATE INDEX idx_ai_annotations_content_gin ON ai_annotations USING gin(content);

CREATE TRIGGER update_ai_annotations_updated_at
    BEFORE UPDATE ON ai_annotations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 2.4 项目表
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    tags JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed')),
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_project_name_length CHECK (LENGTH(name) >= 2)
);

CREATE INDEX idx_projects_created_by ON projects(created_by) WHERE is_deleted = false;
CREATE INDEX idx_projects_status ON projects(status) WHERE is_deleted = false;
CREATE INDEX idx_projects_created_at ON projects(created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_projects_name ON projects(name) WHERE is_deleted = false;
CREATE INDEX idx_projects_tags_gin ON projects USING gin(tags);

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 2.5 项目-报告关联表
CREATE TABLE project_reports (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    report_id INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    added_by INTEGER REFERENCES users(id),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    CONSTRAINT uq_project_report UNIQUE (project_id, report_id)
);

CREATE INDEX idx_project_reports_project ON project_reports(project_id);
CREATE INDEX idx_project_reports_report ON project_reports(report_id);
CREATE INDEX idx_project_reports_added_at ON project_reports(added_at DESC);
CREATE INDEX idx_project_reports_project_added ON project_reports(project_id, added_at DESC);

-- =====================================================
-- 3. 初始数据
-- =====================================================

-- 创建默认管理员账号（密码: Admin@123456）
INSERT INTO users (email, password_hash, full_name, role) VALUES
('admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIpVO7fUOu', '系统管理员', 'admin');

-- =====================================================
-- 4. 视图（可选）
-- =====================================================

-- 报告统计视图
CREATE OR REPLACE VIEW v_report_statistics AS
SELECT
    COUNT(*) as total_reports,
    COUNT(DISTINCT patient_id) as unique_patients,
    COUNT(DISTINCT exam_type) as exam_types,
    MIN(exam_date) as earliest_exam,
    MAX(exam_date) as latest_exam
FROM reports
WHERE is_deleted = false;

-- 项目统计视图
CREATE OR REPLACE VIEW v_project_statistics AS
SELECT
    p.id as project_id,
    p.name as project_name,
    p.status,
    COUNT(pr.report_id) as report_count,
    COUNT(DISTINCT r.patient_id) as patient_count,
    MAX(pr.added_at) as last_updated
FROM projects p
LEFT JOIN project_reports pr ON p.id = pr.project_id
LEFT JOIN reports r ON pr.report_id = r.id
WHERE p.is_deleted = false AND (r.is_deleted = false OR r.id IS NULL)
GROUP BY p.id, p.name, p.status;

-- AI标记统计视图
CREATE OR REPLACE VIEW v_ai_annotation_statistics AS
SELECT
    annotation_type,
    COUNT(*) as annotation_count,
    COUNT(DISTINCT report_id) as annotated_reports,
    AVG(confidence) as avg_confidence
FROM ai_annotations
GROUP BY annotation_type;

-- =====================================================
-- 5. 完成信息
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Phase 1 数据库初始化完成';
    RAISE NOTICE '📊 创建了5张核心表：users, reports, ai_annotations, projects, project_reports';
    RAISE NOTICE '🔑 创建了默认管理员账号：admin@example.com / Admin@123456';
    RAISE NOTICE '📈 创建了3个统计视图：v_report_statistics, v_project_statistics, v_ai_annotation_statistics';
END $$;
```

---

## 常用查询示例

### 1. 报告搜索查询

```sql
-- 全文搜索报告内容
SELECT
    id,
    patient_id,
    patient_name,
    exam_date,
    exam_type,
    ts_rank(to_tsvector('simple', report_content), to_tsquery('simple', '肺部 & 异常')) as rank
FROM reports
WHERE
    to_tsvector('simple', report_content) @@ to_tsquery('simple', '肺部 & 异常')
    AND is_deleted = false
ORDER BY rank DESC, exam_date DESC
LIMIT 50;

-- 多条件组合查询
SELECT *
FROM reports
WHERE
    is_deleted = false
    AND exam_date BETWEEN '2024-01-01' AND '2024-12-31'
    AND exam_type = 'CT'
    AND department = '放射科'
    AND (patient_name LIKE '%张%' OR patient_id LIKE '%123%')
ORDER BY exam_date DESC;
```

### 2. AI标记相关查询

```sql
-- 获取报告的所有AI标记
SELECT
    a.id,
    a.annotation_type,
    a.user_prompt,
    a.content,
    a.confidence,
    a.created_at,
    u.full_name as annotated_by
FROM ai_annotations a
LEFT JOIN users u ON a.created_by = u.id
WHERE a.report_id = 123
ORDER BY a.created_at DESC;

-- 查找被分类为"异常"的报告
SELECT DISTINCT r.*
FROM reports r
JOIN ai_annotations a ON r.id = a.report_id
WHERE
    a.annotation_type = 'classification'
    AND a.content->>'category' = 'abnormal'
    AND r.is_deleted = false;

-- AI标记统计
SELECT
    annotation_type,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    MIN(created_at) as first_annotation,
    MAX(created_at) as last_annotation
FROM ai_annotations
GROUP BY annotation_type;
```

### 3. 项目管理查询

```sql
-- 获取项目详情和报告列表
SELECT
    p.id as project_id,
    p.name as project_name,
    r.id as report_id,
    r.patient_id,
    r.patient_name,
    r.exam_date,
    r.exam_type,
    pr.added_at
FROM projects p
JOIN project_reports pr ON p.id = pr.project_id
JOIN reports r ON pr.report_id = r.id
WHERE
    p.id = 1
    AND p.is_deleted = false
    AND r.is_deleted = false
ORDER BY pr.added_at DESC;

-- 项目报告数量统计
SELECT
    p.id,
    p.name,
    COUNT(pr.report_id) as report_count,
    COUNT(DISTINCT r.patient_id) as patient_count
FROM projects p
LEFT JOIN project_reports pr ON p.id = pr.project_id
LEFT JOIN reports r ON pr.report_id = r.id AND r.is_deleted = false
WHERE p.is_deleted = false
GROUP BY p.id, p.name;
```

### 4. 数据统计查询

```sql
-- 总体数据统计
SELECT
    (SELECT COUNT(*) FROM reports WHERE is_deleted = false) as total_reports,
    (SELECT COUNT(DISTINCT patient_id) FROM reports WHERE is_deleted = false) as unique_patients,
    (SELECT COUNT(*) FROM ai_annotations) as total_annotations,
    (SELECT COUNT(*) FROM projects WHERE is_deleted = false) as total_projects;

-- 按检查类型统计
SELECT
    exam_type,
    COUNT(*) as count,
    COUNT(DISTINCT patient_id) as unique_patients
FROM reports
WHERE is_deleted = false
GROUP BY exam_type
ORDER BY count DESC;

-- 按月份统计报告数量
SELECT
    DATE_TRUNC('month', exam_date) as month,
    COUNT(*) as report_count
FROM reports
WHERE is_deleted = false AND exam_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', exam_date)
ORDER BY month;
```

---

## 数据迁移策略 (Phase 1 → Phase 2)

### Phase 2 需要添加的表

```sql
-- 患者表（从reports中提取）
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) UNIQUE NOT NULL,
    patient_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(10),
    -- 更多患者信息
);

-- 检查表（DICOM Study level）
CREATE TABLE studies (
    id SERIAL PRIMARY KEY,
    study_instance_uid VARCHAR(64) UNIQUE NOT NULL,
    patient_id INTEGER REFERENCES patients(id),
    study_date DATE,
    modality VARCHAR(10),
    -- DICOM标准字段
);

-- 影像表
CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    study_id INTEGER REFERENCES studies(id),
    sop_instance_uid VARCHAR(64) UNIQUE NOT NULL,
    file_path VARCHAR(500),
    -- 影像元数据
);
```

### 迁移脚本示例

```sql
-- Phase 1 → Phase 2 数据迁移

-- 1. 提取患者数据到患者表
INSERT INTO patients (patient_id, patient_name, gender)
SELECT DISTINCT
    patient_id,
    patient_name,
    patient_gender
FROM reports
WHERE is_deleted = false
ON CONFLICT (patient_id) DO NOTHING;

-- 2. 更新reports表关联患者ID
ALTER TABLE reports ADD COLUMN patient_fk INTEGER REFERENCES patients(id);

UPDATE reports r
SET patient_fk = p.id
FROM patients p
WHERE r.patient_id = p.patient_id;

-- 3. 逐步移除冗余字段（可选）
-- ALTER TABLE reports DROP COLUMN patient_name;
-- ALTER TABLE reports DROP COLUMN patient_gender;
```

---

## 性能优化建议

### 1. 查询优化

```sql
-- 使用EXPLAIN ANALYZE分析查询性能
EXPLAIN ANALYZE
SELECT * FROM reports
WHERE exam_type = 'CT' AND exam_date > '2024-01-01';

-- 为高频查询创建物化视图
CREATE MATERIALIZED VIEW mv_recent_reports AS
SELECT *
FROM reports
WHERE exam_date >= CURRENT_DATE - INTERVAL '30 days'
  AND is_deleted = false;

CREATE INDEX idx_mv_recent_reports_exam_date ON mv_recent_reports(exam_date DESC);

-- 定期刷新物化视图
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_recent_reports;
```

### 2. 索引优化

```sql
-- 分析索引使用情况
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- 删除未使用的索引
-- SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0;
```

### 3. 分区表（大数据量时）

```sql
-- 如果reports表超过1000万条记录，考虑按日期分区

CREATE TABLE reports_partitioned (
    -- 同reports表结构
) PARTITION BY RANGE (exam_date);

CREATE TABLE reports_2024_q1 PARTITION OF reports_partitioned
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE reports_2024_q2 PARTITION OF reports_partitioned
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');
```

---

## 备份和恢复

### 备份策略

```bash
# 每日全量备份
pg_dump -U postgres -d imagedb > backup_$(date +%Y%m%d).sql

# 只备份schema
pg_dump -U postgres -d imagedb --schema-only > schema.sql

# 只备份数据
pg_dump -U postgres -d imagedb --data-only > data.sql

# 备份特定表
pg_dump -U postgres -d imagedb -t reports -t ai_annotations > critical_tables.sql
```

### 恢复

```bash
# 恢复完整数据库
psql -U postgres -d imagedb < backup_20241201.sql

# 只恢复schema
psql -U postgres -d imagedb < schema.sql

# 只恢复数据
psql -U postgres -d imagedb < data.sql
```

---

## 附录

### A. 数据类型说明

| PostgreSQL类型 | 说明 | 使用场景 |
|--------------|------|---------|
| SERIAL | 自增整数 | 主键ID |
| VARCHAR(n) | 可变长度字符串 | 邮箱、姓名、短文本 |
| TEXT | 无限长度文本 | 报告内容、长文本 |
| JSONB | 二进制JSON | AI标记内容、标签数组 |
| TIMESTAMP WITH TIME ZONE | 带时区时间戳 | 创建时间、更新时间 |
| BOOLEAN | 布尔值 | 是否删除、是否激活 |
| DECIMAL(p,s) | 精确小数 | 置信度、评分 |

### B. Phase 1 vs Phase 2 对比

| 维度 | Phase 1 | Phase 2 |
|-----|---------|---------|
| 表数量 | 5张 | 11+张 |
| 核心功能 | 报告分析+项目管理 | +影像管理+系统集成 |
| 数据规模 | 10万+报告 | 100万+报告+影像 |
| 存储需求 | ~10GB (仅文本) | 10TB+ (含影像) |
| 查询复杂度 | 简单-中等 | 中等-复杂 |
| 性能优化 | 基础索引 | 分区+缓存+优化 |

---

**文档版本历史**:

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v2.0.0 | 2024-12-01 | Phase 1重构：从11表简化为5表 |
| v1.0.0 | 2024-12-01 | 初始版本（完整平台11表设计） |

---

**审批记录**:

| 角色 | 姓名 | 日期 |
|------|------|------|
| 数据库架构师 | | |
| 技术负责人 | | |
| 开发负责人 | | |
