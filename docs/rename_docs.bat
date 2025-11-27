@echo off
REM Main documentation files (001-099 series)
move docs\README.md docs\001_README.md 2>nul
move docs\DOCUMENT_INDEX.md docs\002_DOCUMENT_INDEX.md 2>nul
move docs\DEVELOPMENT_SETUP.md docs\003_DEVELOPMENT_SETUP.md 2>nul
move docs\API_REFERENCE.md docs\004_API_REFERENCE.md 2>nul
move docs\TROUBLESHOOTING.md docs\005_TROUBLESHOOTING.md 2>nul
move docs\PRD_PHASE3.md docs\006_PRD_PHASE3.md 2>nul
move docs\PRD_PHASE3_TECHNICAL.md docs\007_PRD_PHASE3_TECHNICAL.md 2>nul
move docs\README.en.md docs\008_README_EN.md 2>nul
move docs\README.zh-TW.md docs\009_README_ZH_TW.md 2>nul
move docs\BACKEND_INTEGRATION_CHECKLIST.md docs\010_BACKEND_INTEGRATION_CHECKLIST.md 2>nul
move docs\STUDY_SEARCH_COMPLETION_REPORT.md docs\011_STUDY_SEARCH_COMPLETION_REPORT.md 2>nul

REM Archive/deprecated index files to be removed
move docs\00_DOCUMENTATION_INDEX.md docs\archive\DEPRECATED_00_DOCUMENTATION_INDEX.md 2>nul
move docs\DOCUMENTATION_INDEX.md docs\archive\DEPRECATED_DOCUMENTATION_INDEX.md 2>nul
move docs\DOCUMENTATION_COMPLETE.md docs\archive\DEPRECATED_DOCUMENTATION_COMPLETE.md 2>nul
move docs\ARCHIVE_INDEX.md docs\archive\DEPRECATED_ARCHIVE_INDEX.md 2>nul
move docs\01_PROJECT_OVERVIEW.md docs\archive\fastapi-v1\A001_PROJECT_OVERVIEW_FASTAPI.md 2>nul

echo Documentation renaming completed
