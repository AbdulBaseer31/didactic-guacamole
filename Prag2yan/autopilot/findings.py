from __future__ import annotations

from typing import Any
from .types import Finding, Observation, Element, StepRecord, FindingDraft


def collect_model_findings(step_records: list[StepRecord]) -> list[Finding]:
    """Source 1: Model-reported findings from ProposedAction.findings"""
    findings: list[Finding] = []
    for sr in step_records:
        for fd in sr.proposed.findings:
            finding_id = f"model_{sr.step}_{fd.category}_{abs(hash(fd.description)) % 100000}"
            findings.append(Finding(
                finding_id=finding_id,
                category=fd.category,
                severity=fd.severity,
                description=fd.description,
                step=sr.step,
                element_name=fd.element_name,
                evidence_refs=fd.evidence_refs or [sr.marked_png, sr.after_png]
            ))
    return findings


def collect_behavioural_findings(step_records: list[StepRecord]) -> list[Finding]:
    """Source 2: Behavioural findings
    - 3 consecutive 'no_change' transitions on interactive actions -> ux_friction (medium)
    - resolver 'ambiguous' rejection -> ux_friction (medium)
    - policy 'block' decision -> high severity
    - step stabilization.wait_ms > 10000 -> performance (medium)
    """
    findings: list[Finding] = []
    
    # 3 consecutive 'no_change' on interactive actions
    no_change_count = 0
    for sr in step_records:
        if sr.transition == "no_change" and sr.proposed.type in ("click", "type", "select", "press", "hover"):
            no_change_count += 1
            if no_change_count >= 3:
                finding_id = f"behav_ux_friction_{sr.step}_{abs(hash('three_no_change')) % 100000}"
                findings.append(Finding(
                    finding_id=finding_id,
                    category="ux_friction",
                    severity="medium",
                    description="Element appeared interactive but produced no observable change after 3 consecutive attempts",
                    step=sr.step,
                    element_name=sr.validated.descriptor.name if sr.validated.descriptor else None,
                    evidence_refs=[sr.before_png, sr.marked_png, sr.after_png]
                ))
        else:
            no_change_count = 0
    
    # resolver 'ambiguous' rejection
    for sr in step_records:
        if sr.validated.block_reason and "ambiguous" in sr.validated.block_reason.lower():
            finding_id = f"behav_ambiguous_{sr.step}_{abs(hash(sr.validated.block_reason)) % 100000}"
            findings.append(Finding(
                finding_id=finding_id,
                category="ux_friction",
                severity="medium",
                description=f"Ambiguous target: {sr.validated.block_reason}",
                step=sr.step,
                element_name=sr.validated.descriptor.name if sr.validated.descriptor else None,
                evidence_refs=[sr.before_png, sr.marked_png, sr.after_png]
            ))
    
    # policy 'block' decision
    for sr in step_records:
        if sr.validated.decision == "block" and sr.validated.block_reason:
            finding_id = f"behav_policy_block_{sr.step}_{abs(hash(sr.validated.block_reason)) % 100000}"
            findings.append(Finding(
                finding_id=finding_id,
                category="error_state",
                severity="high",
                description=f"Policy blocked action: {sr.validated.block_reason}",
                step=sr.step,
                element_name=sr.validated.descriptor.name if sr.validated.descriptor else None,
                evidence_refs=[sr.before_png, sr.marked_png, sr.after_png]
            ))
    
    # step stabilization.wait_ms > 10000
    for sr in step_records:
        wait_ms = sr.stabilization.get("wait_ms", 0) if isinstance(sr.stabilization, dict) else 0
        if wait_ms > 10000:
            finding_id = f"behav_perf_{sr.step}_{abs(hash(str(wait_ms))) % 100000}"
            findings.append(Finding(
                finding_id=finding_id,
                category="performance",
                severity="medium",
                description=f"Step stabilization exceeded 10s (waited {wait_ms}ms)",
                step=sr.step,
                element_name=sr.validated.descriptor.name if sr.validated.descriptor else None,
                evidence_refs=[sr.before_png, sr.marked_png, sr.after_png]
            ))
    
    return findings


def collect_static_a11y_findings(observations: list[Observation]) -> list[Finding]:
    """Source 3: Static accessibility checks on inventory (no new capture)
    1. Interactive element with empty accessible name
    2. role='button'/'link' with tabindex='-1' (unreachable by keyboard)
    3. Image-only link/button with no alt/aria-label
    4. Form input with no associated label (name derived from placeholder alone)
    5. Positive tabindex values (break natural focus order)
    
    Deduplicate by (category, element_name, description).
    """
    findings: list[Finding] = []
    seen: set[tuple[str, str, str]] = set()
    
    interactive_roles = {"button", "link", "textbox", "checkbox", "radio", "combobox", "searchbox", "menuitem", "tab", "slider"}
    
    for obs in observations:
        for el in obs.elements:
            # 1. Interactive element with empty accessible name
            if el.role in interactive_roles and not el.name:
                key = ("accessibility", el.path, "Interactive element has empty accessible name")
                if key not in seen:
                    seen.add(key)
                    finding_id = f"a11y_empty_name_{obs.step}_{el.uix}"
                    findings.append(Finding(
                        finding_id=finding_id,
                        category="accessibility",
                        severity="medium",
                        description="Interactive element has empty accessible name",
                        step=obs.step,
                        element_name=el.path,
                        evidence_refs=[f"{obs.step:03d}_marked.png"]
                    ))
            
            # 2. role='button'/'link' with tabindex='-1'
            if el.role in ("button", "link") and el.tabindex == "-1":
                key = ("accessibility", el.path, "Button or link has tabindex=-1 (unreachable by keyboard)")
                if key not in seen:
                    seen.add(key)
                    finding_id = f"a11y_tabindex_neg1_{obs.step}_{el.uix}"
                    findings.append(Finding(
                        finding_id=finding_id,
                        category="accessibility",
                        severity="medium",
                        description="Button or link has tabindex=-1 (unreachable by keyboard)",
                        step=obs.step,
                        element_name=el.path,
                        evidence_refs=[f"{obs.step:03d}_marked.png"]
                    ))
            
            # 3. Image-only link/button with no alt/aria-label
            if el.role in ("button", "link") and el.tag in ("img", "svg") and not el.alt and not el.aria_label:
                key = ("accessibility", el.path, "Image-only button or link has no alt or aria-label")
                if key not in seen:
                    seen.add(key)
                    finding_id = f"a11y_img_no_alt_{obs.step}_{el.uix}"
                    findings.append(Finding(
                        finding_id=finding_id,
                        category="accessibility",
                        severity="medium",
                        description="Image-only button or link has no alt or aria-label",
                        step=obs.step,
                        element_name=el.path,
                        evidence_refs=[f"{obs.step:03d}_marked.png"]
                    ))
            
            # 4. Form input with no associated label (name derived from placeholder alone)
            if el.role in ("textbox", "searchbox", "combobox", "checkbox", "radio") and el.name:
                # Check if name comes only from placeholder (no label, aria-label, aria-labelledby)
                has_label = bool(el.aria_label or el.aria_labelledby)
                # Note: can't detect <label for=> from current inventory
                # We'll flag if name == placeholder as a heuristic
                if not has_label and el.input_type != "hidden":
                    key = ("accessibility", el.path, "Form input may lack associated label (name from placeholder only)")
                    if key not in seen:
                        seen.add(key)
                        finding_id = f"a11y_input_no_label_{obs.step}_{el.uix}"
                        findings.append(Finding(
                            finding_id=finding_id,
                            category="accessibility",
                            severity="low",
                            description="Form input may lack associated label (name from placeholder only)",
                            step=obs.step,
                            element_name=el.path,
                            evidence_refs=[f"{obs.step:03d}_marked.png"]
                        ))
            
            # 5. Positive tabindex values (break natural focus order)
            if el.tabindex and el.tabindex.isdigit() and int(el.tabindex) > 0:
                key = ("accessibility", el.path, f"Positive tabindex={el.tabindex} breaks natural focus order")
                if key not in seen:
                    seen.add(key)
                    finding_id = f"a11y_tabindex_pos_{obs.step}_{el.uix}"
                    findings.append(Finding(
                        finding_id=finding_id,
                        category="accessibility",
                        severity="low",
                        description=f"Positive tabindex={el.tabindex} breaks natural focus order",
                        step=obs.step,
                        element_name=el.path,
                        evidence_refs=[f"{obs.step:03d}_marked.png"]
                    ))
    
    return findings


def collect_all_findings(step_records: list[StepRecord], observations: list[Observation]) -> list[Finding]:
    """Combine all three sources, deduplicate, return list."""
    all_findings: list[Finding] = []
    all_findings.extend(collect_model_findings(step_records))
    all_findings.extend(collect_behavioural_findings(step_records))
    all_findings.extend(collect_static_a11y_findings(observations))
    
    # Deduplicate by (category, element_name, description)
    seen: set[tuple[str, str, str]] = set()
    deduped: list[Finding] = []
    for f in all_findings:
        key = (f.category, f.element_name or "", f.description)
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    return deduped