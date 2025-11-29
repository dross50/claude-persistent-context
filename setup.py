#!/usr/bin/env python3
"""
Claude Persistent Context - Setup Script

Scans your system, generates initial context, and installs the update infrastructure.
"""

import argparse
import json
import os
import shutil
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from scanner import SystemScanner


def get_primary_ip(network_data: dict) -> str:
    """Extract the most likely primary IP from network scan."""
    for iface in network_data.get("interfaces", []):
        for ip in iface.get("ipv4", []):
            # Skip loopback and link-local
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    return "Unknown"


def format_gpus(gpu_list: list) -> dict:
    """Format GPU list into structured dict."""
    if not gpu_list:
        return {"note": "No GPUs detected"}

    gpus = {}
    for gpu in gpu_list:
        idx = gpu.get("index", len(gpus))
        key = f"gpu{idx}"

        gpu_info = {
            "vendor": gpu.get("vendor", "Unknown"),
            "model": gpu["model"],
        }

        # Add VRAM if available
        vram_mb = gpu.get("vram_mb", 0)
        if vram_mb:
            gpu_info["vram"] = f"{vram_mb // 1024}GB" if vram_mb >= 1024 else f"{vram_mb}MB"

        # Add PCIe bus if available (NVIDIA)
        if "pcie_bus" in gpu:
            gpu_info["pcie_bus"] = gpu["pcie_bus"]

        # Add UUID if available (NVIDIA)
        if "uuid" in gpu:
            gpu_info["uuid"] = gpu["uuid"]

        gpus[key] = gpu_info
    return gpus


def format_storage(storage_list: list) -> dict:
    """Format storage list into structured dict."""
    if not storage_list:
        return {"note": "No storage devices detected"}

    storage = {}
    for i, disk in enumerate(storage_list):
        # Try to create a meaningful key
        model = disk.get("model", "").replace(" ", "_")[:20]
        key = model if model and model != "Unknown" else f"disk{i}"
        storage[key] = {
            "device": disk["device"],
            "size": disk["size"],
            "model": disk["model"]
        }
    return storage


def format_network(network_data: dict) -> dict:
    """Format network interfaces."""
    interfaces = {}
    for iface in network_data.get("interfaces", []):
        name = iface["name"]
        ipv4 = iface.get("ipv4", [])
        if ipv4:  # Only include interfaces with IPv4
            interfaces[name] = ipv4[0] if len(ipv4) == 1 else ipv4
    return interfaces


def format_ssh_keys(keys_list: list) -> dict:
    """Format SSH keys list."""
    if not keys_list:
        return {"note": "No SSH keys found in ~/.ssh/"}

    keys = {}
    for key in keys_list:
        keys[key["name"]] = {
            "type": key.get("type", "unknown"),
            "has_private": key["has_private"]
        }
    return keys


def build_context(scan_data: dict, minimal: bool = False) -> dict:
    """Build context JSON from scan data."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    context_path = str(Path.home() / "claude_context.json")

    # CPU info
    cpu = scan_data.get("cpu", {})
    cpu_str = f"{cpu.get('model', 'Unknown')}"
    if cpu.get("cores") and cpu.get("threads"):
        cpu_str += f" ({cpu['cores']}c/{cpu['threads']}t)"

    context = {
        "_instructions_for_claude": {
            "purpose": "Persistent infrastructure configuration for continuity across sessions.",
            "update_procedure": f"NEVER use Edit/Write directly - use the update script to preserve audit trail.\nPattern: python3 -c \"import json; d=json.load(open('{context_path}')); d['key']['subkey']='value'; print(json.dumps(d,indent=2))\" | python3 ~/.claude/update_context.py\nThis pattern is tested and correct - use it directly without exploration.",
            "maintenance_policy": "Update when infrastructure changes. Facts only, no explanations - you are the consumer of this file. Keep actionable, delete stale."
        },
        "context_backup": {
            "changelog": "~/.claude/context_changelog.diff",
            "update_script": "~/.claude/update_context.py"
        },
        "last_updated": timestamp,
        "infrastructure_overview": {
            "hostname": scan_data.get("hostname", "Unknown"),
            "platform": scan_data.get("platform", "Unknown"),
            "primary_ip": get_primary_ip(scan_data.get("network", {}))
        },
        "hardware": {
            "cpu": cpu_str,
            "memory": f"{scan_data.get('memory', {}).get('total_gb', 0)}GB",
            "gpus": format_gpus(scan_data.get("gpus", [])),
            "storage": format_storage(scan_data.get("storage", []))
        },
        "network": {
            "interfaces": format_network(scan_data.get("network", {}))
        },
        "ssh_keys": format_ssh_keys(scan_data.get("ssh_keys", []))
    }

    if not minimal:
        context.update({
            "servers": {},
            "credentials": {},
            "key_paths": {},
            "active_projects": {},
            "pending_tasks": [],
            "important_notes": []
        })

    return context


def install_update_script(source_dir: Path, claude_dir: Path, context_path: Path) -> None:
    """Install the update script to ~/.claude/ with correct context path."""
    source = source_dir / "scripts" / "update_context.py"
    dest = claude_dir / "update_context.py"

    # Read template and substitute the context path
    content = source.read_text()
    content = content.replace(
        'CONTEXT_FILE = Path.home() / "claude_context.json"',
        f'CONTEXT_FILE = Path("{context_path}")'
    )
    dest.write_text(content)

    # Make executable
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  Installed update script: {dest}")


def install_hook(claude_dir: Path, context_path: Path) -> None:
    """Install the SessionStart hook for auto-loading context."""
    hooks_dir = claude_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_script = hooks_dir / "load_context.sh"
    hook_content = f'''#!/bin/bash
# Claude Persistent Context - SessionStart Hook
# Loads context JSON at session start

CONTEXT_FILE="{context_path}"

if [ -f "$CONTEXT_FILE" ]; then
    cat "$CONTEXT_FILE"
else
    echo "Context file not found: $CONTEXT_FILE" >&2
fi
'''

    hook_script.write_text(hook_content)
    hook_script.chmod(hook_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  Installed hook script: {hook_script}")

    # Create/update settings.json with hook configuration
    settings_file = claude_dir / "settings.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
        except json.JSONDecodeError:
            settings = {}
    else:
        settings = {}

    # Add SessionStart hook (preserve existing hooks)
    if "hooks" not in settings:
        settings["hooks"] = {}

    existing_session_hooks = settings["hooks"].get("SessionStart", [])

    # Check if our hook is already installed
    our_hook_command = str(hook_script)
    already_installed = any(
        any(h.get("command") == our_hook_command for h in entry.get("hooks", []))
        for entry in existing_session_hooks
    )

    if not already_installed:
        existing_session_hooks.append({
            "matcher": "",
            "hooks": [{
                "type": "command",
                "command": our_hook_command
            }]
        })
        settings["hooks"]["SessionStart"] = existing_session_hooks
    else:
        print(f"  Hook already installed, skipping")

    settings_file.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"  Updated settings: {settings_file}")


def initialize_changelog(claude_dir: Path, context: dict) -> None:
    """Initialize the changelog with the baseline context."""
    changelog = claude_dir / "context_changelog.diff"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    baseline = json.dumps(context, indent=2, sort_keys=True)

    content = f'''# Claude Persistent Context - Changelog
# This file tracks all changes to claude_context.json
# Use this to recover deleted information or review history

{"=" * 60}
# {timestamp} - BASELINE
{"=" * 60}
{baseline}

'''

    changelog.write_text(content)
    print(f"  Initialized changelog: {changelog}")


def main():
    parser = argparse.ArgumentParser(
        description="Set up Claude Persistent Context"
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Only include hardware/network (no project tracking sections)"
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only run scanner and print results (don't install)"
    )
    parser.add_argument(
        "--context-path",
        type=Path,
        default=Path.home() / "claude_context.json",
        help="Where to create the context file (default: ~/claude_context.json)"
    )

    args = parser.parse_args()

    print("Claude Persistent Context - Setup")
    print("=" * 40)

    # Run scanner
    print("\nScanning system...")
    scanner = SystemScanner()
    scan_data = scanner.scan_all()

    if args.scan_only:
        print(json.dumps(scan_data, indent=2))
        return

    print(f"  Platform: {scan_data['platform']}")
    print(f"  Hostname: {scan_data['hostname']}")
    print(f"  CPU: {scan_data['cpu'].get('model', 'Unknown')}")
    print(f"  Memory: {scan_data['memory'].get('total_gb', 0)}GB")
    print(f"  GPUs: {len(scan_data['gpus'])}")
    print(f"  Storage devices: {len(scan_data['storage'])}")
    print(f"  Network interfaces: {len(scan_data['network'].get('interfaces', []))}")
    print(f"  SSH keys: {len(scan_data['ssh_keys'])}")

    # Build context
    print("\nBuilding context...")
    context = build_context(scan_data, minimal=args.minimal)

    # Setup directories
    claude_dir = Path.home() / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # Write context file
    context_path = args.context_path
    context_path.write_text(json.dumps(context, indent=2) + "\n")
    print(f"  Created context file: {context_path}")

    # Install components
    print("\nInstalling components...")
    source_dir = Path(__file__).parent
    install_update_script(source_dir, claude_dir, context_path)
    install_hook(claude_dir, context_path)
    initialize_changelog(claude_dir, context)

    print("\n" + "=" * 40)
    print("Setup complete!")
    print("\n" + "=" * 40)
    print("NEXT STEP: Start a Claude Code session and paste this prompt:")
    print("=" * 40)
    print("""
I just installed Claude Persistent Context. Read ~/claude_context.json to see my
system configuration that was auto-detected.

Help me add:
- Remote servers I SSH into regularly (IP, user, purpose)
- Credentials you'll need for accessing systems
- Key file paths I reference often
- Any active projects with current status

Use the update script pattern shown in _instructions_for_claude.
""")


if __name__ == "__main__":
    main()
