# F1 Knowledge Graph Explorer

A semantic web application that exposes the Formula 1 World Championship (1950–2024) as a queryable RDF knowledge graph, built with Django, GraphDB, and SPARQL.

**Authors:** Rodrigo Abreu (113626), Hugo Ribeiro — Web Semantics, MEI 2025/2026

---

## What It Is

The dataset (≈ 150 000+ triples) is modelled in RDF using a custom `f1:` vocabulary and stored in GraphDB. The Django front-end issues SPARQL queries at runtime — no relational database is used for domain data. An admin panel (authenticated via Django sessions) supports full CRUD operations on all core entities via SPARQL UPDATE.

---

## Main Pages

| URL | Page | Description |
|-----|------|-------------|
| `/` | Home | Hero stats (drivers, constructors, circuits, races, seasons) sourced live from GraphDB |
| `/drivers/` | Drivers | Card grid of all drivers (nationality, flag, constructor image) |
| `/drivers/<id>/` | Driver Detail | Career stats, wins, podiums, race-by-race results |
| `/constructors/` | Constructors | Card grid with podium image for Ferrari, McLaren, Red Bull, Mercedes |
| `/constructors/<id>/` | Constructor Detail | Season-by-season stats, top drivers, race results |
| `/circuits/` | Circuits | All circuits with country and race count |
| `/circuits/<ref>/` | Circuit Detail | Full race history at that circuit, fastest laps |
| `/races/` | Races | All races grouped or listed, filterable by season |
| `/races/<id>/` | Race Detail | Full results table (position, driver, constructor, laps, time, status), pit stops, qualifying |
| `/seasons/` | Seasons | 16-season card grid with race count, top winner per season |
| `/seasons/<year>/` | Season Detail | Race calendar, driver standings, constructor standings |

---

## RDF Knowledge Graph

### Namespace

| Prefix | IRI |
|--------|-----|
| `f1:` | `http://example.org/ontology/formula1#` |
| `f1r:` | `http://example.org/resource/` (entity URIs) |
| `rdfs:` | `http://www.w3.org/2000/01/rdf-schema#` |
| `xsd:` | `http://www.w3.org/2001/XMLSchema#` |

### URI Patterns

```
f1r:driver/{driverId}          e.g. f1r:driver/1
f1r:constructor/{constructorId}
f1r:circuit/{circuitRef}       e.g. f1r:circuit/monza
f1r:race/{raceId}
f1r:result/{resultId}
f1r:qualify/{qualifyId}
f1r:pitstop/{raceId}/{driverId}/{stop}
f1r:season/{year}
```

### CSV → RDF Class Mapping

| CSV file | Entity class | Anchor property |
|----------|-------------|-----------------|
| `drivers.csv` | Driver | `f1:driverId` |
| `constructors.csv` | Constructor | `f1:constructorId` |
| `circuits.csv` | Circuit | `f1:circuitRef` |
| `races.csv` | Race | `f1:round` |
| `results.csv` | Result | `f1:resultId` |
| `qualifying.csv` | QualifyResult | `f1:qualifyId` |
| `pit_stops.csv` | PitStop | `f1:stop` |
| `seasons.csv` | Season | (year literal) |

The conversion script is at `scripts/csv_to_rdf.py`. It reads from `data/raw/`, produces `data/rdf/formula1.nt` (N-Triples), and logs skipped rows.

---

## How to Run

### Prerequisites

- Python 3.11+
- GraphDB Free running locally (default: `http://localhost:7200`)
- A GraphDB repository named `formula1`

### Steps

```bash
# 1. Clone and create virtual environment
python -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set GRAPHDB_ENDPOINT, GRAPHDB_REPO, SECRET_KEY

# 4. Build the RDF graph (requires CSV files in data/raw/)
python scripts/csv_to_rdf.py
# Then import data/rdf/formula1.nt into GraphDB via the workbench UI
# or: curl -X POST ... (see GraphDB REST import docs)

# 5. Set up Django (SQLite — auth only)
python manage.py migrate
python manage.py createsuperuser   # mark is_staff=True for admin panel access

# 6. Start the dev server
python manage.py runserver
```

Open `http://localhost:8000`.

Admin panel: `http://localhost:8000/admin-panel/login/`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Django 4.x |
| Triplestore | GraphDB Free (Ontotext) |
| SPARQL client | SPARQLWrapper |
| RDF serialisation | rdflib (N-Triples output) |
| Auth / sessions | Django `contrib.auth` (SQLite) |
| Front-end | Vanilla HTML/CSS (dark + light theme) |
| Fonts | Barlow Condensed (Google Fonts) |
| Report | LaTeX (`report/report.tex`) — build with `cd report && ./build.sh` |

---

## Report

The project report is at `report/report.tex`. To build the PDF:

```bash
cd report
./build.sh      # requires pdflatex (texlive-latex-extra)
```

Output: `report/report.pdf`
