#!/usr/bin/env bash
set -uo pipefail

# Never hang waiting for passwords in an overnight run
export GIT_TERMINAL_PROMPT=0

REMOTE_URL="https://github.com/AbdulBaseer31/didactic-guacamole.git"
LOG_DIR="logs"
CP_TIMEOUT="55m"          # hard ceiling per checkpoint attempt
MAX_ATTEMPTS=3

mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ---- 0. Pre-flight: Check environment (keys optional) ----
log "Pre-flight: checking environment"
if [ -f ".env" ]; then
    set -a; source .env; set +a
    log "Loaded .env file"
else
    log "WARNING: No .env found. Continuing without API keys (silent pass)."
fi

log "Pre-flight OK — API keys optional, proceeding with build."

# ---- 1. Git setup ----
if [ ! -d ".git" ]; then
    git init
    git branch -M main
fi

if ! git remote | grep -q "^origin$"; then
    git remote add origin "$REMOTE_URL"
else
    git remote set-url origin "$REMOTE_URL"
fi

# Ensure we're on main branch
git checkout main 2>/dev/null || git checkout -b main

# .gitignore doesn't exist yet (checkpoint 1 creates it), so write a minimal
# one now to guarantee .env and logs/ never enter the very first commit,
# before the real .gitignore lands.
if [ ! -f ".gitignore" ]; then
    printf '.env\nlogs/\nruns/\n__pycache__/\n.venv/\n*.pyc\n' > .gitignore
    log "Wrote minimal .gitignore before first commit (checkpoint 1 will expand it)"
fi

git add -A
git reset -- .env >/dev/null 2>&1 || true   # belt and suspenders: never stage .env
git commit -m "initial commit" >/dev/null 2>&1 || log "Nothing to commit initially"
if ! git push -u origin main > "$LOG_DIR/00_initial_push.log" 2>&1; then
    log "WARNING: initial push failed — check $LOG_DIR/00_initial_push.log and your git auth."
    log "Continuing locally; commits will still happen, they just won't reach GitHub."
fi

# ---- 2. Checkpoint runner ----
run_checkpoint() {
    local cp_num="$1" cp_title="$2" instruction="$3" verify_cmd="$4"
    local logfile="$LOG_DIR/checkpoint_${cp_num}.log"
    local attempt=1

    echo "==================================================" | tee -a "$logfile"
    echo "Checkpoint ${cp_num}: ${cp_title}"                   | tee -a "$logfile"
    echo "==================================================" | tee -a "$logfile"

    while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
        log "Checkpoint ${cp_num}, attempt ${attempt}/${MAX_ATTEMPTS}"

        timeout "$CP_TIMEOUT" opencode run "$instruction" \
            >> "$logfile" 2>&1
        local run_status=$?

        if [ $run_status -eq 124 ]; then
            log "Checkpoint ${cp_num} attempt ${attempt}: TIMED OUT after ${CP_TIMEOUT}"
        elif [ $run_status -ne 0 ]; then
            log "Checkpoint ${cp_num} attempt ${attempt}: opencode exited ${run_status}"
        fi

        # Run verification command
        if eval "$verify_cmd" >> "$logfile" 2>&1; then
            log "Checkpoint ${cp_num}: verification PASSED"
            git add -A
            git reset -- .env >/dev/null 2>&1 || true
            if ! git diff-index --quiet HEAD --; then
                git commit -m "checkpoint ${cp_num}: ${cp_title}" >> "$logfile" 2>&1
                if git push origin main >> "$logfile" 2>&1; then
                    log "Checkpoint ${cp_num}: committed and pushed"
                else
                    log "Checkpoint ${cp_num}: committed LOCALLY, push failed (see log)"
                fi
            else
                log "Checkpoint ${cp_num}: verification passed (no extra diff)"
            fi
            return 0
        else
            log "Checkpoint ${cp_num} attempt ${attempt}: verification FAILED"
            attempt=$((attempt + 1))
        fi
    done

    log "Checkpoint ${cp_num}: FAILED after ${MAX_ATTEMPTS} attempts. Committing partial state."
    git add -A
    git reset -- .env >/dev/null 2>&1 || true
    if ! git diff-index --quiet HEAD --; then
        git commit -m "checkpoint ${cp_num}: PARTIAL/FAILED - see logs/checkpoint_${cp_num}.log" >> "$logfile" 2>&1
        git push origin main >> "$logfile" 2>&1 || log "Push of partial state failed"
    fi
    return 1
}

# ---- 3. Checkpoints ----
FAILED_AT=""

run_checkpoint "1" "skeleton and config" \
  "Read MVP-BUILD-SPEC.md. Implement Checkpoint 1: cli.py, config.py, types.py, .env.example, requirements.txt, .gitignore, and config/default.yaml. Use Playwright's sync API, not async." \
  "python -m autopilot --validate-only --profile primary || python -m autopilot --validate-only --profile sonnet45" \
  || FAILED_AT="1"

if [ -z "$FAILED_AT" ]; then
  run_checkpoint "2" "browser and perception" \
    "Read MVP-BUILD-SPEC.md. Implement Checkpoint 2: browser.py, perception.py, js/inventory.js, js/mark.js, js/observer.js, using the JS verbatim from the spec." \
    "python -m autopilot observe --url https://www.saucedemo.com" \
    || FAILED_AT="2"
fi

if [ -z "$FAILED_AT" ]; then
  run_checkpoint "3" "full loop" \
    "Read MVP-BUILD-SPEC.md. Implement Checkpoint 3: planner.py, resolver.py, policy.py, executor.py, evidence.py. trace.jsonl must flush after every step." \
    "python -m autopilot run --scenario config/scenarios/saucedemo.yaml" \
    || FAILED_AT="3"
fi

if [ -z "$FAILED_AT" ]; then
  run_checkpoint "4" "findings and report" \
    "Read MVP-BUILD-SPEC.md. Implement Checkpoint 4: findings.py and report.py — a self-contained single-file HTML report with base64 screenshots and the five static accessibility checks." \
    "python -m autopilot run --scenario config/scenarios/saucedemo.yaml && ls runs/*/report.html >/dev/null 2>&1" \
    || FAILED_AT="4"
fi

if [ -z "$FAILED_AT" ]; then
  run_checkpoint "5" "scenarios" \
    "Read MVP-BUILD-SPEC.md. Implement Checkpoint 5: config/scenarios/search.yaml and config/scenarios/youtube.yaml exactly as specified." \
    "test -f config/scenarios/search.yaml && test -f config/scenarios/youtube.yaml" \
    || FAILED_AT="5"
fi

if [ -z "$FAILED_AT" ]; then
  run_checkpoint "6" "tests and hardening" \
    "Read MVP-BUILD-SPEC.md. Implement Checkpoint 6: tests/test_resolver.py, tests/test_policy.py, tests/test_perception.py, scripts/smoke.sh, requirements.lock.txt. Write STATUS.md using the template in the spec, filling in real results from this build." \
    "pytest -q" \
    || FAILED_AT="6"
fi

# ---- 4. Status summary ----
{
  echo "# Overnight build summary — $(date)"
  echo
  if [ -n "$FAILED_AT" ]; then
    echo "Stopped at checkpoint ${FAILED_AT} after ${MAX_ATTEMPTS} failed attempts."
    echo "See logs/checkpoint_${FAILED_AT}.log for the failure detail."
  else
    echo "All 6 checkpoints completed and verified."
  fi
  echo
  echo "Logs are in ./${LOG_DIR}/"
  echo "Run 'cat STATUS.md' for the agent's account if checkpoint 6 finished."
} > "$LOG_DIR/OVERNIGHT_SUMMARY.md"

log "=================================================="
if [ -n "$FAILED_AT" ]; then
    log "Build stopped at checkpoint ${FAILED_AT}. See ${LOG_DIR}/OVERNIGHT_SUMMARY.md"
else
    log "All checkpoints finished. See ${LOG_DIR}/OVERNIGHT_SUMMARY.md and STATUS.md"
fi
log "=================================================="
