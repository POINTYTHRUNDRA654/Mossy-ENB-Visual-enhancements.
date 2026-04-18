#!/usr/bin/env python3
"""
tools/patch_enblocal.py – Mossy ENB Visual Enhancements
========================================================
Standalone helper that writes optimal memory and performance settings into
``enblocal.ini`` based on the installed GPU's VRAM.

This script is a convenience wrapper around the ``patch-local`` sub-command
in ``enb_optimizer.py``.  It is useful when you want to run just the memory-
patching step without loading the rest of the optimizer.

Usage
-----
    python tools/patch_enblocal.py                        # auto-detect VRAM
    python tools/patch_enblocal.py --video-mb 7680        # manual override
    python tools/patch_enblocal.py --game-dir "C:\\Steam\\steamapps\\common\\Fallout4"

Arguments
---------
--game-dir  PATH    Path to your Fallout 4 installation folder.
                    Defaults to the repo root (useful when the repo lives
                    inside the game folder or a mod-manager staging area).
--video-mb  MiB     Explicit VideoMemorySizeMb value.  When omitted the value
                    is calculated automatically from the detected VRAM.
--reserved-mb MiB   ReservedMemorySizeMb.  Default: 256 MiB.
--fps-limit FLOAT   Target frame rate for ENB's built-in FPS cap.  Default: 60.

Requirements
------------
Python 3.8+ — stdlib only.
"""

from __future__ import annotations

import argparse
import configparser
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Import shared helpers from enb_optimizer (both live in the repo root)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from enb_optimizer import (  # noqa: E402
    _calc_memory_budget,
    _detect_vram_mib,
    _read_ini,
    _write_ini,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# VRAM-to-memory-budget pairs (MiB).
# Keeps ~512 MiB free for the OS and audio/background processes.
_DEFAULT_ENBLOCAL = "enblocal.ini"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _backup(path: Path) -> Path | None:
    """Timestamped backup; returns the backup path or None if src missing."""
    if not path.exists():
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = backup_dir / f"enblocal_{ts}.ini.bak"
    shutil.copy2(path, dst)
    return dst


def patch(
    enblocal_path: Path,
    video_mb: int,
    reserved_mb: int,
    fps_limit: float = 60.0,
) -> None:
    """Apply memory and performance settings to *enblocal_path*."""
    if not enblocal_path.exists():
        print(f"[ERROR] enblocal.ini not found: {enblocal_path}")
        sys.exit(1)

    bak = _backup(enblocal_path)
    if bak:
        print(f"[BACKUP] {enblocal_path.name} backed up → {bak}")

    cfg = _read_ini(enblocal_path)

    # [GLOBAL]
    if not cfg.has_section("GLOBAL"):
        cfg.add_section("GLOBAL")
    cfg.set("GLOBAL", "AutodetectVideoMemorySize", "false")

    # [MEMORY]
    if not cfg.has_section("MEMORY"):
        cfg.add_section("MEMORY")
    cfg.set("MEMORY", "VideoMemorySizeMb", str(video_mb))
    cfg.set("MEMORY", "ReservedMemorySizeMb", str(reserved_mb))

    # [ENGINE]
    if not cfg.has_section("ENGINE"):
        cfg.add_section("ENGINE")
    cfg.set("ENGINE", "EnableVSync", "false")
    cfg.set("ENGINE", "EnableFpsLimit", "true")
    cfg.set("ENGINE", "FpsLimit", f"{fps_limit:.1f}")

    _write_ini(cfg, enblocal_path)

    print(f"[OK] Patched {enblocal_path}:")
    print(f"     VideoMemorySizeMb       = {video_mb}")
    print(f"     ReservedMemorySizeMb    = {reserved_mb}")
    print(f"     AutodetectVideoMemorySize = false")
    print(f"     EnableVSync = false  |  EnableFpsLimit = true  |  FpsLimit = {fps_limit:.1f}")
    print("     Restart Fallout 4 for the memory settings to take effect.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Patch enblocal.ini memory/performance values for your GPU",
    )
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=REPO_ROOT,
        metavar="PATH",
        help="Path to Fallout 4 install directory (default: repo root)",
    )
    parser.add_argument(
        "--video-mb",
        type=int,
        default=None,
        metavar="MiB",
        help="Explicit VideoMemorySizeMb.  Auto-detected when omitted.",
    )
    parser.add_argument(
        "--reserved-mb",
        type=int,
        default=256,
        metavar="MiB",
        help="ReservedMemorySizeMb (default: 256)",
    )
    parser.add_argument(
        "--fps-limit",
        type=float,
        default=60.0,
        metavar="FPS",
        help="Target FPS cap written to FpsLimit (default: 60.0)",
    )
    args = parser.parse_args()

    enblocal = args.game_dir / _DEFAULT_ENBLOCAL

    if args.video_mb is None:
        vram = _detect_vram_mib()
        video_mb, reserved_mb = _calc_memory_budget(vram)
        print(f"[AUTO] Detected ~{vram} MiB VRAM → VideoMemorySizeMb={video_mb}")
    else:
        video_mb = args.video_mb
        reserved_mb = args.reserved_mb

    patch(enblocal, video_mb, reserved_mb, fps_limit=args.fps_limit)


if __name__ == "__main__":
    main()
