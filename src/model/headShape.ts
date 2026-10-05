import * as THREE from 'three';
import { HeadSurface, V } from '../viewport/parts';

/**
 * The head is a union of ellipsoids. These are their sizes and places, kept apart from the Three.js
 * build so the shape can be measured and tested against reference proportions (knowledge/head-targets.json).
 * Units are the head scale h. The head group origin is the skull centre. +z is forward.
 */
export interface HeadDims {
  R: THREE.Vector3;
  jawC: THREE.Vector3;
  jawR: THREE.Vector3;
  chinC: THREE.Vector3;
  chinR: THREE.Vector3;
  cheekR: number;
  cheekC: THREE.Vector3;
  noseY: number;
}

/**
 * Multipliers fitted to the reference head profile with scripts/fit_head.ts. 1 is the original ellipsoid size.
 * Fitted 2026-10-05 against knowledge/head-targets.json: cranium 0.70H -> 0.59H, width:depth 0.88 -> 0.74,
 * jaw at 0.8H 0.57H -> 0.34H, nose ahead of chin 0.08H -> 0.11H.
 */
export interface HeadTuning {
  rx: number; rz: number;
  jawRx: number; jawRz: number; jawCz: number;
  chinRx: number; chinRz: number; chinCz: number;
  cheekCx: number; cheekR: number; cheekCz: number;
  noseZ: number; noseDown: number;
}
export const HEAD_TUNING: HeadTuning = {
  rx: 0.846, rz: 1.004, jawRx: 0.604, jawRz: 1.161, jawCz: 1.5, chinRx: 0.923, chinRz: 1.13, chinCz: 0.974, cheekCx: 1, cheekR: 1, cheekCz: 1, noseZ: 1.401, noseDown: 0.049,
};

export function headDims(n: (k: string) => number, h: number, child: boolean, young: number, t: HeadTuning = HEAD_TUNING): HeadDims {
  const pos = (k: string) => Math.max(0, n(k));
  const skullW = 1 + 0.1 * n('skull.width') + 0.07 * pos('face.heart') - 0.04 * pos('face.diamond') + 0.05 * pos('face.round');
  const R = V(0.39 * h * skullW * t.rx, 0.43 * h * (1 + 0.06 * n('skull.crown') + 0.05 * pos('face.long')), 0.42 * h * (1 + 0.1 * n('skull.depth')) * t.rz);
  const faceSoft = n('face.softness');
  const jawWidth = 1 + 0.18 * n('jaw.width') + 0.14 * pos('face.square') + 0.1 * pos('face.round') - 0.16 * pos('face.heart') - 0.1 * pos('face.diamond') + 0.05 * faceSoft + 0.06 * pos('age.jawSoft');
  const jawLen = 1 + 0.14 * pos('face.long') + 0.06 * n('jaw.height');
  const jawC = V(0, -0.3 * h * jawLen - 0.03 * h * pos('age.jawSoft'), 0.07 * h * t.jawCz);
  const jawR = V(0.3 * h * jawWidth * (child ? 1.05 : 1) * t.jawRx, 0.27 * h * jawLen * (1 + 0.05 * young), 0.31 * h * t.jawRz);
  const chinW = 1 + 0.3 * n('chin.width') - 0.3 * pos('face.heart') - 0.2 * pos('face.diamond') + 0.2 * pos('face.square');
  const chinC = V(0, jawC.y - jawR.y * 0.72 - 0.035 * h * n('chin.length'), jawC.z + jawR.z * 0.55 * t.chinCz);
  const chinR = V(0.1 * h * chinW * t.chinRx, 0.085 * h * (1 + 0.3 * n('chin.length')), 0.085 * h * t.chinRz);
  const cheekR = 0.12 * h * t.cheekR * (1 + 0.25 * n('cheek.full') + 0.18 * pos('face.round') + 0.12 * young + 0.08 * faceSoft);
  const cheekC = V(0.2 * h * t.cheekCx * (1 + 0.08 * n('cheek.bone') + 0.08 * pos('face.diamond')), -0.15 * h + 0.03 * h * n('cheek.bone'), 0.19 * h * t.cheekCz);
  const noseY = -(0.2 + t.noseDown) * h - 0.02 * h * n('nose.length');
  return { R, jawC, jawR, chinC, chinR, cheekR, cheekC, noseY };
}

export interface HeadProfile {
  /** Fractions of head height, 0 = top of skull, 1 = chin tip. */
  width: Record<string, number>;
  behindNose: Record<string, number>;
  skullDepth03: number;
  cranium: number;
  widthToDepth: number;
}

const FRACS = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.75, 0.8, 0.85, 0.9, 0.95, 0.97];

/** Silhouette profile of the ellipsoid head, measured the same way as head_profile.py measures an image. */
export function headProfile(d: HeadDims, h: number, child: boolean, n: (k: string) => number, t: HeadTuning = HEAD_TUNING): HeadProfile {
  const surf = new HeadSurface();
  surf.add(V(0, 0, 0), d.R);
  surf.add(d.jawC, d.jawR);
  surf.add(d.chinC, d.chinR);
  for (const s of [1, -1]) surf.add(V(s * d.cheekC.x, d.cheekC.y, d.cheekC.z), V(d.cheekR, d.cheekR * 0.9, d.cheekR));
  const noseSize = (1 + 0.3 * n('nose.size')) * (child ? 0.85 : 1);
  const np = new THREE.Vector3();
  surf.hit(0, d.noseY, np);
  const noseLen = 0.07 * h * noseSize * (1 + 0.3 * n('nose.length')) * t.noseZ;
  const bridge = 1 + 0.5 * n('nose.bridgeHeight');
  const noseC = np.clone().add(V(0, 0.01 * h * n('nose.tipUp'), -0.01 * h));
  const noseR = V(0.035 * h * noseSize, 0.04 * h * noseSize, noseLen * bridge * 0.6);
  const parts = [...surf.parts, { c: noseC, r: noseR }];
  const top = d.R.y;
  const chinTip = d.chinC.y - d.chinR.y;
  const H = top - chinTip;
  const span = (y: number, pick: (c: number, r: number, k: number) => number, axis: 'x' | 'z') => {
    let best: number | null = null;
    for (const p of parts) {
      const dy = (y - p.c.y) / p.r.y;
      if (Math.abs(dy) >= 1) continue;
      const k = Math.sqrt(1 - dy * dy);
      const v = pick(p.c[axis], p.r[axis], k);
      best = best === null ? v : Math.max(best, v);
    }
    return best;
  };
  const width: Record<string, number> = {};
  const behindNose: Record<string, number> = {};
  const noseTip = noseC.z + noseR.z;
  for (const f of FRACS) {
    const y = top - f * H;
    const hx = span(y, (c, r, k) => Math.abs(c) + r * k, 'x');
    width[String(f)] = hx === null ? 0 : (2 * hx) / H;
    const fz = span(y, (c, r, k) => c + r * k, 'z');
    behindNose[String(f)] = fz === null ? 0 : (noseTip - fz) / H;
  }
  for (const f of [0.1, 0.2, 0.3, 0.4, 0.6, 0.8, 0.9]) {
    const y = top - f * H;
    const fz = span(y, (c, r, k) => c + r * k, 'z');
    behindNose[String(f)] = fz === null ? 0 : (noseTip - fz) / H;
  }
  const y3 = top - 0.3 * H;
  const front = span(y3, (c, r, k) => c + r * k, 'z') ?? 0;
  const back = span(y3, (c, r, k) => -(c - r * k), 'z') ?? 0;
  const skullDepth03 = (front + back) / H;
  const cranium = (width['0.2'] + width['0.25'] + width['0.3']) / 3;
  return { width, behindNose, skullDepth03, cranium, widthToDepth: cranium / skullDepth03 };
}
