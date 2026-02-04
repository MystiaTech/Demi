#!/usr/bin/env python3
"""
Discord Webhook for Demi Repository Progress Reports

Posts commit updates and progress reports to Discord channel via webhook.
Usage:
    python scripts/discord_webhook.py [message]
    
Environment Variables:
    DISCORD_WEBHOOK_URL - Required. The webhook URL from Discord channel settings
    
Examples:
    python scripts/discord_webhook.py "New feature deployed!"
    python scripts/discord_webhook.py  # Auto-generates from latest commit
"""

import os
import sys
import subprocess
import json
import urllib.request
import urllib.error
from datetime import datetime


def get_latest_commit():
    """Get the latest commit information."""
    try:
        # Get commit hash
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ).decode().strip()
        
        # Get commit message
        commit_msg = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%B"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ).decode().strip()
        
        # Get author
        author = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%an"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ).decode().strip()
        
        # Get commit time
        commit_time = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%ci"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ).decode().strip()
        
        return {
            "hash": commit_hash,
            "message": commit_msg,
            "author": author,
            "time": commit_time
        }
    except subprocess.CalledProcessError as e:
        print(f"Error getting commit info: {e}")
        return None


def get_repo_stats():
    """Get repository statistics."""
    try:
        # Count commits
        commit_count = subprocess.check_output(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ).decode().strip()
        
        # Get branch
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ).decode().strip()
        
        return {
            "commits": commit_count,
            "branch": branch
        }
    except subprocess.CalledProcessError:
        return {"commits": "?", "branch": "?"}


def send_webhook(webhook_url, content, embeds=None):
    """Send message to Discord webhook."""
    payload = {
        "content": content,
        "username": "Demi Repo Bot",
        "avatar_url": "https://raw.githubusercontent.com/MystiaTech/Demi/main/Demi.png"
    }
    
    if embeds:
        payload["embeds"] = embeds
    
    data = json.dumps(payload).encode('utf-8')
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Demi-Webhook/1.0"
    }
    
    try:
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status in (200, 204):
                print("✓ Webhook sent successfully")
                return True
            else:
                print(f"✗ Webhook failed: HTTP {response.status}")
                return False
                
    except urllib.error.HTTPError as e:
        print(f"✗ HTTP Error: {e.code} - {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"✗ URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def create_commit_embed(commit_info, stats):
    """Create Discord embed for commit notification."""
    # Truncate message if too long
    message = commit_info["message"]
    if len(message) > 1000:
        message = message[:997] + "..."
    
    # Format commit message - get first line as title
    lines = message.split('\n')
    title = lines[0][:256] if lines else "New Commit"
    description = '\n'.join(lines[2:]) if len(lines) > 2 else ""
    
    embed = {
        "title": f"📝 {title}",
        "description": description if description else None,
        "color": 0x9b59b6,  # Purple color
        "fields": [
            {
                "name": "👤 Author",
                "value": commit_info["author"],
                "inline": True
            },
            {
                "name": "🔀 Branch",
                "value": stats["branch"],
                "inline": True
            },
            {
                "name": "🔢 Commit",
                "value": f"`{commit_info['hash']}`",
                "inline": True
            },
            {
                "name": "📊 Total Commits",
                "value": stats["commits"],
                "inline": True
            }
        ],
        "footer": {
            "text": f"Demi Repository • {commit_info['time'][:10]}"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Remove None values
    if embed["description"] is None:
        del embed["description"]
    
    return embed


def create_progress_embed(title, description, fields=None):
    """Create a general progress report embed."""
    embed = {
        "title": f"🚀 {title}",
        "description": description,
        "color": 0x2ecc71,  # Green color
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if fields:
        embed["fields"] = fields
    
    return embed


def main():
    """Main function."""
    # Get webhook URL from environment
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        print("Error: DISCORD_WEBHOOK_URL environment variable not set")
        print("Set it with: export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/...'")
        sys.exit(1)
    
    # Check if message provided as argument
    if len(sys.argv) > 1:
        # Custom message mode
        message = " ".join(sys.argv[1:])
        embed = create_progress_embed(
            "Progress Report",
            message,
            [
                {
                    "name": "⏰ Time",
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "inline": True
                }
            ]
        )
        success = send_webhook(webhook_url, "", [embed])
    else:
        # Auto-commit mode
        commit_info = get_latest_commit()
        
        if not commit_info:
            print("Error: Could not get commit information")
            sys.exit(1)
        
        stats = get_repo_stats()
        embed = create_commit_embed(commit_info, stats)
        
        # Create mention message
        mention = ""
        if "fix" in commit_info["message"].lower():
            mention = "🔧 Bug fix deployed!"
        elif "feat" in commit_info["message"].lower():
            mention = "✨ New feature added!"
        elif "docs" in commit_info["message"].lower():
            mention = "📚 Documentation updated!"
        
        success = send_webhook(webhook_url, mention, [embed])
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
