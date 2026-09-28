import * as THREE from 'three';
import type { ImportedPack } from '../library/importer';
import { neutralPerformance, resolvePerformance, wrinkleActivation, type PerformanceState } from '../model/performance';
import type { Identity } from '../model/types';
import { buildRig } from './build';
import { attachPacks } from './gltfPacks';
import type { Rig } from './rig';

export type ThumbFrame = 'body' | 'head' | 'hair' | 'bust' | 'feet' | 'hands';

export interface ThumbJob {
  identity: Identity;
  frame: ThumbFrame;
  perf?: Partial<PerformanceState>;
}

const SIZE = 256;

const quadVertex = /* glsl */ `
varying vec2 vUv;
void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`;

/** Same depth-edge outline as the viewport, over a transparent background so cards supply their own. */
const quadFragment = /* glsl */ `
uniform sampler2D tColor;
uniform sampler2D tDepth;
uniform vec2 uTexel;
uniform float uNear;
uniform float uFar;
varying vec2 vUv;
float lin(float d) {
  float z = d * 2.0 - 1.0;
  return 2.0 * uNear * uFar / (uFar + uNear - z * (uFar - uNear));
}
void main() {
  float d0 = texture2D(tDepth, vUv).r;
  vec4 c0 = texture2D(tColor, vUv);
  float z0 = lin(d0);
  float best = d0;
  vec2 bestUv = vUv;
  float edge = 0.0;
  vec2 offs[8];
  offs[0] = vec2(1.0, 0.0); offs[1] = vec2(-1.0, 0.0); offs[2] = vec2(0.0, 1.0); offs[3] = vec2(0.0, -1.0);
  offs[4] = vec2(0.7, 0.7); offs[5] = vec2(-0.7, 0.7); offs[6] = vec2(0.7, -0.7); offs[7] = vec2(-0.7, -0.7);
  for (int i = 0; i < 8; i++) {
    vec2 uv = vUv + offs[i] * uTexel * 1.2;
    float d = texture2D(tDepth, uv).r;
    float z = lin(d);
    float nearZ = min(z, z0);
    float diff = abs(z - z0) / max(nearZ, 1e-3);
    edge = max(edge, smoothstep(0.03, 0.08, diff));
    if (d < best) { best = d; bestUv = uv; }
  }
  if (best >= 1.0) edge = 0.0;
  vec3 lineCol = texture2D(tColor, bestUv).rgb * 0.35;
  float a = d0 >= 1.0 ? edge : max(c0.a, edge);
  vec3 col = d0 >= 1.0 ? lineCol : mix(c0.rgb, lineCol, edge);
  gl_FragColor = vec4(col, a);
  #include <colorspace_fragment>
}
`;

class ThumbRenderer {
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(26, 1, 0.05, 60);
  rt: THREE.WebGLRenderTarget;
  quadScene = new THREE.Scene();
  quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

  constructor() {
    this.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true, premultipliedAlpha: false, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(1);
    this.renderer.setSize(SIZE, SIZE, false);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.rt = new THREE.WebGLRenderTarget(SIZE, SIZE, { type: THREE.HalfFloatType, depthTexture: new THREE.DepthTexture(SIZE, SIZE), samples: 0 });
    this.rt.depthTexture!.type = THREE.UnsignedIntType;
    const quad = new THREE.Mesh(
      new THREE.PlaneGeometry(2, 2),
      new THREE.ShaderMaterial({
        vertexShader: quadVertex,
        fragmentShader: quadFragment,
        depthTest: false,
        depthWrite: false,
        transparent: true,
        uniforms: {
          tColor: { value: this.rt.texture },
          tDepth: { value: this.rt.depthTexture },
          uTexel: { value: new THREE.Vector2(1 / SIZE, 1 / SIZE) },
          uNear: { value: this.camera.near },
          uFar: { value: this.camera.far },
        },
      }),
    );
    quad.frustumCulled = false;
    this.quadScene.add(quad);
  }

  frame(rig: Rig, frame: ThumbFrame) {
    rig.root.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(rig.root);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const h = size.y;
    const beast = rig.identity.bodyKind === 'beast';
    const headPos = new THREE.Vector3(0, h * 0.9, 0);
    rig.head?.getWorldPosition(headPos);
    const fit = (extent: number) => extent / (2 * Math.tan((this.camera.fov * Math.PI) / 360)) * 1.12;
    let target = center.clone();
    let dist = fit(Math.max(size.y, size.x, beast ? size.z : 0));
    let dir = beast ? new THREE.Vector3(0.8, 0.3, 0.75) : new THREE.Vector3(0.3, 0.06, 1);
    switch (frame) {
      case 'head':
      case 'hair': {
        const kind = rig.identity.bodyKind;
        const hs = beast ? h * 0.38 : h * (kind === 'child' ? 0.24 : kind === 'robot' ? 0.21 : 0.17);
        const wide = frame === 'hair' && !beast;
        target = headPos.clone();
        target.y += beast ? 0 : wide ? -hs * 0.25 : hs * 0.08;
        dist = fit(hs * (wide ? 1.8 : 1.3));
        dir = beast ? new THREE.Vector3(0.6, 0.2, 0.9) : new THREE.Vector3(0.35, 0.05, 1);
        break;
      }
      case 'bust':
        target = beast ? headPos.clone() : new THREE.Vector3(headPos.x, headPos.y - h * 0.07, headPos.z);
        dist = fit(h * (beast ? 0.5 : 0.36));
        break;
      case 'hands':
        target = new THREE.Vector3(center.x, box.min.y + h * 0.5, center.z);
        dist = fit(h * 0.55);
        dir = new THREE.Vector3(0.55, 0.1, 1);
        break;
      case 'feet':
        target = new THREE.Vector3(center.x, box.min.y + h * 0.13, center.z);
        dist = fit(h * 0.34);
        dir = new THREE.Vector3(0.5, 0.35, 1);
        break;
      default:
        break;
    }
    dir.normalize();
    this.camera.position.copy(target).addScaledVector(dir, dist);
    this.camera.lookAt(target);
    this.camera.updateProjectionMatrix();
  }

  render(): string {
    const r = this.renderer;
    r.setRenderTarget(this.rt);
    r.setClearColor(0x000000, 0);
    r.clear();
    r.render(this.scene, this.camera);
    r.setRenderTarget(null);
    r.setClearColor(0x000000, 0);
    r.clear();
    r.render(this.quadScene, this.quadCam);
    return r.domElement.toDataURL('image/png');
  }
}

let renderer: ThumbRenderer | null = null;
const cache = new Map<string, string>();
type Waiter = (url: string) => void;
interface Queued { key: string; make: () => ThumbJob; packs: Map<string, ImportedPack>; waiters: Set<Waiter> }
const queue: Queued[] = [];
const byKey = new Map<string, Queued>();
let running = false;
let generation = 0;
const listeners = new Set<() => void>();

async function renderJob(job: ThumbJob, packs: Map<string, ImportedPack>): Promise<string> {
  renderer ??= new ThumbRenderer();
  const perf: PerformanceState = { ...neutralPerformance(), autoBlink: false, ...job.perf };
  const rig = buildRig(job.identity, packs, perf.bodyPose);
  try {
    const hasPacks = !!job.identity.body || Object.values(rig.equipObjects).some((o) => o.userData.pack);
    if (hasPacks) await attachPacks(rig, packs, () => true);
    const w = resolvePerformance(perf, job.identity.faceProfile, 0, 0);
    rig.update({ w, time: 0, dt: 0, perf, wrinkle: wrinkleActivation({}, job.identity.faceProfile) });
    renderer.scene.add(rig.root);
    renderer.frame(rig, job.frame);
    return renderer.render();
  } finally {
    renderer.scene.remove(rig.root);
    rig.dispose();
  }
}

function pump() {
  if (running) return;
  const next = queue.shift();
  if (!next) return;
  running = true;
  byKey.delete(next.key);
  const gen = generation;
  const done = (url: string) => {
    running = false;
    if (gen === generation) {
      if (url) cache.set(next.key, url);
      for (const w of next.waiters) w(url);
    }
    requestAnimationFrame(pump);
  };
  requestAnimationFrame(() => {
    let job: ThumbJob;
    try {
      job = next.make();
    } catch {
      done('');
      return;
    }
    renderJob(job, next.packs).then(done, () => done(''));
  });
}

export function cachedThumbnail(key: string): string | undefined {
  return cache.get(key);
}

/** Queues a render and calls back once with a PNG data URL (empty string if it failed). Returns a cancel function. */
export function requestThumbnail(key: string, make: () => ThumbJob, packs: Map<string, ImportedPack>, onDone: Waiter): () => void {
  const hit = cache.get(key);
  if (hit) {
    onDone(hit);
    return () => {};
  }
  let q = byKey.get(key);
  if (!q) {
    q = { key, make, packs, waiters: new Set() };
    byKey.set(key, q);
    queue.push(q);
  }
  q.waiters.add(onDone);
  pump();
  const entry = q;
  return () => {
    entry.waiters.delete(onDone);
    if (entry.waiters.size === 0 && byKey.get(key) === entry) {
      byKey.delete(key);
      const i = queue.indexOf(entry);
      if (i >= 0) queue.splice(i, 1);
    }
  };
}

/** Drops every cached thumbnail so visible cards render again. */
export function clearThumbnails() {
  cache.clear();
  queue.length = 0;
  byKey.clear();
  generation++;
  for (const l of listeners) l();
}

export function onThumbnailsCleared(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
