import * as THREE from 'three';
import { mixHex } from '../model/character';
import { ACCESSORY_BY_ID } from '../model/looks';
import { buildCape, buildProp, colorsOf, equipRoot, gearMat, packPlaceholder } from './accessories';
import { solveBrow, solveEye, solveMouth, type BrowShape } from './face';
import { V } from './parts';
import { groundSnap, poseAngles, socket, type BuildCtx } from './rig';

const S = [1, -1];

export function buildRobot(ctx: BuildCtx): { root: THREE.Group; head: THREE.Object3D } {
  const { id, n, reg } = ctx;
  const L = id.looks;
  const c = id.colors;
  const boneF = (k: string, lo: number, hi: number) => (n(k) >= 0 ? 1 + n(k) * (hi - 1) : 1 + n(k) * (1 - lo));
  const bulk = n('robot.bulk');
  const u = (1.6 * boneF('body.height', 0.9, 1.1)) / 6.4;
  const hs = boneF('head.size', 0.9, 1.15);
  const wear = Math.max(0, n('robot.wear'));
  const gap = Math.max(0, n('robot.panelGap'));
  const glowK = 0.4 + 0.9 * Math.max(0, n('robot.emissive'));
  const paint = ctx.mat(c.robotPaint, 'metal', wear > 0 ? { wear } : undefined);
  const panel = ctx.mat(c.robotPanel, 'metal', wear > 0 ? { wear: wear * 0.7 } : undefined);
  const joint = ctx.mat(c.robotJoint, 'metal');
  const seam = ctx.mat(mixHex(c.robotJoint, '#000000', 0.5), 'dark');
  const glow = ctx.mat(c.robotGlow, 'emissive', { emissive: c.robotGlow, emissiveStrength: glowK });
  const lensDark = ctx.mat(mixHex(c.robotGlow, '#000000', 0.8), 'dark');

  const dims = {
    torsoLen: u * 1.7 * boneF('torso.length', 0.85, 1.15),
    chestW: u * 0.95 * (1 + 0.22 * bulk),
    chestD: u * 0.62 * (1 + 0.18 * bulk),
    upperLen: u * 1.05 * boneF('upperArm.length', 0.85, 1.15),
    foreLen: u * 1.0 * boneF('forearm.length', 0.85, 1.15),
    thighLen: u * 1.2 * boneF('thigh.length', 0.85, 1.15),
    shinLen: u * 1.25 * boneF('shin.length', 0.85, 1.15),
    neckLen: u * 0.28 * boneF('neck.length', 0.85, 1.15),
    limbR: u * 0.16 * (1 + 0.3 * bulk),
    handLen: u * 0.5 * boneF('hand.length', 0.85, 1.15) * (1 + 0.15 * n('hand.size')),
    footLen: u * 0.95 * boneF('foot.length', 0.85, 1.15) * (1 + 0.15 * n('foot.size')),
  };
  const pose = poseAngles(ctx.pose);
  const root = new THREE.Group();
  root.name = 'CHR_Armature';
  const pelvis = new THREE.Group();
  pelvis.position.y = dims.thighLen + dims.shinLen + u * 0.3;
  root.add(pelvis);
  const spine = new THREE.Group();
  spine.rotation.x = pose.spine;
  pelvis.add(spine);
  const chest = new THREE.Group();
  chest.position.y = dims.torsoLen * 0.45;
  spine.add(chest);

  reg.box(pelvis, paint, V(0, 0, 0), V(dims.chestW * 1.5, u * 0.5, dims.chestD * 1.5), { region: 'body', name: 'CHR_Pelvis' });
  reg.limb(spine, joint, V(0, 0, 0), V(0, dims.torsoLen * 0.45, 0), u * 0.28 * (1 + 0.2 * bulk), u * 0.3 * (1 + 0.2 * bulk), { region: 'body' });
  for (let i = 0; i < 3; i += 1) reg.add(spine, new THREE.TorusGeometry(u * 0.3 * (1 + 0.2 * bulk), u * 0.035, 6, 20), seam, { region: 'body', pickable: false }).position.set(0, dims.torsoLen * (0.1 + i * 0.12), 0);
  reg.box(chest, paint, V(0, dims.torsoLen * 0.18, 0), V(dims.chestW * 2, dims.torsoLen * 0.62, dims.chestD * 2), { region: 'chest', name: 'CHR_Chest', bevel: 0.3 });
  reg.box(chest, panel, V(0, dims.torsoLen * 0.2, dims.chestD * 0.98), V(dims.chestW * 1.4, dims.torsoLen * 0.44, u * 0.06), { region: 'chest', bevel: 0.3 });
  if (gap > 0.02) {
    reg.box(chest, seam, V(0, dims.torsoLen * 0.2, dims.chestD * 0.97), V(dims.chestW * 1.4 + gap * u * 0.12, dims.torsoLen * 0.44 + gap * u * 0.12, u * 0.05), { region: 'chest', pickable: false, bevel: 0.3 });
    reg.box(chest, seam, V(0, -dims.torsoLen * 0.13, 0), V(dims.chestW * 2.02, gap * u * 0.08, dims.chestD * 2.02), { region: 'chest', pickable: false });
  }
  const coreR = u * 0.16 * (1 + 0.5 * n('robot.core'));
  const core = reg.add(chest, new THREE.CircleGeometry(coreR, 24), glow, { region: 'chest', name: 'CHR_Core' });
  core.position.set(0, dims.torsoLen * 0.24, dims.chestD * 1.02 + u * 0.01);
  const coreRim = reg.add(chest, new THREE.TorusGeometry(coreR * 1.08, u * 0.03, 6, 24), joint, { region: 'chest' });
  coreRim.position.copy(core.position);

  const sh: THREE.Group[] = [];
  const el: THREE.Group[] = [];
  const wr: THREE.Group[] = [];
  const hip: THREE.Group[] = [];
  const knee: THREE.Group[] = [];
  const ankle: THREE.Group[] = [];
  const shoulderHalf = dims.chestW + dims.limbR * 1.3;
  S.forEach((s, i) => {
    const shG = new THREE.Group();
    shG.position.set(s * shoulderHalf, dims.torsoLen * 0.34, 0);
    shG.rotation.z = s * pose.shoulder;
    shG.rotation.x = -pose.shoulderFwd;
    chest.add(shG);
    reg.ellipsoid(shG, paint, V(0, 0, 0), V(dims.limbR * 1.7, dims.limbR * 1.5, dims.limbR * 1.6), { region: 'arms', name: `CHR_Shoulder_${i ? 'R' : 'L'}` });
    reg.limb(shG, joint, V(0, 0, 0), V(0, -dims.upperLen, 0), dims.limbR * 0.7, dims.limbR * 0.7, { region: 'arms' });
    const elG = new THREE.Group();
    elG.position.y = -dims.upperLen;
    elG.rotation.x = pose.elbow;
    shG.add(elG);
    reg.ellipsoid(elG, joint, V(0, 0, 0), V(dims.limbR * 0.95, dims.limbR * 0.95, dims.limbR * 0.95), { region: 'arms' });
    reg.box(elG, paint, V(0, -dims.foreLen * 0.5, 0), V(dims.limbR * 2.2, dims.foreLen * 0.9, dims.limbR * 2.2), { region: 'arms', bevel: 0.3 });
    const wrG = new THREE.Group();
    wrG.position.y = -dims.foreLen;
    elG.add(wrG);
    reg.box(wrG, joint, V(0, -dims.handLen * 0.3, 0), V(dims.limbR * 1.2, dims.handLen * 0.6, dims.limbR * 1.8), { region: 'hands', name: `CHR_Hand_${i ? 'R' : 'L'}` });
    for (let f = 0; f < 3; f += 1) {
      const z = (f - 1) * dims.limbR * 0.6;
      const a = V(0, -dims.handLen * 0.6, z);
      const m = a.clone().add(V(-s * dims.handLen * 0.05, -dims.handLen * 0.3, 0));
      const t = m.clone().add(V(-s * dims.handLen * 0.1, -dims.handLen * 0.22, 0));
      reg.limb(wrG, panel, a, m, u * 0.045, u * 0.045, { region: 'hands' });
      reg.limb(wrG, panel, m, t, u * 0.045, u * 0.035, { region: 'hands' });
    }
    reg.limb(wrG, panel, V(0, -dims.handLen * 0.25, dims.limbR * 0.9), V(-s * u * 0.05, -dims.handLen * 0.5, dims.limbR * 1.3), u * 0.05, u * 0.04, { region: 'hands' });
    sh.push(shG);
    el.push(elG);
    wr.push(wrG);

    const hipG = new THREE.Group();
    hipG.position.set(s * dims.chestW * 0.55, -u * 0.2, 0);
    hipG.rotation.z = s * pose.hipSpread;
    hipG.rotation.x = pose.hipFwd;
    pelvis.add(hipG);
    reg.ellipsoid(hipG, joint, V(0, 0, 0), V(dims.limbR * 1.1, dims.limbR * 1.1, dims.limbR * 1.1), { region: 'legs' });
    reg.box(hipG, paint, V(0, -dims.thighLen * 0.5, 0), V(dims.limbR * 2.1, dims.thighLen * 0.85, dims.limbR * 2.2), { region: 'legs', name: `CHR_Thigh_${i ? 'R' : 'L'}`, bevel: 0.3 });
    const kG = new THREE.Group();
    kG.position.y = -dims.thighLen;
    kG.rotation.x = pose.knee;
    hipG.add(kG);
    reg.ellipsoid(kG, joint, V(0, 0, 0), V(dims.limbR * 1.1, dims.limbR * 1.1, dims.limbR * 1.1), { region: 'legs' });
    reg.box(kG, paint, V(0, -dims.shinLen * 0.5, u * 0.02), V(dims.limbR * 2.6, dims.shinLen * 0.92, dims.limbR * 2.8), { region: 'legs', bevel: 0.35 });
    reg.box(kG, panel, V(0, -dims.shinLen * 0.35, dims.limbR * 1.42), V(dims.limbR * 1.6, dims.shinLen * 0.4, u * 0.04), { region: 'legs' });
    const aG = new THREE.Group();
    aG.position.y = -dims.shinLen;
    aG.rotation.x = pose.ankle;
    kG.add(aG);
    const foot = new THREE.Group();
    foot.rotation.x = -(hipG.rotation.x + kG.rotation.x + aG.rotation.x);
    aG.add(foot);
    const fm = reg.box(foot, joint, V(0, -u * 0.18, dims.footLen * 0.25), V(dims.limbR * 2.6, u * 0.24, dims.footLen), { region: 'feet', name: `CHR_Foot_${i ? 'R' : 'L'}`, bevel: 0.35 });
    fm.userData.ground = true;
    reg.box(foot, paint, V(0, -u * 0.1, dims.footLen * 0.55), V(dims.limbR * 2.4, u * 0.16, dims.footLen * 0.35), { region: 'feet', bevel: 0.4 });
    hip.push(hipG);
    knee.push(kG);
    ankle.push(aG);
  });

  // Head
  const neck = new THREE.Group();
  neck.position.y = dims.torsoLen * 0.5;
  chest.add(neck);
  for (let i = 0; i < 3; i += 1) reg.ellipsoid(neck, joint, V(0, dims.neckLen * (0.2 + i * 0.35), 0), V(u * 0.16, dims.neckLen * 0.22, u * 0.16), { region: 'neck', name: i === 0 ? 'CHR_Neck' : undefined });
  const head = new THREE.Group();
  const hh = u * 1.05 * hs;
  head.position.set(0, dims.neckLen + hh * 0.45, u * 0.02);
  neck.add(head);
  const helm = V(hh * 0.5, hh * 0.52, hh * 0.52);
  reg.ellipsoid(head, paint, V(0, hh * 0.05, -hh * 0.02), helm, { region: 'skull', name: 'CHR_Head' });
  reg.box(head, panel, V(0, -hh * 0.08, hh * 0.3), V(hh * 0.78, hh * 0.62, hh * 0.44), { region: 'skull', bevel: 0.45 });
  for (const s of S) reg.limb(head, joint, V(s * hh * 0.48, -hh * 0.02, 0), V(s * hh * 0.58, -hh * 0.02, 0), hh * 0.12, hh * 0.12, { region: 'skull' });
  const faceZ = hh * 0.52 + u * 0.005;

  const opticK = 1 + 0.35 * n('robot.optic');
  const optic = L.optic ?? 'twin';
  const lids: { mesh: THREE.Mesh; base: number; h: number; side: 'L' | 'R' }[] = [];
  const pupils: { mesh: THREE.Mesh; base: THREE.Vector3; r: number }[] = [];
  const eyeY = hh * 0.02;
  const eyeX = hh * 0.17;
  const addLens = (x: number, rx: number, ry: number, side: 'L' | 'R', name: string) => {
    const lens = reg.add(head, new THREE.CircleGeometry(1, 28), glow, { region: 'eyes', name });
    lens.scale.set(rx, ry, 1);
    lens.position.set(x, eyeY, faceZ);
    const socketRing = reg.add(head, new THREE.TorusGeometry(1, 0.1, 6, 28), joint, { region: 'eyes', pickable: false });
    socketRing.scale.set(rx * 1.05, ry * 1.05, rx);
    socketRing.position.copy(lens.position);
    const p = reg.add(head, new THREE.CircleGeometry(Math.min(rx, ry) * 0.38, 20), lensDark, { region: 'eyes', pickable: false });
    p.position.set(x, eyeY, faceZ + u * 0.004);
    pupils.push({ mesh: p, base: p.position.clone(), r: Math.min(rx, ry) * 0.45 });
    const lid = reg.box(head, paint, V(x, eyeY + ry * 1.6, faceZ + u * 0.01), V(rx * 2.3, ry * 2.1, u * 0.03), { region: 'eyes', pickable: false });
    lids.push({ mesh: lid, base: eyeY + ry * 1.6, h: ry * 2.1, side });
  };
  if (optic === 'visor') {
    addLens(0, hh * 0.3 * opticK, hh * 0.07 * opticK, 'L', 'CHR_Eye_L');
  } else if (optic === 'mono') {
    addLens(0, hh * 0.13 * opticK, hh * 0.13 * opticK, 'L', 'CHR_Eye_L');
  } else {
    addLens(eyeX, hh * 0.085 * opticK, hh * 0.1 * opticK, 'L', 'CHR_Eye_L');
    addLens(-eyeX, hh * 0.085 * opticK, hh * 0.1 * opticK, 'R', 'CHR_Eye_R');
  }
  const browBars = S.map((s) => {
    const m = reg.box(head, glow, V(s * eyeX, eyeY + hh * 0.2, faceZ + u * 0.012), V(hh * 0.2, hh * 0.028, u * 0.02), { region: 'brows', name: `CHR_Brow_${s > 0 ? 'L' : 'R'}` });
    return m;
  });
  const browRest: BrowShape[] = S.map((s) => ({ inner: [s * eyeX * 0.4, eyeY + hh * 0.2], mid: [s * eyeX, eyeY + hh * 0.21], outer: [s * eyeX * 1.6, eyeY + hh * 0.2] }));

  const mouthStyle = L.robotMouth ?? 'segments';
  const mouthY = -hh * 0.26;
  const segs: THREE.Mesh[] = [];
  let bar: THREE.Mesh | null = null;
  let plate: THREE.Group | null = null;
  if (mouthStyle === 'segments') {
    for (let r = 0; r < 2; r += 1) for (let k = 0; k < 6; k += 1) {
      const m = reg.box(head, glow, V((k - 2.5) * hh * 0.055, mouthY + (0.5 - r) * hh * 0.04, faceZ - hh * 0.07 + u * 0.01), V(hh * 0.04, hh * 0.03, u * 0.02), { region: 'mouth', name: k === 0 && r === 0 ? 'CHR_Mouth' : undefined, pickable: k === 0 });
      segs.push(m);
    }
  } else if (mouthStyle === 'bar') {
    bar = reg.box(head, glow, V(0, mouthY, faceZ - hh * 0.07 + u * 0.01), V(hh * 0.3, hh * 0.02, u * 0.02), { region: 'mouth', name: 'CHR_Mouth' });
  } else {
    reg.box(head, lensDark, V(0, mouthY, faceZ - hh * 0.08), V(hh * 0.34, hh * 0.1, u * 0.02), { region: 'mouth', pickable: false });
    plate = new THREE.Group();
    plate.position.set(0, mouthY + hh * 0.05, faceZ - hh * 0.07);
    head.add(plate);
    reg.box(plate, panel, V(0, -hh * 0.06, u * 0.015), V(hh * 0.38, hh * 0.13, u * 0.03), { region: 'mouth', name: 'CHR_Mouth' });
  }

  const antenna = L.antenna ?? 'none';
  if (antenna !== 'none') {
    const alen = hh * 0.55 * (1 + 0.5 * n('robot.antenna'));
    const bases = antenna === 'twin' ? S.map((s) => V(s * hh * 0.3, hh * 0.45, -hh * 0.05)) : [V(0, hh * 0.55, -hh * 0.05)];
    for (const b of bases) {
      if (antenna === 'fin') {
        const f = reg.cone(head, paint, b, V(0, 1, -0.6), hh * 0.18, alen, { region: 'skull', name: 'CHR_Antenna' });
        f.scale.x = u * 0.02;
      } else {
        reg.limb(head, joint, b, b.clone().add(V(Math.sign(b.x) * alen * 0.2, alen, -alen * 0.15)), u * 0.02, u * 0.012, { region: 'skull', name: 'CHR_Antenna' });
        reg.ellipsoid(head, glow, b.clone().add(V(Math.sign(b.x) * alen * 0.2, alen, -alen * 0.15)), V(u * 0.045, u * 0.045, u * 0.045), { region: 'skull' });
      }
    }
  }

  // Sockets
  socket(ctx, 'SOC-HeadTop', head, V(0, hh * 0.55, 0));
  socket(ctx, 'SOC-Antenna', head, V(0, hh * 0.55, -hh * 0.05));
  socket(ctx, 'SOC-Core', chest, core.position);
  socket(ctx, 'SOC-Eyewear', head, V(0, eyeY, faceZ));
  socket(ctx, 'SOC-Neck', neck, V(0, dims.neckLen * 0.3, 0));
  socket(ctx, 'SOC-Chest', chest, V(0, dims.torsoLen * 0.2, dims.chestD));
  socket(ctx, 'SOC-Back', chest, V(0, dims.torsoLen * 0.2, -dims.chestD));
  socket(ctx, 'SOC-Cape', chest, V(0, dims.torsoLen * 0.45, -dims.chestD * 0.9));
  socket(ctx, 'SOC-Waist', spine, V(0, 0, 0));
  S.forEach((_, i) => {
    const sfx = i ? 'R' : 'L';
    socket(ctx, `SOC-Shoulder_${sfx}`, sh[i], V(0, 0, 0));
    socket(ctx, `SOC-ForeArm_${sfx}`, el[i], V(0, -dims.foreLen * 0.5, 0));
    socket(ctx, `SOC-Hand_${sfx}`, wr[i], V(0, -dims.handLen * 0.45, 0));
    socket(ctx, `SOC-Weapon_${sfx}`, wr[i], V(0, -dims.handLen * 0.5, 0));
    socket(ctx, `SOC-Hip_${sfx}`, hip[i], V(0, 0, 0));
    socket(ctx, `SOC-Shin_${sfx}`, knee[i], V(0, -dims.shinLen * 0.5, 0));
    socket(ctx, `SOC-Foot_${sfx}`, ankle[i], V(0, 0, 0));
  });

  // Gear
  for (const e of id.equipped) {
    if (packPlaceholder(ctx, e, chest)) continue;
    const def = ACCESSORY_BY_ID[e.id];
    if (!def || !def.bodies.includes('robot')) continue;
    const before = reg.meshes.length;
    if (def.id === 'blade' || def.id === 'launcher') {
      const { inner } = equipRoot(ctx, e, def.socket, wr[def.id === 'blade' ? 1 : 0]);
      inner.position.set(0, 0, 0);
      buildProp(ctx, e, def, inner, u);
    } else if (def.id === 'panel_kit') {
      const col = colorsOf(e, def);
      const pm = gearMat(ctx, e, col.paint, 'metal');
      const pn = gearMat(ctx, e, col.panel, 'metal');
      const { root: eroot } = equipRoot(ctx, e, 'SOC-Shoulder_L', sh[0]);
      S.forEach((s, i) => {
        const g = i === 0 ? eroot : new THREE.Group();
        if (i) sh[1].add(g);
        const p = reg.box(g, pm, V(s * dims.limbR * 0.4, dims.limbR * 1.2, 0), V(dims.limbR * 2.8, u * 0.08, dims.limbR * 3.2), { region: 'arms', name: 'EQ_Panel', bevel: 0.3 });
        p.rotation.z = s * -0.35;
        reg.box(g, pn, V(s * dims.limbR * 1.6, dims.limbR * 0.3, 0), V(u * 0.06, dims.limbR * 1.8, dims.limbR * 2.6), { region: 'arms', bevel: 0.3 });
      });
    } else if (def.id === 'robot_cape') {
      const { inner } = equipRoot(ctx, e, 'SOC-Cape', chest);
      inner.position.set(0, 0, 0);
      buildCape(ctx, inner, { width: shoulderHalf * 2, length: dims.torsoLen + dims.thighLen, depth: dims.chestD * 0.5, colors: colorsOf(e, def), torn: false, e, region: 'body' });
    }
    for (let i = before; i < reg.meshes.length; i += 1) reg.meshes[i].userData.equipUid = e.uid;
  }

  groundSnap(root, reg.meshes);

  const baseHead = head.rotation.clone();
  ctx.updaters.push((f) => {
    const w = f.w;
    const gz = f.perf.gaze;
    for (const l of lids) {
      const e = solveEye(w, l.side, 0, gz.y);
      const close = Math.min(1, Math.max(0, e.upper - 0.1) / 0.9);
      l.mesh.position.y = l.base - close * l.h * 0.5 - e.squeeze * l.h * 0.05;
    }
    for (const p of pupils) p.mesh.position.set(p.base.x + gz.x * p.r, p.base.y + gz.y * p.r, p.base.z);
    browBars.forEach((m, i) => {
      const s = S[i];
      const b = solveBrow(w, i === 0 ? 'L' : 'R', browRest[i], hh * 0.12);
      m.position.y = b.mid[1];
      m.rotation.z = Math.atan2(b.outer[1] - b.inner[1], (b.outer[0] - b.inner[0]) * s) * s;
    });
    const ms = solveMouth(w, 0, 0.72);
    const open = Math.min(1, ms.jaw + ms.openUp + ms.openDown);
    if (segs.length) {
      const lit = Math.round(2 + open * 4 + ms.halfW * 2);
      segs.forEach((m, k) => {
        const col = k % 6;
        const row = Math.floor(k / 6);
        const dist = Math.abs(col - 2.5);
        m.visible = dist < lit / 2 && (row === 0 || open > 0.15 || ms.cornerL + ms.cornerR < -0.1);
        m.position.y = mouthY + (0.5 - row) * hh * (0.04 + open * 0.05) + (row === 0 ? (ms.cornerL + ms.cornerR) * 0.5 * hh * 0.08 * (dist / 2.5) : 0);
      });
    }
    if (bar) {
      bar.scale.set(hh * 0.3 * (ms.halfW / 0.72), hh * (0.02 + open * 0.08), u * 0.02);
      bar.rotation.z = (ms.cornerL - ms.cornerR) * 0.4;
    }
    if (plate) plate.rotation.x = open * 0.6;
    head.rotation.set(baseHead.x + f.perf.head.pitch * 0.5, baseHead.y + f.perf.head.yaw * 0.7, baseHead.z + f.perf.head.roll * 0.3);
    const pulse = 0.85 + Math.sin(f.time * 2.4) * 0.15;
    glow.uniforms.uEmissiveStrength.value = glowK * pulse;
    if (pose.waveArm) {
      sh[1].rotation.z = -2.55;
      el[1].rotation.z = -0.35 + Math.sin(f.time * 6) * 0.35;
    }
  });
  return { root, head };
}
