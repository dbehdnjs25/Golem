# Item art redraw

48 inventory icons generated with built-in image_gen, using the user-edited
grassland tree as the visual reference. All prompts are recorded in prompts.json.
Existing files were backed up in backup/ before replacement. Source renders live
in source/; final 32x32 PNGs and monochrome-layer Aseprite files live in final32/.
The matching files in ../items/ are the runtime assets once installed.

Each material has one Base, Highlight and Shadow color, plus a shared outline.
prepare.py exports available sources through native Aseprite Lua. validate.py
checks layer colors, exact PNG/native equality, transparency and silhouette edges.
preview32.lua produces a sheet: each cell shows 3x native size and actual 32px native size.
No src/ or tiles32/ changes are part of this task.

Tools face upper-left with the handle ending lower-right. align_tools.lua
mirrors the six originally opposite sprites from direction_backup/ and preserves
their monochrome layers. Run it before preview32.lua if rebuilding those sources.

All 15 axes/pickaxes share the entire identical wooden shaft, including its top
protrusion, joint and lower end. unify_full_handles.lua is the current tool builder;
it supersedes the partial-grip shared_handles.lua. It combines one shaft template
with axe/pick head shapes and material palettes. Handle / Base, Highlight, Shadow
layers are separate from Head layers. shared_handle.png is the common pixel template.
Run unify_full_handles.lua before preview32.lua when rebuilding these tools.
The shared shaft now follows the original crude axe's irregular wooden stick,
including bark shading and a thicker rounded end, rather than a straight rod.
The head/shaft joint has two shaded cord turns and a small knot, stored in
separate monochrome Binding layers. This covers the abrupt seam at the socket.

The requested final size is 32x32, superseding the earlier 48px and 16px drafts.
final/ and final16/ contain intermediate versions, not the delivered icons.
The final crude axe generation prompt is recorded in crude_axe_prompt.txt.
The final hide, cooked_meat and potion prompts are recorded in final_prompts.txt.
Run prepare.py, Aseprite -b --script preview32.lua, then install32.py to export,
validate and install. The installer preserves replaced files in before_install32/.
Do not run the older ../build_item_icons.py: it recreates the superseded procedural icons.

Preview/atlas order, left to right then top to bottom:

1. core_shard
2. twig
3. pebble
4. grass
5. charcoal
6. copper_ingot
7. iron_ingot
8. gold_ingot
9. brass_ingot
10. steel_ingot
11. obsidian
12. obsidian_stone
13. frost_crystal
14. weathered_stone
15. bog_moss
16. thunder_stone
17. crude_axe
18. wood_pick
19. stone_pick
20. copper_pick
21. iron_pick
22. gold_pick
23. brass_pick
24. steel_pick
25. wood_axe
26. stone_axe
27. copper_axe
28. iron_axe
29. gold_axe
30. brass_axe
31. steel_axe
32. bench
33. smelter
34. hearth
35. fine_bench
36. blast_furnace
37. burnt_forest_detector
38. snowfield_detector
39. wind_detector
40. bog_detector
41. wasteland_detector
42. staff
43. worn_pack
44. leather_pack
45. hide
46. raw_meat
47. cooked_meat
48. potion
