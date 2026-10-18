---
name: mhs3-shader-match
description: Locked MHS3 cel shader for the anime head - three skin tones (lit, warm cel shadow at ~0.80, a deep core tone at ~0.57 along the jaw), hard terminator, warm dark outline, flat painted skin, fixed key light - and the measured shader rules S1-S8 against the official Leo render. Use whenever a head is rendered for judging, when shading looks rubbery or amateur, and before changing any shader, light or skin-texture setting.
---

# MHS3 shader: one locked spec, changed only through measured rules

Sammy (q35): "the shading overall looks rubbery and amateur, unlike the mhs3 shading which looks neat". Sammy (q36):
"the shader must always match the mhs3 shader."

## The spec
`MHS3_SPEC` in `blender/head_vroid/vroid_toon.py`. Every judged render uses `vt_go2(key)`, so a change in score is a
change in the model, never in the light. The same values are mirrored in `knowledge/mhs3_face_rules.json` under
`shader.spec`.

- **Skin.** Diffuse, then Shader-to-RGB, then a two-stop ramp (0.285-0.315, a hard cel edge).
  - The shadow multiply tint is warm, linear (0.66, 0.58, 0.56). Linear tint = sRGB ratio ** 2.2, because the
    render's Standard view transform turns linear 0.6 into an sRGB ratio of about 0.79.
  - A third deep tone (`VT_DeepRamp`, BW threshold 0.19, tint (0.35, 0.27, 0.27)) sits in the core of the shadow.
    Leo has it along the jaw side, on about 4.6% of the lower face.
- **Light.** Key light (0.30, -0.90, 0.35), near-frontal from the viewer's right. Leo's shadow covers 16% of the
  lower-face skin: one strip on the far side plus the shapes under the nose and lip.
- **Face normals.** Ellipsoid-blended at w 0.95, which gives clean shadow shapes. Smoothed proxies were blotchy.
- **Skin texture** (`mhs3_paint.py face()`):
  - flat (`mf=1.0`);
  - warm bake (1.04, 0.92, 0.82) x skin_scale 0.88, which gives lit skin of about (227, 189, 159) against Leo's
    (227, 190, 161);
  - painted details only: nose wedge, nose base, lid socket shade, subtle lower lip (alpha 0.45).
- **Outline.** Solidify, 1.2 mm, (92, 58, 44).
- **Eyes, brows, lashes, mouth.** Unlit (emission). Use DITHERED, not BLENDED, which hid the iris.

## Rules (render, measured by `blender/tools/mhs3_render_measure.py` on the front render vs Leo)
| id | metric | Leo |
|---|---|---|
| S1 | main cel-shadow band / lit peak | 0.803 |
| S2 | shadow warmth: R ratio - mean(G, B) | 0.049 |
| S3-S5 | lit skin RGB | 227 / 190 / 161 |
| S6 | shadow area (below 0.9 of lit) | 0.16 |
| S7 | terminator softness | 0.089 |
| S8 | deep-tone fraction (below 0.68 of lit) | 0.046 |

## Changing the spec
Only when an S rule fails for a lighting reason. Try the change on the same mesh with `vt_front(key, tag, light)`,
validate all S rules, then update `MHS3_SPEC` and the rulebook's `shader.spec` together and log why. `vt_skin` must
skip `VT_DeepRamp`: it set every ramp once and made the deep tone 12% of the face.
