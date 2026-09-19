from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Optional
from playwright.sync_api import BrowserContext, Page, sync_playwright, Playwright

from .config import Config
from .types import Observation, Element


class BrowserManager:
    def __init__(self, config: Config):
        self.config = config
        self.playwright: Optional[Playwright] = None
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._dialog_texts: list[str] = []

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.config.browser.headless,
            slow_mo=self.config.browser.slow_mo_ms,
        )
        self.context = self.browser.new_context(
            viewport=self.config.browser.viewport,
            locale=self.config.browser.locale,
            timezone_id=self.config.browser.timezone,
        )
        self._setup_dialog_handler()
        self._setup_popup_handler()
        self._inject_observer_script()
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def _setup_dialog_handler(self):
        def on_dialog(dialog):
            self._dialog_texts.append(f"{dialog.type}: {dialog.message}")
            if self.config.policy.allow_dialog_accept and dialog.type in ("alert", "beforeunload"):
                dialog.accept()
            else:
                dialog.dismiss()

        self.context.on("dialog", on_dialog)

    def _setup_popup_handler(self):
        def on_page(page: Page):
            # Skip initial blank page
            if page.url == "about:blank":
                return
            self._dialog_texts.append(f"popup: {page.url}")
            if any(page.url.startswith(f"https://{d}") or page.url.startswith(f"http://{d}") 
                   for d in self.config.policy.domain_allowlist):
                self.page = page
            else:
                page.close()

        self.context.on("page", on_page)

    def _inject_observer_script(self):
        observer_js = Path(__file__).parent.joinpath("js", "observer.js").read_text()
        self.context.add_init_script(observer_js)

    def goto(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")

    def capture_observation(self, step: int, max_elements: int) -> Observation:
        # Inject inventory script
        inventory_js = Path(__file__).parent.joinpath("js", "inventory.js").read_text()
        inventory_js = inventory_js.replace("__MAX_ELEMENTS__", str(max_elements))

        all_elements = []
        all_frames = ["main"]
        frame_id_map = {"main": self.page.main_frame}

        # Main frame
        result = self.page.main_frame.evaluate(inventory_js)
        for el in result["elements"]:
            el["frame_id"] = "main"
            all_elements.append(Element(**el))

        # Other frames
        for i, frame in enumerate(self.page.frames[1:], 1):
            try:
                frame_id = f"f{i}:{frame.url.split('/')[2] if '://' in frame.url else 'unknown'}"
                frame_id_map[frame_id] = frame
                all_frames.append(frame_id)
                result = frame.evaluate(inventory_js)
                for el in result["elements"]:
                    el["frame_id"] = frame_id
                    all_elements.append(Element(**el))
            except Exception:
                pass  # Skip detached frames

        # State hash
        sorted_elements = sorted(all_elements, key=lambda e: (e.role, e.name))
        state_hash_parts = [result["url"].split("?")[0].split("#")[0]]
        state_hash_parts.extend(f"{e.role}:{e.name}" for e in sorted_elements)
        import hashlib
        state_hash = hashlib.sha256("|".join(state_hash_parts).encode()).hexdigest()[:16]

        return Observation(
            step=step,
            url=result["url"],
            title=result["title"],
            frames=all_frames,
            elements=all_elements,
            scroll_y=result["scroll_y"],
            max_scroll=result["max_scroll"],
            state_hash=state_hash,
            captured_at=__import__("datetime").datetime.now(),
        )

    def draw_marks(self) -> None:
        mark_js = Path(__file__).parent.joinpath("js", "mark.js").read_text()
        self.page.evaluate(mark_js + "\ndraw();")

    def clear_marks(self) -> None:
        mark_js = Path(__file__).parent.joinpath("js", "mark.js").read_text()
        self.page.evaluate(mark_js + "\nclear();")

    def screenshot(self, path: Path, scale: float = 0.75) -> None:
        self.page.screenshot(path=str(path), scale="css" if scale == 1.0 else "device")

    def wait_for_quiet(self, quiet_ms: int, max_wait_ms: int) -> dict[str, Any]:
        # Wait for DOM content loaded
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=max_wait_ms)
        except Exception:
            pass

        # Poll for mutation quiet
        start = time.time()
        while True:
            since = self.page.evaluate("window.__uixMut ? window.__uixMut.since() : null")
            if since is not None and since >= quiet_ms:
                return {"state": "QUIESCENT", "wait_ms": int((time.time() - start) * 1000), "mutations_seen": self.page.evaluate("window.__uixMut.count()")}
            if (time.time() - start) * 1000 >= max_wait_ms:
                return {"state": "CONTINUOUSLY_ACTIVE", "wait_ms": max_wait_ms, "mutations_seen": self.page.evaluate("window.__uixMut.count()")}
            time.sleep(0.1)

    def get_dialog_texts(self) -> list[str]:
        texts = self._dialog_texts
        self._dialog_texts = []
        return texts


def create_browser_manager(config: Config) -> BrowserManager:
    return BrowserManager(config)