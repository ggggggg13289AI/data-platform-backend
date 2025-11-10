# 醫療影像管理系統 Django 後端

**Medical Imaging Management System - Django Backend**

---

## 🌐 選擇語言 / Choose Language

- **[📖 繁體中文 (預設)](docs/README.zh-TW.md)** ← Default
- **[📖 English](docs/README.en.md)**

---

## 快速開始 / Quick Start

這是基於 Django + PostgreSQL 的醫療影像管理系統後端，提供 REST API 供前端應用程式使用。

This is a Django + PostgreSQL backend for the Medical Imaging Management System, providing REST API for frontend applications.

### 主要特色 / Key Features

- ✅ **務實設計** / Pragmatic Design - 為實際需求而非理論完美
- ✅ **扁平架構** / Flat Architecture - 單一資料表，無過度正規化
- ✅ **Django Ninja** - FastAPI 風格的 Django REST 框架
- ✅ **PostgreSQL** - 穩定可靠的關聯式資料庫
- ✅ **完整測試** / Comprehensive Testing - API 契約測試確保相容性

### 技術堆疊 / Tech Stack

```
Django 4.x + Django Ninja
PostgreSQL Database
Python 3.10+
Pydantic Schemas
```

### 快速啟動 / Quick Launch

```bash
# 1. 安裝相依套件 / Install dependencies
pip install -r requirements.txt

# 2. 設定資料庫 / Setup database
python manage.py migrate

# 3. 啟動開發伺服器 / Start development server
python manage.py runserver 8001
```

### API 文件 / API Documentation

啟動伺服器後，訪問 / After starting the server, visit:
- **API Docs**: http://localhost:8001/api/v1/docs
- **Health Check**: http://localhost:8001/api/v1/health

---

## 📚 完整文件 / Full Documentation

請選擇您偏好的語言閱讀完整安裝指南、API 說明和疑難排解：

Please choose your preferred language for complete setup guide, API documentation, and troubleshooting:

- **[📖 繁體中文完整文件](docs/README.zh-TW.md)** ← 預設 / Default
- **[📖 English Full Documentation](docs/README.en.md)**

---

## 專案結構 / Project Structure

```
backend_django/
├── config/          # Django 設定 / Django configuration
├── studies/         # 主要應用程式 / Main application
├── docs/            # 多語言文件 / Multilingual documentation
│   ├── README.zh-TW.md  # 繁體中文 / Traditional Chinese
│   └── README.en.md     # English
├── tests/           # 測試套件 / Test suite
└── manage.py        # Django 管理 / Django management
```

---

## 授權 / License

請參閱專案授權文件 / See project license documentation

---

**狀態 / Status**: ✅ 生產就緒 / Production Ready
**版本 / Version**: 1.0.0
**維護者 / Maintainer**: Medical Imaging Team
