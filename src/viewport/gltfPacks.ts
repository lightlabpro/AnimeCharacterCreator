import * as THREE from 'three';
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';
import type { ImportedPack } from '../library/importer';
import { assetUrl, resolveRelative } from '../library/platform';
import { CONTROLS } from '../model/controls';
import type { Identity } from '../model/types';
import type { Rig } from './rig';
import { toon, type ToonKind } from './toonMaterial';

const cache = new Map<string, Promise<GLTF>>();

function loadPack(pack: ImportedPack): Promise<GLTF> | null {
  if (!pack.mainAsset) return null;
  const main = pack.mainAsset;
  const mainUrl = assetUrl(main);
  let p = cache.get(mainUrl);
  if (!p) {
    const manager = new THREE.LoadingManager();
    manager.setURLModifier((url) => {
      if (url === mainUrl || url.startsWith('data:')) return url;
      if (url.startsWith('blob:')) {
        const tail = decodeURIComponent(url.split('/').pop() ?? '');
        return assetUrl(resolveRelative(main, tail));
      }
      return url;
    });
    const loader = new GLTFLoader(manager);
    p = loader.loadAsync(mainUrl);
    cache.set(mainUrl, p);
    p.catch(() => cache.delete(mainUrl));
  }
  return p;
}

/** Material category from the material or mesh name. The order matters: the first match wins. */
export function kindFor(name: string): ToonKind {
  const n = name.toLowerCase();
  const words = n.split(/[^a-z]+/);
  if (n.includes('hair')) return 'hair';
  if (n.includes('lens') || n.includes('goggle')) return 'lens';
  if (n.includes('crystal') || words.includes('gem') || words.includes('ice')) return 'crystal';
  if (n.includes('membrane') || words.includes('aura')) return 'membrane';
  if (n.includes('velvet')) return 'velvet';
  if (n.includes('metal') || n.includes('paint') || n.includes('armor') || n.includes('gold') || n.includes('steel')) return 'metal';
  if (n.includes('leather') || n.includes('strap')) return 'leather';
  if (n.includes('skin')) return 'skin';
  if (n.includes('scale')) return 'scale';
  if (n.includes('fur')) return 'fur';
  if (n.includes('glass')) return 'glass';
  if (n.includes('glow') || n.includes('emiss')) return 'emissive';
  return 'cloth';
}

/** Outline shells draw in the post pass's line color: black with zero alpha marks a line pixel. */
const outlineShellMaterial = new THREE.ShaderMaterial({
  vertexShader: /* glsl */ `
#include <common>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
void main() {
  #include <skinbase_vertex>
  #include <begin_vertex>
  #include <morphtarget_vertex>
  #include <skinning_vertex>
  #include <project_vertex>
}`,
  fragmentShader: 'void main() { gl_FragColor = vec4(0.0); }',
  blending: THREE.NoBlending,
});

/** Replaces imported PBR materials with the toon shader so packs match the procedural parts. */
function toonify(root: THREE.Object3D, colorOverrides: Record<string, string>) {
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    const src = (Array.isArray(mesh.material) ? mesh.material[0] : mesh.material) as THREE.MeshStandardMaterial;
    const name = src?.name ?? mesh.name;
    const meshName = mesh.name.toLowerCase();
    if (meshName.endsWith('_shadow')) {
      mesh.visible = false;
      mesh.userData.shadowProxy = true;
      return;
    }
    if (meshName.endsWith('_outline')) {
      mesh.material = outlineShellMaterial;
      mesh.userData.outlineShell = true;
      mesh.userData.pickable = false;
      return;
    }
    const kind = meshName.endsWith('_line') ? 'dark' : kindFor(name);
    const key = Object.keys(colorOverrides).find((k) => name.toLowerCase().includes(k.toLowerCase()));
    const color = key ? colorOverrides[key] : `#${(src?.color ?? new THREE.Color('#cccccc')).getHexString()}`;
    const emissive = src?.emissive && src.emissive.getHex() !== 0 ? src.emissive : null;
    const m = toon({
      color,
      kind,
      map: src?.map ?? undefined,
      recolor: !!key && !!src?.map,
      aoMap: src?.aoMap ?? undefined,
      ilmMap: src?.metalnessMap ?? src?.roughnessMap ?? undefined,
      emissiveMap: src?.emissiveMap ?? undefined,
      normalMap: src?.normalMap ?? undefined,
      normalScale: src?.normalScale ? Math.min(0.5, src.normalScale.x * 0.35) : undefined,
      opacity: src?.transparent ? src.opacity : 1,
      side: src?.side,
      emissive: emissive ? `#${emissive.getHexString()}` : undefined,
      emissiveStrength: emissive ? src.emissiveIntensity ?? 1 : kind === 'emissive' ? 1 : 0,
    });
    mesh.material = m;
    mesh.userData.pickable = true;
  });
}

function boneKey(prop: string): string {
  return prop.replace(/_(length|scale|width)$/, '').replace(/_/g, '').toLowerCase();
}

function boneBase(name: string): string {
  return name.replace(/^DEF-/, '').replace(/[._](L|R|l|r)$/, '').replace(/[^a-zA-Z]/g, '').toLowerCase();
}

/** Writes identity values into ID- shape keys, bone scale properties, and armature extras. */
export function applyIdentityToScene(root: THREE.Object3D, id: Identity) {
  const morphW: Record<string, number> = {};
  const boneScale: Record<string, { v: number; axis: 'y' | 'xyz' | 'x' }> = {};
  for (const c of CONTROLS) {
    if (!c.bodies.includes(id.bodyKind)) continue;
    const v = (id.values[c.id] ?? 0) / 100;
    if (c.morph) {
      if (v >= 0 || !c.morphNeg) morphW[c.morph] = Math.max(morphW[c.morph] ?? 0, Math.max(0, v));
      if (c.morphNeg) morphW[c.morphNeg] = Math.max(morphW[c.morphNeg] ?? 0, Math.max(0, -v));
    }
    if (c.bone) {
      const { prop, lo, hi } = c.bone;
      const s = v >= 0 ? 1 + v * (hi - 1) : 1 + v * (1 - lo);
      boneScale[boneKey(prop)] = { v: s, axis: prop.endsWith('_scale') ? 'xyz' : prop.endsWith('_width') ? 'x' : 'y' };
    }
  }
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (mesh.isMesh && mesh.morphTargetDictionary && mesh.morphTargetInfluences) {
      for (const [k, i] of Object.entries(mesh.morphTargetDictionary)) {
        if (k.startsWith('ID-')) mesh.morphTargetInfluences[i] = morphW[k] ?? 0;
      }
    }
    if ((o as THREE.Bone).isBone && o.name.startsWith('DEF-')) {
      const b = boneScale[boneBase(o.name)];
      if (b) {
        if (!o.userData.restScale) o.userData.restScale = o.scale.clone();
        const r = o.userData.restScale as THREE.Vector3;
        if (b.axis === 'xyz') o.scale.copy(r).multiplyScalar(b.v);
        else if (b.axis === 'x') o.scale.set(r.x * b.v, r.y, r.z);
        else o.scale.set(r.x, r.y * b.v, r.z);
      }
    }
    if (o.userData && typeof o.userData === 'object') {
      for (const c of CONTROLS) {
        if (c.bone && c.bone.prop in o.userData) o.userData[c.bone.prop] = boneScale[boneKey(c.bone.prop)]?.v ?? 1;
      }
    }
  });
}

/** Drives PF- shape keys every frame from the resolved performance weights. */
function performanceDriver(root: THREE.Object3D) {
  const targets: { infl: number[]; map: [string, number][] }[] = [];
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (mesh.isMesh && mesh.morphTargetDictionary && mesh.morphTargetInfluences) {
      const map = Object.entries(mesh.morphTargetDictionary).filter(([k]) => k.startsWith('PF-'));
      if (map.length) targets.push({ infl: mesh.morphTargetInfluences, map });
    }
  });
  return (w: Record<string, number>) => {
    for (const t of targets) for (const [k, i] of t.map) t.infl[i] = w[k] ?? 0;
  };
}

function findSocket(root: THREE.Object3D): THREE.Object3D | null {
  let found: THREE.Object3D | null = null;
  root.traverse((o) => {
    if (!found && (o.name.startsWith('SOC-') || o.userData?.socket_name)) found = o;
  });
  return found;
}

export interface PackAttachResult {
  loaded: string[];
  failed: { id: string; reason: string }[];
}

/** Loads glTF packs for the body and every pack-backed equip on the rig. Safe to call after the rig is replaced. */
export async function attachPacks(rig: Rig, packs: Map<string, ImportedPack>, isCurrent: () => boolean): Promise<PackAttachResult> {
  const result: PackAttachResult = { loaded: [], failed: [] };
  const id = rig.identity;
  const jobs: Promise<void>[] = [];
  const bodyPack = id.body ? packs.get(id.body) : undefined;
  if (bodyPack) {
    const p = loadPack(bodyPack);
    if (p) {
      jobs.push(p.then((gltf) => {
        if (!isCurrent()) return;
        const scene = SkeletonUtils.clone(gltf.scene);
        toonify(scene, {});
        applyIdentityToScene(scene, id);
        for (const m of rig.meshes) if (!m.userData.equipUid) m.visible = false;
        scene.name = `PACK_${bodyPack.id}`;
        rig.root.add(scene);
        const drive = performanceDriver(scene);
        rig.addUpdater((f) => drive(f.w));
        result.loaded.push(bodyPack.id);
      }).catch((e: unknown) => {
        result.failed.push({ id: bodyPack.id, reason: e instanceof Error ? e.message : String(e) });
      }));
    }
  }
  for (const [, obj] of Object.entries(rig.equipObjects)) {
    const pack = obj.userData.pack as ImportedPack | undefined;
    if (!pack) continue;
    const p = loadPack(pack);
    if (!p) {
      result.failed.push({ id: pack.id, reason: 'The pack has no .glb or .gltf file.' });
      continue;
    }
    jobs.push(p.then((gltf) => {
      if (!isCurrent()) return;
      const scene = SkeletonUtils.clone(gltf.scene);
      toonify(scene, (obj.userData.packColors as Record<string, string>) ?? {});
      applyIdentityToScene(scene, id);
      const soc = findSocket(scene);
      if (soc) {
        scene.updateMatrixWorld(true);
        const wp = new THREE.Vector3();
        soc.getWorldPosition(wp);
        scene.position.sub(wp);
      }
      scene.traverse((o) => {
        o.userData.equipUid = obj.userData.equipUid;
      });
      obj.add(scene);
      const drive = performanceDriver(scene);
      rig.addUpdater((f) => drive(f.w));
      result.loaded.push(pack.id);
    }).catch((e: unknown) => {
      result.failed.push({ id: pack.id, reason: e instanceof Error ? e.message : String(e) });
    }));
  }
  await Promise.all(jobs);
  return result;
}

/** Meshes added from packs, for picking. */
export function packMeshes(rig: Rig): THREE.Mesh[] {
  const out: THREE.Mesh[] = [];
  rig.root.traverse((o) => {
    const m = o as THREE.Mesh;
    if (m.isMesh && !rig.meshes.includes(m) && m.visible) out.push(m);
  });
  return out;
}
