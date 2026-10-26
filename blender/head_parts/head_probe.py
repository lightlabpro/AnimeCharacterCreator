"""q41c head probes (run in Blender; exec this file, then call). World space: +Z up, front = -Y.

measure(name, pupil_z=None) - rulebook profile on the midline: P1-P6 (behind the nose tip at 0.3..0.9 H, H = skull
    top -> chin bottom), and with pupil_z also P7 lower lip / P8 chin (behind the tip, in D = pupil line -> chin)
    and F3 (nose tip below the pupil line, in D). Chin bottom = the profile jump to the neck.
nose(name, L=0.096) - nose rules N1 (points down, deg; MHS3 +9) and N2 (tip angle, deg; MHS3 108), windows 0.11-0.37
    of the nose length above and below the tip (references/nose_rules.json).
"""
import math

import numpy as np


def _world(name):
    import bpy
    o = bpy.data.objects[name]
    co = np.empty(len(o.data.vertices) * 3); o.data.vertices.foreach_get("co", co); W = co.reshape(-1, 3)
    M = np.array(o.matrix_world)
    return W @ M[:3, :3].T + M[:3, 3]


def profile(W, step=0.005, half=0.003, xw=0.006):
    mid = W[(np.abs(W[:, 0]) < xw) & (W[:, 1] < 0)]
    P = []
    for z in np.arange(W[:, 2].min(), W[:, 2].max(), step):
        s = mid[np.abs(mid[:, 2] - z) < half]
        if len(s):
            P.append((z, s[:, 1].min()))
    return np.array(P)


def measure(name, pupil_z=None):
    W = _world(name)
    P = profile(W); zs, ys = P[:, 0], P[:, 1]
    k = [i for i in range(1, len(zs)) if ys[i] - ys[i - 1] < -0.05][0]
    chin = zs[k]; top = W[:, 2].max(); H = top - chin
    t = int(np.argmin(ys)); tip = (zs[t], ys[t])
    at = lambda z: float(np.interp(z, zs[k:], ys[k:]))
    out = {"chin": round(float(chin), 3), "top": round(float(top), 3), "tip": (round(float(tip[0]), 3), round(float(tip[1]), 3)),
           "P": {f: round((at(top - f * H) - tip[1]) / H, 3) for f in (0.3, 0.4, 0.5, 0.6, 0.8, 0.9)}}
    if pupil_z:
        D = pupil_z - chin
        out.update({"P7": round((at(pupil_z - 0.68 * D) - tip[1]) / D, 3),
                    "P8": round((at(pupil_z - 0.90 * D) - tip[1]) / D, 3),
                    "F3": round((pupil_z - tip[0]) / D, 3)})
    return out


def nose(name, L=0.096):
    W = _world(name)
    P = profile(W, 0.003, 0.004)
    tip = P[np.argmin(P[:, 1])]

    def unit(sel):
        q = P[sel]; v = np.array([q[:, 1].mean() - tip[1], q[:, 0].mean() - tip[0]]); return v / np.linalg.norm(v)
    uu = unit((P[:, 0] > tip[0] + 0.11 * L) & (P[:, 0] < tip[0] + 0.37 * L))
    ud = unit((P[:, 0] < tip[0] - 0.11 * L) & (P[:, 0] > tip[0] - 0.37 * L))
    m = -(uu + ud)
    return {"N1_down_deg": round(math.degrees(math.atan2(-m[1], -m[0])), 1),
            "N2_tip_deg": round(math.degrees(math.acos(np.clip(np.dot(uu, ud), -1, 1))), 1)}
