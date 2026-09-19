from __future__ import annotations

from typing import Any, Optional
from playwright.sync_api import Locator, Page
from .types import ProposedAction, Observation, TargetDescriptor, Element


class Resolver:
    def resolve(self, page: Page, proposed: ProposedAction, obs: Observation) -> tuple[Optional[Locator], Optional[TargetDescriptor], float, int]:
        if proposed.uix is None:
            return None, None, 0.0, 0
        
        # Find element by uix
        element = None
        for el in obs.elements:
            if el.uix == proposed.uix:
                element = el
                break
        
        if not element:
            return None, None, 0.0, 0
        
        # Build descriptor
        descriptor = TargetDescriptor(
            frame_id=element.frame_id,
            role=element.role,
            name=element.name,
            tag=element.tag,
            path=element.path,
            ordinal=0,
        )
        
        # Get locator
        frame = page.main_frame if element.frame_id == "main" else None
        if not frame:
            for f in page.frames:
                if f.url.split('/')[2] if '://' in f.url else 'unknown' == element.frame_id.split(':')[-1]:
                    frame = f
                    break
        
        if not frame:
            frame = page.main_frame
        
        locator = frame.locator(f'[data-uix="{proposed.uix}"]')
        
        return locator, descriptor, 1.0, 1


def create_resolver() -> Resolver:
    return Resolver()