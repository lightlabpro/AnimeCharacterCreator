import { CONTROLS } from './controls';
import { clone } from './character';
import type { Identity } from './types';

export type MixScope = 'head' | 'eyes' | 'nose' | 'mouth' | 'skull' | 'ears' | 'muzzle';

export const MIX_SCOPES: { id: MixScope; label: string; prefixes: string[]; looks: string[] }[] = [
  { id: 'head', label: 'Whole head', prefixes: ['face.', 'skull.', 'jaw.', 'chin.', 'cheek.', 'brow.', 'eye.', 'lid.', 'lash.', 'nose.', 'mouth.', 'lip.', 'ear.', 'muzzle.', 'earEl.'], looks: ['muzzle', 'ears', 'pupil'] },
  { id: 'eyes', label: 'Eyes', prefixes: ['eye.', 'lid.', 'lash.'], looks: ['pupil'] },
  { id: 'nose', label: 'Nose', prefixes: ['nose.'], looks: [] },
  { id: 'mouth', label: 'Mouth', prefixes: ['mouth.', 'lip.'], looks: [] },
  { id: 'skull', label: 'Skull and jaw', prefixes: ['face.', 'skull.', 'jaw.', 'chin.', 'cheek.'], looks: [] },
  { id: 'ears', label: 'Ears', prefixes: ['ear.', 'earEl.'], looks: ['ears'] },
  { id: 'muzzle', label: 'Muzzle', prefixes: ['muzzle.'], looks: ['muzzle'] },
];

export function scopeControlIds(scope: MixScope): string[] {
  const s = MIX_SCOPES.find((m) => m.id === scope)!;
  return CONTROLS.filter((c) => c.tab === 'morphs' && s.prefixes.some((p) => c.id.startsWith(p))).map((c) => c.id);
}

export interface MixerSlot {
  label: string;
  values: Record<string, number>;
  looks: Record<string, string>;
}

export function captureSlot(id: Identity, label: string): MixerSlot {
  return { label, values: { ...id.values }, looks: { ...id.looks } };
}

export const WHEEL_SLOTS = 6;

export function slotDirection(i: number): [number, number] {
  const a = -Math.PI / 2 + (i / WHEEL_SLOTS) * Math.PI * 2;
  return [Math.cos(a), Math.sin(a)];
}

/** Weights for each wheel slot given a handle position inside the unit disc. */
export function wheelWeights(handle: [number, number], filled: boolean[]): number[] {
  const r = Math.hypot(handle[0], handle[1]);
  const w = filled.map((f, i) => {
    if (!f || r < 1e-4) return 0;
    const [dx, dy] = slotDirection(i);
    const cos = (handle[0] * dx + handle[1] * dy) / r;
    const angular = Math.max(0, cos);
    return angular * angular;
  });
  const sum = w.reduce((a, b) => a + b, 0);
  if (sum <= 0) return w.map(() => 0);
  const reach = Math.min(1, r);
  return w.map((x) => (x / sum) * reach);
}

/** Blends the chosen scope of the base face toward the slot faces. Controls outside the scope are untouched. */
export function blendFaces(base: Identity, slots: (MixerSlot | null)[], weights: number[], scope: MixScope): Identity {
  const out = clone(base);
  const ids = scopeControlIds(scope);
  for (const cid of ids) {
    const b = base.values[cid] ?? 0;
    let v = b;
    slots.forEach((s, i) => {
      if (!s || !weights[i]) return;
      v += ((s.values[cid] ?? 0) - b) * weights[i];
    });
    if (Math.abs(v) < 0.5) delete out.values[cid];
    else out.values[cid] = Math.round(v * 10) / 10;
  }
  const lookSlots = MIX_SCOPES.find((m) => m.id === scope)!.looks;
  let best = -1;
  let bestW = 0.5;
  weights.forEach((w, i) => {
    if (slots[i] && w > bestW) {
      best = i;
      bestW = w;
    }
  });
  if (best >= 0) for (const l of lookSlots) out.looks[l] = slots[best]!.looks[l] ?? out.looks[l];
  return out;
}
