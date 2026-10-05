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

/**
 * Clean, repeatable renders of the current character for the render validator.
 * Transparent background, no ground shadow, no grain or vignette, and a narrow field of view so every body
 * view has the same scale (the validator checks that front, side and back are the same height).
 */
export type CaptureView = 'front' | 'three_quarter' | 'side' | 'back' | 'face' | 'face_three_quarter';
export const CAPTURE_VIEWS: CaptureView[] = ['front', 'three_quarter', 'side', 'back', 'face', 'face_three_quarter'];

const DIRECTION: Record<CaptureView, [number, number, number]> = {
  front: [0, 0.02, 1],
  three_quarter: [0.62, 0.1, 0.78],
  side: [1, 0.02, 0],
  back: [0, 0.02, -1],
  face: [0, 0.02, 1],
  face_three_quarter: [0.5, 0.06, 0.86],
};

export interface CaptureOptions {
  size?: number;
  views?: CaptureView[];
  overrides?: Partial<Record<StylePreset, RenderOverrides>>;
  perf?: Partial<PerformanceState>;
}

/** Frames one view. Returns the camera distance. Body views share one scale, face views share another. */
function frame(camera: THREE.PerspectiveCamera, rig: Rig, view: CaptureView): number {
  rig.root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(rig.root);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const kind = rig.identity.bodyKind;
  const head = new THREE.Vector3(0, size.y * 0.9, 0);
  rig.head?.getWorldPosition(head);
  const fit = (extent: number) => extent / (2 * Math.tan((camera.fov * Math.PI) / 360)) * 1.08;
  const isFace = view === 'face' || view === 'face_three_quarter';
  const headSpan = size.y * (kind === 'child' ? 0.24 : kind === 'robot' ? 0.21 : 0.17);
  const target = isFace ? new THREE.Vector3(head.x, head.y, head.z) : center.clone();
  const dist = isFace ? fit(headSpan * 1.5) : fit(Math.max(size.y, size.x * 1.1, size.z));
  const dir = new THREE.Vector3(...DIRECTION[view]).normalize().applyAxisAngle(new THREE.Vector3(0, 1, 0), rig.root.rotation.y);
  camera.position.copy(target).addScaledVector(dir, dist);
  camera.lookAt(target);
  camera.updateProjectionMatrix();
  return dist;
}

/** Renders the identity from each view. Returns PNG data URLs keyed by view name. */
export async function captureViews(identity: Identity, packs: Map<string, ImportedPack>, opts: CaptureOptions = {}): Promise<Record<string, string>> {
  const size = opts.size ?? 768;
  const views = opts.views ?? CAPTURE_VIEWS;
  const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true, premultipliedAlpha: false, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(size, size, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const post = new PostPipeline(renderer, true);
  post.setSize(size, size, 1);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(12, 1, 0.05, 80);
  const perf: PerformanceState = { ...neutralPerformance(), autoBlink: false, ...opts.perf };
  const rig = buildRig(identity, packs, perf.bodyPose);
  const out: Record<string, string> = {};
  try {
    const hasPacks = !!identity.body || Object.values(rig.equipObjects).some((o) => o.userData.pack);
    if (hasPacks) await attachPacks(rig, packs, () => true, perf.bodyPose);
    const w = resolvePerformance(perf, identity.faceProfile, 0, 0);
    rig.update({ w, time: 0, dt: 0, perf, wrinkle: wrinkleActivation({}, identity.faceProfile) });
    scene.add(rig.root);
    for (const view of views) {
      const focus = frame(camera, rig, view);
      out[view] = withStyle(identity.style, opts.overrides?.[identity.style], (s) => {
        post.setStyle({ ...s, particles: 0, flare: 0, para: 0, vignette: 0 });
        post.render(scene, camera, { time: 0, focus, sensitivity: identity.bodyKind === 'beast' ? 0.6 : 1 });
        return renderer.domElement.toDataURL('image/png');
      });
    }
  } finally {
    scene.remove(rig.root);
    rig.dispose();
    post.dispose();
    renderer.dispose();
  }
  return out;
}
