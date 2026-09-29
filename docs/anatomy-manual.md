# Anatomy manual

Read this manual in full before modeling any body, element, or preset from `docs/CLAUDE_BUILD_PROMPT.md`, and run its checklists (section 14) at every phase gate. It tells you which direction to take and what to focus on for the adult humanoid, the child humanoid, the thirteen beast-folk archetypes, and the winged quadruped dragon.

It works with `docs/shading-style-guide.md`: the style guide decides how surfaces shade; this manual decides what the forms are. Screenshots are cited by number, for example MHS3-09 (see [reference/mhs3/](reference/mhs3/README.md)).

Every source link in this manual was fetched and checked against the claim it supports. Links that failed or did not support their claim were replaced or removed.

Each section ends with:
- **Focus on**: what must be right.
- **Avoid**: the common mistakes.
- **Controls**: the build-prompt keys and lengths the section governs.

---

## 1. How to use this manual

Work in this priority order. Don't move down the list until the level above reads correctly from front, three-quarter, and side.

1. **Silhouette.** Does the body read as the right kind, age, and archetype in solid black?
2. **Proportion.** Head count, landmark heights, widths.
3. **Skeleton landmarks.** Joints where the bones put them; bony points that stay visible under any fat.
4. **Muscle and fat masses.** Large masses only, placed on the skeleton.
5. **Surface traits.** Scales, fur, skin, markings.
6. **Detail.** Last, and in texture where possible.

Stylization rules for the Stories look:
- **Anatomy stays believable underneath.** Stylize by simplifying, never by breaking the skeleton.
- **Information is grouped into clear planes.** Stories shades with a hard two-tone boundary, so every plane change becomes a shadow shape. Choose plane changes on purpose.
- **Normals stay clean.** Small muscle bumps, pores, and wrinkles in the geometry turn into noisy shadow islands. Keep them out of the mesh and out of the normals; put them in the base color as a few lines if at all.
- **Detail depends on the subject.** Characters are flat and graphic; monsters are more rendered; environments are painterly (MHS3-01).

**Focus on:** reading order, clean planes.
**Avoid:** detailing before the silhouette works; sculpting noise that becomes shadow noise.
**Controls:** all.

---

## 2. Adult humanoid proportions

Sources: [Wikipedia, Body proportions](https://en.wikipedia.org/wiki/body_proportion); [Proko, Human Proportions: Idealistic Figures](https://www.proko.com/course-lesson/human-proportions-idealistic-figures/); [Grid Maker Pro, the 8-head canon](https://gridmakerpro.com/grids/artist-guides/figure-proportion/); [Anime Art Magazine, head-to-body ratio](https://animeartmagazine.com/head-to-body-ratio-this-simple-anime-illustration-technique-will-give-you-perfect-proportions-every-time/).

- **Unit.** The head, crown to chin.
- **Height.** Real adults are about 7 to 7.5 heads; the idealized figure is 8. Young-adult manga runs 7.5 to 8.5. The project's adult is **about 7 to 7.5 heads**, matching the build prompt.
- **Landmarks, in heads from the top** (8-head canon; compress evenly for 7.5):

| Head line | Landmark |
| --- | --- |
| 1 | Chin |
| 2 | Nipples |
| 3 | Navel |
| 4 | Pubis, the body's midpoint (greater trochanters just above) |
| 5 | Mid-thigh |
| 6 | Just below the knee |
| 8 | Soles |

- **Arms.** Hanging arms put the wrists at the crotch line and the elbows at the waist and navel.
- **Torso.** Chest, abdomen, and pelvis are three roughly even parts.
- **Legs.** The thigh roughly equals the lower leg.
- **Widths.** Shoulders about 2 heads (Loomis gives 2⅓ for the heroic male); hips about 1.5 heads.
- **Hands and feet.** The hand is about as long as the face (chin to hairline); the foot is about as long as the forearm.
- **Rig.** Tie each landmark to an armature joint so the length sliders keep the ratios believable at their extremes. At every slider extreme, the wrists must still land near the crotch unless the slider is explicitly an arm-length slider.

**Focus on:** the midpoint at the pubis; wrists at the crotch; elbows at the waist.
**Avoid:** a long torso with short legs on the adult (that is the child's proportion); chibi heads.
**Controls:** `head_scale`, `neck_length`, `torso_length`, `leg_length`, `thigh_length`, `shin_length`, `upper_arm_length`, `forearm_length`, `hand_length`, `foot_length`, `shoulder_width`, `hip_width`, `body_size`.

---

## 3. Sex differences, for the feminine and masculine presets

Sources: [Wikipedia, Sexual dimorphism in human physiology](https://en.wikipedia.org/wiki/Sexual_dimorphism_in_human_physiology); [Smithsonian, "Written in Bone" skeleton activity (PDF)](https://naturalhistory.si.edu/sites/default/files/media/file/wibskeletonmaleorfemalefinal.pdf); [Skyrye Design, male vs female proportions](https://skyryedesign.com/art/drawing/body/male-vs-female-body-proportions/); [YouTalent, anatomical differences in figure drawing](https://blog.youtalent.com/in-depth-guide-anatomical-differences-male-female-figure-drawing/).

- **Pelvis, the largest difference.**
  - Feminine: wider, shorter, rounder, tilted forward (more lower-back sway), femurs set wider apart.
  - Masculine: taller and narrower, with a larger ribcage and broader shoulders.
- **Skull.**
  - Masculine: larger brow ridge, sloping forehead, square chin, sharper jaw angle, larger mastoids and nuchal ridge.
  - Feminine: vertical forehead, sharp upper eye-socket rims, pointed chin, wider (more open) jaw angle.
- **Throat.** The thyroid cartilage angle is about 90° in males (a visible Adam's apple) and about 120° in females.
- **Fat.** Gynoid (hips, thighs, glutes, continuous S-curves) versus android (belly, boxier transitions).
- **Stacking.** Ribcage and pelvis stack more directly on the masculine figure; on the feminine figure they sit more offset and counter-tilted.
- **Neck.** The masculine neck is shorter and thicker, with more trapezius.
- **Rule.** Presentation is a blend of these traits, not a swap of the whole body. Every trait must interpolate cleanly at 50%, and presentation must stack on every archetype and every age.

**Focus on:** pelvis and ribcage ratio first, then the skull traits, then fat.
**Avoid:** doing presentation with breasts and hair alone; a 50% blend that looks broken.
**Controls:** `ID-WideHips`, `ID-NarrowWaist`, `ID-BroadShoulders`, `ID-Chest`, `ID-Glute`, `ID-BrowRidge`, `ID-JawWidth`, `ID-ChinWidth`, `ID-NeckThickness`, `hip_width`, `shoulder_width`.

---

## 4. Age, for the young adult, adult, and old presets

Sources: [PMC, "The Facial Aging Process From the Inside Out"](https://pmc.ncbi.nlm.nih.gov/articles/PMC8438644/); [Mendelson and Wong, "Changes in the Facial Skeleton With Aging", Aesthetic Plastic Surgery](https://link.springer.com/article/10.1007/s00266-012-9904-3); [MDPI, "Personalized Research on the Aging Face: A Narrative History"](https://www.mdpi.com/2075-4426/14/4/343); [Anime Art Magazine, ages in anime men](https://animeartmagazine.com/how-to-represent-different-ages-in-anime-men/); [Clip Studio Tips, "Throughout the Generations"](https://tips.clip-studio.com/en-us/articles/7069).

- **Young adult.** A slightly larger iris-to-eye ratio, a softer jaw, a fuller midface, slimmer muscle definition.
- **Adult.** A longer, slimmer face; a defined jaw and nose; a shorter gap between brow and eye (which reads as more mature); a thicker neck.
- **Old**, working from the bone outward:
  - The eye sockets enlarge; the maxilla (upper jaw) and the jaw angle recede.
  - The nose lengthens and its tip drops.
  - Fat pads descend, creating tear troughs, nasolabial folds, and jowls.
  - The jaw-neck boundary softens; the hyoid and larynx drop.
  - The ears lengthen.
  - The spine rounds (kyphosis) and the head moves forward.
  - Muscles lose definition; skin shows wrinkles and color changes.
- **Anime simplification.** Express age with a few thin lines at the eyes, the nasolabial fold, and the jaw, plus a longer face and painted stubble (MHS3-09). Never use noise or dense wrinkles.
- **Rule.** Age stacks on presentation and on every element mix; mixing an element must not reset age.

**Focus on:** bone changes first (sockets, maxilla, jaw), then fat descent, then a few lines.
**Avoid:** age as wrinkles only; wrinkles in the geometry.
**Controls:** age presets; `ID-CheekHollow`, `ID-CheekFull`, `ID-EyeDroop`, `ID-LidHood`, `ID-NoseLong`, `ID-JawHeight`, `ID-EarLobe`, wrinkle maps.

---

## 5. Child humanoid

The child is clothed and general-audience, as the build prompt requires. Sources: [Illustrator Draftsman manual, measuring the child figure](https://draftingmanuals.tpub.com/14262/css/Measuring-The-Child-Figure-With-The-Head-149.htm); [Envato Tuts+, drawing different ages](https://design.tutsplus.com/tutorials/human-anatomy-fundamentals-drawing-different-ages--cms-21905); [Fiveable, proportions of the human body](https://fiveable.me/drawing-foundations/unit-10/proportions-human-body/study-guide/bVYcw96jRRpCUZJk); [Clip Studio Tips, "Throughout the Generations"](https://tips.clip-studio.com/en-us/articles/7069).

- **Height.** About 5 heads at ages 4 to 5 and about 6 heads at 7 to 9. The project's child is **5 to 5.5 heads**.
- **Midpoint.** The body's center sits above the hips, not at the crotch.
- **Torso and limbs.** Long torso, short limbs.
- **Face.** The face takes less of the head than an adult's: large cranium, high wide forehead, features on the lower half, large ears (MHS3-07).
- **Features.** Large round eyes set low and wide, a short upturned nose, a soft round chin, thin brows set apart, rosy cheeks.
- **Neck and shoulders.** A thin neck and an almost horizontal shoulder line (little trapezius). Shoulders about 1.5 heads.
- **Hands.** Softer and rounder, with shorter fingers and subtle knuckles.
- **Rule.** Dimorphism, muscle, and adult presentation keys are excluded from the child.

**Focus on:** the high midpoint, the large cranium, low eyes.
**Avoid:** adult proportions scaled down; any adult presentation sliders.
**Controls:** child length controls, `head_scale`, `ID-EyeSize`, `ID-EyeHeight`, `ID-NoseSmall`, `ID-FaceRound`, `ID-EarSize`, `blush_strength`.

---

## 6. Body types, fat, and muscle

Sources: [Classic Human Anatomy in Motion, "Body Types, Surface Landmarks, and Soft-Tissue Characteristics"](https://doctorlib.org/anatomy/classic-human-anatomy-motion/9.html); [Skyrye Design, body types drawing](https://skyryedesign.com/art/body-types-drawing/).

- **Somatotypes are blendable axes, not categories.**
  - Ectomorph: narrow frame, long limbs, bones visible at the surface.
  - Mesomorph: broad shoulders, visible muscle.
  - Endomorph: round torso, short neck; wrists and ankles stay lean.
- **Fat patterns.** Apple (android, belly), pear (gynoid, hips and thighs), and even.
- **Rules.**
  - Fat hides muscle but not bony landmarks: the pit of the neck, the collarbones, the front hip points (ASIS), the kneecap, the ankle bones.
  - Shoulders, calves, and forearms keep their form under fat.
  - Change the underlying proportions; don't just inflate the body.
  - Muscle keys move large masses (pectoral, deltoid, quadriceps), never add small bumps.

**Focus on:** lean wrists and ankles at every bulk; landmarks that survive fat.
**Avoid:** balloon inflation; six-pack noise that becomes shadow islands.
**Controls:** `ID-BodyBulk`, `ID-BodyLean`, `ID-BodySoft`, `ID-Belly`, `ID-MuscleAbs`, `ID-MuscleArms`, `ID-MuscleChest`, `ID-MuscleLegs`, `ID-UpperArmBulk`, `ID-ForeArmBulk`, `ID-ThighBulk`, `ID-CalfBulk`.

---

## 7. Surface anatomy that must read in cel shading

Sources: [Classic Human Anatomy in Motion, "Structures and Planes of the Figure"](https://doctorlib.org/anatomy/classic-human-anatomy-motion/10.html); [the same, "Muscle and Tendon Characteristics"](https://doctorlib.org/anatomy/classic-human-anatomy-motion/4.html); [Art Prof, front torso muscles](https://artprof.org/learn/fundamentals/anatomy/anatomy-for-artists-front-torso-muscles/).

- **Bony landmarks:** the pit of the neck and collarbones; the acromion (shoulder point) and spine of the scapula; the sternum; the ASIS and sacral dimples; the elbow point; the kneecap; the ankle bones.
- **Muscle masses:** sternocleidomastoid, trapezius, deltoid, pectoralis; serratus interlocking with the external oblique; rectus abdominis; latissimus; glutes; quadriceps; calves.
- **Plane changes that become shadow shapes** under a key light from above and to the side:
  - under the pectoral and along the ribcage's side plane;
  - the side plane of the abdomen where the oblique turns;
  - under the jaw and down the neck beside the sternocleidomastoid;
  - the underside of the deltoid and the inner arm;
  - the inner thigh and the back of the calf;
  - under the kneecap.
- **Rule.** Model these as large planes. Stories keeps two tones, so remove small muscle noise from the geometry and the normals.

**Focus on:** a few big plane breaks per body part.
**Avoid:** every muscle visible; separate abdominal blocks at default bulk.
**Controls:** muscle and bulk keys; normal-map strength.

---

## 8. Head and face

Sources: [OtakuKart, basic manga proportion rules](https://otakukart.com/4-basic-proportion-rules-can-teach-beginners-how-to-draw-manga/); [Dattebayo, how to draw anime faces](https://dattebayo.me/en/blog/how-to-draw-anime-faces); [Clip Studio Tips, faces across ages](https://tips.clip-studio.com/en-us/articles/7069); [Golden Ratio Face, face shape chart](https://goldenratioface.net/face-shape-chart/).

- **Construction.** A ball (the cranium) plus a wedge (the jaw).
- **Placement.** Eyes at about the vertical midpoint of the head, one eye-width apart. The nose about halfway from eyes to chin; in anime faces the mouth sits close under the nose.
- **Face shape** comes from three measures: length against width, which part is widest (forehead, cheekbones, or jaw), and the jaw type (corner, curve, or point). That gives oval, round, square, oblong, rectangle, heart, diamond, and triangle.
- **Eyes** are independent axes:
  - outline: almond or round;
  - lid: monolid, hooded, or creased;
  - corner tilt: up, level, or down;
  - set: close, wide, deep, or prominent.
- **Nose families:** bridge height and width, length, tip up or down, tip width, nostril flare. In Stories the nose is a small wedge shadow or one line, no front outline.
- **Lip families:** upper and lower fullness, width, philtrum depth, corner direction. A darker lip hint only on adults.
- **Stories face rules** (see the style guide): near-flat skin with one hard shadow shape; face normals from a head proxy; a forced-shadow mask under the fringe and lip.

**Focus on:** eye placement and spacing; jaw type; clean normals from the proxy.
**Avoid:** realistic nose modeling that casts a nose shadow at the front view; noisy cheek normals.
**Controls:** `ID-FaceRound`, `ID-FaceLong`, `ID-FaceSquare`, `ID-FaceHeart`, `ID-FaceDiamond`, `ID-EyeAlmond`, `ID-EyeRound`, `ID-LidCrease`, `ID-LidHood`, `ID-EyeTilt`, `ID-EyeUpturn`, `ID-EyeDroop`, `ID-EyeSpacing`, `ID-EyeHeight`, `ID-EyeSize`, `ID-EyeNarrow`, `ID-NoseBridgeHigh`, `ID-NoseBridgeWide`, `ID-NoseLong`, `ID-NoseSmall`, `ID-NoseTipUp`, `ID-NoseTipWide`, `ID-NostrilFlare`, `ID-LipUpper`, `ID-LipLower`, `ID-LipThin`, `ID-Philtrum`, `ID-MouthWidth`, `ID-MouthHeight`, `ID-CornerUp`, `ID-CornerDown`, `ID-JawWidth`, `ID-JawHeight`, `ID-ChinLength`, `ID-ChinWidth`, `ID-ChinCleft`, `ID-Cheekbone`.

---

## 9. Hands and feet

Sources: [Proko, hand bones](https://www.proko.com/course-lesson/how-to-draw-hand-bones-anatomy-for-artists/); [Anatomy for Sculptors, hand anatomy](https://anatomy4sculptors.com/blog/hand-anatomy-for-artists/); [Clip Studio Tips, a systematic guide to hands and feet](https://tips.clip-studio.com/en-us/articles/11103).

- **Hand.**
  - About as long as the face. Palm and fingers are about equal in visible length from the palm side; the finger bones are actually longer, because the palm's fat pads cover the first finger joints.
  - The knuckles form an arc that peaks at the middle finger; fingers taper and lean toward the middle finger.
  - The palm is a curved block with a transverse arch; the thumb sits on a triangular web and the thenar pad, the thickest mass on the palm.
  - Fingers look longer from the back than from the palm side. The back of the hand is bones and tendons; the tendons fan toward the wrist.
- **Foot.**
  - A wedge with a high inner arch and a flatter, padded outer edge.
  - The transverse arch flattens toward the toes; the toes step down like a staircase and line up with the ball of the foot.
  - The inner ankle bone sits higher than the outer one.
  - The forefoot is about twice as wide as the heel.

**Focus on:** knuckle arc; thumb base; ankle bone heights.
**Avoid:** fingers of equal length; flat-soled feet.
**Controls:** `hand_length`, `finger_length`, `foot_length`, `ID-HandSize`, `ID-FootSize`, `ID-NailLength`, `ID-ClawLength`.

---

## 10. Beast-folk anatomy, for the element library

Sources: [How to Draw Manga Furries (Internet Archive)](https://archive.org/details/how-to-draw-manga-furries-the-complete-guide-to-anthropomorphic-fantasy-characters-750-illustrations); [Winged Canvas, drawing anthro characters](https://www.wingedcanvas.com/single-post/how-to-draw-animal-anthro-characters); [digitigrade legs tutorial (video)](https://www.youtube.com/watch?v=o5k_LSRXo2E); [Jesseth, digitigrade legs for the scientifically accurate](https://www.deviantart.com/jesseth/art/Digigrade-Legs-for-the-Scientifically-Accurate-303608200); [John Muir Laws, comparative anatomy of the legs](https://johnmuirlaws.com/how-to-draw-mammals-comparative-anatomy-legs/); [John Muir Laws, predator vs prey heads](https://johnmuirlaws.com/drawing-mammal-heads-predator-vs-prey/).

### Muzzles
- A prism (mammals) or a cone (beaks) attached to the cranium ball.
- The jawline runs from the base of the ear, down and under the head.
- The muzzle must foreshorten correctly from the front.
- The mouth corner reaches about two-thirds of the way toward the eye.
- Lip and tongue speech shapes must still read: the muzzle visemes need closed, small, mid, and open.

### Legs
- **Plantigrade** (human, bear): the whole sole on the ground; the wrist at ground level.
- **Digitigrade** (cat, dog, bird, dinosaur): the heel permanently raised, which is the "backward knee"; it is really the ankle, and the long metatarsals become the lower leg segment. The wrist sits a little off the ground.
- **Unguligrade** (hoofed): walking on the nail; the wrist and heel are halfway down the exposed leg.
- In a digitigrade leg, the thigh muscles join about halfway down the calf, and the heel bone lengthens as the foot lengthens.
- Lengthen the legs or shift the joints, but keep the crotch roughly at the midpoint so clothing still fits.

### Feet and hands
- Toes radiate from the ankle. Reptile claws angle outward; wolf and cat claws angle inward. Dogs show four toes on the ground.
- Hands grade from human to paw:
  1. fur on the back of the hand;
  2. palm pads;
  3. pads plus claws;
  4. fused finger tips (paw).
- A human hand must equip on any archetype (phase 10 gate).

### Tail
A continuation of the spine at the coccyx. The base is as wide as the sacrum, clothing gets a cutout, and the tail counterbalances the pose.

### Ears
- Mounted where each species carries them.
- Predators have ears broad across the base; prey have broad ears that swivel on a narrow base.
- Hair needs a gap or corrective shape so it never swallows the ears (phase 6 gate).

### Eyes and skulls
Sources: [San Francisco Zoo docents, biofacts: skulls (PDF)](https://www.sfzoodocents.org/notebook/TrainingNewDocentsSlides/19.BiofactsSkulls.pdf); [Alaska Department of Fish and Game, "Become a Skull Detective"](https://www.adfg.alaska.gov/index.cfm?adfg=wildlifenews.view_article&articles_id=1049); [John Muir Laws, predator vs prey heads](https://johnmuirlaws.com/drawing-mammal-heads-predator-vs-prey/).
- "Eyes in front like to hunt, eyes on the side like to hide." Predators have forward-facing eyes; prey have eyes on the sides of the head.
- Most animals' eyes sit in a bulge of bone and tissue, unlike a primate's sunken eyes; predators have an extra bump on the inner edge.
- Canids have long nasal passages; felids have short muzzles and large eye sockets.
- Rabbits have two pairs of upper incisors (a small pair behind the large front pair).

### Per-archetype sheet

Every archetype must be distinct from its neighbors in silhouette alone (phase 11 gate).

| Archetype | Skull and muzzle | Eyes | Ears | Hands, feet, legs | Tail | Surface | Markings | Distinct from |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Human | Flat face, no muzzle | Forward, round pupil | Human | Plantigrade, human hands | None | Skin | Freckles, moles | The baseline |
| Tiger | Short broad muzzle, big cheek ruff | Forward, round pupil, large sockets | Rounded, broad base, white back spot | Digitigrade option, pads and retractable claws | Long, thick, ringed | Short fur | Vertical stripes, white muzzle and chest | Lion: stripes, no mane |
| Lion | Short broad muzzle, square nose pad | Forward, round pupil | Small rounded, often hidden by mane | Digitigrade option, big paws | Long with a tuft | Short fur plus mane | Plain tawny, dark tuft | Tiger: mane and plain coat |
| Fish | Wide lipless mouth, no nose | Side-set, round, lidless look | Fin-like ear fans | Webbed fingers, plantigrade | Optional caudal fin | Overlapping scales from deep skin | Countershading, lateral line | Frog: scales and fins |
| Dog | Long muzzle (canid nasal length), visible stop | Forward, round pupil | Upright or floppy, broad base | Digitigrade option, four toes on the ground, blunt claws | Medium, brushy | Fur | Saddle, masks, points | Wolf-like but friendlier; not a tiger |
| Dragon | Long reptile snout, horns as keratin over bone | Forward, slit pupil, brow ridge | Frills or fins | Plantigrade or digitigrade, clawed | Long, tapering | Large plates, belly scutes | Crest, contrasting belly | Lizard: horns and plates |
| Bird | Beak cone of keratin over bone | Side-set (prey) or forward (raptor) | Hidden; feather tufts | Scaly digitigrade legs; arm-wings or back-wings | Tail feathers | Feathers, scaly shins | Bars, crests | Every other: the beak |
| Frog | Wide flat head, huge mouth line | Bulging, high on the head | Tympanum, no ear flap | Long jumping legs, webbed toe pads | None | Thin smooth moist skin | Spots, bright warning colors | Fish: skin and legs |
| Serpent | Narrow wedge head, no external ears | Side or forward, slit pupil | None | Human or reduced limbs | Long, the main feature | Fine scales, belly scutes | Diamonds, bands | Lizard: no ears, long tail |
| Rabbit | Short muzzle, split upper lip, two pairs of upper incisors | Large, side-set (prey) | Very long, narrow swivel base | Big hind feet, plantigrade or digitigrade | Short puff | Soft fur | White belly, agouti | Every other: the ears |
| Dinosaur | Deep skull, big jaw, rows of teeth | Forward or side | Hole only | Strong digitigrade legs, three-toed feet | Heavy counterbalance | Pebbled scales, some feathers | Stripes, crest | Lizard: stance and mass |
| Rhino | Long heavy head, nasal horn(s) | Small, side-set | Tubular, mobile | Three-toed, near-unguligrade, pillar legs | Short, thin | Thick folded hide | Plain, armor-plate folds | Every other: horn and hide |
| Lizard | Flat triangular head, small snout | Side-set, round pupil | Ear hole | Sprawling plantigrade, clawed | Long, tapering | Small scales | Dewlap, bands, spines | Serpent: legs and ear holes; dragon: no horns |

### Surfaces
Sources: [Wikipedia, Reptile scale](https://en.wikipedia.org/wiki/Reptile_scale); [IntechOpen, "Reptilian Skin and Its Special Histological Structures"](https://www.intechopen.com/chapters/65535).
- Reptile scales are folds of the outer skin. Large ones are scutes; some have bony plates (osteoderms) beneath.
- Crests, frills, and spines are projections of the outer skin.
- Fish scales grow from the deeper skin layer and overlap.
- Amphibian skin is thin and smooth.
- **Stories rule:** render scales as large graphic plates with a darker border and lighter center, not dense texture (MHS3-01, MHS3-10). Beast-folk simplify plates further than monsters.

### Bird people
Sources: [F-no Dragon Art, vertebrate wings crash course](https://f-nodragonart.tumblr.com/post/641263760327213056); [Beauty of Birds, feathers and skin](https://beautyofbirds.com/feathersandskin/); [Candlekeep, "On Harpies"](http://candlekeep.com/library/articles/on_harpies.htm).
- Wings evolved from arms but are not arms. Choose arm-wings or back-wings explicitly.
- Wing shoulders need large chest muscles and a deeper chest.
- Primaries attach to the hand; secondaries to the ulna.
- The beak is keratin over bone.
- Back-wings add a second shoulder mass behind the arms.

### Fur direction
Source: [Russell Collection, how to paint fur](https://russell-collection.com/how-to-paint-fur-with-acrylic/).
- Fur radiates from growth points, reverses along the spine, fans around the eyes and muzzle, and changes direction at the joints.
- Guard hair lies over an undercoat. Common markings: countershading, stripes, spots.
- **Stories rule:** fur is sculpted as clumps whose tips form the silhouette, with a soft shadow boundary and no strands (MHS3-09, MHS3-10). Clumps point along the direction map.

**Focus on:** skull type and eye placement first; leg type second; surface last.
**Avoid:** a human head with animal ears glued on; archetypes that differ only by color.
**Controls:** element looks, `ID-SnoutLong`, `ID-SnoutShort`, `ID-EarSize`, `ID-EarPoint`, `ID-EarOut`, `ID-EarFin`, `ID-Crest`, `ID-HornStyle`, `ID-ClawLength`, `tail_length`, `scale_color`, `belly_color`, `horn_color`.

---

## 11. Quadruped dragon anatomy

Sources: [University of Minnesota, CVM Large Animal Anatomy: thoracic limb](https://pressbooks.umn.edu/largeanimalanatomy/chapter/thoracic-limb-forelimb/); [PMC, "Somitic origin of the medial border of the mammalian scapula"](https://pmc.ncbi.nlm.nih.gov/articles/PMC2849525/); [John Muir Laws, comparative anatomy of the legs](https://johnmuirlaws.com/how-to-draw-mammals-comparative-anatomy-legs/); [Ben-Amotz et al., BMC Veterinary Research, stance and weight distribution in dogs](https://link.springer.com/article/10.1186/s12917-020-02402-7); [Daniel Fotheringham, spine gaits](http://danielfotheringham.com/quad-blog-beta/the-spine/spine-gaits/); [Animal Diversity Web, bat wings](https://animaldiversity.org/collections/mammal_anatomy/bat_wings/); [Wikipedia, Patagium](https://en.wikipedia.org/wiki/Patagium); [F-no Dragon Art, full-body wing integration](https://f-nodragonart.tumblr.com/post/641263965657284609); [Lesterbanks, "How to Make your Dragon"](https://lesterbanks.com/2016/01/how-to-make-your-dragon/); [Worldbuilding Stack Exchange, dragon muscular structure](https://worldbuilding.stackexchange.com/questions/219219/how-to-design-the-muscular-structure-of-a-dragon).

### Shoulders and legs
- **No rigid shoulder joint to the chest.** Ungulates have no collarbone and carnivores only a small one, so the forelimb hangs from the trunk by muscles alone (synsarcosis). The serratus ventralis forms a sling that suspends the chest between the forelimbs. This gives longer, straighter strides.
- **Hidden elbows and knees.** The elbow and knee often sit at belly level, so the first visible joint below the body is the wrist or heel.
- **Wrist height.** At the ground (plantigrade), a little up (digitigrade), halfway down the exposed leg (unguligrade). Pick one for the dragon and keep front and hind consistent.

### Weight
- A standing four-legged dog carries about 60% of its weight on the forelimbs and 40% on the hindlimbs. Give the dragon the same bias: heavier forelimbs and shoulders.
- Balance head and neck against the body: a short strong neck with a big head, or a long neck with a light head, not a long neck with a heavy head.

### Spine
- The spine drives the gait. Rigid-spined animals move chest and hips as one mass; flexible-spined animals move chest, hips, and head separately.
- The offset between chest and hips is about **18% of the cycle in a walk, 5% in a trot, and 27% in a gallop**. Use this for the idle and walk and to check the rig.

### Wings (six limbs)
Four legs plus two wings has no real-animal equivalent. Make it believable:
- The wing roots sit behind and above the forelimbs on a large floating shoulder blade. Flying animals hang from the wing shoulder in flight, so the torso is short, compact, and stiff.
- The chest is deep, with a keel-like sternum for flight muscles. On a horse-sized flier the flight muscles are a large share of the body mass.
- The membrane follows bat anatomy:
  - **propatagium**: leading edge, shoulder to wrist;
  - **dactylopatagium**: between the fingers, supported by digits 2 to 5;
  - **plagiopatagium**: from the fifth digit to the flank or hind leg;
  - optionally a **uropatagium** between the hind legs and tail.
- The digits fold like a closing hand so the wing tucks along the back.
- Wing bones are thick enough to read at size extremes.
- Stories: flat color areas with pattern patches, dark bone struts, spiky trailing edges (MHS3-08).

### Neck, tail, head
- Neck and tail are one continuous spine with a smooth taper.
- The talking muzzle keeps a lip line for visemes, with in-betweens.
- Horns are keratin sheaths over a bone core, with etched grooves and a ridge highlight (MHS3-10).
- Teeth: many small, sharp ivory cones. Eyes: yellow, slit pupil, dark rim.

### Surface
- Scale plates sized by region: large dorsal scutes, a smaller belly pattern, fine scales at the joints so they bend.
- Accent zones as hard-edged color patches in a region mask (MHS3-01, MHS3-08).

**Focus on:** shoulder sling and hidden elbows; forelimb weight bias; wing roots behind the forelimbs with shoulder mass.
**Avoid:** a human torso shape; wings stuck on with no shoulder mass; a long flexible body for a flier; copying a monster silhouette.
**Controls:** `wing_size`, `tail_length`, `neck_length`, `body_size`, `ID-HornStyle`, `ID-ClawLength`, `scale_color`, `membrane_color`, `belly_color`, `horn_color`, dragon age presets.

---

## 12. Physical traits and diversity

Sources: [WebMD, hair types](https://www.webmd.com/beauty/hair-types); [Allure, curl type chart](https://www.allure.com/gallery/curl-hair-type-guide); the eye axes in section 8; the [face shape chart](https://goldenratioface.net/face-shape-chart/).

- **Hair** has two independent axes: type (1 straight, 2 wavy, 3 curly, 4 coily, each with subtypes a to c) and strand texture (fine to coarse). Coily hair grows outward rather than downward and can shrink up to about 75% of its stretched length. The hair pack list needs every type, and volume is modeled outward for type 4.
- **Skin** has warm, cool, or neutral undertones across the full range of tones. Shadow colors are hue-shifted, not a darker grey (the style guide's shadow tint).
- **Eyes, nose, lips, and face shape** are independent sliders; no feature is tied to another.
- **Markings:** freckles, moles, scars, vitiligo, age spots, animal patterns.
- **Height and build** vary across presets.
- **Rule.** No archetype is tied to one skin tone or feature set, and the presets span the range.

**Focus on:** independent axes; the full tone range.
**Avoid:** one default face shape for everyone; grey shadows on dark skin.
**Controls:** `skin_color`, `lip_color`, `nail_color`, `blush_strength`, hair packs, markings layers, face keys.

---

## 13. Topology and deformation, for Blender

Sources: [The Gnomon Workshop, Topology for Animated Characters](https://thegnomonworkshop.com/workshops/topology-for-animated-characters); [Blender Base Camp, topology for rigging](https://www.blenderbasecamp.com/topology-for-blender-rigging-best-practices/); [TRUETECH, deformation-friendly topology](https://truetech.dev/games-development/services/3d-modeling/creating-proper-topology-for-graphics-deformations.html).

- Quads throughout, with edge flow following the forms.
- Edge loops at joints:

| Area | Loops |
| --- | --- |
| Shoulder | 3 to 5 |
| Elbow | 2 to 4, with an arc on the inner side |
| Knee | 4 to 6, with enough behind it |
| Face | 8 to 12: rings around the eyes, loops radiating from the mouth, a loop along the nasolabial fold |

- Poles (five or more edges) go on flat, low-motion areas.
- Test-bend early, at every joint, before detailing.
- **Stories ties:** clean normals for two-tone shading; face normals transferred from a head proxy; `*_outline` hull meshes and `*_shadow` proxy meshes where needed (see the style guide's asset contract).

**Focus on:** loops at joints; clean normals.
**Avoid:** triangles and poles in the bend areas; detailing before a bend test.
**Controls:** every body and length control (they must deform cleanly at 0, 0.5, and 1).

---

## 14. Checklists per phase gate

Run the matching list at each gate in `docs/CLAUDE_BUILD_PROMPT.md`, on front, three-quarter, and side renders. Record the result in `docs/PHASE_LOG.md`.

**Phase 2 (base body)**
- [ ] Adult is 7 to 7.5 heads; landmarks at their head lines (section 2).
- [ ] The pubis is at the midpoint.
- [ ] Hanging wrists reach the crotch; elbows at the waist.
- [ ] Shoulders about 2 heads wide, hips about 1.5.
- [ ] Surface planes are large; no muscle noise in the normals.

**Phase 3 (body keys and lengths)**
- [ ] Every key at 0, 0.5, and 1 keeps wrists and ankles lean and bony landmarks visible.
- [ ] Presentation at 50% reads as a clean blend.
- [ ] Length extremes keep the crotch near the midpoint.

**Phase 4 (face)**
- [ ] Eyes at the head's midpoint, one eye-width apart.
- [ ] Each face axis (shape, eye outline, lid, tilt, set, nose, lips) moves independently.
- [ ] No nose outline or nose shadow at the front view in Stories.

**Phase 5 (performance)**
- [ ] Lid shadow and eye highlight survive every expression.
- [ ] Smile with the jaw open doesn't collapse the cheeks.

**Phase 6 (hair)**
- [ ] Hair types 1 to 4 are covered; type 4 volume grows outward.
- [ ] Hair over creature ears leaves the ears visible.

**Phase 10 (elements)**
- [ ] Muzzles foreshorten from the front; mouth corners reach about two-thirds toward the eye.
- [ ] Muzzle visemes hit closed, small, mid, and open.
- [ ] Digitigrade legs have the raised heel; the crotch stays near the midpoint.
- [ ] Tails root at the sacrum.

**Phase 11 (archetypes, presentation, age)**
- [ ] Each archetype is identifiable in silhouette alone, per the sheet in section 10.
- [ ] Rabbit, dinosaur, rhino, and lizard are distinct from each other and from the tiger.
- [ ] Old reads through bone and fat changes plus a few lines, not noise.
- [ ] Presentation and age stack on every archetype and mix.

**Phase 12 and 13 (child)**
- [ ] Child is 5 to 5.5 heads; the midpoint is above the hips.
- [ ] Large cranium, low and wide eyes, thin neck, level shoulders.
- [ ] No adult presentation sliders.

**Phase 15 (quadruped dragon)**
- [ ] Forelimbs visibly carry more weight (about 60%).
- [ ] Elbows and knees sit near belly level; wrist height is consistent front and back.
- [ ] Wing roots are behind and above the forelimbs with visible shoulder mass; the torso is short and deep-chested.
- [ ] Membrane sections follow the bat layout; wings fold along the back.
- [ ] Neck and tail taper as one spine; the muzzle keeps a lip line.
- [ ] Reads as a four-legged winged creature at every size extreme.

**Every gate**
- [ ] Silhouette first: the body reads in solid black.
- [ ] Two-tone test: under the Stories key light, shadows form a few clean shapes, not islands.
- [ ] Presets readable at 50% blends.

---

## 15. Glossary and sources

### Glossary
- **ASIS**: anterior superior iliac spine, the front hip points.
- **Acromion**: the bony point of the shoulder.
- **Android / gynoid fat**: belly-centered versus hip-and-thigh-centered fat distribution.
- **Dactylopatagium, plagiopatagium, propatagium, uropatagium**: the sections of a bat's wing membrane (between the fingers, finger to flank, shoulder to wrist, between legs and tail).
- **Digitigrade / plantigrade / unguligrade**: standing on the toes / on the whole sole / on the nail or hoof.
- **Ectomorph / mesomorph / endomorph**: lean / muscular / round body-type axes.
- **Head (unit)**: crown to chin, the unit of body proportion.
- **Kyphosis**: forward rounding of the upper spine.
- **Maxilla**: the upper jaw bone.
- **Osteoderm**: a bony plate under a reptile scale.
- **Scute**: a large reptile scale or plate.
- **Serratus ventralis**: the fan-shaped muscle that slings a quadruped's chest between its forelimbs.
- **Synsarcosis**: a limb attached to the trunk by muscle alone, with no bony joint.
- **Thenar pad**: the thick muscle mass at the base of the thumb.
- **Tone-on-tone**: a pattern drawn in lighter or darker values of the same hue.

### Sources (all fetched and checked)

Proportion and sex differences
- https://en.wikipedia.org/wiki/body_proportion
- https://www.proko.com/course-lesson/human-proportions-idealistic-figures/
- https://gridmakerpro.com/grids/artist-guides/figure-proportion/
- https://animeartmagazine.com/head-to-body-ratio-this-simple-anime-illustration-technique-will-give-you-perfect-proportions-every-time/
- https://en.wikipedia.org/wiki/Sexual_dimorphism_in_human_physiology
- https://naturalhistory.si.edu/sites/default/files/media/file/wibskeletonmaleorfemalefinal.pdf
- https://skyryedesign.com/art/drawing/body/male-vs-female-body-proportions/
- https://blog.youtalent.com/in-depth-guide-anatomical-differences-male-female-figure-drawing/

Age and children
- https://pmc.ncbi.nlm.nih.gov/articles/PMC8438644/
- https://link.springer.com/article/10.1007/s00266-012-9904-3
- https://www.mdpi.com/2075-4426/14/4/343
- https://animeartmagazine.com/how-to-represent-different-ages-in-anime-men/
- https://tips.clip-studio.com/en-us/articles/7069
- https://draftingmanuals.tpub.com/14262/css/Measuring-The-Child-Figure-With-The-Head-149.htm
- https://design.tutsplus.com/tutorials/human-anatomy-fundamentals-drawing-different-ages--cms-21905
- https://fiveable.me/drawing-foundations/unit-10/proportions-human-body/study-guide/bVYcw96jRRpCUZJk

Body types and surface anatomy
- https://doctorlib.org/anatomy/classic-human-anatomy-motion/9.html
- https://doctorlib.org/anatomy/classic-human-anatomy-motion/10.html
- https://doctorlib.org/anatomy/classic-human-anatomy-motion/4.html
- https://skyryedesign.com/art/body-types-drawing/
- https://artprof.org/learn/fundamentals/anatomy/anatomy-for-artists-front-torso-muscles/

Head, face, hands, feet
- https://otakukart.com/4-basic-proportion-rules-can-teach-beginners-how-to-draw-manga/
- https://dattebayo.me/en/blog/how-to-draw-anime-faces
- https://goldenratioface.net/face-shape-chart/
- https://www.proko.com/course-lesson/how-to-draw-hand-bones-anatomy-for-artists/
- https://anatomy4sculptors.com/blog/hand-anatomy-for-artists/
- https://tips.clip-studio.com/en-us/articles/11103

Beast-folk
- https://archive.org/details/how-to-draw-manga-furries-the-complete-guide-to-anthropomorphic-fantasy-characters-750-illustrations
- https://www.wingedcanvas.com/single-post/how-to-draw-animal-anthro-characters
- https://www.youtube.com/watch?v=o5k_LSRXo2E
- https://www.deviantart.com/jesseth/art/Digigrade-Legs-for-the-Scientifically-Accurate-303608200
- https://johnmuirlaws.com/drawing-mammal-heads-predator-vs-prey/
- https://www.sfzoodocents.org/notebook/TrainingNewDocentsSlides/19.BiofactsSkulls.pdf
- https://www.adfg.alaska.gov/index.cfm?adfg=wildlifenews.view_article&articles_id=1049
- https://en.wikipedia.org/wiki/Reptile_scale
- https://www.intechopen.com/chapters/65535
- https://f-nodragonart.tumblr.com/post/641263760327213056
- https://beautyofbirds.com/feathersandskin/
- http://candlekeep.com/library/articles/on_harpies.htm
- https://russell-collection.com/how-to-paint-fur-with-acrylic/

Quadruped dragon
- https://pressbooks.umn.edu/largeanimalanatomy/chapter/thoracic-limb-forelimb/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC2849525/
- https://johnmuirlaws.com/how-to-draw-mammals-comparative-anatomy-legs/
- https://link.springer.com/article/10.1186/s12917-020-02402-7
- http://danielfotheringham.com/quad-blog-beta/the-spine/spine-gaits/
- https://animaldiversity.org/collections/mammal_anatomy/bat_wings/
- https://en.wikipedia.org/wiki/Patagium
- https://f-nodragonart.tumblr.com/post/641263965657284609
- https://lesterbanks.com/2016/01/how-to-make-your-dragon/
- https://worldbuilding.stackexchange.com/questions/219219/how-to-design-the-muscular-structure-of-a-dragon

Diversity and topology
- https://www.webmd.com/beauty/hair-types
- https://www.allure.com/gallery/curl-hair-type-guide
- https://thegnomonworkshop.com/workshops/topology-for-animated-characters
- https://www.blenderbasecamp.com/topology-for-blender-rigging-best-practices/
- https://truetech.dev/games-development/services/3d-modeling/creating-proper-topology-for-graphics-deformations.html

Removed during verification: the direct archive.org PDF mirror (unreachable; replaced by the Internet Archive details page) and the giraffe locomotion PDF (its claim is covered by the dog weight-distribution study).
