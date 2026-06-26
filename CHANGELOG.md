# Changelog

All notable changes to RitterRadar are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [0.0.34] — 2026-06-26
### Added
- **New adapter: taterman.at** (v0.1.0, verified 2026-06-26)
  - Austrian medieval-market info magazine; ~26 events/year for 2026
  - iCal feed at `/termin/categories/markt/?ical=1` (Markt category filtered)
  - `icalendar==7.2.0` dependency added for RFC 5545 parsing
  - Non-standard `DTSTART;TZID=...;VALUE=DATE` handled via property params;
    DTEND is exclusive for all-day events (subtract 1 day to get last day)
  - LOCATION parsed for 4-digit Austrian PLZ; province names filtered as non-cities
  - Market-type keywords: Advent/Weihnacht → christmas, Wikinger → viking, etc.
### Fixed
- **88 pre-existing ruff violations eliminated** (codebase is now lint-clean):
  - E402: `__version__` / `_VERIFIED_DATE` moved after imports in all adapters
  - F401: unused imports removed (urljoin, datetime.datetime, datetime.timezone)
  - E501: 6 lines shortened across api/markets, crawler, adapters
  - B007: renamed unused loop variable `i` → `_i` in generic_table
  - UP017: `datetime.UTC` alias (replaces `timezone.utc`) throughout

## [0.0.32] — 2026-06-26
### Fixed
- **Cross-source duplicate markets eliminated** — three-phase upsert in `worker.py`:
  1. Match by `(name, start_date, postal_code)` — prevents the same real event from being
     inserted from 5 different sources (e.g. "Glanz der Ritterzeit" was stored 3×)
  2. Match by `(name, start_date, city)` — catches sources that omit PLZ (Spectaculum.de)
  3. Fallback to `(name, start_date, source_url)` — original same-source re-crawl logic
- On dupe match: enrich existing record (fill missing city/PLZ/geocoords) instead of skipping
- Retroactively cleaned 114 duplicate rows (1971 → 1859 markets)

## [0.0.31] — 2026-06-26
### Docs
- `documents/03_sources.md`: added source entries for marktkalendarium.de and mittelaltermarkt.online
- Crawler architecture diagram updated: pre-geocoded lat/lon fast path shown
- Adapter versioning guide added (SemVer semantics for `__version__` / `_VERIFIED_DATE`)

## [0.0.30] — 2026-06-26
### Added
- **New adapter: mittelaltermarkt.online** (v0.1.0, verified 2026-06-25)
  - Uses The Events Calendar REST API (`/wp-json/tribe/events/v1/events`) — no HTML scraping
  - 531 events (2026-2027): 491 DE + 29 AT + 9 CH
  - 528/531 events carry pre-geocoded `venue.geo_lat` / `venue.geo_lng` → Nominatim skipped
  - Category-slug → market_type mapping (christmas/viking/renaissance/fantasy/medieval)
  - HTML entity unescape (`&#8211;` → `–`)
- `MarketData` dataclass: optional `latitude`/`longitude` fields for pre-geocoded data
- `CrawlWorker`: short-circuits Nominatim when `mdata.latitude` is already set

## [0.0.29] — 2026-06-26
### Added
- **New adapter: marktkalendarium.de** (Pfalzis Marktkalendarium, v0.1.0, verified 2026-06-25)
  - 334 events for 2026, 8 for 2027; 311 DE + 10 AT + 11 CH
  - 7-column HTML table; variable-width date format `D.M.YYYY`; country prefix map D-/A-/CH-/L-

## [0.0.28] — 2026-06-26
### Changed
- **Logging**: `force=True` in `basicConfig` so RitterRadar config wins over uvicorn; name column widened to 40 chars; httpx/httpcore/geopy/urllib3 suppressed to WARNING
- **Adapter versioning**: all 3 existing adapters gain `__version__ = "0.1.0"` and `_VERIFIED_DATE = "2026-06-25"`
- **Dependencies**: all runtime and dev dependencies verified at latest stable versions — no changes required
  (fastapi 0.138.1, uvicorn 0.49.0, sqlmodel 0.0.39, httpx 0.28.1, lxml 6.1.1, etc.)

## [0.0.27] — 2026-06-25
### Docs
- `docs/architecture.md` rewritten with 8 Mermaid diagrams (C4 L1–L3, ER diagram, module graph, HTTP client flow, active sources, directory layout)
- Replaces all ASCII art diagrams

## [0.0.19] — 2026-06-25
### Changed
- Version bumped to 0.0.19 (synchronises pyproject.toml with commit count)

## [0.0.18] — 2026-06-25
### Added
- Sphinx documentation (autodoc, napoleon, RTD theme) in `docs/source/`
- C4 architecture document in `docs/architecture.md`
- Adapter development guide (`docs/source/adapter_guide.rst`)

## [0.0.17] — 2026-06-25
### Added
- Comprehensive `README.md` covering installation, configuration, usage,
  crawler management, adapter development, database management, and API reference

## [0.0.16] — 2026-06-25
### Added
- Test suite: 48 tests across conftest, models, date parser, Haversine,
  adapter base, and all API endpoints; uses StaticPool in-memory SQLite
### Fixed
- CrawlJob/Source `DetachedInstanceError` in worker.py — attributes now
  read within the session context before the `with` block exits

## [0.0.15] — 2026-06-25
### Added
- Four ES module JavaScript files: map.js, filters.js, detail-panel.js,
  crawler-status.js

## [0.0.14] — 2026-06-25
### Added
- `ritterradar.css` — full medieval CSS theme with custom properties,
  grid layout, marker styles, slider overrides, Leaflet popup overrides

## [0.0.13] — 2026-06-25
### Added
- Jinja2 HTML templates: `base.html` and `index.html` with full layout
  (header, sidebar, map, detail panel, status bar, jobs panel)

## [0.0.12] — 2026-06-25
### Added
- `main.py` — FastAPI application with lifespan, all routers, static files,
  Jinja2 templates, health endpoint, and `run()` console script entry point

## [0.0.11] — 2026-06-25
### Added
- API routers: markets (list + filter + hide), sources (list), crawl
  (status + trigger), settings (get/put + geocode endpoint)

## [0.0.10] — 2026-06-25
### Added
- Five crawler adapters: mittelalterfeste, spectaculum, schwerttanz,
  ritterschaft, mittelaltermarkt; plus generic_table fallback
- `config/sources.yaml` with all five sources pre-configured

## [0.0.9] — 2026-06-25
### Added
- Crawler infrastructure: AbstractCrawlerAdapter, MarketData, PoliteHttpClient
  (delays + backoff), date_parser (6 German formats), registry (@register),
  CrawlWorker (asyncio Task, failure isolation), CrawlQueue (seed + enqueue)

## [0.0.8] — 2026-06-25
### Added
- Haversine distance formula (`geocoding/haversine.py`)
- Nominatim geocoder with SQLite cache and asyncio rate limiting (`geocoding/nominatim.py`)

## [0.0.7] — 2026-06-25
### Added
- Alembic migration infrastructure (`alembic.ini`, `alembic/env.py`,
  `alembic/script.py.mako`, initial autogenerated migration)
### Fixed
- Build backend changed from `setuptools.backends.legacy:build` to
  `setuptools.build_meta` (unavailable on host Python 3.14)

## [0.0.6] — 2026-06-25
### Added
- Database engine singleton (`database/engine.py`)
- `get_session()` FastAPI dependency (`database/session.py`)

## [0.0.5] — 2026-06-25
### Added
- SQLModel table models: Market, Source, CrawlJob, UserSettings, GeocodingCache

## [0.0.4] — 2026-06-25
### Added
- Package skeleton (`src/ritterradar/`) with `__init__.py` and `config.py`
  (pydantic-settings, `RITTERRADAR_*` env prefix)

## [0.0.3] — 2026-06-25
### Added
- `justfile` with all dev commands
- Shell scripts: install.sh, start.sh, start_dev.sh, reset_db.sh,
  trigger_crawl.sh, crawl_status.sh

## [0.0.2] — 2026-06-25
### Added
- `.gitignore`, `LICENSE` (GPLv3), `CHANGELOG.md`, `.env.example`

## [0.0.1] — 2026-06-25
### Added
- `pyproject.toml` with all pinned dependencies, ruff/mypy/pytest config

## [0.0.0] — 2026-06-25
### Added
- Initial repository structure
- Vision document (`documents/00_VISION.md`)
- Implementation plan (`documents/01_plan.md`)
