FO:     Stopping reloader process [640275]
❯ ./scripts/start_dev.sh
==> Starting RitterRadar [DEV] at http://127.0.0.1:13370
==> Auto-reload enabled — file changes restart the server automatically.
==> Press Ctrl+C to stop.
INFO:     Will watch for changes in these directories: ['/home/mpetrick/repos/RitterRadar/src']
INFO:     Uvicorn running on http://127.0.0.1:13370 (Press CTRL+C to quit)
INFO:     Started reloader process [665957] using WatchFiles
INFO:     Started server process [665962]
INFO:     Waiting for application startup.
21:18:53 INFO     ritterradar.main — RitterRadar starting up…
21:18:53 INFO     ritterradar.main — Database tables ready
21:18:53 INFO     ritterradar.crawler.queue — CrawlQueue: sources seeded from config/sources.yaml
21:18:53 INFO     ritterradar.crawler.queue — CrawlQueue: enqueued 3 jobs
21:18:53 INFO     ritterradar.crawler.queue — CrawlQueue: started 3 workers
21:18:53 INFO     ritterradar.main — Crawler queue started
21:18:53 INFO     ritterradar.crawler.worker — Worker 0: crawling Spectaculum.de
21:18:53 INFO     ritterradar.crawler.worker — Worker 1: crawling Mittelalterkalender.info
21:18:53 INFO     ritterradar.crawler.worker — Worker 2: crawling Vehi Mercatus Marktkalender
INFO:     Application startup complete.
21:18:54 INFO     httpx — HTTP Request: GET https://www.mittelalterkalender.info/mittelaltermarkt/mittelalterfeste-2026-nach-datum.php "HTTP/1.1 200 OK"
21:18:54 INFO     ritterradar.crawler.adapters.mittelalterkalender_info — Mittelalterkalender.info: 808 rows found for 2026
21:18:55 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&land=Deutschland&jahr=2026&seite=1 "HTTP/1.1 301 Moved Permanently"
21:18:55 INFO     httpx — HTTP Request: GET https://www.spectaculum.de "HTTP/1.1 200 OK"
21:18:55 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&jahr=2026&land=Deutschland&seite=1 "HTTP/1.1 200 OK"
21:18:55 INFO     ritterradar.crawler.adapters.spectaculum — Spectaculum.de (MPS): scraped 9 events
21:18:56 INFO     ritterradar.crawler.worker — Worker 0: Spectaculum.de done — 9 found, 0 inserted, 9 updated
21:18:56 INFO     httpx — HTTP Request: GET https://www.mittelalterkalender.info/mittelaltermarkt/mittelalterfeste-2027-nach-datum.php "HTTP/1.1 302 Found"
21:18:56 INFO     httpx — HTTP Request: GET https://www.mittelalterkalender.info/mittelaltermarkt/fehlerseite.php "HTTP/1.1 200 OK"
21:18:56 INFO     ritterradar.crawler.adapters.mittelalterkalender_info — Mittelalterkalender.info: 0 rows found for 2027
21:18:56 INFO     ritterradar.crawler.adapters.mittelalterkalender_info — Mittelalterkalender.info: scraped 806 events total
21:18:57 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&land=Deutschland&jahr=2026&seite=2 "HTTP/1.1 301 Moved Permanently"
21:18:57 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&jahr=2026&land=Deutschland&seite=2 "HTTP/1.1 200 OK"
21:18:58 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&land=Deutschland&jahr=2026&seite=3 "HTTP/1.1 301 Moved Permanently"
21:18:59 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&jahr=2026&land=Deutschland&seite=3 "HTTP/1.1 200 OK"
21:19:00 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&land=Deutschland&jahr=2026&seite=4 "HTTP/1.1 301 Moved Permanently"
21:19:00 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&jahr=2026&land=Deutschland&seite=4 "HTTP/1.1 200 OK"
21:19:01 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&land=Deutschland&jahr=2026&seite=5 "HTTP/1.1 301 Moved Permanently"
INFO:     127.0.0.1:55030 - "GET / HTTP/1.1" 200 OK
21:19:01 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&jahr=2026&land=Deutschland&seite=5 "HTTP/1.1 200 OK"
INFO:     127.0.0.1:55030 - "GET /static/css/ritterradar.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:55032 - "GET /static/js/map.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:55048 - "GET /static/js/detail-panel.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:55044 - "GET /static/js/filters.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:55054 - "GET /static/js/crawler-status.js HTTP/1.1" 304 Not Modified
21:19:02 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&land=Deutschland&jahr=2026&seite=6 "HTTP/1.1 301 Moved Permanently"
21:19:02 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&jahr=2026&land=Deutschland&seite=6 "HTTP/1.1 200 OK"
21:19:02 INFO     ritterradar.crawler.adapters.vehi_mercatus — Vehi Mercatus Marktkalender: scraped 287 events so far (after year 2026)
21:19:04 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&land=Deutschland&jahr=2027&seite=1 "HTTP/1.1 301 Moved Permanently"
21:19:04 INFO     httpx — HTTP Request: GET https://vehi-mercatus.de/marktkalender/?ansicht=liste&jahr=2027&land=Deutschland&seite=1 "HTTP/1.1 200 OK"
21:19:04 INFO     ritterradar.crawler.adapters.vehi_mercatus — Vehi Mercatus Marktkalender: scraped 287 events so far (after year 2027)
21:19:04 INFO     ritterradar.crawler.adapters.vehi_mercatus — Vehi Mercatus Marktkalender: scraped 287 events total
