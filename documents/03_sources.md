# RitterRadar — Crawler Sources Documentation

Last verified: 2026-06-26 · 7 active sources · 4 disabled

---

## Active Sources

### 1. Mittelalterkalender.info

| Property | Value |
|---|---|
| **Adapter** | `mittelalterkalender_info` |
| **Base URL** | https://www.mittelalterkalender.info |
| **List URL** | `/mittelaltermarkt/mittelalterfeste-{YEAR}-nach-datum.php` |
| **Events/year** | ~808 (2026) |
| **Coverage** | Germany + Europe |
| **Update frequency** | Continuous community submissions |

**Page structure:**  
Each event is a `<tr class="isbfilter">` row in a Semantic UI table:

```
[0] <td> start date + <span class="dash"> bis </span>
[1] <td> end date (DD.MM.YYYY)
[2] <td> <button formaction="detail-URL"> Event title </button>
[3] <td> PLZ (5-digit postal code)
[4] <td> City name
[5] <td> Details button (same URL as [2])
```

**Known quirks:**
- Cell[0] text renders as `"DD.MM.YYYYbis"` (no space between date and span text) — extract with `re.search(r"\d{2}\.\d{2}\.\d{4}")`.
- 2027 list page exists but may be empty until events are submitted.
- Detail pages use POST via `<button formaction>` — not directly accessible via GET.

---

### 2. Vehi Mercatus Marktkalender

| Property | Value |
|---|---|
| **Adapter** | `vehi_mercatus` |
| **Base URL** | https://vehi-mercatus.de |
| **List URL** | `/marktkalender/?ansicht=liste&land=Deutschland&jahr={YEAR}&seite={N}` |
| **Events/year** | ~287 (Germany, 2026); ~526 all countries |
| **Coverage** | Germany, Austria, Switzerland + Europe |
| **Update frequency** | Regularly maintained |

**Page structure:**  
Each event is an `<a class="mk-compact-row">` link with named child spans:

```html
<a class="mk-compact-row [is-past]" href="/marktkalender/SLUG/">
  <span class="mk-compact-col-date">26.02.–01.03.2026</span>
  <span class="mk-compact-col-name">Event NameFrei</span>
  <span class="mk-compact-col-location">24103 Kiel, Sch.</span>
  <span class="mk-compact-col-type">Mittelaltermarkt</span>
  <span class="mk-compact-col-arrow"></span>
</a>
```

**Date formats observed:**

| Format | Example | Meaning |
|---|---|---|
| Single day | `29.05.2026` | One-day event |
| Same-month range | `06.–08.03.2026` | 6–8 March 2026 |
| Cross-month range | `26.02.–01.03.2026` | 26 Feb – 1 Mar 2026 |

**Known quirks:**
- "Frei" suffix in event names means free entry — stripped by adapter.
- Location format: `"NNNNN City, StateAbbr."` — regex extracts PLZ and city.
- Pagination controlled by `?seite=N`; adapter reads `"Seite N von M"` from `.mk-event-count` to know when to stop.
- Filter `?land=Deutschland` limits to German events; remove for pan-European.

---

### 3. Spectaculum.de (MPS)

| Property | Value |
|---|---|
| **Adapter** | `spectaculum` |
| **Base URL** | https://www.spectaculum.de |
| **Events/year** | ~6–9 (MPS events only) |
| **Coverage** | Germany |
| **Update frequency** | Annual schedule, published in advance |

**Page structure:**  
All upcoming MPS events are listed in the homepage navigation as `<a>` links:

```html
<a href="/termine/bueckeburg_1/">25.07. + 26.07.2026Bückeburg 1</a>
```

Link text format: `{DD.MM.} [+|-] {DD.MM.YYYY}{city name}` concatenated.  
Adapter uses regex `(\d{1,2})\.(\d{2})\.\s*[+\-–]\s*(\d{1,2})\.(\d{2})\.(\d{4})\s*(.*)` to split date and city.

**Known quirks:**
- `/termine` path (listed in old documentation) returns **403 Forbidden** — do not use.
- Only 9 events per year (MPS is a premium medieval event series).
- Sub-events at the same city get a trailing digit (e.g., "Bückeburg 1", "Bückeburg 2") — adapter strips the number suffix from the city name.

---

### 4. Pfalzis Marktkalendarium

| Property | Value |
|---|---|
| **Adapter** | `marktkalendarium` · `__version__ = "0.1.0"` |
| **Base URL** | https://marktkalendarium.de |
| **List URL** | `/maerkte{YEAR}.php` |
| **Events/year** | ~334 (2026), 8 (2027 early entries) |
| **Coverage** | Germany (301), Switzerland (11), Austria (10), others (12) |
| **Update frequency** | Hand-curated, new entries added continuously |

**Page structure:**  
Plain HTML table rows — no class selector needed, select by date content:

```
[0] <td> start date "D.M.YYYY" or "DD.MM.YYYY" (no leading zeros!)
[1] <td> end date (same format)
[2] <td> event name (plain text)
[3] <td> <a href="maps.google.de/...?q=D-XXXXX City">D-55232 Alzey</a>
[4] <td> venue / location detail (e.g. "Innenstadt", "Schlossgarten")
[5] <td> <a href="URL">Event website name</a>
[6] <td> optional second link or email contact
```

**Country prefix mapping:**

| Prefix | ISO | Example |
|---|---|---|
| `D-` | DE | `D-55232 Alzey` |
| `A-` | AT | `A-1010 Wien` |
| `CH-` | CH | `CH-8001 Zürich` |
| `L-` | LU | `L-1234 Luxembourg` |

**Known quirks:**
- Date format uses variable width: `"6.6.2026"` not `"06.06.2026"` — parse with regex `(\d{1,2})\.(\d{1,2})\.(\d{4})`.
- Row count fluctuates; all rows with a date in any TD are event rows.
- Source URL extracted from first `<a href>` in TD[5] that is not a Google Maps link.
- Some entries use `"d-"` (lowercase) prefix — normalise before lookup.

---

### 5. Mittelaltermarkt.online

| Property | Value |
|---|---|
| **Adapter** | `mittelaltermarkt_online` · `__version__ = "0.1.0"` |
| **Base URL** | https://mittelaltermarkt.online |
| **API URL** | `/wp-json/tribe/events/v1/events` (The Events Calendar plugin) |
| **Events/year** | 531 (2026-2027: 491 DE + 29 AT + 9 CH) |
| **Coverage** | Germany, Austria, Switzerland |
| **Update frequency** | Community-submitted, regularly updated |

**Access method: REST API (no HTML scraping)**

```
GET /wp-json/tribe/events/v1/events?per_page=100&status=publish&start_date=YYYY-01-01&end_date=YYYY+1-12-31&page=N
```

Response JSON:
```json
{
  "events": [...],
  "total": 531,
  "total_pages": 11,
  "next_rest_url": "..."
}
```

Event fields used:
```
title          → name (HTML-unescaped — WP encodes "–" as &#8211;)
start_date     → "YYYY-MM-DD HH:MM:SS"
end_date       → "YYYY-MM-DD HH:MM:SS"
url            → source_url (canonical event page)
categories[].slug → market_type (see table below)
venue.city     → city
venue.zip      → postal_code
venue.country  → country ("Deutschland" → "DE")
venue.geo_lat  → latitude (pre-geocoded, skips Nominatim)
venue.geo_lng  → longitude (pre-geocoded, skips Nominatim)
```

**Category → market_type mapping:**

| Slug | market_type |
|---|---|
| `mittelalterspektakel`, `mittelaltermaerkten`, `mittelalterfeste`, `ritterturniere`, `historische-feste`, `andere-veranstaltungen` | `medieval` |
| `weihnachtsmaerkte` | `christmas` |
| `wikingerspektakel` | `viking` |
| `renaissance-*` | `renaissance` |
| `fantasy-*` | `fantasy` |

**Key advantage:** 528/531 events have pre-geocoded `venue.geo_lat` / `venue.geo_lng` — the worker skips Nominatim for these, saving ~528 API calls per crawl cycle.

---

### 6. Trollfelsen.de

| Property | Value |
|---|---|
| **Adapter** | `trollfelsen` · `__version__ = "0.1.0"` |
| **Base URL** | https://trollfelsen.de |
| **List URL** | `/termine` |
| **Events/year** | ~21 confirmed (2026) |
| **Coverage** | Germany primarily; Austria/Switzerland possible |
| **Update frequency** | Updated when vendor confirms/adds appearances |

**Page structure (class="event-card"):**

```html
<div class="event-card">
  <div class="picture"><a href="EVENT_WEBSITE">...</a></div>
  <div class="infos">
    <h3>Event name</h3>
    <div>
      <div class="font-weight-bold">DD.MM.YYYY - DD.MM.YYYY</div>
    </div>
    <div>Mehr von: Organizer</div>
    <div class="icons">...</div>   <!-- social links (skipped) -->
    <div>Venue</div>
    <div>Street address</div>
    <div>DE - 06217 Merseburg</div>   <!-- country code, PLZ, city -->
    <!-- optional: -->
    <div>* Teilnahme noch nicht bestätigt</div>
  </div>
</div>
```

**Key advantage:** The picture link (`<a href>` in `.picture`) points to the
event's own website — not trollfelsen.de. This gives a higher-quality `source_url`
than sources that only link to their own listing.

**Filtering:** Cards with "Teilnahme noch nicht bestätigt" in their text are
skipped (11 of 32 cards in 2026). Only events from the current year onwards
are returned.

**Known quirks:**
- Site is Trollfelsen's own attendance schedule, not a comprehensive market
  directory — dataset is small but events are often niche or under-represented
  elsewhere.
- Occasional PLZ typos (e.g. "2399" instead of "23999"); accepted as-is;
  Nominatim geocodes from city name when PLZ is wrong.
- Picture link URL may point to a co-located event sponsor rather than the
  event's canonical site (e.g. WGT for a sub-event at Merseburg).

---

### 7. Taterman.at

| Property | Value |
|---|---|
| **Adapter** | `taterman_at` · `__version__ = "0.1.0"` |
| **Base URL** | https://www.taterman.at |
| **Feed URL** | `/termin/categories/markt/?ical=1` (wp-events-plugin.com) |
| **Events/year** | ~26 (2026, Austria only; growing) |
| **Coverage** | Austria exclusively |
| **Update frequency** | Community-submitted, continuously updated |

**Access method: iCal feed (RFC 5545)**

```
GET https://www.taterman.at/termin/categories/markt/?ical=1
Content-Type: text/calendar; charset=utf-8
```

Each VEVENT uses:
```
SUMMARY   → event name
DTSTART;TZID=Europe/Vienna;VALUE=DATE:YYYYMMDD   → all-day start
DTEND;TZID=Europe/Vienna;VALUE=DATE:YYYYMMDD     → exclusive end (subtract 1 day)
URL       → canonical event page on taterman.at (source_url)
LOCATION  → "Venue, [Street,] City, PLZ, Österreich"
CATEGORIES → "Bundesland,Markt,<Province>" or "Markt,<Theme>"
```

**LOCATION parsing:**

The LOCATION value follows the pattern `Venue, [Street,] City, PLZ, Österreich`.
Split by `", "` → scan for a 4-digit PLZ; city = part immediately before PLZ.
If that part is an Austrian province name, city is set to None (Nominatim
geocodes from PLZ alone).

Provinces excluded from city field: `Niederösterreich`, `Oberösterreich`,
`Steiermark`, `Tirol`, `Vorarlberg`, `Kärnten`, `Burgenland`, `NÖ`, `OÖ`.
Wien and Salzburg are kept (both province and city).

**Market-type detection (SUMMARY keyword scan):**

| Keyword | market_type |
|---|---|
| `adventmarkt`, `weihnacht`, `advent` | `christmas` |
| `wikinger`, `viking` | `viking` |
| `renaissance` | `renaissance` |
| `fantasy` | `fantasy` |
| everything else | `medieval` |

**Known quirks:**
- taterman.at uses the non-standard `DTSTART;TZID=Europe/Vienna;VALUE=DATE:...`
  combination — RFC 5545 forbids TZID on VALUE=DATE properties, but the plugin
  emits it anyway. The `icalendar` library returns a timezone-aware `datetime`
  instead of a plain `date`; the adapter detects all-day via `dtstart.params.get("VALUE") == "DATE"`.
- DTEND for all-day events is exclusive (RFC 5545 §3.6.1) — the adapter
  subtracts 1 day to store the actual last day of the event.
- Country is always `AT` (all taterman events are Austrian).
- The feed covers all years since 2014; adapter filters to current + next year.

---

## Disabled Sources (Investigation Required)

| Source | URL | Reason disabled |
|---|---|---|
| **Mittelalterfeste.de** | `https://www.mittelalterfeste.de/termine` | Domain expired; `GET /termine` → 303 → `sedo.com` (parked) |
| **Schwerttanz Marktkalender** | `https://www.schwerttanz.de/marktkalender` | TLS cert issued for `hypenat-casa-25.netboot.nethost.cz` (wrong host); `/marktkalender` → 404 |
| **Ritterschaft.de** | `https://www.ritterschaft.de/termine` | TLS cert issued for `mx01.droids.de`; domain returns `droids.de` content |
| **Mittelaltermarkt.com** | `https://www.mittelaltermarkt.com/marktkalender` | Domain for sale — returns a JS spinner with no real content |

---

## Crawler Architecture

```
config/sources.yaml
        │
        │  (name, url, adapter, enabled, crawl_interval_hours)
        ▼
  CrawlQueue._seed_sources()
        │
        │  Creates Source rows in DB + CrawlJob rows in asyncio.Queue
        ▼
  CrawlWorker (N parallel workers)
        │
        │  1. Load CrawlJob + Source from DB
        │  2. Instantiate adapter via registry.get_adapter(source.adapter_name)
        │  3. Run adapter.crawl(PoliteHttpClient) → list[MarketData]
        │  4. For each MarketData:
        │       if mdata.latitude is set → use directly (skip Nominatim)
        │       else → geocode via Nominatim (SQLite cache, 1.1s rate limit)
        │  5. Three-phase dedup upsert (see below)
        │  6. Mark CrawlJob completed/failed
        ▼
  SQLite database (data/ritterradar.db)
```

### Three-Phase Dedup Upsert

Because the same real-world event appears on multiple source websites with
different URLs, a simple `(name, start_date, source_url)` key was insufficient
— it led to 3× duplicates for popular events.

The worker now checks in order:

| Phase | Key | Purpose |
|---|---|---|
| 1a | `name + start_date + postal_code` | Cross-source dedup (PLZ) — primary |
| 1b | `name + start_date + city` | Cross-source dedup (city) — for sources that omit PLZ |
| 2  | `name + start_date + source_url` | Same-source re-crawl detection |

When phases 1a or 1b find an existing row, the record is **enriched** rather than duplicated:
- Fills in missing `city`, `postal_code`, `address`
- Improves geocoords when existing row has `latitude = NULL`
- Updates `end_date` and `original_text` if new data is richer

Correctly **kept separate**: events that share a generic name (e.g., "Mittelaltermarkt")
but are at different locations on the same date — these have distinct postal codes and
are genuinely different events.

### PoliteHttpClient behaviour

- Random delay: 0.5–2.0 s between requests
- Retry on HTTP 429/503: exponential backoff `min(2^attempt, 60)` seconds
- Retry on network error: same backoff, max 3 retries
- Domain-drift guard: raises `RequestError` if final URL domain differs from requested domain (parked-domain detection)
- User-Agent: `Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0`
- `Accept-Encoding` managed by httpx (gzip/deflate) — **do not** manually advertise `br` without installing the `brotli` package

---

## Adding a New Source

### Step 1 — Inspect the target site

```bash
# Check accessibility and find the right URL
curl -skL --max-time 10 \
  -A "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0" \
  -H "Accept-Language: de-DE,de;q=0.9" \
  "https://www.example.de/termine" | python3 -c "
from bs4 import BeautifulSoup
import sys
soup = BeautifulSoup(sys.stdin.read(), 'html.parser')
print(soup.title.get_text() if soup.title else 'no title')
classes = sorted({c for t in soup.find_all(class_=True) for c in t.get('class',[])})
print('Classes:', classes[:30])
print('Text:', soup.get_text(strip=True)[:500])
"
```

### Step 2 — Write the adapter

Create `src/ritterradar/crawler/adapters/mysite.py`.

Every adapter must include version and verification metadata at the top:

```python
__version__ = "0.1.0"          # start here; bump when parsing logic changes
_VERIFIED_DATE = "YYYY-MM-DD"  # last date you confirmed the site structure is correct
```

Adapter versioning uses SemVer:
- **patch** bump (`0.1.x`): minor fixes, whitespace/regex tuning
- **minor** bump (`0.x.0`): structural change in how the site is parsed
- **major** bump (`x.0.0`): completely new page structure (site redesign)

See `docs/source/adapter_guide.rst` for the full annotated example.

### Step 3 — Register the adapter

Add import to `src/ritterradar/crawler/adapters/__init__.py`:
```python
from ritterradar.crawler.adapters import mysite  # noqa: F401
```

### Step 4 — Add to sources.yaml

```yaml
- name: "My Site"
  url: "https://www.example.de/termine"
  adapter: "mysite"
  enabled: true
  crawl_interval_hours: 24
```

### Step 5 — Validate end-to-end

```bash
bash scripts/crawl_e2e_test.sh mysite
```

The test must print `✓ PASS` with at least 1 result before enabling in production.
