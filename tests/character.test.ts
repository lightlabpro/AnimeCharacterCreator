import { describe, expect, it } from 'vitest';
import {
  applyAge, applyArchetype, applyPresentation, deserializeCharacter, makeChildCounterpart, newCharacter, randomizeIdentity, serializeCharacter, switchBodyKind,
} from '../src/model/character';
import { CONTROL_BY_ID, controlRange } from '../src/model/controls';
import { blendFaces, captureSlot, wheelWeights, WHEEL_SLOTS } from '../src/model/mixer';
import { neutralPerformance, resolvePerformance } from '../src/model/performance';
import { AGE_PRESETS_ADULT, PRESENTATION_PRESETS } from '../src/model/presets';

describe('new character', () => {
  it('opens dressed in the Stories style', () => {
    const adult = newCharacter('adult');
    expect(adult.style).toBe('stories');
    expect(adult.equipped.some((e) => e.slot === 'outfit')).toBe(true);
    const child = newCharacter('child');
    expect(child.equipped.map((e) => e.slot)).toEqual(expect.arrayContaining(['outfit', 'footwear']));
  });
});

describe('child counterpart', () => {
  it('drops adult-only keys and facial hair', () => {
    const adult = newCharacter('adult');
    adult.values = { 'muscle.chest': 80, 'body.chest': 50, 'chin.cleft': 60, 'age.years': 40, 'eye.size': 30 };
    adult.facialHair.beard = { id: 'full', length: 20, bulk: 20, color: '#222222' };
    const child = makeChildCounterpart(adult);
    expect(child.bodyKind).toBe('child');
    for (const k of ['muscle.chest', 'body.chest', 'chin.cleft', 'age.years']) expect(child.values[k]).toBeUndefined();
    for (const [k, v] of Object.entries(child.values)) {
      const ctl = CONTROL_BY_ID[k];
      expect(ctl.bodies).toContain('child');
      const [lo, hi] = controlRange(ctl, 'child');
      expect(v).toBeGreaterThanOrEqual(lo);
      expect(v).toBeLessThanOrEqual(hi);
    }
    expect(child.facialHair.beard.id).toBe('none');
    expect(child.equipped.some((e) => e.slot === 'outfit')).toBe(true);
  });

  it('keeps the child clothed when switching body kind', () => {
    const adult = newCharacter('adult');
    adult.equipped = [];
    const child = switchBodyKind(adult, 'child');
    expect(child.equipped.map((e) => e.slot)).toEqual(expect.arrayContaining(['outfit', 'footwear']));
  });
});

describe('archetype', () => {
  it('keeps age and presentation values', () => {
    let id = newCharacter('adult');
    id = applyPresentation(id, 'masculine');
    id = applyAge(id, 'old');
    const before = { ...id.values };
    const tiger = applyArchetype(id, 'tiger');
    expect(tiger.archetype).toBe('tiger');
    for (const k of [...Object.keys(PRESENTATION_PRESETS.masculine), ...Object.keys(AGE_PRESETS_ADULT.old)]) {
      if (before[k] !== undefined) expect(tiger.values[k]).toBe(before[k]);
    }
    expect(tiger.looks.muzzle).not.toBe('none');
  });
});

describe('serialization', () => {
  it('round-trips identity and never includes performance', () => {
    const id = newCharacter('adult');
    id.values['eye.size'] = 42;
    const text = serializeCharacter(id);
    const data = JSON.parse(text);
    for (const k of ['perf', 'manual', 'gaze', 'clip', 'bodyPose']) {
      expect(text).not.toContain(`"${k}"`);
      expect(data.identity[k]).toBeUndefined();
    }
    const back = deserializeCharacter(text);
    expect(back.values['eye.size']).toBe(42);
    expect(back.bodyKind).toBe('adult');
  });

  it('rejects files that are not characters', () => {
    expect(() => deserializeCharacter('{"hello":1}')).toThrow();
  });
});

describe('randomize', () => {
  it('stays inside every control range', () => {
    let seed = 7;
    const rand = () => {
      seed = (seed * 16807) % 2147483647;
      return seed / 2147483647;
    };
    for (const kind of ['adult', 'child', 'robot', 'beast'] as const) {
      const id = randomizeIdentity(newCharacter(kind), undefined, 1, rand);
      for (const [k, v] of Object.entries(id.values)) {
        const ctl = CONTROL_BY_ID[k];
        if (!ctl) continue;
        expect(ctl.bodies).toContain(kind);
        const [lo, hi] = controlRange(ctl, kind);
        expect(v).toBeGreaterThanOrEqual(lo);
        expect(v).toBeLessThanOrEqual(hi);
      }
    }
  });
});

describe('mixer', () => {
  it('weights are zero at the center and full toward a filled slot', () => {
    const filled = Array(WHEEL_SLOTS).fill(false);
    filled[0] = true;
    expect(wheelWeights([0, 0], filled).every((w) => w === 0)).toBe(true);
    const w = wheelWeights([0, -1], filled);
    expect(w[0]).toBeCloseTo(1);
  });

  it('blends only the chosen scope', () => {
    const base = newCharacter('adult');
    base.values = { 'eye.size': 0, 'body.height': 30 };
    const other = newCharacter('adult');
    other.values = { 'eye.size': 100, 'body.height': -50 };
    const slots = Array(WHEEL_SLOTS).fill(null);
    slots[0] = captureSlot(other, 'other');
    const weights = Array(WHEEL_SLOTS).fill(0);
    weights[0] = 0.5;
    const out = blendFaces(base, slots, weights, 'eyes');
    expect(out.values['eye.size']).toBe(50);
    expect(out.values['body.height']).toBe(30);
  });
});

describe('performance', () => {
  it('is neutral after reset and clamps weights', () => {
    const perf = neutralPerformance();
    const profile = newCharacter('adult').faceProfile;
    expect(resolvePerformance(perf, profile, 0, 0)).toEqual({});
    const w = resolvePerformance({ ...perf, pose: 'Laugh', manual: { 'PF-JawOpen': 1 } }, profile, 0, 0);
    expect(w['PF-JawOpen']).toBe(1);
  });
});
