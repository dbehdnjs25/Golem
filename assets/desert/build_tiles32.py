"""Build the desert's single seamless, unvaried sandy ground tile."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent / "tiles32"
SIZE = 32
COLS = 1
ASEPRITE = Path(r"C:\Users\ykb62\Desktop\aseprite.exe")

SAND = (211, 183, 119, 255)
TEXTURE_DARK = (202, 173, 109, 255)
TEXTURE_LIGHT = (222, 197, 137, 255)


def ground() -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), SAND)
    draw = ImageDraw.Draw(image)
    # A low contrast 8px repeating grain keeps the ground seamless at tile edges.
    dark = [(2, 3), (11, 1), (20, 5), (29, 2), (6, 12), (16, 10),
            (26, 14), (1, 22), (12, 19), (22, 25), (7, 30), (29, 29)]
    light = [(5, 6), (15, 4), (25, 8), (9, 16), (19, 18), (30, 20),
             (4, 27), (15, 28), (26, 31)]
    for x, y in dark:
        draw.point((x, y), fill=TEXTURE_DARK)
    for x, y in light:
        draw.point((x, y), fill=TEXTURE_LIGHT)
    return image


NAMES = ["\uae30\ubcf8 \ubaa8\ub798"]


def save_project(atlas: Image.Image, tiles: list[Image.Image]) -> None:
    if not ASEPRITE.is_file():
        raise FileNotFoundError(f"Aseprite not found: {ASEPRITE}")
    canvas_size = atlas.size
    with tempfile.TemporaryDirectory() as temp:
        tmp = Path(temp)
        names = []
        for i, (name, tile) in enumerate(zip(NAMES, tiles)):
            layer = Image.new("RGBA", canvas_size)
            layer.alpha_composite(tile, ((i % COLS) * SIZE, (i // COLS) * SIZE))
            layer.save(tmp / f"{i}.png")
            names.append(name)
        (tmp / "layers.txt").write_text("\n".join(names), encoding="utf-8")
        lua = r'''local dir=app.params.dir
local names={}
for line in io.lines(dir.."/layers.txt") do names[#names+1]=line end
local first=Image{fromFile=dir.."/0.png"}
local sprite=Sprite(first.width,first.height,ColorMode.RGB)
sprite.gridBounds=Rectangle(0,0,32,32)
for i,name in ipairs(names) do
  local layer=(i==1) and sprite.layers[1] or sprite:newLayer()
  layer.name=name
  local image=Image{fromFile=dir.."/"..(i-1)..".png"}
  sprite:newCel(layer,sprite.frames[1],image,Point(0,0))
end
sprite:saveAs(app.params.out)
'''
        script = tmp / "assemble.lua"
        script.write_text(lua, encoding="utf-8")
        subprocess.run(
            [str(ASEPRITE), "-b", "--script-param", f"dir={tmp.as_posix()}",
             "--script-param", f"out={(ROOT / 'desert-32.aseprite').resolve().as_posix()}",
             "--script", str(script)],
            check=True,
        )


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    # This biome intentionally has exactly one ground tile and no variants.
    for stale in (*ROOT.glob("desert_*.png"), *ROOT.glob("desert_*.webp")):
        stale.unlink()
    tiles = [ground()]
    atlas = Image.new("RGBA", (COLS * SIZE, ((len(tiles) + COLS - 1) // COLS) * SIZE))
    rows = []
    for tile_id, (name, tile) in enumerate(zip(NAMES, tiles)):
        x, y = (tile_id % COLS) * SIZE, (tile_id // COLS) * SIZE
        atlas.alpha_composite(tile, (x, y))
        tile.save(ROOT / f"desert_{tile_id:02}.png")
        tile.convert("RGB").save(
            ROOT / f"desert_{tile_id:02}.webp", "WEBP", lossless=True, method=6
        )
        rows.append({
            "id": tile_id, "name": name, "file": "desert_00.webp",
            "rect": [x, y, SIZE, SIZE], "category": "ground", "family": tile_id,
            "position": "\uae30\ubcf8",
        })
    atlas.convert("RGB").save(ROOT / "desert-32.webp", "WEBP", lossless=True, method=6)
    atlas.resize((atlas.width * 4, atlas.height * 4), Image.Resampling.NEAREST).save(ROOT / "desert-preview.png")
    (ROOT / "tileset.json").write_text(json.dumps({
        "image": "desert-32.webp", "tilewidth": SIZE, "tileheight": SIZE,
        "columns": COLS, "tilecount": len(tiles), "margin": 0, "spacing": 0,
        "tiles": rows,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    save_project(atlas, tiles)
    print(f"Built {len(tiles)} desert ground tiles at {ROOT}")


if __name__ == "__main__":
    main()
