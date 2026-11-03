# Implementation Plan: EDA Notebook

**Branch**: `007-eda-notebook` | **Date**: 2026-11-01 | **Spec**: `spec.md`

## Summary

Add a small, standalone `analysis/` uv project (separate from `backend/` and `frontend/`, so it
carries its own data-science dependencies — pandas, matplotlib, jupyter — without bloating the
agent's runtime image) containing one notebook, `eda.ipynb`, that loads the source CSVs with
pandas and renders matplotlib charts. Export to static HTML with `nbconvert` and commit both.

## Technical Context

**Language/Version**: Python 3.13 (matches backend)

**Primary Dependencies**: pandas, matplotlib, jupyter, nbconvert, ipykernel

**Storage**: none — reads `inputs/data/*.csv` directly, read-only

**Testing**: the notebook itself is the artifact; "test" = `uv run jupyter nbconvert --execute`
succeeds with exit code 0 (no network, no randomness, so output is reproducible)

**Target Platform**: local dev machine; outputs committed, not deployed

## Structure

```
analysis/
  pyproject.toml       # uv project: pandas, matplotlib, jupyter, nbconvert
  eda.ipynb            # the notebook (committed with outputs)
  eda.html             # nbconvert export (committed)
  README.md            # how to run it
```

## Approach

1. `uv init --no-workspace analysis` style minimal pyproject (does not join the backend's uv
   workspace — avoids coupling analysis deps to the API's dependency graph).
2. One notebook, sections in order: load & schema overview → products (price/stock/status/specs)
   → categories → orders & order_items (value, status, payment method, totals-vs-items check) →
   customers (incl. shared email check) → promotions (active vs duplicate) → cross-cutting
   summary tying each anomaly to `docs/data-quality-report.md`.
3. Charts via matplotlib only (no seaborn dependency) — histograms, bar counts, a couple of
   scatter/box plots.
4. Execute headless (`--execute`) so outputs are baked in, then `nbconvert --to html`.

## Constitution Check

- Principle III (clean, traceable data): the notebook treats `inputs/` as read-only and cites
  the decision log for every interpretation; no new cleaning rule is invented here that isn't
  already in `docs/data-quality-report.md`.
- No agent/LLM code touched; no deterministic-fact rule changed.
