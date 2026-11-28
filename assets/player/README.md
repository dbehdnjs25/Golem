# White player character

Original minimal white pixel character: large round head, small body, black dot
eyes, no clothing or accessories. Built-in image_gen source and prompt are in source/.

- player_down.png / player_up.png / player_left.png / player_right.png: 32x32.
- Matching individual .aseprite files: four editable monochrome layers.
- player.aseprite: four frames, tagged down, up, left, right, one frame each.
- player_sheet.png: 128x32, left to right down / up / left / right.
- preview.png: enlarged and native-size views in the same order.
- Anchor: bottom center at (16,30). Nearest-neighbor scaling recommended.

These are four idle direction poses, not a walking animation.
Runtime integration is pending; src/ was not changed.
Native export: aseprite -b --script source/export.lua.
Validation: aseprite -b --script source/validate.lua.

Arms are detached from the torso with a transparent gap in all four views.
source/separate_arms.lua applies this revision from source/before_arms.aseprite;
run it after the initial export if regenerating. Front/back have two detached
arms, while side views show one detached near arm.
