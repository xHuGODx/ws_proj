# WS Project: Formula 1 Knowledge Graph

Web information system for the WS practical assignment, built with Django, RDF, GraphDB, and SPARQL around the Formula 1 World Championship dataset.

## Dataset

- Source: https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020
- Expected local placement after download and extraction:
  - `data/raw/`

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

4. Apply Django migrations:

```bash
python manage.py migrate
```

5. Generate RDF from the Kaggle CSV files:

```bash
python scripts/csv_to_rdf.py --input-dir data/raw --output data/rdf/formula1.ttl
```

6. Import the generated RDF into GraphDB.
7. Run the development server:

```bash
python manage.py runserver
```

## Current baseline

This repository currently provides:

- Django project scaffolding
- environment-driven GraphDB configuration
- a starter GraphDB client service
- a first-pass CSV-to-RDF pipeline for core Formula 1 entities
- sample SPARQL query files
- drafted GitHub issues in `docs/github-issues-draft.md`

## Delivery notes

- No Docker or containers are used.
- `requirements.txt` is the only dependency file.
- SQLite is used only for Django's local metadata. Domain data lives in GraphDB.

