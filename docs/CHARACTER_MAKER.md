# Anime Character Creator

This repository holds two products that meet at one folder layout.

The software is the standalone creator. It is built in this repository. It shows the character, the sliders, the mixer, the appearance layers, and playback. It imports finished packs. It does not sculpt the meshes.

The asset library is built later in Blender, from [CLAUDE_BUILD_PROMPT.md](CLAUDE_BUILD_PROMPT.md). Copy that prompt into Claude when you want the meshes made. Claude writes packs into `library/` and exports glTF beside the Blender sources. The software imports those folders. It does not open a live Blender session.

The remote is [lightlabpro/AnimeCharacterCreator](https://github.com/lightlabpro/AnimeCharacterCreator).

## Art

The style is anime. Monster Hunter Stories 3 is the base: adult height, soft shadow bands, a real light direction, a thin rim, painted faces, glossy eyes with one catchlight, thick hair clumps, layered cloth, leather, metal, and fur, and creature scales as large graphic plates.

Two shader presets sit on that base.

- **Breath** moves toward Breath of Fire 3 and 4: brighter painted color and cleaner illustration edges. Beast people and dragon people use this lane.
- **Legends** moves toward Mega Man Legends 2 and 3: cleaner cel bands and chunkier painted metal. Robots and wearable robot armor use this lane.

Stories is the default. Characters, costumes, monsters, and machines from those games are not copied. Extra style notes live in [style_dataset/README.md](style_dataset/README.md).

## Bodies

Four bodies. Nothing is an extreme scale of a different body.

| Body | Role |
| --- | --- |
| Adult humanoid | About 7 to 7.5 heads. The human and every human-beast share this mesh. |
| Child humanoid | About 5 to 5.5 heads. Clothed by default. No adult presentation, age, facial hair, or muscle keys. |
| Robot | Segmented machine. Separate from armor a human wears. |
| Quadruped dragon | Four legs, wings, tail, talking muzzle. Separate from the humanoid dragon person. |

Human parts and human-beast parts are one library. Any mix is valid: rabbit ears on a human, a tiger muzzle with human hands, a horn on a bird person. An archetype preset only fills values. It does not lock them.

Full-beast parts and robot parts are separate libraries. They are not offered on a humanoid, and humanoid parts are not offered on them.

Adult humanoids and the full beast have young adult, adult, and old as presets on the adult mesh. Those ages stack with feminine or masculine presentation and with mixed elements. The child body does not use them.

Archetype presets, each with a masculine adult, a feminine adult, and a clothed child: Human, Tiger, Lion, Fish, Dog, Dragon, Bird, Frog, Serpent, Rabbit, Dinosaur, Rhino, Lizard. The humanoid dragon is not the quadruped.

Recipes that keep the later animals distinct: rabbit is long ears, a short muzzle, and a puff tail; dinosaur is a reptile muzzle, a crest, scales, a thick tail, and shorter arms; rhino is a heavy muzzle, one or two horns, and thick hide; lizard is a reptile muzzle, scales, a long tail, and an optional frill. The serpent stays longer and slimmer than the lizard.

## Identity and performance

Identity is who the character is: shape, lengths, colors, hair, surface, and gear. Performance is how the face moves: gaze, blink, brows, visemes, and emotions. Performance stacks on identity. Saving a character stores identity only. Resetting a facial preview does not wipe the person.

Shape keys carry volume and facial form. Bone length carries neck, limb, and head size, scaled along the bone so a longer arm does not become a fatter arm. Corrective keys ease the seams at the extremes. Colors, veins, dirt, and cape damage are shader parameters.

The mouth is a jaw bone, visemes that include the small and mid openings, and additive emotions. Blink and talking are actions with in-betweens, not a two-frame flap. The same performance names mean the same idea on a muzzle, a shutter lid, or a human mouth.

## Library folders

Import accepts the library root or one category folder. A root import registers every pack. A category import adds only that pack. Each chosen folder has a `manifest.json` or a `pack.json`. The importer checks that `library` is `humanoid`, `robot`, or `full_beast` and matches the tree the file sits in. The report lists what was added, what was skipped, and why.

```
library/
  manifest.json
  humanoid/
    bodies/adult
    bodies/child
    morphs
    hair/front
    hair/back
    hair/sides
    hair/extras
    facial_hair
    elements/ears
    elements/muzzles
    elements/tails
    elements/wings
    elements/horns
    elements/hands
    elements/feet
    outfits
    accessories/armor
    accessories/clothing
    accessories/weapons
    accessories/robot_armor
    accessories/organic
    accessories/eyewear
    accessories/footwear
    accessories/belts
    accessories/capes
    materials
    motions
    presets
  robot/
    body
    parts
    materials
    motions
  full_beast/
    body
    elements
    accessories
    materials
    motions
    presets
```

A pack folder holds the mesh, a glTF export, and `pack.json`:

```json
{
  "id": "hair_front_blunt",
  "display_name": "Blunt fringe",
  "library": "humanoid",
  "slot": "hair_front",
  "socket": "SOC-HairFront"
}
```

Deforming clothes carry the same identity shape-key names as the body region they cover. Shoes and sealed armor may hide a body vertex group. Accessories are parented to sockets. They are not booleans cut into the body.

Hair is a large mixable set: front, sides, back, and extras, each with volume, width, length where the cut allows it, and root and tip color. Facial hair is adult-only, with length and bulk. Child hair is authored for the child head. The full lists are in the library prompt.

The first library pass ships one good exemplar of each accessory type, plus the full hair list and the creature element looks. More entries use the same pack file.

## Where the software reads this

The creator workspace is specified in [ANIME_CREATOR_CORE.md](ANIME_CREATOR_CORE.md). Blender remains the workshop for the library. The application the user opens is the standalone creator.
