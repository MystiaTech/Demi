#!/usr/bin/env python3
r"""
Demi Discord Progress Reporter
Sends daily summaries of project progress to a Discord webhook.

Usage:
    python discord_reporter.py

Set up cron job (Linux/Mac):
    0 18 * * * cd /home/mystiatech/projects/Demi && python .planning/discord_reporter.py

Set up task scheduler (Windows):
    schtasks /create /tn "Demi Daily Report" /tr "python C:\path\to\Demi\.planning\discord_reporter.py" /sc daily /st 18:00
"""

import requests
import json
import subprocess
import base64
import os
from datetime import datetime, timedelta
from pathlib import Path

# Discord webhook URL from environment variable
WEBHOOK_URL = os.getenv("DISCORD_PROGRESS_WEBHOOK_URL")

if not WEBHOOK_URL:
    raise ValueError(
        "DISCORD_PROGRESS_WEBHOOK_URL environment variable not set. "
        "Add your webhook URL to .env file."
    )

# Project paths
# .planning/discord_reporter.py -> parent: .planning -> parent: Demi -> parent: projects
SCRIPT_DIR = Path(__file__).parent  # .planning
PROJECT_DIR = SCRIPT_DIR.parent  # Demi root
STATE_FILE = PROJECT_DIR / ".planning" / "STATE.md"
ROADMAP_FILE = PROJECT_DIR / ".planning" / "ROADMAP.md"
REQUIREMENTS_FILE = PROJECT_DIR / ".planning" / "REQUIREMENTS.md"
DEMI_IMAGE = PROJECT_DIR / "Demi.png"


def get_git_stats():
    """Get recent git commits and changes."""
    try:
        # Recent commits
        commits = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True
        ).stdout.strip().split('\n')

        # Uncommitted changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True
        ).stdout.strip()

        return commits, status
    except Exception as e:
        return [], f"Error getting git stats: {e}"


def get_phase_status():
    """Extract current phase status from STATE.md."""
    try:
        if not STATE_FILE.exists():
            return "Phase data not found"

        content = STATE_FILE.read_text()
        lines = content.split('\n')

        # Look for phase markers in Current Position section
        phase_info = []
        in_position = False
        for i, line in enumerate(lines):
            if '## Current Position' in line:
                in_position = True
                continue
            if in_position:
                # Stop at next section header or blank line followed by ---
                if line.startswith('##'):
                    break
                if line.strip() and ('**Phase:**' in line or '**Progress:**' in line or '**Status:**' in line):
                    phase_info.append(line.strip())

        if phase_info:
            return '\n'.join(phase_info[:3])  # First 3 lines of phase info

        return "Phase status unclear - check STATE.md"
    except Exception as e:
        return f"Error reading phase status: {e}"


def get_requirements_progress():
    """Count completed vs total requirements."""
    try:
        if not REQUIREMENTS_FILE.exists():
            return "No requirements file found"

        content = REQUIREMENTS_FILE.read_text()
        total = content.count('- [ ]') + content.count('- [x]')
        completed = content.count('- [x]')

        if total == 0:
            return "No requirements defined"

        percentage = (completed / total) * 100
        return f"{completed}/{total} requirements complete ({percentage:.0f}%)"
    except Exception as e:
        return f"Error reading requirements: {e}"


def create_embed():
    """Create Discord embed with project status."""
    commits, git_status = get_git_stats()
    phase_status = get_phase_status()
    requirements = get_requirements_progress()

    timestamp = datetime.now()

    # Build commit summary
    commit_text = "No recent commits"
    if commits and commits[0]:
        commit_text = '\n'.join(commits[:3]) if len(commits) > 1 else commits[0]

    # Build changes summary
    changes_text = "No uncommitted changes"
    if git_status:
        changes = git_status.split('\n')[:5]
        changes_text = '\n'.join(changes)

    embed = {
        "title": "✨ Demi Progress Report",
        "description": "Divine Autonomous Companion - In Control, Always",
        "color": 0xC67FD8,  # Regal purple/violet
        "fields": [
            {
                "name": "📊 Requirements Progress",
                "value": requirements,
                "inline": False
            },
            {
                "name": "🔄 Recent Commits",
                "value": f"```\n{commit_text}\n```" if commit_text != "No recent commits" else commit_text,
                "inline": False
            },
            {
                "name": "📝 Uncommitted Changes",
                "value": f"```\n{changes_text}\n```" if changes_text != "No uncommitted changes" else changes_text,
                "inline": False
            },
            {
                "name": "📍 Current Phase",
                "value": phase_status,
                "inline": False
            }
        ],
        "footer": {
            "text": "Status Report • " + timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
    }

    # Add Demi's image if it exists
    if DEMI_IMAGE.exists():
        embed["thumbnail"] = {
            "url": "attachment://Demi.png"
        }

    return embed


def send_to_discord(embed):
    """Send embed to Discord webhook with Demi's image."""
    try:
        payload = {
            "username": "✨ Demi",
            "embeds": [embed]
        }

        # If image exists, send it as multipart form data
        if DEMI_IMAGE.exists():
            with open(DEMI_IMAGE, 'rb') as img_file:
                files = {
                    'file': (DEMI_IMAGE.name, img_file, 'image/png')
                }
                data = {
                    'payload_json': json.dumps(payload)
                }
                response = requests.post(
                    WEBHOOK_URL,
                    files=files,
                    data=data,
                    timeout=10
                )
        else:
            response = requests.post(
                WEBHOOK_URL,
                json=payload,
                timeout=10
            )

        if response.status_code in [200, 204]:
            print(f"✅ Progress report sent to Discord at {datetime.now()}")
            return True
        else:
            print(f"❌ Failed to send to Discord. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending to Discord: {e}")
        return False


def main():
    """Main entry point."""
    print(f"\n✨ Demi Progress Reporter - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # Verify project directory
    if not PROJECT_DIR.exists():
        print(f"❌ Project directory not found: {PROJECT_DIR}")
        return False

    print(f"📁 Project directory: {PROJECT_DIR}")

    # Check for Demi's image
    if DEMI_IMAGE.exists():
        print(f"✨ Found Demi's image: {DEMI_IMAGE}")
    else:
        print(f"⚠️  Demi's image not found at {DEMI_IMAGE} (report will work without it)")

    # Create embed
    print("\n📊 Gathering project status...")
    embed = create_embed()

    # Send to Discord
    print("📤 Sending to Discord...")
    success = send_to_discord(embed)

    print("=" * 50)
    return success


if __name__ == "__main__":
    main()
