# Reference-match judge: first run (eyes, n47 -> n49e)

| round | analysis | TypeSafe first fix (both orders) | applied | effect |
|---|---|---|---|---|
| n47 | usable 0.95 | eye_rounder_corners | yes | no visible change |
| n48 | usable 0.95 | eye_rounder_corners | yes, double step | no visible change (head grid limits the corner shape) -> excluded |
| n49 | usable 0.94 | upper_lid_line_even | yes | outer wedge thinner (upper_lid_line 0.02 -> 0.07) |
| n49b | usable 0.94 | eye_taller / upper_lid_line_even split; tie-break upper_lid_line_even | yes | even line, short wrap (0.07 -> 0.48) |
| n49c | usable 0.94 | lower_lid_line_full (tie-break) | yes | full lower line (0.03 -> 0.54) |
| n49d | usable 0.95 | eye_taller | no: Claude's height/spacing/iris rows were eyeballed; measured, they match | analysis corrected |
| n49e | usable 0.94 | brow_arch | yes | brow arched |

After n49e: matches = pupil, flatness, height_to_width, eye_spacing; needs a human = brow colour, iris colour,
iris pattern, lower/upper lid lines; off = outline_shape, brow_shape, brow_position, iris_size (ours larger),
highlight, sclera. Boards: eyes_n47c.png ... eyes_n49e.png.
