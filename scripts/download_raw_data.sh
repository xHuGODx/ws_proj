#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

REPO_URL="${1:-https://github.com/muharsyad/formula-one-datasets.git}"

git clone --depth 1 "$REPO_URL" "$TMP_DIR/source"
mkdir -p "$ROOT_DIR/data/raw"
cp "$TMP_DIR"/source/*.csv "$ROOT_DIR/data/raw/"

echo "Downloaded raw CSV files into $ROOT_DIR/data/raw"

