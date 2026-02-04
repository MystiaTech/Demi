#!/bin/bash
# Progress Report Script
# Usage: ./scripts/progress_report.sh "Your progress message here"

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}📊 Demi Progress Reporter${NC}"
echo "=========================="

# Check if message provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage:${NC} $0 \"Your progress message here\""
    echo ""
    echo "Examples:"
    echo "  $0 \"Fixed Discord voice connection issue\""
    echo "  $0 \"Added new avatar animations\""
    exit 1
fi

MESSAGE="$1"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠️  You have uncommitted changes. Committing first...${NC}"
    
    # Stage all changes
    git add -A
    
    # Commit with progress message
    git commit -m "progress: $MESSAGE"
    echo -e "${GREEN}✓ Changes committed${NC}"
fi

# Push to origin
echo ""
echo "🚀 Pushing to origin..."
if git push origin HEAD; then
    echo -e "${GREEN}✓ Pushed to origin${NC}"
else
    echo -e "${RED}✗ Failed to push to origin${NC}"
    exit 1
fi

# Send Discord webhook if configured
if [ -n "$DISCORD_WEBHOOK_URL" ]; then
    echo ""
    echo "📤 Sending Discord notification..."
    if python3 "$REPO_ROOT/scripts/discord_webhook.py" "$MESSAGE"; then
        echo -e "${GREEN}✓ Discord notification sent${NC}"
    else
        echo -e "${YELLOW}⚠️  Failed to send Discord notification${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}ℹ️  DISCORD_WEBHOOK_URL not set - skipping Discord notification${NC}"
    echo "   Set it with: export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/...'"
fi

# Try to push to GitHub mirror
echo ""
echo "🔄 Syncing to GitHub mirror..."
if git push github HEAD 2>/dev/null; then
    echo -e "${GREEN}✓ Synced to GitHub${NC}"
else
    echo -e "${YELLOW}⚠️  Could not sync to GitHub (authentication may be required)${NC}"
fi

echo ""
echo -e "${GREEN}✅ Progress report complete!${NC}"
