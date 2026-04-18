# Mossy ENB Visual Enhancements

A configuration toolkit that makes **Fallout 4** look as close to a modern
photorealistic game as possible while keeping a solid, playable frame rate.

It ships three quality-tier ENB presets and a Python command-line tool
(`enb_optimizer.py`) that lets you switch presets, auto-detect the best
settings for your GPU, and tune individual values — all without editing INI
files by hand.

---

## Table of Contents

- [What is ENB?](#what-is-enb)
- [Why does this exist?](#why-does-this-exist)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Preset overview](#preset-overview)
- [Using the optimizer tool](#using-the-optimizer-tool)
- [Manual INI editing](#manual-ini-editing)
- [Settings reference](#settings-reference)
- [Performance tips](#performance-tips)
- [Running the tests](#running-the-tests)
- [File structure](#file-structure)
- [License](#license)

---

## What is ENB?

[ENBSeries](http://enbdev.com) is a post-processing injector for many Bethesda
games.  For Fallout 4 it adds effects the vanilla engine is missing or
implements poorly: high-quality ambient occlusion, sub-surface scattering,
accurate tone mapping, volumetric light rays, detailed contact shadows, screen-
space reflections, and much more.  The result can make the game look
significantly more realistic — much closer to modern titles — without replacing
a single texture or mesh.

---

## Why does this exist?

ENB is powerful but intimidating.  The in-game GUI exposes hundreds of sliders,
and the reference documentation is minimal.  Getting Fallout 4 to look
photorealistic *and* run at a stable 60 FPS requires careful tuning that can
take hours of experimentation.

This project packages that work as three ready-to-use presets and a small
Python tool so that anyone can get great results in minutes.

---

## Features

| Feature | Details |
|---|---|
| **Three quality presets** | `performance`, `balanced`, `ultra` — tuned for real hardware |
| **Auto-detect preset** | The tool reads your GPU's VRAM and picks the best preset automatically |
| **Backup before every change** | The old `enbseries.ini` is always backed up to `backups/` before being overwritten |
| **Single-setting tuning** | Change one value without touching anything else |
| **Fully commented INIs** | Every setting has an inline comment explaining what it does and why |
| **No third-party dependencies** | Pure Python 3 standard library |

---

## Requirements

| Item | Notes |
|---|---|
| **Fallout 4** | Any edition (base game or GOTY) |
| **ENBSeries binary** | Download the Fallout 4 version from [enbdev.com](http://enbdev.com). You need `d3d11.dll` and `d3dcompiler_46e.dll`. |
| **Python 3.8+** | Only needed for the optimizer tool — not needed to use the INI presets manually |
| **GPU** | GTX 1060 / RX 580 or better recommended |

---

## Installation

### Step 1 – ENBSeries binary

1. Go to <http://enbdev.com/download_mod_fallout4.htm> and download the latest
   binary archive.
2. Open the archive and copy **`d3d11.dll`** and **`d3dcompiler_46e.dll`** to
   your Fallout 4 root folder (the folder containing `Fallout4.exe`).

### Step 2 – Mossy ENB configuration files

Copy the following files to the same Fallout 4 root folder:

```
enbseries.ini    ← main ENB settings (the "balanced" preset by default)
enblocal.ini     ← local hardware settings
```

### Step 3 – (Optional) Use the optimizer tool

```bash
python enb_optimizer.py apply --preset balanced
```

See [Using the optimizer tool](#using-the-optimizer-tool) for more options.

### Step 4 – Launch the game

Start Fallout 4 normally.  Press **Shift + Enter** to open the ENB in-game
GUI where you can see all active settings and make live adjustments.

---

## Preset overview

| Preset | VRAM target | GPU examples | Notable trade-offs |
|---|---|---|---|
| `performance` | < 4 GiB | GTX 1060, RX 580 | SSAO quality reduced; no detailed shadows, volumetric rays, or SSS |
| `balanced` | 4–8 GiB | RTX 2070, RX 6700 XT | Everything on at medium-high quality; HBAO, SSS, volumetric rays |
| `ultra` | 8 GiB+ | RTX 3080, RX 7900 XT | Everything at maximum; HBAO+, particle-light shadows, maximum SSAO samples |

The root `enbseries.ini` is identical to the `balanced` preset and is the
file that ENB actually reads.

---

## Using the optimizer tool

```
python enb_optimizer.py <command> [options]
```

### `list` — show available presets

```bash
python enb_optimizer.py list
```

```
Available presets:

  performance     ✓
  balanced        ✓
  ultra           ✓
```

### `show` — inspect a preset's settings

```bash
python enb_optimizer.py show --preset ultra
```

### `apply` — activate a preset

```bash
# Apply by name
python enb_optimizer.py apply --preset balanced

# Auto-detect from GPU VRAM
python enb_optimizer.py apply --auto
```

The existing `enbseries.ini` is always backed up to `backups/` first.  Press
**Shift + Enter** in-game to reload the settings without restarting.

### `tune` — change a single setting

```bash
# Format: SECTION/Key
python enb_optimizer.py tune --setting SSAO_SSIL/EnableAmbientOcclusion --value false
python enb_optimizer.py tune --setting BLOOM/BloomAmount --value 0.08
python enb_optimizer.py tune --setting TONEMAPPING/ToneMappingCurve --value 2
```

---

## Manual INI editing

Both `enbseries.ini` and `enblocal.ini` contain detailed inline comments.
Open either file in any text editor.  Every section and key has a description
of what it does and the recommended range of values.

The `presets/` directory contains the three clean preset files if you want to
copy-paste sections manually.

---

## Settings reference

### The biggest visual-quality wins (in order of impact)

1. **SSAO / HBAO** (`[SSAO_SSIL]`) — contact shadows and surface depth
2. **Sub-surface scattering** (`[SUBSURFACESCATTERING]`) — skin and foliage
3. **Tone mapping** (`[TONEMAPPING]`, `ToneMappingCurve=3`) — ACES film curve
4. **Volumetric rays** (`[VOLUMETRICROYS]`) — god rays
5. **Detailed shadows** (`[DETAILSHADOW]`) — high-res contact shadows
6. **Eye adaptation** (`[TONEMAPPING]`) — dynamic exposure like a camera iris

### The biggest performance costs

| Effect | Relative cost |
|---|---|
| SSAO (high samples) | ★★★★ |
| Volumetric rays (quality 2) | ★★★ |
| Subsurface scattering | ★★ |
| Detailed shadows | ★★ |
| Particle light shadows | ★★ |
| Bloom | ★ |

---

## Performance tips

* **Cap your frame rate** — set `EnableFpsLimit=true` and `FpsLimit=60.0` in
  `enblocal.ini`.  Uncapped frame rates cause micro-stutter with ENB's
  synchronisation.
* **Disable in-game Depth of Field** — use ENB's DoF instead
  (`QualityDOF=2`).  The vanilla DoF is very expensive and low quality.
* **Use TAA in-game** — ENB's sharpening pass (`SharpeningStrength=0.35`)
  recovers the fine detail that TAA blurs, so you get the stability of TAA
  without the soft look.
* **Lower `SamplingStep`** — changing from 8 → 4 in `[SSAO_SSIL]` gives a
  large FPS boost with only a subtle quality reduction.
* **Disable `EnableParticleLightsShadows`** — particle shadows are expensive
  and rarely noticeable in normal gameplay.

---

## Running the tests

```bash
pip install pytest
python -m pytest tests/ -v
```

All 21 tests should pass with no external dependencies.

---

## File structure

```
Mossy-ENB-Visual-enhancements/
├── enbseries.ini              ← Active ENB config (balanced preset)
├── enblocal.ini               ← Local hardware / system settings
├── enb_optimizer.py           ← Preset manager CLI tool
├── presets/
│   ├── enbseries_performance.ini
│   ├── enbseries_balanced.ini
│   └── enbseries_ultra.ini
├── tests/
│   └── test_enb_optimizer.py
├── backups/                   ← Auto-created; timestamped .ini.bak files
├── LICENSE
└── README.md
```

---

## License

See [LICENSE](LICENSE).