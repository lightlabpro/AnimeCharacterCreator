---
name: mhs3-master-loop
description: MASTER RULE for every head / face change on the anime character - the mandatory measure, change, render, validate loop that forces the mhs3-rulebook, mhs3-shader-match, face-gate, head-shape-audit and reference-match-judge skills, TypeSafe and TypeSafe image, per-region mesh analysis in Blender and the version lessons; iterate until every rule passes the strict threshold. Use for any head, eye, brow, nose, mouth, jaw, ear, skin or shading change, before showing a result to Sammy, and before export.
---

# Master loop: no head change without measured validation

Sammy (q36, 2026-10-18): "make a master rule that always forces you to use the skills you acquired and made from the
3d model references, the dataset, the trial and errors of the versions, they must integrate typesafe and typesafe
image, all the analysis you have previously done by dividing the model head into sections and analyzing per region,
vertex, faces and lines in blender ... Validation is always strictly necessary and must not be skipped. Iterations
must be validated and done until your margin of error threshold is at a minimum (make it extremely strict)."

## The loop (every iteration, no step skipped)
1. **Read the standards.** Read the `mhs3-rulebook` (`knowledge/mhs3_face_rules.json`: rules, eye_shape_template,
   lessons), the `mhs3-shader-match` spec, and Sammy's latest words. A new complaint becomes a rule first (a
   `mhs3-rulebook` step), and must fail the version he complained about.
2. **Change one region at a time.** Use the knobs in `blender/head_vroid/mhs3_reshape.py` (K) and
   `mhs3_paint.py` (K). Prefer the fitters over guesses:
   - `mhs3_fit_profile.py` fits the profile rules, using the mesh only;
   - `mhs3_fit_eyes.py` fits the eye-shape standard (mesh proxy `mhs3_eye_proxy.py`, bias-corrected from the last
     render with `--bias <render>_rm.json`).
3. **Mesh check.** `mhs3_warp_np.py` (numpy warp of `vroid_mesh.npz`), then
   `mhs3_measure.py --orig vroid_mesh.npz`. This is the per-region analysis on the real vertices and faces: profile
   ray casts, landmarks, widths, ears. Every mesh rule must pass before rendering.
4. **Build and render with the locked spec.** Build the GLB with `mhs3_reshape.py IN.glb TEX_DIR OUT.glb --knobs`.
   On Sammy's PC run `vt_go2(key)` (front, 34, side, eye_close, prof_close) and `vt_y70(key)`. Stage the renders
   back.
5. **Validate.** Run:
   `python3 blender/head_vroid/mhs3_validate.py OUT.json --mesh meas.json --render front.png --ts TSDIR --prev approved.json`
   - Exit 0 = pass, 12 = a rule failed, 13 = something unmeasured. Unmeasured is never a pass.
   - TypeSafe (`blender/tools/typesafe_defects.py` and `typesafe_anime_check.py`, images on, both orders, on the PC
     through `ts_bg`) answers the rulebook's TypeSafe sets. A missing key stops the loop: tell Sammy, never fake a
     judgment.
6. **Face gate.** Run the `face-gate` skill (book rules, MHS3 look per element, no regression against the version
   Sammy approved). Use the `head-shape-audit` skill when the form looks wrong but the rules pass. Use the
   `reference-match-judge` skill when TypeSafe names an element but not the fix.
6b. **Strict regression gate (hard, q36b/q36c).** On the PC:
   `py -3 blender/tools/mhs3_strict_gate.py OUT.json --cand <new>_g1 --cand-fresh <new>_g2 --base <accepted>_g1 --base-fresh <accepted>_g2`
   - sync `vroid_toon.py` to the PC and check its sha1 against the repo; render baseline and candidate twice each
     (`_g1`, `_g2`) in the same session - the gate refuses on drift (> 1.0 mean pixel difference) or when the
     render spec sidecars (`<prefix>_spec.json`) differ from each other or from the rulebook's locked shader;
   - TypeSafe A/B with pictures on 6 renders x 3 runs x both orders, against every baseline: losing overall or
     head_shape in ANY run fails; a majority loss on eyes / nose_mouth / jaw_chin / face_shading / clean fails;
   - anime check x 3 runs x 3 MHS3 references (no drop beyond 1 SE, mhs3 up by > 2 SE), defect regression;
   - `--sanity` (baseline vs itself) must give zero winners; `--screen --views ...` is for diagnosis only.
   Nothing is shown to Sammy without a PASS. q36: m46 passed all measured rules and looked worse; q36c: a stale
   baseline render made every side-view verdict wrong.
7. **Look.** Check the pupil-aligned eye crop, the board, and the profile next to face_profile_04. A detector that
   misreads gets fixed before its number is trusted. Note it in `lessons`.
8. **Repeat or stop.**
   - Fix the worst `err_tol` first, then re-run steps 3-7.
   - **Pass** = every rule has err_tol <= 1.0, RMS <= 0.5, every TypeSafe threshold is cleared, and nothing
     regressed by more than 0.25 tol.
   - If a rule cannot be met after honest attempts, stop changing and report it to Sammy with numbers and the board.
     Never widen a tolerance, drop a rule or skip a check to get a pass.
9. **Record.** Add a log entry (`docs/qa/head_v2/log.md`) with the validator table, the board, and new lessons in the
   rulebook. Then commit.

## Never
- Show Sammy a version that skipped step 3, 5, 6 or 6b (the A/B gate against the version he accepted).
- Judge by eye when a rule exists.
- Change the light or shader to rescue a model rule.
- Compare mesh-D with render-D, or pixels between differently framed renders.
- Shrink the eyes or add a lid glare (q34b), or add a lash tail or a tilted, Egyptian opening (q35, q36).
