from __future__ import annotations

from typing import Any, Optional

from .types import Element, Observation, ProposedAction

# History is capped to the last N steps to keep prompts small, mirroring the
# rolling-window approach used by the Live/ reference project's Gemini agent.
HISTORY_LIMIT = 6

VALID_ACTION_TYPES = {"click", "type", "select", "hover", "scroll", "press", "goto", "finish"}


def _serialize_elements(elements: list[Element]) -> list[dict[str, Any]]:
    """Reduce the full Element model down to the compact menu an LLM should reason over."""
    return [
        {
            "uix": el.uix,
            "role": el.role,
            "name": el.name,
            "tag": el.tag,
            "disabled": el.disabled,
        }
        for el in elements
    ]


class GeminiPlanner:
    """Planner that will delegate action proposals to the Gemini API.

    This mirrors the interface of `autopilot.planner.DynamicPlanner` so it can be
    dropped into the existing step loop as a straight substitute:

        planner.propose_action(obs, goal, prev_action) -> ProposedAction

    The actual model call is intentionally left unimplemented - see `_call_gemini`
    below. Everything else here (element serialization, rolling history, error
    feedback, response parsing/validation, safe fallback on failure) is real and
    ready to use once that one method is filled in.
    """

    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []

    def _record(self, entry: dict[str, Any]) -> None:
        self.history.append(entry)
        if len(self.history) > HISTORY_LIMIT:
            self.history = self.history[-HISTORY_LIMIT:]

    def _call_gemini(
        self,
        goal: str,
        elements: list[dict[str, Any]],
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Call the Gemini API to decide the next action. NOT YET IMPLEMENTED.

        Fill this in with your own Gemini request/response handling. Contract:

        Input:
            goal      - natural language goal for the whole journey, unchanged
                        across calls.
            elements  - the current page's visible interactive elements, e.g.
                        [{"uix": 3, "role": "textbox", "name": "Username",
                          "tag": "input", "disabled": False}, ...]
            history   - up to the last HISTORY_LIMIT entries of
                        {"action": ..., "reasoning": ..., "outcome": ...} from
                        previous steps (outcome may be "ok" or an error string),
                        so the model can see and correct its own past mistakes.

        Required output: a dict matching autopilot.types.ProposedAction fields:
            {
                "type": one of "click" | "type" | "select" | "hover" | "scroll"
                         | "press" | "goto" | "finish",
                "uix": int | None,          # required for click/type/select/hover/press
                "value": str | None,        # text to type, option to select, etc.
                "key": str | None,          # key name for "press"
                "direction": "down" | "up" | None,   # for "scroll"
                "url": str | None,          # for "goto"
                "reasoning": str,           # short plain-English reason
                "success": bool | None,     # for "finish": whether the goal was met
            }

        Raise on failure (network error, bad JSON, etc.) - the caller
        (`propose_action`) already catches exceptions, records them into history,
        and falls back to a safe "finish" action so the CLI never crashes.
        """
        raise NotImplementedError(
            "GeminiPlanner._call_gemini is a stub. Plug in your Gemini API call here "
            "(model, request, and JSON parsing) - see the docstring for the exact "
            "input/output contract expected by propose_action()."
        )

    def propose_action(
        self,
        obs: Observation,
        goal: str,
        prev_action: Optional[ProposedAction] = None,
    ) -> ProposedAction:
        elements = _serialize_elements(obs.elements)

        try:
            raw = self._call_gemini(goal, elements, list(self.history))
        except Exception as exc:
            self._record({"action": "error", "reasoning": str(exc), "outcome": "error"})
            return ProposedAction(
                type="finish",
                success=False,
                reasoning=f"Planner could not decide on a next action: {exc}",
            )

        action_type = raw.get("type")
        if action_type not in VALID_ACTION_TYPES:
            error = f"Gemini returned an invalid action type: {action_type!r}"
            self._record({"action": raw, "reasoning": error, "outcome": "error"})
            return ProposedAction(type="finish", success=False, reasoning=error)

        try:
            action = ProposedAction(
                type=action_type,
                uix=raw.get("uix"),
                value=raw.get("value"),
                key=raw.get("key"),
                direction=raw.get("direction"),
                url=raw.get("url"),
                reasoning=raw.get("reasoning", ""),
                success=raw.get("success"),
            )
        except Exception as exc:
            error = f"Gemini response did not match the expected action shape: {exc}"
            self._record({"action": raw, "reasoning": error, "outcome": "error"})
            return ProposedAction(type="finish", success=False, reasoning=error)

        self._record({"action": action.type, "reasoning": action.reasoning, "outcome": "ok"})
        return action


def create_ai_planner() -> GeminiPlanner:
    return GeminiPlanner()
