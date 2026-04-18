#!/usr/bin/env python3
"""
tools/verify_install.py – Mossy ENB Visual Enhancements
========================================================
Checks that every file required by ENBSeries and ReShade is present in the
target Fallout 4 installation directory, then prints a pass/fail checklist.

Run this after installing ENB and ReShade to confirm nothing is missing before
launching the game for the first time.

Usage
-----
    python tools/verify_install.py
    python tools/verify_install.py --game-dir "C:\\Steam\\steamapps\\common\\Fallout4"

Exit codes
----------
0  — all required files found
1  — one or more required files are missing

Requirements
------------
Python 3.8+ — stdlib only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo root (used as default game dir when the repo lives inside the game
# folder or when testing outside a real installation)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Required files
# ---------------------------------------------------------------------------

# Each entry is (relative_path_from_game_dir, description, optional).
# optional=True means the file is recommended but the game can start without it.
REQUIRED_FILES: list[tuple[str, str, bool]] = [
    # ENBSeries core
    ("d3d11.dll",                          "ENBSeries core DLL",                   False),
    ("d3dcompiler_46e.dll",                "ENBSeries shader compiler",            False),
    ("enbseries.ini",                      "ENB effect settings",                  False),
    ("enblocal.ini",                       "ENB local hardware settings",          False),
    # ReShade core
    ("ReShade.ini",                        "ReShade master config",                False),
    ("reshade-shaders/Shaders/SMAA.fx",    "SMAA shader (bundled with ReShade)",   False),
    # iMMERSE free shaders
    ("reshade-shaders/Shaders/MXAO.fx",    "iMMERSE MXAO ambient occlusion",      False),
    # qUINT shaders
    ("reshade-shaders/Shaders/AdaptiveSharpen.fx", "qUINT AdaptiveSharpen",        False),
    ("reshade-shaders/Shaders/Bloom.fx",   "qUINT Bloom",                          False),
    ("reshade-shaders/Shaders/DOF.fx",     "qUINT Depth-of-Field",                 False),
    ("reshade-shaders/Shaders/FilmGrain.fx", "qUINT FilmGrain",                    False),
    # iMMERSE LUT shader
    ("reshade-shaders/Shaders/LUT.fx",     "iMMERSE LUT shader",                   True),
    # LUT texture
    ("reshade-shaders/Textures/MossyLUT.png", "Mossy film LUT texture",            True),
    # iMMERSE Pro (optional)
    ("reshade-shaders/Shaders/iMMERSE_RTGI.fx", "iMMERSE Pro RTGI (Patreon)",     True),
    # F4SE (optional but strongly recommended)
    ("f4se_loader.exe",                    "F4SE loader (strongly recommended)",   True),
]

# ---------------------------------------------------------------------------
# Check logic
# ---------------------------------------------------------------------------


def check(game_dir: Path) -> bool:
    """
    Check all required files against *game_dir*.

    Returns True when every non-optional file is found, False otherwise.
    """
    pass_count = 0
    fail_count = 0
    warn_count = 0

    col_path = 50
    col_desc = 42

    print(f"\nChecking Fallout 4 installation: {game_dir}\n")
    print(f"  {'File':<{col_path}}  {'Description':<{col_desc}}  Status")
    print(f"  {'-' * col_path}  {'-' * col_desc}  ------")

    for rel_path, description, optional in REQUIRED_FILES:
        full = game_dir / rel_path
        exists = full.exists()

        if exists:
            status = "✓  OK"
            pass_count += 1
        elif optional:
            status = "⚠  MISSING (optional)"
            warn_count += 1
        else:
            status = "✗  MISSING"
            fail_count += 1

        print(f"  {rel_path:<{col_path}}  {description:<{col_desc}}  {status}")

    print()
    print(f"  Result: {pass_count} present, {warn_count} optional missing, {fail_count} required missing")

    if fail_count:
        print("\n[FAIL] Some required files are missing.  Install ENB and/or ReShade then re-run.")
        _print_install_hints(game_dir)
        return False

    if warn_count:
        print("\n[WARN] Optional files are missing — some preset features will be unavailable.")
        _print_install_hints(game_dir)

    print("\n[PASS] All required files found.  You are ready to launch Fallout 4.")
    return True


def _print_install_hints(game_dir: Path) -> None:
    """Print a quick reference for where to get each missing component."""
    print()
    print("  Install / download locations:")
    print("    ENBSeries:    http://enbdev.com/download_mod_fallout4.htm")
    print("                  → extract d3d11.dll + d3dcompiler_46e.dll into:")
    print(f"                    {game_dir}")
    print("    ReShade:      https://reshade.me/")
    print("                  → run the ReShade installer and select Fallout4.exe")
    print("    iMMERSE:      https://github.com/martymcmodding/iMMERSE")
    print("                  → copy Shaders/ and Textures/ into reshade-shaders/")
    print("    iMMERSE Pro:  https://www.patreon.com/mcflypg  (paid)")
    print("    qUINT:        https://github.com/martymcmodding/qUINT")
    print("    F4SE:         https://f4se.silverlock.org/")
    print("    MossyLUT.png: run  python tools/generate_lut.py  then copy the")
    print(f"                  PNG into {game_dir / 'reshade-shaders' / 'Textures'}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify ENBSeries + ReShade installation for Fallout 4",
    )
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=REPO_ROOT,
        metavar="PATH",
        help=(
            "Path to your Fallout 4 installation directory "
            "(default: repository root)"
        ),
    )
    args = parser.parse_args()

    ok = check(args.game_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
