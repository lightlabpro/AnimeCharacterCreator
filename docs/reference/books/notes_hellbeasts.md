# Hell Beasts - Jim Pavelec (IMPACT 2007, 292 PDF pp) - reading notes (q20)

Read: full text layer (every page, 2 chunks) + every page image (9 combined sheets hb00-hb08) + full-size
close-ups of the face pages (p100, p101, p195, p231, p273).

## Core content
- Basics: tools, gesture-first construction (primary + secondary gesture lines, a basic shape over them),
  iconic vs action poses (p20-37).
- Light and shadow (p38-39): the four basic shapes become cube / sphere / cylinder / cone through rendering. On a
  sphere lit from upper right: highlight, light, halftone, core (form) shadow = the darkest area, reflected light
  bounced back onto the shadow side, and a cast shadow that "starts out with a dark, hard edge and softens as it
  moves away from the object casting it". Cast shadows push forms back in space (p40-41); environmental lighting
  uses cast shadows from off-frame objects to steer focus (p204-207).
- Ch.1-4 humanoids, undead, dark creatures, wyrms: orc (asymmetry suggests chaos, p61), lich with a full drapery
  section - five fold types: single-point hanging, dual-point hanging, compression, zigzag, spiral (p76-79);
  zombie (p100-102), vampire, oni (near arm drawn larger to come out of the picture plane, p118), Tiamat, hydra.
- Zombie mouth (p101): with the lips gone, "draw a line to indicate the space in which the upper and lower teeth
  meet. This area, comprised of the maxilla on top and the mandible on bottom, should be treated as a rounded
  surface that the teeth wrap around." The drawing shows the bite line curving with the skull, not a flat
  horizontal.
- Were-spider face (p194-195): "construct the face with as few lines as possible, as extraneous lines take on
  the appearance of wrinkles, aging your subject"; nose = one line for the lower edge of nostrils and tip; brows
  angle sharply toward the nose; full lips; "Since the upper lip recedes into the skull from top to bottom, it
  should fall into shadow."
- Harpy (p231): age is shown by gravity on the face - sagging cheeks and jowls, shadow under cheekbones and lower
  jaw, sunken sockets, droopy lids - the opposite of a young face.
- Ch.5 winged beasts (dragon, harpy, chimera, Koshei, ropen, demogorgon), inspiration, and an anatomy appendix:
  human skulls in front / 3/4 / profile (p273), animal skulls, horns/hooves/claws, human and animal skeletons and
  musculature (p273-290).

## What this means for head_mhs3_n56 (q20)
- Teeth/tongue look flat: p101 says the teeth sit on a rounded maxilla/mandible and the bite line wraps it. Our
  tooth strips must follow an arch (curved in plan view, receding at the sides), not a flat card.
- "Looks like it has no upper lip": p195 says the upper lip faces down-and-forward-to-back, so under top light it
  falls into shadow. That supports keeping a dedicated upper-lip shadow shape (UpperLipShade) rather than
  lighting it like the lower lip.
- Young/beautiful face = few lines; every extra crease ages it (p191, p195). Cast shadows hard near the caster,
  softer away (p38) - matches a crisp shadow right under the upper lip / nose fading out.
- The p273 skull views confirm the maxilla curves back strongly at the canines in 3/4 - the mouth is not a
  flat front plane.
