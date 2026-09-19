from __future__ import annotations

import argparse
import sys
import json
import webbrowser
from pathlib import Path
from datetime import datetime

from .config import Config, load_config, resolve_profile, validate_api_key, load_scenario
from .types import RunManifest, StepRecord, Observation
from .findings import collect_all_findings
from .report import generate_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="autopilot", description="Autonomous web journey agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a journey")
    run_parser.add_argument("--goal", help="Natural language goal")
    run_parser.add_argument("--url", help="Start URL")
    run_parser.add_argument("--scenario", help="Path to scenario YAML")
    run_parser.add_argument("--profile", help="API profile to use")
    run_parser.add_argument("--validate-only", action="store_true", help="Validate API key and exit")
    run_parser.add_argument("--no-open", action="store_true", help="Don't open report.html")

    observe_parser = subparsers.add_parser("observe", help="Observe a page and capture elements")
    observe_parser.add_argument("--url", required=True, help="URL to observe")
    observe_parser.add_argument("--profile", help="API profile to use")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run_command(args)
    elif args.command == "observe":
        return observe_command(args)

    return 0


def finalize_run(
    run_dir: Path,
    manifest: RunManifest,
    step_records: list[StepRecord],
    observations: list[Observation],
    config: Config,
    profile_name: str,
    model_id: str,
    no_open: bool = False
) -> Path:
    """Generate findings and report, return report path."""
    findings = collect_all_findings(step_records, observations)
    
    # Write findings.json
    findings_path = run_dir / "findings.json"
    findings_data = [f.model_dump() for f in findings]
    findings_path.write_text(json.dumps(findings_data, indent=2, default=str))
    
    # Generate report
    report_path = generate_report(run_dir, manifest, step_records, findings, config, profile_name, model_id)
    
    print(f"Report: file://{report_path.absolute()}")
    
    if not no_open:
        webbrowser.open(f"file://{report_path.absolute()}")
    
    return report_path


def run_command(args: argparse.Namespace) -> int:
    profile = resolve_profile(args.profile)

    if args.validate_only:
        if validate_api_key(profile):
            print(f"OK  {profile.model}")
            return 0
        else:
            return 1

    if not args.scenario and not (args.goal and args.url):
        print("Either --scenario or both --goal and --url required", file=sys.stderr)
        return 2

    config = load_config(
        Path("config/default.yaml"),
        Path(args.scenario) if args.scenario else None,
    )
    
    scenario = None
    if args.scenario:
        scenario = load_scenario(Path(args.scenario))

    print(f"Running with profile: {profile.name} ({profile.model})")
    print(f"Config loaded: {config.model_dump()}")

    # TODO: Actual run loop (Checkpoint 3) would go here
    # It should produce: run_dir, manifest, step_records, observations
    # Then call finalize_run(...)
    print("NOTE: Full run loop (Checkpoint 3) not implemented in this version")
    print("This is a Checkpoint 4 implementation - findings.py and report.py are ready")
    
    return 0


def observe_command(args: argparse.Namespace) -> int:
    profile = resolve_profile(args.profile)

    if not profile:
        from .config import load_profiles, prompt_profile
        profiles = load_profiles()
        if len(profiles) == 1:
            profile = next(iter(profiles.values()))
            print(f"Auto-selected profile: {profile.name} ({profile.model})")
        else:
            profile = prompt_profile(profiles)

    if not validate_api_key(profile):
        return 1

    print(f"Observing {args.url} with profile {profile.name}")

    from .browser import create_browser_manager
    from .perception import Perception
    from .config import Config, BrowserConfig, StabilizationConfig, PerceptionConfig, PolicyConfig, BudgetsConfig

    # Create a minimal config for perception
    config = Config(
        browser=BrowserConfig(),
        budgets=BudgetsConfig(),
        stabilization=StabilizationConfig(),
        perception=PerceptionConfig(),
        policy=PolicyConfig(),
    )

    with create_browser_manager(config) as browser:
        perception = Perception(browser, config)
        obs = perception.observe(0, args.url)

    print(f"URL: {obs.url}")
    print(f"Title: {obs.title}")
    print(f"Frames: {obs.frames}")
    print(f"Elements found: {len(obs.elements)}")
    for el in obs.elements[:10]:
        print(f"  [{el.uix}] {el.role} \"{el.name}\" ({el.tag})")
    if len(obs.elements) > 10:
        print(f"  ... and {len(obs.elements) - 10} more")

    return 0


if __name__ == "__main__":
    sys.exit(main())