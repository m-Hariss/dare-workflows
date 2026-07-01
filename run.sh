#!/usr/bin/env bash
set -e

# ---------------------------------------------------------------------------
# run.sh — start the Dare Workflow Runner
#
# Designed for non-technical users: if Python is not installed, uv will
# download it automatically. If uv itself is not installed, this script
# installs it first.
#
# What this script does:
#   1. Installs uv (a Python toolchain manager) if not already present
#   2. Uses uv to create a .venv with Python 3.10+ (downloads it if missing)
#   3. Installs dependencies from requirements.txt into the venv
#   4. Starts the FastAPI server
# ---------------------------------------------------------------------------

# Always run from the directory this script lives in
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PORT="${APP_PORT:-8000}"

# ── Step 1: ensure uv is available ──────────────────────────────────────────
# uv can download Python itself, so the user does not need to have Python
# pre-installed. It is a single ~10 MB binary.

if ! command -v uv &>/dev/null; then
    echo "uv not found — installing it now (this only happens once)..."
    if command -v curl &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget &>/dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo "ERROR: Neither curl nor wget is available. Cannot install uv."
        echo "Please install Python 3.10+ from https://www.python.org/downloads/"
        exit 1
    fi
    # The uv installer puts the binary in ~/.local/bin
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv &>/dev/null; then
    echo "ERROR: uv installation failed."
    echo "Please install Python 3.10+ manually from https://www.python.org/downloads/"
    exit 1
fi

# ── Step 2: create virtual environment ──────────────────────────────────────
# uv downloads Python 3.10 automatically if it is not found on the system.
if [ ! -d ".venv" ]; then
    echo "Setting up Python environment (may download Python — one-time setup)..."
    uv venv --python 3.10 .venv
fi

# ── Step 3: install / sync dependencies ─────────────────────────────────────
echo "Installing dependencies..."
uv pip install --quiet --python .venv/bin/python -r requirements.txt

# ── Step 4: start the server ─────────────────────────────────────────────────
mkdir -p .data

echo ""
echo "Dare Workflow Runner is starting on port $PORT"
echo ""

exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
