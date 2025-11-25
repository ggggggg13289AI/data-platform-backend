# 数据库备份与恢复指南

完整的数据库备份与恢复工具，支持 Django JSON 和 PostgreSQL SQL 两种格式。

## 快速开始

### 基础备份（推荐）
```bash
# Django JSON 格式备份（默认）
python scripts/backup_database.py

# 压缩备份（节省空间）
python scripts/backup_database.py --compress
```

### 基础恢复
```bash
# 从备份恢复（会要求确认）
python scripts/restore_database.py backups/backup_20250125_143000.json

# 跳过确认（谨慎使用！）
python scripts/restore_database.py backups/backup_20250125_143000.json --force
```

## 备份模式对比

### Django 模式（默认）
**优点**：
- ✅ 跨数据库兼容（可在不同数据库间迁移）
- ✅ 包含完整的数据关系
- ✅ JSON 格式，易于版本控制和查看
- ✅ 无需 PostgreSQL 客户端工具

**缺点**：
- ⚠️ 大型数据库备份较慢
- ⚠️ 文件较大（建议启用压缩）

**适用场景**：
- 开发环境数据迁移
- 版本控制中的测试数据
- 跨环境数据同步

### PostgreSQL 模式
**优点**：
- ✅ 备份速度快
- ✅ PostgreSQL 原生格式，效率高
- ✅ 支持增量备份（配合 pg_dump 选项）
- ✅ 适合大型数据库

**缺点**：
- ⚠️ 需要安装 PostgreSQL 客户端工具
- ⚠️ 仅限 PostgreSQL 数据库
- ⚠️ SQL 格式，不易人工查看

**适用场景**：
- 生产环境定期备份
- 大型数据库备份
- 灾难恢复准备

## 完整使用示例

### 备份命令示例

```bash
# 1. 基础 JSON 备份
python scripts/backup_database.py

# 2. PostgreSQL SQL 备份
python scripts/backup_database.py --mode postgres

# 3. 压缩备份（推荐用于生产环境）
python scripts/backup_database.py --mode postgres --compress

# 4. 自定义输出目录
python scripts/backup_database.py --output /path/to/backups

# 5. 保留最近 7 个备份，自动删除旧的
python scripts/backup_database.py --compress --keep-last 7

# 6. 完整生产环境备份（推荐）
python scripts/backup_database.py \
  --mode postgres \
  --compress \
  --output backups/production \
  --keep-last 30
```

### 恢复命令示例

```bash
# 1. 从 JSON 备份恢复
python scripts/restore_database.py backups/backup_20250125_143000.json

# 2. 从压缩备份恢复
python scripts/restore_database.py backups/backup_20250125_143000.json.gz

# 3. 从 SQL 备份恢复
python scripts/restore_database.py backups/backup_20250125_143000.sql

# 4. 干跑模式（不实际恢复，只显示信息）
python scripts/restore_database.py backups/backup_20250125_143000.json --dry-run

# 5. 强制恢复（跳过确认）
python scripts/restore_database.py backups/backup_20250125_143000.json --force
```

## 自动化备份

### Windows 任务计划程序

创建定时任务每天凌晨 2 点备份：

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每天 02:00
4. 操作：启动程序
   - 程序：`python`
   - 参数：`scripts/backup_database.py --compress --keep-last 30`
   - 起始于：`D:\00_Chen\spider\image_data_platform\backend_django`

### Linux Cron 任务

编辑 crontab：
```bash
crontab -e
```

添加定时任务：
```cron
# 每天凌晨 2 点备份，保留最近 30 天
0 2 * * * cd /path/to/backend_django && python scripts/backup_database.py --compress --keep-last 30

# 每周日凌晨 3 点创建完整 PostgreSQL 备份
0 3 * * 0 cd /path/to/backend_django && python scripts/backup_database.py --mode postgres --compress --output backups/weekly
```

## 备份文件命名规则

备份文件自动添加时间戳：
```
backup_YYYYMMDD_HHMMSS.扩展名

示例：
backup_20250125_143052.json       # Django JSON 备份
backup_20250125_143052.json.gz    # Django JSON 压缩备份
backup_20250125_143052.sql        # PostgreSQL SQL 备份
backup_20250125_143052.sql.gz     # PostgreSQL SQL 压缩备份
```

## 安全建议

### ⚠️ 重要安全提醒

1. **备份文件包含敏感数据**
   - 用户信息
   - 医疗影像数据
   - 系统配置

   ➡️ **必须**加密存储或限制访问权限

2. **恢复操作不可逆**
   - 恢复会覆盖现有数据
   - 务必在恢复前创建当前数据备份

   ➡️ 使用 `--dry-run` 先测试

3. **定期测试恢复流程**
   - 备份无法恢复等于没有备份
   - 建议每月测试一次恢复流程

   ➡️ 使用测试环境验证

### 最佳实践

#### 3-2-1 备份策略
- **3** 份数据副本
- **2** 种不同介质（本地硬盘 + 云存储）
- **1** 份异地存储

#### 备份频率建议
- **开发环境**：每天一次
- **测试环境**：每天一次
- **生产环境**：
  - 增量备份：每 4 小时
  - 完整备份：每天一次
  - 周备份：每周日
  - 月备份：每月 1 号

#### 保留策略建议
- 日备份：保留 30 天
- 周备份：保留 12 周
- 月备份：保留 12 月
- 年备份：永久保留

## 故障排除

### PostgreSQL 模式问题

**问题**：`pg_dump command not found`

**解决方案**：
1. 安装 PostgreSQL 客户端工具
2. Windows：https://www.postgresql.org/download/windows/
3. Linux：`sudo apt-get install postgresql-client`
4. macOS：`brew install postgresql`

**问题**：`psql: FATAL: password authentication failed`

**解决方案**：
检查 `.env` 文件中的数据库密码配置：
```env
DB_PASSWORD=your_password_here
```

### Django 模式问题

**问题**：`CommandError: Unable to serialize database`

**解决方案**：
某些数据类型可能无法序列化，尝试：
```bash
# 排除特定应用
python manage.py dumpdata --exclude auth --exclude sessions
```

**问题**：`IntegrityError` during restore

**解决方案**：
数据库约束冲突，建议：
1. 先清空数据库：`python manage.py flush`
2. 再恢复备份

## 高级用法

### 仅备份特定应用

```bash
# Django 模式：备份特定应用
python manage.py dumpdata study report > backups/apps_only.json
```

### 排除大型数据

```bash
# Django 模式：排除文件上传等大型数据
python manage.py dumpdata --exclude study.medicalimage > backups/no_images.json
```

### 创建可移植的测试数据

```bash
# 备份测试数据
python scripts/backup_database.py --output tests/fixtures

# 在测试中加载
python manage.py loaddata tests/fixtures/backup_20250125_143052.json
```

## 监控和日志

### 备份成功验证

备份脚本输出摘要信息：
```
============================================================
Backup Completed Successfully
============================================================
File:     backup_20250125_143052.json.gz
Size:     12.34 MB
Location: D:\...\backups\backup_20250125_143052.json.gz
============================================================
```

### 建议监控指标

1. **备份文件大小**：异常增长或减少
2. **备份执行时间**：超过预期时长
3. **备份文件数量**：确认自动清理正常
4. **磁盘空间使用**：避免空间耗尽

### 日志记录

建议将备份日志重定向到文件：
```bash
# Windows PowerShell
python scripts/backup_database.py --compress 2>&1 | Tee-Object -FilePath logs/backup.log -Append

# Linux/macOS
python scripts/backup_database.py --compress 2>&1 | tee -a logs/backup.log
```

## 性能优化

### 压缩率对比

| 格式 | 原始大小 | 压缩后 | 压缩率 | 备份时间 |
|------|---------|--------|--------|---------|
| JSON | 100 MB | 15 MB | 85% | ~30s |
| SQL | 80 MB | 12 MB | 85% | ~20s |

**建议**：生产环境始终启用 `--compress`

### 大型数据库优化

对于 >10GB 数据库：
1. 使用 PostgreSQL 模式
2. 启用压缩
3. 考虑增量备份
4. 使用专业备份工具（如 pgBackRest）

## 相关文档

- [Django 数据库文档](https://docs.djangoproject.com/en/4.2/topics/db/)
- [PostgreSQL 备份文档](https://www.postgresql.org/docs/current/backup.html)
- [项目 README](../README.md)

## 支持

遇到问题？
1. 检查本文档的"故障排除"章节
2. 查看 `debug.log` 日志
3. 提交 Issue 到项目仓库
