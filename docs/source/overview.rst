Overview
========

RitterRadar consists of two cooperating subsystems:

**Crawler subsystem**
  Background adapter-based web scrapers that harvest event data from
  configured sources and persist it in SQLite via SQLModel/SQLAlchemy.

**UI subsystem**
  A FastAPI-powered local web application with a Leaflet/OpenStreetMap
  frontend rendered in medieval visual style.

Technology stack
----------------

+------------------+-------------------------------+
| Layer            | Technology                    |
+==================+===============================+
| Web framework    | FastAPI 0.138                 |
+------------------+-------------------------------+
| ORM              | SQLModel 0.0.39               |
+------------------+-------------------------------+
| Database         | SQLite (via SQLAlchemy 2.x)   |
+------------------+-------------------------------+
| HTTP client      | httpx 0.28                    |
+------------------+-------------------------------+
| HTML parsing     | BeautifulSoup4 + lxml         |
+------------------+-------------------------------+
| Geocoding        | geopy Nominatim (cached)      |
+------------------+-------------------------------+
| Map              | Leaflet 1.9 + OpenStreetMap   |
+------------------+-------------------------------+
| Migrations       | Alembic 1.18                  |
+------------------+-------------------------------+
| Configuration    | pydantic-settings 2.x         |
+------------------+-------------------------------+
