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

export interface StyleSettings {
  id: StylePreset;
  label: string;
  hint: string;
  bands: number;
  softness: number;
  rim: number;
  saturation: number;
  brightness: number;
  shadowTint: [number, number, number];
  specBoost: number;
  outline: number;
  outlineDark: number;
  background: [string, string];
}

export const STYLE_PRESETS: Record<StylePreset, StyleSettings> = {
  stories: {
    id: 'stories', label: 'Stories', hint: 'Default. Soft shadow bands, painted faces, a thin rim.',
    bands: 3, softness: 0.22, rim: 0.4, saturation: 1.0, brightness: 1.0, shadowTint: [0.72, 0.66, 0.82], specBoost: 1, outline: 1.1, outlineDark: 0.38,
    background: ['#58708c', '#1d2330'],
  },
  breath: {
    id: 'breath', label: 'Breath', hint: 'Brighter painted color and cleaner illustration edges.',
    bands: 2, softness: 0.12, rim: 0.28, saturation: 1.18, brightness: 1.08, shadowTint: [0.8, 0.7, 0.8], specBoost: 0.8, outline: 1.3, outlineDark: 0.3,
    background: ['#8aa4b8', '#2a2c3a'],
  },
  legends: {
    id: 'legends', label: 'Legends', hint: 'Cleaner cel bands and chunkier painted metal.',
    bands: 2, softness: 0.04, rim: 0.22, saturation: 1.08, brightness: 1.04, shadowTint: [0.66, 0.7, 0.84], specBoost: 1.6, outline: 1.6, outlineDark: 0.25,
    background: ['#9ab8d0', '#2a3444'],
  },
};
