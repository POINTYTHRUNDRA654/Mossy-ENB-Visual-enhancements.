#!/usr/bin/env python3
"""
tools/export_diagnostics.py – Mossy ENB Visual Enhancements
============================================================
Dumps GPU name, VRAM, active ENB/ReShade preset, and all non-default INI
values to a ``diagnostics.txt`` file.  Attach this file to bug reports so
maintainers can reproduce your exact configuration.

Usage
-----
    python tools/export_diagnostics.py
    python tools/export_diagnostics.py --game-dir "C:\\Steam\\...\\Fallout4"
    python tools/export_diagnostics.py --out /tmp/my_diagnostics.txt

Output
------
Written to ``diagnostics.txt`` in the repository root by default.

Requirements
------------
Python 3.8+ — stdlib only.
"""

from __future__ import annotations

import argparse
import configparser
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from enb_optimizer import (  # noqa: E402
    PRESET_FILES,
    RESHADE_PRESET_FILES,
    _detect_gpu_name,
    _detect_vram_mib,
    _read_ini,
)

# ---------------------------------------------------------------------------
# Default baselines — values considered "stock" for each file.
# Non-default values are highlighted in the output.
# ---------------------------------------------------------------------------

# enbseries.ini defaults (subset of common keys)
_ENB_DEFAULTS: dict[str, dict[str, str]] = {
    "GLOBAL": {"UseEffect": "true"},
    "SSAO_SSIL": {
        "EnableAmbientOcclusion": "false",
        "AOType": "0",
        "Quality": "0",
        "EnableIL": "false",
    },
    "SUBSURFACESCATTERING": {"EnableSubSurfaceScattering": "false"},
    "BLOOM": {"EnableBloom": "false"},
    "DETAILSHADOW": {"EnableDetailedShadow": "false"},
    "PARTICLELIGHTS": {
        "EnableParticleLights": "false",
        "EnableParticleLightsShadows": "false",
    },
    "COMPLEXFIRE": {"EnableComplexFire": "false"},
    "COMPLEXPARTICLES": {"EnableComplexParticles": "false"},
    "VOLUMETRICRAYS": {"EnableVolumetricRays": "false"},
}

# enblocal.ini defaults (subset)
_LOCAL_DEFAULTS: dict[str, dict[str, str]] = {
    "MEMORY": {
        "VideoMemorySizeMb": "0",
        "ReservedMemorySizeMb": "128",
    },
    "ENGINE": {
        "EnableVSync": "true",
        "FpsLimit": "0.0",
        "EnableFpsLimit": "false",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _non_default_values(
    cfg: configparser.ConfigParser,
    defaults: dict[str, dict[str, str]],
) -> list[tuple[str, str, str, str]]:
    """
    Return a list of (section, key, value, default) for every value in *cfg*
    that differs from its known default in *defaults*.

    Values with no known default are also included (shown as "default: <unknown>").
    """
    rows: list[tuple[str, str, str, str]] = []
    for section in cfg.sections():
        for key, value in cfg.items(section):
            known = defaults.get(section, {}).get(key)
            if known is None:
                # Not in our baseline — include it; caller can decide what to do
                rows.append((section, key, value, "<unknown>"))
            elif value.lower() != known.lower():
                rows.append((section, key, value, known))
    return rows


def _active_preset(ini_path: Path, preset_files: dict[str, Path]) -> str:
    """Return the name of the preset whose file matches *ini_path* contents."""
    if not ini_path.exists():
        return "<not found>"
    try:
        active = ini_path.read_bytes()
    except OSError:
        return "<unreadable>"
    for name, path in preset_files.items():
        if path.exists() and path.read_bytes() == active:
            return name
    return "<custom / modified>"


def _reshade_active_preset(reshade_ini: Path) -> str:
    """Read PresetPath from ReShade.ini and return just the filename."""
    if not reshade_ini.exists():
        return "<not found>"
    try:
        cfg = _read_ini(reshade_ini)
        return cfg.get("GENERAL", "PresetPath", fallback="<not set>")
    except Exception:
        return "<unreadable>"


# ---------------------------------------------------------------------------
# Main diagnostic builder
# ---------------------------------------------------------------------------


def export(game_dir: Path, out: Path) -> None:
    """Collect diagnostics and write them to *out*."""
    lines: list[str] = []

    def h(title: str) -> None:
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  {title}")
        lines.append("=" * 70)

    def kv(key: str, value: str) -> None:
        lines.append(f"  {key:<40} {value}")

    # Header
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"Mossy ENB Visual Enhancements — Diagnostics Report")
    lines.append(f"Generated: {ts}")
    lines.append(f"Repo root: {REPO_ROOT}")
    lines.append(f"Game dir:  {game_dir}")

    # GPU
    h("GPU")
    gpu_name = _detect_gpu_name()
    vram = _detect_vram_mib()
    kv("GPU name", gpu_name or "(detection failed)")
    kv("VRAM (detected)", f"{vram} MiB" if vram else "(detection failed)")

    # Active presets
    h("Active presets")
    enb_ini = game_dir / "enbseries.ini"
    local_ini = game_dir / "enblocal.ini"
    reshade_ini = game_dir / "ReShade.ini"

    kv("ENB preset",     _active_preset(enb_ini, PRESET_FILES))
    kv("ReShade preset", _reshade_active_preset(reshade_ini))

    # enbseries.ini non-defaults
    h("enbseries.ini — non-default / custom values")
    if enb_ini.exists():
        cfg = _read_ini(enb_ini)
        rows = _non_default_values(cfg, _ENB_DEFAULTS)
        if rows:
            for section, key, value, default in rows:
                lines.append(f"  [{section}] {key} = {value}  (default: {default})")
        else:
            lines.append("  (all values match the stock defaults)")
    else:
        lines.append(f"  (file not found: {enb_ini})")

    # enblocal.ini non-defaults
    h("enblocal.ini — non-default / custom values")
    if local_ini.exists():
        cfg = _read_ini(local_ini)
        rows = _non_default_values(cfg, _LOCAL_DEFAULTS)
        memory_section_rows = [r for r in rows if r[0] == "MEMORY"]
        engine_section_rows = [r for r in rows if r[0] == "ENGINE"]
        other_rows = [r for r in rows if r[0] not in ("MEMORY", "ENGINE")]
        for section, key, value, default in memory_section_rows + engine_section_rows + other_rows:
            lines.append(f"  [{section}] {key} = {value}  (default: {default})")
        if not rows:
            lines.append("  (all values match the stock defaults)")
    else:
        lines.append(f"  (file not found: {local_ini})")

    # ReShade.ini summary
    h("ReShade.ini — key values")
    if reshade_ini.exists():
        cfg = _read_ini(reshade_ini)
        for section in cfg.sections():
            for key, value in cfg.items(section):
                lines.append(f"  [{section}] {key} = {value}")
    else:
        lines.append(f"  (file not found: {reshade_ini})")

    # File presence check
    h("Required file presence")
    from verify_install import REQUIRED_FILES  # local import to avoid circular
    for rel_path, description, optional in REQUIRED_FILES:
        full = game_dir / rel_path
        status = "present" if full.exists() else ("MISSING (optional)" if optional else "MISSING")
        lines.append(f"  {'present' if full.exists() else 'MISSING':<10}  {rel_path}")

    # Footer
    lines.append("")
    lines.append("-" * 70)
    lines.append("End of diagnostics report")
    lines.append("")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Diagnostics written → {out}")
    print(f"     Attach this file to your bug report.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Mossy ENB diagnostics to a text file for bug reports",
    )
    parser.add_argument(
        "--game-dir",
        type=Path,
        default=REPO_ROOT,
        metavar="PATH",
        help="Path to Fallout 4 installation directory (default: repo root)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "diagnostics.txt",
        metavar="FILE",
        help="Output file path (default: diagnostics.txt in repo root)",
    )
    args = parser.parse_args()
    export(args.game_dir, args.out)


if __name__ == "__main__":
    main()
