#!/usr/bin/env python3
"""
tools/generate_lut.py – Mossy ENB Visual Enhancements
======================================================
Generates a 512×512 Hald CLUT PNG that can be used as the LUT texture for
iMMERSE's LUT.fx shader in Fallout 4 ReShade setups.

The default output is a **neutral identity LUT** (every colour passes through
unchanged).  Replace or modify it with a grading tool such as:
  * DaVinci Resolve (free)        — export a 64-level Hald CLUT
  * Affinity Photo / Photoshop    — apply grades, then export via LUT panel
  * Lutify.me or Unreal Color Grader — free online tools

Film look emulation (Kodak Vision3 500T)
-----------------------------------------
An additional "film" LUT is generated when you pass ``--film`` on the command
line.  It applies a mild lift (shadow toe), slight warm colour push (tungsten
film emulation), and a gentle shoulder roll-off to the highlights.

Usage
-----
    python tools/generate_lut.py                        # identity (neutral)
    python tools/generate_lut.py --film                 # Kodak Vision3-style
    python tools/generate_lut.py --out /path/to/out.png # custom output path

Output
------
Written to ``reshade/reshade-textures/MossyLUT.png`` by default.
Copy the file into ``<Fallout4>/reshade-shaders/Textures/`` before launching.

Format
------
512×512 RGBA PNG, 8-bit per channel.
Hald CLUT level 8:  8³ = 512 colours per axis, stored as 8×8 tiles of 64×64.

  Tile column (tx, 0-7) and row (ty, 0-7) together encode the blue channel:
      B slice = ty * 8 + tx   (0-63)
  Within each tile:
      local_x (0-63) → R channel
      local_y (0-63) → G channel

Requirements
------------
Python 3.8+ — stdlib only (struct, zlib).
"""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "reshade" / "reshade-textures" / "MossyLUT.png"

# LUT dimensions
LUT_SIZE = 64       # colours per axis (64³ = 262 144 unique input colours)
TILES_PER_ROW = 8   # sqrt(LUT_SIZE) — must satisfy TILES_PER_ROW² = LUT_SIZE
TILE_SIZE = LUT_SIZE
IMG_SIZE = TILES_PER_ROW * TILE_SIZE  # 8 * 64 = 512


# ---------------------------------------------------------------------------
# PNG writer (stdlib only — no Pillow required)
# ---------------------------------------------------------------------------

def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    """Pack a single PNG chunk."""
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def _write_png(pixels: list[list[tuple[int, int, int, int]]], path: Path) -> None:
    """
    Write a 512×512 RGBA PNG from *pixels* (list of rows, each a list of RGBA
    tuples) to *path*.  Uses only Python's stdlib (struct + zlib).
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    height = len(pixels)
    width = len(pixels[0])

    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)

    # IDAT — compress each scanline with a leading filter byte (0 = None)
    raw_rows = bytearray()
    for row in pixels:
        raw_rows.append(0)  # filter byte
        for r, g, b, a in row:
            raw_rows += bytes([r, g, b, a])

    compressed = zlib.compress(bytes(raw_rows), level=9)

    with path.open("wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")  # PNG signature
        fh.write(_png_chunk(b"IHDR", ihdr_data))
        fh.write(_png_chunk(b"IDAT", compressed))
        fh.write(_png_chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# Colour-grading helpers for the film look
# ---------------------------------------------------------------------------

def _gamma(v: float, g: float) -> float:
    """Apply a simple power-law gamma curve (v in 0-1)."""
    return max(0.0, min(1.0, v ** (1.0 / g)))


def _lift_gamma_gain(
    r: float, g: float, b: float,
    lift: float = 0.0,
    gamma: float = 1.0,
    gain: float = 1.0,
) -> tuple[float, float, float]:
    """Simple lift / gamma / gain colour grade (all values in 0-1)."""
    r = (r + lift) * gain
    g = (g + lift) * gain
    b = (b + lift) * gain
    r = _gamma(r, gamma)
    g = _gamma(g, gamma)
    b = _gamma(b, gamma)
    return r, g, b


def _shoulder(v: float, strength: float = 0.25) -> float:
    """Soft shoulder roll-off to prevent harsh highlight clipping."""
    if v < 1.0 - strength:
        return v
    x = (v - (1.0 - strength)) / strength  # 0-1 in shoulder region
    # Smooth step
    x = x * x * (3 - 2 * x)
    return (1.0 - strength) + strength * x


def _film_grade(r: float, g: float, b: float) -> tuple[float, float, float]:
    """
    Kodak Vision3 500T tungsten-film emulation.

    Characteristics:
    * Slight shadow lift  (analogue film never reaches pure black)
    * Warm midtone push   (tungsten-balanced film under mixed lighting)
    * Gentle highlight shoulder
    * Slight green/blue desaturation in shadows (shadow toning)
    """
    # Lift shadows slightly
    lift = 0.015
    r = (r + lift) * (1.0 - lift)
    g = (g + lift) * (1.0 - lift)
    b = (b + lift) * (1.0 - lift)

    # Warm colour push: boost red/green, restrain blue in midtones
    # Using a gentle S-curve via gamma adjustments per channel
    r = _gamma(r, 0.96)   # slight red boost
    g = _gamma(g, 0.99)   # neutral green
    b = _gamma(b, 1.04)   # slight blue reduction

    # Shoulder roll-off
    r = _shoulder(r, 0.20)
    g = _shoulder(g, 0.22)
    b = _shoulder(b, 0.18)

    # Clamp
    return (
        max(0.0, min(1.0, r)),
        max(0.0, min(1.0, g)),
        max(0.0, min(1.0, b)),
    )


# ---------------------------------------------------------------------------
# LUT pixel generators
# ---------------------------------------------------------------------------

def _identity_pixel(tx: int, ty: int, lx: int, ly: int) -> tuple[int, int, int, int]:
    """Return the RGBA value for an identity (neutral) LUT pixel."""
    blue_slice = ty * TILES_PER_ROW + tx       # 0-63
    r = round(lx * 255 / (LUT_SIZE - 1))
    g = round(ly * 255 / (LUT_SIZE - 1))
    b = round(blue_slice * 255 / (LUT_SIZE - 1))
    return r, g, b, 255


def _film_pixel(tx: int, ty: int, lx: int, ly: int) -> tuple[int, int, int, int]:
    """Return the RGBA value for a Kodak Vision3-style film LUT pixel."""
    blue_slice = ty * TILES_PER_ROW + tx
    r_in = lx / (LUT_SIZE - 1)
    g_in = ly / (LUT_SIZE - 1)
    b_in = blue_slice / (LUT_SIZE - 1)
    r_out, g_out, b_out = _film_grade(r_in, g_in, b_in)
    return (
        round(r_out * 255),
        round(g_out * 255),
        round(b_out * 255),
        255,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(out: Path, film: bool = False) -> None:
    """Generate the LUT PNG and write it to *out*."""
    pixel_fn = _film_pixel if film else _identity_pixel

    pixels: list[list[tuple[int, int, int, int]]] = []
    for py in range(IMG_SIZE):
        ty = py // TILE_SIZE        # tile row   (0-7)
        ly = py % TILE_SIZE         # local y within tile (0-63)
        row: list[tuple[int, int, int, int]] = []
        for px in range(IMG_SIZE):
            tx = px // TILE_SIZE    # tile column (0-7)
            lx = px % TILE_SIZE     # local x within tile (0-63)
            row.append(pixel_fn(tx, ty, lx, ly))
        pixels.append(row)

    _write_png(pixels, out)
    label = "film (Kodak Vision3 500T)" if film else "identity (neutral)"
    print(f"[OK] LUT written ({label}) → {out}")
    print("     Copy to <Fallout4>/reshade-shaders/Textures/MossyLUT.png")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate MossyLUT.png for the Mossy ENB ReShade screenshot preset",
    )
    parser.add_argument(
        "--film",
        action="store_true",
        help="Generate the Kodak Vision3 500T film-look LUT instead of identity",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output PNG path (default: {DEFAULT_OUT})",
    )
    args = parser.parse_args()
    generate(args.out, film=args.film)


if __name__ == "__main__":
    main()
