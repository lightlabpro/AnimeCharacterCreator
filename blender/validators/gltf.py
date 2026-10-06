"""Read a .gltf/.glb export into a SceneInfo, with no Blender and no third-party packages.

glTF is Y-up, +Z forward; Blender's exporter maps Blender (x, y, z) to glTF (x, z, -y), so
we invert that: blender = (gx, -gz, gy).
"""
from __future__ import annotations

import base64
import json
import math
import os
import struct
from typing import Dict, List, Optional, Tuple

from .model import SceneInfo, Vec

_COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def load(path: str) -> Tuple[dict, List[bytes]]:
    with open(path, "rb") as fh:
        data = fh.read()
    base = os.path.dirname(path)
    if data[:4] == b"glTF":
        _, _, total = struct.unpack_from("<4sII", data, 0)
        off, js, binchunk = 12, None, b""
        while off < total:
            ln, ty = struct.unpack_from("<II", data, off)
            chunk = data[off + 8: off + 8 + ln]
            if ty == 0x4E4F534A:
                js = json.loads(chunk.decode("utf-8"))
            elif ty == 0x004E4942:
                binchunk = chunk
            off += 8 + ln
        return js or {}, [binchunk]
    doc = json.loads(data.decode("utf-8"))
    bufs = []
    for b in doc.get("buffers", []):
        uri = b.get("uri", "")
        if uri.startswith("data:"):
            bufs.append(base64.b64decode(uri.split(",", 1)[1]))
        elif uri:
            with open(os.path.join(base, uri), "rb") as fh:
                bufs.append(fh.read())
        else:
            bufs.append(b"")
    return doc, bufs


def _read_accessor(doc: dict, bufs: List[bytes], idx: int) -> List[tuple]:
    acc = doc["accessors"][idx]
    bv = doc["bufferViews"][acc["bufferView"]]
    fmt, size = _COMP[acc["componentType"]]
    n = _NCOMP[acc["type"]]
    stride = bv.get("byteStride") or size * n
    base = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    buf = bufs[bv["buffer"]]
    return [struct.unpack_from("<" + fmt * n, buf, base + i * stride) for i in range(acc["count"])]


def _mat(node: dict) -> List[float]:
    """Column-major 4x4."""
    if "matrix" in node:
        return list(node["matrix"])
    t = node.get("translation", [0, 0, 0])
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    s = node.get("scale", [1, 1, 1])
    r = [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w),
         2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w),
         2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)]
    return [r[0] * s[0], r[1] * s[0], r[2] * s[0], 0, r[3] * s[1], r[4] * s[1], r[5] * s[1], 0,
            r[6] * s[2], r[7] * s[2], r[8] * s[2], 0, t[0], t[1], t[2], 1]


def _mul(a: List[float], b: List[float]) -> List[float]:
    return [sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4)) for c in range(4) for r in range(4)]


def _to_blender(p) -> Vec:
    return (p[0], -p[2], p[1])


def scene_from_gltf(path: str, kind: str) -> SceneInfo:
    doc, bufs = load(path)
    nodes = doc.get("nodes", [])
    parent: Dict[int, int] = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    world: Dict[int, List[float]] = {}

    def w(i: int) -> List[float]:
        if i not in world:
            m = _mat(nodes[i])
            world[i] = _mul(w(parent[i]), m) if i in parent else m
        return world[i]

    pos = {i: _to_blender(w(i)[12:15]) for i in range(len(nodes))}
    info = SceneInfo(kind=kind, source=path)
    joints = {j for s in doc.get("skins", []) for j in s.get("joints", [])}
    for i, n in enumerate(nodes):
        name = n.get("name", f"node{i}")
        info.objects.add(name)
        if name.startswith("LM-"):
            info.markers[name] = pos[i]
        if i in joints:
            kids = [pos[c] for c in n.get("children", []) if c in joints]
            tail = tuple(sum(k[a] for k in kids) / len(kids) for a in range(3)) if kids else pos[i]
            info.bones[name] = (pos[i], tail)
            info.deform_bones.add(name)
        extras = n.get("extras") or {}
        if "socket_name" in extras:
            info.custom_props[name] = {"socket_name": extras["socket_name"]}
    for n in nodes:
        if "mesh" not in n:
            continue
        mesh = doc["meshes"][n["mesh"]]
        name = n.get("name") or mesh.get("name", "")
        targets = (mesh.get("extras") or {}).get("targetNames")
        if targets is None:
            for prim in mesh.get("primitives", []):
                targets = (prim.get("extras") or {}).get("targetNames") or targets
        if targets is not None:
            info.shape_keys[name] = ["Basis"] + list(targets)
        tris = 0
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4:
                continue
            if "indices" in prim:
                tris += doc["accessors"][prim["indices"]]["count"] // 3
            else:
                tris += doc["accessors"][prim["attributes"]["POSITION"]]["count"] // 3
        info.tris[name] = tris
        info.transforms[name] = {"scale": tuple(n.get("scale", (1, 1, 1))), "rotation": (0.0, 0.0, 0.0),
                                 "location": tuple(n.get("translation", (0, 0, 0)))}
    # Body vertices (world space) for the head/neck measurements.
    body_name = {"adult": "CHR_Body", "child": "CHR_Body_Child", "robot": "CHR_Body_Robot", "dragon": "CHR_Body_Dragon"}[kind]
    for i, n in enumerate(nodes):
        if (n.get("name") == body_name or doc["meshes"][n["mesh"]].get("name") == body_name) if "mesh" in n else False:
            m = w(i)
            verts: List[Vec] = []
            for prim in doc["meshes"][n["mesh"]]["primitives"]:
                for p in _read_accessor(doc, bufs, prim["attributes"]["POSITION"]):
                    gx = m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12]
                    gy = m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13]
                    gz = m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14]
                    verts.append(_to_blender((gx, gy, gz)))
            info.body_verts = verts
            break
    return info
