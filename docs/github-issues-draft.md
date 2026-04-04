# GitHub Issue Drafts

Direct GitHub issue creation is not available from this session because there is no usable GitHub API credential exposed here. The issue set below is ready to create in `xHuGODx/ws_proj`.

## Issue 1: Model the Formula 1 domain for RDF conversion

Define the URI strategy, namespaces, classes, and core predicates for seasons, races, circuits, drivers, constructors, results, and status values.

### Acceptance criteria

- Decide and document the base namespace.
- Define which CSV files are in scope for v1.
- Document entity relationships needed by the UI.

## Issue 2: Complete the CSV to RDF transformation pipeline

Extend `scripts/csv_to_rdf.py` to cover all selected CSV files from the Kaggle dataset and produce a clean RDF export for GraphDB import.

### Acceptance criteria

- Parse all agreed source CSV files.
- Emit RDF in a single reproducible export.
- Validate output size and basic triple counts.

## Issue 3: Prepare GraphDB repository and import workflow

Document the GraphDB repository configuration and make the import process reproducible.

### Acceptance criteria

- Define the repository name and graph URI.
- Document import steps.
- Verify that the generated RDF loads without schema or datatype issues.

## Issue 4: Build SPARQL query layer for read operations

Implement the query service used by Django views for listing and detail pages.

### Acceptance criteria

- Add reusable query helpers.
- Cover seasons, races, drivers, and constructors.
- Handle empty and unavailable GraphDB responses gracefully.

## Issue 5: Implement SPARQL update operations

Add at least one clear write path to satisfy the assignment's data modification requirement.

### Acceptance criteria

- Define a safe update scenario.
- Implement the SPARQL update.
- Surface success and failure clearly in the UI.

## Issue 6: Build the main Django UI flows

Create the core user-facing pages around the F1 knowledge graph.

### Acceptance criteria

- Home dashboard
- Entity listing pages
- Entity detail pages
- Search or filtering support

## Issue 7: Add tests for the baseline application and data pipeline

Cover the most important setup and behavior paths before feature growth.

### Acceptance criteria

- Django smoke tests
- GraphDB client behavior tests with mocked responses
- CSV-to-RDF script tests against small fixture data

## Issue 8: Write the final report and execution guide

Prepare the report sections required by the assignment and align them with the implemented system.

### Acceptance criteria

- Follow the assignment section order.
- Include data sources and transformation notes.
- Include SPARQL operations and execution steps.

