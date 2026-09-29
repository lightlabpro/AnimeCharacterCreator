import * as THREE from 'three';
import { ACCESSORY_BY_ID, type AccessoryDef } from '../model/looks';
import type { Equipped, Region } from '../model/types';
import type { HumanoidBody } from './humanoid';
import { hashString, V } from './parts';
import type { BuildCtx } from './rig';
import { damageTexture } from './textures';
import { toon, type ToonKind, type ToonMaterial, type ToonOptions } from './toonMaterial';

const S = [1, -1];

export function colorsOf(e: Equipped, def?: AccessoryDef): Record<string, string> {
  return { ...(def?.colors ?? {}), ...e.colors };
}

/** Wear-aware material for gear. Damage above zero adds dirt, chips, and holes. */
export function gearMat(ctx: BuildCtx, e: Equipped, color: string, kind: ToonKind, torn = false, extra: Partial<ToonOptions> = {}): ToonMaterial {
  const d = e.damage / 100;
  if (d <= 0.001 && !torn) return ctx.mat(color, kind, Object.keys(extra).length ? extra : undefined);
  const m = toon({ color, kind, wear: kind === 'metal' || kind === 'leather' ? d : d * 0.4, damageMap: damageTexture(hashString(e.uid), torn), ...extra });
  m.uniforms.uDamage.value = torn ? Math.max(0.35, d) : d * 0.6;
  return m;
}

/** A group attached to a socket with the equip offset applied. Content is authored in the socket parent's space. */
export function equipRoot(ctx: BuildCtx, e: Equipped, socketName: string, fallback: THREE.Object3D): { root: THREE.Group; inner: THREE.Group } {
  const sock = ctx.sockets[socketName] ?? fallback;
  const root = new THREE.Group();
  root.name = `EQ_${e.id}`;
  root.userData.equipUid = e.uid;
  root.position.set(...e.offset.p);
  root.rotation.set(...e.offset.r);
  root.scale.setScalar(e.offset.s || 1);
  sock.add(root);
  const inner = new THREE.Group();
  if (sock !== fallback && sock.parent) inner.position.copy(sock.position).negate();
  root.add(inner);
  ctx.equipObjects[e.uid] = root;
  return { root, inner };
}

/** Empty socket group that the glTF pack loader fills once the file is fetched. */
export function packPlaceholder(ctx: BuildCtx, e: Equipped, fallback: THREE.Object3D): boolean {
  const pack = ctx.packs.get(e.id);
  if (!pack) return false;
  const { root } = equipRoot(ctx, e, pack.socket || 'SOC-Chest', fallback);
  root.userData.pack = pack;
  root.userData.packColors = e.colors;
  return true;
}

function tag(root: THREE.Object3D, uid: string) {
  root.traverse((o) => {
    o.userData.equipUid = uid;
  });
}

export interface CapeOptions {
  width: number;
  length: number;
  depth: number;
  colors: Record<string, string>;
  torn: boolean;
  e: Equipped;
  region?: Region;
}

/** Hanging cape with an outer face, a lining, and sway driven by the cape physics channel. */
export function buildCape(ctx: BuildCtx, parent: THREE.Object3D, o: CapeOptions) {
  const cols = 12;
  const rows = 18;
  const g = new THREE.PlaneGeometry(o.width, o.length, cols, rows);
  const pos = g.attributes.position as THREE.BufferAttribute;
  const rest: number[] = [];
  for (let i = 0; i < pos.count; i += 1) {
    const x = pos.getX(i);
    const y = pos.getY(i) - o.length / 2;
    const t = -y / o.length;
    const xn = x / (o.width / 2);
    const spread = 1 + t * 0.35;
    const z = -o.depth * (1 - xn * xn) * (1 - t * 0.4) - t * o.depth * 0.6;
    pos.setXYZ(i, x * spread, y, z);
    rest.push(x * spread, y, z);
  }
  g.computeVertexNormals();
  const outer = gearMat(ctx, o.e, o.colors.cloth ?? '#3a4a6a', 'cloth', o.torn, { side: THREE.BackSide });
  const lining = gearMat(ctx, o.e, o.colors.lining ?? '#8a3a3a', 'cloth', o.torn, { side: THREE.FrontSide });
  const holder = new THREE.Group();
  parent.add(holder);
  ctx.reg.add(holder, g, outer, { region: o.region ?? 'body', name: 'EQ_Cape' });
  ctx.reg.add(holder, g, lining, { region: o.region ?? 'body', name: 'EQ_CapeLining' });
  const trim = ctx.mat(o.colors.trim ?? '#c9a35a', 'metal');
  ctx.reg.limb(holder, trim, V(-o.width * 0.5, 0, 0), V(o.width * 0.5, 0, 0), o.width * 0.03, o.width * 0.03, { region: o.region ?? 'body' });
  const phys = ctx.id.physics.cape;
  ctx.updaters.push((f) => {
    if (!phys.enabled) return;
    const amp = phys.amount * (1 - phys.stiffness * 0.7);
    for (let i = 0; i < pos.count; i += 1) {
      const rx = rest[i * 3];
      const ry = rest[i * 3 + 1];
      const rz = rest[i * 3 + 2];
      const t = -ry / o.length;
      const wave = Math.sin(f.time * 1.6 + t * 3.2 + rx * 6) * 0.025 * amp * t * t;
      const flap = Math.sin(f.time * 0.9 + rx * 3) * 0.02 * amp * t;
      pos.setXYZ(i, rx + flap * 0.3, ry + Math.abs(wave) * 0.2, rz - wave - Math.abs(flap));
    }
    pos.needsUpdate = true;
    g.computeVertexNormals();
  });
}

/** Handheld props: shared by the humanoid and robot bodies. */
export function buildProp(ctx: BuildCtx, e: Equipped, def: AccessoryDef, parent: THREE.Object3D, scale: number) {
  const c = colorsOf(e, def);
  const { reg } = ctx;
  const u = scale;
  if (def.id === 'blade') {
    const grip = gearMat(ctx, e, c.grip, 'leather');
    const guard = gearMat(ctx, e, c.guard, 'metal');
    const blade = gearMat(ctx, e, c.blade, 'metal');
    reg.limb(parent, grip, V(0, 0, -u * 0.15), V(0, 0, u * 0.2), u * 0.045, u * 0.045, { region: 'hands', name: 'EQ_Blade_Grip' });
    reg.box(parent, guard, V(0, 0, u * 0.22), V(u * 0.42, u * 0.07, u * 0.08), { region: 'hands' });
    reg.box(parent, blade, V(0, 0, u * 1.3), V(u * 0.11, u * 0.025, u * 2.1), { region: 'hands', name: 'EQ_Blade', bevel: 0.3 });
    const tip = reg.cone(parent, blade, V(0, 0, u * 2.35), V(0, 0, 1), u * 0.06, u * 0.2, { region: 'hands' });
    tip.scale.x *= 0.95;
    tip.scale.z = u * 0.014;
    reg.ellipsoid(parent, guard, V(0, 0, -u * 0.19), V(u * 0.06, u * 0.06, u * 0.06), { region: 'hands' });
  } else if (def.id === 'launcher') {
    const body = gearMat(ctx, e, c.body, 'leather');
    const metal = gearMat(ctx, e, c.metal, 'metal');
    const string = ctx.mat(c.string, 'cloth');
    reg.box(parent, body, V(0, 0, u * 0.25), V(u * 0.14, u * 0.12, u * 0.9), { region: 'hands', name: 'EQ_Launcher' });
    reg.limb(parent, metal, V(0, u * 0.06, u * 0.6), V(0, u * 0.06, u * 0.95), u * 0.035, u * 0.03, { region: 'hands' });
    for (const s of S) {
      reg.limb(parent, metal, V(0, 0, u * 0.62), V(s * u * 0.45, 0, u * 0.45), u * 0.03, u * 0.018, { region: 'hands' });
      reg.limb(parent, string, V(s * u * 0.45, 0, u * 0.45), V(0, 0, u * 0.05), u * 0.006, u * 0.006, { region: 'hands', pickable: false });
    }
    reg.box(parent, metal, V(0, -u * 0.1, u * 0.1), V(u * 0.06, u * 0.2, u * 0.05), { region: 'hands' });
  }
}

type Shell = (tag: string, mat: THREE.Material, inflate: number, opts?: { from?: number; to?: number; region?: Region; scale?: THREE.Vector3 }) => THREE.Mesh | null;

function makeShell(ctx: BuildCtx, b: HumanoidBody, uid: string): Shell {
  return (tagName, mat, inflate, opts = {}) => {
    const s = b.shapes[tagName];
    if (!s) return null;
    let m: THREE.Mesh;
    if (s.kind === 'ell') {
      const r = s.radii!.clone().addScalar(b.u * 0.012 * inflate).multiplyScalar(1 + 0.02 * inflate);
      if (opts.scale) r.multiply(opts.scale);
      m = ctx.reg.ellipsoid(s.parent, mat, s.pos!, r, { region: opts.region ?? (s.parent.userData.region as Region | undefined) });
    } else {
      const a = s.a!.clone().lerp(s.b!, opts.from ?? 0);
      const bb = s.a!.clone().lerp(s.b!, opts.to ?? 1);
      const t0 = opts.from ?? 0;
      const t1 = opts.to ?? 1;
      const r0 = (s.r0! + (s.r1! - s.r0!) * t0) + b.u * 0.014 * inflate;
      const r1 = (s.r0! + (s.r1! - s.r0!) * t1) + b.u * 0.014 * inflate;
      m = ctx.reg.limb(s.parent, mat, a, bb, r0, r1, { region: opts.region });
    }
    m.userData.equipUid = uid;
    return m;
  };
}

function buildOutfit(ctx: BuildCtx, b: HumanoidBody, e: Equipped, def: AccessoryDef) {
  const c = colorsOf(e, def);
  const shell = makeShell(ctx, b, e.uid);
  const { reg } = ctx;
  const u = b.u;
  const cloth = gearMat(ctx, e, c.cloth, 'cloth');
  const pants = gearMat(ctx, e, c.pants ?? c.cloth, 'cloth');
  const leather = gearMat(ctx, e, c.leather ?? '#6b4428', 'leather');
  const trim = gearMat(ctx, e, c.trim ?? '#c9a35a', 'metal');
  const childish = b.child;
  const sleeve = def.id === 'ranger_outfit' ? 0.95 : def.id === 'traveler_outfit' ? 0.75 : 0.45;
  const leg = childish ? 0.55 : def.id === 'traveler_outfit' ? 1 : 1;
  shell('chest', cloth, 1, { region: 'chest' });
  shell('waist', cloth, 1, { region: 'waist' });
  shell('trap', cloth, 1, { region: 'shoulders' });
  for (const s of [1, -1]) shell(`bust${s}`, cloth, 1, { region: 'chest' });
  for (const i of [0, 1]) {
    shell(`deltoid${i}`, cloth, 1, { region: 'shoulders' });
    shell(`upperArm${i}`, cloth, 1, { to: sleeve > 0.5 ? 1 : sleeve * 2, region: 'arms' });
    if (sleeve > 0.5) shell(`forearm${i}`, cloth, 1, { to: (sleeve - 0.5) * 2, region: 'arms' });
  }
  shell('pelvis', pants, 1, { region: 'hips' });
  for (const s of [1, -1]) shell(`glute${s}`, pants, 1, { region: 'hips' });
  for (const i of [0, 1]) {
    shell(`thigh${i}`, pants, 1, { to: childish ? 0.55 : 1, region: 'legs' });
    if (!childish && leg >= 1) {
      shell(`shin${i}`, pants, 1, { to: 0.92, region: 'legs' });
      shell(`calf${i}`, pants, 1, { region: 'legs' });
      if (b.digitigrade) shell(`meta${i}`, pants, 0.6, { to: 0.4, region: 'legs' });
    }
  }
  const neckTop = b.g.neck;
  const collar = reg.add(neckTop, new THREE.TorusGeometry(b.dims.neckR * 1.25, u * 0.05, 8, 24), def.id === 'ranger_outfit' ? leather : trim, { region: 'neck' });
  collar.rotation.x = Math.PI / 2 + 0.12;
  collar.position.set(0, u * 0.02, u * 0.02);
  const waistBand = reg.add(b.g.spine, new THREE.TorusGeometry(1, 0.08, 8, 32), trim, { region: 'waist' });
  waistBand.scale.set(b.dims.waistW * 1.06, b.dims.waistD * 1.08, u * 0.9);
  waistBand.rotation.x = Math.PI / 2;
  waistBand.position.set(0, b.dims.waistY - b.dims.torsoLen * 0.22, 0);
  if (def.id === 'ranger_outfit') {
    const p = reg.ellipsoid(b.g.sh[0], leather, V(0, -u * 0.02, 0), V(b.dims.armR * 1.6, b.dims.armR * 1.2, b.dims.armR * 1.5), { region: 'shoulders', name: 'EQ_Pauldron' });
    p.userData.equipUid = e.uid;
    for (const i of [0, 1]) {
      const br = reg.limb(b.g.el[i], leather, V(0, -b.dims.foreLen * 0.55, 0), V(0, -b.dims.foreLen * 0.95, 0), b.dims.foreR * 1.02 + u * 0.03, b.dims.foreR * 0.68 + u * 0.03, { region: 'arms', name: 'EQ_Bracer' });
      br.userData.equipUid = e.uid;
    }
    const strap = reg.add(b.g.chest, new THREE.TorusGeometry(1, 0.05, 6, 32), leather, { region: 'chest' });
    strap.rotation.order = 'YXZ';
    strap.rotation.set(0, Math.PI / 2, 0.55);
    strap.scale.set(b.dims.chestD * 1.12, b.dims.torsoLen * 0.42, b.dims.chestW * 1.1);
    strap.position.y = b.dims.torsoLen * 0.08;
    const tunic = new THREE.LatheGeometry([new THREE.Vector2(1, 0), new THREE.Vector2(1.08, -0.5), new THREE.Vector2(1.2, -1)], 24);
    const t = reg.add(b.g.pelvis, tunic, gearMat(ctx, e, c.cloth, 'cloth', false, { side: THREE.DoubleSide }), { region: 'hips', name: 'EQ_Tunic' });
    t.scale.set(b.dims.hipW * 1.05, u * 0.7, b.dims.hipD * 1.1);
    t.position.y = u * 0.3;
  } else if (def.id === 'traveler_outfit') {
    const skirt = new THREE.LatheGeometry([new THREE.Vector2(1, 0), new THREE.Vector2(1.15, -0.5), new THREE.Vector2(1.35, -1)], 28);
    const clothDs = gearMat(ctx, e, c.cloth, 'cloth', false, { side: THREE.DoubleSide });
    const t = reg.add(b.g.pelvis, skirt, clothDs, { region: 'hips', name: 'EQ_Tunic' });
    t.scale.set(b.dims.hipW * 1.08, b.dims.thighLen * 0.62, b.dims.hipD * 1.15);
    t.position.y = u * 0.35;
    const sash = reg.add(b.g.spine, new THREE.TorusGeometry(1, 0.12, 8, 32), leather, { region: 'waist' });
    sash.scale.set(b.dims.waistW * 1.1, b.dims.waistD * 1.12, u * 0.9);
    sash.rotation.x = Math.PI / 2;
    sash.position.y = b.dims.waistY - b.dims.torsoLen * 0.1;
    reg.box(b.g.spine, leather, V(b.dims.waistW * 0.3, b.dims.waistY - b.dims.torsoLen * 0.25, b.dims.waistD * 0.95), V(u * 0.12, u * 0.45, u * 0.05), { region: 'waist' });
  } else if (def.id === 'child_outfit') {
    const stripe = reg.add(b.g.chest, new THREE.TorusGeometry(1, 0.05, 6, 32), trim, { region: 'chest' });
    stripe.scale.set(b.dims.chestW * 1.05, b.dims.chestD * 1.07, u);
    stripe.rotation.x = Math.PI / 2;
    stripe.position.y = b.dims.torsoLen * 0.08;
  } else if (def.id === 'child_explorer') {
    const vest = gearMat(ctx, e, c.trim, 'cloth');
    shell('chest', vest, 1.8, { region: 'chest', scale: V(1, 0.9, 1) });
    const strap = reg.add(b.g.chest, new THREE.TorusGeometry(1, 0.05, 6, 32), leather, { region: 'chest' });
    strap.rotation.order = 'YXZ';
    strap.rotation.set(0, Math.PI / 2, 0.6);
    strap.scale.set(b.dims.chestD * 1.2, b.dims.torsoLen * 0.45, b.dims.chestW * 1.15);
    const bag = reg.box(b.g.pelvis, leather, V(-b.dims.hipW * 0.95, u * 0.1, u * 0.05), V(u * 0.12, u * 0.3, u * 0.28), { region: 'hips', name: 'EQ_Satchel' });
    bag.userData.equipUid = e.uid;
  }
}

function buildArmor(ctx: BuildCtx, b: HumanoidBody, e: Equipped, def: AccessoryDef) {
  const c = colorsOf(e, def);
  const shell = makeShell(ctx, b, e.uid);
  const { reg } = ctx;
  const u = b.u;
  const metal = gearMat(ctx, e, c.metal, 'metal');
  const fur = gearMat(ctx, e, c.fur, 'fur');
  const strap = gearMat(ctx, e, c.strap, 'leather');
  shell('chest', metal, 2.4, { region: 'chest', scale: V(1.02, 0.95, 1.04) });
  for (const s of [1, -1]) shell(`bust${s}`, metal, 2.4, { region: 'chest' });
  for (const i of [0, 1]) {
    const pa = reg.ellipsoid(b.g.sh[i], metal, V(0, u * 0.02, 0), V(b.dims.armR * 1.85, b.dims.armR * 1.1, b.dims.armR * 1.7), { region: 'shoulders', name: 'EQ_Pauldron' });
    pa.rotation.z = (i ? -1 : 1) * 0.25;
    pa.userData.equipUid = e.uid;
    shell(`forearm${i}`, metal, 2.2, { from: 0.35, to: 0.95, region: 'arms' });
    shell(`shin${i}`, metal, 2.2, { from: 0.1, to: 0.7, region: 'legs' });
  }
  const collar = reg.add(b.g.neck, new THREE.TorusGeometry(b.dims.neckR * 1.5, u * 0.12, 10, 28), fur, { region: 'neck', name: 'EQ_FurCollar' });
  collar.rotation.x = Math.PI / 2 + 0.15;
  const belt = reg.add(b.g.spine, new THREE.TorusGeometry(1, 0.1, 8, 32), strap, { region: 'waist' });
  belt.scale.set(b.dims.waistW * 1.12, b.dims.waistD * 1.14, u * 0.9);
  belt.rotation.x = Math.PI / 2;
  belt.position.y = b.dims.waistY - b.dims.torsoLen * 0.12;
  for (let k = 0; k < 3; k += 1) {
    const f = reg.box(b.g.pelvis, metal, V((k - 1) * b.dims.hipW * 0.55, -u * 0.1, b.dims.hipD * 0.95), V(u * 0.3, u * 0.5, u * 0.05), { region: 'hips', name: 'EQ_Faulds' });
    f.rotation.x = -0.12;
    f.rotation.y = (k - 1) * 0.35;
  }
}

function buildHeadGear(ctx: BuildCtx, b: HumanoidBody, e: Equipped, def: AccessoryDef, parent: THREE.Object3D) {
  const c = colorsOf(e, def);
  const { reg } = ctx;
  const h = b.h;
  const R = b.headR;
  if (def.id === 'goggles') {
    const frame = gearMat(ctx, e, c.frame, 'leather');
    const lens = ctx.mat(c.lens, 'lens', { opacity: 0.9 });
    const band = reg.add(parent, new THREE.TorusGeometry(1, 0.035, 8, 40), frame, { region: 'skull', name: 'EQ_Goggles' });
    band.scale.set(R.x * 1.04, R.z * 1.05, h);
    band.rotation.x = Math.PI / 2 - 0.35;
    band.position.set(0, R.y * 0.42, -R.z * 0.02);
    for (const s of S) {
      const g = new THREE.Group();
      g.position.set(s * R.x * 0.38, R.y * 0.62, R.z * 0.8);
      g.rotation.set(-0.7, s * 0.28, 0);
      parent.add(g);
      const rim = reg.add(g, new THREE.CylinderGeometry(0.11 * h, 0.12 * h, 0.08 * h, 20), frame, { region: 'skull' });
      rim.rotation.x = Math.PI / 2;
      const l = reg.add(g, new THREE.CircleGeometry(0.09 * h, 20), lens, { region: 'skull' });
      l.position.z = 0.041 * h;
    }
  } else if (def.id === 'bandana') {
    const cloth = gearMat(ctx, e, c.cloth, 'cloth');
    const band = reg.add(parent, new THREE.TorusGeometry(1, 0.09, 8, 40), cloth, { region: 'skull', name: 'EQ_Bandana' });
    band.scale.set(R.x * 1.03, R.z * 1.04, h * 0.9);
    band.rotation.x = Math.PI / 2 - 0.3;
    band.position.set(0, R.y * 0.36, 0);
    const knot = V(0, R.y * 0.3, -R.z * 1.02);
    reg.ellipsoid(parent, cloth, knot, V(0.05 * h, 0.045 * h, 0.04 * h), { region: 'skull' });
    for (const s of S) {
      const t = reg.box(parent, gearMat(ctx, e, c.cloth, 'cloth', false, { side: THREE.DoubleSide }), knot.clone().add(V(s * 0.04 * h, -0.14 * h, -0.02 * h)), V(0.05 * h, 0.26 * h, 0.01 * h), { region: 'skull' });
      t.rotation.z = s * 0.25;
      t.rotation.x = 0.2;
    }
  } else if (def.id === 'sunglasses' || def.id === 'eyeglasses') {
    const frame = gearMat(ctx, e, c.frame, def.id === 'sunglasses' ? 'dark' : 'metal');
    const lens = ctx.mat(c.lens, 'glass', { opacity: def.id === 'sunglasses' ? 0.92 : 0.28 });
    const ex = b.eye.x;
    const r = b.eye.w * (def.id === 'sunglasses' ? 1.25 : 1.15);
    const p = new THREE.Vector3();
    for (const s of S) {
      b.surface.hit(s * ex, b.eye.y, p);
      const z = p.z + 0.05 * h;
      const rim = reg.add(parent, new THREE.TorusGeometry(r, 0.008 * h + 0.004 * h * (def.id === 'sunglasses' ? 1 : 0), 6, 28), frame, { region: 'eyes', name: 'EQ_Eyewear' });
      rim.position.set(s * ex, b.eye.y, z);
      if (def.id === 'sunglasses') rim.scale.set(1.15, 0.85, 1);
      const l = reg.add(parent, new THREE.CircleGeometry(r, 28), lens, { region: 'eyes' });
      l.position.copy(rim.position);
      l.scale.copy(rim.scale);
      reg.limb(parent, frame, V(s * (ex + r * 1.1), b.eye.y, z - 0.01 * h), V(s * R.x * 1.02, b.eye.y - 0.02 * h, -0.06 * h), 0.008 * h, 0.008 * h, { region: 'eyes' });
    }
    b.surface.hit(0, b.eye.y, p);
    reg.limb(parent, frame, V(ex - r, b.eye.y + 0.01 * h, p.z + 0.05 * h), V(-(ex - r), b.eye.y + 0.01 * h, p.z + 0.05 * h), 0.008 * h, 0.008 * h, { region: 'eyes' });
  }
}

function buildBoots(ctx: BuildCtx, b: HumanoidBody, e: Equipped, def: AccessoryDef) {
  const c = colorsOf(e, def);
  const { reg } = ctx;
  const u = b.u;
  const leather = gearMat(ctx, e, c.leather, 'leather');
  const sole = ctx.mat(c.sole, 'leather');
  const buckle = gearMat(ctx, e, c.buckle, 'metal');
  ctx.hides.add('toes');
  ctx.hides.add('toenails');
  b.g.ankle.forEach((ankle, i) => {
    const foot = ankle.userData.foot as THREE.Group | undefined;
    if (!foot) return;
    const FL = b.dims.footLen;
    const digi = b.digitigrade;
    const heelZ = digi ? 0 : -FL * 0.18;
    const len = FL * (digi ? 0.55 : 1.0);
    const bootM = reg.ellipsoid(foot, leather, V(0, -u * 0.06, heelZ + len * 0.42), V(u * 0.16, u * 0.12, len * 0.58), { region: 'feet', name: `EQ_Boot_${i ? 'R' : 'L'}` });
    bootM.userData.equipUid = e.uid;
    const s = reg.box(foot, sole, V(0, -u * 0.17, heelZ + len * 0.42), V(u * 0.3, u * 0.06, len * 1.12), { region: 'feet' });
    s.userData.ground = true;
    const parent = digi ? ankle : b.g.knee[i];
    const segLen = digi ? b.dims.metaLen : b.dims.shinLen;
    const shaftTop = digi ? 0.08 : b.child ? 0.55 : 0.4;
    const r0 = digi ? b.dims.calfR * 0.55 + u * 0.05 : b.dims.calfR * (b.child ? 0.9 : 0.95) + u * 0.04;
    const r1 = digi ? b.dims.calfR * 0.45 + u * 0.05 : b.dims.calfR * 0.6 + u * 0.05;
    const top = V(0, -segLen * shaftTop, 0);
    const bot = V(0, -segLen * 1.02, 0);
    reg.limb(parent, leather, top, bot, r0, r1, { region: 'legs', name: 'EQ_BootShaft' });
    const cuff = reg.add(parent, new THREE.TorusGeometry(r0 + u * 0.01, u * 0.035, 6, 20), leather, { region: 'legs' });
    cuff.rotation.x = Math.PI / 2;
    cuff.position.copy(top);
    reg.box(parent, buckle, V(0, -segLen * 0.7, r1 + u * 0.03), V(u * 0.09, u * 0.06, u * 0.02), { region: 'legs' });
  });
}

function buildBelt(ctx: BuildCtx, b: HumanoidBody, e: Equipped, def: AccessoryDef) {
  const c = colorsOf(e, def);
  const { reg } = ctx;
  const u = b.u;
  const leather = gearMat(ctx, e, c.leather, 'leather');
  const buckle = gearMat(ctx, e, c.buckle, 'metal');
  const y = u * 0.32;
  const t = reg.add(b.g.pelvis, new THREE.TorusGeometry(1, 0.07, 8, 36), leather, { region: 'hips', name: 'EQ_Belt' });
  t.scale.set(b.dims.hipW * 1.1, b.dims.hipD * 1.14, u * 0.9);
  t.rotation.x = Math.PI / 2;
  t.position.y = y;
  reg.box(b.g.pelvis, buckle, V(0, y, b.dims.hipD * 1.14), V(u * 0.16, u * 0.13, u * 0.03), { region: 'hips' });
  for (const s of S) {
    const a = s * 0.9;
    reg.box(b.g.pelvis, leather, V(Math.sin(a) * b.dims.hipW * 1.12, y - u * 0.08, Math.cos(a) * b.dims.hipD * 1.12), V(u * 0.18, u * 0.2, u * 0.1), { region: 'hips', name: 'EQ_Pouch' }).rotation.y = a;
  }
}

function buildCompanion(ctx: BuildCtx, b: HumanoidBody, e: Equipped, def: AccessoryDef, parent: THREE.Object3D) {
  const c = colorsOf(e, def);
  const { reg } = ctx;
  const u = b.u;
  const body = ctx.mat(c.body, 'skin');
  const belly = ctx.mat(c.belly, 'skin');
  const eye = ctx.mat(c.eye, 'emissive', { emissive: c.eye, emissiveStrength: 0.5 });
  const dark = ctx.mat('#1a1418', 'dark');
  const g = new THREE.Group();
  parent.add(g);
  g.position.x += u * 0.08;
  const main = reg.ellipsoid(g, body, V(0, 0, 0), V(u * 0.16, u * 0.3, u * 0.18), { region: 'arms', name: 'EQ_Companion' });
  reg.ellipsoid(g, belly, V(u * 0.07, -u * 0.02, u * 0.05), V(u * 0.1, u * 0.22, u * 0.12), { region: 'arms' });
  const head = new THREE.Group();
  head.position.set(0, -u * 0.34, u * 0.02);
  g.add(head);
  reg.ellipsoid(head, body, V(0, 0, 0), V(u * 0.14, u * 0.13, u * 0.14), { region: 'arms' });
  const eyes: THREE.Mesh[] = [];
  for (const s of S) {
    const m = reg.ellipsoid(head, eye, V(u * 0.1, -u * 0.02, s * u * 0.06), V(u * 0.035, u * 0.045, u * 0.035), { region: 'arms' });
    reg.ellipsoid(head, dark, V(u * 0.13, -u * 0.02, s * u * 0.06), V(u * 0.012, u * 0.03, u * 0.014), { region: 'arms', pickable: false });
    eyes.push(m);
  }
  reg.box(head, dark, V(u * 0.12, -u * 0.08, 0), V(u * 0.02, u * 0.012, u * 0.08), { region: 'arms', pickable: false });
  for (let k = 0; k < 3; k += 1) {
    const ring = reg.add(parent, new THREE.TorusGeometry(b.dims.foreR * 1.12, u * 0.03, 6, 20), body, { region: 'arms' });
    ring.rotation.x = Math.PI / 2;
    ring.rotation.y = 0.3;
    ring.position.set(-u * 0.05, (k - 1) * u * 0.18, 0);
  }
  const base = main.scale.clone();
  ctx.updaters.push((f) => {
    const t = (f.time % 2) / 2;
    const br = Math.sin(t * Math.PI * 2) * 0.05;
    main.scale.set(base.x * (1 + br), base.y * (1 - br * 0.4), base.z * (1 + br));
    head.rotation.x = Math.sin(f.time * 0.7) * 0.15;
    const blink = f.time % 3.7 < 0.14 ? 0.1 : 1;
    for (const m of eyes) m.scale.y = u * 0.045 * blink;
  });
}

function buildMechShell(ctx: BuildCtx, b: HumanoidBody, e: Equipped, def: AccessoryDef) {
  const c = colorsOf(e, def);
  const shell = makeShell(ctx, b, e.uid);
  const { reg } = ctx;
  const u = b.u;
  const paint = gearMat(ctx, e, c.paint, 'metal');
  const panel = gearMat(ctx, e, c.panel, 'metal');
  const glow = ctx.mat(c.glow, 'emissive', { emissive: c.glow, emissiveStrength: 1 });
  if (def.id === 'mech_chest') {
    shell('chest', paint, 3, { region: 'chest', scale: V(1.04, 0.95, 1.06) });
    shell('trap', panel, 2.5, { region: 'shoulders' });
    reg.box(b.g.chest, panel, V(0, b.dims.torsoLen * 0.12, b.dims.chestD * 1.05), V(b.dims.chestW * 0.9, b.dims.torsoLen * 0.3, u * 0.06), { region: 'chest', name: 'EQ_MechPanel' });
    const core = reg.add(b.g.chest, new THREE.CircleGeometry(u * 0.14, 20), glow, { region: 'chest' });
    core.position.set(0, b.dims.torsoLen * 0.14, b.dims.chestD * 1.09);
  } else {
    shell('forearm1', paint, 3, { from: 0.1, to: 0.95, region: 'arms' });
    const f = b.g.el[1];
    reg.box(f, panel, V(-b.dims.foreR * 1.05, -b.dims.foreLen * 0.5, 0), V(u * 0.05, b.dims.foreLen * 0.55, b.dims.foreR * 1.1), { region: 'arms', name: 'EQ_MechPanel' });
    reg.box(f, glow, V(-b.dims.foreR * 1.1, -b.dims.foreLen * 0.5, 0), V(u * 0.02, b.dims.foreLen * 0.4, u * 0.04), { region: 'arms', pickable: false });
  }
}

export function buildHumanoidAccessories(ctx: BuildCtx, b: HumanoidBody) {
  for (const e of ctx.id.equipped) {
    if (packPlaceholder(ctx, e, b.g.chest)) continue;
    const def = ACCESSORY_BY_ID[e.id];
    if (!def || !def.bodies.includes(ctx.id.bodyKind)) continue;
    const before = ctx.reg.meshes.length;
    switch (def.id) {
      case 'ranger_outfit':
      case 'traveler_outfit':
      case 'child_outfit':
      case 'child_explorer':
        buildOutfit(ctx, b, e, def);
        break;
      case 'painted_armor':
        buildArmor(ctx, b, e, def);
        break;
      case 'goggles':
      case 'bandana':
      case 'sunglasses':
      case 'eyeglasses': {
        const sock = def.id === 'sunglasses' || def.id === 'eyeglasses' ? 'SOC-Eyewear' : 'SOC-HeadTop';
        const { inner } = equipRoot(ctx, e, sock, b.g.head);
        buildHeadGear(ctx, b, e, def, inner);
        break;
      }
      case 'blade':
      case 'launcher': {
        const { inner } = equipRoot(ctx, e, def.socket, b.g.wr[def.id === 'blade' ? 1 : 0]);
        inner.position.set(0, 0, 0);
        buildProp(ctx, e, def, inner, b.u);
        break;
      }
      case 'mech_chest':
      case 'mech_forearm':
        buildMechShell(ctx, b, e, def);
        break;
      case 'organic_companion': {
        const { inner } = equipRoot(ctx, e, def.socket, b.g.el[0]);
        inner.position.set(0, 0, 0);
        buildCompanion(ctx, b, e, def, inner);
        break;
      }
      case 'boots':
      case 'child_shoes':
        buildBoots(ctx, b, e, def);
        break;
      case 'belt':
        buildBelt(ctx, b, e, def);
        break;
      case 'cape':
      case 'torn_cape':
      case 'child_cape': {
        const { inner } = equipRoot(ctx, e, 'SOC-Cape', b.g.chest);
        inner.position.set(0, 0, 0);
        const len = (b.child ? 0.55 : 0.62) * (b.dims.torsoLen + b.dims.thighLen + b.dims.shinLen * 0.6);
        buildCape(ctx, inner, { width: b.dims.shoulderHalf * 2.1, length: len, depth: b.dims.chestD * 0.55, colors: colorsOf(e, def), torn: def.id === 'torn_cape', e, region: 'body' });
        break;
      }
      default:
        break;
    }
    for (let i = before; i < ctx.reg.meshes.length; i += 1) ctx.reg.meshes[i].userData.equipUid = e.uid;
    const obj = ctx.equipObjects[e.uid];
    if (obj) tag(obj, e.uid);
  }
}
