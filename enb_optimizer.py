#!/usr/bin/env python3
"""
enb_optimizer.py – Mossy ENB Visual Enhancements
=================================================
A command-line tool that reads, tweaks and applies ENBSeries configuration
presets for Fallout 4.  It also manages ReShade presets and provides
GPU-specific recommendations for DLSS.

Features
--------
* Apply a named ENB preset (performance / balanced / ultra).
* Auto-detect an appropriate preset based on the available GPU VRAM.
* Tweak individual settings interactively without leaving the terminal.
* Backup the current ``enbseries.ini`` before overwriting it.
* List, show and apply ReShade presets (reshade sub-command).
* Detect Nvidia RTX GPUs and recommend DLSS Enabler.
* Patch ``enblocal.ini`` memory values to match detected GPU VRAM
  (patch-local sub-command).

Usage
-----
    python enb_optimizer.py apply --preset balanced
    python enb_optimizer.py apply --auto
    python enb_optimizer.py list
    python enb_optimizer.py show --preset ultra
    python enb_optimizer.py tune --setting SSAO_SSIL/EnableAmbientOcclusion --value true
    python enb_optimizer.py patch-local --auto-vram
    python enb_optimizer.py reshade list
    python enb_optimizer.py reshade show --preset balanced
    python enb_optimizer.py reshade apply --preset ultra
    python enb_optimizer.py reshade apply --preset screenshot
    python enb_optimizer.py reshade apply --auto

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
ENBLOCAL_INI = REPO_ROOT / "enblocal.ini"
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
# ReShade paths
# ---------------------------------------------------------------------------

RESHADE_DIR = REPO_ROOT / "reshade"
RESHADE_PRESETS_DIR = RESHADE_DIR / "reshade-presets"
RESHADE_DEST_INI = RESHADE_DIR / "ReShade.ini"
RESHADE_BACKUP_DIR = BACKUP_DIR / "reshade"

RESHADE_PRESET_FILES: dict[str, Path] = {
    "performance": RESHADE_PRESETS_DIR / "Mossy_performance.ini",
    "balanced": RESHADE_PRESETS_DIR / "Mossy_balanced.ini",
    "ultra": RESHADE_PRESETS_DIR / "Mossy_ultra.ini",
    "screenshot": RESHADE_PRESETS_DIR / "Mossy_screenshot.ini",
}

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

    Side effect: if an Nvidia RTX GPU is detected, prints a recommendation
    to install DLSS Enabler for AI-powered upscaling in Fallout 4.
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
                    vram = int(line) // (1024 * 1024)
                    _maybe_print_dlss_tip(_detect_gpu_name())
                    return vram
        except Exception:
            pass
    # --- Linux: nvidia-smi --------------------------------------
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
                _maybe_print_dlss_tip(_detect_gpu_name())
                return int(total)
    except Exception:
        pass
    return 0


def _detect_gpu_name() -> str:
    """Best-effort GPU name detection.  Returns an empty string on failure."""
    if sys.platform == "win32":
        try:
            import subprocess

            out = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "Name"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            for line in out.splitlines():
                line = line.strip()
                if line and line.lower() != "name":
                    return line
        except Exception:
            pass
    try:
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            import subprocess

            out = subprocess.check_output(
                [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            name = out.strip().split("\n")[0].strip()
            if name:
                return name
    except Exception:
        pass
    return ""


def _is_rtx_gpu(name: str) -> bool:
    """Return True if *name* looks like an Nvidia RTX GPU."""
    return "RTX" in name.upper()


def _maybe_print_dlss_tip(gpu_name: str) -> None:
    """Print a DLSS recommendation when an Nvidia RTX GPU is detected."""
    if _is_rtx_gpu(gpu_name):
        print(f"[DLSS] Nvidia RTX GPU detected: {gpu_name}")
        print("       Install 'DLSS Enabler' by PureDark (Nexus Mods) to add DLSS to Fallout 4.")
        print("       Recommended enblocal.ini: EnableVSync=false, FpsLimit=60.0")


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
# patch-local sub-command
# ---------------------------------------------------------------------------

# VRAM-to-memory-budget mapping (MiB).
# ENB docs recommend leaving ~512 MiB headroom for the OS and other processes.
_VRAM_BUDGET_TABLE: list[tuple[int, int, int]] = [
    # (min_vram_mib, video_size_mib, reserved_size_mib)
    (8192, 7680, 512),
    (6144, 5632, 512),
    (4096, 3584, 256),
    (2048, 1792, 128),
    (0,    1024, 128),
]


def _calc_memory_budget(vram_mib: int) -> tuple[int, int]:
    """Return (VideoMemorySizeMb, ReservedMemorySizeMb) for the given VRAM."""
    for min_vram, video, reserved in _VRAM_BUDGET_TABLE:
        if vram_mib >= min_vram:
            return video, reserved
    return 1024, 128


def cmd_patch_local(args: argparse.Namespace) -> None:
    """
    Write optimal memory and performance settings into enblocal.ini.

    With --auto-vram the VRAM is detected automatically and the best
    VideoMemorySizeMb / ReservedMemorySizeMb pair is calculated.
    EnableVSync, EnableFpsLimit, and FpsLimit are also written.
    """
    if not ENBLOCAL_INI.exists():
        print(f"[ERROR] {ENBLOCAL_INI} not found.")
        sys.exit(1)

    if args.auto_vram:
        vram = _detect_vram_mib()
        video_mb, reserved_mb = _calc_memory_budget(vram)
        print(f"[AUTO] Detected ~{vram} MiB VRAM → VideoMemorySizeMb={video_mb}, ReservedMemorySizeMb={reserved_mb}")
    else:
        # Manual values supplied via --video-mb and --reserved-mb
        video_mb = args.video_mb
        reserved_mb = args.reserved_mb

    backup = _backup_local(ENBLOCAL_INI)
    if backup:
        print(f"[BACKUP] Existing enblocal.ini backed up to: {backup}")

    cfg = _read_ini(ENBLOCAL_INI)

    # [MEMORY] section
    if not cfg.has_section("MEMORY"):
        cfg.add_section("MEMORY")
    cfg.set("MEMORY", "VideoMemorySizeMb", str(video_mb))
    cfg.set("MEMORY", "ReservedMemorySizeMb", str(reserved_mb))

    # [GLOBAL] – turn off ENB auto-detect so our values are used
    if not cfg.has_section("GLOBAL"):
        cfg.add_section("GLOBAL")
    cfg.set("GLOBAL", "AutodetectVideoMemorySize", "false")

    # [ENGINE] – recommended frame-rate settings
    if not cfg.has_section("ENGINE"):
        cfg.add_section("ENGINE")
    cfg.set("ENGINE", "EnableVSync", "false")
    cfg.set("ENGINE", "EnableFpsLimit", "true")
    cfg.set("ENGINE", "FpsLimit", "60.0")

    _write_ini(cfg, ENBLOCAL_INI)

    print(f"[OK] enblocal.ini patched:")
    print(f"     VideoMemorySizeMb    = {video_mb}")
    print(f"     ReservedMemorySizeMb = {reserved_mb}")
    print(f"     AutodetectVideoMemorySize = false")
    print(f"     EnableVSync = false  |  EnableFpsLimit = true  |  FpsLimit = 60.0")
    print("     Restart Fallout 4 for the memory settings to take effect.")


def _backup_local(path: Path) -> Optional[Path]:
    """Create a timestamped backup of enblocal.ini in the backups dir."""
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"enblocal_{timestamp}.ini.bak"
    shutil.copy2(path, backup_path)
    return backup_path


# ---------------------------------------------------------------------------
# ReShade sub-commands
# ---------------------------------------------------------------------------


def cmd_reshade_list(_args: argparse.Namespace) -> None:
    """List all available ReShade presets."""
    print("\nAvailable ReShade presets:\n")
    for name, path in RESHADE_PRESET_FILES.items():
        status = "✓" if path.exists() else "✗ (missing)"
        print(f"  {name:<15} {status}")
    print()


def cmd_reshade_show(args: argparse.Namespace) -> None:
    """Show the contents of a ReShade preset."""
    preset = args.preset.lower()
    if preset not in RESHADE_PRESET_FILES:
        print(f"[ERROR] Unknown ReShade preset '{preset}'. Use one of: {', '.join(RESHADE_PRESET_FILES)}")
        sys.exit(1)
    path = RESHADE_PRESET_FILES[preset]
    if not path.exists():
        print(f"[ERROR] ReShade preset file not found: {path}")
        sys.exit(1)
    cfg = _read_ini(path)
    print(f"\n=== ReShade preset: {preset} ({path}) ===")
    _print_section_table(cfg)
    print()


def cmd_reshade_apply(args: argparse.Namespace) -> None:
    """
    Set the active ReShade preset by updating PresetPath in ReShade.ini.

    Uses --auto to mirror the ENB VRAM-detection logic.
    """
    if args.auto:
        vram = _detect_vram_mib()
        preset = _choose_preset_by_vram(vram)
        print(f"[AUTO] Detected ~{vram} MiB VRAM → selecting ReShade preset: {preset}")
    else:
        preset = args.preset.lower() if args.preset else "balanced"

    if preset not in RESHADE_PRESET_FILES:
        print(f"[ERROR] Unknown ReShade preset '{preset}'. Use one of: {', '.join(RESHADE_PRESET_FILES)}")
        sys.exit(1)

    preset_path = RESHADE_PRESET_FILES[preset]
    if not preset_path.exists():
        print(f"[ERROR] ReShade preset file not found: {preset_path}")
        sys.exit(1)

    if not RESHADE_DEST_INI.exists():
        print(f"[ERROR] {RESHADE_DEST_INI} not found. Ensure the reshade/ directory is present.")
        sys.exit(1)

    # Back up current ReShade.ini before modifying it.
    backup = _backup_reshade(RESHADE_DEST_INI)
    if backup:
        print(f"[BACKUP] Existing ReShade.ini backed up to: {backup}")

    # Update the PresetPath key in [GENERAL].
    cfg = _read_ini(RESHADE_DEST_INI)
    if not cfg.has_section("GENERAL"):
        cfg.add_section("GENERAL")
    # Store a relative path from the game root (same directory as ReShade.ini).
    relative = f".\\reshade-presets\\{preset_path.name}"
    cfg.set("GENERAL", "PresetPath", relative)
    _write_ini(cfg, RESHADE_DEST_INI)

    print(f"[OK] ReShade preset '{preset}' activated → PresetPath={relative}")
    print("     Press [Home] in-game to open the ReShade overlay and confirm the change.")


def _backup_reshade(path: Path) -> Optional[Path]:
    """Create a timestamped backup of a ReShade file in the reshade backup dir."""
    if not path.exists():
        return None
    RESHADE_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = RESHADE_BACKUP_DIR / f"ReShade_{timestamp}.ini.bak"
    shutil.copy2(path, backup_path)
    return backup_path


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
    sub.add_parser("list", help="List available ENB presets")

    # show
    p_show = sub.add_parser("show", help="Display the settings of an ENB preset")
    p_show.add_argument("--preset", required=True, choices=list(PRESET_FILES), help="Preset name")

    # apply
    p_apply = sub.add_parser("apply", help="Apply an ENB preset to enbseries.ini")
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

    # patch-local
    p_patch = sub.add_parser(
        "patch-local",
        help="Patch enblocal.ini memory/performance values for your GPU",
    )
    patch_group = p_patch.add_mutually_exclusive_group(required=True)
    patch_group.add_argument(
        "--auto-vram",
        action="store_true",
        help="Auto-detect GPU VRAM and calculate optimal memory budget",
    )
    patch_group.add_argument(
        "--video-mb",
        type=int,
        metavar="MiB",
        help="Explicit VideoMemorySizeMb value (requires --reserved-mb)",
    )
    p_patch.add_argument(
        "--reserved-mb",
        type=int,
        default=256,
        metavar="MiB",
        help="ReservedMemorySizeMb value when using --video-mb (default: 256)",
    )

    # reshade  (sub-command group)
    p_reshade = sub.add_parser("reshade", help="Manage ReShade presets")
    reshade_sub = p_reshade.add_subparsers(dest="reshade_command", required=True)

    # reshade list
    reshade_sub.add_parser("list", help="List available ReShade presets")

    # reshade show
    p_rs_show = reshade_sub.add_parser("show", help="Display the settings of a ReShade preset")
    p_rs_show.add_argument(
        "--preset", required=True, choices=list(RESHADE_PRESET_FILES), help="Preset name"
    )

    # reshade apply
    p_rs_apply = reshade_sub.add_parser("apply", help="Activate a ReShade preset via ReShade.ini")
    rs_group = p_rs_apply.add_mutually_exclusive_group(required=True)
    rs_group.add_argument("--preset", choices=list(RESHADE_PRESET_FILES), help="Preset name")
    rs_group.add_argument(
        "--auto",
        action="store_true",
        help="Auto-detect GPU VRAM and choose the best ReShade preset",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "reshade":
        reshade_dispatch = {
            "list": cmd_reshade_list,
            "show": cmd_reshade_show,
            "apply": cmd_reshade_apply,
        }
        reshade_dispatch[args.reshade_command](args)
        return

    dispatch = {
        "list": cmd_list,
        "show": cmd_show,
        "apply": cmd_apply,
        "tune": cmd_tune,
        "patch-local": cmd_patch_local,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
