import type { BodyKind, ControlDef, Region } from './types';

const HUM: BodyKind[] = ['adult', 'child'];
const ADULT: BodyKind[] = ['adult'];
const ALL_HUMANLIKE: BodyKind[] = ['adult', 'child', 'robot'];

interface Opts {
  bi?: boolean;
  bodies?: BodyKind[];
  region: Region;
  morph?: string;
  morphNeg?: string;
  bone?: [string, number, number];
  shader?: string;
  childLimit?: number;
  needsLook?: { slot: string; not: string[] };
  tab?: 'morphs' | 'material';
  pathFor?: Partial<Record<BodyKind, string[]>>;
}

function c(id: string, label: string, hint: string, path: string[], o: Opts): ControlDef {
  return {
    id,
    label,
    hint,
    path,
    pathFor: o.pathFor,
    min: o.bi ? -100 : 0,
    max: 100,
    bodies: o.bodies ?? HUM,
    region: o.region,
    tab: o.tab ?? 'morphs',
    morph: o.morph,
    morphNeg: o.morphNeg,
    bone: o.bone ? { prop: o.bone[0], lo: o.bone[1], hi: o.bone[2] } : undefined,
    shader: o.shader,
    childLimit: o.childLimit,
    needsLook: o.needsLook,
  };
}

const FACE = ['Head', 'Face shape'];
const SKULL = ['Head', 'Skull'];
const JAW = ['Head', 'Jaw and chin'];
const CHEEK = ['Head', 'Cheeks'];
const BROW = ['Head', 'Brows'];
const EYE = ['Head', 'Eyes'];
const NOSE = ['Head', 'Nose'];
const MOUTH = ['Head', 'Mouth'];
const EAR = ['Head', 'Ears'];
const BUILD = ['Body', 'Build'];
const MUSCLE = ['Body', 'Muscle'];
const TORSO = ['Body', 'Torso'];
const ARMS = ['Body', 'Arms and hands'];
const LEGS = ['Body', 'Legs and feet'];
const NECK = ['Body', 'Neck'];
const PRES = ['Presentation'];
const AGE = ['Age'];
const EL = (s: string) => ['Elements', s];
const ROBOT_BODY = ['Chassis'];
const ROBOT_HEAD = ['Optics and head'];
const BEAST_BODY = ['Beast body'];
const BEAST_HEAD = ['Beast head'];
const MAT = (s: string) => ['Material', s];

const notNone = (slot: string) => ({ slot, not: ['none'] });

export const CONTROLS: ControlDef[] = [
  c('face.round', 'Round face', 'Fuller, rounder cheeks and jaw.', FACE, { region: 'face', morph: 'ID-FaceRound' }),
  c('face.long', 'Long face', 'Taller face from brow to chin.', FACE, { region: 'face', morph: 'ID-FaceLong' }),
  c('face.square', 'Square face', 'Flatter jaw corners and a wider chin.', FACE, { region: 'jaw', morph: 'ID-FaceSquare' }),
  c('face.heart', 'Heart face', 'Wide forehead tapering to a small chin.', FACE, { region: 'face', morph: 'ID-FaceHeart' }),
  c('face.diamond', 'Diamond face', 'Wide cheekbones, narrow forehead and chin.', FACE, { region: 'cheeks', morph: 'ID-FaceDiamond' }),

  c('head.size', 'Head size', 'Scales the whole head. The neck seam is corrected.', SKULL, { bi: true, bodies: ALL_HUMANLIKE, region: 'skull', bone: ['head_scale', 0.9, 1.15], childLimit: 60 }),
  c('skull.width', 'Skull width', 'Wider or narrower cranium. Drag the skull in front view.', SKULL, { bi: true, region: 'skull', morph: 'ID-SkullWidth', morphNeg: 'ID-SkullWidth_Neg' }),
  c('skull.depth', 'Skull depth', 'Deeper or shallower cranium. Drag the skull in side view.', SKULL, { bi: true, region: 'skull', morph: 'ID-SkullDepth', morphNeg: 'ID-SkullDepth_Neg' }),
  c('skull.crown', 'Crown height', 'Raises or lowers the top of the head.', SKULL, { bi: true, region: 'skull', morph: 'ID-SkullCrown', morphNeg: 'ID-SkullCrown_Neg' }),

  c('jaw.width', 'Jaw width', 'Wider or narrower jaw.', JAW, { bi: true, region: 'jaw', morph: 'ID-JawWidth', morphNeg: 'ID-JawWidth_Neg' }),
  c('jaw.height', 'Jaw angle height', 'Moves the jaw corners up or down.', JAW, { bi: true, region: 'jaw', morph: 'ID-JawHeight', morphNeg: 'ID-JawHeight_Neg' }),
  c('chin.length', 'Chin length', 'Longer or shorter chin.', JAW, { bi: true, region: 'jaw', morph: 'ID-ChinLength', morphNeg: 'ID-ChinLength_Neg' }),
  c('chin.width', 'Chin width', 'Wider or pointier chin.', JAW, { bi: true, region: 'jaw', morph: 'ID-ChinWidth', morphNeg: 'ID-ChinWidth_Neg' }),
  c('chin.cleft', 'Chin cleft', 'A small dimple in the chin.', JAW, { region: 'jaw', morph: 'ID-ChinCleft', bodies: ADULT }),

  c('cheek.full', 'Cheek fullness', 'Full cheeks to the right, hollow cheeks to the left.', CHEEK, { bi: true, region: 'cheeks', morph: 'ID-CheekFull', morphNeg: 'ID-CheekHollow' }),
  c('cheek.bone', 'Cheekbones', 'Higher, more defined cheekbones.', CHEEK, { bi: true, region: 'cheeks', morph: 'ID-Cheekbone', morphNeg: 'ID-Cheekbone_Neg' }),

  c('brow.ridge', 'Brow ridge', 'Heavier or flatter bone above the eyes.', BROW, { bi: true, region: 'brows', morph: 'ID-BrowRidge', morphNeg: 'ID-BrowRidge_Neg' }),
  c('brow.height', 'Brow height', 'Places the brows higher or lower. Expression brows move from here.', BROW, { bi: true, region: 'brows', bone: ['brow_height', 0.85, 1.15] }),
  c('brow.tilt', 'Brow tilt', 'Tilts the outer brow up or down.', BROW, { bi: true, region: 'brows', bone: ['brow_tilt', 0.85, 1.15] }),
  c('brow.spacing', 'Brow spacing', 'Moves the brows apart or together.', BROW, { bi: true, region: 'brows', bone: ['brow_spacing', 0.85, 1.15] }),
  c('brow.thickness', 'Brow thickness', 'Thicker or thinner brow strip.', BROW, { bi: true, region: 'brows', morph: 'ID-BrowThick', morphNeg: 'ID-BrowThin' }),
  c('brow.length', 'Brow length', 'Longer or shorter brow strip.', BROW, { bi: true, region: 'brows', morph: 'ID-BrowLong', morphNeg: 'ID-BrowShort' }),

  c('eye.size', 'Eye size', 'Larger or smaller eyes.', EYE, { bi: true, region: 'eyes', morph: 'ID-EyeSize', morphNeg: 'ID-EyeSize_Neg' }),
  c('eye.height', 'Eye height', 'Places the eyes higher or lower on the face.', EYE, { bi: true, region: 'eyes', morph: 'ID-EyeHeight', morphNeg: 'ID-EyeHeight_Neg' }),
  c('eye.spacing', 'Eye spacing', 'Wider or closer set eyes.', EYE, { bi: true, region: 'eyes', morph: 'ID-EyeSpacing', morphNeg: 'ID-EyeSpacing_Neg' }),
  c('eye.tilt', 'Eye tilt', 'Tilts the outer corners up or down.', EYE, { bi: true, region: 'eyes', morph: 'ID-EyeTilt', morphNeg: 'ID-EyeTilt_Neg' }),
  c('eye.almond', 'Almond shape', 'Pointed corners, curved lids.', EYE, { region: 'eyes', morph: 'ID-EyeAlmond' }),
  c('eye.round', 'Round shape', 'A rounder opening.', EYE, { region: 'eyes', morph: 'ID-EyeRound' }),
  c('eye.narrow', 'Narrow shape', 'A slimmer opening.', EYE, { region: 'eyes', morph: 'ID-EyeNarrow' }),
  c('eye.droop', 'Outer corner', 'Droop to the left, upturn to the right.', EYE, { bi: true, region: 'eyes', morph: 'ID-EyeUpturn', morphNeg: 'ID-EyeDroop' }),
  c('lid.crease', 'Lid crease', 'A visible fold above the eye.', EYE, { region: 'eyes', morph: 'ID-LidCrease' }),
  c('lid.hood', 'Hooded lid', 'The upper lid sits lower over the eye.', EYE, { region: 'eyes', morph: 'ID-LidHood' }),
  c('lash.length', 'Lash length', 'Short lashes to the left, long lashes to the right.', EYE, { bi: true, region: 'eyes', morph: 'ID-LashLong', morphNeg: 'ID-LashShort' }),

  c('nose.bridgeHeight', 'Bridge height', 'A higher or flatter nose bridge.', NOSE, { bi: true, region: 'nose', morph: 'ID-NoseBridgeHigh', morphNeg: 'ID-NoseBridgeHigh_Neg' }),
  c('nose.bridgeWidth', 'Bridge width', 'A wider or narrower bridge.', NOSE, { bi: true, region: 'nose', morph: 'ID-NoseBridgeWide', morphNeg: 'ID-NoseBridgeWide_Neg' }),
  c('nose.tipUp', 'Tip lift', 'Turns the tip up or down.', NOSE, { bi: true, region: 'nose', morph: 'ID-NoseTipUp', morphNeg: 'ID-NoseTipUp_Neg' }),
  c('nose.tipWidth', 'Tip width', 'A wider or finer tip.', NOSE, { bi: true, region: 'nose', morph: 'ID-NoseTipWide', morphNeg: 'ID-NoseTipWide_Neg' }),
  c('nose.size', 'Nose size', 'Smaller to the left, larger to the right.', NOSE, { bi: true, region: 'nose', morph: 'ID-NoseLarge', morphNeg: 'ID-NoseSmall' }),
  c('nose.length', 'Nose length', 'Longer or shorter nose.', NOSE, { bi: true, region: 'nose', morph: 'ID-NoseLong', morphNeg: 'ID-NoseLong_Neg' }),
  c('nose.nostril', 'Nostril flare', 'Wider nostrils.', NOSE, { region: 'nose', morph: 'ID-NostrilFlare' }),

  c('mouth.width', 'Mouth width', 'Wider or narrower mouth.', MOUTH, { bi: true, region: 'mouth', morph: 'ID-MouthWidth', morphNeg: 'ID-MouthWidth_Neg' }),
  c('mouth.height', 'Mouth height', 'Moves the mouth up or down.', MOUTH, { bi: true, region: 'mouth', morph: 'ID-MouthHeight', morphNeg: 'ID-MouthHeight_Neg' }),
  c('lip.upper', 'Upper lip', 'Fuller or thinner upper lip.', MOUTH, { bi: true, region: 'mouth', morph: 'ID-LipUpper', morphNeg: 'ID-LipUpper_Neg' }),
  c('lip.lower', 'Lower lip', 'Fuller or thinner lower lip.', MOUTH, { bi: true, region: 'mouth', morph: 'ID-LipLower', morphNeg: 'ID-LipLower_Neg' }),
  c('lip.thin', 'Thin lips', 'Thins both lips together.', MOUTH, { region: 'mouth', morph: 'ID-LipThin' }),
  c('mouth.corner', 'Mouth corners', 'Resting corners down to the left, up to the right.', MOUTH, { bi: true, region: 'mouth', morph: 'ID-CornerUp', morphNeg: 'ID-CornerDown' }),
  c('mouth.philtrum', 'Philtrum', 'Deeper groove above the upper lip.', MOUTH, { region: 'mouth', morph: 'ID-Philtrum' }),

  c('ear.size', 'Ear size', 'Larger or smaller human ears.', EAR, { bi: true, region: 'ears', morph: 'ID-EarSize', morphNeg: 'ID-EarSize_Neg' }),
  c('ear.point', 'Ear point', 'Pointed tips on a human ear.', EAR, { region: 'ears', morph: 'ID-EarPoint' }),
  c('ear.out', 'Ear angle', 'Ears stand out from the head.', EAR, { region: 'ears', morph: 'ID-EarOut' }),
  c('ear.lobe', 'Ear lobe', 'Larger ear lobes.', EAR, { region: 'ears', morph: 'ID-EarLobe' }),
  c('ear.height', 'Ear height', 'Places the ears higher or lower.', EAR, { bi: true, region: 'ears', bone: ['ear_height', 0.85, 1.15] }),

  c('body.height', 'Height', 'Overall height. Proportions stay the same.', BUILD, { bi: true, bodies: ALL_HUMANLIKE, region: 'body', bone: ['height', 0.9, 1.1], childLimit: 70, pathFor: { adult: PRES } }),
  c('body.bulk', 'Bulk', 'Lean to the left, heavy to the right.', BUILD, { bi: true, region: 'body', morph: 'ID-BodyBulk', morphNeg: 'ID-BodyLean', childLimit: 60 }),
  c('body.soft', 'Softness', 'Softer, rounder forms.', BUILD, { region: 'body', morph: 'ID-BodySoft' }),
  c('body.belly', 'Belly', 'A rounder or flatter belly.', BUILD, { bi: true, region: 'waist', morph: 'ID-Belly', morphNeg: 'ID-Belly_Neg', childLimit: 50 }),
  c('body.glute', 'Seat', 'Fuller or flatter seat.', BUILD, { bi: true, bodies: ADULT, region: 'hips', morph: 'ID-Glute', morphNeg: 'ID-Glute_Neg' }),

  c('muscle.chest', 'Chest muscle', 'Definition on the chest.', MUSCLE, { bodies: ADULT, region: 'chest', morph: 'ID-MuscleChest' }),
  c('muscle.abs', 'Abdominal muscle', 'Definition on the stomach.', MUSCLE, { bodies: ADULT, region: 'waist', morph: 'ID-MuscleAbs' }),
  c('muscle.arms', 'Arm muscle', 'Definition on the arms.', MUSCLE, { bodies: ADULT, region: 'arms', morph: 'ID-MuscleArms' }),
  c('muscle.legs', 'Leg muscle', 'Definition on the legs.', MUSCLE, { bodies: ADULT, region: 'legs', morph: 'ID-MuscleLegs' }),

  c('body.shoulders', 'Shoulders', 'Wider or narrower shoulders.', TORSO, { bi: true, bodies: ALL_HUMANLIKE, region: 'shoulders', bone: ['shoulder_width', 0.85, 1.15], morph: 'ID-BroadShoulders', childLimit: 50, pathFor: { adult: PRES } }),
  c('body.chest', 'Chest', 'Chest volume.', TORSO, { bi: true, bodies: ADULT, region: 'chest', morph: 'ID-Chest', morphNeg: 'ID-Chest_Neg', pathFor: { adult: PRES } }),
  c('body.waist', 'Waist', 'Narrower waist to the right.', TORSO, { bi: true, region: 'waist', morph: 'ID-NarrowWaist', morphNeg: 'ID-NarrowWaist_Neg', childLimit: 40, pathFor: { adult: PRES } }),
  c('body.hips', 'Hips', 'Wider or narrower hips.', TORSO, { bi: true, region: 'hips', bone: ['hip_width', 0.85, 1.15], morph: 'ID-WideHips', childLimit: 40, pathFor: { adult: PRES } }),
  c('face.softness', 'Face softness', 'Softer to the right, sharper to the left.', PRES, { bi: true, bodies: ADULT, region: 'face', morph: 'ID-FaceSoft', morphNeg: 'ID-FaceSharp' }),
  c('torso.length', 'Torso length', 'Longer or shorter torso.', TORSO, { bi: true, bodies: ALL_HUMANLIKE, region: 'chest', bone: ['torso_length', 0.85, 1.15], childLimit: 60 }),

  c('upperArm.length', 'Upper arm length', 'Longer or shorter upper arms.', ARMS, { bi: true, bodies: ALL_HUMANLIKE, region: 'arms', bone: ['upper_arm_length', 0.85, 1.15], childLimit: 60 }),
  c('forearm.length', 'Forearm length', 'Longer or shorter forearms.', ARMS, { bi: true, bodies: ALL_HUMANLIKE, region: 'arms', bone: ['forearm_length', 0.85, 1.15], childLimit: 60 }),
  c('upperArm.bulk', 'Upper arm bulk', 'Thicker or thinner upper arms.', ARMS, { bi: true, region: 'arms', morph: 'ID-UpperArmBulk', morphNeg: 'ID-UpperArmBulk_Neg', childLimit: 50 }),
  c('forearm.bulk', 'Forearm bulk', 'Thicker or thinner forearms.', ARMS, { bi: true, region: 'arms', morph: 'ID-ForeArmBulk', morphNeg: 'ID-ForeArmBulk_Neg', childLimit: 50 }),
  c('hand.size', 'Hand size', 'Larger or smaller hands.', ARMS, { bi: true, bodies: ALL_HUMANLIKE, region: 'hands', morph: 'ID-HandSize', morphNeg: 'ID-HandSize_Neg', childLimit: 50 }),
  c('hand.length', 'Hand length', 'Longer palms.', ARMS, { bi: true, bodies: ALL_HUMANLIKE, region: 'hands', bone: ['hand_length', 0.85, 1.15], childLimit: 50 }),
  c('finger.length', 'Finger length', 'Longer or shorter fingers.', ARMS, { bi: true, region: 'hands', bone: ['finger_length', 0.85, 1.15], childLimit: 50 }),
  c('nail.length', 'Nail length', 'Longer fingernails and toenails.', ARMS, { region: 'hands', morph: 'ID-NailLength', childLimit: 20 }),

  c('thigh.length', 'Thigh length', 'Longer or shorter thighs.', LEGS, { bi: true, bodies: ALL_HUMANLIKE, region: 'legs', bone: ['thigh_length', 0.85, 1.15], childLimit: 60 }),
  c('shin.length', 'Shin length', 'Longer or shorter shins.', LEGS, { bi: true, bodies: ALL_HUMANLIKE, region: 'legs', bone: ['shin_length', 0.85, 1.15], childLimit: 60 }),
  c('thigh.bulk', 'Thigh bulk', 'Thicker or thinner thighs.', LEGS, { bi: true, region: 'legs', morph: 'ID-ThighBulk', morphNeg: 'ID-ThighBulk_Neg', childLimit: 50 }),
  c('calf.bulk', 'Calf bulk', 'Thicker or thinner calves.', LEGS, { bi: true, region: 'legs', morph: 'ID-CalfBulk', morphNeg: 'ID-CalfBulk_Neg', childLimit: 50 }),
  c('foot.size', 'Foot size', 'Larger or smaller feet.', LEGS, { bi: true, bodies: ALL_HUMANLIKE, region: 'feet', morph: 'ID-FootSize', morphNeg: 'ID-FootSize_Neg', childLimit: 50 }),
  c('foot.length', 'Foot length', 'Longer or shorter feet.', LEGS, { bi: true, bodies: ALL_HUMANLIKE, region: 'feet', bone: ['foot_length', 0.85, 1.15], childLimit: 50 }),

  c('neck.length', 'Neck length', 'Longer or shorter neck.', NECK, { bi: true, bodies: ALL_HUMANLIKE, region: 'neck', bone: ['neck_length', 0.85, 1.15], childLimit: 60 }),
  c('neck.thickness', 'Neck thickness', 'Thicker or thinner neck.', NECK, { bi: true, bodies: ALL_HUMANLIKE, region: 'neck', morph: 'ID-NeckThickness', morphNeg: 'ID-NeckThickness_Neg', childLimit: 50 }),

  c('age.years', 'Age', 'Young adult to the left, adult at zero, old to the right.', AGE, { bi: true, bodies: ['adult', 'beast'], region: 'face', morph: 'ID-AgeOld', morphNeg: 'ID-AgeYoung' }),
  c('age.creases', 'Creases', 'Brow, eye, and mouth creases.', AGE, { bodies: ADULT, region: 'face', morph: 'ID-AgeCreases' }),
  c('age.jawSoft', 'Jaw softness', 'A softer jaw line with age.', AGE, { bodies: ADULT, region: 'jaw', morph: 'ID-AgeJawSoft' }),
  c('age.stoop', 'Stoop', 'A mild forward stoop.', AGE, { bodies: ADULT, region: 'body', bone: ['stoop', 0, 1] }),
  c('age.wear', 'Scale wear', 'Worn, chipped scale edges.', AGE, { bodies: ['beast'], region: 'body', shader: 'scale_wear' }),
  c('age.posture', 'Low posture', 'Lower head and shoulders with age.', AGE, { bodies: ['beast'], region: 'neck', bone: ['posture', 0, 1] }),

  c('muzzle.length', 'Muzzle length', 'How far the muzzle or beak reaches.', EL('Muzzle or beak'), { bi: true, region: 'muzzle', morph: 'ID-MuzzleLength', morphNeg: 'ID-MuzzleLength_Neg', needsLook: notNone('muzzle') }),
  c('muzzle.width', 'Muzzle width', 'Wider or narrower muzzle.', EL('Muzzle or beak'), { bi: true, region: 'muzzle', morph: 'ID-MuzzleWidth', morphNeg: 'ID-MuzzleWidth_Neg', needsLook: notNone('muzzle') }),
  c('muzzle.height', 'Muzzle height', 'Taller or flatter muzzle.', EL('Muzzle or beak'), { bi: true, region: 'muzzle', morph: 'ID-MuzzleHeight', morphNeg: 'ID-MuzzleHeight_Neg', needsLook: notNone('muzzle') }),
  c('muzzle.bridge', 'Muzzle bridge', 'A raised or dipped bridge between the eyes and nose.', EL('Muzzle or beak'), { bi: true, region: 'muzzle', morph: 'ID-MuzzleBridge', morphNeg: 'ID-MuzzleBridge_Neg', needsLook: notNone('muzzle') }),
  c('earEl.size', 'Ear size', 'Size of the chosen ear look.', EL('Ears'), { bi: true, region: 'ears', morph: 'ID-EarElSize', morphNeg: 'ID-EarElSize_Neg', needsLook: { slot: 'ears', not: ['none', 'human'] } }),
  c('earEl.lift', 'Ear lift', 'Ears sit higher or droop lower.', EL('Ears'), { bi: true, region: 'ears', morph: 'ID-EarElLift', morphNeg: 'ID-EarElLift_Neg', needsLook: { slot: 'ears', not: ['none', 'human'] } }),
  c('earEl.spread', 'Ear spread', 'Ears angle out or lie back.', EL('Ears'), { bi: true, region: 'ears', morph: 'ID-EarElSpread', morphNeg: 'ID-EarElSpread_Neg', needsLook: { slot: 'ears', not: ['none', 'human'] } }),
  c('eye.forward', 'Eye placement', 'Eyes sit more to the front or more to the sides.', EL('Eyes'), { bi: true, region: 'eyes', morph: 'ID-EyeForward', morphNeg: 'ID-EyeForward_Neg' }),
  c('fang.length', 'Fang length', 'Longer fangs.', EL('Mouth extras'), { region: 'mouth', morph: 'ID-FangLength', needsLook: notNone('fangs') }),
  c('whisker.density', 'Whisker density', 'More whiskers on each side.', EL('Mouth extras'), { region: 'muzzle', shader: 'whisker_density', needsLook: notNone('whiskers') }),
  c('mane.length', 'Length', 'Longer mane, crest, or feathers.', EL('Mane, crest, or feathers'), { bi: true, region: 'mane', morph: 'ID-ManeLength', morphNeg: 'ID-ManeLength_Neg', needsLook: notNone('mane') }),
  c('mane.volume', 'Volume', 'Fuller mane, crest, or feathers.', EL('Mane, crest, or feathers'), { bi: true, region: 'mane', morph: 'ID-ManeVolume', morphNeg: 'ID-ManeVolume_Neg', needsLook: notNone('mane') }),
  c('horn.length', 'Horn length', 'Longer or shorter horns or head fins.', EL('Horns or head fins'), { bi: true, region: 'horns', morph: 'ID-HornLength', morphNeg: 'ID-HornLength_Neg', needsLook: notNone('horns') }),
  c('horn.thickness', 'Horn thickness', 'Thicker or thinner horns.', EL('Horns or head fins'), { bi: true, region: 'horns', morph: 'ID-HornThickness', morphNeg: 'ID-HornThickness_Neg', needsLook: notNone('horns') }),
  c('horn.curve', 'Horn curve', 'Straighter to the left, more curved to the right.', EL('Horns or head fins'), { bi: true, region: 'horns', morph: 'ID-HornCurve', morphNeg: 'ID-HornCurve_Neg', needsLook: notNone('horns') }),
  c('frill.size', 'Frill size', 'Size of the neck frill or gills.', EL('Neck frill or gills'), { bi: true, region: 'frill', morph: 'ID-FrillSize', morphNeg: 'ID-FrillSize_Neg', needsLook: notNone('frill') }),
  c('frill.flare', 'Frill flare', 'How far the frill opens.', EL('Neck frill or gills'), { region: 'frill', morph: 'ID-FrillFlare', needsLook: notNone('frill') }),
  c('digit.emphasis', 'Digit emphasis', 'Bolder fingers and toes on paws, webs, and talons.', EL('Hands and feet'), { region: 'hands', morph: 'ID-DigitEmphasis' }),
  c('claw.length', 'Claw length', 'Longer claws on paws and talons.', EL('Hands and feet'), { region: 'hands', morph: 'ID-ClawLength' }),
  c('tail.length', 'Tail length', 'Longer or shorter tail.', EL('Tail'), { bi: true, region: 'tail', bone: ['tail_length', 0.6, 1.5], needsLook: notNone('tail') }),
  c('tail.thickness', 'Tail thickness', 'Thicker or thinner tail.', EL('Tail'), { bi: true, region: 'tail', morph: 'ID-TailThick', morphNeg: 'ID-TailThin', needsLook: notNone('tail') }),
  c('tail.tip', 'Tail tip', 'A larger tuft, fin, or fan at the tip.', EL('Tail'), { bi: true, region: 'tail', morph: 'ID-TailTip', morphNeg: 'ID-TailTip_Neg', needsLook: notNone('tail') }),
  c('wing.span', 'Wing span', 'Wider or narrower wings.', EL('Wings'), { bi: true, region: 'wings', bone: ['wing_span', 0.6, 1.4], needsLook: notNone('wings') }),
  c('wing.fold', 'Wing fold', 'Open to the left, folded to the right.', EL('Wings'), { bi: true, region: 'wings', bone: ['wing_fold', 0, 1], needsLook: notNone('wings') }),
  c('surface.coverage', 'Coverage', 'Patchy coverage to the left, full coverage with extra tufts to the right.', EL('Surface'), { bi: true, region: 'body', shader: 'surface_coverage', needsLook: { slot: 'surface', not: ['skin'] } }),

  c('robot.bulk', 'Chassis bulk', 'Slim frame to the left, heavy frame to the right.', ROBOT_BODY, { bi: true, bodies: ['robot'], region: 'body', morph: 'ID-ChassisBulk', morphNeg: 'ID-ChassisBulk_Neg' }),
  c('robot.core', 'Chest core', 'Size of the glowing chest core.', ROBOT_BODY, { bi: true, bodies: ['robot'], region: 'chest', morph: 'ID-ChestCore', morphNeg: 'ID-ChestCore_Neg' }),
  c('robot.panelGap', 'Panel gap', 'Wider gaps between plates.', ROBOT_BODY, { bodies: ['robot'], region: 'body', shader: 'panel_gap' }),
  c('robot.wear', 'Paint wear', 'Chipped paint on edges.', ROBOT_BODY, { bodies: ['robot'], region: 'body', shader: 'paint_wear' }),
  c('robot.optic', 'Optic size', 'Larger or smaller lens eyes.', ROBOT_HEAD, { bi: true, bodies: ['robot'], region: 'eyes', morph: 'ID-OpticSize', morphNeg: 'ID-OpticSize_Neg' }),
  c('robot.antenna', 'Antenna length', 'Longer antenna.', ROBOT_HEAD, { bi: true, bodies: ['robot'], region: 'skull', morph: 'ID-AntennaLength', morphNeg: 'ID-AntennaLength_Neg', needsLook: notNone('antenna') }),

  c('beast.size', 'Body size', 'Overall size of the dragon.', BEAST_BODY, { bi: true, bodies: ['beast'], region: 'body', bone: ['body_size', 0.6, 1.4] }),
  c('beast.neck', 'Neck length', 'Longer or shorter neck.', BEAST_BODY, { bi: true, bodies: ['beast'], region: 'neck', bone: ['neck_length', 0.7, 1.4] }),
  c('beast.tail', 'Tail length', 'Longer or shorter tail.', BEAST_BODY, { bi: true, bodies: ['beast'], region: 'tail', bone: ['tail_length', 0.7, 1.4] }),
  c('beast.wing', 'Wing size', 'Larger or smaller wings.', BEAST_BODY, { bi: true, bodies: ['beast'], region: 'wings', bone: ['wing_size', 0.7, 1.4] }),
  c('beast.wingFold', 'Wing fold', 'Open to the left, folded to the right.', BEAST_BODY, { bi: true, bodies: ['beast'], region: 'wings', bone: ['wing_fold', 0, 1] }),
  c('beast.leg', 'Leg length', 'Longer or shorter legs.', BEAST_BODY, { bi: true, bodies: ['beast'], region: 'legs', bone: ['leg_length', 0.8, 1.25] }),
  c('beast.bulk', 'Bulk', 'Leaner or heavier body.', BEAST_BODY, { bi: true, bodies: ['beast'], region: 'body', morph: 'ID-BeastBulk', morphNeg: 'ID-BeastLean' }),
  c('beast.claw', 'Claw length', 'Longer claws.', BEAST_BODY, { bodies: ['beast'], region: 'feet', morph: 'ID-ClawLength' }),
  c('beast.snout', 'Snout length', 'Short snout to the left, long snout to the right.', BEAST_HEAD, { bi: true, bodies: ['beast'], region: 'muzzle', morph: 'ID-SnoutLong', morphNeg: 'ID-SnoutShort' }),
  c('beast.jaw', 'Jaw width', 'Wider or narrower jaw.', BEAST_HEAD, { bi: true, bodies: ['beast'], region: 'jaw', morph: 'ID-JawWidth', morphNeg: 'ID-JawWidth_Neg' }),
  c('beast.head', 'Head size', 'Larger or smaller head.', BEAST_HEAD, { bi: true, bodies: ['beast'], region: 'skull', bone: ['head_scale', 0.85, 1.2] }),
  c('beast.horn', 'Horn size', 'Longer, heavier horns.', BEAST_HEAD, { bi: true, bodies: ['beast'], region: 'horns', morph: 'ID-HornStyleSize', morphNeg: 'ID-HornStyleSize_Neg', needsLook: notNone('beastHorns') }),
  c('beast.crest', 'Crest size', 'Taller crest.', BEAST_HEAD, { bi: true, bodies: ['beast'], region: 'mane', morph: 'ID-Crest', morphNeg: 'ID-Crest_Neg', needsLook: notNone('beastCrest') }),
  c('beast.earFin', 'Ear fin size', 'Larger ear fins.', BEAST_HEAD, { bi: true, bodies: ['beast'], region: 'ears', morph: 'ID-EarFin', morphNeg: 'ID-EarFin_Neg', needsLook: notNone('beastEarFin') }),
  c('beast.eye', 'Eye size', 'Larger or smaller eyes.', BEAST_HEAD, { bi: true, bodies: ['beast'], region: 'eyes', morph: 'ID-EyeSize', morphNeg: 'ID-EyeSize_Neg' }),

  c('skin.blush', 'Blush', 'Painted blush on the cheeks.', MAT('Skin'), { tab: 'material', region: 'cheeks', shader: 'blush_strength' }),
  c('skin.veins', 'Veins', 'Vein mask on the forearms and hands.', MAT('Skin'), { tab: 'material', bodies: ADULT, region: 'arms', shader: 'vein_strength' }),
  c('skin.bodyHair', 'Body hair', 'Body hair opacity. Zero hides it.', MAT('Skin'), { tab: 'material', bodies: ADULT, region: 'chest', shader: 'body_hair_opacity' }),
  c('skin.armHair', 'Arm hair', 'Arm hair opacity. Zero hides it.', MAT('Skin'), { tab: 'material', bodies: ADULT, region: 'arms', shader: 'arm_hair_opacity' }),
  c('eye.irisSize', 'Iris size', 'Larger or smaller iris.', MAT('Eyes'), { tab: 'material', bi: true, bodies: ['adult', 'child', 'beast'], region: 'eyes', shader: 'iris_size' }),
  c('eye.pupilSize', 'Pupil size', 'Larger or smaller pupil.', MAT('Eyes'), { tab: 'material', bi: true, bodies: ['adult', 'child', 'beast'], region: 'eyes', shader: 'pupil_size' }),
  c('eye.catchlight', 'Catchlight', 'Strength of the single bright highlight.', MAT('Eyes'), { tab: 'material', bi: true, bodies: ['adult', 'child', 'beast'], region: 'eyes', shader: 'catchlight' }),
  c('robot.emissive', 'Glow strength', 'Brightness of optics and core.', MAT('Paint'), { tab: 'material', bodies: ['robot'], region: 'eyes', shader: 'emissive_strength' }),
];

export const CONTROL_BY_ID: Record<string, ControlDef> = Object.fromEntries(CONTROLS.map((ctl) => [ctl.id, ctl]));

export function controlsFor(kind: BodyKind, tab: 'morphs' | 'material' = 'morphs'): ControlDef[] {
  return CONTROLS.filter((ctl) => ctl.bodies.includes(kind) && ctl.tab === tab);
}

export function controlPath(ctl: ControlDef, kind: BodyKind): string[] {
  return ctl.pathFor?.[kind] ?? ctl.path;
}

export function controlRange(ctl: ControlDef, kind: BodyKind): [number, number] {
  if (kind === 'child' && ctl.childLimit !== undefined) {
    return [Math.max(ctl.min, -ctl.childLimit), Math.min(ctl.max, ctl.childLimit)];
  }
  return [ctl.min, ctl.max];
}

export function isControlVisible(ctl: ControlDef, kind: BodyKind, looks: Record<string, string>): boolean {
  if (!ctl.bodies.includes(kind)) return false;
  if (ctl.needsLook) {
    const look = looks[ctl.needsLook.slot] ?? 'none';
    if (ctl.needsLook.not.includes(look)) return false;
  }
  return true;
}

/** Drag mapping used by viewport region morphing. Front and side views drive different controls. */
export const REGION_DRAG: Partial<Record<Region, { frontX?: string; frontY?: string; sideX?: string; sideY?: string }>> = {
  skull: { frontX: 'skull.width', frontY: 'skull.crown', sideX: 'skull.depth', sideY: 'skull.crown' },
  face: { frontX: 'face.round', frontY: 'face.long', sideX: 'face.softness', sideY: 'face.long' },
  jaw: { frontX: 'jaw.width', frontY: 'chin.length', sideX: 'chin.length', sideY: 'jaw.height' },
  cheeks: { frontX: 'cheek.full', frontY: 'cheek.bone', sideX: 'cheek.full', sideY: 'cheek.bone' },
  eyes: { frontX: 'eye.spacing', frontY: 'eye.height', sideX: 'eye.forward', sideY: 'eye.size' },
  brows: { frontX: 'brow.spacing', frontY: 'brow.height', sideX: 'brow.ridge', sideY: 'brow.height' },
  nose: { frontX: 'nose.tipWidth', frontY: 'nose.length', sideX: 'nose.bridgeHeight', sideY: 'nose.tipUp' },
  mouth: { frontX: 'mouth.width', frontY: 'mouth.height', sideX: 'lip.lower', sideY: 'mouth.height' },
  ears: { frontX: 'ear.out', frontY: 'ear.height', sideX: 'ear.size', sideY: 'ear.height' },
  neck: { frontX: 'neck.thickness', frontY: 'neck.length', sideX: 'neck.thickness', sideY: 'neck.length' },
  shoulders: { frontX: 'body.shoulders', frontY: 'torso.length' },
  chest: { frontX: 'body.chest', frontY: 'torso.length', sideX: 'body.chest', sideY: 'torso.length' },
  waist: { frontX: 'body.waist', frontY: 'torso.length', sideX: 'body.belly', sideY: 'torso.length' },
  hips: { frontX: 'body.hips', frontY: 'thigh.length', sideX: 'body.glute', sideY: 'thigh.length' },
  arms: { frontX: 'upperArm.bulk', frontY: 'upperArm.length', sideX: 'forearm.bulk', sideY: 'forearm.length' },
  hands: { frontX: 'hand.size', frontY: 'finger.length', sideX: 'hand.size', sideY: 'hand.length' },
  legs: { frontX: 'thigh.bulk', frontY: 'shin.length', sideX: 'calf.bulk', sideY: 'thigh.length' },
  feet: { frontX: 'foot.size', frontY: 'foot.length', sideX: 'foot.length', sideY: 'foot.size' },
  body: { frontX: 'body.bulk', frontY: 'body.height', sideX: 'body.soft', sideY: 'body.height' },
  muzzle: { frontX: 'muzzle.width', frontY: 'muzzle.height', sideX: 'muzzle.length', sideY: 'muzzle.bridge' },
  tail: { frontX: 'tail.thickness', frontY: 'tail.length', sideX: 'tail.length', sideY: 'tail.tip' },
  wings: { frontX: 'wing.span', frontY: 'wing.fold', sideX: 'wing.span', sideY: 'wing.fold' },
  horns: { frontX: 'horn.thickness', frontY: 'horn.length', sideX: 'horn.curve', sideY: 'horn.length' },
  mane: { frontX: 'mane.volume', frontY: 'mane.length', sideX: 'mane.volume', sideY: 'mane.length' },
  frill: { frontX: 'frill.size', frontY: 'frill.flare' },
};

export const BEAST_REGION_DRAG: Partial<Record<Region, { frontX?: string; frontY?: string; sideX?: string; sideY?: string }>> = {
  body: { frontX: 'beast.bulk', frontY: 'beast.size', sideX: 'beast.size', sideY: 'beast.leg' },
  neck: { frontY: 'beast.neck', sideX: 'beast.neck', sideY: 'age.posture' },
  tail: { sideX: 'beast.tail', frontY: 'beast.tail' },
  wings: { frontX: 'beast.wing', frontY: 'beast.wingFold', sideX: 'beast.wing', sideY: 'beast.wingFold' },
  legs: { frontY: 'beast.leg', sideY: 'beast.leg' },
  muzzle: { sideX: 'beast.snout', frontX: 'beast.jaw' },
  jaw: { frontX: 'beast.jaw', sideX: 'beast.snout' },
  skull: { frontX: 'beast.head', frontY: 'beast.head', sideX: 'beast.head' },
  horns: { frontY: 'beast.horn', sideX: 'beast.horn' },
  mane: { frontY: 'beast.crest', sideY: 'beast.crest' },
  eyes: { frontX: 'beast.eye', frontY: 'beast.eye' },
  feet: { frontY: 'beast.claw' },
};

export const ROBOT_REGION_DRAG: Partial<Record<Region, { frontX?: string; frontY?: string; sideX?: string; sideY?: string }>> = {
  body: { frontX: 'robot.bulk', frontY: 'body.height', sideX: 'robot.bulk', sideY: 'body.height' },
  chest: { frontX: 'robot.core', frontY: 'torso.length', sideY: 'torso.length' },
  skull: { frontX: 'head.size', frontY: 'head.size', sideX: 'head.size' },
  eyes: { frontX: 'robot.optic', frontY: 'robot.optic' },
  arms: { frontY: 'upperArm.length', sideY: 'forearm.length' },
  legs: { frontY: 'thigh.length', sideY: 'shin.length' },
  neck: { frontY: 'neck.length', sideY: 'neck.length' },
  shoulders: { frontX: 'body.shoulders' },
  hands: { frontY: 'hand.length', frontX: 'hand.size' },
  feet: { frontY: 'foot.length', frontX: 'foot.size' },
};
