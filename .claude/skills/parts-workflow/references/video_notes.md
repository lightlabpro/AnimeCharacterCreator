# Stefan 3D, "Ultimate Free AI Workflow for Anime 3D Character" (ibMxfcNh_oY) - notes

Read from the full caption track (q41). Times are seconds.

| t | What he does | Our version |
|---|---|---|
| 40-80 | References: head in three views and body in three views as separate sheets (long hair, so the head is separate); hands separate because fingers fail in one go; props separate | Same, and finer: one sheet per part in `part_specs.md`, head first |
| 81-101 | Hunyuan 3.1, Chinese site, Multi-image mode, drop each view in its slot, 500K faces, Generate | Same, 3d.hunyuan.tencent.com/creation in Firefox on Sammy's PC, free credits only |
| 101-160 | Reviews: body texture decent, hands from the body have merged fingers, separate hand is clean, head has a neck problem | Gate stage 2: faithful check vs sheet, `anatomy_rules.py` finger count |
| 203-470 | Blender: position parts; cut arms with mask brush/lasso mask, Mask > Slice and Fill Holes; elastic grab to tuck joins inside; cut the spare hand part the same way; Clear Mask; mirror hand: origin to 3D cursor, Ctrl+A rotation and scale, Mirror modifier, apply | Same operations through Blender MCP (bpy: mask -> separate + fill, or bmesh bisect + fill); joins hidden inside the sleeve/body |
| 465-545 | Head: smooth brush on artifacts, eyeballs rounder, grab hair forward off the body, blob brush adds neck volume | Head fixes go through the master loop; eyes must meet the rulebook eye standard |
| 545-640 | Texturing tool (Modddif) and simplify: bow 5K, head 15K, body 20K, hands 10K, generate normal map | Budgets kept; we decimate in Blender (`decimate_to_budget.py`) and bake normals ourselves - no third-party upload needed |
| 640-790 | Projection texturing from each view, upscale, patch black lines and eyelash backs | Optional; free tier only. Default: Hunyuan texture + Blender texture-paint patching |
| 787-830 | Export (FBX is Pro tier - avoid), reassemble in Blender | GLB only (free) |
| 827-990 | Mixamo rig (OBJ upload, markers, standard skeleton), scale 100x, reassign materials, parent prop to hand bone, weight fix: neck 0 on the face, head 100 | We rig with our `DEF-` rig for the app contract; keep the head/neck weight rule |
| 990-1130 | VRM add-on for MToon in Blender: connect lit and shade colour textures, outline | We keep the locked MHS3 shader `vroid_toon.py`; MToon only if Sammy asks |
| 1130-1320 | Unity 6.3 Universal 3D, unpack textures, FBX, Package Manager git URL `com.unity.toonshader`, Toon material: base map, first shading feather, normal map, rim light (feather off), outline width + black | Stage 9 |

Lesson for us: split anything the generator gets wrong into its own sheet and generation, then join it in Blender at a
cut that ends up hidden.
