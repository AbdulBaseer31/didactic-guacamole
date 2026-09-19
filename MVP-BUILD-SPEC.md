# PROBLEM STATEMENT:

"Build an agentic, framework-agnostic, black-box UI/UX testing engine that accepts high-level natural language intent descriptions and autonomously navigates target applications to discover usability friction, map multi-path user journeys, detect UI/UX regressions, and audit accessibility tree structures. The system should treat the target application as a true black box relying on visible UI cues, layout context, or standard accessibility nodes rather than proprietary test hooks or embedded SDKs.



Intent-Based Action: Autonomous navigation driven entirely by natural language intent without pre-scripted steps.

Multi-Path Exploration: Actively discovering alternate routes, redundant loops, and dead ends.

UX Friction and Regression Detection: Identifying usability bottlenecks during execution and surfacing regressions between application versions.

Accessibility Verification: Auditing standard accessibility tree nodes for missing labels, ARIA roles, and keyboard focus order.

Zero Application Instrumentation: Operating strictly as a black box with no source code access, hardcoded DOM selectors, embedded SDKs, or proprietary hooks.

Visual Tracing & Audit Reporting: Logging every action step-by-step with visual screenshots and compiling findings into a comprehensive audit report.

Target Scope: A minimum proof-of-concept covering at least one target platform (web was chosen).

# AUTOPILOT — MVP Build Specification

**Autonomous black-box web journey agent with a deterministic safety gate and a full evidence trail.**

Version 1.0-MVP · Derived from `pdf3.pdf` v1.0, scope-reduced for a single-session build.

---

## 0. Instructions to the building agent — read this first

You are implementing this document end to end. It is the contract; where it disagrees with the source PDF, **this document wins**.

**Hard rules:**

1. Work through §12 (Build Order) in order. Do not start a checkpoint before the previous one's verification command passes.
2. **Commit after every checkpoint** with the message `checkpoint N: <name>`. This is not optional — it is the human's rollback path.
3. Every file listed in §3 must exist and be importable when you finish. No empty directories, no `TODO` stubs in shipped code paths.
4. If you cannot make a checkpoint pass after **three** attempts, stop working on it, write what failed into `STATUS.md`, and move to the next checkpoint. Do not silently continue on a broken foundation, and do not spend the whole night on one module.
5. Before you stop for any reason, write `STATUS.md` (template in §14).
6. Do not add dependencies beyond §2. Do not add stealth plugins, proxy rotation, or fingerprint spoofing — deliberately out of scope.
7. Do not invent requirements from the source PDF. If this document doesn't specify it, it isn't in the MVP.

**Target:** ~1,500 lines of Python across 11 files. If a module is ballooning past its line budget in §3, you are over-engineering it.

---

## 1. What this is

A Python CLI that takes a natural-language goal and a start URL, drives Chromium through a web journey to achieve it, and emits a reproducible evidence trail plus an HTML report.

```bash
autopilot run --goal "Buy a Sauce Labs Backpack and complete checkout" \
              --url https://www.saucedemo.com \
              --profile primary
```

**Core rule, inherited from the source spec and non-negotiable:** the model proposes actions; deterministic Python resolves, validates, executes, observes and records them. No model output ever reaches Playwright directly.

```
observe → mark → plan (AI) → resolve → validate → execute → stabilize → record
   ↑                                                                      │
   └──────────────────────────────────────────────────────────────────────┘
```

### In scope

- Single linear journey, one browser context, one run at a time
- Element perception via injected JS (role, accessible name, state, geometry)
- Set-of-Mark screenshot annotation
- Claude as planner, one action per turn, via forced tool use
- Deterministic target resolver with ambiguity rejection
- Policy gate: domain allowlist, blocked action classes, dialog safety
- Bounded stabilization (mutation-quiet, never `networkidle`)
- Per-step evidence: before/after screenshots, JSON trace
- Self-contained HTML report
- Lightweight UX friction + accessibility findings
- Two API key profiles, selectable at startup

### Explicitly out of scope

Branch exploration trees · regression baselines · CDP AX tree · OOPIF coordinate maths · exact multimodal token accounting · TOTP · stealth / proxy rotation / fingerprint spoofing · parallel runs · real purchases on live commerce sites.

---

## 2. Environment

- **Python 3.11+**
- **Chromium via Playwright** (`playwright install chromium`)

`requirements.txt`:

```
playwright>=1.47
anthropic>=0.40
pydantic>=2.7
rich>=13.7
Pillow>=10.3
python-dotenv>=1.0
```

Floors, not pins. After install run `pip freeze > requirements.lock.txt` and commit it, so tomorrow's environment matches tonight's.

Use **Playwright's sync API** (`playwright.sync_api`). No asyncio. Avoids a whole class of event-loop bugs under time pressure.

Setup, to be captured verbatim in `README.md`:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env     # then fill in keys
```

---

## 3. Repository layout

Exactly these files. Line budgets are guidance — significant overruns mean over-engineering.

```
autopilot/
├── README.md
├── STATUS.md                  # written by you before you stop
├── requirements.txt
├── requirements.lock.txt
├── .env.example
├── .gitignore                 # MUST include .env and runs/
├── config/
│   ├── default.yaml           # budgets, policy, viewport
│   └── scenarios/
│       ├── saucedemo.yaml
│       ├── search.yaml
│       └── youtube.yaml
├── autopilot/
│   ├── __init__.py
│   ├── cli.py                 # ~120  entry point, profile selection, run wiring
│   ├── config.py              # ~110  config + profile loading, startup validation
│   ├── types.py               # ~130  all dataclasses / pydantic models
│   ├── browser.py             # ~150  context lifecycle, dialogs, popups, screenshots
│   ├── perception.py          # ~180  JS inventory, SoM overlay, state hashing
│   ├── js/
│   │   ├── inventory.js       # element harvest
│   │   ├── mark.js            # SoM overlay draw/clear
│   │   └── observer.js        # mutation-quiet init script
│   ├── planner.py             # ~170  Claude client, tool schema, history
│   ├── resolver.py            # ~130  descriptor → locator, ambiguity rejection
│   ├── policy.py              # ~120  action classes, allowlist, gate
│   ├── executor.py            # ~150  Playwright actions + stabilization
│   ├── evidence.py            # ~110  run dir, trace writer, manifest
│   ├── findings.py            # ~110  UX friction + a11y checks
│   └── report.py              # ~160  self-contained HTML
├── tests/
│   ├── test_resolver.py
│   ├── test_policy.py
│   └── test_perception.py
└── scripts/
    └── smoke.sh               # runs all Tier A scenarios
```

`runs/` is created at runtime and **git-ignored**. Screenshots can contain anything the browser rendered.

---

## 4. Configuration and API key profiles

### 4.1 `.env.example`

```bash
# Profile: primary
AUTOPILOT_KEY_PRIMARY=sk-ant-...
AUTOPILOT_MODEL_PRIMARY=claude-sonnet-5

# Profile: sonnet45  (borrowed key)
AUTOPILOT_KEY_SONNET45=sk-ant-...
AUTOPILOT_MODEL_SONNET45=claude-sonnet-4-5-20250929
```

### 4.2 Profile selection

Resolution order: `--profile <name>` flag → `AUTOPILOT_PROFILE` env var → **interactive prompt**.

The interactive prompt lists only profiles whose key env var is actually populated:

```
Which API profile?
  1) primary    claude-sonnet-5              [key found]
  2) sonnet45   claude-sonnet-4-5-20250929   [key found]
> 
```

If exactly one profile has a key, select it automatically and log the choice. If none do, exit code 2 with a message naming the expected env vars.

### 4.3 Startup validation — required

Before opening a browser, send a minimal request (`max_tokens: 16`, one short user message) on the selected profile. On failure, print the status code and the model ID and **exit non-zero**. Add `--validate-only` to run this check and exit.

This exists so a dead key or retired model surfaces tonight, not on stage.

### 4.4 Sampling parameters — do not send them

Never pass `temperature`, `top_p`, or `top_k`. Newer models reject non-default values with a 400, and Anthropic's Python SDK v1.0+ removed the parameters entirely — passing them raises `TypeError`. Omitting them keeps every profile working.

### 4.5 `config/default.yaml`

```yaml
browser:
  headless: false          # false for the demo — people want to watch it
  viewport: {width: 1280, height: 800}
  locale: en-US
  timezone: Asia/Kolkata
  slow_mo_ms: 120          # visible, not painful. 0 for the smoke suite.

budgets:
  max_steps: 25
  max_wall_clock_s: 300
  max_total_input_tokens: 400000
  step_timeout_s: 30

stabilization:
  quiet_ms: 400
  max_wait_ms: 6000
  post_action_settle_ms: 150

perception:
  max_elements: 120
  screenshot_scale: 0.75

policy:
  domain_allowlist: []     # REQUIRED per scenario; empty means block all navigation
  blocked_classes: [payment, destructive, external_comms, account_change]
  allow_dialog_accept: false
```

### 4.6 Scenario files

Scenario files override defaults and carry the goal:

```yaml
# config/scenarios/saucedemo.yaml
name: saucedemo_checkout
goal: >
  Log in as standard_user with password secret_sauce, add the
  Sauce Labs Backpack to the cart, and complete checkout with
  first name Ada, last name Lovelace, postal code 500001.
  Finish when you see the order confirmation.
start_url: https://www.saucedemo.com
policy:
  domain_allowlist: [saucedemo.com]
budgets:
  max_steps: 22
secrets:
  SAUCE_PASSWORD: secret_sauce   # referenced by name, never sent to the model
```

---

## 5. Data contracts

`types.py`. Use pydantic models. These are binding — every module reads and writes these shapes.

```python
class Element(BaseModel):
    uix: int                       # short-lived mark ID, valid for THIS capture only
    frame_id: str                  # "main" or "f<index>:<origin>"
    role: str                      # link|button|textbox|checkbox|combobox|...
    name: str                      # accessible name, normalized, <=120 chars
    tag: str
    input_type: str | None
    disabled: bool
    checked: bool | None
    expanded: str | None
    value: str | None              # None for type=password, always
    href: str | None
    path: str                      # css path, max depth 6
    box: tuple[int, int, int, int] # x, y, w, h (viewport coords)

class Observation(BaseModel):
    step: int
    url: str
    title: str
    frames: list[str]
    elements: list[Element]
    scroll_y: int
    max_scroll: int
    state_hash: str                # see §6.4
    captured_at: datetime

class TargetDescriptor(BaseModel):
    """Durable. Survives re-render. This is what gets persisted, never `uix`."""
    frame_id: str
    role: str
    name: str
    tag: str
    path: str
    ordinal: int                   # index among identical (role,name,tag) at capture

class ProposedAction(BaseModel):
    type: Literal["click","type","select","hover","scroll","press","goto","finish"]
    uix: int | None
    value: str | None              # for type=="type": literal text, OR "$SECRET:NAME"
    key: str | None                # for type=="press": e.g. "Enter"
    direction: Literal["down","up"] | None
    url: str | None                # for type=="goto"
    reasoning: str                 # <=200 chars, shown in report
    success: bool | None           # for type=="finish"
    findings: list[FindingDraft] = []

class ValidatedAction(BaseModel):
    action: ProposedAction
    descriptor: TargetDescriptor | None
    action_class: str              # observation|navigation|data_entry|payment|destructive|...
    decision: Literal["allow","block"]
    block_reason: str | None
    resolver_confidence: float     # 0.0 - 1.0
    candidates_considered: int

class StepRecord(BaseModel):
    step: int
    observation: Observation
    proposed: ProposedAction
    validated: ValidatedAction
    executed: bool
    error: str | None
    stabilization: dict            # {state, wait_ms, mutations_seen}
    before_png: str                # relative path
    marked_png: str
    after_png: str
    duration_ms: int
    transition: str                # "url_change" | "dom_change" | "no_change"

class Finding(BaseModel):
    finding_id: str
    category: Literal["ux_friction","accessibility","error_state","performance"]
    severity: Literal["low","medium","high"]
    description: str
    step: int
    element_name: str | None
    evidence_refs: list[str]
```

**Rule the resolver depends on:** `uix` is a disposable alias for one capture. Nothing outside a single step may store or reuse it. Anything persisted uses `TargetDescriptor`. This is the fix for the ephemeral-ID replay flaw the source review flagged.

---

## 6. Perception

### 6.1 Element inventory (`js/inventory.js`)

Injected via `frame.evaluate()`. Runs in every frame, including cross-origin ones — Playwright's `Frame` objects work across origins transparently, so no CDP session or coordinate translation is needed.

```javascript
(() => {
  const MAX = __MAX_ELEMENTS__;
  const SEL = 'a[href], button, input:not([type="hidden"]), select, textarea, ' +
              'summary, [role], [onclick], [tabindex]:not([tabindex="-1"]), ' +
              '[contenteditable="true"]';

  const isVisible = el => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return false;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none') return false;
    if (parseFloat(s.opacity) < 0.05) return false;
    if (el.closest('[aria-hidden="true"]')) return false;
    return true;
  };

  const inViewport = el => {
    const r = el.getBoundingClientRect();
    return r.bottom > -50 && r.top < innerHeight + 50 &&
           r.right > -50 && r.left < innerWidth + 50;
  };

  const TAG_ROLE = {A:'link', BUTTON:'button', SELECT:'combobox',
                    TEXTAREA:'textbox', SUMMARY:'button'};

  const roleOf = el => {
    const explicit = el.getAttribute('role');
    if (explicit) return explicit.split(/\s+/)[0];
    if (el.tagName === 'INPUT') {
      const t = (el.type || 'text').toLowerCase();
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      if (t === 'search') return 'searchbox';
      if (['submit','button','reset','image'].includes(t)) return 'button';
      return 'textbox';
    }
    return TAG_ROLE[el.tagName] || el.tagName.toLowerCase();
  };

  const labelledBy = el => {
    const ids = el.getAttribute('aria-labelledby');
    if (!ids) return null;
    return ids.split(/\s+/)
              .map(i => (document.getElementById(i) || {}).innerText || '')
              .join(' ');
  };

  const nameOf = el => {
    const isBtnInput = el.tagName === 'INPUT' &&
                       ['submit','button'].includes((el.type || '').toLowerCase());
    const cands = [
      el.getAttribute('aria-label'),
      labelledBy(el),
      (el.labels && el.labels[0]) ? el.labels[0].innerText : null,
      el.getAttribute('placeholder'),
      el.getAttribute('alt'),
      el.getAttribute('title'),
      isBtnInput ? el.value : null,
      el.innerText,
      el.getAttribute('name'),
    ];
    for (const c of cands) {
      if (c && c.trim()) return c.trim().replace(/\s+/g, ' ').slice(0, 120);
    }
    return '';
  };

  const cssPath = el => {
    const parts = [];
    let cur = el, depth = 0;
    while (cur && cur.nodeType === 1 && depth < 6) {
      let seg = cur.tagName.toLowerCase();
      const p = cur.parentElement;
      if (p) {
        const sibs = [...p.children].filter(c => c.tagName === cur.tagName);
        if (sibs.length > 1) seg += `:nth-of-type(${sibs.indexOf(cur) + 1})`;
      }
      parts.unshift(seg);
      cur = p; depth++;
    }
    return parts.join('>');
  };

  document.querySelectorAll('[data-uix]').forEach(e => e.removeAttribute('data-uix'));

  const out = [];
  let n = 0;
  for (const el of document.querySelectorAll(SEL)) {
    if (!isVisible(el) || !inViewport(el)) continue;

    // collapse wrapper/child pairs that expose the same name
    const parentMarked = el.parentElement && el.parentElement.closest('[data-uix]');
    if (parentMarked && nameOf(parentMarked) === nameOf(el)) continue;

    if (++n > MAX) break;
    el.setAttribute('data-uix', String(n));
    const r = el.getBoundingClientRect();
    const isTextish = el.tagName === 'INPUT' || el.tagName === 'TEXTAREA';
    out.push({
      uix: n,
      role: roleOf(el),
      name: nameOf(el),
      tag: el.tagName.toLowerCase(),
      input_type: el.getAttribute('type'),
      disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
      checked: el.checked !== undefined ? el.checked : null,
      expanded: el.getAttribute('aria-expanded'),
      value: (isTextish && el.type !== 'password')
                ? String(el.value || '').slice(0, 60) : null,
      href: el.tagName === 'A' ? (el.getAttribute('href') || '').slice(0, 200) : null,
      path: cssPath(el),
      box: [Math.round(r.x), Math.round(r.y),
            Math.round(r.width), Math.round(r.height)],
    });
  }

  return {
    url: location.href, title: document.title,
    scroll_y: Math.round(scrollY),
    max_scroll: Math.round(document.body.scrollHeight),
    elements: out,
  };
})()
```

Never emit `value` for `type=password`. Not once, not redacted later — never captured.

Frame iteration: `page.main_frame` first, then `page.frames[1:]`. `frame_id` is `"main"` or `f"f{i}:{urlparse(frame.url).netloc}"`. On a detached frame, `evaluate()` raises — catch it and skip that frame. `uix` numbering continues across frames so IDs stay globally unique within a capture.

### 6.2 Set-of-Mark overlay (`js/mark.js`)

Two exported functions, `draw()` and `clear()`. `draw()` creates one `#__uix_overlay` container with `position:fixed; inset:0; z-index:2147483647; pointer-events:none`, and for every `[data-uix]` element adds a 2px outline box at its rect plus a small numbered badge at the rect's top-left. Use a high-contrast palette (magenta `#e5007d` outline, white text on magenta badge, 11px monospace). `clear()` removes the container.

Sequence per step: `before.png` → `draw()` → `marked.png` → `clear()`. Send **`marked.png`** to the model; keep the clean `before.png` for the report so the human sees the real page.

Badges must not shift layout — the container is `position:fixed` and `pointer-events:none`, so it can't. Never screenshot without calling `clear()` afterwards.

### 6.3 Stabilization (`js/observer.js`)

Registered with `context.add_init_script()` so it installs on every document in every frame automatically, including after navigation.

```javascript
(() => {
  if (window.__uixMut) return;
  let last = Date.now(), count = 0;
  const obs = new MutationObserver(m => { last = Date.now(); count += m.length; });
  const start = () => obs.observe(document.documentElement,
    {subtree: true, childList: true, attributes: true, characterData: true});
  if (document.documentElement) start();
  else document.addEventListener('DOMContentLoaded', start);
  window.__uixMut = { since: () => Date.now() - last, count: () => count };
})();
```

`wait_for_quiet(page, quiet_ms, max_wait_ms)`:

1. `page.wait_for_load_state("domcontentloaded")` with `max_wait_ms` timeout, swallowing timeouts.
2. Poll `window.__uixMut.since()` every 100ms until it exceeds `quiet_ms` or the total wait exceeds `max_wait_ms`.
3. Classify and return: `QUIESCENT` (quiet reached), `CONTINUOUSLY_ACTIVE` (hit `max_wait_ms` still mutating — proceed anyway, don't hang), `UNKNOWN` (observer missing, e.g. after a hard navigation; fall back to a flat 800ms).

**Do not use `wait_for_load_state("networkidle")`.** Playwright's own docs discourage it as a readiness signal and it hangs indefinitely on pages with polling, analytics beacons, or open websockets — which is most of them. Playwright's per-locator actionability checks already cover the majority of real waiting.

### 6.4 State hashing

`state_hash = sha256(url_without_query_fragment + "|" + "\n".join(f"{e.role}:{e.name}" for e in sorted(elements, key=lambda e: (e.role, e.name))))[:16]`

Used only for loop detection: if the same hash appears **3 times in a row**, inject a system note into the next planning turn — *"You have seen this exact page state 3 times. The previous approach is not working. Try a different element or scroll."* If it appears **5 times**, abort with `stuck_loop`. Note the sort: this is order-insensitive by design, so pure reordering (ads, carousels) doesn't read as a new state.

---

## 7. Planner

### 7.1 Tool-use, not JSON parsing

Do **not** ask for raw JSON and regex out code fences. Define a single tool and force it:

```python
tools=[{
    "name": "propose_action",
    "description": "Propose exactly one next action toward the goal.",
    "input_schema": { ... mirrors ProposedAction ... }
}],
tool_choice={"type": "tool", "name": "propose_action"}
```

Read `response.content`, find the first block with `type == "tool_use"`, validate `block.input` against `ProposedAction`. On `ValidationError`, retry once with the error text appended; on a second failure, abort the step with `error="planner_schema"`.

### 7.2 System prompt

```
You are the planning component of an autonomous web testing agent.

You receive a screenshot with numbered magenta badges on interactive
elements, and a matching list of those elements. Propose exactly ONE
next action toward the goal, using propose_action.

RULES
- Reference elements only by their badge number (uix). Never invent a
  number that is not in the list.
- One action per turn. Do not batch.
- Before typing into a field, click it first unless it is already focused.
- If an element you need is not visible, scroll rather than guessing.
- If the goal is achieved, call propose_action with type="finish" and
  success=true. If it is impossible, finish with success=false and
  explain in reasoning.
- Never attempt payment, account deletion, sending messages, or changing
  account settings. These are blocked and will be rejected.
- For secret values, pass "$SECRET:NAME" as value. Never guess a real
  credential.
- In `findings`, note genuine UX friction you observe: dead ends,
  unclear labels, error messages, elements that did nothing. Keep it
  empty when there is nothing real to report.
- `reasoning` must be under 200 characters.
```

### 7.3 User turn

```
GOAL: {goal}
STEP: {n} of {max_steps}
URL: {url}
PREVIOUS ACTION: {summary or "none"}
RESULT: {transition or error}

ELEMENTS:
[12] button "Add to cart"
[13] link "Sauce Labs Backpack"
[14] textbox "Username" value=""
[15] textbox "Password" (password)
...
```

Plus the marked screenshot as an image block. Format elements as one compact line each — `[uix] role "name" <flags>` — with flags only when true (`disabled`, `checked`, `expanded=true`, `value="..."`). This is far cheaper than JSON and reads better.

### 7.4 History management

Keep the last **4** turns in full. For older turns keep a one-line text summary only and **drop the images** — images dominate token cost and stale screenshots actively mislead the planner. Always keep the original goal in the system prompt where it can't scroll away.

Track `usage.input_tokens` from each response. At 85% of `max_total_input_tokens`, drop to 2 turns of history. At 95%, abort cleanly with `budget_exhausted` and write the report — never die mid-run with no artifacts.

---

## 8. Resolver

The trust boundary. `uix` from the model is untrusted input.

```python
def resolve(page, proposed: ProposedAction, obs: Observation
            ) -> tuple[Locator | None, TargetDescriptor | None, float, int]:
```

1. **Bounds check.** `proposed.uix` must exist in `obs.elements`. If not → `(None, None, 0.0, 0)`, resolver error `unknown_uix`. No fuzzy matching, no nearest-neighbour.
2. **Build the descriptor** from that element: `frame_id`, `role`, `name`, `tag`, `path`, and `ordinal` = its index among elements sharing `(role, name, tag)`.
3. **Re-capture the inventory for that frame** and score every candidate:
   - `(role, name, tag)` all equal → **+3**
   - `path` equal → **+2**
   - normalized name equal (casefold, collapse whitespace, strip punctuation) → **+1**
4. **Decide:**
   - Top score `< 3` → reject, `low_confidence`.
   - Top score tied with the runner-up **and** `ordinal` doesn't disambiguate → reject, `ambiguous`. Record both candidates in evidence.
   - Otherwise accept. `confidence = min(1.0, top_score / 6.0)`.
5. **Return** `frame.locator(f'[data-uix="{winner_uix}"]')`.

On rejection the step is **not** executed. Record the failure, re-observe, and feed the reason back to the planner next turn. Never guess, never fall back to clicking by coordinates. Two consecutive resolver rejections on the same descriptor → abort with `unresolvable_target`.

---

## 9. Policy gate

Runs **after** the resolver and **before** the executor. A valid DOM target is not proof the action is safe.

### 9.1 Classification

Classify from `(action.type, element.role, element.name, element.href)`. Name matching is casefolded substring against these lists:

| Class | Trigger |
|---|---|
| `payment` | `pay`, `place order`, `buy now`, `purchase`, `complete purchase`, `subscribe`, `checkout` **only when** the element also matches `pay`/`confirm order` |
| `destructive` | `delete`, `remove account`, `deactivate`, `close account`, `erase`, `wipe`, `permanently` |
| `external_comms` | `send`, `post`, `publish`, `tweet`, `submit review`, `email` |
| `account_change` | `change password`, `update email`, `security settings`, `privacy settings`, `2fa` |
| `navigation` | `type == "goto"`, or `click` on an element with an off-origin `href` |
| `data_entry` | `type == "type"` or `select` |
| `observation` | everything else |

### 9.2 Rules

1. **Blocked classes** (from config) → `decision="block"`. Record the attempt as a finding with `severity="high"`. Return the block reason to the planner so it routes around it. **Do not abort the run** — a blocked action is the safety layer working, and it's a highlight of the demo.
2. **Domain allowlist.** Any navigation whose target host is not the allowlist or a subdomain of it → block. An empty allowlist blocks all navigation. Off-origin *clicks* are checked against `href` before executing.
3. **Secrets.** If `value` starts with `$SECRET:`, look up the name in the scenario's `secrets` map. Missing → block. The resolved value goes to `locator.fill()` and **never** into the trace, the report, or model history. Persist `value="$SECRET:SAUCE_PASSWORD"` verbatim.
4. **Disabled targets** → block with `target_disabled`. Playwright would hang on actionability anyway.

### 9.3 Dialogs

Register a handler at context creation, before any navigation:

```python
def _on_dialog(dialog):
    record_dialog(dialog.type, dialog.message)
    if config.policy.allow_dialog_accept and dialog.type in ("alert", "beforeunload"):
        dialog.accept()
    else:
        dialog.dismiss()
```

**Never auto-accept a `confirm` or `prompt` dialog.** This is the one rule carried over verbatim from the source spec's §12, and it's the difference between a safe agent and one that clicks through "Permanently delete your account?". Every dialog's text is captured into evidence regardless of the decision.

Also handle `context.on("page", ...)` for popups: record the opener step, adopt the new page as active if it's on an allowlisted domain, otherwise close it and note it.

---

## 10. Executor

One function per action type. Every one goes through Playwright locators so actionability checks apply, with `timeout=step_timeout_s * 1000`.

| Action | Implementation |
|---|---|
| `click` | `locator.click()` |
| `type` | `locator.click()` then `locator.fill(value)`. Use `fill`, not `type` — it's atomic and doesn't fight debounced inputs. |
| `select` | `locator.select_option(value)` |
| `hover` | `locator.hover()` |
| `press` | `locator.press(key)` |
| `scroll` | `page.mouse.wheel(0, ±600)` |
| `goto` | `page.goto(url, wait_until="domcontentloaded")` |
| `finish` | Terminate the loop. |

**Retries:** one retry on `TimeoutError` only, after a fresh observation and re-resolve (the DOM may have re-rendered and wiped `data-uix`). Never retry an error that isn't a timeout.

**After every action:** `wait_for_quiet(...)`, then `sleep(post_action_settle_ms)`, then capture `after.png`.

**Transition classification:** compare pre/post `url` and `state_hash`. `url_change` > `dom_change` > `no_change`. Three consecutive `no_change` results emit a `ux_friction` finding — "element appeared interactive but produced no observable change" — which is a genuinely good thing to point at during the demo.

**Scroll progress:** replace any fixed scroll cap with progress-based stopping. If `scroll_y` doesn't increase after a `scroll` action, mark bottom-reached and tell the planner to stop scrolling.

---

## 11. Evidence, findings and report

### 11.1 Run directory

```
runs/<run_id>/                       # run_id = YYYYMMDD-HHMMSS-<goal-slug>
├── manifest.json
├── trace.jsonl                      # one StepRecord per line, flushed each step
├── findings.json
├── report.html
└── steps/
    ├── 001_before.png  001_marked.png  001_after.png
    └── ...
```

`manifest.json`: `run_id`, `goal`, `start_url`, `profile_name`, `model_id`, browser version, viewport, locale, timezone, config snapshot, policy snapshot, start/end time, outcome, total tokens, step count. Redact key values; store profile *name* only.

**Flush `trace.jsonl` after every step.** If the process dies at step 19 you still have 18 steps and can still produce a report. This matters more than anything else in this section.

Downscale screenshots to `screenshot_scale` on write. Full-size PNGs at 25 steps × 3 is a lot of disk for no benefit.

### 11.2 Findings

Three sources, all nearly free since the data is already captured:

**Model-reported** — the `findings` array on each proposed action. Category `ux_friction`.

**Behavioural** (from the executor): `no_change` after three interactive clicks; any resolver `ambiguous` rejection (two indistinguishable controls is a real usability defect); any policy block; any step exceeding 10s of stabilization (`performance`).

**Static accessibility** — five checks over the existing inventory. No new capture needed:

1. Interactive element with an empty accessible name
2. `role="button"`/`link` with `tabindex="-1"` (unreachable by keyboard)
3. Image-only link or button with no `alt` or `aria-label`
4. Form input with no associated label (name derived from `placeholder` alone)
5. Positive `tabindex` values (break natural focus order)

Deduplicate by `(category, element_name, description)` so a check firing on the same element across 20 steps produces one finding, not twenty.

Do **not** attempt contrast checks. Needs computed style plus background compositing, and it's a false-positive machine.

### 11.3 Report

One self-contained `report.html`. No external CSS, no CDN, no fonts — it has to open from `file://` on a conference-room laptop with no wifi.

- **Header:** goal, outcome badge (success / failed / blocked / budget), duration, step count, model, run ID
- **Findings panel:** grouped by severity, each linking to its step anchor
- **Step timeline:** per step — number, action type + target name, the planner's `reasoning`, transition badge, duration, and the before/after images side by side
- **Policy blocks rendered prominently in amber**, not hidden. They are the safety story.

Embed images as base64 JPEG at width 640, quality 70 (use Pillow), keeping full PNGs on disk. Keeps the report a single portable file at a few MB.

System font stack, dark-on-light, one accent colour. Clean and legible beats flashy. Restrained styling reads as more engineered, not less.

Print `file:///abs/path/report.html` to stdout at the end and open it automatically unless `--no-open`.

---

## 12. Build order — six checkpoints

Each checkpoint has a verification command. It passes or it doesn't. Commit after each.

### Checkpoint 1 — Skeleton and config *(~45 min)*
`cli.py`, `config.py`, `types.py`, `.env.example`, `requirements.txt`, `.gitignore`.
Profile resolution, interactive prompt, startup API validation.

```bash
python -m autopilot --validate-only --profile primary   # exit 0, prints model ID
python -m autopilot --validate-only --profile bogus     # exit 2, clear error
```

### Checkpoint 2 — Browser and perception *(~90 min)*
`browser.py`, `perception.py`, all three JS files. Dialog and popup handlers registered at creation.

```bash
python -m autopilot observe --url https://www.saucedemo.com
```
Must print ≥3 elements including both textboxes and the login button, with correct roles and names, and write `before.png` + `marked.png` with visible badges on the real controls. **Open `marked.png` and look at it.** If badges are misaligned, nothing downstream can work — fix it here.

### Checkpoint 3 — Full loop, end to end *(~2.5 h) ← THE DEMO LIVES HERE*
`planner.py`, `resolver.py`, `policy.py`, `executor.py`, `evidence.py`, minimal report.

```bash
python -m autopilot run --scenario config/scenarios/saucedemo.yaml
```
Must reach the order-confirmation page in ≤22 steps and write a complete `trace.jsonl`.

**If you get here and nothing else works, the human still has a demo.** Commit before touching anything else.

### Checkpoint 4 — Findings and report *(~75 min)*
`findings.py`, `report.py`.

```bash
python -m autopilot run --scenario config/scenarios/saucedemo.yaml
# report.html opens, shows every step with images, ≥1 finding
```

### Checkpoint 5 — Remaining scenarios *(~60 min)*
`search.yaml`, `youtube.yaml`. Run each. Record actual outcomes in `STATUS.md` — including failures. An honest status file is worth more than an optimistic one.

### Checkpoint 6 — Hardening *(~45 min)*
Unit tests in `tests/`, `scripts/smoke.sh`, `README.md`, `requirements.lock.txt`.

```bash
pytest -q && bash scripts/smoke.sh
```

Minimum test coverage: resolver rejects unknown `uix`; resolver rejects ambiguous matches; policy blocks payment class; policy blocks off-allowlist navigation; secrets never appear in a serialized `StepRecord`; state hash is stable under element reordering.

---

## 13. Demo scenarios

### Tier A — must work

**A1 · Commerce journey** (`saucedemo.yaml`) — login → browse → add to cart → checkout → confirmation. Allowlist `saucedemo.com`. ~18 steps. This is the "order something" demo. Purpose-built for automation, so it won't fight you.

**A2 · Search and navigate** (`search.yaml`) — goal: *"Search for the Playwright Python documentation and open the official playwright.dev site."* Start `https://duckduckgo.com`. Allowlist `duckduckgo.com`, `playwright.dev`. ~5 steps.

> DuckDuckGo rather than Google deliberately. Google challenges automated Chromium hard, and a CAPTCHA mid-demo is unrecoverable. The story — search, evaluate results, navigate, confirm arrival — is identical. Try Google live only *after* the DDG run has already succeeded in front of the room.

**A3 · Safety demo** (inline, no file) — run A1 with `blocked_classes` including `data_entry`. The agent gets blocked, the gate fires, and the report shows an amber block. Thirty seconds, and it's the most convincing thing you'll show all day: it proves the AI isn't in control of the browser.

### Tier B — stretch, have a fallback

**B1 · YouTube lyric** (`youtube.yaml`) — goal: *"Open the transcript, find the line containing '<lyric>', and click it to jump the player there."* Start from a specific `watch?v=` URL. Allowlist `youtube.com`, `www.youtube.com`.

Known risks, in order: a consent interstitial on Indian IPs; a pre-roll ad blocking the player; the transcript button living behind a "..." overflow menu; virtualised transcript list so the target line isn't in the DOM until scrolled.

Mitigations: set `locale: en-US`; add `&hl=en` to the URL; pick a video you've **verified has a transcript** and whose lyric sits in the **first 30 seconds** of the transcript panel so no scrolling is needed. Run it at least twice tonight. If it fails twice, screen-record one good run and show that.

**B2 · Accessibility findings** — run against `https://the-internet.herokuapp.com/` with a browsing goal. Deliberately broken pages, so the static a11y checks produce real findings and the report looks substantial.

---

## 14. `STATUS.md` template

Write this before you stop, whatever state things are in.

```markdown
# Build Status — <timestamp>

## Checkpoints
- [x] 1 Skeleton and config
- [x] 2 Browser and perception
- [ ] 3 Full loop          <- FAILED, see below
...

## Verified working
Exact commands that pass, with observed output.

## Known broken
What fails, the error, what was tried, best guess at the cause.

## Not attempted
And why.

## Demo readiness
For each scenario: last run outcome, step count, wall time, whether
report.html rendered.

## First thing to fix in the morning
One item.
```

---

## 15. Failure handling

| Failure | Required response |
|---|---|
| Unknown `uix` from model | Reject, re-observe, feed reason back. Never fuzzy-match. |
| Ambiguous target | Reject, record both candidates as evidence, emit finding. |
| Frame detached mid-capture | Skip that frame, continue. Don't abort. |
| Actionability timeout | One retry after fresh observe + re-resolve, then record and continue. |
| Dialog | Capture text; dismiss unless explicitly allowed. Never auto-accept confirm/prompt. |
| Popup | Adopt if allowlisted, else close and note. |
| Same state 3× | System note to planner. 5× → abort `stuck_loop`. |
| Token budget 85% | Shrink history to 2 turns. 95% → clean abort + report. |
| Step / wall-clock budget | Clean abort, outcome `budget_exhausted`, **still write the report**. |
| Browser crash | Catch, mark run `interrupted`, write report from the trace written so far. |
| Planner schema violation | One retry with the error text, then abort the step. |
| API 429 | Exponential backoff, 3 attempts (2s, 4s, 8s), then abort cleanly. |
| API 404 on model | Abort immediately with a message naming the model and suggesting `--profile`. |

**Universal rule:** every abort path writes `report.html` from whatever is in `trace.jsonl`. A partial report is a demo. A stack trace is not.

---

## 16. Acceptance gates

| Gate | Pass condition |
|---|---|
| Perception | ≥90% of visibly interactive controls on the three Tier A start pages appear in the inventory with a non-empty name |
| Marking | Badges align with their elements within 3px; `clear()` always runs before the next screenshot |
| Targeting | No ambiguous or unknown target ever executes; both paths covered by a unit test |
| Safety | Blocked classes cannot execute; off-allowlist navigation cannot execute |
| Dialogs | No `confirm`/`prompt` auto-accepted; every dialog's text in evidence |
| Stabilization | No step waits longer than `max_wait_ms`; no run hangs indefinitely |
| Secrets | `grep -r "secret_sauce" runs/` returns nothing from any trace or report |
| Evidence | Every step in the report has before + after images and a named action |
| Recovery | Killing the process mid-run still permits `report.html` generation from the trace |
| Demo | A1 and A2 succeed on three consecutive runs from a clean `runs/` |

---

## 17. Pre-demo checklist — for the human, tomorrow morning

Thirty minutes. Do not skip this.

```bash
bash scripts/smoke.sh                    # A1 + A2, clean runs/
python -m autopilot --validate-only --profile primary
python -m autopilot --validate-only --profile sonnet45
grep -r "secret_sauce" runs/ && echo "SECRET LEAK"   # must find nothing
```

- Open `report.html` from a clean browser profile — confirm images render offline
- Run A1 once on the **presentation machine**, on the **presentation network**
- Confirm `headless: false` and `slow_mo_ms: 120` so the room can follow along
- Have `--profile` fallback rehearsed in case a key fails live
- Have the B1 screen recording on disk as a fallback
