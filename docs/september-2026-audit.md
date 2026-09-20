# September 2026 crawler and application audit

Checked on 19–20 September 2026 against the local database and live sources.
The database was backed up before running crawlers. User settings and hidden
flags were preserved. September means any event overlapping 1–30 September,
including an event starting before the month.

## Result

All nine enabled crawlers completed without a failed job. Their latest raw
discovery counts were:

| Source | Records discovered |
| --- | ---: |
| Spectaculum.de | 8 |
| Mittelalterkalender.info | 943 |
| Vehi Mercatus | 431 |
| Pfalzis Marktkalendarium | 181 |
| Mittelaltermarkt.online | 823 |
| Taterman.at | 43 |
| Trollfelsen.de | 9 |
| Fyndling.de | 1330 |
| Mittelaltermarkt-info.de | 324 |

These are source records across the crawler's year range, not unique events.
Sources can update their calendars between runs.

For September, the database contained 484 non-hidden overlapping records.
The API returned 443 eligible current records after scope and date-correction
checks. With all five event categories selected and no distance limit, the
browser displayed 257 listings: 251 map markers and six unmapped listings.
Eleven displayed listings had approximate coordinates. Names, dates and venue
precision still vary between sources; display deduplication is heuristic.

## Application defects fixed

| Severity | Finding | Fix and regression coverage |
| --- | --- | --- |
| High | Month filtering dropped ongoing events that started earlier. | Inclusive interval overlap; API and browser boundary fixtures. |
| High | Cancelled events, Roman/Stone Age activities and general museum programmes appeared as medieval events. | Shared ingestion/display scope rules, applied to existing records too; positive and negative title fixtures. |
| High | Clearing every category restored all events. | Empty category selection clears map and preview; browser regression. |
| Medium | Postcode-only display deduplication hid unrelated events and could select an unmapped duplicate. | Require related titles and compatible countries; prefer reliable coordinates; browser fixture with distinct same-postcode events. |
| Medium | Retro MPS branding became part of a city, Dutch postcode letters became part of a city, and Swiss place/venue labels remained unresolvable. | Adapter parsing and live re-crawl; Borken, Arcen and Lenzburg now have coordinates. |
| Medium | Re-crawls retained incorrect location fields and reused coordinates after an address changed. | Repair same-source nonempty fields, invalidate changed-address coordinates, retain cross-source safeguards; persistence tests. |
| Medium | REST-feed foreign country names could fall back to Germany. | Preserve the supported country names and ISO codes; parser fixtures. |
| Medium | Changed iCal dates left two listings for the same event. | Update overlapping dates for Taterman's canonical event URLs; suppress historical duplicates without deleting them; retain disjoint recurring dates. |
| Medium | Invalid source ranges entered the database. | Reject reversed Pfalzis dates on ingestion; exclude existing invalid ranges from results. |
| Low | The same bad address triggered repeated geocoding attempts during a crawl. | Reuse results, including failures, within that crawl; retry on later crawls. |
| Low | Long date labels and an expanding preview overlapped adjacent content. | Wrap date labels and clip animated panel contents; browser width assertion reproduced the failure before the fix. |

The Taterman feed currently reports Judenburg on 25–27 September. Its older
26–27 September record is now suppressed. The organiser's
[Borken page](https://www.spectaculum.de/termine/borken/) confirms that “Retro MPS”
is festival branding and gives the event's Borken address.

## Remaining source-data limitations

Six September records still lack a defensible location:

| Record | Source | Issue |
| --- | --- | --- |
| Mittelaltermarkt Schallaburg | Taterman.at | No location in the feed record. |
| 1200 Jahrfeier Mittelaltermarkt | Pfalzis | Older stored row has commentary instead of a place and is no longer in the current source output. |
| Retro MPS Borken | Trollfelsen.de | No address in this source record; other sources do map the event. |
| Uelzener Hansefest | Mittelaltermarkt-info.de | Source still says `29595 Uelzen`; geocoding rejects the mismatch. |
| Mittelalterspektakel Biel/Niedau | Fyndling.de | Source gives `Neues OK` as the place. New ingestion rejects this placeholder; the historical row remains. |
| Ritterfest am Kloster | Fyndling.de | Source says `Jericho`; matching listings elsewhere say Jerichow. No speculative correction is made. |

The stored Trollfelsen title “Mittelalterfestival Sigmaringen 2025” also conflicts
with its September 2026 date and is absent from the current source output.
Two older reversed 2027 date ranges remain in storage but are excluded from
results. Absence from a later source page is not treated as proof of cancellation.

Scope is restricted to medieval, Renaissance, Viking, fantasy and themed
Christmas events. Broad-directory titles without evidence of these themes are
omitted; that can also omit legitimate but ambiguously named events. Excluded
records remain available in the database for later investigation.

## Reproduce

```bash
python scripts/audit_month.py --month 2026-09
pytest
python scripts/browser_test.py
```

The audit opens SQLite read-only and reports excluded records, uncertain/missing
coordinates, title/year mismatches, source jobs and date conflicts. The browser
test uses an isolated database and the real FastAPI server, freezes the browser
date, and blocks all external requests. It is part of CI on Python 3.14.

Validation includes lint, formatting, strict typing, tests with more than 98%
coverage on Python 3.12–3.14, the offline browser test, live local browser checks,
wheel/sdist metadata checks, and a Docker build with HTTP/static-asset smoke tests.

## Release monitored

[v0.0.87](https://github.com/marcelpetrick/RitterRadar/releases/tag/v0.0.87) is the
public dependency-maintenance release. Its CI, release assets, and amd64/arm64
Docker publication completed successfully. These audit fixes are versions 0.0.88–0.0.89
and do not alter that release tag.
