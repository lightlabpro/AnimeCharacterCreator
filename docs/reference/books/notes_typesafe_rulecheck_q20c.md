# TypeSafe rule check (run_q20c, 2026-10-16) - summary

Second batch: the 18 books read in q20 part 2 (cartooning_epub, dragonart, fantasyarch, force_animal, force_life,
graphicnovel, hellbeasts, howtodraw, landscape, maps_epub, mechanika, mgs, penink_epub, penpencil, perspective_easy,
render, steampunk, understandarch). TypeSafe (`typesafe_book_reader.py --only-rule-pages`) re-read every page a
Claude rule cites and scored whether that page supports the rule (best page score shown; both option orders asked).
Log: `_ab/books/run_q20c.log` - ALL DONE, 0 errors. 127 rules checked. Parts with no cited pages produced empty files
(cartooning part 3, graphicnovel part 2, howtodraw part 2, understandarch part 2).

## Confirmed (>= 0.85)
Most rules, including the ones this head work leans on:
- Mouth / teeth: hb_teeth_wrap 0.96, ct_open_teeth 0.98, hb_upper_lip_shadow 0.86, r_upper_lip_cylinder 0.86.
- Turned views: gn_eye_wrap 0.97, gn_far_eye 0.85, hb_near_larger 0.96, fa_near_eye 0.96, pe_wide_vps 0.98,
  h_50mm 0.98, pe_narrow_field 0.94.
- Face construction: ct_eye_four 0.97, ct_jaw_half 0.91, ct_small_features 0.97, ct_planes 0.93, hb_few_lines_young
  0.93, hb_nose_one_line 0.96, da_eye_socket 0.95, da_happy_eyes 0.95, gn_quasimodo 0.95, fl_head_box 0.93.
- Light and value: all 13 fantasyarch rules 0.94-0.99, r_core_shadow 0.98, r_occlusion 0.96, ua_light_45 0.94,
  ua_raking_light 0.97, pe_shade_edge 0.93, pp_dark_accents 0.85, mp_no_pure_black 0.98.
- Readability: all mechanika rules 0.84-0.99 (silhouette, squint, flip check, head first).

## Partly supported (0.45-0.75) - use with care
- Profile / far eye from Manga Guide: mg_far_eye_inside 0.60, mg_profile_wedge 0.56; graphicnovel gn_near_corner 0.60,
  gn_profile_mistakes 0.50. As in q20b (c_profile_eye_quarter, r_profile_eye 0.34), TypeSafe does not clearly find the
  "profile eye is a short wedge" claim on the cited pages. It stays a Claude reading backed mainly by the online
  sources (AnimeOutline) and Borgman's p114/p120 drawings.
- ct_female_upper_lip 0.67, ct_top_lid_dark 0.70, ct_features_low_young 0.45, fl_neck_oppose 0.71,
  pe_eye_level 0.72, pe_parallel_converge 0.72, mp_line_hierarchy 0.52, pp_paper_affects 0.61.

## Not supported on the cited page (< 0.4) - treat as Claude-only
ct_oval_perspective 0.12, hb_sphere_values 0.28, hb_cast_pushes_back 0.03, hb_asymmetry_chaos 0.21,
hb_fold_types 0.04, pi_lit_edge_no_line 0.15, pp_spot_blacks 0.13, mg_few_lines 0.35.
Several of these are probably a page-number mismatch (rule text from a spread, or a caption on the next page)
rather than a wrong rule, but they are not counted as confirmed. None of them drove a change to the head.
