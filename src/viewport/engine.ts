import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { TransformControls } from 'three/examples/jsm/controls/TransformControls.js';
import type { ImportedPack } from '../library/importer';
import { STYLE_PRESETS, type RenderOverrides } from '../model/presets';
import { CLIP_BY_ID, clipFinished, resolvePerformance, sampleClip, wrinkleActivation, type PerformanceState } from '../model/performance';
import type { Identity, Region, StylePreset } from '../model/types';
import { buildRig } from './build';
import { attachPacks, packMeshes } from './gltfPacks';
import { PostPipeline } from './postPipeline';
import type { Rig } from './rig';
import { applyStyle } from './toonMaterial';

export interface EngineCallbacks {
  onHover(region: Region | null, equipUid: string | null): void;
  onPick(region: Region | null, equipUid: string | null, ev: PointerEvent): void;
  onRegionDragStart(region: Region, view: 'front' | 'side'): boolean;
  onRegionDrag(dx: number, dy: number): void;
  onRegionDragEnd(): void;
  onGizmoStart(): void;
  onGizmoChange(uid: string, p: [number, number, number], r: [number, number, number], s: number): void;
  onGizmoEnd(): void;
  onClipFinished(): void;
  onPackReport(failed: { id: string; reason: string }[]): void;
}

export class Engine {
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  overlay = new THREE.Scene();
  camera: THREE.PerspectiveCamera;
  controls: OrbitControls;
  gizmo: TransformControls;
  rig: Rig | null = null;
  holder = new THREE.Group();
  private post: PostPipeline;
  private shadow: THREE.Mesh;
  private raycaster = new THREE.Raycaster();
  private pointer = new THREE.Vector2();
  private raf = 0;
  private last = performance.now() / 1000;
  private dirty = true;
  private pending: { id: Identity; packs: Map<string, ImportedPack>; pose: PerformanceState['bodyPose'] } | null = null;
  private rigKey = '';
  private nextBlink = 2;
  private blinkStart = -10;
  private hoverRegion: Region | null = null;
  private hoverEquip: string | null = null;
  highlight: Region[] | null = null;
  selectedEquip: string | null = null;
  perf: PerformanceState | null = null;
  profile: Identity['faceProfile'] | null = null;
  turntable = false;
  shapeDrag = false;
  private drag: { x: number; y: number } | null = null;
  private resizeObs: ResizeObserver;
  private style: StylePreset = 'stories';
  private overrides: Partial<Record<StylePreset, RenderOverrides>> = {};
  private buildGen = 0;
  private framedOnce = false;
  private userMoved = false;
  private lastPreset = 'frame';

  constructor(private host: HTMLElement, private cb: EngineCallbacks) {
    this.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(this.renderer.domElement);
    this.renderer.domElement.style.display = 'block';
    this.camera = new THREE.PerspectiveCamera(30, 1, 0.05, 60);
    this.camera.position.set(0, 1.1, 4.2);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.set(0, 0.95, 0);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.12;
    this.controls.minDistance = 0.3;
    this.controls.maxDistance = 14;
    this.controls.update();
    this.controls.addEventListener('start', () => {
      this.userMoved = true;
    });
    this.gizmo = new TransformControls(this.camera, this.renderer.domElement);
    this.gizmo.setSize(0.8);
    this.overlay.add(this.gizmo.getHelper());
    this.gizmo.addEventListener('dragging-changed', (e) => {
      this.controls.enabled = !(e as unknown as { value: boolean }).value;
      if ((e as unknown as { value: boolean }).value) this.cb.onGizmoStart();
      else this.cb.onGizmoEnd();
    });
    this.gizmo.addEventListener('objectChange', () => {
      const o = this.gizmo.object;
      if (!o || !this.selectedEquip) return;
      this.cb.onGizmoChange(this.selectedEquip, [o.position.x, o.position.y, o.position.z], [o.rotation.x, o.rotation.y, o.rotation.z], o.scale.x);
    });

    this.scene.add(this.holder);
    const sh = document.createElement('canvas');
    sh.width = sh.height = 128;
    const g = sh.getContext('2d')!;
    const grad = g.createRadialGradient(64, 64, 4, 64, 64, 62);
    grad.addColorStop(0, 'rgba(0,0,0,0.45)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 128, 128);
    const shTex = new THREE.CanvasTexture(sh);
    this.shadow = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: shTex, transparent: true, depthWrite: false }));
    this.shadow.rotation.x = -Math.PI / 2;
    this.shadow.renderOrder = -1;
    this.scene.add(this.shadow);

    this.post = new PostPipeline(this.renderer, false);
    this.post.setStyle(applyStyle(this.style));

    const el = this.renderer.domElement;
    el.addEventListener('pointermove', this.onMove);
    el.addEventListener('pointerdown', this.onDown);
    window.addEventListener('pointerup', this.onUp);
    el.addEventListener('pointerleave', () => {
      if (!this.drag) this.setHover(null, null);
    });
    this.resizeObs = new ResizeObserver(() => this.resize());
    this.resizeObs.observe(host);
    this.resize();
    this.loop();
  }

  setStyle(style: StylePreset) {
    this.style = style;
    this.post.setStyle(applyStyle(style, this.overrides[style]));
  }

  /** The person's Render section overrides, per style. */
  setRenderOverrides(o: Partial<Record<StylePreset, RenderOverrides>>) {
    this.overrides = o;
    this.setStyle(this.style);
  }

  setCharacter(id: Identity, packs: Map<string, ImportedPack>, pose: PerformanceState['bodyPose']) {
    const key = JSON.stringify({ ...id, faceProfile: undefined, style: undefined, name: undefined }) + pose + [...packs.keys()].join(',');
    if (id.style !== this.style) this.setStyle(id.style);
    if (key === this.rigKey) return;
    this.rigKey = key;
    this.pending = { id, packs, pose };
    this.dirty = true;
  }

  private rebuild() {
    if (!this.pending) return;
    const { id, packs, pose } = this.pending;
    this.pending = null;
    const turn = this.rig?.root.rotation.y ?? 0;
    const prevKind = this.rig?.identity.bodyKind;
    if (this.rig) {
      this.gizmo.detach();
      this.holder.remove(this.rig.root);
      this.rig.dispose();
    }
    const rig = buildRig(id, packs, pose);
    rig.root.rotation.y = turn;
    this.holder.add(rig.root);
    this.rig = rig;
    const gen = ++this.buildGen;
    const hasPacks = !!id.body || Object.values(rig.equipObjects).some((o) => o.userData.pack);
    if (hasPacks) {
      attachPacks(rig, packs, () => gen === this.buildGen).then((r) => {
        if (gen === this.buildGen && r.failed.length) this.cb.onPackReport(r.failed);
      });
    }
    const s = Math.max(0.8, rig.height * (id.bodyKind === 'beast' ? 0.9 : 0.45));
    this.shadow.scale.set(s, s, 1);
    this.applySelection();
    if (!this.framedOnce || prevKind !== id.bodyKind) {
      this.framedOnce = true;
      this.cameraPreset('frame');
    }
  }

  private allMeshes(): THREE.Mesh[] {
    if (!this.rig) return [];
    return [...this.rig.meshes, ...packMeshes(this.rig)];
  }

  applySelection() {
    const hl = new Set<string>(this.highlight ?? []);
    if (this.hoverRegion && this.shapeDrag) hl.add(this.hoverRegion);
    for (const m of this.allMeshes()) {
      const eq = m.userData.equipUid as string | undefined;
      let s = 0;
      if (eq && (eq === this.selectedEquip || (eq === this.hoverEquip && !this.shapeDrag))) s = eq === this.selectedEquip ? 0.6 : 0.35;
      else if (!eq && m.userData.region && hl.has(m.userData.region)) s = 1;
      m.userData.sel = s;
      const mat = m.material as THREE.ShaderMaterial;
      if (mat.uniforms?.uSelect && !this.rig?.meshes.includes(m)) mat.uniforms.uSelect.value = s;
    }
    if (this.rig && this.selectedEquip && this.rig.equipObjects[this.selectedEquip]) {
      const o = this.rig.equipObjects[this.selectedEquip];
      if (this.gizmo.object !== o) this.gizmo.attach(o);
    } else if (this.gizmo.object) this.gizmo.detach();
  }

  setGizmoMode(mode: 'translate' | 'rotate' | 'scale') {
    this.gizmo.setMode(mode);
  }

  private pick(ev: PointerEvent): { region: Region | null; equip: string | null } {
    const r = this.renderer.domElement.getBoundingClientRect();
    this.pointer.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const meshes = this.allMeshes().filter((m) => m.visible && m.userData.pickable !== false);
    const hits = this.raycaster.intersectObjects(meshes, false);
    for (const h of hits) {
      let o: THREE.Object3D | null = h.object;
      while (o && !o.visible) o = null;
      if (!o) continue;
      const eq = (h.object.userData.equipUid as string | undefined) ?? null;
      let region = (h.object.userData.region as Region | undefined) ?? null;
      if (!region && eq) region = 'body';
      return { region, equip: eq };
    }
    return { region: null, equip: null };
  }

  private setHover(region: Region | null, equip: string | null) {
    if (region === this.hoverRegion && equip === this.hoverEquip) return;
    this.hoverRegion = region;
    this.hoverEquip = equip;
    this.cb.onHover(region, equip);
    this.applySelection();
  }

  private viewAxis(): 'front' | 'side' {
    const d = new THREE.Vector3().subVectors(this.camera.position, this.controls.target);
    const yaw = Math.atan2(d.x, d.z) - (this.rig?.root.rotation.y ?? 0);
    return Math.abs(Math.sin(yaw)) > 0.72 ? 'side' : 'front';
  }

  private onMove = (ev: PointerEvent) => {
    if (this.drag) {
      const dx = (ev.clientX - this.drag.x) / 120;
      const dy = -(ev.clientY - this.drag.y) / 120;
      this.cb.onRegionDrag(dx, dy);
      return;
    }
    if ((ev.buttons & 1) !== 0) return;
    const p = this.pick(ev);
    this.setHover(p.region, p.equip);
    this.renderer.domElement.style.cursor = this.shapeDrag && p.region ? 'ns-resize' : p.equip ? 'pointer' : 'default';
  };

  private onDown = (ev: PointerEvent) => {
    if (ev.button !== 0) return;
    if (this.gizmo.dragging || (this.gizmo as unknown as { axis: string | null }).axis) return;
    const p = this.pick(ev);
    if (this.shapeDrag && p.region && !p.equip) {
      if (this.cb.onRegionDragStart(p.region, this.viewAxis())) {
        this.controls.enabled = false;
        this.drag = { x: ev.clientX, y: ev.clientY };
        this.renderer.domElement.setPointerCapture(ev.pointerId);
        return;
      }
    }
    const start = { x: ev.clientX, y: ev.clientY };
    const up = (e2: PointerEvent) => {
      window.removeEventListener('pointerup', up);
      if (Math.hypot(e2.clientX - start.x, e2.clientY - start.y) < 4) this.cb.onPick(p.region, p.equip, e2);
    };
    window.addEventListener('pointerup', up);
  };

  private onUp = () => {
    if (!this.drag) return;
    this.drag = null;
    this.controls.enabled = true;
    this.cb.onRegionDragEnd();
  };

  cameraPreset(name: string, saved?: { position: [number, number, number]; target: [number, number, number] }) {
    if (saved) {
      this.camera.position.set(...saved.position);
      this.controls.target.set(...saved.target);
      this.controls.update();
      this.userMoved = true;
      return;
    }
    this.lastPreset = name;
    this.userMoved = false;
    const rig = this.rig;
    const h = rig?.height ?? 1.7;
    const box = rig ? new THREE.Box3().setFromObject(rig.root) : new THREE.Box3(new THREE.Vector3(-0.5, 0, -0.5), new THREE.Vector3(0.5, 1.7, 0.5));
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const fit = (extent: number) => extent / (2 * Math.tan((this.camera.fov * Math.PI) / 360)) * 1.18;
    const headPos = new THREE.Vector3();
    if (rig?.head) rig.head.getWorldPosition(headPos);
    else headPos.set(0, h * 0.9, 0);
    const beast = rig?.identity.bodyKind === 'beast';
    const aspect = this.camera.aspect;
    let target = center.clone();
    let dir = new THREE.Vector3(0, 0.05, 1);
    let dist = fit(Math.max(size.y, size.x / aspect, beast ? size.z / aspect : 0));
    switch (name) {
      case 'front':
        break;
      case 'side':
        dir = new THREE.Vector3(1, 0.05, 0);
        if (beast) dist = fit(Math.max(size.y, size.z / aspect));
        break;
      case 'back':
        dir = new THREE.Vector3(0, 0.05, -1);
        break;
      case 'threeQuarter':
        dir = new THREE.Vector3(0.7, 0.12, 0.72);
        break;
      case 'face': {
        target = headPos.clone();
        const kind = rig?.identity.bodyKind;
        const hs = beast ? h * 0.35 : h * (kind === 'child' ? 0.23 : kind === 'robot' ? 0.2 : 0.16);
        dist = fit(hs * 1.4);
        dir = beast ? new THREE.Vector3(0.45, 0.15, 1) : new THREE.Vector3(0, 0.02, 1);
        break;
      }
      case 'upper':
        target = new THREE.Vector3(center.x, box.max.y - size.y * 0.25, center.z);
        dist = fit(size.y * 0.55);
        break;
      default:
        dir = beast ? new THREE.Vector3(0.75, 0.25, 0.8) : new THREE.Vector3(0.28, 0.08, 1);
        break;
    }
    dir.normalize().applyAxisAngle(new THREE.Vector3(0, 1, 0), rig?.root.rotation.y ?? 0);
    this.controls.target.copy(target);
    this.camera.position.copy(target).addScaledVector(dir, dist);
    this.controls.update();
  }

  currentView(): { position: [number, number, number]; target: [number, number, number] } {
    const p = this.camera.position;
    const t = this.controls.target;
    return { position: [p.x, p.y, p.z], target: [t.x, t.y, t.z] };
  }

  /** Camera orientation as a quaternion [x, y, z, w], for the axis widget. */
  viewQuaternion(): [number, number, number, number] {
    const q = this.camera.quaternion;
    return [q.x, q.y, q.z, q.w];
  }

  screenshot(): string {
    this.render();
    return this.renderer.domElement.toDataURL('image/png');
  }

  private resize() {
    const w = Math.max(1, this.host.clientWidth);
    const h = Math.max(1, this.host.clientHeight);
    this.renderer.setSize(w, h, false);
    this.renderer.domElement.style.width = `${w}px`;
    this.renderer.domElement.style.height = `${h}px`;
    const pr = this.renderer.getPixelRatio();
    this.post.setSize(Math.floor(w * pr), Math.floor(h * pr), pr);
    const aspect = w / h;
    const changed = Math.abs(aspect - this.camera.aspect) > 0.01;
    this.camera.aspect = aspect;
    this.camera.updateProjectionMatrix();
    if (changed && this.rig && !this.userMoved) this.cameraPreset(this.lastPreset);
  }

  private render() {
    const r = this.renderer;
    this.post.render(this.scene, this.camera, {
      time: performance.now() / 1000,
      focus: this.camera.position.distanceTo(this.controls.target),
      sensitivity: this.rig?.identity.bodyKind === 'beast' ? 0.6 : 1,
    });
    if (this.gizmo.object) {
      r.autoClear = false;
      r.clearDepth();
      r.render(this.overlay, this.camera);
      r.autoClear = true;
    }
  }

  private loop = () => {
    this.raf = requestAnimationFrame(this.loop);
    const now = performance.now() / 1000;
    const dt = Math.min(0.1, now - this.last);
    this.last = now;
    if (this.dirty) {
      this.dirty = false;
      this.rebuild();
    }
    const rig = this.rig;
    if (rig && this.perf && this.profile) {
      if (this.turntable) rig.root.rotation.y += dt * 0.5;
      const perf = this.perf;
      let idle = 0;
      const manualBlink = (perf.manual['PF-Blink_L'] ?? 0) + (perf.manual['PF-Blink_R'] ?? 0) > 0;
      if (perf.autoBlink && !manualBlink && !(perf.clip && perf.clip.id !== 'talk')) {
        if (now > this.nextBlink) {
          this.blinkStart = now;
          this.nextBlink = now + 2.2 + Math.random() * 3.6;
        }
        const t = now - this.blinkStart;
        const clip = CLIP_BY_ID.blink;
        if (clip && t < clip.duration) idle = sampleClip(clip, t)['PF-Blink_L'] ?? 0;
      }
      const w = resolvePerformance(perf, this.profile, now, idle);
      const wrinkle = wrinkleActivation(perf.wrinklePreview ? w : {}, this.profile);
      rig.update({ w, time: now, dt, perf, wrinkle });
      if (clipFinished(perf, now)) this.cb.onClipFinished();
    }
    this.controls.update();
    this.render();
  };

  dispose() {
    cancelAnimationFrame(this.raf);
    this.resizeObs.disconnect();
    window.removeEventListener('pointerup', this.onUp);
    this.gizmo.dispose();
    this.controls.dispose();
    this.rig?.dispose();
    this.post.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}

export const STYLE_BG = (style: StylePreset) => STYLE_PRESETS[style].background;
