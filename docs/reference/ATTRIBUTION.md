# Third-party models used in the library

## Head base (q31)

The v2 head's face front and ears come from a reworked dataset head:

- **"Autumn Girl" by Aryzus** (Sketchfab), licensed **CC Attribution 4.0** (CC BY 4.0).
  TexVerse uid `d60fb4427e6e4858bc82c4175b0fdbb5`.
- Changes: re-proportioned to the median of five verified dataset heads, eye sockets filled, smoothed and resampled
  into a signed-distance grid (`blender/head_v3/base_head.py` makes `blender/head_v3/base_grid_d60.npz`).
  `blender/head_v2/sdf_head.py` blends that grid with our own measured skull, back of the head, jaw sides and neck,
  narrows the lower face and closes the eye sockets. Eyes, brows, nose, mouth, hair and shading are our own pieces.

This credit must ship with any exported head, pack or app build that contains the head.

## VRoid-standard head base (q32)

Sammy lifted the no-VRoid rule on 2026-10-17 so the head can use the industry-standard VRoid build. Candidates
(Sketchfab VRoid exports, all **CC Attribution 4.0**, via the TexVerse dataset), downloaded to
`datasets_work/vroid_male/` with his go-ahead:

- **"Anime Boy for Blender."** by **Zarya** - TexVerse uid `3f8f011947cb4e1a9e0e97f8c38a4cc3` (first base tried)
- "anime style male character" by A3i - `ea4402ae79004c8aad4c4c73df801bdf`
- "Anime Model Boy Rigged" and "Anime Model, Beuatiful Boy, Rigged!" by dequeijospizza - `0fe1676a...`, `b1beef26...`
- "Anime Boy Ninja Character - Fully Rigged" by infinitymanpk - `2bca956058144a339b28c218c38b6e9b`

Whichever base ships, its author's credit must ship with it (and VRoid's own terms for exported models apply).
