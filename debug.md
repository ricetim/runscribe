# RunScribe Debug Log

All debugging notes, build issues, and fixes encountered during implementation.

---

## 2026-03-04

### Task 1 — Backend scaffold

**Issue: `setuptools.backends.legacy` not available**
- System pip/setuptools is too old to support the `setuptools.backends.legacy:build` backend
- Fix: changed `pyproject.toml` to `build-backend = "setuptools.build_meta"`

**Issue: Python 3.12 not installed**
- System has Python 3.10.18
- Fix: updated `requires-python = ">=3.10"` in `pyproject.toml`; Docker image uses `python:3.11-slim`

**Issue: `@app.on_event("startup")` deprecation warning**
- FastAPI recommends the `lifespan` pattern (asynccontextmanager) in modern versions
- Fix: replaced `on_event` with `@asynccontextmanager async def lifespan(app)` + `FastAPI(lifespan=lifespan)`

**Issue: pytest running test suite twice**
- Root cause: missing `[tool.pytest.ini_options]` in `pyproject.toml` caused pytest to discover tests from the wrong root
- Fix: added `testpaths = ["tests"]` and `asyncio_mode = "auto"` to `pyproject.toml`

---

### Task 2 — Docker Compose

No issues. Noted that Docker Compose requires the frontend to be built before serving; nginx proxies `/api/` to the backend container by hostname.

---

### Task 3 — Data models

No issues. All 4 tests passed on first run after model creation.

---

### Task 4 — .fit parser

No issues. `fitparse` installed cleanly. Three fixture-dependent tests skip until a `sample.fit` is placed at `backend/tests/fixtures/sample.fit`.

**Note for Tim:** Drop any `.fit` file exported from your Coros Pace 4 at `backend/tests/fixtures/sample.fit` to enable the full parser test suite.

---

### Task 5 — Activities router

No issues. 5 tests pass; 2 skip pending `sample.fit`.

---

### Task 6 — Frontend scaffold

**Issue: `npm create vite@latest` cancelled — Node.js version conflict**
- `create-vite@latest` requires Node `^20.19.0 || >=22.12.0`; system has Node v21.7.1
- Fix: used `npm create vite@5` which is compatible with Node 21

**Issue: Vite scaffold "remove existing files" deleted frontend/Dockerfile and nginx.conf**
- The scaffold prompt defaulted to "Remove existing files" which wiped Docker files committed earlier
- Fix: recreated both files after the scaffold; noted to always scaffold into an empty directory in future

**Issue: `npx tailwindcss init` failed with latest Tailwind**
- Tailwind v4 changed the init command; `npx tailwindcss init -p` is v3 syntax
- Fix: explicitly installed `tailwindcss@3` with `npm install -D tailwindcss@3 postcss autoprefixer`

---

## Running metrics research notes

Research complete — see `docs/running_metrics_research.md`.

### Books to procure (flagged by research agent)

These sources contain formulas/methodology used in RunScribe's analytics engine. The user should obtain them:

| Book | Author(s) | Relevance |
|------|-----------|-----------|
| *Oxygen Power* | Daniels & Gilbert, 1979 | Original VDOT regression equations |
| *Daniels' Running Formula* (3rd ed.) | Jack Daniels | VDOT pace tables, training zones, plan structure |
| *Training and Racing with a Power Meter* | Allen & Coggan | Power-based TSS formula, FTP methodology |
| *The Triathlete's Training Bible* | Joe Friel | 30-min lactate threshold field test protocol |
| *Physiology of Sport and Exercise* (MacDougall et al., eds.) | Various | Contains Banister's 1991 impulse-response model chapter (ATL/CTL/TSB) |

### Freely available key papers

All of these can be implemented without licensing concerns:

| Metric | Paper | DOI/Source |
|--------|-------|------------|
| VO2Max (sub-max) | Åstrand & Ryhming, 1954 | 10.1152/jappl.1954.7.2.218 |
| VO2Max (Cooper test) | Cooper, 1968 | JAMA |
| Race prediction | Riegel, 1981 | *American Scientist* 69(3) |
| ATL/CTL/TSB | Morton et al., 1990 | 10.1152/jappl.1990.69.3.1171 |
| Grade-adjusted pace | Minetti et al., 2002 | 10.1152/japplphysiol.01177.2001 |
| Lactate threshold | Conconi et al., 1982 | 10.1152/jappl.1982.52.4.869 |
| Cadence optimization | Heiderscheit et al., 2011 | PMC3022995 |
