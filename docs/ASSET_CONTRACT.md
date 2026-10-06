# Asset contract

What a Blender asset must provide so the creator app can drive it. The app's built-in bodies are placeholders; the library replaces them, so this contract is written from what the app is wired to (`src/model/controls.ts`, `src/model/performance.ts`, `src/model/looks.ts`) and from [CLAUDE_BUILD_PROMPT.md](CLAUDE_BUILD_PROMPT.md). Where the two differ, the app-driven tables below win. The tables are generated: edit the app source, then run `python -m blender.validators app-contract --update docs/ASSET_CONTRACT.md`. Check a model with the `<region>.app.*` findings of `blender/scripts/analyze_regions.py` (see [VALIDATORS.md](VALIDATORS.md)).

## Naming

| Thing | Rule |
| --- | --- |
| Armature | `CHR_Armature` (child `CHR_Armature_Child`, robot `CHR_Armature_Robot`, dragon `CHR_Armature_Dragon`) |
| Body | `CHR_Body`, `CHR_Body_Child`, `CHR_Body_Robot`, `CHR_Body_Dragon` |
| Face parts | `CHR_Eye_L`, `CHR_Eye_R`, `CHR_EyeWet_L/R`, `CHR_Lashes`, `CHR_Brows`, `CHR_TeethUpper` (on the head), `CHR_TeethLower` and `CHR_Tongue` (on the jaw) |
| Deform bones | `DEF-` prefix; sockets `SOC-` prefix; every socket has a `socket_name` custom property equal to its name |
| Shape keys | `ID-` identity, `PF-` performance. Left/right pairs are `_L` / `_R`. The opposite direction of a bidirectional slider is `<Key>_Neg` unless the table names another key. |
| Outline and proxy meshes | `*_outline` hull, `*_line` dark line, `*_shadow` hidden proxy |
| Units and axes | 1 unit = 1 m, forward -Y, up Z, origin at the floor between the feet, transforms applied, relaxed A-pose |

## How a slider drives the model

- **Shape keys** run 0 to 1 from the Basis and rest at 0. The app's sliders run -100 to 100: a positive value sets the slider's key to `value / 100`; a negative value sets its opposite key to `-value / 100`. If the opposite key is missing, the negative half of the slider does nothing (`src/viewport/gltfPacks.ts`).
- **Bone length properties** are armature custom properties, default 1, ranges in the tables. They scale along the bone axis only; corrective shape keys fix the seams at the extremes.
- **Shader parameters** are inputs of the shared node groups (`NG_ToonSkin`, `NG_Eye`, `NG_ToonScale`, `NG_ToonMetal`...), not extra textures.
- **Child** sliders use the narrower range in the table. The child has no adult presentation, muscle, facial hair or age keys (the tables list exactly which keys it has).
- **Elements** (muzzle, ears, horns, mane, frill, tail, wings, hands and feet looks) have a look (a style id) and shape sliders. A shape slider is hidden while its look is `none`, but its keys must still exist.
- Never bake a performance key into identity. The creator stores identity only.

## Sockets (humanoid)

`SOC-HeadTop, SOC-HairScalp, SOC-HairFront, SOC-HairSide_L/R, SOC-HairBack, SOC-HairExtra, SOC-Ear_L/R, SOC-Eyewear, SOC-Moustache, SOC-Beard, SOC-Sideburn_L/R, SOC-Neck, SOC-Chest, SOC-Back, SOC-Shoulder_L/R, SOC-UpperArm_L/R, SOC-ForeArm_L/R, SOC-Hand_L/R, SOC-Waist, SOC-Hip_L/R, SOC-Thigh_L/R, SOC-Shin_L/R, SOC-Foot_L/R, SOC-Cape, SOC-Weapon_L/R, SOC-OrganicForeArm_L`. Robot adds `SOC-Antenna`, `SOC-Core`. Dragon: `SOC-Crest, SOC-Neck, SOC-Back, SOC-Wing_L/R, SOC-Tail, SOC-Shoulder_L/R`. The child has the human sockets without the facial-hair ones.

## Packs

Each pack folder holds the mesh, a glTF export (GLTF_SEPARATE, shape keys start at 0) and `pack.json`:

```json
{ "id": "hair_front_blunt", "display_name": "Blunt fringe", "library": "humanoid", "slot": "hair_front", "socket": "SOC-HairFront" }
```

`library` is `humanoid`, `robot` or `full_beast` and must match the folder tree; `library/manifest.json` lists every pack. No trademarked names in ids or display names. Validate with `python -m blender.validators pack library/` and the Khronos glTF-Validator (`node blender/scripts/validate_gltf.js`).

## Accessory manifest

Stored in the collection's custom properties and mirrored here: `id, display_name, slot, socket, type, hides_body_groups, follows_shape_keys, color_slots, damage_masks`. `type` is `rigid`, `deform`, `replacement`, `prop` or `creature`. A `deform` asset carries the body shape keys of the region it covers under the same names (the keys it follows are listed in `follows_shape_keys`). A `replacement` asset names the body vertex groups it hides. Checked by `clothing.contract_findings`.

## What the app drives

<!-- begin generated: app keys (python -m blender.validators app-contract --update docs/ASSET_CONTRACT.md) -->

### Adult Humanoid

151 shape keys, 21 bone length properties, 9 shader parameters.

| Region | App menu | Control | Shape key (opposite key) | Bone property (range) | Shader parameter | Child range | Shown when | What it does |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| face | Head > Face shape | Round face | `ID-FaceRound` |  |  |  |  | Round face: Fuller, rounder cheeks and jaw |
| face | Head > Face shape | Long face | `ID-FaceLong` |  |  |  |  | Long face: Taller face from brow to chin |
| jaw | Head > Face shape | Square face | `ID-FaceSquare` |  |  |  |  | Square face: Flatter jaw corners and a wider chin |
| face | Head > Face shape | Heart face | `ID-FaceHeart` |  |  |  |  | Heart face: Wide forehead tapering to a small chin |
| cheeks | Head > Face shape | Diamond face | `ID-FaceDiamond` |  |  |  |  | Diamond face: Wide cheekbones, narrow forehead and chin |
| skull | Head > Skull | Head size |  | `head_scale` (0.9-1.15) |  |  |  | Scales the whole head. The neck seam is corrected |
| skull | Head > Skull | Skull width | `ID-SkullWidth` / `ID-SkullWidth_Neg` |  |  |  |  | +: wider or narrower cranium. Drag the skull in front view; -: the reverse of ID-SkullWidth |
| skull | Head > Skull | Skull depth | `ID-SkullDepth` / `ID-SkullDepth_Neg` |  |  |  |  | +: deeper or shallower cranium. Drag the skull in side view; -: the reverse of ID-SkullDepth |
| skull | Head > Skull | Crown height | `ID-SkullCrown` / `ID-SkullCrown_Neg` |  |  |  |  | +: raises or lowers the top of the head; -: the reverse of ID-SkullCrown |
| jaw | Head > Jaw and chin | Jaw width | `ID-JawWidth` / `ID-JawWidth_Neg` |  |  |  |  | +: wider or narrower jaw; -: the reverse of ID-JawWidth |
| jaw | Head > Jaw and chin | Jaw angle height | `ID-JawHeight` / `ID-JawHeight_Neg` |  |  |  |  | +: moves the jaw corners up or down; -: the reverse of ID-JawHeight |
| jaw | Head > Jaw and chin | Chin length | `ID-ChinLength` / `ID-ChinLength_Neg` |  |  |  |  | +: longer or shorter chin; -: the reverse of ID-ChinLength |
| jaw | Head > Jaw and chin | Chin width | `ID-ChinWidth` / `ID-ChinWidth_Neg` |  |  |  |  | +: wider or pointier chin; -: the reverse of ID-ChinWidth |
| jaw | Head > Jaw and chin | Chin cleft | `ID-ChinCleft` |  |  |  |  | Chin cleft: A small dimple in the chin |
| cheeks | Head > Cheeks | Cheek fullness | `ID-CheekFull` / `ID-CheekHollow` |  |  |  |  | +: full cheeks; -: hollow cheeks |
| cheeks | Head > Cheeks | Cheekbones | `ID-Cheekbone` / `ID-Cheekbone_Neg` |  |  |  |  | +: higher, more defined cheekbones; -: the reverse of ID-Cheekbone |
| brows | Head > Brows | Brow ridge | `ID-BrowRidge` / `ID-BrowRidge_Neg` |  |  |  |  | +: heavier or flatter bone above the eyes; -: the reverse of ID-BrowRidge |
| brows | Head > Brows | Brow height |  | `brow_height` (0.85-1.15) |  |  |  | Places the brows higher or lower. Expression brows move from here |
| brows | Head > Brows | Brow tilt |  | `brow_tilt` (0.85-1.15) |  |  |  | Tilts the outer brow up or down |
| brows | Head > Brows | Brow spacing |  | `brow_spacing` (0.85-1.15) |  |  |  | Moves the brows apart or together |
| brows | Head > Brows | Brow thickness | `ID-BrowThick` / `ID-BrowThin` |  |  |  |  | +: thicker or thinner brow strip; -: the reverse of ID-BrowThick |
| brows | Head > Brows | Brow length | `ID-BrowLong` / `ID-BrowShort` |  |  |  |  | +: longer or shorter brow strip; -: the reverse of ID-BrowLong |
| eyes | Head > Eyes | Eye size | `ID-EyeSize` / `ID-EyeSize_Neg` |  |  |  |  | +: larger or smaller eyes; -: the reverse of ID-EyeSize |
| eyes | Head > Eyes | Eye height | `ID-EyeHeight` / `ID-EyeHeight_Neg` |  |  |  |  | +: places the eyes higher or lower on the face; -: the reverse of ID-EyeHeight |
| eyes | Head > Eyes | Eye spacing | `ID-EyeSpacing` / `ID-EyeSpacing_Neg` |  |  |  |  | +: wider or closer set eyes; -: the reverse of ID-EyeSpacing |
| eyes | Head > Eyes | Eye tilt | `ID-EyeTilt` / `ID-EyeTilt_Neg` |  |  |  |  | +: tilts the outer corners up or down; -: the reverse of ID-EyeTilt |
| eyes | Head > Eyes | Almond shape | `ID-EyeAlmond` |  |  |  |  | Almond shape: Pointed corners, curved lids |
| eyes | Head > Eyes | Round shape | `ID-EyeRound` |  |  |  |  | Round shape: A rounder opening |
| eyes | Head > Eyes | Narrow shape | `ID-EyeNarrow` |  |  |  |  | Narrow shape: A slimmer opening |
| eyes | Head > Eyes | Outer corner | `ID-EyeUpturn` / `ID-EyeDroop` |  |  |  |  | +: upturn; -: droop |
| eyes | Head > Eyes | Lid crease | `ID-LidCrease` |  |  |  |  | Lid crease: A visible fold above the eye |
| eyes | Head > Eyes | Hooded lid | `ID-LidHood` |  |  |  |  | Hooded lid: The upper lid sits lower over the eye |
| eyes | Head > Eyes | Lash length | `ID-LashLong` / `ID-LashShort` |  |  |  |  | +: long lashes; -: short lashes |
| nose | Head > Nose | Bridge height | `ID-NoseBridgeHigh` / `ID-NoseBridgeHigh_Neg` |  |  |  |  | +: a higher or flatter nose bridge; -: the reverse of ID-NoseBridgeHigh |
| nose | Head > Nose | Bridge width | `ID-NoseBridgeWide` / `ID-NoseBridgeWide_Neg` |  |  |  |  | +: a wider or narrower bridge; -: the reverse of ID-NoseBridgeWide |
| nose | Head > Nose | Tip lift | `ID-NoseTipUp` / `ID-NoseTipUp_Neg` |  |  |  |  | +: turns the tip up or down; -: the reverse of ID-NoseTipUp |
| nose | Head > Nose | Tip width | `ID-NoseTipWide` / `ID-NoseTipWide_Neg` |  |  |  |  | +: a wider or finer tip; -: the reverse of ID-NoseTipWide |
| nose | Head > Nose | Nose size | `ID-NoseLarge` / `ID-NoseSmall` |  |  |  |  | +: larger; -: smaller |
| nose | Head > Nose | Nose length | `ID-NoseLong` / `ID-NoseLong_Neg` |  |  |  |  | +: longer or shorter nose; -: the reverse of ID-NoseLong |
| nose | Head > Nose | Nostril flare | `ID-NostrilFlare` |  |  |  |  | Nostril flare: Wider nostrils |
| mouth | Head > Mouth | Mouth width | `ID-MouthWidth` / `ID-MouthWidth_Neg` |  |  |  |  | +: wider or narrower mouth; -: the reverse of ID-MouthWidth |
| mouth | Head > Mouth | Mouth height | `ID-MouthHeight` / `ID-MouthHeight_Neg` |  |  |  |  | +: moves the mouth up or down; -: the reverse of ID-MouthHeight |
| mouth | Head > Mouth | Upper lip | `ID-LipUpper` / `ID-LipUpper_Neg` |  |  |  |  | +: fuller or thinner upper lip; -: the reverse of ID-LipUpper |
| mouth | Head > Mouth | Lower lip | `ID-LipLower` / `ID-LipLower_Neg` |  |  |  |  | +: fuller or thinner lower lip; -: the reverse of ID-LipLower |
| mouth | Head > Mouth | Thin lips | `ID-LipThin` |  |  |  |  | Thin lips: Thins both lips together |
| mouth | Head > Mouth | Mouth corners | `ID-CornerUp` / `ID-CornerDown` |  |  |  |  | +: up; -: resting corners down |
| mouth | Head > Mouth | Philtrum | `ID-Philtrum` |  |  |  |  | Philtrum: Deeper groove above the upper lip |
| ears | Head > Ears | Ear size | `ID-EarSize` / `ID-EarSize_Neg` |  |  |  |  | +: larger or smaller human ears; -: the reverse of ID-EarSize |
| ears | Head > Ears | Ear point | `ID-EarPoint` |  |  |  |  | Ear point: Pointed tips on a human ear |
| ears | Head > Ears | Ear angle | `ID-EarOut` |  |  |  |  | Ear angle: Ears stand out from the head |
| ears | Head > Ears | Ear lobe | `ID-EarLobe` |  |  |  |  | Ear lobe: Larger ear lobes |
| ears | Head > Ears | Ear height |  | `ear_height` (0.85-1.15) |  |  |  | Places the ears higher or lower |
| body | Body > Build | Height |  | `height` (0.9-1.1) |  |  |  | Overall height. Proportions stay the same |
| body | Body > Build | Bulk | `ID-BodyBulk` / `ID-BodyLean` |  |  |  |  | +: heavy; -: lean |
| body | Body > Build | Softness | `ID-BodySoft` |  |  |  |  | Softness: Softer, rounder forms |
| waist | Body > Build | Belly | `ID-Belly` / `ID-Belly_Neg` |  |  |  |  | +: a rounder or flatter belly; -: the reverse of ID-Belly |
| hips | Body > Build | Seat | `ID-Glute` / `ID-Glute_Neg` |  |  |  |  | +: fuller or flatter seat; -: the reverse of ID-Glute |
| chest | Body > Muscle | Chest muscle | `ID-MuscleChest` |  |  |  |  | Chest muscle: Definition on the chest |
| waist | Body > Muscle | Abdominal muscle | `ID-MuscleAbs` |  |  |  |  | Abdominal muscle: Definition on the stomach |
| arms | Body > Muscle | Arm muscle | `ID-MuscleArms` |  |  |  |  | Arm muscle: Definition on the arms |
| legs | Body > Muscle | Leg muscle | `ID-MuscleLegs` |  |  |  |  | Leg muscle: Definition on the legs |
| shoulders | Body > Torso | Shoulders | `ID-BroadShoulders` | `shoulder_width` (0.85-1.15) |  |  |  | Shoulders: Wider or narrower shoulders |
| chest | Body > Torso | Chest | `ID-Chest` / `ID-Chest_Neg` |  |  |  |  | +: chest volume; -: the reverse of ID-Chest |
| waist | Body > Torso | Waist | `ID-NarrowWaist` / `ID-NarrowWaist_Neg` |  |  |  |  | +: narrower waist; -: the reverse of ID-NarrowWaist |
| hips | Body > Torso | Hips | `ID-WideHips` | `hip_width` (0.85-1.15) |  |  |  | Hips: Wider or narrower hips |
| face | Presentation | Face softness | `ID-FaceSoft` / `ID-FaceSharp` |  |  |  |  | +: softer; -: sharper |
| chest | Body > Torso | Torso length |  | `torso_length` (0.85-1.15) |  |  |  | Longer or shorter torso |
| arms | Body > Arms and hands | Upper arm length |  | `upper_arm_length` (0.85-1.15) |  |  |  | Longer or shorter upper arms |
| arms | Body > Arms and hands | Forearm length |  | `forearm_length` (0.85-1.15) |  |  |  | Longer or shorter forearms |
| arms | Body > Arms and hands | Upper arm bulk | `ID-UpperArmBulk` / `ID-UpperArmBulk_Neg` |  |  |  |  | +: thicker or thinner upper arms; -: the reverse of ID-UpperArmBulk |
| arms | Body > Arms and hands | Forearm bulk | `ID-ForeArmBulk` / `ID-ForeArmBulk_Neg` |  |  |  |  | +: thicker or thinner forearms; -: the reverse of ID-ForeArmBulk |
| hands | Body > Arms and hands | Hand size | `ID-HandSize` / `ID-HandSize_Neg` |  |  |  |  | +: larger or smaller hands; -: the reverse of ID-HandSize |
| hands | Body > Arms and hands | Hand length |  | `hand_length` (0.85-1.15) |  |  |  | Longer palms |
| hands | Body > Arms and hands | Finger length |  | `finger_length` (0.85-1.15) |  |  |  | Longer or shorter fingers |
| hands | Body > Arms and hands | Nail length | `ID-NailLength` |  |  |  |  | Nail length: Longer fingernails and toenails |
| legs | Body > Legs and feet | Thigh length |  | `thigh_length` (0.85-1.15) |  |  |  | Longer or shorter thighs |
| legs | Body > Legs and feet | Shin length |  | `shin_length` (0.85-1.15) |  |  |  | Longer or shorter shins |
| legs | Body > Legs and feet | Thigh bulk | `ID-ThighBulk` / `ID-ThighBulk_Neg` |  |  |  |  | +: thicker or thinner thighs; -: the reverse of ID-ThighBulk |
| legs | Body > Legs and feet | Calf bulk | `ID-CalfBulk` / `ID-CalfBulk_Neg` |  |  |  |  | +: thicker or thinner calves; -: the reverse of ID-CalfBulk |
| feet | Body > Legs and feet | Foot size | `ID-FootSize` / `ID-FootSize_Neg` |  |  |  |  | +: larger or smaller feet; -: the reverse of ID-FootSize |
| feet | Body > Legs and feet | Foot length |  | `foot_length` (0.85-1.15) |  |  |  | Longer or shorter feet |
| neck | Body > Neck | Neck length |  | `neck_length` (0.85-1.15) |  |  |  | Longer or shorter neck |
| neck | Body > Neck | Neck thickness | `ID-NeckThickness` / `ID-NeckThickness_Neg` |  |  |  |  | +: thicker or thinner neck; -: the reverse of ID-NeckThickness |
| face | Age | Age | `ID-AgeOld` / `ID-AgeYoung` |  |  |  |  | +: old; -: young adult |
| face | Age | Creases | `ID-AgeCreases` |  |  |  |  | Creases: Brow, eye, and mouth creases |
| jaw | Age | Jaw softness | `ID-AgeJawSoft` |  |  |  |  | Jaw softness: A softer jaw line with age |
| body | Age | Stoop |  | `stoop` (0-1) |  |  |  | A mild forward stoop |
| muzzle | Elements > Muzzle or beak | Muzzle length | `ID-MuzzleLength` / `ID-MuzzleLength_Neg` |  |  |  | look: muzzle | +: how far the muzzle or beak reaches; -: the reverse of ID-MuzzleLength |
| muzzle | Elements > Muzzle or beak | Muzzle width | `ID-MuzzleWidth` / `ID-MuzzleWidth_Neg` |  |  |  | look: muzzle | +: wider or narrower muzzle; -: the reverse of ID-MuzzleWidth |
| muzzle | Elements > Muzzle or beak | Muzzle height | `ID-MuzzleHeight` / `ID-MuzzleHeight_Neg` |  |  |  | look: muzzle | +: taller or flatter muzzle; -: the reverse of ID-MuzzleHeight |
| muzzle | Elements > Muzzle or beak | Muzzle bridge | `ID-MuzzleBridge` / `ID-MuzzleBridge_Neg` |  |  |  | look: muzzle | +: a raised or dipped bridge between the eyes and nose; -: the reverse of ID-MuzzleBridge |
| ears | Elements > Ears | Ear size | `ID-EarElSize` / `ID-EarElSize_Neg` |  |  |  | look: ears | +: size of the chosen ear look; -: the reverse of ID-EarElSize |
| ears | Elements > Ears | Ear lift | `ID-EarElLift` / `ID-EarElLift_Neg` |  |  |  | look: ears | +: ears sit higher or droop lower; -: the reverse of ID-EarElLift |
| ears | Elements > Ears | Ear spread | `ID-EarElSpread` / `ID-EarElSpread_Neg` |  |  |  | look: ears | +: ears angle out or lie back; -: the reverse of ID-EarElSpread |
| eyes | Elements > Eyes | Eye placement | `ID-EyeForward` / `ID-EyeForward_Neg` |  |  |  |  | +: eyes sit more to the front or more to the sides; -: the reverse of ID-EyeForward |
| mouth | Elements > Mouth extras | Fang length | `ID-FangLength` |  |  |  | look: fangs | Fang length: Longer fangs |
| muzzle | Elements > Mouth extras | Whisker density |  |  | `whisker_density` |  | look: whiskers | More whiskers on each side |
| mane | Elements > Mane, crest, or feathers | Length | `ID-ManeLength` / `ID-ManeLength_Neg` |  |  |  | look: mane | +: longer mane, crest, or feathers; -: the reverse of ID-ManeLength |
| mane | Elements > Mane, crest, or feathers | Volume | `ID-ManeVolume` / `ID-ManeVolume_Neg` |  |  |  | look: mane | +: fuller mane, crest, or feathers; -: the reverse of ID-ManeVolume |
| horns | Elements > Horns or head fins | Horn length | `ID-HornLength` / `ID-HornLength_Neg` |  |  |  | look: horns | +: longer or shorter horns or head fins; -: the reverse of ID-HornLength |
| horns | Elements > Horns or head fins | Horn thickness | `ID-HornThickness` / `ID-HornThickness_Neg` |  |  |  | look: horns | +: thicker or thinner horns; -: the reverse of ID-HornThickness |
| horns | Elements > Horns or head fins | Horn curve | `ID-HornCurve` / `ID-HornCurve_Neg` |  |  |  | look: horns | +: more curved; -: straighter |
| frill | Elements > Neck frill or gills | Frill size | `ID-FrillSize` / `ID-FrillSize_Neg` |  |  |  | look: frill | +: size of the neck frill or gills; -: the reverse of ID-FrillSize |
| frill | Elements > Neck frill or gills | Frill flare | `ID-FrillFlare` |  |  |  | look: frill | Frill flare: How far the frill opens |
| hands | Elements > Hands and feet | Digit emphasis | `ID-DigitEmphasis` |  |  |  |  | Digit emphasis: Bolder fingers and toes on paws, webs, and talons |
| hands | Elements > Hands and feet | Claw length | `ID-ClawLength` |  |  |  |  | Claw length: Longer claws on paws and talons |
| tail | Elements > Tail | Tail length |  | `tail_length` (0.6-1.5) |  |  | look: tail | Longer or shorter tail |
| tail | Elements > Tail | Tail thickness | `ID-TailThick` / `ID-TailThin` |  |  |  | look: tail | +: thicker or thinner tail; -: the reverse of ID-TailThick |
| tail | Elements > Tail | Tail tip | `ID-TailTip` / `ID-TailTip_Neg` |  |  |  | look: tail | +: a larger tuft, fin, or fan at the tip; -: the reverse of ID-TailTip |
| wings | Elements > Wings | Wing span |  | `wing_span` (0.6-1.4) |  |  | look: wings | Wider or narrower wings |
| wings | Elements > Wings | Wing fold |  | `wing_fold` (0-1) |  |  | look: wings | Open to the left, folded to the right |
| body | Elements > Surface | Coverage |  |  | `surface_coverage` |  | look: surface | Patchy coverage to the left, full coverage with extra tufts to the right |
| cheeks | Material > Skin | Blush |  |  | `blush_strength` |  |  | Painted blush on the cheeks |
| arms | Material > Skin | Veins |  |  | `vein_strength` |  |  | Vein mask on the forearms and hands |
| chest | Material > Skin | Body hair |  |  | `body_hair_opacity` |  |  | Body hair opacity. Zero hides it |
| arms | Material > Skin | Arm hair |  |  | `arm_hair_opacity` |  |  | Arm hair opacity. Zero hides it |
| eyes | Material > Eyes | Iris size |  |  | `iris_size` |  |  | Larger or smaller iris |
| eyes | Material > Eyes | Pupil size |  |  | `pupil_size` |  |  | Larger or smaller pupil |
| eyes | Material > Eyes | Catchlight |  |  | `catchlight` |  |  | Strength of the single bright highlight |

### Child Humanoid

135 shape keys, 20 bone length properties, 6 shader parameters.

| Region | App menu | Control | Shape key (opposite key) | Bone property (range) | Shader parameter | Child range | Shown when | What it does |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| face | Head > Face shape | Round face | `ID-FaceRound` |  |  | 0 to 100 |  | Round face: Fuller, rounder cheeks and jaw |
| face | Head > Face shape | Long face | `ID-FaceLong` |  |  | 0 to 100 |  | Long face: Taller face from brow to chin |
| jaw | Head > Face shape | Square face | `ID-FaceSquare` |  |  | 0 to 100 |  | Square face: Flatter jaw corners and a wider chin |
| face | Head > Face shape | Heart face | `ID-FaceHeart` |  |  | 0 to 100 |  | Heart face: Wide forehead tapering to a small chin |
| cheeks | Head > Face shape | Diamond face | `ID-FaceDiamond` |  |  | 0 to 100 |  | Diamond face: Wide cheekbones, narrow forehead and chin |
| skull | Head > Skull | Head size |  | `head_scale` (0.9-1.15) |  | -60 to 60 |  | Scales the whole head. The neck seam is corrected |
| skull | Head > Skull | Skull width | `ID-SkullWidth` / `ID-SkullWidth_Neg` |  |  | -100 to 100 |  | +: wider or narrower cranium. Drag the skull in front view; -: the reverse of ID-SkullWidth |
| skull | Head > Skull | Skull depth | `ID-SkullDepth` / `ID-SkullDepth_Neg` |  |  | -100 to 100 |  | +: deeper or shallower cranium. Drag the skull in side view; -: the reverse of ID-SkullDepth |
| skull | Head > Skull | Crown height | `ID-SkullCrown` / `ID-SkullCrown_Neg` |  |  | -100 to 100 |  | +: raises or lowers the top of the head; -: the reverse of ID-SkullCrown |
| jaw | Head > Jaw and chin | Jaw width | `ID-JawWidth` / `ID-JawWidth_Neg` |  |  | -100 to 100 |  | +: wider or narrower jaw; -: the reverse of ID-JawWidth |
| jaw | Head > Jaw and chin | Jaw angle height | `ID-JawHeight` / `ID-JawHeight_Neg` |  |  | -100 to 100 |  | +: moves the jaw corners up or down; -: the reverse of ID-JawHeight |
| jaw | Head > Jaw and chin | Chin length | `ID-ChinLength` / `ID-ChinLength_Neg` |  |  | -100 to 100 |  | +: longer or shorter chin; -: the reverse of ID-ChinLength |
| jaw | Head > Jaw and chin | Chin width | `ID-ChinWidth` / `ID-ChinWidth_Neg` |  |  | -100 to 100 |  | +: wider or pointier chin; -: the reverse of ID-ChinWidth |
| cheeks | Head > Cheeks | Cheek fullness | `ID-CheekFull` / `ID-CheekHollow` |  |  | -100 to 100 |  | +: full cheeks; -: hollow cheeks |
| cheeks | Head > Cheeks | Cheekbones | `ID-Cheekbone` / `ID-Cheekbone_Neg` |  |  | -100 to 100 |  | +: higher, more defined cheekbones; -: the reverse of ID-Cheekbone |
| brows | Head > Brows | Brow ridge | `ID-BrowRidge` / `ID-BrowRidge_Neg` |  |  | -100 to 100 |  | +: heavier or flatter bone above the eyes; -: the reverse of ID-BrowRidge |
| brows | Head > Brows | Brow height |  | `brow_height` (0.85-1.15) |  | -100 to 100 |  | Places the brows higher or lower. Expression brows move from here |
| brows | Head > Brows | Brow tilt |  | `brow_tilt` (0.85-1.15) |  | -100 to 100 |  | Tilts the outer brow up or down |
| brows | Head > Brows | Brow spacing |  | `brow_spacing` (0.85-1.15) |  | -100 to 100 |  | Moves the brows apart or together |
| brows | Head > Brows | Brow thickness | `ID-BrowThick` / `ID-BrowThin` |  |  | -100 to 100 |  | +: thicker or thinner brow strip; -: the reverse of ID-BrowThick |
| brows | Head > Brows | Brow length | `ID-BrowLong` / `ID-BrowShort` |  |  | -100 to 100 |  | +: longer or shorter brow strip; -: the reverse of ID-BrowLong |
| eyes | Head > Eyes | Eye size | `ID-EyeSize` / `ID-EyeSize_Neg` |  |  | -100 to 100 |  | +: larger or smaller eyes; -: the reverse of ID-EyeSize |
| eyes | Head > Eyes | Eye height | `ID-EyeHeight` / `ID-EyeHeight_Neg` |  |  | -100 to 100 |  | +: places the eyes higher or lower on the face; -: the reverse of ID-EyeHeight |
| eyes | Head > Eyes | Eye spacing | `ID-EyeSpacing` / `ID-EyeSpacing_Neg` |  |  | -100 to 100 |  | +: wider or closer set eyes; -: the reverse of ID-EyeSpacing |
| eyes | Head > Eyes | Eye tilt | `ID-EyeTilt` / `ID-EyeTilt_Neg` |  |  | -100 to 100 |  | +: tilts the outer corners up or down; -: the reverse of ID-EyeTilt |
| eyes | Head > Eyes | Almond shape | `ID-EyeAlmond` |  |  | 0 to 100 |  | Almond shape: Pointed corners, curved lids |
| eyes | Head > Eyes | Round shape | `ID-EyeRound` |  |  | 0 to 100 |  | Round shape: A rounder opening |
| eyes | Head > Eyes | Narrow shape | `ID-EyeNarrow` |  |  | 0 to 100 |  | Narrow shape: A slimmer opening |
| eyes | Head > Eyes | Outer corner | `ID-EyeUpturn` / `ID-EyeDroop` |  |  | -100 to 100 |  | +: upturn; -: droop |
| eyes | Head > Eyes | Lid crease | `ID-LidCrease` |  |  | 0 to 100 |  | Lid crease: A visible fold above the eye |
| eyes | Head > Eyes | Hooded lid | `ID-LidHood` |  |  | 0 to 100 |  | Hooded lid: The upper lid sits lower over the eye |
| eyes | Head > Eyes | Lash length | `ID-LashLong` / `ID-LashShort` |  |  | -100 to 100 |  | +: long lashes; -: short lashes |
| nose | Head > Nose | Bridge height | `ID-NoseBridgeHigh` / `ID-NoseBridgeHigh_Neg` |  |  | -100 to 100 |  | +: a higher or flatter nose bridge; -: the reverse of ID-NoseBridgeHigh |
| nose | Head > Nose | Bridge width | `ID-NoseBridgeWide` / `ID-NoseBridgeWide_Neg` |  |  | -100 to 100 |  | +: a wider or narrower bridge; -: the reverse of ID-NoseBridgeWide |
| nose | Head > Nose | Tip lift | `ID-NoseTipUp` / `ID-NoseTipUp_Neg` |  |  | -100 to 100 |  | +: turns the tip up or down; -: the reverse of ID-NoseTipUp |
| nose | Head > Nose | Tip width | `ID-NoseTipWide` / `ID-NoseTipWide_Neg` |  |  | -100 to 100 |  | +: a wider or finer tip; -: the reverse of ID-NoseTipWide |
| nose | Head > Nose | Nose size | `ID-NoseLarge` / `ID-NoseSmall` |  |  | -100 to 100 |  | +: larger; -: smaller |
| nose | Head > Nose | Nose length | `ID-NoseLong` / `ID-NoseLong_Neg` |  |  | -100 to 100 |  | +: longer or shorter nose; -: the reverse of ID-NoseLong |
| nose | Head > Nose | Nostril flare | `ID-NostrilFlare` |  |  | 0 to 100 |  | Nostril flare: Wider nostrils |
| mouth | Head > Mouth | Mouth width | `ID-MouthWidth` / `ID-MouthWidth_Neg` |  |  | -100 to 100 |  | +: wider or narrower mouth; -: the reverse of ID-MouthWidth |
| mouth | Head > Mouth | Mouth height | `ID-MouthHeight` / `ID-MouthHeight_Neg` |  |  | -100 to 100 |  | +: moves the mouth up or down; -: the reverse of ID-MouthHeight |
| mouth | Head > Mouth | Upper lip | `ID-LipUpper` / `ID-LipUpper_Neg` |  |  | -100 to 100 |  | +: fuller or thinner upper lip; -: the reverse of ID-LipUpper |
| mouth | Head > Mouth | Lower lip | `ID-LipLower` / `ID-LipLower_Neg` |  |  | -100 to 100 |  | +: fuller or thinner lower lip; -: the reverse of ID-LipLower |
| mouth | Head > Mouth | Thin lips | `ID-LipThin` |  |  | 0 to 100 |  | Thin lips: Thins both lips together |
| mouth | Head > Mouth | Mouth corners | `ID-CornerUp` / `ID-CornerDown` |  |  | -100 to 100 |  | +: up; -: resting corners down |
| mouth | Head > Mouth | Philtrum | `ID-Philtrum` |  |  | 0 to 100 |  | Philtrum: Deeper groove above the upper lip |
| ears | Head > Ears | Ear size | `ID-EarSize` / `ID-EarSize_Neg` |  |  | -100 to 100 |  | +: larger or smaller human ears; -: the reverse of ID-EarSize |
| ears | Head > Ears | Ear point | `ID-EarPoint` |  |  | 0 to 100 |  | Ear point: Pointed tips on a human ear |
| ears | Head > Ears | Ear angle | `ID-EarOut` |  |  | 0 to 100 |  | Ear angle: Ears stand out from the head |
| ears | Head > Ears | Ear lobe | `ID-EarLobe` |  |  | 0 to 100 |  | Ear lobe: Larger ear lobes |
| ears | Head > Ears | Ear height |  | `ear_height` (0.85-1.15) |  | -100 to 100 |  | Places the ears higher or lower |
| body | Body > Build | Height |  | `height` (0.9-1.1) |  | -70 to 70 |  | Overall height. Proportions stay the same |
| body | Body > Build | Bulk | `ID-BodyBulk` / `ID-BodyLean` |  |  | -60 to 60 |  | +: heavy; -: lean |
| body | Body > Build | Softness | `ID-BodySoft` |  |  | 0 to 100 |  | Softness: Softer, rounder forms |
| waist | Body > Build | Belly | `ID-Belly` / `ID-Belly_Neg` |  |  | -50 to 50 |  | +: a rounder or flatter belly; -: the reverse of ID-Belly |
| shoulders | Body > Torso | Shoulders | `ID-BroadShoulders` | `shoulder_width` (0.85-1.15) |  | -50 to 50 |  | Shoulders: Wider or narrower shoulders |
| waist | Body > Torso | Waist | `ID-NarrowWaist` / `ID-NarrowWaist_Neg` |  |  | -40 to 40 |  | +: narrower waist; -: the reverse of ID-NarrowWaist |
| hips | Body > Torso | Hips | `ID-WideHips` | `hip_width` (0.85-1.15) |  | -40 to 40 |  | Hips: Wider or narrower hips |
| chest | Body > Torso | Torso length |  | `torso_length` (0.85-1.15) |  | -60 to 60 |  | Longer or shorter torso |
| arms | Body > Arms and hands | Upper arm length |  | `upper_arm_length` (0.85-1.15) |  | -60 to 60 |  | Longer or shorter upper arms |
| arms | Body > Arms and hands | Forearm length |  | `forearm_length` (0.85-1.15) |  | -60 to 60 |  | Longer or shorter forearms |
| arms | Body > Arms and hands | Upper arm bulk | `ID-UpperArmBulk` / `ID-UpperArmBulk_Neg` |  |  | -50 to 50 |  | +: thicker or thinner upper arms; -: the reverse of ID-UpperArmBulk |
| arms | Body > Arms and hands | Forearm bulk | `ID-ForeArmBulk` / `ID-ForeArmBulk_Neg` |  |  | -50 to 50 |  | +: thicker or thinner forearms; -: the reverse of ID-ForeArmBulk |
| hands | Body > Arms and hands | Hand size | `ID-HandSize` / `ID-HandSize_Neg` |  |  | -50 to 50 |  | +: larger or smaller hands; -: the reverse of ID-HandSize |
| hands | Body > Arms and hands | Hand length |  | `hand_length` (0.85-1.15) |  | -50 to 50 |  | Longer palms |
| hands | Body > Arms and hands | Finger length |  | `finger_length` (0.85-1.15) |  | -50 to 50 |  | Longer or shorter fingers |
| hands | Body > Arms and hands | Nail length | `ID-NailLength` |  |  | -20 to 20 |  | Nail length: Longer fingernails and toenails |
| legs | Body > Legs and feet | Thigh length |  | `thigh_length` (0.85-1.15) |  | -60 to 60 |  | Longer or shorter thighs |
| legs | Body > Legs and feet | Shin length |  | `shin_length` (0.85-1.15) |  | -60 to 60 |  | Longer or shorter shins |
| legs | Body > Legs and feet | Thigh bulk | `ID-ThighBulk` / `ID-ThighBulk_Neg` |  |  | -50 to 50 |  | +: thicker or thinner thighs; -: the reverse of ID-ThighBulk |
| legs | Body > Legs and feet | Calf bulk | `ID-CalfBulk` / `ID-CalfBulk_Neg` |  |  | -50 to 50 |  | +: thicker or thinner calves; -: the reverse of ID-CalfBulk |
| feet | Body > Legs and feet | Foot size | `ID-FootSize` / `ID-FootSize_Neg` |  |  | -50 to 50 |  | +: larger or smaller feet; -: the reverse of ID-FootSize |
| feet | Body > Legs and feet | Foot length |  | `foot_length` (0.85-1.15) |  | -50 to 50 |  | Longer or shorter feet |
| neck | Body > Neck | Neck length |  | `neck_length` (0.85-1.15) |  | -60 to 60 |  | Longer or shorter neck |
| neck | Body > Neck | Neck thickness | `ID-NeckThickness` / `ID-NeckThickness_Neg` |  |  | -50 to 50 |  | +: thicker or thinner neck; -: the reverse of ID-NeckThickness |
| muzzle | Elements > Muzzle or beak | Muzzle length | `ID-MuzzleLength` / `ID-MuzzleLength_Neg` |  |  | -100 to 100 | look: muzzle | +: how far the muzzle or beak reaches; -: the reverse of ID-MuzzleLength |
| muzzle | Elements > Muzzle or beak | Muzzle width | `ID-MuzzleWidth` / `ID-MuzzleWidth_Neg` |  |  | -100 to 100 | look: muzzle | +: wider or narrower muzzle; -: the reverse of ID-MuzzleWidth |
| muzzle | Elements > Muzzle or beak | Muzzle height | `ID-MuzzleHeight` / `ID-MuzzleHeight_Neg` |  |  | -100 to 100 | look: muzzle | +: taller or flatter muzzle; -: the reverse of ID-MuzzleHeight |
| muzzle | Elements > Muzzle or beak | Muzzle bridge | `ID-MuzzleBridge` / `ID-MuzzleBridge_Neg` |  |  | -100 to 100 | look: muzzle | +: a raised or dipped bridge between the eyes and nose; -: the reverse of ID-MuzzleBridge |
| ears | Elements > Ears | Ear size | `ID-EarElSize` / `ID-EarElSize_Neg` |  |  | -100 to 100 | look: ears | +: size of the chosen ear look; -: the reverse of ID-EarElSize |
| ears | Elements > Ears | Ear lift | `ID-EarElLift` / `ID-EarElLift_Neg` |  |  | -100 to 100 | look: ears | +: ears sit higher or droop lower; -: the reverse of ID-EarElLift |
| ears | Elements > Ears | Ear spread | `ID-EarElSpread` / `ID-EarElSpread_Neg` |  |  | -100 to 100 | look: ears | +: ears angle out or lie back; -: the reverse of ID-EarElSpread |
| eyes | Elements > Eyes | Eye placement | `ID-EyeForward` / `ID-EyeForward_Neg` |  |  | -100 to 100 |  | +: eyes sit more to the front or more to the sides; -: the reverse of ID-EyeForward |
| mouth | Elements > Mouth extras | Fang length | `ID-FangLength` |  |  | 0 to 100 | look: fangs | Fang length: Longer fangs |
| muzzle | Elements > Mouth extras | Whisker density |  |  | `whisker_density` | 0 to 100 | look: whiskers | More whiskers on each side |
| mane | Elements > Mane, crest, or feathers | Length | `ID-ManeLength` / `ID-ManeLength_Neg` |  |  | -100 to 100 | look: mane | +: longer mane, crest, or feathers; -: the reverse of ID-ManeLength |
| mane | Elements > Mane, crest, or feathers | Volume | `ID-ManeVolume` / `ID-ManeVolume_Neg` |  |  | -100 to 100 | look: mane | +: fuller mane, crest, or feathers; -: the reverse of ID-ManeVolume |
| horns | Elements > Horns or head fins | Horn length | `ID-HornLength` / `ID-HornLength_Neg` |  |  | -100 to 100 | look: horns | +: longer or shorter horns or head fins; -: the reverse of ID-HornLength |
| horns | Elements > Horns or head fins | Horn thickness | `ID-HornThickness` / `ID-HornThickness_Neg` |  |  | -100 to 100 | look: horns | +: thicker or thinner horns; -: the reverse of ID-HornThickness |
| horns | Elements > Horns or head fins | Horn curve | `ID-HornCurve` / `ID-HornCurve_Neg` |  |  | -100 to 100 | look: horns | +: more curved; -: straighter |
| frill | Elements > Neck frill or gills | Frill size | `ID-FrillSize` / `ID-FrillSize_Neg` |  |  | -100 to 100 | look: frill | +: size of the neck frill or gills; -: the reverse of ID-FrillSize |
| frill | Elements > Neck frill or gills | Frill flare | `ID-FrillFlare` |  |  | 0 to 100 | look: frill | Frill flare: How far the frill opens |
| hands | Elements > Hands and feet | Digit emphasis | `ID-DigitEmphasis` |  |  | 0 to 100 |  | Digit emphasis: Bolder fingers and toes on paws, webs, and talons |
| hands | Elements > Hands and feet | Claw length | `ID-ClawLength` |  |  | 0 to 100 |  | Claw length: Longer claws on paws and talons |
| tail | Elements > Tail | Tail length |  | `tail_length` (0.6-1.5) |  | -100 to 100 | look: tail | Longer or shorter tail |
| tail | Elements > Tail | Tail thickness | `ID-TailThick` / `ID-TailThin` |  |  | -100 to 100 | look: tail | +: thicker or thinner tail; -: the reverse of ID-TailThick |
| tail | Elements > Tail | Tail tip | `ID-TailTip` / `ID-TailTip_Neg` |  |  | -100 to 100 | look: tail | +: a larger tuft, fin, or fan at the tip; -: the reverse of ID-TailTip |
| wings | Elements > Wings | Wing span |  | `wing_span` (0.6-1.4) |  | -100 to 100 | look: wings | Wider or narrower wings |
| wings | Elements > Wings | Wing fold |  | `wing_fold` (0-1) |  | -100 to 100 | look: wings | Open to the left, folded to the right |
| body | Elements > Surface | Coverage |  |  | `surface_coverage` | -100 to 100 | look: surface | Patchy coverage to the left, full coverage with extra tufts to the right |
| cheeks | Material > Skin | Blush |  |  | `blush_strength` | 0 to 100 |  | Painted blush on the cheeks |
| eyes | Material > Eyes | Iris size |  |  | `iris_size` | -100 to 100 |  | Larger or smaller iris |
| eyes | Material > Eyes | Pupil size |  |  | `pupil_size` | -100 to 100 |  | Larger or smaller pupil |
| eyes | Material > Eyes | Catchlight |  |  | `catchlight` | -100 to 100 |  | Strength of the single bright highlight |

### Robot

15 shape keys, 11 bone length properties, 3 shader parameters.

| Region | App menu | Control | Shape key (opposite key) | Bone property (range) | Shader parameter | Child range | Shown when | What it does |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| skull | Head > Skull | Head size |  | `head_scale` (0.9-1.15) |  |  |  | Scales the whole head. The neck seam is corrected |
| body | Body > Build | Height |  | `height` (0.9-1.1) |  |  |  | Overall height. Proportions stay the same |
| shoulders | Body > Torso | Shoulders | `ID-BroadShoulders` | `shoulder_width` (0.85-1.15) |  |  |  | Shoulders: Wider or narrower shoulders |
| chest | Body > Torso | Torso length |  | `torso_length` (0.85-1.15) |  |  |  | Longer or shorter torso |
| arms | Body > Arms and hands | Upper arm length |  | `upper_arm_length` (0.85-1.15) |  |  |  | Longer or shorter upper arms |
| arms | Body > Arms and hands | Forearm length |  | `forearm_length` (0.85-1.15) |  |  |  | Longer or shorter forearms |
| hands | Body > Arms and hands | Hand size | `ID-HandSize` / `ID-HandSize_Neg` |  |  |  |  | +: larger or smaller hands; -: the reverse of ID-HandSize |
| hands | Body > Arms and hands | Hand length |  | `hand_length` (0.85-1.15) |  |  |  | Longer palms |
| legs | Body > Legs and feet | Thigh length |  | `thigh_length` (0.85-1.15) |  |  |  | Longer or shorter thighs |
| legs | Body > Legs and feet | Shin length |  | `shin_length` (0.85-1.15) |  |  |  | Longer or shorter shins |
| feet | Body > Legs and feet | Foot size | `ID-FootSize` / `ID-FootSize_Neg` |  |  |  |  | +: larger or smaller feet; -: the reverse of ID-FootSize |
| feet | Body > Legs and feet | Foot length |  | `foot_length` (0.85-1.15) |  |  |  | Longer or shorter feet |
| neck | Body > Neck | Neck length |  | `neck_length` (0.85-1.15) |  |  |  | Longer or shorter neck |
| neck | Body > Neck | Neck thickness | `ID-NeckThickness` / `ID-NeckThickness_Neg` |  |  |  |  | +: thicker or thinner neck; -: the reverse of ID-NeckThickness |
| body | Chassis | Chassis bulk | `ID-ChassisBulk` / `ID-ChassisBulk_Neg` |  |  |  |  | +: heavy frame; -: slim frame |
| chest | Chassis | Chest core | `ID-ChestCore` / `ID-ChestCore_Neg` |  |  |  |  | +: size of the glowing chest core; -: the reverse of ID-ChestCore |
| body | Chassis | Panel gap |  |  | `panel_gap` |  |  | Wider gaps between plates |
| body | Chassis | Paint wear |  |  | `paint_wear` |  |  | Chipped paint on edges |
| eyes | Optics and head | Optic size | `ID-OpticSize` / `ID-OpticSize_Neg` |  |  |  |  | +: larger or smaller lens eyes; -: the reverse of ID-OpticSize |
| skull | Optics and head | Antenna length | `ID-AntennaLength` / `ID-AntennaLength_Neg` |  |  |  | look: antenna | +: longer antenna; -: the reverse of ID-AntennaLength |
| eyes | Material > Paint | Glow strength |  |  | `emissive_strength` |  |  | Brightness of optics and core |

### Quadruped Dragon

17 shape keys, 8 bone length properties, 4 shader parameters.

| Region | App menu | Control | Shape key (opposite key) | Bone property (range) | Shader parameter | Child range | Shown when | What it does |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| face | Age | Age | `ID-AgeOld` / `ID-AgeYoung` |  |  |  |  | +: old; -: young adult |
| body | Age | Scale wear |  |  | `scale_wear` |  |  | Worn, chipped scale edges |
| neck | Age | Low posture |  | `posture` (0-1) |  |  |  | Lower head and shoulders with age |
| body | Beast body | Body size |  | `body_size` (0.6-1.4) |  |  |  | Overall size of the dragon |
| neck | Beast body | Neck length |  | `neck_length` (0.7-1.4) |  |  |  | Longer or shorter neck |
| tail | Beast body | Tail length |  | `tail_length` (0.7-1.4) |  |  |  | Longer or shorter tail |
| wings | Beast body | Wing size |  | `wing_size` (0.7-1.4) |  |  |  | Larger or smaller wings |
| wings | Beast body | Wing fold |  | `wing_fold` (0-1) |  |  |  | Open to the left, folded to the right |
| legs | Beast body | Leg length |  | `leg_length` (0.8-1.25) |  |  |  | Longer or shorter legs |
| body | Beast body | Bulk | `ID-BeastBulk` / `ID-BeastLean` |  |  |  |  | +: leaner or heavier body; -: the reverse of ID-BeastBulk |
| feet | Beast body | Claw length | `ID-ClawLength` |  |  |  |  | Claw length: Longer claws |
| muzzle | Beast head | Snout length | `ID-SnoutLong` / `ID-SnoutShort` |  |  |  |  | +: long snout; -: short snout |
| jaw | Beast head | Jaw width | `ID-JawWidth` / `ID-JawWidth_Neg` |  |  |  |  | +: wider or narrower jaw; -: the reverse of ID-JawWidth |
| skull | Beast head | Head size |  | `head_scale` (0.85-1.2) |  |  |  | Larger or smaller head |
| horns | Beast head | Horn size | `ID-HornStyleSize` / `ID-HornStyleSize_Neg` |  |  |  | look: beastHorns | +: longer, heavier horns; -: the reverse of ID-HornStyleSize |
| mane | Beast head | Crest size | `ID-Crest` / `ID-Crest_Neg` |  |  |  | look: beastCrest | +: taller crest; -: the reverse of ID-Crest |
| ears | Beast head | Ear fin size | `ID-EarFin` / `ID-EarFin_Neg` |  |  |  | look: beastEarFin | +: larger ear fins; -: the reverse of ID-EarFin |
| eyes | Beast head | Eye size | `ID-EyeSize` / `ID-EyeSize_Neg` |  |  |  |  | +: larger or smaller eyes; -: the reverse of ID-EyeSize |
| eyes | Material > Eyes | Iris size |  |  | `iris_size` |  |  | Larger or smaller iris |
| eyes | Material > Eyes | Pupil size |  |  | `pupil_size` |  |  | Larger or smaller pupil |
| eyes | Material > Eyes | Catchlight |  |  | `catchlight` |  |  | Strength of the single bright highlight |

### Conflicts to resolve in the app

The build prompt forbids these adult body-shape keys on the child body (the child is a clothed, general-audience species). The app still wires them to a child control, so a child library built to the prompt leaves that control without a key: `ID-WideHips` (control `body.hips`). Recommended fix: show the control on the adult only, or drive the child's hip width with the `hip_width` bone property alone. The contract keeps the prompt's rule.

### Performance keys

| Group | Key | What it does |
| --- | --- | --- |
| Eyes | `PF-Blink_L` | Blink left (eyes) |
| Eyes | `PF-Blink_R` | Blink right (eyes) |
| Eyes | `PF-EyeWide_L` | Wide left (eyes) |
| Eyes | `PF-EyeWide_R` | Wide right (eyes) |
| Eyes | `PF-Squint_L` | Squint left (eyes) |
| Eyes | `PF-Squint_R` | Squint right (eyes) |
| Eyes | `PF-LidUpperDown_L` | Upper lid down left (eyes) |
| Eyes | `PF-LidUpperDown_R` | Upper lid down right (eyes) |
| Eyes | `PF-LidLowerUp_L` | Lower lid up left (eyes) |
| Eyes | `PF-LidLowerUp_R` | Lower lid up right (eyes) |
| Eyes | `PF-Squeeze_L` | Squeeze left (eyes) |
| Eyes | `PF-Squeeze_R` | Squeeze right (eyes) |
| Brows | `PF-BrowRaise_L` | Brow raise left (brows) |
| Brows | `PF-BrowRaise_R` | Brow raise right (brows) |
| Brows | `PF-BrowInnerUp_L` | Inner brow up left (brows) |
| Brows | `PF-BrowInnerUp_R` | Inner brow up right (brows) |
| Brows | `PF-BrowOuterUp_L` | Outer brow up left (brows) |
| Brows | `PF-BrowOuterUp_R` | Outer brow up right (brows) |
| Brows | `PF-BrowLower_L` | Brow lower left (brows) |
| Brows | `PF-BrowLower_R` | Brow lower right (brows) |
| Brows | `PF-BrowFurrow_L` | Brow furrow left (brows) |
| Brows | `PF-BrowFurrow_R` | Brow furrow right (brows) |
| Brows | `PF-BrowSad_L` | Sad brow left (brows) |
| Brows | `PF-BrowSad_R` | Sad brow right (brows) |
| Jaw | `PF-JawOpen` | Jaw open (mouth) |
| Visemes | `PF-VisMBP` | Closed lips (M, B, P) (mouth) |
| Visemes | `PF-VisSmall` | Small opening (mouth) |
| Visemes | `PF-VisMid` | Mid opening (mouth) |
| Visemes | `PF-VisAA` | A (mouth) |
| Visemes | `PF-VisEE` | E (mouth) |
| Visemes | `PF-VisIH` | I (mouth) |
| Visemes | `PF-VisOH` | O (mouth) |
| Visemes | `PF-VisOO` | U (mouth) |
| Visemes | `PF-VisFV` | F and V (mouth) |
| Visemes | `PF-VisL` | L (mouth) |
| Visemes | `PF-VisTH` | Th (mouth) |
| Visemes | `PF-VisSZ` | S and Z (mouth) |
| Visemes | `PF-VisWide` | Shout (mouth) |
| Emotions | `PF-SmileClosed` | Closed smile (mouth) |
| Emotions | `PF-SmileOpenJaw` | Open smile (mouth) |
| Emotions | `PF-Smirk_L` | Smirk left (mouth) |
| Emotions | `PF-Smirk_R` | Smirk right (mouth) |
| Emotions | `PF-Frown` | Frown (mouth) |
| Emotions | `PF-FrownOpen` | Open frown (mouth) |
| Emotions | `PF-Pout` | Pout (mouth) |
| Emotions | `PF-Press` | Press lips (mouth) |
| Emotions | `PF-LipBite` | Lip bite (mouth) |
| Emotions | `PF-Grimace` | Grimace (mouth) |
| Emotions | `PF-Snarl` | Snarl (mouth) |
| Emotions | `PF-Disgust` | Disgust (mouth) |
| Emotions | `PF-Surprise` | Surprise (mouth) |
| Emotions | `PF-Cry` | Cry (mouth) |
| Emotions | `PF-MouthSide_L` | Mouth shift left (mouth) |
| Emotions | `PF-MouthSide_R` | Mouth shift right (mouth) |
| Tongue | `PF-TongueL` | Tongue up (L) (mouth) |
| Tongue | `PF-TongueTh` | Tongue forward (Th) (mouth) |
| Tongue | `PF-TongueRest` | Tongue visible at rest (mouth) |

<!-- end generated: app keys -->
