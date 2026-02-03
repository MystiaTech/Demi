# Git Hooks

## post-commit - Auto-push Hook

This hook automatically pushes commits to your Gitea instance after each local commit.

### Installation

```bash
# From repo root
cp scripts/git-hooks/post-commit .git/hooks/
chmod +x .git/hooks/post-commit
```

### What it does

After every `git commit`, the hook automatically runs `git push origin <current-branch>`.

### Disabling temporarily

```bash
# Skip the hook for a single commit
git commit --no-verify -m "Your message"

# Or rename the hook
mv .git/hooks/post-commit .git/hooks/post-commit.disabled
```

### Troubleshooting

If push fails:
1. Check your network connection
2. Verify credentials: `git remote -v`
3. Check Gitea status: https://giteas.fullmooncyberworks.com
