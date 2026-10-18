#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec conda run -n pyy --no-capture-output python run.py
