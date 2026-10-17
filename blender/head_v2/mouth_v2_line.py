"""Mouth line shared by face_paint_v2 (system python) and mouth_v2 (bpy): same numbers as mouth_v2.line_h."""
import numpy as np
EYE_H = 0.50
D = 1.0 - EYE_H
MY = EYE_H + 0.64 * D
MW = 0.49 * D / 2
CURVE = 0.006


def line(x):
    u = np.clip(np.abs(x) / MW, 0, 1)
    return MY - CURVE * u ** 2
