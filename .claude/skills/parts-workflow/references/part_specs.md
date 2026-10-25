# Part sheets: what each Midjourney job must show

All sheets: plain light-grey background, orthographic-looking turnaround, flat even light (no dramatic shadows - the
generator bakes them into the texture), MHS3 character art style (Capcom Monster Hunter Stories 3 toon look: soft cel
shading, large clear eyes with a simple upper-lid line, small nose, clean shapes). Use an MHS3 render from
`docs/reference/mhs3/` as `--sref` (style), never `--cref` of Leo's face (not an exact copy of Leo).
Aspect `--ar 3:1` for three views, `--ar 1:1` for one view. One job per sheet; at most two re-rolls.

Hunyuan multi-image wants separate images per view: crop each view from the sheet into its own square PNG with
`.claude/skills/ai-3d-pipeline/scripts/prepare_reference.py` (it checks size, background and centring).

| Order | Part | Sheet | Views | Notes |
|---|---|---|---|---|
| 1 | head_base | bald head and neck, neutral face, ears visible | front, side, back (+3/4 if a re-roll is needed) | the face is part of this mesh; hair hidden so the skull is clean |
| 2 | hair | hair only, on a faint grey head silhouette | front, side, back | black hair (base D choice); fringe length per `front_len`; becomes a separate shell |
| 3 | eyes | eye sheet: open eye front, 3/4, iris detail | front, 3/4 | mostly texture: iris and lid line painted onto the head; MHS3 eye standard |
| 4 | eyebrows | brows front and 3/4 | front, 3/4 | texture or thin ribbon mesh |
| 5 | mouth | mouth closed + slightly open, front and 3/4 | front, 3/4 | texture + small inner mouth mesh |
| 6 | ears | ear close-up front, side, back | front, side, back | only if head_base ears fail their mesh rules |
| 7 | nose | nose close-up front, side | front, side | only if head_base nose fails its profile rules |
| 8 | facial_hair | none by default | - | Sammy decides |
| 9 | torso | neckless torso in light clothes, T-pose arms cut at the shoulder | front, side, back | |
| 10 | arms_hands | one arm with open hand, fingers spread | front (palm down), side, back | mirrored in Blender |
| 11 | legs_feet | legs with boots, from the hips | front, side, back | |

Prompt template (fill the bracket, keep the rest):
`character design turnaround sheet, [PART DESCRIPTION], [VIEWS] views side by side, Monster Hunter Stories 3 character
art style, anime toon render, soft cel shading, flat even lighting, plain light grey background, no text --ar 3:1
--sref <MHS3 image URL> --v 7`
