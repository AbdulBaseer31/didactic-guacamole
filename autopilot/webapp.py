from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import load_scenario

PROJECT_ROOT = Path(__file__).parent.parent
SCENARIOS_DIR = PROJECT_ROOT / "config" / "scenarios"
RUNS_DIR = PROJECT_ROOT / "runs"
FRONTEND_DIR = PROJECT_ROOT / "stitch_custom_frontend_application"

RUNS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Autopilot Dashboard API")

# --- Job launching: buttons on the dashboard shell out to the exact same
# `python -m autopilot ...` commands a person would type themselves, and this
# tracks each one so the page can poll for progress. ---

# key -> (scenario filename, needs the free-form Gemini planner, display label)
SCENARIO_BUTTONS: dict[str, dict[str, Any]] = {
    "saucedemo": {"file": "saucedemo.yaml", "ai": False, "label": "Commerce Checkout (SauceDemo)"},
    "search": {"file": "search.yaml", "ai": True, "label": "Search & Navigate (Google -> playwright.dev)"},
    "youtube": {"file": "youtube.yaml", "ai": True, "label": "YouTube Transcript Jump"},
}

_RUN_DIR_RE = re.compile(r"^(?:Run directory|Saving everything to): (.+)$")

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


class CustomRunRequest(BaseModel):
    goal: str
    url: str


def _run_job(job_id: str, cmd: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdin=subprocess.DEVNULL,  # never let a spawned job block on input() with no one to answer it
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    with _jobs_lock:
        _jobs[job_id]["pid"] = proc.pid

    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        with _jobs_lock:
            job = _jobs[job_id]
            job["log"].append(line)
            if job["run_id"] is None:
                m = _RUN_DIR_RE.match(line.strip())
                if m:
                    job["run_id"] = Path(m.group(1).strip()).name

    proc.wait()
    with _jobs_lock:
        job = _jobs[job_id]
        job["exit_code"] = proc.returncode
        job["status"] = "succeeded" if proc.returncode == 0 else "failed"


def _start_job(cmd: list[str], label: str) -> str:
    with _jobs_lock:
        if any(j["status"] == "running" for j in _jobs.values()):
            raise HTTPException(status_code=409, detail="A run is already in progress - wait for it to finish first")
        job_id = uuid.uuid4().hex[:12]
        _jobs[job_id] = {
            "status": "running",
            "label": label,
            "log": [],
            "run_id": None,
            "exit_code": None,
            "pid": None,
        }
    thread = threading.Thread(target=_run_job, args=(job_id, cmd), daemon=True)
    thread.start()
    return job_id


def _job_view(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": job["status"],
        "label": job["label"],
        "run_id": job["run_id"],
        "report_url": f"/runs/{job['run_id']}/report.html" if job["run_id"] else None,
        "exit_code": job["exit_code"],
        "log_tail": job["log"][-60:],
    }


@app.get("/")
def root() -> RedirectResponse:
    # The dashboard's page lives under its own subfolder rather than a root
    # index.html, so GET / would otherwise 404 - send visitors straight there.
    return RedirectResponse(url="/autopilot_run_console/code.html")


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
    return json.loads(path.read_text(encoding="utf-8"))


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


@app.post("/api/run/scenario/{key}")
def run_scenario(key: str) -> dict[str, Any]:
    choice = SCENARIO_BUTTONS.get(key)
    if not choice:
        raise HTTPException(status_code=404, detail=f"Unknown scenario button '{key}'")
    scenario_path = SCENARIOS_DIR / choice["file"]
    if not scenario_path.exists():
        raise HTTPException(status_code=404, detail=f"{choice['file']} not found in config/scenarios/")

    cmd = [
        sys.executable, "-m", "autopilot", "run",
        "--scenario", str(scenario_path), "--profile", "primary", "--no-open",
        "--live",  # config/default.yaml runs headless by default - force a visible window so the run can be watched
    ]
    if choice["ai"]:
        cmd.append("--ai")
    job_id = _start_job(cmd, choice["label"])
    return {"job_id": job_id}


@app.post("/api/run/custom")
def run_custom(body: CustomRunRequest) -> dict[str, Any]:
    goal = body.goal.strip()
    url = body.url.strip()
    if not goal or not url:
        raise HTTPException(status_code=400, detail="goal and url are both required")

    cmd = [
        sys.executable, "-m", "autopilot", "interactive",
        "--goal", goal, "--url", url, "--profile", "primary", "--no-open",
    ]
    job_id = _start_job(cmd, f"Custom: {goal[:60]}")
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return _job_view(job)


# Serve run artifacts (report.html, screenshots) directly by URL, and the
# dashboard's own static files at the root. Registered last so the /api/*
# routes above always take precedence over this catch-all mount.
app.mount("/runs", StaticFiles(directory=str(RUNS_DIR)), name="runs")
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
