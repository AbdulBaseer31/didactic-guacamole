from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import Config, load_config, resolve_profile, validate_api_key
from .types import StepRecord, Observation, ProposedAction, ValidatedAction, TargetDescriptor, Element, Finding, RunManifest
from .browser import create_browser_manager
from .perception import Perception
from .planner import create_planner
from .resolver import create_resolver
from .policy import create_policy_gate
from .executor import create_executor
from .evidence import create_run_dir, create_evidence_collector


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

    # Get scenario for goal/start_url/secrets
    scenario = None
    if args.scenario:
        from .config import load_scenario
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

    # State tracking
    prev_state_hash = None
    same_state_count = 0
    no_change_count = 0
    start_time = time.time()
    max_wall_clock_ms = config.budgets.max_wall_clock_s * 1000
    max_steps = config.budgets.max_steps

    with create_browser_manager(config) as browser:
        perception = Perception(browser, config)

        # Initial observation - navigate to start URL first
        obs = perception.observe(0, start_url)
        prev_state_hash = obs.state_hash

        for step in range(1, max_steps + 1):
            # Check wall clock budget
            if (time.time() - start_time) * 1000 > max_wall_clock_ms:
                print("Wall clock budget exceeded")
                evidence.finalize("budget_exhausted")
                return 0

            # Get action from planner
            proposed = planner.propose_action(obs, goal)

            # Take before screenshot
            before_name, marked_name, after_name = perception.take_screenshots(step, run_dir, config.perception.screenshot_scale)

            # Resolve target
            locator, descriptor, confidence, candidates = None, None, 0.0, 0
            if proposed.uix is not None:
                locator, descriptor, confidence, candidates = resolver.resolve(browser.page, proposed, obs)

            # Validate with policy
            element = None
            if proposed.uix is not None:
                for el in obs.elements:
                    if el.uix == proposed.uix:
                        element = el
                        break
            validated = policy_gate.validate(proposed, descriptor, element)

            # Execute if allowed
            executed = False
            error = None
            if validated.decision == "allow":
                executed, error = executor.execute(browser.page, locator, proposed, element)
                if executed:
                    # Stabilize
                    stabilization = executor.wait_for_quiet(browser)
                    executor.settle()
                else:
                    error = error or "Execution failed"
            else:
                error = validated.block_reason or "Blocked by policy"
                print(f"  BLOCKED: {error}")

            # Capture after observation
            after_obs = perception.capture_step_observation(step)
            
            # Take after screenshot
            browser.screenshot(run_dir / "steps" / after_name, config.perception.screenshot_scale)
            browser.clear_marks()

            # Classify transition
            if after_obs.url != obs.url:
                transition = "url_change"
            elif after_obs.state_hash != obs.state_hash:
                transition = "dom_change"
            else:
                transition = "no_change"
                no_change_count += 1
            if transition != "no_change":
                no_change_count = 0

            # Check for stuck loop
            if after_obs.state_hash == prev_state_hash:
                same_state_count += 1
            else:
                same_state_count = 0
            prev_state_hash = after_obs.state_hash

            if same_state_count >= 3:
                print(f"Stuck loop detected (same state {same_state_count}x)")
                # Could inject a note to planner here
            if same_state_count >= 5:
                print("Aborting: stuck loop")
                evidence.finalize("stuck_loop")
                return 0

            # Record step
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

            print(f"Step {step}: {proposed.type} uix={proposed.uix} - {transition} - {'OK' if executed else 'BLOCKED/FAILED'}")

            # Check for finish
            if proposed.type == "finish":
                if proposed.success:
                    print("Goal achieved!")
                    evidence.finalize("success")
                else:
                    print("Goal failed")
                    evidence.finalize("failed")
                return 0

            # Update observation for next step
            obs = after_obs

            # Check for 3 no-change in a row
            if no_change_count >= 3:
                from .types import Finding
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

    evidence.finalize("max_steps_reached")
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