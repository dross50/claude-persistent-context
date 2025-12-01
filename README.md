# Claude Persistent Context

A self-maintaining knowledge base for Claude Code that persists across sessions with version-controlled audit trails.

Vibe-coded by [David](https://github.com/dross50) with Claude (Opus 4.5).

## The Problem

Claude Code starts fresh each session. You re-explain your infrastructure, re-establish context, and waste tokens on information Claude should already know. Existing solutions (CLAUDE.md, MCP memory servers) either lack version control, don't self-update, or require external dependencies.

## The Solution

This system creates:
- A **context JSON file** that Claude reads at session start and actively maintains
- An **update script** that logs all changes as diffs for recovery and history
- **Self-referential instructions** embedded in the context file teaching Claude how to maintain it
- A **SessionStart hook** for automatic loading

## Features

- **Cross-platform**: Works on Linux, macOS, and Windows
- **Automatic hardware/network discovery**: Scans your system to populate initial context
- **Audit trail**: Every change logged with timestamps - rebuild if Claude deletes too much
- **Token-efficient**: Claude updates the file, not the conversation
- **No external dependencies**: Pure Python, no databases or cloud services

## ⚠️ Security Warning

**IMPORTANT**: The context file will contain sensitive information about your infrastructure:
- SSH keys and their locations
- Server IP addresses and hostnames
- Credentials and API tokens (if you add them)
- Network topology

**Never commit `~/claude_context.json` or `~/.claude/context_changelog.diff` to version control!**

Add these to your `.gitignore`:
```
claude_context.json
.claude/
```

The example files in this repo are sanitized with placeholder values. Your actual context file will contain real data.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/dross50/claude-persistent-context.git
cd claude-persistent-context

# Run the setup script
python3 setup.py

# Follow the prompts to configure your context
```

The setup script will:
1. Detect your OS and hardware
2. Scan network configuration
3. Generate your initial `claude_context.json`
4. Install the update script to `~/.claude/`
5. Create the SessionStart hook for auto-loading
6. Initialize the changelog with your baseline

## How It Works

### Context File Structure

```json
{
  "_instructions_for_claude": {
    "purpose": "Persistent infrastructure configuration",
    "update_procedure": "NEVER use Edit/Write directly - use the update script..."
  },
  "hardware": { ... },
  "network": { ... },
  "servers": { ... },
  "active_projects": { ... }
}
```

### Update Flow

1. Claude reads context at session start (via hook)
2. When infrastructure changes, Claude updates via:
   ```bash
   python3 -c "import json; d=json.load(open('~/claude_context.json')); d['key']='value'; print(json.dumps(d,indent=2))" | python3 ~/.claude/update_context.py
   ```
3. Script logs the diff and writes the new version
4. Next session, Claude sees the updated context

### Audit Trail

All changes are logged to `~/.claude/context_changelog.diff`:

```diff
============================================================
# 2025-11-29 14:06:03
============================================================
--- claude_context.json.old
+++ claude_context.json.new
@@ -46,7 +46,7 @@
-      "status": "pending",
+      "status": "complete",
```

## What Gets Captured

The scanner automatically detects:

| Category | Linux | macOS | Windows |
|----------|-------|-------|---------|
| CPU model/cores | ✓ | ✓ | ✓ |
| Memory | ✓ | ✓ | ✓ |
| GPUs (NVIDIA/AMD/Intel/Apple) | ✓ | ✓ | ✓ |
| Storage devices | ✓ | ✓ | ✓ |
| Network interfaces | ✓ | ✓ | ✓ |
| SSH keys | ✓ | ✓ | ✓ |

## Manual Configuration

The scanner gets you started, but the real value comes from what you add:

- **Servers**: SSH connections, purposes, credentials
- **Projects**: Active work with status and blockers
- **Pending tasks**: Things Claude should remember to do
- **Important notes**: Gotchas and tribal knowledge

See `examples/` for reference configurations.

## Options

```bash
python3 setup.py --minimal
```
Just hardware, network, and basic structure (no empty sections for servers, projects, etc).

```bash
python3 setup.py --context-path /custom/path/context.json
```
Use a custom location for the context file instead of `~/claude_context.json`.

```bash
python3 setup.py --scan-only
```
Just run the scanner and print results without installing anything.

## Verification

After installation, verify everything is working:

```bash
# Check that context file was created
ls -lh ~/claude_context.json

# Verify it's valid JSON and view infrastructure overview
python3 -c "import json; from pathlib import Path; ctx=json.load(open(Path.home()/'claude_context.json')); print(json.dumps(ctx['infrastructure_overview'], indent=2))"

# Check that update script is installed
ls -lh ~/.claude/update_context.py

# View the changelog baseline
head -20 ~/.claude/context_changelog.diff
```

## Recovery

If Claude deletes important information:

```bash
# View recent changes
tail -100 ~/.claude/context_changelog.diff

# Find when something was deleted
grep -B5 -A5 "deleted_key" ~/.claude/context_changelog.diff

# Manually restore by editing and piping through update script
```

## Philosophy

This system is opinionated:

- **Facts, not explanations**: Store "CPU: EPYC 7453" not "The CPU is an AMD EPYC 7453 which is a server-grade processor..."
- **Actionable over archival**: Current projects and pending tasks, not completed history
- **Minimal tokens**: Claude reads this every session - keep it lean
- **Trust but verify**: Audit trail lets you catch and fix mistakes

## Status

**Working:**
- Scanner runs on Linux (tested), macOS and Windows (untested but should work)
- Multi-vendor GPU detection (NVIDIA, AMD, Intel, Apple Silicon)
- Hook installation preserves existing SessionStart hooks
- Custom context paths via `--context-path`

**Known Limitations:**
- macOS and Windows detection code is untested - feedback welcome
- `templates/context_template.json` exists but isn't used (template is in setup.py)
- SessionStart hooks use bash scripts - Windows users will need to manually load context or use WSL

## Security Best Practices

1. **Credential Storage**: Store sensitive credentials in a password manager (Bitwarden, 1Password, etc.) and reference them in the context file rather than storing them directly
2. **File Permissions**: The setup script doesn't set restrictive permissions - consider running:
   ```bash
   chmod 600 ~/claude_context.json
   chmod 600 ~/.claude/context_changelog.diff
   ```
3. **Backup Security**: If you back up your home directory, ensure backups are encrypted
4. **Audit Trail**: Periodically review `~/.claude/context_changelog.diff` for any accidentally committed secrets
5. **Rotation**: If you suspect the context file was exposed, rotate any credentials referenced in it

## Contributing

Issues and PRs welcome. Please test on your platform before submitting.

**Note for contributors**: Example files must use placeholder values only. Never commit real credentials, IPs, or identifying information.

## License

MIT
