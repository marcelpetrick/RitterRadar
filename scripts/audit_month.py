#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only month audit: python scripts/audit_month.py --month 2026-09.

Outputs JSON for every excluded, unmapped, uncertain, or conflicting record.
Raw record counts include cross-source duplicates; they are not event counts.
"""

import argparse
import calendar
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from ritterradar.config import get_settings
from ritterradar.event_scope import exclusion_reason
from ritterradar.market_identity import current_source_records
from ritterradar.models.market import Market


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", default=date.today().strftime("%Y-%m"))
    parser.add_argument("--db", type=Path, default=get_settings().db_path)
    args = parser.parse_args()
    first = date.fromisoformat(args.month + "-01")
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    with sqlite3.connect(args.db.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        all_rows = [dict(row) for row in db.execute("SELECT * FROM market")]
        current_ids = {
            row.id
            for row in current_source_records([Market.model_validate(row) for row in all_rows])
        }
        rows = [
            row
            for row in all_rows
            if not row["hidden"]
            and row["start_date"] <= last.isoformat()
            and row["end_date"] >= first.isoformat()
        ]
        invalid = [
            dict(row)
            for row in db.execute(
                "SELECT id, name, start_date, end_date, source_name FROM market "
                "WHERE end_date < start_date"
            )
        ]
        jobs = [
            dict(row)
            for row in db.execute(
                "SELECT source_name, status, events_discovered, events_inserted, error_message "
                "FROM crawl_job WHERE id IN (SELECT MAX(id) FROM crawl_job GROUP BY source_id) "
                "AND source_id IN (SELECT id FROM source WHERE enabled = 1)"
            )
        ]
    fields = (
        "id",
        "name",
        "start_date",
        "end_date",
        "city",
        "postal_code",
        "country",
        "source_name",
        "source_url",
    )

    def brief(row):
        return {field: row[field] for field in fields}

    eligible = []
    excluded = []
    for row in rows:
        reason = exclusion_reason(row["name"], row["source_name"])
        if row["id"] not in current_ids:
            reason = "superseded source dates"
        if row["end_date"] < row["start_date"]:
            reason = "invalid date range"
        if reason:
            excluded.append({**brief(row), "reason": reason})
        else:
            eligible.append(row)
    identities = defaultdict(list)
    for row in eligible:
        identities[
            (
                row["source_name"],
                row["source_url"],
                row["name"],
                row["country"],
                row["postal_code"] or row["city"],
            )
        ].append(row)
    conflicts = []
    for group in identities.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if (a["start_date"], a["end_date"]) != (b["start_date"], b["end_date"]) and (
                    a["start_date"] <= b["end_date"] and b["start_date"] <= a["end_date"]
                ):
                    conflicts.append([brief(a), brief(b)])
    result = {
        "month": args.month,
        "raw_records": len(rows),
        "eligible_records": len(eligible),
        "by_source": dict(Counter(row["source_name"] for row in eligible)),
        "latest_jobs": jobs,
        "excluded": excluded,
        "unmapped": [brief(row) for row in eligible if row["latitude"] is None],
        "uncertain": [brief(row) for row in eligible if row["geocode_uncertain"]],
        "invalid_ranges_all_years": invalid,
        "overlapping_same_source_dates": conflicts,
        "title_year_mismatches": [
            brief(row)
            for row in eligible
            if any(int(y) != first.year for y in re.findall(r"\b20\d{2}\b", row["name"]))
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
