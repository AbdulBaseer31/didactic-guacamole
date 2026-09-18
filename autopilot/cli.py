from __future__ import annotations
import sys
from pathlib import Path

import click
from rich.console import Console

from .config import (
    load_default_config,
    load_profiles,
    load_scenario,
    merge_config,
    prompt_profile,
    select_profile,
    validate_profile,
)
from .types import Profile, RunConfig, Scenario

console = Console()


def _select_and_validate_profile(profile: str | None) -> Profile | None:
    profiles = load_profiles()

    if not profiles:
        console.print(
            "[red]No API profiles configured. Set AUTOPILOT_KEY_<NAME> and AUTOPILOT_MODEL_<NAME> in .env[/red]"
        )
        sys.exit(2)

    selected = select_profile(profile, profiles)

    if not selected:
        if profile:
            console.print(f"[red]Profile '{profile}' not found or has no key configured[/red]")
            sys.exit(2)
        selected = prompt_profile(profiles)

    if not validate_profile(selected):
        sys.exit(1)

    return selected


@click.group(invoke_without_command=True)
@click.option("--profile", type=str, help="API profile to use")
@click.option("--validate-only", is_flag=True, help="Only validate the API key and exit")
@click.pass_context
def cli(ctx: click.Context, profile: str | None, validate_only: bool) -> None:
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile

    if validate_only:
        selected = _select_and_validate_profile(profile)
        if selected:
            console.print(f"[green]Profile '{selected.name}' validated successfully: {selected.model}[/green]")
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(1)


@cli.command()
@click.option("--scenario", type=click.Path(exists=True), help="Scenario YAML file")
@click.option("--profile", type=str, help="API profile to use")
@click.pass_context
def run(ctx: click.Context, scenario: str | None, profile: str | None) -> None:
    """Run the autopilot agent."""
    effective_profile = profile or ctx.obj.get("profile") if ctx.obj else None

    selected = _select_and_validate_profile(effective_profile)
    if not selected:
        return

    console.print(f"[green]Using profile: {selected.name} ({selected.model})[/green]")

    default_config = load_default_config()
    scenario_obj: Scenario | None = None

    if scenario:
        scenario_obj = load_scenario(Path(scenario))

    config = merge_config(default_config, scenario_obj)

    run_config = RunConfig(
        goal=scenario_obj.goal if scenario_obj else "",
        start_url=scenario_obj.start_url if scenario_obj else "",
        profile=selected,
        config=config,
        scenario=scenario_obj,
    )

    console.print(f"[cyan]Goal:[/cyan] {run_config.goal}")
    console.print(f"[cyan]Start URL:[/cyan] {run_config.start_url}")
    console.print(f"[cyan]Max steps:[/cyan] {config.budgets.max_steps}")


@cli.command()
@click.option("--url", required=True, help="URL to observe")
@click.pass_context
def observe(ctx: click.Context, url: str) -> None:
    """Observe a page and print element inventory."""
    console.print(f"[cyan]Observing:[/cyan] {url}")
    console.print("[yellow]Not yet implemented - checkpoint 2[/yellow]")


if __name__ == "__main__":
    cli()
