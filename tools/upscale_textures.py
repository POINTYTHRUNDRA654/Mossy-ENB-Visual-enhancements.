#!/usr/bin/env python3
"""
tools/upscale_textures.py – Mossy ENB Visual Enhancements
==========================================================
Batch-upscales Fallout 4 DDS textures using a Real-ESRGAN-ncnn-vulkan binary,
then re-encodes the results into the correct BC-format DDS files for the game.

Workflow
--------
  1. Scan *input_dir* for ``.dds`` files (recursive by default).
  2. Convert each DDS → PNG using ``texconv`` (Windows) or ImageMagick
     ``magick``/``convert`` (Linux / macOS).
  3. Pass the PNGs through a Real-ESRGAN-ncnn-vulkan binary with the chosen
     model, writing upscaled PNGs into a temporary directory.
  4. Re-encode the upscaled PNGs back to DDS, choosing BC1/BC3/BC5 compression
     by examining the filename suffix:

       * ``_n`` / ``_normal`` / ``_nm``    → BC5   (two-channel normal map)
       * ``_s`` / ``_spec``                → BC1   (specular, no alpha)
       * ``_g`` / ``_glow`` / ``_em``      → BC1   (glow / environment mask)
       * everything else                  → BC3   (diffuse with alpha)

  5. Write the final DDS files to *output_dir*, mirroring the source layout.

Usage
-----
    python tools/upscale_textures.py \\
        --input-dir  "C:\\Fallout4\\Data\\Textures" \\
        --output-dir "C:\\Fallout4\\Data\\Textures_upscaled" \\
        --model      4x_foolhardy_Remacri \\
        --scale      4

    # Dry run (no files written)
    python tools/upscale_textures.py --input-dir /tmp/test --output-dir /tmp/out --dry-run

Requirements
------------
* Python 3.8+ — stdlib only.
* **texconv** (Windows) OR **ImageMagick** ``magick``/``convert`` (Linux/macOS)
  for DDS ↔ PNG conversion.
  - texconv:     https://github.com/microsoft/DirectXTex/releases
  - ImageMagick: https://imagemagick.org/
* **realesrgan-ncnn-vulkan** for AI upscaling.
  - https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases
  - Extract the executable and model files somewhere accessible.
  - Pass ``--esrgan-bin /path/to/realesrgan-ncnn-vulkan`` if not on PATH.
* Model files (see tools/models/README.md for recommended models and
  download links).

Exit codes
----------
0  — all textures processed successfully
1  — one or more textures failed (partial success)
2  — fatal error (missing tools or bad arguments)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# DDS format classification
# ---------------------------------------------------------------------------

# Lower-case stem suffixes that identify each texture type.
_NORMAL_SUFFIXES: frozenset[str] = frozenset({"_n", "_normal", "_nm"})
_SPECULAR_SUFFIXES: frozenset[str] = frozenset({"_s", "_spec", "_specular"})
_GLOW_SUFFIXES: frozenset[str] = frozenset({"_g", "_glow", "_em", "_emissive"})

# texconv / ImageMagick format identifiers
_FORMAT_BC3 = "BC3_UNORM"   # diffuse with alpha channel
_FORMAT_BC1 = "BC1_UNORM"   # specular / glow (no alpha needed)
_FORMAT_BC5 = "BC5_UNORM"   # normal maps (two-channel R+G)


def _dds_format(filename: str) -> str:
    """Return the BC DDS format string appropriate for *filename*.

    Infers the texture type from the filename stem suffix so that diffuse,
    normal, specular, and glow maps are each compressed correctly.
    """
    stem = Path(filename).stem.lower()
    for suffix in _NORMAL_SUFFIXES:
        if stem.endswith(suffix):
            return _FORMAT_BC5
    for suffix in _SPECULAR_SUFFIXES:
        if stem.endswith(suffix):
            return _FORMAT_BC1
    for suffix in _GLOW_SUFFIXES:
        if stem.endswith(suffix):
            return _FORMAT_BC1
    return _FORMAT_BC3


# ---------------------------------------------------------------------------
# External tool detection
# ---------------------------------------------------------------------------

#: Ordered list of DDS converter candidates to check on PATH.
_DDS_CONVERTER_CANDIDATES: tuple[str, ...] = (
    "texconv",
    "texconv.exe",
    "magick",
    "convert",
)

#: Ordered list of ESRGAN binary candidates to check on PATH.
_ESRGAN_BINARY_CANDIDATES: tuple[str, ...] = (
    "realesrgan-ncnn-vulkan",
    "realesrgan-ncnn-vulkan.exe",
)


def _find_tool(*candidates: str) -> str | None:
    """Return the first *candidate* that exists on PATH, or ``None``."""
    for name in candidates:
        if shutil.which(name):
            return name
    return None


def _find_dds_converter() -> str | None:
    """Return a usable DDS conversion tool name from PATH, or ``None``."""
    return _find_tool(*_DDS_CONVERTER_CANDIDATES)


def _find_esrgan_binary(hint: str | None = None) -> str | None:
    """Return the path or name of the Real-ESRGAN binary to use.

    *hint* is an explicit path or name supplied by the user via
    ``--esrgan-bin``.  Falls back to well-known executable names on PATH
    when *hint* is ``None``.
    """
    if hint is not None:
        p = Path(hint)
        if p.is_file():
            return str(p)
        resolved = shutil.which(hint)
        if resolved:
            return resolved
        return None
    return _find_tool(*_ESRGAN_BINARY_CANDIDATES)


# ---------------------------------------------------------------------------
# DDS ↔ PNG conversion helpers
# ---------------------------------------------------------------------------


def _dds_to_png(dds_path: Path, out_dir: Path, converter: str) -> Path | None:
    """Convert *dds_path* to a PNG in *out_dir*.

    Returns the PNG ``Path`` on success, ``None`` on failure.
    """
    out_png = out_dir / (dds_path.stem + ".png")

    if converter in ("texconv", "texconv.exe"):
        cmd = [
            converter,
            str(dds_path),
            "-ft", "png",
            "-o", str(out_dir),
            "-y",  # overwrite without prompting
        ]
    elif converter == "magick":
        cmd = ["magick", "convert", str(dds_path), str(out_png)]
    else:
        # plain 'convert' (older ImageMagick on Linux)
        cmd = ["convert", str(dds_path), str(out_png)]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        return None
    return out_png if out_png.exists() else None


def _png_to_dds(
    png_path: Path, out_dir: Path, dds_fmt: str, converter: str
) -> Path | None:
    """Convert *png_path* to a DDS file in *out_dir* with *dds_fmt* compression.

    Returns the DDS ``Path`` on success, ``None`` on failure.
    """
    out_dds = out_dir / (png_path.stem + ".dds")

    if converter in ("texconv", "texconv.exe"):
        cmd = [
            converter,
            str(png_path),
            "-f", dds_fmt,
            "-o", str(out_dir),
            "-y",
        ]
    elif converter == "magick":
        cmd = ["magick", "convert", str(png_path), str(out_dds)]
    else:
        cmd = ["convert", str(png_path), str(out_dds)]

    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        return None
    return out_dds if out_dds.exists() else None


# ---------------------------------------------------------------------------
# ESRGAN upscaling
# ---------------------------------------------------------------------------


def _run_esrgan(
    esrgan_bin: str,
    input_dir: Path,
    output_dir: Path,
    model_name: str,
    scale: int,
    models_dir: Path | None = None,
) -> bool:
    """Run the ESRGAN binary on all PNGs in *input_dir*, writing to *output_dir*.

    Passes ``-m models_dir`` when *models_dir* is a valid directory so that
    the binary can locate ``.param``/``.bin`` model files that are not in its
    own working directory.

    Returns ``True`` if the process exits with code 0.
    """
    cmd = [
        esrgan_bin,
        "-i", str(input_dir),
        "-o", str(output_dir),
        "-n", model_name,
        "-s", str(scale),
    ]
    if models_dir and models_dir.is_dir():
        cmd += ["-m", str(models_dir)]

    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def upscale(
    input_dir: Path,
    output_dir: Path,
    *,
    model: str = "4x_foolhardy_Remacri",
    scale: int = 4,
    esrgan_bin: str | None = None,
    dds_converter: str | None = None,
    models_dir: Path | None = None,
    recursive: bool = True,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Run the full DDS upscale pipeline.

    Parameters
    ----------
    input_dir:
        Root folder containing ``.dds`` files to process.
    output_dir:
        Destination folder; the source sub-directory layout is mirrored here.
    model:
        ESRGAN model name (without extension) passed to the binary via ``-n``.
    scale:
        Upscale factor — 2 or 4.
    esrgan_bin:
        Explicit path or name of the ESRGAN binary.  Auto-detected when
        ``None``.
    dds_converter:
        Explicit DDS converter name.  Auto-detected when ``None``.
    models_dir:
        Directory containing ``.param``/``.bin`` model files.  Passed to the
        ESRGAN binary via ``-m``.
    recursive:
        When ``True`` (default) glob ``**/*.dds``; otherwise only the top
        level of *input_dir*.
    dry_run:
        Print what would be done without executing any conversions.

    Returns
    -------
    tuple[int, int]
        ``(success_count, fail_count)``
    """
    converter = dds_converter or _find_dds_converter()
    if converter is None or not shutil.which(converter):
        print(
            "[ERROR] No DDS converter found.\n"
            "        Install texconv (Windows) or ImageMagick (Linux/macOS).\n"
            "        See tools/models/README.md for download links.",
            file=sys.stderr,
        )
        sys.exit(2)

    esrgan = _find_esrgan_binary(esrgan_bin)
    if esrgan is None:
        print(
            "[ERROR] No Real-ESRGAN binary found.\n"
            "        Download realesrgan-ncnn-vulkan from:\n"
            "          https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases\n"
            "        Then pass --esrgan-bin /path/to/realesrgan-ncnn-vulkan.",
            file=sys.stderr,
        )
        sys.exit(2)

    pattern = "**/*.dds" if recursive else "*.dds"
    dds_files = sorted(input_dir.glob(pattern))

    if not dds_files:
        print(f"[WARN] No .dds files found in {input_dir}")
        return 0, 0

    print(f"[INFO] Found {len(dds_files)} DDS file(s) in {input_dir}")
    print(f"[INFO] Model: {model}  |  Scale: {scale}x  |  Converter: {converter}")

    if dry_run:
        print("[DRY RUN] No files will be written.\n")
        col = max(len(str(f.relative_to(input_dir))) for f in dds_files) + 2
        for f in dds_files:
            rel = f.relative_to(input_dir)
            fmt = _dds_format(f.name)
            print(f"  {str(rel):<{col}}  →  {fmt}")
        return len(dds_files), 0

    success = 0
    fail = 0

    with tempfile.TemporaryDirectory(prefix="mossy_esrgan_") as tmp_str:
        tmp = Path(tmp_str)
        png_dir = tmp / "pngs"
        upscaled_dir = tmp / "upscaled"
        png_dir.mkdir()
        upscaled_dir.mkdir()

        # Step 1: DDS → PNG ------------------------------------------------
        print("\n[1/3] Converting DDS → PNG …")
        png_to_src_map: dict[Path, Path] = {}  # png_path → original dds_path
        for dds in dds_files:
            png = _dds_to_png(dds, png_dir, converter)
            if png:
                png_to_src_map[png] = dds
            else:
                print(f"  [FAIL] DDS→PNG: {dds.name}")
                fail += 1

        if not png_to_src_map:
            print(
                "[ERROR] All DDS→PNG conversions failed.  Aborting.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Step 2: ESRGAN upscale -------------------------------------------
        print(f"\n[2/3] Running ESRGAN ({model}) on {len(png_to_src_map)} PNG(s) …")
        ok = _run_esrgan(esrgan, png_dir, upscaled_dir, model, scale, models_dir)
        if not ok:
            print(
                "[ERROR] ESRGAN process failed.  "
                "Check your binary and model files.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Step 3: PNG → DDS ------------------------------------------------
        print("\n[3/3] Re-encoding upscaled PNG → DDS …")
        for png, src_dds in png_to_src_map.items():
            upscaled_png = upscaled_dir / png.name
            if not upscaled_png.exists():
                print(f"  [FAIL] ESRGAN did not produce output for: {png.name}")
                fail += 1
                continue

            rel = src_dds.relative_to(input_dir)
            out_dds_path = output_dir / rel
            out_dds_path.parent.mkdir(parents=True, exist_ok=True)

            fmt = _dds_format(src_dds.name)
            result = _png_to_dds(upscaled_png, out_dds_path.parent, fmt, converter)
            if result:
                success += 1
                print(f"  [OK]   {rel}  ({fmt})")
            else:
                fail += 1
                print(f"  [FAIL] PNG→DDS: {upscaled_png.name}")

    print(f"\n[DONE] {success} succeeded, {fail} failed.")
    print(f"       Output: {output_dir}")
    return success, fail


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

#: Default models directory shipped with this repo.
MODELS_DIR = Path(__file__).resolve().parent / "models"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Batch-upscale Fallout 4 DDS textures via Real-ESRGAN, "
            "re-encoding to BC1/BC3/BC5 DDS."
        ),
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        metavar="PATH",
        help='Folder containing DDS textures to upscale (e.g. "Data\\Textures").',
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        metavar="PATH",
        help="Destination folder for upscaled DDS files.",
    )
    parser.add_argument(
        "--model",
        default="4x_foolhardy_Remacri",
        metavar="NAME",
        help=(
            "ESRGAN model name (default: 4x_foolhardy_Remacri). "
            "See tools/models/README.md for alternatives."
        ),
    )
    parser.add_argument(
        "--scale",
        type=int,
        choices=[2, 4],
        default=4,
        metavar="{2,4}",
        help="Upscale factor: 2× or 4× (default: 4).",
    )
    parser.add_argument(
        "--esrgan-bin",
        default=None,
        metavar="PATH",
        help=(
            "Path or name of the realesrgan-ncnn-vulkan executable. "
            "Auto-detected from PATH when omitted."
        ),
    )
    parser.add_argument(
        "--dds-converter",
        default=None,
        metavar="NAME",
        choices=list(_DDS_CONVERTER_CANDIDATES),
        help=(
            "DDS converter to use: texconv, texconv.exe, magick, or convert. "
            "Auto-detected when omitted."
        ),
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=MODELS_DIR,
        metavar="PATH",
        help=(
            f"Directory containing ESRGAN .param/.bin model files "
            f"(default: {MODELS_DIR})."
        ),
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help=(
            "Only process DDS files in the top level of --input-dir "
            "(skip subdirectories)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without executing any conversions.",
    )
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        print(
            f"[ERROR] --input-dir does not exist: {args.input_dir}",
            file=sys.stderr,
        )
        sys.exit(2)

    success, fail = upscale(
        args.input_dir,
        args.output_dir,
        model=args.model,
        scale=args.scale,
        esrgan_bin=args.esrgan_bin,
        dds_converter=args.dds_converter,
        models_dir=args.models_dir,
        recursive=not args.no_recursive,
        dry_run=args.dry_run,
    )
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
