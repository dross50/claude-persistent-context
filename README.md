# Claude Persistent Context

A self-maintaining knowledge base for Claude Code that persists across sessions with version-controlled audit trails.

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

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/claude-persistent-context.git
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

## Configuration Options

### Minimal (Solo Developer)
```bash
python3 setup.py --minimal
```
Just hardware, network, and basic structure.

### Full (Homelab/Infrastructure)
```bash
python3 setup.py --full
```
Includes server inventory, project tracking, credential placeholders.

## Customization

### Adding Sections

Edit the template in `templates/context_template.json` before running setup, or add sections directly to your generated context file using the update script.

### Changing Hook Behavior

Edit `~/.claude/hooks/load_context.sh` to customize what gets loaded at session start.

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

## Contributing

Issues and PRs welcome. Please test on your platform before submitting.

## License

MIT
