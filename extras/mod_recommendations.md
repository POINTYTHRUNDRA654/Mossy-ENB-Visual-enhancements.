# Recommended Mods — Mossy ENB Visual Enhancements

These mods are curated companions to the ENB and ReShade configuration in this
repository.  They feed higher-quality data into ENB's lighting engine and fill
gaps that post-processing alone cannot fix (textures, meshes, weather).

All mods are available on [Nexus Mods](https://www.nexusmods.com/fallout4)
unless otherwise noted.  Install with a mod manager such as **Mod Organizer 2**
or **Vortex**.

---

## Essential (all GPU tiers)

These mods have a negligible performance impact and should be used regardless of
your hardware.

| Mod | What it does |
|---|---|
| **Clarity** | Removes the greenish-yellow atmospheric tint from the vanilla renderer. Essential for accurate colour with any ENB preset. |
| **True Storms — Wasteland Edition** | High-resolution storm cloud meshes, dynamic volumetric lightning, and new interior/exterior weather sounds. Pairs perfectly with ENB volumetric rays. |
| **Enhanced Lights and FX (ELFX)** | Rebuilds every interior light source to be physically plausible — no more flat ambient fill. Works hand-in-hand with ENB's `[PARTICLELIGHTS]` section. |
| **Boston FPS Fix — aka BFix** | Reduces the precombine-mesh CPU bottleneck in central Boston. This is not a visual mod but it keeps the GPU busy doing ENB work rather than waiting for the CPU. |
| **Pip-Boy Flashlight** | Replaces the vanilla wrist-glow with a proper directional torch that casts real ENB particle-light shadows when `EnableParticleLightsShadows=true`. |

---

## Texture Upgrades — Performance tier (GTX 1060 / RX 580)

Focus on 2× AI-upscaled packs that load quickly and stay within a 4 GiB VRAM budget.

| Mod | Resolution / notes |
|---|---|
| **Fallout 4 HD Overhaul 2k** | Community-curated 2K retexture of most surfaces. Large download but dramatic improvement over vanilla 512/1K assets. |
| **Vivid Fallout — All in One** | 2K landscape and rock textures with saturated, painterly detail that reads well at distance. |
| **BaronGhoti's ESRGAN 2x Upscale Pack** | Full vanilla texture set processed through ESRGAN at 2× — subtle but universal improvement. No handcrafted art changes. |
| **Lore-Based Loading Screens** | Light mod; replaces the loading screen slides with high-resolution renders — no VRAM cost in-game. |

---

## Texture Upgrades — Balanced tier (RTX 2070 / RX 6700 XT)

4K textures and richer normal maps that benefit from ENB's HBAO and sub-surface
scattering.

| Mod | Resolution / notes |
|---|---|
| **Fallout 4 HD Overhaul 4k** | Official Bethesda 4K texture DLC — best starting point for a 4K install. Free on Steam/GOG. |
| **Vivid Fallout — All in One (4K)** | 4K variant of the landscape pack. The extra detail interacts well with ENB's horizon-based AO. |
| **BaronGhoti's ESRGAN 4x Pack** | Full vanilla set at 4×. Pairs with the 4K HD Overhaul to cover any missed assets. |
| **NAC X — Natural and Atmospheric Commonwealth** | Rebuilds the sky, weather system, and interior ambience. Adds over 100 weather types including radiation storms and heat haze. |
| **Vivid Weathers — Definitive Edition** | Alternative/complement to NAC X; focuses on sky and cloud realism with ENB-tuned weather data. |

---

## Texture Upgrades — Ultra tier (RTX 3080+ / RX 7900 XT+)

8K textures and mesh replacers. Only meaningful on 10 GiB+ VRAM.

| Mod | Resolution / notes |
|---|---|
| **Fallout 4 HD Overhaul 4k** + **ESRGAN 4x** | Same as balanced tier; the extra VRAM headroom allows loading without compression. |
| **Lush Green Mod** | High-density foliage mesh replacer — adds grass tuft geometry into areas that vanilla leaves nearly bare. ENB sub-surface scattering makes the leaves glow correctly in sunlight. |
| **Commonwealth Cuts — NPC Overhaul** | Rebuilds NPC hair and skin materials with PBR normal maps. SSS values in the balanced/ultra ENB preset make a visible difference. |
| **PhyLight — Physicalized Lighting** | Adds thousands of additional point lights to interiors, diegetic light sources, and fire. Works directly with `EnableParticleLights=true` and `EnableParticleLightsShadows=true`. |

---

## AI & Nvidia Tools (hardware-specific)

| Tool | Requirement | What it adds |
|---|---|---|
| **DLSS Enabler** (PureDark, Nexus Mods) | Nvidia RTX GPU | Retrofits DLSS 2/3 into Fallout 4. AI upscaling at 67 % render resolution with better-than-native sharpness. Frees up ~30 % GPU budget for ENB and ReShade. Recommended: set `EnableVSync=false` and `FpsLimit=60.0` in `enblocal.ini`. |
| **RTX Remix** (Nvidia, open-source) | Nvidia RTX GPU | Full path-traced renderer replacement using Nvidia Omniverse. Community Fallout 4 port is in active development. Replaces ENB entirely when used. |
| **Chainner + ESRGAN models** (PC tool) | Any GPU | Open-source node-based pipeline for batch-processing all vanilla textures through AI upscaling models. Use the `4x_foolhardy_Remacri` or `4x_NMKD-Superscale` models for Bethesda textures. |
| **Topaz Gigapixel AI** | Nvidia GPU (CUDA) / CPU fallback | Commercial AI upscaler; best quality-per-iteration for individual texture work. |

---

## Physics & Animation

Realistic physics and animation make ENB's subsurface scattering and particle
lights land correctly.  Stiff vanilla animations break the illusion that ENB
works hard to create.

| Mod | What it does |
|---|---|
| **Bullet Counted Reload (BCR)** | Magazine-aware reload animations: characters actually retain partial magazines instead of discarding them. Pairs with ENB particle lights on shell casings mid-reload. |
| **BGSM Material Swapper** | Swaps weapon and armour material files to PBR-ready variants, so ENB's specular and metalness calculations look physically correct on every surface. |
| **Atomic Muscle — Male Body Replacer** | PBR-capable male body mesh with correctly authored normal maps. ENB's `[SUBSURFACESCATTERING]` section makes skin look translucent and believable instead of plastic. |
| **CBBE 3BA (3BBB)** | The standard female body framework with full Havok bone-driven physics (breast, belly, butt collisions). ENB SSS works on the same skin normal maps. Requires **BodySlide and Outfit Studio**. |
| **Havok Physics Fix** | Prevents physics objects from vibrating and exploding at high FPS. Essential when `FpsLimit` is raised above 60 in `enblocal.ini`. |
| **Realistic Ragdoll Force** | Calibrates ragdoll forces to real-world ballistic data so body reactions look grounded rather than cartoonish, complementing ENB's lighting realism. |
| **Hit Stop and Stagger** | Adds screen-space feedback (hit-stop, micro-stagger) that interacts believably with ENB's depth-of-field and motion-blur shaders. |
| **NPCs Travel** | Gives settlers and wanderers realistic travel routines — ensures ENB's exterior volumetric rays and weather interactions are always populated with moving characters. |

### Load Order — Physics Mods

Place physics mods **after** body framework masters in your load order:

```
CBBE.esp           (or BodyTalk3.esp for males)
CBBE3BA.esp
AtomicMuscle.esp
HavokFix.esp
RealisticRagdoll.esp
```

---

## AI Texture Upscaling — DIY Pipeline

The `tools/upscale_textures.py` script in this repository lets you run your
**own** Fallout 4 texture folder through a locally-executed ESRGAN neural
network, producing photorealistic upscaled DDS files without uploading
anything to a cloud service.  Everything runs on your GPU using Vulkan.

### Requirements

| Tool | Platform | Download |
|---|---|---|
| **realesrgan-ncnn-vulkan** | Win / Linux / macOS | <https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases> |
| **texconv** (DDS ↔ PNG) | Windows | <https://github.com/microsoft/DirectXTex/releases> |
| **ImageMagick** `magick` (DDS ↔ PNG) | Linux / macOS | <https://imagemagick.org/> |

Both tools must be on your system `PATH`, or passed explicitly via
`--esrgan-bin` / `--dds-converter`.  Run `python tools/verify_install.py`
to confirm they are detected.

### Workflow

```
# 1. Dry run to preview which BC format will be used for each texture
python tools/upscale_textures.py \
    --input-dir  "C:\Fallout4\Data\Textures\Landscape" \
    --output-dir "C:\Fallout4\Data\Textures_upscaled\Landscape" \
    --model 4x_foolhardy_Remacri \
    --scale 4 \
    --dry-run

# 2. Full run
python tools/upscale_textures.py \
    --input-dir  "C:\Fallout4\Data\Textures\Landscape" \
    --output-dir "C:\Fallout4\Data\Textures_upscaled\Landscape" \
    --model 4x_foolhardy_Remacri \
    --scale 4
```

After the run completes, copy the contents of `Textures_upscaled\` over your
existing `Data\Textures\` folder (or install it as a mod via Mod Organizer 2
so the originals are preserved).

### Model Recommendations by Category

For full model download links and VRAM requirements, see
`tools/models/README.md`.

| Texture category | Recommended model | Scale | DDS format |
|---|---|---|---|
| **Landscape / rocks** (`terrain\`, `landscape\`) | `4x_foolhardy_Remacri` | 4× | BC3 (diffuse), BC5 (normals) |
| **Vegetation / foliage** | `4x_foolhardy_Remacri` | 4× | BC3 (diffuse) |
| **Characters / skin** (`actors\`, `characters\`) | `4x_NMKD-Superscale-SP` | 4× | BC3 (diffuse), BC5 (normals) |
| **Weapons / armour** (`weapons\`, `armor\`) | `4x_foolhardy_Remacri` | 4× | BC3 (diffuse), BC1 (specular) |
| **Architecture / interiors** | `4x_foolhardy_Remacri` | 4× | BC3 (diffuse) |
| **Normal maps** (`*_n.dds`) | `4x_NormalNM` | 4× | **BC5** (auto-detected) |

> **Tip:** `upscale_textures.py` detects `_n` / `_normal` / `_nm` suffixes
> and automatically applies `BC5_UNORM` encoding for normal maps — no manual
> format selection needed.

### Performance notes

- A full `Data\Textures\` folder is ~8–30 GB.  Process sub-folders separately
  to manage disk space and resume more easily after interruptions.
- `realesrgan-ncnn-vulkan` tiles large textures automatically, so GPUs with
  less VRAM (4 GiB) can run 4× upscaling — it will just be slower.
- Processing 1 GiB of vanilla textures takes roughly 5–20 minutes depending
  on GPU tier.

---

## Weather Mods — Load Order Note

If you use both **True Storms** and **NAC X** or **Vivid Weathers**, place a
compatibility patch *after* all three in your load order.  Search Nexus Mods
for "True Storms + NAC X patch" or "True Storms + Vivid Weathers patch".

---

## Shader Packs for ReShade

Download and extract these into `reshade-shaders/Shaders/` and
`reshade-shaders/Textures/` inside your Fallout 4 folder.

| Pack | URL | Cost |
|---|---|---|
| **iMMERSE** (MXAO, SMAA, sharpening) | https://github.com/martymcmodding/iMMERSE | Free |
| **iMMERSE Pro** (RTGI — used in balanced/ultra presets) | https://www.patreon.com/mcflypg | Paid (Patreon) |
| **qUINT** (AdaptiveSharpen, DoF, Bloom) | https://github.com/martymcmodding/qUINT | Free |
