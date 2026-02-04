# Autopush & Discord Webhook Setup

This guide explains how to set up automatic pushing to multiple remotes and Discord webhook notifications for the Demi repository.

## Quick Start

Run the setup script:

```bash
./scripts/setup_autopush.sh
```

## Features

- ✅ **Autopush**: Automatically push to all configured remotes on commit
- ✅ **Discord Notifications**: Get webhook notifications for every commit
- ✅ **Progress Reports**: Easy script to commit, push, and notify in one command
- ✅ **Multi-Remote Sync**: Push to Gitea and GitHub simultaneously
- ✅ **GitHub Actions**: Automatic Discord notifications on GitHub pushes

## Configuration

### 1. Set Up Discord Webhook

1. In your Discord server:
   - Go to **Server Settings** → **Integrations** → **Webhooks**
   - Click **New Webhook**
   - Choose the channel for notifications
   - Copy the Webhook URL

2. Set the environment variable:
   ```bash
   export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/...'
   ```

3. Make it persistent by adding to `~/.bashrc` or `~/.zshrc`:
   ```bash
   echo 'export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."' >> ~/.bashrc
   source ~/.bashrc
   ```

### 2. Configure Git Remotes

Current remotes are configured as:
- `origin` → Gitea (primary)
- `github` → GitHub (mirror)

To add GitHub credentials for autopush:
```bash
# Option 1: Use SSH (recommended)
git remote set-url github git@github.com:MystiaTech/Demi.git

# Option 2: Use GitHub CLI
gh auth login

# Option 3: Use personal access token
git remote set-url github https://USERNAME:TOKEN@github.com/MystiaTech/Demi.git
```

## Usage

### Progress Report (Recommended)

The easiest way to commit and notify:

```bash
./scripts/progress_report.sh "Fixed Discord voice connection issue"
```

This will:
1. Commit any uncommitted changes with your message
2. Push to origin (Gitea)
3. Send Discord notification
4. Try to sync to GitHub

### Git Aliases

After setup, these aliases are available:

```bash
# Push to all remotes
git pushall

# Pull from origin and push to all
git sync
```

### Manual Discord Notification

```bash
# Notify about latest commit
python3 scripts/discord_webhook.py

# Send custom message
python3 scripts/discord_webhook.py "Deployed new feature!"
```

## How It Works

### Git Hooks

The setup configures two git hooks:

1. **post-commit**: Runs after each commit
   - Sends Discord notification
   - Pushes to all remotes except origin

2. **post-push**: Runs after each push
   - Syncs to other remotes

### GitHub Actions

The `.github/workflows/discord-notify.yml` workflow:
- Triggers on every push to `main` or `develop`
- Triggers on pull requests to `main`
- Sends Discord notification using the webhook

Requires `DISCORD_WEBHOOK_URL` secret in GitHub repository settings.

## Discord Message Format

Commit notifications include:
- 📝 Commit title and description
- 👤 Author name
- 🔀 Branch name
- 🔢 Short commit hash
- 📊 Total commit count
- ⏰ Timestamp

Special prefixes:
- `feat:` → ✨ New feature added!
- `fix:` → 🔧 Bug fix deployed!
- `docs:` → 📚 Documentation updated!

## Troubleshooting

### Webhook not sending

1. Check if `DISCORD_WEBHOOK_URL` is set:
   ```bash
   echo $DISCORD_WEBHOOK_URL
   ```

2. Test webhook manually:
   ```bash
   python3 scripts/discord_webhook.py "Test message"
   ```

3. Check webhook URL is valid in Discord server settings

### GitHub push fails

GitHub requires authentication. Options:

1. **SSH Key** (recommended):
   ```bash
   git remote set-url github git@github.com:MystiaTech/Demi.git
   ```

2. **GitHub CLI**:
   ```bash
   gh auth login
   ```

3. **Personal Access Token**:
   - Create token at https://github.com/settings/tokens
   - Use in remote URL:
     ```bash
     git remote set-url github https://USERNAME:TOKEN@github.com/MystiaTech/Demi.git
     ```

### Hooks not running

Ensure hooks are executable:
```bash
chmod +x .git/hooks/post-commit
chmod +x .git/hooks/post-push
```

## Security Notes

- Never commit `.env` files with secrets
- Keep Discord webhook URLs private
- Use GitHub Secrets for CI/CD webhooks
- Personal access tokens should have minimal permissions

## Related Documentation

- [Git Setup](SECURE_TOKEN_SETUP.md) - Secure token configuration
- [Docker Setup](DOCKER_SETUP.md) - Container deployment
- [Main README](../../README.md) - Project overview
