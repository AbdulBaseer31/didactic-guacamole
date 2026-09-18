from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


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