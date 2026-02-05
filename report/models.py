"""
Report 模型模組 - 提供報告儲存、版本控制與去重功能。

本模組實現了完整的報告生命週期管理，包括：
- 內容去重：基於 SHA256 雜湊與時間戳進行智能去重
- 版本控制：追蹤所有版本變更和修改歷史
- 全文搜尋支援：PostgreSQL 全文搜尋向量化
- 靈活的元資料儲存：JSON 格式的動態屬性存儲

設計原則：
- 扁平化結構：避免過多的外鍵關聯，使用去正規化提升查詢效能
- 高效索引策略：對常用查詢欄位建立複合索引
- 原子性事務：保障導入和更新操作的資料一致性

----------
"""

import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models


class Report(models.Model):
    """
    網頁爬蟲報告儲存模型 - 支援版本控制與去重功能。

    二維、大小可變、可能異質的表格式資料結構。

    此模型儲存來自網頁爬蟲的醫療報告，支援完整的版本控制和內容去重。

    特性
    --------
    - Content-based deduplication (hash + time): 基於內容雜湊和時間戳的智能去重
    - Version control (tracks all versions): 完整追蹤所有版本變更
    - Full-text search support: 支援 PostgreSQL 全文搜尋
    - Flexible metadata storage: 使用 JSON 儲存動態屬性
    - Efficient indexing: 複合索引優化查詢效能

    參數
    ----------
    uid : CharField
        原始爬蟲標識符，主鍵。從遺留資料庫相容性考量，最大長度 56 字元
        預設: 必填
    report_id : CharField
        內部報告編號，可用於系統識別
        預設: 可為空
    title : CharField
        報告標題，最大長度 500 字元
        預設: 必填
    report_type : CharField
        報告格式類型 (PDF, HTML, TXT, XRay, MRI, CT 等)
        預設: 必填
    content_raw : TextField
        原始報告內容，未經處理
        預設: 必填
    content_processed : TextField
        經過處理的報告內容，用於全文搜尋
        預設: 可為空
    content_hash : CharField
        內容的 SHA256 雜湊值，用於去重
        預設: 必填
    version_number : IntegerField
        版本號，從 1 開始遞增
        預設: 1
    is_latest : BooleanField
        是否為最新版本，確保查詢時只取得最新版本
        預設: True
    source_url : URLField
        原始爬蟲來源 URL
        預設: 必填
    chr_no : CharField
        字符代碼（來自遺留系統）
        預設: 可為空
    mod : CharField
        模式/類型代碼（來自遺留系統）
        預設: 可為空
    report_date : CharField
        報告日期字符串表示
        預設: 可為空
    created_at : DateTimeField
        記錄創建時間戳，自動設定
        預設: 自動設定為當前時間
    updated_at : DateTimeField
        記錄更新時間戳，每次修改自動更新
        預設: 自動設定為當前時間
    verified_at : DateTimeField
        報告驗證時間戳，用於排序和去重判定
        預設: 可為空
    metadata : JSONField
        動態元資料，儲存額外的特定領域資訊
        預設: 空字典 {}
    search_vector : SearchVectorField
        PostgreSQL 全文搜尋向量，自動生成
        預設: 可為空

    設計原則
    -------
    - 扁平化結構: 避免過多外鍵關聯，通過去正規化提升查詢效能
    - 數據驅動型索引: 對常用查詢欄位建立複合索引
    - 原子性事務: 使用 @transaction.atomic 保障多步操作的一致性
    - Good Taste 編碼: 消除特殊情況處理，使用資料結構驅動邏輯

    注意事項
    -------
    去重策略:
        - 若 uid 相同且內容雜湊相同: 保留驗證時間戳較新的版本
        - 若 uid 相同但內容不同: 自動建立新版本記錄
        - 版本號遞增，舊版本標記 is_latest=False

    索引策略:
        1. uid: 主鍵索引，快速 UID 查詢
        2. (content_hash, verified_at): 複合索引，加速去重判定
        3. (source_url, verified_at): 複合索引，加速來源查詢
        4. (is_latest, verified_at): 複合索引，加速最新版本查詢
        5. search_vector: GIN 全文搜尋索引

    範例
    --------
    建立新報告:

    >>> from report.models import Report
    >>> from datetime import datetime
    >>> report = Report.objects.create(
    ...     uid='uid_001',
    ...     report_id='exam_123',
    ...     title='CT 掃描報告',
    ...     report_type='CT',
    ...     content_raw='報告正文內容...',
    ...     source_url='https://example.com/reports/001',
    ...     verified_at=datetime.now()
    ... )

    查詢最新版本:

    >>> latest = Report.objects.filter(is_latest=True).order_by('-verified_at')[:10]

    搜尋內容:

    >>> from django.db.models import Q
    >>> results = Report.objects.filter(
    ...     Q(title__icontains='關鍵字') |
    ...     Q(content_processed__icontains='關鍵字'),
    ...     is_latest=True
    ... ).order_by('-verified_at')

    參考資訊
    --------
    - ReportVersion: 完整的版本歷史記錄模型
    - ReportSummary: 報告摘要儲存模型
    - ReportSearchIndex: 全文搜尋索引模型
    - AIAnnotation: AI 註解儲存模型

    另見
    ----
    ReportService: 報告管理的業務邏輯層
    ReportVersion: 版本歷史追蹤
    """

    # ============================================================================
    # 唯一識別欄位 - 用於區別和查詢不同的報告
    # ============================================================================

    uid = models.CharField(
        max_length=100,
        primary_key=True,
        db_index=True,
        help_text="原始爬蟲標識符，為主鍵。相容遺留資料庫中最大 56 字元的 UID",
    )
    """原始爬蟲 UID，主鍵，最多 100 字元"""

    report_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="系統內部報告編號，用於與外部系統對應",
    )
    """內部報告編號，可為空"""

    # ============================================================================
    # 基本信息欄位 - 儲存報告的主要內容和元資訊
    # ============================================================================

    title = models.CharField(max_length=500, db_index=True, help_text="報告標題，用於檢索和展示")
    """報告標題，最大 500 字元"""

    report_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="報告格式類型 (PDF, HTML, TXT, XRay, MRI, CT, Ultrasound 等)",
    )
    """報告類型 (PDF/HTML/TXT/XRay/MRI/CT 等)"""

    content_raw = models.TextField(help_text="原始報告內容，完整保存爬蟲結果")
    """原始報告內容"""

    content_processed = models.TextField(
        null=True, blank=True, help_text="經正規化處理的報告內容，用於全文搜尋"
    )
    """經處理的報告內容，用於搜尋"""

    # ============================================================================
    # 去重與版本控制欄位 - 支援版本追蹤和內容去重
    # ============================================================================

    content_hash = models.CharField(
        max_length=64, db_index=True, help_text="內容 SHA256 雜湊值，用於快速去重"
    )
    """內容 SHA256 雜湊，用於去重"""

    version_number = models.IntegerField(default=1, help_text="版本號，每次更新內容時遞增")
    """版本號，從 1 開始"""

    is_latest = models.BooleanField(
        default=True, db_index=True, help_text="是否為最新版本，查詢時應優先過濾此欄位"
    )
    """是否為最新版本"""

    # ============================================================================
    # 來源追蹤欄位 - 記錄資料來源信息
    # ============================================================================

    source_url = models.URLField(
        max_length=500, db_index=True, unique=False, help_text="原始爬蟲來源 URL"
    )
    """來源 URL"""

    # ============================================================================
    # 遺留系統相容欄位 - 為向後相容性保留
    # ============================================================================

    chr_no = models.CharField(
        max_length=100, null=True, blank=True, help_text="字符代碼，來自遺留系統"
    )
    """字符代碼（遺留系統）"""

    mod = models.CharField(
        max_length=100, null=True, blank=True, help_text="模式/類型代碼，來自遺留系統"
    )
    """模式類型（遺留系統）"""

    report_date = models.CharField(
        max_length=50, null=True, blank=True, help_text="報告日期字符串表示"
    )
    """報告日期"""

    # ============================================================================
    # 時間追蹤欄位 - 完整的時間審計紀錄
    # ============================================================================

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="記錄創建時間戳，自動設定為當前時間"
    )
    """創建時間"""

    updated_at = models.DateTimeField(auto_now=True, help_text="記錄更新時間戳，每次修改自動更新")
    """更新時間"""

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="報告驗證時間戳，用於排序、去重判定和時間範圍過濾",
    )
    """驗證時間戳"""

    # ============================================================================
    # 元資料欄位 - 靈活儲存額外的領域特定信息
    # ============================================================================

    metadata = models.JSONField(
        default=dict, blank=True, help_text="動態元資料，儲存額外的特定領域資訊 (JSON 格式)"
    )
    """動態元資料 (JSON)"""

    search_vector = SearchVectorField(
        null=True, blank=True, help_text="PostgreSQL 全文搜尋向量，自動生成"
    )
    """全文搜尋向量"""

    # ============================================================================
    # PostgreSQL Generated Columns (Imaging Report Fields)
    # These fields are auto-extracted from content_raw by PostgreSQL.
    # Defined here to enable Django ORM filtering, but managed by database.
    # ============================================================================

    imaging_findings = models.TextField(
        null=True,
        blank=True,
        editable=False,
        help_text="影像發現區塊，由 PostgreSQL GENERATED COLUMN 自動從 content_raw 解析",
    )
    """影像發現 (PostgreSQL generated column)"""

    impression = models.TextField(
        null=True,
        blank=True,
        editable=False,
        help_text="診斷意見區塊，由 PostgreSQL GENERATED COLUMN 自動從 content_raw 解析",
    )
    """診斷意見 (PostgreSQL generated column)"""

    class Meta:
        """
        Django 模型元選項。

        配置資料庫表名、排序順序、索引策略等。
        """

        db_table = "one_page_text_report_v2"
        """資料庫表名稱"""

        ordering = ["-verified_at", "-created_at"]
        """預設排序: 按驗證時間戳降序，若無則按建立時間"""

        # 複合索引: 加速去重判定查詢
        # 複合索引: 加速來源追蹤查詢
        # 複合索引: 加速最新版本查詢
        # 單一欄位索引: 加速報告類型過濾
        # GIN 全文搜尋索引: 支援 PostgreSQL 全文搜尋
        indexes = [
            models.Index(
                fields=["content_hash", "verified_at"],
                name="idx_content_hash_verified_at",
            ),
            models.Index(
                fields=["source_url", "verified_at"],
                name="idx_source_url_verified_at",
            ),
            models.Index(
                fields=["is_latest", "-verified_at"],
                name="idx_is_latest_verified_at",
            ),
            models.Index(
                fields=["report_type"],
                name="idx_report_type",
            ),
            GinIndex(
                fields=["search_vector"],
                name="idx_search_vector_gin",
            ),
        ]

        verbose_name = "Report"
        """模型顯示名稱 (單數)"""

        verbose_name_plural = "Reports"
        """模型顯示名稱 (複數)"""

    def __str__(self) -> str:
        """
        報告模型的字符串表示。

        用於 Django Admin 和日誌中的模型展示。

        Returns
        -------
        str
            格式: "report_id: title (vN)"，其中 N 是版本號

        Examples
        --------
        >>> report = Report.objects.first()
        >>> str(report)
        'exam_123: CT 掃描報告 (v2)'
        """
        return f"{self.report_id}: {self.title} (v{self.version_number})"

    def to_dict(self) -> dict:
        """
        將報告模型轉換為字典，用於 API 回應。

        此方法將 Django 模型實例序列化為適合 JSON 序列化的字典。
        內容被截斷至 500 字元以減少傳輸體積。

        Returns
        -------
        dict
            包含以下鍵值的字典:
            - uid (str): 原始爬蟲標識符
            - report_id (str): 系統內部報告編號
            - title (str): 報告標題
            - report_type (str): 報告格式類型
            - content_raw (str): 原始內容 (最多 500 字元)
            - version_number (int): 版本號
            - source_url (str): 來源 URL
            - created_at (str): 建立時間 (ISO 格式) 或 None
            - verified_at (str): 驗證時間 (ISO 格式) 或 None
            - is_latest (bool): 是否為最新版本

        Examples
        --------
        >>> report = Report.objects.first()
        >>> data = report.to_dict()
        >>> import json
        >>> json.dumps(data)  # 可直接序列化為 JSON

        Notes
        -----
        - 時間戳使用 ISO 8601 格式表示
        - 原始內容被截斷至 500 字元，避免傳輸過大的資料
        - 此方法不包含完整內容，若需要完整內容請使用 content_raw

        See Also
        --------
        safe_truncate: 安全的文本截斷方法
        """
        from report.service import ReportService

        return {
            "uid": self.uid,
            "report_id": self.report_id,
            "title": self.title,
            "report_type": self.report_type,
            "content_raw": ReportService.safe_truncate(self.content_raw, 500),
            "version_number": self.version_number,
            "source_url": self.source_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "is_latest": self.is_latest,
        }


class ReportVersion(models.Model):
    """
    報告版本歷史模型 - 追蹤所有版本變更以進行審計和歷史回溯。

    完整版本記錄每次報告的修改，包括內容快照、變更類型和時間戳。
    此模型實現審計追蹤功能，支援以下使用場景：

    - 版本歷史查詢: 取得任意版本的報告內容
    - 變更審計: 追蹤誰在何時進行了什麼修改
    - 內容恢復: 若需要回復到舊版本，可直接查詢此表
    - 去重驗證: 驗證去重決策是否正確

    與 Report 模型的關聯:
    - Report 保存當前最新版本的信息
    - ReportVersion 保存所有版本的快照
    - 關係: 一對多，一個 Report 可有多個 ReportVersion

    參數
    ----------
    report : ForeignKey
        指向父 Report 記錄的外鍵，建立版本與報告的聯繫
        刪除父報告時自動刪除所有版本記錄
    version_number : IntegerField
        版本號，與 Report.version_number 對應
        組成複合主鍵 (report_id, version_number)
    content_hash : CharField
        內容 SHA256 雜湊值快照，用於追蹤內容變更
    content_raw : TextField
        報告內容的完整快照，保存版本發佈時的原始內容
    changed_at : DateTimeField
        變更時間戳，自動設定為記錄建立時間
    verified_at : DateTimeField
        驗證時間戳，可用於追蹤驗證時間點
    change_description : CharField
        變更描述，簡要說明本次修改內容
    change_type : CharField
        變更類型，取值為: 'create', 'update', 'verify', 'deduplicate'
        見 CHANGE_TYPES 常數定義

    CHANGE_TYPES 常數
    -----------------
    'create': 初始建立 - 新報告首次建立
    'update': 內容更新 - 報告內容被修改
    'verify': 驗證標記 - 報告被驗證為正確
    'deduplicate': 去重合併 - 重複報告被合併

    索引策略
    -------
    1. (report_id, -version_number): 快速查詢某報告的所有版本
    2. content_hash: 加速內容查詢
    3. verified_at: 加速驗證時間範圍查詢

    範例
    --------
    取得某報告的完整版本歷史:

    >>> from report.models import ReportVersion
    >>> versions = ReportVersion.objects.filter(
    ...     report_id='exam_123'
    ... ).order_by('-version_number')
    >>> for v in versions:
    ...     print(f"v{v.version_number}: {v.change_type} at {v.changed_at}")

    參考資訊
    --------
    - Report: 當前報告記錄模型
    - ReportService.import_or_update_report: 建立版本記錄的業務邏輯
    """

    # ============================================================================
    # 關聯欄位 - 指向父 Report 記錄
    # ============================================================================

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="versions",
        help_text="指向父報告記錄，刪除時自動級聯刪除版本",
    )
    """父報告外鍵"""

    version_number = models.IntegerField(
        help_text="版本號，與 Report.version_number 對應，組成複合主鍵"
    )
    """版本號"""

    # ============================================================================
    # 內容快照欄位 - 保存該版本的完整內容
    # ============================================================================

    content_hash = models.CharField(
        max_length=64, db_index=True, help_text="內容 SHA256 雜湊值快照，追蹤內容變更"
    )
    """內容雜湊快照"""

    content_raw = models.TextField(help_text="報告內容的完整快照，保存版本發佈時的原始內容")
    """內容快照"""

    # ============================================================================
    # 變更追蹤欄位 - 記錄版本變更的元資訊
    # ============================================================================

    changed_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="變更時間戳，自動設定為記錄建立時間"
    )
    """變更時間戳"""

    verified_at = models.DateTimeField(
        null=True, blank=True, help_text="驗證時間戳，追蹤驗證發生的時間點"
    )
    """驗證時間戳"""

    change_description = models.CharField(
        max_length=500, blank=True, help_text="變更描述，簡要說明本次修改內容和原因"
    )
    """變更描述"""

    # ============================================================================
    # 變更類型 - 列舉所有可能的變更類型
    # ============================================================================

    CHANGE_TYPES = [
        ("create", "初始建立"),
        ("update", "內容更新"),
        ("verify", "驗證確認"),
        ("deduplicate", "去重合併"),
    ]
    """變更類型選擇"""

    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPES,
        default="create",
        help_text="變更類型: create (初始建立), update (內容更新), verify (驗證確認), deduplicate (去重合併)",
    )
    """變更類型"""

    class Meta:
        """Django 模型元選項 - 版本記錄配置。"""

        db_table = "one_page_text_report_versions"
        """資料庫表名稱"""

        ordering = ["-version_number"]
        """預設排序: 按版本號降序"""

        unique_together = [["report", "version_number"]]
        """複合唯一約束: (報告, 版本號)"""

        # 複合索引: 快速查詢某報告的所有版本
        # 單一欄位索引: 加速內容查詢
        # 單一欄位索引: 加速驗證時間範圍查詢
        indexes = [
            models.Index(
                fields=["report", "-version_number"],
                name="idx_report_version_number",
            ),
            models.Index(
                fields=["content_hash"],
                name="idx_version_content_hash",
            ),
            models.Index(
                fields=["verified_at"],
                name="idx_version_verified_at",
            ),
        ]

        verbose_name = "Report Version"
        """模型顯示名稱 (單數)"""

        verbose_name_plural = "Report Versions"
        """模型顯示名稱 (複數)"""

    def __str__(self) -> str:
        """
        版本記錄的字符串表示。

        Returns
        -------
        str
            格式: "report_id v版本號 - 變更類型"

        Examples
        --------
        >>> version = ReportVersion.objects.first()
        >>> str(version)
        'exam_123 v2 - update'
        """
        return f"{self.report.report_id} v{self.version_number} - {self.change_type}"


class ReportSummary(models.Model):
    """
    報告摘要模型 - 儲存提取的摘要以加速檢索和展示。

    此模型儲存報告的結構化摘要信息，包括簡短摘要、詳細摘要和關鍵要點。
    是報告的一對一關係，用於優化前端展示效能。

    與 Report 模型的關聯:
    - 一對一關係: 每個 Report 有一個 ReportSummary
    - 延遲加載: 只在需要時從資料庫查詢
    - 級聯刪除: 刪除報告時自動刪除摘要

    參數
    ----------
    report : OneToOneField
        與 Report 的一對一關係
        刪除報告時自動級聯刪除摘要
    short_summary : CharField
        簡短摘要，約 100-200 字
    long_summary : TextField
        詳細摘要，約 500-1000 字
    key_points : JSONField
        關鍵要點列表，JSON 數組格式
    created_at : DateTimeField
        建立時間戳
    updated_at : DateTimeField
        更新時間戳

    範例
    --------
    建立摘要:

    >>> from report.models import ReportSummary
    >>> summary = ReportSummary.objects.create(
    ...     report_id='exam_123',
    ...     short_summary='CT 掃描顯示...',
    ...     long_summary='詳細描述：...',
    ...     key_points=['要點1', '要點2']
    ... )

    查詢摘要:

    >>> from report.models import Report
    >>> report = Report.objects.get(report_id='exam_123')
    >>> summary = report.summary
    >>> print(summary.short_summary)
    """

    # ============================================================================
    # 關聯欄位 - 與 Report 的一對一關係
    # ============================================================================

    report = models.OneToOneField(
        Report,
        on_delete=models.CASCADE,
        related_name="summary",
        help_text="與報告的一對一關係，刪除報告時自動級聯刪除摘要",
    )
    """報告外鍵 (一對一)"""

    # ============================================================================
    # 摘要欄位 - 儲存不同粒度的摘要信息
    # ============================================================================

    short_summary = models.CharField(max_length=500, help_text="簡短摘要，約 100-200 字")
    """簡短摘要 (~100-200 字)"""

    long_summary = models.TextField(help_text="詳細摘要，約 500-1000 字")
    """詳細摘要 (~500-1000 字)"""

    # ============================================================================
    # 關鍵信息欄位 - 結構化的摘要要點
    # ============================================================================

    key_points = models.JSONField(
        default=list, help_text='關鍵要點列表，JSON 數組格式，如 ["要點1", "要點2", ...]'
    )
    """關鍵要點列表 (JSON 數組)"""

    # ============================================================================
    # 時間追蹤欄位 - 摘要的生命週期追蹤
    # ============================================================================

    created_at = models.DateTimeField(auto_now_add=True, help_text="摘要建立時間戳")
    """建立時間"""

    updated_at = models.DateTimeField(auto_now=True, help_text="摘要更新時間戳，每次修改自動更新")
    """更新時間"""

    class Meta:
        """Django 模型元選項 - 摘要記錄配置。"""

        db_table = "one_page_text_report_summaries"
        """資料庫表名稱"""

        verbose_name = "Report Summary"
        """模型顯示名稱 (單數)"""

        verbose_name_plural = "Report Summaries"
        """模型顯示名稱 (複數)"""

    def __str__(self) -> str:
        """
        摘要記錄的字符串表示。

        Returns
        -------
        str
            格式: "Summary: report_id"

        Examples
        --------
        >>> summary = ReportSummary.objects.first()
        >>> str(summary)
        'Summary: exam_123'
        """
        return f"Summary: {self.report.report_id}"


class ReportSearchIndex(models.Model):
    """
    報告搜尋索引模型 - 支援高效的全文搜尋功能。

    此模型維護報告的搜尋索引，包含標題、處理過的內容和元資料的合併文本。
    用於優化搜尋查詢效能，避免每次搜尋時掃描完整的 content_raw 欄位。

    與 Report 模型的關聯:
    - 一對一關係: 每個 Report 有一個搜尋索引
    - 非正規化儲存: 複製部分內容供搜尋使用
    - 異步更新: 可通過信號或定期任務更新索引

    參數
    ----------
    report : OneToOneField
        與 Report 的一對一關係
        刪除報告時自動級聯刪除索引
    search_text : TextField
        可搜尋的文本，包含標題、處理內容和元資料
        已建立資料庫索引以加速搜尋
    relevance_score : FloatField
        相關性得分，用於搜尋結果排序
        預設值為 1.0
    updated_at : DateTimeField
        索引更新時間戳

    設計原理
    -------
    - 搜尋優化: 預先組合搜尋所需的文本，避免運行時處理
    - 相關性排序: 支援基於得分的結果排序
    - 異步管理: 可異步更新索引以提高效能

    範例
    --------
    建立搜尋索引:

    >>> from report.models import ReportSearchIndex
    >>> index = ReportSearchIndex.objects.create(
    ...     report_id='exam_123',
    ...     search_text='標題 CT 掃描報告 處理內容 關鍵詞...',
    ...     relevance_score=1.0
    ... )

    搜尋報告:

    >>> from django.db.models import Q
    >>> results = ReportSearchIndex.objects.filter(
    ...     search_text__icontains='關鍵詞'
    ... ).order_by('-relevance_score')
    """

    # ============================================================================
    # 關聯欄位 - 與 Report 的一對一關係
    # ============================================================================

    report = models.OneToOneField(
        Report,
        on_delete=models.CASCADE,
        related_name="search_index",
        help_text="與報告的一對一關係，刪除報告時自動級聯刪除索引",
    )
    """報告外鍵 (一對一)"""

    # ============================================================================
    # 搜尋文本欄位 - 經過合併的可搜尋內容
    # ============================================================================

    search_text = models.TextField(
        db_index=True, help_text="可搜尋的文本，包含標題 + 處理過的內容 + 元資料"
    )
    """搜尋文本 (已索引)"""

    # ============================================================================
    # 排序元資訊 - 支援搜尋結果的相關性排序
    # ============================================================================

    relevance_score = models.FloatField(
        default=1.0, help_text="相關性得分，用於搜尋結果排序，預設值為 1.0"
    )
    """相關性得分"""

    # ============================================================================
    # 時間追蹤欄位 - 索引的生命週期追蹤
    # ============================================================================

    updated_at = models.DateTimeField(auto_now=True, help_text="索引更新時間戳，每次修改自動更新")
    """更新時間"""

    class Meta:
        """Django 模型元選項 - 搜尋索引配置。"""

        db_table = "one_page_text_report_search_index"
        """資料庫表名稱"""

        verbose_name = "Report Search Index"
        """模型顯示名稱 (單數)"""

        verbose_name_plural = "Report Search Indexes"
        """模型顯示名稱 (複數)"""

    def __str__(self) -> str:
        """
        搜尋索引的字符串表示。

        Returns
        -------
        str
            格式: "Index: report_id"

        Examples
        --------
        >>> index = ReportSearchIndex.objects.first()
        >>> str(index)
        'Index: exam_123'
        """
        return f"Index: {self.report.report_id}"


class ExportTask(models.Model):
    """
    匯出任務追蹤模型 - 追蹤批量匯出操作的狀態、進度和結果。

    此模型管理報告批量匯出功能，支援多種匯出格式和完整的進度追蹤。
    每個匯出任務都有獨立的生命週期，從提交到完成或失敗。

    功能特性
    --------
    - 任務狀態追蹤: 完整的狀態流轉 (pending → processing → completed/failed)
    - 多格式支援: 支援 CSV, JSON, Excel, XML 四種匯出格式
    - 進度追蹤: 實時監控已處理記錄數和進度百分比
    - 文件管理: 儲存生成文件的路徑和下載 URL
    - 自動過期: 支援設置文件過期時間，便於自動清理
    - 錯誤追蹤: 記錄失敗原因供用戶和管理員參考

    任務流程
    -------
    1. 創建: 用戶提交匯出請求，任務創建為 pending 狀態
    2. 處理: 非同步任務開始處理，狀態變更為 processing
    3. 完成: 處理完成，狀態變更為 completed，生成文件並設置下載 URL
    4. 失敗: 若出錯，狀態變更為 failed，記錄錯誤訊息
    5. 過期: 文件存儲一段時間後自動過期，便於清理存儲空間

    參數
    ----------
    task_id : CharField
        唯一任務標識，主鍵
    user_id : CharField
        建立任務的用戶 ID，用於權限控制
    query_params : JSONField
        搜尋參數，包含 page_size, filters, sort 等
    export_format : CharField
        匯出格式，取值: 'csv', 'json', 'xlsx', 'xml'
    include_fields : JSONField
        用戶選定的匯出欄位清單
    status : CharField
        任務狀態，取值: 'pending', 'processing', 'completed', 'failed', 'cancelled'
    total_records : IntegerField
        需要匯出的總記錄數
    processed_records : IntegerField
        已處理的記錄數，用於計算進度
    file_path : CharField
        本地文件存儲路徑
    file_url : URLField
        文件下載 URL
    file_size : BigIntegerField
        文件大小 (bytes)
    error_message : TextField
        失敗原因描述
    created_at : DateTimeField
        任務創建時間
    started_at : DateTimeField
        處理開始時間
    completed_at : DateTimeField
        處理完成時間
    expires_at : DateTimeField
        文件過期時間，用於自動清理

    例子
    --------
    建立匯出任務:

    >>> from report.models import ExportTask
    >>> from datetime import datetime, timedelta
    >>> task = ExportTask.objects.create(
    ...     task_id='export_001',
    ...     user_id='user_123',
    ...     query_params={'filters': {'report_type': 'CT'}},
    ...     export_format='csv',
    ...     status='pending',
    ...     expires_at=datetime.now() + timedelta(days=7)
    ... )

    查詢用戶的匯出任務:

    >>> tasks = ExportTask.objects.filter(user_id='user_123')
    >>> for task in tasks:
    ...     print(f"{task.task_id}: {task.status} ({task.get_progress_percent()}%)")

    參考資訊
    --------
    - status 狀態流轉: pending → processing → (completed | failed | cancelled)
    - 進度計算: get_progress_percent() 方法計算百分比
    - 過期管理: expires_at 欄位用於自動清理任務和文件
    """

    # ============================================================================
    # 狀態定義 - 任務的所有可能狀態
    # ============================================================================

    STATUS_CHOICES = [
        ("pending", "待處理"),
        ("processing", "處理中"),
        ("completed", "已完成"),
        ("failed", "失敗"),
        ("cancelled", "已取消"),
    ]
    """任務狀態選擇"""

    # ============================================================================
    # 格式定義 - 支援的匯出格式
    # ============================================================================

    FORMAT_CHOICES = [
        ("csv", "CSV"),
        ("json", "JSON"),
        ("xlsx", "Excel"),
        ("xml", "XML"),
    ]
    """匯出格式選擇"""

    # ============================================================================
    # 任務識別欄位 - 唯一標識任務
    # ============================================================================

    task_id = models.CharField(
        max_length=100, primary_key=True, db_index=True, help_text="唯一任務標識，主鍵"
    )
    """任務 ID (主鍵)"""

    # ============================================================================
    # 使用者信息欄位 - 追蹤任務所有者
    # ============================================================================

    user_id = models.CharField(
        max_length=100, db_index=True, help_text="建立任務的用戶 ID，用於權限控制"
    )
    """使用者 ID"""

    # ============================================================================
    # 匯出參數欄位 - 配置匯出操作
    # ============================================================================

    query_params = models.JSONField(help_text="搜尋參數 (page_size, filters, sort 等)")
    """查詢參數 (JSON)"""

    export_format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        db_index=True,
        help_text="匯出格式: csv, json, xlsx, xml",
    )
    """匯出格式"""

    include_fields = models.JSONField(null=True, blank=True, help_text="用戶選定的匯出欄位清單")
    """匯出欄位清單 (JSON)"""

    # ============================================================================
    # 任務狀態欄位 - 追蹤任務進度
    # ============================================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
        help_text="任務當前狀態: pending, processing, completed, failed, cancelled",
    )
    """任務狀態"""

    # ============================================================================
    # 進度追蹤欄位 - 監控處理進度
    # ============================================================================

    total_records = models.IntegerField(default=0, help_text="需要匯出的總記錄數")
    """總記錄數"""

    processed_records = models.IntegerField(
        default=0, help_text="已處理的記錄數，用於計算進度百分比"
    )
    """已處理記錄數"""

    # ============================================================================
    # 文件信息欄位 - 儲存生成的文件信息
    # ============================================================================

    file_path = models.CharField(
        max_length=500, null=True, blank=True, help_text="本地文件存儲路徑"
    )
    """文件本地路徑"""

    file_url = models.URLField(
        max_length=500, null=True, blank=True, help_text="文件下載 URL，供用戶直接下載"
    )
    """文件下載 URL"""

    file_size = models.BigIntegerField(null=True, blank=True, help_text="文件大小 (bytes)")
    """文件大小 (bytes)"""

    # ============================================================================
    # 錯誤追蹤欄位 - 記錄失敗信息
    # ============================================================================

    error_message = models.TextField(
        null=True, blank=True, help_text="失敗原因描述，供用戶和管理員參考"
    )
    """錯誤訊息"""

    # ============================================================================
    # 時間追蹤欄位 - 完整的任務生命週期追蹤
    # ============================================================================

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="任務創建時間，自動設定為當前時間"
    )
    """建立時間"""

    started_at = models.DateTimeField(
        null=True, blank=True, help_text="處理開始時間，當狀態變更為 processing 時設置"
    )
    """開始時間"""

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="處理完成時間，當狀態變更為 completed/failed/cancelled 時設置",
    )
    """完成時間"""

    expires_at = models.DateTimeField(
        db_index=True, help_text="文件過期時間，用於自動清理任務和文件"
    )
    """過期時間"""

    class Meta:
        """Django 模型元選項 - 匯出任務配置。"""

        db_table = "report_export_tasks"
        """資料庫表名稱"""

        ordering = ["-created_at"]
        """預設排序: 按建立時間降序 (最新在前)"""

        verbose_name = "報告匯出任務"
        """模型顯示名稱 (單數)"""

        verbose_name_plural = "報告匯出任務"
        """模型顯示名稱 (複數)"""

        # 複合索引: 快速查詢用戶的匯出歷史
        # 複合索引: 加速按狀態查詢
        # 單一欄位索引: 支援過期任務的批量清理
        # 複合索引: 統計各格式的匯出任務
        indexes = [
            models.Index(
                fields=["user_id", "-created_at"],
                name="idx_user_created_at",
            ),
            models.Index(
                fields=["status", "created_at"],
                name="idx_status_created_at",
            ),
            models.Index(
                fields=["expires_at"],
                name="idx_expires_at",
            ),
            models.Index(
                fields=["export_format", "-created_at"],
                name="idx_format_created_at",
            ),
        ]

    def __str__(self) -> str:
        """
        匯出任務的字符串表示。

        Returns
        -------
        str
            格式: "task_id: 格式 (狀態)"

        Examples
        --------
        >>> task = ExportTask.objects.first()
        >>> str(task)
        'export_001: CSV (completed)'
        """
        return f"{self.task_id}: {self.export_format.upper()} ({self.status})"

    def get_progress_percent(self) -> int:
        """
        計算匯出進度百分比。

        此方法計算已處理記錄數占總記錄數的百分比，
        用於前端進度條展示。

        Returns
        -------
        int
            進度百分比 (0-100)

        Notes
        -----
        - 若 total_records 為 0，返回 0
        - 結果四捨五入到整數

        Examples
        --------
        >>> task = ExportTask.objects.first()
        >>> print(f"進度: {task.get_progress_percent()}%")
        進度: 45%
        """
        if self.total_records == 0:
            return 0
        return int((self.processed_records / self.total_records) * 100)

    def get_status_display_zh(self) -> str:
        """
        取得中文狀態描述。

        將英文狀態代碼轉換為中文顯示文本，
        用於前端和日誌中的用戶友好展示。

        Returns
        -------
        str
            中文狀態描述，如無對應映射則返回原始狀態值

        Examples
        --------
        >>> task = ExportTask.objects.first()
        >>> print(task.get_status_display_zh())
        已完成

        See Also
        --------
        STATUS_CHOICES: 狀態定義
        """
        status_map = {
            "pending": "待處理",
            "processing": "處理中",
            "completed": "已完成",
            "failed": "失敗",
            "cancelled": "已取消",
        }
        return status_map.get(self.status, self.status)

    def to_dict(self) -> dict:
        """
        將匯出任務轉換為字典，用於 API 回應。

        此方法將 Django 模型實例序列化為適合 JSON 序列化的字典，
        包含進度百分比的實時計算。

        Returns
        -------
        dict
            包含以下鍵值的字典:
            - task_id (str): 唯一任務標識
            - user_id (str): 使用者 ID
            - status (str): 任務狀態
            - export_format (str): 匯出格式
            - total_records (int): 總記錄數
            - processed_records (int): 已處理記錄數
            - progress_percent (int): 進度百分比 (0-100)
            - file_url (str): 文件下載 URL (可為 None)
            - file_size (int): 文件大小 (可為 None)
            - error_message (str): 錯誤訊息 (可為 None)
            - created_at (str): 建立時間 (ISO 格式)
            - started_at (str): 開始時間 (ISO 格式 或 None)
            - completed_at (str): 完成時間 (ISO 格式 或 None)
            - expires_at (str): 過期時間 (ISO 格式)

        Examples
        --------
        >>> import json
        >>> task = ExportTask.objects.first()
        >>> data = task.to_dict()
        >>> print(json.dumps(data))  # 可直接序列化為 JSON

        Notes
        -----
        - 時間戳使用 ISO 8601 格式表示
        - progress_percent 為實時計算的動態值
        - 可為 None 的欄位在完成前可能為 null
        """
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "status": self.status,
            "export_format": self.export_format,
            "total_records": self.total_records,
            "processed_records": self.processed_records,
            "progress_percent": self.get_progress_percent(),
            "file_url": self.file_url,
            "file_size": self.file_size,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


class AIAnnotation(models.Model):
    """
    報告 AI 註解模型 - 儲存 AI 生成或用戶修正的報告註解。

    此模型儲存對報告進行的各種 AI 分析結果和用戶手動修正，
    支援命名實體識別 (NER)、分類、摘要等多種註解類型。

    功能特性
    --------
    - AI 分析結果儲存: 儲存各種 AI 模型的輸出
    - 用戶修正支援: 允許用戶修正或改進 AI 生成的註解
    - 完整審計追蹤: 記錄誰在何時進行了什麼操作
    - 靈活的內容格式: 支援 JSON 字符串或純文本內容
    - 動態元資料: 使用 JSON 欄位儲存額外信息
    - 版本控制: 關聯分類指南版本，支援廢棄標記

    與 Report 模型的關聯:
    - 多對一關係: 一個 Report 可有多個 AIAnnotation
    - 級聯刪除: 刪除報告時自動刪除所有註解
    - 審計追蹤: 記錄創建者和創建時間

    參數
    ----------
    id : UUIDField
        唯一標識符，使用 UUID v4，主鍵
    report : ForeignKey
        指向父 Report 記錄的外鍵
        刪除報告時自動級聯刪除所有註解
    annotation_type : CharField
        註解類型，如 "NER", "Classification", "Summary" 等
    content : TextField
        註解內容，可為 JSON 字符串或純文本
    metadata : JSONField
        動態元資料，儲存額外的分析信息
    created_at : DateTimeField
        註解建立時間戳
    updated_at : DateTimeField
        註解更新時間戳
    created_by : ForeignKey
        註解的創建者 (用戶)，可為空
        若用戶被刪除，此欄位設為 NULL
    guideline : ForeignKey
        關聯的分類指南 (用於批次分析)
    guideline_version : IntegerField
        建立時的指南版本號
    batch_task : ForeignKey
        關聯的批次分析任務
    confidence_score : FloatField
        AI 分類的信心度分數 (0.0-1.0)
    is_deprecated : BooleanField
        是否已廢棄 (重新分析後舊結果會被標記為廢棄)
    deprecated_at : DateTimeField
        廢棄時間戳
    deprecated_reason : CharField
        廢棄原因說明

    支援的註解類型
    ---------------
    'NER': Named Entity Recognition (命名實體識別)
        提取文本中的人名、地名、組織名等實體
    'Classification': 分類
        對報告進行分類標籤標記
    'Summary': 摘要
        生成報告的自動摘要
    'Extraction': 信息提取
        提取結構化的關鍵信息
    'Sentiment': 情感分析
        分析文本的情感傾向

    範例
    --------
    建立 AI 註解:

    >>> from report.models import AIAnnotation
    >>> from report.models import Report
    >>> report = Report.objects.first()
    >>> annotation = AIAnnotation.objects.create(
    ...     report=report,
    ...     annotation_type='NER',
    ...     content='{"entities": [{"text": "患者", "type": "PERSON"}]}',
    ...     metadata={'model': 'spacy_ner_v1', 'confidence': 0.95}
    ... )

    查詢報告的所有 NER 註解:

    >>> annotations = report.annotations.filter(annotation_type='NER')
    >>> for ann in annotations:
    ...     print(f"建立者: {ann.created_by.get_full_name()}")
    ...     print(f"內容: {ann.content}")

    參考資訊
    --------
    - Report: 報告主模型
    - created_by: 使用者 (Django User Model)
    - metadata: 儲存模型版本、置信度等信息
    """

    # ============================================================================
    # 唯一識別欄位 - 使用 UUID 確保全球唯一性
    # ============================================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="唯一標識符，使用 UUID v4 生成",
    )
    """註解 ID (UUID)"""

    # ============================================================================
    # 關聯欄位 - 與 Report 的多對一關係
    # ============================================================================

    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="annotations",
        help_text="指向父報告，刪除報告時自動級聯刪除所有註解",
    )
    """父報告外鍵"""

    # ============================================================================
    # 註解詳細欄位 - 儲存註解的核心內容
    # ============================================================================

    annotation_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="註解類型: NER, Classification, Summary, Extraction, Sentiment 等",
    )
    """註解類型"""

    content = models.TextField(help_text="註解內容，可為 JSON 字符串或純文本")
    """註解內容 (JSON 或文本)"""

    # ============================================================================
    # 元資料欄位 - 儲存額外的分析信息
    # ============================================================================

    metadata = models.JSONField(
        default=dict, blank=True, help_text="動態元資料，如模型版本、置信度等"
    )
    """元資料 (JSON)"""

    # ============================================================================
    # 審計欄位 - 完整的變更追蹤
    # ============================================================================

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="註解建立時間，自動設定為當前時間"
    )
    """建立時間"""

    updated_at = models.DateTimeField(auto_now=True, help_text="註解更新時間，每次修改自動更新")
    """更新時間"""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_annotations",
        help_text="註解的創建者 (用戶)，用於審計追蹤",
    )
    """建立者 (用戶)"""

    # ============================================================================
    # 分類指南關聯欄位 - 用於批次分析和版本控制
    # ============================================================================

    guideline = models.ForeignKey(
        "ai.ClassificationGuideline",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="annotations",
        help_text="關聯的分類指南，用於批次分析",
    )
    """分類指南外鍵"""

    guideline_version = models.IntegerField(
        null=True,
        blank=True,
        help_text="建立時的指南版本號，用於追蹤版本",
    )
    """指南版本號"""

    batch_task = models.ForeignKey(
        "ai.BatchAnalysisTask",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="annotations",
        help_text="關聯的批次分析任務",
    )
    """批次分析任務外鍵"""

    confidence_score = models.FloatField(
        null=True,
        blank=True,
        help_text="AI 分類的信心度分數 (0.0-1.0)",
    )
    """信心度分數"""

    # ============================================================================
    # 廢棄標記欄位 - 支援版本控制和結果追蹤
    # ============================================================================

    is_deprecated = models.BooleanField(
        default=False,
        db_index=True,
        help_text="是否已廢棄，重新分析後舊結果會被標記為廢棄",
    )
    """是否已廢棄"""

    deprecated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="廢棄時間戳",
    )
    """廢棄時間"""

    deprecated_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="廢棄原因說明，如 'Re-analyzed with guideline v2'",
    )
    """廢棄原因"""

    class Meta:
        """Django 模型元選項 - AI 註解配置。"""

        db_table = "report_ai_annotations"
        """資料庫表名稱"""

        ordering = ["-created_at"]
        """預設排序: 按建立時間降序 (最新在前)"""

        # 複合索引: 快速查詢某報告的特定類型註解
        # 單一欄位索引: 加速時間範圍查詢
        indexes = [
            models.Index(
                fields=["report", "annotation_type"],
                name="idx_report_annotation_type",
            ),
            models.Index(
                fields=["created_at"],
                name="idx_annotation_created_at",
            ),
            models.Index(
                fields=["guideline", "-created_at"],
                name="idx_annotation_guideline",
            ),
            models.Index(
                fields=["is_deprecated", "-created_at"],
                name="idx_annotation_deprecated",
            ),
            models.Index(
                fields=["batch_task"],
                name="idx_annotation_batch_task",
            ),
        ]

        verbose_name = "AI Annotation"
        """模型顯示名稱 (單數)"""

        verbose_name_plural = "AI Annotations"
        """模型顯示名稱 (複數)"""

    def __str__(self) -> str:
        """
        AI 註解的字符串表示。

        Returns
        -------
        str
            格式: "report_id - annotation_type"

        Examples
        --------
        >>> annotation = AIAnnotation.objects.first()
        >>> str(annotation)
        'exam_123 - NER'
        """
        return f"{self.report.report_id} - {self.annotation_type}"

    def to_dict(self) -> dict:
        """
        將 AI 註解轉換為字典，用於 API 回應。

        此方法將 Django 模型實例序列化為適合 JSON 序列化的字典。

        Returns
        -------
        dict
            包含以下鍵值的字典:
            - id (str): UUID 字符串
            - report_id (str): 報告 UID
            - annotation_type (str): 註解類型
            - content (str): 註解內容
            - metadata (dict): 元資料
            - created_at (str): 建立時間 (ISO 格式)
            - updated_at (str): 更新時間 (ISO 格式 或 None)
            - created_by (str): 創建者全名 (或 None)
            - guideline_id (str): 分類指南 ID (或 None)
            - guideline_version (int): 指南版本號 (或 None)
            - batch_task_id (str): 批次任務 ID (或 None)
            - confidence_score (float): 信心度分數 (或 None)
            - is_deprecated (bool): 是否已廢棄
            - deprecated_at (str): 廢棄時間 (ISO 格式 或 None)
            - deprecated_reason (str): 廢棄原因

        Examples
        --------
        >>> import json
        >>> annotation = AIAnnotation.objects.first()
        >>> data = annotation.to_dict()
        >>> print(json.dumps(data))  # 可直接序列化為 JSON

        Notes
        -----
        - id 和 created_at 始終有值
        - updated_at 在未修改時可能與 created_at 相同
        - created_by 若用戶已刪除則為 None
        """
        return {
            "id": str(self.id),
            "report_id": self.report.uid,
            "annotation_type": self.annotation_type,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by.get_full_name() if self.created_by else None,
            # Guideline and batch task tracking
            "guideline_id": str(self.guideline_id) if self.guideline_id else None,
            "guideline_version": self.guideline_version,
            "batch_task_id": str(self.batch_task_id) if self.batch_task_id else None,
            "confidence_score": self.confidence_score,
            # Deprecation tracking
            "is_deprecated": self.is_deprecated,
            "deprecated_at": self.deprecated_at.isoformat() if self.deprecated_at else None,
            "deprecated_reason": self.deprecated_reason,
        }
