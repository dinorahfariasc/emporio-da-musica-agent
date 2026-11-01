# Feature Specification: EDA Notebook

**Feature Branch**: `007-eda-notebook`

**Created**: 2026-11-01

**Status**: Draft

**Input**: Issue #22 (P2) — exploratory data analysis notebook over `challenge/data/`.

## Scope

A reproducible, read-only EDA notebook over the five CSVs in `challenge/data/`
(products, orders, order_items, customers, promotions) plus the policy PDF for context.
It does not replace `docs/data-quality-report.md` (the authoritative, ETL-generated anomaly
list) — it complements it with distributions, cross-table patterns, and visual evidence for
the anomalies already catalogued there, plus any new observations.

## User Scenarios & Testing

### User Story 1 - Reviewer skims data shape and quality (Priority: P1)

A reviewer (hiring panel or future contributor) wants a quick, visual understanding of the
dataset: sizes, distributions (price, stock, order totals), category mix, and the known data
quality issues, without reading raw CSVs.

**Independent Test**: open the exported HTML and see summary stats + charts for all 5 tables
within the first few cells.

**Acceptance Scenarios**:
1. **Given** the notebook, **When** run top to bottom with `uv run jupyter nbconvert --execute`,
   **Then** it completes without errors and produces deterministic output (no network/LLM calls).
2. **Given** the exported HTML, **When** opened in a browser, **Then** all charts render inline
   (no external notebook runtime needed).

### User Story 2 - Anomalies are traceable to the data quality report (Priority: P2)

Each anomaly surfaced in the notebook (price/stock/promo outliers, order total mismatches,
duplicate promotions, etc.) references the matching row in
`docs/data-quality-report.md` so the two documents stay consistent.

**Independent Test**: grep the notebook for each anomaly name in the report's summary table;
all should appear.

## Requirements

- **FR-001**: Notebook MUST load the 5 CSVs directly from `challenge/data/` (read-only, no copy).
- **FR-002**: Notebook MUST run deterministically with `uv run` and no API keys or network calls.
- **FR-003**: Notebook MUST cover: table sizes/schemas, price/stock distributions, category mix,
  order value/status/payment patterns, promotion overlap, and the known anomalies from the data
  quality report.
- **FR-004**: Output MUST be committed both as the `.ipynb` (with outputs) and an exported
  static `.html`.
- **FR-005**: MUST NOT modify `backend/app`, `frontend/`, or the CSVs themselves.

## Out of Scope

- Replacing or regenerating `docs/data-quality-report.md` (that stays ETL-owned, DL-002).
- Statistical modeling or forecasting — this is descriptive EDA only.
