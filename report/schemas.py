"""
報告 Schema 模組 - 定義 API 請求和回應的資料結構驗證規則。

此模組使用 Django Ninja Schema 定義所有與報告相關的 API 輸入輸出格式。
通過 Pydantic 進行類型驗證和序列化，確保 API 資料的一致性。

----------
"""

from __future__ import annotations

from typing import Any, Literal

from ninja import Schema


class ReportImportRequest(Schema):
    """
    報告導入請求 Schema - 定義報告導入 API 的輸入格式。

    此 Schema 驗證從爬蟲系統提交的報告導入請求。
    包含報告的基本信息和元資料。

    參數
    ----------
    uid : str
        原始爬蟲標識符
    title : str
        報告標題
    content : str
        報告完整內容
    report_type : str
        報告格式類型 (PDF, HTML, TXT, XRay, MRI, CT 等)
    source_url : str
        報告來源 URL
    report_id : str | None
        內部報告編號，可為空
    chr_no : str | None
        字符代碼 (遺留系統欄位)，可為空
    mod : str | None
        模式/類型代碼 (遺留系統欄位)，可為空
    report_date : str | None
        報告日期字符串，可為空
    verified_at : str | None
        驗證時間 (ISO 8601 格式)，可為空

    範例
    --------
    >>> payload = {
    ...     "uid": "uid_001",
    ...     "title": "CT 掃描報告",
    ...     "content": "報告正文...",
    ...     "report_type": "CT",
    ...     "source_url": "https://example.com/reports/001",
    ...     "report_id": "exam_123"
    ... }
    """

    uid: str
    """原始爬蟲標識符"""

    title: str
    """報告標題"""

    content: str
    """報告完整內容"""

    report_type: str
    """報告格式類型 (PDF, HTML, TXT, XRay, MRI, CT 等)"""

    source_url: str
    """報告來源 URL"""

    report_id: str | None = None
    """內部報告編號，可為空"""

    chr_no: str | None = None
    """字符代碼 (遺留系統欄位)，可為空"""

    mod: str | None = None
    """模式/類型代碼 (遺留系統欄位)，可為空"""

    report_date: str | None = None
    """報告日期字符串，可為空"""

    verified_at: str | None = None
    """驗證時間 (ISO 8601 格式)，可為空"""


class StudyInfoResponse(Schema):
    """
    檢查資訊 Schema - 嵌入在報告回應中的檢查信息。

    此 Schema 包含與報告相關的醫學影像檢查的詳細信息，
    用於在檢索報告時同時提供背景信息。

    參數
    ----------
    exam_id : str | None
        檢查 ID
    patient_name : str | None
        患者名稱
    patient_age : int | None
        患者年齡
    patient_gender : str | None
        患者性別 (M/F 等)
    exam_source : str | None
        檢查來源
    exam_item : str | None
        檢查項目
    exam_status : str | None
        檢查狀態
    equipment_type : str | None
        設備類型
    order_datetime : str | None
        訂單時間 (ISO 8601 格式)
    check_in_datetime : str | None
        簽到時間 (ISO 8601 格式)
    report_certification_datetime : str | None
        報告認證時間 (ISO 8601 格式)
    """

    exam_id: str | None = None
    """檢查 ID"""

    patient_name: str | None = None
    """患者名稱"""

    patient_age: int | None = None
    """患者年齡"""

    patient_gender: str | None = None
    """患者性別"""

    exam_source: str | None = None
    """檢查來源"""

    exam_item: str | None = None
    """檢查項目"""

    exam_status: str | None = None
    """檢查狀態"""

    equipment_type: str | None = None
    """設備類型"""

    order_datetime: str | None = None
    """訂單時間"""

    check_in_datetime: str | None = None
    """簽到時間"""

    report_certification_datetime: str | None = None
    """報告認證時間"""


class ReportResponse(Schema):
    """
    報告回應 Schema - 基礎報告檢索回應格式。

    此 Schema 定義標準的報告回應格式，包含報告的基本信息和預覽。
    用於列表和簡短展示場景。

    參數
    ----------
    uid : str
        原始爬蟲標識符
    report_id : str | None
        內部報告編號，可為空
    exam_id : str | None
        檢查 ID
    title : str
        報告標題
    report_type : str
        報告格式類型
    version_number : int
        版本號
    is_latest : bool
        是否為最新版本
    created_at : str
        建立時間 (ISO 8601 格式)
    verified_at : str | None
        驗證時間 (ISO 8601 格式)，可為空
    content_preview : str
        內容預覽 (前 500 字元)
    content_raw : str | None
        完整原始內容，可為空
    study : StudyInfoResponse | None
        相關檢查信息，可為空

    範例
    --------
    >>> response = {
    ...     "uid": "uid_001",
    ...     "report_id": "exam_123",
    ...     "title": "CT 掃描報告",
    ...     "report_type": "CT",
    ...     "version_number": 1,
    ...     "is_latest": True,
    ...     "created_at": "2024-01-15T10:30:00",
    ...     "verified_at": "2024-01-15T11:00:00",
    ...     "content_preview": "報告概要..."
    ... }
    """

    uid: str
    """原始爬蟲標識符"""

    report_id: str | None = None
    """內部報告編號，可為空"""

    exam_id: str | None = None
    """檢查 ID"""

    title: str
    """報告標題"""

    report_type: str
    """報告格式類型"""

    version_number: int
    """版本號"""

    is_latest: bool
    """是否為最新版本"""

    created_at: str
    """建立時間"""

    verified_at: str | None = None
    """驗證時間，可為空"""

    content_preview: str
    """內容預覽 (前 500 字元)"""

    content_raw: str | None = None
    """完整原始內容，可為空"""

    study: StudyInfoResponse | None = None
    """相關檢查信息，可為空"""

    class Config:
        """Pydantic 配置"""

        orm_mode = True
        """啟用 ORM 模式，支援直接從 Django 模型轉換"""


class ReportDetailResponse(ReportResponse):
    """
    報告詳細回應 Schema - 完整內容報告回應格式。

    此 Schema 繼承自 ReportResponse，額外提供完整內容和來源 URL。
    用於詳細頁面展示場景。

    參數
    ----------
    content_raw : str
        完整報告原始內容 (必填，不同於基類)
    source_url : str
        報告來源 URL

    繼承欄位
    --------
    所有 ReportResponse 的欄位都適用

    範例
    --------
    >>> detail = {
    ...     "uid": "uid_001",
    ...     "report_id": "exam_123",
    ...     "title": "CT 掃描報告",
    ...     "report_type": "CT",
    ...     "version_number": 1,
    ...     "is_latest": True,
    ...     "created_at": "2024-01-15T10:30:00",
    ...     "verified_at": "2024-01-15T11:00:00",
    ...     "content_preview": "報告概要...",
    ...     "content_raw": "完整報告內容...",
    ...     "source_url": "https://example.com/reports/001"
    ... }
    """

    content_raw: str
    """完整報告原始內容"""

    source_url: str
    """報告來源 URL"""


class ReportVersionResponse(Schema):
    """
    報告版本回應 Schema - 報告版本歷史回應格式。

    此 Schema 用於返回報告的版本信息，包括版本號、變更類型等。

    參數
    ----------
    version_number : int
        版本號
    changed_at : str
        變更時間 (ISO 8601 格式)
    verified_at : str | None
        驗證時間 (ISO 8601 格式)，可為空
    change_type : str
        變更類型 (create, update, verify, deduplicate)
    change_description : str
        變更描述
    """

    version_number: int
    """版本號"""

    changed_at: str
    """變更時間"""

    verified_at: str | None
    """驗證時間，可為空"""

    change_type: str
    """變更類型"""

    change_description: str
    """變更描述"""


class AIAnnotationResponse(Schema):
    """
    AI 註解回應 Schema - AI 註解回應格式。

    此 Schema 用於返回報告的 AI 分析結果和用戶修正。

    參數
    ----------
    id : str
        註解唯一識別符 (UUID)
    report_id : str
        報告 UID
    annotation_type : str
        註解類型 (NER, Classification, Summary 等)
    content : str
        註解內容 (JSON 或純文本)
    created_at : str
        建立時間 (ISO 8601 格式)
    updated_at : str | None
        更新時間 (ISO 8601 格式)，可為空
    created_by : str | None
        創建者名稱，可為空
    metadata : dict | None
        元資料 (JSON)，可為空
    """

    id: str
    """註解 ID (UUID)"""

    report_id: str
    """報告 UID"""

    annotation_type: str
    """註解類型"""

    content: str
    """註解內容"""

    created_at: str
    """建立時間"""

    updated_at: str | None = None
    """更新時間，可為空"""

    created_by: str | None = None
    """創建者名稱，可為空"""

    metadata: dict | None = None
    """元資料 (JSON)，可為空"""


class DateRange(Schema):
    """
    日期範圍 Schema - 可重用的日期範圍元資料。

    此 Schema 用於表示時間範圍，常用於過濾和報表。

    參數
    ----------
    start : str | None
        開始日期 (ISO 8601 格式)，可為空
    end : str | None
        結束日期 (ISO 8601 格式)，可為空
    """

    start: str | None = None
    """開始日期，可為空"""

    end: str | None = None
    """結束日期，可為空"""


class ReportFilterOptionsResponse(Schema):
    """
    報告過濾選項回應 Schema - 搜尋過濾下拉菜單選項。

    此 Schema 用於返回可用於過濾的所有選項值，
    通常用於前端下拉菜單的動態填充。

    參數
    ----------
    report_types : list[str]
        可用的報告類型列表
    report_statuses : list[str]
        可用的報告狀態列表
    mods : list[str]
        可用的模式類型列表
    verified_date_range : DateRange
        報告驗證時間的範圍
    """

    report_types: list[str]
    """可用的報告類型列表"""

    report_statuses: list[str]
    """可用的報告狀態列表"""

    mods: list[str]
    """可用的模式類型列表"""

    verified_date_range: DateRange
    """報告驗證時間的範圍"""


class ImportResponse(Schema):
    """
    導入操作回應 Schema - 報告導入操作的結果。

    此 Schema 用於返回導入操作的結果，包括是否為新報告、
    執行的操作類型等信息。

    參數
    ----------
    uid : str
        原始爬蟲標識符
    report_id : str
        內部報告編號
    is_new : bool
        是否為新建報告
    action : str
        執行的操作類型 (create, update, deduplicate 等)
    version_number : int
        報告版本號

    範例
    --------
    >>> response = {
    ...     "uid": "uid_001",
    ...     "report_id": "exam_123",
    ...     "is_new": True,
    ...     "action": "create",
    ...     "version_number": 1
    ... }
    """

    uid: str
    """原始爬蟲標識符"""

    report_id: str
    """內部報告編號"""

    is_new: bool
    """是否為新建報告"""

    action: str
    """執行的操作類型"""

    version_number: int
    """報告版本號"""


class AdvancedSearchFilters(Schema):
    """
    進階搜尋過濾器 Schema - 與 DSL 一起應用的附加過濾器。

    此 Schema 定義進階搜尋支援的所有過濾維度。

    參數
    ----------
    report_type : str | None
        報告類型過濾，可為空
    report_status : str | None
        報告狀態過濾，可為空
    report_format : list[str] | None
        報告格式多選過濾，可為空
    physician : str | None
        醫生名稱過濾，可為空
    report_id : str | None
        報告 ID 過濾，可為空
    exam_id : str | None
        檢查 ID 過濾，可為空
    date_from : str | None
        開始日期 (ISO 8601 格式)，可為空
    date_to : str | None
        結束日期 (ISO 8601 格式)，可為空
    """

    report_type: str | None = None
    """報告類型，可為空"""

    report_status: str | None = None
    """報告狀態，可為空"""

    report_format: list[str] | None = None
    """報告格式列表，可為空"""

    physician: str | None = None
    """醫生名稱，可為空"""

    report_id: str | None = None
    """報告 ID，可為空"""

    exam_id: str | None = None
    """檢查 ID，可為空"""

    date_from: str | None = None
    """開始日期，可為空"""

    date_to: str | None = None
    """結束日期，可為空"""


class BasicAdvancedQuery(Schema):
    """
    基礎進階查詢 Schema - 簡單進階搜尋模式的負載。

    此 Schema 用於簡單的全文搜尋查詢。

    參數
    ----------
    text : str
        搜尋文本
    """

    text: str
    """搜尋文本"""


class AdvancedSearchNode(Schema):
    """
    進階搜尋節點 Schema - JSON DSL 的遞歸節點定義。

    此 Schema 支援構建複雜的搜尋條件樹，
    每個節點可以是條件也可以是操作符組合。

    參數
    ----------
    operator : str | None
        邏輯操作符 (AND, OR, NOT 等)，可為空
    field : str | None
        搜尋欄位名稱，可為空
    value : Any
        搜尋值，可為任何類型
    conditions : list['AdvancedSearchNode'] | None
        子條件列表，支援遞歸，可為空

    範例
    --------
    AND 操作符的組合:

    >>> node = {
    ...     "operator": "AND",
    ...     "conditions": [
    ...         {"field": "title", "value": "CT"},
    ...         {"field": "report_type", "value": "medical"}
    ...     ]
    ... }
    """

    operator: str | None = None
    """邏輯操作符，可為空"""

    field: str | None = None
    """搜尋欄位，可為空"""

    value: Any = None
    """搜尋值"""

    conditions: list[AdvancedSearchNode] | None = None
    """子條件列表，可為空"""


class AdvancedSearchRequest(Schema):
    """
    進階搜尋請求 Schema - POST /reports/search/advanced 的請求負載。

    此 Schema 支援兩種搜尋模式：
    1. basic: 簡單全文搜尋
    2. multi: 複雜的多條件 DSL 搜尋

    參數
    ----------
    mode : Literal['basic', 'multi']
        搜尋模式，預設為 'basic'
    basic : BasicAdvancedQuery | None
        簡單查詢負載，mode='basic' 時使用
    tree : AdvancedSearchNode | None
        DSL 查詢樹，mode='multi' 時使用
    filters : AdvancedSearchFilters | None
        附加過濾器，可為空
    sort : str | None
        排序規則，可為空
    page : int
        頁碼，預設為 1
    page_size : int
        每頁記錄數，預設為 20

    範例
    --------
    基礎模式:

    >>> request = {
    ...     "mode": "basic",
    ...     "basic": {"text": "CT 掃描"},
    ...     "page": 1,
    ...     "page_size": 20
    ... }

    多條件模式:

    >>> request = {
    ...     "mode": "multi",
    ...     "tree": {
    ...         "operator": "AND",
    ...         "conditions": [...]
    ...     },
    ...     "page": 1
    ... }
    """

    mode: Literal["basic", "multi"] = "basic"
    """搜尋模式，預設 basic"""

    basic: BasicAdvancedQuery | None = None
    """簡單查詢，可為空"""

    tree: AdvancedSearchNode | None = None
    """DSL 查詢樹，可為空"""

    filters: AdvancedSearchFilters | None = None
    """附加過濾器，可為空"""

    sort: str | None = None
    """排序規則，可為空"""

    page: int = 1
    """頁碼"""

    page_size: int = 20
    """每頁記錄數"""


class AdvancedSearchResponse(Schema):
    """
    進階搜尋回應 Schema - POST /reports/search/advanced 的回應負載。

    此 Schema 返回分頁搜尋結果及過濾選項。

    參數
    ----------
    items : list[ReportResponse]
        搜尋結果報告列表
    total : int
        搜尋結果總數
    page : int
        當前頁碼
    page_size : int
        每頁記錄數
    pages : int
        總頁數
    filters : ReportFilterOptionsResponse
        可用過濾選項
    """

    items: list[ReportResponse]
    """搜尋結果"""

    total: int
    """結果總數"""

    page: int
    """當前頁碼"""

    page_size: int
    """每頁記錄數"""

    pages: int
    """總頁數"""

    filters: ReportFilterOptionsResponse
    """過濾選項"""


class ReportExportRequest(Schema):
    """
    報告匯出請求 Schema - POST /reports/export 的請求負載。

    僅需報告 ID 列表，後端會返回 CSV 或 ZIP 檔案。
    """

    report_ids: list[str]
    """要匯出的報告 ID 清單"""

    format: Literal["csv", "zip"] | None = "zip"
    """匯出格式，預設 zip"""

    filename: str | None = None
    """自訂檔名，可為空"""

    filters: AdvancedSearchFilters | None = None
    """預留欄位：未來支援依篩選條件匯出"""
