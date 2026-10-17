# TypeSafe rule check (run_q20b, 2026-10-16) - summary

TypeSafe re-read the exact pages each Claude rule cites and scored whether the page supports the rule
(probability, both picture orders agree). 0 errors, ALL DONE.

- Strongly confirmed (>=0.9): marvel m_egyptian, m_face_cylinder, m_flatness, m_profile_square, m_nose_quarter,
  m_mouth_triangle, m_nose_third, m_eye_not_long, m_mouth_forward, m_underside_lines; chardesigner c_eye_apart,
  c_mouth_third, c_volume_keep, c_jaw_age (0.98); manga12 r_lens_tones, r_ear_middle, r_open_mouth_shade (0.98);
  urban p_diminish_both, p_block_first, p_foreshorten_flat, p_ellipse_no_points.
- Partly: marvel m_upper_lip_forward 0.87; urban p_ellipse_offset 0.71.
- Weak (0.34): both profile-eye rules (chardesigner c_profile_eye_quarter, manga12 r_profile_eye). TypeSafe did
  not find the profile-eye claim on those pages from the picture alone; treat them as Claude-only readings.
- fantasyart parts 2-3 had no rule pages (all rules cite part 1).
