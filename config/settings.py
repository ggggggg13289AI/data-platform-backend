"""
Django settings for medical imaging backend (Django + Django Ninja).
PostgreSQL database backend for production.
Pragmatic, minimal configuration - no over-engineering.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# URL Configuration - CRITICAL for Django
ROOT_URLCONF = "config.urls"

# Installed apps - minimal, no over-engineering
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "study",  # Study management
    "project",  # Project management
    "report",  # Report management
    "imports",  # Data import from CSV/Excel
    "common",  # Shared functionality
    "ai",  # AI assistant and prompt templates
    "corsheaders",
    "ninja_jwt",  # JWT authentication for Django Ninja
    "ninja_jwt.token_blacklist",  # Token blacklist for logout
]

# Middleware
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",  # MUST be before Auth and CSRF
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # MUST be after Session
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "common.middleware.RequestTimingMiddleware",  # Request timing logging
]

# CORS configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True

# Database - PostgreSQL (no DuckDB for Django)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "medical_imaging"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "postgres"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "client_encoding": "UTF8",
        },
    }
}

# Cache configuration - environment-aware
CACHE_BACKEND = os.getenv("CACHE_BACKEND", "locmem")

if CACHE_BACKEND == "redis":
    # Production: Redis cache
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {"max_connections": 50, "retry_on_timeout": True},
            },
        }
    }
else:
    # Development: Local memory cache (default)
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "study_cache",
            "OPTIONS": {"MAX_ENTRIES": 1000},
        }
    }

# Authentication
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Templates - Required for Django Ninja API docs
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Internationalization
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# Static files configuration - REQUIRED for Django Admin
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Default auto field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "debug.log",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "study": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
        },
        "project": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
        },
        "report": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
        },
        "common": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
        },
        "request_timing": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    },
}

# API Configuration
API_V1_STR = "/api/v1"
APP_NAME = "医疗影像管理系统"  # Medical Imaging Management System
APP_VERSION = "1.1.0"

# JWT Configuration
NINJA_JWT = {
    # Token Lifetimes
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),  # 1 hour access token
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),  # 7 days refresh token
    "ROTATE_REFRESH_TOKENS": True,  # Issue new refresh token on refresh
    "BLACKLIST_AFTER_ROTATION": True,  # Blacklist old refresh tokens for security
    "UPDATE_LAST_LOGIN": True,  # Update User.last_login field on authentication
    # Token Configuration
    "ALGORITHM": "HS256",  # HMAC using SHA-256
    "SIGNING_KEY": SECRET_KEY,  # Use Django's SECRET_KEY for signing
    "VERIFYING_KEY": None,  # Not needed for symmetric algorithm
    "AUDIENCE": None,
    "ISSUER": None,
    # Authentication Header
    "AUTH_HEADER_TYPES": ("Bearer",),  # Frontend sends "Authorization: Bearer <token>"
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",  # User model primary key field
    "USER_ID_CLAIM": "user_id",  # JWT claim for user ID
    # Token Claims
    "AUTH_TOKEN_CLASSES": ("ninja_jwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",  # JWT ID claim for token tracking
    # Sliding Tokens (optional, disabled by default)
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# AI Configuration - Multi-Provider LLM Integration
# Supports: Ollama, LM Studio, vLLM, LocalAI, Text Generation WebUI, etc.
AI_CONFIG = {
    # Default LLM Provider (ollama, lmstudio, vllm, localai, openai_compatible)
    "PROVIDER": os.getenv("AI_PROVIDER", "ollama"),
    # Default Model (provider-specific)
    "MODEL": os.getenv("AI_MODEL", "qwen2.5:7b"),
    # Default API Base URL (provider-specific)
    "API_BASE": os.getenv("AI_API_BASE", os.getenv("OLLAMA_API_BASE", "http://localhost:11434")),
    # Optional API Key (for OpenAI-compatible providers)
    "API_KEY": os.getenv("AI_API_KEY", ""),
    # Request Settings
    "TIMEOUT": int(os.getenv("AI_TIMEOUT", "120")),
    "MAX_TOKENS": int(os.getenv("AI_MAX_TOKENS", "4096")),
    "TEMPERATURE": float(os.getenv("AI_TEMPERATURE", "0.7")),
    # Rate Limiting
    "MAX_CONCURRENT_REQUESTS": int(os.getenv("AI_MAX_CONCURRENT", "5")),
    # Retry Settings
    "MAX_RETRIES": int(os.getenv("AI_MAX_RETRIES", "3")),
    "RETRY_DELAY": float(os.getenv("AI_RETRY_DELAY", "2.0")),
}

# Provider-specific configurations (optional overrides)
# Each provider can have its own API_BASE, MODEL, and other settings
AI_PROVIDERS = {
    "ollama": {
        "API_BASE": os.getenv("OLLAMA_API_BASE", "http://localhost:11434"),
        "MODEL": os.getenv("OLLAMA_MODEL", os.getenv("AI_MODEL", "qwen2.5:7b")),
    },
    "lmstudio": {
        "API_BASE": os.getenv("LMSTUDIO_API_BASE", "http://localhost:1234/v1"),
        "MODEL": os.getenv("LMSTUDIO_MODEL", "local-model"),
    },
    "vllm": {
        "API_BASE": os.getenv("VLLM_API_BASE", "http://localhost:8000/v1"),
        "MODEL": os.getenv("VLLM_MODEL", "default"),
        "API_KEY": os.getenv("VLLM_API_KEY", ""),
    },
    "localai": {
        "API_BASE": os.getenv("LOCALAI_API_BASE", "http://localhost:8080/v1"),
        "MODEL": os.getenv("LOCALAI_MODEL", "default"),
    },
    "text_generation_webui": {
        "API_BASE": os.getenv("TGWUI_API_BASE", "http://localhost:5000/v1"),
        "MODEL": os.getenv("TGWUI_MODEL", "default"),
    },
}

# Funboost Configuration - Distributed Task Framework
# See: https://github.com/ydf0509/funboost
FUNBOOST_CONFIG = {
    # Broker type: SQLITE_QUEUE for dev, REDIS_ACK_ABLE for production
    "BROKER_KIND": os.getenv("FUNBOOST_BROKER", "SQLITE_QUEUE"),
    # Concurrent workers for batch analysis
    "CONCURRENT_NUM": int(os.getenv("FUNBOOST_CONCURRENT", "3")),
    # Rate limit for LLM calls (queries per second)
    "QPS": float(os.getenv("FUNBOOST_QPS", "2")),
    # Retry configuration
    "MAX_RETRY_TIMES": int(os.getenv("FUNBOOST_MAX_RETRY", "3")),
    "RETRY_INTERVAL": int(os.getenv("FUNBOOST_RETRY_INTERVAL", "5")),
}

# Redis URL for production funboost (reuses existing REDIS_URL if available)
FUNBOOST_REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
