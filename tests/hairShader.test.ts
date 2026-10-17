import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { deserializeCharacter, newCharacter, serializeCharacter } from '../src/model/character';
import { DEFAULT_HAIR_SHADER } from '../src/model/hairShader';
import { HAIR_GLSL, applyHairShader, hairUniforms } from '../src/viewport/hairShader';

const hlsl = readFileSync(new URL('../shaders/hair/AnimeHair.hlsl', import.meta.url), 'utf8');

describe('anime hair shader', () => {
  it('every GLSL uniform has a uniform object and an HLSL parameter of the same name', () => {
    const names = [...HAIR_GLSL.matchAll(/^uniform \w+ (u\w+);/gm)].map((m) => m[1]);
    expect(names.length).toBeGreaterThan(10);
    for (const n of names) {
      expect(hairUniforms).toHaveProperty(n);
      expect(hlsl).toMatch(new RegExp(`\\b${n.slice(1)}\\b`));
    }
  });

  it('the GLSL and HLSL functions keep the same steps', () => {
    for (const step of ['hairTangent', 'animeHair', 'hairHash']) {
      expect(HAIR_GLSL).toContain(step);
      expect(hlsl.toLowerCase()).toContain(step.toLowerCase());
    }
  });

  it('applies a character setting to the shared uniforms and falls back to defaults', () => {
    applyHairShader({ ringPos: 0.5, shade: '#ff0000' });
    expect(hairUniforms.uRingPos.value).toBe(0.5);
    expect(hairUniforms.uHairShade.value.r).toBeCloseTo(1);
    expect(hairUniforms.uHairHard.value).toBe(DEFAULT_HAIR_SHADER.hardness);
    applyHairShader(undefined);
    expect(hairUniforms.uRingPos.value).toBe(DEFAULT_HAIR_SHADER.ringPos);
  });

  it('new characters carry the defaults and old saves without hairShader get them on load', () => {
    const id = newCharacter('adult', 'stories');
    expect(id.hairShader).toEqual(DEFAULT_HAIR_SHADER);
    const old = JSON.parse(serializeCharacter(id));
    delete old.identity.hairShader;
    const loaded = deserializeCharacter(JSON.stringify(old));
    expect(loaded.hairShader).toEqual(DEFAULT_HAIR_SHADER);
  });
});
