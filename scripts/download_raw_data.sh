#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

DATASET_SLUG="${1:-rohanrao/formula-1-world-championship-1950-2020}"

if ! command -v kaggle >/dev/null 2>&1; then
  echo "The Kaggle CLI is required." >&2
  echo "Install it with: python3 -m pip install kaggle" >&2
  exit 1
fi

if [[ ! -f "${KAGGLE_CONFIG_DIR:-$HOME/.kaggle}/kaggle.json" ]]; then
  echo "Kaggle credentials not found." >&2
  echo "Run 'kaggle config set -n path -v \$HOME/.kaggle' if needed and place kaggle.json there." >&2
  exit 1
fi

rm -rf "$ROOT_DIR/data/raw"
mkdir -p "$ROOT_DIR/data/raw"
kaggle datasets download \
  -d "$DATASET_SLUG" \
  -p "$TMP_DIR"
unzip -o "$TMP_DIR"/*.zip -d "$ROOT_DIR/data/raw" >/dev/null

find "$ROOT_DIR/data/raw" -maxdepth 1 -type f ! -name '*.csv' -delete

echo "Downloaded Kaggle dataset '$DATASET_SLUG' into $ROOT_DIR/data/raw"
