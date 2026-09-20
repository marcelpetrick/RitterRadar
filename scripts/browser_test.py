#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline browser regression test with an isolated database and real FastAPI app.

Install with pip install -e '.[browser]' and python -m playwright install chromium.
Set RITTERRADAR_BROWSER_EXECUTABLE to use an existing Chromium installation.
No live sources, tiles, fonts, geocoder, or personal database are used.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from sqlmodel import Session, SQLModel, create_engine

import ritterradar.models  # noqa: F401 — register the complete schema
from ritterradar.models.market import Market

ROOT = Path(__file__).resolve().parents[1]


def seed_database(path: Path) -> None:
    engine = create_engine(f"sqlite:///{path}")
    SQLModel.metadata.create_all(engine)
    rows = [
        {"name": "Ritterfest am Kloster", "market_type": "medieval"},
        {"name": "Wikingerfest am See", "market_type": "viking"},
        # A longer duplicate with no coordinates must not replace the mapped row.
        {"name": "Ritterfest am Kloster 2026", "latitude": None, "longitude": None},
        {"name": "Ritterfest am Kloster", "country": "CH"},
        {
            "name": "Mittelalterfest über die Monatsgrenze",
            "start_date": date(2026, 8, 30),
            "end_date": date(2026, 9, 2),
        },
        {"name": "ABGESAGT Ritterfest"},
        {"name": "Römerfest Carnuntum"},
        {"name": "Mähen mit der Sense", "source_name": "Fyndling.de"},
    ]
    with Session(engine) as session:
        for i, overrides in enumerate(rows):
            values = {
                "name": "",
                "start_date": date(2026, 9, 19),
                "end_date": date(2026, 9, 20),
                "city": "Teststadt",
                "postal_code": "12345",
                "country": "DE",
                "latitude": 51.0,
                "longitude": 10.0,
                "source_name": "Browser fixture",
                "source_url": f"https://example.invalid/event/{i}",
            }
            values.update(overrides)
            session.add(Market(**values))
        session.commit()
    engine.dispose()


def check_browser(base_url: str) -> None:
    executable = os.environ.get("RITTERRADAR_BROWSER_EXECUTABLE") or shutil.which("chromium")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable)
        try:
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route(
                "**/*",
                lambda route: (
                    route.continue_()
                    if route.request.url.startswith(base_url + "/")
                    else route.abort()
                ),
            )
            page.clock.install(time=datetime(2026, 9, 20, 12, tzinfo=UTC))
            page.goto(base_url, wait_until="domcontentloaded")
            page.locator("#month-to").select_option("2026-09")
            page.locator("#btn-apply").click()
            expect(page.locator("#preview-count")).to_have_text("4")
            page.locator("#preview-toggle").click()
            expect(page.locator(".preview-row")).to_have_count(4)
            expect(page.locator("#preview-list")).to_contain_text("Monatsgrenze")
            expect(page.locator("#preview-list")).not_to_contain_text("ABGESAGT")
            expect(page.locator("#preview-list")).not_to_contain_text("Römerfest")
            expect(page.locator("#preview-list")).not_to_contain_text("Sense")
            expect(page.locator("#preview-list")).not_to_contain_text("Kloster 2026")
            expect(page.locator(".rr-marker")).to_have_count(4)

            # Distinct events sharing a postcode survive; clearing types shows none.
            for checkbox in page.locator("#type-filters input").all():
                checkbox.uncheck()
            page.locator("#btn-apply").click()
            expect(page.locator("#preview-count")).to_have_text("0")
            expect(page.locator(".rr-marker")).to_have_count(0)
            page.locator('#type-filters input[value="viking"]').check()
            page.locator("#btn-apply").click()
            expect(page.locator("#preview-count")).to_have_text("1")
            expect(page.locator("#preview-list")).to_contain_text("Wikingerfest am See")

            page.locator("#month-from").select_option("2026-10")
            page.locator("#btn-apply").click()
            expect(page.locator("#preview-count")).to_have_text("0")
            assert not errors, errors
        finally:
            browser.close()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ritterradar-browser-") as temporary:
        work = Path(temporary)
        db_path = work / "test.db"
        seed_database(db_path)
        sources = work / "sources.yaml"
        sources.write_text("sources: []\n")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        base_url = f"http://127.0.0.1:{port}"
        env = os.environ.copy()
        env.update(
            RITTERRADAR_DB_PATH=str(db_path),
            RITTERRADAR_SOURCES_FILE=str(sources),
            RITTERRADAR_WORKERS="0",
            RITTERRADAR_HOST="127.0.0.1",
            RITTERRADAR_PORT=str(port),
        )
        with (work / "server.log").open("w+") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "ritterradar.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Browser fixture server exited early")
                    try:
                        with urllib.request.urlopen(base_url + "/health", timeout=1) as response:
                            assert json.load(response) == {"status": "ok"}
                        break
                    except urllib.error.URLError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Browser fixture server failed to start")
                check_browser(base_url)
            except Exception:
                log.seek(0)
                print(log.read(), file=sys.stderr)
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    print("Browser regression tests passed (month overlap, scope, duplicates, category filters).")


if __name__ == "__main__":
    main()
