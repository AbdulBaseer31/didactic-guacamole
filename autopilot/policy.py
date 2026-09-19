from __future__ import annotations

from typing import Any, Optional
from .types import ProposedAction, ValidatedAction, TargetDescriptor, Element


class PolicyGate:
    def __init__(self, config: Any):
        self.config = config
        self.blocked_classes = set(config.policy.blocked_classes)
        self.domain_allowlist = config.policy.domain_allowlist
        self.allow_dialog_accept = config.policy.allow_dialog_accept
        self.secrets = getattr(config, 'secrets', {})

    def classify_action(self, action: ProposedAction, element: Optional[Element]) -> str:
        if action.type == "finish":
            return "observation"
        if action.type == "goto":
            return "navigation"
        if action.type in ("type", "select"):
            return "data_entry"
        if action.type == "click" and element:
            href = element.href
            if href and any(kw in (element.name + " " + (href or "")).lower() for kw in ["pay", "place order", "buy now", "purchase", "complete purchase", "subscribe", "checkout"]):
                return "payment"
            if any(kw in element.name.lower() for kw in ["delete", "remove account", "deactivate", "close account", "erase", "wipe", "permanently"]):
                return "destructive"
            if any(kw in element.name.lower() for kw in ["send", "post", "publish", "tweet", "submit review", "email"]):
                return "external_comms"
            if any(kw in element.name.lower() for kw in ["change password", "update email", "security settings", "privacy settings", "2fa"]):
                return "account_change"
            if href and not any(href.startswith(f"https://{d}") or href.startswith(f"http://{d}") for d in self.domain_allowlist):
                return "navigation"
            return "observation"
        return "observation"

    def check_secrets(self, action: ProposedAction) -> Optional[str]:
        if action.value and action.value.startswith("$SECRET:"):
            secret_name = action.value[8:]
            if secret_name not in self.secrets:
                return f"Secret '{secret_name}' not found in scenario"
        return None

    def validate(self, action: ProposedAction, descriptor: Optional[TargetDescriptor], element: Optional[Element]) -> ValidatedAction:
        action_class = self.classify_action(action, element)
        block_reason = None
        decision = "allow"
        
        # Check blocked classes
        if action_class in self.blocked_classes:
            decision = "block"
            block_reason = f"Action class '{action_class}' is blocked"
        
        # Check domain allowlist for navigation
        if action_class == "navigation" and action.type == "click" and element and element.href:
            if self.domain_allowlist and not any(element.href.startswith(f"https://{d}") or element.href.startswith(f"http://{d}") for d in self.domain_allowlist):
                decision = "block"
                block_reason = f"Navigation to {element.href} not in allowlist"
        
        # Check secrets
        secret_error = self.check_secrets(action)
        if secret_error:
            decision = "block"
            block_reason = secret_error
        
        # Check disabled
        if element and element.disabled:
            decision = "block"
            block_reason = "Target element is disabled"
        
        return ValidatedAction(
            action=action,
            descriptor=descriptor,
            action_class=action_class,
            decision=decision,
            block_reason=block_reason,
            resolver_confidence=1.0,
            candidates_considered=1,
        )


def create_policy_gate(config: Any) -> PolicyGate:
    return PolicyGate(config)