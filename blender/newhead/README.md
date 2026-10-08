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
