import * as THREE from 'three';
import { mixHex } from '../model/character';
import type { Region } from '../model/types';
import { leafLayers } from '../model/appearance';
import { applyMouthUniforms, BrowRibbon, eyeGeometry, eyeMaterial, mouthMaterial, solveBrow, solveEye, solveMouth, squareToDiscUv, type BrowShape } from './face';
import { facialHairGeometry, hairGeometry, scalpShell, type HairHead } from './hair';
import { conformGrid, HeadSurface, hashString, V } from './parts';
import { groundSnap, poseAngles, socket, type BuildCtx } from './rig';
import { faceTexture, surfaceTexture, wrinkleTexture, type FaceLayout } from './textures';
import { toon, type ToonMaterial } from './toonMaterial';
import { buildEars, buildFeet, buildFrill, buildHands, buildHorns, buildMane, buildMuzzle, buildTail, buildTufts, buildWings } from './elements';
import { buildHumanoidAccessories } from './accessories';

export interface LimbShape {
  parent: THREE.Object3D;
  kind: 'limb' | 'ell';
  a?: THREE.Vector3;
  b?: THREE.Vector3;
  r0?: number;
  r1?: number;
  pos?: THREE.Vector3;
  radii?: THREE.Vector3;
}

export interface HumanoidBody {
  child: boolean;
  u: number;
  h: number;
  g: {
    root: THREE.Group;
    pelvis: THREE.Group;
    spine: THREE.Group;
    chest: THREE.Group;
    neck: THREE.Group;
    head: THREE.Group;
    jaw: THREE.Group;
    sh: THREE.Group[];
    el: THREE.Group[];
    wr: THREE.Group[];
    hip: THREE.Group[];
    knee: THREE.Group[];
    ankle: THREE.Group[];
  };
  shapes: Record<string, LimbShape>;
  dims: {
    chestW: number; chestD: number; waistW: number; waistD: number; hipW: number; hipD: number; torsoLen: number; waistY: number;
    upperLen: number; foreLen: number; thighLen: number; shinLen: number; neckLen: number; neckR: number;
    armR: number; foreR: number; thighR: number; calfR: number; shoulderHalf: number; footLen: number; handLen: number; metaLen: number;
  };
  headR: THREE.Vector3;
  surface: HeadSurface;
  layout: FaceLayout;
  eye: { x: number; y: number; w: number; h: number };
  mouthY: number;
  noseY: number;
  digitigrade: boolean;
  skin: string;
  bodyColor: string;
  furColor: string;
  coverage: number;
  tuft: number;
  headMat: ToonMaterial;
  bodyMat: ToonMaterial;
  armMat: ToonMaterial;
  legMat: ToonMaterial;
  nailColor: string;
  lipColor: string;
  earGaps: THREE.Vector3[];
  shoes: boolean;
}

const S = [1, -1];

function layerTint(layers: { category: string; color: string; opacity: number; hidden: boolean }[], category: string, base: string): string {
  let c = base;
  for (const l of layers) if (l.category === category && !l.hidden) c = mixHex(c, l.color, l.opacity);
  return c;
}

export function buildHumanoid(ctx: BuildCtx): { root: THREE.Group; head: THREE.Object3D; body: HumanoidBody } {
  const { id, n, reg } = ctx;
  const child = id.bodyKind === 'child';
  const L = id.looks;
  const colors = id.colors;
  const pos = (k: string) => Math.max(0, n(k));
  const neg = (k: string) => Math.max(0, -n(k));
  const boneF = (k: string, lo: number, hi: number) => (n(k) >= 0 ? 1 + n(k) * (hi - 1) : 1 + n(k) * (1 - lo));

  const surface = L.surface ?? 'skin';
  const covV = n('surface.coverage');
  const coverage = surface === 'skin' ? 0 : Math.max(0, Math.min(1, 1 + Math.min(0, covV)));
  const tuft = surface === 'skin' ? 0 : Math.max(0, covV);
  const skin = colors.skin;
  const furColor = colors.surfacePrimary;
  const bodyColor = coverage > 0 ? mixHex(skin, furColor, coverage) : skin;
  const young = neg('age.years');
  const old = pos('age.years');

  const heightF = boneF('body.height', 0.9, 1.1);
  const baseH = child ? 1.22 : 1.72;
  const u = (baseH * heightF) / (child ? 5.3 : 7.35);
  const headScale = boneF('head.size', 0.9, 1.15) * (child ? 1.0 : 1.18);
  const h = u * headScale;

  const bulk = n('body.bulk');
  const soft = pos('body.soft');
  const shoulderF = boneF('body.shoulders', 0.85, 1.15);
  const hipF = boneF('body.hips', 0.85, 1.15);
  const legDigi = L.legs === 'digitigrade';

  const dims = {
    chestW: u * (child ? 0.58 : 0.78) * (1 + 0.12 * bulk + 0.05 * pos('muscle.chest') + 0.06 * n('body.shoulders')),
    chestD: u * (child ? 0.44 : 0.5) * (1 + 0.12 * bulk + 0.1 * pos('muscle.chest')),
    waistW: u * (child ? 0.48 : 0.6) * (1 - 0.14 * n('body.waist') + 0.2 * bulk + 0.1 * n('body.belly') + 0.05 * soft),
    waistD: u * (child ? 0.38 : 0.44) * (1 + 0.25 * n('body.belly') + 0.15 * bulk + 0.06 * soft),
    hipW: u * (child ? 0.6 : 0.7) * hipF * (1 + 0.1 * bulk + 0.08 * n('body.hips')),
    hipD: u * (child ? 0.44 : 0.5) * (1 + 0.1 * bulk + 0.12 * n('body.glute')),
    torsoLen: u * (child ? 1.6 : 2.2) * boneF('torso.length', 0.85, 1.15),
    waistY: 0,
    upperLen: u * (child ? 0.85 : 1.3) * boneF('upperArm.length', 0.85, 1.15),
    foreLen: u * (child ? 0.78 : 1.1) * boneF('forearm.length', 0.85, 1.15),
    thighLen: u * (child ? 1.15 : 1.95) * boneF('thigh.length', 0.85, 1.15),
    shinLen: u * (child ? 1.1 : 1.9) * boneF('shin.length', 0.85, 1.15),
    neckLen: u * (child ? 0.26 : 0.36) * boneF('neck.length', 0.85, 1.15),
    neckR: u * (child ? 0.1 : 0.165) * (1 + 0.28 * n('neck.thickness') + 0.08 * bulk),
    armR: u * (child ? 0.16 : 0.19) * (1 + 0.22 * n('upperArm.bulk') + 0.15 * bulk + 0.12 * pos('muscle.arms') + 0.05 * soft),
    foreR: u * (child ? 0.14 : 0.16) * (1 + 0.22 * n('forearm.bulk') + 0.12 * bulk + 0.1 * pos('muscle.arms')),
    thighR: u * (child ? 0.26 : 0.3) * (1 + 0.22 * n('thigh.bulk') + 0.15 * bulk + 0.1 * pos('muscle.legs') + 0.08 * soft),
    calfR: u * (child ? 0.18 : 0.2) * (1 + 0.22 * n('calf.bulk') + 0.1 * bulk + 0.1 * pos('muscle.legs')),
    shoulderHalf: u * (child ? 0.72 : 0.88) * shoulderF * (1 + 0.06 * bulk),
    footLen: u * (child ? 0.62 : 0.95) * boneF('foot.length', 0.85, 1.15) * (1 + 0.15 * n('foot.size')),
    handLen: u * (child ? 0.5 : 0.62) * boneF('hand.length', 0.85, 1.15) * (1 + 0.15 * n('hand.size')),
    metaLen: legDigi ? u * (child ? 0.45 : 0.62) : 0,
  };
  if (legDigi) {
    dims.shinLen *= 0.82;
  }

  const layers = id.appearance;
  const seed = hashString(id.name + id.archetype);
  const surfaceBase = {
    base: skin, primary: furColor, secondary: colors.surfaceSecondary, belly: colors.belly, pattern: L.pattern ?? 'plain', surface,
    coverage, seed, hairColor: colors.brow,
  };
  const bodyTex = surfaceTexture({ ...surfaceBase, bellyWidth: 0.2, veins: 0, hair: child ? 0 : pos('skin.bodyHair'), layers: layers.body, zone: 'body' });
  const armTex = surfaceTexture({ ...surfaceBase, bellyWidth: 0.08, veins: child ? 0 : pos('skin.veins'), hair: child ? 0 : pos('skin.armHair'), layers: layers.arms, zone: 'arms' });
  const legTex = surfaceTexture({ ...surfaceBase, bellyWidth: 0.08, veins: 0, hair: child ? 0 : pos('skin.bodyHair') * 0.6, layers: layers.legs, zone: 'legs' });
  const kindFor = surface === 'scales' || surface === 'hide' ? 'scale' : surface === 'skin' || surface === 'amphibian' ? 'skin' : 'fur';
  const bodyMat = toon({ color: '#ffffff', kind: kindFor, map: bodyTex });
  const armMat = toon({ color: '#ffffff', kind: kindFor, map: armTex });
  const legMat = toon({ color: '#ffffff', kind: kindFor, map: legTex });
  if (surface === 'amphibian') {
    for (const m of [bodyMat, armMat, legMat]) m.uniforms.uSpec.value = 0.5;
  }

  const root = new THREE.Group();
  root.name = 'CHR_Armature';
  const pelvis = new THREE.Group();
  const spine = new THREE.Group();
  const chest = new THREE.Group();
  const neckG = new THREE.Group();
  const headG = new THREE.Group();
  const jawG = new THREE.Group();
  root.add(pelvis);
  pelvis.add(spine);
  const hipY = u * 0.18 + dims.shinLen + dims.thighLen + dims.metaLen;
  pelvis.position.set(0, hipY, 0);
  chest.position.set(0, dims.torsoLen * 0.5, 0);
  spine.add(chest);
  neckG.position.set(0, dims.torsoLen * 0.5, 0);
  chest.add(neckG);
  neckG.add(headG);
  headG.position.set(0, dims.neckLen + h * 0.5, h * 0.05);
  headG.add(jawG);

  const pose = poseAngles(ctx.pose);
  const stoop = pos('age.stoop');
  spine.rotation.x = pose.spine + stoop * 0.22;
  neckG.rotation.x = -stoop * 0.12 + 0.04;
  headG.rotation.x = -stoop * 0.1 - pose.spine * 0.6;

  const shapes: Record<string, LimbShape> = {};
  const ell = (tag: string, parent: THREE.Object3D, mat: THREE.Material, p: THREE.Vector3, r: THREE.Vector3, region: Region) => {
    shapes[tag] = { parent, kind: 'ell', pos: p.clone(), radii: r.clone() };
    return reg.ellipsoid(parent, mat, p, r, { region, name: tag });
  };
  const limb = (tag: string, parent: THREE.Object3D, mat: THREE.Material, a: THREE.Vector3, b: THREE.Vector3, r0: number, r1: number, region: 'arms' | 'legs' | 'neck' | 'body' | 'shoulders') => {
    shapes[tag] = { parent, kind: 'limb', a: a.clone(), b: b.clone(), r0, r1 };
    return reg.limb(parent, mat, a, b, r0, r1, { region, name: tag });
  };

  ell('pelvis', pelvis, legMat, V(0, u * 0.05, 0), V(dims.hipW, u * 0.42, dims.hipD), 'hips');
  for (const s of S) ell(`glute${s}`, pelvis, legMat, V(s * dims.hipW * 0.42, -u * 0.02, -dims.hipD * 0.35), V(u * 0.32 * (1 + 0.2 * n('body.glute')), u * 0.32, u * 0.3 * (1 + 0.35 * n('body.glute'))), 'hips');
  dims.waistY = dims.torsoLen * 0.3;
  ell('waist', spine, bodyMat, V(0, dims.waistY, dims.waistD * 0.06 * n('body.belly')), V(dims.waistW, dims.torsoLen * 0.3, dims.waistD), 'waist');
  ell('chest', chest, bodyMat, V(0, dims.torsoLen * 0.12, 0), V(dims.chestW, dims.torsoLen * 0.34, dims.chestD), 'chest');
  const chestVol = child ? 0 : n('body.chest');
  if (!child && (chestVol > 0.05 || pos('muscle.chest') > 0.05)) {
    const r = u * (0.24 + 0.12 * Math.max(chestVol, 0)) * (1 + 0.1 * bulk);
    for (const s of S) ell(`bust${s}`, chest, bodyMat, V(s * dims.chestW * 0.42, dims.torsoLen * 0.12, dims.chestD * 0.55), V(r * 1.05, r * (chestVol > 0 ? 0.95 : 0.7), r * (0.55 + 0.35 * Math.max(chestVol, 0))), 'chest');
  }
  if (!child && pos('muscle.abs') > 0.2) {
    for (let i = 0; i < 3; i += 1) for (const s of S) reg.ellipsoid(spine, bodyMat, V(s * u * 0.12, dims.waistY + u * (0.25 - i * 0.22), dims.waistD * 0.88), V(u * 0.1, u * 0.09, u * 0.05 * pos('muscle.abs')), { region: 'waist' });
  }
  ell('trap', chest, bodyMat, V(0, dims.torsoLen * 0.38, -dims.chestD * 0.1), V(dims.shoulderHalf * 0.85, u * 0.2, dims.chestD * 0.7), 'shoulders');
  limb('neck', neckG, bodyMat, V(0, -u * 0.1, 0), V(0, dims.neckLen + h * 0.2, 0), dims.neckR, dims.neckR * 0.92, 'neck');

  const sh: THREE.Group[] = [];
  const el: THREE.Group[] = [];
  const wr: THREE.Group[] = [];
  const hip: THREE.Group[] = [];
  const knee: THREE.Group[] = [];
  const ankle: THREE.Group[] = [];
  S.forEach((s, i) => {
    const shG = new THREE.Group();
    shG.position.set(s * dims.shoulderHalf, dims.torsoLen * 0.36, -u * 0.02);
    chest.add(shG);
    shG.rotation.z = s * pose.shoulder;
    shG.rotation.x = -pose.shoulderFwd;
    ell(`deltoid${i}`, shG, armMat, V(0, -u * 0.05, 0), V(dims.armR * 1.25, dims.armR * 1.3, dims.armR * 1.2), 'shoulders');
    limb(`upperArm${i}`, shG, armMat, V(0, 0, 0), V(0, -dims.upperLen, 0), dims.armR, dims.foreR * 1.02, 'arms');
    const elG = new THREE.Group();
    elG.position.set(0, -dims.upperLen, 0);
    elG.rotation.x = pose.elbow;
    shG.add(elG);
    limb(`forearm${i}`, elG, armMat, V(0, 0, 0), V(0, -dims.foreLen, 0), dims.foreR, dims.foreR * 0.62, 'arms');
    const wrG = new THREE.Group();
    wrG.position.set(0, -dims.foreLen, 0);
    elG.add(wrG);
    sh.push(shG);
    el.push(elG);
    wr.push(wrG);

    const hipG = new THREE.Group();
    hipG.position.set(s * dims.hipW * 0.5, -u * 0.05, 0);
    hipG.rotation.z = s * pose.hipSpread;
    hipG.rotation.x = pose.hipFwd + (legDigi ? -0.32 : 0);
    pelvis.add(hipG);
    limb(`thigh${i}`, hipG, legMat, V(0, 0, 0), V(0, -dims.thighLen, 0), dims.thighR, dims.calfR * 1.02, 'legs');
    const kG = new THREE.Group();
    kG.position.set(0, -dims.thighLen, 0);
    kG.rotation.x = pose.knee + (legDigi ? 0.95 : 0);
    hipG.add(kG);
    limb(`shin${i}`, kG, legMat, V(0, 0, 0), V(0, -dims.shinLen, 0), dims.calfR, dims.calfR * 0.55, 'legs');
    if (!child) ell(`calf${i}`, kG, legMat, V(0, -dims.shinLen * 0.3, -dims.calfR * 0.25), V(dims.calfR * 1.05, dims.shinLen * 0.25, dims.calfR * 1.05), 'legs');
    const aG = new THREE.Group();
    aG.position.set(0, -dims.shinLen, 0);
    aG.rotation.x = pose.ankle + (legDigi ? -0.63 : 0);
    kG.add(aG);
    if (legDigi) {
      limb(`meta${i}`, aG, legMat, V(0, 0, 0), V(0, -dims.metaLen, 0), dims.calfR * 0.55, dims.calfR * 0.45, 'legs');
    }
    hip.push(hipG);
    knee.push(kG);
    ankle.push(aG);
  });

  // Head
  const skullW = 1 + 0.1 * n('skull.width') + 0.07 * pos('face.heart') - 0.04 * pos('face.diamond') + 0.05 * pos('face.round');
  const R = V(0.39 * h * skullW, 0.43 * h * (1 + 0.06 * n('skull.crown') + 0.05 * pos('face.long')), 0.42 * h * (1 + 0.1 * n('skull.depth')));
  const faceSoft = n('face.softness');
  const jawWidth = 1 + 0.18 * n('jaw.width') + 0.14 * pos('face.square') + 0.1 * pos('face.round') - 0.16 * pos('face.heart') - 0.1 * pos('face.diamond') + 0.05 * faceSoft + 0.06 * pos('age.jawSoft');
  const jawLen = 1 + 0.14 * pos('face.long') + 0.06 * n('jaw.height');
  const jawC = V(0, -0.3 * h * jawLen - 0.03 * h * pos('age.jawSoft'), 0.07 * h);
  const jawR = V(0.3 * h * jawWidth * (child ? 1.05 : 1), 0.27 * h * jawLen * (1 + 0.05 * young), 0.31 * h);
  const chinW = 1 + 0.3 * n('chin.width') - 0.3 * pos('face.heart') - 0.2 * pos('face.diamond') + 0.2 * pos('face.square');
  const chinC = V(0, jawC.y - jawR.y * 0.72 - 0.035 * h * n('chin.length'), jawC.z + jawR.z * 0.55);
  const chinR = V(0.1 * h * chinW, 0.085 * h * (1 + 0.3 * n('chin.length')), 0.085 * h);
  const cheekR = 0.12 * h * (1 + 0.25 * n('cheek.full') + 0.18 * pos('face.round') + 0.12 * young + 0.08 * faceSoft);
  const cheekC = V(0.2 * h * (1 + 0.08 * n('cheek.bone') + 0.08 * pos('face.diamond')), -0.15 * h + 0.03 * h * n('cheek.bone'), 0.19 * h);

  const surf = new HeadSurface();
  surf.add(V(0, 0, 0), R);
  surf.add(jawC, jawR);
  surf.add(chinC, chinR);
  for (const s of S) surf.add(V(s * cheekC.x, cheekC.y, cheekC.z), V(cheekR, cheekR * 0.9, cheekR));
  const browRidge = n('brow.ridge');
  const ridgeC = V(0, 0.08 * h, 0.3 * h);
  const ridgeR = V(0.3 * h, 0.07 * h, 0.12 * h * (1 + 0.5 * browRidge));
  if (browRidge > 0.05) surf.add(ridgeC, ridgeR);

  const eyeSize = n('eye.size');
  const ew = 0.072 * h * (1 + 0.2 * eyeSize + 0.05 * young) * (child ? 1.12 : 1);
  const eh = ew * ((child ? 1.0 : 0.62) + 0.3 * pos('eye.round') - 0.38 * pos('eye.narrow') - 0.08 * pos('eye.almond') - 0.05 * old);
  const forward = n('eye.forward');
  const ex = 0.17 * h * (1 + 0.12 * n('eye.spacing')) * (1 - 0.18 * forward);
  const ey = -0.05 * h + 0.05 * h * n('eye.height');
  const eye = { x: ex, y: ey, w: ew, h: eh };
  const noseY = -0.25 * h - 0.02 * h * n('nose.length');
  const mouthY = -0.36 * h + 0.035 * h * n('mouth.height') - 0.02 * h * pos('face.long');
  const mouthW = 0.085 * h * (1 + 0.25 * n('mouth.width'));
  const browBase = n('brow.height');
  const browY = ey + eh * 1.45 + browBase * 0.35 * eh;
  const layout: FaceLayout = {
    cx: 0, cy: -0.08 * h, hx: 0.46 * h, hy: 0.52 * h,
    eyes: eye, mouth: { x: 0, y: mouthY, w: mouthW }, cheeks: { x: cheekC.x, y: cheekC.y - 0.02 * h, r: cheekR * 0.9 },
    nose: { x: 0, y: noseY }, browY, foreheadY: 0.24 * h, jawY: jawC.y - jawR.y * 0.5,
  };

  const headLayers = layers.head;
  const muzzle = L.muzzle && L.muzzle !== 'none' ? L.muzzle : null;
  const beard = id.facialHair?.beard;
  const faceTex = faceTexture({
    layout,
    blush: pos('skin.blush'),
    blushColor: '#f07a80',
    crease: pos('lid.crease') * 0.8 + pos('age.creases') * 0.4,
    creaseColor: mixHex(skin, '#6a3a30', 0.6),
    surface,
    coverage,
    pattern: L.pattern ?? 'plain',
    secondary: colors.surfaceSecondary,
    belly: colors.belly,
    muzzle: !!muzzle,
    stubble: !child && beard && beard.id === 'stubble' ? 0.5 + beard.bulk / 200 : 0,
    stubbleColor: beard?.color ?? '#3a2a20',
    layers: headLayers,
    seed,
  });
  const headColor = coverage > 0 ? mixHex(skin, furColor, coverage * 0.95) : skin;
  const headInv = new THREE.Matrix4();
  const headMat = toon({
    color: headColor,
    kind: kindFor,
    face: { map: faceTex, rect: new THREE.Vector4(layout.cx, layout.cy, layout.hx, layout.hy), front: 0.12 * h, headInv, radii: V(R.x, R.y, R.z * 1.15) },
    wrinkleMap: wrinkleTexture(layout),
  });
  const plainHead = ctx.mat(headColor, kindFor);

  reg.ellipsoid(headG, headMat, V(0, 0, 0), R, { region: 'skull', name: 'CHR_Head' });
  reg.ellipsoid(jawG, headMat, jawC, jawR, { region: 'jaw' });
  reg.ellipsoid(jawG, headMat, chinC, chinR, { region: 'jaw' });
  for (const s of S) reg.ellipsoid(headG, headMat, V(s * cheekC.x, cheekC.y, cheekC.z), V(cheekR, cheekR * 0.9, cheekR), { region: 'cheeks' });
  if (browRidge > 0.05) reg.ellipsoid(headG, headMat, ridgeC, ridgeR, { region: 'brows' });

  const lipColor = layerTint(leafLayers(headLayers), 'lips', colors.lip);
  const nailColor = layerTint(leafLayers(layers.nails), 'nails', colors.nail);
  const eyeShadow = leafLayers(headLayers).filter((l) => l.category === 'eyeshadow');

  // Eyes
  const eyeMats: THREE.ShaderMaterial[] = [];
  const tilt = 0.28 * n('eye.tilt') + 0.12 * n('eye.droop');
  const almond = pos('eye.almond');
  const irisSize = 0.62 * (1 + 0.25 * n('eye.irisSize')) * (child ? 1.05 : 1);
  const pupilSize = 0.42 * (1 + 0.4 * n('eye.pupilSize'));
  const catchL = 0.95 * (1 + n('eye.catchlight') * 0.5);
  const pupilStyle = { round: 0, slit: 1, wide: 2, star: 3 }[L.pupil ?? 'round'] ?? 0;
  const lash = 0.13 * (1 + 0.5 * n('lash.length')) * (child ? 0.8 : 1) * (1 + 0.25 * pos('face.softness'));
  S.forEach((s) => {
    const cxE = s * ex;
    const g = eyeGeometry(surf, cxE, ey, ew, eh, tilt, almond, s as 1 | -1);
    squareToDiscUv(g);
    const mat = eyeMaterial(s as 1 | -1);
    const u2 = mat.uniforms;
    u2.uIris.value.set(colors.iris);
    u2.uIrisDark.value.set(mixHex(colors.iris, '#06100e', 0.72));
    u2.uSclera.value.set(colors.sclera);
    u2.uSkin.value.set(coverage > 0.5 ? headColor : skin);
    u2.uLash.value.set(colors.lash);
    u2.uIrisSize.value = irisSize;
    u2.uPupilSize.value = pupilSize;
    u2.uPupilStyle.value = pupilStyle;
    u2.uCatch.value = catchL;
    u2.uLashT.value = lash;
    if (eyeShadow.length) {
      u2.uLidTint.value.set(eyeShadow[eyeShadow.length - 1].color);
      u2.uLidTintA.value = Math.min(0.8, eyeShadow.reduce((a, l) => a + l.opacity, 0));
    }
    reg.add(headG, g, mat, { region: 'eyes', name: s > 0 ? 'CHR_Eye_L' : 'CHR_Eye_R' });
    eyeMats.push(mat);
  });

  // Brows
  const browMat = ctx.mat(colors.brow, 'hair');
  const browThick = 0.055 * h * (1 + 0.45 * n('brow.thickness')) * (child ? 0.9 : 1) * (1 - 0.2 * pos('face.softness'));
  const browLen = 1 + 0.25 * n('brow.length');
  const browSpacing = n('brow.spacing');
  const browTilt = n('brow.tilt');
  const browRest: BrowShape[] = S.map((s) => ({
    inner: [s * (ex - ew * 0.85 * browLen + browSpacing * 0.02 * h), browY - eh * 0.08],
    mid: [s * (ex + ew * 0.05), browY + eh * 0.18],
    outer: [s * (ex + ew * 1.1 * browLen), browY - eh * 0.12 + browTilt * 0.3 * eh],
  }));
  const brows = S.map(() => new BrowRibbon(surf, reg, headG, browMat, browThick));

  // Nose and mouth
  const mouthMat = mouthMaterial();
  mouthMat.uniforms.uLip.value.set(lipColor);
  mouthMat.uniforms.uLipUpper.value = 0.5 + 0.5 * n('lip.upper') - 0.4 * pos('lip.thin') - 0.2 * old;
  mouthMat.uniforms.uLipLower.value = 0.6 + 0.5 * n('lip.lower') - 0.4 * pos('lip.thin') - 0.2 * old;
  mouthMat.uniforms.uFangs.value = L.fangs && L.fangs !== 'none' ? (L.fangs === 'long' ? 0.8 : 0.4) * (1 + pos('fang.length')) : 0;
  const lineCol = mixHex(lipColor, '#3a1a1a', 0.6);
  mouthMat.uniforms.uLine.value.set(lineCol);
  const restCorner = 0.12 * n('mouth.corner');
  let mouthMesh: THREE.Mesh | null = null;
  if (!muzzle) {
    const mg = conformGrid(surf, new THREE.Vector2(0, mouthY), mouthW * 1.35, mouthW * 0.95, 24, 14, 0.0015);
    mouthMesh = reg.add(jawG, mg, mouthMat, { region: 'mouth', name: 'CHR_Mouth' });
    const noseSize = (1 + 0.3 * n('nose.size')) * (child ? 0.85 : 1);
    const np = new THREE.Vector3();
    const nn = new THREE.Vector3();
    surf.hit(0, noseY, np, nn);
    const noseLen = 0.07 * h * noseSize * (1 + 0.3 * n('nose.length'));
    const bridge = 1 + 0.5 * n('nose.bridgeHeight');
    reg.ellipsoid(headG, plainHead, np.clone().add(V(0, 0.01 * h * n('nose.tipUp'), 0.01 * h)), V(0.035 * h * noseSize * (1 + 0.35 * n('nose.tipWidth') + 0.2 * pos('nose.nostril')), 0.04 * h * noseSize, noseLen * bridge * 1.0), { region: 'nose', name: 'CHR_Nose' });
    const bp = new THREE.Vector3();
    const bn = new THREE.Vector3();
    surf.hit(0, (noseY + ey) / 2, bp, bn);
    reg.ellipsoid(headG, plainHead, bp.add(V(0, 0, -0.012 * h)), V(0.022 * h * (1 + 0.4 * n('nose.bridgeWidth')), Math.abs(ey - noseY) * 0.55, 0.022 * h * bridge), { region: 'nose' });
    const nost = pos('nose.nostril');
    const nostMat = ctx.mat(mixHex(headColor, '#5a2a26', 0.5), 'dark');
    for (const s of S) reg.ellipsoid(headG, nostMat, np.clone().add(V(s * 0.014 * h * (1 + nost), -0.022 * h, noseLen * 0.35)), V(0.006 * h * (1 + nost), 0.004 * h, 0.004 * h), { region: 'nose', pickable: false });
  }

  // Human ears
  const earGaps: THREE.Vector3[] = [];
  if (L.ears === 'human' || !L.ears) {
    const es = (1 + 0.25 * n('ear.size')) * (child ? 1.05 : 1);
    const ePoint = pos('ear.point');
    const eOut = pos('ear.out');
    const eY = ey - 0.06 * h + 0.05 * h * n('ear.height');
    S.forEach((s, i) => {
      const eg = new THREE.Group();
      eg.position.set(s * R.x * 0.94, eY, -0.03 * h);
      eg.rotation.y = s * (0.3 + eOut * 0.55);
      headG.add(eg);
      reg.ellipsoid(eg, plainHead, V(s * 0.02 * h, 0, 0), V(0.035 * h * es, 0.1 * h * es, 0.065 * h * es), { region: 'ears', name: `CHR_Ear_${i ? 'R' : 'L'}` });
      reg.ellipsoid(eg, ctx.mat(mixHex(headColor, '#b0605a', 0.25), 'skin'), V(s * 0.035 * h, -0.005 * h, 0.01 * h), V(0.012 * h * es, 0.06 * h * es, 0.035 * h * es), { region: 'ears', pickable: false });
      if (pos('ear.lobe') > 0.05) reg.ellipsoid(eg, plainHead, V(s * 0.02 * h, -0.1 * h * es, 0.01 * h), V(0.03 * h, 0.035 * h * (1 + pos('ear.lobe')), 0.03 * h), { region: 'ears' });
      if (ePoint > 0.02) reg.cone(eg, plainHead, V(s * 0.02 * h, 0.06 * h * es, -0.02 * h), V(s * 0.25, 1, -0.55), 0.03 * h * es, 0.16 * h * ePoint * es, { region: 'ears' });
      socket(ctx, `SOC-Ear_${i ? 'R' : 'L'}`, eg, V(0, 0, 0));
    });
  }

  const body: HumanoidBody = {
    child, u, h,
    g: { root, pelvis, spine, chest, neck: neckG, head: headG, jaw: jawG, sh, el, wr, hip, knee, ankle },
    shapes, dims, headR: R, surface: surf, layout, eye, mouthY, noseY, digitigrade: legDigi,
    skin, bodyColor, furColor, coverage, tuft, headMat, bodyMat, armMat, legMat, nailColor, lipColor, earGaps,
    shoes: id.equipped.some((e) => e.slot === 'footwear'),
  };

  // Elements
  const muzzleRig = buildMuzzle(ctx, body, headColor);
  buildEars(ctx, body, headColor);
  buildHorns(ctx, body);
  buildMane(ctx, body);
  buildFrill(ctx, body);
  buildHands(ctx, body);
  buildFeet(ctx, body);
  const tailRig = buildTail(ctx, body);
  const wingRig = buildWings(ctx, body);
  buildTufts(ctx, body);

  // Hair
  const hairHead: HairHead = {
    r: R.clone(), u: h, collide: new HeadSurface(), gaps: earGaps, jaw: { c: jawC, r: jawR }, mouthY, noseY,
  };
  hairHead.collide.add(V(0, 0, 0), R);
  hairHead.collide.add(jawC, jawR);
  hairHead.collide.add(chinC, chinR);
  const neckTopY = -(h * 0.5 + dims.neckLen);
  hairHead.collide.add(V(0, neckTopY - u * 0.25, -u * 0.1), V(dims.shoulderHalf * 1.05, u * 0.45, dims.chestD * 1.15));
  hairHead.collide.add(V(0, neckTopY - dims.torsoLen * 0.35, -u * 0.05), V(dims.chestW * 1.05, dims.torsoLen * 0.4, dims.chestD * 1.08));
  hairHead.collide.add(V(0, -h * 0.55, -0.05 * h), V(dims.neckR * 1.1, h * 0.35, dims.neckR * 1.1));
  const headKey = [R.x, R.y, R.z, h, dims.shoulderHalf, dims.chestD, earGaps.map((g) => g.toArray().map((x) => x.toFixed(2)).join(',')).join(';')].map((x) => (typeof x === 'number' ? x.toFixed(4) : x)).join('|');
  const hairPieces: { slot: 'front' | 'back' | 'sides' | 'extra'; piece: typeof id.hair.front }[] = [
    { slot: 'back', piece: id.hair.back },
    { slot: 'front', piece: id.hair.front },
    { slot: 'sides', piece: id.hair.sides },
    ...id.hair.extras.map((p) => ({ slot: 'extra' as const, piece: p })),
  ];
  socket(ctx, 'SOC-HairScalp', headG, V(0, R.y, 0));
  socket(ctx, 'SOC-HairFront', headG, V(0, R.y * 0.7, R.z * 0.7));
  socket(ctx, 'SOC-HairSide_L', headG, V(R.x, 0, 0));
  socket(ctx, 'SOC-HairSide_R', headG, V(-R.x, 0, 0));
  socket(ctx, 'SOC-HairBack', headG, V(0, 0, -R.z));
  socket(ctx, 'SOC-HairExtra', headG, V(0, R.y, -R.z * 0.3));
  const hairGroup = new THREE.Group();
  hairGroup.name = 'CHR_Hair';
  headG.add(hairGroup);
  for (const { slot, piece } of hairPieces) {
    if (piece.id.startsWith('pack:')) {
      const pk = ctx.packs.get(piece.id.slice(5));
      const sockName = pk?.socket ?? (slot === 'front' ? 'SOC-HairFront' : slot === 'sides' ? 'SOC-HairSide_L' : slot === 'extra' ? 'SOC-HairExtra' : 'SOC-HairScalp');
      const sock = ctx.sockets[sockName];
      if (pk && sock) {
        const holder = new THREE.Group();
        holder.userData.pack = pk;
        holder.userData.packColors = { hair: piece.root };
        holder.userData.equipUid = `hair-${slot}-${pk.id}`;
        sock.add(holder);
        ctx.equipObjects[holder.userData.equipUid] = holder;
      }
      continue;
    }
    const mat = toon({ color: piece.root, tip: piece.tip, kind: 'hair', highlight: piece.highlight });
    if (slot === 'back') {
      const shell = scalpShell(hairHead, piece.id);
      if (shell) reg.ellipsoid(hairGroup, toon({ color: piece.root, kind: 'hair' }), shell.c, shell.r.clone().multiply(V(1, 0.93, 1)), { region: 'hair', name: 'CHR_HairScalp' });
    }
    if (slot === 'extra' && (piece.id === 'ribbon' || piece.id === 'band')) {
      const cm = ctx.mat(piece.tip, 'cloth');
      if (piece.id === 'band') {
        const t = reg.add(hairGroup, new THREE.TorusGeometry(1, 0.045, 8, 40, Math.PI), cm, { region: 'hair' });
        t.scale.set(R.x * 1.1, R.y * 1.1, R.x * 1.1);
        t.position.set(0, 0, R.z * 0.25);
        t.rotation.x = -0.45;
      } else {
        const bow = new THREE.Group();
        bow.position.set(0, R.y * 0.1, -R.z * 1.02);
        hairGroup.add(bow);
        for (const s of S) {
          const loop = reg.add(bow, new THREE.TorusGeometry(0.07 * h, 0.025 * h, 8, 16), cm, { region: 'hair' });
          loop.position.set(s * 0.07 * h, 0, 0);
          loop.scale.set(1, 0.6, 0.5);
          reg.box(bow, cm, V(s * 0.03 * h, -0.1 * h, 0), V(0.035 * h, 0.16 * h, 0.01 * h));
        }
        reg.ellipsoid(bow, cm, V(0, 0, 0), V(0.03 * h, 0.03 * h, 0.03 * h));
      }
      continue;
    }
    const g = hairGeometry(slot, piece, hairHead, headKey);
    if (g) reg.add(hairGroup, g, mat, { region: 'hair', name: `CHR_Hair_${slot}` });
  }
  if (!child) {
    const fh = id.facialHair;
    for (const kind of ['moustache', 'sideburns', 'beard'] as const) {
      const piece = fh[kind];
      const g = facialHairGeometry(kind, piece, { ...hairHead, collide: surf }, headKey + (muzzle ?? ''));
      if (g) reg.add(kind === 'sideburns' ? headG : jawG, g, toon({ color: piece.color, tip: mixHex(piece.color, '#ffffff', 0.15), kind: 'hair', highlight: 0.3 }), { region: 'hair', name: `CHR_${kind}` });
    }
  }

  // Sockets
  socket(ctx, 'SOC-HeadTop', headG, V(0, R.y * 0.95, 0));
  const ep = new THREE.Vector3();
  surf.hit(0, ey, ep);
  socket(ctx, 'SOC-Eyewear', headG, V(0, ey, ep.z));
  if (!child) {
    socket(ctx, 'SOC-Moustache', jawG, V(0, mouthY + 0.05 * h, jawR.z + jawC.z));
    socket(ctx, 'SOC-Beard', jawG, chinC);
    socket(ctx, 'SOC-Sideburn_L', headG, V(R.x * 0.95, noseY, 0.05 * h));
    socket(ctx, 'SOC-Sideburn_R', headG, V(-R.x * 0.95, noseY, 0.05 * h));
  }
  socket(ctx, 'SOC-Neck', neckG, V(0, dims.neckLen * 0.3, 0));
  socket(ctx, 'SOC-Chest', chest, V(0, dims.torsoLen * 0.12, dims.chestD));
  socket(ctx, 'SOC-Back', chest, V(0, dims.torsoLen * 0.18, -dims.chestD));
  socket(ctx, 'SOC-Cape', chest, V(0, dims.torsoLen * 0.36, -dims.chestD * 0.7));
  socket(ctx, 'SOC-Waist', spine, V(0, dims.waistY - dims.torsoLen * 0.12, 0));
  S.forEach((s, i) => {
    const sfx = i ? 'R' : 'L';
    socket(ctx, `SOC-Shoulder_${sfx}`, sh[i], V(0, 0, 0));
    socket(ctx, `SOC-UpperArm_${sfx}`, sh[i], V(0, -dims.upperLen * 0.5, 0));
    socket(ctx, `SOC-ForeArm_${sfx}`, el[i], V(0, -dims.foreLen * 0.5, 0));
    socket(ctx, `SOC-Hand_${sfx}`, wr[i], V(0, -dims.handLen * 0.45, 0));
    socket(ctx, `SOC-Weapon_${sfx}`, wr[i], V(0, -dims.handLen * 0.5, 0), new THREE.Euler(0, 0, 0));
    socket(ctx, `SOC-Hip_${sfx}`, hip[i], V(0, 0, 0));
    socket(ctx, `SOC-Thigh_${sfx}`, hip[i], V(0, -dims.thighLen * 0.5, 0));
    socket(ctx, `SOC-Shin_${sfx}`, knee[i], V(0, -dims.shinLen * 0.5, 0));
    socket(ctx, `SOC-Foot_${sfx}`, ankle[i], V(0, -dims.metaLen, 0));
    void s;
  });
  socket(ctx, 'SOC-OrganicForeArm_L', el[0], V(dims.foreR * 0.9, -dims.foreLen * 0.45, 0));

  buildHumanoidAccessories(ctx, body);

  const meshes = reg.meshes;
  groundSnap(root, meshes);

  // Performance
  const hood = pos('lid.hood') + old * 0.3;
  const baseHeadRot = headG.rotation.clone();
  const chestBase = chest.scale.clone();
  const shoulderBase = sh.map((g) => g.rotation.clone());
  const elbowBase = el.map((g) => g.rotation.clone());
  const jawBaseY = jawG.position.y;
  ctx.updaters.push((f) => {
    const w = f.w;
    headInv.copy(headG.matrixWorld).invert();
    const gz = f.perf.gaze;
    eyeMats.forEach((m, i) => {
      const side = i === 0 ? 'L' : 'R';
      const e = solveEye(w, side, hood, gz.y);
      const u2 = m.uniforms;
      u2.uUpper.value = e.upper;
      u2.uLower.value = e.lower;
      u2.uSqueeze.value = e.squeeze;
      u2.uGaze.value.set(gz.x + (i === 0 ? -1 : 1) * gz.converge * 0.3, gz.y);
    });
    brows.forEach((b, i) => b.update(solveBrow(w, i === 0 ? 'L' : 'R', browRest[i], eh)));
    const ms = solveMouth(w, restCorner, 0.72);
    applyMouthUniforms(mouthMat, ms);
    jawG.position.y = jawBaseY - ms.jaw * 0.035 * h;
    if (mouthMesh) mouthMesh.position.y = ms.jaw * 0.035 * h * 0.5;
    muzzleRig?.(w, ms);
    const wr2 = f.wrinkle;
    const ageCrease = pos('age.creases') * 0.45;
    headMat.uniforms.uWrinkle.value.set(
      (f.perf.wrinklePreview ? wr2.forehead : 0) + ageCrease,
      (f.perf.wrinklePreview ? Math.max(wr2.brow, wr2.nose) : 0) + ageCrease * 0.6,
      (f.perf.wrinklePreview ? wr2.eyes : 0) + ageCrease,
      (f.perf.wrinklePreview ? wr2.mouth : 0) + ageCrease * 0.8,
    );
    headG.rotation.set(baseHeadRot.x + f.perf.head.pitch * 0.5, baseHeadRot.y + f.perf.head.yaw * 0.7, baseHeadRot.z + f.perf.head.roll * 0.3);
    const br = 1 + Math.sin(f.time * 1.5) * 0.008;
    chest.scale.set(chestBase.x * br, chestBase.y, chestBase.z * br);
    if (pose.waveArm) {
      sh[1].rotation.set(shoulderBase[1].x - 0.1, shoulderBase[1].y, -2.55);
      el[1].rotation.set(elbowBase[1].x, elbowBase[1].y, -0.35 + Math.sin(f.time * 6) * 0.35);
    }
    tailRig?.(f);
    wingRig?.(f);
  });

  return { root, head: headG, body };
}
