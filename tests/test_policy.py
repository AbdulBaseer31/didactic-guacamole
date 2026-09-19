from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock
import json

from autopilot.types import ProposedAction, Element, TargetDescriptor, StepRecord, ValidatedAction, Observation
from autopilot.policy import create_policy_gate
from autopilot.config import PolicyConfig


class TestPolicy:
    """Tests for policy gate: blocks payment class; blocks off-allowlist navigation; secrets never in serialized StepRecord."""

    def make_policy_gate(self, domain_allowlist=None, blocked_classes=None):
        """Create a policy gate with test config."""
        config = Mock()
        config.policy = PolicyConfig(
            domain_allowlist=domain_allowlist or ["example.com"],
            blocked_classes=blocked_classes or ["payment", "destructive", "external_comms", "account_change"],
            allow_dialog_accept=False
        )
        config.secrets = {}
        return create_policy_gate(config)

    def test_blocks_payment_class(self):
        """Policy blocks actions classified as payment."""
        policy = self.make_policy_gate()
        
        element = Element(
            uix=1, frame_id="main", role="button", name="Place Order", tag="button",
            input_type=None, disabled=False, checked=None, expanded=None, value=None,
            href=None, path="button", box=(0, 0, 100, 30)
        )
        
        proposed = ProposedAction(
            type="click", uix=1, value=None, key=None, direction=None, url=None,
            reasoning="Place order", success=None, findings=[]
        )
        
        descriptor = TargetDescriptor(
            frame_id="main", role="button", name="Place Order", tag="button",
            path="button", ordinal=0
        )
        
        validated = policy.validate(proposed, descriptor, element)
        
        assert validated.decision == "block"
        assert "payment" in validated.block_reason.lower()
        assert validated.action_class == "payment"

    def test_blocks_off_allowlist_navigation(self):
        """Policy blocks navigation to domain not in allowlist."""
        policy = self.make_policy_gate(domain_allowlist=["example.com"])
        
        element = Element(
            uix=1, frame_id="main", role="link", name="External Site", tag="a",
            input_type=None, disabled=False, checked=None, expanded=None, value=None,
            href="https://evil.com/page", path="a", box=(0, 0, 100, 30)
        )
        
        proposed = ProposedAction(
            type="click", uix=1, value=None, key=None, direction=None, url=None,
            reasoning="Go to external", success=None, findings=[]
        )
        
        descriptor = TargetDescriptor(
            frame_id="main", role="link", name="External Site", tag="a",
            path="a", ordinal=0
        )
        
        validated = policy.validate(proposed, descriptor, element)
        
        assert validated.decision == "block"
        assert "allowlist" in validated.block_reason.lower() or "domain" in validated.block_reason.lower()
        assert validated.action_class == "navigation"

    def test_allows_allowlist_navigation(self):
        """Policy allows navigation to domain in allowlist."""
        policy = self.make_policy_gate(domain_allowlist=["playwright.dev"])
        
        element = Element(
            uix=1, frame_id="main", role="link", name="Allowed Site", tag="a",
            input_type=None, disabled=False, checked=None, expanded=None, value=None,
            href="https://playwright.dev/docs", path="a", box=(0, 0, 100, 30)
        )
        
        proposed = ProposedAction(
            type="click", uix=1, value=None, key=None, direction=None, url=None,
            reasoning="Go to allowed", success=None, findings=[]
        )
        
        descriptor = TargetDescriptor(
            frame_id="main", role="link", name="Allowed Site", tag="a",
            path="a", ordinal=0
        )
        
        validated = policy.validate(proposed, descriptor, element)
        
        assert validated.decision == "allow"
        assert validated.action_class == "navigation"

    def test_blocks_goto_off_allowlist(self):
        """Policy blocks goto to domain not in allowlist."""
        policy = self.make_policy_gate(domain_allowlist=["example.com"])
        
        proposed = ProposedAction(
            type="goto", uix=None, value=None, key=None, direction=None, url="https://evil.com",
            reasoning="Go to evil", success=None, findings=[]
        )
        
        validated = policy.validate(proposed, None, None)
        
        assert validated.decision == "block"
        assert validated.action_class == "navigation"

    def test_secrets_never_in_serialized_steprecord(self):
        """Secret values ($SECRET:NAME) are never resolved in serialized StepRecord."""
        policy = self.make_policy_gate(domain_allowlist=["saucedemo.com"])
        
        element = Element(
            uix=1, frame_id="main", role="textbox", name="Password", tag="input",
            input_type="password", disabled=False, checked=None, expanded=None, value=None,
            href=None, path="input", box=(0, 0, 200, 30)
        )
        
        proposed = ProposedAction(
            type="type", uix=1, value="$SECRET:SAUCE_PASSWORD", key=None, direction=None, url=None,
            reasoning="Enter password", success=None, findings=[]
        )
        
        descriptor = TargetDescriptor(
            frame_id="main", role="textbox", name="Password", tag="input",
            path="input", ordinal=0
        )
        
        validated = policy.validate(proposed, descriptor, element)
        
        # The proposed value should remain as $SECRET:SAUCE_PASSWORD in validated action
        assert validated.action.value == "$SECRET:SAUCE_PASSWORD"
        
        # Simulate StepRecord serialization
        obs = Observation(
            step=1, url="https://saucedemo.com", title="Test", frames=["main"],
            elements=[element], scroll_y=0, max_scroll=100,
            state_hash="abc123", captured_at=__import__("datetime").datetime.now()
        )
        
        step_record = StepRecord(
            step=1,
            observation=obs,
            proposed=proposed,
            validated=validated,
            executed=False,
            error=None,
            stabilization={},
            before_png="001_before.png",
            marked_png="001_marked.png",
            after_png="001_after.png",
            duration_ms=100,
            transition="dom_change"
        )
        
        # Serialize to JSON
        json_str = step_record.model_dump_json()
        
        # Secret should never appear in serialized form
        assert "secret_sauce" not in json_str.lower()
        assert "$SECRET:SAUCE_PASSWORD" in json_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])