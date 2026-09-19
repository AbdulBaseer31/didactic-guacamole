from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class BrowserConfig(BaseModel):
    headless: bool = False
    viewport: dict[str, int] = Field(default_factory=lambda: {"width": 1280, "height": 800})
    locale: str = "en-US"
    timezone: str = "Asia/Kolkata"
    slow_mo_ms: int = 120


class StabilizationConfig(BaseModel):
    quiet_ms: int = 400
    max_wait_ms: int = 6000
    post_action_settle_ms: int = 150


class PerceptionConfig(BaseModel):
    max_elements: int = 120
    screenshot_scale: float = 0.75


class PolicyConfig(BaseModel):
    domain_allowlist: list[str] = Field(default_factory=list)
    blocked_classes: list[str] = Field(default_factory=lambda: ["payment", "destructive", "external_comms", "account_change"])
    allow_dialog_accept: bool = False


class BudgetsConfig(BaseModel):
    max_steps: int = 25
    max_wall_clock_s: int = 300
    max_total_input_tokens: int = 400000
    step_timeout_s: int = 30


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


class Element(BaseModel):
    uix: int
    frame_id: str
    role: str
    name: str
    tag: str
    input_type: Optional[str] = None
    disabled: bool
    checked: Optional[bool] = None
    expanded: Optional[str] = None
    value: Optional[str] = None
    href: Optional[str] = None
    path: str
    box: tuple[int, int, int, int]
    tabindex: Optional[str] = None
    alt: Optional[str] = None
    aria_label: Optional[str] = None
    aria_labelledby: Optional[str] = None


class Observation(BaseModel):
    step: int
    url: str
    title: str
    frames: list[str]
    elements: list[Element]
    scroll_y: int
    max_scroll: int
    state_hash: str
    captured_at: datetime


class TargetDescriptor(BaseModel):
    frame_id: str
    role: str
    name: str
    tag: str
    path: str
    ordinal: int


class FindingDraft(BaseModel):
    category: Literal["ux_friction", "accessibility", "error_state", "performance"]
    severity: Literal["low", "medium", "high"]
    description: str
    element_name: Optional[str] = None
    evidence_refs: list[str] = Field(default_factory=list)


class ProposedAction(BaseModel):
    type: Literal["click", "type", "select", "hover", "scroll", "press", "goto", "finish"]
    uix: Optional[int] = None
    value: Optional[str] = None
    key: Optional[str] = None
    direction: Optional[Literal["down", "up"]] = None
    url: Optional[str] = None
    reasoning: str
    success: Optional[bool] = None
    findings: list[FindingDraft] = Field(default_factory=list)


class ValidatedAction(BaseModel):
    action: ProposedAction
    descriptor: Optional[TargetDescriptor] = None
    action_class: str
    decision: Literal["allow", "block"]
    block_reason: Optional[str] = None
    resolver_confidence: float
    candidates_considered: int


class StepRecord(BaseModel):
    step: int
    observation: Observation
    proposed: ProposedAction
    validated: ValidatedAction
    executed: bool
    error: Optional[str] = None
    stabilization: dict[str, Any]
    before_png: str
    marked_png: str
    after_png: str
    duration_ms: int
    transition: str


class Finding(BaseModel):
    finding_id: str
    category: Literal["ux_friction", "accessibility", "error_state", "performance"]
    severity: Literal["low", "medium", "high"]
    description: str
    step: int
    element_name: Optional[str] = None
    evidence_refs: list[str] = Field(default_factory=list)


class RunManifest(BaseModel):
    run_id: str
    goal: str
    start_url: str
    profile_name: str
    model_id: str
    browser_version: str
    viewport: dict[str, int]
    locale: str
    timezone: str
    config_snapshot: dict[str, Any]
    policy_snapshot: dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime] = None
    outcome: Optional[str] = None
    total_tokens: int = 0
    step_count: int = 0


class RunConfig(BaseModel):
    goal: str
    start_url: str
    profile: Profile
    config: Config
    scenario: Scenario | None = None