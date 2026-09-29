# Shading style guide

This guide defines how characters, beasts, and props look in the creator, and how Blender assets must be built so they shade correctly. It covers four picture styles: **Stories** (the default, after Monster Hunter Stories 3), **Breath** (after Breath of Fire 3 and 4), **Legends** (after Mega Man Legends 2 and 3), and **Comic** (a hatched ink look). Style similarity is the goal. Never copy characters, monsters, costumes, emblems, or textures from those games.

Screenshots are cited by number, for example MHS3-09. They are in [reference/mhs3/](reference/mhs3/README.md).

Where this guide and `docs/CLAUDE_BUILD_PROMPT.md` disagree about shading, lines, highlights, or materials, this guide wins. In particular, Stories uses a hard two-tone boundary (not soft bands), and hair gets short highlight slashes (not a continuous band).

---

## Claude working prompt

Copy this block into any Claude session that works on shaders, materials, post effects, or Blender assets for this project.

> Before writing any shader, material, or Blender guidance, read the entire EEVEE manual, completely and without exceptions. Read every page listed below in full, including every note, tip, and limitation. Do not skim, skip, or summarize from memory. If a page fails to load, retry it or report it; do not continue without it.
>
> The 25 pages, all under `https://docs.blender.org/manual/en/latest/render/eevee/`:
>
> 1. `index.html`
> 2. `render_settings/index.html`
> 3. `render_settings/sampling.html`
> 4. `render_settings/light_paths.html`
> 5. `render_settings/raytracing.html`
> 6. `render_settings/volumes.html`
> 7. `render_settings/curves.html`
> 8. `render_settings/depth_of_field.html`
> 9. `render_settings/motion_blur.html`
> 10. `render_settings/film.html`
> 11. `render_settings/performance.html`
> 12. `render_settings/grease_pencil.html`
> 13. `scene_settings.html`
> 14. `world_settings.html`
> 15. `object_settings/index.html`
> 16. `object_settings/object_data.html`
> 17. `material_settings.html`
> 18. `light_settings.html`
> 19. `light_probes/index.html`
> 20. `light_probes/sphere.html`
> 21. `light_probes/plane.html`
> 22. `light_probes/volume.html`
> 23. `limitations/index.html`
> 24. `limitations/limitations.html`
> 25. `limitations/nodes_support.html`
>
> After reading, check every answer against the EEVEE limitations pages and against the rules of `docs/shading-style-guide.md`. Also read `docs/anatomy-manual.md` before modeling any body. Cite the MHS3 screenshot numbers for every Stories decision. The app's shader is the source of truth for the final look; Blender is a preview.

---

## 1. The Stories look in one page

Capcom presented the Monster Hunter Stories 3 renderer at CEDEC 2026 ([Famitsu](https://www.famitsu.com/article/202608/83946), [CGWORLD](https://cgworld.jp/article/202609-cedec-mhs3.html)). The art brief was "young-adult manga with a theatrical anime film feel" ([Game*Spark, February 2026](https://www.gamespark.jp/article/2026/02/13/162686.html)). The rules that follow from it:

- **Two tones, hard boundary.** Shading comes from the angle between the surface and the light. There is a lit color and a shadow color with a hard edge between them. A second, darker shadow color appears only where a mask forces it (under the lip, inside a collar), never as a third light band.
- **Only fur is soft.** Every other material keeps a hard boundary. Softness, highlight size, and highlight softness are fixed per material category, so carapace reads as carapace on a monster and on armor alike.
- **Skin never gets ugly shadows.** Skin has a lift correction that keeps small shadow islands off the face as the light moves.
- **Faces shade from a proxy.** Face normals come from a generic head shape (a fitted ellipsoid in the app), not from the sculpt. Face shadow maps are not used, because they break under several free lights.
- **Designed shadows are masks.** Forced shadows are a separate mask, never painted into the base color.
- **One highlight source.** Highlights come from the key light only. An edge highlight adds a glint near the silhouette where the normal highlight disappears. An optional gradient tints the highlight only, for iridescent shells.
- **Light in five parts.** Base color, shadow color, second shadow color, rim light, and fill. Ambient comes from one fixed direction and touches only the shadow color. Fill also touches only the shadow color. Base colors stay true.
- **Two outline layers.** An inverted-hull outline built into the mesh, plus depth and normal edges in post. Lines are tinted by the surface they belong to and are never pure black. Beasts use a lower edge sensitivity so they don't drown in lines.
- **Anime compositing.** A characters-only glow (diffusion) that keeps the brightest color channel so skin keeps its warmth; flare that brightens screen edges; para that darkens the top of the frame; depth fog; a shadow-only color change.
- **Detail depends on the subject.** Characters are flat and graphic. Monsters and props are more rendered but still two-tone. Environments are painterly (MHS3-01). Characters never get monster-level rendering.
- **Complexity lives inside clear symbols.** Add pattern and texture inside the lit area, the shadow area, the highlight, and the rim. Never add a new tone.

---

## 2. Per-style rules

Every style uses the same material and post pipeline. The presets are in `src/model/presets.ts`. The Render section of the Material tab can override the main values per style.

### Stories (default)

| Area | Rule |
| --- | --- |
| Palette | Clean, rich, a little moody. Warm key light, cool shadows outdoors (MHS3-01, MHS3-02). Warm candlelight with haze indoors (MHS3-05). |
| Shading | One hard boundary. Shadow tint is hue-shifted toward blue-violet, never grey. Second shadow only from masks. |
| Lines | Hull plus post edges, thin, colored by the local material (about 40% of its color), never pure black. |
| Rim | Post rim of constant width on the lit side, weaker on the shadow side, masked by lighting so it never reads as a sticker outline. |
| Highlights | Key-light only, small. Leather gets a broad soft one, metal a sharp one, cloth none. |
| Face and hair | Near-flat skin with one hard shadow shape. Hair highlights are short slashes along clumps on the lit side (MHS3-07, MHS3-09). |
| Post | Diffusion instead of big bloom, flare, para, light fog, a slight film grade and grain. |
| Background | Deep blue gradient in the app; painterly environments in scenes. |

### Breath

Breath of Fire 4 used muted, earthy colors and planar shading with big flat areas and few outlines, so the whole screen reads as one painting. Breath of Fire 3 was brighter.

| Area | Rule |
| --- | --- |
| Palette | Muted, earthy, with warm-against-cool contrast. |
| Shading | Two hard planar steps. The boundary follows the painted texture's brightness (the Lightning Boy painted method). |
| Lines | Thin, in a darker version of the surface color. |
| Texture | Paper grain, pigment pooling at edges, and a light 4-sector Kuwahara filter for a watercolor feel. |
| Post | Warm/cool split tone, more fog. |

### Legends

| Area | Rule |
| --- | --- |
| Palette | Saturated primaries, bright sky background. |
| Shading | Almost flat, two steps, very sharp. |
| Lines | Thick, even, and dark. |
| Highlights | Glossy, toy-like highlights on metal and plastic. |
| Shapes | Chunky and simple, like a living animation cel. Robots are segmented machines. |

### Comic

Based on the hatched ink shader the project references (the five images in `docs/style_dataset/`) and the ArcSys-style recreations below.

| Area | Rule |
| --- | --- |
| Light | Duotone per light: a warm key (red to peach), a green second light, a blue fill. |
| Shadows | Ink hatching and crosshatching only in the shadows, getting denser as it gets darker. Surface-locked by default so strokes don't slide as the character moves; Screen mode is optional. |
| Highlights | Halftone dots in the midtones and highlights. |
| Lines | Sketchy ink lines that jitter and overshoot, with an ink layer offset about a pixel for a print feel. Dark cracks at creases. |
| Eyes | Glowing ring irises with bloom. |
| Background | Charcoal. |

---

## 3. Per-material rules

These come from the screenshot study. Each rule says who handles it: **Blender** (authoring), **App** (the shader), or **Both**.

### Overall rule: detail changes with the subject

- **Characters** are flat and graphic. Skin is nearly flat with one hard shadow shape. Cloth has two tones plus texture linework. Highlights are few.
- **Monsters and props** are more rendered but still two-tone: normal-mapped scales and carved patterns, glossy highlights on horns and teeth, glowing translucent parts.
- **Environments** are painterly and semi-realistic, with atmospheric depth (MHS3-01, MHS3-03).

### Ornaments and patterns on clothing

These are the strongest identifying trait of the style.

- **Tone-on-tone relief** (Both). Embossed patterns are lighter or darker areas of the same hue, never new colors: the vine pattern on a vest (MHS3-07), knotwork on a coat (MHS3-11), an embossed emblem and laurel on a pauldron (MHS3-04), carved panels on shields and monster armor (MHS3-10, MHS3-11). In Blender, author the linework in the base color plus a shallow normal or height map. In the app, the normal map runs at low strength, so it only nudges the shadow boundary and never adds a gradient.
- **Trim bands** (Blender). Robe edges, sleeves, and hems carry repeating bands: gold diamond and chevron motifs (MHS3-08), vertical braid trims (MHS3-06), lace or scalloped hems (MHS3-05). Use a shared trim-sheet texture (`TRM_*`) laid along UV strips so bands stay straight and the same size on every outfit.
- **Stitching and seams** (Blender). Thin dashed lines along seams; quilting as rows of short marks (MHS3-09, MHS3-11). Paint them into the base color, never as geometry.
- **Construction details** (Blender): rows of toggles on a jacket front and criss-cross lacing (MHS3-04), buckles, D-rings, strap keepers, and belt pouches (MHS3-02), rivets and pyramid studs (MHS3-09, MHS3-11), scalloped scale-mail edges on hoods and cloaks (MHS3-02). Build these as small modeled pieces or alpha cards in a shared `ACC_detail` library.
- **Patches and emblems** (Both). A rounded rectangle or shield, a raised rim with a stitched edge, and a simple one- or two-color icon in the center. Red on white or cream is the recurring faction color (MHS3-01, MHS3-09, MHS3-11). They go on shoulders, upper arms, and chests. In Blender, build them as `DCL_patch_*` decal meshes floating about 0.5 mm off the cloth, with their own UV island so the icon can be swapped, and a recolor mask for base and icon. In the app, the icon becomes a selectable decal slot.
- **Floor-scale patterns** (carpets, tapestries) are environment work and out of scope. They confirm the rule anyway: a pattern is a low-contrast relief in one or two values (MHS3-05).

### Fabrics

| Material | Look | App kind |
| --- | --- | --- |
| Heavy cloth and wool | Matte, no highlight, two tones, folds as a few big planes. | `cloth` |
| Leather | Two tones plus a small, broad highlight on the key-light side only (MHS3-02, MHS3-04). | `leather` |
| Velvet | Warmer, more saturated shadow; lighter at grazing angles (MHS3-06). | `velvet` |
| Fur trim | Large jagged or zigzag tufts for the silhouette (spiky on MHS3-09, rounder on MHS3-11). The only soft shadow boundary on the character. No strand texture. | `fur` |

### Metals

- **Gold and brass** (crowns, brooches, emblems, studs, lanterns): flat base color, a slightly darker and warmer shadow, one sharp white or pale-yellow highlight shape, no environment reflections (MHS3-01, MHS3-07).
- **Steel and silver** (goggle rims, bolts, shields): cool grey with a crisp edge highlight and dark engraved lines (MHS3-09, MHS3-11).
- **Rule** (App): metals read through color and highlight shape, never through reflection maps. The `metal` kind uses the key-light highlight plus the edge highlight. Environment probes stay off.

### Lenses, glass, and translucency

- **Goggle lenses** (Both): a vertical orange-to-yellow gradient, darker at the top, a white highlight slash, optionally a thin rim (MHS3-02, MHS3-09). App kind `lens`, which draws the gradient from UV and adds the slash. Blender: the lens needs a clean 0–1 vertical UV.
- **Crystals** (App): pink, violet, and ice blue; see-through facets with brighter inner facets and a darker core; hard facet edges; glitter sparkles; bloom where sparkles are densest (MHS3-03). App kind `crystal`: facet normals, an inner-facet ramp, fresnel brightening, masked sparkle points, HDR output into diffusion and bloom.
- **Egg in its membrane** (Both): faceted shell plates split by dark cracks that glow orange-red from within, strongest in the cracks and at the edges; a pale pink outer membrane that is bright at grazing angles (MHS3-04). Emissive-mask cracks plus a `membrane` shell. The membrane recipe is reused for element auras and magic shields.
- **Glowing jewelry** (App): the pendant emits blue with a small flare streak (MHS3-07). Emissive above 1.0 plus the flare pass.
- **Candle flames** (Blender): emissive cards with a white core fading to warm yellow (MHS3-08).

### Beast and monster scales

- **Size.** Scales read as large plates on the silhouette and major forms (MHS3-01, MHS3-04, MHS3-10). Fine scale texture shows only where form is secondary: limbs, belly, secondary armor (MHS3-03).
- **Plate edges** (Blender). A darker border line in the base color and a slightly lighter plate center, for a tone-on-tone bevel with no specular noise.
- **Color** (Blender). A body color plus contrasting accent zones in hard-edged flat patches: red crests on blue plates (MHS3-01), teal patches and dark bone struts on an orange wing (MHS3-08). These go in a region mask for recoloring.
- **Glints** (App). Sparse glitter on scales, from the same sparkle function as crystals, driven by a mask so it can run per element (MHS3-01). Keep it rare: most scale cells never glint.
- **Teeth and horns.** Many small, sharp ivory cones; etched grooves with a highlight along the ridges; yellow eyes with a slit pupil and dark rim (MHS3-10).
- **Wing membranes.** Flat color areas with the pattern painted in large shapes, dark bone struts at the leading edge and fingers, spiky trailing edges (MHS3-08).
- **Beast-folk characters** use the character-level treatment: plates simplified further than on monsters, low-strength normals, pattern done with color regions.

### Fur on beasts

Sculpted clumps whose tips form the silhouette, a soft shadow boundary, color regions for markings, no strands. Clump direction follows the fur direction map in the anatomy manual.

### Faces and expressions

- **Skin:** peach or tan, nearly flat; one hard shadow shape under the jaw, beside the nose, and under the brow; a pink blush for children and softer faces (MHS3-04, MHS3-07).
- **Nose:** a small wedge shadow or a single line, sometimes a highlight on the tip. No nose outline from the front.
- **Mouth:** a short line; a darker lip hint only on adults; open mouths show a flat teeth band.
- **Eyes:** a large iris with a dark pupil, a darker upper iris (lid shadow), one or two white highlight dots, sometimes a bright rim ring (MHS3-09), a thick upper lash line, a thin lower line, sometimes a crease line. The lid shadow slides with blinks and the highlight follows gaze so no expression hides it.
- **Closed eyes and smiles:** a single curved line arched upward (MHS3-11).
- **Brows:** short thick strokes or dashes in the hair color (MHS3-07, MHS3-09).
- **Face marks:** a mole is one dark dot (MHS3-11).
- **Age:** a few thin lines at the nasolabial fold and eyes, a longer face, stubble as a stippled lighter texture, never geometry (MHS3-09).
- **Child face:** large head, eyes set low and wide, tiny nose, round jaw, large ears with simple inner lines, rosy cheeks (MHS3-07).
- **Face coverings** (hood, veil, mask, goggles) are separate layered pieces, so a face can be partly covered without breaking its shading (MHS3-02, MHS3-08).

### Hair

- Large clumps with sharp tips (MHS3-07, MHS3-09, MHS3-11).
- Clump separation is thin dark lines in the texture, not many small meshes.
- Highlights are a few short white slashes along each clump on the lit side, not a continuous ring.
- One hard shadow shape, cast by the fringe onto the forehead, from the forced-shadow mask.

### Lighting and post in the references

- Warm key, cool shadows outdoors; blue shadows on snow (MHS3-01, MHS3-02).
- Warm candlelight indoors with haze (MHS3-05, MHS3-08).
- Dappled sunlight through leaves as bright blobs (MHS3-10). App: the optional gobo in the Render section.
- Depth-of-field bokeh in close-ups. App: optional depth of field.
- Light floating particles. App: optional particle overlay.
- Strong atmospheric fade with distance (MHS3-01).
- Thin outlines tinted by the local material, never pure black.

### Crowd recoloring

One robe model appears in many color variants across a crowd (MHS3-05). The app recolors with a gradient map: the texture's brightness picks a position between a deep tone, the chosen color, and a lifted tone. Multiplying brightness by a color makes outfits dull; the gradient keeps them vivid. Element variants store a target color and a hue-shift rate per element.

---

## 4. How the app implements it

Code: `src/viewport/toonMaterial.ts`, `src/viewport/postPipeline.ts`, `src/viewport/hatch.ts`, `src/model/palette.ts`, `src/model/presets.ts`.

**Material kinds** (`KIND_PARAMS`): `skin`, `cloth`, `leather`, `metal`, `hair`, `scale`, `fur`, `glass`, `emissive`, `lens`, `crystal`, `velvet`, `membrane`, and `dark` for line strips. Each has fixed boundary softness, highlight strength and size, edge highlight, skin lift, and sparkle.

**Material inputs**, all optional, from glTF:

| glTF slot | Meaning in this project |
| --- | --- |
| Base color | Linework and colors. Keep it at high resolution. |
| Occlusion (R) | Forced-shadow mask. Below 0.5 forces the shadow color; below 0.2 forces the second shadow color. |
| Metallic-roughness (G) | Highlight size. |
| Metallic-roughness (B) | Highlight mask. |
| Emissive | Emissive color; strength above 1.0 feeds diffusion and bloom. |
| Normal | Used at low strength only; it moves the shadow boundary, it never adds a gradient. |

**Post pipeline**, in order: scene color and depth, the inverted-hull pass from smoothed `outlineNormal`, a normal pass for creases, a half-resolution glow (diffusion plus bloom), then one composite that draws colored lines, the screen-space rim, Kuwahara, depth of field, fog, flare, para, split tone, vignette, grain, and particles. Thumbnails use the same pipeline with a transparent background.

**Render section** (Material tab): Shade shift, Toony, Line width, Line tint, Outline shell, Lit rim, Shadow rim, Hatching and Hatch mode, Grain, Diffusion, Bloom, Light 2 color and strength, Glow eyes, Dappled light, Depth of field, Particles. Overrides are saved per style on the computer and have a "Reset to preset" button.

---

## 5. Blender asset contract

Everything here is optional unless marked required. The importer (`kindFor` in `src/viewport/gltfPacks.ts`) reads names as whole words.

### Material names choose the kind

| Word in the material or mesh name | Kind |
| --- | --- |
| `hair` | hair |
| `lens`, `goggle` | lens |
| `crystal`, `gem`, `ice` | crystal |
| `membrane`, `aura` | membrane |
| `velvet` | velvet |
| `metal`, `paint`, `armor`, `gold`, `steel` | metal |
| `leather`, `strap` | leather |
| `skin` | skin |
| `scale` | scale |
| `fur` | fur |
| `glass` | glass |
| `glow`, `emiss` | emissive |
| anything else | cloth |

### Mesh name suffixes

| Suffix | What the app does |
| --- | --- |
| `*_outline` | An inverted-hull outline mesh (flipped normals, pushed out). Drawn as line color. When present, author its width in the mesh. |
| `*_line` | Line strips for eyelid folds and the jaw/neck line. Drawn in the dark line kind. |
| `*_shadow` | A shadow-only proxy, for example a face without the nose bump. Hidden in the color pass. |

### Textures and data

- **Base color** carries linework (stitches, pattern relief lines, plate borders, hair clump lines). Keep it at 2K–4K. Control maps can be 512–1K.
- **Forced-shadow mask** in the occlusion slot (R channel), per the table above. Put designed shadows here: under the lip, under the fringe, inside collars.
- **Highlight mask** in the metallic-roughness slot: G for size, B for mask.
- **Recolor**: a grey brightness texture as base color, with region masks, where 0.5 grey maps to the chosen color.
- **Trim sheets** `TRM_*`: shared textures for bands along UV strips.
- **Patch decals** `DCL_patch_*`: floating decal meshes about 0.5 mm off the cloth, their own UV island, plus a recolor mask.
- **Detail library** `ACC_detail`: toggles, buckles, D-rings, rivets, studs, pouches, lacing cards.
- **Lens gradient**: lenses need a clean vertical 0–1 UV.
- **Region masks** for scale accent zones and fur markings.
- **Custom normals are kept.** Transfer face normals from a simple head proxy (Data Transfer from an ellipsoid, then light Laplacian smoothing). Use Weighted Normal on hard-surface parts.
- **Monster normal maps** are allowed on scales and carved relief only, at low strength.
- **Vertex colors** are reserved for shadow bias (R) and outline width (G) when the app reads them.

---

## 6. EEVEE preview recipe

Use this so Blender material previews match the app. It is based on the full EEVEE manual (the 25 pages above).

### Blender 5.2 LTS: Shader to RGB

1. Diffuse BSDF, then Shader to RGB, then a Color Ramp set to **Constant** (two stops for Stories, three for Breath's planar steps), then Mix with the lit and shadow colors. EEVEE doesn't support the Toon BSDF, and its Diffuse BSDF is Lambertian only.
2. Shader to RGB behaves like a blended material: it doesn't work with raytracing or render passes. Keep **Raytracing off** for toon previews.
3. Sharp shadows on EEVEE Next: Sun **Angle 0**, shadow **Resolution Limit 0**, **Absolute Resolution Limit off**, **Jitter off**. Otherwise Shader to RGB receives stippled soft shadows ([Blender Artists thread](https://blenderartists.org/t/did-eevee-next-break-everyone-elses-toon-shaders/1539334), [4.2 migration notes](https://developer.blender.org/docs/release_notes/4.2/eevee_migration/)).
4. Forced shadow: multiply the ramp input by the mask (occlusion texture R) before the ramp.
5. Highlight: a Glossy BSDF through its own Shader to RGB and a narrow Constant ramp, from the key light only (use Light Linking so fill lights don't add highlights).

### Blender 5.3 and later: Material Lighting nodes

The [Material Lighting Nodes](https://devtalk.blender.org/t/material-lighting-nodes-feedback/45695) (Light Info, Light Evaluation, Shadow Raycast with Softness, Attribute (Light), Light Accumulation) evaluate each light separately. Build the ramp per light and accumulate. This reacts to light color, gives sharp shadows from any light, and works with render passes. It matches the app's model: a key light plus a colored second light. See also the [NPR Project blog](https://code.blender.org/2025/05/npr-project/).

### Both versions

- **Outlines:** a Solidify modifier with flipped normals and a material with Backface Culling (Camera). This matches the app's hull. Line Art (Grease Pencil) can preview crease lines; its anti-aliasing is set by the Grease Pencil SMAA threshold and SSAA samples.
- **Glow:** the current manual has no Bloom setting. Preview emissive glow with the compositor's Glare node on emission strength above 1.
- **Hair cards and eyelashes:** Render Method **Dithered**, alpha hard-clipped with a Greater Than node. Blended transparency sorts per object only.
- **Attributes:** read color attributes and UV maps with the Attribute node. A material can use at most 14 Geometry Nodes attributes and 8 object attributes, so control channels must fit. When flat-shaded geometry is displaced, pass smoothed normals as a custom attribute.
- **Terminator artifacts** on low-poly faces: fix with the object's Shadow Terminator Normal Offset and Geometry Offset. Use custom split normals for clean faces; they export as normals and the app keeps them.
- **Colored rim or fill lights:** use Light Linking so they affect only the character. Diffuse and Glossy influence can move away from 1.0 for an artistic look.
- **Thumbnails:** Film > Transparent, low Filter Size for crisp lines. EEVEE works in half precision, like the app's HDR target.
- **Frame edges:** screen-space effects vanish at the edges; use Overscan. The app's screen-space rim and lines have the same limit, so leave margin in the frame.
- **Atmosphere** for Breath: World Mist pass plus the compositor.

---

## 7. Prompt blocks for image AIs and concept artists

These describe traits only. Don't add game or studio names.

**Stories**
> Anime film character, young-adult manga proportions, clean two-tone cel shading with one hard shadow boundary, cool blue-violet shadows and a warm key light, thin outlines tinted by each material, small key-light highlights, near-flat skin with one shadow shape, hair in large sharp clumps with short white highlight slashes, layered cloth, leather, metal and fur trim, tone-on-tone embossed patterns, gold trim bands, stitched patches with simple icons, soft glow around bright areas, painterly background with atmospheric depth.

**Breath**
> Muted earthy palette, planar cel shading with big flat areas and two hard steps, warm light against cool shadow, thin lines in a darker shade of each surface, watercolor paper grain and pigment pooling at edges, painted illustration feel, beast-folk and dragon-folk characters.

**Legends**
> Chunky toy-like shapes, saturated primary colors, nearly flat two-step cel shading, thick even dark outlines, glossy plastic and metal highlights, bright sky background, segmented robot parts, living animation cel feel.

**Comic**
> Ink comic render, warm key light and a green second light with a blue fill, crosshatching only in the shadows getting denser as it darkens, halftone dots in the midtones, sketchy jittered ink lines that overshoot the silhouette, dark crease lines, glowing ring-shaped irises, charcoal background, slight print misregistration.

---

## 8. References and lessons

**Monster Hunter Stories 3**
- [Famitsu CEDEC 2026 report](https://www.famitsu.com/article/202608/83946) and [CGWORLD CEDEC 2026 report](https://cgworld.jp/article/202609-cedec-mhs3.html): the full renderer recipe. Lesson: everything in section 1.
- [Game*Spark, February 2026](https://www.gamespark.jp/article/2026/02/13/162686.html), [Game*Spark, TGS 2025](https://www.gamespark.jp/article/2025/09/28/157778.html), [ScreenRant](https://screenrant.com/monster-hunter-stories-3-behind-the-scenes/), [Crunchyroll](https://www.crunchyroll.com/news/interviews/2026/3/13/monster-hunter-stories-3-twisted-reflection-interview): art direction. Lesson: theatrical film feel, taller proportions, at most two shadow tones, group information.

**EEVEE toon and stylized shaders**
- [StraySpark add-on comparison, 2026](https://www.strayspark.studio/blog/best-blender-toon-shader-addons-2026): Diffuse, Shader to RGB, Constant ramp, Fresnel rim, Solidify hull. Lesson: the ramp is the core; the app's per-style values are the right foundation.
- [Lightning Boy Shader 2.1](https://lightningboystudio.gumroad.com/l/aYbiH) ([video](https://www.youtube.com/watch?v=YdoBJ2lnkks)): the painted boundary comes from the texture's own brightness, then a levels crunch. Lesson: use it for Breath and fur only. It stopped at Blender 3.4 because EEVEE Next broke it, so keep the app's shader self-contained.
- [Goo Engine](https://github.com/MatandoYT/goo-engine) ([toon demo](https://dillongoo.gumroad.com/l/gooenginetoonshader)): separates self-shadow, cast shadow, and ambient; a depth-based screen rim. Lesson: a raw screen rim looks like a sticker; mask it by lighting, with separate lit and shadow strengths.
- [Festivity's HoYoverse shaders](https://github.com/festivities/Blender-miHoYo-Shaders) ([setup add-on](https://github.com/michael-gh1/Addons-And-Tools-For-Blender-miHoYo-Shaders)): separate body, hair, and face materials with per-material outline colors. Lesson: per-material line colors. Its face shadow map is not used for Stories.
- [MToon (VRM)](https://dwango.github.io/en/vrm/univrm/shaders/mtoon/): Shade Shift, Toony, rim, outline width in world or screen space. Lesson: the Render section uses these names.
- Blender Studio, Wing It! ([shading](https://studio.blender.org/blog/shading-and-rendering-of-wing-it/), [Geometry Nodes outlines](https://studio.blender.org/blog/cartoon-character-shading-with-geometry-nodes/), [lighting](https://studio.blender.org/blog/wing-it-from-concept-to-render/)): lines inside the silhouette in the surface's color; depth tint for separation. Lesson: colored inner lines.
- Custom normals: [aVersion of Reality series](http://www.aversionofreality.com/blog/2022/3/19/customizing-normals), [workflow](http://www.aversionofreality.com/blog/2022/4/21/custom-normals-workflow), [Fondant](https://fondanttools.gumroad.com/l/stylized-normals). Lesson: face normals from a proxy ellipsoid; the app blends toward one at runtime.
- [FletchDotGames ArcSys recreation](https://fletch.games/works/arcsyslighting/): ILM channels for shade bias, highlight strength, and highlight size; screen-space dots and a Fresnel tint only in shadow. Lesson: Comic halftone and the shadow rim are shadow-masked.
- [Spider-Verse in EEVEE](https://garagefarm.net/blog/recreating-the-spider-verse-look-in-the-blender-node-editor): halftone in highlights, hatching in shadows, misregistration. Lesson: Comic ink offset.
- [NPR Shader Kit](https://superhivemarket.com/products/npr-shader-kit--stylized-rendering): patterns locked to screen or surface. Lesson: Hatch mode, Surface by default.
- Painterly: [80.lv Kuwahara-style tutorial](https://80.lv/articles/tutorial-how-to-make-any-texture-look-painterly-in-blender), [BlenderNation hand-painted look](https://www.blendernation.com/2025/10/26/how-to-create-a-hand-painted-look-in-blender/). Lesson: light Kuwahara for Breath.
- EEVEE Next toon fixes: [Blender Artists thread](https://blenderartists.org/t/did-eevee-next-break-everyone-elses-toon-shaders/1539334), [4.2 migration notes](https://developer.blender.org/docs/release_notes/4.2/eevee_migration/), [devtalk feedback](https://devtalk.blender.org/t/blender-4-2-eevee-next-feedback/31813?page=42). Lesson: the sharp-shadow settings in section 6.
- Blender NPR roadmap: [NPR Project](https://code.blender.org/2025/05/npr-project/), [Material Lighting Nodes](https://devtalk.blender.org/t/material-lighting-nodes-feedback/45695). Lesson: two preview recipes, 5.2 and 5.3+.

**Techniques**
- Guilty Gear Xrd: ILM control maps, vertex-color outline width, hull with smoothed normals.
- Tonal art maps (Praun et al., 2001): nested hatch levels so strokes stay put as tone changes. The app's `hatch.ts` builds four nested levels.
