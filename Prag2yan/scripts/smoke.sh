#!/usr/bin/env bash
set -euo pipefail

echo "=== Smoke test: Tier A scenarios ==="
rm -rf runs

echo "Running saucedemo.yaml..."
python -m autopilot run --scenario config/scenarios/saucedemo.yaml

echo "Running search.yaml..."
python -m autopilot run --scenario config/scenarios/search.yaml

echo "Running youtube.yaml..."
python -m autopilot run --scenario config/scenarios/youtube.yaml

echo "=== All scenarios completed ==="
ls runs/*/report.html