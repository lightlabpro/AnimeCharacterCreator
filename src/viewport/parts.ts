import * as THREE from 'three';
import type { Region } from '../model/types';
import type { ToonMaterial } from './toonMaterial';

const geomCache = new Map<string, THREE.BufferGeometry>();

function cached(key: string, make: () => THREE.BufferGeometry): THREE.BufferGeometry {
  let g = geomCache.get(key);
  if (!g) {
    g = make();
    g.userData.cached = true;
    geomCache.set(key, g);
  }
  return g;
}

/** Unit sphere built as a lathe so u = 0 faces +Z, matching every limb and torso part. */
export function unitSphere(seg = 28): THREE.BufferGeometry {
  return cached(`sphere${seg}`, () => {
    const pts: THREE.Vector2[] = [];
    const rows = Math.round(seg * 0.6);
    for (let i = 0; i <= rows; i += 1) {
      const a = -Math.PI / 2 + (i / rows) * Math.PI;
      pts.push(new THREE.Vector2(Math.max(Math.cos(a), 1e-4), Math.sin(a)));
    }
    return new THREE.LatheGeometry(pts, seg);
  });
}

/** Tapered capsule from y = 0 (radius r0) to y = len (radius r1). */
export function taperCapsule(r0: number, r1: number, len: number, seg = 18): THREE.BufferGeometry {
  const k = (n: number) => Math.round(n * 2000) / 2000;
  return cached(`cap${k(r0)}_${k(r1)}_${k(len)}_${seg}`, () => {
    const pts: THREE.Vector2[] = [];
    const cap = 6;
    for (let i = 0; i <= cap; i += 1) {
      const a = -Math.PI / 2 + (i / cap) * (Math.PI / 2);
      pts.push(new THREE.Vector2(Math.max(Math.cos(a) * r0, 1e-4), Math.sin(a) * r0));
    }
    const body = 6;
    for (let i = 1; i < body; i += 1) {
      const t = i / body;
      pts.push(new THREE.Vector2(r0 + (r1 - r0) * t, len * t));
    }
    for (let i = 0; i <= cap; i += 1) {
      const a = (i / cap) * (Math.PI / 2);
      pts.push(new THREE.Vector2(Math.max(Math.cos(a) * r1, 1e-4), len + Math.sin(a) * r1));
    }
    return new THREE.LatheGeometry(pts, seg);
  });
}

export function unitBox(bevel = 0.18): THREE.BufferGeometry {
  return cached(`box${bevel}`, () => roundedBox(1, 1, 1, bevel));
}

export function unitCone(seg = 14): THREE.BufferGeometry {
  return cached(`cone${seg}`, () => {
    const g = new THREE.ConeGeometry(1, 1, seg, 1);
    g.translate(0, 0.5, 0);
    return g;
  });
}

export function unitCylinder(seg = 16): THREE.BufferGeometry {
  return cached(`cyl${seg}`, () => {
    const g = new THREE.CylinderGeometry(1, 1, 1, seg, 1);
    g.translate(0, 0.5, 0);
    return g;
  });
}

export function unitTorus(tube = 0.25, arc = Math.PI * 2): THREE.BufferGeometry {
  return cached(`torus${tube}_${arc.toFixed(3)}`, () => new THREE.TorusGeometry(1, tube, 10, 32, arc));
}

function roundedBox(w: number, h: number, d: number, r: number): THREE.BufferGeometry {
  const g = new THREE.BoxGeometry(w, h, d, 6, 6, 6);
  const pos = g.attributes.position as THREE.BufferAttribute;
  const v = new THREE.Vector3();
  const inner = new THREE.Vector3(w / 2 - r, h / 2 - r, d / 2 - r);
  for (let i = 0; i < pos.count; i += 1) {
    v.fromBufferAttribute(pos, i);
    const c = new THREE.Vector3(
      Math.max(-inner.x, Math.min(inner.x, v.x)),
      Math.max(-inner.y, Math.min(inner.y, v.y)),
      Math.max(-inner.z, Math.min(inner.z, v.z)),
    );
    const dir = v.clone().sub(c);
    if (dir.lengthSq() > 1e-9) v.copy(c.add(dir.normalize().multiplyScalar(r)));
    pos.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  return g;
}

export interface PartOptions {
  region?: Region;
  name?: string;
  outline?: boolean;
  pickable?: boolean;
}

export class PartRegistry {
  meshes: THREE.Mesh[] = [];
  materials = new Set<ToonMaterial>();
  owned: THREE.BufferGeometry[] = [];

  add(parent: THREE.Object3D, geom: THREE.BufferGeometry, mat: THREE.Material, opts: PartOptions = {}): THREE.Mesh {
    const m = new THREE.Mesh(geom, mat);
    m.userData.region = opts.region;
    m.userData.pickable = opts.pickable !== false;
    if (opts.name) m.name = opts.name;
    parent.add(m);
    this.meshes.push(m);
    if ((mat as ToonMaterial).kind) this.materials.add(mat as ToonMaterial);
    if (!geom.userData.cached) this.owned.push(geom);
    return m;
  }

  ellipsoid(parent: THREE.Object3D, mat: THREE.Material, pos: THREE.Vector3Like, radii: THREE.Vector3Like, opts: PartOptions = {}): THREE.Mesh {
    const m = this.add(parent, unitSphere(), mat, opts);
    m.position.set(pos.x, pos.y, pos.z);
    m.scale.set(radii.x, radii.y, radii.z);
    return m;
  }

  /** A tapered limb from a to b in parent space. */
  limb(parent: THREE.Object3D, mat: THREE.Material, a: THREE.Vector3, b: THREE.Vector3, r0: number, r1: number, opts: PartOptions = {}): THREE.Mesh {
    const dir = b.clone().sub(a);
    const len = Math.max(dir.length(), 1e-4);
    const m = this.add(parent, taperCapsule(r0, r1, len), mat, opts);
    m.position.copy(a);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    return m;
  }

  box(parent: THREE.Object3D, mat: THREE.Material, pos: THREE.Vector3Like, size: THREE.Vector3Like, opts: PartOptions & { bevel?: number } = {}): THREE.Mesh {
    const m = this.add(parent, unitBox(opts.bevel ?? 0.18), mat, opts);
    m.position.set(pos.x, pos.y, pos.z);
    m.scale.set(size.x, size.y, size.z);
    return m;
  }

  cone(parent: THREE.Object3D, mat: THREE.Material, base: THREE.Vector3, dir: THREE.Vector3, radius: number, length: number, opts: PartOptions = {}): THREE.Mesh {
    const m = this.add(parent, unitCone(), mat, opts);
    m.position.copy(base);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
    m.scale.set(radius, length, radius);
    return m;
  }

  dispose() {
    for (const g of this.owned) g.dispose();
    for (const m of this.materials) m.dispose();
    this.owned = [];
    this.meshes = [];
    this.materials.clear();
  }
}

export interface Ellipsoid {
  c: THREE.Vector3;
  r: THREE.Vector3;
}

/** Front-projected surface made of ellipsoids. Features are laid on the outermost hit. */
export class HeadSurface {
  parts: Ellipsoid[] = [];

  add(c: THREE.Vector3, r: THREE.Vector3) {
    this.parts.push({ c: c.clone(), r: r.clone() });
  }

  hit(x: number, y: number, out = new THREE.Vector3(), normal = new THREE.Vector3()): boolean {
    let best = -Infinity;
    let bp: Ellipsoid | null = null;
    for (const p of this.parts) {
      const a = ((x - p.c.x) / p.r.x) ** 2 + ((y - p.c.y) / p.r.y) ** 2;
      if (a >= 1) continue;
      const z = p.c.z + p.r.z * Math.sqrt(1 - a);
      if (z > best) {
        best = z;
        bp = p;
      }
    }
    if (!bp) {
      out.set(x, y, 0);
      normal.set(0, 0, 1);
      return false;
    }
    out.set(x, y, best);
    normal.set((x - bp.c.x) / bp.r.x ** 2, (y - bp.c.y) / bp.r.y ** 2, (best - bp.c.z) / bp.r.z ** 2).normalize();
    return true;
  }

  /** Pushes a point out of every ellipsoid (inflated by pad). Used by hair collision. */
  pushOut(p: THREE.Vector3, pad: number) {
    for (const e of this.parts) {
      const rx = e.r.x + pad;
      const ry = e.r.y + pad;
      const rz = e.r.z + pad;
      const dx = (p.x - e.c.x) / rx;
      const dy = (p.y - e.c.y) / ry;
      const dz = (p.z - e.c.z) / rz;
      const d = Math.hypot(dx, dy, dz);
      if (d < 1 && d > 1e-6) {
        p.set(e.c.x + (dx / d) * rx, e.c.y + (dy / d) * ry, e.c.z + (dz / d) * rz);
      }
    }
  }
}

/** Lays a flat 2D grid onto the head surface. Used by eyes and the mouth so they follow the face. */
export function conformGrid(
  surface: HeadSurface,
  center: THREE.Vector2,
  halfW: number,
  halfH: number,
  cols: number,
  rows: number,
  lift: number,
  shape?: (u: number, v: number) => [number, number],
  rotation = 0,
): THREE.BufferGeometry {
  const pos: number[] = [];
  const uv: number[] = [];
  const nrm: number[] = [];
  const idx: number[] = [];
  const p = new THREE.Vector3();
  const n = new THREE.Vector3();
  const cr = Math.cos(rotation);
  const sr = Math.sin(rotation);
  for (let j = 0; j <= rows; j += 1) {
    for (let i = 0; i <= cols; i += 1) {
      const u = i / cols;
      const v = j / rows;
      let [lx, ly] = shape ? shape(u * 2 - 1, v * 2 - 1) : [u * 2 - 1, v * 2 - 1];
      lx *= halfW;
      ly *= halfH;
      const rx = lx * cr - ly * sr;
      const ry = lx * sr + ly * cr;
      surface.hit(center.x + rx, center.y + ry, p, n);
      p.addScaledVector(n, lift);
      pos.push(p.x, p.y, p.z);
      nrm.push(n.x, n.y, n.z);
      uv.push(u, v);
    }
  }
  for (let j = 0; j < rows; j += 1) {
    for (let i = 0; i < cols; i += 1) {
      const a = j * (cols + 1) + i;
      const b = a + 1;
      const c = a + cols + 1;
      const d = c + 1;
      idx.push(a, b, d, a, d, c);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

export function seeded(seed: number): () => number {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return ((s >>> 0) % 100000) / 100000;
  };
}

export function hashString(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i += 1) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export const V = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
