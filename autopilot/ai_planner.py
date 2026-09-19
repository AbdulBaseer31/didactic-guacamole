from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Optional

from .types import Element, Observation, ProposedAction

# History is capped to the last N steps to keep prompts small, mirroring the
# rolling-window approach used by the Live/ reference project's Gemini agent.
HISTORY_LIMIT = 6

VALID_ACTION_TYPES = {"click", "type", "select", "hover", "scroll", "press", "goto", "finish"}

API_KEY_ENV_VAR = "GEMINI_API_KEY"

# Priority-ordered fallback chain of Gemini models, plus each one's own minimum
# call interval derived from its published RPM limit (60 / RPM, so a step never
# fires faster than that model's own quota resets). Sourced from a free-tier
# rate-limit export (Modelratecsv.csv, gitignored - not shipped/read at
# runtime): only models with a nonzero RPM/RPD were kept, ordered by daily
# quota (RPD) then per-minute quota (RPM), since the "*-lite" tiers on this
# account carry far more headroom (RPD 500 vs 20) than the plain "flash" tiers.
# A different API key (different project/tier) can see different numbers
# entirely - that's exactly why this is a *chain with per-model pacing* rather
# than a single hardcoded model: whichever entries actually have quota on the
# key in use will work, and the ones that don't just get skipped/cooled down.
DEFAULT_MODEL_CHAIN: list[tuple[str, float]] = [
    ("gemini-3.5-flash-lite", 4.0),   # RPM 15, RPD 500
    ("gemini-3.1-flash-lite", 4.0),   # RPM 15, RPD 500
    ("gemini-2.5-flash-lite", 6.0),   # RPM 10, RPD 20
    ("gemini-3.8-flash", 12.0),       # RPM 5,  RPD 20
    ("gemini-3.7-flash", 12.0),
    ("gemini-3.6-flash", 12.0),
    ("gemini-3.5-flash", 12.0),
    ("gemini-3-flash", 12.0),
    ("gemini-2.5-flash", 12.0),
]
# Fallback pacing for any model named via an override that isn't in the table
# above - conservative, matching the tightest known tier (5 RPM).
DEFAULT_MIN_INTERVAL_S = 12.0

# Env var overrides so a different API key/project (different available
# models, different fresh rate limits) can retarget this without code changes.
MODELS_ENV_VAR = "AUTOPILOT_GEMINI_MODELS"          # comma-separated priority list
MODEL_ENV_VAR = "AUTOPILOT_GEMINI_MODEL"            # single-model override (legacy)
MIN_INTERVAL_ENV_VAR = "AUTOPILOT_GEMINI_MIN_INTERVAL_S"  # blanket interval override

# How long a model that just got rate-limited is skipped before being retried.
# A bit over a minute so a per-minute (RPM) quota window has time to clear.
MODEL_COOLDOWN_S = 65.0
# One quick retry on the same model for a plainly transient (non-rate-limit)
# error before giving up on it for this call and trying the next model.
TRANSIENT_RETRY_DELAY_S = 1.5

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)

_SYSTEM_INSTRUCTION = """You are driving a web browser step by step to accomplish a goal.
You will be given the goal, a numbered list of the currently visible interactive
elements on the page, and a short history of your own recent actions (and whether
they worked). Reply with a single JSON object - no prose, no markdown fences -
describing exactly one next action:

{
  "type": "click" | "type" | "select" | "hover" | "scroll" | "press" | "goto" | "finish",
  "uix": <int, the element's uix - required for click/type/select/hover/press>,
  "value": <string to type or option to select, or null>,
  "key": <key name for "press", or null>,
  "direction": "down" | "up" | null,
  "url": <url for "goto", or null>,
  "reasoning": "<one short plain-English sentence>",
  "success": <true|false, only for "finish": whether the goal was actually achieved>
}

Pick "finish" with success=true only once the goal is clearly satisfied (e.g. a
confirmation message or the expected end state is visible). If your last action's
outcome in history was an error or "blocked", do not repeat the exact same action -
try a different element or approach instead."""


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


def _extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object out of a model response, tolerating stray code fences/prose."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(text)
        if match:
            return json.loads(match.group(0))
        raise


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(token in message for token in ("429", "resource_exhausted", "rate limit", "quota"))


def _resolve_model_chain() -> list[tuple[str, float]]:
    """Build the priority-ordered (model, min_interval_s) chain to try, honoring
    env overrides so a different key/project/tier can retarget this entirely."""
    override = os.getenv(MODELS_ENV_VAR)
    if override:
        names = [m.strip() for m in override.split(",") if m.strip()]
    else:
        single = os.getenv(MODEL_ENV_VAR)
        names = [single] if single else [name for name, _ in DEFAULT_MODEL_CHAIN]

    blanket_interval = os.getenv(MIN_INTERVAL_ENV_VAR)
    default_intervals = dict(DEFAULT_MODEL_CHAIN)
    if blanket_interval:
        interval = float(blanket_interval)
        return [(name, interval) for name in names]
    return [(name, default_intervals.get(name, DEFAULT_MIN_INTERVAL_S)) for name in names]


class GeminiPlanner:
    """Planner that delegates action proposals to the Gemini API.

    Mirrors the interface of `autopilot.planner.DynamicPlanner` so it drops into
    the existing step loop as a straight substitute:

        planner.propose_action(obs, goal, prev_action) -> ProposedAction

    Calls a priority-ordered chain of Gemini models (see DEFAULT_MODEL_CHAIN)
    rather than a single fixed model: each model is paced to its own known rate
    limit, and if one is rate-limited it's put on a short cooldown and the next
    model in the chain is tried immediately, so a single exhausted quota doesn't
    stall (or crash) a run.
    """

    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []
        self._cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._client = None
        self._model_chain = _resolve_model_chain()
        self._last_call_ts: dict[str, float] = {}
        self._cooldown_until: dict[str, float] = {}

    def _record(self, entry: dict[str, Any]) -> None:
        self.history.append(entry)
        if len(self.history) > HISTORY_LIMIT:
            self.history = self.history[-HISTORY_LIMIT:]

    def _get_client(self):
        if self._client is None:
            api_key = os.getenv(API_KEY_ENV_VAR)
            if not api_key:
                raise RuntimeError(
                    f"{API_KEY_ENV_VAR} is not set - add it to your .env file before "
                    "running the interactive command."
                )
            from google import genai

            self._client = genai.Client(api_key=api_key)
        return self._client

    def _throttle(self, model: str, min_interval_s: float) -> None:
        """Enforce model's own minimum call interval, independent of other models."""
        elapsed = time.monotonic() - self._last_call_ts.get(model, 0.0)
        remaining = min_interval_s - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _build_prompt(
        self,
        goal: str,
        elements: list[dict[str, Any]],
        history: list[dict[str, Any]],
    ) -> str:
        return (
            f"Goal: {goal}\n\n"
            f"Visible elements:\n{json.dumps(elements, indent=None)}\n\n"
            f"Recent history (most recent last):\n{json.dumps(history, indent=None)}\n\n"
            "Respond with the JSON action object now."
        )

    def _call_gemini(
        self,
        goal: str,
        elements: list[dict[str, Any]],
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Call Gemini to decide the next action, switching models on rate limits.

        Input/output contract:
            goal      - natural language goal for the whole journey.
            elements  - visible interactive elements, e.g.
                        [{"uix": 3, "role": "textbox", "name": "Username",
                          "tag": "input", "disabled": False}, ...]
            history   - up to the last HISTORY_LIMIT {"action", "reasoning", "outcome"}
                        entries from previous steps.
        Returns a dict matching autopilot.types.ProposedAction fields. Raises only
        once every model in the chain has failed - the caller (`propose_action`)
        catches that, records it into history, and falls back to a safe "finish"
        action so the CLI never crashes.
        """
        from google.genai import types

        client = self._get_client()
        prompt = self._build_prompt(goal, elements, history)

        now = time.monotonic()
        candidates = [(m, i) for m, i in self._model_chain if self._cooldown_until.get(m, 0.0) <= now]
        if not candidates:
            # Every model is cooling down - use whichever clears soonest rather
            # than failing the step outright.
            m, i = min(self._model_chain, key=lambda pair: self._cooldown_until.get(pair[0], 0.0))
            candidates = [(m, i)]

        last_exc: Optional[Exception] = None
        for model, min_interval_s in candidates:
            for attempt in range(2):  # one quick retry per model for transient errors
                self._throttle(model, min_interval_s)
                self._last_call_ts[model] = time.monotonic()
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=_SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            temperature=0.0,
                        ),
                    )
                    return _extract_json(response.text or "")
                except Exception as exc:
                    last_exc = exc
                    if _is_rate_limit_error(exc):
                        self._cooldown_until[model] = time.monotonic() + MODEL_COOLDOWN_S
                        print(f"  (Gemini: {model} hit a rate limit - switching to the next model)")
                        break  # don't retry a rate-limited model, move to the next one
                    if attempt == 0:
                        time.sleep(TRANSIENT_RETRY_DELAY_S)
                        continue
                    break  # gave this model one retry, move to the next one

        assert last_exc is not None
        raise last_exc

    def propose_action(
        self,
        obs: Observation,
        goal: str,
        prev_action: Optional[ProposedAction] = None,
    ) -> ProposedAction:
        elements = _serialize_elements(obs.elements)
        # Keyed on the DOM state hash *and* the full recent-history window, not
        # state_hash alone: state_hash only reflects element roles/names, so a
        # "type" action (which changes a field's value, not what elements
        # exist) leaves it unchanged - keying on state_hash alone would replay
        # the same cached "type username" decision forever instead of
        # progressing to "type password". Requiring the history window to also
        # match means a cache hit only happens when we're in a genuinely
        # identical situation, including our own recent memory of it (i.e. a
        # real stuck loop), not just a superficially similar DOM.
        history_fingerprint = tuple(
            (h.get("action"), h.get("reasoning"), h.get("outcome")) for h in self.history
        )
        cache_key = (goal, obs.state_hash, history_fingerprint)

        if cache_key in self._cache:
            raw = self._cache[cache_key]
        else:
            try:
                raw = self._call_gemini(goal, elements, list(self.history))
            except Exception as exc:
                self._record({"action": "error", "reasoning": str(exc), "outcome": "error"})
                return ProposedAction(
                    type="finish",
                    success=False,
                    reasoning=f"Planner could not decide on a next action: {exc}",
                )
            self._cache[cache_key] = raw

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
