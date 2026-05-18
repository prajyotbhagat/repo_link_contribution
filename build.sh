#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Determine which Python to use (local venv or system python)
if [ -f "venv/bin/python" ]; then
  PYTHON="venv/bin/python"
elif command -v python3 &>/dev/null; then
  PYTHON="python3"
else
  PYTHON="python"
fi

# Collect static files for production deployment
$PYTHON manage.py collectstatic --noinput
