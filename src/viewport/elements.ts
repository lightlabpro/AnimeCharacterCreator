import * as THREE from 'three';
import { mixHex } from '../model/character';
import type { MouthSolve } from './face';
import type { HumanoidBody } from './humanoid';
import { V } from './parts';
import { socket, type BuildCtx, type FrameState } from './rig';

const S = [1, -1];

/** Sweeps a tapering round tube along points. */
export function taperTube(points: THREE.Vector3[], r0: number, r1: number, ring = 10, flatten = 1): THREE.BufferGeometry {
  const curve = new THREE.CatmullRomCurve3(points);
  const segs = Math.max(8, points.length * 4);
  const frames = curve.computeFrenetFrames(segs, false);
  const pos: number[] = [];
  const uv: number[] = [];
  const idx: number[] = [];
  for (let i = 0; i <= segs; i += 1) {
    const t = i / segs;
    const p = curve.getPointAt(t);
    const r = r0 + (r1 - r0) * t;
    const N = frames.normals[i];
    const B = frames.binormals[i];
    for (let k = 0; k < ring; k += 1) {
      const a = (k / ring) * Math.PI * 2;
      const q = p.clone().addScaledVector(N, Math.cos(a) * r).addScaledVector(B, Math.sin(a) * r * flatten);
      pos.push(q.x, q.y, q.z);
      uv.push(k / ring, t);
    }
  }
  for (let i = 0; i < segs; i += 1) {
    for (let k = 0; k < ring; k += 1) {
      const a = i * ring + k;
      const b = i * ring + ((k + 1) % ring);
      idx.push(a, a + ring, b, b, a + ring, b + ring);
    }
  }
  const tip = curve.getPointAt(1);
  const tipIdx = pos.length / 3;
  pos.push(tip.x, tip.y, tip.z);
  uv.push(0.5, 1);
  for (let k = 0; k < ring; k += 1) idx.push(segs * ring + k, tipIdx, segs * ring + ((k + 1) % ring));
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

function scalpPoint(R: THREE.Vector3, az: number, el: number, lift = 0.98): THREE.Vector3 {
  return V(Math.sin(az) * Math.cos(el) * R.x, Math.sin(el) * R.y, Math.cos(az) * Math.cos(el) * R.z).multiplyScalar(lift);
}

function orient(o: THREE.Object3D, dir: THREE.Vector3) {
  o.quaternion.setFromUnitVectors(V(0, 1, 0), dir.clone().normalize());
}

const MUZZLE: Record<string, { w: number; hg: number; len: number; nosePad: boolean; teeth: boolean }> = {
  feline: { w: 0.17, hg: 0.1, len: 0.13, nosePad: true, teeth: false },
  canine: { w: 0.13, hg: 0.1, len: 0.26, nosePad: true, teeth: true },
  reptile: { w: 0.14, hg: 0.075, len: 0.32, nosePad: false, teeth: true },
  fish: { w: 0.2, hg: 0.09, len: 0.12, nosePad: false, teeth: false },
  bird: { w: 0.09, hg: 0.07, len: 0.3, nosePad: false, teeth: false },
  frog: { w: 0.3, hg: 0.075, len: 0.1, nosePad: false, teeth: false },
  lagomorph: { w: 0.14, hg: 0.1, len: 0.1, nosePad: true, teeth: false },
  heavy: { w: 0.2, hg: 0.15, len: 0.22, nosePad: false, teeth: false },
};

export function buildMuzzle(ctx: BuildCtx, b: HumanoidBody, headColor: string): ((w: Record<string, number>, ms: MouthSolve) => void) | null {
  const look = ctx.id.looks.muzzle;
  if (!look || look === 'none' || !MUZZLE[look]) return null;
  const { n, reg, id } = ctx;
  const h = b.h;
  const spec = MUZZLE[look];
  const lenF = 1 + 0.45 * n('muzzle.length');
  const wF = 1 + 0.35 * n('muzzle.width');
  const hF = 1 + 0.35 * n('muzzle.height');
  const bridge = n('muzzle.bridge');
  const W = spec.w * h * wF;
  const H = spec.hg * h * hF;
  const Ln = spec.len * h * lenF;
  const p = new THREE.Vector3();
  b.surface.hit(0, b.noseY - 0.03 * h, p);
  const rootG = new THREE.Group();
  rootG.position.set(0, b.noseY - 0.035 * h, p.z - 0.06 * h);
  b.g.head.add(rootG);
  const skinMat = ctx.mat(headColor, b.coverage > 0 ? 'fur' : 'skin');
  const bellyMat = ctx.mat(b.coverage > 0 ? mixHex(headColor, id.colors.belly, 0.7) : headColor, b.coverage > 0 ? 'fur' : 'skin');
  const darkMat = ctx.mat('#2a1a1c', 'dark');
  const cavity = ctx.mat('#6a1e24', 'dark');
  const teethMat = ctx.mat('#fbf8f2', 'skin');
  const beakMat = ctx.mat(id.colors.beak, 'leather');
  const upper = new THREE.Group();
  rootG.add(upper);
  const jaw = new THREE.Group();
  jaw.position.set(0, -H * 0.45, 0.02 * h);
  rootG.add(jaw);

  if (look === 'bird') {
    const hook = id.looks.beak === 'strong' ? 1 : id.looks.beak === 'slight' ? 0.5 : 0;
    const top = reg.add(upper, taperTube([V(0, 0, 0), V(0, -H * 0.1, Ln * 0.5), V(0, -H * (0.3 + hook * 0.5), Ln * (1 + hook * 0.05))], W * 0.95, W * 0.05, 12, 0.75), beakMat, { region: 'muzzle', name: 'CHR_Beak_Upper' });
    top.position.z = 0.02 * h;
    reg.add(jaw, taperTube([V(0, 0, 0), V(0, -H * 0.05, Ln * 0.45), V(0, 0, Ln * 0.8)], W * 0.8, W * 0.05, 12, 0.5), beakMat, { region: 'muzzle', name: 'CHR_Beak_Lower' });
    reg.ellipsoid(rootG, cavity, V(0, -H * 0.3, Ln * 0.25), V(W * 0.7, H * 0.4, Ln * 0.5), { region: 'muzzle', pickable: false });
  } else {
    const bridgeLift = 0.03 * h * bridge;
    reg.ellipsoid(upper, skinMat, V(0, bridgeLift, Ln * 0.45), V(W, H, Ln), { region: 'muzzle', name: 'CHR_Muzzle' });
    if (bridge > -0.9) reg.ellipsoid(upper, skinMat, V(0, H * 0.6 + bridgeLift, Ln * 0.05), V(W * 0.55, H * (0.55 + 0.3 * bridge), Ln * 0.65), { region: 'muzzle' });
    reg.ellipsoid(jaw, bellyMat, V(0, -H * 0.1, Ln * 0.4), V(W * 0.85, H * 0.55, Ln * 0.92), { region: 'muzzle', name: 'CHR_Muzzle_Jaw' });
    reg.ellipsoid(rootG, cavity, V(0, -H * 0.42, Ln * 0.4), V(W * 0.78, H * 0.35, Ln * 0.85), { region: 'muzzle', pickable: false });
    if (spec.nosePad) {
      reg.ellipsoid(upper, darkMat, V(0, H * 0.55 + bridgeLift, Ln * 0.45 + Ln * 0.9), V(W * 0.32, H * 0.28, H * 0.25), { region: 'muzzle', name: 'CHR_NosePad' });
    } else {
      for (const s of S) reg.ellipsoid(upper, darkMat, V(s * W * 0.3, H * 0.5 + bridgeLift, Ln * 1.3), V(W * 0.06, H * 0.06, H * 0.05), { region: 'muzzle', pickable: false });
    }
    if (look === 'feline' || look === 'lagomorph' || look === 'canine') {
      for (const s of S) reg.ellipsoid(upper, bellyMat, V(s * W * 0.45, -H * 0.1, Ln * 1.05), V(W * 0.5, H * 0.55, H * 0.55), { region: 'muzzle' });
    }
    if (look === 'lagomorph') {
      for (const s of S) reg.box(upper, teethMat, V(s * W * 0.1, -H * 0.55, Ln * 1.3), V(W * 0.18, H * 0.4, H * 0.08), { region: 'muzzle', pickable: false });
    }
    if (spec.teeth) {
      for (const s of S) for (let i = 0; i < 5; i += 1) {
        const t = 0.3 + i * 0.16;
        reg.cone(upper, teethMat, V(s * W * 0.75 * (1 - t * 0.3), -H * 0.55, Ln * (t * 1.25)), V(0, -1, 0), W * 0.06, H * 0.25, { region: 'muzzle', pickable: false });
      }
    }
    if (look === 'fish' || look === 'frog') {
      const lip = reg.add(rootG, new THREE.TorusGeometry(1, 0.08, 8, 28, Math.PI), ctx.mat(mixHex(headColor, '#5a2a2a', 0.35), 'skin'), { region: 'muzzle' });
      lip.scale.set(W * 0.95, W * 0.95, H * 1.2);
      lip.rotation.set(Math.PI / 2, 0, Math.PI);
      lip.position.set(0, -H * 0.42, Ln * 0.45);
    }
  }
  const fang = id.looks.fangs && id.looks.fangs !== 'none' ? (id.looks.fangs === 'long' ? 1.6 : 1) * (1 + 0.8 * Math.max(0, n('fang.length'))) : 0;
  const fangs: THREE.Mesh[] = [];
  if (fang > 0) {
    for (const s of S) fangs.push(reg.cone(upper, teethMat, V(s * W * 0.55, -H * 0.65, Ln * (look === 'bird' ? 0.6 : 1.1)), V(0, -1, 0.1), W * 0.1, H * 0.35 * fang, { region: 'mouth', name: 'CHR_Fang' }));
  }
  const whisk = id.looks.whiskers;
  if (whisk && whisk !== 'none') {
    const count = Math.round(2 + Math.max(0, n('whisker.density')) * 4);
    const len = (whisk === 'long' ? 0.4 : 0.25) * h;
    const wm = ctx.mat('#f4f0e8', 'skin');
    for (const s of S) for (let i = 0; i < count; i += 1) {
      const a = (i / Math.max(1, count - 1) - 0.5) * 0.6;
      reg.limb(upper, wm, V(s * W * 0.7, -H * 0.05, Ln * 1.05), V(s * (W * 0.7 + len), -H * 0.05 + Math.sin(a) * len * 0.6, Ln * 1.05 + len * 0.15), 0.0016, 0.0006, { region: 'muzzle', pickable: false });
    }
  }
  const corners: THREE.Mesh[] = [];
  if (look !== 'bird') {
    for (const s of S) {
      const c = reg.add(rootG, new THREE.TorusGeometry(1, 0.18, 6, 12, Math.PI * 0.6), darkMat, { region: 'mouth', pickable: false });
      c.scale.setScalar(H * 0.35);
      c.position.set(s * W * 0.88, -H * 0.42, Ln * 0.4);
      c.rotation.y = s * Math.PI / 2;
      corners.push(c);
    }
  }
  (b as HumanoidBody & { muzzleTop?: THREE.Vector3 }).muzzleTop = rootG.position.clone().add(V(0, H * 0.9, Ln * (look === 'heavy' ? 0.9 : 0.6)));
  socket(ctx, 'SOC-Muzzle', rootG, V(0, 0, Ln));

  const jawScale = jaw.scale.clone();
  const upperPos = upper.position.clone();
  return (w, ms) => {
    const open = Math.min(1, ms.jaw + (ms.openUp + ms.openDown) * 0.9);
    jaw.rotation.x = open * (look === 'bird' ? 0.5 : 0.55);
    const wide = (ms.halfW - 0.72) * 0.9;
    jaw.scale.set(jawScale.x * (1 + wide * 0.4), jawScale.y, jawScale.z * (1 - wide * 0.1));
    const snarl = (w['PF-Snarl'] ?? 0) + (w['PF-Disgust'] ?? 0) * 0.5;
    upper.position.set(upperPos.x, upperPos.y + snarl * H * 0.12, upperPos.z);
    upper.rotation.x = -snarl * 0.08;
    for (const f of fangs) f.scale.y = H * 0.35 * fang * (1 + snarl * 0.5);
    corners.forEach((c, i) => {
      const cornerLift = i === 0 ? ms.cornerL : ms.cornerR;
      c.rotation.z = (i === 0 ? 1 : -1) * cornerLift * 1.4 - open * 0.4 + Math.PI * 1.2;
      c.visible = open < 0.5;
    });
  };
}

export function buildEars(ctx: BuildCtx, b: HumanoidBody, headColor: string) {
  const look = ctx.id.looks.ears;
  if (!look || look === 'human' || look === 'none') return;
  const { n, reg, id } = ctx;
  const h = b.h;
  const size = 1 + 0.4 * n('earEl.size');
  const lift = n('earEl.lift');
  const spread = n('earEl.spread');
  const outer = ctx.mat(headColor, b.coverage > 0 ? 'fur' : 'skin');
  const inner = ctx.mat(mixHex(id.colors.belly, '#f0a0a8', 0.35), 'skin');
  const membrane = ctx.mat(id.colors.membrane, 'skin', { opacity: 0.92 });
  const mane = ctx.mat(id.colors.mane, 'fur');
  S.forEach((s, i) => {
    const g = new THREE.Group();
    const top = look === 'round' || look === 'pointed' || look === 'long';
    const az = s * (top ? 0.78 : 1.5);
    const el = top ? 0.82 + lift * 0.18 : 0.05 + lift * 0.1;
    const root = scalpPoint(b.headR, az, el, 0.92);
    g.position.copy(root);
    const up = top ? root.clone().normalize().add(V(0, 0.8, -0.1)) : V(s, 0.25, -0.8);
    orient(g, up);
    g.rotateZ(-s * spread * 0.45);
    b.g.head.add(g);
    if (top) b.earGaps.push(root.clone().normalize());
    if (look === 'round') {
      reg.ellipsoid(g, outer, V(0, 0.08 * h * size, 0), V(0.11 * h * size, 0.1 * h * size, 0.035 * h), { region: 'ears', name: `CHR_Ear_${i ? 'R' : 'L'}` });
      reg.ellipsoid(g, inner, V(0, 0.08 * h * size, 0.02 * h), V(0.065 * h * size, 0.06 * h * size, 0.015 * h), { region: 'ears', pickable: false });
    } else if (look === 'pointed') {
      const m = reg.cone(g, outer, V(0, 0, 0), V(0, 1, 0), 0.085 * h * size, 0.24 * h * size, { region: 'ears', name: `CHR_Ear_${i ? 'R' : 'L'}` });
      m.scale.z *= 0.35;
      const m2 = reg.cone(g, inner, V(0, 0.02 * h, 0.018 * h), V(0, 1, 0), 0.05 * h * size, 0.17 * h * size, { region: 'ears', pickable: false });
      m2.scale.z *= 0.2;
    } else if (look === 'long') {
      reg.ellipsoid(g, outer, V(0, 0.28 * h * size, 0), V(0.065 * h * size, 0.3 * h * size, 0.03 * h), { region: 'ears', name: `CHR_Ear_${i ? 'R' : 'L'}` });
      reg.ellipsoid(g, inner, V(0, 0.27 * h * size, 0.018 * h), V(0.04 * h * size, 0.24 * h * size, 0.012 * h), { region: 'ears', pickable: false });
      g.rotateX(-0.15 - lift * 0.3);
    } else if (look === 'fin') {
      for (let k = 0; k < 3; k += 1) {
        const f = reg.cone(g, membrane, V(0, 0, 0), V(0, 1, (k - 1) * 0.5), 0.05 * h * size, 0.2 * h * size * (1 - Math.abs(k - 1) * 0.25), { region: 'ears', name: `CHR_Ear_${i ? 'R' : 'L'}` });
        f.scale.x *= 0.25;
      }
    } else if (look === 'feathered') {
      for (let k = 0; k < 3; k += 1) {
        const f = reg.ellipsoid(g, mane, V(0, 0.12 * h * size, -k * 0.03 * h), V(0.03 * h, 0.13 * h * size * (1 - k * 0.15), 0.012 * h), { region: 'ears', name: `CHR_Ear_${i ? 'R' : 'L'}` });
        f.rotation.x = -0.3 - k * 0.25;
      }
    }
    socket(ctx, `SOC-Ear_${i ? 'R' : 'L'}`, g, V(0, 0, 0));
  });
}

export function buildHorns(ctx: BuildCtx, b: HumanoidBody) {
  const look = ctx.id.looks.horns;
  if (!look || look === 'none') return;
  const { n, reg, id } = ctx;
  const h = b.h;
  const len = 1 + 0.5 * n('horn.length');
  const th = 1 + 0.45 * n('horn.thickness');
  const curve = 0.5 + 0.5 * n('horn.curve');
  const mat = ctx.mat(id.colors.horn, 'scale');
  const top = (b as HumanoidBody & { muzzleTop?: THREE.Vector3 }).muzzleTop;
  if (look === 'nose' || look === 'twinNose') {
    const base = top ?? V(0, b.noseY + 0.03 * h, b.headR.z * 0.95);
    const count = look === 'twinNose' ? 2 : 1;
    for (let i = 0; i < count; i += 1) {
      const p0 = base.clone().add(V(0, 0, -i * 0.09 * h));
      const L = 0.2 * h * len * (i ? 0.6 : 1);
      reg.add(b.g.head, taperTube([p0, p0.clone().add(V(0, L * 0.6, L * 0.15)), p0.clone().add(V(0, L, -L * 0.25 * curve))], 0.055 * h * th * (i ? 0.8 : 1), 0.004 * h), mat, { region: 'horns', name: 'CHR_Horn' });
    }
    return;
  }
  S.forEach((s) => {
    const root = scalpPoint(b.headR, s * 0.5, 0.95, 0.95);
    b.earGaps.push(root.clone().normalize());
    const L = 0.35 * h * len;
    let pts: THREE.Vector3[];
    if (look === 'straight') pts = [root, root.clone().add(V(s * L * 0.2, L * 0.55, -L * 0.05)), root.clone().add(V(s * L * 0.35, L, -L * 0.1))];
    else if (look === 'curved') pts = [root, root.clone().add(V(s * L * 0.35, L * 0.45, -L * 0.25)), root.clone().add(V(s * L * 0.6, L * 0.55, -L * 0.1 + L * 0.5 * curve)), root.clone().add(V(s * L * 0.7, L * (0.3 + 0.4 * (1 - curve)), L * 0.45 * curve))];
    else if (look === 'swept') pts = [root, root.clone().add(V(s * L * 0.15, L * 0.3, -L * 0.4)), root.clone().add(V(s * L * 0.25, L * (0.3 + 0.2 * curve), -L * 0.95))];
    else {
      const g = new THREE.Group();
      g.position.copy(scalpPoint(b.headR, s * 1.35, 0.35, 0.95));
      b.g.head.add(g);
      for (let k = 0; k < 3; k += 1) {
        const f = reg.cone(g, ctx.mat(id.colors.membrane, 'skin', { opacity: 0.9 }), V(0, 0, -k * 0.04 * h), V(s * 0.4, 1, -0.6 - k * 0.3), 0.05 * h * th, 0.28 * h * len * (1 - k * 0.2), { region: 'horns', name: 'CHR_HeadFin' });
        f.scale.x *= 0.25;
      }
      return;
    }
    reg.add(b.g.head, taperTube(pts, 0.055 * h * th, 0.004 * h, 12), mat, { region: 'horns', name: 'CHR_Horn' });
  });
}

export function buildMane(ctx: BuildCtx, b: HumanoidBody) {
  const look = ctx.id.looks.mane;
  if (!look || look === 'none') return;
  const { n, reg, id } = ctx;
  const h = b.h;
  const len = 1 + 0.5 * n('mane.length');
  const vol = 1 + 0.45 * n('mane.volume');
  const mat = ctx.mat(id.colors.mane, 'fur', { tip: mixHex(id.colors.mane, '#ffffff', 0.2), kind: 'hair', highlight: 0.4 });
  const R = b.headR;
  if (look === 'mane') {
    const count = 26;
    for (let i = 0; i < count; i += 1) {
      const a = (i / count) * Math.PI * 2;
      const dir = V(Math.cos(a), Math.sin(a) * 1.1, -0.35).normalize();
      const p0 = V(Math.cos(a) * R.x * 0.85, Math.sin(a) * R.y * 0.9 - 0.08 * h, -0.08 * h);
      const L = 0.3 * h * len * (a > Math.PI * 1.1 && a < Math.PI * 1.9 ? 1.25 : 1);
      reg.add(b.g.head, taperTube([p0, p0.clone().addScaledVector(dir, L * 0.5).add(V(0, -L * 0.1, -L * 0.1)), p0.clone().addScaledVector(dir, L).add(V(0, -L * 0.3, -L * 0.2))], 0.07 * h * vol, 0.01 * h, 8, 0.6), mat, { region: 'mane', name: 'CHR_Mane' });
    }
    for (let i = 0; i < 10; i += 1) {
      const a = Math.PI + (i / 9) * Math.PI;
      const p0 = V(Math.cos(a) * b.dims.neckR * 1.3, -0.55 * h, Math.sin(a) * b.dims.neckR * 1.3 * -1);
      reg.add(b.g.head, taperTube([p0, p0.clone().add(V(Math.cos(a) * 0.1 * h, -0.2 * h * len, 0.05 * h)), p0.clone().add(V(Math.cos(a) * 0.15 * h, -0.35 * h * len, 0.02 * h))], 0.08 * h * vol, 0.01 * h, 8, 0.6), mat, { region: 'mane' });
    }
  } else if (look === 'crest') {
    for (let i = 0; i < 6; i += 1) {
      const el = 1.3 - i * 0.32;
      const p0 = V(0, Math.sin(el) * R.y * 0.95, Math.cos(el) * R.z * 0.95 * (el > Math.PI / 2 ? 1 : 1));
      const sz = (1 - Math.abs(i - 1.5) * 0.15) * len;
      const f = reg.cone(b.g.head, ctx.mat(id.colors.mane, 'scale'), p0, p0.clone().normalize().add(V(0, 0.3, -0.5)), 0.08 * h * vol, 0.22 * h * sz, { region: 'mane', name: 'CHR_Crest' });
      f.scale.x *= 0.22;
    }
  } else {
    for (let i = 0; i < 6; i += 1) {
      const a = (i / 5 - 0.5) * 0.9;
      const p0 = scalpPoint(R, a, 1.1, 0.96);
      const f = reg.ellipsoid(b.g.head, mat, p0.clone().add(V(0, 0.1 * h * len, -0.12 * h * len)), V(0.035 * h * vol, 0.2 * h * len, 0.012 * h), { region: 'mane', name: 'CHR_HeadFeathers' });
      f.rotation.set(-0.9, a * 0.8, 0);
    }
  }
}

export function buildFrill(ctx: BuildCtx, b: HumanoidBody) {
  const look = ctx.id.looks.frill;
  if (!look || look === 'none') return;
  const { n, reg, id } = ctx;
  const h = b.h;
  if (look === 'gills') {
    const dm = ctx.mat(mixHex(b.bodyColor, '#3a1a2a', 0.6), 'dark');
    for (const s of S) for (let i = 0; i < 3; i += 1) {
      const m = reg.box(b.g.neck, dm, V(s * b.dims.neckR * 0.95, b.dims.neckLen * 0.5 + i * 0.035 * h * (1 + 0.3 * n('frill.size')), 0.01 * h), V(0.006 * h, 0.012 * h, 0.07 * h * (1 + 0.3 * n('frill.size'))), { region: 'frill', name: 'CHR_Gills' });
      m.rotation.y = s * 0.3;
    }
    return;
  }
  const size = 0.42 * h * (1 + 0.4 * n('frill.size'));
  const flare = 0.5 + 0.5 * Math.max(0, n('frill.flare'));
  const arc = Math.PI * (0.8 + 0.5 * flare);
  const g = new THREE.CircleGeometry(size, 24, -Math.PI / 2 - arc / 2 + Math.PI, arc);
  const mat = ctx.mat(id.colors.membrane, 'skin', { opacity: 0.94, side: THREE.DoubleSide });
  const m = reg.add(b.g.head, g, mat, { region: 'frill', name: 'CHR_Frill' });
  m.position.set(0, -0.32 * h, -0.1 * h);
  m.rotation.x = -0.35 - 0.4 * (1 - flare);
  const rib = ctx.mat(mixHex(id.colors.membrane, '#000000', 0.35), 'scale');
  for (let i = 0; i < 7; i += 1) {
    const a = -Math.PI / 2 - arc / 2 + Math.PI + (i / 6) * arc;
    reg.limb(m, rib, V(0, 0, 0.002), V(Math.cos(a) * size * 0.98, Math.sin(a) * size * 0.98, 0.002), 0.006 * h, 0.002 * h, { region: 'frill', pickable: false });
  }
}

export function buildHands(ctx: BuildCtx, b: HumanoidBody) {
  const { n, reg, id } = ctx;
  const look = id.looks.hands ?? 'human';
  const u = b.u;
  const hs = 1 + 0.15 * n('hand.size');
  const fl = (1 + 0.25 * n('finger.length')) * (b.child ? 0.9 : 1);
  const digit = 1 + 0.6 * Math.max(0, n('digit.emphasis'));
  const claw = Math.max(0, n('claw.length'));
  const nailLen = Math.max(0, n('nail.length'));
  const skin = b.armMat;
  const nail = ctx.mat(b.nailColor, 'leather');
  const clawMat = ctx.mat(id.colors.claw, 'scale');
  const web = ctx.mat(mixHex(b.bodyColor, id.colors.belly, 0.5), 'skin', { opacity: 0.9, side: THREE.DoubleSide });
  S.forEach((s, i) => {
    const wr = b.g.wr[i];
    const palmL = b.dims.handLen * 0.5;
    const palmW = u * 0.2 * hs * (look === 'paw' ? 1.25 : 1);
    reg.ellipsoid(wr, skin, V(0, -palmL * 0.5, 0), V(u * 0.075 * hs * (look === 'paw' ? 1.3 : 1), palmL * 0.55, palmW * 0.5), { region: 'hands', name: `CHR_Hand_${i ? 'R' : 'L'}` });
    const fingers = look === 'talon' ? 3 : 4;
    const tips: THREE.Vector3[] = [];
    for (let f = 0; f < fingers; f += 1) {
      const z = ((f / (fingers - 1)) - 0.5) * palmW * 0.8;
      const lenF = (look === 'paw' ? 0.45 : look === 'talon' ? 1.2 : 1) * (1 - Math.abs(f - (fingers - 1) / 2) * 0.12) * fl;
      const L1 = u * 0.18 * lenF;
      const r = u * 0.032 * hs * digit * (look === 'paw' ? 1.5 : 1);
      const a = V(0, -palmL * 0.95, z);
      const m1 = a.clone().add(V(-s * L1 * 0.12, -L1, z * 0.06));
      const tip = m1.clone().add(V(-s * L1 * 0.35, -L1 * 0.85, 0));
      reg.limb(wr, skin, a, m1, r, r * 0.9, { region: 'hands' });
      reg.limb(wr, skin, m1, tip, r * 0.9, r * 0.75, { region: 'hands' });
      tips.push(tip);
      if (look === 'human' || look === 'webbed') {
        const nm = reg.ellipsoid(wr, nail, tip.clone().add(V(s * r * 0.55, -r * 0.1 - nailLen * r * 0.8, 0)), V(r * 0.35, r * (0.8 + nailLen * 1.8), r * 0.75), { region: 'hands', name: 'CHR_Nail' });
        void nm;
      } else {
        const cl = u * (0.04 + 0.12 * claw) * (look === 'talon' ? 1.5 : 1);
        reg.cone(wr, clawMat, tip, V(-s * 0.4, -1, 0), r * 0.6, cl, { region: 'hands', name: 'CHR_Claw' });
      }
    }
    const tb = V(s * u * 0.02, -palmL * 0.3, palmW * 0.45);
    const tt = tb.clone().add(V(-s * u * 0.05, -u * 0.12 * fl, u * 0.1));
    reg.limb(wr, skin, tb, tt, u * 0.034 * hs * digit, u * 0.028 * hs, { region: 'hands' });
    if (look === 'webbed' && tips.length > 1) {
      for (let f = 0; f < tips.length - 1; f += 1) {
        const a = V(0, -palmL * 0.9, tips[f].z);
        const bb = V(0, -palmL * 0.9, tips[f + 1].z);
        const g = new THREE.BufferGeometry().setFromPoints([a, tips[f].clone().lerp(a, 0.25), tips[f + 1].clone().lerp(bb, 0.25), bb]);
        g.setIndex([0, 1, 2, 0, 2, 3]);
        g.computeVertexNormals();
        g.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 0, 1, 1, 1, 1, 0], 2));
        reg.add(wr, g, web, { region: 'hands', pickable: false });
      }
    }
  });
}

export function buildFeet(ctx: BuildCtx, b: HumanoidBody) {
  const { n, reg, id } = ctx;
  const look = id.looks.feet ?? 'human';
  const u = b.u;
  const claw = Math.max(0, n('claw.length'));
  const digit = 1 + 0.5 * Math.max(0, n('digit.emphasis'));
  const fs = 1 + 0.15 * n('foot.size');
  const nailLen = Math.max(0, n('nail.length'));
  const skin = b.legMat;
  const nail = ctx.mat(b.nailColor, 'leather');
  const clawMat = ctx.mat(id.colors.claw, 'scale');
  const web = ctx.mat(mixHex(b.bodyColor, id.colors.belly, 0.5), 'skin', { opacity: 0.9, side: THREE.DoubleSide });
  S.forEach((s, i) => {
    const ankle = b.g.ankle[i];
    const hip = b.g.hip[i];
    const knee = b.g.knee[i];
    const footG = new THREE.Group();
    footG.position.set(0, -b.dims.metaLen, 0);
    ankle.add(footG);
    footG.rotation.x = -(hip.rotation.x + knee.rotation.x + ankle.rotation.x);
    ankle.userData.foot = footG;
    const FL = b.dims.footLen;
    const digi = b.digitigrade;
    const heelZ = digi ? 0 : -FL * 0.18;
    const main = reg.ellipsoid(footG, skin, V(0, -u * 0.08, heelZ + FL * 0.4 * (digi ? 0.6 : 1)), V(u * 0.13 * fs * (look === 'paw' || look === 'webbed' ? 1.25 : 1), u * 0.09, FL * (digi ? 0.3 : 0.5)), { region: 'feet', name: `CHR_Foot_${i ? 'R' : 'L'}` });
    main.userData.ground = true;
    if (b.shoes) return;
    const toes = look === 'talon' ? 3 : look === 'human' ? 5 : 4;
    const front = heelZ + FL * (digi ? 0.75 : 0.85);
    for (let t = 0; t < toes; t += 1) {
      const x = ((t / (toes - 1)) - 0.5) * u * 0.22 * fs * (look === 'paw' ? 1.3 : 1);
      const r = u * (look === 'human' ? 0.035 : 0.045) * digit * (t === (s > 0 ? toes - 1 : 0) && look === 'human' ? 1.25 : 1);
      const L = u * (look === 'talon' ? 0.28 : look === 'human' ? 0.07 : 0.1) * (1 - Math.abs(t - (toes - 1) / 2) * 0.08);
      const a = V(x * (look === 'talon' ? 1.6 : 1), -u * 0.12, front);
      const bb = a.clone().add(V(x * (look === 'talon' ? 0.8 : 0.1), -u * 0.02, L));
      const toe = reg.limb(footG, skin, a, bb, r, r * 0.85, { region: 'feet' });
      toe.userData.ground = true;
      if (look === 'human' || look === 'webbed') {
        reg.ellipsoid(footG, nail, bb.clone().add(V(0, r * 0.45, -r * 0.2 + nailLen * r * 0.3)), V(r * 0.7, r * 0.25, r * (0.6 + nailLen)), { region: 'feet', name: 'CHR_Toenail', pickable: false });
      } else {
        reg.cone(footG, clawMat, bb, V(0, -0.35, 1), r * 0.55, u * (0.05 + 0.12 * claw) * (look === 'talon' ? 1.4 : 1), { region: 'feet', name: 'CHR_Claw' });
      }
    }
    if (look === 'talon') {
      const a = V(0, -u * 0.12, heelZ);
      const back = reg.limb(footG, skin, a, a.clone().add(V(0, -u * 0.02, -u * 0.16)), u * 0.04 * digit, u * 0.03, { region: 'feet' });
      back.userData.ground = true;
      reg.cone(footG, clawMat, a.clone().add(V(0, -u * 0.02, -u * 0.16)), V(0, -0.3, -1), u * 0.025, u * (0.05 + 0.1 * claw), { region: 'feet' });
    }
    if (look === 'webbed') {
      const g = new THREE.CircleGeometry(u * 0.2 * fs, 12, Math.PI * 0.15, Math.PI * 0.7);
      const m = reg.add(footG, g, web, { region: 'feet', pickable: false });
      m.rotation.x = -Math.PI / 2;
      m.position.set(0, -u * 0.13, front - u * 0.02);
    }
  });
}

const TAIL: Record<string, { len: number; r0: number; r1: number; droop: number; curl: number }> = {
  feline: { len: 1.8, r0: 0.09, r1: 0.055, droop: -0.9, curl: 0.16 },
  canine: { len: 1.3, r0: 0.13, r1: 0.05, droop: -0.6, curl: 0.12 },
  lizard: { len: 2.8, r0: 0.3, r1: 0.03, droop: -1.1, curl: 0.12 },
  fish: { len: 1.5, r0: 0.22, r1: 0.06, droop: -1.0, curl: 0.12 },
  bird: { len: 0.5, r0: 0.14, r1: 0.1, droop: -0.8, curl: 0 },
  serpent: { len: 4.6, r0: 0.34, r1: 0.03, droop: -1.35, curl: 0.22 },
  puff: { len: 0.1, r0: 0.1, r1: 0.1, droop: -0.4, curl: 0 },
};

export function buildTail(ctx: BuildCtx, b: HumanoidBody): ((f: FrameState) => void) | null {
  const look = ctx.id.looks.tail;
  if (!look || look === 'none' || !TAIL[look]) return null;
  const { n, reg, id } = ctx;
  const u = b.u;
  const spec = TAIL[look];
  const lenF = n('tail.length') >= 0 ? 1 + n('tail.length') * 0.5 : 1 + n('tail.length') * 0.4;
  const th = 1 + 0.45 * n('tail.thickness');
  const tip = 1 + 0.6 * n('tail.tip');
  const mat = ctx.mat(b.bodyColor, b.coverage > 0 ? 'fur' : 'skin');
  const tipMat = ctx.mat(look === 'feline' ? id.colors.mane : mixHex(b.bodyColor, id.colors.surfaceSecondary, 0.4), 'fur');
  const base = new THREE.Group();
  base.position.set(0, -u * 0.02, -b.dims.hipD * 0.85);
  b.g.pelvis.add(base);
  socket(ctx, 'SOC-Tail', base, V(0, 0, 0));
  const segs: THREE.Group[] = [];
  const count = look === 'puff' ? 1 : 10;
  const segLen = (spec.len * u * lenF) / count;
  let parent: THREE.Object3D = base;
  for (let i = 0; i < count; i += 1) {
    const g = new THREE.Group();
    if (i > 0) g.position.set(0, 0, -segLen);
    g.rotation.x = i === 0 ? spec.droop : spec.curl * (look === 'serpent' && i < 4 ? 1.4 : 1);
    parent.add(g);
    segs.push(g);
    const t0 = i / count;
    const t1 = (i + 1) / count;
    const r0 = u * (spec.r0 + (spec.r1 - spec.r0) * t0) * th;
    const r1 = u * (spec.r0 + (spec.r1 - spec.r0) * t1) * th;
    if (look !== 'puff') reg.limb(g, mat, V(0, 0, 0), V(0, 0, -segLen * 1.05), r0, r1, { region: 'tail', name: 'CHR_Tail' });
    parent = g;
  }
  const end = segs[segs.length - 1];
  const endP = V(0, 0, -segLen);
  if (look === 'puff') reg.ellipsoid(end, ctx.mat(id.colors.belly, 'fur'), V(0, 0, -u * 0.08), V(u * 0.2 * tip, u * 0.2 * tip, u * 0.2 * tip), { region: 'tail', name: 'CHR_Tail' });
  if (look === 'feline' && tip > 1.05) reg.ellipsoid(end, tipMat, endP, V(u * 0.1 * tip, u * 0.1 * tip, u * 0.16 * tip), { region: 'tail' });
  if (look === 'canine') reg.ellipsoid(end, tipMat, endP.clone().multiplyScalar(0.6), V(u * 0.14 * tip, u * 0.14 * tip, u * 0.26 * tip), { region: 'tail' });
  if (look === 'fish') {
    const fm = ctx.mat(id.colors.membrane, 'skin', { opacity: 0.9 });
    for (const s of [1, -1]) {
      const c = reg.cone(end, fm, endP, V(0, s * 0.8, -1), u * 0.18 * tip, u * 0.5 * tip, { region: 'tail' });
      c.scale.x *= 0.15;
    }
  }
  if (look === 'bird') {
    const fm = ctx.mat(id.colors.surfaceSecondary, 'fur');
    for (let k = 0; k < 5; k += 1) {
      const a = (k / 4 - 0.5) * 1.1;
      const e = reg.ellipsoid(end, fm, V(Math.sin(a) * u * 0.25 * tip, 0, -u * 0.35 * tip), V(u * 0.06, u * 0.015, u * 0.4 * tip), { region: 'tail' });
      e.rotation.y = a;
    }
  }
  const phys = id.physics.tail;
  const bases = segs.map((g) => g.rotation.clone());
  return (f) => {
    if (!phys.enabled) return;
    const amp = phys.amount * (1 - phys.stiffness * 0.6) * 0.14;
    segs.forEach((g, i) => {
      g.rotation.y = bases[i].y + Math.sin(f.time * 1.7 - i * 0.55) * amp * (0.4 + i * 0.12);
      g.rotation.x = bases[i].x + Math.sin(f.time * 1.1 - i * 0.4) * amp * 0.3;
    });
  };
}

export function buildWings(ctx: BuildCtx, b: HumanoidBody): ((f: FrameState) => void) | null {
  const look = ctx.id.looks.wings;
  if (!look || look === 'none') return null;
  const { n, reg, id } = ctx;
  const u = b.u;
  const spanF = n('wing.span') >= 0 ? 1 + n('wing.span') * 0.4 : 1 + n('wing.span') * 0.4;
  const fold = (n('wing.fold') + 1) / 2;
  const boneMat = ctx.mat(mixHex(b.bodyColor, '#000000', 0.15), b.coverage > 0 ? 'scale' : 'skin');
  const mem = ctx.mat(id.colors.membrane, 'skin', { opacity: 0.93, side: THREE.DoubleSide });
  const feather = ctx.mat(id.colors.surfaceSecondary === '#2a1e1a' ? '#f4f0e8' : id.colors.surfaceSecondary, 'fur', { side: THREE.DoubleSide });
  const featherTip = ctx.mat(b.bodyColor, 'fur', { side: THREE.DoubleSide });
  const anchor = socket(ctx, 'SOC-Wings', b.g.chest, V(0, b.dims.torsoLen * 0.22, -b.dims.chestD * 0.85));
  const roots: THREE.Group[] = [];
  const elbows: THREE.Group[] = [];
  const span = (look === 'fin' ? 1.2 : 2.6) * u * spanF;
  S.forEach((s, i) => {
    const root = new THREE.Group();
    root.position.set(s * u * 0.18, 0, 0);
    anchor.add(root);
    root.rotation.set(0, s * (0.35 + fold * 0.9), s * (0.55 - fold * 0.75));
    const elbow = new THREE.Group();
    const armLen = span * 0.42;
    elbow.position.set(s * armLen, 0, 0);
    elbow.rotation.z = s * -(0.4 + fold * 1.4);
    root.add(elbow);
    roots.push(root);
    elbows.push(elbow);
    socket(ctx, `SOC-Wing_${i ? 'R' : 'L'}`, root, V(s * armLen * 0.5, 0, 0));
    if (look === 'fin') {
      const g = new THREE.CircleGeometry(span * 0.5, 16, 0, Math.PI * 0.55);
      const m = reg.add(root, g, mem, { region: 'wings', name: 'CHR_Wing' });
      m.scale.x = s;
      m.rotation.y = Math.PI / 2;
      return;
    }
    reg.limb(root, boneMat, V(0, 0, 0), V(s * armLen, 0, 0), u * 0.06, u * 0.045, { region: 'wings', name: 'CHR_Wing' });
    const foreLen = span * 0.58;
    const rays = look === 'membrane' ? 4 : 0;
    const tipsLocal: THREE.Vector3[] = [];
    for (let r = 0; r < rays; r += 1) {
      const a = -0.25 - r * 0.42;
      const tip = V(s * Math.cos(a) * foreLen * (1 - r * 0.12), Math.sin(a) * foreLen * (1 - r * 0.12), 0);
      reg.limb(elbow, boneMat, V(0, 0, 0), tip, u * 0.035, u * 0.01, { region: 'wings' });
      tipsLocal.push(tip);
    }
    if (look === 'membrane') {
      const pts: number[] = [];
      const idx: number[] = [];
      const uvs: number[] = [];
      pts.push(0, 0, 0);
      uvs.push(0, 1);
      for (const t of tipsLocal) {
        pts.push(t.x, t.y, t.z);
        uvs.push(1, 0.5);
      }
      const bodyPt = V(-s * armLen * 0.9, -span * 0.35, 0);
      pts.push(bodyPt.x, bodyPt.y, bodyPt.z);
      uvs.push(0, 0);
      for (let k = 1; k < tipsLocal.length; k += 1) {
        const mid = tipsLocal[k - 1].clone().lerp(tipsLocal[k], 0.5).multiplyScalar(0.72);
        const mi = pts.length / 3;
        pts.push(mid.x, mid.y, mid.z);
        uvs.push(0.7, 0.4);
        idx.push(0, k, mi, 0, mi, k + 1);
      }
      idx.push(0, tipsLocal.length, tipsLocal.length + 1);
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
      g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
      g.setIndex(idx);
      g.computeVertexNormals();
      reg.add(elbow, g, mem, { region: 'wings' });
      const inner = new THREE.BufferGeometry();
      inner.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, -s * armLen, 0, 0, bodyPt.x, bodyPt.y, 0], 3));
      inner.setAttribute('uv', new THREE.Float32BufferAttribute([0, 1, 1, 1, 0, 0], 2));
      inner.setIndex([0, 1, 2]);
      inner.computeVertexNormals();
      reg.add(elbow, inner, mem, { region: 'wings' });
    } else {
      for (let k = 0; k < 9; k += 1) {
        const t = k / 8;
        const a = -0.2 - t * 1.1;
        const L = foreLen * (0.55 + 0.45 * (1 - t));
        const e = reg.ellipsoid(elbow, k % 2 ? featherTip : feather, V(s * Math.cos(a) * L * 0.5, Math.sin(a) * L * 0.5, -k * 0.002), V(L * 0.5, u * 0.09, u * 0.012), { region: 'wings' });
        e.rotation.z = s > 0 ? a : Math.PI - a;
      }
      for (let k = 0; k < 6; k += 1) {
        const t = k / 5;
        const e = reg.ellipsoid(root, feather, V(s * armLen * t, -u * 0.12, 0.003), V(u * 0.08, u * 0.22, u * 0.012), { region: 'wings' });
        e.rotation.z = -s * 0.3;
      }
    }
  });
  const phys = id.physics.wings;
  const base = roots.map((r) => r.rotation.clone());
  return (f) => {
    if (!phys.enabled) return;
    const amp = phys.amount * (1 - phys.stiffness * 0.7) * 0.08;
    roots.forEach((r, i) => {
      r.rotation.z = base[i].z + Math.sin(f.time * 1.3) * amp * (i ? -1 : 1);
    });
  };
}

export function buildTufts(ctx: BuildCtx, b: HumanoidBody) {
  const surface = ctx.id.looks.surface;
  if (surface !== 'longFur' && surface !== 'feathers' && b.tuft < 0.2) return;
  if (surface === 'skin' || surface === 'scales' || surface === 'hide' || surface === 'amphibian') return;
  const { reg, id } = ctx;
  const h = b.h;
  const u = b.u;
  const extra = 1 + b.tuft * 0.6;
  const mat = ctx.mat(b.bodyColor, 'fur', { tip: mixHex(b.bodyColor, id.colors.belly, 0.5), kind: 'hair', highlight: 0.2 });
  for (const s of S) {
    for (let k = 0; k < 3; k += 1) {
      const p0 = V(s * b.headR.x * 0.85, -0.2 * h - k * 0.05 * h, 0.05 * h);
      reg.add(b.g.head, taperTube([p0, p0.clone().add(V(s * 0.1 * h * extra, -0.04 * h, -0.02 * h)), p0.clone().add(V(s * 0.16 * h * extra, -0.1 * h, -0.05 * h))], 0.035 * h, 0.004 * h, 6, 0.5), mat, { region: 'cheeks', pickable: false });
    }
  }
  b.g.el.forEach((el, i) => {
    const s = S[i];
    for (let k = 0; k < 3; k += 1) {
      const p0 = V(s * b.dims.foreR * 0.4, -k * 0.06 * u, -b.dims.foreR * 0.8);
      reg.add(el, taperTube([p0, p0.clone().add(V(0, -0.08 * u, -0.15 * u * extra))], 0.05 * u, 0.005 * u, 6, 0.5), mat, { region: 'arms', pickable: false });
    }
  });
  for (let k = 0; k < 5; k += 1) {
    const x = (k / 4 - 0.5) * b.dims.chestW;
    const p0 = V(x, b.dims.torsoLen * 0.3, b.dims.chestD * 0.9);
    reg.add(b.g.chest, taperTube([p0, p0.clone().add(V(x * 0.1, -0.12 * u, 0.1 * u * extra))], 0.07 * u, 0.006 * u, 6, 0.5), mat, { region: 'chest', pickable: false });
  }
}
