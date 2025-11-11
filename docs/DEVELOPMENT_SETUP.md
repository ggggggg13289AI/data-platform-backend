# Development Setup Guide

**医疗影像管理系统 - Django 后端开发环境设置指南**

本文档提供完整的开发环境设置指南，适用于新加入团队的开发者或需要重新配置开发环境的情况。

---

## 📋 目录

1. [系统要求](#系统要求)
2. [UV 包管理器安装](#uv-包管理器安装)
3. [项目设置](#项目设置)
4. [数据库配置](#数据库配置)
5. [开发工具配置](#开发工具配置)
6. [运行开发服务器](#运行开发服务器)
7. [测试执行](#测试执行)
8. [常见开发任务](#常见开发任务)
9. [故障排除](#故障排除)

---

## 系统要求

### 必需软件

| 软件 | 版本要求 | 用途 |
|------|---------|------|
| **Python** | 3.11+ | 运行时环境 |
| **PostgreSQL** | 14+ | 主数据库 |
| **UV** | Latest | 包管理器 |
| **Git** | 2.x+ | 版本控制 |

### 推荐软件

| 软件 | 用途 |
|------|------|
| **VS Code** | 代码编辑器（推荐插件见下文） |
| **pgAdmin** | PostgreSQL 图形界面管理 |
| **Postman** / **Insomnia** | API 测试工具 |
| **Redis** | 缓存服务器（生产环境） |

### 操作系统

- ✅ Windows 10/11
- ✅ macOS 12+
- ✅ Linux (Ubuntu 20.04+, Debian, etc.)

---

## UV 包管理器安装

### 什么是 UV？

UV 是一个现代化的 Python 包管理器，提供：
- ⚡ 更快的依赖解析和安装速度
- 🔒 确定性的依赖锁定（uv.lock）
- 🎯 更好的虚拟环境管理
- 📦 与 pyproject.toml 的原生集成

> ⚠️ **重要**: 本项目使用 UV 而非 pip。请勿使用 pip 命令以避免环境污染。

### 安装 UV

**Windows (PowerShell)**:
```powershell
# 使用 pipx 安装（推荐）
pipx install uv

# 或使用 pip（仅此一次）
pip install uv

# 验证安装
uv --version
```

**macOS / Linux**:
```bash
# 使用官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip（仅此一次）
pip install uv

# 验证安装
uv --version
```

### UV 基础命令速查

```bash
# 依赖管理
uv sync                 # 同步依赖（首次设置或更新后）
uv add <package>        # 添加新依赖到 pyproject.toml
uv add --dev <package>  # 添加开发依赖
uv remove <package>     # 移除依赖
uv pip list             # 列出已安装包

# 虚拟环境
uv venv                 # 创建虚拟环境
uv venv --python 3.11   # 指定 Python 版本

# 运行命令
uv run python script.py # 在 UV 环境中运行脚本
uv run pytest           # 在 UV 环境中运行测试

# 锁定文件
uv lock                 # 更新 uv.lock
uv lock --upgrade       # 升级所有依赖到最新版本
```

---

## 项目设置

### 1. 克隆仓库

```bash
# 克隆项目
git clone https://github.com/your-org/image_data_platform.git
cd image_data_platform/backend_django

# 检查分支
git branch
git checkout main  # 或你的工作分支
```

### 2. 安装项目依赖

```bash
# UV 会自动创建虚拟环境并安装所有依赖
uv sync

# 预期输出：
# Resolved XX packages in XXms
# Downloaded XX packages in XXms
# Installed XX packages in XXms

# 验证安装
uv pip list
```

**输出示例**:
```
Package                 Version
----------------------- -------
Django                  5.0.0
django-ninja            1.3.0
psycopg2-binary         2.9.9
pydantic                2.5.0
...
```

### 3. 环境变量配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件（使用你喜欢的编辑器）
# Windows:
notepad .env
# macOS/Linux:
nano .env
```

**必需的环境变量** (`.env`):

```bash
# Django 配置
DEBUG=True                                    # 开发环境设为 True
DJANGO_SECRET_KEY=your-secret-key-here       # 生成方式见下文
ALLOWED_HOSTS=localhost,127.0.0.1            # 开发环境

# 数据库配置
DB_NAME=medical_imaging                       # 数据库名称
DB_USER=postgres                              # 数据库用户
DB_PASSWORD=your_password                     # 数据库密码
DB_HOST=localhost                             # 数据库主机
DB_PORT=5432                                  # PostgreSQL 默认端口

# 缓存配置
CACHE_BACKEND=locmem                          # 开发环境使用内存缓存
# CACHE_BACKEND=redis                         # 生产环境使用 Redis

# CORS 配置（前端开发）
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# 可选：性能监控
REQUEST_LOGGING=True                          # 启用请求计时日志
```

**生成 SECRET_KEY**:
```bash
# 使用 Python 生成安全的 SECRET_KEY
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 数据库配置

### 1. 安装 PostgreSQL

**Windows**:
```powershell
# 下载安装程序
# https://www.postgresql.org/download/windows/
# 运行安装程序，记住设置的密码
```

**macOS** (使用 Homebrew):
```bash
# 安装 PostgreSQL
brew install postgresql@14

# 启动 PostgreSQL 服务
brew services start postgresql@14

# 或手动启动
pg_ctl -D /usr/local/var/postgres start
```

**Linux** (Ubuntu/Debian):
```bash
# 安装 PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 切换到 postgres 用户
sudo -i -u postgres
```

### 2. 创建数据库和用户

```bash
# 连接到 PostgreSQL
psql -U postgres

# 在 psql 提示符中执行：
CREATE DATABASE medical_imaging ENCODING 'UTF8';
CREATE USER medical_user WITH PASSWORD 'your_secure_password';
ALTER ROLE medical_user SET client_encoding TO 'utf8';
ALTER ROLE medical_user SET timezone TO 'Asia/Taipei';  # 根据需要调整时区
GRANT ALL PRIVILEGES ON DATABASE medical_imaging TO medical_user;

# 验证
\l                              # 列出所有数据库
\du                             # 列出所有用户
\q                              # 退出 psql
```

### 3. 运行数据库迁移

```bash
# 检查迁移状态
python manage.py showmigrations

# 执行迁移（创建表结构）
python manage.py migrate

# 预期输出：
# Running migrations:
#   Applying contenttypes.0001_initial... OK
#   Applying studies.0001_initial... OK
#   ...
```

### 4. 验证数据库连接

```bash
# 使用 Django shell 测试数据库连接
uv run python manage.py shell

# 在 Python shell 中：
>>> from studies.models import Study
>>> Study.objects.count()
0
>>> exit()
```

### 5. （可选）加载测试数据

```bash
# 如果有 DuckDB 数据需要迁移
export DUCKDB_PATH=path/to/medical_imaging.duckdb
python scripts/migrate_from_duckdb.py

# 或创建测试数据
python manage.py shell
```

```python
# 在 Django shell 中创建测试数据
from studies.models import Study
from datetime import datetime

study = Study.objects.create(
    exam_id="TEST001",
    patient_name="测试患者",
    patient_gender="M",
    patient_age=45,
    exam_status="pending",
    exam_source="CT",
    exam_item="胸部CT",
    order_datetime=datetime.now()
)
print(f"Created test study: {study.exam_id}")
```

---

## 开发工具配置

### VS Code 推荐插件

```json
{
  "recommendations": [
    "ms-python.python",              // Python 支持
    "ms-python.vscode-pylance",      // 类型检查和智能提示
    "charliermarsh.ruff",            // 代码格式化和 linting
    "mtxr.sqltools",                 // SQL 工具
    "mtxr.sqltools-driver-pg",       // PostgreSQL 驱动
    "humao.rest-client",             // HTTP 请求测试
    "editorconfig.editorconfig"      // 代码风格配置
  ]
}
```

**配置文件** (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.tabSize": 4
  }
}
```

### Git 配置

```bash
# 设置 Git 用户信息（如未设置）
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 配置默认分支
git config --global init.defaultBranch main

# 配置自动换行（Windows）
git config --global core.autocrlf true

# 配置自动换行（macOS/Linux）
git config --global core.autocrlf input
```

### Pre-commit Hooks（可选）

```bash
# 安装 pre-commit
uv add --dev pre-commit

# 安装 hooks
uv run pre-commit install

# 手动运行所有 hooks
uv run pre-commit run --all-files
```

**配置文件** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

---

## 运行开发服务器

### 基本启动

```bash
# 启动开发服务器（默认端口 8000）
python manage.py runserver

# 指定端口
python manage.py runserver 8001

# 指定主机和端口（允许外部访问）
python manage.py runserver 0.0.0.0:8001
```

**预期输出**:
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
November 10, 2025 - 10:30:00
Django version 5.0.0, using settings 'config.settings'
Starting development server at http://127.0.0.1:8001/
Quit the server with CTRL-BREAK.
```

### 访问 API 文档

服务器启动后，访问：

- **Swagger UI**: http://localhost:8001/api/v1/docs
- **Health Check**: http://localhost:8001/api/v1/health

### 测试 API 端点

```bash
# 使用 curl 测试健康检查
curl http://localhost:8001/api/v1/health

# 测试搜索 API
curl "http://localhost:8001/api/v1/studies/search?q=test&page=1&page_size=20"

# 测试筛选选项
curl http://localhost:8001/api/v1/studies/filters/options
```

---

## 测试执行

### 运行所有测试

```bash
# 运行完整测试套件（63 个测试案例）
python manage.py test tests

# 预期输出：
# Creating test database for alias 'default'...
# System check identified no issues (0 silenced).
# ...............................................................
# ----------------------------------------------------------------------
# Ran 63 tests in 5.234s
#
# OK
# Destroying test database for alias 'default'...
```

### 运行特定测试模块

```bash
# 模型测试（15 个案例）
python manage.py test tests.test_models

# 服务层测试（30 个案例）
python manage.py test tests.test_services

# 缓存测试（10 个案例）
python manage.py test tests.test_caching

# 中间层测试（8 个案例）
python manage.py test tests.test_middleware
```

### 运行特定测试类或方法

```bash
# 运行特定测试类
python manage.py test tests.test_models.StudyModelCreationTests

# 运行特定测试方法
python manage.py test tests.test_models.StudyModelCreationTests.test_create_study_with_all_fields
```

### 详细输出

```bash
# 显示每个测试的名称和结果
python manage.py test tests --verbosity=2

# 显示完整的调试信息
python manage.py test tests --verbosity=3
```

### 测试覆盖率分析

```bash
# 安装 coverage（如未安装）
uv add --dev coverage

# 运行测试并生成覆盖率报告
coverage run --source='studies' manage.py test tests

# 显示覆盖率摘要
coverage report

# 预期输出：
# Name                         Stmts   Miss  Cover
# ------------------------------------------------
# studies/__init__.py              0      0   100%
# studies/api.py                 145     22    85%
# studies/config.py               45      5    89%
# studies/exceptions.py           38      3    92%
# studies/middleware.py           18      2    89%
# studies/models.py               67      5    93%
# studies/services.py            198     25    87%
# ------------------------------------------------
# TOTAL                          511     62    88%

# 生成 HTML 覆盖率报告
coverage html

# 打开报告（会在浏览器中打开）
# Windows:
start htmlcov/index.html
# macOS:
open htmlcov/index.html
# Linux:
xdg-open htmlcov/index.html
```

---

## 常见开发任务

### 创建新的 Django App

```bash
# 创建新应用
python manage.py startapp app_name

# 在 config/settings.py 中注册
# INSTALLED_APPS = [
#     ...
#     'app_name',
# ]
```

### 数据库模型变更

```bash
# 1. 修改 models.py

# 2. 创建迁移文件
python manage.py makemigrations

# 3. 检查生成的迁移文件
cat studies/migrations/0002_auto_*.py

# 4. 应用迁移
python manage.py migrate

# 5. 验证
python manage.py showmigrations
```

### Django Shell 交互

```bash
# 启动 Django shell
python manage.py shell

# 或使用 IPython（更好的交互体验）
uv add --dev ipython
python manage.py shell
```

**常用 Shell 操作**:
```python
# 导入模型
from studies.models import Study
from studies.services import StudyService

# 查询数据
studies = Study.objects.all()
study = Study.objects.get(exam_id="EXAM001")

# 创建数据
study = Study.objects.create(
    exam_id="NEW001",
    patient_name="New Patient",
    ...
)

# 更新数据
study.patient_name = "Updated Name"
study.save()

# 删除数据
study.delete()

# 使用服务层
from django.http import QueryDict
query_dict = QueryDict("q=test&exam_status=completed")
results = StudyService.get_studies_queryset(query_dict)
```

### 数据库备份和恢复

```bash
# 备份数据库
pg_dump -U postgres medical_imaging > backup_$(date +%Y%m%d).sql

# 恢复数据库
psql -U postgres medical_imaging < backup_20251110.sql

# 或使用 Django 的 dumpdata/loaddata
python manage.py dumpdata studies > fixtures/studies_data.json
python manage.py loaddata fixtures/studies_data.json
```

### 清理缓存

```bash
# Django shell
python manage.py shell

>>> from django.core.cache import cache
>>> cache.clear()
>>> exit()
```

### 查看日志

```bash
# 开发服务器日志（终端输出）
python manage.py runserver

# 应用日志文件
tail -f debug.log

# Windows:
type debug.log
```

---

## 故障排除

### 问题 1: `uv: command not found`

**原因**: UV 未正确安装或未添加到 PATH

**解决方案**:
```bash
# 重新安装 UV
pip install --user uv

# 添加到 PATH（Windows）
# 将 %USERPROFILE%\AppData\Roaming\Python\Python310\Scripts 添加到系统 PATH

# 添加到 PATH（macOS/Linux）
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 问题 2: 数据库连接错误

**错误信息**: `OperationalError: could not connect to server`

**解决方案**:
```bash
# 检查 PostgreSQL 服务是否运行
# Windows:
net start postgresql-x64-14

# macOS:
brew services list
brew services start postgresql@14

# Linux:
sudo systemctl status postgresql
sudo systemctl start postgresql

# 检查 .env 配置
cat .env | grep DB_

# 测试数据库连接
psql -U postgres -d medical_imaging -h localhost
```

### 问题 3: 端口已被占用

**错误信息**: `Error: That port is already in use.`

**解决方案**:
```bash
# 查找占用端口的进程
# Windows:
netstat -ano | findstr :8001

# macOS/Linux:
lsof -i :8001

# 终止进程或使用不同端口
python manage.py runserver 8002
```

### 问题 4: 迁移冲突

**错误信息**: `InconsistentMigrationHistory`

**解决方案**:
```bash
# 查看迁移状态
python manage.py showmigrations

# 回滚到特定迁移
python manage.py migrate studies 0001

# 重新应用
python manage.py migrate

# 如果严重，重置数据库（开发环境）
python manage.py flush
python manage.py migrate
```

### 问题 5: 测试失败

**错误信息**: 测试案例失败

**解决方案**:
```bash
# 运行单个测试查看详细错误
python manage.py test tests.test_services.StudyServiceQuerySetTextSearchTests.test_search_in_exam_id --verbosity=2

# 检查测试数据库权限
# 确保 .env 中的数据库用户有创建数据库权限

# 清理测试数据库
python manage.py test --keepdb  # 保留测试数据库以便调试
```

### 问题 6: `ModuleNotFoundError`

**错误信息**: `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
```bash
# 确保在正确的虚拟环境中
uv pip list | grep xxx

# 重新同步依赖
uv sync

# 如果是新依赖，添加到项目
uv add package_name

# 检查 Python 解释器
which python  # macOS/Linux
where python  # Windows
```

---

## 下一步

开发环境设置完成后，建议：

1. ✅ 阅读 [API_REFERENCE.md](API_REFERENCE.md) - 了解 API 端点详细信息
2. ✅ 阅读 [TESTING_GUIDE.md](TESTING_GUIDE.md) - 学习如何编写和运行测试
3. ✅ 查看 [claudedocs/](../claudedocs/) - 了解架构设计和技术决策
4. ✅ 探索代码库：
   - `studies/models.py` - 数据模型
   - `studies/services.py` - 业务逻辑
   - `studies/api.py` - API 端点
   - `tests/` - 测试套件

---

## 获取帮助

如遇到文档未覆盖的问题：

1. 📖 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. 🔍 搜索项目 Issues: https://github.com/your-org/image_data_platform/issues
3. 💬 联系团队成员或提交新 Issue

---

**文档版本**: 1.0.0
**最后更新**: 2025-11-10
**维护者**: Medical Imaging Development Team
