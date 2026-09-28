export type BodyKind = 'adult' | 'child' | 'robot' | 'beast';
export type LibraryTag = 'humanoid' | 'robot' | 'full_beast';
export type StylePreset = 'stories' | 'breath' | 'legends';

export const BODY_KINDS: { id: BodyKind; label: string; hint: string }[] = [
  { id: 'adult', label: 'Adult humanoid', hint: 'Human and every human-beast. About 7 to 7.5 heads tall.' },
  { id: 'child', label: 'Child humanoid', hint: 'Clothed child, about 5 to 5.5 heads tall. No adult sliders.' },
  { id: 'robot', label: 'Robot', hint: 'Segmented machine with its own parts library.' },
  { id: 'beast', label: 'Quadruped dragon', hint: 'Four legs, wings, tail, and a talking muzzle.' },
];

export function libraryOf(kind: BodyKind): LibraryTag {
  if (kind === 'robot') return 'robot';
  if (kind === 'beast') return 'full_beast';
  return 'humanoid';
}

export function isHumanoid(kind: BodyKind): boolean {
  return kind === 'adult' || kind === 'child';
}

export type Region =
  | 'skull' | 'eyes' | 'brows' | 'nose' | 'mouth' | 'jaw' | 'cheeks' | 'ears'
  | 'neck' | 'chest' | 'waist' | 'hips' | 'shoulders' | 'arms' | 'hands' | 'legs' | 'feet' | 'body'
  | 'hair' | 'muzzle' | 'tail' | 'wings' | 'horns' | 'mane' | 'frill' | 'face';

export interface HairPiece {
  id: string;
  volume: number;
  width: number;
  length: number;
  root: string;
  tip: string;
  highlight: number;
}

export interface FacialHairPiece {
  id: string;
  length: number;
  bulk: number;
  color: string;
}

export interface EquipOffset {
  p: [number, number, number];
  r: [number, number, number];
  s: number;
}

export interface Equipped {
  uid: string;
  id: string;
  slot: string;
  colors: Record<string, string>;
  damage: number;
  offset: EquipOffset;
}

export type MaterialZone = 'head' | 'body' | 'arms' | 'legs' | 'nails';
export type LayerPage = 'skin' | 'makeup';

export interface AppearanceLayer {
  uid: string;
  category: string;
  name: string;
  page: LayerPage;
  color: string;
  opacity: number;
  mask: string;
  hidden: boolean;
  children?: AppearanceLayer[];
}

export type WrinkleRegion = 'forehead' | 'brow' | 'eyes' | 'nose' | 'mouth';

export interface FaceProfile {
  rig: 'hybrid' | 'bone' | 'morph';
  wrinkles: Record<WrinkleRegion, number>;
  expressions: Record<string, Record<string, number>>;
}

export interface PhysicsChannel {
  enabled: boolean;
  amount: number;
  stiffness: number;
}

export interface Identity {
  version: 1;
  name: string;
  bodyKind: BodyKind;
  archetype: string;
  style: StylePreset;
  values: Record<string, number>;
  looks: Record<string, string>;
  hair: {
    front: HairPiece;
    back: HairPiece;
    sides: HairPiece;
    extras: HairPiece[];
  };
  facialHair: {
    moustache: FacialHairPiece;
    sideburns: FacialHairPiece;
    beard: FacialHairPiece;
  };
  colors: Record<string, string>;
  equipped: Equipped[];
  appearance: Record<MaterialZone, AppearanceLayer[]>;
  faceProfile: FaceProfile;
  physics: Record<'hair' | 'cape' | 'tail' | 'wings', PhysicsChannel>;
  body: string | null;
}

export interface ControlDef {
  id: string;
  label: string;
  hint: string;
  path: string[];
  pathFor?: Partial<Record<BodyKind, string[]>>;
  min: number;
  max: number;
  bodies: BodyKind[];
  region: Region;
  tab: 'morphs' | 'material';
  morph?: string;
  morphNeg?: string;
  bone?: { prop: string; lo: number; hi: number };
  shader?: string;
  childLimit?: number;
  needsLook?: { slot: string; not: string[] };
}
