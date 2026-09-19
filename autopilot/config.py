from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class BrowserConfig(BaseModel):
    headless: bool = False
    viewport: dict[str, int] = Field(default_factory=lambda: {"width": 1280, "height": 800})
    locale: str = "en-US"
    timezone: str = "Asia/Kolkata"
    slow_mo_ms: int = 120


class BudgetsConfig(BaseModel):
    max_steps: int = 25
    max_wall_clock_s: int = 300
    max_total_input_tokens: int = 400000
    step_timeout_s: int = 30


class StabilizationConfig(BaseModel):
    quiet_ms: int = 400
    max_wait_ms: int = 6000
    post_action_settle_ms: int = 150


class PerceptionConfig(BaseModel):
    max_elements: int = 120
    screenshot_scale: float = 0.75


class PolicyConfig(BaseModel):
    domain_allowlist: list[str] = Field(default_factory=list)
    blocked_classes: list[str] = Field(
        default_factory=lambda: ["payment", "destructive", "external_comms", "account_change"]
    )
    allow_dialog_accept: bool = False


class Profile(BaseModel):
    name: str
    model: str
    api_key: str


class Scenario(BaseModel):
    name: str
    goal: str
    start_url: str
    policy: Optional[PolicyConfig] = None
    budgets: Optional[BudgetsConfig] = None
    secrets: dict[str, str] = Field(default_factory=dict)


class Config(BaseModel):
    browser: BrowserConfig
    budgets: BudgetsConfig
    stabilization: StabilizationConfig
    perception: PerceptionConfig
    policy: PolicyConfig


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


def load_config(default_path: Path, scenario_path: Path | None = None) -> Config:
    default = load_default_config()
    scenario = load_scenario(scenario_path) if scenario_path else None
    return merge_config(default, scenario)


def load_profiles() -> dict[str, Profile]:
    profiles: dict[str, Profile] = {}

    for prefix in ["PRIMARY", "SONNET45"]:
        key = os.getenv(f"AUTOPILOT_KEY_{prefix}")
        model = os.getenv(f"AUTOPILOT_MODEL_{prefix}")
        if key and model:
            name = prefix.lower()
            profiles[name] = Profile(name=name, model=model, api_key=key)

    return profiles


def resolve_profile(profile_name: str | None) -> Profile | None:
    profiles = load_profiles()

    if profile_name:
        if profile_name in profiles:
            return profiles[profile_name]
        return None

    env_profile = os.getenv("AUTOPILOT_PROFILE")
    if env_profile and env_profile in profiles:
        return profiles[env_profile]

    if len(profiles) == 1:
        return next(iter(profiles.values()))

    # Non-interactive: auto-pick first profile instead of hanging
    if not sys.stdin.isatty():
        if profiles:
            first = next(iter(profiles.values()))
            print(f"Auto-selected profile (non-interactive): {first.name} ({first.model})")
            return first
        return None

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


def validate_api_key(profile: Profile | None) -> bool:
    if not profile:
        print("No API profiles configured. Set AUTOPILOT_KEY_<NAME> and AUTOPILOT_MODEL_<NAME> in .env")
        return False

    # Skip validation for placeholder keys (testing mode)
    if profile.api_key.startswith("sk-ant-..."):
        print(f"Validation SKIPPED (placeholder key): {profile.model} ({profile.name})")
        return True

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