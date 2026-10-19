"""q33 MHS3 reshape of a VRoid export + MHS3 textures -> new GLB (bpy, headless).

    python mhs3_reshape.py IN.glb TEX_DIR OUT.glb [--knobs knobs.json]

One smooth warp field is applied to EVERY mesh (face, eyes, mouth, brows, hair, body neck): vertices that two meshes share
(the face / body neck seam) move identically, so nothing opens. Measured on the VRoid face (3f8f0119) in pupil-distance
units (IPD = 0.0796 m, pupil line z = 1.6093 m): nose tip 0.49, mouth 0.76, chin 1.30 below the pupils - a short VRoid
lower face. MHS3 Leo (pupil-aligned): nose 0.63, mouth 0.85; MHS3 adult faces are longer. The warp maps depth below the
pupils d -> g(d) through MAP (Pchip), widens the jaw/chin a little (Leo 0.81 IPD wide 1.2 below the pupils, VRoid a V),
lifts the nose bridge (VRoid nose is almost flat) and lowers the brows onto the eyes (VRoid brows 0.40 IPD above the
pupils, Leo ~0.2).
"""
import json
import os
import sys

import bpy
import numpy as np


def pchip(xk, yk):
    """Monotone cubic (Fritsch-Carlson) - no scipy in Blender's Python."""
    xk = np.asarray(xk, float); yk = np.asarray(yk, float)
    h = np.diff(xk); dlt = np.diff(yk) / h
    m = np.zeros_like(yk)
    for i in range(1, len(xk) - 1):
        if dlt[i - 1] * dlt[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dlt[i - 1] + w2 / dlt[i])
    m[0], m[-1] = dlt[0], dlt[-1]

    def f(x):
        x = np.asarray(x, float); xc = np.clip(x, xk[0], xk[-1])
        i = np.clip(np.searchsorted(xk, xc) - 1, 0, len(h) - 1)
        t = (xc - xk[i]) / h[i]
        h00, h10, h01, h11 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t, -2 * t**3 + 3 * t**2, t**3 - t**2
        v = h00 * yk[i] + h10 * h[i] * m[i] + h01 * yk[i + 1] + h11 * h[i] * m[i + 1]
        # outside the table: keep the end offset (m1: clamping flattened everything above the brow into one plane)
        return np.where(x < xk[0], x - xk[0] + yk[0], np.where(x > xk[-1], x - xk[-1] + yk[-1], v))
    return f

K = dict(
    z0=1.6093, ipd=0.0796,
    MAP=[[-1.0, -1.0], [0.0, 0.0], [0.22, 0.22], [0.49, 0.62], [0.76, 0.86], [1.30, 1.42], [2.0, 2.12], [3.0, 3.0], [9.0, 9.0]],   # m14: (0,0)->(0.49,0.62) stretched the lower iris x1.27 (tall pupil) - identity through the eyes
    jaw=[[0.40, 0.0], [0.65, -0.05], [0.95, 0.02], [1.15, 0.16], [1.32, 0.26], [1.6, 0.12], [2.2, 0.0]],   # q34 realism: cheeks in (pupil-aligned 1.63 vs Leo 1.43 IPD), chin broader/squarer (0.74 vs 0.81)
    neck_sx=0.16, neck_d=(1.45, 1.75, 2.15, 2.5),   # q34: thicker adult neck (all round), ramps in/out over d
      # m3: still a narrow V      # extra x scale by depth (front half)
    nose_lift=0.0070, nose_z=(0.15, 0.50), nose_w=0.12,                        # metres forward along +y on the bridge
    brow_dz=-0.0185,   # m11 brows_far 0.74 (control 0.60)
      # m5: still high above the eyes (Leo ~0.12 IPD gap)
                                                             # metres (brow mesh only)
    eye_sz=1.06,   # q35 Sammy 'eyes too elongated / egyptian': taller, rounder opening   # q34b Sammy: eyes must be a bit bigger, not smaller (0.86 'looked almost evil')   # q34: narrower opening (realism)
                                                                 # eye opening height scale (almond)
    # q33 TypeSafe (m2 vs Leo; Leia control): eyes_vroid 0.87 (0.58), too_anime 0.85 (0.58) -> smaller eye region:
    # everything round each eye (eye parts AND the face's eye hole) scaled toward the eye centre, fading out
    eye_c=(0.0424, 1.6061), eye_r=(0.034, 0.024), eye_s=1.04, eye_sx=0.92, eye_sx_out=0.80,   # q35: the outer half pulled in harder (VRoid's long outer tail)   # q34b: bigger than m15 (0.88); a little shorter sideways only   # q34: eye_sx - opening shorter sideways (VRoid's long white outer corner; Leo's eye is compact)
      # q34: smaller eyes (realism; m15 0.88)
    eye_fall=0.9, iris_s=1.12,   # q35: Leo's iris fills more of the opening (less white each side)
      # m3: iris 0.93 read small (Leo's fills the opening)
    iris_c=0.0398, iris_sx=1.0, iris_dx=0.0,   # m13: iris painted in 3D instead (iris_sx 1.22 / dx 0.0012 tried)     # m12 close-up: the iris rendered as a tall narrow oval set inward
    lid_low=0.0004, lid_up=0.0026,   # q34b: open, friendly (raised lower lid + heavy lid read as a glare)   # q34: lower lid up to the iris (m19 showed a white band under the iris - staring)
      # m11 TypeSafe shape_flat_top 0.77 (control 0.65)
                       # m6: round the lower lid (VRoid flat), lift the inner-mid upper lid
    mouth_c=(0.0, 1.5493), mouth_r=(0.032, 0.012), mouth_sx=1.0,   # m3: 1.16 dented the cheeks by the mouth - the line is widened in paint instead
    mouth_fall=1.2,
)


def local_fields(P, key):
    """Eye-region shrink (toward each eye centre, in x and z) and mouth widening, before the global warp."""
    x, y, z = P[:, 0].copy(), P[:, 1].copy(), P[:, 2].copy()
    ex, ez = K["eye_c"]; rx, rz = K["eye_r"]
    for sgn in (1, -1):
        r = np.hypot((x - sgn * ex) / rx, (z - ez) / rz)
        w = np.clip((1 + K["eye_fall"] - r) / K["eye_fall"], 0, 1); w = w * w * (3 - 2 * w)
        s = 1 - (1 - K["eye_s"]) * w
        if key.startswith("EyeIris"):
            s = s * K["iris_s"]
        if key.startswith(("EyeIris", "EyeHighlight")):
            ic = sgn * K["iris_c"]
            x = np.where((x * sgn) > 0, ic + (x - ic) * K["iris_sx"] + sgn * K["iris_dx"], x)
        if key.startswith(("EyeIris", "EyeHighlight")):           # q36 E1: the lid covers the iris top (Leo)
            z = np.where((x * sgn) > 0, z + K.get("iris_dz", 0.0) * np.clip(1 - r, 0, 1) ** 0, z)
        side = (x * sgn) > 0
        outer = np.clip((x * sgn - ex) / (0.5 * rx), 0, 1)          # 0 at the eye centre .. 1 on the outer half
        sx_e = K.get("eye_sx", 1.0) * (1 - outer) + K.get("eye_sx_out", K.get("eye_sx", 1.0)) * outer
        sxx = s * (1 - (1 - sx_e) * w)
        if key.startswith(("EyeIris", "EyeHighlight")):
            sxx = s
        x = np.where(side, sgn * ex + (x - sgn * ex) * sxx, x)
        z = np.where(side, ez + (z - ez) * s, z)
        # lid shape: relative position across the eye (-1 inner .. +1 outer) and above / below the centre
        rel = np.clip((x * sgn - ex) / rx, -1.2, 1.2); wl = np.clip((1.6 - r) / 0.8, 0, 1)
        wl2 = np.clip((2.3 - r) / 0.8, 0, 1)
        lowb = (z < ez) * K["lid_low"] * np.clip(1 - rel ** 2, 0, 1) * wl
        upb = (z > ez) * K["lid_up"] * np.exp(-((rel - K.get("lid_up_c", -0.25)) / K.get("lid_up_w", 0.5)) ** 2) * wl
        # q36 ES2: Leo's upper lid is low at the inner corner and stays high over the outer half (a lens, peak mid)
        wl2 = np.clip((2.3 - r) / 0.8, 0, 1)                    # the corners sit at rel ~ +-0.53 (opening 36 mm, eye_r 34 mm)
        upb = upb - (z > ez) * K.get("lid_in_drop", 0.0) * np.exp(-((rel + 0.40) / 0.15) ** 2) * wl2 \
                  + (z > ez) * K.get("lid_out_up", 0.0) * np.exp(-((rel - 0.30) / 0.15) ** 2) * wl2
        # q36 ES2: the lower lid's outer half sat low against Leo's lens-shaped opening - lift it
        lowb = lowb - (z < ez) * K.get("lid_low_out", 0.0) * np.clip((rel - 0.05) / 0.40, 0, 1) * wl2
        # q34: heavy MHS3 upper lid - the lid (skin edge, lash, white's top) comes down over the top of the iris
        upb = upb - (z > ez) * K.get("lid_drop", 0.0010) * np.clip(1 - (rel / 1.1) ** 2, 0, 1) * wl
        if not key.startswith(("EyeIris", "EyeHighlight")):    # m14: the lid offsets also stretched the iris
            z = np.where(side, z - lowb + upb, z)
        # q36 ES1 (Sammy: 'the eye shape is not matching the mhs3 one ... a standard'): VRoid's opening is tilted
        # (outer corner 0.27 of the width higher than the inner; Leo ~level) - rotate the opening, not the iris
        et = K.get("eye_tilt", 0.0)
        if et and not key.startswith(("EyeIris", "EyeHighlight", "FaceBrow")):
            wt = np.clip((1.9 - r) / 0.7, 0, 1); wt = wt * wt * (3 - 2 * wt)
            z = np.where(side, z - et * np.clip(rel, -1.2, 1.2) * wt, z)
    # q35 Sammy 'the nose looks too thin': widen the nose (bridge to wings) about the midline
    nz0, nz1 = K.get("nose_zr", (1.5700, 1.5960))
    nwz = np.clip((nz1 - z) / 0.004, 0, 1) * np.clip((z - nz0) / 0.004, 0, 1)
    nwx = np.exp(-(x / K.get("nose_wr", 0.016)) ** 2)
    x = x * (1 + (K.get("nose_sx", 1.45) - 1) * nwz * nwx * (y > 0.03))
    # q36 ear rule (Leo: ear top ~0.15 D above the pupils, lobe ~0.31 D below; VRoid lobe 0.47 D): shorten the ear
    # about its top, outer shell only (|x| past the head side), blended in over 1 cm so the root does not tear
    esz = K.get("ear_sz", 1.0)
    if esz != 1.0 and key.startswith(("Face_00_SKIN", "Body_00_SKIN")):   # (kept for old versions; prefer ear_dz)
        x0, x1 = K.get("ear_x", (0.078, 0.089)); etop = K["z0"] + K.get("ear_top", 0.020)
        we = np.clip((np.abs(x) - x0) / (x1 - x0), 0, 1) * (y < 0.005) * (z < etop + 0.01)
        we = we * we * (3 - 2 * we)
        z = z + we * ((etop + (z - etop) * esz) - z)
    edz = K.get("ear_dz", 0.0)                 # q36: squashing (ear_sz < 1) made the ear top pointed - lift instead
    if edz and key.startswith(("Face_00_SKIN", "Body_00_SKIN")):
        x0, x1 = K.get("ear_x", (0.078, 0.089))
        we2 = np.clip((np.abs(x) - x0) / (x1 - x0), 0, 1) * (y < 0.005)
        we2 = we2 * we2 * (3 - 2 * we2)
        z = z + edz * we2
    # q36 R5: behind the jaw, under the ear, VRoid's head side sticks out past the jaw line in the front view (1.49 D
    # wide at 0.40 D below the pupils; Leo's jaw contour is the outline there, 1.31 D) - pull that side in
    hs = K.get("headside_sx", 1.0)
    if hs != 1.0:
        za, zb, zc, zd = K.get("headside_z", (0.010, 0.025, 0.070, 0.095))     # metres below the pupils
        dz = K["z0"] - z
        wz = np.clip((dz - za) / (zb - za), 0, 1) * np.clip((zd - dz) / (zd - zc), 0, 1)
        wy = np.clip((0.002 - y) / 0.018, 0, 1)
        wx = np.clip((np.abs(x) - 0.058) / 0.016, 0, 1)
        w = wz * wy * wx; w = w * w * (3 - 2 * w)
        w = w * (1 - np.clip((np.abs(x) - 0.083) / 0.005, 0, 1) * (dz < 0.045))   # q36: leave the ear shell (pulling
        x = x * (1 - (1 - hs) * w)                                               # its lobe in left a pointed top)
    mx, mz = K["mouth_c"]; mrx, mrz = K["mouth_r"]
    r = np.hypot((x - mx) / (mrx * 1.4), (z - mz) / (mrz * 2.5))
    w = np.clip((1 + K["mouth_fall"] - r) / K["mouth_fall"], 0, 1); w = w * w * (3 - 2 * w)
    x = x * (1 + (K["mouth_sx"] - 1) * w * (y > 0.0))
    return np.stack([x, y, z], 1)


def warp(P, key):
    P = local_fields(P, key)
    z0, u = K["z0"], K["ipd"]
    m = np.array(K["MAP"], float); g = pchip(m[:, 0], m[:, 1])
    j = np.array(K["jaw"], float); jaw0 = pchip(j[:, 0], j[:, 1]); jaw = lambda d: np.where((d < j[0, 0]) | (d > j[-1, 0]), 0.0, jaw0(d))
    x, y, z = P[:, 0].copy(), P[:, 1].copy(), P[:, 2].copy()
    d = (z0 - z) / u
    dn = g(d)
    front = np.clip((y + 0.01) / 0.05, 0, 1)                  # jaw widening only on the front half
    sx = 1 + np.nan_to_num(jaw(d)) * front
    ct = K.get("cheek_tab")                   # q36 R6/R7: the cheek silhouette (front view) is on the side of the head,
    if ct:                                   # behind the jaw table's front-half weight - scale x at all depths
        c_ = np.array(ct, float); gc = pchip(c_[:, 0], c_[:, 1])
        inr = (d >= c_[0, 0]) & (d <= c_[-1, 0])
        sx = sx * (1 + np.where(inr, gc(np.clip(d, c_[0, 0], c_[-1, 0])), 0.0))
    a0, a1, a2, a3 = K["neck_d"]
    nk = np.clip((d - a0) / (a1 - a0), 0, 1) * np.clip((a3 - d) / (a3 - a2), 0, 1)
    nk = nk * nk * (3 - 2 * nk)
    sx = sx * (1 + K["neck_sx"] * nk)
    x2 = x * sx
    yc = 0.0                                              # neck depth too (about the neck axis)
    y = yc + (y - yc) * (1 + 0.6 * K["neck_sx"] * nk)
    z2 = z0 - dn * u
    # nose bridge lift
    t = (d - K["nose_z"][0]) / (K["nose_z"][1] - K["nose_z"][0])
    bump = np.exp(-(x / u / K["nose_w"]) ** 2) * np.clip(t, 0, 1) * np.clip((1.15 - t) / 0.3, 0, 1)
    # q36 artifacts: the mouth interior / teeth sit behind the skin at small y - with the skin-depth gates they stayed
    # put while the skin moved back and poked through the philtrum and chin (grey patches). They follow the skin.
    inner = key.startswith("FaceMouth")
    G = (lambda c: np.ones_like(y)) if inner else (lambda c: c.astype(float))
    y2 = y + K["nose_lift"] * bump * G(y > 0.04)
    # q36 Sammy 'the side view shows that the face features are too forward': the nose tip sat 0.20 D ahead of the
    # eye-level profile (MHS3-04 / dataset ~0.08-0.11 D) - push the nose back (narrow, tip-centred) and lift the root
    nb = K.get("nose_back", 0.0)
    if nb:
        d0, d1, d2, d3 = K.get("nose_back_d", (0.10, 0.50, 0.60, 0.72))
        gb = np.clip((d - d0) / (d1 - d0), 0, 1) * np.clip((d3 - d) / (d3 - d2), 0, 1); gb = gb * gb * (3 - 2 * gb)
        y2 = y2 - nb * gb * np.exp(-(x / K.get("nose_back_w", 0.020)) ** 2) * G(y > 0.03)
    nu = K.get("nose_tip_up", 0.0)
    if nu:
        # q38 (TypeSafe vs Leo / face_profile_04: nose_tip_sharp 0.71-0.83 in 3/4 and side, nose reads long): lift the
        # lower nose (tip and base, d 0.38-0.62 below the pupils) up and slightly back - a shorter, softer, a touch
        # upturned MHS3 nose; the cheeks and lip stay (narrow x and depth gates)
        t0, t1, t2, t3 = K.get("nose_tip_d", (0.30, 0.44, 0.56, 0.68))
        gt = np.clip((d - t0) / (t1 - t0), 0, 1) * np.clip((t3 - d) / (t3 - t2), 0, 1); gt = gt * gt * (3 - 2 * gt)
        wx = np.exp(-(x / K.get("nose_tip_w", 0.018)) ** 2) * G(y > 0.035)
        z2 = z2 + nu * gt * wx
        y2 = y2 - K.get("nose_tip_back", 0.0) * gt * wx
    rl = K.get("root_lift", 0.0)
    if rl:
        r0, r1, r2, r3 = K.get("root_d", (-0.30, -0.05, 0.20, 0.45))
        gr = np.clip((d - r0) / (r1 - r0), 0, 1) * np.clip((r3 - d) / (r3 - r2), 0, 1); gr = gr * gr * (3 - 2 * gr)
        y2 = y2 + rl * gr * np.exp(-(x / K.get("root_w", 0.012)) ** 2) * G(y > 0.03)
    lf = K.get("lowface_fwd", None)
    if lf:
        lt = np.array(lf, float); g3 = pchip(lt[:, 0], lt[:, 1])
        inr = (d >= lt[0, 0]) & (d <= lt[-1, 0])
        y2 = y2 + np.where(inr, g3(np.clip(d, lt[0, 0], lt[-1, 0])), 0.0) * np.exp(-(x / (0.9 * u)) ** 2) * G(y > 0.0)
    # q34: a stronger chin in profile (MHS3 adult chin projects; VRoid's recedes)
    cz = np.clip((d - 1.05) / 0.15, 0, 1) * np.clip((1.55 - d) / 0.2, 0, 1)
    y2 = y2 + K.get("chin_fwd", 0.0045) * cz * np.exp(-(x / (0.5 * u)) ** 2) * G(y > 0.0)
    if key.startswith("FaceBrow"):
        z2 = z2 + K["brow_dz"]
    if key.startswith(("EyeWhite", "EyeIris", "EyeHighlight", "FaceEyeline")) and K["eye_sz"] != 1.0:
        zc = z0 - 0.0005
        # q36 R-lash_gap: the lash floated 1 mm above the opening when the eye parts were scaled more than the lid hole
        sz = K.get("eyeline_sz", K["eye_sz"]) if key.startswith("FaceEyeline") else K["eye_sz"]
        z2 = zc + (z2 - zc) * sz
        if key.startswith("FaceEyeline"):                  # q36 E1: the lid's inner skin showed under the lash
            z2 = z2 + K.get("eyeline_dz", 0.0) * (z2 > zc)
    if key.startswith("EyeIris") and K.get("iris_concave", 0.0):
        # q38 (Sammy: "in the mhs3 game the iris is a bit concave, just like real eyes"): dish each iris - the centre
        # set back by iris_concave (m), falling off as 1 - r^2 to 0 at the iris edge (elliptic radius from the iris'
        # own extent). The highlight mesh stays on the surface, so it floats in front of the iris (cornea) and the
        # iris shifts toward the viewer in turned views. The eye white has a hole behind the iris, nothing occludes.
        for sgn in (1, -1):
            m = (x2 * sgn) > 0
            if not m.any():
                continue
            cx, cz = x2[m].mean(), z2[m].mean()
            ax = max(np.abs(x2[m] - cx).max(), 1e-6); az = max(np.abs(z2[m] - cz).max(), 1e-6)
            rn = np.clip(np.hypot((x2 - cx) / ax, (z2 - cz) / az), 0, 1)
            y2 = np.where(m, y2 - K["iris_concave"] * (1 - rn ** 2), y2)
    return np.stack([x2, y2, z2], 1)


def _world(o):
    mw = np.array(o.matrix_world); co = np.array([v.co[:] for v in o.data.vertices])
    return (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3], mw


def seat_brows(lift=0.0007):
    """m7: brows lowered 12 mm sank under the brow ridge (only a sliver showed). Put each brow vertex on the warped
    face surface (front projection, max y of the face triangles under it) + lift."""
    objs = {o.data.materials[0].name.split("_Instance")[0]: o for o in bpy.context.scene.objects
            if o.type == "MESH" and o.data.materials}
    face = next(o for k, o in objs.items() if k.endswith("Face_00_SKIN"))
    brow = next(o for k, o in objs.items() if k.endswith("FaceBrow_00_FACE"))
    FV, _ = _world(face); face.data.calc_loop_triangles()
    T = np.array([t.vertices[:] for t in face.data.loop_triangles])
    A, B, C = FV[T[:, 0]], FV[T[:, 1]], FV[T[:, 2]]
    BV, mw = _world(brow)
    for i, p in enumerate(BV):
        # barycentric in the x-z plane
        v0, v1 = B - A, C - A; v2 = np.array([p[0], 0, p[2]]) - A
        d00 = v0[:, 0] ** 2 + v0[:, 2] ** 2; d01 = v0[:, 0] * v1[:, 0] + v0[:, 2] * v1[:, 2]; d11 = v1[:, 0] ** 2 + v1[:, 2] ** 2
        d20 = v2[:, 0] * v0[:, 0] + v2[:, 2] * v0[:, 2]; d21 = v2[:, 0] * v1[:, 0] + v2[:, 2] * v1[:, 2]
        den = d00 * d11 - d01 ** 2; den[np.abs(den) < 1e-14] = np.nan
        v = (d11 * d20 - d01 * d21) / den; w = (d00 * d21 - d01 * d20) / den; u = 1 - v - w
        hit = (u >= 0) & (v >= 0) & (w >= 0)
        if hit.any():
            y = (u * A[:, 1] + v * B[:, 1] + w * C[:, 1])[hit].max()
            BV[i, 1] = max(BV[i, 1], y + lift)
    L = (np.c_[BV, np.ones(len(BV))] @ np.linalg.inv(mw).T)[:, :3]
    brow.data.vertices.foreach_set("co", L.astype(np.float32).ravel()); brow.data.update()
    print("brows seated")


def smooth_parts(keys, levels=1):
    """q38 (Sammy: "the shapes and lines are not smooth like in the mhs3 model ... smooth those edges"): VRoid's face,
    eye and mouth meshes are low-poly, so the silhouette, the toon terminator and the outline (a shell of the same
    polygons) show every facet - the jaw line, lid lines, eye-white edge, nose tip. Catmull-Clark subdivision applied
    to the mesh data (UVs smoothed with boundaries kept, open edges' corners kept, vertex groups interpolated) before
    export. keys: material keys that contain any of these strings, e.g. ["Face_00_SKIN", "EyeWhite", ...]."""
    if not keys:
        return
    if K.get("smooth_skip_ears", True):
        # q38c: the ears are four loose islands of the face mesh; smoothed they read wrong (ears / ear_shape lost 3/3
        # in the side, 70-degree and profile views) - split them off so only the face itself is subdivided
        for o in list(bpy.context.scene.objects):
            if o.type == "MESH" and o.data.materials and o.data.materials[0] and "Face_00_SKIN" in o.data.materials[0].name:
                bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
                bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
                bpy.ops.mesh.separate(type="LOOSE"); bpy.ops.object.mode_set(mode="OBJECT")
    min_v = K.get("smooth_min_verts", 400)
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH" or not o.data.materials or not o.data.materials[0]:
            continue
        if not any(k in o.data.materials[0].name for k in keys):
            continue
        n0 = len(o.data.vertices)
        if "Face_00_SKIN" in o.data.materials[0].name and n0 < min_v:
            continue                                                # an ear island
        ang = K.get("smooth_crease_deg", 0.0)
        if ang:
            # q38b: plain subdivision rounded the profile's small sharp features (lip notch, nostril, nose tip) and
            # the profile close-up lost 3/3 to m58b - keep edges whose faces meet at more than `ang` degrees sharp
            import bmesh, math
            bm = bmesh.new(); bm.from_mesh(o.data)
            cl = bm.edges.layers.float.get("crease_edge") or bm.edges.layers.float.new("crease_edge")
            nc = 0
            for e in bm.edges:
                if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(ang):
                    e[cl] = K.get("smooth_crease", 0.8); nc += 1
            bm.to_mesh(o.data); bm.free(); o.data.update()
            print("  creased", nc, "edges >", ang, "deg")
        mode = K.get("smooth_mode", "cc")
        stack = []
        md = o.modifiers.new("q38_smooth", "SUBSURF")
        md.levels = md.render_levels = levels
        md.uv_smooth = "PRESERVE_BOUNDARIES"; md.boundary_smooth = "PRESERVE_CORNERS"
        if mode == "laplace":
            # q38d: Catmull-Clark shrinks the surface away from its open borders - the head pulled off the ears
            # (a doubled ear edge; ears / ear_shape lost in the turned views) and the lips / nose tip rounded off.
            # Simple subdivision (shape unchanged) + volume-preserving Laplacian smoothing with the borders pinned:
            # the facets round off, the volume stays, every seam (ears, neck, eye holes) stays where it was.
            md.subdivision_type = "SIMPLE"
            lp = o.modifiers.new("q38_lap", "LAPLACIANSMOOTH")
            lp.iterations = K.get("lap_iter", 4); lp.lambda_factor = K.get("lap_lambda", 0.6); lp.lambda_border = 0.0
            lp.use_volume_preserve = True; lp.use_normalized = True
            if "Face_00_SKIN" in o.data.materials[0].name and K.get("smooth_keep_profile", True):
                # q38e: smoothing the midline (nose, philtrum, lips, chin) rounded the profile - the profile close-up
                # and the side view were lost 3/3 to m58b with any face smoothing, won 2/3 without. Weight the
                # smoothing to zero along the front midline below the brows.
                Mw = np.array(o.matrix_world); co = np.array([v.co[:] for v in o.data.vertices])
                W = (np.c_[co, np.ones(len(co))] @ Mw.T)[:, :3]
                mid = np.exp(-(W[:, 0] / K.get("profile_keep_w", 0.016)) ** 2) * (W[:, 1] > 0.02) * \
                    (W[:, 2] < K["z0"] - 0.005) * (W[:, 2] > K["z0"] - 0.14)
                vg = o.vertex_groups.new(name="q38_smooth_w")
                for i, w in enumerate(1.0 - mid):
                    vg.add([i], float(w), "REPLACE")
                lp.vertex_group = vg.name
            stack.append(lp)
        for mm in [md] + stack:
            while o.modifiers[[m_.name for m_ in o.modifiers].index(mm.name) - 1].type == "ARMATURE" if \
                    [m_.name for m_ in o.modifiers].index(mm.name) > 0 else False:
                with bpy.context.temp_override(object=o, active_object=o):
                    bpy.ops.object.modifier_move_up(modifier=mm.name)
        for mm in [md] + stack:                                     # apply on the rest shape (before the armature)
            while o.modifiers[0].name != mm.name:
                with bpy.context.temp_override(object=o, active_object=o):
                    bpy.ops.object.modifier_move_up(modifier=mm.name)
            with bpy.context.temp_override(object=o, active_object=o):
                bpy.ops.object.modifier_apply(modifier=mm.name)
        if o.vertex_groups.get("q38_smooth_w"):
            o.vertex_groups.remove(o.vertex_groups["q38_smooth_w"])
        for p in o.data.polygons:
            p.use_smooth = True
        print("smoothed", o.data.materials[0].name.split("_Instance")[0], n0, "->", len(o.data.vertices))
    # join the face islands back into one object (vroid_toon, the measure scripts and the creator expect one face mesh)
    faces = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
             and "Face_00_SKIN" in o.data.materials[0].name]
    if len(faces) > 1:
        main = max(faces, key=lambda o: len(o.data.vertices))
        bpy.ops.object.select_all(action="DESELECT")
        for o in faces:
            o.select_set(True)
        bpy.context.view_layer.objects.active = main
        bpy.ops.object.join()
        print("face islands joined:", len(main.data.vertices), "verts")


def main():
    src, texd, out = sys.argv[1:4]
    if "--knobs" in sys.argv:
        K.update(json.load(open(sys.argv[sys.argv.index("--knobs") + 1])))
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    bpy.ops.import_scene.gltf(filepath=src)
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or not o.data.materials:
            continue
        m = o.data.materials[0]
        key = m.name.split("_Instance")[0].replace("N00_000_00_", "").replace("N00_000_", "")
        mw = np.array(o.matrix_world); inv = np.linalg.inv(mw)
        co = np.array([v.co[:] for v in o.data.vertices]); W = (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3]
        W2 = warp(W, key)
        L = (np.c_[W2, np.ones(len(W2))] @ inv.T)[:, :3]
        o.data.vertices.foreach_set("co", L.astype(np.float32).ravel())
        if o.data.shape_keys:
            print("note: shape keys on", key, "not warped")
        tp = os.path.join(texd, m.name.split("_Instance")[0] + ".png")
        if os.path.exists(tp):
            img = bpy.data.images.load(tp); img.pack()
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE":
                    n.image = img
            print("texture", key)
        o.data.update()
    seat_brows()
    smooth_parts(K.get("smooth", []), K.get("smooth_levels", 1))
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_image_format="AUTO")
    print("wrote", out)


if __name__ == "__main__":
    main()
