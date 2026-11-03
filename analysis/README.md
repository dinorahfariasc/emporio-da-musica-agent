# EDA — Empório da Música

Exploratory data analysis over `inputs/data/`. Standalone `uv` project, separate from
`backend/` and `frontend/`, read-only.

## Run

```bash
cd analysis
uv sync
uv run jupyter nbconvert --execute --to notebook --inplace eda.ipynb
uv run jupyter nbconvert --to html eda.ipynb
```

`eda.ipynb` is committed with outputs baked in; `eda.html` is a static export (open directly in
a browser, no Jupyter runtime needed).

`build_notebook.py` regenerates `eda.ipynb` from scratch (its cell sources are the source of
truth); re-run it, then the two nbconvert commands above, after editing the notebook's content.

See `specs/007-eda-notebook/` for the spec/plan/tasks and `docs/data-quality-report.md` for the
authoritative anomaly catalogue this notebook cross-references.
