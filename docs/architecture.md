# RitterRadar — Architecture Documentation

> Last updated: 2026-06-25 · Version 0.0.26

RitterRadar is a **local-first** Python web application.
It crawls German medieval market websites in the background, geocodes every event,
and lets the user explore them on an interactive OpenStreetMap map.
Everything runs in a single Python process, stores data in a local SQLite file,
and requires no external infrastructure (no cloud, no broker, no database server).

---

## C4 Level 1 — System Context

Who uses it and what external systems does it touch?

```mermaid
graph LR
    User["👤 User\n(Browser on localhost)"]

    subgraph LOCAL["Local machine"]
        RR["⚔ RitterRadar\nFastAPI · Python 3.12\nuvicorn :13370"]
        DB[("🗄 SQLite\ndata/ritterradar.db")]
        RR <-->|"reads/writes"| DB
    end

    subgraph INTERNET["Internet (HTTPS)"]
        OSM["🗺 OpenStreetMap\nTile servers\ntile.openstreetmap.org"]
        NOM["📍 Nominatim\nGeocoding API\nnominatim.openstreetmap.org"]
        MKI["📅 Mittelalterkalender.info\n~808 events/year"]
        VHM["📅 Vehi-Mercatus.de\n~287 DE events/year"]
        SPE["📅 Spectaculum.de\n9 MPS events/year"]
    end

    User -->|"GET / · GET /api/*\nHTTP :13370"| RR
    RR -->|"serves tiles\n(loaded by browser JS)"| OSM
    RR -->|"geocode PLZ / city\n1 req/s, cached"| NOM
    RR -->|"HTTPS crawl\nevery 24 h"| MKI
    RR -->|"HTTPS crawl\nevery 24 h"| VHM
    RR -->|"HTTPS crawl\nevery 24 h"| SPE
```

---

## C4 Level 2 — Container Diagram

What are the major building blocks inside the single process?

```mermaid
graph TB
    Browser["🌐 Browser\nLeaflet map · vanilla JS"]

    subgraph PROC["Python process (uvicorn)"]
        direction TB

        subgraph API["FastAPI — HTTP Layer"]
            R_ROOT["GET /\nJinja2 → index.html"]
            R_MKT["GET /api/markets\nFiltered market list\n(date · radius · type)"]
            R_HIDE["POST /api/markets/{id}/hide\nToggle visibility"]
            R_CRAWL["GET /api/crawl/status\nGET /api/crawl/geo-progress\nPOST /api/crawl/trigger"]
            R_SETTINGS["GET/PUT /api/settings\nGET /api/settings/geocode\nHome location + radius"]
            R_STATIC["GET /static/**\nCSS · JS · vendor/leaflet"]
        end

        subgraph CRAWLER["Crawler Subsystem (asyncio background)"]
            CQ["CrawlQueue\nSeeds Sources from\nconfig/sources.yaml\nSpawns 3 workers"]
            CW1["CrawlWorker 0"]
            CW2["CrawlWorker 1"]
            CW3["CrawlWorker 2"]
            CQ --> CW1 & CW2 & CW3
        end

        subgraph GEO["Geocoding"]
            NOM_PROXY["Nominatim client\n(geopy)\n1.1 s rate limit\nSQLite cache"]
        end

        DB[("SQLite\ndata/ritterradar.db\n5 tables")]

        API -->|"SELECT / UPDATE"| DB
        CRAWLER -->|"INSERT / UPDATE\nMarket · CrawlJob"| DB
        CRAWLER -->|"geocode city+PLZ"| NOM_PROXY
        NOM_PROXY -->|"cache reads/writes"| DB
    end

    Browser -->|"HTTP :13370"| API
    Browser -->|"fetch OSM tiles\n(direct, no proxy)"| TILE_EXT["tile.openstreetmap.org"]
    NOM_PROXY -->|"HTTPS"| NOM_EXT["nominatim.openstreetmap.org"]
    CW1 & CW2 & CW3 -->|"HTTPS crawl"| WEB_EXT["Market Websites"]
```

---

## C4 Level 3 — Crawler Pipeline

How does a single crawl job flow from queue to database?

```mermaid
sequenceDiagram
    participant APP  as main.py<br/>(startup)
    participant Q    as CrawlQueue
    participant W    as CrawlWorker
    participant REG  as Registry
    participant ADP  as Adapter<br/>(e.g. mittelalterkalender_info)
    participant HTTP as PoliteHttpClient
    participant NOM  as Nominatim<br/>(cached)
    participant DB   as SQLite

    APP->>Q: start() — read sources.yaml
    Q->>DB: upsert Source rows (3 active)
    Q->>DB: insert CrawlJob rows (status=pending)
    Q->>Q: put job_id into asyncio.Queue
    Q->>W: spawn 3 CrawlWorker tasks

    loop for each job_id from queue
        W->>DB: load CrawlJob + Source
        W->>DB: update CrawlJob status=running
        W->>REG: get_adapter("mittelalterkalender_info")
        REG-->>W: MittelalterkalenderInfoAdapter()

        W->>ADP: crawl(PoliteHttpClient)

        loop for each page / URL
            ADP->>HTTP: GET https://www.mittelalterkalender.info/...
            Note over HTTP: random delay 0.5–2 s<br/>retry on 429/503<br/>domain-drift guard
            HTTP-->>ADP: HTML response
            ADP->>ADP: BeautifulSoup parse<br/>extract MarketData list
        end

        ADP-->>W: list[MarketData] (806 events)

        loop for each MarketData
            W->>NOM: geocode("PLZ City")
            alt cache hit
                NOM-->>W: GeoResult (instant)
            else cache miss
                NOM->>NOM: wait 1.1 s (rate limit)
                NOM->>NOM_EXT: Nominatim HTTPS lookup
                NOM_EXT-->>NOM: lat/lon/display_name
                NOM->>DB: cache result
                NOM-->>W: GeoResult
            end
            W->>DB: upsert Market row<br/>(name + start_date + source_url unique)
        end

        W->>DB: CrawlJob status=completed<br/>events_discovered=806<br/>events_inserted=N
    end
```

---

## C4 Level 3 — Web UI Data Flow

How does the browser load and display the map when a user searches?

```mermaid
sequenceDiagram
    participant U    as 👤 User
    participant BRW  as Browser<br/>(Leaflet + JS modules)
    participant API  as FastAPI
    participant DB   as SQLite
    participant OSM  as OpenStreetMap<br/>tile.openstreetmap.org
    participant GEO  as Nominatim<br/>(via FastAPI)

    U->>BRW: navigate to http://127.0.0.1:13370

    BRW->>API: GET /
    API-->>BRW: index.html (Jinja2)

    BRW->>API: GET /static/vendor/leaflet.js
    BRW->>API: GET /static/js/map.js (ES module)
    BRW->>API: GET /static/js/filters.js
    BRW->>API: GET /static/js/activity-log.js
    BRW->>API: GET /static/js/crawler-status.js

    Note over BRW: map.js: L.map() + L.tileLayer(OSM)<br/>→ activity log: "Karte geladen"
    BRW->>OSM: GET /a/tile.openstreetmap.org/{z}/{x}/{y}.png
    OSM-->>BRW: PNG map tiles (Germany overview)

    BRW->>API: GET /api/settings
    API->>DB: SELECT user_settings WHERE id=1
    DB-->>API: {home: null, radius: 100}
    API-->>BRW: UserSettings JSON

    BRW->>API: GET /api/markets?date_from=2026-06&date_to=2027-06&market_type=medieval&...
    API->>DB: SELECT market WHERE start_date BETWEEN ... AND NOT hidden
    DB-->>API: list[Market] (all types, date-filtered)
    Note over API: Haversine filter:<br/>drop markets > radius_km<br/>(skipped when no home set)
    API-->>BRW: JSON list[MarketOut] (~336 markets)
    Note over BRW: Leaflet DivIcon markers<br/>placed at lat/lon<br/>activity log: "336 Märkte geladen"

    U->>BRW: types "81825" in Heimatort, clicks Suchen
    BRW->>API: GET /api/settings/geocode?q=81825
    API->>GEO: geocode("81825", user_agent)
    Note over GEO: cache miss → wait 1.1 s<br/>HTTPS to Nominatim
    GEO-->>API: GeoResult(lat=48.09, lon=11.56,<br/>display_name="81825, München…")
    API-->>BRW: {found:true, latitude:48.09, longitude:11.56, ...}

    BRW->>BRW: setHomePin(lat, lon) · flyTo(lat, lon, zoom=8)
    Note over BRW: activity log: "Heimatort gesetzt: 81825, München…"

    BRW->>API: PUT /api/settings {home_latitude:48.09, ...}
    API->>DB: UPDATE user_settings SET home_latitude=...

    BRW->>API: GET /api/markets?lat=48.09&lon=11.56&radius_km=100&date_from=...
    API->>DB: SELECT market WHERE ...
    Note over API: Haversine: keep only<br/>markets ≤ 100 km from München
    API-->>BRW: filtered JSON (~N markets near München)
    Note over BRW: Re-render markers\nactivity log: "N Märkte geladen"

    U->>BRW: clicks a marker
    BRW->>BRW: market-selected CustomEvent<br/>→ detail-panel.js renders side panel
    Note over BRW: activity log: "Markt geöffnet: …"
```

---

## Data Model (ER Diagram)

Five tables in `data/ritterradar.db`:

```mermaid
erDiagram
    SOURCE {
        int     id              PK
        string  name
        string  base_url
        string  adapter_name
        bool    enabled
        int     crawl_interval_hours
        datetime last_crawled_at    "nullable"
        datetime last_success_at    "nullable"
        string  last_error          "nullable"
    }

    CRAWL_JOB {
        int     id              PK
        int     source_id       FK
        string  source_name
        string  status          "pending|running|completed|failed|skipped"
        datetime started_at     "nullable"
        datetime finished_at    "nullable"
        int     events_discovered
        int     events_inserted
        int     events_updated
        string  error_message   "nullable, max 2000 chars"
    }

    MARKET {
        int     id              PK
        string  name
        string  market_type     "medieval|renaissance|viking|fantasy|christmas"
        date    start_date
        date    end_date
        string  city            "nullable"
        string  postal_code     "nullable"
        string  country         "default DE"
        float   latitude        "nullable — None = not geocoded yet"
        float   longitude       "nullable"
        bool    geocode_uncertain
        string  source_url      "unique with name+start_date"
        string  source_name
        bool    hidden          "user-hidden flag"
        float   confidence_score
        string  original_text   "raw scraped content, max 500 chars"
        datetime created_at
        datetime updated_at
    }

    GEOCODING_CACHE {
        int     id              PK
        string  query           "unique — normalised query string"
        float   latitude
        float   longitude
        string  display_name
        bool    uncertain
        datetime cached_at
    }

    USER_SETTINGS {
        int     id              PK "always 1"
        float   home_latitude   "nullable"
        float   home_longitude  "nullable"
        string  home_label      "nullable — display name"
        float   default_radius_km
        int     default_month_offset_start
        int     default_month_offset_end
    }

    SOURCE     ||--o{ CRAWL_JOB : "produces"
    CRAWL_JOB  }o--|| SOURCE    : "references"
```

UniqueConstraint on `market(name, start_date, source_url)` — prevents duplicate inserts across re-crawls.

---

## Active Crawler Sources (as of 2026-06-25)

```mermaid
graph LR
    YAML["config/sources.yaml"]:::config

    subgraph ACTIVE["✅ Active — 3 sources"]
        MKI["Mittelalterkalender.info\nadapter: mittelalterkalender_info\n~808 events / year\nURL: /mittelalterfeste-YEAR-nach-datum.php"]
        VHM["Vehi Mercatus Marktkalender\nadapter: vehi_mercatus\n~287 DE events / year\nURL: /marktkalender/?ansicht=liste&land=Deutschland&..."]
        SPE["Spectaculum.de (MPS)\nadapter: spectaculum\n9 premium events / year\nURL: homepage nav links /termine/SLUG/"]
    end

    subgraph DISABLED["❌ Disabled — 4 sources (documented reason)"]
        D1["Mittelalterfeste.de\nDomain expired → parked on sedo.com"]
        D2["Schwerttanz.de\nWrong TLS cert · no market calendar"]
        D3["Ritterschaft.de\nWrong TLS cert · resolves to droids.de"]
        D4["Mittelaltermarkt.com\nDomain for sale · JS-only page"]
    end

    YAML --> ACTIVE
    YAML --> DISABLED

    classDef config fill:#2c1a0e,color:#c5a028,stroke:#c5a028
```

---

## HTTP Client Safety Features

Every outbound crawler request goes through `PoliteHttpClient`:

```mermaid
flowchart TD
    A["adapter.crawl() calls client.get(url)"]
    B{"cache / reuse\nprevious response?"}
    C["random sleep\n0.5 – 2.0 s"]
    D["httpx.AsyncClient.get(url)\nUser-Agent: Firefox 128 UA\nAccept-Language: de-DE\nfollow_redirects=True"]
    E{"HTTP 200?"}
    F{"domain drift?\nfinal URL eTLD+1\n≠ requested eTLD+1"}
    G["raise RequestError\n'parked/hijacked domain'"]
    H{"HTTP 429\nor 503?"}
    I["exponential backoff\nmin(2^attempt, 60) s\nmax 3 retries"]
    J{"retries\nexhausted?"}
    K["raise RequestError\n'all retries exhausted'"]
    L["return httpx.Response\n(decompressed, text ready)"]

    A --> B
    B -->|no| C
    B -->|yes| L
    C --> D
    D --> E
    E -->|yes| F
    F -->|domain changed| G
    F -->|same eTLD+1| L
    E -->|no| H
    H -->|yes| I
    I --> J
    J -->|no| C
    J -->|yes| K
    H -->|other error| I
```

---

## Frontend Module Architecture

The browser-side code is split into ES modules that communicate via **Custom Events** (no shared global state):

```mermaid
graph TB
    subgraph HTML["index.html (served by Jinja2)"]
        IDX["#map · #sidebar · #detail-panel\n#status-bar · #jobs-panel · #activity-log"]
    end

    subgraph MODULES["ES Modules (type=module)"]
        ML["map.js\n• L.map() init\n• OSM tile layer\n• DivIcon markers (22×22)\n• renderMarkers(list)\n• setHomePin(lat,lon)\n• flyTo(lat,lon,zoom)\n• fires: market-selected event"]

        FL["filters.js\n• month-range selectors\n• type checkboxes\n• radius slider\n• geocodeHome(query)\n• fetchAndRender(silent?)\n• auto-refresh every 8 s (silent)"]

        DP["detail-panel.js\n• listens: market-selected\n• renders name, dates, city,\n  source, hide/unhide button\n• fires: markets-refresh"]

        CS["crawler-status.js\n• polls /api/crawl/status\n• polls /api/crawl/geo-progress\n• updates footer badges\n• triggers fetchAndRender\n  when new jobs complete"]

        AL["activity-log.js\n• appLog(level, msg)\n• listens: rr-log window event\n• renders timestamped\n  colour-coded log entries\n• max 50 entries, clearable"]
    end

    subgraph EVENTS["Custom Events (window)"]
        E1["rr-log\n{level, msg}"]
        E2["market-selected\n{market object}"]
        E3["markets-refresh"]
    end

    subgraph API["FastAPI REST API"]
        A1["GET /api/markets"]
        A2["GET /api/settings/geocode"]
        A3["GET /api/crawl/status"]
        A4["GET /api/crawl/geo-progress"]
        A5["PUT /api/settings"]
        A6["POST /api/markets/{id}/hide"]
    end

    IDX --> ML & FL & DP & CS & AL

    FL -->|"import"| ML
    FL -->|"import"| AL
    CS -->|"import"| FL
    CS -->|"import"| AL
    DP -->|"import"| AL

    ML -->|"fires"| E1
    ML -->|"fires"| E2
    DP -->|"fires"| E3
    DP -->|"fires"| E1
    FL -->|"fires"| E1

    E2 -->|"listened by"| DP
    E3 -->|"listened by"| CS
    E1 -->|"listened by"| AL

    FL -->|"fetch"| A1
    FL -->|"fetch"| A2
    FL -->|"fetch"| A5
    CS -->|"fetch"| A3
    CS -->|"fetch"| A4
    DP -->|"fetch"| A6
```

---

## Key Design Decisions

| Decision | Choice | Why |
|---|---|---|
| Single process | asyncio Tasks (not Celery/RQ) | No broker, no Redis, runs anywhere; crawlers and FastAPI share one event loop |
| Database | SQLite | Zero infrastructure; fits in one file; sufficient for < 100k events |
| Geocoding rate limit | 1.1 s/request + SQLite cache | Nominatim ToS; cache means PLZ "81825" is only looked up once ever |
| Tiles | OpenStreetMap standard (`tile.openstreetmap.org`) | Free, widely accessible, no API key |
| Leaflet | Bundled locally (`static/vendor/leaflet.js`) | No CDN dependency; works on offline/firewalled machines |
| Adapter pattern | `@register` decorator + registry dict | New source = one file + one YAML line; no core code change |
| Domain-drift guard | eTLD+1 comparison in PoliteHttpClient | Detects parked/expired domains automatically (caught mittelalterfeste.de → sedo.com) |
| No brotli | Accept-Encoding omitted from headers | httpx cannot decode brotli without the `brotli` package; omitting forces gzip/deflate which httpx handles natively |
| Frontend logging | Activity log panel + `rr-log` CustomEvent bus | Every UI action shows visible feedback without alert() dialogs |
| Module deduplication | ES module `import` + `window` event bus | `activity-log.js` is imported by three modules but only evaluated once |

---

## Directory Layout (as built)

```
RitterRadar/
├── src/ritterradar/
│   ├── main.py                      # FastAPI app + asyncio lifespan
│   ├── config.py                    # pydantic-settings (RITTERRADAR_* prefix)
│   ├── models/
│   │   ├── market.py                # Market SQLModel
│   │   ├── source.py                # Source SQLModel
│   │   ├── crawl_job.py             # CrawlJob SQLModel
│   │   ├── user_settings.py         # UserSettings (single row, id=1)
│   │   └── geocoding_cache.py       # GeocodingCache SQLModel
│   ├── database/
│   │   ├── engine.py                # get_engine(), create_tables()
│   │   └── session.py               # get_session() FastAPI dependency
│   ├── crawler/
│   │   ├── base_adapter.py          # AbstractCrawlerAdapter ABC + MarketData
│   │   ├── http_client.py           # PoliteHttpClient (delay, backoff, drift-guard)
│   │   ├── queue.py                 # CrawlQueue (seeds DB, spawns workers)
│   │   ├── worker.py                # CrawlWorker (geocode + upsert, failure isolation)
│   │   ├── registry.py              # @register decorator + get_adapter()
│   │   └── adapters/
│   │       ├── mittelalterkalender_info.py  # ✅ 808 events/year
│   │       ├── vehi_mercatus.py             # ✅ 287 DE events/year
│   │       ├── spectaculum.py               # ✅ 9 MPS events/year
│   │       ├── mittelalterfeste.py          # ❌ domain expired
│   │       ├── ritterschaft.py              # ❌ wrong TLS cert
│   │       └── schwerttanz.py               # ❌ wrong TLS cert
│   ├── geocoding/
│   │   ├── nominatim.py             # async Nominatim + SQLite cache + rate limit
│   │   └── haversine.py             # distance_km(lat1,lon1,lat2,lon2)
│   ├── api/
│   │   ├── markets.py               # GET /api/markets, POST /{id}/hide
│   │   ├── crawl.py                 # GET /status, GET /geo-progress, POST /trigger
│   │   ├── settings.py              # GET/PUT /api/settings + geocode proxy
│   │   └── sources.py               # GET /api/sources
│   ├── templates/
│   │   ├── base.html                # Leaflet CSS from /static/vendor/
│   │   └── index.html               # full SPA layout
│   └── static/
│       ├── css/ritterradar.css      # medieval palette + all component styles
│       ├── js/
│       │   ├── map.js               # Leaflet init, markers, OSM tiles
│       │   ├── filters.js           # sidebar controls + fetchAndRender()
│       │   ├── detail-panel.js      # market detail side panel
│       │   ├── crawler-status.js    # footer badges + jobs panel polling
│       │   └── activity-log.js      # UI activity log panel
│       └── vendor/
│           ├── leaflet.js           # Leaflet 1.9.4 (local, no CDN)
│           ├── leaflet.css
│           └── images/              # default Leaflet marker PNGs
├── config/
│   └── sources.yaml                 # source list (edit without code change)
├── data/
│   └── ritterradar.db               # SQLite — created by prepare.sh
├── scripts/
│   ├── prepare.sh                   # one-time setup (venv + pip + alembic)
│   ├── start_dev.sh                 # uvicorn with --reload
│   ├── start.sh                     # production start
│   ├── crawl_e2e_test.sh            # end-to-end adapter test (no server needed)
│   └── reset_db.sh                  # drop + recreate database
├── tests/                           # 48 pytest tests
├── documents/
│   ├── 00_VISION.md
│   ├── 01_plan.md
│   ├── 02_issues.md                 # first-run failure log (historical)
│   └── 03_sources.md                # per-source HTML structure + quirks
├── docs/
│   └── architecture.md              # this file
├── alembic/                         # DB migration history
├── pyproject.toml                   # version 0.0.26 · single source of truth
├── .env.example                     # copy to .env before first run
└── README.md
```
