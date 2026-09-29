import type { StylePreset } from './types';

export interface ArchetypePreset {
  id: string;
  label: string;
  looks: Record<string, string>;
  values: Record<string, number>;
  colors: Record<string, string>;
}

const HUMAN_LOOKS: Record<string, string> = {
  muzzle: 'none', ears: 'human', pupil: 'round', fangs: 'none', whiskers: 'none', beak: 'none', mane: 'none', horns: 'none',
  frill: 'none', hands: 'human', feet: 'human', legs: 'plantigrade', tail: 'none', wings: 'none', surface: 'skin', pattern: 'plain',
};

const L = (over: Record<string, string>) => ({ ...HUMAN_LOOKS, ...over });

export const ARCHETYPES: ArchetypePreset[] = [
  { id: 'human', label: 'Human', looks: L({}), values: {}, colors: {} },
  {
    id: 'tiger', label: 'Tiger',
    looks: L({ muzzle: 'feline', ears: 'round', fangs: 'small', whiskers: 'short', hands: 'paw', feet: 'paw', legs: 'digitigrade', tail: 'feline', surface: 'shortFur', pattern: 'stripes' }),
    values: { 'muzzle.length': -30, 'muzzle.width': 20, 'tail.length': 20, 'claw.length': 40, 'whisker.density': 60 },
    colors: { surfacePrimary: '#e58a2e', surfaceSecondary: '#2a1e1a', belly: '#f4ead8', iris: '#e0b030', mane: '#f4ead8' },
  },
  {
    id: 'lion', label: 'Lion',
    looks: L({ muzzle: 'feline', ears: 'round', fangs: 'small', whiskers: 'short', mane: 'mane', hands: 'paw', feet: 'paw', legs: 'digitigrade', tail: 'feline', surface: 'shortFur' }),
    values: { 'muzzle.length': -20, 'muzzle.width': 30, 'mane.volume': 60, 'mane.length': 30, 'tail.tip': 80, 'claw.length': 30, 'whisker.density': 40 },
    colors: { surfacePrimary: '#d8a456', surfaceSecondary: '#8a5a2a', belly: '#f0dcb4', mane: '#7a3e1e', iris: '#d89a30' },
  },
  {
    id: 'fish', label: 'Fish',
    looks: L({ muzzle: 'fish', ears: 'fin', frill: 'gills', hands: 'webbed', feet: 'webbed', tail: 'fish', wings: 'fin', surface: 'scales', pattern: 'spots', pupil: 'round' }),
    values: { 'muzzle.length': -40, 'muzzle.width': 40, 'eye.forward': -40, 'wing.span': -50, 'digit.emphasis': 40 },
    colors: { surfacePrimary: '#3a8ab8', surfaceSecondary: '#f0d060', belly: '#e8f2f4', iris: '#f0c040', membrane: '#7ac8e8' },
  },
  {
    id: 'dog', label: 'Dog',
    looks: L({ muzzle: 'canine', ears: 'pointed', fangs: 'small', hands: 'paw', feet: 'paw', legs: 'digitigrade', tail: 'canine', surface: 'shortFur', pattern: 'spots' }),
    values: { 'muzzle.length': 20, 'earEl.size': 20, 'tail.thickness': 30, 'claw.length': 20 },
    colors: { surfacePrimary: '#b07844', surfaceSecondary: '#5a3a22', belly: '#f2e4cc', iris: '#8a5a2a' },
  },
  {
    id: 'dragon', label: 'Dragon',
    looks: L({ muzzle: 'reptile', ears: 'pointed', fangs: 'small', horns: 'curved', hands: 'talon', feet: 'talon', legs: 'digitigrade', tail: 'lizard', wings: 'membrane', surface: 'scales', pattern: 'plates', pupil: 'slit' }),
    values: { 'muzzle.length': 20, 'horn.length': 30, 'horn.curve': 50, 'tail.length': 40, 'tail.thickness': 40, 'wing.fold': 60, 'claw.length': 50 },
    colors: { surfacePrimary: '#c8442e', surfaceSecondary: '#6a2a8a', belly: '#f2c890', horn: '#f0e0c0', iris: '#40c0b0', membrane: '#e0784a' },
  },
  {
    id: 'bird', label: 'Bird',
    looks: L({ muzzle: 'bird', beak: 'slight', ears: 'feathered', mane: 'feathers', hands: 'talon', feet: 'talon', legs: 'digitigrade', tail: 'bird', wings: 'feathered', surface: 'feathers' }),
    values: { 'muzzle.length': -10, 'mane.length': 40, 'wing.fold': 70 },
    colors: { surfacePrimary: '#3a6ad0', surfaceSecondary: '#f0f0f0', belly: '#f4e8c8', beak: '#f0b030', mane: '#e84a3a', iris: '#f0d040' },
  },
  {
    id: 'frog', label: 'Frog',
    looks: L({ muzzle: 'frog', ears: 'none', hands: 'webbed', feet: 'webbed', surface: 'amphibian', pattern: 'spots', pupil: 'wide' }),
    values: { 'muzzle.width': 60, 'muzzle.length': -40, 'eye.forward': -30, 'eye.size': 30, 'eye.height': 40, 'digit.emphasis': 60 },
    colors: { surfacePrimary: '#5ab04a', surfaceSecondary: '#2a5a2a', belly: '#f0f0c0', iris: '#f0c030' },
  },
  {
    id: 'serpent', label: 'Serpent',
    looks: L({ muzzle: 'reptile', ears: 'none', fangs: 'long', tail: 'serpent', surface: 'scales', pattern: 'plates', pupil: 'slit' }),
    values: { 'muzzle.length': -20, 'muzzle.width': -20, 'body.bulk': -40, 'tail.length': 100, 'tail.thickness': 40, 'fang.length': 60, 'neck.length': 40 },
    colors: { surfacePrimary: '#3a8a4a', surfaceSecondary: '#e0c040', belly: '#e8e0b0', iris: '#f0e040' },
  },
  {
    id: 'rabbit', label: 'Rabbit',
    looks: L({ muzzle: 'lagomorph', ears: 'long', whiskers: 'short', feet: 'paw', legs: 'digitigrade', tail: 'puff', surface: 'shortFur' }),
    values: { 'muzzle.length': -50, 'earEl.size': 50, 'earEl.lift': 30, 'tail.tip': 30, 'foot.length': 40, 'whisker.density': 30 },
    colors: { surfacePrimary: '#f2ece4', surfaceSecondary: '#b08a70', belly: '#ffffff', iris: '#c04a5a' },
  },
  {
    id: 'dinosaur', label: 'Dinosaur',
    looks: L({ muzzle: 'reptile', ears: 'none', fangs: 'small', mane: 'crest', hands: 'talon', feet: 'talon', legs: 'digitigrade', tail: 'lizard', surface: 'scales', pattern: 'spots', pupil: 'slit' }),
    values: { 'muzzle.length': 40, 'muzzle.height': 30, 'mane.length': 30, 'tail.length': 60, 'tail.thickness': 100, 'upperArm.length': -70, 'forearm.length': -60, 'body.bulk': 30 },
    colors: { surfacePrimary: '#6a9a3a', surfaceSecondary: '#3a5a2a', belly: '#e8d8a0', mane: '#d85a2a', iris: '#f0a030' },
  },
  {
    id: 'rhino', label: 'Rhino',
    looks: L({ muzzle: 'heavy', ears: 'round', horns: 'twinNose', hands: 'human', feet: 'paw', surface: 'hide', pattern: 'plates' }),
    values: { 'muzzle.length': 30, 'muzzle.width': 40, 'muzzle.height': 40, 'horn.length': 40, 'horn.thickness': 60, 'earEl.size': -40, 'body.bulk': 70, 'neck.thickness': 60 },
    colors: { surfacePrimary: '#8a8a90', surfaceSecondary: '#6a6a70', belly: '#b0aaa4', horn: '#e0d8c8', iris: '#5a4a3a' },
  },
  {
    id: 'lizard', label: 'Lizard',
    looks: L({ muzzle: 'reptile', ears: 'none', frill: 'frill', hands: 'talon', feet: 'talon', tail: 'lizard', surface: 'scales', pattern: 'stripes', pupil: 'slit' }),
    values: { 'muzzle.length': 10, 'muzzle.width': -10, 'tail.length': 80, 'tail.thickness': 0, 'frill.size': 20, 'frill.flare': 50, 'claw.length': 30 },
    colors: { surfacePrimary: '#40a080', surfaceSecondary: '#f0d050', belly: '#f0e8c0', iris: '#f0a020', membrane: '#f06a4a' },
  },
];

export const ARCHETYPE_BY_ID: Record<string, ArchetypePreset> = Object.fromEntries(ARCHETYPES.map((a) => [a.id, a]));

export const PRESENTATION_KEYS = ['body.shoulders', 'body.chest', 'body.waist', 'body.hips', 'face.softness', 'body.height'];

export const PRESENTATION_PRESETS: Record<'feminine' | 'neutral' | 'masculine', Record<string, number>> = {
  feminine: { 'body.shoulders': -40, 'body.chest': 40, 'body.waist': 45, 'body.hips': 45, 'face.softness': 50, 'body.height': -25 },
  neutral: { 'body.shoulders': 0, 'body.chest': 0, 'body.waist': 0, 'body.hips': 0, 'face.softness': 0, 'body.height': 0 },
  masculine: { 'body.shoulders': 45, 'body.chest': -10, 'body.waist': -20, 'body.hips': -25, 'face.softness': -35, 'body.height': 20 },
};

export const AGE_KEYS_ADULT = ['age.years', 'age.creases', 'age.jawSoft', 'age.stoop'];
export const AGE_KEYS_BEAST = ['age.years', 'age.wear', 'age.posture'];

export const AGE_PRESETS_ADULT: Record<'youngAdult' | 'adult' | 'old', Record<string, number>> = {
  youngAdult: { 'age.years': -70, 'age.creases': 0, 'age.jawSoft': 0, 'age.stoop': 0 },
  adult: { 'age.years': 0, 'age.creases': 0, 'age.jawSoft': 0, 'age.stoop': 0 },
  old: { 'age.years': 90, 'age.creases': 70, 'age.jawSoft': 50, 'age.stoop': 40 },
};

export const AGE_PRESETS_BEAST: Record<'youngAdult' | 'adult' | 'old', Record<string, number>> = {
  youngAdult: { 'age.years': -70, 'age.wear': 0, 'age.posture': 0 },
  adult: { 'age.years': 0, 'age.wear': 0, 'age.posture': 0 },
  old: { 'age.years': 90, 'age.wear': 70, 'age.posture': 50 },
};

export const OLD_HAIR_GRAY = '#cfcfd4';

export const BODY_PRESETS: { id: string; label: string; values: Record<string, number> }[] = [
  { id: 'average', label: 'Average', values: { 'body.bulk': 0, 'body.soft': 0, 'muscle.chest': 0, 'muscle.abs': 0, 'muscle.arms': 0, 'muscle.legs': 0, 'body.belly': 0 } },
  { id: 'lean', label: 'Lean', values: { 'body.bulk': -60, 'body.soft': 0, 'body.belly': -30, 'upperArm.bulk': -20, 'thigh.bulk': -20 } },
  { id: 'athletic', label: 'Athletic', values: { 'body.bulk': 20, 'muscle.chest': 60, 'muscle.abs': 60, 'muscle.arms': 60, 'muscle.legs': 50, 'body.belly': -30 } },
  { id: 'heavy', label: 'Heavy', values: { 'body.bulk': 80, 'body.soft': 40, 'body.belly': 60, 'neck.thickness': 40 } },
  { id: 'soft', label: 'Soft', values: { 'body.bulk': 20, 'body.soft': 70, 'body.belly': 30 } },
  { id: 'longLimbed', label: 'Long-limbed', values: { 'upperArm.length': 60, 'forearm.length': 60, 'thigh.length': 60, 'shin.length': 60, 'torso.length': -20 } },
  { id: 'compact', label: 'Compact', values: { 'upperArm.length': -40, 'forearm.length': -40, 'thigh.length': -40, 'shin.length': -40, 'body.bulk': 30 } },
];

export const HEAD_PRESETS: { id: string; label: string; values: Record<string, number> }[] = [
  { id: 'softRound', label: 'Soft round', values: { 'face.round': 70, 'face.long': 0, 'face.square': 0, 'jaw.width': 10, 'cheek.full': 40, 'eye.size': 20, 'eye.round': 40 } },
  { id: 'sharp', label: 'Sharp', values: { 'face.diamond': 50, 'cheek.bone': 60, 'jaw.width': -20, 'chin.width': -40, 'eye.almond': 70, 'eye.tilt': 30 } },
  { id: 'long', label: 'Long', values: { 'face.long': 70, 'chin.length': 40, 'nose.length': 30, 'eye.narrow': 30 } },
  { id: 'square', label: 'Square', values: { 'face.square': 80, 'jaw.width': 50, 'chin.width': 40, 'brow.ridge': 40, 'brow.thickness': 40 } },
  { id: 'heart', label: 'Heart', values: { 'face.heart': 80, 'chin.width': -50, 'skull.width': 20, 'eye.size': 20 } },
  { id: 'gentle', label: 'Gentle', values: { 'eye.droop': -40, 'brow.tilt': -30, 'mouth.corner': 20, 'face.round': 30 } },
  { id: 'bold', label: 'Bold', values: { 'brow.ridge': 60, 'brow.thickness': 60, 'jaw.width': 40, 'nose.bridgeHeight': 50, 'eye.narrow': 40 } },
];

export const SKIN_TONES: { id: string; label: string; color: string }[] = [
  { id: 'porcelain', label: 'Porcelain', color: '#fbe3d6' },
  { id: 'light', label: 'Light', color: '#f6d2bc' },
  { id: 'warm', label: 'Warm', color: '#eab896' },
  { id: 'olive', label: 'Olive', color: '#d6a67c' },
  { id: 'tan', label: 'Tan', color: '#c08a60' },
  { id: 'brown', label: 'Brown', color: '#99633f' },
  { id: 'deep', label: 'Deep', color: '#6e4430' },
  { id: 'ebony', label: 'Ebony', color: '#4a2e22' },
];

export const HAIR_COLORS: { id: string; label: string; root: string; tip: string }[] = [
  { id: 'chestnut', label: 'Chestnut', root: '#5a3420', tip: '#8a5634' },
  { id: 'black', label: 'Blue black', root: '#1c1c28', tip: '#3a3e58' },
  { id: 'blonde', label: 'Blonde', root: '#c89a4a', tip: '#f2d88a' },
  { id: 'pale', label: 'Pale silver', root: '#bcc0cc', tip: '#f4f4f8' },
  { id: 'rose', label: 'Rose', root: '#c85a78', tip: '#f4a8bc' },
  { id: 'teal', label: 'Teal', root: '#1e6a70', tip: '#58c0b8' },
  { id: 'red', label: 'Red', root: '#8a2a22', tip: '#d8583a' },
  { id: 'gray', label: 'Gray', root: '#8a8a90', tip: '#cfcfd4' },
];

type RGB = [number, number, number];

/**
 * Everything one picture style sets. Shading values reach every toon material through shared uniforms,
 * line and post values reach the post pipeline. See docs/shading-style-guide.md for what each style is after.
 */
export interface StyleSettings {
  id: StylePreset;
  label: string;
  hint: string;
  /** Light steps above the shadow. 1 is Capcom's hard two-tone. */
  bands: number;
  /** Width of the light/shadow boundary before the per-material multiplier. */
  softness: number;
  /** MToon Toony: 1 is razor sharp, 0 doubles the softness. */
  toony: number;
  /** MToon Shade Shift: moves the boundary toward the light (negative) or away (positive). */
  shadeShift: number;
  /** Painted boundary: texture brightness and brush noise push the threshold around. */
  painted: number;
  /** Shading rim strength. Zero when the screen rim replaces it. */
  rim: number;
  saturation: number;
  brightness: number;
  /** First shadow color as a multiplier of the lit color. Hue-shifted, never gray. */
  shadowTint: RGB;
  /** Second, darker shadow inside the first, from forced-shadow masks and deep occlusion. */
  shadow2Tint: RGB;
  /** Color change applied to shadowed pixels only. */
  shadowGrade: RGB;
  specBoost: number;
  edgeHighlight: number;
  lightColor: string;
  /** Ambient from one fixed direction, on shadows only. */
  ambient: number;
  ambientColor: string;
  /** Fill light, on shadows only. */
  fill: number;
  fillColor: string;
  /** Second colored light, used by gradient-mapped looks such as Comic. */
  light2: { dir: RGB; color: string; strength: number };
  /** Blend of face normals toward the head proxy, 0 to 1. */
  faceSmooth: number;
  /** Depth and normal edge width in pixels. */
  outline: number;
  /** Line color as a multiple of the surface color. */
  outlineDark: number;
  /** 1 colors lines by the surface under them, 0 uses near black. */
  lineColorMix: number;
  /** Inverted-hull outline width in pixels, 0 turns it off. */
  hull: number;
  /** Normal edge sensitivity for creases, 0 turns them off. */
  creases: number;
  /** Sketchy line wobble in pixels. */
  lineJitter: number;
  /** Ink layer offset in pixels, for print misregistration. */
  inkOffset: number;
  /** Screen-space rim of constant width: lit side, shadow side, width in pixels. */
  screenRim: { lit: number; shadow: number; width: number };
  /** Shadow hatching strength, density, and whether strokes stick to the surface or the screen. */
  hatch: number;
  hatchScale: number;
  hatchMode: 'surface' | 'screen';
  /** Halftone dots in the highlights and midtones. */
  halftone: number;
  grain: number;
  /** Four-sector Kuwahara radius in pixels, 0 turns it off. */
  kuwahara: number;
  /** Character-only bloom that keeps the brightest channel, so skin stays warm. */
  diffusion: number;
  /** Bloom on HDR emissive above 1. */
  bloom: number;
  /** Warm brightening at the screen edges and a darkening gradient from the top. */
  flare: number;
  para: number;
  fog: number;
  splitTone: { shadow: string; highlight: string; amount: number };
  vignette: number;
  sparkle: number;
  /** Glowing ring eyes, 0 to 1. */
  glowEyes: number;
  background: [string, string];
}

const STORIES: StyleSettings = {
  id: 'stories', label: 'Stories', hint: 'Default. Hard two-tone cel shading, colored lines, soft fur, and a film-like finish.',
  bands: 1, softness: 0.035, toony: 0.6, shadeShift: 0, painted: 0, rim: 0.12,
  saturation: 1.04, brightness: 1.0, shadowTint: [0.74, 0.66, 0.86], shadow2Tint: [0.56, 0.48, 0.7], shadowGrade: [0.96, 0.97, 1.04],
  specBoost: 1, edgeHighlight: 0.6, lightColor: '#fff6ea', ambient: 0.12, ambientColor: '#9ab4e0', fill: 0.1, fillColor: '#b8c4ff',
  light2: { dir: [-0.6, 0.2, -0.5], color: '#8fb4ff', strength: 0 }, faceSmooth: 0.75,
  outline: 1.0, outlineDark: 0.42, lineColorMix: 1, hull: 1.3, creases: 0.5, lineJitter: 0, inkOffset: 0,
  screenRim: { lit: 0.35, shadow: 0.12, width: 2.5 },
  hatch: 0, hatchScale: 1, hatchMode: 'surface', halftone: 0, grain: 0.015, kuwahara: 0,
  diffusion: 0.22, bloom: 0.25, flare: 0.14, para: 0.18, fog: 0.12,
  splitTone: { shadow: '#3a4a8a', highlight: '#ffd9a8', amount: 0.08 }, vignette: 0.2, sparkle: 0.6, glowEyes: 0,
  background: ['#58708c', '#1d2330'],
};

export const STYLE_PRESETS: Record<StylePreset, StyleSettings> = {
  stories: STORIES,
  breath: {
    ...STORIES,
    id: 'breath', label: 'Breath', hint: 'Muted earthy paint, planar steps, thin lines in the surface color, and watercolor grain.',
    bands: 2, softness: 0.06, toony: 0.5, painted: 0.55, rim: 0.08,
    saturation: 0.86, brightness: 1.03, shadowTint: [0.8, 0.7, 0.72], shadow2Tint: [0.62, 0.52, 0.6], shadowGrade: [0.94, 0.96, 1.06],
    specBoost: 0.6, edgeHighlight: 0.3, lightColor: '#ffeccc', ambientColor: '#8aa0b8', fillColor: '#a8b4d0',
    outline: 0.9, outlineDark: 0.55, hull: 0.8, creases: 0.3,
    screenRim: { lit: 0.2, shadow: 0, width: 2 },
    grain: 0.05, kuwahara: 2, diffusion: 0.16, bloom: 0.15, flare: 0.1, para: 0.12, fog: 0.22,
    splitTone: { shadow: '#40506a', highlight: '#ffe0b0', amount: 0.14 }, vignette: 0.28, sparkle: 0.3,
    background: ['#b8b09a', '#4a4438'],
  },
  legends: {
    ...STORIES,
    id: 'legends', label: 'Legends', hint: 'Toy-like chunky shapes, near-flat shading, thick dark lines, glossy metal, bright sky.',
    bands: 1, softness: 0.02, toony: 0.8, rim: 0.05,
    saturation: 1.14, brightness: 1.05, shadowTint: [0.7, 0.74, 0.88], shadow2Tint: [0.55, 0.58, 0.75], shadowGrade: [1, 1, 1],
    specBoost: 1.7, edgeHighlight: 0.8, lightColor: '#ffffff', ambient: 0.16, ambientColor: '#b0d0ff', fill: 0.05,
    faceSmooth: 0.9, outline: 1.4, outlineDark: 0.22, lineColorMix: 0.5, hull: 2.2, creases: 0.35,
    screenRim: { lit: 0.15, shadow: 0, width: 2 },
    grain: 0, diffusion: 0.1, bloom: 0.2, flare: 0.05, para: 0.05, fog: 0.05,
    splitTone: { shadow: '#2a3a7a', highlight: '#fff4d0', amount: 0.04 }, vignette: 0.12, sparkle: 0.3,
    background: ['#9ad0f0', '#3a6aa0'],
  },
  comic: {
    ...STORIES,
    id: 'comic', label: 'Comic', hint: 'Duotone light per lamp, ink hatching in the shadows, sketchy lines, halftone, and glowing ring eyes.',
    bands: 1, softness: 0.05, toony: 0.7, rim: 0,
    saturation: 1.1, brightness: 1.02, shadowTint: [0.5, 0.36, 0.5], shadow2Tint: [0.3, 0.2, 0.34], shadowGrade: [0.9, 0.9, 1.08],
    specBoost: 0.9, edgeHighlight: 0.5, lightColor: '#ffd2b0', ambient: 0.08, ambientColor: '#4a6ad0', fill: 0.22, fillColor: '#4a78ff',
    light2: { dir: [-0.7, 0.35, -0.4], color: '#50e0a0', strength: 0.55 }, faceSmooth: 0.6,
    outline: 1.5, outlineDark: 0.12, lineColorMix: 0.25, hull: 1.8, creases: 0.9, lineJitter: 1.2, inkOffset: 0.8,
    screenRim: { lit: 0.25, shadow: 0.3, width: 3 },
    hatch: 0.85, hatchScale: 1.2, hatchMode: 'surface', halftone: 0.45, grain: 0.035, kuwahara: 0,
    diffusion: 0.1, bloom: 0.8, flare: 0.08, para: 0.2, fog: 0,
    splitTone: { shadow: '#302040', highlight: '#ffe6c8', amount: 0.1 }, vignette: 0.35, sparkle: 0.2, glowEyes: 1,
    background: ['#3a3a40', '#141418'],
  },
};

/** Style values a person can override from the Render section. Stored per style. */
export interface RenderOverrides {
  shadeShift?: number;
  toony?: number;
  outline?: number;
  lineColorMix?: number;
  hull?: number;
  rimLit?: number;
  rimShadow?: number;
  hatch?: number;
  hatchMode?: 'surface' | 'screen';
  grain?: number;
  bloom?: number;
  diffusion?: number;
  light2Color?: string;
  light2Strength?: number;
  gobo?: number;
  dof?: number;
  particles?: number;
  glowEyes?: number;
}

/** Extras that are off in every preset and only come from the Render section. */
export interface RenderExtras {
  gobo: number;
  dof: number;
  particles: number;
}

/** The preset with the person's overrides applied. */
export function resolveStyle(style: StylePreset, o: RenderOverrides = {}): StyleSettings & RenderExtras {
  const base = STYLE_PRESETS[style] ?? STYLE_PRESETS.stories;
  const pick = <T,>(v: T | undefined, d: T) => (v === undefined ? d : v);
  return {
    ...base,
    shadeShift: pick(o.shadeShift, base.shadeShift),
    toony: pick(o.toony, base.toony),
    outline: pick(o.outline, base.outline),
    lineColorMix: pick(o.lineColorMix, base.lineColorMix),
    hull: pick(o.hull, base.hull),
    screenRim: { ...base.screenRim, lit: pick(o.rimLit, base.screenRim.lit), shadow: pick(o.rimShadow, base.screenRim.shadow) },
    hatch: pick(o.hatch, base.hatch),
    hatchMode: pick(o.hatchMode, base.hatchMode),
    grain: pick(o.grain, base.grain),
    bloom: pick(o.bloom, base.bloom),
    diffusion: pick(o.diffusion, base.diffusion),
    light2: { ...base.light2, color: pick(o.light2Color, base.light2.color), strength: pick(o.light2Strength, base.light2.strength) },
    glowEyes: pick(o.glowEyes, base.glowEyes),
    gobo: pick(o.gobo, 0),
    dof: pick(o.dof, 0),
    particles: pick(o.particles, 0),
  };
}

export function isStylePreset(v: unknown): v is StylePreset {
  return typeof v === 'string' && Object.prototype.hasOwnProperty.call(STYLE_PRESETS, v);
}
