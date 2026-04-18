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
| **Topaz Gigapixel AI** | Any GPU | Commercial AI upscaler; best quality-per-iteration for individual texture work. |

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
