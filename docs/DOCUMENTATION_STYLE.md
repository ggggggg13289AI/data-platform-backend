# @report 模組文檔規格說明

本文檔說明 `@report` 模組採用的文檔標準，遵循 pandas DataFrame 的文檔風格。

## 文檔規格概覽

### 1. 模組級文檔

每個 Python 模組都以詳細的模組文檔開頭：

```python
"""
模組簡要描述

此模組的詳細說明，包括：
- 功能概述
- 主要組件
- 設計原則

----------
"""
```

### 2. 類級文檔

每個類都有完整的 docstring，包含：

```python
class ClassName:
    """
    類的簡要描述 - 一句話總結
    
    詳細描述:
    此類的詳細說明，包括功能、設計原則、使用場景等。
    
    特性
    ----
    - 特性 1: 描述
    - 特性 2: 描述
    
    參數
    ----------
    param1 : type
        參數 1 的描述
    param2 : type
        參數 2 的描述
    
    設計原則
    -------
    - 原則 1: 說明
    - 原則 2: 說明
    
    索引策略
    -------
    1. 索引 1: 說明
    2. 索引 2: 說明
    
    範例
    --------
    >>> # 使用範例
    >>> result = ClassName(...)
    
    參考資訊
    --------
    - RelatedClass: 相關類描述
    - related_method: 相關方法描述
    
    另見
    ----
    OtherClass: 另一個相關類
    """
```

### 3. 欄位級文檔

模型欄位使用内連註解和 help_text：

```python
class Model(models.Model):
    """模型描述"""
    
    # ============================================================================
    # 欄位分類 - 說明該組欄位的用途
    # ============================================================================
    
    field_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text='欄位的具體說明'
    )
    """欄位簡要描述"""
```

### 4. 方法級文檔

每個方法都有完整的 docstring：

```python
def method_name(self, param1: str, param2: int) -> dict:
    """
    方法簡要描述 - 一句話總結
    
    詳細描述，解釋方法做了什麼、為什麼這樣設計。
    
    Parameters
    ----------
    param1 : str
        參數 1 的描述
    param2 : int
        參數 2 的描述
    
    Returns
    -------
    dict
        返回值的描述，包括結構和含義
    
    Notes
    -----
    - 注意事項 1
    - 注意事項 2
    
    Examples
    --------
    >>> result = obj.method_name('value', 42)
    >>> print(result)
    {'key': 'value'}
    
    See Also
    --------
    related_method: 相關方法
    """
```

### 5. Schema 級文檔

API Schema 使用詳細的類註解：

```python
class ResponseSchema(Schema):
    """
    回應 Schema 簡要描述
    
    詳細描述此 Schema 的用途和使用場景。
    
    參數
    ----------
    field1 : type
        字段 1 描述
    field2 : type | None
        字段 2 描述，可為空
    
    範例
    --------
    >>> response = {
    ...     "field1": "value",
    ...     "field2": None
    ... }
    """
    
    field1: str
    """字段 1"""
    
    field2: str | None = None
    """字段 2，可為空"""
```

## 文檔內容結構

### 按序的標題層級

```
模組級文檔 (無標題)
    ↓
特性 (### 特性)
    ↓
參數 (### 參數)
    ↓
設計原則 (### 設計原則)
    ↓
索引策略 (### 索引策略)
    ↓
範例 (### 範例)
    ↓
參考資訊 (### 參考資訊)
    ↓
另見 (### 另見)
```

### 標準章節名稱 (中文)

| 英文 | 中文 | 用途 |
|------|------|------|
| Description | 描述 | 詳細說明 |
| Parameters | 參數 | 輸入參數 |
| Returns | 返回 | 返回值說明 |
| Raises | 異常 | 可能的異常 |
| Notes | 注意事項 | 特殊說明 |
| Examples | 範例 | 使用示例 |
| See Also | 另見 | 相關項目 |

## 特殊格式規則

### 1. 參數列表格式

```
參數
----------
param_name : type
    參數描述，可跨多行
    - 可使用項目符號
    - 對複雜參數進行詳細說明
```

### 2. 類型提示

```
str          # 字符串
int          # 整數
float        # 浮點數
bool         # 布爾值
list[str]    # 字符串列表
dict[str, int]  # 字符串到整數的映射
Type | None  # 可為 None 的類型
```

### 3. 代碼示例

```python
# ✅ 推薦
>>> from mymodule import MyClass
>>> obj = MyClass(param='value')
>>> result = obj.method()
>>> print(result)
{'status': 'success'}

# ❌ 不推薦
# 缺少預期輸出
>>> x = something()
```

### 4. 注意事項

```
Notes
-----
- 使用項目符號列出要點
- 每個要點保持簡潔明瞭
- 重要信息用粗體 **強調**
```

## 文檔維護指南

### 1. 更新頻率

- 新增功能時立即更新文檔
- 修改 API 時更新相應文檔
- 每個版本發佈前檢查文檔一致性

### 2. 一致性檢查

```python
# ✅ 參數名稱與函數簽名一致
def method(param1, param2):
    """
    參數
    ----------
    param1 : type
    param2 : type
    """

# ❌ 參數不一致
def method(param1, param2):
    """
    參數
    ----------
    param_a : type
    param_b : type
    """
```

### 3. 範例測試

```python
# ✅ 範例應能直接運行
>>> x = 5
>>> print(x * 2)
10

# ❌ 範例不完整
>>> print(x * 2)  # 缺少 x 的定義
```

## 文檔主題指南

### Report 模型文檔主題

1. **功能描述**: 報告模型的核心功能
2. **特性列表**: 主要特性和優勢
3. **參數說明**: 各字段的詳細說明
4. **設計原則**: 扁平化結構、去正規化等
5. **索引策略**: 複合索引的優化策略
6. **範例代碼**: 常見使用場景
7. **相關模型**: ReportVersion、ReportSummary 等

### ReportService 方法文檔主題

1. **功能描述**: 方法的核心作用
2. **參數說明**: 輸入參數及類型
3. **返回值**: 返回數據結構
4. **業務邏輯**: 方法的具體實現邏輯
5. **範例代碼**: 調用方式
6. **錯誤處理**: 可能的異常情況

## 國際化考慮

- 所有文檔使用繁體中文 (Traditional Chinese)
- 技術術語保留英文 (如 UUID, JSON, SQL)
- 使用通用術語而非台灣或大陸特定詞匯
- 日期格式使用 ISO 8601 (YYYY-MM-DD)

## 工具支援

### 生成文檔

```bash
# 生成 HTML 文檔
python -m pydoc -w report.models

# 使用 Sphinx
sphinx-apidoc -o docs src/report
```

### 驗證文檔

```bash
# 檢查 docstring 格式
python -m doctest report/models.py

# 使用 pydocstyle 檢查規範
pydocstyle report/
```

## 範例: Report 模型完整文檔

見 `models.py` 中的 Report 類，包含：

- 詳細的模型描述
- 所有字段的參數說明
- 設計原則和索引策略
- 實際使用範例
- 相關模型和方法的參考

## 參考資源

- pandas 文檔: https://pandas.pydata.org/docs/
- NumPy 文檔風格: https://numpydoc.readthedocs.io/
- PEP 257 - Docstring Conventions: https://www.python.org/dev/peps/pep-0257/
- Google Python Style Guide: https://google.github.io/styleguide/pyguide.html

