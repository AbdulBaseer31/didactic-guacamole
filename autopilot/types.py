from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class Element(BaseModel):
    uix: int
    frame_id: str
    role: str
    name: str
    tag: str
    input_type: str | None = None
    disabled: bool
    checked: bool | None = None
    expanded: str | None = None
    value: str | None = None
    href: str | None = None
    path: str
    box: tuple[int, int, int, int]


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
    element_name: str | None = None


class ProposedAction(BaseModel):
    type: Literal["click", "type", "select", "hover", "scroll", "press", "goto", "finish"]
    uix: int | None = None
    value: str | None = None
    key: str | None = None
    direction: Literal["down", "up"] | None = None
    url: str | None = None
    reasoning: str = Field(max_length=200)
    success: bool | None = None
    findings: list[FindingDraft] = Field(default_factory=list)


class ValidatedAction(BaseModel):
    action: ProposedAction
    descriptor: TargetDescriptor | None = None
    action_class: str
    decision: Literal["allow", "block"]
    block_reason: str | None = None
    resolver_confidence: float
    candidates_considered: int


class StepRecord(BaseModel):
    step: int
    observation: Observation
    proposed: ProposedAction
    validated: ValidatedAction
    executed: bool
    error: str | None = None
    stabilization: dict
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
    element_name: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class BrowserConfig(BaseModel):
    headless: bool
    viewport: dict[str, int]
    locale: str
    timezone: str
    slow_mo_ms: int


class BudgetsConfig(BaseModel):
    max_steps: int
    max_wall_clock_s: int
    max_total_input_tokens: int
    step_timeout_s: int


class StabilizationConfig(BaseModel):
    quiet_ms: int
    max_wait_ms: int
    post_action_settle_ms: int


class PerceptionConfig(BaseModel):
    max_elements: int
    screenshot_scale: float


class PolicyConfig(BaseModel):
    domain_allowlist: list[str] = Field(default_factory=list)
    blocked_classes: list[str] = Field(default_factory=list)
    allow_dialog_accept: bool = False


class Config(BaseModel):
    browser: BrowserConfig
    budgets: BudgetsConfig
    stabilization: StabilizationConfig
    perception: PerceptionConfig
    policy: PolicyConfig


class Scenario(BaseModel):
    name: str
    goal: str
    start_url: str
    policy: PolicyConfig | None = None
    budgets: BudgetsConfig | None = None
    secrets: dict[str, str] = Field(default_factory=dict)


class Profile(BaseModel):
    name: str
    model: str
    api_key: str


class RunConfig(BaseModel):
    goal: str
    start_url: str
    profile: Profile
    config: Config
    scenario: Scenario | None = None