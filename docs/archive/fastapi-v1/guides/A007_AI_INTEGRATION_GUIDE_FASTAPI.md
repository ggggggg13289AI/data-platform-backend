# Ollama 本地LLM集成指南

## 文档概述

本指南提供完整的Ollama本地大语言模型（LLM）部署、配置、集成和优化方案，用于医疗报告AI辅助分析系统。

**目标读者**：后端开发人员、AI工程师、DevOps工程师

**文档版本**：v1.0.0
**最后更新**：2024-12-01

---

## 目录

1. [Ollama简介](#ollama简介)
2. [环境准备](#环境准备)
3. [Ollama安装](#ollama安装)
4. [模型选择与下载](#模型选择与下载)
5. [FastAPI集成](#fastapi集成)
6. [性能优化](#性能优化)
7. [Prompt工程最佳实践](#prompt工程最佳实践)
8. [测试与验证](#测试与验证)
9. [生产环境部署](#生产环境部署)
10. [故障排查](#故障排查)

---

## Ollama简介

### 什么是Ollama？

Ollama是一个开源的本地LLM运行框架，支持在本地部署和运行多种大语言模型，无需依赖云服务。

**核心优势**：
- ✅ **数据隐私**：医疗数据完全本地处理，不发送到外部服务器
- ✅ **零API费用**：无需支付云服务API调用费用
- ✅ **离线运行**：无需互联网连接即可工作
- ✅ **模型灵活性**：支持qwen、llama、mistral、gemma等多种模型
- ✅ **简单部署**：一条命令下载和运行模型
- ✅ **REST API**：标准HTTP接口，易于集成

**技术架构**：
```
┌─────────────────┐      HTTP REST API      ┌──────────────────┐
│  FastAPI 后端   │ ──────────────────────> │  Ollama 服务     │
│  (Python)       │  POST /api/chat         │  (Port 11434)    │
└─────────────────┘  JSON Request/Response  └──────────────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │  qwen2.5:7b      │
                                             │  (4.4GB Model)   │
                                             └──────────────────┘
```

### 为什么选择Ollama？

**对比云服务API（OpenAI、Claude、通义千问）**：
| 对比项 | Ollama本地部署 | 云服务API |
|--------|----------------|-----------|
| 数据隐私 | ⭐⭐⭐⭐⭐ 完全本地 | ⭐⭐ 数据需上传云端 |
| 成本 | ⭐⭐⭐⭐⭐ 硬件成本（一次性） | ⭐⭐ 按调用计费（持续） |
| 网络依赖 | ⭐⭐⭐⭐⭐ 离线可用 | ⭐ 需要稳定网络 |
| 响应速度 | ⭐⭐⭐⭐ 本地推理（取决于硬件） | ⭐⭐⭐ 网络延迟 |
| 模型定制 | ⭐⭐⭐⭐ 可微调模型 | ⭐⭐ 仅限prompt调优 |
| 易用性 | ⭐⭐⭐⭐ 简单安装 | ⭐⭐⭐⭐⭐ 即开即用 |

**本项目选择Ollama的关键原因**：
1. **医疗数据隐私合规**：患者报告包含敏感信息，不能上传到外部服务
2. **成本可控**：预计每天分析500-1000份报告，云API费用不可控
3. **离线部署需求**：医院内网环境可能无法访问外网
4. **中文医学理解**：qwen2.5模型对中文医学术语理解优秀

---

## 环境准备

### 硬件要求

#### 最低配置（开发/测试环境）
- **CPU**：4核心及以上（支持AVX2指令集）
- **内存**：8GB RAM
- **硬盘**：20GB可用空间（模型文件约5-10GB）
- **GPU**：可选（NVIDIA GPU可显著加速推理）

#### 推荐配置（生产环境）
- **CPU**：8核心及以上（AMD Ryzen 7 / Intel Core i7）
- **内存**：16GB RAM
- **硬盘**：50GB SSD（推荐NVMe）
- **GPU**：NVIDIA GPU（6GB+ VRAM，如RTX 3060、RTX 4060）

#### GPU加速性能对比
| 硬件配置 | 7B模型推理速度 | 适用场景 |
|----------|----------------|----------|
| CPU Only (8核) | ~15-30 tokens/s | 开发、小规模测试 |
| NVIDIA RTX 3060 (12GB) | ~50-80 tokens/s | 生产环境（单用户） |
| NVIDIA RTX 4090 (24GB) | ~100-150 tokens/s | 高并发生产环境 |

**检查硬件支持**：
```bash
# Linux/macOS - 检查CPU指令集
lscpu | grep avx2

# Windows - 检查CPU指令集
wmic cpu get caption

# 检查NVIDIA GPU
nvidia-smi
```

### 软件依赖

#### 操作系统支持
- ✅ **Linux**：Ubuntu 20.04+, CentOS 8+, Debian 11+
- ✅ **macOS**：macOS 11 (Big Sur) 及以上（Apple Silicon M1/M2原生支持）
- ✅ **Windows**：Windows 10/11（需要WSL2或原生支持）

#### 必需软件
- **Python**: 3.10+ (FastAPI项目依赖)
- **Docker**: 20.10+ (推荐使用Docker部署)
- **curl/wget**: 测试API连接

#### GPU驱动（如果使用GPU加速）
- **NVIDIA GPU**: CUDA 11.7+, cuDNN 8.x+
- **AMD GPU**: ROCm 5.x+（支持有限）

**安装CUDA Toolkit (Ubuntu示例)**：
```bash
# 添加NVIDIA仓库
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub
sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /"

# 安装CUDA
sudo apt update
sudo apt install cuda-11-8

# 验证安装
nvcc --version
```

---

## Ollama安装

### Linux 安装

**方法1：官方安装脚本（推荐）**
```bash
# 下载并运行官方安装脚本
curl -fsSL https://ollama.com/install.sh | sh

# 验证安装
ollama --version
# 输出: ollama version 0.1.x
```

**方法2：手动安装**
```bash
# 下载二进制文件
wget https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64
sudo mv ollama-linux-amd64 /usr/local/bin/ollama
sudo chmod +x /usr/local/bin/ollama

# 创建systemd服务
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"

[Install]
WantedBy=default.target
EOF

# 创建用户
sudo useradd -r -s /bin/false -m -d /usr/share/ollama ollama

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

# 检查状态
sudo systemctl status ollama
```

### macOS 安装

**方法1：官方安装包（推荐）**
```bash
# 下载并安装Ollama.app
# 访问 https://ollama.com/download/mac
# 下载 Ollama-darwin.zip，解压并拖动到应用程序文件夹

# 或使用命令行下载
curl -L https://ollama.com/download/Ollama-darwin.zip -o Ollama.zip
unzip Ollama.zip
sudo mv Ollama.app /Applications/

# 启动Ollama（会在后台运行）
open /Applications/Ollama.app

# 验证安装
ollama --version
```

**方法2：Homebrew安装**
```bash
# 安装Ollama
brew install ollama

# 启动服务
brew services start ollama

# 验证安装
ollama --version
```

### Windows 安装

**方法1：官方安装包（推荐）**
```powershell
# 下载Windows安装包
# 访问 https://ollama.com/download/windows
# 下载 OllamaSetup.exe 并运行安装

# 安装完成后，Ollama会作为Windows服务自动启动

# 验证安装（PowerShell）
ollama --version
```

**方法2：WSL2安装（推荐用于开发）**
```bash
# 在WSL2 Ubuntu中安装
wsl --install -d Ubuntu-22.04

# 进入WSL2
wsl

# 按照Linux安装步骤安装Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### Docker 部署（推荐生产环境）

**基本Docker运行**：
```bash
# CPU版本
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  ollama/ollama:latest

# GPU版本（NVIDIA）
docker run -d \
  --name ollama \
  --gpus all \
  -p 11434:11434 \
  -v ollama_data:/root/.ollama \
  ollama/ollama:latest

# 验证运行
docker logs ollama
docker exec -it ollama ollama --version
```

**Docker Compose集成（推荐）**：
```yaml
# docker-compose.yml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    # GPU支持（取消注释以下行）
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
      - OLLAMA_ORIGINS=*
      - OLLAMA_NUM_PARALLEL=4
      - OLLAMA_MAX_LOADED_MODELS=2
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  ollama_data:
    driver: local
```

**启动和管理**：
```bash
# 启动服务
docker-compose up -d ollama

# 查看日志
docker-compose logs -f ollama

# 停止服务
docker-compose stop ollama

# 重启服务
docker-compose restart ollama
```

### 验证安装

**检查Ollama服务**：
```bash
# 测试API端点
curl http://localhost:11434/api/tags

# 预期输出：
# {"models":[]}  # 初始安装时模型列表为空
```

**检查GPU支持（如果使用GPU）**：
```bash
# Docker内检查
docker exec ollama nvidia-smi

# 本地检查
ollama run llama2:7b --verbose
# 输出应包含 "using GPU" 信息
```

---

## 模型选择与下载

### 推荐模型：qwen2.5:7b

**选择理由**：
1. ✅ **中文理解优秀**：阿里达摩院训练，针对中文优化
2. ✅ **医学知识丰富**：预训练数据包含大量医学文献
3. ✅ **推理速度快**：7B参数，在消费级硬件上运行流畅
4. ✅ **JSON输出稳定**：支持结构化输出，适合API集成
5. ✅ **社区支持好**：活跃的开发社区和文档

**模型规格**：
- **参数量**：7B (70亿参数)
- **文件大小**：4.4GB
- **量化版本**：Q4_0 (4-bit量化，精度与速度平衡)
- **上下文长度**：32,768 tokens
- **支持语言**：中文、英文、多语言

### 模型下载

**方法1：Ollama命令行（推荐）**
```bash
# 下载qwen2.5:7b模型
ollama pull qwen2.5:7b

# 预期输出：
# pulling manifest
# pulling 8934d96d3f08... 100% ▕████████████████████▏ 4.4 GB
# pulling 8c17c2ebb0ea... 100% ▕████████████████████▏ 7.0 kB
# pulling 7c23fb36d801... 100% ▕████████████████████▏ 4.8 kB
# pulling 2e0493f67d0c... 100% ▕████████████████████▏ 59 B
# verifying sha256 digest
# writing manifest
# removing any unused layers
# success

# 验证模型下载
ollama list

# 预期输出：
# NAME            ID              SIZE    MODIFIED
# qwen2.5:7b      a1b2c3d4e5f6    4.4 GB  2 minutes ago
```

**方法2：Docker内下载**
```bash
# 进入Docker容器
docker exec -it ollama bash

# 下载模型
ollama pull qwen2.5:7b

# 退出容器
exit

# 验证下载（从外部）
docker exec ollama ollama list
```

**模型文件存储位置**：
- **Linux**: `/usr/share/ollama/.ollama/models/`
- **macOS**: `~/.ollama/models/`
- **Windows**: `C:\Users\<username>\.ollama\models\`
- **Docker**: `/root/.ollama/models/` (容器内)

### 备选模型对比

| 模型 | 参数 | 文件大小 | 中文能力 | 医学理解 | 推理速度 | 推荐场景 |
|------|------|----------|----------|----------|----------|----------|
| **qwen2.5:7b** | 7B | 4.4GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 中 | **首选** |
| llama3.1:8b | 8B | 4.7GB | ⭐⭐⭐ | ⭐⭐⭐ | 中 | 英文为主 |
| mistral:7b | 7B | 4.1GB | ⭐⭐ | ⭐⭐⭐ | 快 | 速度优先 |
| gemma2:9b | 9B | 5.4GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 慢 | 高精度 |
| qwen2:1.5b | 1.5B | 934MB | ⭐⭐⭐⭐ | ⭐⭐ | 快 | 资源受限 |

**下载备选模型**：
```bash
# 下载多个模型用于对比测试
ollama pull llama3.1:8b
ollama pull mistral:7b
ollama pull gemma2:9b

# 查看所有已下载模型
ollama list
```

### 模型测试

**交互式测试**：
```bash
# 启动交互式对话
ollama run qwen2.5:7b

# 测试中文理解
>>> 请分析以下CT报告：双肺纹理增多，未见明显实质性病变。

# 预期输出示例：
# 根据CT报告描述，主要发现如下：
# 1. 双肺纹理增多：提示可能存在轻度炎症、充血或间质性改变
# 2. 未见明显实质性病变：说明肺实质未发现占位性病变、结节或肿块
# 3. 综合评估：整体影像表现良好，建议结合临床症状综合判断
# ...

# 退出交互模式
>>> /bye
```

**API测试**：
```bash
# 测试JSON格式输出
curl http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:7b",
  "messages": [
    {
      "role": "system",
      "content": "你是医学报告分析专家。请用JSON格式返回分析结果。"
    },
    {
      "role": "user",
      "content": "分析报告：心影不大，主动脉未见异常。请提取关键发现。"
    }
  ],
  "format": "json",
  "stream": false
}'

# 预期输出：
# {
#   "model": "qwen2.5:7b",
#   "created_at": "2024-12-01T10:30:00Z",
#   "message": {
#     "role": "assistant",
#     "content": "{\"findings\": [\"心影大小正常\", \"主动脉形态正常\"], \"impression\": \"心脏及大血管影像学表现正常\"}"
#   },
#   "done": true,
#   "total_duration": 2500000000,
#   "load_duration": 500000000,
#   "prompt_eval_duration": 1000000000,
#   "eval_duration": 1000000000
# }
```

---

## FastAPI集成

### OllamaClient实现

**完整客户端类** (`app/services/ollama_client.py`):

```python
import json
import logging
from typing import Dict, List, Any, Optional
import httpx
from httpx import TimeoutException, ConnectError, HTTPStatusError

logger = logging.getLogger(__name__)


class OllamaClient:
    """Ollama本地LLM客户端

    提供与Ollama服务的异步通信接口，支持对话、报告分析和批量处理。
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        timeout: float = 60.0,
        connect_timeout: float = 5.0,
    ):
        """初始化Ollama客户端

        Args:
            base_url: Ollama服务地址
            model: 使用的模型名称
            timeout: 请求超时时间（秒）
            connect_timeout: 连接超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = httpx.Timeout(timeout, connect=connect_timeout)

    async def health_check(self) -> bool:
        """检查Ollama服务健康状态

        Returns:
            bool: 服务是否可用
        """
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        format: str = "json",
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """与Ollama LLM进行对话

        Args:
            messages: 消息列表，每条消息包含role和content
            format: 输出格式（"json"或""）
            temperature: 温度参数（0.0-1.0），控制随机性
            top_p: 核采样参数（0.0-1.0）
            max_tokens: 最大生成token数

        Returns:
            Dict: Ollama响应数据

        Raises:
            TimeoutException: 请求超时
            ConnectError: 连接失败
            HTTPStatusError: HTTP错误
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            }
        }

        if format:
            payload["format"] = format

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                return response.json()

        except TimeoutException as e:
            logger.error(f"Ollama request timeout: {e}")
            raise
        except ConnectError as e:
            logger.error(f"Cannot connect to Ollama: {e}")
            raise
        except HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            raise

    def _build_system_prompt(self, annotation_type: str) -> str:
        """构建系统提示词

        Args:
            annotation_type: 标注类型（highlight/classification/extraction/scoring）

        Returns:
            str: 系统提示词
        """
        prompts = {
            "highlight": """你是医学报告分析专家。你的任务是识别报告中的关键信息并进行高亮标注。

请分析用户提供的医学报告，根据用户需求标注重要内容。

输出JSON格式：
{
  "highlights": [
    {"text": "标注文本", "category": "类别", "start": 起始位置, "end": 结束位置, "reason": "标注理由"}
  ]
}""",

            "classification": """你是医学报告分类专家。你的任务是对报告进行多维度分类。

请分析用户提供的医学报告，根据用户需求进行分类。

输出JSON格式：
{
  "classifications": [
    {"dimension": "分类维度", "category": "类别", "confidence": 0.95}
  ]
}""",

            "extraction": """你是医学信息提取专家。你的任务是从报告中提取结构化信息。

请分析用户提供的医学报告，根据用户需求提取关键信息。

输出JSON格式：
{
  "findings": ["发现1", "发现2"],
  "measurements": [{"item": "项目", "value": "数值", "unit": "单位"}],
  "locations": ["部位1", "部位2"]
}""",

            "scoring": """你是医学报告评分专家。你的任务是对报告进行多维度评分。

请分析用户提供的医学报告，根据用户需求进行评分。

输出JSON格式：
{
  "scores": [
    {"dimension": "评分维度", "score": 85, "max_score": 100, "reason": "评分理由"}
  ],
  "overall_score": 82
}"""
        }

        return prompts.get(annotation_type, prompts["extraction"])

    async def analyze_report(
        self,
        report_text: str,
        user_prompt: str,
        annotation_type: str,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """分析医学报告

        Args:
            report_text: 报告内容
            user_prompt: 用户需求描述
            annotation_type: 标注类型
            temperature: 温度参数

        Returns:
            Dict: 分析结果，包含annotation_type、content、confidence等
        """
        system_prompt = self._build_system_prompt(annotation_type)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户需求: {user_prompt}\n\n报告内容:\n{report_text}\n\n请严格按照JSON格式返回分析结果。"}
        ]

        response = await self.chat(
            messages=messages,
            format="json",
            temperature=temperature
        )

        # 解析响应内容
        raw_content = response["message"]["content"]

        try:
            content = json.loads(raw_content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response, using raw text")
            content = {"raw_text": raw_content}

        # 计算置信度（基于响应时间和内容完整性）
        eval_count = response.get("eval_count", 0)
        prompt_eval_count = response.get("prompt_eval_count", 0)
        total_tokens = eval_count + prompt_eval_count

        # 简单的置信度估算（可根据实际情况调整）
        confidence = min(0.95, 0.7 + (total_tokens / 1000) * 0.1)

        return {
            "annotation_type": annotation_type,
            "content": content,
            "confidence": round(confidence, 2),
            "model_name": self.model,
            "model_temperature": temperature,
            "raw_response": raw_content,
            "total_duration_seconds": response.get("total_duration", 0) / 1e9,
            "eval_count": eval_count,
            "prompt_eval_count": prompt_eval_count,
        }


# 全局单例实例
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """获取全局Ollama客户端实例

    Returns:
        OllamaClient: 客户端实例
    """
    global _ollama_client

    if _ollama_client is None:
        from app.core.config import settings
        _ollama_client = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout=settings.OLLAMA_TIMEOUT,
        )

    return _ollama_client
```

### 配置管理

**环境变量配置** (`app/core/config.py`):

```python
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # Ollama配置
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    OLLAMA_TIMEOUT: float = 60.0
    OLLAMA_CONNECT_TIMEOUT: float = 5.0
    OLLAMA_MAX_CONCURRENT: int = 3
    OLLAMA_DEFAULT_TEMPERATURE: float = 0.7

    # 数据库配置
    DATABASE_URL: str

    # JWT配置
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 应用配置
    PROJECT_NAME: str = "医疗报告AI分析平台"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
```

**环境变量文件** (`.env`):
```ini
# Ollama配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=60.0
OLLAMA_CONNECT_TIMEOUT=5.0
OLLAMA_MAX_CONCURRENT=3
OLLAMA_DEFAULT_TEMPERATURE=0.7

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/imagedb

# JWT配置
SECRET_KEY=your-secret-key-here-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 应用配置
PROJECT_NAME=医疗报告AI分析平台
VERSION=1.0.0
DEBUG=False
```

### API端点实现

**AI分析端点** (`app/api/ai_analysis.py`):

```python
import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.ollama_client import get_ollama_client
from app.models.report import Report
from app.models.ai_annotation import AIAnnotation
from app.api.dependencies import get_current_user


router = APIRouter(prefix="/api/v1/ai", tags=["AI Analysis"])


# 请求模型
class AnalyzeRequest(BaseModel):
    report_id: int = Field(..., description="报告ID")
    user_prompt: str = Field(..., description="用户需求描述")
    annotation_type: str = Field(..., pattern="^(highlight|classification|extraction|scoring)$")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="温度参数")


class BatchAnalyzeRequest(BaseModel):
    report_ids: List[int] = Field(..., max_length=50, description="报告ID列表（最多50个）")
    user_prompt: str = Field(..., description="用户需求描述")
    annotation_type: str = Field(..., pattern="^(highlight|classification|extraction|scoring)$")
    temperature: float = Field(0.7, ge=0.0, le=1.0)


# 响应模型
class AnalyzeResponse(BaseModel):
    annotation_id: int
    report_id: int
    annotation_type: str
    content: dict
    confidence: float
    model_name: str
    model_temperature: float
    created_at: str
    duration_seconds: float


# 并发控制
semaphore = asyncio.Semaphore(3)  # 最多3个并发请求


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_single_report(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """单个报告AI分析

    对指定报告进行AI分析，生成标注结果。
    """
    ollama_client = get_ollama_client()

    # 检查Ollama服务状态
    if not await ollama_client.health_check():
        raise HTTPException(status_code=503, detail="Ollama service unavailable")

    # 获取报告
    result = await db.execute(
        "SELECT * FROM reports WHERE id = :id AND is_deleted = false",
        {"id": request.report_id}
    )
    report = result.fetchone()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # 使用信号量控制并发
    async with semaphore:
        try:
            # 调用Ollama分析
            analysis_result = await ollama_client.analyze_report(
                report_text=report["report_content"],
                user_prompt=request.user_prompt,
                annotation_type=request.annotation_type,
                temperature=request.temperature,
            )

            # 保存标注结果
            annotation = AIAnnotation(
                report_id=request.report_id,
                annotation_type=request.annotation_type,
                content=analysis_result["content"],
                user_prompt=request.user_prompt,
                confidence=analysis_result["confidence"],
                model_name=analysis_result["model_name"],
                model_temperature=analysis_result["model_temperature"],
                created_by=current_user.id,
            )

            db.add(annotation)
            await db.commit()
            await db.refresh(annotation)

            return AnalyzeResponse(
                annotation_id=annotation.id,
                report_id=annotation.report_id,
                annotation_type=annotation.annotation_type,
                content=annotation.content,
                confidence=annotation.confidence,
                model_name=annotation.model_name,
                model_temperature=annotation.model_temperature,
                created_at=annotation.created_at.isoformat(),
                duration_seconds=analysis_result["total_duration_seconds"],
            )

        except Exception as e:
            logger.error(f"Analysis failed for report {request.report_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/batch-analyze")
async def batch_analyze_reports(
    request: BatchAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """批量报告AI分析

    对多个报告进行批量AI分析，作为后台任务执行。
    """
    # 验证report_ids
    if len(request.report_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 reports per batch")

    # 添加后台任务
    background_tasks.add_task(
        _batch_analyze_task,
        report_ids=request.report_ids,
        user_prompt=request.user_prompt,
        annotation_type=request.annotation_type,
        temperature=request.temperature,
        user_id=current_user.id,
    )

    return {
        "status": "processing",
        "message": f"Batch analysis started for {len(request.report_ids)} reports",
        "report_count": len(request.report_ids),
    }


async def _batch_analyze_task(
    report_ids: List[int],
    user_prompt: str,
    annotation_type: str,
    temperature: float,
    user_id: int,
):
    """批量分析后台任务

    使用asyncio.gather并发处理多个报告。
    """
    ollama_client = get_ollama_client()

    async def analyze_one(report_id: int):
        """分析单个报告（带并发控制）"""
        async with semaphore:
            try:
                async with get_db() as db:
                    # 获取报告
                    result = await db.execute(
                        "SELECT * FROM reports WHERE id = :id AND is_deleted = false",
                        {"id": report_id}
                    )
                    report = result.fetchone()

                    if not report:
                        logger.warning(f"Report {report_id} not found")
                        return {"status": "error", "report_id": report_id, "error": "not_found"}

                    # 分析报告
                    analysis_result = await ollama_client.analyze_report(
                        report_text=report["report_content"],
                        user_prompt=user_prompt,
                        annotation_type=annotation_type,
                        temperature=temperature,
                    )

                    # 保存结果
                    annotation = AIAnnotation(
                        report_id=report_id,
                        annotation_type=annotation_type,
                        content=analysis_result["content"],
                        user_prompt=user_prompt,
                        confidence=analysis_result["confidence"],
                        model_name=analysis_result["model_name"],
                        model_temperature=analysis_result["model_temperature"],
                        created_by=user_id,
                    )

                    db.add(annotation)
                    await db.commit()

                    return {"status": "success", "report_id": report_id, "annotation_id": annotation.id}

            except Exception as e:
                logger.error(f"Failed to analyze report {report_id}: {e}")
                return {"status": "error", "report_id": report_id, "error": str(e)}

    # 并发处理所有报告
    results = await asyncio.gather(*[analyze_one(rid) for rid in report_ids])

    # 记录结果统计
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count

    logger.info(f"Batch analysis completed: {success_count} success, {error_count} errors")
```

### 健康检查端点

**健康检查API** (`app/api/health.py`):

```python
from fastapi import APIRouter
from app.services.ollama_client import get_ollama_client
from app.core.database import engine


router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get("")
async def health_check():
    """系统健康检查

    检查数据库和Ollama服务状态。
    """
    # 检查数据库
    db_status = "ok"
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
    except Exception as e:
        db_status = f"error: {str(e)}"

    # 检查Ollama
    ollama_client = get_ollama_client()
    ollama_status = "ok" if await ollama_client.health_check() else "unavailable"

    overall_status = "healthy" if db_status == "ok" and ollama_status == "ok" else "degraded"

    return {
        "status": overall_status,
        "database": db_status,
        "ollama": ollama_status,
        "model": ollama_client.model,
    }
```

---

## 性能优化

### 并发控制

**信号量限流**：
```python
import asyncio

# 全局信号量（限制最多3个并发）
semaphore = asyncio.Semaphore(3)

async def controlled_analysis(report_text: str):
    """带并发控制的分析"""
    async with semaphore:
        # 实际分析逻辑
        result = await ollama_client.analyze_report(report_text, ...)
        return result
```

**优势**：
- 防止Ollama服务过载
- 控制GPU显存占用
- 提升整体系统稳定性

### GPU优化

**Docker GPU配置**：
```yaml
# docker-compose.yml
services:
  ollama:
    image: ollama/ollama:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1  # 使用1块GPU
              capabilities: [gpu]
    environment:
      # 限制GPU显存使用（以MB为单位）
      - OLLAMA_GPU_MEMORY_LIMIT=8192
      # 启用KV缓存
      - OLLAMA_KV_CACHE_TYPE=q4_0
```

**性能监控**：
```bash
# 实时监控GPU使用情况
watch -n 1 nvidia-smi

# 查看Ollama GPU使用
docker exec ollama nvidia-smi
```

### 模型缓存

**预加载模型**：
```bash
# 启动时预加载模型到内存
docker exec ollama ollama run qwen2.5:7b --keepalive 24h

# 或在Docker Compose中配置
services:
  ollama:
    command: >
      sh -c "ollama serve &
             sleep 5 &&
             ollama run qwen2.5:7b --keepalive 24h &&
             wait"
```

**环境变量配置**：
```yaml
environment:
  # 同时加载的最大模型数
  - OLLAMA_MAX_LOADED_MODELS=2
  # 并发请求数
  - OLLAMA_NUM_PARALLEL=4
  # 模型保持时间
  - OLLAMA_KEEP_ALIVE=24h
```

### 连接池优化

**httpx连接池**：
```python
import httpx

# 创建持久化客户端（连接复用）
class OllamaClient:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
            )
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
```

### 响应缓存

**基于内容哈希的缓存**：
```python
import hashlib
import json
from functools import lru_cache

class CachedOllamaClient(OllamaClient):
    """带缓存的Ollama客户端"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}

    def _cache_key(self, report_text: str, user_prompt: str, annotation_type: str) -> str:
        """生成缓存键"""
        content = f"{report_text}{user_prompt}{annotation_type}"
        return hashlib.md5(content.encode()).hexdigest()

    async def analyze_report(self, report_text: str, user_prompt: str, annotation_type: str, **kwargs):
        """带缓存的报告分析"""
        cache_key = self._cache_key(report_text, user_prompt, annotation_type)

        # 检查缓存
        if cache_key in self._cache:
            logger.info(f"Cache hit for {cache_key}")
            return self._cache[cache_key]

        # 调用实际分析
        result = await super().analyze_report(report_text, user_prompt, annotation_type, **kwargs)

        # 保存缓存
        self._cache[cache_key] = result

        return result
```

---

## Prompt工程最佳实践

### System Prompt设计原则

**1. 明确角色定位**
```python
# ✅ Good
system_prompt = "你是医学报告分析专家，专注于CT和MRI影像报告的结构化信息提取。"

# ❌ Bad
system_prompt = "你是AI助手。"
```

**2. 提供明确的输出格式**
```python
# ✅ Good
system_prompt = """你是医学报告分析专家。

请分析报告并返回JSON格式：
{
  "findings": ["发现1", "发现2"],
  "measurements": [{"item": "心胸比例", "value": "0.48", "unit": "ratio"}],
  "locations": ["双肺", "心脏"]
}"""

# ❌ Bad
system_prompt = "请分析报告。"
```

**3. 包含示例（Few-Shot Learning）**
```python
system_prompt = """你是医学报告分析专家。

示例输入：
双肺纹理增多，心影不大，主动脉未见异常。

示例输出：
{
  "findings": ["双肺纹理增多", "心影大小正常", "主动脉形态正常"],
  "measurements": [],
  "locations": ["双肺", "心脏", "主动脉"]
}

现在请分析以下报告："""
```

### User Prompt优化

**1. 具体化需求**
```python
# ✅ Good
user_prompt = "请提取报告中所有测量数值，包括数值、单位和测量部位。"

# ❌ Bad
user_prompt = "分析报告。"
```

**2. 分解复杂任务**
```python
# ✅ Good - 分步骤
user_prompt = """请按以下步骤分析报告：
1. 识别所有提到的器官和部位
2. 提取每个部位的描述性发现
3. 提取数值测量结果
4. 总结整体印象"""

# ❌ Bad - 一次性复杂任务
user_prompt = "全面分析报告并提取所有信息。"
```

### 温度参数调优

**不同任务的推荐温度**：
```python
# 信息提取（需要精确）
temperature = 0.3

# 分类任务（需要稳定）
temperature = 0.5

# 高亮标注（允许一定灵活性）
temperature = 0.7

# 创意性总结（允许变化）
temperature = 0.9
```

### Prompt模板库

**完整模板示例** (`app/prompts/medical_prompts.py`):

```python
"""医学报告分析Prompt模板库"""

HIGHLIGHT_SYSTEM_PROMPT = """你是医学报告分析专家。你的任务是识别报告中的关键信息并进行高亮标注。

标注规则：
1. 异常发现 (category: abnormal) - 任何偏离正常的描述
2. 测量数值 (category: measurement) - 具体的数值和单位
3. 部位信息 (category: location) - 解剖结构和位置
4. 诊断结论 (category: diagnosis) - 明确的诊断或印象

输出JSON格式：
{
  "highlights": [
    {
      "text": "标注文本",
      "category": "abnormal|measurement|location|diagnosis",
      "start": 起始字符位置,
      "end": 结束字符位置,
      "reason": "标注理由"
    }
  ]
}

示例输入：
双肺纹理增多，心胸比例约0.48，未见明显实质性病变。

示例输出：
{
  "highlights": [
    {"text": "双肺纹理增多", "category": "abnormal", "start": 0, "end": 7, "reason": "肺部纹理异常增多"},
    {"text": "心胸比例约0.48", "category": "measurement", "start": 8, "end": 18, "reason": "心胸比例测量值"},
    {"text": "双肺", "category": "location", "start": 0, "end": 2, "reason": "解剖部位"}
  ]
}"""

CLASSIFICATION_SYSTEM_PROMPT = """你是医学报告分类专家。你的任务是对报告进行多维度分类。

分类维度：
1. 紧急程度: 正常/异常轻微/异常中度/异常严重/危急
2. 检查部位: 头颅/胸部/腹部/四肢/脊柱/其他
3. 检查类型: CT/MRI/X-Ray/超声/其他
4. 是否需要随访: 是/否
5. 是否需要进一步检查: 是/否

输出JSON格式：
{
  "classifications": [
    {"dimension": "紧急程度", "category": "异常轻微", "confidence": 0.92},
    {"dimension": "检查部位", "category": "胸部", "confidence": 0.98}
  ]
}"""

EXTRACTION_SYSTEM_PROMPT = """你是医学信息提取专家。你的任务是从报告中提取结构化信息。

提取内容：
1. findings: 所有描述性发现（列表）
2. measurements: 数值测量结果（对象数组，包含item、value、unit）
3. locations: 涉及的解剖部位（列表）
4. impression: 总体印象或结论

输出JSON格式：
{
  "findings": ["发现1", "发现2"],
  "measurements": [
    {"item": "心胸比例", "value": "0.48", "unit": "ratio"}
  ],
  "locations": ["部位1", "部位2"],
  "impression": "整体结论"
}

示例输入：
胸部CT平扫：双肺纹理增多，未见明显实质性病变。心影不大，心胸比例约0.48。主动脉未见异常。印象：双肺炎症可能。

示例输出：
{
  "findings": ["双肺纹理增多", "未见明显实质性病变", "心影大小正常", "主动脉形态正常"],
  "measurements": [{"item": "心胸比例", "value": "0.48", "unit": "ratio"}],
  "locations": ["双肺", "心脏", "主动脉"],
  "impression": "双肺炎症可能"
}"""

SCORING_SYSTEM_PROMPT = """你是医学报告评分专家。你的任务是对报告进行多维度评分。

评分维度（0-100分）：
1. 报告完整性: 报告是否包含必要的描述和结论
2. 描述清晰度: 语言是否清晰、术语使用是否准确
3. 发现详细度: 异常发现是否有详细描述
4. 测量精确度: 数值测量是否完整和精确
5. 临床价值: 报告对临床决策的参考价值

输出JSON格式：
{
  "scores": [
    {"dimension": "报告完整性", "score": 85, "max_score": 100, "reason": "包含描述和印象，缺少技术参数"},
    {"dimension": "描述清晰度", "score": 90, "max_score": 100, "reason": "术语准确，表述清晰"}
  ],
  "overall_score": 87
}"""


def get_system_prompt(annotation_type: str) -> str:
    """获取系统提示词

    Args:
        annotation_type: 标注类型

    Returns:
        str: 系统提示词
    """
    prompts = {
        "highlight": HIGHLIGHT_SYSTEM_PROMPT,
        "classification": CLASSIFICATION_SYSTEM_PROMPT,
        "extraction": EXTRACTION_SYSTEM_PROMPT,
        "scoring": SCORING_SYSTEM_PROMPT,
    }

    return prompts.get(annotation_type, EXTRACTION_SYSTEM_PROMPT)
```

---

## 测试与验证

### 单元测试

**测试OllamaClient** (`tests/test_ollama_client.py`):

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.services.ollama_client import OllamaClient


@pytest.fixture
def ollama_client():
    """创建测试客户端"""
    return OllamaClient(base_url="http://localhost:11434")


@pytest.mark.asyncio
async def test_health_check_success(ollama_client):
    """测试健康检查 - 成功"""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = await ollama_client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(ollama_client):
    """测试健康检查 - 失败"""
    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection error")):
        result = await ollama_client.health_check()
        assert result is False


@pytest.mark.asyncio
async def test_chat_success(ollama_client):
    """测试对话 - 成功"""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": '{"findings": ["test"]}'},
            "model": "qwen2.5:7b",
            "total_duration": 2000000000,
            "eval_count": 50,
            "prompt_eval_count": 30,
        }
        mock_post.return_value = mock_response

        messages = [{"role": "user", "content": "测试"}]
        result = await ollama_client.chat(messages)

        assert result["model"] == "qwen2.5:7b"
        assert "message" in result


@pytest.mark.asyncio
async def test_analyze_report_success(ollama_client):
    """测试报告分析 - 成功"""
    with patch.object(ollama_client, "chat") as mock_chat:
        mock_chat.return_value = {
            "message": {"content": '{"findings": ["双肺纹理增多"], "locations": ["双肺"]}'},
            "total_duration": 3000000000,
            "eval_count": 60,
            "prompt_eval_count": 40,
        }

        result = await ollama_client.analyze_report(
            report_text="双肺纹理增多，心影不大。",
            user_prompt="提取发现和部位",
            annotation_type="extraction",
        )

        assert result["annotation_type"] == "extraction"
        assert "findings" in result["content"]
        assert result["confidence"] > 0.7


@pytest.mark.asyncio
async def test_analyze_report_invalid_json(ollama_client):
    """测试报告分析 - 无效JSON"""
    with patch.object(ollama_client, "chat") as mock_chat:
        mock_chat.return_value = {
            "message": {"content": "这不是有效的JSON"},
            "total_duration": 2000000000,
            "eval_count": 30,
            "prompt_eval_count": 20,
        }

        result = await ollama_client.analyze_report(
            report_text="测试报告",
            user_prompt="测试",
            annotation_type="extraction",
        )

        assert "raw_text" in result["content"]
```

### 集成测试

**测试API端点** (`tests/test_ai_analysis_api.py`):

```python
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_analyze_single_report(authenticated_client):
    """测试单报告分析API"""
    response = await authenticated_client.post(
        "/api/v1/ai/analyze",
        json={
            "report_id": 1,
            "user_prompt": "提取关键发现",
            "annotation_type": "extraction",
            "temperature": 0.7,
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "annotation_id" in data
    assert data["annotation_type"] == "extraction"
    assert "content" in data


@pytest.mark.asyncio
async def test_batch_analyze_reports(authenticated_client):
    """测试批量分析API"""
    response = await authenticated_client.post(
        "/api/v1/ai/batch-analyze",
        json={
            "report_ids": [1, 2, 3],
            "user_prompt": "分类报告紧急程度",
            "annotation_type": "classification",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["report_count"] == 3


@pytest.mark.asyncio
async def test_health_check_ollama(client):
    """测试健康检查API"""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert "ollama" in data
    assert "database" in data
```

### 性能测试

**负载测试脚本** (`tests/load_test_ollama.py`):

```python
import asyncio
import time
from app.services.ollama_client import OllamaClient


async def analyze_one_report(client: OllamaClient, report_id: int):
    """分析单个报告"""
    start_time = time.time()

    try:
        result = await client.analyze_report(
            report_text=f"测试报告 {report_id}: 双肺纹理增多，心影不大。",
            user_prompt="提取关键发现",
            annotation_type="extraction",
        )

        duration = time.time() - start_time
        return {"status": "success", "duration": duration, "report_id": report_id}

    except Exception as e:
        duration = time.time() - start_time
        return {"status": "error", "duration": duration, "report_id": report_id, "error": str(e)}


async def load_test(num_requests: int, concurrent: int):
    """负载测试

    Args:
        num_requests: 总请求数
        concurrent: 并发数
    """
    client = OllamaClient()

    print(f"Starting load test: {num_requests} requests, {concurrent} concurrent")

    start_time = time.time()

    # 创建信号量控制并发
    semaphore = asyncio.Semaphore(concurrent)

    async def controlled_analyze(report_id):
        async with semaphore:
            return await analyze_one_report(client, report_id)

    # 执行所有请求
    results = await asyncio.gather(*[
        controlled_analyze(i) for i in range(num_requests)
    ])

    total_duration = time.time() - start_time

    # 统计结果
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = num_requests - success_count

    durations = [r["duration"] for r in results if r["status"] == "success"]
    avg_duration = sum(durations) / len(durations) if durations else 0
    min_duration = min(durations) if durations else 0
    max_duration = max(durations) if durations else 0

    # 输出报告
    print(f"\n=== Load Test Results ===")
    print(f"Total requests: {num_requests}")
    print(f"Concurrent: {concurrent}")
    print(f"Success: {success_count} ({success_count/num_requests*100:.1f}%)")
    print(f"Errors: {error_count} ({error_count/num_requests*100:.1f}%)")
    print(f"Total time: {total_duration:.2f}s")
    print(f"Throughput: {num_requests/total_duration:.2f} requests/s")
    print(f"Avg response time: {avg_duration:.2f}s")
    print(f"Min response time: {min_duration:.2f}s")
    print(f"Max response time: {max_duration:.2f}s")


if __name__ == "__main__":
    # 测试场景1: 10个请求，并发3
    asyncio.run(load_test(num_requests=10, concurrent=3))

    # 测试场景2: 50个请求，并发5
    # asyncio.run(load_test(num_requests=50, concurrent=5))
```

**运行负载测试**：
```bash
# 确保Ollama服务运行
docker-compose up -d ollama

# 运行负载测试
python tests/load_test_ollama.py

# 预期输出：
# Starting load test: 10 requests, 3 concurrent
#
# === Load Test Results ===
# Total requests: 10
# Concurrent: 3
# Success: 10 (100.0%)
# Errors: 0 (0.0%)
# Total time: 35.42s
# Throughput: 0.28 requests/s
# Avg response time: 10.63s
# Min response time: 8.21s
# Max response time: 12.94s
```

---

## 生产环境部署

### Docker生产配置

**生产环境Docker Compose** (`docker-compose.prod.yml`):

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    container_name: postgres_prod
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  ollama:
    image: ollama/ollama:latest
    container_name: ollama_prod
    ports:
      - "127.0.0.1:11434:11434"  # 仅本地访问
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
        limits:
          memory: 16G
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

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    container_name: backend_prod
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - OLLAMA_BASE_URL=http://ollama:11434
      - OLLAMA_MODEL=qwen2.5:7b
      - OLLAMA_TIMEOUT=60.0
      - OLLAMA_MAX_CONCURRENT=3
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=False
    depends_on:
      postgres:
        condition: service_healthy
      ollama:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - backend
      - frontend

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    container_name: frontend_prod
    environment:
      - VITE_API_URL=https://api.yourdomain.com
    restart: unless-stopped
    networks:
      - frontend

  nginx:
    image: nginx:alpine
    container_name: nginx_prod
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
    networks:
      - frontend

volumes:
  postgres_data:
    driver: local
  ollama_data:
    driver: local
  nginx_logs:
    driver: local

networks:
  backend:
    driver: bridge
  frontend:
    driver: bridge
```

### Nginx反向代理

**Nginx配置** (`nginx/nginx.conf`):

```nginx
worker_processes auto;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss;

    # 上游服务器
    upstream backend_api {
        server backend:8000;
        keepalive 32;
    }

    upstream frontend_app {
        server frontend:3000;
        keepalive 32;
    }

    # HTTP重定向到HTTPS
    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS主服务器
    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        # SSL证书
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # 安全头
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # API代理
        location /api/ {
            proxy_pass http://backend_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 超时设置（考虑AI分析耗时）
            proxy_connect_timeout 10s;
            proxy_send_timeout 90s;
            proxy_read_timeout 90s;

            # 缓冲设置
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }

        # 前端代理
        location / {
            proxy_pass http://frontend_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket支持（如果需要）
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # 静态文件缓存
        location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
            proxy_pass http://frontend_app;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # 健康检查端点
        location /health {
            proxy_pass http://backend_api/api/v1/health;
            access_log off;
        }
    }
}
```

### 监控和日志

**Prometheus监控配置** (`monitoring/prometheus.yml`):

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Ollama指标（如果支持）
  - job_name: 'ollama'
    static_configs:
      - targets: ['ollama:11434']
    metrics_path: '/metrics'

  # FastAPI应用指标
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'

  # PostgreSQL指标
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
```

**日志聚合（使用ELK或Loki）**：
```yaml
# docker-compose.yml中添加
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/loki

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
```

### 备份策略

**自动备份脚本** (`scripts/backup.sh`):

```bash
#!/bin/bash

# 配置
BACKUP_DIR="/backups"
POSTGRES_CONTAINER="postgres_prod"
OLLAMA_CONTAINER="ollama_prod"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR/postgres
mkdir -p $BACKUP_DIR/ollama

# 备份PostgreSQL
echo "Backing up PostgreSQL..."
docker exec $POSTGRES_CONTAINER pg_dump -U user imagedb | gzip > $BACKUP_DIR/postgres/imagedb_$DATE.sql.gz

# 备份Ollama模型和数据
echo "Backing up Ollama data..."
docker exec $OLLAMA_CONTAINER tar czf /tmp/ollama_backup_$DATE.tar.gz /root/.ollama
docker cp $OLLAMA_CONTAINER:/tmp/ollama_backup_$DATE.tar.gz $BACKUP_DIR/ollama/
docker exec $OLLAMA_CONTAINER rm /tmp/ollama_backup_$DATE.tar.gz

# 清理旧备份（保留7天）
find $BACKUP_DIR/postgres -name "*.sql.gz" -mtime +7 -delete
find $BACKUP_DIR/ollama -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

**配置定时任务**：
```bash
# 编辑crontab
crontab -e

# 每天凌晨2点执行备份
0 2 * * * /path/to/scripts/backup.sh >> /var/log/backup.log 2>&1
```

---

## 故障排查

### 常见问题

#### 1. Ollama服务无法启动

**症状**：
```bash
docker-compose up ollama
# 输出: Error: Cannot connect to the Docker daemon
```

**排查步骤**：
```bash
# 检查Docker服务
sudo systemctl status docker

# 检查端口占用
sudo netstat -tulpn | grep 11434

# 查看Ollama日志
docker logs ollama

# 检查GPU驱动（如果使用GPU）
nvidia-smi
```

**解决方案**：
- Docker未运行：`sudo systemctl start docker`
- 端口被占用：修改`docker-compose.yml`中的端口映射
- GPU驱动问题：重新安装NVIDIA驱动和CUDA

#### 2. 模型下载失败

**症状**：
```bash
ollama pull qwen2.5:7b
# 输出: Error: failed to download model
```

**排查步骤**：
```bash
# 检查网络连接
curl -I https://ollama.com

# 检查磁盘空间
df -h

# 查看Ollama日志
docker logs ollama
```

**解决方案**：
- 网络问题：配置代理或使用镜像
- 磁盘空间不足：清理磁盘或扩容
- 权限问题：`sudo chown -R $(whoami) ~/.ollama`

#### 3. API请求超时

**症状**：
```python
# Python客户端报错
httpx.ReadTimeout: The read operation timed out
```

**排查步骤**：
```bash
# 检查Ollama响应时间
time curl -X POST http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:7b",
  "messages": [{"role": "user", "content": "测试"}],
  "stream": false
}'

# 检查GPU使用情况
nvidia-smi

# 查看系统负载
htop
```

**解决方案**：
- 增加超时时间：`timeout=httpx.Timeout(120.0)`
- 减少并发数：`semaphore = asyncio.Semaphore(2)`
- 使用更小的模型：`qwen2:1.5b`
- 启用GPU加速（如果未启用）

#### 4. JSON解析错误

**症状**：
```python
# 代码报错
json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**排查步骤**：
```python
# 打印原始响应
logger.info(f"Raw response: {response['message']['content']}")

# 检查prompt设置
logger.info(f"System prompt: {system_prompt}")
```

**解决方案**：
- 强制JSON格式：`"format": "json"`
- 优化system prompt，明确要求JSON输出
- 降低temperature参数：`temperature=0.5`
- 添加JSON解析异常处理

#### 5. 内存溢出（OOM）

**症状**：
```bash
# Docker日志
docker logs ollama
# 输出: Out of memory: Killed process
```

**排查步骤**：
```bash
# 检查内存使用
docker stats ollama

# 检查GPU显存使用
nvidia-smi
```

**解决方案**：
- 限制Docker内存：在`docker-compose.yml`中添加`mem_limit: 16g`
- 限制GPU显存：`environment: - OLLAMA_GPU_MEMORY_LIMIT=8192`
- 减少并发模型数：`- OLLAMA_MAX_LOADED_MODELS=1`
- 使用量化模型：`qwen2.5:7b-q4_0`

### 调试技巧

**1. 启用详细日志**：
```python
import logging

# 设置日志级别
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

**2. 使用curl测试Ollama**：
```bash
# 测试基本连接
curl http://localhost:11434/api/tags

# 测试对话功能
curl http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:7b",
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "stream": false
}'

# 测试JSON格式输出
curl http://localhost:11434/api/chat -d '{
  "model": "qwen2.5:7b",
  "messages": [
    {"role": "system", "content": "请用JSON格式回答。"},
    {"role": "user", "content": "分析报告：双肺纹理增多。"}
  ],
  "format": "json",
  "stream": false
}'
```

**3. 监控性能指标**：
```python
import time

async def analyze_with_metrics(report_text: str):
    """带性能监控的分析"""
    start_time = time.time()

    try:
        result = await ollama_client.analyze_report(report_text, ...)

        duration = time.time() - start_time

        logger.info(f"Analysis completed in {duration:.2f}s")
        logger.info(f"Tokens: {result['eval_count']} eval, {result['prompt_eval_count']} prompt")
        logger.info(f"Speed: {result['eval_count'] / duration:.2f} tokens/s")

        return result

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Analysis failed after {duration:.2f}s: {e}")
        raise
```

---

## 附录

### 环境变量完整清单

```ini
# Ollama配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=60.0
OLLAMA_CONNECT_TIMEOUT=5.0
OLLAMA_MAX_CONCURRENT=3
OLLAMA_DEFAULT_TEMPERATURE=0.7
OLLAMA_GPU_MEMORY_LIMIT=8192
OLLAMA_NUM_PARALLEL=4
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_KEEP_ALIVE=24h

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/imagedb
POSTGRES_DB=imagedb
POSTGRES_USER=user
POSTGRES_PASSWORD=password

# JWT配置
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 应用配置
PROJECT_NAME=医疗报告AI分析平台
VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO
```

### 参考链接

- **Ollama官方文档**: https://ollama.com/docs
- **qwen2.5模型**: https://ollama.com/library/qwen2.5
- **FastAPI文档**: https://fastapi.tiangolo.com
- **httpx文档**: https://www.python-httpx.org
- **Docker文档**: https://docs.docker.com
- **NVIDIA Docker**: https://github.com/NVIDIA/nvidia-docker

### 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0.0 | 2024-12-01 | 初始版本，完整的Ollama集成指南 |

---

**文档维护**：AI集成团队
**联系方式**：ai-team@hospital.com
**最后审核**：2024-12-01
