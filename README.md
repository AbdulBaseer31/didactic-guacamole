# Autopilot MVP

Autonomous web journey agent with deterministic safety gate and evidence trail.

## Quick Start

```bash
git init
git clone https://github.com/AbdulBaseer31/didactic-guacamole
cd didactic-guacamole
python -m venv .venv
set-executionpolicy unrestricted -scope process
.venv/scripts/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env 
```

Open .env file and add gemini api key in api key


## Run Frontend

```bash

#Start frontend server
python -m autopilot serve --port 8050

```


## Run Demo (Alternative to Frontend)

```bash
# Commerce checkout (saucedemo)
python -m autopilot run --scenario config/scenarios/saucedemo.yaml --profile primary --live

# Search & navigate (DuckDuckGo -> playwright.dev)
python -m autopilot run --scenario config/scenarios/search.yaml --profile primary --live

# YouTube transcript (lyric jump)
python -m autopilot run --scenario config/scenarios/youtube.yaml --profile primary --live

#If you want to use Interactive
python -m autopilot interactive

#Here, input your data

#Here set primary (even if it says claude
```

## Output

Each run creates `runs/YYYYMMDD-HHMMSS-goal-slug/` with:

- `report.html` — self-contained visual report (open in browser)
- `trace.jsonl` — step-by-step JSON trace
- `steps/` — before/marked/after screenshots
- `findings.json` — UX friction & accessibility findings

## Architecture

```
observe -> mark -> plan (AI) -> resolve -> validate -> execute -> stabilize -> record
    ^                                                                      |
    └──────────────────────────────────────────────────────────────────────┘
```

Model proposes → Resolver validates → Policy gates → Executor runs → Evidence recorded
