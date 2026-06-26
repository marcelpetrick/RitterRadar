# ⚔ RitterRadar

**Discover German medieval markets, Renaissance festivals, Viking fairs, and
fantasy markets on a beautiful interactive map.**

RitterRadar crawls configured web sources in the background, geocodes event
locations, and displays results on a Leaflet/OpenStreetMap map with medieval
visual styling.  Everything runs locally — no cloud, no accounts, no data
leaves your machine.

**Author: Marcel Petrick <mail@marcelpetrick.it>**  
**License: GPLv3 or later. See `LICENSE`.**

### current state web UI
![](media/currentStateWebUi.png)

---

## Features

| Feature | Description |
|---|---|
| **Auto-crawling** | Background workers harvest events from all configured sources on startup |
| **6 active adapters** | mittelalterkalender.info, vehi-mercatus.de, spectaculum.de, marktkalendarium.de, mittelaltermarkt.online, taterman.at |
| **REST API adapter** | mittelaltermarkt.online uses WordPress Events Calendar JSON API — no HTML scraping |
| **Deduplication** | Three-phase upsert (PLZ → city → source_url) merges the same event from multiple sources into one record |
| **Extensible** | Generic table adapter + guide for adding any new site; each adapter carries its own SemVer |
| **Geocoding** | Nominatim (OpenStreetMap) with SQLite cache and rate-limit compliance |
| **Distance filter** | Haversine straight-line distance from your home pin |
| **Time filter** | Month-range slider covering current month through next 12 months |
| **Type filter** | Medieval · Renaissance · Viking · Fantasy · Christmas |
| **Detail panel** | Click a marker for name, dates, location, program, source link, hide button |
| **Crawler status** | Live badge counts + per-job log in the status bar |
| **Medieval UI** | Dark wood + aged gold + burgundy theme with IM Fell English font |

---

## Requirements

- **Python 3.12+** (tested on 3.14)
- **pip** (no other system dependencies)
- **Internet access** for map tiles and initial crawling

---

## Installation

**Recommended — one command does everything** (venv, deps, DB migration):

```bash
# 1. Clone the repository
git clone https://github.com/mpetrick/RitterRadar.git
cd RitterRadar

# 2. Copy and edit the environment file
cp .env.example .env
# Set RITTERRADAR_GEOCODER_EMAIL to your e-mail address

# 3. Run the setup script (creates .venv/, installs deps, migrates DB)
bash scripts/prepare.sh
```

> `prepare.sh` works on Arch/Manjaro and any system that enforces
> PEP 668 (externally-managed-environment).  It never touches the
> system Python — everything goes into `.venv/`.

**Manual alternative:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
```

---

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

Key settings:

| Variable | Default | Description |
|---|---|---|
| `RITTERRADAR_DB_PATH` | `data/ritterradar.db` | SQLite database file path |
| `RITTERRADAR_SOURCES_FILE` | `config/sources.yaml` | Crawl source list |
| `RITTERRADAR_WORKERS` | `3` | Parallel crawler workers |
| `RITTERRADAR_GEOCODER_EMAIL` | *(empty)* | Your email for Nominatim user-agent (required by ToS) |
| `RITTERRADAR_HOST` | `127.0.0.1` | Bind address |
| `RITTERRADAR_PORT` | `8000` | HTTP port |
| `RITTERRADAR_LOG_LEVEL` | `INFO` | Log level |

> **Set your Nominatim email** — the OpenStreetMap geocoder requires a valid
> contact in the User-Agent.  Without it geocoding may be rate-limited.

---

## Running the App

### Development (auto-reload)

```bash
bash scripts/start_dev.sh
# or: uvicorn ritterradar.main:app --reload
```

### Production

```bash
bash scripts/start.sh
# or: ritterradar          (console script after pip install)
```

Open your browser at **http://127.0.0.1:8000**

The app:
1. Creates `data/ritterradar.db` automatically on first start
2. Seeds all sources from `config/sources.yaml`
3. Starts background crawler workers
4. Opens a beautiful medieval-themed map

---

## Using the Map

| Action | Effect |
|---|---|
| Enter postal code / city in **Heimatort** | Geocodes and sets your home pin; enables distance filter |
| Drag **Umkreis** slider | Limits markers to N km radius |
| Choose months in **Zeitraum** | Filters by event start date |
| Check/uncheck **Markttyp** boxes | Show/hide event categories |
| Click **Karte aktualisieren** | Re-applies all filters |
| **Hover** a marker | Shows name and date range |
| **Click** a marker | Opens detail panel on the right |
| **↗ Zur Originalseite** | Opens the source page in a new tab |
| **🚫 Ausblenden** | Hides the market from the map (data kept in DB) |
| Click **⟳ Neu laden** in status bar | Triggers a fresh crawl of all sources |

---

## Crawler Management

### Trigger a crawl via script

```bash
bash scripts/trigger_crawl.sh
```

### Check crawl status

```bash
bash scripts/crawl_status.sh
```

### Via API

```bash
# Trigger
curl -X POST http://127.0.0.1:8000/api/crawl/trigger

# Status
curl http://127.0.0.1:8000/api/crawl/status | python3 -m json.tool
```

---

## Adding New Crawl Sources

### Option A — Use the generic table adapter

Add a new entry to `config/sources.yaml`:

```yaml
- name: "My New Site"
  url: "https://www.example.de/termine"
  adapter: "generic_table"
  enabled: true
```

Restart the app.  The generic adapter tries to extract events from HTML tables
automatically.  It works on many sites without any code change.

### Option B — Write a dedicated adapter

1. Create `src/ritterradar/crawler/adapters/mysite.py`:

```python
# SPDX-License-Identifier: GPL-3.0-or-later
from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
from ritterradar.crawler.http_client import PoliteHttpClient
from ritterradar.crawler.registry import register
from bs4 import BeautifulSoup
from datetime import date

__version__ = "0.1.0"          # bump when parsing logic changes
_VERIFIED_DATE = "YYYY-MM-DD"  # last date you confirmed the page structure

@register("mysite")
class MySiteAdapter(AbstractCrawlerAdapter):
    SOURCE_NAME = "My Site"
    BASE_URL    = "https://www.mysite.de/events"

    async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
        response = await client.get(self.BASE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        results = []
        for article in soup.find_all("article", class_="event"):
            name = article.find("h2").get_text(strip=True)
            # parse start/end dates from the article, set city/postal_code for dedup
            results.append(MarketData(
                name=name,
                start_date=date(2026, 7, 1),   # replace with real parsing
                end_date=date(2026, 7, 3),
                city="Berlin",
                postal_code="10115",
                source_url=self.BASE_URL,
            ))
        return results
```

2. Import it in `src/ritterradar/crawler/adapters/__init__.py`:

```python
from ritterradar.crawler.adapters import mysite  # noqa: F401
```

3. Add to `config/sources.yaml`:

```yaml
- name: "My Site"
  url: "https://www.mysite.de/events"
  adapter: "mysite"
  enabled: true
```

4. Restart the app.

See `docs/adapter-guide.md` for a complete walk-through.

---

## Database Management

### Reset the database

```bash
bash scripts/reset_db.sh
```

This deletes the SQLite file and recreates the schema.  All markets and crawl
history are lost.

### Apply migrations (after upgrading)

```bash
alembic upgrade head
```

### Inspect the database

```bash
sqlite3 data/ritterradar.db ".tables"
sqlite3 data/ritterradar.db "SELECT name, start_date, city FROM market LIMIT 20;"
```

---

## Development

### Install dev dependencies

```bash
bash scripts/prepare.sh          # first time
# or manually:
pip install -e ".[dev]"
```

### Run tests

```bash
pytest                       # with coverage report
pytest --no-cov -x -q       # fast, stop on first failure
```

### Lint and format

```bash
ruff check src tests         # lint
ruff format src tests        # format
mypy src                     # type check
```

### All in one (CI)

```bash
# with just:
just ci

# without just:
ruff check src tests && mypy src && pytest
```

### Build Sphinx documentation

```bash
sphinx-build docs/source docs/_build/html
open docs/_build/html/index.html
```

---

## API Reference

Interactive docs available at **http://127.0.0.1:8000/api/docs** (Swagger UI)
and **http://127.0.0.1:8000/api/redoc** (ReDoc) when the app is running.

Key endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/markets` | List markets with optional filters |
| `POST` | `/api/markets/{id}/hide` | Toggle market visibility |
| `GET` | `/api/sources` | List configured crawl sources |
| `GET` | `/api/crawl/status` | Crawler queue state + recent jobs |
| `POST` | `/api/crawl/trigger` | Enqueue all enabled sources now |
| `GET` | `/api/settings` | Get user settings (home location, etc.) |
| `PUT` | `/api/settings` | Update user settings |
| `GET` | `/api/settings/geocode?q=…` | Geocode an address |
| `GET` | `/health` | Liveness check |

---

## Architecture

See `docs/architecture.md` for C4 container and component diagrams.

```
┌──────────────────────────────────────────────────────────┐
│  Browser (Leaflet + Vanilla JS)                           │
│  - map.js · filters.js · detail-panel.js · crawler-status│
└───────────────────────┬──────────────────────────────────┘
                        │ HTTP (polling, 4–8 s)
┌───────────────────────▼──────────────────────────────────┐
│  FastAPI Application (uvicorn)                            │
│  - /api/markets   - /api/settings  - /health             │
│  - /api/sources   - /api/crawl/*                         │
└──────────┬────────────────────────┬──────────────────────┘
           │                        │
┌──────────▼───────────┐  ┌────────▼──────────────────────┐
│  SQLite (SQLModel)    │  │  CrawlQueue + N CrawlWorkers  │
│  - market            │  │  - asyncio.Queue              │
│  - source            │◄─┤  - PoliteHttpClient           │
│  - crawl_job         │  │  - Per-site Adapters          │
│  - user_settings     │  │  - Nominatim geocoding        │
│  - geocoding_cache   │  └───────────────────────────────┘
└──────────────────────┘
```

---

## License

RitterRadar is free software licensed under the
[GNU General Public License v3.0](LICENSE) or any later version.

Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>

> *"Free as in freedom — and as in the freedom to roam medieval markets."*
