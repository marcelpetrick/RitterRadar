# RitterRadar — Architecture (C4 Model)

## Level 1: System Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Local Machine                               │
│                                                                     │
│   ┌──────────────┐    HTTP      ┌─────────────────────────────────┐ │
│   │   User       │◄────────────►│        RitterRadar              │ │
│   │  (Browser)   │   :8000      │  (Python / FastAPI / Uvicorn)   │ │
│   └──────────────┘              └─────────────┬───────────────────┘ │
│                                               │                     │
└───────────────────────────────────────────────┼─────────────────────┘
                                                │ HTTPS
                              ┌─────────────────▼──────────────────┐
                              │     External Web Sources           │
                              │  mittelalterfeste.de               │
                              │  spectaculum.de                    │
                              │  schwerttanz.de + others           │
                              │  Nominatim (OpenStreetMap)         │
                              │  Leaflet tile servers (CARTO)      │
                              └────────────────────────────────────┘
```

RitterRadar is a **local-first** application.  All persistent data stays in
`data/ritterradar.db` (SQLite) on the user's machine.

---

## Level 2: Container Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│  RitterRadar Process (single Python process, uvicorn)                  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application                                             │  │
│  │                                                                  │  │
│  │  GET /               → Jinja2 index.html                        │  │
│  │  GET /api/markets    → market listing (filtered)                │  │
│  │  POST /api/.../hide  → toggle visibility                        │  │
│  │  GET /api/sources    → source list                              │  │
│  │  GET /api/crawl/*    → queue status + trigger                   │  │
│  │  GET /PUT /api/settings → user profile (home, radius)          │  │
│  │  GET /api/settings/geocode → Nominatim proxy                   │  │
│  │  GET /static/**      → CSS, JS, images                         │  │
│  └──────────────────┬───────────────────────────────────────────┘  │  │
│                     │                                               │  │
│  ┌──────────────────▼───────────────────────────────────────────┐  │  │
│  │  CrawlQueue (asyncio)                                         │  │  │
│  │  - asyncio.Queue of job IDs                                   │  │  │
│  │  - Reads sources.yaml; seeds Source table on startup         │  │  │
│  │  - Spawns N CrawlWorker asyncio.Tasks                        │  │  │
│  │  ┌──────────────────────────────────────────────────────┐    │  │  │
│  │  │  CrawlWorker × N                                     │    │  │  │
│  │  │  - PoliteHttpClient (delays, retries, backoff)       │    │  │  │
│  │  │  - Adapter (site-specific BeautifulSoup parser)      │    │  │  │
│  │  │  - Nominatim geocoding (with SQLite cache)           │    │  │  │
│  │  │  - Upsert Market rows + update CrawlJob row         │    │  │  │
│  │  └──────────────────────────────────────────────────────┘    │  │  │
│  └──────────────────────────────────────────────────────────────┘  │  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  SQLite Database  (data/ritterradar.db)                         │  │
│  │  market · source · crawl_job · user_settings · geocoding_cache  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Level 3: Component Diagram (Crawler Subsystem)

```
config/sources.yaml
      │
      │ parsed by CrawlQueue._seed_sources()
      ▼
┌─────────────┐    enqueues job IDs    ┌───────────────────────────────┐
│  CrawlQueue │───────────────────────►│  asyncio.Queue[int]           │
│  queue.py   │                        └──────────────┬────────────────┘
└─────────────┘                                       │ pulls job_id
                                                      ▼
                                        ┌─────────────────────────────┐
                                        │  CrawlWorker (worker.py)    │
                                        │  for each job:              │
                                        │  1. load CrawlJob from DB   │
                                        │  2. load Source from DB     │
                                        │  3. mark status = running   │
                                        │  4. get_adapter(name)       │
                                        │         │                   │
                                        │  ┌──────▼──────────────┐   │
                                        │  │ AbstractCrawlerAdapter│  │
                                        │  │  .crawl(client)      │  │
                                        │  │  → list[MarketData]  │  │
                                        │  └──────┬───────────────┘  │
                                        │         │                   │
                                        │  5. for each MarketData:    │
                                        │     geocode(city, PLZ)      │
                                        │     upsert Market row       │
                                        │  6. mark status = completed │
                                        └─────────────────────────────┘
```

---

## Level 4: Data Flow (Frontend → API → DB)

```
Browser                FastAPI                  SQLite
   │                      │                        │
   │  GET /api/markets     │                        │
   │  ?date_from=2026-07   │                        │
   │  &lat=48.1&lon=11.6   │                        │
   │  &radius_km=100       │──► SELECT market WHERE ─┤
   │  &market_type=medieval│    start_date≥date_from │
   │                       │    AND NOT hidden       │
   │                       │◄──── list[Market] ──────┤
   │                       │                        │
   │                       │  Haversine filter:     │
   │                       │  drop markets >100 km  │
   │                       │                        │
   │◄── JSON list[MarketOut]│                        │
   │                       │                        │
   │  renderMarkers(data)  │                        │
   │  [Leaflet DivIcons]   │                        │
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Database | SQLite | Zero infra; sufficient for <100k records |
| Background tasks | asyncio.Tasks (not Celery) | Single process; no broker needed |
| Geocoding | Nominatim (cached in DB) | Free; OpenStreetMap-compatible; respects ToS |
| Distance | Haversine only | Sufficient precision; no routing API needed |
| Frontend | Vanilla JS + Leaflet | No build step; runs anywhere |
| Crawl ethics | Random delay 0.5–2s + backoff | Polite; protects source sites |
| Failure mode | Per-adapter try/except | Broken adapter never stops others |
