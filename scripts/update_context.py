#!/usr/bin/env python3
"""
Context JSON update script with diff logging.

Usage:
    # Pipe new JSON content:
    python3 -c "import json; d=json.load(open('~/claude_context.json')); d['key']='value'; print(json.dumps(d,indent=2))" | python3 ~/.claude/update_context.py

The script will:
1. Read the current context JSON
2. Read the new JSON from stdin
3. Validate both are valid JSON
4. Generate a unified diff
5. Append the diff (with timestamp) to the changelog
6. Write the new version
"""

import json
import sys
import difflib
from datetime import datetime
from pathlib import Path

CONTEXT_FILE = Path.home() / "claude_context.json"
CHANGELOG_FILE = Path.home() / ".claude" / "context_changelog.diff"


def main():
    # Read new content from stdin
    new_content = sys.stdin.read().strip()

    if not new_content:
        print("ERROR: No content provided on stdin", file=sys.stderr)
        sys.exit(1)

    # Validate new JSON
    try:
        new_json = json.loads(new_content)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in new content: {e}", file=sys.stderr)
        sys.exit(1)

    # Read current content (or empty dict if doesn't exist)
    if CONTEXT_FILE.exists():
        old_content = CONTEXT_FILE.read_text()
        try:
            old_json = json.loads(old_content)
        except json.JSONDecodeError:
            print("WARNING: Current context file is invalid JSON, will be overwritten", file=sys.stderr)
            old_json = {}
            old_content = "{}"
    else:
        old_content = "{}"
        old_json = {}

    # Pretty-print both for consistent diffing
    old_formatted = json.dumps(old_json, indent=2, sort_keys=True) + "\n"
    new_formatted = json.dumps(new_json, indent=2, sort_keys=True) + "\n"

    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        old_formatted.splitlines(keepends=True),
        new_formatted.splitlines(keepends=True),
        fromfile='claude_context.json.old',
        tofile='claude_context.json.new',
        lineterm=''
    ))

    if not diff_lines:
        print("No changes detected")
        sys.exit(0)

    # Build changelog entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separator = "=" * 60
    changelog_entry = f"\n{separator}\n# {timestamp}\n{separator}\n"
    changelog_entry += "".join(diff_lines)
    changelog_entry += "\n"

    # Append to changelog
    CHANGELOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHANGELOG_FILE, 'a') as f:
        f.write(changelog_entry)

    # Write the new context file
    with open(CONTEXT_FILE, 'w') as f:
        json.dump(new_json, f, indent=2)
        f.write("\n")

    # Count changes for summary
    additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
    deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))

    print(f"Updated {CONTEXT_FILE}")
    print(f"  +{additions} -{deletions} lines")
    print(f"Diff appended to {CHANGELOG_FILE}")


if __name__ == "__main__":
    main()
