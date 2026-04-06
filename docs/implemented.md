# Implemented Baseline

This file summarizes what has already been implemented in the repository baseline.

## Repository and project setup

- Git repository initialized with `main` as the default branch
- Remote `origin` configured to `git@github.com:xHuGODx/ws_proj.git`
- Initial project state pushed to GitHub

## Python and Django scaffolding

- Python virtual environment structure prepared for local development
- `requirements.txt` added with the project dependencies
- Django project `ws_project` created
- Django app `championship` created for the Formula 1 domain
- Root routing configured to serve the application home page

## Configuration

- `.gitignore` added for virtualenv, local database, environment files, and raw dataset files
- `.env.example` added with Django and GraphDB configuration variables
- Django settings updated to read configuration from `.env`
- Static and template directories configured
- Time zone set to `Europe/Lisbon`

## Data and RDF pipeline

- `data/raw/` created for Kaggle CSV files
- `data/rdf/` created for generated RDF output
- CSV-to-RDF script added at `scripts/csv_to_rdf.py`
- Official Kaggle raw CSV files are present in `data/raw/`
- Shell helpers added to:
  - run the Django webserver
  - convert CSV to RDF
  - load RDF into GraphDB
- Current RDF conversion targets the official Kaggle schema and emits `N3`
- Current RDF conversion covers:
  - seasons
  - circuits
  - constructors
  - drivers
  - races
  - results
  - sprint results
  - qualifying
  - pit stops
  - lap times
  - driver standings
  - constructor standings
  - constructor results
  - status

## GraphDB and SPARQL baseline

- GraphDB client service added at `championship/services/graphdb.py`
- GraphDB health check wired into the home page
- Sample SPARQL select query added in `queries/select/`
- Sample SPARQL update query added in `queries/update/`

## UI baseline

- Initial home page created for the Formula 1 knowledge graph
- Home page displays:
  - project overview
  - expected application scope
  - GraphDB connection status
  - next setup step for dataset import

## Documentation

- `README.md` added with setup and execution instructions
- `docs/report-outline.md` added to match the assignment report structure
- `docs/github-issues-draft.md` added with the project backlog and acceptance criteria

## Verification completed

- `python manage.py check`
- `python manage.py test`
- `python -m py_compile scripts/csv_to_rdf.py`
- `./scripts/convert_csv_to_rdf.sh`

## Not implemented yet

- Full dataset coverage and validated final RDF model
- GraphDB import automation
- Entity list/detail pages backed by SPARQL queries
- SPARQL update flows exposed in the UI
- Full test coverage for data transformation and GraphDB integration
- Final report content
