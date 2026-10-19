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
    if key.startswith("FaceEyeline") and K.get("eyeline_fwd", 0.0):
        # q38f: with the eye-hole rim brought forward (no pink rim band) the skin edge hid the lash mesh - lash forward
        y2 = y2 + K["eyeline_fwd"]
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


def _apply_subsurf(o, kind="CATMULL_CLARK", levels=1, uv_smooth="PRESERVE_BOUNDARIES"):
    md = o.modifiers.new("q38_tmp", "SUBSURF"); md.levels = md.render_levels = levels; md.subdivision_type = kind
    md.uv_smooth = uv_smooth; md.boundary_smooth = "PRESERVE_CORNERS"
    while o.modifiers[0].name != md.name:
        with bpy.context.temp_override(object=o, active_object=o):
            bpy.ops.object.modifier_move_up(modifier=md.name)
    with bpy.context.temp_override(object=o, active_object=o):
        bpy.ops.object.modifier_apply(modifier=md.name)


def smooth_eye_borders(levels=1):
    """q38f (Sammy: "the eyes still look distorted around the borders"): the eye holes of the face skin are a coarse
    polygon - the lid edges, the skin rim showing between lash and white and the outlines along them are faceted.
    Whole-face subdivision lost the profile views (q38), so subdivide the face with Catmull-Clark AND with 'simple'
    (same topology, shape unchanged) and keep the smooth result only round the eyes: an ellipse round each eye
    (K eye_smooth_r, metres) fading to the unchanged shape - ears, nose, mouth and the profile stay as they were."""
    face = next((o for o in bpy.context.scene.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
                 and "Face_00_SKIN" in o.data.materials[0].name), None)
    iris = next((o for o in bpy.context.scene.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
                 and "EyeIris" in o.data.materials[0].name), None)
    if face is None or iris is None:
        return
    # the ears are loose islands of the face mesh; subdividing them (even with 'simple') changed their border
    # normals and the outline drew a ragged pale edge in front of each ear (ears / ear_shape lost 3/3 in the profile
    # views) - split them off, subdivide only the face itself, join back
    bpy.ops.object.select_all(action="DESELECT"); face.select_set(True); bpy.context.view_layer.objects.active = face
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE"); bpy.ops.object.mode_set(mode="OBJECT")
    parts = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
             and "Face_00_SKIN" in o.data.materials[0].name]
    face = max(parts, key=lambda o: len(o.data.vertices))
    Mi = np.array(iris.matrix_world); I = (np.c_[np.array([v.co[:] for v in iris.data.vertices]), np.ones(len(iris.data.vertices))] @ Mi.T)[:, :3]
    cents = [I[I[:, 0] > 0].mean(0), I[I[:, 0] < 0].mean(0)]
    rest = None
    if K.get("eye_smooth_local", True):
        # q38h: even with the shape, UVs and normals kept, subdividing the whole face changed the strip in front of
        # the ear and TypeSafe still saw it (side 'overall' lost 3/3 with < 900 px changed). Cut out only the faces
        # round the eyes, subdivide those, split the matching seam edges of the rest so there are no T-junctions,
        # join and weld - every polygon away from the eyes stays exactly as it was.
        import bmesh
        rx_, rz_ = K.get("eye_smooth_r", (0.030, 0.020)); lim = 1 + K.get("eye_smooth_fall", 0.6) + K.get("eye_smooth_margin", 0.3)
        Mf0 = np.array(face.matrix_world); V0 = np.array([v.co[:] for v in face.data.vertices])
        W0 = (np.c_[V0, np.ones(len(V0))] @ Mf0.T)[:, :3]
        rr = np.full(len(W0), 99.0)
        for c in cents:
            rr = np.minimum(rr, np.hypot((W0[:, 0] - c[0]) / rx_, (W0[:, 2] - c[2]) / rz_) + 99.0 * (W0[:, 1] <= c[1] - 0.03))
        inside = rr < lim
        full_orig = bpy.data.objects.new("q38_full_orig", face.data.copy()); bpy.context.scene.collection.objects.link(full_orig)
        full_orig.matrix_world = face.matrix_world
        if not inside.any():
            print("eye-border smoothing skipped: no faces round the eyes"); return
        for p_ in face.data.polygons:
            p_.select = bool(inside[list(p_.vertices)].any())
        for v_ in face.data.vertices:
            v_.select = False
        for e_ in face.data.edges:
            e_.select = False
        bpy.ops.object.select_all(action="DESELECT"); face.select_set(True); bpy.context.view_layer.objects.active = face
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_mode(type="FACE")
        bpy.ops.mesh.separate(type="SELECTED"); bpy.ops.object.mode_set(mode="OBJECT")
        eye_o = next(o for o in bpy.context.selected_objects if o is not face)
        rest = face; face = eye_o
        # seam = boundary vertices of the eye part that also lie on the rest's boundary
        def bnd_co(o):
            bm_ = bmesh.new(); bm_.from_mesh(o.data)
            out_ = {tuple(np.round(v.co[:], 6)) for e in bm_.edges if e.is_boundary for v in e.verts}
            bm_.free(); return out_
        seam = bnd_co(face) & bnd_co(rest)
        bm_ = bmesh.new(); bm_.from_mesh(rest.data)
        es = [e for e in bm_.edges if e.is_boundary and all(tuple(np.round(v.co[:], 6)) in seam for v in e.verts)]
        if K.get("eye_seam_split_rest", True):
            r_ = bmesh.ops.subdivide_edges(bm_, edges=es, cuts=1, use_grid_fill=False, use_single_edge=True)
            ng = [f for f in bm_.faces if len(f.verts) > 4]
            bmesh.ops.triangulate(bm_, faces=ng, quad_method="BEAUTY", ngon_method="BEAUTY")
        seam4 = {tuple(np.round(v.co[:], 4)) for e in bm_.edges if e.is_boundary for v in e.verts
                 if any(tuple(np.round(w.co[:], 6)) in seam for w in [v])} | {tuple(np.round(np.array(c), 4)) for c in seam}
        for e in bm_.edges:
            if e.is_boundary and sum(tuple(np.round(w.co[:], 6)) in seam for w in e.verts) >= 1:
                for w in e.verts:
                    nb = [x for x in w.link_edges if x.is_boundary]
                    if all(any(tuple(np.round(u.co[:], 6)) in seam for u in x.verts) for x in nb):
                        seam4.add(tuple(np.round(w.co[:], 4)))
        bm_.to_mesh(rest.data); bm_.free(); rest.data.update()
        print("  local eye smoothing:", len(face.data.polygons), "faces cut out,", len(es), "seam edges split")
    tmp = bpy.data.objects.new("q38_simple", face.data.copy()); bpy.context.scene.collection.objects.link(tmp)
    tmp.matrix_world = face.matrix_world
    # the VRoid face carries custom (split) normals that the toon shading and the outline shell use; subdivision
    # drops them, which changed the outline and terminator all over the profile even with the shape unchanged
    # (m62f vs m62g pixel diff). Keep an untouched copy to transfer them back outside the eye regions.
    orig = bpy.data.objects.new("q38_orig", face.data.copy()); bpy.context.scene.collection.objects.link(orig)
    orig.matrix_world = face.matrix_world
    n0 = len(face.data.vertices)
    _apply_subsurf(face, "CATMULL_CLARK", levels); _apply_subsurf(tmp, "SIMPLE", levels, uv_smooth="NONE")
    if len(tmp.data.vertices) != len(face.data.vertices):
        print("eye-border smoothing skipped: topology differs"); bpy.data.objects.remove(tmp); bpy.data.objects.remove(orig); return
    cc = np.array([v.co[:] for v in face.data.vertices]); sp = np.array([v.co[:] for v in tmp.data.vertices])
    Mf = np.array(face.matrix_world); W = (np.c_[sp, np.ones(len(sp))] @ Mf.T)[:, :3]
    rx, rz = K.get("eye_smooth_r", (0.030, 0.020)); fall = K.get("eye_smooth_fall", 0.6)
    m = np.zeros(len(W))
    for c in cents:
        # q38g bug fix: this used to MULTIPLY r by the in-front test, so every vertex more than 3 cm behind the eye
        # got r = 0 = full Catmull-Clark - the sides of the head in front of the ears were smoothed (the ragged
        # strip in front of the ear changed; 'clean' lost in side / 70 / profile)
        r = np.hypot((W[:, 0] - c[0]) / rx, (W[:, 2] - c[2]) / rz) + 99.0 * (W[:, 1] <= c[1] - 0.03)
        w = np.clip((1 + fall - r) / fall, 0, 1); m = np.maximum(m, w * w * (3 - 2 * w))
    out = sp + (cc - sp) * m[:, None]
    rb = K.get("eye_rim_back", 0.0)
    if rb:
        # the hole's inner rim (the skin's thickness round the eye) showed as a pink band with stray texture between
        # lash and white (worse after rounding the hole): tuck the hole's border loop and the ring next to it back
        # behind the eye white, so the visible lid edge is the skin's front surface (anime lids have no thickness)
        import bmesh
        bm = bmesh.new(); bm.from_mesh(face.data); bm.verts.ensure_lookup_table()
        bnd = np.zeros(len(out), bool)
        for e in bm.edges:
            if e.is_boundary:
                for v in e.verts:
                    bnd[v.index] = True
        ring = np.zeros(len(out), bool)
        for e in bm.edges:
            a_, b_ = e.verts[0].index, e.verts[1].index
            if bnd[a_] and not bnd[b_]:
                ring[b_] = True
            if bnd[b_] and not bnd[a_]:
                ring[a_] = True
        bm.free()
        Minv = np.linalg.inv(Mf)[:3, :3]
        back = (Minv @ np.array([0.0, -1.0, 0.0])); back /= np.linalg.norm(back)
        sel = m > 0.5
        out[bnd & sel] += back * rb
        out[ring & sel] += back * rb * K.get("eye_rim_ring", 0.35)
        print("  eye rim tucked back:", int((bnd & sel).sum()), "border verts")
    face.data.vertices.foreach_set("co", out.astype(np.float32).ravel()); face.data.update()
    # q38g: Catmull-Clark also smoothed the UVs of the whole face, which slid the face texture (blush, nose and
    # hairline shading) everywhere - m62h lost 'clean' in 4 views and skin_mhs3 fell. Take the UVs of the 'simple'
    # copy (linear, the original mapping) outside the eyes and blend to the smoothed UVs inside them.
    nl = len(face.data.loops)
    if len(tmp.data.loops) == nl:
        cv = np.zeros(nl, np.int32); face.data.loops.foreach_get("vertex_index", cv)
        ml = m[cv][:, None]
        for uvl in face.data.uv_layers:
            ul = tmp.data.uv_layers.get(uvl.name)
            if ul is None:
                continue
            a_ = np.zeros(nl * 2); b_ = np.zeros(nl * 2)
            uvl.data.foreach_get("uv", a_); ul.data.foreach_get("uv", b_)
            a_ = a_.reshape(-1, 2); b_ = b_.reshape(-1, 2)
            uvl.data.foreach_set("uv", (b_ + (a_ - b_) * ml).astype(np.float32).ravel())
        print("  UVs kept linear outside the eye regions")
    for p in face.data.polygons:
        p.use_smooth = True
    if K.get("eye_keep_normals", True) and orig.data.has_custom_normals:
        vg = face.vertex_groups.new(name="q38_keepn")
        keep = 1.0 - m
        for w in np.unique(np.round(keep, 2)):
            if w > 0:
                vg.add([int(i) for i in np.where(np.round(keep, 2) == w)[0]], float(w), "REPLACE")
        dt = face.modifiers.new("q38_nrm", "DATA_TRANSFER")
        dt.object = orig; dt.use_loop_data = True; dt.data_types_loops = {"CUSTOM_NORMAL"}
        dt.loop_mapping = "POLYINTERP_NEAREST"; dt.vertex_group = vg.name; dt.mix_mode = "REPLACE"; dt.mix_factor = 1.0
        bpy.ops.object.select_all(action="DESELECT"); face.select_set(True); bpy.context.view_layer.objects.active = face
        bpy.ops.object.modifier_apply(modifier=dt.name)
        face.vertex_groups.remove(face.vertex_groups["q38_keepn"])
        print("  custom normals transferred back outside the eye regions")
    bpy.data.objects.remove(tmp); bpy.data.objects.remove(orig)
    if rest is not None:
        import bmesh
        if not K.get("eye_seam_split_rest", True):
            # q38i: splitting the rest's seam edges re-triangulated its quads and the outline shell poked through
            # in short strokes along the cut (forehead, cheeks). Leave the rest untouched and instead dissolve the
            # eye part's seam midpoints (they lie on the straight original edges there, mask 0)
            bm_ = bmesh.new(); bm_.from_mesh(face.data); bm_.verts.ensure_lookup_table()
            mids = [v for v in bm_.verts if v.is_boundary and v.index < len(m) and m[v.index] < 1e-6
                    and tuple(np.round(v.co[:], 6)) not in seam and len([e for e in v.link_edges if e.is_boundary]) == 2]
            bmesh.ops.dissolve_verts(bm_, verts=mids)
            # the merged faces are concave n-gons; the exporter's fan triangulation flipped some of them and the
            # outline shell showed through as short strokes - ear-clip them here
            ng = [f for f in bm_.faces if len(f.verts) > 4]
            bmesh.ops.triangulate(bm_, faces=ng, quad_method="BEAUTY", ngon_method="EAR_CLIP")
            bm_.to_mesh(face.data); bm_.free(); face.data.update()
            print("  seam midpoints dissolved on the eye side:", len(mids))
        bpy.ops.object.select_all(action="DESELECT"); face.select_set(True); rest.select_set(True)
        bpy.context.view_layer.objects.active = rest; bpy.ops.object.join()
        bm_ = bmesh.new(); bm_.from_mesh(rest.data)
        bv = [v for v in bm_.verts if v.is_boundary]
        nv = len(bm_.verts); bmesh.ops.remove_doubles(bm_, verts=bv, dist=2e-5); nw = len(bm_.verts)
        bm_.to_mesh(rest.data); bm_.free(); rest.data.update()
        print("  seam welded:", nv - nw, "vertices merged")
        # the two sides of the seam carried different custom normals, so the glTF export split the seam vertices
        # and the outline drew short strokes along the cut (forehead, cheeks) - average the corner normals of every
        # seam vertex and set them back as one normal per vertex there
        me = rest.data
        bm_ = bmesh.new(); bm_.from_mesh(me)
        seam_v = {v.index for v in bm_.verts if tuple(np.round(v.co[:], 4)) in seam4}
        bm_.free()
        cn = np.array([c.vector[:] for c in me.corner_normals])
        cv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", cv)
        acc = {}
        for li, vi in enumerate(cv):
            if vi in seam_v:
                acc.setdefault(vi, []).append(li)
        for vi, ls in acc.items():
            n_ = cn[ls].mean(0); n_ /= max(np.linalg.norm(n_), 1e-9); cn[ls] = n_
        me.normals_split_custom_set([tuple(x) for x in cn])
        print("  seam normals unified on", len(acc), "vertices")
        # final: custom normals of the whole joined face from the untouched original, weight 1 - eye mask (the
        # per-part transfer left the seam ring off by > 5 degrees on 49 vertices -> outline strokes on the cheeks)
        if full_orig.data.has_custom_normals:
            Mj = np.array(rest.matrix_world); Vj = np.array([v.co[:] for v in me.vertices])
            Wj = (np.c_[Vj, np.ones(len(Vj))] @ Mj.T)[:, :3]
            rx2, rz2 = K.get("eye_smooth_r", (0.030, 0.020)); fall2 = K.get("eye_smooth_fall", 0.6)
            mj = np.zeros(len(Wj))
            for c in cents:
                r2 = np.hypot((Wj[:, 0] - c[0]) / rx2, (Wj[:, 2] - c[2]) / rz2) + 99.0 * (Wj[:, 1] <= c[1] - 0.03)
                w2 = np.clip((1 + fall2 - r2) / fall2, 0, 1); mj = np.maximum(mj, w2 * w2 * (3 - 2 * w2))
            keep = np.round(1.0 - mj, 2)
            vg = rest.vertex_groups.new(name="q38_keepn2")
            for w in np.unique(keep):
                if w > 0:
                    vg.add([int(i) for i in np.where(keep == w)[0]], float(w), "REPLACE")
            dt = rest.modifiers.new("q38_nrm2", "DATA_TRANSFER")
            dt.object = full_orig; dt.use_loop_data = True; dt.data_types_loops = {"CUSTOM_NORMAL"}
            dt.loop_mapping = "POLYINTERP_NEAREST"; dt.vertex_group = "q38_keepn2"; dt.mix_mode = "REPLACE"; dt.mix_factor = 1.0
            bpy.ops.object.select_all(action="DESELECT"); rest.select_set(True); bpy.context.view_layer.objects.active = rest
            bpy.ops.object.modifier_apply(modifier=dt.name)
            rest.vertex_groups.remove(rest.vertex_groups["q38_keepn2"])
            print("  custom normals of the joined face transferred from the original (1 - eye mask)")
        bpy.data.objects.remove(full_orig)
        if os.environ.get("Q38_DEBUG"):
            for uvl in me.uv_layers:
                uv = np.zeros(len(me.loops) * 2); uvl.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
                spread = [np.ptp(uv[ls], 0).max() for ls in acc.values()]
                print("   dbg uv", uvl.name, "max spread at seam", max(spread), "n>1e-4", sum(x > 1e-4 for x in spread))
            se = np.zeros(len(me.edges), bool)
            if "sharp_edge" in me.attributes:
                me.attributes["sharp_edge"].data.foreach_get("value", se)
            ev = np.zeros(len(me.edges) * 2, np.int32); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
            sv = np.array(sorted(seam_v)); ons = np.isin(ev, sv).all(1)
            print("   dbg sharp edges", se.sum(), "on seam", (se & ons).sum(), "seam edges", ons.sum())
        face = rest
    if len(parts) > 1:
        bpy.ops.object.select_all(action="DESELECT")
        for o in parts:
            o.select_set(True)
        bpy.context.view_layer.objects.active = face
        bpy.ops.object.join()
    print("eye borders smoothed: face", n0, "->", len(out), "verts,", int((m > 0.5).sum()), "in the eye regions;",
          len(parts) - 1, "ear islands left as they were")


def _taubin(co, edges, movable, bnd, iters, lam=0.5, mu=-0.53, bedge=None):
    """Taubin (lambda|mu) smoothing - rounds a polyline / surface without shrinking it. Boundary vertices are
    smoothed only along the boundary (so an outline becomes a smooth curve instead of being pulled inward).
    bedge: per edge, True for real boundary edges (a rung across a one-face-wide strip joins two boundary vertices
    but is not a boundary edge - using it zig-zagged the brows)."""
    e = np.asarray(edges)
    eb = np.asarray(bedge) if bedge is not None else (bnd[e[:, 0]] & bnd[e[:, 1]])
    use = np.where(bnd[e[:, 0]] | bnd[e[:, 1]], eb, True)          # boundary verts: boundary edges only
    a, b = e[use, 0], e[use, 1]
    for _ in range(iters):
        for f in (lam, mu):
            acc = np.zeros_like(co); cnt = np.zeros(len(co))
            np.add.at(acc, a, co[b]); np.add.at(acc, b, co[a]); np.add.at(cnt, a, 1); np.add.at(cnt, b, 1)
            ok = movable & (cnt > 0)
            co[ok] += f * (acc[ok] / cnt[ok, None] - co[ok])
    return co


def curve_smooth():
    """q38j (Sammy: "They can be smoother ... how to do smooth curves. The eyes still look bad"): the lid lines,
    the lash strip and the brows followed VRoid's coarse polygon path - every outline had kinks. Give each part
    enough vertices (simple subdivision, shape unchanged) and run Taubin smoothing with outlines smoothed along
    themselves only: the borders become smooth curves without shrinking. Parts: K curve_parts (material keys);
    the face's eye holes are smoothed along the hole loop (K curve_hole_iter) and the next ring follows."""
    import bmesh
    parts = K.get("curve_parts", [])
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH" or not o.data.materials or not o.data.materials[0]:
            continue
        mn = o.data.materials[0].name
        if not any(k in mn for k in parts):
            continue
        for _ in range(K.get("curve_sub", 1)):
            _apply_subsurf(o, "SIMPLE", 1, uv_smooth="NONE")
        # VRoid meshes are split at UV seams (duplicate vertices): smooth on the welded topology, otherwise every
        # seam counts as an outline and the two sides drift apart (the brows came out zig-zag)
        bm = bmesh.new(); bm.from_mesh(o.data)
        co_all = np.array([v.co[:] for v in bm.verts])
        _, uid, inv = np.unique(np.round(co_all, 6), axis=0, return_index=True, return_inverse=True)
        inv = inv.ravel(); nu = len(uid)
        eset = {}
        for x in bm.edges:
            a_, b_ = inv[x.verts[0].index], inv[x.verts[1].index]
            if a_ != b_:
                k_ = (min(a_, b_), max(a_, b_)); eset[k_] = eset.get(k_, 0) + len(x.link_faces)
        bm.free()
        ed = list(eset.keys())
        bnd = np.zeros(nu, bool)
        for (a_, b_), nf in eset.items():
            if nf < 2:
                bnd[a_] = bnd[b_] = True
        co = co_all[uid].copy()
        co = _taubin(co, ed, np.ones(nu, bool), bnd, K.get("curve_iter", 30), bedge=[eset[k_] < 2 for k_ in ed])
        o.data.vertices.foreach_set("co", co[inv].astype(np.float32).ravel()); o.data.update()
        for p_ in o.data.polygons:
            p_.use_smooth = True
        print("curve-smoothed", mn.split("_Instance")[0], len(co), "verts")
    hi = K.get("curve_hole_iter", 0)
    if not hi:
        return
    face = max((o for o in bpy.context.scene.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
                and "Face_00_SKIN" in o.data.materials[0].name), key=lambda o: len(o.data.vertices))
    iris = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
                and "EyeIris" in o.data.materials[0].name)
    Mi = np.array(iris.matrix_world); I = (np.c_[np.array([v.co[:] for v in iris.data.vertices]), np.ones(len(iris.data.vertices))] @ Mi.T)[:, :3]
    cents = [I[I[:, 0] > 0].mean(0), I[I[:, 0] < 0].mean(0)]
    bm = bmesh.new(); bm.from_mesh(face.data)
    bnd = np.array([v.is_boundary for v in bm.verts]); ed = [(x.verts[0].index, x.verts[1].index) for x in bm.edges]
    be = [x.is_boundary for x in bm.edges]
    co = np.array([v.co[:] for v in bm.verts]); bm.free()
    Mf = np.array(face.matrix_world); W = (np.c_[co, np.ones(len(co))] @ Mf.T)[:, :3]
    near = np.zeros(len(co), bool)
    for c in cents:
        near |= (np.hypot((W[:, 0] - c[0]) / 0.024, (W[:, 2] - c[2]) / 0.016) < 1.0) & (W[:, 1] > c[1] - 0.02)
    hole = bnd & near
    co0 = co.copy()
    co = _taubin(co, ed, hole, bnd, hi, bedge=be)
    d = co - co0
    e = np.asarray(ed)
    ring_d = np.zeros_like(co); cnt = np.zeros(len(co))          # the ring behind the hole edge follows it
    for a, b in ((0, 1), (1, 0)):
        sel = hole[e[:, a]] & ~bnd[e[:, b]]
        np.add.at(ring_d, e[sel, b], d[e[sel, a]]); np.add.at(cnt, e[sel, b], 1)
    ok = cnt > 0
    co[ok] += ring_d[ok] / cnt[ok, None] * K.get("curve_ring_follow", 0.7)
    face.data.vertices.foreach_set("co", co.astype(np.float32).ravel()); face.data.update()
    print("eye holes curve-smoothed:", int(hole.sum()), "loop verts, max move %.2f mm" % (np.abs(d).max() * 1000))


def eye_line_ribbon():
    """q38k (Sammy: "They can be smoother ... how to do smooth curves. The eyes still look bad"). MHS3 draws one
    clean, continuous dark line round each eye opening (thick on top, thin below) with the white right against it;
    ours showed the lash, then the skin rim, then the outline shell - a messy double line with beads under the eye.
    Build the line as a real curve: take each eye hole's boundary loop, resample it evenly, smooth it as a closed
    curve (Taubin, no shrinking), and sweep a ribbon along it (width varies round the eye, tapered at the corners)
    lying on the skin just in front of the hole edge, covering the rim. Unlit dark-brown material."""
    import bmesh
    from mathutils.bvhtree import BVHTree
    face = max((o for o in bpy.context.scene.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
                and "Face_00_SKIN" in o.data.materials[0].name), key=lambda o: len(o.data.vertices))
    iris = next(o for o in bpy.context.scene.objects if o.type == "MESH" and o.data.materials and o.data.materials[0]
                and "EyeIris" in o.data.materials[0].name)
    Mi = np.array(iris.matrix_world); I = (np.c_[np.array([v.co[:] for v in iris.data.vertices]), np.ones(len(iris.data.vertices))] @ Mi.T)[:, :3]
    cents = [I[I[:, 0] > 0].mean(0), I[I[:, 0] < 0].mean(0)]
    Mf = np.array(face.matrix_world)
    bm = bmesh.new(); bm.from_mesh(face.data); bm.transform(face.matrix_world)
    bm.verts.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(bm)
    W = np.array([v.co[:] for v in bm.verts])
    # boundary loops near the eyes
    bedges = [e for e in bm.edges if e.is_boundary]
    adj = {}
    for e in bedges:
        a, b = e.verts[0].index, e.verts[1].index
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    seen = set(); loops = []
    for st in adj:
        if st in seen:
            continue
        lp = [st]; seen.add(st); prev = None; cur = st
        while True:
            nx = [n for n in adj[cur] if n != prev and n not in seen]
            if not nx:
                break
            prev, cur = cur, nx[0]; lp.append(cur); seen.add(cur)
        loops.append(lp)
    verts, faces = [], []
    tw_in, tw_out = K.get("lidline_top", (0.00035, 0.00055)); bw_in, bw_out = K.get("lidline_bot", (0.00015, 0.00018))
    fwd = K.get("lidline_fwd", 0.0003)
    for c in cents:
        cand = [lp for lp in loops if len(lp) > 12 and np.hypot(*(W[lp][:, [0, 2]].mean(0) - c[[0, 2]])) < 0.012]
        if not cand:
            print("lid line: no hole loop near", np.round(c, 3)); continue
        lp = max(cand, key=len)
        P = W[lp]
        # even resampling by arc length (closed)
        Q = np.vstack([P, P[:1]]); sl = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
        N = K.get("lidline_n", 160); t = np.linspace(0, sl[-1], N, endpoint=False)
        R = np.stack([np.interp(t, sl, Q[:, k]) for k in range(3)], 1)
        ed = [(i, (i + 1) % N) for i in range(N)]
        R = _taubin(R, ed, np.ones(N, bool), np.zeros(N, bool), K.get("lidline_iter", 40))
        ctr = R.mean(0); hz = (R[:, 2].max() - R[:, 2].min()) / 2; hx = (R[:, 0].max() - R[:, 0].min()) / 2
        tan = np.roll(R, -1, 0) - np.roll(R, 1, 0)
        nrm = np.cross(tan, np.array([0.0, 1.0, 0.0])); nrm[:, 1] = 0
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
        out_dir = R - ctr; out_dir[:, 1] = 0
        nrm *= np.sign((nrm * out_dir).sum(1))[:, None]
        f = np.clip((R[:, 2] - ctr[2]) / max(hz, 1e-6), -1, 1)            # +1 top, -1 bottom
        top = np.clip((f + 0.25) / 0.75, 0, 1); top = top * top * (3 - 2 * top)
        corner = np.clip(np.abs(R[:, 0] - ctr[0]) / max(hx, 1e-6), 0, 1)
        taper = 1 - K.get("lidline_corner_taper", 0.45) * corner ** 6
        win = (bw_in + (tw_in - bw_in) * top) * taper; wout = (bw_out + (tw_out - bw_out) * top) * taper
        # the visible opening is smaller than the hole loop (the rim folds inward): find, along the inward normal,
        # where a ray from the front stops hitting skin, and start the line's inner edge just past it
        vis = np.zeros(N)
        for i in range(N):
            for d in np.arange(0.0, 0.0025, 0.00005):
                q = R[i] - nrm[i] * d
                hit = bvh.ray_cast((q[0], q[1] + 0.03, q[2]), (0.0, -1.0, 0.0), 0.06)
                if hit[0] is None or hit[0][1] < R[i][1] - 0.004:
                    vis[i] = d; break
        vis = _taubin(vis[:, None].copy(), ed, np.ones(N, bool), np.zeros(N, bool), 20)[:, 0]
        win = vis + win
        print("  lid line: visible-opening offset mm min %.2f med %.2f max %.2f" % (vis.min()*1000, np.median(vis)*1000, vis.max()*1000))
        base = len(verts)
        for i in range(N):
            pin = R[i] - nrm[i] * win[i]; pout = R[i] + nrm[i] * wout[i]
            yy = []
            for q in (pin, pout):
                hit = bvh.ray_cast((q[0], q[1] + 0.03, q[2]), (0.0, -1.0, 0.0), 0.06)
                yy.append(hit[0][1] if hit[0] is not None else R[i][1])
            yb = max(R[i][1], yy[0])
            verts.append((pin[0], yb + fwd, pin[2])); verts.append((pout[0], max(yy[1], yb) + fwd, pout[2]))
        for i in range(N):
            j = (i + 1) % N
            faces.append((base + 2 * i, base + 2 * j, base + 2 * j + 1, base + 2 * i + 1))
    bm.free()
    if not faces:
        return
    me = bpy.data.meshes.new("EyeLidLine")
    me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    for p_ in me.polygons:
        p_.use_smooth = True
    uv = me.uv_layers.new(name="UVMap")
    for l in me.loops:
        uv.data[l.index].uv = (0.5, 0.5)
    col = K.get("lidline_col", (0.24, 0.13, 0.09))
    img = bpy.data.images.new("EyeLidLine_col", 4, 4, alpha=True)
    img.pixels = (list(col) + [1.0]) * 16
    img.pack()
    mat = bpy.data.materials.new("EyeLidLine_00_FACE"); mat.use_nodes = True
    nt = mat.node_tree; bsdf = nt.nodes.get("Principled BSDF")
    tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = img
    nt.links.new(tx.outputs["Color"], bsdf.inputs["Base Color"])
    me.materials.append(mat)
    ob = bpy.data.objects.new("EyeLidLine", me); bpy.context.scene.collection.objects.link(ob)
    if face.parent is not None:
        ob.parent = face.parent; ob.matrix_parent_inverse = face.parent.matrix_world.inverted()
    print("lid line ribbons:", len(faces), "quads")


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
    if K.get("eye_border_smooth"):
        smooth_eye_borders(K.get("eye_levels", K.get("smooth_levels", 1)))
    if K.get("curve_parts") or K.get("curve_hole_iter"):
        curve_smooth()
    if K.get("lidline"):
        eye_line_ribbon()
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_image_format="AUTO")
    print("wrote", out)


if __name__ == "__main__":
    main()
