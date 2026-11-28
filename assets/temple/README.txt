TEMPLE TILESETS

Biome folders (20 tiles each, all 32x32, PNG + Aseprite):
grassland: original gray-green stone / bronze / teal grassland temple
burnt_forest: charred basalt / ember orange
snowfield: blue-gray stone / frost / ice
wind_plateau: pale weathered limestone / wind motifs
bog: damp olive stone / moss / roots
wasteland: desert sandstone / copper / lightning motifs

Each biome's tiles32/ has a 128x160 atlas and tiles.json coordinates.
Atlas rows: floors; cardinal walls; corners; north doors/stairs/altar;
west closed, west open, east closed, east open doors.
West doors belong in the LEFT wall; east doors in the RIGHT wall.
Passages through side doors run horizontally.
Each atlas Aseprite has 20 named tile layers.
Grassland keeps the original 16 native tiles unchanged; adds 4 side doors.
biomes-overview.png: top row grassland / burnt forest / snowfield;
bottom row wind plateau / bog / desert.

Built-in image_gen sources and exact prompts live in each biome's source/.
Rebuild with Aseprite --batch --script assets/temple/build_biomes.lua.
The original tiles32/ below is retained for compatibility as grassland art.

ORIGINAL GRASSLAND SET

16 opaque 32x32 pixel tiles, PNG + Aseprite.
tiles32/temple-atlas.png and .aseprite: 128x128 atlas, 4 columns.
tiles32/tiles.json: tile names and atlas coordinates.

Row 1: plain / worn / cracked / mossy stone floors.
Row 2: north / south / west / east walls.
Row 3: northwest / northeast / southwest / southeast corners.
Row 4: closed door / open door / descending stairs / altar.

Source generated with the built-in image_gen tool; prompt in source/prompt.txt.
Native-size packaging uses Aseprite nearest-neighbor scaling and cropping.
Run python assets/temple/build_tiles.py to rebuild.
These assets are available in the gallery; game rendering is not changed.
