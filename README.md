# WS Project: Formula 1 Knowledge Graph

Web information system for the WS practical assignment, built with Django, RDF, GraphDB, and SPARQL around the Formula 1 World Championship dataset.

## Dataset

- Source: https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020
- Raw CSVs are stored in `data/raw/`
- Add the Kaggle CSV files manually to `data/raw/`

## Stack

- Python 3
- Django
- RDF via `rdflib`
- GraphDB as triplestore
- SPARQL via `SPARQLWrapper`

## Repository layout

- `championship/`: Django app for the F1 domain
- `data/raw/`: Kaggle CSV files after extraction
- `data/rdf/`: generated RDF files for GraphDB import
- `docs/`: setup notes, issue drafts, and report-oriented material
- `queries/`: sample SPARQL queries and updates
- `scripts/`: data transformation utilities
- `templates/`: shared Django templates

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the environment template:

```bash
cp .env.example .env
```

4. Place the Kaggle CSV files into `data/raw/`

5. Generate RDF from the raw CSV files:

```bash
./scripts/convert_csv_to_rdf.sh
```

6. Import the generated RDF into GraphDB:

```bash
./scripts/load_rdf_to_graphdb.sh
```

7. If you only want the development server, run:

```bash
./scripts/run_webserver.sh
```

## Current baseline

This repository currently provides:

- Django project scaffolding
- environment-driven GraphDB configuration
- a starter GraphDB client service
- runnable helper scripts for RDF conversion, GraphDB loading, and the Django dev server
- a CSV-to-RDF pipeline adapted to the official Kaggle Formula 1 CSV schema
- an empty `data/raw/` directory for manually added Kaggle CSV files
- sample SPARQL query files
- drafted GitHub issues in `docs/github-issues-draft.md`

## Delivery notes

- No Docker or containers are used.
- `requirements.txt` is the only dependency file.
- SQLite is used only for Django's local metadata. Domain data lives in GraphDB.

## Helper scripts

- `./scripts/convert_csv_to_rdf.sh`
- `./scripts/load_rdf_to_graphdb.sh`
- `./scripts/run_webserver.sh`
