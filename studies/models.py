"""
Study Model - Medical examination records.
PRAGMATIC DESIGN: Flat structure, minimal relationships.
All fields needed for search, no speculation about future uses.
"""

from django.db import models


class Study(models.Model):
    """
    Medical examination study record.
    
    Flat design - all data in one table for simplicity.
    No relationships or signals, only direct field references.
    This follows Linus Torvalds principle: eliminate special cases through better data structures.
    """
    
    # Primary key and identifiers
    exam_id = models.CharField(max_length=100, primary_key=True, db_index=True)
    medical_record_no = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    application_order_no = models.CharField(max_length=100, null=True, blank=True)
    
    # Patient information
    patient_name = models.CharField(max_length=200, db_index=True)
    patient_gender = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[('M', 'Male'), ('F', 'Female'), ('U', 'Unknown')]
    )
    patient_birth_date = models.CharField(max_length=20, null=True, blank=True)
    patient_age = models.IntegerField(null=True, blank=True)
    
    # Examination details
    exam_status = models.CharField(
        max_length=20,
        db_index=True,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
    )
    exam_source = models.CharField(max_length=50, db_index=True)  # CT, MRI, X-ray, etc.
    exam_item = models.CharField(max_length=200, db_index=True)  # Chest CT, Spine MRI, etc.
    exam_description = models.TextField(null=True, blank=True)
    exam_room = models.CharField(max_length=100, null=True, blank=True)
    exam_equipment = models.CharField(max_length=200, null=True, blank=True)
    equipment_type = models.CharField(max_length=100)
    
    # Time fields - CRITICAL: Must be ISO format in API
    order_datetime = models.DateTimeField(db_index=True)
    check_in_datetime = models.DateTimeField(null=True, blank=True)
    report_certification_datetime = models.DateTimeField(null=True, blank=True)
    
    # Reporting
    certified_physician = models.CharField(max_length=200, null=True, blank=True)
    data_load_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        # Ordering - most recent first (users expect this)
        ordering = ['-order_datetime']
        
        # Indexes for common queries
        indexes = [
            models.Index(fields=['exam_status', '-order_datetime']),
            models.Index(fields=['exam_source', '-order_datetime']),
            models.Index(fields=['patient_name']),
            models.Index(fields=['exam_item']),
        ]
        
        # Table name
        db_table = 'medical_examinations_fact'
        
        # No admin, no signals, no special handling
        verbose_name = '医疗研究'
        verbose_name_plural = '医疗研究'
    
    def __str__(self):
        return f'{self.exam_id}: {self.patient_name} - {self.exam_item}'
    
    def to_dict(self):
        """Convert to dictionary for API response.
        
        CRITICAL: DateTime format must be ISO 8601 without timezone.
        This matches FastAPI response format exactly.
        """
        return {
            'exam_id': self.exam_id,
            'medical_record_no': self.medical_record_no,
            'application_order_no': self.application_order_no,
            'patient_name': self.patient_name,
            'patient_gender': self.patient_gender,
            'patient_birth_date': self.patient_birth_date,
            'patient_age': self.patient_age,
            'exam_status': self.exam_status,
            'exam_source': self.exam_source,
            'exam_item': self.exam_item,
            'exam_description': self.exam_description,
            'exam_room': self.exam_room,
            'exam_equipment': self.exam_equipment,
            'equipment_type': self.equipment_type,
            'order_datetime': self.order_datetime.isoformat() if self.order_datetime else None,
            'check_in_datetime': self.check_in_datetime.isoformat() if self.check_in_datetime else None,
            'report_certification_datetime': self.report_certification_datetime.isoformat() if self.report_certification_datetime else None,
            'certified_physician': self.certified_physician,
            'data_load_time': self.data_load_time.isoformat() if self.data_load_time else None,
        }


class Report(models.Model):
    """
    Scraped report storage with version control and deduplication.

    Features:
    - Content-based deduplication (hash + time)
    - Version control (tracks all versions)
    - Full-text search support
    - Flexible metadata storage

    Design principle: Flat structure with efficient indexing.
    """

    # Unique identification
    uid = models.CharField(max_length=100, primary_key=True, db_index=True)  # Original UID from scraper (up to 56 chars from legacy DB)
    report_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)  # Internal ID

    # Basic information
    title = models.CharField(max_length=500, db_index=True)
    report_type = models.CharField(max_length=50, db_index=True)  # PDF, HTML, TXT, etc.
    content_raw = models.TextField()  # Original content
    content_processed = models.TextField(null=True, blank=True)  # Processed for search

    # Deduplication and versioning
    content_hash = models.CharField(max_length=64, db_index=True)  # SHA256 hash of content
    version_number = models.IntegerField(default=1)  # Version counter
    is_latest = models.BooleanField(default=True, db_index=True)  # Is this the latest version?

    # Source tracking
    source_url = models.URLField(max_length=500, db_index=True, unique=False)  # URL from scraper

    # Original fields from scraper
    chr_no = models.CharField(max_length=100, null=True, blank=True)  # Character code
    mod = models.CharField(max_length=100, null=True, blank=True)  # Type/Mode
    report_date = models.CharField(max_length=50, null=True, blank=True)  # Report date

    # Temporal tracking
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True, db_index=True)  # Verification timestamp

    # Metadata storage (flexible)
    metadata = models.JSONField(default=dict, blank=True)  # Dynamic metadata

    class Meta:
        db_table = 'one_page_text_report_v2'
        ordering = ['-verified_at', '-created_at']
        indexes = [
            models.Index(fields=['content_hash', 'verified_at']),
            models.Index(fields=['source_url', 'verified_at']),
            models.Index(fields=['is_latest', '-verified_at']),
            models.Index(fields=['report_type']),
        ]
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'

    def __str__(self):
        return f'{self.report_id}: {self.title} (v{self.version_number})'

    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            'uid': self.uid,
            'report_id': self.report_id,
            'title': self.title,
            'report_type': self.report_type,
            'content_raw': self.content_raw[:500],  # Preview only
            'version_number': self.version_number,
            'source_url': self.source_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'is_latest': self.is_latest,
        }


class ReportVersion(models.Model):
    """
    Track all versions of a report for audit and history purposes.

    Requirement: Track complete update history.
    """

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()

    # Content snapshot
    content_hash = models.CharField(max_length=64, db_index=True)
    content_raw = models.TextField()

    # Change tracking
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    change_description = models.CharField(max_length=500, blank=True)

    # Change type
    CHANGE_TYPES = [
        ('create', 'Initial creation'),
        ('update', 'Content updated'),
        ('verify', 'Content verified'),
        ('deduplicate', 'Duplicate consolidated'),
    ]
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES, default='create')

    class Meta:
        db_table = 'one_page_text_report_versions'
        ordering = ['-version_number']
        unique_together = [['report', 'version_number']]
        indexes = [
            models.Index(fields=['report', '-version_number']),
            models.Index(fields=['content_hash']),
            models.Index(fields=['verified_at']),
        ]
        verbose_name = 'Report Version'
        verbose_name_plural = 'Report Versions'

    def __str__(self):
        return f'{self.report.report_id} v{self.version_number} - {self.change_type}'


class ReportSummary(models.Model):
    """
    Store extracted summaries for faster retrieval and display.

    Requirement: Support full-text and summary display.
    """

    report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='summary')

    # Summaries
    short_summary = models.CharField(max_length=500)  # ~100-200 words
    long_summary = models.TextField()  # ~500-1000 words

    # Key information
    key_points = models.JSONField(default=list)  # List of key points

    # Temporal
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'one_page_text_report_summaries'
        verbose_name = 'Report Summary'
        verbose_name_plural = 'Report Summaries'

    def __str__(self):
        return f'Summary: {self.report.report_id}'


class ReportSearchIndex(models.Model):
    """
    Full-text search index for efficient searching across all reports.

    Uses: Full-text search on title and processed content.
    """

    report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='search_index')

    # Searchable content
    search_text = models.TextField(db_index=True)  # Combined title + processed_content + metadata

    # Ranking metadata
    relevance_score = models.FloatField(default=1.0)

    # Temporal
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'one_page_text_report_search_index'
        verbose_name = 'Report Search Index'
        verbose_name_plural = 'Report Search Indexes'

    def __str__(self):
        return f'Index: {self.report.report_id}'


class ExportTask(models.Model):
    """
    匯出任務追蹤模型 - 追蹤批量匯出操作的狀態和進度。
    
    功能:
    - 任務狀態追蹤 (pending, processing, completed, failed, cancelled)
    - 匯出格式支援 (CSV, JSON, Excel, XML)
    - 進度追蹤和文件管理
    - 自動過期和清理
    """
    
    STATUS_CHOICES = [
        ('pending', '待處理'),
        ('processing', '處理中'),
        ('completed', '已完成'),
        ('failed', '失敗'),
        ('cancelled', '已取消'),
    ]
    
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xlsx', 'Excel'),
        ('xml', 'XML'),
    ]
    
    # 任務識別
    task_id = models.CharField(
        max_length=100,
        primary_key=True,
        db_index=True,
        help_text='唯一任務標識'
    )
    
    # 使用者信息
    user_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text='創建用戶 ID'
    )
    
    # 匯出參數
    query_params = models.JSONField(
        help_text='搜尋參數 (page_size, filters, sort, etc.)'
    )
    export_format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        db_index=True,
        help_text='匯出格式'
    )
    include_fields = models.JSONField(
        null=True,
        blank=True,
        help_text='選定的匯出欄位清單'
    )
    
    # 任務狀態
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text='任務當前狀態'
    )
    
    # 進度追蹤
    total_records = models.IntegerField(
        default=0,
        help_text='需要匯出的總記錄數'
    )
    processed_records = models.IntegerField(
        default=0,
        help_text='已處理的記錄數'
    )
    
    # 文件信息
    file_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='本地文件路徑'
    )
    file_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text='文件下載 URL'
    )
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='文件大小 (bytes)'
    )
    
    # 錯誤信息
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='失敗原因描述'
    )
    
    # 時間追蹤
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='任務創建時間'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='處理開始時間'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='處理完成時間'
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text='文件過期時間'
    )
    
    class Meta:
        db_table = 'report_export_tasks'
        ordering = ['-created_at']
        verbose_name = '報告匯出任務'
        verbose_name_plural = '報告匯出任務'
        indexes = [
            models.Index(fields=['user_id', '-created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['export_format', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.task_id}: {self.export_format.upper()} ({self.status})'
    
    def get_progress_percent(self) -> int:
        """計算匯出進度百分比。"""
        if self.total_records == 0:
            return 0
        return int((self.processed_records / self.total_records) * 100)
    
    def get_status_display_zh(self) -> str:
        """取得中文狀態描述。"""
        status_map = {
            'pending': '待處理',
            'processing': '處理中',
            'completed': '已完成',
            'failed': '失敗',
            'cancelled': '已取消',
        }
        return status_map.get(self.status, self.status)
    
    def to_dict(self):
        """轉換為字典格式供 API 返回。"""
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'status': self.status,
            'export_format': self.export_format,
            'total_records': self.total_records,
            'processed_records': self.processed_records,
            'progress_percent': self.get_progress_percent(),
            'file_url': self.file_url,
            'file_size': self.file_size,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
