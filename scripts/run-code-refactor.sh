#!/usr/bin/env bash
# ============================================================================
# Linting Script
#Description: Runs Black for automatic formatting and Flake8 for linting report
#
#Setup: 
#1 make sure .env file is properly set up
#Usage: 
#1. Make this script executable: chmod +x run-code-refactor.sh
#2. Run the script: ./run-code-refactor.sh
# ============================================================================
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
  set -a
  source "$SCRIPT_DIR/.env"
  set +a
fi

PROJECT_DIR="${PROJECT_DIR:-}"

VENV_DIR="${VENV_DIR:-}"

if [ -z "$PROJECT_DIR" ] || [ -z "$VENV_DIR" ]; then
  echo "Error: PROJECT_DIR and VENV_DIR must be set (see scripts/.env.example)"
  exit 1
fi

cd $VENV_DIR && source bin/activate
cd $PROJECT_DIR/cookBot/

echo "================ BLACK (formatting) ================"
black .

echo ""
echo "================ FLAKE8 (linting) ================"
if flake8 .; then
  echo ""
  echo "Linting passed."
else
  echo ""
  echo "Linting failed."
  exit 1
fi

echo ""
echo "================ DONE ================"