# RitterRadar — Review Findings

Format: severity-rated findings from periodic review passes.  
**High** → fixed immediately in the same session.  
**Medium** → scheduled for next loop.  
**Low** → tracked here; addressed when convenient.

---

## Review Pass R1 — 2026-06-25 (post Phase 5/6)

| ID | Severity | Component | Finding | Status |
|---|---|---|---|---|
| R1-001 | HIGH | `crawler/worker.py` | DB session not closed on exception path — `DetachedInstanceError` when reading CrawlJob attributes after session closed | **Fixed** v0.0.16 — attributes read within session context before `with` block exits |
| R1-002 | HIGH | All adapters | `__version__` / `_VERIFIED_DATE` declared before imports → ruff E402 on all subsequent imports (88 violations total) | **Fixed** v0.0.34 — moved to after `logger = logging.getLogger(__name__)` |
| R1-003 | HIGH | `crawler/worker.py` | Cross-source duplicate markets — same event inserted 3× from different sources (1971 rows → 1859 after cleanup) | **Fixed** v0.0.32 — three-phase upsert dedup (PLZ → city → source_url) |
| R1-004 | HIGH | `taterman_at.py` | `_coerce_date` returned `datetime` not `date` — `isinstance(datetime, date)` is True (datetime subclasses date) | **Fixed** v0.0.34 — check for callable `.date()` method first |
| R1-005 | HIGH | `taterman_at.py` | All-day detection failed for non-standard `DTSTART;TZID=...;VALUE=DATE` (RFC 5545 violation by site) — icalendar returns timezone-aware `datetime` instead of `date` | **Fixed** v0.0.34 — detect all-day via `dtstart.params.get("VALUE") == "DATE"` |
| R1-006 | MEDIUM | `api/markets.py` | No pagination on `/api/markets` — returns all matching records at once; at 2000+ markets this may be slow | **Open** — acceptable at SQLite scale; add `limit`/`offset` params if latency grows |
| R1-007 | MEDIUM | Frontend | No "set home on map" click-to-pin interaction — text geocode is the only input method | **Open / Deferred** — text input + Nominatim geocode covers 95% of use cases |
| R1-008 | MEDIUM | `crawler/adapters/` | Adapter integration tests use no HTML fixtures — only API-level tests exist; a site redesign would break adapters silently | **Open** — fixture-based adapter tests planned for next test pass |
| R1-009 | LOW | `api/main.py` | FastAPI `version` field was hardcoded to `"0.0.12"` — stale after every commit | **Fixed** v0.0.37 — reads from `importlib.metadata.version("ritterradar")` |
| R1-010 | LOW | Frontend | Leaflet "Leaflet" branding prefix in attribution bar cluttered the map corner | **Fixed** v0.0.36 — `attributionControl.setPrefix('')`; OSM credit retained |
| R1-011 | LOW | `vehi_mercatus.py` | `href` ternary was over 100 chars and used unused `datetime` import | **Fixed** v0.0.34 — E501 unwrapped, F401 removed |
| R1-012 | LOW | All adapters | `datetime.timezone.utc` used in several places instead of Python 3.11+ `datetime.UTC` alias | **Fixed** v0.0.34 — UP017 applied throughout |

---

## Review Pass R2 — 2026-06-26 (post Phase 7)

| ID | Severity | Component | Finding | Status |
|---|---|---|---|---|
| R2-001 | MEDIUM | `pyproject.toml` | Coverage threshold set to 80%; vision document specifies 90% goal | **Open** — adapter fixture tests needed to close the gap |
| R2-002 | LOW | `documents/02_issues.md` | File contained raw uvicorn log output instead of structured findings | **Fixed** 2026-06-26 — replaced with this document |
| R2-003 | LOW | Slider UX | Umkreis slider capped at 500 km — unusable for Austria/Switzerland events | **Fixed** v0.0.36 — range extended to 0–1024 km, step 8 |
| R2-004 | LOW | Sidebar UX | "Suchen" button was next to the Heimatort input field (side-by-side); visually displaced | **Fixed** v0.0.36 — button moved below input (`flex-direction: column`) |
| R2-005 | LOW | Legend | "Unsicherer Ort !" label was informal and used a stray exclamation mark | **Fixed** v0.0.37 — renamed to "Ungefährer Ort" |
| R2-006 | LOW | Legend / Markttyp | No explanation of what each category means or which sources contribute to it | **Fixed** v0.0.36 — `title` attribute tooltips added to all legend entries and type checkboxes |
| R2-007 | LOW | Header | No visible version number in the UI — hard to know which build is running | **Fixed** v0.0.37 — tagline shows `· v{version}` via Jinja2 template context |

---

## Open Items (backlog)

| ID | Severity | Component | Finding |
|---|---|---|---|
| R1-006 | MEDIUM | `api/markets.py` | No pagination on `/api/markets` |
| R1-007 | MEDIUM | Frontend | No "set home on map" click-to-pin |
| R1-008 | MEDIUM | `tests/` | Adapter-level HTML fixture tests not written |
| R2-001 | MEDIUM | `pyproject.toml` | Coverage at 80%; goal is 90% |
| — | LOW | `crawler/worker.py` | `original_text` from scraped HTML is stored raw; no HTML sanitisation |
| — | LOW | `crawler/http_client.py` | SSRF guard is domain-drift only; no explicit allowlist |
