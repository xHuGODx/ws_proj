#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

RDF_FILE="${1:-data/rdf/formula1.ttl}"
GRAPHDB_BASE_URL="${GRAPHDB_BASE_URL:-http://localhost:7200}"
GRAPHDB_REPOSITORY="${GRAPHDB_REPOSITORY:-ws-formula1}"
GRAPHDB_GRAPH_URI="${GRAPHDB_GRAPH_URI:-}"

if [[ ! -f "$RDF_FILE" ]]; then
  echo "RDF file not found: $RDF_FILE" >&2
  echo "Run ./scripts/convert_csv_to_rdf.sh first." >&2
  exit 1
fi

ENDPOINT="${GRAPHDB_BASE_URL%/}/repositories/${GRAPHDB_REPOSITORY}/statements"
if [[ -n "$GRAPHDB_GRAPH_URI" ]]; then
  CONTEXT="$(python3 - <<'PY'
import os
import urllib.parse
print(urllib.parse.quote(f"<{os.environ['GRAPHDB_GRAPH_URI']}>", safe=""))
PY
)"
  ENDPOINT="${ENDPOINT}?context=${CONTEXT}"
fi

CURL_ARGS=(
  --fail
  --show-error
  --silent
  -X POST
  -H "Content-Type: text/turtle"
  --data-binary "@${RDF_FILE}"
)

if [[ -n "${GRAPHDB_USERNAME:-}" && -n "${GRAPHDB_PASSWORD:-}" ]]; then
  CURL_ARGS+=(-u "${GRAPHDB_USERNAME}:${GRAPHDB_PASSWORD}")
fi

echo "Loading ${RDF_FILE} into ${ENDPOINT}"
curl "${CURL_ARGS[@]}" "$ENDPOINT"
echo
echo "GraphDB load completed."

