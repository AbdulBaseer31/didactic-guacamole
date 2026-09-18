from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


class AppConfig(BaseModel):
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    budgets: BudgetsConfig = Field(default_factory=BudgetsConfig)
    stabilization: StabilizationConfig = Field(default_factory=StabilizationConfig)
    perception: PerceptionConfig = Field(default_factory=PerceptionConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)


class Profile(BaseModel):
    name: str
    api_key: str
    model: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    autopilot_key_primary: str | None = None
    autopilot_model_primary: str = "claude-sonnet-5"
    autopilot_key_sonnet45: str | None = None
    autopilot_model_sonnet45: str = "claude-sonnet-4-5-20250929"

    def get_profiles(self) -> list[Profile]:
        profiles = []
        if self.autopilot_key_primary:
            profiles.append(Profile(name="primary", api_key=self.autopilot_key_primary, model=self.autopilot_model_primary))
        if self.autopilot_key_sonnet45:
            profiles.append(Profile(name="sonnet45", api_key=self.autopilot_key_sonnet45, model=self.autopilot_model_sonnet45))
        return profiles

    def get_profile(self, name: str) -> Profile | None:
        for p in self.get_profiles():
            if p.name == name:
                return p
        return None


@dataclass
class RuntimeConfig:
    app: AppConfig
    profile: Profile
    scenario: dict[str, Any] | None = None

    @property
    def max_steps(self) -> int:
        if self.scenario and "budgets" in self.scenario and "max_steps" in self.scenario["budgets"]:
            return self.scenario["budgets"]["max_steps"]
        return self.app.budgets.max_steps

    @property
    def domain_allowlist(self) -> list[str]:
        if self.scenario and "policy" in self.scenario and "domain_allowlist" in self.scenario["policy"]:
            return self.scenario["policy"]["domain_allowlist"]
        return self.app.policy.domain_allowlist

    @property
    def blocked_classes(self) -> list[str]:
        if self.scenario and "policy" in self.scenario and "blocked_classes" in self.scenario["policy"]:
            return self.scenario["policy"]["blocked_classes"]
        return self.app.policy.blocked_classes

    @property
    def secrets(self) -> dict[str, str]:
        if self.scenario and "secrets" in self.scenario:
            return self.scenario["secrets"]
        return {}


def load_app_config(config_path: Path | None = None) -> AppConfig:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "default.yaml"

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return AppConfig(**data)


def load_scenario(scenario_path: Path) -> dict[str, Any]:
    with open(scenario_path) as f:
        return yaml.safe_load(f)


def resolve_profile(
    settings: Settings,
    cli_profile: str | None = None,
    env_profile: str | None = None,
) -> Profile:
    profiles = settings.get_profiles()

    if not profiles:
        raise ValueError(
            "No API profiles configured. Set AUTOPILOT_KEY_PRIMARY or AUTOPILOT_KEY_SONNET45 in .env"
        )

    profile_name = cli_profile or env_profile

    if profile_name:
        profile = settings.get_profile(profile_name)
        if not profile:
            available = ", ".join(p.name for p in profiles)
            raise ValueError(f"Profile '{profile_name}' not found or has no key. Available: {available}")
        if not profile.api_key:
            raise ValueError(f"Profile '{profile_name}' has no API key configured")
        return profile

    if len(profiles) == 1:
        print(f"Auto-selected profile: {profiles[0].name} ({profiles[0].model})")
        return profiles[0]

    print("Which API profile?")
    for i, p in enumerate(profiles, 1):
        print(f"  {i}) {p.name:<10} {p.model:<35} [key found]")

    while True:
        try:
            choice = input("> ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(profiles):
                return profiles[idx]
            print(f"Enter a number between 1 and {len(profiles)}")
        except (ValueError, EOFError):
            print("Invalid input")
        except KeyboardInterrupt:
            raise SystemExit(1)
