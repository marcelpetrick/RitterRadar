#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Standalone end-to-end crawler test.

Runs each enabled source's adapter directly (no database, no queue, no app
server) and prints a structured pass/fail report.  Exit code is 0 only if
every enabled adapter returns at least one result.

Usage:
    python3 scripts/crawl_e2e_test.py              # all enabled adapters
    python3 scripts/crawl_e2e_test.py spectaculum  # specific adapter(s)
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Allow running from repo root without installing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml  # type: ignore[import-untyped]

from ritterradar.crawler.http_client import PoliteHttpClient, make_client
from ritterradar.crawler.registry import get_adapter

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)-8s  %(name)s — %(message)s",
)
# Show adapter-level INFO so we can see "scraped N events"
logging.getLogger("ritterradar.crawler").setLevel(logging.INFO)

SOURCES_FILE = Path(__file__).parent.parent / "config" / "sources.yaml"
SEP = "─" * 60


def load_enabled_sources() -> list[dict]:
    with open(SOURCES_FILE) as f:
        cfg = yaml.safe_load(f)
    return [s for s in cfg.get("sources", []) if s.get("enabled", True)]


async def test_adapter(name: str, url: str) -> tuple[bool, int, float, str]:
    """Returns (passed, result_count, elapsed_s, error_message)."""
    t0 = time.monotonic()
    try:
        adapter = get_adapter(name)
    except KeyError:
        return False, 0, 0.0, f"adapter '{name}' not registered"

    try:
        async with make_client() as raw:
            client = PoliteHttpClient(raw, min_delay=0.2, max_delay=0.5)
            results = await adapter.crawl(client)
    except Exception as exc:
        elapsed = time.monotonic() - t0
        return False, 0, elapsed, str(exc)

    elapsed = time.monotonic() - t0
    return len(results) > 0, len(results), elapsed, ""


async def main(filter_names: list[str]) -> int:
    sources = load_enabled_sources()
    if filter_names:
        sources = [s for s in sources if s["name"].lower() in
                   {n.lower() for n in filter_names} or
                   s.get("adapter", "").lower() in {n.lower() for n in filter_names}]

    if not sources:
        print("No enabled sources found (check config/sources.yaml).")
        return 1

    print(f"\n{'⚔  RitterRadar — Crawler E2E Test':^60}")
    print(SEP)
    print(f"{'Source':<30} {'Results':>8} {'Time':>8}  Status")
    print(SEP)

    failures = 0
    for source in sources:
        sname = source["name"]
        adapter_name = source.get("adapter", "generic_table")
        passed, count, elapsed, err = await test_adapter(adapter_name, source.get("url", ""))
        status = "✓ PASS" if passed else "✗ FAIL"
        note = f"  ({err})" if err else ""
        print(f"{sname:<30} {count:>8} {elapsed:>7.1f}s  {status}{note}")
        if not passed:
            failures += 1

    print(SEP)
    total = len(sources)
    passed = total - failures
    print(f"Result: {passed}/{total} sources returned data.\n")

    if failures == 0:
        # Print sample results from the first passing adapter
        print("Sample data from first successful adapter:")
        source = sources[0]
        adapter = get_adapter(source.get("adapter", "generic_table"))
        async with make_client() as raw:
            client = PoliteHttpClient(raw, min_delay=0.2, max_delay=0.5)
            results = await adapter.crawl(client)
        for r in results[:5]:
            print(f"  • {r.name!r:<40}  {r.start_date} – {r.end_date}  {r.city or '?'}")
        print()

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    names = sys.argv[1:]
    sys.exit(asyncio.run(main(names)))
