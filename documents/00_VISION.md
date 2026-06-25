## data from several conversations

* make it GPLv3
* prepare a gitignore
* never mention the use of ai or claude code for commit message; make them with conventional commit message format. and details.
* sign off all the commits.
* use semver. single source of truth. we start with 0.0.0. increase by one with each commit. unless said so. single source of truth.
* test coverage 90% percent as goal; add linters and formatters , add sphinx and make sure all the interfaces are documented, robust code, etc., c4 architecture documentation
* do from time to time review cycles. mark downt he findings and rate them with severity high, medium, low. fix the high ones immediately. others when fitting.
* do loops until everything is developed.
* pin used dependencies - most recent and stable releases, focus on python stuff and shell scripts
* plan first, then implement. do loops.

----------------

this is what i defined so far.

ChatGPT

Okay, I want to create a new project. It should be something, I mean, it should be Python-based and then create maybe via Flask or Django or whatever and send kind of a page locally. So it will have two components. One is something like a web crawler, I mean, gathering data from the internet, and the other one will be that it displays a map, maybe using OpenStreetMap, I mean, for the front-end. And on that map, I mean, you can see then all those medieval market things that we have found, I mean, for the current month and all future months for the next year. And then you have something where you have a selection of a range of, where you can say which month should be shown. I mean, that you have something like a slider for current months and the next 12 months or just the current months and so on. And then some things that it also does some limitation based on the distance, that I mean, you set some home address and then it does some calculation, I mean, just really roughly directly on the map of the home position to set medieval market position. So the web crawling part should also be something which is running then transparently in the background. We will provide it to start some kind of list of pages to check, and then we will also create some kind of crawling adapter for each page. I mean, maybe something like BeautifulSoup could help. So the goal is, I mean, that you start the application and then it will run for a while and then it will search through all those pages, scrapes the data, put it maybe into some kind of local database, SQLite and whatever. And then the front-end, when it gets new data inside the database, maybe it does a query each second, it will display based on the currently selected time range and on the location, I mean, on the map, those things. And when you do a mouse move over, there's a mouse, I mean, you will see on the map then what kind of market this is. And when you click on it, I mean, then you get some kind of, not pop-up window, but some better overview window, which is showing you the market type from which to which day exactly and how it's named and also the original information. The surface, I mean, the front end should really be pretty and be beautiful. I mean, we have 2026, it should not be old as and ugly. So use color, so wherever possible, maybe also with a medieval theme. I said we will focus on German medieval markets. So one part of the development task is also to create a list of web pages which have medieval markets. I mean, use Google or DuckDuckGo to find some. I mean, there are several overview pages. And then for each of those pages, create some kind of web crawling agent, which is, I mean, not aggressively crawling, but also does some back off. I mean, with some random interval between zero and two seconds until it goes to the next page, and then also how to scan those results. I mean, you should extract, I mean, for the markets, always the name of the markets and the date from when to when. Then also if there's some program, then what it is, and also then the address. I mean, of course, the postlet site address is the most important part. And this should all be then inserted via, I mean, the Django or Flask or whatever backend into the database. And when the database has new data, it will also display it on the map. And I said the map is zoom and pinnable, and the users can also filter it by the time range I want to check. And it should also, I mean, really use OpenStreetMap maybe for the map data, and that you have some nice user interface where you can then really figure out where to go next. And those markets should be, I mean, marked by some nice, maybe half-transparent dot. So make it really pretty and fancy for 2026. It should be also robust code for the crawling as well as for the other things. If the crawling breaks, it should not rip down the whole application. So maybe separate it into some processes and write extensive documentation, like a readme of how to run and configure it, and it should be GPLv3 code. Ja.


--- write this down and think about fancy names for the repo. geeky. twenty ideas be creative. then also tell me ten qustions, which i could answer to improve the quality of this sw-development project.

Here’s a cleaned-up project brief plus repo-name ideas and quality-improving questions.
Project Brief: German Medieval Market Finder
Goal

Build a Python-based local web application that discovers, stores, filters, and displays German medieval markets on an interactive OpenStreetMap-based map.

The app should have two main components:

    Crawler / data ingestion

        Scrapes configured websites for medieval market listings.

        Extracts market name, date range, address/location, program details, source URL, and original text.

        Stores normalized results in a local SQLite database.

        Runs in the background without blocking or crashing the web UI.

        Uses polite crawling with retry logic, backoff, and random delays between requests.

    Interactive web UI

        Displays discovered markets on a beautiful medieval-themed map.

        Uses OpenStreetMap, likely via Leaflet.

        Allows filtering by month range: current month through the next 12 months.

        Allows filtering by distance from a configured home address.

        Shows markets as attractive semi-transparent markers.

        Shows hover previews and richer click details.

        Updates automatically when new crawler results arrive.

Suggested Tech Stack

    Backend: Flask or Django

    Database: SQLite

    ORM: SQLAlchemy or Django ORM

    Scraping: requests, BeautifulSoup, optional Playwright for JavaScript-heavy sites

    Map UI: Leaflet + OpenStreetMap

    Geocoding: Nominatim / OpenStreetMap-compatible geocoder with caching

    Background Jobs: APScheduler, Celery, RQ, or separate worker process

    Frontend: HTML, CSS, JavaScript, possibly HTMX or Alpine.js

    License: GPLv3

Core Features
Crawler

    Configurable list of source pages.

    Adapter-based scraper architecture:

        One adapter per supported website.

        Each adapter knows how to parse that website’s structure.

    Polite crawling:

        User-agent string.

        Random delay between 0 and 2 seconds.

        Retry with exponential backoff.

        Failure isolation per source.

    Robust error handling:

        One broken crawler must not crash the whole app.

        Errors should be logged.

        Failed sources should be visible in an admin/debug view.

    Duplicate detection:

        Based on name, date, location, and source URL.

    Store raw original source text for traceability.

Data Model

Suggested entities:

    Market

        id

        name

        market_type

        start_date

        end_date

        address

        city

        postal_code

        country

        latitude

        longitude

        program_text

        original_text

        source_url

        source_name

        created_at

        updated_at

        confidence_score

    Source

        id

        name

        base_url

        adapter_name

        enabled

        last_crawled_at

        last_success_at

        last_error

UI

    Interactive OpenStreetMap map.

    Beautiful 2026-quality medieval-inspired design:

        parchment textures

        dark wood / iron accents

        gold highlights

        shield, banner, or wax-seal visual motifs

    Month range slider:

        Current month

        Next 12 months

        Custom range

    Distance filter:

        Home address configuration

        Radius slider

        Rough straight-line distance calculation

    Marker behavior:

        Semi-transparent dots or themed pins.

        Hover shows quick preview.

        Click opens detail panel with:

            name

            exact date range

            location/address

            program details

            original source info

            source link

    Auto-refresh:

        Frontend polls backend periodically, for example every second or every few seconds.

        Newly discovered markets appear without manual reload.

Non-Goals for First Version

    User accounts

    Cloud deployment

    Complex route planning

    Ticket purchase integration

    Perfect data extraction from every site

    Aggressive crawling

Documentation

The repository should include:

    README.md

        project purpose

        installation

        configuration

        running the app

        running the crawler

        adding new crawler adapters

        database reset/migration steps

        license notice

    docs/architecture.md

        backend structure

        crawler lifecycle

        database schema

        frontend update flow

    docs/adapter-guide.md

        how to add a new website scraper

        expected return format

        parsing examples

License

The project should be released under GPLv3.
20 geeky repo-name ideas

    Mittelmark

    RitterRadar

    MarketMancer

    YeOldeCrawler

    FeastFinder

    KnightMap

    BurgBazaar

    MedievalMatrix

    MärkteMotte

    OpenSchildMap

    TavernTrail

    QuestForMarkets

    ParchmentPins

    LanzenLocator

    MeadMap

    ChronoBazaar

    MarketGrimoire

    RabenRoute

    KettenhemdKartograph

    Drachenmarkt

My favorites: RitterRadar, MarketGrimoire, ParchmentPins, and KettenhemdKartograph.
10 questions to improve the project

    Should the first version use Flask for simplicity or Django for batteries-included admin/database tooling?

    Should crawling start automatically when the app starts, or only when manually triggered?

    Should the app store only German medieval markets, or also Renaissance fairs, fantasy festivals, Viking markets, LARP events, and Christmas markets with medieval themes?

    What should count as the “home address”: exact street address, city center, postal code, or manually selected map point?

    Should distance filtering use simple straight-line distance, or eventually real travel distance by car/public transport?

    Should geocoding happen automatically, or should uncertain addresses be flagged for manual review?

    How often should sources be re-crawled: once on startup, daily, weekly, or configurable per source?

    Should the UI support multiple saved profiles, for example “home”, “parents”, “holiday region”?

    Should crawler results require approval before appearing on the map, or appear immediately with a confidence score?

    Should the app be designed only for local use, or should future deployment on a server/NAS be considered from the beginning?


Okay, for your questions, I mean, I don't care if you use Flask or Django or FastAPI or whatever is necessary. I mean, whatever is Django or Python-based, use it. I mean, you have free choice. I mean, use something which is really, I mean, best practice in 2026, but should be Python-based. I also can learn something new. Yes, the crawling should start automatically when the app starts and also show some progress to the user, so you always know what is currently crawled and that there may be some threads or processes in parallel running. But as said, I mean, it should be stable and even if something crashes or is wrong, it should not abort immediately. Just have a queue of all the things that want to check. Yes, it should check medieval markets, Renaissance festivals, fantasy festivals, viking, LARP events, not. It's more like markets where you have something to buy and something to see. Christmas markets with medieval themes is also okay. Home address is something where the user is putting the marker. Either they enter it as some kind of geocode with latitude and longitude or a city name or a postletal. Postletal from Germany would maybe be best so that you also do some conversion of postletal and so on. If not, the user can also point it's a map and set some marker manually, but we can think about this later. Distance filtering should be a straight line distance. I mean, nothing like a travel distance. We can improve this further. Geocoding should happen automatically. Flag for manual review. Maybe it has an exclamation mark or so. Re-crawled. I mean, once every startup, I mean, you know, that you have also maybe some text file where you can enter new data if you want that more additional pages are crawled. No, there shouldn't be multiple safe profiles. There should be just one profile. The results should not require approval. Maybe the user can click on one of the results and then also say, make this considered invisible. So or filter it. It should be for local use. I mean, for right now, we will just use local use. Also something like if it is a secure domain or so, it can be, it's not so important. I mean, functionality is first and foremost important.

Good. I would choose FastAPI + SQLModel/SQLAlchemy + SQLite + background worker thread/process + Leaflet frontend.

Updated project direction:
Updated Project Decisions
Stack

Use a modern Python stack:

    Backend: FastAPI

    Database: SQLite

    ORM: SQLModel or SQLAlchemy 2.x

    Frontend: Server-rendered HTML + modern JavaScript

    Map: Leaflet with OpenStreetMap tiles

    Crawler: Adapter-based Python crawlers using requests/httpx + BeautifulSoup

    Background execution: queue-based worker system started with the app

    Realtime UI updates: polling or Server-Sent Events

    License: GPLv3

FastAPI is a good fit because it is modern, typed, lightweight, easy to document, and works well with background APIs and JSON endpoints.
Functional Scope

The app should find and display:

    medieval markets

    Renaissance festivals

    fantasy festivals with market character

    Viking markets

    medieval-themed Christmas markets

It should not focus on pure LARP events unless they also have a public market/festival character.
Startup Behavior

When the application starts:

    Load configured sources from a text/YAML/TOML config file.

    Create crawl jobs for all enabled sources.

    Start a background crawler queue.

    Crawl sources automatically.

    Continue serving the frontend while crawling is running.

    Show crawl progress in the UI.

Crawler failures must be isolated. A failed source should be marked as failed, logged, and skipped without stopping the whole application.
Crawl Queue

The crawler should use a job queue model:

    pending

    running

    completed

    failed

    skipped

Each job should store:

    source name

    source URL

    adapter name

    status

    start time

    finish time

    number of discovered events

    error message, if any

Multiple workers may run in parallel, but politely:

    random delay between requests

    retry with exponential backoff

    source-level rate limiting

    no aggressive crawling

Source Configuration

Sources should be configurable without code changes.

Example:

sources:
  - name: "Example Medieval Calendar"
    url: "https://example.org/maerkte"
    adapter: "example_calendar"
    enabled: true

Adding a new site should require:

    Add URL to the config.

    Create or select a matching adapter.

    Restart app or reload sources.

User Location

There is one local user profile.

The user can define their home position by:

    German postal code

    city name

    latitude/longitude

    later: clicking on the map

Geocoding happens automatically.

If geocoding is uncertain, the app should still store the result but mark it as uncertain.

Uncertain locations should be visually marked, for example with an exclamation icon.
Distance Filtering

Use straight-line distance only.

Distance can be calculated with the Haversine formula between:

    home coordinates

    market coordinates

No routing, driving distance, or public transport calculation in the first version.
Result Visibility

Crawler results appear immediately.

No approval workflow.

Users can hide individual markets manually.

Hidden markets should remain in the database but not appear on the default map view.
Frontend

The UI should be polished and modern:

    Leaflet map

    medieval-inspired visual design

    parchment, dark wood, gold, burgundy, iron, banner/shield motifs

    semi-transparent event markers

    hover preview

    click detail side panel

    month range slider

    distance radius slider

    crawler progress panel

    warnings for uncertain geocoding

    source/debug panel for failed crawls

Local-First Assumption

The app is designed for local use first.

Security, authentication, HTTPS, multi-user accounts, and production deployment are not first-version priorities.

Best repo name based on the refined concept: RitterRadar.

Strong alternatives: MarketGrimoire, Mittelmark, ParchmentPins, KettenhemdKartograph.


