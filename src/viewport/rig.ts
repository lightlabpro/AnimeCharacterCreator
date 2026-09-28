import * as THREE from 'three';
import type { ImportedPack } from '../library/importer';
import type { BodyPose, PerformanceState } from '../model/performance';
import type { Identity, WrinkleRegion } from '../model/types';
import { PartRegistry } from './parts';
import { toon, type ToonKind, type ToonMaterial } from './toonMaterial';

export interface FrameState {
  w: Record<string, number>;
  time: number;
  dt: number;
  perf: PerformanceState;
  wrinkle: Record<WrinkleRegion, number>;
}

export interface BuildCtx {
  id: Identity;
  n(key: string): number;
  reg: PartRegistry;
  updaters: ((f: FrameState) => void)[];
  sockets: Record<string, THREE.Object3D>;
  packs: Map<string, ImportedPack>;
  hides: Set<string>;
  equipObjects: Record<string, THREE.Object3D>;
  mat(color: string, kind?: ToonKind, extra?: Partial<Parameters<typeof toon>[0]>): ToonMaterial;
  pose: BodyPose;
}

export interface Rig {
  root: THREE.Group;
  meshes: THREE.Mesh[];
  sockets: Record<string, THREE.Object3D>;
  equipObjects: Record<string, THREE.Object3D>;
  head: THREE.Object3D | null;
  height: number;
  identity: Identity;
  update(f: FrameState): void;
  addUpdater(fn: (f: FrameState) => void): void;
  dispose(): void;
}

export function createCtx(id: Identity, packs: Map<string, ImportedPack>, pose: BodyPose): BuildCtx {
  const reg = new PartRegistry();
  const matCache = new Map<string, ToonMaterial>();
  return {
    id,
    n: (key: string) => (id.values[key] ?? 0) / 100,
    reg,
    updaters: [],
    sockets: {},
    packs,
    hides: new Set(),
    equipObjects: {},
    pose,
    mat(color, kind = 'cloth', extra) {
      if (extra) return toon({ color, kind, ...extra });
      const key = `${color}:${kind}`;
      let m = matCache.get(key);
      if (!m) {
        m = toon({ color, kind });
        matCache.set(key, m);
      }
      return m;
    },
  };
}

export function socket(ctx: BuildCtx, name: string, parent: THREE.Object3D, pos: THREE.Vector3Like, rot?: THREE.Euler): THREE.Object3D {
  const o = new THREE.Object3D();
  o.name = name;
  o.userData.socket_name = name;
  o.position.set(pos.x, pos.y, pos.z);
  if (rot) o.rotation.copy(rot);
  parent.add(o);
  ctx.sockets[name] = o;
  return o;
}

/** Drops the character so its lowest mesh touches the floor. */
export function groundSnap(root: THREE.Group, meshes: THREE.Mesh[]) {
  root.updateMatrixWorld(true);
  let minY = Infinity;
  const box = new THREE.Box3();
  for (const m of meshes) {
    if (!m.userData.ground) continue;
    box.setFromObject(m);
    minY = Math.min(minY, box.min.y);
  }
  if (Number.isFinite(minY)) root.position.y -= minY;
  root.updateMatrixWorld(true);
}

export function finishRig(ctx: BuildCtx, root: THREE.Group, head: THREE.Object3D | null): Rig {
  const box = new THREE.Box3().setFromObject(root);
  for (const m of ctx.reg.meshes) {
    m.onBeforeRender = () => {
      const mat = m.material as THREE.ShaderMaterial;
      const u = mat.uniforms?.uSelect;
      if (u) {
        const s = m.userData.sel ?? 0;
        if (u.value !== s) {
          u.value = s;
          mat.uniformsNeedUpdate = true;
        }
      }
    };
  }
  return {
    root,
    meshes: ctx.reg.meshes,
    sockets: ctx.sockets,
    equipObjects: ctx.equipObjects,
    head,
    height: box.max.y - box.min.y,
    identity: ctx.id,
    update(f) {
      for (const u of ctx.updaters) u(f);
    },
    addUpdater(fn) {
      ctx.updaters.push(fn);
    },
    dispose() {
      ctx.reg.dispose();
      root.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.isMesh && !ctx.reg.meshes.includes(m)) {
          if (!m.geometry.userData.cached) m.geometry.dispose();
        }
      });
    },
  };
}

export interface PoseAngles {
  shoulder: number;
  shoulderFwd: number;
  elbow: number;
  hipSpread: number;
  hipFwd: number;
  knee: number;
  ankle: number;
  spine: number;
  waveArm: boolean;
}

export function poseAngles(pose: BodyPose): PoseAngles {
  switch (pose) {
    case 'relaxed':
      return { shoulder: 0.14, shoulderFwd: 0.05, elbow: -0.25, hipSpread: 0.04, hipFwd: 0, knee: 0.04, ankle: 0, spine: 0, waveArm: false };
    case 'tpose':
      return { shoulder: 1.52, shoulderFwd: 0, elbow: 0, hipSpread: 0.06, hipFwd: 0, knee: 0, ankle: 0, spine: 0, waveArm: false };
    case 'hero':
      return { shoulder: 0.32, shoulderFwd: 0.1, elbow: -0.35, hipSpread: 0.2, hipFwd: 0, knee: 0.05, ankle: 0, spine: -0.04, waveArm: false };
    case 'wave':
      return { shoulder: 0.16, shoulderFwd: 0.05, elbow: -0.2, hipSpread: 0.05, hipFwd: 0, knee: 0.03, ankle: 0, spine: 0, waveArm: true };
    case 'sit':
      return { shoulder: 0.35, shoulderFwd: 0.5, elbow: -0.6, hipSpread: 0.22, hipFwd: -1.35, knee: 2.1, ankle: -0.75, spine: 0.35, waveArm: false };
    default:
      return { shoulder: 0.72, shoulderFwd: 0.04, elbow: -0.12, hipSpread: 0.05, hipFwd: 0, knee: 0.02, ankle: 0, spine: 0, waveArm: false };
  }
}
