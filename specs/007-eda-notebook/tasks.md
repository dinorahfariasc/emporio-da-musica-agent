# Tasks: EDA Notebook

**Input**: `spec.md`, `plan.md`

## Tasks

- [x] T001 [US1] Create `analysis/pyproject.toml` (uv, Python 3.13, pandas/matplotlib/jupyter/nbconvert/ipykernel)
- [x] T002 [US1] Write `analysis/eda.ipynb`: load the 5 CSVs, schema/size overview
- [x] T003 [US1] Products section: price/stock distributions, status mix, category mix
- [x] T004 [US1] Orders section: value/status/payment distributions, order-total-vs-items check
- [x] T005 [US2] Promotions section: active vs duplicate discounts per product
- [x] T006 [US2] Customers section: shared-email check
- [x] T007 [US2] Summary cell mapping each finding to its row in `docs/data-quality-report.md`
- [x] T008 [US1] Execute headless (`uv run jupyter nbconvert --execute --to notebook --inplace eda.ipynb`)
- [x] T009 [US1] Export `analysis/eda.html` (`uv run jupyter nbconvert --to html eda.ipynb`)
- [x] T010 Write `analysis/README.md` (how to run)
- [x] T011 Append DL-DATA-001 to `docs/decision-log.md`; update `docs/HANDOFF.md` session log
