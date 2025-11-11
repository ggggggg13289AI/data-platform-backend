# Excel Data Integration for Study Search

## Overview

Study Search has been updated to use real data from the Excel file `20251029130203.xlsx` with Chinese column name mapping. This document describes the implementation and how to use it.

## Architecture

### Components

1. **ExcelDataLoader** (`backend/app/utils/excel_loader.py`)
   - Loads Excel files with Chinese column names
   - Maps Chinese column names to database field names
   - Handles date conversion and type conversion
   - Supports multiple variations of Chinese column names for flexibility

2. **DatabaseInitializer** (`backend/app/db/init_data.py`)
   - Initializes DuckDB on application startup
   - Automatically loads data from Excel file if it exists
   - Creates table and inserts data on first run
   - Logs detailed information about the loading process

3. **FastAPI Lifespan** (`backend/app/main.py`)
   - Integrated with FastAPI application startup
   - Calls DatabaseInitializer on application startup
   - Runs before any API endpoints are available

### Column Mapping

The Excel file's Chinese column names are automatically mapped to database field names:

| Excel Column (Chinese) | Database Field | Type |
|------------------------|----------------|------|
| 检查号 / 檢查號 | exam_id | VARCHAR (Primary Key) |
| 醫療記錄編號 | medical_record_no | VARCHAR |
| 應用訂單編號 | application_order_no | VARCHAR |
| 患者名稱 | patient_name | VARCHAR |
| 患者性別 | patient_gender | VARCHAR |
| 患者年齡 | patient_age | INTEGER |
| 検査ステータス / 檢查狀態 | exam_status | VARCHAR |
| 檢查來源 | exam_source | VARCHAR |
| 檢查項目 | exam_item | VARCHAR |
| 檢查描述 | exam_description | VARCHAR |
| 訂單日期時間 | order_datetime | TIMESTAMP |
| 入院日期時間 | check_in_datetime | TIMESTAMP |
| 報告認證日期時間 | report_certification_datetime | TIMESTAMP |
| 認證醫生 | certified_physician | VARCHAR |

The mapping supports multiple variations of Chinese characters (Traditional, Simplified, Japanese) for robustness.

## Setup Instructions

### Prerequisites

- Python 3.8+
- Backend dependencies installed

### Installation

1. **Install backend dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

   Required packages:
   - `fastapi==0.104.1` - Web framework
   - `duckdb==0.9.2` - Database
   - `openpyxl==3.11.0` - Excel reading
   - `pydantic==2.5.0` - Data validation

2. **Verify Excel file**:
   - Ensure `20251029130203.xlsx` exists in the project root
   - The file should contain medical examination data with Chinese column headers

3. **Start the backend**:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   You should see in the logs:
   ```
   Application startup: Initializing database...
   Found Excel file: 20251029130203.xlsx
   Loaded [X] records from Excel
   Creating medical_examinations_fact table...
   Table created successfully
   Successfully inserted [X] records into database
   Database initialization complete
   ```

### Data Flow

1. **Application Startup**:
   - FastAPI application starts
   - Lifespan context manager triggers
   - DatabaseInitializer.init_database() is called

2. **Excel File Discovery**:
   - Looks for files in this order:
     - `20251029130203.xlsx` (specific file)
     - `medical_examinations.xlsx`
     - `data.xlsx`
   - Checks project root first, then current directory

3. **Data Loading**:
   - ExcelDataLoader reads the Excel file
   - Maps Chinese column names to database fields
   - Converts date formats to ISO format
   - Converts age to integers

4. **Database Initialization**:
   - Creates `medical_examinations_fact` table in DuckDB
   - Inserts data in batches of 100 records
   - Commits transaction on success

5. **Ready for Queries**:
   - Study Search API endpoints become available
   - All searches query the populated `medical_examinations_fact` table

## API Integration

The Study Search API automatically uses the populated database:

### Search Endpoint
```
GET /api/v1/studies/search?q=&exam_status=&exam_source=&exam_item=&start_date=&end_date=&page=1&page_size=20
```

Response includes real data from the Excel file:
```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8,
  "studies": [
    {
      "exam_id": "E001",
      "medical_record_no": "MR001",
      "patient_name": "Patient Name",
      "exam_status": "completed",
      "exam_source": "OPD",
      "exam_item": "X-Ray",
      "order_datetime": "2025-10-29T13:02:03"
    }
    // ... more records
  ]
}
```

### Filter Options Endpoint
```
GET /api/v1/studies/filters/options
```

Returns distinct values from the Excel data:
```json
{
  "exam_statuses": ["pending", "completed", "failed"],
  "exam_sources": ["OPD", "IPD", "ED"],
  "exam_items": ["X-Ray", "CT", "MRI"],
  "equipment_types": ["General", "Digital", "3D"]
}
```

## Troubleshooting

### Excel File Not Found
**Error**: "No Excel file found"
**Solution**: Ensure `20251029130203.xlsx` exists in the project root directory

### Unmapped Columns Warning
**Message**: "Unmapped columns found: [...]"
**Explanation**: The Excel file has columns that aren't recognized
**Solution**: Check the column names in Excel and update COLUMN_MAPPING in ExcelDataLoader if needed

### No Data Loaded
**Error**: "No data loaded from Excel file"
**Possible Causes**:
- Excel file is empty (no data rows)
- All rows are header rows
- File is corrupted

**Solution**: Verify Excel file has data starting from row 2

### Database Connection Error
**Error**: "Database query error"
**Solution**: Ensure DuckDB file path is writable and the directory exists

### Column Mapping Issues
**Issue**: Some columns aren't imported correctly
**Solution**: Check the exact column names in your Excel file and add them to COLUMN_MAPPING if they differ from the predefined list

## Performance Considerations

- **Batch Insertion**: Data is inserted in batches of 100 records for memory efficiency
- **Read-Only Connection**: After initialization, the database connection is read-only for safety
- **Automatic Discovery**: Excel file is automatically discovered on startup, no manual configuration needed

## Customization

### Adding New Column Mappings

If your Excel file has different column names, update the COLUMN_MAPPING in `backend/app/utils/excel_loader.py`:

```python
COLUMN_MAPPING = {
    'Your Chinese Column Name': 'database_field_name',
    # ... existing mappings
}
```

### Changing Excel File Name

The application looks for files in order. To use a different file name, modify the search order in `backend/app/db/init_data.py`:

```python
excel_candidates = [
    "your_file_name.xlsx",  # Add your file here
    "20251029130203.xlsx",
    # ... others
]
```

### Adjusting Batch Size

To change the batch insertion size, modify in `backend/app/db/init_data.py`:

```python
batch_size = 100  # Change this number
```

## Testing

A test script is provided: `test_excel_integration.py`

Run it to validate the Excel loading setup:

```bash
python test_excel_integration.py
```

This will:
1. Test Excel file loading
2. Verify table creation SQL
3. Generate INSERT SQL
4. Test full DuckDB integration with a temporary database

## Files Modified

1. **backend/app/utils/excel_loader.py** - New file for Excel loading with Chinese column mapping
2. **backend/app/db/init_data.py** - New file for database initialization
3. **backend/app/db/database.py** - Modified to support write connections
4. **backend/app/main.py** - Added lifespan context manager for initialization
5. **backend/requirements.txt** - Already includes openpyxl and other dependencies

## Frontend Integration

No changes required to the frontend. The Study Search component automatically:
- Uses the populated data from DuckDB
- Gets filter options from the database
- Performs searches across real data

## Next Steps

1. Install backend dependencies
2. Verify `20251029130203.xlsx` is in the project root
3. Start the backend server
4. Test with the frontend application or use the test script
5. Verify data appears in Study Search results

## FAQ

**Q: Will the data be lost when the backend restarts?**
A: No. DuckDB persists the data to disk. The initialization process runs on each startup but uses the existing data if the table already exists.

**Q: Can I update the data?**
A: Currently, the loader creates/appends data on startup. To reload, delete the `.duckdb` file and restart the backend.

**Q: What if the Excel file format changes?**
A: Update the COLUMN_MAPPING to match the new column names, or use the flexible column mapping that supports variations.

**Q: How many rows can it handle?**
A: DuckDB can handle millions of rows efficiently. The batch insertion is designed for large datasets.

**Q: Can I use multiple Excel files?**
A: Currently, the system loads from a single file. To support multiple files, modify DatabaseInitializer.init_database() to load multiple files.
