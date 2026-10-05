import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { headDims, headProfile } from '../src/model/headShape';

const target = JSON.parse(readFileSync(new URL('../knowledge/head-targets.json', import.meta.url), 'utf8'));
const none = () => 0;
const h = 0.234; // everything is divided by head height, so the scale does not matter

describe('default adult head against the reference profile (knowledge/head-targets.json)', () => {
  const p = headProfile(headDims(none, h, false, 0), h, false, none);
  const tol = 0.045;

  it('cranium is as narrow as the reference, not egg-wide', () => {
    expect(Math.abs(p.cranium - target.derived.cranium_width_H)).toBeLessThan(tol);
  });
  it('skull is as deep as the reference', () => {
    expect(Math.abs(p.skullDepth03 - target.derived.skull_depth_H)).toBeLessThan(tol);
  });
  it('width to depth ratio stays near the reference, which fixes flat, wide heads', () => {
    expect(Math.abs(p.widthToDepth - target.derived.width_to_depth_ratio)).toBeLessThan(0.07);
  });
  it('jaw and chin taper like the reference', () => {
    for (const f of ['0.8', '0.85', '0.9', '0.95']) expect(Math.abs(p.width[f] - target.front.width[f])).toBeLessThan(tol);
  });
  it('nose stands out ahead of forehead and chin by the reference amount', () => {
    expect(Math.abs(p.behindNose['0.3'] - target.side.behind_nose['0.3'])).toBeLessThan(tol);
    expect(Math.abs(p.behindNose['0.9'] - target.side.behind_nose['0.9'])).toBeLessThan(tol);
  });

});
