# Anatomy research for the library (2026-10-15)

Purpose: rules the asset scripts and validators can check, each tied to a source. "Measured" = a number from a study
or our dataset; "textbook" = standard anatomy (OpenStax Anatomy & Physiology, peer-reviewed open textbook); "style" =
an anime/MHS3 convention that deliberately departs from real anatomy. Where a source was only seen as an abstract it
says so.

## 1. Face (human)
- **Eye fissure and spacing (measured).** Young adults (n = 103, Hong Kong; PMC3730197): fissure length 27.6 / 26.0 mm
  (m/f), fissure height 11.6 / 11.9 mm (height:length 0.42 / 0.46), intercanthal 40.6 / 38.3 mm, outer canthal 93.0 /
  88.4 mm, canthal index ~44. Saudi adults (n = 168; Al-Sebaei 2015, Head & Face Med 11:4): the neoclassical canons do
  not hold for most faces - the eye fissure is usually ~1.07-1.09x the intercanthal distance, the nose ~1.08-1.22x;
  facial thirds are unequal (middle third smallest, men's lower third largest).
  -> Real-face anchor for the creator's "realistic" end; anime faces scale the eye up (below).
- **Anime eye (measured, ours).** Leo (MHS3): eye width ~0.32-0.34 D (D = pupil line to chin), opening h/w ~0.55-0.6,
  gap between eyes ~1.25-1.3 eye widths, iris a tall oval ~0.45 of the opening wide and the full opening tall.
- **Cuteness / baby schema (measured).** Glocker et al. 2009 (Ethology 115:257): rounder face, higher forehead, larger
  eyes, smaller nose and mouth raise cuteness ratings and caretaking motivation (kept within ±2 SD to stay natural).
  Disney Research (Designing Animated Characters for Children of Different Ages): artists give younger-audience
  characters larger heads (r = -0.72 with target age) and larger, rounder eyes, but children did not prefer enlarged
  heads. -> The age slider should move eye size, forehead height and nose/mouth size together; adult MHS3 males sit at
  the low end.
- **Face form (measured, our dataset pass 2).** See `dataset-study-pass2.md`: the face front must not bow inward beside
  the eyes; setback at 0.30 hh 0.10-0.19 at brow, eye and cheek height.

## 2. Expression muscles and wrinkles (textbook + clinical)
- Muscles of facial expression insert into skin (OpenStax A&P 11.3): frontalis (raises brows -> horizontal forehead
  lines), corrugator supercilii (draws brows together -> vertical glabellar lines), procerus (horizontal line at the
  nose root), orbicularis oculi (circular; crow's feet radiating from the outer corner), zygomaticus major/minor and
  levator labii (nasolabial fold), orbicularis oris (vertical lip lines), mentalis (chin dimpling), platysma (neck bands).
- Expression wrinkles run **perpendicular to the pull of the muscle beneath** (Kraissl's lines / relaxed skin tension
  lines; gpnotebook clinical summaries). -> Wrinkle masks and PF- keys: forehead lines horizontal, glabella vertical,
  crow's feet radial from the outer canthus, nasolabial fold from the nose wing to the mouth corner; age (ID-AgeCreases)
  deepens the same lines rather than adding new directions.

## 3. Joints and range of motion (measured)
Soucie et al. 2010 (Haemophilia; CDC Joint ROM study), adults 20-44 (f / m, degrees): shoulder flexion 172 / 169,
elbow flexion 150 / 145, elbow extension 5 / 1, pronation 82 / 77, supination 91 / 85, hip flexion 134 / 130, hip
extension 18 / 17, knee flexion 142 / 138, ankle dorsiflexion 14 / 13, plantar flexion 62 / 55. Older adults lose
3-6 degrees. -> `pose_stress.py` limits for the rig tests; corrective shape keys are needed near the ends of these
ranges (elbow, knee, shoulder) where skin folds.

## 4. Quadrupeds and digitigrade beast legs (measured + textbook)
- Kilbourne & Hoffman 2013 (PLoS ONE 8:e78392; 44 species): limb length scales with positive allometry
  (~ body mass^0.40), limb mass isometrically (^1.0); forelimb inertial properties scale with positive allometry,
  hindlimb ones geometrically. -> Bigger quadrupeds get relatively longer legs, not just scaled-up ones.
- Posture (textbook): plantigrade (heel down: bears, humans), digitigrade (on the toes, heel = the "backwards knee":
  cats, dogs, birds, most beast-folk legs), unguligrade (on the hoof tips: horses, deer). The joint that looks like a
  backwards knee is the ankle; the real knee sits high, near the body. -> Beast-human leg options must move the
  ankle up (long metatarsus) and keep the knee at the hip-to-ankle 40-50 % point, never bend a human knee backwards.

## 5. Horns, feathers, scales, fur (measured where available)
- **Horns (textbook / abstracts):** bovid horns are a keratin sheath over a bony core growing from the base, so growth
  adds rings at the base and the curve follows a (near-)logarithmic spiral; antlers are bone and branch. -> Horn
  generator: a tapered tube swept along a log spiral, ring texture banded from the base, cross-section flattened on
  the inside of the curve.
- **Feathers:** Ho et al. 2019 (PLoS Biol 17:e3000132): feather buds form first along the dorsal midline, then rows
  are added in a spreading wave (FGF/BMP signalling with cell density), giving ordered tracts (pterylae) with bare
  areas between them. -> Feather cards in rows that follow tracts (spine, shoulders, wings, thighs), offset like
  shingles, not a uniform coat.
- **Scales:** Manukyan et al. 2017 (Nature 544:173): lizard scales form a roughly hexagonal lattice and each scale is
  one colour cell of a cellular automaton (reaction-diffusion at the scale level). Milinkovitch et al. 2013 (Science
  339:78): crocodile head scales are random polygons made by the skin cracking under growth stress. -> Two scale
  modes: body = hex lattice with per-scale colour; head/face = Voronoi-like cracked polygons.
- **Fur direction:** planar cell polarity aligns follicles; on the trunk hair points toward the tail within about
  ±45 degrees of the body axis; whorls appear where directions meet (rosette mouse study, bioRxiv
  10.1101/2023.07.27.550849). -> Fur clumps follow a direction field: head to tail on the back, down the limbs, whorls
  at the crown and where fields meet; MHS3 draws fur as big jagged tufts that follow this field.

## 6. Anime / MHS3 stylisation (style)
- Adult MHS3 males ~6.3-6.7 heads tall (brief), our dataset 6.3-8.6 (median 7.2).
- Large eyes, small nose drawn as one shadow, mouth close to the chin; jaw and cheek planes simplified but the face
  front stays convex (pass 2).
- Muscles are drawn as a few large planes and shadow shapes (deltoid cap, pectoral shelf, rib cage, abdominal block,
  quadriceps teardrop, calf) rather than individual muscle bellies; wrinkles appear only at strong expressions and
  age settings.
