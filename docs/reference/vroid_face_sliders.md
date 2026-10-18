# VRoid Studio 2.10 face sliders (read on Sammy's PC, 2026-10-18)

Sammy: "the eyes and all elements of the head/face are editable, just like in vroid". The library head's defaults are a
starting point; every one of these must become a slider (ID- shape key) in the creator. Parameters panel, Face tab,
male base, in order:

- Eyes: Eye Size X, Eye Size Y, Eyes Position (Y), Eyes Position (X), Rotate Eye Socket, Inner Eye Slant (Y), Reduce
  Inner Slant, Outer Eye Slant (Y), Straighten Upper Eyelid, Straighten Lower Eyelid, Move Upper Eyelid Down, Move
  Lower Eyelid Up, Scornful Look, Droopy Eyes, Lower Eyelashes Tips, Iris Size (X), Iris Size (Y), Gaze (Y), Gaze
  Distance
- Brows: Eyebrows Tilt, Eyebrows Position (Y), (X), (Z), Rotate Eyebrows (Y), Eyebrows Arch, Eyebrows Length
- Nose: Nose Size, Nose Width, Nose Tip Position (Y), Nose Bridge Prominence, Nose Bridge Width, Nose Bridge Curve,
  Nose Size Scale, Nose Base Prominence (Y)
- Mouth: Mouth Width, Mouth Position (Y), Mouth Corners, Mouth (Z), Thinner Lips, Thicker Upper / Lower Lip (Fem,
  Masc), teeth (vampire, shark, fang, hide, shrink - upper / lower)
- Ears: Ear Size, Ear Tip (Y), Ear Stretch, Ear Prominence, Remove Ears
- Contour: Jaw Position (Y), Cheekbones Position (Z), Sunken Cheeks, Chin Roundness, Jawline Position (Y), Chin Length,
  Chin Tip Position (Z), Chin Width, Jaw Angle (Increase)
- Blends: Fem / Masc Eyebrows, Nose, Mouth, Outlines, Head
- Left column: Face Sets, then per-part texture/shape presets (brows, eyelashes, eyeline, iris, nose, mouth, ears,
  skin, makeup).

Our MHS3 rework (blender/head_vroid/mhs3_reshape.py) already drives several of these as knobs (eye_s / eye_sx /
eye_sz = eye size, lid_low / lid_up / lid_drop = eyelids, brow_dz, nose_lift, jaw table = chin width / jaw, chin_fwd,
neck_sx). Next step: bake each knob (+/-) into shape keys on the VRoid face so the creator exposes them like VRoid.
