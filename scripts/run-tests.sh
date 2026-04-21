#!/usr/bin/env bash
# ============================================================================
# Run Django and Behave tests 
#Description: Runs both Django unit tests and Behave BDD tests for the project
#
#Setup: 
#1 make sure .env file is properly set up
#Usage: 
#1. Make this script executable: chmod +x run-tests.sh (must do this command in the scripts directory)
#2. Run the script: ./run-tests.sh
# ============================================================================
set -e

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


echo "================ DJANGO TESTS ================"
python manage.py test

echo ""
echo "================ BEHAVE TESTS ================"
python manage.py behave



