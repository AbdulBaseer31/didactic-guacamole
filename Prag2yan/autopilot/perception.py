from __future__ import annotations

from pathlib import Path
from typing import Any
from playwright.sync_api import Page

from .browser import BrowserManager
from .types import Observation, Element


class Perception:
    def __init__(self, browser: BrowserManager, config: Any):
        self.browser = browser
        self.config = config

    def observe(self, step: int, url: str) -> Observation:
        self.browser.goto(url)
        self.browser.wait_for_quiet(
            self.config.stabilization.quiet_ms,
            self.config.stabilization.max_wait_ms
        )
        obs = self.browser.capture_observation(step, self.config.perception.max_elements)
        return obs

    def capture_step_observation(self, step: int) -> Observation:
        obs = self.browser.capture_observation(step, self.config.perception.max_elements)
        return obs

    def take_screenshots(self, step: int, run_dir: Path, scale: float) -> tuple[str, str, str]:
        """Take before, marked, after screenshots. Returns relative paths."""
        before_path = run_dir / "steps" / f"{step:03d}_before.png"
        marked_path = run_dir / "steps" / f"{step:03d}_marked.png"
        after_path = run_dir / "steps" / f"{step:03d}_after.png"

        before_path.parent.mkdir(parents=True, exist_ok=True)

        # Before
        self.browser.screenshot(before_path, scale)

        # Marked
        self.browser.draw_marks()
        self.browser.screenshot(marked_path, scale)
        self.browser.clear_marks()

        # After will be captured after action execution
        return (
            before_path.name,
            marked_path.name,
            after_path.name
        )