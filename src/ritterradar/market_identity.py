# SPDX-License-Identifier: GPL-3.0-or-later
"""Identity rules for sources with one canonical page per event."""

from urllib.parse import urlsplit

from ritterradar.models.market import Market


def has_stable_event_url(source_name: str, url: str) -> bool:
    """Taterman's iCal URL identifies an event even when its dates change."""
    parsed = urlsplit(url)
    return (
        source_name == "Taterman.at"
        and parsed.hostname in {"taterman.at", "www.taterman.at"}
        and parsed.path.startswith("/termin/")
        and len(parsed.path.strip("/").split("/")) == 2
    )


def current_source_records(markets: list[Market]) -> list[Market]:
    """Suppress superseded overlapping dates, retaining historical rows in storage.

    Recurring events on disjoint dates and records from separate sources remain
    separate. This also repairs display of duplicates created by older crawls.
    """
    current: list[Market] = []
    for market in sorted(markets, key=lambda item: item.updated_at, reverse=True):
        if has_stable_event_url(market.source_name, market.source_url) and any(
            other.source_name == market.source_name
            and other.source_url == market.source_url
            and other.start_date <= market.end_date
            and market.start_date <= other.end_date
            for other in current
        ):
            continue
        current.append(market)
    return sorted(current, key=lambda item: item.start_date)
