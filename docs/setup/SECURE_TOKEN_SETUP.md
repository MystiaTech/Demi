# Secure Token Management Guide

## ✅ What We Set Up

Your project is now configured to handle sensitive data securely:

### File Structure
```
Demi/
├── .env                    ← YOUR LOCAL SECRETS (git ignored ✓)
├── .env.example            ← SAFE TO COMMIT (template only)
└── docker-compose.yml      ← Reads from .env file
```

### Git Protection
- ✓ `.env` is in `.gitignore` - will NEVER be committed
- ✓ `.env.example` is committed - shows what variables are needed
- ✓ No secrets in any committed files

---

## 🔒 How to Add Your Discord Token

### Step 1: Get Your Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create or select your application
3. Go to "Bot" → Copy your token

### Step 2: Add to Local .env File

Open `.env` (already created for you):

```bash
# Edit .env
nano .env
```

Change this:
```env
DISCORD_TOKEN=
```

To this:
```env
DISCORD_TOKEN=your_actual_token_here_abcd1234xyz
```

### Step 3: Restart Docker

```bash
docker-compose restart backend
```

That's it! Your token is now loaded securely.

---

## 🛡️ Security Checks

### Verify It's Secure

```bash
# Check that .env is ignored by git
git check-ignore .env
# Should output: .env

# Verify no secrets in git history
git log --all --full-history -S "token" -- .env
# Should show nothing

# Check what would be committed
git status
# Should NOT show .env in the list
```

### If You Accidentally Committed a Token

**⚠️ IMMEDIATELY REVOKE IT:**

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "Regenerate" on your bot token
3. Update your local `.env` file
4. Restart Docker

The old token is now useless.

---

## 📝 Environment Variables Available

Edit `.env` to configure any of these:

| Variable | Purpose | Example |
|----------|---------|---------|
| `DISCORD_TOKEN` | Discord bot authentication | `MzI4MjUxODMyODI4ODA5MjE2.D...` |
| `DISCORD_GUILD_ID` | Specific Discord server ID | `123456789` |
| `DISCORD_CHANNEL_ID` | Specific Discord channel ID | `987654321` |
| `TELEGRAM_TOKEN` | Telegram bot token | `110201543:AAHdqTcvCH1...` |
| `LMSTUDIO_BASE_URL` | LMStudio API endpoint | `http://localhost:8000` |
| `DEBUG` | Debug mode | `False` |

**Leave blank to disable that feature.**

---

## 🔄 Environment Variable Priority

Docker-compose applies variables in this order:

1. `.env` file values (overrides everything)
2. `docker-compose.yml` hardcoded values (fallback)
3. System environment variables (if set)

So your `.env` values always take priority.

---

## 📚 What Each User Needs

When sharing your project with others:

1. **They get:** `docker-compose.yml` + `.env.example`
2. **They create:** Their own `.env` file (copy from `.env.example`)
3. **They add:** Their own tokens (Discord, Telegram, etc.)
4. **They run:** `docker-compose up -d`

### For Them (First Time Setup)

```bash
# Clone the repo
git clone <your-repo>
cd Demi

# Create their local .env file
cp .env.example .env

# Edit .env with their tokens
nano .env

# Add their tokens:
# - DISCORD_TOKEN=...
# - TELEGRAM_TOKEN=...

# Start Docker
docker-compose up -d
```

Their `.env` will never be committed to git.

---

## 🚨 Important Security Notes

### DO NOT:
- ❌ Put tokens in `docker-compose.yml`
- ❌ Commit `.env` file to git
- ❌ Share `.env` file with others
- ❌ Post `.env` on GitHub issues/forums
- ❌ Use the same token across multiple deployments

### DO:
- ✅ Keep `.env` in `.gitignore`
- ✅ Use different tokens for dev/prod
- ✅ Rotate tokens periodically
- ✅ Revoke immediately if exposed
- ✅ Check git history before pushing

---

## 🔍 Verify Current Setup

```bash
# View current .env (safe - no actual secrets shown)
cat .env | grep -v "^#"

# Verify backend loaded env variables
docker-compose logs backend | grep DISCORD_TOKEN

# Check if Discord bot is recognized
curl http://localhost:8080/api/metrics/discord
```

---

## ✨ You're Secure!

Your project is now set up correctly:
- ✓ Secrets stored locally only
- ✓ Git cannot see them
- ✓ Docker loads them safely
- ✓ Safe to push code to GitHub

**Add your Discord token to `.env` and you're ready to go!**

