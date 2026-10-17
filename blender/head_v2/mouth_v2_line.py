"""Face layout shared by sdf_head / face_paint_v2 (system python) and mouth_v2 (bpy).

Leo (MHST3-Leo_Render_001), measured on rows clear of the hair: in D = pupil line to chin, the face is 0.97 D wide at
the mouth, 0.69 D at 0.8 D, 0.54 D at 0.9 D, the chin 0.32 D at 0.97 D. With the dataset skull widths that puts the
pupil line at h = 0.445 (D = 0.555 H): eyes a bit higher on the skull than half, a longer lower face.
"""
import numpy as np
EYE_H = 0.445
D = 1.0 - EYE_H
MY = EYE_H + 0.64 * D          # mouth line
MW = 0.49 * D / 2              # mouth half width
NB = EYE_H + 0.49 * D          # nose bottom
CURVE = 0.006


def line(x):
    u = np.clip(np.abs(x) / MW, 0, 1)
    return MY - CURVE * u ** 2
