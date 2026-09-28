import * as THREE from 'three';
import { mixHex } from '../model/character';
import { ACCESSORY_BY_ID } from '../model/looks';
import { colorsOf, equipRoot, gearMat, packPlaceholder } from './accessories';
import { taperTube } from './elements';
import { eyeMaterial, solveBrow, solveEye, solveMouth } from './face';
import { hashString, V } from './parts';
import { groundSnap, socket, type BuildCtx } from './rig';
import { surfaceTexture } from './textures';
import { toon } from './toonMaterial';

const S = [1, -1];

export function buildDragon(ctx: BuildCtx): { root: THREE.Group; head: THREE.Object3D } {
  const { id, n, reg } = ctx;
  const L = id.looks;
  const c = id.colors;
  const pos = (k: string) => Math.max(0, n(k));
  const boneF = (k: string, lo: number, hi: number) => (n(k) >= 0 ? 1 + n(k) * (hi - 1) : 1 + n(k) * (1 - lo));
  const young = Math.max(0, -n('age.years'));
  const old = pos('age.years');
  const size = boneF('beast.size', 0.6, 1.4) * (1 - young * 0.25);
  const u = 0.32 * size;
  const bulk = n('beast.bulk');
  const legF = boneF('beast.leg', 0.8, 1.25) * (1 - young * 0.05);
  const neckF = boneF('beast.neck', 0.7, 1.4);
  const tailF = boneF('beast.tail', 0.7, 1.4);
  const wingF = boneF('beast.wing', 0.7, 1.4);
  const fold = (n('beast.wingFold') + 1) / 2;
  const headF = boneF('beast.head', 0.85, 1.2) * (1 + young * 0.25);
  const posture = pos('age.posture');
  const wear = pos('age.wear');

  const seed = hashString(id.name + 'beast');
  const tex = surfaceTexture({
    base: c.surfacePrimary, primary: c.surfacePrimary, secondary: c.surfaceSecondary, belly: c.belly, pattern: L.pattern ?? 'plates', surface: 'scales',
    coverage: 1, seed, hairColor: c.surfacePrimary, bellyWidth: 0.22, veins: 0, hair: 0, layers: id.appearance.body, zone: 'body',
  });
  const scale = toon({ color: '#ffffff', kind: 'scale', map: tex, wear: wear * 0.8 });
  const belly = ctx.mat(c.belly, 'skin');
  const hornMat = ctx.mat(c.horn, 'scale', wear > 0 ? { wear } : undefined);
  const clawMat = ctx.mat(c.claw, 'scale');
  const mem = ctx.mat(c.membrane, 'skin', { opacity: 0.94, side: THREE.DoubleSide });
  const dark = ctx.mat('#2a1418', 'dark');
  const cavity = ctx.mat('#6a1e24', 'dark');
  const teeth = ctx.mat('#fbf8f2', 'skin');

  const bodyR = V(u * 1.05 * (1 + 0.2 * bulk), u * 1.0 * (1 + 0.15 * bulk), u * 2.1);
  const legLen = u * 2.2 * legF;
  const root = new THREE.Group();
  root.name = 'CHR_Armature';
  const body = new THREE.Group();
  body.position.y = legLen + bodyR.y * 0.4;
  root.add(body);
  reg.ellipsoid(body, scale, V(0, 0, 0), bodyR, { region: 'body', name: 'CHR_Body' });
  reg.ellipsoid(body, scale, V(0, u * 0.1, bodyR.z * 0.55), V(bodyR.x * 1.08, bodyR.y * 1.02, bodyR.z * 0.5), { region: 'chest' });
  reg.ellipsoid(body, belly, V(0, -bodyR.y * 0.45, 0), V(bodyR.x * 0.8, bodyR.y * 0.6, bodyR.z * 0.9), { region: 'body' });

  // Legs
  const legs: { hip: THREE.Group; knee: THREE.Group; front: boolean }[] = [];
  for (const front of [true, false]) {
    S.forEach((s) => {
      const hip = new THREE.Group();
      hip.position.set(s * bodyR.x * 0.72, -bodyR.y * 0.2, (front ? 1 : -1) * bodyR.z * 0.58);
      body.add(hip);
      const upper = legLen * 0.52;
      const lower = legLen * 0.5;
      const r = u * (front ? 0.36 : 0.42) * (1 + 0.2 * bulk);
      hip.rotation.x = front ? 0.12 : -0.3;
      reg.ellipsoid(hip, scale, V(0, -upper * 0.2, 0), V(r * 1.35, upper * 0.5, r * 1.4), { region: 'legs' });
      reg.limb(hip, scale, V(0, 0, 0), V(0, -upper, 0), r, r * 0.8, { region: 'legs', name: 'CHR_Leg' });
      const knee = new THREE.Group();
      knee.position.y = -upper;
      knee.rotation.x = front ? -0.2 : 0.62;
      hip.add(knee);
      reg.limb(knee, scale, V(0, 0, 0), V(0, -lower, 0), r * 0.8, r * 0.6, { region: 'legs' });
      const foot = new THREE.Group();
      foot.position.y = -lower;
      foot.rotation.x = -(hip.rotation.x + knee.rotation.x);
      knee.add(foot);
      const fm = reg.ellipsoid(foot, scale, V(0, -r * 0.3, r * 0.5), V(r * 1.1, r * 0.5, r * 1.3), { region: 'feet', name: 'CHR_Foot' });
      fm.userData.ground = true;
      const claw = u * (0.12 + 0.3 * pos('beast.claw')) * (1 + old * 0.2);
      for (let t = 0; t < 4; t += 1) {
        const x = (t - 1.5) * r * 0.55;
        const a = V(x, -r * 0.45, r * 1.3);
        const tip = a.clone().add(V(x * 0.3, -r * 0.2, r * 0.45));
        const toe = reg.limb(foot, scale, a, tip, r * 0.26, r * 0.2, { region: 'feet' });
        toe.userData.ground = true;
        reg.cone(foot, clawMat, tip, V(0, -0.5, 1), r * 0.16, claw, { region: 'feet' });
      }
      legs.push({ hip, knee, front });
    });
  }

  // Back ridge
  const back = L.beastBack ?? 'spines';
  const ridgeCount = 9;
  for (let i = 0; i < ridgeCount && back !== 'smooth'; i += 1) {
    const t = i / (ridgeCount - 1);
    const z = bodyR.z * (0.8 - t * 1.6);
    const y = bodyR.y * Math.sqrt(Math.max(0.05, 1 - ((z / bodyR.z) ** 2))) * 0.98;
    const hgt = u * (back === 'sail' ? 0.9 : back === 'plates' ? 0.45 : 0.35) * (1 - Math.abs(t - 0.45) * 0.8);
    if (back === 'spines') reg.cone(body, hornMat, V(0, y, z), V(0, 1, -0.5), u * 0.08, hgt, { region: 'body', name: 'CHR_BackRidge' });
    else if (back === 'plates') {
      const p = reg.cone(body, hornMat, V(0, y, z), V(0, 1, -0.2), u * 0.22, hgt, { region: 'body', name: 'CHR_BackRidge' });
      p.scale.z = u * 0.04;
      p.scale.x = u * 0.22;
    }
  }
  if (back === 'sail') {
    const g = new THREE.CircleGeometry(bodyR.z * 0.8, 20, 0, Math.PI);
    const m = reg.add(body, g, mem, { region: 'body', name: 'CHR_BackRidge' });
    m.rotation.y = Math.PI / 2;
    m.position.y = bodyR.y * 0.85;
    m.scale.y = 0.55;
  }

  // Neck and head
  const neckSegs: THREE.Group[] = [];
  let parent: THREE.Object3D = body;
  const neckCount = 5;
  const neckLen = u * 2.2 * neckF;
  const segLen = neckLen / neckCount;
  const neckBase = new THREE.Group();
  neckBase.position.set(0, bodyR.y * 0.35, bodyR.z * 0.9);
  const neckBend = 0.1 + posture * 0.03;
  neckBase.rotation.x = 0.5 + posture * 0.45;
  body.add(neckBase);
  parent = neckBase;
  for (let i = 0; i < neckCount; i += 1) {
    const g = new THREE.Group();
    if (i) g.position.y = segLen;
    g.rotation.x = i ? neckBend : 0;
    parent.add(g);
    const r0 = u * (0.55 - i * 0.05) * (1 + 0.15 * bulk);
    reg.limb(g, scale, V(0, 0, 0), V(0, segLen * 1.1, 0), r0, r0 * 0.9, { region: 'neck', name: i === 0 ? 'CHR_Neck' : undefined });
    reg.ellipsoid(g, belly, V(0, segLen * 0.5, r0 * 0.55), V(r0 * 0.6, segLen * 0.55, r0 * 0.5), { region: 'neck', pickable: false });
    if (back === 'spines' || back === 'plates') reg.cone(g, hornMat, V(0, segLen * 0.5, -r0 * 0.9), V(0, 0.3, -1), u * 0.06, u * 0.25, { region: 'neck', pickable: false });
    neckSegs.push(g);
    parent = g;
  }
  const head = new THREE.Group();
  head.position.y = segLen;
  head.rotation.x = -(neckBase.rotation.x + neckBend * (neckCount - 1)) + 0.15 + posture * 0.2;
  parent.add(head);
  const hs = u * headF;
  const snout = boneF('beast.snout', 0.7, 1.4);
  const jawW = 1 + 0.3 * n('beast.jaw');
  const skull = V(hs * 0.55, hs * 0.5, hs * 0.6);
  reg.ellipsoid(head, scale, V(0, hs * 0.1, 0), skull, { region: 'skull', name: 'CHR_Head' });
  const upperJaw = new THREE.Group();
  upperJaw.position.set(0, 0, hs * 0.3);
  head.add(upperJaw);
  const snLen = hs * 0.95 * snout;
  reg.ellipsoid(upperJaw, scale, V(0, hs * 0.02, snLen * 0.55), V(hs * 0.36 * jawW, hs * 0.26, snLen * 0.75), { region: 'muzzle', name: 'CHR_Muzzle' });
  for (const s of S) reg.ellipsoid(upperJaw, dark, V(s * hs * 0.13, hs * 0.18, snLen * 1.22), V(hs * 0.045, hs * 0.03, hs * 0.03), { region: 'muzzle', pickable: false });
  const jaw = new THREE.Group();
  jaw.position.set(0, -hs * 0.18, hs * 0.05);
  head.add(jaw);
  reg.ellipsoid(jaw, belly, V(0, -hs * 0.06, snLen * 0.75), V(hs * 0.32 * jawW, hs * 0.14, snLen * 0.72), { region: 'jaw', name: 'CHR_Jaw' });
  reg.ellipsoid(head, cavity, V(0, -hs * 0.12, hs * 0.3 + snLen * 0.5), V(hs * 0.28 * jawW, hs * 0.1, snLen * 0.7), { region: 'mouth', pickable: false });
  for (const s of S) for (let k = 0; k < 5; k += 1) {
    const t = 0.25 + k * 0.17;
    reg.cone(upperJaw, teeth, V(s * hs * 0.3 * jawW * (1 - t * 0.35), -hs * 0.2, snLen * (0.1 + t * 1.05)), V(0, -1, 0), hs * 0.03, hs * (k === 1 ? 0.14 : 0.08), { region: 'mouth', pickable: false });
  }
  // Eyes on the sides of the skull, looking forward and out
  const eyeK = (1 + 0.35 * n('beast.eye')) * (1 + young * 0.35);
  const eyeR = hs * 0.14 * eyeK;
  const eyeMats: THREE.ShaderMaterial[] = [];
  const browRidges: THREE.Mesh[] = [];
  S.forEach((s) => {
    const m = eyeMaterial(s as 1 | -1);
    m.uniforms.uIris.value.set(c.iris);
    m.uniforms.uIrisDark.value.set(mixHex(c.iris, '#06100e', 0.7));
    m.uniforms.uSclera.value.set(mixHex(c.sclera, c.iris, 0.35));
    m.uniforms.uSkin.value.set(c.surfacePrimary);
    m.uniforms.uLash.value.set(mixHex(c.surfacePrimary, '#000000', 0.5));
    m.uniforms.uIrisSize.value = 0.82;
    m.uniforms.uPupilSize.value = 0.35;
    m.uniforms.uPupilStyle.value = (L.beastPupil ?? 'slit') === 'slit' ? 1 : 0;
    m.uniforms.uCatch.value = 0.95;
    m.uniforms.uLashT.value = 0.08;
    const g = new THREE.CircleGeometry(eyeR, 24);
    const mesh = reg.add(head, g, m, { region: 'eyes', name: s > 0 ? 'CHR_Eye_L' : 'CHR_Eye_R' });
    const q = V(s * 0.8, 0.18, 0.58).normalize();
    const surfP = q.clone().multiply(skull).add(V(0, hs * 0.1, 0));
    const normal = V(q.x / skull.x, q.y / skull.y, q.z / skull.z).normalize();
    mesh.position.copy(surfP).addScaledVector(normal, hs * 0.012);
    mesh.quaternion.setFromUnitVectors(V(0, 0, 1), normal);
    eyeMats.push(m);
    const br = reg.ellipsoid(head, scale, surfP.clone().add(V(-s * eyeR * 0.1, eyeR * 1.05, 0)), V(eyeR * 1.1, eyeR * 0.35, eyeR * 0.9), { region: 'brows', name: s > 0 ? 'CHR_Brow_L' : 'CHR_Brow_R' });
    br.rotation.y = s * 0.6;
    browRidges.push(br);
  });
  // Horns, crest, ear fins
  const hornLook = L.beastHorns ?? 'swept';
  const hornK = (1 + 0.45 * n('beast.horn')) * (1 - young * 0.5) * (1 + old * 0.25);
  const hornBase = (s: number) => V(s * skull.x * 0.55, hs * 0.45, -skull.z * 0.3);
  if (hornLook !== 'none') {
    if (hornLook === 'single') {
      const b0 = V(0, hs * 0.2, hs * 0.3 + snLen * 0.95);
      reg.add(head, taperTube([b0, b0.clone().add(V(0, hs * 0.35 * hornK, hs * 0.05)), b0.clone().add(V(0, hs * 0.6 * hornK, -hs * 0.12))], hs * 0.09, hs * 0.01), hornMat, { region: 'horns', name: 'CHR_Horn' });
    }
    for (const s of S) {
      if (hornLook === 'single') break;
      const b0 = hornBase(s);
      const Lh = hs * 1.1 * hornK;
      let pts: THREE.Vector3[];
      if (hornLook === 'swept') pts = [b0, b0.clone().add(V(s * Lh * 0.1, Lh * 0.2, -Lh * 0.5)), b0.clone().add(V(s * Lh * 0.15, Lh * 0.35, -Lh))];
      else if (hornLook === 'curled') pts = [b0, b0.clone().add(V(s * Lh * 0.35, Lh * 0.1, -Lh * 0.4)), b0.clone().add(V(s * Lh * 0.5, -Lh * 0.3, -Lh * 0.3)), b0.clone().add(V(s * Lh * 0.45, -Lh * 0.35, Lh * 0.05))];
      else pts = [b0, b0.clone().add(V(s * Lh * 0.1, Lh * 0.5, -Lh * 0.15)), b0.clone().add(V(s * Lh * 0.15, Lh * 0.8, -Lh * 0.1))];
      reg.add(head, taperTube(pts, hs * 0.1 * (1 + 0.3 * pos('beast.horn')), hs * 0.01), hornMat, { region: 'horns', name: 'CHR_Horn' });
      if (hornLook === 'crown') {
        for (let k = 1; k <= 2; k += 1) {
          const b1 = V(s * skull.x * (0.55 + k * 0.15), hs * (0.4 - k * 0.1), -skull.z * (0.3 + k * 0.1));
          reg.cone(head, hornMat, b1, V(s * 0.3, 1, -0.4), hs * 0.06, Lh * (0.5 - k * 0.1), { region: 'horns' });
        }
      }
    }
  }
  const crest = L.beastCrest ?? 'none';
  const crestK = 1 + 0.45 * n('beast.crest');
  if (crest === 'ridge' || crest === 'spines') {
    for (let k = 0; k < 5; k += 1) {
      const p = V(0, skull.y * (1 - k * 0.12) + hs * 0.05, skull.z * (0.3 - k * 0.3));
      const m = reg.cone(head, hornMat, p, V(0, 1, -0.6), hs * (crest === 'ridge' ? 0.16 : 0.05), hs * 0.35 * crestK * (1 - k * 0.12), { region: 'mane', name: 'CHR_Crest' });
      if (crest === 'ridge') m.scale.x = hs * 0.03;
    }
  } else if (crest === 'fan') {
    const g = new THREE.CircleGeometry(hs * 0.7 * crestK, 16, Math.PI * 0.1, Math.PI * 0.8);
    const m = reg.add(head, g, mem, { region: 'mane', name: 'CHR_Crest' });
    m.rotation.y = Math.PI / 2;
    m.position.set(0, skull.y * 0.7, -skull.z * 0.4);
  }
  const fin = L.beastEarFin ?? 'none';
  if (fin !== 'none') {
    const fk = 1 + 0.45 * n('beast.earFin');
    for (const s of S) {
      const g = new THREE.Group();
      g.position.set(s * skull.x * 0.95, hs * 0.05, -skull.z * 0.45);
      g.rotation.set(0, s * 0.6, s * -0.3);
      head.add(g);
      const count = fin === 'frilled' ? 4 : 1;
      for (let k = 0; k < count; k += 1) {
        const f = reg.cone(g, fin === 'frilled' ? mem : scale, V(0, 0, 0), V(s * 0.8, 0.5 - k * 0.3, -1), hs * 0.18, hs * 0.55 * fk * (1 - k * 0.12), { region: 'ears', name: 'CHR_EarFin' });
        f.scale.x = hs * 0.03;
      }
    }
  }

  // Wings
  const wingRoots: THREE.Group[] = [];
  const span = u * 4.2 * wingF * (1 - young * 0.2);
  S.forEach((s, i) => {
    const rootW = new THREE.Group();
    rootW.position.set(s * bodyR.x * 0.6, bodyR.y * 0.75, bodyR.z * 0.4);
    rootW.rotation.set(0, s * (0.2 + fold * 1.0), s * (0.45 - fold * 0.65));
    body.add(rootW);
    wingRoots.push(rootW);
    const arm = span * 0.45;
    reg.limb(rootW, scale, V(0, 0, 0), V(s * arm, 0, 0), u * 0.14, u * 0.1, { region: 'wings', name: 'CHR_Wing' });
    const elbow = new THREE.Group();
    elbow.position.x = s * arm;
    elbow.rotation.z = s * -(0.3 + fold * 1.3);
    rootW.add(elbow);
    const tips: THREE.Vector3[] = [];
    for (let r = 0; r < 4; r += 1) {
      const a = -0.2 - r * 0.45;
      const Lr = span * 0.6 * (1 - r * 0.15);
      const tip = V(s * Math.cos(a) * Lr, Math.sin(a) * Lr, 0);
      reg.limb(elbow, scale, V(0, 0, 0), tip, u * 0.07, u * 0.02, { region: 'wings' });
      tips.push(tip);
    }
    reg.cone(elbow, clawMat, V(0, 0, 0), V(s * 0.3, 1, 0.2), u * 0.05, u * 0.25, { region: 'wings' });
    const pts: number[] = [0, 0, 0];
    const uvs: number[] = [0, 1];
    for (const t of tips) {
      pts.push(t.x, t.y, t.z);
      uvs.push(1, 0.5);
    }
    const bodyPt = V(-s * arm * 0.95, -span * 0.3, -u * 0.6);
    pts.push(bodyPt.x, bodyPt.y, bodyPt.z);
    uvs.push(0, 0);
    const idx: number[] = [];
    for (let k = 1; k < tips.length; k += 1) {
      const mid = tips[k - 1].clone().lerp(tips[k], 0.5).multiplyScalar(0.72);
      const mi = pts.length / 3;
      pts.push(mid.x, mid.y, mid.z);
      uvs.push(0.7, 0.4);
      idx.push(0, k, mi, 0, mi, k + 1);
    }
    idx.push(0, tips.length, tips.length + 1);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    g.setIndex(idx);
    g.computeVertexNormals();
    reg.add(elbow, g, mem, { region: 'wings' });
    const inner = new THREE.BufferGeometry();
    inner.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0, -s * arm, 0, 0, bodyPt.x, bodyPt.y, bodyPt.z], 3));
    inner.setAttribute('uv', new THREE.Float32BufferAttribute([0, 1, 1, 1, 0, 0], 2));
    inner.setIndex([0, 1, 2]);
    inner.computeVertexNormals();
    reg.add(elbow, inner, mem, { region: 'wings' });
    socket(ctx, `SOC-Wing_${i ? 'R' : 'L'}`, rootW, V(s * arm * 0.6, 0, 0));
  });

  // Tail
  const tailSegs: THREE.Group[] = [];
  const tailCount = 12;
  const tailLen = u * 5.2 * tailF;
  const tSeg = tailLen / tailCount;
  let tp: THREE.Object3D = body;
  const tailBase = new THREE.Group();
  tailBase.position.set(0, bodyR.y * 0.1, -bodyR.z * 0.9);
  tailBase.rotation.x = -0.3;
  body.add(tailBase);
  tp = tailBase;
  for (let i = 0; i < tailCount; i += 1) {
    const g = new THREE.Group();
    if (i) g.position.z = -tSeg;
    g.rotation.x = i ? 0.025 : 0;
    tp.add(g);
    const r0 = u * 0.55 * (1 - i / tailCount) * (1 + 0.15 * bulk) + u * 0.03;
    const r1 = u * 0.55 * (1 - (i + 1) / tailCount) * (1 + 0.15 * bulk) + u * 0.03;
    reg.limb(g, scale, V(0, 0, 0), V(0, 0, -tSeg * 1.08), r0, r1, { region: 'tail', name: i === 0 ? 'CHR_Tail' : undefined });
    if (back !== 'smooth' && back !== 'sail' && i % 2 === 0) reg.cone(g, hornMat, V(0, r0 * 0.9, -tSeg * 0.5), V(0, 1, -0.6), u * 0.05, u * 0.25 * (1 - i / tailCount), { region: 'tail', pickable: false });
    tailSegs.push(g);
    tp = g;
  }
  const tipM = reg.cone(tp, hornMat, V(0, 0, -tSeg), V(0, 0, -1), u * 0.14, u * 0.45, { region: 'tail' });
  tipM.scale.y = u * 0.45;
  tipM.scale.x = u * 0.25;
  tipM.scale.z = u * 0.04;

  // Sockets
  socket(ctx, 'SOC-Neck', neckSegs[1] ?? neckBase, V(0, segLen * 0.3, 0));
  socket(ctx, 'SOC-Back', body, V(0, bodyR.y * 0.95, bodyR.z * 0.1));
  socket(ctx, 'SOC-HeadTop', head, V(0, skull.y + hs * 0.1, 0));
  socket(ctx, 'SOC-Tail', tailBase, V(0, 0, 0));
  socket(ctx, 'SOC-Crest', head, V(0, skull.y, -skull.z * 0.2));
  legs.filter((l) => l.front).forEach((l, i) => socket(ctx, `SOC-Shoulder_${i ? 'R' : 'L'}`, l.hip, V(0, 0, 0)));

  // Gear
  for (const e of id.equipped) {
    if (packPlaceholder(ctx, e, body)) continue;
    const def = ACCESSORY_BY_ID[e.id];
    if (!def || !def.bodies.includes('beast')) continue;
    const col = colorsOf(e, def);
    const before = reg.meshes.length;
    if (def.id === 'dragon_collar') {
      const { inner } = equipRoot(ctx, e, 'SOC-Neck', neckSegs[1]);
      inner.position.set(0, 0, 0);
      const r = u * 0.55;
      const t = reg.add(inner, new THREE.TorusGeometry(r, u * 0.08, 8, 28), gearMat(ctx, e, col.leather, 'leather'), { region: 'neck', name: 'EQ_Collar' });
      t.rotation.x = Math.PI / 2;
      for (let k = 0; k < 6; k += 1) {
        const a = (k / 6) * Math.PI * 2;
        reg.cone(inner, gearMat(ctx, e, col.metal, 'metal'), V(Math.cos(a) * r * 1.05, 0, Math.sin(a) * r * 1.05), V(Math.cos(a), 0, Math.sin(a)), u * 0.04, u * 0.12, { region: 'neck' });
      }
      reg.ellipsoid(inner, ctx.mat(col.gem, 'glass', { opacity: 0.9, emissive: col.gem, emissiveStrength: 0.3 }), V(0, 0, r * 1.1), V(u * 0.09, u * 0.12, u * 0.06), { region: 'neck' });
    } else if (def.id === 'dragon_harness') {
      const { inner } = equipRoot(ctx, e, 'SOC-Back', body);
      inner.position.set(0, 0, 0);
      const lm = gearMat(ctx, e, col.leather, 'leather');
      reg.box(inner, gearMat(ctx, e, col.pad, 'cloth'), V(0, u * 0.08, 0), V(bodyR.x * 1.2, u * 0.18, u * 1.1), { region: 'body', name: 'EQ_Saddle' });
      reg.box(inner, lm, V(0, u * 0.25, -u * 0.35), V(bodyR.x * 0.9, u * 0.3, u * 0.2), { region: 'body' });
      for (const dz of [-u * 0.35, u * 0.35]) {
        const t = reg.add(body, new THREE.TorusGeometry(1, 0.035, 6, 32), lm, { region: 'body' });
        t.scale.set(bodyR.x * 1.03, bodyR.y * 1.03, bodyR.x);
        t.position.set(0, 0, bodyR.z * 0.1 + dz);
      }
      for (const s of S) reg.add(inner, new THREE.TorusGeometry(u * 0.08, u * 0.02, 6, 16), gearMat(ctx, e, col.metal, 'metal'), { region: 'body' }).position.set(s * bodyR.x * 0.65, u * 0.1, 0);
    } else if (def.id === 'wing_ornament') {
      const { inner } = equipRoot(ctx, e, 'SOC-Wing_L', wingRoots[0]);
      inner.position.set(0, 0, 0);
      const ring = reg.add(inner, new THREE.TorusGeometry(u * 0.16, u * 0.03, 6, 20), gearMat(ctx, e, col.metal, 'metal'), { region: 'wings', name: 'EQ_WingOrnament' });
      ring.rotation.y = Math.PI / 2;
      const cloth = reg.box(inner, gearMat(ctx, e, col.cloth, 'cloth'), V(0, -u * 0.35, 0), V(u * 0.12, u * 0.5, u * 0.02), { region: 'wings' });
      cloth.rotation.z = 0.1;
    }
    for (let i = before; i < reg.meshes.length; i += 1) reg.meshes[i].userData.equipUid = e.uid;
  }

  groundSnap(root, reg.meshes);

  const baseHead = head.rotation.clone();
  const tailBaseRot = tailSegs.map((g) => g.rotation.clone());
  const wingBase = wingRoots.map((g) => g.rotation.clone());
  const brBase = browRidges.map((b) => b.position.clone());
  ctx.updaters.push((f) => {
    const w = f.w;
    const gz = f.perf.gaze;
    eyeMats.forEach((m, i) => {
      const side = i === 0 ? 'L' : 'R';
      const e = solveEye(w, side, 0.25 + old * 0.2, gz.y);
      m.uniforms.uUpper.value = e.upper;
      m.uniforms.uLower.value = e.lower;
      m.uniforms.uSqueeze.value = e.squeeze;
      m.uniforms.uGaze.value.set(gz.x * (i === 0 ? 1 : -1) * 0.5, gz.y);
    });
    browRidges.forEach((b, i) => {
      const r = solveBrow(w, i === 0 ? 'L' : 'R', { inner: [0, 0], mid: [0, 0], outer: [0, 0] }, 1);
      b.position.y = brBase[i].y + r.mid[1] * eyeR * 0.8;
      b.rotation.z = (i === 0 ? 1 : -1) * (r.inner[1] - r.outer[1]) * 0.8;
    });
    const ms = solveMouth(w, 0, 0.72);
    const open = Math.min(1, ms.jaw + (ms.openUp + ms.openDown) * 0.9);
    jaw.rotation.x = open * 0.5;
    const snarl = (w['PF-Snarl'] ?? 0) + (w['PF-Disgust'] ?? 0) * 0.5;
    upperJaw.rotation.x = -snarl * 0.08 - open * 0.05;
    head.rotation.set(baseHead.x + f.perf.head.pitch * 0.5, baseHead.y + f.perf.head.yaw * 0.7, baseHead.z + f.perf.head.roll * 0.3);
    const br = 1 + Math.sin(f.time * 1.2) * 0.012;
    body.scale.set(br, br, 1);
    const tp2 = id.physics.tail;
    if (tp2.enabled) {
      const amp = tp2.amount * (1 - tp2.stiffness * 0.6) * 0.08;
      tailSegs.forEach((g, i) => {
        g.rotation.y = tailBaseRot[i].y + Math.sin(f.time * 1.2 - i * 0.45) * amp * (0.3 + i * 0.1);
      });
    }
    const wp = id.physics.wings;
    if (wp.enabled) {
      const amp = wp.amount * (1 - wp.stiffness * 0.7) * 0.06;
      wingRoots.forEach((g, i) => {
        g.rotation.z = wingBase[i].z + Math.sin(f.time * 1.1) * amp * (i ? -1 : 1);
      });
    }
  });
  return { root, head };
}
