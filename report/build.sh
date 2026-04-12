#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build.sh — compile report.tex → report.pdf
#
# Runs pdflatex twice (resolves cross-references / table of contents),
# then cleans auxiliary files.
#
# Usage:
#   cd report/
#   chmod +x build.sh
#   ./build.sh
#
# Requirements:
#   pdflatex  (part of TeX Live / MiKTeX)
#
# If pdflatex is not installed:
#   Ubuntu/Debian: sudo apt install texlive-latex-extra texlive-fonts-recommended
#   macOS (Homebrew): brew install --cask mactex
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEX_FILE="report.tex"
PDF_FILE="report.pdf"

cd "$SCRIPT_DIR"

# ── Check pdflatex is available ───────────────────────────────────────────────
if ! command -v pdflatex &>/dev/null; then
  echo ""
  echo "  ERROR: pdflatex not found."
  echo ""
  echo "  Install it with:"
  echo "    Ubuntu/Debian : sudo apt install texlive-latex-extra texlive-fonts-recommended"
  echo "    macOS (brew)  : brew install --cask mactex"
  echo ""
  exit 1
fi

echo "──────────────────────────────────────────────"
echo "  Building: $TEX_FILE"
echo "──────────────────────────────────────────────"

# First pass — generates .aux, .toc, etc.
echo "[1/2] First pdflatex pass..."
pdflatex -interaction=nonstopmode -halt-on-error "$TEX_FILE" > /dev/null

# Second pass — resolves cross-references and table of contents
echo "[2/2] Second pdflatex pass (resolving references)..."
pdflatex -interaction=nonstopmode -halt-on-error "$TEX_FILE" > /dev/null

# ── Clean auxiliary files ─────────────────────────────────────────────────────
echo "Cleaning auxiliary files..."
rm -f *.aux *.log *.toc *.out *.lof *.lot *.fls *.fdb_latexmk

echo ""
echo "  Done! Output: $SCRIPT_DIR/$PDF_FILE"
echo "──────────────────────────────────────────────"
