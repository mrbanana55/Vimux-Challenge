#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 (>= 3.11) is required to run Vimux Challenge." >&2
    exit 1
fi

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Creating virtual environment in .venv..."
    python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_PYTHON" -c "import textual" >/dev/null 2>&1; then
    echo "Installing dependencies into .venv..."
    "$VENV_DIR/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt"
fi

export PYTHONPATH="$REPO_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$VENV_PYTHON" -m vim_tmux_quest "$@"
