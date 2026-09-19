from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import load_scenario

PROJECT_ROOT = Path(__file__).parent.parent
SCENARIOS_DIR = PROJECT_ROOT / "config" / "scenarios"
RUNS_DIR = PROJECT_ROOT / "runs"
FRONTEND_DIR = PROJECT_ROOT / "stitch_custom_frontend_application"

RUNS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Autopilot Dashboard API")


@app.get("/")
def root() -> RedirectResponse:
    # The dashboard's pages live under their own subfolders (e.g.
    # autopilot_home_dashboard/code.html) rather than a root index.html, so
    # GET / would otherwise 404 - send visitors straight to the home page.
    return RedirectResponse(url="/autopilot_home_dashboard/code.html")


@app.get("/api/scenarios")
def list_scenarios() -> list[dict[str, Any]]:
    scenarios = []
    if not SCENARIOS_DIR.exists():
        return scenarios
    for path in sorted(SCENARIOS_DIR.glob("*.yaml")):
        try:
            scenario = load_scenario(path)
        except Exception:
            continue
        scenarios.append({
            "file": path.name,
            "name": scenario.name,
            "goal": scenario.goal.strip(),
            "start_url": scenario.start_url,
            "max_steps": scenario.budgets.max_steps if scenario.budgets else None,
            "domain_allowlist": scenario.policy.domain_allowlist if scenario.policy else [],
        })
    return scenarios


def _read_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _run_summary(run_dir: Path) -> Optional[dict[str, Any]]:
    manifest = _read_json(run_dir / "manifest.json")
    if not manifest:
        return None
    findings = _read_json(run_dir / "findings.json") or []
    counts = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.get("severity")
        if sev in counts:
            counts[sev] += 1

    duration = None
    start, end = manifest.get("start_time"), manifest.get("end_time")
    if start and end:
        try:
            duration = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
        except ValueError:
            duration = None

    max_steps = ((manifest.get("config_snapshot") or {}).get("budgets") or {}).get("max_steps")

    return {
        "run_id": manifest.get("run_id", run_dir.name),
        "goal": manifest.get("goal", ""),
        "start_url": manifest.get("start_url", ""),
        "outcome": manifest.get("outcome", "unknown"),
        "step_count": manifest.get("step_count", 0),
        "max_steps": max_steps,
        "start_time": start,
        "end_time": end,
        "duration_seconds": duration,
        "findings_count": counts,
    }


@app.get("/api/runs")
def list_runs() -> list[dict[str, Any]]:
    runs = []
    if RUNS_DIR.exists():
        for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue
            summary = _run_summary(run_dir)
            if summary:
                runs.append(summary)
    return runs


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    run_dir = RUNS_DIR / run_id
    manifest = _read_json(run_dir / "manifest.json")
    if manifest is None:
        raise HTTPException(status_code=404, detail="Run not found")
    findings = _read_json(run_dir / "findings.json") or []
    return {"manifest": manifest, "findings": findings, "summary": _run_summary(run_dir)}


# Serve run artifacts (report.html, screenshots) directly by URL, and the
# dashboard's own static files at the root. Registered last so the /api/*
# routes above always take precedence over this catch-all mount.
app.mount("/runs", StaticFiles(directory=str(RUNS_DIR)), name="runs")
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
