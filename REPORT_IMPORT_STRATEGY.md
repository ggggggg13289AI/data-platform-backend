# Report Import Strategy - Legacy Data Migration

## 概述 (Overview)

本文档描述如何将 `data.db` 中的 `one_page_text_report` 表中的数据智能地导入到新的报告管理系统中，并解决 `id='unknown'` 导致的多笔报告问题。

## 问题分析 (Problem Analysis)

### 数据现状
- **总记录数**: 64,734 条
- **id='unknown' 记录**: 21,959 条 (33.9%) - 来自多种 API 端点
- **id!=unknown 记录**: 42,775 条 (66.1%) - 医学影像报告

### 数据来源分类

#### 1. 医学影像报告 (id != 'unknown')
- **来源**: `pt.get_resource` API 返回的 `image` key 数据
- **类型**: MR(MRI), CR(X-Ray), CT, US(超声), MG(乳房摄影), etc.
- **特点**:
  - 有具体的报告ID
  - 包含诊断报告文本
  - 每条记录是一个独立的完整报告
- **处理方式**: 直接导入，使用原有的 id 和 uid

#### 2. 系统记录 (id = 'unknown')
来自各种 API 端点的数据，格式：`{chr_no}_{api_endpoint}_{timestamp}_{hash}`

**子类型**:
- **pt.get** - 患者基本信息 (JSON格式，包含患者个人资料)
- **pt.cross_get** - 患者跨域信息
- **allergy.list** - 过敏信息
- **lab.list** - 实验室检查结果
- **hcheckup.list** - 健康检查列表
- **vitals.list** - 生命体征数据
- **pt.dnr.list** - DNR (不复苏) 指示

**特点**:
- id 字段为 'unknown'，标记为系统API返回的数据
- 包含结构化数据（通常是JSON）
- 一条记录对应一个患者的一类信息快照
- MOD 字段指示数据来源 API

**处理方式**:
- 需要根据 MOD 字段智能分类
- 选择性导入（可跳过纯患者信息）
- 保留元数据便于追踪

## 导入策略 (Import Strategy)

### 1. 数据分类 (Data Classification)

根据 `id` 和 `mod` 字段确定报告类型：

```python
# Medical Imaging (id != 'unknown')
id=21008220003, mod=MR      → type='MRI'
id=21204270027, mod=CT      → type='CT'
id=11002020569, mod=CR      → type='XRay'

# System Data (id = 'unknown')
id=unknown, mod=pt.get      → type='patient_info' (可选跳过)
id=unknown, mod=allergy.*   → type='allergy'
id=unknown, mod=lab.*       → type='laboratory'
id=unknown, mod=vitals.*    → type='vitals'
id=unknown, mod=hcheckup.*  → type='health_checkup'
```

### 2. UID 处理 (UID Handling)

**对于 id != 'unknown'**:
- 使用现有 UID（已经是格式化的）
- 示例: `76a9b5152d0344d4ba458eabc459774b`

**对于 id = 'unknown'**:
- 使用现有 UID（已包含患者号和API端点信息）
- 示例: `01055045_pt.get_1762241459563_ukebfibty`
- 报告ID: UID的前32字符

### 3. 去重处理 (Deduplication)

- **内容哈希**: SHA256(content) 确保完全重复的记录不会被重复导入
- **时间戳比较**: 相同内容时，保留 verified_at 时间最晚的版本
- **版本管理**: 内容不同时自动创建新版本记录

### 4. 日期处理 (Date Handling)

支持多种日期格式：
- ISO 8601: `2025-11-04T07:30:47.377Z`
- 标准日期: `2025-11-04`
- 日期时间: `2025-11-04 07:30:47`

### 5. 元数据保留 (Metadata Preservation)

在导入时保留原始数据追踪信息：
```python
metadata = {
    'legacy_id': 'unknown',        # 原始ID
    'legacy_uid': '...',           # 原始UID
    'legacy_import': True,         # 标记为导入数据
}
```

## 实现方案 (Implementation)

### 核心变更

#### 1. report_service.py 增强

**新增方法**:
- `_parse_datetime()` - 智能日期解析
- `_determine_report_type()` - 根据 MOD 字段确定报告类型
- 增强的 `migrate_from_legacy_db()` - 完整的导入逻辑

**特性**:
- 批处理支持（可设置批大小）
- 可选跳过患者信息记录
- 详细的统计数据
- 错误处理和日志记录

#### 2. 管理命令 (Django Management Command)

创建 `migrate_legacy_reports.py` 命令

**使用方式**:
```bash
# 默认导入
python manage.py migrate_legacy_reports

# 跳过患者信息，只导入报告
python manage.py migrate_legacy_reports --skip-patient-info

# 指定数据库路径
python manage.py migrate_legacy_reports --db-path /path/to/data.db

# 设置批处理大小
python manage.py migrate_legacy_reports --batch-size 1000

# 详细输出
python manage.py migrate_legacy_reports --verbose
```

## 执行步骤 (Execution Steps)

### 1. 准备阶段 (Preparation)

```bash
# 确保虚拟环境已激活
source .venv/Scripts/activate

# 确保 data.db 存在于项目根目录
ls -la data.db
```

### 2. 执行导入 (Execution)

**选项 A: 导入所有数据（包括患者信息）**
```bash
python manage.py migrate_legacy_reports
```

**选项 B: 只导入报告，跳过患者信息**
```bash
python manage.py migrate_legacy_reports --skip-patient-info
```

### 3. 验证结果 (Verification)

```bash
# 查看导入的报告数量
python manage.py shell
>>> from studies.models import Report
>>> Report.objects.count()
>>> Report.objects.values('report_type').annotate(count=Count('id'))

# 查看报告类型分布
>>> from django.db.models import Count
>>> Report.objects.values('report_type').annotate(count=Count('id')).order_by('-count')

# 查看示例报告
>>> Report.objects.filter(is_latest=True).first()
```

## 报告类型映射 (Report Type Mapping)

### 医学影像类型 (Medical Imaging)
| MOD | 英文 | 中文 |
|-----|------|------|
| MR | MRI | 核磁共振 |
| CR | XRay | X光 |
| CT | CT | 计算机断层扫描 |
| US | Ultrasound | 超声 |
| MG | Mammography | 乳房摄影 |
| OT | Other | 其他 |
| RF | Fluoroscopy | 透视 |

### 系统数据类型 (System Data)
| MOD 前缀 | 报告类型 | 中文 |
|---------|---------|------|
| pt.get | patient_info | 患者信息 |
| allergy | allergy | 过敏 |
| lab | laboratory | 实验室检查 |
| vital | vitals | 生命体征 |
| hcheckup | health_checkup | 健康检查 |

## 预期结果 (Expected Results)

### 导入统计
- 预期导入成功率: >99%
- 预期创建新报告: ~64,000 条（或更少，取决于去重）
- 预期更新记录: ~1,000 条（重复导入处理）
- 预期去重记录: ~2,000 条

### 数据质量
- 所有报告都会有唯一的 uid 和 report_id
- 所有报告都会有对应的版本记录
- 相同内容的报告会被自动去重
- 所有报告都可通过 API 搜索和检索

## 故障排除 (Troubleshooting)

### 问题 1: 数据库文件不存在
```
ERROR: Database file not found: ./data.db
```
**解决**: 确保 data.db 在项目根目录或指定正确的路径
```bash
python manage.py migrate_legacy_reports --db-path /correct/path/to/data.db
```

### 问题 2: 导入过程中出现错误
```
ERROR: Error migrating record: ...
```
**解决**: 使用 `--verbose` 标志获取详细的错误信息
```bash
python manage.py migrate_legacy_reports --verbose
```

### 问题 3: 导入速度太慢
**解决**: 增加批处理大小
```bash
python manage.py migrate_legacy_reports --batch-size 2000
```

## API 使用示例 (API Usage Examples)

导入完成后，可以通过以下 API 端点访问报告：

### 搜索报告
```bash
GET /api/v1/reports/search?q=MRI&limit=20
```

### 获取最新报告
```bash
GET /api/v1/reports/latest?limit=10
```

### 获取特定报告
```bash
GET /api/v1/reports/{report_id}
```

### 查看报告历史版本
```bash
GET /api/v1/reports/{report_id}/versions
```

## 技术细节 (Technical Details)

### 数据库索引
- `content_hash` + `verified_at`: 快速查询和去重
- `source_url` + `verified_at`: 来源追踪
- `is_latest` + `-verified_at`: 快速获取最新报告
- `report_type`: 按类型分类

### 事务安全
- 所有导入操作都在数据库事务中进行
- 如果发生错误，可以安全地重新运行
- 支持幂等操作（重复导入不会导致数据问题）

### 性能考虑
- 批处理大小: 500-2000 条（可根据系统资源调整）
- 预计导入时间: 2-5 分钟（取决于硬件和批大小）
- 内存占用: 相对较小，支持大规模数据导入

## 总结 (Summary)

这个导入策略：
1. ✅ 智能区分医学影像报告和系统数据
2. ✅ 自动处理 id='unknown' 的问题
3. ✅ 实现内容去重，避免重复数据
4. ✅ 保留完整的版本历史
5. ✅ 支持灵活的报告类型分类
6. ✅ 提供详细的导入统计和日志
7. ✅ 支持重新运行而不担心数据损坏
