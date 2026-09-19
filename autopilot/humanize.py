from __future__ import annotations

from .types import ProposedAction, StepRecord

# Translation table per FRONTEND_DETAIL.txt section 1.5 - keep any new user-facing
# string here in sync with that spec so the CLI and the future dashboard agree on
# the same plain-English phrasing.

_ACTION_VERBS = {
    "click": "Clicking",
    "type": "Typing into",
    "select": "Choosing an option in",
    "hover": "Pointing at",
    "scroll": "Scrolling the page",
    "press": "Pressing a key on",
    "goto": "Opening",
    "finish": "Wrapping up",
}


def humanize_action(action: ProposedAction) -> str:
    verb = _ACTION_VERBS.get(action.type, action.type.capitalize())
    if action.type == "goto" and action.url:
        return f"{verb} {action.url}"
    if action.type == "scroll":
        return f"{verb} {action.direction or 'down'}"
    if action.type == "finish":
        return "Finishing up: goal achieved" if action.success else "Finishing up: could not complete the goal"
    return verb


def humanize_step(record: StepRecord) -> str:
    """One plain-English line summarizing what happened during a step."""
    action_line = humanize_action(record.proposed)

    if record.validated.decision == "block":
        reason = record.validated.block_reason or "not allowed in test mode"
        return f"Step {record.step}: The system prevented this action - {humanize_block_reason(reason)}"

    if not record.executed:
        return f"Step {record.step}: {action_line} - this didn't work ({record.error or 'unknown reason'})"

    if record.transition == "url_change":
        outcome = "took us to a new page"
    elif record.transition == "dom_change":
        outcome = "changed what's on screen"
    else:
        outcome = "didn't seem to change anything"

    return f"Step {record.step}: {action_line} - {outcome}"


def humanize_block_reason(reason: str) -> str:
    lowered = reason.lower()
    if "payment" in lowered:
        return "entering payment details isn't allowed in test mode"
    if "destructive" in lowered:
        return "this action could permanently change or delete something, so it was blocked"
    if "external_comms" in lowered:
        return "sending a message or email isn't allowed in test mode"
    if "account_change" in lowered:
        return "changing account settings isn't allowed in test mode"
    return reason


def humanize_stuck_loop(same_state_count: int) -> str:
    return f"The test got stuck repeating the same action ({same_state_count}x in a row) - stopped automatically"


def humanize_budget_exceeded() -> str:
    return "The test ran out of time and was stopped automatically"


def humanize_observing(url: str) -> str:
    return f"Opening {url} and reading what's on screen"


def humanize_outcome(outcome: str) -> str:
    return {
        "success": "Done - the goal was achieved",
        "failed": "Done - the goal could not be achieved",
        "stuck_loop": "Stopped - the test got stuck repeating itself",
        "budget_exhausted": "Stopped - ran out of time",
        "max_steps_reached": "Stopped - reached the step limit before finishing",
        "blocked": "Stopped - a required action was blocked by policy",
    }.get(outcome, f"Finished with outcome: {outcome}")
