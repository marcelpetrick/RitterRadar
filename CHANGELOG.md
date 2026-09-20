# Changelog

All notable changes to RitterRadar are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [0.0.88] — 2026-09-20
### Fixed
- Month filters include events spanning month boundaries and reject reversed
  ranges. Clearing all event categories now clears the map and preview.
- Exclude cancelled, out-of-scope, and invalid-date records from results;
  general museum programmes no longer default to medieval events.
- Parse Retro MPS city labels, Dutch postcode suffixes, Swiss location labels,
  and places without postcodes correctly; preserve foreign REST-feed countries.
- Re-crawls repair location fields and revalidate coordinates after a location
  changes. Repeated failed geocoding requests are reused within a crawl.
- Corrected iCal dates update the event, and old overlapping date records are
  suppressed without deleting history or merging separate recurring dates.
- Duplicate detection checks titles and countries, retains distinct events
  sharing a postcode, and prefers records with reliable coordinates.

### Tests
- Add September data regression fixtures and an isolated offline browser test
  to CI, plus a read-only month-audit command for live data checks.

## [0.0.87] — 2026-09-19
### Changed
- Updated Uvicorn from 0.52.4 to 0.53.0, SQLAlchemy from 2.0.52 to 2.0.54,
  and Ruff from 0.16.7 to 0.16.8, retaining exact version pins.
- Updated Docker workflow actions: setup-qemu-action from v4.3.0 to v4.4.0,
  setup-buildx-action from v4.3.0 to v4.4.1, and build-push-action from v7.3.0
  to v7.4.0, retaining full commit SHA pins.

## [0.0.86] — 2026-09-14
### Fixed
- Pfalzis Marktkalendarium names spanning several lines were glued together
  ("Mittelaltermeile<br/>Altstadtfest" became "MittelaltermeileAltstadtfest");
  the lines are now joined with a space. Adapter version 0.2.0.

## [0.0.85] — 2026-09-14
### Fixed
- A re-crawl whose event name differs only in whitespace from the stored one
  (same start date and source URL) now updates that record and adopts the
  corrected name instead of inserting a duplicate.

## [0.0.84] — 2026-09-14
### Fixed
- Re-crawls now correct the country of existing events: a record still on the
  default `DE` takes the country a source reports (e.g. the Swiss and Austrian
  events from mittelalterkalender.info), while a known country is never
  overwritten by a source's default.

## [0.0.83] — 2026-09-14
### Documentation
- Sources documentation describes the country comments on
  mittelalterkalender.info and the fyndling.de location cleanup.

## [0.0.82] — 2026-09-14
### Fixed
- Compound place names such as "Mechernich-Satzvey", "Schwendi - Orsenhausen"
  or "Bornhagen OT Rimbach" are geocoded via their parts (district first) when
  the full name gives no certain result. Cache keys move to `market-v4` so the
  affected entries are looked up once again.

## [0.0.81] — 2026-09-14
### Fixed
- Fyndling.de locations: Swiss canton suffixes ("Zofingen AG") are removed,
  legacy country markers ("Campo di Trens (I)") set the country, and
  "D.87700 Memmingen" / "Drage 21423" postcodes are recognised.

## [0.0.80] — 2026-09-14
### Fixed
- Mittelalterkalender.info stored every event as German, so ~100 Austrian,
  Swiss, Dutch and other events were geocoded within Germany and failed. The
  country is now read from the commented-out country cell of each row.

## [0.0.79] — 2026-09-13
### Documentation
- README documents the 90% coverage gate and that the test suite runs fully
  offline.

## [0.0.78] — 2026-09-13
### Fixed
- Nearly every geocoded market was shown as "Ungefährer Ort". Town results
  from Nominatim carry no postcode and were rejected, and the postcode
  centroids used instead never reached an importance of 0.4. Results that
  name the requested city are now accepted and treated as certain; country,
  state and county results stay uncertain.
- Constrained cache entries move to `market-v3`: existing entries that name
  the requested city are promoted without a network request, the rest are
  looked up once again, keeping the previous coordinates if nothing better
  is found.

## [0.0.77] — 2026-09-13
### Changed
- Coverage gate raised from 50% to the 90% goal of the project vision; the
  suite now covers 98% of the code (146 tests, all offline).

## [0.0.76] — 2026-09-13
### Tests
- Fixture tests for the disabled heuristic adapters (mittelalterfeste,
  mittelaltermarkt.com, schwerttanz, ritterschaft) and `generic_table`.

## [0.0.75] — 2026-09-13
### Tests
- Fixture tests for the Taterman.at iCal, Mittelaltermarkt.online REST API,
  Vehi Mercatus, Marktkalendarium, Trollfelsen and Spectaculum adapters.

## [0.0.74] — 2026-09-13
### Tests
- Index page, static cache headers, crawl API without a queue, geocode
  endpoint, `run()` entry point and database engine creation.

## [0.0.73] — 2026-09-13
### Tests
- Geocoder cache round trip, cached and constrained lookups, rate limiting,
  error handling and coarse-result uncertainty.

## [0.0.72] — 2026-09-13
### Tests
- Crawl worker job lifecycle (skipped, failed, completed, trusted-coordinate
  reuse, record enrichment) and queue worker start/stop and source seeding.

## [0.0.71] — 2026-09-13
### Tests
- Polite HTTP client retries, backoff and domain-drift guard; the offline
  fake client now supports bytes, JSON, status codes and raised errors.

## [0.0.70] — 2026-09-13
### Documentation
- Sources documentation: review of all sources on 2026-09-13 with event counts,
  sections for Fyndling.de and Mittelaltermarkt-info.de, re-checked disabled
  sources and a table of evaluated but rejected candidate sites.
- README and architecture overview list 9 active adapters.

## [0.0.69] — 2026-09-13
### Added
- `fyndling` adapter: ~1,300 DE/AT/CH/LI/LU events from the fyndling.de market
  list (`/maerkte.html`).
- `mittelaltermarkt_info` adapter: ~320 events from the curated DE, AT and CH
  lists on mittelaltermarkt-info.de, including unlinked entries and all observed
  date notations.
- Offline fixture tests for the new adapters; map filter tooltips name the new
  sources.

## [0.0.68] — 2026-09-13
### Fixed
- Mittelalterkalender.info returned no events for next year because the site
  renamed its yearly list page. The adapter (0.2.0) now discovers the list pages
  from homepage links and falls back to both known URL patterns.

## [0.0.67] — 2026-09-13
### Documentation
- README: Docker section (published image tags, `docker run`, Compose, local
  build, image details, publishing pipeline, release procedure), Docker badge,
  fixed clone URL.
- Architecture: container deployment section with pipeline diagram, design
  decision and updated directory layout.

## [0.0.66] — 2026-09-13
### Added
- Docker workflow: builds the image, smoke-tests `/health`, `/`, static files
  and the crawl API, then publishes a multi-arch (amd64/arm64) image with SBOM
  and build provenance to `ghcr.io/marcelpetrick/ritterradar`
  (`:edge` from master, `:X.Y.Z`/`:X.Y`/`:latest` from `vX.Y.Z` tags).
### Changed
- CI now runs the quality gate on Python 3.12, 3.13 and 3.14.
- Release workflow attaches the wheel and sdist to the GitHub release; build
  tools pinned (build 1.6.1, twine 7.0.0).
- All GitHub Actions updated to their latest releases and pinned by commit SHA.

## [0.0.65] — 2026-09-13
### Added
- Two-stage `Dockerfile` on `python:3.14.7-slim-trixie`: non-root user,
  `/app/data` volume, healthcheck against `/health`.
- Allow-list `.dockerignore`, `compose.yaml`, `just docker-build` / `docker-run`.

## [0.0.64] — 2026-09-13
### Changed
- Package metadata uses an SPDX license expression (`GPL-3.0-or-later`) instead
  of the license table and classifier deprecated by setuptools 84.

## [0.0.63] — 2026-09-13
### Changed
- Updated 13 dependencies to latest stable versions: fastapi 0.141.1,
  uvicorn 0.52.4, sqlmodel 0.0.42, sqlalchemy 2.0.52, alembic 1.20.0,
  pydantic-settings 2.15.0, lxml 6.1.3, geopy 2.5.0, anyio 4.15.1,
  icalendar 7.3.0, ruff 0.16.7, mypy 2.3.1, types-PyYAML 6.0.12.20260906.
- Pinned build-system requirements exactly (setuptools 84.0.0, wheel 0.48.0).

## [0.0.62] — 2026-08-25
### Fixed
- Corrected badge URLs in README (owner was mpetrick, should be marcelpetrick).

## [0.0.61] — 2026-08-25
### Added
- CI pipeline (lint, type check, test across Python 3.12–3.14).
- PyPI release pipeline (build sdist/wheel, publish via trusted publisher).
- MANIFEST.in for complete source distributions.
### Changed
- Updated 11 dependencies to latest stable versions (fastapi, uvicorn, sqlalchemy,
  alembic, pydantic-settings, lxml, geopy, anyio, ruff, mypy, types-PyYAML).
- Reformat for ruff 0.16.4.
- Lower coverage threshold to 50% to match actual coverage.

## [0.0.54] — 2026-07-10
### Fixed
- Startup now marks crawl jobs orphaned by an earlier application shutdown as
  skipped before enqueuing the new run, keeping status counters accurate.

## [0.0.53] — 2026-07-10
### Changed
- Existing geocoder cache entries are promoted without a network request when
  their display name confirms the expected postal code and country.

## [0.0.52] — 2026-07-10
### Fixed
- Crawls reuse existing trusted coordinates so only missing or uncertain
  locations consume new geocoder requests.

## [0.0.51] — 2026-07-10
### Fixed
- Market geocoding now constrains Nominatim lookups by country, validates
  returned postal codes, and falls back to a postal centroid when locality
  names are ambiguous.
- Constrained market lookups use isolated cache keys, and subsequent crawls
  can replace previously uncertain coordinates with revalidated results.

## [0.0.50] — 2026-07-10
### Fixed
- Spatial market responses now exclude events without coordinates, ensuring
  every map, preview, and copied-list result has a calculated distance.
- Partial spatial API parameters are rejected instead of silently returning
  unfiltered events.

## [0.0.49] — 2026-07-10
### Documentation
- Documented the filtered upcoming-events preview and its copyable plain-text
  list in the feature overview and map usage guide.
- Clarified the default HTTP port and the commonly configured local port
  `13370` used by the startup scripts through `.env`.

## [0.0.48] — 2026-07-10
### Fixed
- Production startup now normalizes configured Uvicorn log levels to lowercase,
  allowing values such as `RITTERRADAR_LOG_LEVEL=INFO`.

## [0.0.47] — 2026-07-09
### Added
- Startup log now reports the running package version.

## [0.0.46] — 2026-07-09
### Changed
- On-the-fly duplicate suppression now also catches safe title/location
  variants using normalized titles, normalized places, and very close
  coordinates for identical date ranges.

## [0.0.45] — 2026-07-09
### Added
- On-the-fly duplicate suppression for filtered map/list results when postal
  code and date range match; the entry with the longer event title is kept.

## [0.0.44] — 2026-07-09
### Fixed
- Startup map loading now waits for saved filter settings before requesting
  markets, preventing an initial unfiltered result set from rendering.
- Overlapping market refreshes now ignore stale responses so crawler-triggered
  updates cannot overwrite the current filtered view with older data.

## [0.0.43] — 2026-07-09
### Changed
- Upcoming-events preview now renders all filtered events instead of capping the
  visible list.

## [0.0.42] — 2026-07-09
### Fixed
- Upcoming-events preview now stays in sync with the map results even when the
  filtered market payload is loaded before the preview module is ready.

## [0.0.41] — 2026-07-09
### Added
- Collapsible bottom preview for upcoming markets based on the current map filters,
  sorted chronologically and copyable as a plain-text list.

## [0.0.40] — 2026-07-09
### Changed
- Dependency pins updated for FastAPI, Uvicorn, and mypy.
- Compatibility fixes for the updated lint/type-checking toolchain.

## [0.0.39] — 2026-06-26
### Docs
- README architecture section: ASCII box diagram replaced with styled Mermaid flowchart
  (dark medieval colour palette matching the app theme; full data-flow including
  three-phase upsert, Nominatim cache path, and all three adapter formats)

## [0.0.38] — 2026-06-26
### Docs
- **README**: intro rewritten in medieval English; features table updated (multi-format parsing,
  pre-geocoded fast path, adapter versioning, tooltips, version in header, 0–1024 km slider)
- **documents/01_plan.md**: all Phase 0–7 checklist items marked complete with actual version
  numbers; Phase 8 open items accurately reflect current state (lint clean, coverage 80%,
  adapter fixture tests missing)
- **documents/02_issues.md**: replaced raw uvicorn log dump with structured R1/R2 review
  findings tables (severity rated; fixed items linked to fix versions; open backlog listed)

## [0.0.37] — 2026-06-26
### Changed
- Header tagline now shows live version number (v{{ version }} via Jinja2 context)
- FastAPI app version sourced from `importlib.metadata` instead of hardcoded string
- Legend entry "Unsicherer Ort !" renamed to "Ungefährer Ort" (cleaner German; ! was redundant since the map marker already carries the indicator)

## [0.0.36] — 2026-06-26
### Changed
- **Umkreis slider** extended from 10–500 km to 0–1024 km (step 8 km)
- **Suchen button** moved below the Heimatort text field (was side-by-side)
- **Tooltips** added to all Markttyp checkboxes and Legende entries — each item
  now shows its meaning and which crawl sources contribute that category on hover
- **Leaflet attribution** restyled to match the medieval theme (dark background,
  gold link, 0.6 rem); "Leaflet" branding prefix removed — only the mandatory
  OpenStreetMap credit remains visible in the map corner

## [0.0.35] — 2026-06-26
### Added
- **New adapter: trollfelsen.de** (v0.1.0, verified 2026-06-26)
  - Vendor tour schedule: ~21 confirmed events in 2026
  - Each card links directly to the event's own website (high-quality source_url)
  - Skips cards flagged "Teilnahme noch nicht bestätigt" (unconfirmed)
  - Location format "DE - 06217 Merseburg" → country + PLZ + city
  - Coverage: Germany primarily; adapts to AT/CH cards when present

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
