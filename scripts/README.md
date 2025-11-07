# Django Backend Scripts

Utility scripts for data migration, testing, and administrative tasks.

## Scripts

### migrate_from_duckdb.py
Data migration script that imports medical examination records from the FastAPI backend's DuckDB database into the Django backend's PostgreSQL database.

**Usage:**
```bash
python scripts/migrate_from_duckdb.py
```

**Environment Variables:**
- `DUCKDB_PATH`: Path to DuckDB database file (default: `../backend/medical_imaging.duckdb`)
- Standard Django/PostgreSQL connection variables (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)

**Features:**
- Validates DuckDB and PostgreSQL connections
- Imports with error handling and reporting
- Verifies count integrity
- Detects duplicates
- Clear status reporting

### run_migration.py
Migration runner script that sets up the correct environment and executes the migration.

**Usage:**
```bash
python scripts/run_migration.py
```

### test_bulk_import_performance.py
Performance testing script that demonstrates the N+1 query problem and the benefits of using bulk_create.

**Usage:**
```bash
python scripts/test_bulk_import_performance.py
```

**What It Tests:**
- N+1 problem with individual saves
- Optimized bulk_create approach
- Performance comparison and metrics

## Organization

All scripts in this directory follow these principles:
- **Single Responsibility**: Each script has one clear purpose
- **Error Handling**: Fail fast with explicit error messages
- **Documentation**: Clear docstrings and usage instructions
- **Django Integration**: Proper Django setup for ORM access
