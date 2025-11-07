# 緩存配置快速設置指南

## ⚡ 快速設置 (2分鐘)

### 選項A: 開發環境 (推薦用於開發測試)

將以下代碼添加到 `config/settings.py` (在DATABASES配置之後):

```python
# Cache configuration for development
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'study_cache',
    }
}
```

### 選項B: 生產環境 (需要Redis)

1. **安裝Redis** (如果還未安裝):
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Windows: 下載或使用Docker
docker run -d -p 6379:6379 redis:latest
```

2. **安裝Django Redis客戶端**:
```bash
pip install django-redis
```

3. **添加到** `config/settings.py`:
```python
# Cache configuration for production
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50}
        }
    }
}
```

---

## ✅ 驗證設置

### 1. 運行測試
```bash
cd backend_django
python manage.py shell

# 測試緩存
from django.core.cache import cache
cache.set('test_key', 'test_value', 300)
print(cache.get('test_key'))  # 應該返回: test_value
```

### 2. 測試API優化

```bash
# 啟動Django服務器
python manage.py runserver

# 在另一個終端測試
curl "http://localhost:8000/api/v1/studies/filters/options"
```

### 3. 監控日誌
```bash
# 查看是否有緩存日誌
tail -f debug.log | grep "Filter options"
```

應該看到:
- 首次: `Filter options cache miss - querying database`
- 後續: `Filter options served from cache`

---

## 🔧 配置文件位置

編輯文件: `config/settings.py`

**在以下位置添加**:

```
約第68行 (DATABASES配置之後):

DATABASES = {
    'default': {
        ...
    }
}

# 在這裡添加CACHES配置 ↓

CACHES = { ... }
```

---

## 📋 完整示例

### 開發環境完整配置

```python
# config/settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'medical_imaging'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# 新增: 緩存配置
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'study_cache',
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# 其他配置...
```

### 生產環境完整配置

```python
# config/settings.py

# 使用環境變數控制緩存後端
CACHE_BACKEND = os.getenv('CACHE_BACKEND', 'locmem')

if CACHE_BACKEND == 'redis':
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 50,
                    'retry_on_timeout': True
                }
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'study_cache',
            'OPTIONS': {'MAX_ENTRIES': 1000}
        }
    }
```

---

## 🚀 部署清單

- [ ] 添加CACHES配置到settings.py
- [ ] 如使用Redis, 安裝django-redis: `pip install django-redis`
- [ ] 如使用Redis, 啟動Redis服務
- [ ] 運行驗證: `python manage.py shell` + 緩存測試
- [ ] 測試API端點: `curl .../filters/options`
- [ ] 查看日誌確認緩存命中
- [ ] 生產環境配置Redis連接字符串
- [ ] 部署更新

---

## 📊 預期效果

配置完成後:

| 指標 | 優化前 | 優化後 |
|------|------|------|
| `/api/v1/studies/filters/options` | 80-100ms | 5-10ms (95%命中) |
| 整體搜索API | 800-1000ms | 400-500ms |

---

## 🐛 故障排查

### 問題1: 「ModuleNotFoundError: django_redis」

**解決方案**:
```bash
pip install django-redis
```

### 問題2: 「ConnectionError: Error 111 connecting to 127.0.0.1:6379」

**解決方案** (Redis未運行):
```bash
# 啟動Redis
redis-server

# 或使用Docker
docker run -d -p 6379:6379 redis:latest
```

### 問題3: 緩存不工作

**診斷**:
```bash
python manage.py shell

from django.core.cache import cache
print(cache.get('test'))  # 應該返回None或'value'

# 檢查配置
from django.conf import settings
print(settings.CACHES)
```

---

## 📞 需要幫助?

查看完整的優化文檔: `OPTIMIZATION_IMPLEMENTATION.md`

性能測試步驟: 見優化文檔中的「性能測試結果」部分

---

**最後更新**: 2025-11-07
**難度等級**: ⭐ 簡單 (5分鐘內完成)
