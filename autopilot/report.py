from __future__ import annotations

from pathlib import Path
from typing import Any
from .types import StepRecord, Finding, RunManifest
import base64
from io import BytesIO
from PIL import Image
import json
from datetime import datetime


def generate_report(
    run_dir: Path,
    manifest: RunManifest,
    step_records: list[StepRecord],
    findings: list[Finding],
    config: Any,
    profile_name: str,
    model_id: str
) -> Path:
    """Produce run_dir/report.html with self-contained HTML report."""
    
    def png_to_base64_jpeg(png_path: Path) -> str:
        try:
            with Image.open(png_path) as img:
                img = img.convert("RGB")
                w, h = img.size
                if w > 640:
                    new_h = int(h * 640 / w)
                    img = img.resize((640, new_h), Image.Resampling.LANCZOS)
                buf = BytesIO()
                img.save(buf, "JPEG", quality=70, optimize=True)
                return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return ""
    
    # Build step data with images
    steps_data = []
    for sr in step_records:
        before_path = run_dir / "steps" / sr.before_png
        after_path = run_dir / "steps" / sr.after_png
        before_b64 = png_to_base64_jpeg(before_path) if before_path.exists() else ""
        after_b64 = png_to_base64_jpeg(after_path) if after_path.exists() else ""
        
        action_desc = sr.proposed.type
        target_name = ""
        if sr.validated.descriptor:
            target_name = sr.validated.descriptor.name
        elif sr.proposed.uix:
            target_name = f"uix:{sr.proposed.uix}"
        
        transition_class = sr.transition.replace("_", "-")
        
        steps_data.append({
            "step": sr.step,
            "action_type": sr.proposed.type,
            "target_name": target_name,
            "reasoning": sr.proposed.reasoning,
            "transition": sr.transition,
            "transition_class": transition_class,
            "duration_ms": sr.duration_ms,
            "before_b64": before_b64,
            "after_b64": after_b64,
            "is_blocked": sr.validated.decision == "block",
            "block_reason": sr.validated.block_reason,
            "error": sr.error,
        })
    
    # Group findings by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings_by_severity: dict[str, list[Finding]] = {"high": [], "medium": [], "low": []}
    for f in findings:
        if f.severity in findings_by_severity:
            findings_by_severity[f.severity].append(f)
    
    # Calculate duration
    duration_s = 0
    if manifest.end_time and manifest.start_time:
        duration_s = int((manifest.end_time - manifest.start_time).total_seconds())
    
    # Outcome badge
    outcome = manifest.outcome or "unknown"
    outcome_class = outcome.replace("_", "-")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autopilot Run Report - {manifest.run_id}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; line-height: 1.6; color: #1a1a2e; background: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
        
        /* Header */
        header {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .header-row {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; }}
        h1 {{ font-size: 1.5rem; font-weight: 600; color: #1a1a2e; }}
        .badges {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .badge {{ padding: 6px 12px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
        .badge-success {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-failed {{ background: #fce4ec; color: #c62828; }}
        .badge-blocked {{ background: #fff3e0; color: #ef6c00; }}
        .badge-budget_exhausted {{ background: #e3f2fd; color: #1565c0; }}
        .badge-stuck_loop {{ background: #f3e5f5; color: #7b1fa2; }}
        .badge-unknown {{ background: #eceff1; color: #455a64; }}
        
        .meta {{ display: flex; flex-wrap: wrap; gap: 16px; margin-top: 16px; font-size: 0.875rem; color: #4a4a6a; }}
        .meta-item {{ display: flex; align-items: center; gap: 6px; }}
        .meta-label {{ font-weight: 500; color: #6b6b8a; }}
        
        /* Findings Panel */
        .section {{ background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .section-title {{ font-size: 1.125rem; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
        .section-title::before {{ content: ''; width: 4px; height: 24px; background: #e5007d; border-radius: 2px; }}
        
        .findings-list {{ display: flex; flex-direction: column; gap: 12px; }}
        .finding {{ padding: 16px; border-radius: 8px; border-left: 4px solid; background: #fafafa; transition: box-shadow 0.2s; }}
        .finding:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        .finding-high {{ border-color: #c62828; background: #fdf2f2; }}
        .finding-medium {{ border-color: #ef6c00; background: #fffbf0; }}
        .finding-low {{ border-color: #1565c0; background: #eef4fc; }}
        .finding-header {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 8px; }}
        .finding-category {{ text-transform: capitalize; font-size: 0.7rem; font-weight: 600; padding: 3px 8px; border-radius: 4px; }}
        .cat-ux_friction {{ background: #fff3e0; color: #ef6c00; }}
        .cat-accessibility {{ background: #e3f2fd; color: #1565c0; }}
        .cat-error_state {{ background: #fce4ec; color: #c62828; }}
        .cat-performance {{ background: #f3e5f5; color: #7b1fa2; }}
        .finding-severity {{ font-size: 0.7rem; font-weight: 600; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; }}
        .sev-high {{ background: #c62828; color: #fff; }}
        .sev-medium {{ background: #ef6c00; color: #fff; }}
        .sev-low {{ background: #1565c0; color: #fff; }}
        .finding-step {{ font-size: 0.75rem; color: #6b6b8a; font-family: monospace; }}
        .finding-desc {{ font-size: 0.875rem; color: #1a1a2e; }}
        .finding-evidence {{ margin-top: 8px; font-size: 0.7rem; color: #888; font-family: monospace; }}
        
        /* Step Timeline */
        .step {{ padding: 20px; border-radius: 8px; background: #fff; border: 1px solid #e8e8ee; margin-bottom: 16px; }}
        .step:hover {{ border-color: #e5007d; box-shadow: 0 4px 16px rgba(229,0,125,0.1); }}
        .step-header {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 12px; }}
        .step-number {{ font-size: 1.5rem; font-weight: 700; color: #e5007d; font-family: monospace; }}
        .step-action {{ font-weight: 600; text-transform: capitalize; }}
        .step-target {{ color: #4a4a6a; font-size: 0.875rem; }}
        .step-transition {{ padding: 4px 10px; border-radius: 999px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }}
        .trans-url-change {{ background: #e8f5e9; color: #2e7d32; }}
        .trans-dom-change {{ background: #e3f2fd; color: #1565c0; }}
        .trans-no-change {{ background: #fff3e0; color: #ef6c00; }}
        .step-reasoning {{ font-size: 0.875rem; color: #3a3a5a; margin-bottom: 12px; padding: 12px; background: #f5f5f7; border-radius: 6px; font-style: italic; }}
        .step-blocked {{ background: #fff3e0; border: 1px solid #ffb700; border-radius: 6px; padding: 12px; margin-bottom: 12px; }}
        .step-blocked-label {{ font-weight: 600; color: #ef6c00; margin-bottom: 4px; }}
        .step-images {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
        .step-image {{ text-align: center; }}
        .step-image-label {{ font-size: 0.7rem; font-weight: 600; text-transform: uppercase; color: #888; margin-bottom: 6px; letter-spacing: 0.5px; }}
        .step-image img {{ max-width: 100%; height: auto; border-radius: 6px; border: 1px solid #e8e8ee; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
        .step-error {{ color: #c62828; font-size: 0.8rem; font-family: monospace; background: #fdf2f2; padding: 8px; border-radius: 4px; margin-top: 8px; }}
        
        /* No findings state */
        .empty-state {{ text-align: center; padding: 32px; color: #888; }}
        .empty-state svg {{ width: 48px; height: 48px; margin-bottom: 12px; opacity: 0.5; }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 16px; }}
            .step-images {{ grid-template-columns: 1fr; }}
            .header-row {{ flex-direction: column; align-items: flex-start; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-row">
                <h1>{manifest.goal}</h1>
                <div class="badges">
                    <span class="badge badge-{outcome_class}">{outcome.replace('_', ' ').title()}</span>
                </div>
            </div>
            <div class="meta">
                <div class="meta-item"><span class="meta-label">Run ID:</span> {manifest.run_id}</div>
                <div class="meta-item"><span class="meta-label">Model:</span> {model_id}</div>
                <div class="meta-item"><span class="meta-label">Profile:</span> {profile_name}</div>
                <div class="meta-item"><span class="meta-label">Duration:</span> {duration_s}s</div>
                <div class="meta-item"><span class="meta-label">Steps:</span> {manifest.step_count}</div>
                <div class="meta-item"><span class="meta-label">Start URL:</span> {manifest.start_url}</div>
            </div>
        </header>
        
        <!-- Findings Panel -->
        <section class="section" id="findings">
            <h2 class="section-title">Findings ({len(findings)} total)</h2>
            <div class="findings-list">
"""
    
    if findings:
        for severity in ["high", "medium", "low"]:
            for f in findings_by_severity[severity]:
                evidence_str = ", ".join(f.evidence_refs) if f.evidence_refs else "none"
                html += f"""
                <div class="finding finding-{f.severity}">
                    <div class="finding-header">
                        <span class="finding-category cat-{f.category}">{f.category.replace('_', ' ')}</span>
                        <span class="finding-severity sev-{f.severity}">{f.severity}</span>
                        <span class="finding-step">Step {f.step}</span>
                    </div>
                    <div class="finding-desc">{f.description}</div>
                    {f'<div class="finding-evidence">Evidence: {evidence_str}</div>' if f.evidence_refs else ''}
                </div>
"""
    else:
        html += """
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <p>No findings detected</p>
                </div>
"""
    
    html += """
            </div>
        </section>
        
        <!-- Step Timeline -->
        <section class="section">
            <h2 class="section-title">Step Timeline</h2>
"""
    
    for step in steps_data:
        html += f"""
            <div class="step" id="step-{step['step']}">
                <div class="step-header">
                    <span class="step-number">{step['step']:03d}</span>
                    <span class="step-action">{step['action_type']}</span>
                    <span class="step-target">{step['target_name'] or '-'}</span>
                    <span class="step-transition trans-{step['transition_class']}">{step['transition'].replace('_', ' ')}</span>
                    <span style="margin-left: auto; color: #888; font-size: 0.8rem; font-family: monospace;">{step['duration_ms']}ms</span>
                </div>
                <div class="step-reasoning">{step['reasoning']}</div>
"""
        
        if step['is_blocked'] and step['block_reason']:
            html += f"""
                <div class="step-blocked">
                    <div class="step-blocked-label">Policy Blocked</div>
                    <div>{step['block_reason']}</div>
                </div>
"""
        
        if step['error']:
            html += f"""
                <div class="step-error">Error: {step['error']}</div>
"""
        
        html += f"""
                <div class="step-images">
                    <div class="step-image">
                        <div class="step-image-label">Before</div>
                        {'<img src="data:image/jpeg;base64,' + step['before_b64'] + '" alt="Before">' if step['before_b64'] else '<div style="height:200px;background:#f0f0f0;display:flex;align-items:center;justify-content:center;color:#888;border-radius:6px;">No image</div>'}
                    </div>
                    <div class="step-image">
                        <div class="step-image-label">After</div>
                        {'<img src="data:image/jpeg;base64,' + step['after_b64'] + '" alt="After">' if step['after_b64'] else '<div style="height:200px;background:#f0f0f0;display:flex;align-items:center;justify-content:center;color:#888;border-radius:6px;">No image</div>'}
                    </div>
                </div>
            </div>
"""
    
    html += """
        </section>
    </div>
</body>
</html>
"""
    
    report_path = run_dir / "report.html"
    report_path.write_text(html, encoding="utf-8")
    return report_path