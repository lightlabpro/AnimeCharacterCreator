# Anime Character Creator

A standalone character maker for original anime characters. The default look is the painted **Stories** style, with **Breath** and **Legends** as alternate picture styles. It builds four bodies:

- **Adult humanoid**: humans and every human-beast (tiger, lion, fish, dog, dragon, bird, frog, serpent, rabbit, dinosaur, rhino, lizard). Species elements mix freely, and species presets never lock sliders.
- **Child humanoid**: always clothed and general audience. It has no adult presentation, age, facial hair, or muscle sliders.
- **Robot**: a segmented machine with its own parts library.
- **Quadruped dragon**: four legs, wings, a tail, and a talking muzzle.

Humanoid, robot, and full-beast libraries never mix. A pack from one library can't be put on another body.

Everything ships as procedural placeholder rigs, so the app works before any Blender assets exist. Packs imported from the library replace or add to those placeholders.

## Run it

PowerShell blocks `npm.ps1`, so use `npm.cmd`.

```powershell
npm.cmd install
npm.cmd run app        # build, then open the desktop app
npm.cmd run app:dev    # desktop app with hot reload
npm.cmd run dev        # browser only, at http://localhost:5173
npm.cmd test           # unit tests
npm.cmd run typecheck
npm.cmd run build
```

In the browser, Import Library uses a folder picker. It cannot see the folders above the one you pick, so each pack's own library tag is used. The desktop app reads real paths and checks every pack against its folder tree.

## Layout

- **Library** (left): Actor, Head, Body, Hair, Facial Hair, Elements, Outfit, Accessory, Material, Motion, Expression, and Favorites. It has search, and every item can be starred. Click an item to read about it, and double-click to apply it. Imported packs show only on the body they belong to.
- **Viewport** (center): camera presets, turntable, picture style, screenshot, and saved views. Click a body region to open its sliders. With **Drag shape** on, drag a region to edit it; the front and side views drive different axes. Click worn gear to show the fit gizmo.
- **Play bar** (bottom): blink, winks, talking, and the wrinkle check, with loop and speed controls. Also body poses, auto blink, the wrinkle preview, and Reset Performance.
- **Right panel**:
  - **Modify** has five tabs:
    - Attribute: body, style, species, presentation, age, worn items, and actions.
    - Pose: body pose, gaze, head, expression, and viseme.
    - Morphs: sliders from −100 to 100 with search, Currently Used, Favorites, Bake, and Reset.
    - Material: colors and skin tones.
    - Physics: hair, cape, tail, and wings.
  - **Mixer**: a six-slot face wheel with a scope. Fill slots from the current face, a species, or a family member.
  - **Appearance**: skin and makeup layers for each zone, with a mask, opacity, reorder, merge down, and flatten.
  - **Face**: rig mode, per-character expression edits, manual face keys, visemes, and wrinkle strength.

Identity and performance are separate. Saving a character stores identity only. **Reset Identity** keeps the current face performance, and **Reset Performance** leaves the character untouched.

## Shortcuts

| Key | Action |
| --- | --- |
| Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+I | New, open, save, import library |
| Ctrl+Z / Ctrl+Y (or Ctrl+Shift+Z) | Undo, redo |
| 1 / 2 / 3 / 4 / 0 | Front, three-quarter, side, face, frame all |
| T / D | Turntable, drag shape |
| W / E / R | Gizmo move, rotate, scale |
| B | Blink |
| Esc | Deselect |

Double-click any slider to reset it. A drag on a slider or in the viewport is one undo step.

## Library import

Choose either the library root (the folder holding `humanoid/`, `robot/`, and `full_beast/`) or any single category folder inside one of them. Each `pack.json` must include `id`, `display_name`, `library`, and `slot`. Its library must match the tree it sits in, and it must agree with `manifest.json` when the root has one. After each import, a report lists what was added, what was replaced, and what was skipped, with the reason for each skip. See [library/README.md](library/README.md) and [docs/CLAUDE_BUILD_PROMPT.md](docs/CLAUDE_BUILD_PROMPT.md) for the export contract: `ID-` identity shape keys, `PF-` face performance keys, `DEF-` bones, and `SOC-` sockets.

## Source map

- `src/model`: identity, controls, looks, presets, performance, mixer, and appearance. These are plain data and functions.
- `src/state/store.ts`: the app state, with undo, live edits, and pack application.
- `src/library`: the importer and the desktop and browser file access.
- `src/viewport`: the Three.js engine, toon shading, the procedural humanoid, robot, and dragon, accessories, and glTF pack loading.
- `src/ui`: the React panels.
- `electron`: the desktop shell and the `pack://` protocol for library files.
- `tests`: the importer and character model tests.
