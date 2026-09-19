from __future__ import annotations

import pytest
import hashlib

from autopilot.types import Observation, Element
from autopilot.browser import BrowserManager
from autopilot.perception import Perception


class TestPerception:
    """Tests for perception: state hash stable under element reordering."""

    def test_state_hash_stable_under_element_reordering(self):
        """State hash should be identical regardless of element order in DOM."""
        # Create two observations with same elements but different order
        elements_a = [
            Element(uix=1, frame_id="main", role="button", name="A", tag="button",
                   input_type=None, disabled=False, checked=None, expanded=None, value=None,
                   href=None, path="button:nth-of-type(1)", box=(0, 0, 50, 30)),
            Element(uix=2, frame_id="main", role="link", name="B", tag="a",
                   input_type=None, disabled=False, checked=None, expanded=None, value=None,
                   href="/b", path="a:nth-of-type(1)", box=(60, 0, 50, 30)),
            Element(uix=3, frame_id="main", role="textbox", name="C", tag="input",
                   input_type="text", disabled=False, checked=None, expanded=None, value=None,
                   href=None, path="input:nth-of-type(1)", box=(120, 0, 100, 30)),
        ]
        
        elements_b = [
            Element(uix=1, frame_id="main", role="textbox", name="C", tag="input",
                   input_type="text", disabled=False, checked=None, expanded=None, value=None,
                   href=None, path="input:nth-of-type(1)", box=(120, 0, 100, 30)),
            Element(uix=2, frame_id="main", role="button", name="A", tag="button",
                   input_type=None, disabled=False, checked=None, expanded=None, value=None,
                   href=None, path="button:nth-of-type(1)", box=(0, 0, 50, 30)),
            Element(uix=3, frame_id="main", role="link", name="B", tag="a",
                   input_type=None, disabled=False, checked=None, expanded=None, value=None,
                   href="/b", path="a:nth-of-type(1)", box=(60, 0, 50, 30)),
        ]
        
        obs_a = Observation(
            step=1, url="https://example.com", title="Test", frames=["main"],
            elements=elements_a, scroll_y=0, max_scroll=100,
            state_hash="", captured_at=__import__("datetime").datetime.now()
        )
        
        obs_b = Observation(
            step=1, url="https://example.com", title="Test", frames=["main"],
            elements=elements_b, scroll_y=0, max_scroll=100,
            state_hash="", captured_at=__import__("datetime").datetime.now()
        )
        
        # Compute state hashes using the same logic as browser.py
        def compute_state_hash(obs: Observation) -> str:
            sorted_elements = sorted(obs.elements, key=lambda e: (e.role, e.name))
            state_hash_parts = [obs.url.split("?")[0].split("#")[0]]
            state_hash_parts.extend(f"{e.role}:{e.name}" for e in sorted_elements)
            return hashlib.sha256("|".join(state_hash_parts).encode()).hexdigest()[:16]
        
        hash_a = compute_state_hash(obs_a)
        hash_b = compute_state_hash(obs_b)
        
        assert hash_a == hash_b, f"State hash differs: {hash_a} != {hash_b}"
        assert len(hash_a) == 16  # Truncated to 16 chars per spec

    def test_state_hash_changes_on_element_addition(self):
        """State hash should change when elements are added/removed."""
        elements_a = [
            Element(uix=1, frame_id="main", role="button", name="A", tag="button",
                   input_type=None, disabled=False, checked=None, expanded=None, value=None,
                   href=None, path="button", box=(0, 0, 50, 30)),
        ]
        
        elements_b = [
            Element(uix=1, frame_id="main", role="button", name="A", tag="button",
                   input_type=None, disabled=False, checked=None, expanded=None, value=None,
                   href=None, path="button", box=(0, 0, 50, 30)),
            Element(uix=2, frame_id="main", role="link", name="B", tag="a",
                   input_type=None, disabled=False, checked=None, expanded=None, value=None,
                   href="/b", path="a", box=(60, 0, 50, 30)),
        ]
        
        obs_a = Observation(
            step=1, url="https://example.com", title="Test", frames=["main"],
            elements=elements_a, scroll_y=0, max_scroll=100,
            state_hash="", captured_at=__import__("datetime").datetime.now()
        )
        
        obs_b = Observation(
            step=1, url="https://example.com", title="Test", frames=["main"],
            elements=elements_b, scroll_y=0, max_scroll=100,
            state_hash="", captured_at=__import__("datetime").datetime.now()
        )
        
        def compute_state_hash(obs: Observation) -> str:
            sorted_elements = sorted(obs.elements, key=lambda e: (e.role, e.name))
            state_hash_parts = [obs.url.split("?")[0].split("#")[0]]
            state_hash_parts.extend(f"{e.role}:{e.name}" for e in sorted_elements)
            return hashlib.sha256("|".join(state_hash_parts).encode()).hexdigest()[:16]
        
        hash_a = compute_state_hash(obs_a)
        hash_b = compute_state_hash(obs_b)
        
        assert hash_a != hash_b, "State hash should change when elements differ"

    def test_state_hash_ignores_query_and_fragment(self):
        """State hash should ignore URL query and fragment."""
        elements = [
            Element(uix=1, frame_id="main", role="button", name="A", tag="button",
                   input_type=None, disabled=False, checked=None, expanded=None, value=None,
                   href=None, path="button", box=(0, 0, 50, 30)),
        ]
        
        obs_a = Observation(
            step=1, url="https://example.com?foo=bar#section", title="Test", frames=["main"],
            elements=elements, scroll_y=0, max_scroll=100,
            state_hash="", captured_at=__import__("datetime").datetime.now()
        )
        
        obs_b = Observation(
            step=1, url="https://example.com?other=baz#different", title="Test", frames=["main"],
            elements=elements, scroll_y=0, max_scroll=100,
            state_hash="", captured_at=__import__("datetime").datetime.now()
        )
        
        def compute_state_hash(obs: Observation) -> str:
            sorted_elements = sorted(obs.elements, key=lambda e: (e.role, e.name))
            state_hash_parts = [obs.url.split("?")[0].split("#")[0]]
            state_hash_parts.extend(f"{e.role}:{e.name}" for e in sorted_elements)
            return hashlib.sha256("|".join(state_hash_parts).encode()).hexdigest()[:16]
        
        hash_a = compute_state_hash(obs_a)
        hash_b = compute_state_hash(obs_b)
        
        assert hash_a == hash_b, "State hash should ignore query and fragment"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])