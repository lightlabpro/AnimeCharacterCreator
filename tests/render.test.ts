import { describe, expect, it } from 'vitest';
import { STYLE_PRESETS, isStylePreset, resolveStyle } from '../src/model/presets';
import { ELEMENT_PALETTES, deepTone, elementVariant, liftTone, recolor, recolorHex } from '../src/model/palette';
import { deserializeCharacter, newCharacter, serializeCharacter } from '../src/model/character';
import { kindFor } from '../src/viewport/gltfPacks';

describe('style presets', () => {
  it('has the four looks, with Stories as the default', () => {
    expect(Object.keys(STYLE_PRESETS).sort()).toEqual(['breath', 'comic', 'legends', 'stories']);
    expect(newCharacter('adult').style).toBe('stories');
  });

  it('recognizes only real preset names', () => {
    expect(isStylePreset('comic')).toBe(true);
    expect(isStylePreset('toString')).toBe(false);
    expect(isStylePreset('')).toBe(false);
    expect(isStylePreset(3)).toBe(false);
  });

  it('keeps preset values when there are no overrides', () => {
    const s = resolveStyle('comic');
    expect(s.hatch).toBe(STYLE_PRESETS.comic.hatch);
    expect(s.light2.color).toBe(STYLE_PRESETS.comic.light2.color);
    expect(s.gobo).toBe(0);
    expect(s.dof).toBe(0);
  });

  it('applies overrides, including zero, without touching the preset', () => {
    const s = resolveStyle('stories', { outline: 0, rimLit: 0.9, light2Color: '#ff0000', hatchMode: 'screen', gobo: 0.5 });
    expect(s.outline).toBe(0);
    expect(s.screenRim.lit).toBe(0.9);
    expect(s.screenRim.shadow).toBe(STYLE_PRESETS.stories.screenRim.shadow);
    expect(s.light2.color).toBe('#ff0000');
    expect(s.light2.dir).toEqual(STYLE_PRESETS.stories.light2.dir);
    expect(s.hatchMode).toBe('screen');
    expect(s.gobo).toBe(0.5);
    expect(STYLE_PRESETS.stories.outline).not.toBe(0);
  });

  it('opens an unknown style as Stories', () => {
    const raw = JSON.parse(serializeCharacter(newCharacter('adult', 'comic')));
    expect(deserializeCharacter(JSON.stringify(raw)).style).toBe('comic');
    raw.identity.style = 'watercolor';
    expect(deserializeCharacter(JSON.stringify(raw)).style).toBe('stories');
  });
});

describe('gradient-map recolor', () => {
  const c: [number, number, number] = [0.8, 0.3, 0.2];

  it('maps grey 0.5 to the chosen color and the ends to deep and lifted tones', () => {
    expect(recolor(c, 0.5)).toEqual(c);
    recolor(c, 0).forEach((v, i) => expect(v).toBeCloseTo(deepTone(c)[i]));
    recolor(c, 1).forEach((v, i) => expect(v).toBeCloseTo(liftTone(c)[i]));
  });

  it('gets lighter as the grey value rises', () => {
    const lum = (g: number) => recolor(c, g).reduce((a, b) => a + b, 0);
    expect(lum(0.2)).toBeLessThan(lum(0.5));
    expect(lum(0.5)).toBeLessThan(lum(0.8));
  });

  it('clamps out-of-range greys and returns hex', () => {
    expect(recolorHex('#cc4433', -1)).toBe(recolorHex('#cc4433', 0));
    expect(recolorHex('#cc4433', 0.5).toLowerCase()).toBe('#cc4433');
  });
});

describe('element variants', () => {
  it('leaves colors alone for no element', () => {
    expect(elementVariant('#808080', 'none')).toBe('#808080');
  });

  it('pulls a color toward the element hue', () => {
    for (const el of Object.keys(ELEMENT_PALETTES) as (keyof typeof ELEMENT_PALETTES)[]) {
      expect(elementVariant('#40a040', el)).toMatch(/^#[0-9a-f]{6}$/i);
    }
    expect(elementVariant('#40a040', 'fire')).not.toBe('#40a040');
  });
});

describe('material names in imported packs', () => {
  it('reads whole words, not fragments', () => {
    expect(kindFor('MAT_lattice_cloth')).toBe('cloth');
    expect(kindFor('ice_shard')).toBe('crystal');
    expect(kindFor('Hair_Front')).toBe('hair');
    expect(kindFor('goggle_lens')).toBe('lens');
    expect(kindFor('wing_membrane')).toBe('membrane');
    expect(kindFor('armor_gold')).toBe('metal');
  });
});
