# RitterRadar — Implementation Plan

**Status:** Draft v1  
**Created:** 2026-06-25  
**Derived from:** `documents/00_VISION.md`

---

## 1. Project Summary

RitterRadar is a local Python web application that discovers, stores, and displays German medieval markets (and similar events) on an interactive map. It consists of two cooperating subsystems:

1. **Crawler subsystem** — background, adapter-based web scrapers that harvest event data from configured sources and store it in SQLite.
2. **UI subsystem** — a FastAPI-powered local web application with a Leaflet/OpenStreetMap frontend rendered in medieval visual style.

---

## 2. Non-Negotiable Constraints

These constraints come directly from the vision and apply to every phase:

| Constraint | Detail |
|---|---|
| License | GPLv3; header in every source file |
| Language | Python only for backend and tooling; HTML/CSS/JS for frontend |
| Commits | Conventional Commit format; `Signed-off-by` trailer; no AI/tool references |
| Version | SemVer; single source of truth in `pyproject.toml`; start at `0.0.0`; patch++ per commit |
| Test coverage | 90 % line coverage goal (pytest-cov); enforced in CI configuration |
| Dependencies | Pinned exact versions in lock file; most recent stable releases |
| Code quality | ruff (lint + format), mypy (strict types) |
| Documentation | Sphinx with autodoc; all public interfaces documented; README; arch doc; adapter guide |
| Architecture docs | C4 model (Context, Container, Component, Code diagrams) |
| Review cycles | Periodic severity-rated review passes; high-severity findings fixed immediately |
| Crawling ethics | Random 0–2 s delay between requests; exponential backoff on retries; polite user-agent |
| Failure isolation | A broken crawler adapter must never crash the web server or other adapters |

---

## 3. Chosen Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Web framework | **FastAPI** | Modern, typed, async-native, excellent auto-docs |
| ORM | **SQLModel** (wraps SQLAlchemy 2.x) | Single class definition for DB model and Pydantic schema |
| Database | **SQLite** | Zero-infrastructure local storage |
| Migrations | **Alembic** | Schema evolution without data loss |
| HTTP client | **httpx** | Async-capable, better than requests for FastAPI apps |
| HTML parsing | **BeautifulSoup4** + **lxml** | Proven, adapter-friendly parsing |
| Geocoding | **geopy** (Nominatim) | OpenStreetMap-compatible; free; cacheable |
| Background work | **asyncio** tasks + `anyio` thread pool | Built into FastAPI; no extra broker |
| Map | **Leaflet.js** + OpenStreetMap tiles | Free, offline-capable tiles; rich plugin ecosystem |
| Frontend interactivity | Vanilla JS + **htmx** | Minimal JS while enabling partial page updates |
| Settings | **pydantic-settings** | Typed config from env / `.env` file |
| Source config | **YAML** file (`config/sources.yaml`) | Human-editable, no code change needed to add a source |
| Lint | **ruff** | Replaces flake8 + isort + pyupgrade |
| Format | **ruff format** | Consistent style |
| Type check | **mypy** (strict) | Catches interface errors early |
| Tests | **pytest** + **pytest-asyncio** + **pytest-cov** | Async test support; coverage reporting |
| Docs | **Sphinx** + **autodoc** + **napoleon** | API docs from docstrings |
| Task runner | **just** (`justfile`) | Simple cross-platform command runner |

---

## 4. Repository Structure

```
RitterRadar/
├── src/
│   └── ritterradar/
│       ├── __init__.py              # version = "0.0.0"
│       ├── main.py                  # FastAPI app + lifespan
│       ├── config.py                # pydantic-settings AppSettings
│       ├── models/
│       │   ├── __init__.py
│       │   ├── market.py            # Market SQLModel
│       │   ├── source.py            # Source SQLModel
│       │   ├── crawl_job.py         # CrawlJob SQLModel
│       │   └── user_settings.py     # UserSettings SQLModel (single row)
│       ├── database/
│       │   ├── __init__.py
│       │   ├── engine.py            # engine, create_tables()
│       │   └── session.py           # get_session() dependency
│       ├── crawler/
│       │   ├── __init__.py
│       │   ├── base_adapter.py      # AbstractCrawlerAdapter ABC
│       │   ├── http_client.py       # PoliteHttpClient (delays, backoff, UA)
│       │   ├── queue.py             # CrawlQueue (asyncio.Queue + state machine)
│       │   ├── worker.py            # CrawlWorker (runs jobs, isolates failures)
│       │   ├── registry.py          # maps adapter_name → adapter class
│       │   └── adapters/
│       │       ├── __init__.py
│       │       ├── mittelalterfeste.py
│       │       ├── spectaculum.py
│       │       ├── schwerttanz.py
│       │       ├── ritterschaft.py
│       │       └── …               # one file per source site
│       ├── geocoding/
│       │   ├── __init__.py
│       │   ├── nominatim.py         # NominatimGeocoder with SQLite cache
│       │   └── haversine.py         # distance_km(lat1, lon1, lat2, lon2)
│       ├── api/
│       │   ├── __init__.py
│       │   ├── markets.py           # GET /api/markets, POST /api/markets/{id}/hide
│       │   ├── sources.py           # GET /api/sources
│       │   ├── crawl.py             # GET /api/crawl/status, POST /api/crawl/trigger
│       │   └── settings.py          # GET/PUT /api/settings
│       └── frontend/
│           ├── templates/
│           │   ├── base.html
│           │   └── index.html
│           └── static/
│               ├── css/
│               │   ├── ritterradar.css
│               │   └── medieval-theme.css
│               ├── js/
│               │   ├── map.js
│               │   ├── filters.js
│               │   ├── detail-panel.js
│               │   └── crawler-status.js
│               └── img/
│                   └── (marker icons, textures)
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_geocoding.py
│   ├── test_haversine.py
│   ├── crawler/
│   │   ├── test_queue.py
│   │   ├── test_worker.py
│   │   ├── test_http_client.py
│   │   └── adapters/
│   │       └── test_adapters.py    # fixture-based adapter tests with mocked HTML
│   └── api/
│       ├── test_markets.py
│       ├── test_crawl.py
│       └── test_settings.py
├── docs/
│   ├── source/                     # Sphinx source
│   │   ├── conf.py
│   │   ├── index.rst
│   │   ├── architecture.rst
│   │   └── adapter-guide.rst
│   ├── architecture.md             # C4 diagrams (Mermaid or PlantUML)
│   └── adapter-guide.md
├── config/
│   └── sources.yaml                # source list (editable without code change)
├── documents/
│   ├── 00_VISION.md
│   └── 01_plan.md                  # this file
├── alembic/
│   ├── env.py
│   └── versions/
├── pyproject.toml                  # version, deps, tool config (single source of truth)
├── justfile                        # dev commands
├── .gitignore
├── .env.example
├── LICENSE                         # GPLv3
├── README.md
└── CHANGELOG.md
```

---

## 5. Data Model

### 5.1 Market

```
Market
├── id: int (PK, autoincrement)
├── name: str
├── market_type: str            # "medieval", "renaissance", "fantasy", "viking", "christmas"
├── start_date: date
├── end_date: date
├── address: str | None
├── city: str | None
├── postal_code: str | None
├── country: str = "DE"
├── latitude: float | None
├── longitude: float | None
├── geocode_uncertain: bool = False
├── program_text: str | None
├── original_text: str          # raw scraped text
├── source_url: str
├── source_name: str
├── hidden: bool = False        # user-hidden
├── confidence_score: float     # 0.0–1.0
├── created_at: datetime
└── updated_at: datetime
```

Uniqueness constraint on `(name, start_date, postal_code, source_url)` for deduplication.

### 5.2 Source

```
Source
├── id: int (PK)
├── name: str
├── base_url: str
├── adapter_name: str
├── enabled: bool = True
├── last_crawled_at: datetime | None
├── last_success_at: datetime | None
├── last_error: str | None
└── crawl_interval_hours: int = 24
```

### 5.3 CrawlJob

```
CrawlJob
├── id: int (PK)
├── source_id: int (FK → Source)
├── status: str  # "pending" | "running" | "completed" | "failed" | "skipped"
├── started_at: datetime | None
├── finished_at: datetime | None
├── events_discovered: int = 0
├── events_inserted: int = 0
├── events_updated: int = 0
└── error_message: str | None
```

### 5.4 UserSettings

Single-row table (id=1, always upserted).

```
UserSettings
├── id: int = 1
├── home_latitude: float | None
├── home_longitude: float | None
├── home_label: str | None       # display label for the home pin
├── default_radius_km: float = 100.0
├── default_month_offset_start: int = 0   # 0 = current month
└── default_month_offset_end: int = 12
```

### 5.5 GeocodingCache

```
GeocodingCache
├── id: int (PK)
├── query: str (unique)
├── latitude: float
├── longitude: float
├── display_name: str
├── uncertain: bool
└── cached_at: datetime
```

---

## 6. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serve `index.html` |
| `GET` | `/api/markets` | List markets; params: `date_from`, `date_to`, `lat`, `lon`, `radius_km`, `include_hidden` |
| `POST` | `/api/markets/{id}/hide` | Toggle hidden flag |
| `GET` | `/api/sources` | List all sources with their status |
| `GET` | `/api/crawl/jobs` | List recent CrawlJob records |
| `GET` | `/api/crawl/status` | Current queue state (pending, running, done counts) |
| `POST` | `/api/crawl/trigger` | Enqueue all enabled sources now |
| `GET` | `/api/settings` | Return UserSettings |
| `PUT` | `/api/settings` | Update UserSettings (including home location) |
| `GET` | `/api/geocode` | Geocode a query string (used by frontend to set home) |
| `GET` | `/health` | Simple liveness endpoint |

---

## 7. Crawler Architecture

### 7.1 AbstractCrawlerAdapter (base class)

```python
class AbstractCrawlerAdapter(ABC):
    SOURCE_NAME: str
    BASE_URL: str

    @abstractmethod
    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        """Scrape the source and return raw parsed market records."""
        ...
```

`MarketData` is a dataclass / Pydantic model carrying the raw extracted fields before they are geocoded and stored.

### 7.2 PoliteHttpClient

Wraps `httpx.AsyncClient` with:
- User-agent: `RitterRadar/0.x (+https://github.com/mpetrick/RitterRadar)`
- Random delay `[0.0, 2.0]` s between requests
- Exponential backoff on 429/5xx: base 2 s, max 60 s, 3 retries
- Per-domain rate limit token bucket
- Timeout: 30 s

### 7.3 CrawlQueue

`asyncio.Queue` of `CrawlJob` objects. The queue manager:

1. On startup: enqueue all enabled sources.
2. Dispatches jobs to `N_WORKERS` (default 3) parallel `CrawlWorker` coroutines.
3. Updates job status in DB atomically.
4. On failure: marks job `failed`, logs error, continues processing remaining queue.

### 7.4 CrawlWorker

Each worker:
1. Pulls a job from the queue.
2. Instantiates the correct adapter via `registry.py`.
3. Calls `adapter.crawl(client)`.
4. For each returned `MarketData`:
   a. Geocode address (with cache).
   b. Check duplicate (name + date + postal code + source_url).
   c. Insert or update Market record.
5. Updates CrawlJob with counts.
6. Catches *all* exceptions — marks job `failed`, never propagates.

### 7.5 Source Configuration (`config/sources.yaml`)

```yaml
sources:
  - name: "Mittelalterfeste.de"
    url: "https://www.mittelalterfeste.de"
    adapter: "mittelalterfeste"
    enabled: true
    crawl_interval_hours: 24

  - name: "Schwerttanz Marktkalender"
    url: "https://www.schwerttanz.de/marktkalender"
    adapter: "schwerttanz"
    enabled: true
    crawl_interval_hours: 24
```

Adding a new source = edit this file + write/select an adapter + restart app.

---

## 8. Frontend Design

### 8.1 Visual Theme

Medieval aesthetic for 2026:

- **Background:** deep parchment `#F2E8C9` with subtle texture overlay
- **Sidebar / panels:** dark wood `#2C1A0E` with `#4A2E1A` borders
- **Accent:** aged gold `#C5A028`, burgundy `#6B1A1A`
- **Text on dark:** warm off-white `#F0E6D0`
- **Typography:** serif heading font (e.g. IM Fell English via Google Fonts) + readable sans for body
- **UI motifs:** shield / banner icons for buttons; wax-seal close buttons; rope/chain dividers

### 8.2 Map

- Leaflet 1.9.x with OpenStreetMap tiles (CartoDB Voyager style or OpenTopoMap for a warmer feel)
- Custom marker icon: SVG shield shape, color-coded by `market_type`:
  - medieval → deep red
  - renaissance → royal blue
  - viking → slate grey
  - fantasy → forest green
  - christmas → deep crimson + silver
- Uncertain geocode: same icon + orange `!` badge
- Markers are semi-transparent (opacity 0.75) until hovered

### 8.3 Interaction Flow

**Hover:** Leaflet tooltip — market name + date range (single line).

**Click:** Side detail panel slides in from the right:
- Full market name (large)
- Type badge
- Date range
- Address (with link to OpenStreetMap search)
- Program details (collapsible if long)
- Original scraped text (collapsible)
- Source link (external)
- Hide / Unhide toggle

### 8.4 Filter Controls (left sidebar)

- **Month range slider:** dual-handle range, min = current month, max = current month + 12
- **Distance radius:** single-handle slider, 10–500 km, disabled if no home set
- **Home location field:** text input (postal code / city / lat,lon); "Set on map" button
- **Market type checkboxes:** medieval, renaissance, viking, fantasy, christmas

### 8.5 Crawler Progress Panel (bottom strip or collapsible drawer)

- Live counts: pending / running / completed / failed jobs
- Per-source rows showing last crawl time, status icon, event count
- "Trigger re-crawl" button
- Expandable error log per failed job

### 8.6 Auto-Refresh

Polling every 5 s via `fetch('/api/markets?...')` with current filter state. Only re-renders markers that changed (add/remove by id diff). Also polls `/api/crawl/status` every 3 s to update the progress panel.

---

## 9. Geocoding

- **Provider:** Nominatim (OSM) via `geopy.geocoders.Nominatim`
- **Cache:** `GeocodingCache` table prevents repeated API calls for the same query string
- **Rate limit:** 1 request/s max (Nominatim ToS)
- **Uncertainty:** if `importance < 0.5` or result type is vague (e.g. country-level), set `geocode_uncertain = True`
- **User-agent:** `RitterRadar/0.x mail@example.com`
- **Fallback:** If geocoding fails entirely, store market with `latitude = None`, `longitude = None`; market still stored but not shown on map (shown in a "no location" list in the debug panel)

---

## 10. Distance Calculation

Haversine formula, pure Python, no external dependency:

```
distance_km = 2R × arcsin(√(sin²(Δφ/2) + cos φ₁ cos φ₂ sin²(Δλ/2)))
```

where R = 6371 km.

Filtering is done in the API layer: after fetching markets from DB (by date range), compute distance for each and exclude those beyond `radius_km`. This is fine at local SQLite scale (expected < 10 000 markets).

---

## 11. Known Target Sources

The following sites are candidates for crawl adapters. Each requires its own adapter; the list will expand:

| Site | Notes |
|---|---|
| mittelalterfeste.de | Large German event calendar |
| schwerttanz.de | Market calendar section |
| spectaculum.de | Professional medieval event company, own schedule |
| ritterschaft.de | Deutsche Ritterschaft event listing |
| mittelalterspektakel.de | Community calendar |
| burg-und-ritter.de | Castle events calendar |
| mittelalterwelt.de | Event directory |
| marktzauber.de | Market organizer with own calendar |

Each adapter must handle:
- Pagination (if present)
- Date parsing (German locale: "12. bis 14. Juli 2026", "12.07.2026", etc.)
- Address extraction (ideally postal code + city)
- Optional program text
- Raw original text capture

---

## 12. Implementation Phases

### Phase 0 — Project Skeleton (version 0.0.1 → ~0.0.5)

- [ ] `pyproject.toml` with all pinned dependencies, version `0.0.1`
- [ ] `justfile` with: `just dev`, `just test`, `just lint`, `just fmt`, `just docs`, `just migrate`
- [ ] `.gitignore` (Python, SQLite, .env, `__pycache__`, `.venv`, `dist/`, `docs/_build/`)
- [ ] `LICENSE` (GPLv3)
- [ ] `CHANGELOG.md` (Keep a Changelog format)
- [ ] `.env.example`
- [ ] ruff config in `pyproject.toml`
- [ ] mypy config in `pyproject.toml` (strict mode)
- [ ] pytest config with coverage threshold = 90
- [ ] Sphinx `docs/source/conf.py`
- [ ] Alembic init
- [ ] `src/ritterradar/__init__.py` with `__version__ = "0.0.1"`

### Phase 1 — Data Layer (version ~0.0.6 → ~0.0.15)

- [ ] SQLModel models: Market, Source, CrawlJob, UserSettings, GeocodingCache
- [ ] Alembic initial migration
- [ ] `database/engine.py` — engine creation, `create_tables()`
- [ ] `database/session.py` — `get_session()` FastAPI dependency
- [ ] Unit tests for all models (field defaults, constraints, repr)
- [ ] Haversine utility + tests (known-distance pairs)

### Phase 2 — Geocoding Service (version ~0.0.16 → ~0.0.20)

- [ ] `geocoding/nominatim.py` — async geocoder with cache lookup/write
- [ ] `geocoding/haversine.py`
- [ ] Tests with mocked Nominatim responses
- [ ] Cache hit/miss test

### Phase 3 — Crawler Infrastructure (version ~0.0.21 → ~0.0.35)

- [ ] `crawler/base_adapter.py` — ABC + `MarketData` dataclass
- [ ] `crawler/http_client.py` — PoliteHttpClient (delay, backoff, UA)
- [ ] `crawler/queue.py` — CrawlQueue with asyncio.Queue
- [ ] `crawler/worker.py` — CrawlWorker (failure isolation, DB write, geocode)
- [ ] `crawler/registry.py` — adapter registry
- [ ] Unit tests for queue state transitions
- [ ] Unit tests for worker (mocked adapter, DB, geocoder)
- [ ] Integration test: full crawl cycle with stub adapter

### Phase 4 — Crawler Adapters (version ~0.0.36 → ~0.0.60)

Per adapter: implement, test with saved HTML fixture, verify extracted fields.

- [ ] `adapters/mittelalterfeste.py`
- [ ] `adapters/schwerttanz.py`
- [ ] `adapters/spectaculum.py`
- [ ] `adapters/ritterschaft.py`
- [ ] `adapters/mittelalterspektakel.py`
- [ ] At least 3 more adapters for identified sources
- [ ] Adapter integration tests (HTML fixtures, no network)

### Phase 5 — FastAPI Application (version ~0.0.61 → ~0.0.75)

- [ ] `main.py` — app + lifespan (startup: load sources, seed DB, start crawler queue)
- [ ] `config.py` — AppSettings (YAML source path, worker count, DB path, etc.)
- [ ] `api/markets.py` — filtered market listing + hide toggle
- [ ] `api/sources.py` — source listing
- [ ] `api/crawl.py` — status + trigger
- [ ] `api/settings.py` — user settings CRUD + geocode endpoint
- [ ] Static file serving for frontend
- [ ] Full pytest-asyncio API tests (TestClient)
- [ ] Error handling middleware (never expose stack traces to client)

### Phase 6 — Frontend (version ~0.0.76 → ~0.0.100)

- [ ] `base.html` — GPLv3 comment, meta, CSS/JS includes
- [ ] `index.html` — layout: map full-screen, left sidebar, bottom panel, right detail panel
- [ ] `medieval-theme.css` — color palette, fonts, textures, motifs
- [ ] `ritterradar.css` — layout, responsive adjustments
- [ ] `map.js` — Leaflet init, custom markers, hover tooltip, click handler
- [ ] `filters.js` — month slider, distance slider, type checkboxes; builds query params
- [ ] `detail-panel.js` — renders click detail; hide/unhide button
- [ ] `crawler-status.js` — polls /api/crawl/status; updates progress strip
- [ ] Auto-refresh polling for market data
- [ ] Home location widget (text input + "set on map" pin mode)
- [ ] Uncertain geocode visual indicator

### Phase 7 — Documentation (version ~0.0.101 → ~0.0.110)

- [ ] `README.md` — purpose, installation, configuration, running, adapter development, license
- [ ] `docs/architecture.md` — C4 Context + Container + Component diagrams (Mermaid)
- [ ] `docs/adapter-guide.md` — step-by-step with annotated example adapter
- [ ] Sphinx autodoc for all public classes and functions
- [ ] `CHANGELOG.md` — entries for each phase

### Phase 8 — Quality Loop (ongoing)

- [ ] Run coverage report; identify gaps; add missing tests until ≥ 90 %
- [ ] Run `ruff check --select ALL`; fix all findings
- [ ] Run mypy strict; fix all type errors
- [ ] Review cycle pass: rate findings high / medium / low
  - High → fix immediately in same session
  - Medium → file in next loop
  - Low → track in CHANGELOG / TODO
- [ ] Performance: profile crawler and API under 5000 market records
- [ ] Security: no shell injection in geocoding; no SSRF in crawler (allowlist or warn); sanitise any HTML from sources before storing

---

## 13. Configuration Reference (`.env.example`)

```dotenv
# Path to sources YAML (default: config/sources.yaml)
RITTERRADAR_SOURCES_FILE=config/sources.yaml

# SQLite database path
RITTERRADAR_DB_PATH=data/ritterradar.db

# Number of parallel crawler workers
RITTERRADAR_WORKERS=3

# Nominatim user-agent email
RITTERRADAR_GEOCODER_EMAIL=your@email.com

# Web server host/port
RITTERRADAR_HOST=127.0.0.1
RITTERRADAR_PORT=8000

# Log level (DEBUG, INFO, WARNING, ERROR)
RITTERRADAR_LOG_LEVEL=INFO
```

---

## 14. Development Commands (`justfile`)

```
just dev       → uvicorn ritterradar.main:app --reload
just test      → pytest --cov=ritterradar --cov-fail-under=90
just lint      → ruff check src tests
just fmt       → ruff format src tests
just types     → mypy src
just docs      → sphinx-build docs/source docs/_build/html
just migrate   → alembic upgrade head
just makemig   → alembic revision --autogenerate -m "…"
just ci        → just lint && just types && just test
```

---

## 15. Review Cycle Template

Each review pass produces a findings table:

| ID | Severity | Component | Finding | Status |
|---|---|---|---|---|
| R1-001 | HIGH | crawler/worker.py | DB session not closed on exception path | Fixed |
| R1-002 | MEDIUM | api/markets.py | No pagination on market list endpoint | Planned |
| R1-003 | LOW | frontend | No keyboard navigation on filter sliders | Backlog |

Review passes: after Phase 3 (crawler), after Phase 5 (API), after Phase 6 (frontend), before any major release.

---

## 16. Versioning Strategy

- Single source of truth: `version` field in `pyproject.toml`
- `src/ritterradar/__init__.py` reads it via `importlib.metadata.version("ritterradar")`
- Start: `0.0.0`
- Increment: patch (`0.0.X`) per commit during development
- Minor bump (`0.X.0`) at completion of a major phase
- Major bump (`X.0.0`) at first stable, fully-functional release
- Versions recorded in `CHANGELOG.md`

---

## 17. Open Questions / Deferred Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Use SSE instead of polling for real-time updates? | Start with polling; switch if UX feels laggy |
| 2 | Playwright for JS-heavy sites? | Add as optional dependency; use only if a specific adapter needs it |
| 3 | "Set home on map" click interaction | Deferred to Phase 6; text input sufficient for Phase 5 |
| 4 | Export / share market list (CSV, iCal)? | Not in scope for v0; design API to make it easy later |
| 5 | Recurring crawl schedule (daily) while app runs? | Phase 5: use `asyncio` background task that re-enqueues sources every N hours |

---

## 18. Success Criteria for v0.1.0

A working release is reached when:

1. App starts with `just dev` and opens in browser without errors.
2. At least 5 crawler adapters are functional and discover real events.
3. Events appear on the Leaflet map within 60 s of first startup.
4. Month range and distance filters visibly change the shown markers.
5. Clicking a marker shows correct detail panel content.
6. Crawler progress panel reflects live queue state.
7. A broken adapter does not crash or degrade other adapters.
8. `just ci` passes (lint + types + tests ≥ 90 % coverage).
9. Sphinx docs build without warnings.
10. README documents the full install-to-run workflow.
