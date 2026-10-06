import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import type { FacialHairPiece, HairPiece } from '../model/types';
import { HeadSurface, hashString, seeded } from './parts';

export interface HairHead {
  /** Cranium radii in head space, centred at the origin. */
  r: THREE.Vector3;
  /** Head height unit. */
  u: number;
  collide: HeadSurface;
  /** Unit directions from the head centre where hair must leave a gap (creature ears, horns). */
  gaps: THREE.Vector3[];
  jaw: { c: THREE.Vector3; r: THREE.Vector3 };
  mouthY: number;
  noseY: number;
}

interface ClumpSpec {
  root: THREE.Vector3;
  dir: THREE.Vector3;
  len: number;
  width: number;
  thick: number;
  gravity: number;
  curl: number;
  wave: number;
  taper: number;
  flat?: THREE.Vector3;
  twist?: number;
  noCollide?: boolean;
}

const SEG = 7;
const RING = 6;

/**
 * Global hair look, measured with the validators in blender/validators/hair.py (tools/placeholders). Placeholders must read as thick,
 * chunky, tapered clumps (the library target: thickness/width >= 0.45, clump width about 0.25 to 0.55 of the head height, 20+ clumps),
 * not needle-thin spikes. The export tool overrides these to compare variants.
 */
type HairTuning = { widthScale: number; minThickRatio: number; taperScale: number; countScale: number; fringeLen: number };
// Held on globalThis so every copy of this module (Vite serves hot-updated modules under a timestamped URL) sees the same values.
export const hairTuning: HairTuning = ((globalThis as unknown as { __hairTuning?: HairTuning }).__hairTuning ??= { widthScale: 1.9, minThickRatio: 0.7, taperScale: 0.7, countScale: 0.7, fringeLen: 0.55 });
export function setHairTuning(t: Partial<HairTuning>) {
  Object.assign(hairTuning, t);
  pieceCache.clear();
}

function buildClump(c0: ClumpSpec, head: HairHead): THREE.BufferGeometry | null {
  // Chunkier clumps: wider, never thinner than minThickRatio of their width, and a gentler taper. Tiny accents (ahoge, wisps) keep their size.
  const big = Math.min(1, c0.width / (head.u * 0.07));
  const widthK = 1 + (hairTuning.widthScale - 1) * big;
  const c: ClumpSpec = { ...c0, width: c0.width * widthK, taper: c0.taper * (1 + (hairTuning.taperScale - 1) * big) };
  c.thick = Math.max(c0.thick * widthK, c.width * hairTuning.minThickRatio * big);
  const pts: THREE.Vector3[] = [c.root.clone()];
  let dir = c.dir.clone().normalize();
  const step = c.len / SEG;
  const p = c.root.clone();
  const side = new THREE.Vector3().crossVectors(dir, new THREE.Vector3(0, 1, 0));
  if (side.lengthSq() < 1e-4) side.set(1, 0, 0);
  side.normalize();
  for (let i = 1; i <= SEG; i += 1) {
    const t = i / SEG;
    dir.y -= c.gravity * step * 10;
    if (c.curl) dir.applyAxisAngle(side, c.curl * step * 12);
    dir.normalize();
    p.addScaledVector(dir, step);
    if (c.wave) p.addScaledVector(side, Math.sin(t * Math.PI * 3) * c.wave * step);
    if (!c.noCollide) head.collide.pushOut(p, 0.006 + c.thick * 0.5);
    pts.push(p.clone());
  }
  const pos: number[] = [];
  const uv: number[] = [];
  const idx: number[] = [];
  const flat = c.flat?.clone().normalize();
  for (let i = 0; i <= SEG; i += 1) {
    const t = i / SEG;
    const a = pts[Math.max(0, i - 1)];
    const b = pts[Math.min(SEG, i + 1)];
    const tan = b.clone().sub(a).normalize();
    let nx = flat ? flat.clone().sub(tan.clone().multiplyScalar(flat.dot(tan))) : pts[i].clone().normalize();
    if (nx.lengthSq() < 1e-6) nx = new THREE.Vector3(0, 0, 1);
    nx.normalize();
    const bx = new THREE.Vector3().crossVectors(tan, nx).normalize();
    const taper = Math.pow(1 - t, c.taper) * (t < 0.12 ? 0.7 + t * 2.5 : 1);
    const w = c.width * Math.max(taper, 0.02);
    const th = c.thick * Math.max(taper, 0.05);
    const tw = (c.twist ?? 0) * t;
    for (let k = 0; k < RING; k += 1) {
      const ang = (k / RING) * Math.PI * 2 + tw;
      const q = pts[i].clone().addScaledVector(bx, Math.cos(ang) * w).addScaledVector(nx, Math.sin(ang) * th);
      pos.push(q.x, q.y, q.z);
      uv.push(k / RING, t);
    }
  }
  for (let i = 0; i < SEG; i += 1) {
    for (let k = 0; k < RING; k += 1) {
      const a = i * RING + k;
      const b = i * RING + ((k + 1) % RING);
      const cc = a + RING;
      const d = b + RING;
      idx.push(a, cc, b, b, cc, d);
    }
  }
  const tipBase = SEG * RING;
  pos.push(pts[SEG].x, pts[SEG].y, pts[SEG].z);
  uv.push(0.5, 1);
  for (let k = 0; k < RING; k += 1) idx.push(tipBase + k, tipBase + RING, tipBase + ((k + 1) % RING));
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

/** Point on the scalp. az: 0 front, +pi/2 character left. el: 0 equator, pi/2 crown. */
function scalp(head: HairHead, az: number, el: number, lift = 1.02): THREE.Vector3 {
  return new THREE.Vector3(Math.sin(az) * Math.cos(el) * head.r.x, Math.sin(el) * head.r.y, Math.cos(az) * Math.cos(el) * head.r.z).multiplyScalar(lift);
}

function outward(p: THREE.Vector3): THREE.Vector3 {
  return p.clone().normalize();
}

function nearGap(head: HairHead, p: THREE.Vector3, radius = 0.42): boolean {
  const d = p.clone().normalize();
  return head.gaps.some((g) => d.angleTo(g) < radius);
}

interface ShapeMods {
  vol: number;
  wid: number;
  len: number;
}

type Builder = (head: HairHead, m: ShapeMods, rand: () => number) => ClumpSpec[];

function cap(head: HairHead, m: ShapeMods, rand: () => number, o: { len: number; gravity: number; minEl?: number; tufts?: number; back?: boolean; sweepTo?: THREE.Vector3; count?: number; wave?: number; curl?: number; skipFront?: boolean }): ClumpSpec[] {
  const out: ClumpSpec[] = [];
  const rings = 5;
  const u = head.u;
  const minEl = o.minEl ?? -0.15;
  for (let r = 0; r < rings; r += 1) {
    const el = minEl + ((r + 0.5) / rings) * (Math.PI / 2 - minEl);
    const count = Math.max(3, Math.round((o.count ?? 14) * Math.cos(el) * hairTuning.countScale));
    for (let i = 0; i < count; i += 1) {
      const az = (i / count) * Math.PI * 2 + r * 0.37 + rand() * 0.1;
      const front = Math.cos(az) > 0.35 && el < 1.0;
      if (o.skipFront && front) continue;
      if (Math.cos(az) > 0.25 && el < 0.3 + 0.35 * Math.cos(az)) continue;
      const root = scalp(head, az, el);
      if (nearGap(head, root)) continue;
      let dir = outward(root).multiplyScalar(0.35).add(new THREE.Vector3(Math.sin(az) * 0.2, -0.3, Math.cos(az) * 0.2 - (o.back ? 0.6 : 0.2)));
      if (o.sweepTo) dir = o.sweepTo.clone().sub(root).normalize().add(outward(root).multiplyScalar(0.2));
      const tuft = o.tufts && el > 0.8 && rand() < o.tufts;
      out.push({
        root,
        dir: tuft ? outward(root).add(new THREE.Vector3(0, 0.7, -0.2)) : dir,
        len: (o.len * (0.8 + rand() * 0.4) * (tuft ? 0.7 : 1)) * u * (1 + m.len * 0.35),
        width: u * 0.085 * (1 + m.wid * 0.35) * (0.85 + rand() * 0.3),
        thick: u * 0.03 * (1 + m.vol * 0.5),
        gravity: tuft ? -0.02 : o.gravity,
        curl: o.curl ?? 0,
        wave: o.wave ?? 0,
        taper: 0.9,
      });
    }
  }
  return out;
}

function tail(head: HairHead, m: ShapeMods, rand: () => number, tie: THREE.Vector3, len: number, spread: number, n: number, braid = false): ClumpSpec[] {
  const out: ClumpSpec[] = [];
  const u = head.u;
  if (braid) {
    const segs = Math.round(8 * (1 + m.len * 0.4) * len);
    const p = tie.clone();
    for (let i = 0; i < segs; i += 1) {
      const t = i / segs;
      const w = u * 0.11 * (1 - t * 0.45) * (1 + m.vol * 0.3);
      for (const s of [-1, 1]) {
        out.push({
          root: p.clone().add(new THREE.Vector3(s * w * 0.35, 0, 0)),
          dir: new THREE.Vector3(-s * 0.45, -1, -0.05),
          len: u * 0.2,
          width: w * 0.65,
          thick: w * 0.45,
          gravity: 0.01,
          curl: 0,
          wave: 0,
          taper: 0.6,
          noCollide: false,
        });
      }
      p.y -= u * 0.16;
      head.collide.pushOut(p, u * 0.08);
    }
    out.push({ root: p.clone(), dir: new THREE.Vector3(0, -1, 0), len: u * 0.35, width: u * 0.08, thick: u * 0.05, gravity: 0.02, curl: 0, wave: 0, taper: 1.2 });
    return out;
  }
  for (let i = 0; i < n; i += 1) {
    const a = (i / n) * Math.PI * 2;
    const root = tie.clone().add(new THREE.Vector3(Math.cos(a) * u * 0.05, Math.sin(a) * u * 0.05, 0));
    out.push({
      root,
      dir: new THREE.Vector3(Math.cos(a) * spread, -0.6 + Math.sin(a) * spread * 0.5, -0.6),
      len: len * u * (0.85 + rand() * 0.3) * (1 + m.len * 0.4),
      width: u * 0.1 * (1 + m.wid * 0.35),
      thick: u * 0.045 * (1 + m.vol * 0.5),
      gravity: 0.045,
      curl: 0,
      wave: 0,
      taper: 1,
    });
  }
  return out;
}

function ballOf(head: HairHead, m: ShapeMods, rand: () => number, center: THREE.Vector3, radius: number, n: number): ClumpSpec[] {
  const out: ClumpSpec[] = [];
  const u = head.u;
  for (let i = 0; i < n; i += 1) {
    const y = 1 - (i / (n - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const a = i * 2.39996;
    const d = new THREE.Vector3(Math.cos(a) * r, y, Math.sin(a) * r);
    out.push({
      root: center.clone().addScaledVector(d, radius * 0.4),
      dir: d,
      len: radius * 0.75 * (1 + m.vol * 0.3),
      width: u * 0.12 * (1 + m.wid * 0.3),
      thick: u * 0.07,
      gravity: 0,
      curl: 0.25 + rand() * 0.2,
      wave: 0,
      taper: 0.7,
      noCollide: true,
    });
  }
  return out;
}

function fringe(head: HairHead, m: ShapeMods, rand: () => number, o: { len: number; count: number; spread: number; sweep: number; part?: number; thick?: number; curl?: number; wisp?: number; lenBias?: (x: number) => number; cover?: number }): ClumpSpec[] {
  const out: ClumpSpec[] = [];
  const u = head.u;
  for (let i = 0; i < o.count; i += 1) {
    const x = o.count === 1 ? 0 : (i / (o.count - 1)) * 2 - 1;
    const az = x * o.spread;
    const el = 0.72 + (1 - Math.abs(x)) * 0.12;
    const root = scalp(head, az, el, 1.03);
    if (nearGap(head, root, 0.3)) continue;
    let sx = o.sweep;
    if (o.part !== undefined) sx = x < o.part ? -0.55 : 0.55;
    const dir = new THREE.Vector3(sx + x * 0.25, -0.75, 0.62);
    const bias = o.lenBias ? o.lenBias(x) : 1;
    out.push({
      root,
      dir,
      len: o.len * u * bias * (0.9 + rand() * 0.2) * (1 + m.len * 0.35) * hairTuning.fringeLen,
      width: u * (o.wisp ? 0.05 : 0.09) * (1 + m.wid * 0.35),
      thick: u * (o.thick ?? 0.028) * (1 + m.vol * 0.5),
      gravity: 0.07,
      curl: o.curl ?? 0.06,
      wave: 0,
      taper: o.wisp ? 1.4 : 0.9,
    });
  }
  return out;
}

const BACK: Record<string, Builder> = {
  bald: () => [],
  crop: (h, m, r) => cap(h, m, r, { len: 0.28, gravity: 0.01, tufts: 0.6, count: 16 }),
  shortLayered: (h, m, r) => cap(h, m, r, { len: 0.42, gravity: 0.025, tufts: 0.45, count: 15 }),
  bob: (h, m, r) => cap(h, m, r, { len: 0.8, gravity: 0.06, count: 16, curl: 0.12, skipFront: true }),
  longStraight: (h, m, r) => cap(h, m, r, { len: 1.8, gravity: 0.07, count: 16, skipFront: true }),
  longLayered: (h, m, r) => [...cap(h, m, r, { len: 1.1, gravity: 0.07, count: 12, skipFront: true }), ...cap(h, m, r, { len: 1.7, gravity: 0.07, count: 10, minEl: -0.2, skipFront: true })],
  wavy: (h, m, r) => cap(h, m, r, { len: 1.5, gravity: 0.06, count: 15, wave: 0.9, skipFront: true }),
  curls: (h, m, r) => cap(h, m, r, { len: 0.8, gravity: 0.03, count: 18, curl: 0.5, skipFront: true }).map((c) => ({ ...c, thick: c.thick * 1.6, width: c.width * 1.1 })),
  hime: (h, m, r) => cap(h, m, r, { len: 1.9, gravity: 0.08, count: 18, skipFront: true }).map((c) => ({ ...c, taper: 0.25 })),
  lowPony: (h, m, r) => { const tie = new THREE.Vector3(0, -0.35 * h.r.y, -h.r.z * 1.05); return [...cap(h, m, r, { len: 0.6, gravity: 0.01, sweepTo: tie, skipFront: true }), ...tail(h, m, r, tie, 1.4, 0.18, 7)]; },
  highPony: (h, m, r) => { const tie = new THREE.Vector3(0, 0.65 * h.r.y, -h.r.z * 0.95); return [...cap(h, m, r, { len: 0.5, gravity: 0, sweepTo: tie, skipFront: true }), ...tail(h, m, r, tie, 1.6, 0.25, 8)]; },
  twinTails: (h, m, r) => { const a = new THREE.Vector3(h.r.x * 0.85, 0.45 * h.r.y, -h.r.z * 0.4); const b = a.clone().setX(-a.x); return [...cap(h, m, r, { len: 0.5, gravity: 0.02, count: 14, skipFront: true }), ...tail(h, m, r, a, 1.5, 0.3, 6), ...tail(h, m, r, b, 1.5, 0.3, 6)]; },
  braid: (h, m, r) => { const tie = new THREE.Vector3(0, -0.4 * h.r.y, -h.r.z * 1.05); return [...cap(h, m, r, { len: 0.6, gravity: 0.01, sweepTo: tie, skipFront: true }), ...tail(h, m, r, tie, 1.2, 0, 0, true)]; },
  twinBraids: (h, m, r) => { const a = new THREE.Vector3(h.r.x * 0.75, -0.45 * h.r.y, -h.r.z * 0.55); const b = a.clone().setX(-a.x); return [...cap(h, m, r, { len: 0.55, gravity: 0.03, count: 14, skipFront: true }), ...tail(h, m, r, a, 1.0, 0, 0, true), ...tail(h, m, r, b, 1.0, 0, 0, true)]; },
  halfUp: (h, m, r) => { const tie = new THREE.Vector3(0, 0.25 * h.r.y, -h.r.z * 1.05); return [...cap(h, m, r, { len: 1.4, gravity: 0.07, count: 12, minEl: -0.3, skipFront: true }), ...tail(h, m, r, tie, 0.5, 0.3, 5)]; },
  bun: (h, m, r) => { const c = new THREE.Vector3(0, 0.7 * h.r.y, -h.r.z * 0.95); return [...cap(h, m, r, { len: 0.5, gravity: 0, sweepTo: c, skipFront: true }), ...ballOf(h, m, r, c, h.u * 0.3, 22)]; },
  twinBuns: (h, m, r) => { const a = new THREE.Vector3(h.r.x * 0.7, 0.8 * h.r.y, -h.r.z * 0.3); const b = a.clone().setX(-a.x); return [...cap(h, m, r, { len: 0.5, gravity: 0.02, count: 14, skipFront: true }), ...ballOf(h, m, r, a, h.u * 0.22, 16), ...ballOf(h, m, r, b, h.u * 0.22, 16)]; },
  sidePony: (h, m, r) => { const tie = new THREE.Vector3(h.r.x * 0.9, -0.35 * h.r.y, -h.r.z * 0.5); return [...cap(h, m, r, { len: 0.55, gravity: 0.01, sweepTo: tie, skipFront: true }), ...tail(h, m, r, tie, 1.3, 0.2, 7)]; },
  afro: (h, m, r) => ballOf(h, m, r, new THREE.Vector3(0, h.r.y * 0.3, -h.r.z * 0.15), h.u * 0.75, 90),
  puff: (h, m, r) => { const c = new THREE.Vector3(0, h.r.y * 0.85, -h.r.z * 0.6); return [...cap(h, m, r, { len: 0.3, gravity: 0, sweepTo: c, skipFront: true }), ...ballOf(h, m, r, c, h.u * 0.42, 40)]; },
  locs: (h, m, r) => cap(h, m, r, { len: 1.4, gravity: 0.08, count: 20, skipFront: true }).map((c) => ({ ...c, width: c.width * 0.45, thick: c.width * 0.45, taper: 0.15 })),
  cornrows: (h, m, r) => {
    const out: ClumpSpec[] = [];
    for (let i = -4; i <= 4; i += 1) {
      const root = scalp(h, i * 0.18, 1.0, 1.01);
      out.push({ root, dir: new THREE.Vector3(i * 0.05, 0.1, -1), len: h.u * 1.4, width: h.u * 0.04, thick: h.u * 0.025, gravity: 0.1, curl: 0, wave: 0, taper: 0.3, twist: 9 });
    }
    return out;
  },
  braidPony: (h, m, r) => { const tie = new THREE.Vector3(0, 0.2 * h.r.y, -h.r.z * 1.05); return [...cap(h, m, r, { len: 0.55, gravity: 0, sweepTo: tie, skipFront: true }), ...tail(h, m, r, tie, 1.4, 0, 0, true)]; },
  mullet: (h, m, r) => [...cap(h, m, r, { len: 0.35, gravity: 0.02, tufts: 0.5, count: 14 }), ...cap(h, m, r, { len: 1.2, gravity: 0.08, count: 10, minEl: -0.35, skipFront: true }).filter((c) => c.root.z < 0)],
  wolf: (h, m, r) => cap(h, m, r, { len: 0.75, gravity: 0.035, tufts: 0.55, count: 17, skipFront: true }).map((c) => ({ ...c, len: c.len * (0.6 + r() * 0.8), curl: 0.08 })),
  undercut: (h, m, r) => cap(h, m, r, { len: 0.7, gravity: 0.02, minEl: 0.7, count: 14 }).map((c) => ({ ...c, dir: c.dir.clone().add(new THREE.Vector3(0.5, 0.4, 0)) })),
  mohawk: (h, m, r) => {
    const out: ClumpSpec[] = [];
    for (let i = 0; i < 9; i += 1) {
      const el = 0.5 + (i / 8) * 1.7;
      const root = new THREE.Vector3(0, Math.sin(Math.min(el, Math.PI / 2)) * h.r.y, Math.cos(el) * h.r.z).multiplyScalar(1.02);
      out.push({ root, dir: outward(root).add(new THREE.Vector3(0, 0.4, 0)), len: h.u * 0.5 * (1 + m.len * 0.4), width: h.u * 0.07, thick: h.u * 0.04 * (1 + m.vol * 0.5), gravity: -0.01, curl: 0, wave: 0, taper: 1, flat: new THREE.Vector3(1, 0, 0) });
    }
    return out;
  },
  drill: (h, m, r) => {
    const base = cap(h, m, r, { len: 0.6, gravity: 0.04, count: 14, skipFront: true });
    const out: ClumpSpec[] = [...base];
    for (const s of [-1, 1]) {
      for (let k = 0; k < 2; k += 1) {
        const root = new THREE.Vector3(s * h.r.x * 0.95, -0.1 * h.r.y, -h.r.z * (0.2 + k * 0.4));
        out.push({ root, dir: new THREE.Vector3(s * 0.2, -1, -0.1), len: h.u * 1.2 * (1 + m.len * 0.3), width: h.u * 0.16, thick: h.u * 0.12, gravity: 0.02, curl: 0, wave: 0, taper: 0.6, twist: 16 });
      }
    }
    return out;
  },
  shoulderBraid: (h, m, r) => { const tie = new THREE.Vector3(h.r.x * 0.8, -0.55 * h.r.y, -h.r.z * 0.2); return [...cap(h, m, r, { len: 0.8, gravity: 0.03, sweepTo: tie, skipFront: true }), ...tail(h, m, r, tie, 1.3, 0, 0, true).map((c) => ({ ...c, root: c.root.clone().add(new THREE.Vector3(0, 0, h.u * 0.25)) }))]; },
};

const FRONT: Record<string, Builder> = {
  none: (h, m, r) => fringe(h, m, r, { len: 0.35, count: 5, spread: 0.7, sweep: 0 }).map((c) => ({ ...c, dir: new THREE.Vector3(0, 0.6, -0.8) })),
  blunt: (h, m, r) => fringe(h, m, r, { len: 0.62, count: 9, spread: 0.85, sweep: 0 }).map((c) => ({ ...c, taper: 0.3 })),
  parted: (h, m, r) => fringe(h, m, r, { len: 0.6, count: 8, spread: 0.9, sweep: 0, part: -0.25 }),
  swept: (h, m, r) => fringe(h, m, r, { len: 0.62, count: 8, spread: 0.85, sweep: 0.75, lenBias: (x) => 1 - x * 0.2 }),
  curtain: (h, m, r) => fringe(h, m, r, { len: 0.8, count: 8, spread: 0.9, sweep: 0, part: 0 }).map((c) => ({ ...c, dir: c.dir.clone().add(new THREE.Vector3(Math.sign(c.root.x) * 0.5, 0, 0)) })),
  asym: (h, m, r) => fringe(h, m, r, { len: 0.55, count: 8, spread: 0.85, sweep: 0.4, lenBias: (x) => 1 + x * 0.6 }),
  heavy: (h, m, r) => fringe(h, m, r, { len: 0.78, count: 10, spread: 0.9, sweep: 0.1, thick: 0.045 }),
  wispy: (h, m, r) => fringe(h, m, r, { len: 0.42, count: 7, spread: 0.85, sweep: 0.1, wisp: 1 }),
  midLong: (h, m, r) => fringe(h, m, r, { len: 1.3, count: 8, spread: 1.0, sweep: 0, part: 0 }).map((c) => ({ ...c, dir: c.dir.clone().add(new THREE.Vector3(Math.sign(c.root.x) * 0.7, -0.2, 0)) })),
  eyeCover: (h, m, r) => fringe(h, m, r, { len: 0.7, count: 8, spread: 0.85, sweep: -0.4, lenBias: (x) => (x < 0 ? 1.5 : 0.8) }),
  curled: (h, m, r) => fringe(h, m, r, { len: 0.55, count: 8, spread: 0.85, sweep: 0, curl: 0.4, thick: 0.04 }),
  braidFringe: (h, m, r) => {
    const out: ClumpSpec[] = [];
    for (let i = 0; i < 10; i += 1) {
      const x = (i / 9) * 2 - 1;
      const root = scalp(h, x * 0.95, 0.78 + (1 - Math.abs(x)) * 0.1, 1.04);
      out.push({ root, dir: new THREE.Vector3(1, -0.1 * x, 0.2), len: h.u * 0.16, width: h.u * 0.06, thick: h.u * 0.04, gravity: 0, curl: 0, wave: 0, taper: 0.5, twist: 3, noCollide: true });
    }
    return [...fringe(h, m, r, { len: 0.3, count: 5, spread: 0.6, sweep: 0 }).map((c) => ({ ...c, dir: new THREE.Vector3(0, 0.6, -0.8) })), ...out];
  },
};

const SIDES: Record<string, Builder> = {
  none: () => [],
  short: (h, m, r) => sideLocks(h, m, r, 0.55, 3),
  long: (h, m, r) => sideLocks(h, m, r, 1.3, 3),
  tucked: (h, m, r) => sideLocks(h, m, r, 0.6, 2).map((c) => ({ ...c, dir: new THREE.Vector3(Math.sign(c.root.x) * 0.3, -0.6, -1) })),
  himeLocks: (h, m, r) => sideLocks(h, m, r, 0.85, 4).map((c) => ({ ...c, taper: 0.2, gravity: 0.1 })),
};

function sideLocks(h: HairHead, m: ShapeMods, rand: () => number, len: number, n: number): ClumpSpec[] {
  const out: ClumpSpec[] = [];
  for (const s of [-1, 1]) {
    for (let i = 0; i < n; i += 1) {
      const az = s * (0.95 + i * 0.16);
      const root = scalp(h, az, 0.55 - i * 0.05, 1.03);
      if (nearGap(h, root, 0.3)) continue;
      out.push({
        root,
        dir: new THREE.Vector3(s * 0.15, -1, 0.3),
        len: h.u * len * (0.9 + rand() * 0.2) * (1 + m.len * 0.4),
        width: h.u * 0.08 * (1 + m.wid * 0.3),
        thick: h.u * 0.03 * (1 + m.vol * 0.5),
        gravity: 0.06,
        curl: 0,
        wave: 0,
        taper: 0.9,
      });
    }
  }
  return out;
}

const EXTRA: Record<string, Builder> = {
  ahoge: (h, m) => [{ root: scalp(h, 0.1, 1.3, 1.02), dir: new THREE.Vector3(0.1, 1, 0.6), len: h.u * 0.35 * (1 + m.len * 0.4), width: h.u * 0.05, thick: h.u * 0.02, gravity: 0, curl: -0.9, wave: 0, taper: 1.3, noCollide: true }],
  sideLock: (h, m) => [{ root: scalp(h, 0.9, 0.5, 1.04), dir: new THREE.Vector3(0.1, -1, 0.5), len: h.u * 1.2 * (1 + m.len * 0.4), width: h.u * 0.07, thick: h.u * 0.03, gravity: 0.06, curl: 0, wave: 0, taper: 0.8 }],
  braidAccent: (h, m, r) => tail(h, m, r, scalp(h, -1.1, 0.4, 1.06), 0.55, 0, 0, true).map((c) => ({ ...c, width: c.width * 0.6, thick: c.thick * 0.6 })),
  ribbon: () => [],
  band: () => [],
};

const pieceCache = new Map<string, THREE.BufferGeometry | null>();

function builderFor(slot: 'front' | 'back' | 'sides' | 'extra', id: string): Builder | undefined {
  if (slot === 'front') return FRONT[id];
  if (slot === 'back') return BACK[id];
  if (slot === 'sides') return SIDES[id];
  return EXTRA[id];
}

export function hairGeometry(slot: 'front' | 'back' | 'sides' | 'extra', piece: HairPiece, head: HairHead, headKey: string): THREE.BufferGeometry | null {
  const b = builderFor(slot, piece.id);
  if (!b) return null;
  const key = `${slot}:${piece.id}:${piece.volume}:${piece.width}:${piece.length}:${headKey}:${Object.values(hairTuning).join(',')}`;
  if (pieceCache.has(key)) return pieceCache.get(key)!;
  const m: ShapeMods = { vol: piece.volume / 100, wid: piece.width / 100, len: piece.length / 100 };
  const rand = seeded(hashString(key));
  const specs = b(head, m, rand).map((c) => ({ ...c, root: c.root.clone().multiplyScalar(1 + m.vol * 0.04) }));
  const geoms = specs.map((c) => buildClump(c, head)).filter((g): g is THREE.BufferGeometry => !!g);
  const merged = geoms.length ? mergeGeometries(geoms, false) : null;
  for (const g of geoms) g.dispose();
  if (merged) merged.userData.cached = true;
  pieceCache.set(key, merged);
  if (pieceCache.size > 90) {
    const first = pieceCache.keys().next().value as string;
    pieceCache.get(first)?.dispose();
    pieceCache.delete(first);
  }
  return merged;
}

/** Scalp shell so short cuts never show gaps. */
export function scalpShell(head: HairHead, style: string): { c: THREE.Vector3; r: THREE.Vector3 } | null {
  if (style === 'bald' || style === 'afro') return null;
  const shaved = style === 'undercut' || style === 'mohawk' || style === 'cornrows';
  return { c: new THREE.Vector3(0, head.r.y * 0.1, -head.r.z * 0.06), r: head.r.clone().multiplyScalar(shaved ? 1.005 : 1.03) };
}

export function facialHairGeometry(kind: 'moustache' | 'sideburns' | 'beard', piece: FacialHairPiece, head: HairHead, headKey: string): THREE.BufferGeometry | null {
  if (piece.id === 'none' || (kind === 'beard' && piece.id === 'stubble')) return null;
  const key = `fh:${kind}:${piece.id}:${piece.length}:${piece.bulk}:${headKey}`;
  if (pieceCache.has(key)) return pieceCache.get(key)!;
  const u = head.u;
  const L = 1 + piece.length / 100 * 0.6;
  const B = 1 + piece.bulk / 100 * 0.6;
  const specs: ClumpSpec[] = [];
  const surf = head.collide;
  const at = (x: number, y: number) => {
    const p = new THREE.Vector3();
    const n = new THREE.Vector3();
    surf.hit(x, y, p, n);
    return { p: p.addScaledVector(n, 0.002), n };
  };
  const my = head.mouthY;
  if (kind === 'moustache') {
    const n = piece.id === 'pencil' ? 6 : 8;
    for (let i = 0; i < n; i += 1) {
      const x = ((i / (n - 1)) * 2 - 1) * u * 0.13;
      const { p, n: nn } = at(x, my + u * 0.06);
      const s = Math.sign(x) || 1;
      let dir = new THREE.Vector3(s * 0.8, -0.35, 0.3);
      let len = u * 0.1 * L;
      let curl = 0;
      if (piece.id === 'handlebar' && Math.abs(x) > u * 0.08) {
        dir = new THREE.Vector3(s, 0.1, 0.2);
        curl = s * 0.9;
        len *= 1.5;
      }
      if (piece.id === 'droop' && Math.abs(x) > u * 0.07) {
        dir = new THREE.Vector3(s * 0.3, -1, 0.2);
        len *= 2;
      }
      specs.push({ root: p, dir, len, width: u * (piece.id === 'pencil' ? 0.02 : 0.045) * B, thick: u * 0.018 * B, gravity: 0.02, curl, wave: 0, taper: 0.8, flat: nn, noCollide: true });
    }
  } else if (kind === 'sideburns') {
    for (const s of [-1, 1]) {
      const rows = piece.id === 'mutton' ? 5 : 3;
      for (let i = 0; i < rows; i += 1) {
        const x = s * head.r.x * (0.92 - i * 0.04);
        const y = head.noseY + u * 0.05 - i * u * 0.07;
        const p = new THREE.Vector3(x, y, head.r.z * 0.1);
        surf.pushOut(p, 0.004);
        specs.push({ root: p, dir: new THREE.Vector3(0, -1, 0.3), len: u * (piece.id === 'mutton' ? 0.2 : 0.12) * L, width: u * 0.05 * B, thick: u * 0.02 * B, gravity: 0.01, curl: 0, wave: 0, taper: 0.8, flat: new THREE.Vector3(s, 0, 0) });
      }
    }
  } else {
    const goatee = piece.id === 'goatee';
    const extent = goatee ? 0.35 : piece.id === 'short' ? 0.8 : 1;
    const len = u * ({ short: 0.12, medium: 0.28, full: 0.45, goatee: 0.2 } as Record<string, number>)[piece.id] * L;
    const cols = goatee ? 4 : 11;
    for (let r = 0; r < 3; r += 1) {
      for (let i = 0; i < cols; i += 1) {
        const x = ((i / (cols - 1)) * 2 - 1) * head.jaw.r.x * 0.95 * extent;
        const y = my - u * 0.08 - r * u * 0.07 + Math.abs(x) * 0.4;
        const { p, n } = at(x, y);
        specs.push({ root: p, dir: n.clone().multiplyScalar(0.4).add(new THREE.Vector3(0, -1, 0.1)), len: len * (1 - r * 0.15), width: u * 0.07 * B, thick: u * 0.03 * B, gravity: 0.03, curl: 0, wave: 0, taper: 0.9, noCollide: true });
      }
    }
  }
  const geoms = specs.map((c) => buildClump(c, head)).filter((g): g is THREE.BufferGeometry => !!g);
  const merged = geoms.length ? mergeGeometries(geoms, false) : null;
  for (const g of geoms) g.dispose();
  if (merged) merged.userData.cached = true;
  pieceCache.set(key, merged);
  return merged;
}
