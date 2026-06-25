Adapter Development Guide
=========================

This guide walks you through creating a new site-specific crawler adapter.

Step 1 — Inspect the target site
----------------------------------

Open the site in your browser and use the developer tools (F12) to find:

- The HTML element containing event listings (``article``, ``div.event``, ``tr``, ``li``, …)
- Where the event name lives (``h2``, ``h3``, ``strong``, …)
- Where the date string is (a ``span.date``, a table cell, plain text, …)
- Where the location is (city, postal code, address)

Step 2 — Create the adapter file
----------------------------------

Create ``src/ritterradar/crawler/adapters/mysite.py``::

    from bs4 import BeautifulSoup
    from ritterradar.crawler.base_adapter import AbstractCrawlerAdapter, MarketData
    from ritterradar.crawler.date_parser import parse_date_range
    from ritterradar.crawler.http_client import PoliteHttpClient
    from ritterradar.crawler.registry import register
    import re, logging
    from urllib.parse import urljoin

    logger = logging.getLogger(__name__)
    POSTAL_RE = re.compile(r"\b(\d{5})\b")
    CITY_RE   = re.compile(
        r"\b(\d{5})\s+([A-ZÄÖÜ][a-zäöüß\-]+(?:\s+[A-ZÄÖÜ][a-zäöüß\-]+)*)"
    )

    @register("mysite")
    class MySiteAdapter(AbstractCrawlerAdapter):
        SOURCE_NAME = "My Site"
        BASE_URL    = "https://www.mysite.de/events"

        async def crawl(self, client: PoliteHttpClient) -> list[MarketData]:
            results = []
            try:
                response = await client.get(self.BASE_URL)
                response.raise_for_status()
            except Exception:
                logger.exception("%s: fetch failed", self.SOURCE_NAME)
                return []

            soup = BeautifulSoup(response.text, "lxml")
            for article in soup.find_all("article", class_="event"):
                name  = article.find("h2").get_text(strip=True)
                full  = article.get_text(" ", strip=True)
                dates = parse_date_range(full)
                if not dates:
                    continue

                city = postal_code = None
                if (m := CITY_RE.search(full)):
                    postal_code, city = m.group(1), m.group(2)

                link = article.find("a", href=True)
                url  = urljoin(self.BASE_URL, link["href"]) if link else self.BASE_URL

                results.append(MarketData(
                    name=name[:200],
                    start_date=dates[0],
                    end_date=dates[1],
                    city=city,
                    postal_code=postal_code,
                    original_text=full[:1000],
                    source_url=url,
                    confidence_score=0.85,
                ))
            logger.info("%s: %d events found", self.SOURCE_NAME, len(results))
            return results

Step 3 — Register the import
------------------------------

Add to ``src/ritterradar/crawler/adapters/__init__.py``::

    from ritterradar.crawler.adapters import mysite  # noqa: F401

Step 4 — Add to sources.yaml
------------------------------

::

    - name: "My Site"
      url: "https://www.mysite.de/events"
      adapter: "mysite"
      enabled: true

Step 5 — Write tests
---------------------

Create ``tests/crawler/adapters/test_mysite.py`` with a fixture that provides
a mock HTML response, then assert that the correct ``MarketData`` objects are
returned::

    import pytest
    from unittest.mock import AsyncMock, MagicMock
    from datetime import date
    from ritterradar.crawler.adapters.mysite import MySiteAdapter

    FIXTURE_HTML = """
    <html><body>
      <article class="event">
        <h2>Ritterturnier Nürnberg</h2>
        <p class="date">12. bis 14. Juli 2026</p>
        <p>90402 Nürnberg, Hauptmarkt</p>
        <a href="/events/ritter-2026">Details</a>
      </article>
    </body></html>
    """

    @pytest.mark.asyncio
    async def test_mysite_adapter_parses_event():
        adapter = MySiteAdapter()
        mock_response = MagicMock()
        mock_response.text = FIXTURE_HTML
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        results = await adapter.crawl(mock_client)
        assert len(results) == 1
        assert results[0].name == "Ritterturnier Nürnberg"
        assert results[0].start_date == date(2026, 7, 12)
        assert results[0].postal_code == "90402"
        assert results[0].city == "Nürnberg"

Step 6 — Test manually
-----------------------

Start the app and trigger a crawl::

    bash scripts/start_dev.sh
    # In another terminal:
    bash scripts/trigger_crawl.sh
    bash scripts/crawl_status.sh

Expected return data fields
----------------------------

A ``MarketData`` object should provide at minimum:

.. list-table::
   :header-rows: 1

   * - Field
     - Required
     - Notes
   * - ``name``
     - Yes
     - Max 200 chars; trim whitespace
   * - ``start_date``
     - Yes
     - ``datetime.date``
   * - ``end_date``
     - Yes
     - Equal to ``start_date`` for single-day events
   * - ``market_type``
     - No
     - medieval / renaissance / viking / fantasy / christmas
   * - ``city``
     - Recommended
     - German city name; enables geocoding
   * - ``postal_code``
     - Recommended
     - 5-digit German postal code
   * - ``source_url``
     - Yes
     - Direct link to the event page (or base URL as fallback)
   * - ``original_text``
     - Recommended
     - Raw scraped text; max 1000 chars
   * - ``confidence_score``
     - No
     - 0.0–1.0; lower for uncertain data

Date parsing
-------------

Use :func:`ritterradar.crawler.date_parser.parse_date_range` to handle
all common German date formats automatically::

    from ritterradar.crawler.date_parser import parse_date_range

    dates = parse_date_range("12. bis 14. Juli 2026")
    # Returns: (date(2026, 7, 12), date(2026, 7, 14))

Supported formats:

- ``12. bis 14. Juli 2026``
- ``12. Juli bis 14. August 2026``
- ``12.07. - 14.07.2026``
- ``12.07.2026 - 14.07.2026``
- ``12. Juli 2026`` (single day)
- ``12.07.2026`` (single day)
