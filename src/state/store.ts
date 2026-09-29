import { create } from 'zustand';
import {
  applyAge, applyArchetype, applyFullHairStyle, applyPresentation, clone, deriveFamily, deserializeCharacter,
  ensureRequiredGear, makeChildCounterpart, makeEquip, newCharacter, randomizeIdentity, serializeCharacter,
  switchBodyKind, type FamilyMember,
} from '../model/character';
import { CONTROL_BY_ID, controlRange } from '../model/controls';
import { ACCESSORY_BY_ID } from '../model/looks';
import { captureSlot, WHEEL_SLOTS, blendFaces, wheelWeights, type MixScope, type MixerSlot } from '../model/mixer';
import { neutralPerformance, type PerformanceState } from '../model/performance';
import type { RenderOverrides } from '../model/presets';
import type { BodyKind, Equipped, Identity, Region, StylePreset } from '../model/types';
import { hairSlotForPack, importLibrary, libraryTabFor, type ImportReport, type ImportedPack, type ScanResult } from '../library/importer';
import { libraryOf } from '../model/types';
import { openTextFile, saveTextFile } from '../library/platform';

export type RightPanel = 'modify' | 'mixer' | 'appearance' | 'face';
export type ModifyTab = 'attribute' | 'pose' | 'morphs' | 'material' | 'physics';

export interface SavedView {
  name: string;
  position: [number, number, number];
  target: [number, number, number];
}

interface UIState {
  rightPanel: RightPanel;
  modifyTab: ModifyTab;
  libraryCategory: string;
  librarySearch: string;
  morphSearch: string;
  morphNode: string;
  highlight: Region[] | null;
  selectedEquip: string | null;
  shapeDrag: boolean;
  turntable: boolean;
  cameraRequest: { name: string; nonce: number } | null;
  savedViews: SavedView[];
  toast: { text: string; nonce: number } | null;
  showImportReport: boolean;
  gizmoMode: 'translate' | 'rotate' | 'scale';
}

interface MixerState {
  scope: MixScope;
  mode: 'edit' | 'mix';
  slots: (MixerSlot | null)[];
  handle: [number, number];
  base: Identity | null;
  expression: string | null;
}

export interface AppState {
  identity: Identity;
  past: Identity[];
  future: Identity[];
  dragSnapshot: Identity | null;
  perf: PerformanceState;
  packs: ImportedPack[];
  report: ImportReport | null;
  ui: UIState;
  mixer: MixerState;
  family: FamilyMember[];
  favorites: string[];
  /** Render section overrides per style. Saved on this machine, not in the character. */
  renderOverrides: Partial<Record<StylePreset, RenderOverrides>>;
  filePath: string | null;
  /** The identity as last saved or opened, used to show unsaved changes. */
  savedIdentity: Identity | null;

  commit(fn: (id: Identity) => Identity | void, label?: string): void;
  /** Applies a change without an undo step. Wrap a continuous gesture in beginEdit and endEdit. */
  editLive(fn: (id: Identity) => Identity | void): void;
  updateEquip(uid: string, fn: (e: Equipped) => void): void;
  applyPack(pack: ImportedPack): void;
  beginEdit(): void;
  setValueLive(key: string, value: number): void;
  endEdit(): void;
  setValue(key: string, value: number): void;
  resetValue(key: string): void;
  undo(): void;
  redo(): void;

  newCharacter(kind?: BodyKind): void;
  resetIdentity(): void;
  setBodyKind(kind: BodyKind): void;
  setStyle(style: StylePreset): void;
  setArchetype(id: string): void;
  setPresentation(which: 'feminine' | 'neutral' | 'masculine'): void;
  setAge(which: 'youngAdult' | 'adult' | 'old'): void;
  setLook(slot: string, look: string): void;
  setColor(key: string, color: string): void;
  applyFullHair(styleId: string): void;
  equip(id: string, def?: { slot: string; colors: Record<string, string>; exclusive?: boolean }): void;
  unequip(uid: string): void;
  randomize(ids?: string[]): void;
  makeChild(): void;
  makeFamily(): void;
  loadIdentity(id: Identity): void;

  setPerf(p: Partial<PerformanceState>): void;
  setPerfKey(key: string, v: number): void;
  playClip(id: string, loop?: boolean): void;
  stopClip(): void;
  resetPerformance(): void;

  importScan(scan: ScanResult): void;
  toggleFavorite(id: string): void;
  setRenderOverride(style: StylePreset, patch: RenderOverrides, persist?: boolean): void;
  resetRenderOverrides(style: StylePreset): void;
  setUI(p: Partial<UIState>): void;
  toast(text: string): void;
  requestCamera(name: string): void;

  setMixer(p: Partial<MixerState>): void;
  mixerCapture(slot: number, from?: Identity, label?: string): void;
  mixerClear(slot: number): void;
  mixerSetHandle(h: [number, number]): void;
  mixerBegin(): void;
  mixerEnd(): void;

  saveCharacter(): Promise<void>;
  openCharacter(): Promise<void>;
}

const HISTORY_LIMIT = 120;

function loadFavorites(): string[] {
  try {
    return JSON.parse(localStorage.getItem('creator.favorites') ?? '[]');
  } catch {
    return [];
  }
}

function saveFavorites(f: string[]) {
  try {
    localStorage.setItem('creator.favorites', JSON.stringify(f));
  } catch {
    /* storage unavailable */
  }
}

const OVERRIDES_KEY = 'creator.renderOverrides';

function loadOverrides(): Partial<Record<StylePreset, RenderOverrides>> {
  try {
    const raw = JSON.parse(localStorage.getItem(OVERRIDES_KEY) ?? '{}');
    return raw && typeof raw === 'object' ? raw : {};
  } catch {
    return {};
  }
}

function saveOverrides(o: Partial<Record<StylePreset, RenderOverrides>>) {
  try {
    localStorage.setItem(OVERRIDES_KEY, JSON.stringify(o));
  } catch {
    /* storage unavailable */
  }
}

function clampValue(identity: Identity, key: string, value: number): number {
  const ctl = CONTROL_BY_ID[key];
  if (!ctl) return value;
  const [lo, hi] = controlRange(ctl, identity.bodyKind);
  return Math.min(hi, Math.max(lo, Math.round(value)));
}

export const useStore = create<AppState>()((set, get) => {
  const push = (prev: Identity, next: Identity) => {
    const past = [...get().past, prev].slice(-HISTORY_LIMIT);
    set({ identity: next, past, future: [] });
  };

  return {
    identity: newCharacter('adult'),
    past: [],
    future: [],
    dragSnapshot: null,
    perf: neutralPerformance(),
    packs: [],
    report: null,
    ui: {
      rightPanel: 'modify',
      modifyTab: 'morphs',
      libraryCategory: 'Actor',
      librarySearch: '',
      morphSearch: '',
      morphNode: 'Currently Used',
      highlight: null,
      selectedEquip: null,
      shapeDrag: false,
      turntable: false,
      cameraRequest: null,
      savedViews: [],
      toast: null,
      showImportReport: false,
      gizmoMode: 'translate',
    },
    mixer: { scope: 'head', mode: 'mix', slots: Array(WHEEL_SLOTS).fill(null), handle: [0, 0], base: null, expression: null },
    family: [],
    favorites: typeof localStorage !== 'undefined' ? loadFavorites() : [],
    renderOverrides: typeof localStorage !== 'undefined' ? loadOverrides() : {},
    filePath: null,
    savedIdentity: null,

    commit(fn) {
      const prev = get().identity;
      const draft = clone(prev);
      const result = fn(draft) ?? draft;
      push(prev, result);
    },
    editLive(fn) {
      const draft = clone(get().identity);
      set({ identity: fn(draft) ?? draft });
    },
    updateEquip(uid, fn) {
      get().commit((id) => {
        const e = id.equipped.find((x) => x.uid === uid);
        if (e) fn(e);
      });
    },
    applyPack(pack) {
      const cur = get().identity;
      if (pack.library !== libraryOf(cur.bodyKind)) {
        get().toast(`${pack.displayName} belongs to the ${pack.library.replace('_', ' ')} library and cannot be used on this body.`);
        return;
      }
      const tab = libraryTabFor(pack);
      if (tab === 'Body') {
        get().commit((id) => {
          id.body = id.body === pack.id ? null : pack.id;
        });
        return;
      }
      if (tab === 'Hair') {
        const slot = hairSlotForPack(pack);
        get().commit((id) => {
          const piece = { id: `pack:${pack.id}`, volume: 0, width: 0, length: 0, root: id.hair.back.root, tip: id.hair.back.tip, highlight: 0.6 };
          if (slot === 'extra') id.hair.extras = [...id.hair.extras.filter((p) => p.id !== piece.id), piece];
          else id.hair[slot] = piece;
        });
        return;
      }
      if (tab === 'Actor' || tab === 'Material') {
        const preset = pack.preset as Partial<Identity> | null;
        if (!preset) {
          get().toast(`${pack.displayName} has no preset file to apply.`);
          return;
        }
        get().commit((id) => {
          if (preset.values) id.values = { ...id.values, ...preset.values };
          if (preset.looks) id.looks = { ...id.looks, ...preset.looks };
          if (preset.colors) id.colors = { ...id.colors, ...preset.colors };
        });
        return;
      }
      if (tab === 'Head') {
        get().toast(`${pack.displayName} adds shape keys to imported bodies. Its sliders are the ones under Morphs.`);
        return;
      }
      if (tab === 'Motion') {
        get().toast(`${pack.displayName} is a motion. Motions play on imported glTF bodies that contain the same action.`);
        return;
      }
      get().equip(pack.id, { slot: pack.slot, colors: {}, exclusive: true });
    },
    beginEdit() {
      if (!get().dragSnapshot) set({ dragSnapshot: get().identity });
    },
    setValueLive(key, value) {
      const id = get().identity;
      const v = clampValue(id, key, value);
      const values = { ...id.values };
      if (v === 0) delete values[key];
      else values[key] = v;
      set({ identity: { ...id, values } });
    },
    endEdit() {
      const snap = get().dragSnapshot;
      if (!snap) return;
      set({ dragSnapshot: null });
      if (JSON.stringify(snap.values) !== JSON.stringify(get().identity.values) || snap !== get().identity) {
        set({ past: [...get().past, snap].slice(-HISTORY_LIMIT), future: [] });
      }
    },
    setValue(key, value) {
      get().commit((id) => {
        const v = clampValue(id, key, value);
        if (v === 0) delete id.values[key];
        else id.values[key] = v;
      });
    },
    resetValue(key) {
      get().setValue(key, 0);
    },
    undo() {
      const { past, identity, future } = get();
      if (!past.length) return;
      set({ identity: past[past.length - 1], past: past.slice(0, -1), future: [identity, ...future] });
    },
    redo() {
      const { past, identity, future } = get();
      if (!future.length) return;
      set({ identity: future[0], future: future.slice(1), past: [...past, identity] });
    },

    newCharacter(kind = 'adult') {
      const cur = get().identity;
      push(cur, newCharacter(kind, cur.bodyKind === 'robot' && kind !== 'robot' ? 'stories' : cur.style));
      set({ perf: neutralPerformance(), filePath: null, savedIdentity: null });
    },
    resetIdentity() {
      const cur = get().identity;
      const fresh = newCharacter(cur.bodyKind, cur.style);
      fresh.name = cur.name;
      push(cur, fresh);
    },
    setBodyKind(kind) {
      const cur = get().identity;
      if (cur.bodyKind === kind) return;
      push(cur, switchBodyKind(cur, kind));
      set({ ui: { ...get().ui, selectedEquip: null } });
    },
    setStyle(style) {
      get().commit((id) => {
        id.style = style;
      });
    },
    setRenderOverride(style, patch, persist = true) {
      const all = { ...get().renderOverrides, [style]: { ...(get().renderOverrides[style] ?? {}), ...patch } };
      set({ renderOverrides: all });
      if (persist) saveOverrides(all);
    },
    resetRenderOverrides(style) {
      const all = { ...get().renderOverrides };
      delete all[style];
      set({ renderOverrides: all });
      saveOverrides(all);
    },
    setArchetype(aid) {
      get().commit((id) => applyArchetype(id, aid));
    },
    setPresentation(which) {
      get().commit((id) => applyPresentation(id, which));
    },
    setAge(which) {
      get().commit((id) => applyAge(id, which));
    },
    setLook(slot, look) {
      get().commit((id) => {
        id.looks[slot] = look;
      });
    },
    setColor(key, color) {
      get().commit((id) => {
        id.colors[key] = color;
      });
    },
    applyFullHair(styleId) {
      get().commit((id) => applyFullHairStyle(id, styleId));
    },
    equip(eid, def) {
      get().commit((id) => {
        const d = def ?? ACCESSORY_BY_ID[eid];
        if (!d) return;
        const exclusive = def?.exclusive ?? ACCESSORY_BY_ID[eid]?.exclusive ?? true;
        if (exclusive) id.equipped = id.equipped.filter((e) => e.slot !== d.slot);
        id.equipped = id.equipped.filter((e) => e.id !== eid);
        id.equipped.push(makeEquip(eid, d));
        return ensureRequiredGear(id);
      });
    },
    unequip(uid) {
      get().commit((id) => {
        const e = id.equipped.find((x) => x.uid === uid);
        id.equipped = id.equipped.filter((x) => x.uid !== uid);
        const out = ensureRequiredGear(id);
        if (e && id.bodyKind === 'child' && (e.slot === 'outfit' || e.slot === 'footwear')) {
          get().toast('The child body always keeps an outfit and shoes. The default was put back.');
        }
        return out;
      });
      if (get().ui.selectedEquip === uid) set({ ui: { ...get().ui, selectedEquip: null } });
    },
    randomize(ids) {
      get().commit((id) => randomizeIdentity(id, ids));
    },
    makeChild() {
      const cur = get().identity;
      if (cur.bodyKind !== 'adult') return;
      push(cur, makeChildCounterpart(cur));
      get().toast('Child counterpart made. Adult presentation, age, facial hair, and muscle were left out.');
    },
    makeFamily() {
      const fam = deriveFamily(get().identity);
      set({ family: fam });
      get().toast(fam.length ? `Family made: ${fam.map((f) => f.label).join(', ')}. Open them from Actor in the library.` : 'Family is available on an adult humanoid or the dragon.');
    },
    loadIdentity(identity) {
      push(get().identity, clone(identity));
    },

    setPerf(p) {
      set({ perf: { ...get().perf, ...p } });
    },
    setPerfKey(key, v) {
      const manual = { ...get().perf.manual };
      if (v <= 0) delete manual[key];
      else manual[key] = Math.min(1, v);
      set({ perf: { ...get().perf, manual } });
    },
    playClip(cid, loop) {
      set({ perf: { ...get().perf, clip: { id: cid, start: performance.now() / 1000, speed: 1, loop: loop ?? (cid === 'talk' || cid === 'wrinkles') } } });
    },
    stopClip() {
      set({ perf: { ...get().perf, clip: null } });
    },
    resetPerformance() {
      const p = get().perf;
      set({ perf: { ...neutralPerformance(), autoBlink: p.autoBlink, wrinklePreview: p.wrinklePreview, bodyPose: p.bodyPose } });
    },

    importScan(scan) {
      const existing = new Set(get().packs.map((p) => p.id));
      const { packs, report } = importLibrary(scan, existing);
      const byId = new Map(get().packs.map((p) => [p.id, p]));
      for (const p of packs) byId.set(p.id, p);
      set({ packs: [...byId.values()], report, ui: { ...get().ui, showImportReport: true } });
    },
    toggleFavorite(fid) {
      const f = get().favorites.includes(fid) ? get().favorites.filter((x) => x !== fid) : [...get().favorites, fid];
      saveFavorites(f);
      set({ favorites: f });
    },
    setUI(p) {
      set({ ui: { ...get().ui, ...p } });
    },
    toast(text) {
      set({ ui: { ...get().ui, toast: { text, nonce: Date.now() } } });
    },
    requestCamera(name) {
      set({ ui: { ...get().ui, cameraRequest: { name, nonce: Date.now() } } });
    },

    setMixer(p) {
      set({ mixer: { ...get().mixer, ...p } });
    },
    mixerCapture(slot, from, label) {
      const src = from ?? get().mixer.base ?? get().identity;
      const slots = get().mixer.slots.slice();
      slots[slot] = captureSlot(src, label ?? `Face ${slot + 1}`);
      set({ mixer: { ...get().mixer, slots } });
    },
    mixerClear(slot) {
      const slots = get().mixer.slots.slice();
      slots[slot] = null;
      set({ mixer: { ...get().mixer, slots } });
    },
    mixerBegin() {
      if (!get().mixer.base) set({ mixer: { ...get().mixer, base: get().identity }, dragSnapshot: get().dragSnapshot ?? get().identity });
    },
    mixerSetHandle(h) {
      const m = get().mixer;
      const base = m.base ?? get().identity;
      const weights = wheelWeights(h, m.slots.map((s) => !!s));
      const blended = blendFaces(base, m.slots, weights, m.scope);
      set({ mixer: { ...m, handle: h, base }, identity: blended });
    },
    mixerEnd() {
      set({ mixer: { ...get().mixer, base: null } });
      get().endEdit();
    },

    async saveCharacter() {
      const id = get().identity;
      const path = await saveTextFile(`${id.name.replace(/[^\w\- ]+/g, '').trim() || 'character'}.json`, serializeCharacter(id));
      if (path) {
        set({ filePath: path, savedIdentity: id });
        get().toast(`Saved ${path}`);
      }
    },
    async openCharacter() {
      const file = await openTextFile();
      if (!file) return;
      try {
        const id = deserializeCharacter(file.text);
        get().loadIdentity(id);
        set({ filePath: file.path, perf: neutralPerformance(), savedIdentity: get().identity });
        get().toast(`Opened ${file.path}`);
      } catch (e) {
        get().toast(`Could not open that file: ${(e as Error).message}`);
      }
    },
  };
});
