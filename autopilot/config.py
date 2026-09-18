from __future__ import annotations
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .types import (
    BrowserConfig,
    BudgetsConfig,
    Config,
    PerceptionConfig,
    PolicyConfig,
    Profile,
    Scenario,
    StabilizationConfig,
)

load_dotenv()

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.yaml"


def load_default_config() -> Config:
    with open(DEFAULT_CONFIG_PATH) as f:
        data = yaml.safe_load(f)

    return Config(
        browser=BrowserConfig(**data["browser"]),
        budgets=BudgetsConfig(**data["budgets"]),
        stabilization=StabilizationConfig(**data["stabilization"]),
        perception=PerceptionConfig(**data["perception"]),
        policy=PolicyConfig(**data["policy"]),
    )


def load_scenario(path: Path) -> Scenario:
    with open(path) as f:
        data = yaml.safe_load(f)

    policy_data = data.get("policy", {})
    budgets_data = data.get("budgets", {})

    return Scenario(
        name=data["name"],
        goal=data["goal"],
        start_url=data["start_url"],
        policy=PolicyConfig(**policy_data) if policy_data else None,
        budgets=BudgetsConfig(**budgets_data) if budgets_data else None,
        secrets=data.get("secrets", {}),
    )


def merge_config(default: Config, scenario: Scenario | None) -> Config:
    if not scenario:
        return default

    policy = default.policy
    if scenario.policy:
        policy = PolicyConfig(
            domain_allowlist=scenario.policy.domain_allowlist or policy.domain_allowlist,
            blocked_classes=scenario.policy.blocked_classes or policy.blocked_classes,
            allow_dialog_accept=scenario.policy.allow_dialog_accept,
        )

    budgets = default.budgets
    if scenario.budgets:
        budgets = BudgetsConfig(
            max_steps=scenario.budgets.max_steps or budgets.max_steps,
            max_wall_clock_s=scenario.budgets.max_wall_clock_s or budgets.max_wall_clock_s,
            max_total_input_tokens=scenario.budgets.max_total_input_tokens or budgets.max_total_input_tokens,
            step_timeout_s=scenario.budgets.step_timeout_s or budgets.step_timeout_s,
        )

    return Config(
        browser=default.browser,
        budgets=budgets,
        stabilization=default.stabilization,
        perception=default.perception,
        policy=policy,
    )


def load_profiles() -> dict[str, Profile]:
    profiles: dict[str, Profile] = {}

    for prefix in ["PRIMARY", "SONNET45"]:
        key = os.getenv(f"AUTOPILOT_KEY_{prefix}")
        model = os.getenv(f"AUTOPILOT_MODEL_{prefix}")
        if key and model:
            name = prefix.lower()
            profiles[name] = Profile(name=name, model=model, api_key=key)

    return profiles


def select_profile(profile_name: str | None, profiles: dict[str, Profile]) -> Profile | None:
    if profile_name:
        if profile_name in profiles:
            return profiles[profile_name]
        return None

    env_profile = os.getenv("AUTOPILOT_PROFILE")
    if env_profile and env_profile in profiles:
        return profiles[env_profile]

    if len(profiles) == 1:
        return next(iter(profiles.values()))

    return None


def list_available_profiles(profiles: dict[str, Profile]) -> None:
    for i, (name, profile) in enumerate(profiles.items(), 1):
        print(f"  {i}) {name:<10} {profile.model:<30} [key found]")


def prompt_profile(profiles: dict[str, Profile]) -> Profile:
    print("Which API profile?")
    list_available_profiles(profiles)
    while True:
        try:
            choice = input("> ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(profiles):
                    return list(profiles.values())[idx]
            else:
                if choice in profiles:
                    return profiles[choice]
        except (EOFError, KeyboardInterrupt):
            pass
        print("Invalid choice, try again.")


def validate_profile(profile: Profile) -> bool:
    from anthropic import Anthropic

    client = Anthropic(api_key=profile.api_key)
    try:
        resp = client.messages.create(
            model=profile.model,
            max_tokens=16,
            messages=[{"role": "user", "content": "ping"}],
        )
        print(f"Validation OK: {profile.model} ({profile.name})")
        return True
    except Exception as e:
        print(f"Validation failed for {profile.model} ({profile.name}): {e}")
        return False