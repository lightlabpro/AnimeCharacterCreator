# Anime Character Creator core

This is the control specification for the standalone application. The layout should feel familiar to someone who has used a character creator with a library, a viewport, and a slider panel. The icons, colors, type, and wording are original. Product names, logos, and panel chrome from other software are not used.

The asset meshes come from the library folders in [CHARACTER_MAKER.md](CHARACTER_MAKER.md). This application imports those folders. It does not sculpt them.

## Workspace

- **Center.** Real-time viewport. Orbit, frame, saved cameras, and a turntable. Dragging a highlighted head or body region morphs that region. A front-view drag and a side-view drag are different axes, so skull width and skull depth are not the same gesture. A gizmo moves the selected accessory.
- **Left.** Content library. Categories: Actor, Head, Body, Hair, Facial Hair, Elements, Outfit, Accessory, Material, Motion, Expression. Double-click applies a pack. Hair splits into a full style, a group (hair, brows, beard), and an element. Elements stay mixable after a style is applied.
- **Right.** Modify. Tabs: Attribute, Pose, Morphs, Material, Physics. Morphs has a filter, a search box, and a tree: Currently Used, Favorites, then Head, Body, Elements, Age, and Presentation. Sub-items expand under the selected node. Sliders run from -100 to 100. Bake commits the current shape and clears the sliders. Reset clears the sliders without baking.
- **Mixer.** A wheel blends a whole head or one part: eyes, nose, mouth, skull, ears, or muzzle. Editing sets the current face. Mixing blends saved faces. An expression preview plays on top and does not write identity. Wheels can be saved and loaded. Randomize stays inside the documented ranges. A family action derives a child and the three adult ages from the current mix, and does not copy adult-only sliders onto the child.
- **Appearance.** One editor, two pages: Skin and Makeup. Each material (head, body, arms, legs, nails) has its own layer stack. A layer has opacity, a mask, hide, reorder, merge, and flatten. Categories for this project: skin color, blush, lips, nails, veins, body hair, dirt, scars, markings, and wrinkle masks. This is painted anime skin, not a pore stack.
- **Face profile.** Separate from identity morphs. An expression set and a viseme set. The rig is hybrid: bones for the jaw, the eyes, and the head; morphs for the lips, the lids, the brows, and the correctives. Wrinkle regions have a strength. The play bar is how those wrinkles are checked. Neutral, reset region, and reset all are explicit.
- **Bottom.** Play bar for blink, the talking loop, the pose library, and wrinkle preview. Reset Performance does not reset identity.

Body kind is the first control: Adult humanoid, Child humanoid, Robot, Quadruped dragon. Changing it loads that body and swaps the visible sliders.

## How it should feel

- Labels are plain words. "Mouth" rather than an internal key name. A short hint on hover.
- A new character opens on the human body, dressed, with the Stories style already applied.
- Search, Favorites, and Currently Used stay visible.
- A slider shows its number, drags in small steps, and double-click resets that slider only.
- Undo covers morphs, clothes, and colors.
- A preset fills values and leaves every control editable. It never locks the panel.
- Body kind, age, and presentation sit at the top of Modify, before the long element list.
- Controls that do not apply to the current body are hidden.
- Touching a slider highlights the region it moves.
- Reset Identity and Reset Performance are separate buttons.

## What the panels edit

Identity is shape, length, color, hair, surface, and gear. Performance is gaze, blink, brows, visemes, and emotions. The save file stores identity. The current viseme is not stored.

On an adult humanoid, presentation is feminine or masculine: shoulders, chest, waist, hips, face softness, and height. Age is young adult, adult, or old. Young adult softens the cheeks and reduces creases. Adult is the basis. Old adds creases, a softer jaw, a mild stoop, and a wrinkle mask, and may suggest gray hair without locking the color. Age and presentation stack with any mix of human and beast elements.

The child panel has the element list and the child hair. It does not have adult presentation, adult age, facial hair, or muscle keys. The default outfit is on.

The full beast has the three ages and its own sliders: size, neck, tail, wings, legs, snout, horns, and colors. It does not have human presentation. The robot has chassis, paint, emissive, and wear. It does not have hair, nails, or skin.

Human and human-beast looks share one list and can be combined. Full-beast assets and robot assets never appear in that list.

Style is a shader preset: Stories, Breath, or Legends. Stories is the default.

## Import

File > Import Library asks for a folder.

- If the folder is the library root, every pack under it is registered.
- If the folder is one category, only that pack is added.
- The importer reads `manifest.json` at the chosen folder when it exists, and `pack.json` in each pack.
- A pack whose `library` field does not match the tree it sits in (`humanoid`, `robot`, or `full_beast`) is skipped.
- The dialog then lists added packs, skipped packs, and the reason for each skip.

Imported hair, elements, outfits, and accessories show up in the left library and can be double-clicked onto the current character when the body kind allows that library.

## Face playback

Blink eases shut, holds a slight squeeze, and opens more slowly than it closed. A wink is a blink on one side. Talking steps through closed, small, mid, a vowel, and back. The pose library previews Neutral, SoftSmile, Happy, Laugh, Sad, Cry, Angry, Shout, Surprised, Skeptical, Sleepy, Focused, and Disgusted on the current identity, including a muzzle when one is equipped.

Gaze is a bone, with the upper lid following so the iris stays inside the lid. Visemes and emotions are morphs, including the openings between closed and wide, and they are tested with the jaw shut and open.

## Out of scope for the first application

Head fitting from a photograph is a later import tool, not the first screen. A full scene editor, cameras for filmmaking, and a second renderer are not part of this creator. The viewport only has to show the character, the equipped packs, and the style preset clearly.
