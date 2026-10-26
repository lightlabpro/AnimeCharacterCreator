# Parts workflow log (q41)

One line per job: date, part, stage, tool, job id / credits used, gate numbers.

- 2026-10-25 setup: Hunyuan 3D signed in in the built-in browser (20 credits). Midjourney web needs sign-in in the built-in browser; Firefox is read-only to computer use; Discord window did not come to front.
- 2026-10-25 head_base reference: Midjourney web job ce6f3794-03ce-4ea9-8081-4001edad77b3 (1 job, niji 7, --ar 3:1, sref MHST3-Rudy_Render_001). Candidate tile 3 (0_2: front, front, side, back; clean neck). Rejected by eye: tile 2 pointed elf ears, tile 1 no back view, tile 4 patchy shading. TypeSafe gate pending (needs the PNG on the PC).
- 2026-10-25 head_base gate (parts_ref_gate.py, TypeSafe jev-1.14 both orders, controls Leia/Eleanor vs Leo, floor = weaker control - 0.05): FAIL. anime 0.930/0.910 ok, mhs3 0.410/0.835 FAIL, eyes 0.815/0.805 ok, face 0.900/0.850 ok, shading 0.780/0.710 ok, polished 0.255/0.800 FAIL, hair skipped; culprit hair, hair. prepare_reference: front, side, back cut off at the neck (rc 12), front2 usable. Hunyuan not used.
- 2026-10-25 head_base generate: Hunyuan 3.1 multi-image (front slot 2, left slot 4, back slot 6; 768 px canvas crops of ce6f3794 tile 2), 500k faces, 1 free credit (20 -> 19). Queued.
