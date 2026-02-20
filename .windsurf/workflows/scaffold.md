---
description: Scaffold a new module (data loader, model module, or Streamlit page)
---

## Scaffold a new data loader

1. Identify the source name (e.g. `iea`, `gsma`, `borderstep`)
2. Create `src/data/loader_<source>.py` following the pattern in `src/data/loader_iea.py`
3. Add `SOURCE_ID`, `RAW_DIR`, and at least one load function returning a cleaned DataFrame
4. Write tests in `tests/unit/test_loader_<source>.py` using fixtures from `tests/conftest.py`
5. Run tests:
// turbo
```
uv run pytest tests/unit/test_loader_<source>.py -v
```

## Scaffold a new model module

1. Create `src/models/<module>.py` following the pattern in `src/models/datacentres.py`
2. Import `validate_output` and `OutputRow` from `src/models/schema.py`
3. Return a DataFrame validated against `OutputSchema`
4. Write tests in `tests/unit/test_<module>.py` — use fixtures from `tests/conftest.py`
5. Run tests:
// turbo
```
uv run pytest tests/unit/test_<module>.py -v
```

## Scaffold a new Streamlit page

1. Create `app/pages/<N>_<PageName>.py` following the pattern in `app/pages/1_Explorer.py`
2. Import data via `from app.stub_data import get_stub_dataframe` (or real loader once available)
3. Use `@st.cache_data` for all expensive computations
4. All charts must use Plotly — no matplotlib
5. Preview:
// turbo
```
uv run streamlit run app/Home.py
```
