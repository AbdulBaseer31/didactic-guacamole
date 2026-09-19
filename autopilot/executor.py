from __future__ import annotations

import time
from typing import Any, Optional
from playwright.sync_api import Locator, Page
from .types import ProposedAction, ValidatedAction, Observation, Element


class Executor:
    def __init__(self, config: Any):
        self.config = config
        self.step_timeout_ms = config.budgets.step_timeout_s * 1000

    def _resolve_value(self, value: str) -> str:
        if value and value.startswith("$SECRET:"):
            secret_name = value[8:]
            return getattr(self.config, 'secrets', {}).get(secret_name, value)
        return value

    def execute(self, page: Page, locator: Optional[Locator], action: ProposedAction, element: Optional[Element]) -> tuple[bool, Optional[str]]:
        try:
            if action.type == "click":
                if locator:
                    locator.click(timeout=self.step_timeout_ms)
                return True, None
            elif action.type == "type":
                if locator:
                    resolved_value = self._resolve_value(action.value or "")
                    locator.fill(resolved_value, timeout=self.step_timeout_ms)
                return True, None
            elif action.type == "select":
                if locator and action.value:
                    locator.select_option(action.value, timeout=self.step_timeout_ms)
                return True, None
            elif action.type == "hover":
                if locator:
                    locator.hover(timeout=self.step_timeout_ms)
                return True, None
            elif action.type == "press":
                if locator and action.key:
                    locator.press(action.key, timeout=self.step_timeout_ms)
                return True, None
            elif action.type == "scroll":
                direction = -600 if action.direction == "up" else 600
                page.mouse.wheel(0, direction)
                return True, None
            elif action.type == "goto":
                if action.url:
                    page.goto(action.url, wait_until="domcontentloaded", timeout=self.step_timeout_ms)
                return True, None
            elif action.type == "finish":
                return True, None
            else:
                return False, f"Unknown action type: {action.type}"
        except Exception as e:
            return False, str(e)

    def wait_for_quiet(self, browser_manager: Any) -> dict[str, Any]:
        return browser_manager.wait_for_quiet(
            self.config.stabilization.quiet_ms,
            self.config.stabilization.max_wait_ms
        )

    def settle(self):
        time.sleep(self.config.stabilization.post_action_settle_ms / 1000.0)


def create_executor(config: Any) -> Executor:
    return Executor(config)