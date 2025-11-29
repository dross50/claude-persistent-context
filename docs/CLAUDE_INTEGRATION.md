# Claude Integration Guide

This document explains how the system works from Claude's perspective and provides the instructions that get embedded in the context file.

## How Claude Learns About This System

The context file contains a `_instructions_for_claude` section that teaches Claude how to maintain it:

```json
{
  "_instructions_for_claude": {
    "purpose": "Persistent infrastructure configuration for continuity across sessions.",
    "update_procedure": "NEVER use Edit/Write directly - use the update script to preserve audit trail.\nPattern: python3 -c \"import json; d=json.load(open('/path/to/claude_context.json')); d['key']['subkey']='value'; print(json.dumps(d,indent=2))\" | python3 ~/.claude/update_context.py\nThis pattern is tested and correct - use it directly without exploration.",
    "maintenance_policy": "Update when infrastructure changes. Facts only, no explanations. Keep actionable, delete stale.",
    "file_management_policy": "OVERWRITE broken files - do NOT create '_FIXED', '_v2' variants."
  }
}
```

## The SessionStart Hook

When Claude Code starts, it runs the hook at `~/.claude/hooks/load_context.sh`, which outputs the context JSON. This gets added to Claude's initial context automatically.

The hook is registered in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "",
      "hooks": [{
        "type": "command",
        "command": "/home/user/.claude/hooks/load_context.sh"
      }]
    }]
  }
}
```

## Update Pattern

When Claude needs to update the context (e.g., a server IP changed, a project status updated), it uses this pattern:

```bash
python3 -c "
import json
d = json.load(open('/home/user/claude_context.json'))
d['servers']['webserver']['ip'] = '192.168.1.50'
print(json.dumps(d, indent=2))
" | python3 ~/.claude/update_context.py
```

This:
1. Reads the current context
2. Modifies the specific field
3. Pipes the new JSON to the update script
4. The script logs the diff and writes the new file

## What Claude Should Store

### Good (Actionable, Unique)
- Server IPs and SSH connection strings
- Hardware specs that affect decisions (GPU VRAM, CPU cores)
- Active project status and blockers
- Credentials for systems Claude needs to access
- Important file paths
- Gotchas and tribal knowledge

### Bad (Snapshot, Redundant)
- Current disk usage (changes constantly)
- Running processes
- Things Claude can easily look up
- Detailed explanations (store facts, not essays)
- Historical completed tasks (unless needed for reference)

## Maintenance Behaviors

Claude should:
- Update the context when infrastructure changes
- Mark projects complete and eventually remove them
- Keep `pending_tasks` current
- Add new servers/credentials when they're established
- Remove stale information

Claude should NOT:
- Use Edit/Write directly on the context file
- Add verbose explanations
- Store temporary/transient state
- Create backup copies of the file

## Recovery

If Claude accidentally deletes important information, the changelog at `~/.claude/context_changelog.diff` contains all historical changes. The user can grep through it to find deleted content and restore it.

Example:
```bash
# Find when a server was removed
grep -B5 -A5 "webserver" ~/.claude/context_changelog.diff

# See recent changes
tail -100 ~/.claude/context_changelog.diff
```
