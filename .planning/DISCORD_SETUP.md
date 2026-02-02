# 🤖 Demi Discord Progress Reports

Automatic daily summaries of your project progress sent to Discord.

## What It Does

The Discord reporter sends a daily status update to your Discord webhook that includes:
- ✅ Requirements progress (X/Y complete, percentage)
- 📝 Recent git commits (last 3-5)
- 📊 Uncommitted changes
- 📍 Current phase status

## Setup

### One-Time Setup

Run the setup script to install the daily scheduler:

```bash
bash .planning/setup_daily_reports.sh
```

This will:
- **Linux/Mac:** Create a cron job that runs daily at 6 PM
- **Windows:** Show you the PowerShell command to run in Task Scheduler

### Manual Setup

**On Linux/Mac (using crontab):**
```bash
# Open crontab editor
crontab -e

# Add this line (runs at 6 PM daily):
0 18 * * * cd /home/mystiatech/projects/Demi && python3 .planning/discord_reporter.py
```

**On Windows (using Task Scheduler):**
```powershell
# Run in PowerShell as Administrator:
schtasks /create /tn "Demi Daily Report" /tr "python.exe 'C:\path\to\Demi\.planning\discord_reporter.py'" /sc daily /st 18:00
```

## Testing

Test the reporter without waiting for the scheduled time:

```bash
python3 .planning/discord_reporter.py
```

You should see a message in your Discord channel within seconds.

## Management

### View Scheduled Reports

**Linux/Mac:**
```bash
crontab -l  # View all cron jobs
```

**Windows:**
```powershell
schtasks /query /tn "Demi Daily Report"
```

### Edit Schedule

**Linux/Mac:**
```bash
crontab -e  # Edit timing or command
```

**Windows:**
```powershell
# Delete and recreate with new time
schtasks /delete /tn "Demi Daily Report" /f
schtasks /create /tn "Demi Daily Report" /tr "python.exe 'path'" /sc daily /st HH:MM
```

### Disable Reports

**Linux/Mac:**
```bash
crontab -e  # Comment out or delete the line
```

**Windows:**
```powershell
schtasks /delete /tn "Demi Daily Report" /f
```

## Files

- **`discord_reporter.py`** - Main reporter script (runs daily)
- **`setup_daily_reports.sh`** - One-time setup script
- **`DISCORD_SETUP.md`** - This file

## Customization

### Change Report Time

Edit the cron time in `setup_daily_reports.sh` or your crontab:

```bash
# Format: minute hour day month weekday
# Examples:
0 9 * * *      # 9 AM daily
0 18 * * *     # 6 PM daily
0 9 * * 1-5    # 9 AM weekdays only
*/30 * * * *   # Every 30 minutes
```

### Customize the Report

Edit `discord_reporter.py` to:
- Change the color, title, or fields
- Add custom statistics from your STATE.md
- Modify the Discord embed formatting
- Pull data from other sources

## Troubleshooting

### Report not sending?

1. **Test the script:**
   ```bash
   python3 .planning/discord_reporter.py
   ```

2. **Check webhook URL:** Verify the webhook URL is correct and still valid

3. **Check logs (Linux/Mac):**
   ```bash
   # View cron logs
   log show --predicate 'process == "cron"' --last 1d  # macOS
   grep CRON /var/log/syslog                           # Linux
   ```

4. **Check dependencies:**
   ```bash
   pip install requests  # Required for Discord API calls
   ```

### Webhook URL expired?

If the webhook stops working, generate a new one:
1. Go to Discord server settings → Webhooks
2. Create a new webhook for your progress channel
3. Update the `WEBHOOK_URL` in `discord_reporter.py`
4. Re-run the setup script

## What Gets Reported

The report automatically gathers:
- **Requirements progress** - Reads `.planning/REQUIREMENTS.md` and counts `[x]` vs `[ ]`
- **Recent commits** - Last 5 git commits with `git log --oneline`
- **Uncommitted changes** - Current git status with `git status --porcelain`
- **Phase status** - Extracts from `.planning/STATE.md`

All data is pulled fresh each time, so it's always current.

---

Questions? Check `discord_reporter.py` for more details or edit it to customize your reports! 🎉
