#!/usr/bin/env bash
set -e

# ---------------------------------------------------------------------------
# run.sh — start the Dare Workflow Runner
#
# What this script does, step by step:
#   1. Checks Python 3.11+ is available
#   2. Creates a .venv if one doesn't exist yet
#   3. Installs / updates dependencies from requirements.txt
#   4. Starts the FastAPI server on http://localhost:8000
# ---------------------------------------------------------------------------

PYTHON=""
for cmd in python3.12 python3.11 python3; do
  if command -v "$cmd" &>/dev/null; then
    version=$("$cmd" -c 'import sys; print(sys.version_info.major * 10 + sys.version_info.minor)')
    if [ "$version" -ge 311 ]; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo "ERROR: Python 3.11 or higher is required but was not found."
  echo "Install it from https://www.python.org/downloads/ and try again."
  exit 1
fi

echo "Using $($PYTHON --version)"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  "$PYTHON" -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install / sync dependencies
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Create .data directory (stores uploaded files, keys, vectors)
mkdir -p .data

echo ""
echo "Starting Dare Workflow Runner at http://localhost:8000"
echo "Press Ctrl+C to stop."
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000
