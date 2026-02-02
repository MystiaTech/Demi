# Auto-Resume Feature — Automatic Phase Execution

Demi's project now includes automatic resumption capabilities when Claude usage limits are reached.

## Quick Start

### Option 1: Local Script (Recommended for Development)

```bash
# Monitor and execute Phase 06 (retries every 5 minutes, max 1 hour wait)
~/.local/bin/gsd-monitor.sh 06

# Execute a different phase
~/.local/bin/gsd-monitor.sh 05

# Custom retry interval and max retries
~/.local/bin/gsd-monitor.sh 06 10  # 10 retries max
```

**What it does:**
- Attempts phase execution
- If rate-limited: waits 5 minutes, shows countdown
- Retries up to 12 times (60 minutes total)
- Exits successfully when phase completes
- Shows progress with timestamps and remaining time

**Example output:**
```
[2026-02-02 23:30:00] Starting gsd-monitor for Phase 06
[2026-02-02 23:30:00] Attempt 1/12: Executing /gsd:execute-phase 06
[2026-02-02 23:33:45] Phase execution did not complete. Waiting 300 seconds...
[2026-02-02 23:33:45] Remaining time before timeout: 59m 15s
[2026-02-02 23:38:45] Resuming in 0 seconds...
[2026-02-02 23:38:46] Attempt 2/12: Executing /gsd:execute-phase 06
[2026-02-02 23:42:30] ✅ Phase 06 execution completed!
```

### Option 2: GitHub Actions (For Scheduled Automation)

The workflow at `.github/workflows/gsd-phase-executor.yml` provides:
- Manual trigger: Dispatch workflow from GitHub Actions UI
- Scheduled: Runs every 4 hours automatically
- Retry logic: Automatically retries on rate limit
- Git integration: Commits results back to main

**To trigger manually:**
1. Go to: https://github.com/YOUR_USERNAME/Demi/actions
2. Select "GSD Phase Executor with Auto-Resume"
3. Click "Run workflow"
4. Enter phase number (e.g., 06)
5. Choose skip-research option
6. Click "Run workflow"

**How it works:**
- Detects if phase already complete (skips if done)
- Checks for in-progress execution
- Retries every 5 minutes on rate limit
- Commits results to git automatically
- Schedules next run if incomplete

### Option 3: Manual Resume (When You Have Fresh Context)

```bash
/clear
/gsd:execute-phase 06
```

---

## Configuration

Settings in `.planning/gsd-config.json`:

```json
{
  "auto_resume": {
    "enabled": true,                    // Enable auto-resume features
    "check_interval_seconds": 300,      // 5 min between retries
    "max_wait_hours": 4,                // Max 4 hours total wait
    "max_retries": 12,                  // Up to 12 retry attempts
    "resume_on_limit_reset": true,      // Auto-resume when usage limit resets
    "notification_on_resume": true      // Show notifications
  }
}
```

---

## How It Works

### When You Hit a Rate Limit

1. **Execution starts but hits limit:** Agent pauses and reports
2. **Monitor detects pause:** Sees status doesn't indicate completion
3. **Retry loop activates:** Waits configured interval, then retries
4. **Usage resets:** Claude has fresh capacity available
5. **Resume succeeds:** Phase execution continues from where it left off
6. **Completion:** Phase marked complete, STATE.md updated

### State Preservation

Auto-resume works because:
- `.planning/STATE.md` tracks current position
- Plan executors are idempotent (safe to retry)
- Completed tasks skip (don't re-run)
- Database state persists between attempts

---

## Example Workflows

### Workflow A: Development (No Wait)

```bash
# Terminal 1: Start execution
~/.local/bin/gsd-monitor.sh 06

# If it hits limit:
# → Automatically retries
# → You can close terminal and come back later
# → Script will complete when usage available
```

### Workflow B: Scheduled (GitHub Actions)

```bash
# Set up once:
# 1. Enable GitHub Actions in repository
# 2. Workflow automatically runs every 4 hours
# 3. Commits results to main branch
# 4. No manual intervention needed

# To force immediate execution:
# Go to Actions tab → Run workflow → Select phase
```

### Workflow C: Manual Resume (When Checking In)

```bash
# You're working on something else
# When you're ready to execute next phase:

/clear
/gsd:execute-phase 07

# If it hits limit again:
~/.local/bin/gsd-monitor.sh 07
```

---

## Understanding the Monitor Script

Location: `~/.local/bin/gsd-monitor.sh`

**Key parameters:**
- `PHASE`: Which phase to execute (default: 06)
- `MAX_RETRIES`: How many times to retry (default: 12)
- `RETRY_INTERVAL`: Wait time between retries (default: 300 seconds = 5 min)
- `TIMEOUT`: Total maximum wait time (default: 3600 seconds = 1 hour)

**Output modes:**
- `INFO` (blue): Status messages and progress
- `SUCCESS` (green): Phase execution completed
- `WARNING` (yellow): Rate limit detected, waiting to retry
- `ERROR` (red): Failure after max retries

**Exit codes:**
- `0`: Phase execution successful
- `1`: Failed after max retries or timeout reached

---

## Monitoring Progress

### Check Phase Status

```bash
# See which plans are complete
ls -la .planning/phases/06-*/*-SUMMARY.md

# Check STATE.md for current position
grep "Current Phase" .planning/STATE.md

# See recent commits
git log --oneline -10
```

### View Logs

```bash
# Monitor script logs (if implemented)
tail -f ~/.demi/logs/gsd.log

# Git commits show execution
git log --grep="gsd\|Phase" --oneline
```

---

## Troubleshooting

### Script not found
```bash
# Reinstall script
chmod +x ~/.local/bin/gsd-monitor.sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Monitor keeps retrying but phase doesn't complete
```bash
# Check if there's an actual blocker
cat .planning/phases/06-*/*-SUMMARY.md

# Check STATE.md for error context
grep -A5 "ERROR\|BLOCKED" .planning/STATE.md

# Look at recent git commits for error messages
git log --oneline -5
```

### GitHub Actions workflow not triggering
- Verify GitHub Actions enabled in repo settings
- Check `.github/workflows/gsd-phase-executor.yml` is present
- Trigger manually: Actions tab → "Run workflow"

---

## Next Steps

**Ready to execute Phase 06 with auto-resume?**

```bash
# Start local monitor (recommended for now)
~/.local/bin/gsd-monitor.sh 06

# Or clear context and execute manually
/clear
/gsd:execute-phase 06
```

When/if you hit a usage limit, the monitor will automatically retry every 5 minutes until the phase completes.

---

## Advanced: Custom Resume Behavior

To change retry strategy, edit `~/.local/bin/gsd-monitor.sh`:

```bash
RETRY_INTERVAL=600     # Change from 300 (5 min) to 600 (10 min)
MAX_RETRIES=20         # More retries
TIMEOUT=7200           # 2 hours instead of 1 hour
```

To configure GitHub Actions schedule, edit `.github/workflows/gsd-phase-executor.yml`:

```yaml
schedule:
  - cron: '0 */2 * * *'  # Every 2 hours instead of 4
```

---

*Auto-resume feature created 2026-02-02*
*Configuration: .planning/gsd-config.json*
*Monitor script: ~/.local/bin/gsd-monitor.sh*
*GitHub Actions: .github/workflows/gsd-phase-executor.yml*
