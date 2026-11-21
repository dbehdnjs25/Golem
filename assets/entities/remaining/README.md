# Remaining entity artwork

Seven single-frame idle sprites, matching the basic tree's muted pixel-art style.
The other Codex owns player, wolf, rabbit, golem, burnt_forest_golem,
snowfield_golem, and wind_plateau_golem. This batch owns only bog_golem,
wasteland_golem, burnt_lord, frost_lord, gale_lord, bog_lord, and storm_lord.

Final PNG and Aseprite files live one directory above this document. Stable
filenames match the entity kind keys. See manifest.json for sizes and anchors.
Use nearest-neighbor scaling and position by midbottom. These are static idle
poses, not movement/attack animation sheets. Runtime integration is pending:
src/ and every biome tiles32/ directory were explicitly outside this task.

Artwork generated with the built-in image_gen tool; complete prompts are in
prompts.json and original transparent sources in source/. Native Aseprite Lua
prepares pixel dimensions and disjoint monochrome Outline / material Base /
Highlight / Shadow layers. Each material uses three solid shades, no gradients.

prepare.lua is self-contained and refuses to overwrite existing final assets.
Run with Aseprite -b --script prepare.lua (root parameter can override assets/entities).
validate.py checks native layer colors, alpha, contour, padding and PNG equality.
For individual exports pass --script-param key=bog_golem before --script.
preview.lua builds the native pixel-art comparison sheet with the reference tree.
Preview order: tree, bog golem, wasteland golem, burnt lord; frost lord,
gale lord, bog lord, storm lord.
