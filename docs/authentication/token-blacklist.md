# TokenBlackList 機制說明

**版本**: v1.1.0
**最後更新**: 2025-01-13
**狀態**: Production Ready

---

## 📋 目錄

1. [概述](#1-概述)
2. [TokenBlackList 機制](#2-tokenblacklist-機制)
3. [資料表結構](#3-資料表結構)
4. [運作流程](#4-運作流程)
5. [清理策略](#5-清理策略)
6. [監控建議](#6-監控建議)
7. [故障排查](#7-故障排查)
8. [管理指令](#8-管理指令)

---

## 1. 概述

### 什麼是 TokenBlackList?

TokenBlackList 是 JWT (JSON Web Token) 認證系統的重要組成部分，用於：

- **Token 撤銷**: 在 token 過期前主動撤銷其有效性
- **Refresh Token 輪換**: 實現 refresh token rotation 機制
- **安全性增強**: 防止已撤銷的 token 被重複使用
- **審計追蹤**: 記錄所有發行與撤銷的 token

### 為什麼需要 TokenBlackList?

JWT token 本身是無狀態的 (stateless)，一旦簽發就無法主動撤銷。TokenBlackList 提供了一個「狀態層」，讓我們能夠：

1. **用戶登出**: 將 token 加入黑名單，即使未過期也無法使用
2. **Token 輪換**: Refresh token 使用後立即失效，增強安全性
3. **異常行為偵測**: 追蹤並撤銷可疑的 token
4. **權限變更**: 用戶權限變更時強制重新認證

---

## 2. TokenBlackList 機制

### 配置說明

`config/settings.py` 中的 NINJA_JWT 配置：

```python
NINJA_JWT = {
    # Token 生命週期
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),

    # Token 輪換與黑名單配置
    'ROTATE_REFRESH_TOKENS': True,  # 啟用 refresh token 輪換
    'BLACKLIST_AFTER_ROTATION': True,  # 輪換後將舊 token 加入黑名單
    'UPDATE_LAST_LOGIN': True,  # 更新用戶最後登入時間

    # Token 配置
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
}
```

### 配置參數解釋

#### ROTATE_REFRESH_TOKENS = True

**行為**: 每次使用 refresh token 時，產生新的 access + refresh token pair，並將舊的 refresh token 失效。

**優點**:
- 增強安全性：限制 refresh token 的使用時間窗口
- 防止 token 重放攻擊
- 限制被竊取的 refresh token 的有效期

**流程**:
```
1. Client 使用 Refresh Token A 請求新 Access Token
2. Server 驗證 Refresh Token A 有效
3. Server 生成新的 Access Token B + Refresh Token B
4. Server 將 Refresh Token A 加入黑名單
5. 返回 Token B pair 給 Client
```

#### BLACKLIST_AFTER_ROTATION = True

**行為**: 與 `ROTATE_REFRESH_TOKENS` 配合，自動將舊的 refresh token 加入 `BlacklistedToken` 表。

**重要性**:
- 防止舊 token 被重複使用
- 即使 token 在有效期內，黑名單中的 token 仍然無效
- 提供審計追蹤能力

#### UPDATE_LAST_LOGIN = True

**行為**: Token refresh 時更新 `User.last_login` 欄位。

**用途**:
- 追蹤用戶活躍度
- 偵測異常登入模式
- 實作"長時間未使用自動登出"機制

---

## 3. 資料表結構

### OutstandingToken Model

記錄所有發行的 token (access 和 refresh)。

```python
class OutstandingToken(models.Model):
    """
    所有發行的 token 記錄

    每次生成 access token 或 refresh token 時，都會在此表建立記錄。
    """

    # 主鍵與識別
    id = models.BigAutoField(primary_key=True)
    jti = models.CharField(max_length=255, unique=True, db_index=True)
        # jti (JWT ID): token 的唯一識別碼

    # Token 內容
    token = models.TextField()  # 完整的 JWT token 字串
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    # 時間戳記
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # Token 過期時間

    class Meta:
        db_table = 'token_blacklist_outstandingtoken'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['jti']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['expires_at']),
        ]
```

### BlacklistedToken Model

記錄被撤銷/黑名單的 token。

```python
class BlacklistedToken(models.Model):
    """
    被撤銷的 token 黑名單

    只要 token 被加入此表，即使未過期也無法使用。
    """

    # 主鍵與關聯
    id = models.BigAutoField(primary_key=True)
    token = models.OneToOneField(
        OutstandingToken,
        on_delete=models.CASCADE,
        related_name='blacklisted'
    )

    # 時間戳記
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'token_blacklist_blacklistedtoken'
        ordering = ['-blacklisted_at']
        indexes = [
            models.Index(fields=['blacklisted_at']),
        ]
```

### 索引策略

```sql
-- OutstandingToken 索引
CREATE INDEX idx_outstandingtoken_jti ON token_blacklist_outstandingtoken(jti);
CREATE INDEX idx_outstandingtoken_user_created ON token_blacklist_outstandingtoken(user_id, created_at);
CREATE INDEX idx_outstandingtoken_expires ON token_blacklist_outstandingtoken(expires_at);

-- BlacklistedToken 索引
CREATE INDEX idx_blacklistedtoken_created ON token_blacklist_blacklistedtoken(blacklisted_at);

-- 優化查詢效能
-- 1. jti 索引: 快速查找特定 token
-- 2. user_id + created_at 索引: 用戶 token 歷史查詢
-- 3. expires_at 索引: 清理過期 token
```

---

## 4. 運作流程

### Token 生成流程

```
1. 用戶登入 (POST /api/v1/auth/login)
   ↓
2. 驗證帳號密碼
   ↓
3. 生成 Access Token + Refresh Token
   ↓
4. 記錄至 OutstandingToken 表
   - Access Token 記錄 (jti_access, expires in 1 hour)
   - Refresh Token 記錄 (jti_refresh, expires in 7 days)
   ↓
5. 返回 token pair 給客戶端
```

### Token 驗證流程

```
1. 客戶端請求受保護端點 (Authorization: Bearer <token>)
   ↓
2. 提取 JWT token 並解碼
   ↓
3. 驗證 token signature (使用 SECRET_KEY)
   ↓
4. 檢查 token 是否過期 (exp claim)
   ↓
5. 從 token 取得 jti (JWT ID)
   ↓
6. 查詢 BlacklistedToken 表 (通過 OutstandingToken.jti)
   ↓
7. 如果 jti 在黑名單 → 拒絕請求 (401 Unauthorized)
   ↓
8. 如果 jti 不在黑名單 → 允許請求
```

### Token 輪換流程 (Refresh)

```
1. 客戶端使用 Refresh Token 請求新 Access Token
   POST /api/v1/auth/token/refresh
   Body: {"refresh_token": "<old_refresh_token>"}
   ↓
2. 驗證 Refresh Token (signature + expiration)
   ↓
3. 檢查 Refresh Token 是否在黑名單
   ↓
4. 生成新的 Access Token + 新的 Refresh Token
   ↓
5. 將舊的 Refresh Token 加入黑名單
   - 在 OutstandingToken 找到舊 refresh token
   - 建立 BlacklistedToken 記錄指向它
   ↓
6. 記錄新的 token pair 至 OutstandingToken
   ↓
7. 返回新的 token pair 給客戶端
```

### Token 撤銷流程 (Logout)

```
1. 用戶登出 (POST /api/v1/auth/logout)
   Body: {"refresh_token": "<refresh_token>"}
   ↓
2. 驗證 Refresh Token
   ↓
3. 將 Refresh Token 加入黑名單
   - OutstandingToken.objects.get(jti=refresh_jti)
   - BlacklistedToken.objects.create(token=outstanding_token)
   ↓
4. (可選) 同時撤銷對應的 Access Token
   - 找到同一用戶的相關 access token
   - 加入黑名單
   ↓
5. 返回登出成功
```

---

## 5. 清理策略

### 為什麼需要清理?

隨著時間推移，OutstandingToken 和 BlacklistedToken 表會持續增長：

- **每次登入**: +2 records (access + refresh)
- **每次 refresh**: +2 new, +1 blacklisted
- **每天 1000 用戶登入**: +2000 records/day
- **30 天**: +60,000 records

**問題**:
- 資料表大小無限增長
- 查詢效能下降 (索引變大)
- 儲存成本增加
- 備份時間延長

### 清理原則

```yaml
保留策略:
  OutstandingToken:
    - 保留未過期的 token (expires_at > now)
    - 保留最近 30 天的審計記錄 (created_at >= now - 30 days)

  BlacklistedToken:
    - 保留對應 OutstandingToken 未刪除的記錄
    - OutstandingToken 刪除時自動刪除 (CASCADE)

清理週期:
  - 建議: 每日執行 (凌晨 02:00)
  - 最少: 每週執行一次
  - 高流量系統: 每 12 小時執行一次

審計保留:
  - 建議保留 30 天記錄供審計
  - 符合性要求: 可能需要 90 天或更長
```

### 自動清理腳本

使用 Django management command:

```bash
# 預覽將清理的記錄 (不實際刪除)
python manage.py cleanup_tokens --days=30 --dry-run

# 執行清理 (刪除 30 天前過期的 token)
python manage.py cleanup_tokens --days=30

# 清理 7 天前過期的 token (較激進)
python manage.py cleanup_tokens --days=7
```

### Cron Job 配置

```bash
# crontab -e

# 每日凌晨 2:00 清理 30 天前過期的 token
0 2 * * * cd /path/to/backend_django && python manage.py cleanup_tokens --days=30 >> /var/log/token_cleanup.log 2>&1
```

### 手動清理 SQL (緊急使用)

```sql
-- ⚠️ 警告: 在執行前先備份資料庫

-- Step 1: 找出過期的 OutstandingToken (> 30 days old)
SELECT COUNT(*) FROM token_blacklist_outstandingtoken
WHERE expires_at < (NOW() - INTERVAL '30 days');

-- Step 2: 刪除對應的 BlacklistedToken (自動 CASCADE)
DELETE FROM token_blacklist_outstandingtoken
WHERE expires_at < (NOW() - INTERVAL '30 days');

-- Step 3: 驗證刪除結果
SELECT
    (SELECT COUNT(*) FROM token_blacklist_outstandingtoken) AS outstanding_count,
    (SELECT COUNT(*) FROM token_blacklist_blacklistedtoken) AS blacklisted_count;

-- Step 4: VACUUM 釋放磁碟空間 (PostgreSQL)
VACUUM FULL token_blacklist_outstandingtoken;
VACUUM FULL token_blacklist_blacklistedtoken;
```

---

## 6. 監控建議

### 關鍵指標

```yaml
表大小監控:
  metric: token_blacklist_outstandingtoken_size_mb
  threshold:
    warning: > 500 MB
    critical: > 1 GB
  query: |
    SELECT
      pg_size_pretty(pg_total_relation_size('token_blacklist_outstandingtoken'))
    AS size;

記錄數量監控:
  metric: token_blacklist_record_count
  threshold:
    warning: > 1,000,000
    critical: > 5,000,000
  query: |
    SELECT COUNT(*) FROM token_blacklist_outstandingtoken;

過期 Token 比例:
  metric: expired_token_percentage
  threshold:
    warning: > 30%
    critical: > 50%
  query: |
    SELECT
      (COUNT(*) FILTER (WHERE expires_at < NOW())::FLOAT /
       COUNT(*)::FLOAT * 100) AS expired_percentage
    FROM token_blacklist_outstandingtoken;

黑名單增長率:
  metric: blacklist_growth_rate_per_day
  threshold:
    warning: > 10,000/day
    critical: > 50,000/day
  query: |
    SELECT COUNT(*) / 7.0 AS avg_per_day
    FROM token_blacklist_blacklistedtoken
    WHERE blacklisted_at >= (NOW() - INTERVAL '7 days');
```

### Grafana Dashboard 範例

```yaml
Dashboard: JWT TokenBlackList Monitoring

Panels:
  1. Token Count Over Time:
     - Line chart
     - OutstandingToken count (daily)
     - BlacklistedToken count (daily)

  2. Table Size Trend:
     - Area chart
     - Total table size (MB)
     - 30-day trend

  3. Expired Token Ratio:
     - Gauge chart
     - % of expired tokens
     - Alert at 30%

  4. Daily Blacklist Operations:
     - Bar chart
     - New blacklisted tokens per day
     - Login/logout activity correlation

  5. Top Users by Token Count:
     - Table
     - User ID
     - Active token count
     - Identify anomalies
```

### 告警規則

```yaml
Alert_1_Table_Size_Critical:
  condition: token_blacklist_size_mb > 1000
  severity: critical
  action: "Immediate cleanup required. Run: python manage.py cleanup_tokens --days=7"

Alert_2_Expired_Token_Buildup:
  condition: expired_token_percentage > 50
  severity: warning
  action: "Schedule cleanup job. Verify cron is running."

Alert_3_Unusual_Blacklist_Growth:
  condition: blacklist_growth_rate_per_day > 50000
  severity: warning
  action: "Investigate: Potential token abuse or bot activity"

Alert_4_Cleanup_Job_Failure:
  condition: last_cleanup_job_status == 'failed'
  severity: critical
  action: "Check cleanup job logs. Manual intervention required."
```

---

## 7. 故障排查

### 問題 1: Token 驗證失敗 (token_not_valid)

**症狀**:
```json
{
  "detail": "token_not_valid",
  "code": "token_not_valid",
  "messages": [{"message": "令牌無效或已過期"}]
}
```

**可能原因**:
1. Token 在黑名單中
2. Token 已過期
3. SECRET_KEY 不一致
4. Token 格式錯誤

**排查步驟**:
```python
# Step 1: 解碼 token 不驗證簽名
import jwt
token = "eyJhbGci..."
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded)  # 檢查 exp, jti, user_id

# Step 2: 檢查 token 是否在黑名單
from token_blacklist.models import OutstandingToken, BlacklistedToken
jti = decoded['jti']
outstanding = OutstandingToken.objects.filter(jti=jti).first()
if outstanding:
    blacklisted = BlacklistedToken.objects.filter(token=outstanding).exists()
    print(f"In blacklist: {blacklisted}")

# Step 3: 驗證 SECRET_KEY 一致性
from django.conf import settings
print(settings.SECRET_KEY)  # 確認與 token 生成時相同
```

### 問題 2: 清理 Job 失敗

**症狀**:
```bash
$ python manage.py cleanup_tokens --days=30
Error: DatabaseError: relation does not exist
```

**可能原因**:
- Migration 未執行
- 資料庫連線問題
- Permission 不足

**排查步驟**:
```bash
# 1. 檢查 migration 狀態
python manage.py showmigrations token_blacklist

# 2. 執行 migration
python manage.py migrate token_blacklist

# 3. 檢查資料表存在
python manage.py dbshell
\dt token_blacklist_*

# 4. 檢查權限
GRANT ALL ON token_blacklist_outstandingtoken TO your_user;
GRANT ALL ON token_blacklist_blacklistedtoken TO your_user;
```

### 問題 3: 資料表大小持續增長

**症狀**:
- OutstandingToken 表超過 1GB
- 查詢變慢
- Backup 時間過長

**排查步驟**:
```sql
-- 1. 檢查記錄分布
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE expires_at < NOW()) AS expired,
    COUNT(*) FILTER (WHERE expires_at >= NOW()) AS active
FROM token_blacklist_outstandingtoken;

-- 2. 檢查最舊的記錄
SELECT MIN(created_at), MAX(created_at)
FROM token_blacklist_outstandingtoken;

-- 3. 檢查 cron job 是否執行
grep "cleanup_tokens" /var/log/token_cleanup.log
```

**解決方案**:
```bash
# 1. 立即手動清理
python manage.py cleanup_tokens --days=7

# 2. 確認 cron job 配置
crontab -l | grep cleanup_tokens

# 3. 如果仍然過大，考慮刪除更多歷史記錄
python manage.py cleanup_tokens --days=3  # 更激進

# 4. VACUUM 回收空間
python manage.py dbshell
VACUUM FULL token_blacklist_outstandingtoken;
```

---

## 8. 管理指令

### cleanup_tokens Command

**位置**: `studies/management/commands/cleanup_tokens.py`

**用法**:
```bash
python manage.py cleanup_tokens [OPTIONS]

Options:
  --days=DAYS     保留最近 N 天的記錄 (default: 30)
  --dry-run       預覽模式，不實際刪除 (default: False)
  --verbose       顯示詳細輸出 (default: False)
```

**範例**:
```bash
# 預覽將清理的記錄
python manage.py cleanup_tokens --days=30 --dry-run --verbose

# 輸出:
# [DRY RUN] Would delete 45,123 expired OutstandingTokens
# [DRY RUN] Would delete 12,456 BlacklistedTokens (via CASCADE)
# [DRY RUN] Estimated space savings: 127 MB

# 執行實際清理
python manage.py cleanup_tokens --days=30 --verbose

# 輸出:
# Deleted 45,123 OutstandingTokens
# Deleted 12,456 BlacklistedTokens (via CASCADE)
# Database size before: 1.2 GB
# Database size after: 1.07 GB
# Space saved: 130 MB
```

### 實作範例

```python
# studies/management/commands/cleanup_tokens.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from token_blacklist.models import OutstandingToken, BlacklistedToken

class Command(BaseCommand):
    help = 'Clean up expired tokens from TokenBlackList'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Keep tokens from last N days (default: 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview without actual deletion',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        # Find expired tokens
        expired_tokens = OutstandingToken.objects.filter(
            expires_at__lt=cutoff_date
        )

        count = expired_tokens.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] Would delete {count} expired tokens'
                )
            )
        else:
            # Delete (CASCADE will handle BlacklistedToken)
            deleted_count, _ = expired_tokens.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} expired tokens'
                )
            )
```

---

## 📊 總結

### 最佳實踐

```yaml
配置:
  - ✅ 啟用 ROTATE_REFRESH_TOKENS
  - ✅ 啟用 BLACKLIST_AFTER_ROTATION
  - ✅ 設定合理的 token lifetime (access: 1h, refresh: 7d)

維護:
  - ✅ 每日自動清理過期 token (30 days)
  - ✅ 監控資料表大小與增長率
  - ✅ 定期檢查清理 job 執行狀態

安全性:
  - ✅ 登出時撤銷 refresh token
  - ✅ 權限變更時撤銷所有 token
  - ✅ 偵測異常活動並自動撤銷

監控:
  - ✅ 設定資料表大小告警 (> 1GB)
  - ✅ 設定過期 token 比例告警 (> 50%)
  - ✅ 追蹤黑名單增長率
```

### 常見問題 FAQ

**Q: 為什麼 token refresh 後舊 token 還能用?**
A: 檢查 `BLACKLIST_AFTER_ROTATION` 是否為 `True`。如果為 `False`，舊 refresh token 不會被撤銷。

**Q: 清理 token 會影響線上用戶嗎?**
A: 不會。清理只刪除已過期的 token。未過期的 access/refresh token 不受影響。

**Q: 如何立即撤銷所有用戶的 token (緊急安全事件)?**
A: 使用 SQL 清空黑名單表，或變更 `SECRET_KEY` (會使所有 token 失效)。

**Q: 資料表過大會影響 token 驗證效能嗎?**
A: 會。建議保持 OutstandingToken < 1M records。使用索引和定期清理。

**Q: 可以完全不使用 TokenBlackList 嗎?**
A: 可以，但會失去 token 撤銷能力。純粹的 stateless JWT 無法在過期前撤銷。

---

**文件維護**: 隨系統升級更新
**負責人**: Backend Security Team
**最後更新**: 2025-01-13

🤖 Generated with [Claude Code](https://claude.com/claude-code)
