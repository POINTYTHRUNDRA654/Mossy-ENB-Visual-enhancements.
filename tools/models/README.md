# ESRGAN Model Files — Mossy ENB Visual Enhancements

This directory is the default search path used by `tools/upscale_textures.py`
when it calls the `realesrgan-ncnn-vulkan` binary.  Place your downloaded
`.param` and `.bin` model files here and they will be picked up automatically.

---

## Quick-start

1. Download **realesrgan-ncnn-vulkan** for your OS:
   <https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases>
2. Extract the archive.  The `models/` sub-folder inside the release contains
   `realesr-animevideov3.param` etc.  Copy (or symlink) whichever models you
   want to use into **this** directory.
3. Download additional community models (see below) and place them here too.
4. Run the upscaler:
   ```
   python tools/upscale_textures.py \
       --input-dir  "C:\Fallout4\Data\Textures" \
       --output-dir "C:\Fallout4\Data\Textures_upscaled" \
       --model      4x_foolhardy_Remacri \
       --scale      4
   ```

---

## Recommended Models by Texture Category

The model choice has a large impact on output quality.  These recommendations
are tuned for Bethesda Creation Engine texture conventions.

### Landscape & Environment (`terrain\`, `landscape\`, `water\`)

| Model | Download | Notes |
|---|---|---|
| **4x_foolhardy_Remacri** | [OpenModelDB](https://openmodeldb.info/models/4x-foolhardy-Remacri) | Best all-round choice for rocky surfaces, dirt, and asphalt. Preserves micro-detail grain without introducing ringing. |
| **4x_NMKD-Superscale-SP_178000_G** | [OpenModelDB](https://openmodeldb.info/models/4x-NMKD-Superscale-SP) | Stronger sharpening than Remacri; good for concrete and brick where hard edges are desirable. |

### Characters & Skin (`actors\`, `characters\`)

| Model | Download | Notes |
|---|---|---|
| **4x_NMKD-Superscale-SP_178000_G** | [OpenModelDB](https://openmodeldb.info/models/4x-NMKD-Superscale-SP) | Produces clean pore-level skin detail that ENB's sub-surface scattering can resolve. |
| **4x_foolhardy_Remacri** | [OpenModelDB](https://openmodeldb.info/models/4x-foolhardy-Remacri) | Softer alternative; better for hair and eye textures where Superscale oversharpens. |

### Weapons & Armour (`weapons\`, `armor\`, `dlc\`)

| Model | Download | Notes |
|---|---|---|
| **4x_foolhardy_Remacri** | [OpenModelDB](https://openmodeldb.info/models/4x-foolhardy-Remacri) | Retains scratches and wear patterns correctly. ENB's metalness reflections pick up the extra specular detail. |
| **4x_NMKD-Superscale-SP_178000_G** | [OpenModelDB](https://openmodeldb.info/models/4x-NMKD-Superscale-SP) | Good for clean, painted surfaces (Power Armor, Institute tech). |

### Normal Maps (`*_n.dds`)

Normal maps require special handling — do **not** run them through a standard
photo-upscale model as it will corrupt the R+G vector data.

| Model | Download | Notes |
|---|---|---|
| **4x_NormalNM** | [OpenModelDB](https://openmodeldb.info/models/4x-NormalNM) | Purpose-built for tangent-space normal maps. Upscales the X/Y vectors without introducing colour shifts. |

`upscale_textures.py` automatically selects `BC5_UNORM` re-encoding for files
whose stem ends in `_n` / `_normal` / `_nm`, which is the correct DDS format
for two-channel normal maps.

### Interior & Architecture (`architecture\`, `interiors\`, `furniture\`)

| Model | Download | Notes |
|---|---|---|
| **4x_foolhardy_Remacri** | [OpenModelDB](https://openmodeldb.info/models/4x-foolhardy-Remacri) | Safe default. Handles the wide variety of surface types found in interior assets. |

---

## DDS Compression Reference

`upscale_textures.py` selects the format automatically based on the filename
stem suffix:

| Suffix | Format | Reason |
|---|---|---|
| `_n`, `_normal`, `_nm` | **BC5_UNORM** | Two-channel (R+G) tangent-space normals |
| `_s`, `_spec` | **BC1_UNORM** | Specular mask — no alpha channel needed |
| `_g`, `_glow`, `_em` | **BC1_UNORM** | Glow / emissive — single RGB channel |
| *(anything else)* | **BC3_UNORM** | Diffuse / albedo with alpha channel |

Use `--dry-run` to confirm the assigned format for each file before committing
to a full batch run:

```
python tools/upscale_textures.py \
    --input-dir "C:\Fallout4\Data\Textures\Landscape" \
    --output-dir /tmp/out \
    --dry-run
```

---

## VRAM Budget Guide

| Scale | Typical output res | Minimum VRAM |
|---|---|---|
| 2× | 2K (vanilla 1K → 2K) | 4 GiB |
| 4× | 4K (vanilla 1K → 4K) | 8 GiB |

The `upscale_textures.py` script uses the `realesrgan-ncnn-vulkan` binary which
runs inference in Vulkan tiles, so larger-than-VRAM batches are handled
automatically (at a performance cost).

---

## File Naming Convention

Place model pairs in this directory with matching base names:

```
tools/models/
    4x_foolhardy_Remacri.param
    4x_foolhardy_Remacri.bin
    4x_NMKD-Superscale-SP_178000_G.param
    4x_NMKD-Superscale-SP_178000_G.bin
    4x_NormalNM.param
    4x_NormalNM.bin
```

The `--model` argument to `upscale_textures.py` is the base name without
extension (e.g. `--model 4x_foolhardy_Remacri`).

---

## Alternative: ChaiNNer GUI

If you prefer a graphical workflow, **ChaiNNer** provides a node-based editor
that wraps the same ESRGAN models with a drag-and-drop interface and supports
batch processing entire texture folders.

- Download: <https://github.com/chaiNNer-org/chaiNNer/releases>
- Use the same model files listed above.
- Recommended chain: `Load Image → Upscale Image → Save Image (DDS BC3)`
  with a separate chain for normal maps using `BC5 (RG)` output format.
