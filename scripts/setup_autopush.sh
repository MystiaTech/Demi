#!/bin/bash
# Setup script for autopush and Discord webhook integration

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "🚀 Setting up Demi Repository Autopush & Webhooks"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check git configuration
echo "📋 Checking Git configuration..."
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not a git repository!"
    exit 1
fi

# Configure git to push to all remotes by default
echo ""
echo "⚙️  Configuring git remotes..."

# Check if GitHub remote exists
if ! git remote | grep -q "^github$"; then
    echo "   Adding GitHub remote..."
    git remote add github https://github.com/MystiaTech/Demi.git 2>/dev/null || true
fi

# Show current remotes
echo "   Current remotes:"
git remote -v | grep "(push)" | while read remote url type; do
    echo "     • $remote: $url"
done

# Set up push URL for GitHub (if credentials are configured)
echo ""
echo "🔧 Setting up autopush hooks..."

# Make hooks executable
chmod +x "$REPO_ROOT/.git/hooks/post-commit" 2>/dev/null || true
chmod +x "$REPO_ROOT/.git/hooks/post-push" 2>/dev/null || true

echo "   ✓ Post-commit hook configured"
echo "   ✓ Post-push hook configured"

# Create local git config for autopush
git config --local alias.pushall '!git remote | xargs -I{} git push {} HEAD'

echo ""
echo "📝 Git aliases added:"
echo "   • git pushall - Push to all remotes"
echo "   • git sync    - Pull from origin and push to all remotes"

# Set up sync alias
git config --local alias.sync '!git pull origin HEAD && git pushall'

echo ""
echo "🔔 Discord Webhook Setup"
echo "------------------------"
echo "To enable Discord notifications, you need to:"
echo ""
echo "1. Create a webhook in your Discord server:"
echo "   • Go to Server Settings → Integrations → Webhooks"
echo "   • Click 'New Webhook' and copy the URL"
echo ""
echo "2. Set the environment variable:"
echo "   export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/YOUR_WEBHOOK_URL'"
echo ""
echo "3. Add it to your shell profile (~/.bashrc or ~/.zshrc) to make it persistent"
echo ""

# Check if webhook URL is set
if [ -z "$DISCORD_WEBHOOK_URL" ]; then
    echo -e "${YELLOW}⚠️  DISCORD_WEBHOOK_URL is not currently set${NC}"
else
    echo -e "${GREEN}✓ DISCORD_WEBHOOK_URL is configured${NC}"
fi

echo ""
echo "📚 Usage"
echo "--------"
echo "Quick push with progress report:"
echo "  ./scripts/progress_report.sh \"Your message here\""
echo ""
echo "Push to all remotes:"
echo "  git pushall"
echo ""
echo "Sync (pull + push to all):"
echo "  git sync"
echo ""
echo "Manual Discord notification:"
echo "  python3 scripts/discord_webhook.py \"Custom message\""
echo ""

echo -e "${GREEN}✅ Setup complete!${NC}"
