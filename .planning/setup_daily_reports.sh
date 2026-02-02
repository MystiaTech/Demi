#!/bin/bash
# Setup script for Demi daily Discord progress reports
# Run this once to enable automatic daily reporting

PROJECT_DIR="/home/mystiatech/projects/Demi"
REPORTER_SCRIPT="$PROJECT_DIR/.planning/discord_reporter.py"

echo "🤖 Setting up Demi Daily Discord Reports"
echo "========================================"

# Check if running on Linux/Mac or WSL
if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✅ Linux/Mac detected - using cron"

    # Create cron job (runs at 6 PM daily)
    CRON_JOB="0 18 * * * cd $PROJECT_DIR && /usr/bin/python3 $REPORTER_SCRIPT"

    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "discord_reporter.py"; then
        echo "⚠️  Cron job already exists. Skipping..."
    else
        # Add to crontab
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "✅ Cron job installed! Reports will send daily at 6 PM"
        echo "   Command: $CRON_JOB"
    fi

    echo ""
    echo "📋 Cron management:"
    echo "   View cron jobs:  crontab -l"
    echo "   Edit cron jobs:  crontab -e"
    echo "   Remove cron job: crontab -r"

elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    echo "✅ Windows detected - using Task Scheduler"
    echo ""
    echo "Run this command in PowerShell (as Administrator):"
    echo ""
    echo "schtasks /create /tn \"Demi Daily Report\" /tr \"python.exe '$REPORTER_SCRIPT'\" /sc daily /st 18:00"
    echo ""
    echo "📋 Task Scheduler management:"
    echo "   View tasks:   schtasks /query /tn \"Demi Daily Report\""
    echo "   Delete task:  schtasks /delete /tn \"Demi Daily Report\" /f"

else
    echo "❌ Unknown OS: $OSTYPE"
    echo "Please set up the cron job or Task Scheduler manually"
    echo ""
    echo "Script location: $REPORTER_SCRIPT"
fi

echo ""
echo "📝 Manual execution (for testing):"
echo "   python3 $REPORTER_SCRIPT"
echo ""
echo "✨ Setup complete! Your daily Demi progress reports are ready."
