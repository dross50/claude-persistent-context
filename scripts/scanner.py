#!/usr/bin/env python3
"""
Cross-platform system scanner for Claude Persistent Context.
Detects hardware, network, and configuration details.
"""

import json
import os
import platform
import re
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any


def run_command(cmd: list[str] | str, shell: bool = False) -> str:
    """Run a command and return output, or empty string on failure."""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        return ""


def get_platform() -> str:
    """Return normalized platform name."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system  # linux, windows


class SystemScanner:
    """Scans system for hardware and configuration details."""

    def __init__(self):
        self.platform = get_platform()
        self.data = {}

    def scan_all(self) -> dict[str, Any]:
        """Run all scans and return combined results."""
        self.data = {
            "platform": self.platform,
            "hostname": socket.gethostname(),
            "cpu": self.scan_cpu(),
            "memory": self.scan_memory(),
            "gpus": self.scan_gpus(),
            "storage": self.scan_storage(),
            "network": self.scan_network(),
            "ssh_keys": self.scan_ssh_keys(),
        }
        return self.data

    def scan_cpu(self) -> dict[str, Any]:
        """Detect CPU information."""
        cpu_info = {"model": "Unknown", "cores": 0, "threads": 0}

        if self.platform == "linux":
            lscpu = run_command(["lscpu"])
            cores_per = None
            sockets = None
            for line in lscpu.split("\n"):
                try:
                    if line.startswith("Model name:"):
                        cpu_info["model"] = line.split(":", 1)[1].strip()
                    elif line.startswith("CPU(s):"):
                        cpu_info["threads"] = int(line.split(":", 1)[1].strip())
                    elif line.startswith("Core(s) per socket:"):
                        cores_per = int(line.split(":", 1)[1].strip())
                    elif line.startswith("Socket(s):"):
                        sockets = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass
            if cores_per and sockets:
                cpu_info["cores"] = cores_per * sockets

        elif self.platform == "macos":
            cpu_info["model"] = run_command(["sysctl", "-n", "machdep.cpu.brand_string"]) or "Unknown"
            cores = run_command(["sysctl", "-n", "hw.physicalcpu"])
            threads = run_command(["sysctl", "-n", "hw.logicalcpu"])
            try:
                if cores:
                    cpu_info["cores"] = int(cores)
                if threads:
                    cpu_info["threads"] = int(threads)
            except ValueError:
                pass

        elif self.platform == "windows":
            wmic = run_command("wmic cpu get name,numberofcores,numberoflogicalprocessors /format:csv", shell=True)
            lines = [l for l in wmic.split("\n") if l.strip() and not l.startswith("Node")]
            if lines:
                parts = lines[0].split(",")
                if len(parts) >= 4:
                    cpu_info["model"] = parts[1].strip()
                    cpu_info["cores"] = int(parts[2]) if parts[2].strip().isdigit() else 0
                    cpu_info["threads"] = int(parts[3]) if parts[3].strip().isdigit() else 0

        return cpu_info

    def scan_memory(self) -> dict[str, Any]:
        """Detect memory information."""
        mem_info = {"total_gb": 0}

        if self.platform == "linux":
            meminfo = run_command(["cat", "/proc/meminfo"])
            for line in meminfo.split("\n"):
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    mem_info["total_gb"] = round(kb / 1024 / 1024)
                    break

        elif self.platform == "macos":
            mem_bytes = run_command(["sysctl", "-n", "hw.memsize"])
            if mem_bytes:
                mem_info["total_gb"] = round(int(mem_bytes) / 1024 / 1024 / 1024)

        elif self.platform == "windows":
            wmic = run_command("wmic computersystem get totalphysicalmemory /format:csv", shell=True)
            lines = [l for l in wmic.split("\n") if l.strip() and not l.startswith("Node")]
            if lines:
                parts = lines[0].split(",")
                if len(parts) >= 2 and parts[1].strip().isdigit():
                    mem_info["total_gb"] = round(int(parts[1]) / 1024 / 1024 / 1024)

        return mem_info

    def scan_gpus(self) -> list[dict[str, Any]]:
        """Detect GPUs (NVIDIA, AMD, Intel, Apple Silicon)."""
        gpus = []

        # NVIDIA via nvidia-smi
        if shutil.which("nvidia-smi"):
            output = run_command([
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,pci.bus_id,uuid",
                "--format=csv,noheader,nounits"
            ])
            for line in output.split("\n"):
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpus.append({
                        "vendor": "NVIDIA",
                        "index": int(parts[0]),
                        "model": parts[1],
                        "vram_mb": int(parts[2]) if parts[2].isdigit() else 0,
                        "pcie_bus": parts[3],
                        "uuid": parts[4]
                    })

        # AMD via rocm-smi
        if shutil.which("rocm-smi"):
            output = run_command(["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--json"])
            if output:
                try:
                    data = json.loads(output)
                    for card_id, card_info in data.items():
                        if card_id.startswith("card"):
                            gpus.append({
                                "vendor": "AMD",
                                "index": int(card_id.replace("card", "")),
                                "model": card_info.get("Card series", "Unknown AMD GPU"),
                                "vram_mb": int(card_info.get("VRAM Total Memory (B)", 0)) // (1024 * 1024),
                            })
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass

        # Linux: fallback to lspci for AMD/Intel if no vendor tools
        if self.platform == "linux" and not any(g["vendor"] == "AMD" for g in gpus):
            lspci = run_command(["lspci", "-nn"])
            for line in lspci.split("\n"):
                # VGA or 3D controller
                if "VGA" in line or "3D controller" in line:
                    if "AMD" in line or "ATI" in line or "Radeon" in line:
                        # Extract model name (text between : and [)
                        match = re.search(r":\s*(.+?)\s*\[", line)
                        model = match.group(1) if match else "AMD GPU"
                        if not any("AMD" in g.get("vendor", "") and model in g.get("model", "") for g in gpus):
                            gpus.append({
                                "vendor": "AMD",
                                "model": model,
                                "source": "lspci"
                            })
                    elif "Intel" in line:
                        match = re.search(r":\s*(.+?)\s*\[", line)
                        model = match.group(1) if match else "Intel GPU"
                        gpus.append({
                            "vendor": "Intel",
                            "model": model,
                            "source": "lspci"
                        })

        # macOS: Apple Silicon or discrete GPUs
        if self.platform == "macos":
            sp_output = run_command(["system_profiler", "SPDisplaysDataType", "-json"])
            if sp_output:
                try:
                    data = json.loads(sp_output)
                    displays = data.get("SPDisplaysDataType", [])
                    for i, gpu in enumerate(displays):
                        gpu_info = {
                            "vendor": "Apple" if "apple" in gpu.get("sppci_vendor", "").lower() else gpu.get("sppci_vendor", "Unknown"),
                            "index": i,
                            "model": gpu.get("sppci_model", "Unknown"),
                        }
                        # VRAM if available (not on Apple Silicon unified memory)
                        vram = gpu.get("spdisplays_vram", "")
                        if vram and "MB" in vram:
                            gpu_info["vram_mb"] = int(vram.replace("MB", "").strip())
                        elif vram and "GB" in vram:
                            gpu_info["vram_mb"] = int(float(vram.replace("GB", "").strip()) * 1024)
                        gpus.append(gpu_info)
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass

        # Windows: fallback to wmic if no NVIDIA
        if self.platform == "windows" and not gpus:
            wmic = run_command("wmic path win32_videocontroller get name,adapterram /format:csv", shell=True)
            lines = [l for l in wmic.split("\n") if l.strip() and not l.startswith("Node")]
            for i, line in enumerate(lines):
                parts = line.split(",")
                if len(parts) >= 3:
                    vram_bytes = int(parts[1]) if parts[1].strip().isdigit() else 0
                    model = parts[2].strip()
                    vendor = "NVIDIA" if "nvidia" in model.lower() else "AMD" if "amd" in model.lower() or "radeon" in model.lower() else "Intel" if "intel" in model.lower() else "Unknown"
                    gpus.append({
                        "vendor": vendor,
                        "index": i,
                        "model": model,
                        "vram_mb": vram_bytes // (1024 * 1024)
                    })

        return gpus

    def scan_storage(self) -> list[dict[str, Any]]:
        """Detect storage devices."""
        storage = []

        if self.platform == "linux":
            lsblk = run_command(["lsblk", "-d", "-o", "NAME,SIZE,TYPE,MODEL", "-n"])
            for line in lsblk.split("\n"):
                parts = line.split()
                if len(parts) >= 3 and parts[2] == "disk":
                    storage.append({
                        "device": f"/dev/{parts[0]}",
                        "size": parts[1],
                        "model": " ".join(parts[3:]) if len(parts) > 3 else "Unknown"
                    })

        elif self.platform == "macos":
            diskutil = run_command(["diskutil", "list", "-plist"])
            # Simplified - just get disk names
            output = run_command(["diskutil", "list"])
            for line in output.split("\n"):
                if line.startswith("/dev/disk") and "physical" in line.lower():
                    parts = line.split()
                    storage.append({
                        "device": parts[0].rstrip(":"),
                        "size": "Unknown",
                        "model": "Unknown"
                    })

        elif self.platform == "windows":
            wmic = run_command("wmic diskdrive get model,size /format:csv", shell=True)
            lines = [l for l in wmic.split("\n") if l.strip() and not l.startswith("Node")]
            for line in lines:
                parts = line.split(",")
                if len(parts) >= 3:
                    size_bytes = int(parts[2]) if parts[2].strip().isdigit() else 0
                    size_gb = round(size_bytes / 1024 / 1024 / 1024)
                    storage.append({
                        "device": "N/A",
                        "size": f"{size_gb}G",
                        "model": parts[1].strip()
                    })

        return storage

    def scan_network(self) -> dict[str, Any]:
        """Detect network interfaces and configuration."""
        network = {"interfaces": []}

        if self.platform == "linux":
            # Get interfaces with IPs
            ip_output = run_command(["ip", "-o", "addr", "show"])
            interfaces = {}
            for line in ip_output.split("\n"):
                parts = line.split()
                if len(parts) >= 4 and parts[2] in ("inet", "inet6"):
                    iface = parts[1]
                    addr = parts[3].split("/")[0]
                    if iface not in interfaces:
                        interfaces[iface] = {"name": iface, "ipv4": [], "ipv6": []}
                    if parts[2] == "inet":
                        interfaces[iface]["ipv4"].append(addr)
                    else:
                        interfaces[iface]["ipv6"].append(addr)

            network["interfaces"] = list(interfaces.values())

        elif self.platform == "macos":
            ifconfig = run_command(["ifconfig"])
            current_iface = None
            interfaces = {}
            for line in ifconfig.split("\n"):
                if line and not line.startswith("\t") and ":" in line:
                    current_iface = line.split(":")[0]
                    interfaces[current_iface] = {"name": current_iface, "ipv4": [], "ipv6": []}
                elif current_iface and "inet " in line:
                    parts = line.split()
                    idx = parts.index("inet") + 1
                    if idx < len(parts):
                        interfaces[current_iface]["ipv4"].append(parts[idx])
                elif current_iface and "inet6 " in line:
                    parts = line.split()
                    idx = parts.index("inet6") + 1
                    if idx < len(parts):
                        interfaces[current_iface]["ipv6"].append(parts[idx].split("%")[0])

            network["interfaces"] = [v for v in interfaces.values() if v["ipv4"] or v["ipv6"]]

        elif self.platform == "windows":
            ipconfig = run_command("ipconfig", shell=True)
            current_iface = None
            interfaces = {}
            for line in ipconfig.split("\n"):
                if "adapter" in line.lower() and ":" in line:
                    current_iface = line.split(":")[0].strip()
                    interfaces[current_iface] = {"name": current_iface, "ipv4": [], "ipv6": []}
                elif current_iface and "ipv4" in line.lower():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        interfaces[current_iface]["ipv4"].append(parts[1].strip())
                elif current_iface and "ipv6" in line.lower():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        interfaces[current_iface]["ipv6"].append(":".join(parts[1:]).strip())

            network["interfaces"] = [v for v in interfaces.values() if v["ipv4"]]

        return network

    def scan_ssh_keys(self) -> list[dict[str, Any]]:
        """Detect SSH keys in ~/.ssh/."""
        ssh_keys = []
        ssh_dir = Path.home() / ".ssh"

        if not ssh_dir.exists():
            return ssh_keys

        # Find public keys
        for pub_key in ssh_dir.glob("*.pub"):
            key_name = pub_key.stem
            private_key = ssh_dir / key_name

            key_info = {
                "name": key_name,
                "public_key": str(pub_key),
                "has_private": private_key.exists()
            }

            # Try to get key type
            content = pub_key.read_text().strip()
            if content.startswith("ssh-"):
                key_info["type"] = content.split()[0]

            ssh_keys.append(key_info)

        return ssh_keys


def main():
    """Run scanner and output JSON."""
    scanner = SystemScanner()
    data = scanner.scan_all()
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
