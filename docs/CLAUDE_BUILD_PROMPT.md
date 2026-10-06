# Asset library prompt

Copy everything below the line into Claude when you are ready to build the meshes in Blender. Also give Claude the `docs/style_dataset/` folder. This prompt builds the library only. It does not build the creator application.

---
MANDATORY READING
Read docs/anatomy-manual.md in full before modeling any body, element, or preset, and run its checklists at every phase gate.
Read docs/shading-style-guide.md in full before authoring any material, texture, outline, or shader node group, and follow its Blender asset contract. Its working prompt requires reading the entire EEVEE manual first. Where that guide and this prompt disagree about shading, lines, highlights, or materials, the guide wins.

You are building the asset library only, inside Blender. Do not build the standalone application, its windows, or its importer. Another project builds that software and imports the folders you create. Work in the existing project folder. Read docs/style_dataset/README.md, docs/style_dataset/entries.json, and the images named there. Treat that dataset as an additional reference. Keep using online references and your own knowledge as well. Use Blenderâ€™s Python API for the rig, drivers, and materials. Use Edit Mode and Sculpt Mode for forms. Save the .blend after every phase. Do not start the next phase until the current phase gate passes. If a gate fails, fix that phase before adding anything new.

LIBRARY FOLDERS
Write every finished pack into library/ using the folders named in the project contract. Human and human-beast assets go under library/humanoid/. The robot goes under library/robot/. The quadruped dragon goes under library/full_beast/. Do not place a full-beast or robot file inside humanoid, or a humanoid file inside the other two. Each pack folder gets the mesh plus pack.json with id, display_name, library, slot, and socket. Update library/manifest.json every time you add a pack. Export a glTF next to the Blender source so the software can import without opening Blender.

GOAL
Create the asset library that a separate character-creator application will import. Author the meshes in Blender and export them into the library folders. Do not build that application. Body kinds: adult humanoid, child humanoid, robot humanoid, and a winged quadruped dragon. Adult and child humanoids cover a human and these humanoid creatures: tiger, lion, fish, dog, dragon, bird, frog, serpent, rabbit, dinosaur, rhino, and lizard. Each creature feature is an element with a look choice and shape sliders. Feminine and masculine are adult presentation presets plus live sliders, for the human and every humanoid creature. Young adult, adult, and old are a second set of presets on every adult human, every human-beast mix, and the full beast. They stack with presentation and with mixed elements. Each adult archetype also has a clothed child counterpart. The child body does not have the adult age presets. The art style is anime. The base is Monster Hunter Stories 3: painted skin, glossy eyes with one catchlight, hair as thick clumps with one highlight band, layered cloth leather metal and fur, and creatures made of large scale plates, spines, and ribbed wing membranes. A shader preset named Breath shifts toward Breath of Fire 3 and 4: brighter painted color and cleaner illustration edges, especially on beast people and dragon people. A shader preset named Legends shifts toward Mega Man Legends 2 and 3: cleaner cel bands and chunkier painted metal, especially on robots and wearable robot armor. Stories is the default. Do not copy the people, monsters, costumes, emblems, or machines from any of those games. Shadow falls in soft bands, with real light falloff, a rim light, and a thin outline. Adult proportion target is about 7 to 7.5 heads tall. The child is about 5 to 5.5 heads tall and must read as a child, not as a scaled adult. The robot is a segmented machine, not a metal-shaded human. The quadruped dragon is four-legged, winged, and tailed, with a talking muzzle, default shoulder height about 1.6 to 2.2 meters. The humanoid dragon person is not that quadruped. Avoid photoreal pores and avoid copying the chibi proportions of older Story games for the adult.

COPYRIGHT
Do not copy or trace commercial game characters, monsters, weapons, armor sets, logos, UI, or textures. Do not use trademarked names in asset names. Style similarity is the target. Asset identity must be original.

PRODUCT
You are authoring the asset library in Blender. Do not build the standalone application. Keep glTF export in mind: prefer bones, shape keys, and packed images over Blender-only modifiers in the final result. A Surface Deform modifier is allowed only as a sculpt helper and must be applied or baked into shape keys before a phase is done.

TWO CONTROL LAYERS
Identity is stored on the armature and describes the person: shape, lengths, colors, hair, facial hair, surface detail, equipped accessories.
Performance describes motion and stacks on identity: gaze, blink, brows, visemes, emotions.
Never bake performance into the identity preset. The creator writes identity. The expression preview writes performance, then can reset performance to neutral without losing identity.

PROJECT LAYOUT
Create this structure:
- blender/character_maker/  the addon package
- blender/character_maker/__init__.py
- blender/character_maker/properties.py
- blender/character_maker/operators.py
- blender/character_maker/ui.py
- blender/character_maker/drivers.py
- blender/character_maker/presets/
- blender/assets/character_adult.blend
- blender/assets/character_child.blend
- blender/assets/character_robot.blend
- blender/assets/character_dragon.blend
- blender/assets/accessories/  one .blend or collection per exemplar
- blender/assets/textures/
- docs/ASSET_CONTRACT.md  sockets, shape-key names, shader inputs, manifest fields, which keys exist per species

The adult file contains the adult body, rig, eyes, brows, lashes, teeth, tongue, sockets, and the shader node groups. Build that file through Phase 9 before opening the child, robot, or dragon files. Those later files instance or append the same node groups. They do not invent a second shader look.

MESH RULES
Quads on the face and joints. Edge loops around the eyes, mouth, and major joints so shape keys deform cleanly. Separate material zones, or clearly named vertex groups, for skin, lips, nails, and eye moisture. Poly budget for the nude base body: 18k to 28k triangles. Put density in the face, hands, and joints. Hair, facial hair, and accessories are extra objects.
Default pose: relaxed A-pose, palms inward, fingers slightly curled. Origin at the floor between the feet. Forward is -Y, up is Z. Scale is 1 Blender unit = 1 meter. Apply transforms on the base mesh.

NAMING
Armature object: CHR_Armature
Body object: CHR_Body
Eyeballs: CHR_Eye_L, CHR_Eye_R
Moisture: CHR_EyeWet_L, CHR_EyeWet_R
Lashes: CHR_Lashes
Brows: CHR_Brows
Upper teeth parented to the head: CHR_TeethUpper
Lower teeth parented to the jaw: CHR_TeethLower
Tongue parented to the jaw: CHR_Tongue
All deform bones and sockets use the prefixes DEF- and SOC-
Shape keys use the prefixes ID- for identity and PF- for performance.
Left and right shape keys that must be asymmetric get _L and _R. A combined key may drive both for symmetric edits.

SOCKETS
Empty or bone sockets, zeroed in the default pose, parented to the deform bone that should carry them:
SOC-HeadTop, SOC-HairScalp, SOC-HairFront, SOC-HairSide_L, SOC-HairSide_R, SOC-HairBack, SOC-HairExtra, SOC-Ear_L, SOC-Ear_R, SOC-Eyewear,
SOC-Moustache, SOC-Beard, SOC-Sideburn_L, SOC-Sideburn_R, SOC-Neck, SOC-Chest,
SOC-Back, SOC-Shoulder_L, SOC-Shoulder_R, SOC-UpperArm_L, SOC-UpperArm_R,
SOC-ForeArm_L, SOC-ForeArm_R, SOC-Hand_L, SOC-Hand_R, SOC-Waist, SOC-Hip_L,
SOC-Hip_R, SOC-Thigh_L, SOC-Thigh_R, SOC-Shin_L, SOC-Shin_R, SOC-Foot_L,
SOC-Foot_R, SOC-Cape, SOC-Weapon_L, SOC-Weapon_R, SOC-OrganicForeArm_L
Each socket has a custom property socket_name matching its object name.

IDENTITY BODY
Shape keys on CHR_Body, each a clean extreme from the Basis, slider 0 to 1 unless noted:
ID-BodyBulk, ID-BodyLean, ID-BodySoft, ID-NarrowWaist, ID-WideHips, ID-BroadShoulders,
ID-Chest, ID-Belly, ID-Glute, ID-ThighBulk, ID-CalfBulk, ID-UpperArmBulk, ID-ForeArmBulk,
ID-MuscleChest, ID-MuscleAbs, ID-MuscleArms, ID-MuscleLegs,
ID-NeckThickness, ID-HandSize, ID-FootSize, ID-NailLength
Muscle keys add definition and separation. Bulk keys add volume. They must be usable together.
Nail length moves nail geometry on fingers and toes.

Length and size are bone controls, exposed as armature custom properties from 0.85 to 1.15 unless noted, default 1:
head_scale 0.9 to 1.15
neck_length
torso_length
shoulder_width
hip_width
upper_arm_length, forearm_length, thigh_length, shin_length
hand_length, finger_length, foot_length
Scale only along the bone axis. Add corrective shape keys, driven by those properties, for the neck seam, shoulder, elbow, wrist, hip, knee, and ankle at the extreme values so the silhouette stays smooth. Head scale includes a neck corrective so the head does not float or sink into the collar.

IDENTITY FACE
Shape keys:
ID-FaceRound, ID-FaceLong, ID-FaceSquare, ID-FaceHeart, ID-FaceDiamond
ID-JawWidth, ID-JawHeight, ID-ChinLength, ID-ChinWidth, ID-ChinCleft
ID-CheekFull, ID-CheekHollow, ID-Cheekbone
ID-BrowRidge
ID-EarSize, ID-EarPoint, ID-EarOut, ID-EarLobe
ID-NoseBridgeHigh, ID-NoseBridgeWide, ID-NoseTipUp, ID-NoseTipWide, ID-NoseSmall, ID-NoseLong, ID-NostrilFlare
ID-EyeSize, ID-EyeHeight, ID-EyeSpacing, ID-EyeTilt, ID-EyeAlmond, ID-EyeRound, ID-EyeNarrow, ID-EyeDroop, ID-EyeUpturn
ID-LidCrease, ID-LidHood
ID-MouthWidth, ID-MouthHeight, ID-LipUpper, ID-LipLower, ID-LipThin, ID-CornerUp, ID-CornerDown, ID-Philtrum
Placement bones, separate from emotion: brow height, brow tilt, brow spacing, eye height already covered by shape keys if that is cleaner, ear position. Pick one method per feature and document it in ASSET_CONTRACT.md. Do not leave two competing controls for the same idea.

Eyebrows are a mesh, CHR_Brows, with enough geometry to bend. Eyelashes are a mesh, CHR_Lashes, that deforms with the lids. Include three lash length variants as shape keys: ID-LashShort, ID-LashDefault, ID-LashLong. Eyes are spheres or slight ovals with a shader iris. Iris size and pupil size are shader parameters. Eye color, sclera tint, and catchlight strength are shader parameters.

IDENTITY SURFACE
Shader parameters, not extra textures per color:
skin_color, lip_color, nail_color, blush_strength, vein_strength, body_hair_opacity, arm_hair_opacity
Veins are a mask in the skin shader, stronger on forearms and hands. Body hair and arm hair are card meshes or a masked shell with low opacity, driven by those parameters, groomed to match the toon style. They must be toggleable to zero.

PERFORMANCE EYES
Bones: eye aim with independent left and right rotation, plus a convergence control. Driving the upper lid slightly when looking up and the upper lid down when looking down is required.
Shape keys, left and right separate, 0 to 1:
PF-Blink_L, PF-Blink_R  with the deformation checked at 0.25, 0.5, 0.75, and 1
PF-EyeWide_L, PF-EyeWide_R
PF-Squint_L, PF-Squint_R
PF-LidUpperDown_L, PF-LidUpperDown_R
PF-LidLowerUp_L, PF-LidLowerUp_R
PF-Squeeze_L, PF-Squeeze_R
Lashes follow the blink and squint keys. Author a blink action: open, fast to 0.55, closed, brief squeeze, then a slower open. A wink uses only one side.

PERFORMANCE BROWS
Per side, on CHR_Brows:
PF-BrowRaise, PF-BrowInnerUp, PF-BrowOuterUp, PF-BrowLower, PF-BrowFurrow, PF-BrowSad
Test 0.25, 0.5, and 0.75. If the midpoint collapses, add a corrective key and drive it from the main key. These keys are offsets on top of the identity brow placement.

PERFORMANCE MOUTH
Jaw bone PF-JawOpen driven 0 to 1, with a corrective shape key at fully open so the lips and cheeks stay appealing.
Viseme shape keys, able to overlap at partial values:
PF-VisMBP closed lips
PF-VisSmall the small opening used between closed and vowels
PF-VisMid
PF-VisAA
PF-VisEE
PF-VisIH
PF-VisOH
PF-VisOO
PF-VisFV
PF-VisL
PF-VisTH
PF-VisSZ
PF-VisWide shout
Emotion keys, additive, and each must be tested with the jaw at 0 and at 0.6:
PF-SmileClosed, PF-SmileOpenJaw corrective, PF-Smirk_L, PF-Smirk_R, PF-Frown, PF-FrownOpen,
PF-Pout, PF-Press, PF-LipBite, PF-Grimace, PF-Snarl, PF-Disgust, PF-Surprise, PF-Cry, PF-MouthSide_L, PF-MouthSide_R
Tongue keys for L, Th, and a visible open-mouth rest. Upper teeth stay on the head. Lower teeth and tongue follow the jaw.
Build a talking action at 24 fps, about 48 frames, that passes through MBP, Small, Mid, AA, Mid, EE, Small, OH, Small, MBP. No two-frame open and close flap.
Build a pose library on the armature with these performance presets, identity left untouched: Neutral, SoftSmile, Happy, Laugh, Sad, Cry, Angry, Shout, Surprised, Skeptical, Sleepy, Focused, Disgusted.

HAIR AND FACIAL HAIR
Separate card meshes on NG_ToonHair. Build them as thick clumps with one soft highlight band, not as fine strands. Short styles need a messy crown and a few upward tufts. Braids are a rope of cards. They are not part of the body. Sockets: SOC-HairScalp, SOC-HairFront, SOC-HairSide_L, SOC-HairSide_R, SOC-HairBack, SOC-HairExtra.
Slots mix. A full-style preset fills several slots and still allows each slot to be replaced. Every piece has shape keys or bone scales for volume and width, length where the cut can grow, plus root color, tip color, and highlight strength.
Hair must fit the human head and keep a visible gap or corrective when creature ears, horns, or a muzzle are equipped.
Adult front looks: none, blunt, parted, swept, curtain, asymmetrical, heavy, wispy, middle-part long, one-eye cover, curled, braided fringe.
Adult back and crown looks: crop, short layered, bob, long straight, long layered, wavy, curls, hime, low ponytail, high ponytail, twin tails, single braid, twin braids, half-up, bun, twin buns, side ponytail, afro, puff, locs, cornrows, braided ponytail, mullet, wolf cut, undercut with long top, mohawk, drill curls, loose shoulder braid.
Stackable extras: ahoge, side lock, ribbon tie, hair band, small braid accent.
Facial hair is adult-only: at least three moustaches, two sideburn shapes, and four beards (stubble, short, medium, full). Each has length and bulk sliders and its own color. Pieces mix.
Build the full adult list in this phase. Do not stop at one short and one long style.

ACCESSORY CONTRACT
Every exemplar has a text manifest in its collection custom properties and a copy in docs/ASSET_CONTRACT.md:
id, display_name, slot, socket, type, hides_body_groups, follows_shape_keys, color_slots, damage_masks
type is one of: rigid, deform, replacement, prop, creature
deform assets include the identity body shape keys for the region they cover, with the same key names, driven by the same armature properties.
replacement assets hide the named body vertex groups when equipped, for sealed shoes or sealed gauntlets.
Build exactly one exemplar of each, original designs, same shader family:
- clothing: a layered ranger outfit, cloth under leather straps, with a pouch
- armor: painted plates over that cloth, plus a fur collar, fur shoulder trim, and goggles with a colored lens. Original shapes only. Do not rebuild the costumes in the reference frames.
- weapon melee: a one-handed blade aligned to SOC-Weapon_R
- weapon ranged: a compact original ranged weapon aligned to SOC-Weapon_L
- robot armor: a painted chest shell and a forearm shell with an elbow split, chunky readable panels, wear mask
- organic: a small original creature on SOC-OrganicForeArm_L with a 3-bone rig and a 48-frame idle breathing loop
- bandana on SOC-HeadTop
- sunglasses and eyeglasses on SOC-Eyewear, lens as a tinted transparent material, eyes still readable
- shoes on SOC-Foot_L and SOC-Foot_R, hiding toenails when equipped
- belt on SOC-Waist
- cape on SOC-Cape with 5 bones, plus a damage property 0 to 1 driving hole alpha, dirt, and edge fray
- torn cape elements: one hole flap mesh and one dirt decal setup, driven by that same damage property
Do not fill a large library. The contract matters more than quantity.

SHADER
Create node groups: NG_ToonSurface, NG_ToonSkin, NG_ToonHair, NG_ToonMetal, NG_ToonCloth, NG_ToonScale, NG_Eye, NG_Outline.
Shared look: 2 to 3 soft shadow bands, gentle wrap on skin, tighter highlight on metal, anisotropic highlight on hair, rim, thin outline. Skin uses skin_color, lip_color, nail_color, blush_strength, vein_strength. Cloth and cape use base color, trim color, dirt, hole alpha, fray. Metal uses base color, paint wear, emissive color, and a harder specular. Scales use scale color, belly color, membrane color, and horn color. The scale pattern is large, graphic, and painted, with a lighter belly and a separate crest color. Wing membranes show simple rib shapes. Spines and teeth are modeled silhouette. Mouth interior can be its own strong color. Eyes use iris color, iris size, pupil size, sclera tint, catchlight. The dragon pupil can be a vertical slit through the same eye group. Pack image masks into the blend. Use Eevee. If you use Cycles for a beauty still, the creator viewport must still look correct in Eevee.

HUMANOID CREATURE ELEMENTS
Do not start until adult Phase 9 passes. Use the adult humanoid mesh. Do not create a separate body per animal.
MIXING
Human looks and humanoid-beast looks are one library. The user can combine them in any way: human ears with a tiger muzzle, rabbit ears on a human, human hands on a lizard, a rhino horn on a bird person, hair on any humanoid. A preset only sets values. It must not lock a slot or hide the human looks.
Full-beast elements belong only to the quadruped dragon. Do not reuse those meshes, shape keys, or sockets on a human or human-beast, and do not put humanoid hair, ears, hands, or clothes-slot elements on the full beast. The robot library is separate in the same way. Tag every asset with library: humanoid, full_beast, or robot. The panel filters by the active body.
Every element stores look (a style id, including a human look and none) and shape (floats). Document every control in ASSET_CONTRACT.md.
Elements:
- Muzzle or beak. Looks: none, feline, canine, reptile, fish, bird, frog, lagomorph, heavy. Shape: length, width, height, bridge.
- Ears. Looks: human, round, pointed, long, fin, feathered, none. Shape: size, lift, spread.
- Eyes. Keep the adult eye-shape keys. Add pupil style and forward placement.
- Mouth extras. Looks for fangs, beak overlap, whiskers. Shape: fang length, whisker density.
- Mane, crest, or feathers. A style mesh plus length, volume, and color.
- Horns or head fins. A style mesh plus length, thickness, and curve.
- Neck frill or gills. Size and flare.
- Hands and feet. Looks: human, paw, webbed, talon. Shape: digit emphasis, claw length. Add a leg look, plantigrade or digitigrade, so a beast person or dragon person can stand on a clawed foot. Clothing still fits.
- Tail. Looks: none, feline, canine, lizard, fish, bird, serpent, puff. Shape: length, thickness, tip.
- Wings. Looks: none, feathered, membrane, fin. Shape: span, fold.
- Surface. Looks: skin, short fur, long fur, scales, feathers, amphibian, thick hide. Shape is coverage. Colors: primary, secondary, belly. Pattern: plain, stripes, spots, plates.
Muzzle and beak meshes deform with the jaw and the viseme keys, including PF-VisSmall and PF-VisMid. Ears, horns, mane, tail, and wings parent to sockets. Hands and feet are swaps that follow the arm and leg bones.
Archetype presets, original designs, each with a masculine adult, a feminine adult, and a clothed child counterpart: Human, Tiger, Lion, Fish, Dog, Dragon, Bird, Frog, Serpent, Rabbit, Dinosaur, Rhino, Lizard. Tiger is the first proof: every element look and both shape extremes must be screenshot before the other presets.
Add these looks so the new presets are not relabeled tigers. Ears: long. Muzzles: lagomorph, heavy. Tails: puff. Surface: thick hide, in addition to the existing skin, fur, and scales.
Preset recipes: Rabbit = long ears, lagomorph muzzle, puff tail. Dinosaur = reptile muzzle, crest, scales, thick tail, shorter arms. Rhino = heavy muzzle, one or two horns, thick hide. Lizard = reptile muzzle, scales, long tail, optional neck frill. Serpent keeps a longer tail and a slimmer body than the lizard. The quadruped dragon stays a separate body from the humanoid dinosaur and the humanoid dragon.
Adult presentation, after the tiger proof: sliders for shoulder width, chest, waist, hips, face softness, and height, plus a feminine preset and a masculine preset. Apply both presentations to the human and to each creature preset. These sliders do not exist on the child.
Adult age, on the same humanoid body: presets YoungAdult, Adult, and Old, plus live sliders. Young adult softens cheeks, enlarges the eyes slightly, and reduces creases and bulk. Adult is the basis at slider 0. Old adds brow, eye, and mouth creases, a softer jaw, slightly thinner lips, a mild stoop, and a wrinkle mask. The old preset may set hair toward gray, and the user can recolor it. Age stacks with feminine or masculine presentation and with any mix of human and beast elements. Do not build separate young-adult or old meshes. Do not put these age sliders on the child. The full beast gets its own YoungAdult, Adult, and Old presets: sleeker and smaller horns, the basis, then worn scales, heavier horns, and a lower posture.

CHILD SPECIES
Do not start until the adult Phase 9 gate has passed.
This is a stylized child for a general-audience character creator. Ship a default shirt and shoes already equipped. Do not create adult sexual anatomy, adult body-shape keys, facial hair, or muscle-definition keys on this species. Sliders are limited to child proportions, face, hair, skin, eyes, short nails, and expression.
Mesh: CHR_Body_Child on CHR_Armature_Child in character_child.blend. Poly budget 14k to 22k triangles. Same human socket names as the adult. Relaxed A-pose.
Identity face and length controls use the adult names that still make sense: face shape, jaw, cheeks, ears, nose, eyes, lids, mouth, neck_length, limb lengths, head_scale. Ranges are narrower than the adult so the result stays a child. Omit ID-Chest, ID-WideHips, ID-Glute, ID-MuscleChest, ID-MuscleAbs, ID-MuscleArms, ID-MuscleLegs, beard, moustache, and sideburns.
Author the full adult performance set on the child face: blinks with midpoints, brow keys, visemes including PF-VisSmall and PF-VisMid, emotions at jaw 0 and jaw 0.6, blink action, talking action, and the same pose-library names. Do not reuse the adult face by scale. When a child muzzle is equipped, those same viseme names still move it, including the small and mid openings.
Child hair, authored for the child head, with the same slot and shape controls: crop, bob, straight long, curls, puff, twin tails, twin braids, ponytail, half-up, and blunt, parted, and wispy fronts. Each has root color, tip color, volume, and width. If an adult hair id has a child version, child counterpart equips it. Otherwise it equips the nearest child style. One default outfit. Build child-scale versions of the creature elements, with the same look ids and shape slider names. A child-counterpart operator copies an adult humanoid's element looks, colors, and clamped shape values onto the child and drops presentation, facial hair, and muscle keys. Ship a child counterpart preset for each archetype. The child sheet shows the default outfit.

ROBOT SPECIES
Do not start until the child gates have passed.
Mesh: CHR_Body_Robot on CHR_Armature_Robot. Poly budget 20k to 35k triangles. Modeled panel gaps and hinges at neck, shoulders, elbows, wrists, hips, knees, and ankles. Default pose matches the adult A-pose so hand props line up.
Identity: ID-ChassisBulk, ID-ChestCore, ID-OpticStyle, head_scale, torso_length, limb lengths, paint_color, emissive_color, paint_wear, panel_gap. No skin, hair, nails, veins, or body hair.
Face performance uses the adult performance names. Blink and squeeze drive shutter lids. Brow keys drive brow panels or light bars. Visemes and emotions drive a segmented mouth, including small, mid, and wide, and they must be tested at partial values. Jaw bone still exists. Reuse the talking action and pose-library names. Add SOC-Antenna and SOC-Core. Human sockets that match a real robot part stay the same names: head, neck, chest, back, arms, hands, waist, feet. One extra panel-kit accessory. The human wearable robot-armor exemplar stays on the adult and is not the robot body.

DRAGON SPECIES
Do not start until the robot gate has passed.
Mesh: CHR_Body_Dragon on CHR_Armature_Dragon in a grounded quadruped pose, head raised, wings readable. Poly budget 30k to 45k triangles including wings and tail. Four legs, two wings, one tail. Original design. No copied monster silhouette.
Identity: body_size 0.6 to 1.4, neck_length, tail_length, wing_size, leg_length, ID-SnoutLong, ID-SnoutShort, ID-JawWidth, ID-HornStyle, ID-Crest, ID-EarFin. Shader: scale_color, belly_color, membrane_color, horn_color, eye color, slit pupil. Claws are the nail equivalent, with ID-ClawLength.
Sockets: SOC-Crest, SOC-Neck, SOC-Back, SOC-Wing_L, SOC-Wing_R, SOC-Tail, SOC-Shoulder_L, SOC-Shoulder_R.
Performance names stay aligned with the adult where the idea exists: PF-Blink_L/R with midpoints, PF-EyeWide, PF-Squint, lid keys, PF-BrowRaise, PF-BrowInnerUp, PF-BrowLower, PF-BrowFurrow, PF-BrowSad on brow ridges. Mouth: jaw bone, PF-VisMBP, PF-VisSmall, PF-VisMid, PF-VisWide as a roar, plus at least four speech-like muzzle shapes so dialogue is not a binary jaw, and PF-SmileClosed, PF-Snarl, PF-Surprise tested with the jaw shut and open. Tongue and fangs follow the jaw. Author blink, talking, and the pose library on this face.
One collar, one back harness, and one wing ornament. No rider, mount controls, or gameplay.

LIBRARY ONLY
Do not build the creator UI. The software that imports these folders is a separate project. Keep pack.json and manifest.json accurate so that importer can load a whole library or one category folder.
Body kind first: Adult humanoid, Child humanoid, Robot, Quadruped dragon. On a humanoid, show archetype presets and then every element with its look and shape controls. Changing body kind loads that mesh and swaps the visible slider set.
The Morphs tree holds Body, Face, Elements, Surface, Accessories, Expression, and Preset. Adult humanoids also get Presentation, with feminine and masculine presets, and Age, with young adult, adult, and old. The full beast gets Age and not human presentation. Facial hair, presentation, and adult age are absent on the child. Hide humanoid elements on the robot and the quadruped dragon. Viewport drag morphs the region under the cursor. The mixer wheel blends heads or one part and does not lock sliders. The appearance editor is a layer stack per material. The play bar previews blink, talking, and wrinkles without writing identity.
Every identity slider writes an armature custom property and applies it to shape keys, bones, shader inputs, and equipped objects.
Expression section: buttons for the pose library, Play Blink, Play Talking, Reset Performance.
Preset section: Save JSON, Load JSON, Randomize Identity, and on an adult preset a Make Child Likeness button.
Randomize stays inside the documented ranges for the active species and never changes performance keys.
JSON stores species and identity only: property values, feature ids, accessory ids, colors, damage. It does not store the current viseme.
Equip and unequip accessories by collection instance or append, parent to the socket, and drive deform keys. Unequip restores hidden body groups.

PHASE GATES
Finish in this order. After each phase, save, and render or screenshot front, three-quarter, and side. Write a short note in docs/PHASE_LOG.md.
Phase 1 gate: addon enables with an empty panel, shader node groups exist on a test sphere, sockets exist on a placeholder armature.
Phase 2 gate: base body in proportion, UVs, zones for skin, lips, and nails, transforms applied.
Phase 3 gate: every identity body key and length control works at 0, 0.5, and 1 without broken joints.
Phase 4 gate: identity face keys, eyes, lashes, and brows read clearly at the neutral and at each extreme.
Phase 5 gate: blink action, talking action, and all pose-library entries. Midpoint visemes and brow keys look intentional. Smile with jaw open uses the corrective and does not collapse the cheeks.
Phase 6 gate: every adult front, back, and extra hair style in the list equips, mixes with another slot, recolors root and tip, and moves volume. At least one style is shown over creature-ear space without swallowing the ears. Facial hair pieces mix, and length and bulk move. A contact sheet of the hair list is saved to docs/qa/hair/.
Phase 7 gate: one accessory of each type equips, parents to the right socket, and body sliders still deform clothing and armor. Cape damage moves from clean to torn. Shoes hide toenails. The organic idle plays.
Phase 8 gate: the panel drives the properties, JSON round-trips, expression preview does not wipe identity.
Phase 9 gate: a contact sheet image saved to docs/qa/adult/ showing neutral, one bulky extreme, one lean extreme, a long-limb extreme, blink midframes, talking midframes, and each pose-library expression.
Phase 10 gate: on the adult, every creature element can change look and can hit both shape extremes. The tiger preset is equipped, then one element is changed without losing the rest. A human ear look, a human hand, and a hairstyle can be equipped on that tiger, and a beast muzzle can be equipped on the human preset. A muzzle viseme hits closed, small, mid, and open. Full-beast assets are not in this list.
Phase 11 gate: presets exist for Human, Lion, Fish, Dog, Dragon, Bird, Frog, Serpent, Rabbit, Dinosaur, Rhino, and Lizard. Rabbit, dinosaur, rhino, and lizard are visually distinct from each other and from the tiger. Feminine and masculine presentations apply on top of each archetype, the sliders still move after the preset, and each archetype has a clothed child counterpart. Young adult, adult, and old apply on top of a human preset and on top of a mixed human-beast preset. The three ages stay visually distinct, and mixing an element does not reset age.
Phase 12 gate: child body reads as a child at neutral and at length extremes, default outfit is on, adult presentation sliders do not exist. Each archetype has a clothed child counterpart.
Phase 13 gate: child blink, talking, and pose library work on a human face and on a muzzle. Midpoint mouth and brow keys look intentional. Child counterpart copies element looks and does not copy adult presentation.
Phase 14 gate: robot reads as segmented metal in front, three-quarter, and side. Blink shutters, brow panels, and mouth shapes hit 0.25, 0.5, 0.75, and 1. Paint color, emissive, and wear work. The talking action plays.
Phase 15 gate: the quadruped dragon reads as a four-legged winged creature at default size and at size extremes. Wings, tail, and neck length work. Muzzle speech shapes include in-betweens. Collar, harness, and wing ornament attach to the correct sockets. Young adult, adult, and old are distinct on this body, and no humanoid element is available.
Phase 16 gate: the body-kind dropdown switches adult humanoid, child humanoid, robot, and quadruped dragon. A mixed humanoid JSON round-trips, including a human part on a beast preset. The humanoid panel has no full-beast assets, and the full-beast panel has no humanoid assets. docs/qa/ contains sheets for a feminine creature, a masculine creature, a mixed human-and-beast humanoid, a child counterpart, the robot, and the quadruped dragon. Expression preview never wipes identity.

WORKING RULES
Run the validators (docs/VALIDATORS.md, blender/scripts/run_validators.py) at every phase gate and paste the summary into docs/PHASE_LOG.md. A FAIL blocks the gate. Add LM-* markers before Phase 2 so the anatomy checks can measure the body.
Prefer a Python script you can re-run over one-off manual clicks for drivers, constraints, materials, and the panel.
When you sculpt a shape key, set the key to 1, sculpt, then return the slider to 0 and confirm the Basis is unchanged.
Name objects as specified. Do not invent a second naming scheme.
Do not Boolean accessories into the body.
Do not proceed to accessories before Phase 5 passes.
Do not start creature elements until adult Phase 9 passes. Do not start the other archetypes until the tiger element gate passes. Do not start the child until adult presentation exists. Do not start the robot until the child gates pass. Do not start the quadruped dragon until the robot gate passes.
A creature preset must leave every element editable. Do not hide shape sliders after an archetype is chosen.
The child species is a clothed, general-audience character. Do not add sexual anatomy, sexual clothing, or adult body sliders to it.
Keep a text block in each blend named CONTRACT listing that speciesâ€™ socket names and shape-key names.
If you are unsure how a control should deform, choose the version that still looks like the same character at 0.5.
