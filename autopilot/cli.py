from __future__ import annotations

import argparse
import os
import re
import sys
import time
import json
import webbrowser
from datetime import datetime
from pathlib import Path

import yaml

from .config import Config, load_config, resolve_profile, validate_api_key, load_scenario
from .types import Profile, RunManifest, StepRecord, Observation, Finding
from .browser import create_browser_manager
from .perception import Perception
from .planner import create_planner
from .ai_planner import create_ai_planner
from .resolver import create_resolver
from .policy import create_policy_gate
from .executor import create_executor
from .evidence import create_run_dir, create_evidence_collector
from .findings import collect_all_findings
from .report import generate_report
from .humanize import (
    humanize_budget_exceeded,
    humanize_observing,
    humanize_outcome,
    humanize_step,
    humanize_stuck_loop,
)


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
    run_parser.add_argument("--live", action="store_true", help="Force a visible browser window (overrides config/default.yaml's headless setting) so you can watch the run")

    observe_parser = subparsers.add_parser("observe", help="Observe a page and capture elements")
    observe_parser.add_argument("--url", required=True, help="URL to observe")
    observe_parser.add_argument("--profile", help="API profile to use")

    interactive_parser = subparsers.add_parser(
        "interactive", help="Define a goal and website interactively, then watch it run live"
    )
    interactive_parser.add_argument("--profile", help="API profile to use (cosmetic only for now)")
    interactive_parser.add_argument("--no-open", action="store_true", help="Don't open report.html")

    serve_parser = subparsers.add_parser("serve", help="Launch the local web dashboard (FastAPI + frontend)")
    serve_parser.add_argument("--port", type=int, default=8050, help="Port to serve on (default 8050)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return run_command(args)
    elif args.command == "observe":
        return observe_command(args)
    elif args.command == "interactive":
        return interactive_command(args)
    elif args.command == "serve":
        return serve_command(args)

    return 0


def _slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:max_len].rstrip("-")) or "goal"


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
    findings_path.write_text(json.dumps(findings_data, indent=2, default=str), encoding="utf-8")
    
    # Generate report
    report_path = generate_report(run_dir, manifest, step_records, findings, config, profile_name, model_id)
    
    print(f"Report: file://{report_path.absolute()}")
    
    if not no_open:
        webbrowser.open(f"file://{report_path.absolute()}")

    return report_path


def execute_journey(
    browser,
    config: Config,
    goal: str,
    start_url: str,
    planner,
    resolver,
    policy_gate,
    executor,
    run_dir: Path,
    evidence,
    start_time: float,
    humanize: bool = False,
) -> tuple[str, list[StepRecord], list[Observation]]:
    """Runs the observe -> plan -> resolve -> validate -> execute -> stabilize loop
    until the goal finishes, the budget runs out, or a stuck loop is detected.

    Shared by the `run` and `interactive` subcommands so both exercise the same
    tested step logic - only the planner and the `humanize` flag differ.
    """
    prev_state_hash = None
    same_state_count = 0
    no_change_count = 0
    max_wall_clock_ms = config.budgets.max_wall_clock_s * 1000
    max_steps = config.budgets.max_steps

    all_observations: list[Observation] = []
    all_step_records: list[StepRecord] = []
    outcome = "max_steps_reached"

    perception = Perception(browser, config)

    if humanize:
        print(humanize_observing(start_url))

    obs = perception.observe(0, start_url)
    prev_state_hash = obs.state_hash
    all_observations.append(obs)

    try:
        for step in range(1, max_steps + 1):
            if (time.time() - start_time) * 1000 > max_wall_clock_ms:
                print(humanize_budget_exceeded() if humanize else "Wall clock budget exceeded")
                evidence.finalize("budget_exhausted")
                outcome = "budget_exhausted"
                break

            proposed = planner.propose_action(obs, goal)

            before_name, marked_name, after_name = perception.take_screenshots(step, run_dir, config.perception.screenshot_scale)

            locator, descriptor, confidence, candidates = None, None, 0.0, 0
            if proposed.uix is not None:
                locator, descriptor, confidence, candidates = resolver.resolve(browser.page, proposed, obs)

            element = None
            if proposed.uix is not None:
                for el in obs.elements:
                    if el.uix == proposed.uix:
                        element = el
                        break
            validated = policy_gate.validate(proposed, descriptor, element)

            executed = False
            error = None
            if validated.decision == "allow":
                executed, error = executor.execute(browser.page, locator, proposed, element)
                if executed:
                    executor.wait_for_quiet(browser)
                    executor.settle()
                else:
                    error = error or "Execution failed"
            else:
                error = validated.block_reason or "Blocked by policy"
                if not humanize:
                    print(f"  BLOCKED: {error}")

            after_obs = perception.capture_step_observation(step)
            all_observations.append(after_obs)

            browser.screenshot(run_dir / "steps" / after_name, config.perception.screenshot_scale)
            browser.clear_marks()

            if after_obs.url != obs.url:
                transition = "url_change"
            elif after_obs.state_hash != obs.state_hash:
                transition = "dom_change"
            else:
                transition = "no_change"
                no_change_count += 1
            if transition != "no_change":
                no_change_count = 0

            if after_obs.state_hash == prev_state_hash:
                same_state_count += 1
            else:
                same_state_count = 0
            prev_state_hash = after_obs.state_hash

            if same_state_count >= 3 and not humanize:
                print(f"Stuck loop detected (same state {same_state_count}x)")
            if same_state_count >= 5:
                print(humanize_stuck_loop(same_state_count) if humanize else "Aborting: stuck loop")
                evidence.finalize("stuck_loop")
                outcome = "stuck_loop"
                break

            record = StepRecord(
                step=step,
                observation=obs,
                proposed=proposed,
                validated=validated,
                executed=executed,
                error=error,
                stabilization={"state": "QUIESCENT", "wait_ms": 0, "mutations_seen": 0},
                before_png=before_name,
                marked_png=marked_name,
                after_png=after_name,
                duration_ms=0,
                transition=transition,
            )
            evidence.add_step(record)
            all_step_records.append(record)

            if humanize:
                print(humanize_step(record))
            else:
                print(f"Step {step}: {proposed.type} uix={proposed.uix} - {transition} - {'OK' if executed else 'BLOCKED/FAILED'}")

            if proposed.type == "finish":
                if proposed.success:
                    outcome = "success"
                    evidence.finalize("success")
                else:
                    outcome = "failed"
                    evidence.finalize("failed")
                print(humanize_outcome(outcome) if humanize else ("Goal achieved!" if proposed.success else "Goal failed"))
                break

            obs = after_obs

            if no_change_count >= 3:
                finding = Finding(
                    finding_id=f"ux_friction_no_change_{step}",
                    category="ux_friction",
                    severity="medium",
                    description="Element appeared interactive but produced no observable change after 3 attempts",
                    step=step,
                    evidence_refs=[before_name, after_name],
                )
                evidence.add_finding(finding)
                no_change_count = 0
        else:
            evidence.finalize("max_steps_reached")
            outcome = "max_steps_reached"
    except Exception as exc:
        # Per MVP-BUILD-SPEC.md SS15: every abort path must still produce a
        # report from whatever trace.jsonl already holds - never let an
        # unexpected exception (Unicode or otherwise) propagate raw and skip
        # report generation.
        print(f"Step {step}: unexpected error, aborting run cleanly - {exc}")
        outcome = "error"
        evidence.finalize("error")

    return outcome, all_step_records, all_observations


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

    if getattr(args, "live", False):
        # Force a visible browser window for this run without touching the
        # committed default (which stays headless for unattended/CI runs).
        config = config.model_copy(update={
            "browser": config.browser.model_copy(update={
                "headless": False,
                "slow_mo_ms": max(config.browser.slow_mo_ms, 150),
            })
        })

    # Get scenario for goal/start_url/secrets
    scenario = None
    if args.scenario:
        scenario = load_scenario(Path(args.scenario))

    goal = scenario.goal if scenario else (args.goal or "")
    start_url = scenario.start_url if scenario else (args.url or "")

    print(f"Running with profile: {profile.name} ({profile.model})")
    print(f"Goal: {goal}")
    print(f"Start URL: {start_url}")

    # Create run directory
    runs_dir = Path("runs")
    runs_dir.mkdir(exist_ok=True)
    run_dir = create_run_dir(runs_dir, goal)
    print(f"Run directory: {run_dir}")

    # Create evidence collector
    evidence = create_evidence_collector(run_dir, config, profile.name, profile.model, goal, start_url)

    # Create components
    planner = create_planner()
    resolver = create_resolver()
    policy_gate = create_policy_gate(config)
    executor = create_executor(config)

    start_time = time.time()

    with create_browser_manager(config) as browser:
        outcome, all_step_records, all_observations = execute_journey(
            browser, config, goal, start_url, planner, resolver, policy_gate, executor,
            run_dir, evidence, start_time,
        )

    # Generate findings and report
    print("Generating report...")
    finalize_run(
        run_dir=run_dir,
        manifest=RunManifest(
            run_id=run_dir.name,
            goal=goal,
            start_url=start_url,
            profile_name=profile.name,
            model_id=profile.model,
            browser_version="chromium-153",
            viewport=config.browser.viewport,
            locale=config.browser.locale,
            timezone=config.browser.timezone,
            config_snapshot=config.model_dump(),
            policy_snapshot=config.policy.model_dump(),
            start_time=datetime.fromtimestamp(start_time),
            end_time=datetime.now(),
            outcome=evidence.outcome,
            total_tokens=evidence.total_tokens,
            step_count=evidence.step_count,
        ),
        step_records=all_step_records,
        observations=all_observations,
        config=config,
        profile_name=profile.name,
        model_id=profile.model,
        no_open=args.no_open
    )
    return 0


INTERACTIVE_MAX_STEPS = 12


def interactive_command(args: argparse.Namespace) -> int:
    if not os.getenv("GEMINI_API_KEY"):
        print(
            "No Gemini API key found - add GEMINI_API_KEY to your .env file and try again.",
            file=sys.stderr,
        )
        return 1

    goal = input("Define your goal: ").strip()
    start_url = input("Define your website: ").strip()

    if not goal or not start_url:
        print("Both a goal and a website are required.", file=sys.stderr)
        return 2

    profile = resolve_profile(getattr(args, "profile", None))
    if not profile:
        from .config import load_profiles, prompt_profile
        profiles = load_profiles()
        if len(profiles) == 1:
            profile = next(iter(profiles.values()))
        elif profiles:
            profile = prompt_profile(profiles)
        else:
            # No Anthropic profile configured - fine here, it's only used for
            # cosmetic manifest metadata since GeminiPlanner doesn't consume it.
            profile = Profile(name="none", model="gemini (not yet wired up)", api_key="")

    slug = _slugify(goal)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    scenario_path = Path("config/scenarios") / f"adhoc_{timestamp}_{slug}.yaml"
    scenario_path.parent.mkdir(parents=True, exist_ok=True)
    with open(scenario_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            {"name": f"adhoc_{slug}", "goal": goal, "start_url": start_url, "secrets": {}},
            f,
            sort_keys=False,
            allow_unicode=True,
        )
    print(f"Saved this as a scenario: {scenario_path}")

    config = load_config(Path("config/default.yaml"), scenario_path)
    # Force a visible browser window for this live, human-watched run regardless
    # of the committed default (which stays headless for unattended/CI runs).
    config = config.model_copy(update={
        "browser": config.browser.model_copy(update={
            "headless": False,
            "slow_mo_ms": max(config.browser.slow_mo_ms, 150),
        }),
        # A user-typed goal is more open-ended/exploratory than a curated
        # scenario file, so cap its worst-case Gemini call count tighter than
        # the shared default.
        "budgets": config.budgets.model_copy(update={
            "max_steps": min(config.budgets.max_steps, INTERACTIVE_MAX_STEPS),
        }),
    })

    print(f"Goal: {goal}")
    print(f"Website: {start_url}")

    runs_dir = Path("runs")
    runs_dir.mkdir(exist_ok=True)
    run_dir = create_run_dir(runs_dir, goal)
    print(f"Saving everything to: {run_dir}")

    evidence = create_evidence_collector(run_dir, config, profile.name, profile.model, goal, start_url)

    planner = create_ai_planner()
    resolver = create_resolver()
    policy_gate = create_policy_gate(config)
    executor = create_executor(config)

    start_time = time.time()

    with create_browser_manager(config) as browser:
        outcome, all_step_records, all_observations = execute_journey(
            browser, config, goal, start_url, planner, resolver, policy_gate, executor,
            run_dir, evidence, start_time, humanize=True,
        )

    print("Putting together the results page...")
    finalize_run(
        run_dir=run_dir,
        manifest=RunManifest(
            run_id=run_dir.name,
            goal=goal,
            start_url=start_url,
            profile_name=profile.name,
            model_id=profile.model,
            browser_version="chromium-153",
            viewport=config.browser.viewport,
            locale=config.browser.locale,
            timezone=config.browser.timezone,
            config_snapshot=config.model_dump(),
            policy_snapshot=config.policy.model_dump(),
            start_time=datetime.fromtimestamp(start_time),
            end_time=datetime.now(),
            outcome=evidence.outcome,
            total_tokens=evidence.total_tokens,
            step_count=evidence.step_count,
        ),
        step_records=all_step_records,
        observations=all_observations,
        config=config,
        profile_name=profile.name,
        model_id=profile.model,
        no_open=getattr(args, "no_open", False),
    )
    print(humanize_outcome(evidence.outcome))
    return 0


def serve_command(args: argparse.Namespace) -> int:
    import uvicorn
    from .webapp import app

    print(f"Dashboard: http://127.0.0.1:{args.port}/autopilot_home_dashboard/code.html")
    uvicorn.run(app, host="127.0.0.1", port=args.port)
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

    config = Config(
        browser=__import__("autopilot.config", fromlist=["BrowserConfig"]).BrowserConfig(),
        budgets=__import__("autopilot.config", fromlist=["BudgetsConfig"]).BudgetsConfig(),
        stabilization=__import__("autopilot.config", fromlist=["StabilizationConfig"]).StabilizationConfig(),
        perception=__import__("autopilot.config", fromlist=["PerceptionConfig"]).PerceptionConfig(),
        policy=__import__("autopilot.config", fromlist=["PolicyConfig"]).PolicyConfig(),
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