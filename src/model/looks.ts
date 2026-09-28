import type { BodyKind, LibraryTag } from './types';

export interface LookOption {
  id: string;
  label: string;
}

export interface LookSlot {
  slot: string;
  label: string;
  group: string;
  bodies: BodyKind[];
  options: LookOption[];
}

const o = (id: string, label: string): LookOption => ({ id, label });
const HUM: BodyKind[] = ['adult', 'child'];

export const LOOK_SLOTS: LookSlot[] = [
  { slot: 'muzzle', label: 'Muzzle or beak', group: 'Muzzle or beak', bodies: HUM, options: [o('none', 'None'), o('feline', 'Feline'), o('canine', 'Canine'), o('reptile', 'Reptile'), o('fish', 'Fish'), o('bird', 'Beak'), o('frog', 'Frog'), o('lagomorph', 'Rabbit-like'), o('heavy', 'Heavy')] },
  { slot: 'ears', label: 'Ears', group: 'Ears', bodies: HUM, options: [o('human', 'Human'), o('round', 'Rounded'), o('pointed', 'Pointed'), o('long', 'Long'), o('fin', 'Fin'), o('feathered', 'Feathered'), o('none', 'None')] },
  { slot: 'pupil', label: 'Pupil style', group: 'Eyes', bodies: HUM, options: [o('round', 'Round'), o('slit', 'Slit'), o('wide', 'Wide bar'), o('star', 'Four-point')] },
  { slot: 'fangs', label: 'Fangs', group: 'Mouth extras', bodies: HUM, options: [o('none', 'None'), o('small', 'Small'), o('long', 'Long')] },
  { slot: 'whiskers', label: 'Whiskers', group: 'Mouth extras', bodies: HUM, options: [o('none', 'None'), o('short', 'Short'), o('long', 'Long')] },
  { slot: 'beak', label: 'Beak overlap', group: 'Mouth extras', bodies: HUM, options: [o('none', 'None'), o('slight', 'Slight hook'), o('strong', 'Strong hook')] },
  { slot: 'mane', label: 'Mane, crest, or feathers', group: 'Mane, crest, or feathers', bodies: HUM, options: [o('none', 'None'), o('mane', 'Mane'), o('crest', 'Crest'), o('feathers', 'Head feathers')] },
  { slot: 'horns', label: 'Horns or head fins', group: 'Horns or head fins', bodies: HUM, options: [o('none', 'None'), o('straight', 'Straight pair'), o('curved', 'Curved pair'), o('swept', 'Swept back'), o('nose', 'Nose horn'), o('twinNose', 'Twin nose horns'), o('fins', 'Head fins')] },
  { slot: 'frill', label: 'Neck frill or gills', group: 'Neck frill or gills', bodies: HUM, options: [o('none', 'None'), o('frill', 'Frill'), o('gills', 'Gills')] },
  { slot: 'hands', label: 'Hands', group: 'Hands and feet', bodies: HUM, options: [o('human', 'Human'), o('paw', 'Paw'), o('webbed', 'Webbed'), o('talon', 'Talon')] },
  { slot: 'feet', label: 'Feet', group: 'Hands and feet', bodies: HUM, options: [o('human', 'Human'), o('paw', 'Paw'), o('webbed', 'Webbed'), o('talon', 'Talon')] },
  { slot: 'legs', label: 'Leg stance', group: 'Hands and feet', bodies: HUM, options: [o('plantigrade', 'Plantigrade'), o('digitigrade', 'Digitigrade')] },
  { slot: 'tail', label: 'Tail', group: 'Tail', bodies: HUM, options: [o('none', 'None'), o('feline', 'Feline'), o('canine', 'Canine'), o('lizard', 'Lizard'), o('fish', 'Fish'), o('bird', 'Bird'), o('serpent', 'Serpent'), o('puff', 'Puff')] },
  { slot: 'wings', label: 'Wings', group: 'Wings', bodies: HUM, options: [o('none', 'None'), o('feathered', 'Feathered'), o('membrane', 'Membrane'), o('fin', 'Fin')] },
  { slot: 'surface', label: 'Surface', group: 'Surface', bodies: HUM, options: [o('skin', 'Skin'), o('shortFur', 'Short fur'), o('longFur', 'Long fur'), o('scales', 'Scales'), o('feathers', 'Feathers'), o('amphibian', 'Amphibian skin'), o('hide', 'Thick hide')] },
  { slot: 'pattern', label: 'Pattern', group: 'Surface', bodies: ['adult', 'child', 'beast'], options: [o('plain', 'Plain'), o('stripes', 'Stripes'), o('spots', 'Spots'), o('plates', 'Plates')] },

  { slot: 'optic', label: 'Optic style', group: 'Optics and head', bodies: ['robot'], options: [o('twin', 'Twin lens'), o('visor', 'Visor'), o('mono', 'Single eye')] },
  { slot: 'antenna', label: 'Antenna', group: 'Optics and head', bodies: ['robot'], options: [o('none', 'None'), o('single', 'Single'), o('twin', 'Twin'), o('fin', 'Fin')] },
  { slot: 'robotMouth', label: 'Mouth grille', group: 'Optics and head', bodies: ['robot'], options: [o('segments', 'Segment grid'), o('bar', 'Light bar'), o('plate', 'Hinged plate')] },

  { slot: 'beastHorns', label: 'Horn style', group: 'Beast head', bodies: ['beast'], options: [o('none', 'None'), o('swept', 'Swept'), o('curled', 'Curled'), o('crown', 'Crown'), o('single', 'Single')] },
  { slot: 'beastCrest', label: 'Crest', group: 'Beast head', bodies: ['beast'], options: [o('none', 'None'), o('ridge', 'Ridge'), o('fan', 'Fan'), o('spines', 'Spines')] },
  { slot: 'beastEarFin', label: 'Ear fins', group: 'Beast head', bodies: ['beast'], options: [o('none', 'None'), o('fin', 'Fin'), o('frilled', 'Frilled')] },
  { slot: 'beastPupil', label: 'Pupil', group: 'Beast head', bodies: ['beast'], options: [o('slit', 'Slit'), o('round', 'Round')] },
  { slot: 'beastBack', label: 'Back ridge', group: 'Beast body', bodies: ['beast'], options: [o('spines', 'Spines'), o('plates', 'Plates'), o('smooth', 'Smooth'), o('sail', 'Sail')] },
];

export const LOOK_SLOT_BY_ID: Record<string, LookSlot> = Object.fromEntries(LOOK_SLOTS.map((s) => [s.slot, s]));

export function lookSlotsFor(kind: BodyKind): LookSlot[] {
  return LOOK_SLOTS.filter((s) => s.bodies.includes(kind));
}

export function defaultLooks(kind: BodyKind): Record<string, string> {
  const out: Record<string, string> = {};
  for (const s of lookSlotsFor(kind)) out[s.slot] = s.options[0].id;
  if (kind === 'beast') out.beastHorns = 'swept';
  if (kind === 'beast') out.beastCrest = 'ridge';
  if (kind === 'beast') out.beastEarFin = 'fin';
  return out;
}

export type HairSlot = 'front' | 'back' | 'sides' | 'extra';

export interface HairStyle {
  id: string;
  label: string;
  slot: HairSlot;
  child: boolean;
  adult: boolean;
}

const h = (slot: HairSlot, id: string, label: string, child = false, adult = true): HairStyle => ({ id, label, slot, child, adult });

export const HAIR_STYLES: HairStyle[] = [
  h('front', 'none', 'No fringe', true),
  h('front', 'blunt', 'Blunt fringe', true),
  h('front', 'parted', 'Parted fringe', true),
  h('front', 'swept', 'Swept fringe'),
  h('front', 'curtain', 'Curtain fringe'),
  h('front', 'asym', 'Asymmetrical fringe'),
  h('front', 'heavy', 'Heavy fringe'),
  h('front', 'wispy', 'Wispy fringe', true),
  h('front', 'midLong', 'Middle-part long'),
  h('front', 'eyeCover', 'One-eye cover'),
  h('front', 'curled', 'Curled fringe'),
  h('front', 'braidFringe', 'Braided fringe'),

  h('back', 'bald', 'Bald', false),
  h('back', 'crop', 'Crop', true),
  h('back', 'shortLayered', 'Short layered'),
  h('back', 'bob', 'Bob', true),
  h('back', 'longStraight', 'Long straight', true),
  h('back', 'longLayered', 'Long layered'),
  h('back', 'wavy', 'Wavy'),
  h('back', 'curls', 'Curls', true),
  h('back', 'hime', 'Hime cut'),
  h('back', 'lowPony', 'Low ponytail', true),
  h('back', 'highPony', 'High ponytail'),
  h('back', 'twinTails', 'Twin tails', true),
  h('back', 'braid', 'Single braid'),
  h('back', 'twinBraids', 'Twin braids', true),
  h('back', 'halfUp', 'Half-up', true),
  h('back', 'bun', 'Bun'),
  h('back', 'twinBuns', 'Twin buns'),
  h('back', 'sidePony', 'Side ponytail'),
  h('back', 'afro', 'Afro'),
  h('back', 'puff', 'Puff', true),
  h('back', 'locs', 'Locs'),
  h('back', 'cornrows', 'Cornrows'),
  h('back', 'braidPony', 'Braided ponytail'),
  h('back', 'mullet', 'Mullet'),
  h('back', 'wolf', 'Wolf cut'),
  h('back', 'undercut', 'Undercut with long top'),
  h('back', 'mohawk', 'Mohawk'),
  h('back', 'drill', 'Drill curls'),
  h('back', 'shoulderBraid', 'Loose shoulder braid'),

  h('sides', 'none', 'No side locks', true),
  h('sides', 'short', 'Short side locks', true),
  h('sides', 'long', 'Long side locks', true),
  h('sides', 'tucked', 'Tucked behind ears', true),
  h('sides', 'himeLocks', 'Straight cut side locks'),

  h('extra', 'ahoge', 'Ahoge', true),
  h('extra', 'sideLock', 'Side lock', true),
  h('extra', 'ribbon', 'Ribbon tie', true),
  h('extra', 'band', 'Hair band', true),
  h('extra', 'braidAccent', 'Small braid accent', true),
];

export const CHILD_HAIR_FALLBACK: Record<string, string> = {
  shortLayered: 'crop', wolf: 'crop', mullet: 'crop', undercut: 'crop', mohawk: 'crop', bald: 'crop', cornrows: 'crop',
  longLayered: 'longStraight', hime: 'longStraight', wavy: 'curls', drill: 'curls', afro: 'puff', locs: 'curls',
  highPony: 'lowPony', sidePony: 'lowPony', braidPony: 'twinBraids', braid: 'twinBraids', shoulderBraid: 'twinBraids',
  bun: 'halfUp', twinBuns: 'twinTails',
  swept: 'parted', curtain: 'parted', asym: 'parted', heavy: 'blunt', midLong: 'parted', eyeCover: 'parted', curled: 'wispy', braidFringe: 'blunt',
  himeLocks: 'long',
};

export function hairStylesFor(slot: HairSlot, kind: BodyKind): HairStyle[] {
  return HAIR_STYLES.filter((s) => s.slot === slot && (kind === 'child' ? s.child : s.adult));
}

export interface FullHairStyle {
  id: string;
  label: string;
  front: string;
  back: string;
  sides: string;
  extras: string[];
  child: boolean;
}

export const FULL_HAIR_STYLES: FullHairStyle[] = [
  { id: 'messyHunter', label: 'Messy hunter crop', front: 'swept', back: 'shortLayered', sides: 'short', extras: ['ahoge'], child: false },
  { id: 'paleBraid', label: 'Long braid with side locks', front: 'midLong', back: 'shoulderBraid', sides: 'long', extras: [], child: false },
  { id: 'neatBob', label: 'Neat bob', front: 'blunt', back: 'bob', sides: 'short', extras: [], child: true },
  { id: 'highTail', label: 'High ponytail', front: 'parted', back: 'highPony', sides: 'long', extras: ['band'], child: false },
  { id: 'twinTailsRibbon', label: 'Twin tails with ribbons', front: 'blunt', back: 'twinTails', sides: 'short', extras: ['ribbon'], child: true },
  { id: 'wildWolf', label: 'Wild wolf cut', front: 'heavy', back: 'wolf', sides: 'short', extras: [], child: false },
  { id: 'courtHime', label: 'Hime cut', front: 'blunt', back: 'hime', sides: 'himeLocks', extras: [], child: false },
  { id: 'cloudAfro', label: 'Cloud afro', front: 'none', back: 'afro', sides: 'none', extras: [], child: false },
  { id: 'kidCrop', label: 'Short crop', front: 'wispy', back: 'crop', sides: 'none', extras: ['ahoge'], child: true },
  { id: 'kidPuff', label: 'Puff', front: 'none', back: 'puff', sides: 'none', extras: ['band'], child: true },
  { id: 'kidBraids', label: 'Twin braids', front: 'parted', back: 'twinBraids', sides: 'short', extras: [], child: true },
  { id: 'elderBun', label: 'Low bun', front: 'curtain', back: 'bun', sides: 'tucked', extras: [], child: false },
];

export interface FacialHairStyle {
  id: string;
  label: string;
  kind: 'moustache' | 'sideburns' | 'beard';
}

export const FACIAL_HAIR_STYLES: FacialHairStyle[] = [
  { id: 'none', label: 'None', kind: 'moustache' },
  { id: 'pencil', label: 'Pencil moustache', kind: 'moustache' },
  { id: 'chevron', label: 'Chevron moustache', kind: 'moustache' },
  { id: 'handlebar', label: 'Handlebar moustache', kind: 'moustache' },
  { id: 'droop', label: 'Drooping moustache', kind: 'moustache' },
  { id: 'none', label: 'None', kind: 'sideburns' },
  { id: 'short', label: 'Short sideburns', kind: 'sideburns' },
  { id: 'mutton', label: 'Mutton chops', kind: 'sideburns' },
  { id: 'none', label: 'None', kind: 'beard' },
  { id: 'stubble', label: 'Stubble', kind: 'beard' },
  { id: 'short', label: 'Short beard', kind: 'beard' },
  { id: 'medium', label: 'Medium beard', kind: 'beard' },
  { id: 'full', label: 'Full beard', kind: 'beard' },
  { id: 'goatee', label: 'Goatee', kind: 'beard' },
];

export type AccessoryType = 'rigid' | 'deform' | 'replacement' | 'prop' | 'creature';

export interface AccessoryDef {
  id: string;
  label: string;
  library: LibraryTag;
  bodies: BodyKind[];
  category: 'Outfit' | 'Accessory';
  slot: string;
  socket: string;
  type: AccessoryType;
  hides: string[];
  followsShape: boolean;
  colors: Record<string, string>;
  damage: boolean;
  exclusive: boolean;
}

const acc = (a: Partial<AccessoryDef> & Pick<AccessoryDef, 'id' | 'label' | 'slot' | 'socket' | 'type'>): AccessoryDef => ({
  library: 'humanoid',
  bodies: ['adult'],
  category: 'Accessory',
  hides: [],
  followsShape: false,
  colors: {},
  damage: false,
  exclusive: true,
  ...a,
});

export const ACCESSORIES: AccessoryDef[] = [
  acc({ id: 'ranger_outfit', label: 'Layered ranger outfit', category: 'Outfit', slot: 'outfit', socket: 'SOC-Chest', type: 'deform', followsShape: true, colors: { cloth: '#6f8a5a', leather: '#7a4b2c', trim: '#c9a35a', pants: '#4a4f5c' } }),
  acc({ id: 'traveler_outfit', label: 'Traveler tunic', category: 'Outfit', slot: 'outfit', socket: 'SOC-Chest', type: 'deform', followsShape: true, colors: { cloth: '#b0564a', leather: '#5b3a24', trim: '#e2c27a', pants: '#3e4a5e' } }),
  acc({ id: 'painted_armor', label: 'Painted plate armor', slot: 'armor', socket: 'SOC-Chest', type: 'deform', followsShape: true, colors: { metal: '#5f8fa6', fur: '#d9cbb0', strap: '#6b4428' } }),
  acc({ id: 'goggles', label: 'Field goggles', slot: 'headgear', socket: 'SOC-HeadTop', type: 'rigid', colors: { frame: '#6b4a2c', lens: '#f09a3a' }, exclusive: false }),
  acc({ id: 'blade', label: 'One-handed blade', slot: 'weapon_r', socket: 'SOC-Weapon_R', type: 'prop', bodies: ['adult', 'robot'], colors: { blade: '#cfd8e0', grip: '#5a3a26', guard: '#c9a35a' } }),
  acc({ id: 'launcher', label: 'Compact launcher', slot: 'weapon_l', socket: 'SOC-Weapon_L', type: 'prop', bodies: ['adult', 'robot'], colors: { body: '#6b5a48', metal: '#9aa6b0', string: '#e8e0c8' } }),
  acc({ id: 'mech_chest', label: 'Robot armor chest shell', slot: 'robot_armor_chest', socket: 'SOC-Chest', type: 'rigid', colors: { paint: '#d8483a', panel: '#f0e6d0', glow: '#58e0ff' } }),
  acc({ id: 'mech_forearm', label: 'Robot armor forearm shell', slot: 'robot_armor_arm', socket: 'SOC-ForeArm_R', type: 'rigid', colors: { paint: '#d8483a', panel: '#f0e6d0', glow: '#58e0ff' } }),
  acc({ id: 'organic_companion', label: 'Living arm companion', slot: 'organic', socket: 'SOC-OrganicForeArm_L', type: 'creature', colors: { body: '#6fbf73', belly: '#e8e0a8', eye: '#ffcc33' } }),
  acc({ id: 'bandana', label: 'Bandana', slot: 'headwear', socket: 'SOC-HeadTop', type: 'rigid', bodies: ['adult', 'child'], colors: { cloth: '#c83a3a', pattern: '#f2e6d0' } }),
  acc({ id: 'sunglasses', label: 'Sunglasses', slot: 'eyewear', socket: 'SOC-Eyewear', type: 'rigid', bodies: ['adult'], colors: { frame: '#222228', lens: '#303848' } }),
  acc({ id: 'eyeglasses', label: 'Round eyeglasses', slot: 'eyewear', socket: 'SOC-Eyewear', type: 'rigid', bodies: ['adult', 'child'], colors: { frame: '#8a6a3a', lens: '#dfeaf0' } }),
  acc({ id: 'boots', label: 'Field boots', slot: 'footwear', socket: 'SOC-Foot_L', type: 'replacement', hides: ['toes', 'toenails'], colors: { leather: '#5b3a24', sole: '#2e2a26', buckle: '#c9a35a' } }),
  acc({ id: 'belt', label: 'Pouch belt', slot: 'belt', socket: 'SOC-Waist', type: 'deform', followsShape: true, colors: { leather: '#6b4428', buckle: '#c9a35a' } }),
  acc({ id: 'cape', label: 'Travel cape', slot: 'cape', socket: 'SOC-Cape', type: 'deform', damage: true, colors: { cloth: '#394a6a', lining: '#a33a3a', trim: '#c9a35a' } }),
  acc({ id: 'torn_cape', label: 'Torn cape', slot: 'cape', socket: 'SOC-Cape', type: 'deform', damage: true, colors: { cloth: '#5a4a3a', lining: '#3a3028', trim: '#8a7a5a' } }),

  acc({ id: 'child_outfit', label: 'Child shirt and shorts', category: 'Outfit', bodies: ['child'], slot: 'outfit', socket: 'SOC-Chest', type: 'deform', followsShape: true, colors: { cloth: '#f2c14e', trim: '#3a7bd5', pants: '#4a6a8a', leather: '#8a5a3a' } }),
  acc({ id: 'child_explorer', label: 'Child explorer outfit', category: 'Outfit', bodies: ['child'], slot: 'outfit', socket: 'SOC-Chest', type: 'deform', followsShape: true, colors: { cloth: '#7aa65a', trim: '#e8d8a8', pants: '#6a4a3a', leather: '#5b3a24' } }),
  acc({ id: 'child_shoes', label: 'Child shoes', bodies: ['child'], slot: 'footwear', socket: 'SOC-Foot_L', type: 'replacement', hides: ['toes', 'toenails'], colors: { leather: '#b04a3a', sole: '#f0ede8', buckle: '#f0ede8' } }),
  acc({ id: 'child_cape', label: 'Child cape', bodies: ['child'], slot: 'cape', socket: 'SOC-Cape', type: 'deform', damage: true, colors: { cloth: '#3a6ad5', lining: '#f2c14e', trim: '#f0ede8' } }),

  acc({ id: 'panel_kit', label: 'Shoulder panel kit', library: 'robot', bodies: ['robot'], slot: 'panel_kit', socket: 'SOC-Shoulder_L', type: 'rigid', colors: { paint: '#f0c040', panel: '#3a3f48' } }),
  acc({ id: 'robot_cape', label: 'Robot cape', library: 'robot', bodies: ['robot'], slot: 'cape', socket: 'SOC-Cape', type: 'deform', damage: true, colors: { cloth: '#2a2f3a', lining: '#d8483a', trim: '#f0c040' } }),

  acc({ id: 'dragon_collar', label: 'Dragon collar', library: 'full_beast', bodies: ['beast'], slot: 'collar', socket: 'SOC-Neck', type: 'rigid', colors: { leather: '#6b4428', metal: '#c9a35a', gem: '#58c0ff' } }),
  acc({ id: 'dragon_harness', label: 'Back harness', library: 'full_beast', bodies: ['beast'], slot: 'harness', socket: 'SOC-Back', type: 'rigid', colors: { leather: '#5b3a24', pad: '#a33a3a', metal: '#c9a35a' } }),
  acc({ id: 'wing_ornament', label: 'Wing ornament', library: 'full_beast', bodies: ['beast'], slot: 'wing_ornament', socket: 'SOC-Wing_L', type: 'rigid', colors: { metal: '#c9a35a', cloth: '#e8e0c8' } }),
];

export const ACCESSORY_BY_ID: Record<string, AccessoryDef> = Object.fromEntries(ACCESSORIES.map((a) => [a.id, a]));

export function accessoriesFor(kind: BodyKind): AccessoryDef[] {
  return ACCESSORIES.filter((a) => a.bodies.includes(kind));
}
