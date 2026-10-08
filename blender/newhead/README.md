# New head (from scratch, iter n31)

Original mesh, no copied geometry. The only dataset input is `mean_head.npz`: the median radial height map r(lon, lat)
of 14 measured anime heads (4 outliers rejected), in head units (chin z=0, skull top z=1, forward -Y). Only the
median is stored; per-model measurements are not.

    python3 build_head.py OUT.npz            # needs the bpy module (Blender 5.x Python)
    python3 validate_head.py OUT.npz val.json   # dataset bands + repo topology stats
    python3 skin_skew.py OUT.npz
    python3 render_new.py OUT.npz out.png       # Cycles clay, eyeballs from OUT_eyes.json
    # TypeSafe (PC, key in env): python typesafe_head_judge.py val.json topo.json out.json

Pipeline: cube lattice warped to the face (front 52 deg, back 100 deg) -> projected on the smoothed mean head plus
authored features (nose, sockets, brow, lips) -> eye O-grids (rectangle block, 3 rings, almond, lid rim) and mouth
O-grid with a bag -> neck: footprint hole + inset ring + analytic tube -> quad squaring -> limit-surface fit ->
one subdivision -> O-grid ears laid out in the ear plane and quad-squared.

Some helper paths (head_audit, the dataset band json) still point at the session scratch folder; see validate_head.py.

## Look (n44)
In Blender (needs the project's NG_ groups from blender/scripts/shaders.py in the file):

    exec(open(r"<repo>\blender\newhead\apply_look.py").read(), {"NPZ": npz, "EYES": eyes_json, "TAG": "n44", "OFF_X": 1.8})
    exec(open(r"<repo>\blender\newhead\render_look.py").read(), {"TAG": "n44", "OUT": r"<repo>\docs\qa\newhead\look_n44"})

NG_ToonSkin with a "shade" mask (ear bowl, under the nose, jaw underside, neck), face normals blended to a head
ellipsoid turned toward the viewer (MHS3 flat-lit face, shadow on the far cheek), NG_Eye irises, inverted-hull
outline faded at the eyes/nose/mouth and off on the buried ear root, upper lash with wing, outer lower lash, brows.
Ears: O-grid in the ear plane, relief in fractions of ear height (helix, scapha, antihelix, concha, tragus, lobe),
back grown out of the skull, one Catmull-Clark level; box 0.19-0.605 H so the visible ear runs brow to nose base.

## Painted eyes (n47)
Matched to an MHS3 frame (eyes_n47c.png: ours top, the game bottom). The lid opening is filled with a thin plate flush
with the skin carrying a painted iris (MAT_MHS3Eye: flat green, dark outline, two concentric arcs on the inner side,
light lower area, darker top, vertical oval pupil, one big highlight half outside the iris, grey sclera with a lid
band). Lid line, lower lid line and brows are flat emission strokes. Eye opening: lid edge h/w 0.64, eye gap 1.20
eye widths (frame 0.57 / 1.2; MHS3 creator 0.62 / 1.25). The lid edge loop is saved per vertex ("lid" in the npz).
