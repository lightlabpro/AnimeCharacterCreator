import { describe, expect, it } from 'vitest';
import { viewKeyWeights } from '../src/viewport/gltfPacks';

// Mirrors blender/newhead/view_keys.py view_weights (Y34 = 35): the head pack's VW- keys must match Blender's renders.
describe('viewKeyWeights', () => {
  it('is all zero from the front', () => {
    expect(Object.values(viewKeyWeights(0)).every((v) => v === 0)).toBe(true);
  });
  it('peaks the 3/4 key at 35 degrees on the camera side', () => {
    const w = viewKeyWeights(35);
    expect(w['VW-Yaw_L']).toBeCloseTo(1);
    expect(w['VW-Side_L']).toBeCloseTo(0);
    expect(viewKeyWeights(-35)['VW-Yaw_R']).toBeCloseTo(1);
    expect(viewKeyWeights(-35)['VW-Yaw_L']).toBe(0);
  });
  it('hands over to the side key at 90 degrees', () => {
    const w = viewKeyWeights(90);
    expect(w['VW-Yaw_L']).toBeCloseTo(0);
    expect(w['VW-Side_L']).toBeCloseTo(1);
    const mid = viewKeyWeights(62.5);
    expect(mid['VW-Yaw_L']).toBeCloseTo(0.5);
    expect(mid['VW-Side_L']).toBeCloseTo(0.5);
  });
  it('fades out behind the head', () => {
    expect(viewKeyWeights(150)['VW-Side_L']).toBeCloseTo(0);
    expect(viewKeyWeights(180)['VW-Yaw_L']).toBe(0);
  });
});
