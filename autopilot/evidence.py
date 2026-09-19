from __future__ import annotations

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from .types import StepRecord, Observation, ProposedAction, ValidatedAction, RunManifest, Finding


class EvidenceCollector:
    def __init__(self, run_dir: Path, config: Any, profile_name: str, model_id: str, goal: str, start_url: str):
        self.run_dir = run_dir
        self.config = config
        self.profile_name = profile_name
        self.model_id = model_id
        self.goal = goal
        self.start_url = start_url
        self.steps: list[StepRecord] = []
        self.findings: list[Finding] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.outcome: Optional[str] = None
        self.total_tokens = 0
        self.step_count = 0

        # Create steps directory
        (run_dir / "steps").mkdir(parents=True, exist_ok=True)

    def add_step(self, record: StepRecord) -> None:
        self.steps.append(record)
        self.step_count += 1
        self._flush_trace()

    def _flush_trace(self) -> None:
        trace_path = self.run_dir / "trace.jsonl"
        with open(trace_path, "a") as f:
            f.write(self.steps[-1].model_dump_json() + "\n")

    def add_finding(self, finding: Finding) -> None:
        self.findings.append(finding)

    def finalize(self, outcome: str) -> None:
        self.end_time = datetime.now()
        self.outcome = outcome
        self._write_manifest()
        self._write_findings()

    def _write_manifest(self) -> None:
        manifest = RunManifest(
            run_id=self.run_dir.name,
            goal=self.goal,
            start_url=self.start_url,
            profile_name=self.profile_name,
            model_id=self.model_id,
            browser_version="chromium-153",
            viewport=self.config.browser.viewport,
            locale=self.config.browser.locale,
            timezone=self.config.browser.timezone,
            config_snapshot=self.config.model_dump() if hasattr(self.config, 'model_dump') else {},
            policy_snapshot=self.config.policy.model_dump() if hasattr(self.config, 'policy') else {},
            start_time=self.start_time,
            end_time=self.end_time,
            outcome=self.outcome,
            total_tokens=self.total_tokens,
            step_count=self.step_count,
        )
        with open(self.run_dir / "manifest.json", "w") as f:
            json.dump(json.loads(manifest.model_dump_json()), f, indent=2, default=str)

    def _write_findings(self) -> None:
        with open(self.run_dir / "findings.json", "w") as f:
            json.dump([f.model_dump() for f in self.findings], f, indent=2, default=str)


def create_run_dir(base: Path, goal: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    goal_slug = "".join(c if c.isalnum() else "-" for c in goal.lower())[:40]
    run_id = f"{timestamp}-{goal_slug}"
    run_dir = base / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def create_evidence_collector(run_dir: Path, config: Any, profile_name: str, model_id: str, goal: str, start_url: str) -> EvidenceCollector:
    return EvidenceCollector(run_dir, config, profile_name, model_id, goal, start_url)