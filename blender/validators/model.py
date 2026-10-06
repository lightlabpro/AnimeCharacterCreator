"""Shared result types and the scene snapshot every check reads.

The snapshot is plain data so the same checks run on a live Blender scene
(bpy_adapter), a glTF/GLB export (gltf), or a unit-test fixture.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Set, Tuple

Vec = Tuple[float, float, float]

PASS, WARN, FAIL, SKIP, INFO = "pass", "warn", "fail", "skip", "info"


@dataclass
class Finding:
    check: str
    severity: str
    message: str
    value: Optional[float] = None
    expected: str = ""
    fix: str = ""
    source: str = ""

    def line(self) -> str:
        v = "" if self.value is None else f" = {self.value:.3f}"
        exp = f" (target {self.expected})" if self.expected else ""
        fix = f"  -> {self.fix}" if self.fix and self.severity in (WARN, FAIL) else ""
        return f"[{self.severity.upper():4}] {self.check}{v}{exp}: {self.message}{fix}"


@dataclass
class Report:
    kind: str
    tag: str = ""
    findings: List[Finding] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    extra: Dict[str, object] = field(default_factory=dict)

    def add(self, *items: Finding) -> None:
        self.findings.extend(items)

    def count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    @property
    def ok(self) -> bool:
        return self.count(FAIL) == 0

    def worst_first(self) -> List[Finding]:
        order = {FAIL: 0, WARN: 1, SKIP: 2, INFO: 3, PASS: 4}
        return sorted(self.findings, key=lambda f: order.get(f.severity, 9))

    def summary(self) -> str:
        c = {s: self.count(s) for s in (FAIL, WARN, SKIP, PASS)}
        head = "PASS" if self.ok else "FAIL"
        return f"{head}  {self.kind} {self.tag}: {c[FAIL]} fail, {c[WARN]} warn, {c[SKIP]} skipped, {c[PASS]} pass"

    def to_text(self) -> str:
        return "\n".join([self.summary()] + [f.line() for f in self.worst_first() if f.severity != PASS])

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "tag": self.tag,
            "ok": self.ok,
            "metrics": self.metrics,
            "findings": [asdict(f) for f in self.findings],
            "extra": self.extra,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


@dataclass
class SceneInfo:
    """Everything the validators need, in Blender space: Z up, forward -Y, metres."""

    kind: str = "adult"  # adult | child | robot | dragon
    source: str = ""
    objects: Set[str] = field(default_factory=set)
    # DEF-/SOC- bones: name -> (head, tail)
    bones: Dict[str, Tuple[Vec, Vec]] = field(default_factory=dict)
    deform_bones: Set[str] = field(default_factory=set)
    # Validator-owned landmark markers (empties named LM-*) and any bone-derived ones.
    markers: Dict[str, Vec] = field(default_factory=dict)
    shape_keys: Dict[str, List[str]] = field(default_factory=dict)  # object -> key names
    tris: Dict[str, int] = field(default_factory=dict)
    # object -> {"scale": Vec, "rotation": Vec, "location": Vec}; Blender object transforms
    transforms: Dict[str, Dict[str, Vec]] = field(default_factory=dict)
    custom_props: Dict[str, Dict[str, object]] = field(default_factory=dict)
    body_verts: Optional[Sequence[Vec]] = None
    quad_ratio: Dict[str, float] = field(default_factory=dict)

    def flip_forward(self) -> None:
        """Reference models that face +Y: mirror Y so every check can assume the library's -Y forward."""
        f = lambda v: (v[0], -v[1], v[2])
        self.markers = {k: f(v) for k, v in self.markers.items()}
        self.bones = {k: (f(h), f(t)) for k, (h, t) in self.bones.items()}
        if self.body_verts is not None:
            self.body_verts = [f(v) for v in self.body_verts]

    def socket_names(self) -> Set[str]:
        return {n for n in self.objects | set(self.bones) if n.startswith("SOC-")}
