import type { HairShader } from './types';

/** Default anime hair shader settings (Leo-like brown hair, MHS3). Parameter notes in src/viewport/hairShader.ts. */
export const DEFAULT_HAIR_SHADER: HairShader = {
  shade: '#5a3a5a',
  shadeMix: 0.35,
  area: 0,
  hardness: 0.85,
  rootDark: 0.25,
  ringPos: 0.32,
  ringWidth: 0.06,
  ringStrength: 0.7,
  ringColor: '#ffe3bd',
  ringFollow: 0.2,
  ringSpace: 0.85,
  ringJag: 0.6,
  ringTeeth: 4,
  strandLines: 0.35,
  strandCount: 3,
  rim: 0.25,
  rimPow: 4,
};
