# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marcel Petrick <mail@marcelpetrick.it>
"""Tests for crawl queue worker lifecycle and source seeding."""

from sqlmodel import Session, select

from ritterradar.config import Settings
from ritterradar.crawler.queue import CrawlQueue
from ritterradar.models.source import Source


async def test_start_and_stop_spawn_and_join_workers(tmp_path, monkeypatch):
    sources = tmp_path / "sources.yaml"
    sources.write_text(
        "sources:\n"
        '  - name: "Queue lifecycle source"\n'
        '    url: "https://example.com"\n'
        '    adapter: "generic_table"\n'
        "    enabled: false\n",
        encoding="utf-8",
    )
    queue = CrawlQueue(Settings(workers=2, sources_file=sources))
    # Keep the shared test database's enabled sources from being crawled for real.
    monkeypatch.setattr(queue, "_enqueue_all", lambda: 0)

    await queue.start()
    assert len(queue._workers) == 2
    await queue.stop()

    assert queue.get_status()["workers"] == 2
    assert all(w._task is not None and w._task.done() for w in queue._workers)


def test_seed_sources_ignores_missing_and_malformed_files(tmp_path):
    CrawlQueue(Settings(workers=0, sources_file=tmp_path / "missing.yaml"))._seed_sources()

    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("- just\n- a list\n", encoding="utf-8")
    CrawlQueue(Settings(workers=0, sources_file=malformed))._seed_sources()


def test_seed_sources_updates_existing_source(tmp_path, session: Session):
    config = tmp_path / "sources.yaml"
    config.write_text(
        'sources:\n  - name: "Seed update source"\n    url: "https://old.example"\n'
        '    adapter: "generic_table"\n',
        encoding="utf-8",
    )
    queue = CrawlQueue(Settings(workers=0, sources_file=config))
    queue._seed_sources()

    config.write_text(
        'sources:\n  - name: "Seed update source"\n    url: "https://new.example"\n'
        '    adapter: "fyndling"\n    enabled: false\n',
        encoding="utf-8",
    )
    queue._seed_sources()

    source = session.exec(select(Source).where(Source.name == "Seed update source")).one()
    session.refresh(source)
    assert (source.base_url, source.adapter_name, source.enabled) == (
        "https://new.example",
        "fyndling",
        False,
    )
