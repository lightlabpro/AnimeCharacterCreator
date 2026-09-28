import type { FaceProfile, WrinkleRegion } from './types';

export interface PFKeyDef {
  key: string;
  label: string;
  group: 'Eyes' | 'Brows' | 'Jaw' | 'Visemes' | 'Emotions' | 'Tongue';
  region: 'eyes' | 'brows' | 'mouth';
}

const sides = (base: string, label: string, group: PFKeyDef['group'], region: PFKeyDef['region']): PFKeyDef[] => [
  { key: `${base}_L`, label: `${label} left`, group, region },
  { key: `${base}_R`, label: `${label} right`, group, region },
];

export const PF_KEYS: PFKeyDef[] = [
  ...sides('PF-Blink', 'Blink', 'Eyes', 'eyes'),
  ...sides('PF-EyeWide', 'Wide', 'Eyes', 'eyes'),
  ...sides('PF-Squint', 'Squint', 'Eyes', 'eyes'),
  ...sides('PF-LidUpperDown', 'Upper lid down', 'Eyes', 'eyes'),
  ...sides('PF-LidLowerUp', 'Lower lid up', 'Eyes', 'eyes'),
  ...sides('PF-Squeeze', 'Squeeze', 'Eyes', 'eyes'),
  ...sides('PF-BrowRaise', 'Brow raise', 'Brows', 'brows'),
  ...sides('PF-BrowInnerUp', 'Inner brow up', 'Brows', 'brows'),
  ...sides('PF-BrowOuterUp', 'Outer brow up', 'Brows', 'brows'),
  ...sides('PF-BrowLower', 'Brow lower', 'Brows', 'brows'),
  ...sides('PF-BrowFurrow', 'Brow furrow', 'Brows', 'brows'),
  ...sides('PF-BrowSad', 'Sad brow', 'Brows', 'brows'),
  { key: 'PF-JawOpen', label: 'Jaw open', group: 'Jaw', region: 'mouth' },
  { key: 'PF-VisMBP', label: 'Closed lips (M, B, P)', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisSmall', label: 'Small opening', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisMid', label: 'Mid opening', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisAA', label: 'A', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisEE', label: 'E', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisIH', label: 'I', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisOH', label: 'O', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisOO', label: 'U', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisFV', label: 'F and V', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisL', label: 'L', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisTH', label: 'Th', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisSZ', label: 'S and Z', group: 'Visemes', region: 'mouth' },
  { key: 'PF-VisWide', label: 'Shout', group: 'Visemes', region: 'mouth' },
  { key: 'PF-SmileClosed', label: 'Closed smile', group: 'Emotions', region: 'mouth' },
  { key: 'PF-SmileOpenJaw', label: 'Open smile', group: 'Emotions', region: 'mouth' },
  { key: 'PF-Smirk_L', label: 'Smirk left', group: 'Emotions', region: 'mouth' },
  { key: 'PF-Smirk_R', label: 'Smirk right', group: 'Emotions', region: 'mouth' },
  { key: 'PF-Frown', label: 'Frown', group: 'Emotions', region: 'mouth' },
  { key: 'PF-FrownOpen', label: 'Open frown', group: 'Emotions', region: 'mouth' },
  { key: 'PF-Pout', label: 'Pout', group: 'Emotions', region: 'mouth' },
  { key: 'PF-Press', label: 'Press lips', group: 'Emotions', region: 'mouth' },
  { key: 'PF-LipBite', label: 'Lip bite', group: 'Emotions', region: 'mouth' },
  { key: 'PF-Grimace', label: 'Grimace', group: 'Emotions', region: 'mouth' },
  { key: 'PF-Snarl', label: 'Snarl', group: 'Emotions', region: 'mouth' },
  { key: 'PF-Disgust', label: 'Disgust', group: 'Emotions', region: 'mouth' },
  { key: 'PF-Surprise', label: 'Surprise', group: 'Emotions', region: 'mouth' },
  { key: 'PF-Cry', label: 'Cry', group: 'Emotions', region: 'mouth' },
  { key: 'PF-MouthSide_L', label: 'Mouth shift left', group: 'Emotions', region: 'mouth' },
  { key: 'PF-MouthSide_R', label: 'Mouth shift right', group: 'Emotions', region: 'mouth' },
  { key: 'PF-TongueL', label: 'Tongue up (L)', group: 'Tongue', region: 'mouth' },
  { key: 'PF-TongueTh', label: 'Tongue forward (Th)', group: 'Tongue', region: 'mouth' },
  { key: 'PF-TongueRest', label: 'Tongue visible at rest', group: 'Tongue', region: 'mouth' },
];

export const VISEME_KEYS = PF_KEYS.filter((k) => k.group === 'Visemes').map((k) => k.key);

type W = Record<string, number>;
const both = (base: string, v: number): W => ({ [`${base}_L`]: v, [`${base}_R`]: v });

export const POSE_NAMES = [
  'Neutral', 'SoftSmile', 'Happy', 'Laugh', 'Sad', 'Cry', 'Angry', 'Shout', 'Surprised', 'Skeptical', 'Sleepy', 'Focused', 'Disgusted',
] as const;

export const POSE_LABELS: Record<string, string> = {
  Neutral: 'Neutral', SoftSmile: 'Soft smile', Happy: 'Happy', Laugh: 'Laugh', Sad: 'Sad', Cry: 'Cry', Angry: 'Angry',
  Shout: 'Shout', Surprised: 'Surprised', Skeptical: 'Skeptical', Sleepy: 'Sleepy', Focused: 'Focused', Disgusted: 'Disgusted',
};

export const DEFAULT_POSES: Record<string, W> = {
  Neutral: {},
  SoftSmile: { 'PF-SmileClosed': 0.55, ...both('PF-Squint', 0.15), ...both('PF-BrowRaise', 0.1) },
  Happy: { 'PF-SmileClosed': 0.8, 'PF-SmileOpenJaw': 0.4, 'PF-JawOpen': 0.2, 'PF-VisSmall': 0.3, ...both('PF-Squint', 0.35), ...both('PF-BrowRaise', 0.3) },
  Laugh: { 'PF-SmileOpenJaw': 0.9, 'PF-SmileClosed': 0.6, 'PF-JawOpen': 0.55, 'PF-VisAA': 0.4, ...both('PF-Squint', 0.55), ...both('PF-Squeeze', 0.25), ...both('PF-BrowRaise', 0.35) },
  Sad: { 'PF-Frown': 0.6, ...both('PF-BrowSad', 0.8), ...both('PF-BrowInnerUp', 0.6), ...both('PF-LidUpperDown', 0.25), 'PF-Press': 0.2 },
  Cry: { 'PF-Cry': 0.9, 'PF-FrownOpen': 0.5, 'PF-JawOpen': 0.3, ...both('PF-BrowSad', 1), ...both('PF-BrowInnerUp', 0.8), ...both('PF-Squint', 0.6), ...both('PF-Squeeze', 0.3) },
  Angry: { 'PF-Snarl': 0.3, 'PF-Press': 0.5, 'PF-Frown': 0.4, ...both('PF-BrowLower', 0.8), ...both('PF-BrowFurrow', 1), ...both('PF-Squint', 0.3) },
  Shout: { 'PF-JawOpen': 0.8, 'PF-VisWide': 0.8, 'PF-FrownOpen': 0.3, ...both('PF-BrowLower', 0.6), ...both('PF-BrowFurrow', 0.8), ...both('PF-EyeWide', 0.3) },
  Surprised: { 'PF-Surprise': 0.8, 'PF-JawOpen': 0.45, 'PF-VisOH': 0.35, ...both('PF-EyeWide', 1), ...both('PF-BrowRaise', 1), ...both('PF-BrowInnerUp', 0.3) },
  Skeptical: { 'PF-BrowRaise_L': 0.8, 'PF-BrowLower_R': 0.5, 'PF-Smirk_R': 0.6, 'PF-Squint_R': 0.3, 'PF-MouthSide_R': 0.3 },
  Sleepy: { ...both('PF-LidUpperDown', 0.6), ...both('PF-Blink', 0.3), ...both('PF-BrowSad', 0.2), 'PF-JawOpen': 0.08, 'PF-VisSmall': 0.2 },
  Focused: { ...both('PF-Squint', 0.4), ...both('PF-BrowLower', 0.35), ...both('PF-BrowFurrow', 0.4), 'PF-Press': 0.3 },
  Disgusted: { 'PF-Disgust': 0.9, 'PF-Snarl': 0.4, 'PF-MouthSide_L': 0.2, ...both('PF-BrowLower', 0.6), ...both('PF-Squint', 0.5) },
};

export const VISEME_SHAPES: Record<string, W> = {
  'PF-VisMBP': { 'PF-VisMBP': 1 },
  'PF-VisSmall': { 'PF-VisSmall': 1, 'PF-JawOpen': 0.12 },
  'PF-VisMid': { 'PF-VisMid': 1, 'PF-JawOpen': 0.3 },
  'PF-VisAA': { 'PF-VisAA': 1, 'PF-JawOpen': 0.55 },
  'PF-VisEE': { 'PF-VisEE': 1, 'PF-JawOpen': 0.2 },
  'PF-VisIH': { 'PF-VisIH': 1, 'PF-JawOpen': 0.22 },
  'PF-VisOH': { 'PF-VisOH': 1, 'PF-JawOpen': 0.4 },
  'PF-VisOO': { 'PF-VisOO': 1, 'PF-JawOpen': 0.18 },
  'PF-VisFV': { 'PF-VisFV': 1, 'PF-JawOpen': 0.08 },
  'PF-VisL': { 'PF-VisL': 1, 'PF-TongueL': 1, 'PF-JawOpen': 0.28 },
  'PF-VisTH': { 'PF-VisTH': 1, 'PF-TongueTh': 1, 'PF-JawOpen': 0.18 },
  'PF-VisSZ': { 'PF-VisSZ': 1, 'PF-JawOpen': 0.1 },
  'PF-VisWide': { 'PF-VisWide': 1, 'PF-JawOpen': 0.85 },
};

export interface Keyframe {
  t: number;
  w: W;
}

export interface Clip {
  id: string;
  label: string;
  duration: number;
  keys: Keyframe[];
  loop: boolean;
}

const blinkKeys = (side: 'both' | 'L' | 'R'): Keyframe[] => {
  const b = (v: number, sq = 0): W => {
    const out: W = {};
    const sidesList = side === 'both' ? ['L', 'R'] : [side];
    for (const s of sidesList) {
      out[`PF-Blink_${s}`] = v;
      if (sq) out[`PF-Squeeze_${s}`] = sq;
    }
    return out;
  };
  return [
    { t: 0, w: b(0) },
    { t: 0.045, w: b(0.55) },
    { t: 0.085, w: b(1) },
    { t: 0.13, w: b(1, 0.35) },
    { t: 0.17, w: b(1, 0.1) },
    { t: 0.26, w: b(0.6) },
    { t: 0.36, w: b(0.2) },
    { t: 0.42, w: b(0) },
  ];
};

const vis = (key: string): W => ({ ...VISEME_SHAPES[key] });

const TALK_SEQUENCE = ['PF-VisMBP', 'PF-VisSmall', 'PF-VisMid', 'PF-VisAA', 'PF-VisMid', 'PF-VisEE', 'PF-VisSmall', 'PF-VisOH', 'PF-VisSmall', 'PF-VisMBP'];

export const CLIPS: Clip[] = [
  { id: 'blink', label: 'Blink', duration: 0.42, keys: blinkKeys('both'), loop: false },
  { id: 'winkL', label: 'Wink left', duration: 0.42, keys: blinkKeys('L'), loop: false },
  { id: 'winkR', label: 'Wink right', duration: 0.42, keys: blinkKeys('R'), loop: false },
  {
    id: 'talk',
    label: 'Talking',
    duration: 2,
    loop: true,
    keys: TALK_SEQUENCE.map((k, i) => ({ t: (i / (TALK_SEQUENCE.length - 1)) * 2, w: vis(k) })),
  },
  {
    id: 'wrinkles',
    label: 'Wrinkle check',
    duration: 6,
    loop: true,
    keys: [
      { t: 0, w: {} },
      { t: 1, w: DEFAULT_POSES.Surprised },
      { t: 2, w: {} },
      { t: 3, w: DEFAULT_POSES.Angry },
      { t: 4, w: DEFAULT_POSES.Laugh },
      { t: 5, w: DEFAULT_POSES.Disgusted },
      { t: 6, w: {} },
    ],
  },
];

export const CLIP_BY_ID: Record<string, Clip> = Object.fromEntries(CLIPS.map((c) => [c.id, c]));

const ease = (x: number) => 0.5 - 0.5 * Math.cos(Math.PI * x);

export function sampleClip(clip: Clip, time: number): W {
  const t = clip.loop ? ((time % clip.duration) + clip.duration) % clip.duration : Math.min(Math.max(time, 0), clip.duration);
  const keys = clip.keys;
  let i = 0;
  while (i < keys.length - 2 && keys[i + 1].t <= t) i += 1;
  const a = keys[i];
  const b = keys[Math.min(i + 1, keys.length - 1)];
  const span = b.t - a.t;
  const f = span > 0 ? ease(Math.min(Math.max((t - a.t) / span, 0), 1)) : 0;
  const out: W = {};
  const names = new Set([...Object.keys(a.w), ...Object.keys(b.w)]);
  for (const n of names) out[n] = (a.w[n] ?? 0) * (1 - f) + (b.w[n] ?? 0) * f;
  return out;
}

export type BodyPose = 'apose' | 'relaxed' | 'tpose' | 'hero' | 'wave' | 'sit';

export const BODY_POSES: { id: BodyPose; label: string }[] = [
  { id: 'apose', label: 'A-pose' },
  { id: 'relaxed', label: 'Relaxed stand' },
  { id: 'tpose', label: 'T-pose' },
  { id: 'hero', label: 'Hero stance' },
  { id: 'wave', label: 'Wave' },
  { id: 'sit', label: 'Crouch' },
];

export interface PerformanceState {
  manual: W;
  gaze: { x: number; y: number; converge: number };
  head: { yaw: number; pitch: number; roll: number };
  pose: string | null;
  poseWeight: number;
  viseme: string | null;
  bodyPose: BodyPose;
  clip: { id: string; start: number; speed: number; loop: boolean } | null;
  autoBlink: boolean;
  wrinklePreview: boolean;
}

export function neutralPerformance(): PerformanceState {
  return {
    manual: {},
    gaze: { x: 0, y: 0, converge: 0 },
    head: { yaw: 0, pitch: 0, roll: 0 },
    pose: null,
    poseWeight: 1,
    viseme: null,
    bodyPose: 'apose',
    clip: null,
    autoBlink: true,
    wrinklePreview: true,
  };
}

export function poseWeights(name: string, profile: FaceProfile): W {
  return { ...(DEFAULT_POSES[name] ?? {}), ...(profile.expressions[name] ?? {}) };
}

/** Combines pose, viseme, clip, idle blink, and manual keys into one clamped set of performance weights. */
export function resolvePerformance(perf: PerformanceState, profile: FaceProfile, now: number, idleBlink: number): W {
  const out: W = {};
  const add = (w: W, scale = 1) => {
    for (const [k, v] of Object.entries(w)) out[k] = (out[k] ?? 0) + v * scale;
  };
  if (perf.pose) add(poseWeights(perf.pose, profile), perf.poseWeight);
  if (perf.viseme && VISEME_SHAPES[perf.viseme]) add(VISEME_SHAPES[perf.viseme]);
  if (perf.clip) {
    const clip = CLIP_BY_ID[perf.clip.id];
    if (clip) add(sampleClip(clip, (now - perf.clip.start) * perf.clip.speed));
  }
  if (idleBlink > 0) {
    out['PF-Blink_L'] = Math.max(out['PF-Blink_L'] ?? 0, idleBlink);
    out['PF-Blink_R'] = Math.max(out['PF-Blink_R'] ?? 0, idleBlink);
  }
  add(perf.manual);
  for (const k of Object.keys(out)) out[k] = Math.min(1, Math.max(0, out[k]));
  return out;
}

export function clipFinished(perf: PerformanceState, now: number): boolean {
  if (!perf.clip) return false;
  const clip = CLIP_BY_ID[perf.clip.id];
  if (!clip || perf.clip.loop) return false;
  return (now - perf.clip.start) * perf.clip.speed >= clip.duration;
}

export const WRINKLE_REGIONS: { id: WrinkleRegion; label: string; drivers: string[] }[] = [
  { id: 'forehead', label: 'Forehead', drivers: ['PF-BrowRaise_L', 'PF-BrowRaise_R', 'PF-BrowInnerUp_L', 'PF-BrowInnerUp_R', 'PF-Surprise'] },
  { id: 'brow', label: 'Between the brows', drivers: ['PF-BrowFurrow_L', 'PF-BrowFurrow_R', 'PF-BrowLower_L', 'PF-BrowLower_R'] },
  { id: 'eyes', label: 'Eye corners', drivers: ['PF-Squint_L', 'PF-Squint_R', 'PF-Squeeze_L', 'PF-Squeeze_R', 'PF-SmileOpenJaw'] },
  { id: 'nose', label: 'Nose bridge', drivers: ['PF-Disgust', 'PF-Snarl'] },
  { id: 'mouth', label: 'Mouth folds', drivers: ['PF-SmileClosed', 'PF-SmileOpenJaw', 'PF-Frown', 'PF-Grimace', 'PF-Cry'] },
];

export function wrinkleActivation(weights: W, profile: FaceProfile): Record<WrinkleRegion, number> {
  const out = {} as Record<WrinkleRegion, number>;
  for (const r of WRINKLE_REGIONS) {
    let m = 0;
    for (const d of r.drivers) m = Math.max(m, weights[d] ?? 0);
    out[r.id] = m * (profile.wrinkles[r.id] ?? 0.5);
  }
  return out;
}
