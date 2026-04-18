#!/usr/bin/env python3
"""
enb_optimizer.py – Mossy ENB Visual Enhancements
=================================================
A command-line tool that reads, tweaks and applies ENBSeries configuration
presets for Fallout 4.

Features
--------
* Apply a named preset (performance / balanced / ultra).
* Auto-detect an appropriate preset based on the available GPU VRAM.
* Tweak individual settings interactively without leaving the terminal.
* Backup the current ``enbseries.ini`` before overwriting it.

Usage
-----
    python enb_optimizer.py apply --preset balanced
    python enb_optimizer.py apply --auto
    python enb_optimizer.py list
    python enb_optimizer.py show --preset ultra
    python enb_optimizer.py tune --setting SSAO_SSIL/EnableAmbientOcclusion --value true

Requirements
------------
Python 3.8+  –  no third-party libraries needed (stdlib only).
"""

from __future__ import annotations

import argparse
import configparser
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
PRESETS_DIR = REPO_ROOT / "presets"
DEST_INI = REPO_ROOT / "enbseries.ini"
BACKUP_DIR = REPO_ROOT / "backups"

PRESET_FILES: dict[str, Path] = {
    "performance": PRESETS_DIR / "enbseries_performance.ini",
    "balanced": PRESETS_DIR / "enbseries_balanced.ini",
    "ultra": PRESETS_DIR / "enbseries_ultra.ini",
}

# VRAM thresholds (MiB) used by --auto detection
VRAM_THRESHOLDS: list[tuple[int, str]] = [
    (8192, "ultra"),
    (4096, "balanced"),
    (0, "performance"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_ini(path: Path) -> configparser.ConfigParser:
    """Read a Windows-style INI file (no default section required)."""
    cfg = configparser.ConfigParser(
        allow_no_value=True,
        inline_comment_prefixes=(";", "#"),
    )
    cfg.optionxform = str  # preserve key case
    # Wrap in a fake [DEFAULT] to avoid "MissingSectionHeaderError" for files
    # that start with a section immediately.
    text = path.read_text(encoding="utf-8")
    cfg.read_string(text)
    return cfg


def _write_ini(cfg: configparser.ConfigParser, path: Path) -> None:
    """Write an INI file preserving section order and key case."""
    lines: list[str] = []
    for section in cfg.sections():
        lines.append(f"[{section}]")
        for key, value in cfg.items(section):
            lines.append(f"{key}={value}" if value is not None else key)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _backup(path: Path) -> Optional[Path]:
    """Create a timestamped backup of *path* and return the backup path."""
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"enbseries_{timestamp}.ini.bak"
    shutil.copy2(path, backup_path)
    return backup_path


def _detect_vram_mib() -> int:
    """
    Best-effort VRAM detection using platform-specific tools.
    Returns 0 if detection fails (falls back to *performance* preset).
    """
    # --- Windows: wmic -----------------------------------------
    if sys.platform == "win32":
        try:
            import subprocess

            out = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "AdapterRAM"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    return int(line) // (1024 * 1024)
        except Exception:
            pass
    # --- Linux: /proc/driver/nvidia/gpus or sysfs ---------------
    try:
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            import subprocess

            out = subprocess.check_output(
                [
                    nvidia_smi,
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            total = out.strip().split("\n")[0].strip()
            if total.isdigit():
                return int(total)
    except Exception:
        pass
    return 0


def _choose_preset_by_vram(vram_mib: int) -> str:
    for threshold, name in VRAM_THRESHOLDS:
        if vram_mib >= threshold:
            return name
    return "performance"


def _print_section_table(cfg: configparser.ConfigParser) -> None:
    """Pretty-print all sections and their key=value pairs."""
    for section in cfg.sections():
        print(f"\n  [{section}]")
        for key, value in cfg.items(section):
            print(f"    {key} = {value}")


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


def cmd_list(_args: argparse.Namespace) -> None:
    """List all available presets."""
    print("\nAvailable presets:\n")
    for name, path in PRESET_FILES.items():
        status = "✓" if path.exists() else "✗ (missing)"
        print(f"  {name:<15} {status}")
    print()


def cmd_show(args: argparse.Namespace) -> None:
    """Show the contents of a preset."""
    preset = args.preset.lower()
    if preset not in PRESET_FILES:
        print(f"[ERROR] Unknown preset '{preset}'. Use one of: {', '.join(PRESET_FILES)}")
        sys.exit(1)
    path = PRESET_FILES[preset]
    if not path.exists():
        print(f"[ERROR] Preset file not found: {path}")
        sys.exit(1)
    cfg = _read_ini(path)
    print(f"\n=== Preset: {preset} ({path}) ===")
    _print_section_table(cfg)
    print()


def cmd_apply(args: argparse.Namespace) -> None:
    """Copy a preset to the active enbseries.ini."""
    if args.auto:
        vram = _detect_vram_mib()
        preset = _choose_preset_by_vram(vram)
        print(f"[AUTO] Detected ~{vram} MiB VRAM → selecting preset: {preset}")
    else:
        preset = args.preset.lower() if args.preset else "balanced"

    if preset not in PRESET_FILES:
        print(f"[ERROR] Unknown preset '{preset}'. Use one of: {', '.join(PRESET_FILES)}")
        sys.exit(1)

    src = PRESET_FILES[preset]
    if not src.exists():
        print(f"[ERROR] Preset file not found: {src}")
        sys.exit(1)

    backup = _backup(DEST_INI)
    if backup:
        print(f"[BACKUP] Existing enbseries.ini backed up to: {backup}")

    shutil.copy2(src, DEST_INI)
    print(f"[OK] Preset '{preset}' applied → {DEST_INI}")
    print("     Restart Fallout 4 (or press [Shift+Enter] in-game) to reload ENB.")


def cmd_tune(args: argparse.Namespace) -> None:
    """
    Modify a single setting in the active enbseries.ini.

    Setting path format:  SECTION/Key
    Example:  SSAO_SSIL/EnableAmbientOcclusion
    """
    if "/" not in args.setting:
        print("[ERROR] Setting must be in SECTION/Key format, e.g. SSAO_SSIL/EnableAmbientOcclusion")
        sys.exit(1)

    section, key = args.setting.split("/", 1)

    if not DEST_INI.exists():
        print(f"[ERROR] {DEST_INI} not found. Run 'apply' first.")
        sys.exit(1)

    backup = _backup(DEST_INI)
    if backup:
        print(f"[BACKUP] Existing enbseries.ini backed up to: {backup}")

    cfg = _read_ini(DEST_INI)

    if not cfg.has_section(section):
        print(f"[ERROR] Section [{section}] not found in {DEST_INI}")
        sys.exit(1)

    old_value = cfg.get(section, key, fallback="<not set>")
    cfg.set(section, key, args.value)
    _write_ini(cfg, DEST_INI)

    print(f"[OK] [{section}] {key}  {old_value} → {args.value}")
    print("     Press [Shift+Enter] in-game to reload ENB settings.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enb_optimizer",
        description="Mossy ENB – Fallout 4 ENB preset manager and optimizer",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    sub.add_parser("list", help="List available presets")

    # show
    p_show = sub.add_parser("show", help="Display the settings of a preset")
    p_show.add_argument("--preset", required=True, choices=list(PRESET_FILES), help="Preset name")

    # apply
    p_apply = sub.add_parser("apply", help="Apply a preset to enbseries.ini")
    group = p_apply.add_mutually_exclusive_group(required=True)
    group.add_argument("--preset", choices=list(PRESET_FILES), help="Preset name to apply")
    group.add_argument(
        "--auto",
        action="store_true",
        help="Auto-detect GPU VRAM and choose the best preset",
    )

    # tune
    p_tune = sub.add_parser("tune", help="Change a single setting in the active enbseries.ini")
    p_tune.add_argument(
        "--setting",
        required=True,
        metavar="SECTION/Key",
        help="Setting path, e.g. SSAO_SSIL/EnableAmbientOcclusion",
    )
    p_tune.add_argument("--value", required=True, help="New value to assign")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "list": cmd_list,
        "show": cmd_show,
        "apply": cmd_apply,
        "tune": cmd_tune,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
