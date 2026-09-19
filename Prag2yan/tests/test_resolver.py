from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock

from autopilot.types import ProposedAction, Observation, Element, TargetDescriptor


class TestResolver:
    """Tests for resolver behavior (rejects unknown uix; rejects ambiguous matches)."""

    def test_rejects_unknown_uix(self):
        """Resolver rejects uix not present in observation."""
        from autopilot.resolver import resolve
        
        obs = Observation(
            step=1,
            url="https://example.com",
            title="Test",
            frames=["main"],
            elements=[
                Element(uix=1, frame_id="main", role="button", name="Submit", tag="button", 
                       input_type=None, disabled=False, checked=None, expanded=None, value=None, 
                       href=None, path="button", box=(0, 0, 100, 30)),
            ],
            scroll_y=0,
            max_scroll=100,
            state_hash="abc123",
            captured_at=__import__("datetime").datetime.now(),
        )
        
        proposed = ProposedAction(
            type="click", uix=999, value=None, key=None, direction=None, url=None,
            reasoning="Click submit", success=None, findings=[]
        )
        
        page = Mock()
        locator, descriptor, confidence, candidates = resolve(page, proposed, obs)
        
        assert locator is None
        assert descriptor is None
        assert confidence == 0.0
        assert candidates == 0

    def test_rejects_ambiguous_match_tie_without_ordinal(self):
        """Resolver rejects when two elements have same (role, name, tag) and no ordinal disambiguation."""
        from autopilot.resolver import resolve
        
        obs = Observation(
            step=1,
            url="https://example.com",
            title="Test",
            frames=["main"],
            elements=[
                Element(uix=1, frame_id="main", role="button", name="Submit", tag="button",
                       input_type=None, disabled=False, checked=None, expanded=None, value=None,
                       href=None, path="button:nth-of-type(1)", box=(0, 0, 100, 30)),
                Element(uix=2, frame_id="main", role="button", name="Submit", tag="button",
                       input_type=None, disabled=False, checked=None, expanded=None, value=None,
                       href=None, path="button:nth-of-type(2)", box=(0, 50, 100, 30)),
            ],
            scroll_y=0,
            max_scroll=100,
            state_hash="abc123",
            captured_at=__import__("datetime").datetime.now(),
        )
        
        proposed = ProposedAction(
            type="click", uix=1, value=None, key=None, direction=None, url=None,
            reasoning="Click submit", success=None, findings=[]
        )
        
        page = Mock()
        # Mock frame.evaluate to return elements with same score
        page.main_frame = Mock()
        page.main_frame.evaluate = Mock(return_value={
            "elements": [
                {"uix": 1, "role": "button", "name": "Submit", "tag": "button", "path": "button:nth-of-type(1)"},
                {"uix": 2, "role": "button", "name": "Submit", "tag": "button", "path": "button:nth-of-type(2)"},
            ],
            "url": "https://example.com",
            "title": "Test",
            "scroll_y": 0,
            "max_scroll": 100,
        })
        page.frames = [page.main_frame]
        
        locator, descriptor, confidence, candidates = resolve(page, proposed, obs)
        
        assert locator is None
        assert descriptor is None
        assert confidence == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])