from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config, load_config, resolve_profile, validate_api_key
from .types import RunManifest


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

    print(f"Running with profile: {profile.name} ({profile.model})")
    print(f"Config loaded: {config.model_dump()}")

    return 0


def observe_command(args: argparse.Namespace) -> int:
    profile = resolve_profile(args.profile)

    if not validate_api_key(profile):
        return 1

    print(f"Observing {args.url} with profile {profile.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())