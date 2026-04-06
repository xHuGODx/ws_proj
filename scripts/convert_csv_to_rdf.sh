#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

python scripts/csv_to_rdf.py \
  --input-dir "${1:-data/raw}" \
  --output "${2:-data/rdf/formula1.n3}"
