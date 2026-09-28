import { CONTROLS, CONTROL_BY_ID, controlRange, isControlVisible } from './controls';
import { ACCESSORY_BY_ID, CHILD_HAIR_FALLBACK, FULL_HAIR_STYLES, HAIR_STYLES, defaultLooks, type AccessoryDef } from './looks';
import { emptyAppearance } from './appearance';
import {
  AGE_PRESETS_ADULT, AGE_PRESETS_BEAST, ARCHETYPE_BY_ID, OLD_HAIR_GRAY, PRESENTATION_PRESETS,
} from './presets';
import type { BodyKind, Equipped, FacialHairPiece, HairPiece, Identity, StylePreset } from './types';

export const DEFAULT_COLORS: Record<string, string> = {
  skin: '#f6d2bc', lip: '#d98a86', nail: '#f4cfc6', iris: '#2fa47e', sclera: '#fbfbff', brow: '#4a2e20', lash: '#241a18',
  surfacePrimary: '#e58a2e', surfaceSecondary: '#2a1e1a', belly: '#f4ead8', mane: '#7a3e1e', horn: '#efe3c8', beak: '#f0b030',
  membrane: '#e0784a', claw: '#f2ecde',
  robotPaint: '#3f7fd8', robotPanel: '#eef0f2', robotJoint: '#3a3f48', robotGlow: '#58e0ff',
  paint: '#3a7bd5', paint2: '#f0ede8', emissive: '#58e0ff', joint: '#3a3f48',
  scale: '#c8442e', beastBelly: '#f2c890', beastMembrane: '#e0784a', beastHorn: '#3a2a2a', beastEye: '#f0d040', beastCrest: '#6a2a8a',
};

let equipCounter = 0;
export function equipUid(): string {
  equipCounter += 1;
  return `E${Date.now().toString(36)}${equipCounter.toString(36)}`;
}

export function makeEquip(id: string, def?: Pick<AccessoryDef, 'slot' | 'colors'>): Equipped {
  const d = def ?? ACCESSORY_BY_ID[id];
  return { uid: equipUid(), id, slot: d?.slot ?? id, colors: { ...(d?.colors ?? {}) }, damage: 0, offset: { p: [0, 0, 0], r: [0, 0, 0], s: 1 } };
}

const hair = (id: string, root = '#5a3420', tip = '#8a5634'): HairPiece => ({ id, volume: 0, width: 0, length: 0, root, tip, highlight: 0.6 });
const facial = (id: string, color = '#4a2e20'): FacialHairPiece => ({ id, length: 0, bulk: 0, color });

export function defaultOutfit(kind: BodyKind): string[] {
  if (kind === 'adult') return ['ranger_outfit', 'boots', 'belt'];
  if (kind === 'child') return ['child_outfit', 'child_shoes'];
  return [];
}

export function newCharacter(kind: BodyKind = 'adult', style: StylePreset = 'stories'): Identity {
  const id: Identity = {
    version: 1,
    name: kind === 'child' ? 'New child' : kind === 'robot' ? 'New robot' : kind === 'beast' ? 'New dragon' : 'New character',
    bodyKind: kind,
    archetype: kind === 'adult' || kind === 'child' ? 'human' : kind,
    style: kind === 'robot' ? 'legends' : style,
    values: {},
    looks: defaultLooks(kind),
    hair: { front: hair('swept'), back: hair('shortLayered'), sides: hair('short'), extras: [hair('ahoge')] },
    facialHair: { moustache: facial('none'), sideburns: facial('none'), beard: facial('none') },
    colors: { ...DEFAULT_COLORS },
    equipped: defaultOutfit(kind).map((e) => makeEquip(e)),
    appearance: emptyAppearance(),
    faceProfile: {
      rig: 'hybrid',
      wrinkles: { forehead: 0.5, brow: 0.5, eyes: 0.5, nose: 0.4, mouth: 0.5 },
      expressions: {},
    },
    physics: {
      hair: { enabled: true, amount: 0.5, stiffness: 0.6 },
      cape: { enabled: true, amount: 0.6, stiffness: 0.4 },
      tail: { enabled: true, amount: 0.6, stiffness: 0.5 },
      wings: { enabled: true, amount: 0.3, stiffness: 0.7 },
    },
    body: null,
  };
  if (kind === 'child') {
    id.hair = { front: hair('wispy'), back: hair('crop'), sides: hair('none'), extras: [hair('ahoge')] };
    id.values['skin.blush'] = 35;
  } else if (kind === 'adult') {
    id.values['skin.blush'] = 20;
  }
  if (kind === 'robot') id.values['robot.emissive'] = 70;
  return id;
}

export function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v));
}

export function clampToBody(values: Record<string, number>, kind: BodyKind): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(values)) {
    const ctl = CONTROL_BY_ID[k];
    if (!ctl || !ctl.bodies.includes(kind)) continue;
    const [lo, hi] = controlRange(ctl, kind);
    out[k] = Math.min(hi, Math.max(lo, v));
  }
  return out;
}

/** Fills element looks, colors, and values from an archetype. Presentation, age, hair, and gear are kept. */
export function applyArchetype(src: Identity, archetypeId: string): Identity {
  const arch = ARCHETYPE_BY_ID[archetypeId];
  if (!arch || (src.bodyKind !== 'adult' && src.bodyKind !== 'child')) return src;
  const id = clone(src);
  id.archetype = arch.id;
  id.looks = { ...id.looks, ...arch.looks };
  const kept: Record<string, number> = {};
  for (const [k, v] of Object.entries(id.values)) {
    if (k.startsWith('age.') || k.startsWith('skin.') || k.startsWith('eye.iris') || k.startsWith('eye.pupil') || k.startsWith('eye.catch')) kept[k] = v;
    if (['body.shoulders', 'body.chest', 'body.waist', 'body.hips', 'face.softness', 'body.height'].includes(k)) kept[k] = v;
  }
  const elementKeys = CONTROLS.filter((c) => c.path[0] === 'Elements').map((c) => c.id);
  for (const [k, v] of Object.entries(id.values)) if (!elementKeys.includes(k) && !(k in kept)) kept[k] = v;
  for (const k of elementKeys) delete kept[k];
  id.values = clampToBody({ ...kept, ...arch.values }, id.bodyKind);
  id.colors = { ...id.colors, ...arch.colors };
  return id;
}

export function applyPresentation(src: Identity, which: keyof typeof PRESENTATION_PRESETS): Identity {
  if (src.bodyKind !== 'adult') return src;
  const id = clone(src);
  id.values = { ...id.values, ...PRESENTATION_PRESETS[which] };
  return id;
}

export function applyAge(src: Identity, which: 'youngAdult' | 'adult' | 'old'): Identity {
  if (src.bodyKind !== 'adult' && src.bodyKind !== 'beast') return src;
  const id = clone(src);
  const preset = src.bodyKind === 'adult' ? AGE_PRESETS_ADULT[which] : AGE_PRESETS_BEAST[which];
  id.values = { ...id.values, ...preset };
  if (src.bodyKind === 'adult' && which === 'old') {
    const gray = (hex: string) => mixHex(hex, OLD_HAIR_GRAY, 0.75);
    id.hair.front.root = gray(id.hair.front.root);
    id.hair.front.tip = gray(id.hair.front.tip);
    id.hair.back.root = gray(id.hair.back.root);
    id.hair.back.tip = gray(id.hair.back.tip);
    id.hair.sides.root = gray(id.hair.sides.root);
    id.hair.sides.tip = gray(id.hair.sides.tip);
    id.colors.brow = mixHex(id.colors.brow, OLD_HAIR_GRAY, 0.6);
  }
  return id;
}

export function applyFullHairStyle(src: Identity, styleId: string): Identity {
  const style = FULL_HAIR_STYLES.find((s) => s.id === styleId);
  if (!style) return src;
  const id = clone(src);
  const kind = id.bodyKind;
  const pick = (hid: string) => (kind === 'child' ? childHairId(hid) : hid);
  id.hair.front = { ...id.hair.front, id: pick(style.front) };
  id.hair.back = { ...id.hair.back, id: pick(style.back) };
  id.hair.sides = { ...id.hair.sides, id: pick(style.sides) };
  id.hair.extras = style.extras.map((e) => ({ ...(id.hair.extras[0] ?? id.hair.front), id: e }));
  return id;
}

export function childHairId(id: string): string {
  const style = HAIR_STYLES.find((s) => s.id === id);
  if (style?.child) return id;
  if (id.startsWith('pack:')) return id;
  return CHILD_HAIR_FALLBACK[id] ?? 'crop';
}

export function ensureRequiredGear(id: Identity): Identity {
  if (id.bodyKind !== 'child') return id;
  const out = clone(id);
  out.equipped = out.equipped.filter((e) => !ACCESSORY_BY_ID[e.id] || ACCESSORY_BY_ID[e.id].bodies.includes('child'));
  const has = (slot: string) => out.equipped.some((e) => e.slot === slot);
  if (!has('outfit')) out.equipped.unshift(makeEquip('child_outfit'));
  if (!has('footwear')) out.equipped.push(makeEquip('child_shoes'));
  return out;
}

/** Switches body kind. Values that exist on both are kept and clamped. Gear that does not fit is removed. */
export function switchBodyKind(src: Identity, kind: BodyKind): Identity {
  if (src.bodyKind === kind) return src;
  const humanoidPair = (src.bodyKind === 'adult' || src.bodyKind === 'child') && (kind === 'adult' || kind === 'child');
  if (humanoidPair && kind === 'child') return makeChildCounterpart(src, false);
  const fresh = newCharacter(kind, src.style);
  if (humanoidPair) {
    fresh.looks = { ...fresh.looks, ...src.looks };
    fresh.archetype = src.archetype;
    fresh.colors = { ...fresh.colors, ...src.colors };
    fresh.values = clampToBody(src.values, kind);
    fresh.hair = clone(src.hair);
    fresh.appearance = clone(src.appearance);
    fresh.name = src.name.replace(/ \(child\)$/, '');
  }
  fresh.style = kind === 'robot' ? 'legends' : src.bodyKind === 'robot' ? 'stories' : src.style;
  return fresh;
}

/** Copies element looks, colors, and clamped shape values onto the child body, and drops adult-only controls. */
export function makeChildCounterpart(src: Identity, rename = true): Identity {
  if (src.bodyKind !== 'adult' && src.bodyKind !== 'child') return src;
  const child = newCharacter('child', src.style);
  child.archetype = src.archetype;
  child.looks = { ...child.looks, ...src.looks };
  child.colors = { ...child.colors, ...src.colors };
  const values = clampToBody(src.values, 'child');
  delete values['age.years'];
  child.values = { ...child.values, ...values };
  const mapPiece = (p: HairPiece): HairPiece => ({ ...p, id: childHairId(p.id) });
  child.hair = {
    front: mapPiece(src.hair.front),
    back: mapPiece(src.hair.back),
    sides: mapPiece(src.hair.sides),
    extras: src.hair.extras.map(mapPiece).filter((p) => HAIR_STYLES.some((s) => s.id === p.id && s.child) || p.id.startsWith('pack:')),
  };
  const keepGear = src.equipped.filter((e) => ACCESSORY_BY_ID[e.id]?.bodies.includes('child'));
  child.equipped = [...child.equipped, ...keepGear.map((e) => ({ ...clone(e), uid: equipUid() }))];
  child.faceProfile = clone(src.faceProfile);
  child.appearance = clone(src.appearance);
  for (const zone of Object.keys(child.appearance) as (keyof typeof child.appearance)[]) {
    child.appearance[zone] = child.appearance[zone].filter((l) => !['veins', 'bodyHair', 'wrinkles'].includes(l.category));
  }
  child.name = rename ? `${src.name.replace(/ \(child\)$/, '')} (child)` : src.name;
  return ensureRequiredGear(child);
}

export interface FamilyMember {
  label: string;
  identity: Identity;
}

export function deriveFamily(src: Identity): FamilyMember[] {
  if (src.bodyKind === 'beast') {
    return (['youngAdult', 'adult', 'old'] as const).map((a) => ({ label: ageLabel(a), identity: rename(applyAge(src, a), ageLabel(a)) }));
  }
  if (src.bodyKind !== 'adult') return [];
  const out: FamilyMember[] = (['youngAdult', 'adult', 'old'] as const).map((a) => ({ label: ageLabel(a), identity: rename(applyAge(src, a), ageLabel(a)) }));
  out.push({ label: 'Child', identity: makeChildCounterpart(src) });
  return out;
}

function ageLabel(a: 'youngAdult' | 'adult' | 'old'): string {
  return a === 'youngAdult' ? 'Young adult' : a === 'adult' ? 'Adult' : 'Old';
}

function rename(id: Identity, suffix: string): Identity {
  return { ...id, name: `${id.name} (${suffix.toLowerCase()})` };
}

/** Random identity values inside each control's range. Performance is untouched because it is not part of identity. */
export function randomizeIdentity(src: Identity, controlIds?: string[], amount = 0.55, rand: () => number = Math.random): Identity {
  const id = clone(src);
  const ids = controlIds ?? CONTROLS.filter((c) => c.tab === 'morphs' && isControlVisible(c, id.bodyKind, id.looks)).map((c) => c.id);
  for (const cid of ids) {
    const ctl = CONTROL_BY_ID[cid];
    if (!ctl || !isControlVisible(ctl, id.bodyKind, id.looks)) continue;
    const [lo, hi] = controlRange(ctl, id.bodyKind);
    const g = (rand() + rand() + rand()) / 3;
    const v = lo + (hi - lo) * (0.5 + (g - 0.5) * 2 * amount);
    const centered = lo < 0 ? v : Math.max(0, (rand() < 0.5 ? 0 : v));
    id.values[cid] = Math.round(Math.min(hi, Math.max(lo, centered)));
  }
  return id;
}

export const SAVE_FORMAT = 'anime-character';

export function serializeCharacter(id: Identity): string {
  return JSON.stringify({ format: SAVE_FORMAT, version: 1, identity: id }, null, 2);
}

export function deserializeCharacter(text: string): Identity {
  const data = JSON.parse(text);
  const raw = data?.format === SAVE_FORMAT ? data.identity : data?.identity ?? data;
  if (!raw || typeof raw !== 'object' || !raw.bodyKind) throw new Error('This file is not a saved character.');
  const kind = raw.bodyKind as BodyKind;
  if (!['adult', 'child', 'robot', 'beast'].includes(kind)) throw new Error(`Unknown body kind: ${raw.bodyKind}`);
  const base = newCharacter(kind, raw.style ?? 'stories');
  const id: Identity = {
    ...base,
    ...raw,
    values: clampToBody(raw.values ?? {}, kind),
    looks: { ...base.looks, ...(raw.looks ?? {}) },
    colors: { ...base.colors, ...(raw.colors ?? {}) },
    hair: { ...base.hair, ...(raw.hair ?? {}) },
    facialHair: { ...base.facialHair, ...(raw.facialHair ?? {}) },
    appearance: { ...base.appearance, ...(raw.appearance ?? {}) },
    faceProfile: { ...base.faceProfile, ...(raw.faceProfile ?? {}), wrinkles: { ...base.faceProfile.wrinkles, ...(raw.faceProfile?.wrinkles ?? {}) } },
    physics: { ...base.physics, ...(raw.physics ?? {}) },
    equipped: Array.isArray(raw.equipped)
      ? raw.equipped.map((e: Equipped) => ({ ...makeEquip(e.id), ...e, slot: e.slot ?? ACCESSORY_BY_ID[e.id]?.slot ?? e.id }))
      : base.equipped,
    version: 1,
  };
  if (kind === 'child') {
    id.facialHair = base.facialHair;
  }
  return ensureRequiredGear(id);
}

export function mixHex(a: string, b: string, t: number): string {
  const pa = parseHex(a);
  const pb = parseHex(b);
  const m = pa.map((v, i) => Math.round(v + (pb[i] - v) * t));
  return `#${m.map((v) => v.toString(16).padStart(2, '0')).join('')}`;
}

export function parseHex(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h.padEnd(6, '0');
  return [parseInt(full.slice(0, 2), 16), parseInt(full.slice(2, 4), 16), parseInt(full.slice(4, 6), 16)];
}

/** Value in slider units, zero when unset. */
export function val(id: Identity, key: string): number {
  return id.values[key] ?? 0;
}

export function changedControls(id: Identity): string[] {
  return Object.entries(id.values).filter(([k, v]) => v !== 0 && CONTROL_BY_ID[k]).map(([k]) => k);
}
