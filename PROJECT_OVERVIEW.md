# Autopilot (a.k.a. Pragyaan) — What This Project Actually Does

*A plain-English walkthrough you can read in under 10 minutes. No code required.*

---

## TL;DR

This project is a robot tester for websites. You tell it a goal in plain English —
"log in and buy the backpack" — and it opens a real Chrome browser, looks at the
page the way a person would (buttons, links, text boxes it can *see*), decides
what to click next, and does it. Every single click is double-checked by
ordinary, boring, predictable computer code before it's allowed to happen — the
AI is only ever allowed to *suggest*, never to act directly. At the end you get a
visual report: what it clicked, in what order, what broke, and where the
website's usability or accessibility is weak.

It's one system, built in two passes: a scrappy one-hour proof of concept
(the `Live/` folder, originally called **Pragyaan**) that proved the idea worked,
and a hardened, full-featured rebuild (the `autopilot/` folder) that turned that
proof of concept into something demoable, safe, and auditable. Same idea from
start to finish — just matured.

---

## 1. The problem it's solving

Testing whether a website is *easy to use* is normally either:

- **Manual** — a human clicks through the app themselves, which is slow, doesn't
  scale, and gets skipped under deadline pressure, or
- **Scripted** — a QA engineer writes brittle automation that hard-codes exact
  button IDs and breaks the moment a developer renames a CSS class.

Neither approach tells you *"a real user would get confused here"* or *"this
button has no label a screen reader can announce."* And both require someone to
already know, step by step, what the correct path through the app looks like.

The brief this project was built against (see `MVP-BUILD-SPEC.md`) asks for
something different: an agent that is handed **only a goal in plain language**
and a **starting URL**, is given **zero access to the website's source code or
test hooks**, and has to figure out the path itself — the same way a first-time
visitor would — while also **flagging confusing UI, broken flows, and
accessibility gaps** along the way, and producing a screenshot-by-screenshot
audit trail as proof.

That's the whole ask: an AI-driven mystery shopper for websites, kept on a very
short leash.

---

## 2. The core idea, in one paragraph

Large language models (the "AI" here — Google's Gemini, or Anthropic's Claude,
depending on which mode is running) are good at *deciding* what a person would
do next on a page, but they are unreliable at *precisely and safely executing*
that decision — they hallucinate buttons that don't exist, misjudge which
element they meant, and can't be fully trusted with anything destructive
(payments, deletions, sending messages). So this project splits the job in two:
**the AI only ever proposes one action at a time** ("click the button labeled
Login"), and **deterministic, ordinary Python code** is the only thing that ever
touches the real browser — it looks up that button, verifies it actually exists
and isn't ambiguous, checks it against a safety rulebook, and only then clicks
it. The AI never gets the steering wheel; it only gets to say which way it
*thinks* the car should turn, and a human-written safety system decides whether
that's actually allowed.

---

## 3. The eight-step loop that runs on every single move

Think of the whole engine as an assembly line with eight stations. For *every
one action* (one click, one bit of typing, one scroll), the run goes through
all eight, in order, before moving to the next action:

1. **Observe** — Take a snapshot of the current webpage: what's on it, what's
   clickable, what text boxes exist, whether things are disabled, where they sit
   on screen. This is done by asking the browser itself (via injected
   JavaScript) "list everything a person could interact with right now" — no
   peeking at the website's source code, only what's visibly rendered.

2. **Mark** — Every interactive thing found gets a small numbered magenta badge
   drawn on top of it, like putting numbered stickers on every button in a room.
   This numbered, labeled version of the screenshot is what actually gets shown
   to the AI — it can only ever refer to a badge number, never guess at where
   something is by pixel coordinates or invent an element that isn't badged.

3. **Plan (the AI's turn)** — The AI is shown that numbered screenshot plus a
   short list of the badges ("[12] button 'Add to cart'", "[14] textbox
   'Username'"), reminded of the goal, and asked for exactly **one** next move —
   never a whole plan, never a batch of steps. It has to answer in a strict,
   fixed format (a small structured message, not free-flowing prose) so the
   next stage can actually parse it.

4. **Resolve** — This is the "fact-checker" stage, and it never trusts the AI's
   answer at face value. It re-scans the page right now (things may have shifted
   a fraction of a second) and checks: does badge number 12 still point at a
   real, unique element? If the badge number doesn't exist, or two different
   elements are tied for the same match with no way to tell them apart, the
   move is **rejected outright** — no guessing, no "closest match," no clicking
   by screen coordinates. A rejected move gets reported back to the AI so it can
   try something else next turn.

5. **Validate (the safety gate)** — Even a perfectly real, perfectly resolved
   button might be something the agent should never press: "Delete Account,"
   "Place Order," "Send Message," "Change Password." This stage classifies the
   proposed action against a rulebook and a per-site domain allowlist (it will
   refuse to navigate anywhere off-list). If it's on the blocked list, the
   action is stopped here — permanently, not with a warning — and the block
   itself gets written down as a finding, because *proving the guardrail
   works* is part of the deliverable, not an afterthought.

6. **Execute** — Only once a move has survived steps 4 and 5 does real
   Playwright browser-automation code actually click, type, select, or scroll.
   Typed secrets (like a test password) are referenced only by a name like
   `$SECRET:SAUCE_PASSWORD` and swapped in at this exact moment — the literal
   password value never appears anywhere in the AI's view, the logs, or the
   final report.

7. **Stabilize** — After acting, the system waits for the page to settle down
   (it watches for the DOM to stop mutating) instead of using a fixed
   guessed delay or Playwright's `networkidle`, which is known to hang forever
   on modern sites with constant background chatter (ads, analytics,
   websockets).

8. **Record** — Before/marked/after screenshots, the AI's stated reasoning, what
   was decided, whether it was blocked, and how the page changed are all
   appended to a running trace file **immediately**, one line per step. If the
   whole process crashes at step 19 of 25, steps 1–18 are already safely on
   disk and a report can still be built from them.

Then the loop goes back to step 1, with the newly-changed page, and repeats —
until the AI says "I'm done," a safety limit is hit (too many steps, too much
time, or the page seems stuck repeating itself), or something breaks.

---

## 4. Why the safety gate is the actual headline feature

It would be easy to read this as "an AI browses a website" — but the interesting
engineering here is everything that stops the AI from being fully in charge:

- It can **never** invent a target — every click must resolve to something
  really present on the current page.
- It can **never** complete a payment, delete something, send a message, or
  change account settings — those action *categories* are hard-blocked
  regardless of what the AI wants, and the block is treated as a successful
  safety demonstration, not a failure.
- It can **never** wander off the allowed domain(s) for a scenario.
- It can **never** auto-accept a "Are you sure you want to permanently delete
  this?" browser popup — those are always dismissed unless a human explicitly
  configured otherwise.
- If it gets stuck clicking the same dead end over and over (the page hashes to
  the same state repeatedly), the system notices and eventually aborts the run
  itself rather than burning time or money in a loop.

In other words: the AI is the "ideas" department, and everything downstream of
it is a very unglamorous but very strict compliance department. That's the
actual solution to the brief's demand for a *safe* black-box tester.

---

## 5. Two "brains," one machine

The eight-step loop above is fixed and shared — but the "Plan" station (step 3)
can be filled by two different decision-makers, depending on how the run was
started. This isn't two competing products; it's one engine with a swappable
brain, used for two different jobs:

- **A rehearsed brain**, used for the curated commerce-checkout demo
  (`saucedemo.yaml`). It already knows the expected shape of that one journey
  (log in, add to cart, fill in shipping details, confirm) and walks through it
  deterministically — reliable, no API calls, no chance of a live demo going
  sideways on stage.
- **A genuinely free-form AI brain** (Gemini, chosen through a prioritized
  fallback list of models so a rate-limited model doesn't stall the whole run),
  used the moment you type *your own* goal and URL — through the `interactive`
  command or the web dashboard. This is the brain with no prior knowledge of the
  target site; it has to actually reason from the numbered screenshot every
  single turn, the same way a human visitor would.

Everything past that point — resolving, safety-gating, executing, recording,
reporting — is identical no matter which brain proposed the move. That shared
back half is the actual "solution" the project set out to build; the brain is
just the pluggable front half.

---

## 6. What you actually get at the end

Every run produces a timestamped folder under `runs/` containing:

- `report.html` — a single, self-contained webpage (no internet connection
  needed to view it) showing, step by step: what was clicked, what the AI's
  stated reasoning was, before/after screenshots side by side, and any policy
  blocks highlighted prominently in amber so they can't be missed.
- `trace.jsonl` — the same story as structured data, one line per step, so it
  can be replayed or reprocessed later.
- `findings.json` — a short list of concrete problems the run noticed for free
  while it was working: buttons that did nothing after being clicked three
  times in a row, elements with no accessible name, images used as buttons with
  no alt text, keyboard-focus traps, and so on. No extra pass over the site is
  needed to generate these — they fall out of data the run already collected.
- A `steps/` folder of the actual screenshots (a plain "before" shot for the
  human reader, and a "marked" shot with the numbered badges, which is what the
  AI itself was shown).

There's also a small local dashboard (`autopilot serve`) — a FastAPI backend
serving a browser-based front end — for picking a saved scenario, kicking off a
run, and browsing past runs and their reports without touching the command
line.

---

## 7. How the project got here (one solution, two passes)

The `Live/` folder is the original build: a same-day, ~130-line proof of
concept called **Pragyaan** — one Python script, one Gemini call per step, no
safety gate beyond "don't retype passwords," meant to answer a single question
fast: *can an LLM reliably drive a real browser toward a stated goal at all?*

Once that was proven, the same idea was rebuilt properly as **Autopilot**
(the `autopilot/` folder), following the detailed build specification in
`MVP-BUILD-SPEC.md`: the same observe→plan→act loop, but now with the trust
boundary formalized into distinct resolver/policy/executor stages, a
structured evidence trail, an HTML report, unit tests, and a dashboard. It's
the difference between a sketch that proves a mechanism works and the finished
machine built around that mechanism — not two different ideas.

---

## 8. Try it yourself

```bash
# one-time setup
python -m venv .venv && .venv/scripts/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env      # then add your API key(s)

# the rehearsed demo (no live AI calls, always reliable)
python -m autopilot run --scenario config/scenarios/saucedemo.yaml --profile primary

# type your own goal and watch the real AI figure it out live
python -m autopilot interactive

# browse past runs in a local dashboard
python -m autopilot serve
```

Each run opens `report.html` automatically when it finishes — that report *is*
the deliverable the whole loop above exists to produce.

---

## 9. The honest state of things right now

- The `README.md` in this repo currently tells a new user to add a **Gemini**
  key, and that's correct for the `interactive` command and the dashboard. The
  scripted `saucedemo` demo path and the `--validate-only` check are wired for
  an **Anthropic (Claude)** key instead, via the profile system described in
  `MVP-BUILD-SPEC.md` §4. Both are real, they're just for different commands —
  worth knowing before a live demo so the right key is loaded.
- `search.yaml` and `youtube.yaml` (the other demo scenarios named in the
  spec) will need the free-form AI brain wired into the `run` command, not just
  `interactive`, to actually complete those journeys — right now the rehearsed
  brain only knows the checkout flow.
- Everything described in sections 3–6 above — perception, marking, the
  resolver, the policy gate, the executor, evidence, findings, and the report —
  is implemented and present in the codebase today, not aspirational.
