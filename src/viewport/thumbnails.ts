import * as THREE from 'three';
import type { ImportedPack } from '../library/importer';
import { neutralPerformance, resolvePerformance, wrinkleActivation, type PerformanceState } from '../model/performance';
import type { RenderOverrides } from '../model/presets';
import type { Identity, StylePreset } from '../model/types';
import { buildRig } from './build';
import { attachPacks } from './gltfPacks';
import { PostPipeline } from './postPipeline';
import type { Rig } from './rig';
import { withStyle } from './toonMaterial';

export type ThumbFrame = 'body' | 'head' | 'hair' | 'bust' | 'feet' | 'hands';

export interface ThumbJob {
  identity: Identity;
  frame: ThumbFrame;
  perf?: Partial<PerformanceState>;
}

const SIZE = 256;

let overrides: Partial<Record<StylePreset, RenderOverrides>> = {};

/** Keeps thumbnails in step with the Render section. Call clearThumbnails() afterwards to redraw. */
export function setThumbnailOverrides(o: Partial<Record<StylePreset, RenderOverrides>>) {
  overrides = o;
}

class ThumbRenderer {
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(26, 1, 0.05, 60);
  post: PostPipeline;

  constructor() {
    this.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true, premultipliedAlpha: false, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(1);
    this.renderer.setSize(SIZE, SIZE, false);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.post = new PostPipeline(this.renderer, true);
    this.post.setSize(SIZE, SIZE, 1);
  }

  frame(rig: Rig, frame: ThumbFrame): number {
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
    return dist;
  }

  render(style: StylePreset, focus: number, beast: boolean): string {
    return withStyle(style, overrides[style], (s) => {
      this.post.setStyle({ ...s, particles: 0, flare: 0, para: 0, vignette: 0 });
      this.post.render(this.scene, this.camera, { time: 0, focus, sensitivity: beast ? 0.6 : 1 });
      return this.renderer.domElement.toDataURL('image/png');
    });
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
    if (hasPacks) await attachPacks(rig, packs, () => true, perf.bodyPose);
    const w = resolvePerformance(perf, job.identity.faceProfile, 0, 0);
    rig.update({ w, time: 0, dt: 0, perf, wrinkle: wrinkleActivation({}, job.identity.faceProfile) });
    renderer.scene.add(rig.root);
    const focus = renderer.frame(rig, job.frame);
    return renderer.render(job.identity.style, focus, job.identity.bodyKind === 'beast');
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
