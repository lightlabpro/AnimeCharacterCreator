# Clay comparison against real anime head meshes (q28)

Sammy (2026-10-17): "the head has some distorted parts and weird shapes all around. Please validate with a 3d model
for an anime character." Toon paint and flat lighting hide dents, ripples and creases; plain clay shading does not.

1. `extract_heads.py OUT_DIR [ours.blend ...]` (bpy python): loads the verified dataset heads
   (`knowledge/dataset-pass2/verified_shape.json`, landmarks from `datasets_work/measured.json`) and our built head,
   normalises to head height (h = 0 skull top .. 1 chin, face toward -y) and writes `ref_*.npz` / `ours_*.npz`.
   2 of the 7 verified models (1ca6d15f, 47a4e71d) import at another scale/pose than their landmarks and come out
   empty - 5 are used.
   `sdfnorm.py sdf.npz out.npz` does the same for a raw `sdf_head.py` mesh (iterate the form without Blender).
2. `clay.py`: numpy z-buffer renderer, smooth normals, one Lambert light - front / 3/4 / side / back views.
3. `sil.py names...`: front and side silhouettes overlaid (align side outlines on the forehead: dataset centres are
   body centres, not head centres).
4. TypeSafe A/B on the clay renders (`typesafe_ab_compare.py` with REF = a dataset head's clay render): overall,
   head_shape, jaw_chin, clean, plus the dented / artifacts yes-no questions.
