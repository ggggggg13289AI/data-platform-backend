# Changelog

All notable changes to the Medical Imaging Management System Django backend
will be documented in this file. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `POST /api/v1/reports/imaging-platform-export`: returns
  `[{AccessionNumber, content, imaging_findings, impression, category,
  confidence, guideline}]` for pushing classification results to an imaging
  platform group (payload only; outbound push wired later).
- AI annotation conditions in project resource advanced-search
  (`POST /api/v1/projects/{id}/search/advanced`): `annotation.classification`,
  `annotation.confidence_score`, `annotation.answer` are extracted from the
  multi-condition tree and applied against each report's latest Classification
  annotation.
- `SearchResultItem.annotation` (`AIAnnotationSummary`): advanced-search rows
  now carry the latest AI annotation so AI columns render inline.

### Fixed
- Advanced-search AI filter matches a report's *latest* non-deprecated
  Classification annotation (consistent with the displayed value), instead of
  any historical/other-guideline annotation.

## [1.5.0] - 2026-05-26

### Added
- Multi-question AI annotation pipeline: `ClassificationGuideline.questions`
  JSONField with optional `depends_on` chains, structured prompt builder,
  and JSON parser that returns a `dict[Q1..Qn]` of validated answers.
  `AIAnnotation.metadata.structured_answers` now persists per-question
  answers separately (not a flattened string).
- AI annotation filter API on `GET /api/v1/projects/{id}/resources`:
  new query params `classification`, `confidence_min`, `confidence_max`,
  and `answers` (JSON dict). Implemented as page-scoped post-filter via
  `ResourceAggregator._apply_ai_filters`.
- `AIAnnotationSummary` embedded in `ProjectResourceItem`, including
  `structured_answers` and `confidence_score`, so the frontend can render
  AI results inline in the resource list.
- `imaging_findings` and `impression` fields on `ReportResponse` and
  `_build_report_item` mapping, so CSV export and detail views can show
  the full structured report.
- `POST /api/v1/ai/guidelines/{id}/restore` for soft-delete restore UX.
- Integration test suite `tests/test_multi_question_structured.py`
  (8 tests) covering parser + filter behavior.

### Changed
- `BatchAnalysisService.MAX_BATCH_SIZE`: 500 → 9999.
- `ProjectService.MAX_BATCH_SIZE`: 500 → 9999.
- `NINJA_JWT.ACCESS_TOKEN_LIFETIME`: 1 hour → 1 day.
- `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` extended for LAN access
  (`10.103.51.2`, ports 3000 / 4173).
- `APP_VERSION` synced with package version (was stale at 1.1.0).

### Fixed
- AI batch test endpoint: replaced non-existent `router.create_response`
  call with the standard Ninja response pattern.
- AI batch analysis: model parameter now correctly forwarded to the LLM
  provider.
- Circular dependency between `ai/0001_initial` and `report/0010` migrations.

## [1.4.0] - 2026-04-21

Baseline release prior to this changelog. See git history before commit
`b834d57` for earlier changes.
