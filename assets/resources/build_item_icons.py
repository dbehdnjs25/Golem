"""Build catalogue-matched 32px inventory icons and an editable Aseprite sheet."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from game.items.item_kinds import ITEM_KINDS  # noqa: E402

OUT = ROOT / "assets" / "resources" / "items"
ASEPRITE = Path(os.environ.get("ASEPRITE", r"C:\Users\ykb62\Desktop\aseprite.exe"))
SIZE = 32
COLS = 6
ROWS = 8
INK = (35, 37, 34, 255)
HANDLE = (112, 76, 48, 255)
HANDLE_LIGHT = (159, 112, 68, 255)

KEYS = (
    "core_shard", "twig", "pebble", "grass", "charcoal",
    "copper_ingot", "iron_ingot", "gold_ingot", "brass_ingot", "steel_ingot",
    "obsidian", "obsidian_stone", "frost_crystal", "weathered_stone", "bog_moss", "thunder_stone",
    "crude_axe", "wood_pick", "stone_pick", "copper_pick", "iron_pick", "gold_pick", "brass_pick", "steel_pick",
    "wood_axe", "stone_axe", "copper_axe", "iron_axe", "gold_axe", "brass_axe", "steel_axe",
    "bench", "smelter", "hearth", "fine_bench", "blast_furnace",
    "burnt_forest_detector", "snowfield_detector", "wind_detector", "bog_detector", "wasteland_detector",
    "staff", "worn_pack", "leather_pack", "hide", "raw_meat", "cooked_meat", "potion",
)


def rgba(color: tuple[int, int, int]) -> tuple[int, int, int, int]:
    return (*color, 255)


def shade(color: tuple[int, int, int], factor: float, offset: int = 0) -> tuple[int, int, int, int]:
    return tuple(max(0, min(255, round(channel * factor + offset))) for channel in color) + (255,)


def make_icon(key: str, color: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    main, light, dark = rgba(color), shade(color, 1.2, 10), shade(color, .62)

    def poly(points, fill=main, outline=INK):
        d.polygon(points, fill=fill, outline=outline)

    def rect(box, fill=main, outline=INK):
        d.rectangle(box, fill=fill, outline=outline)

    def line(points, fill=main, width=1):
        d.line(points, fill=fill, width=width, joint="curve")

    def rock(cx=16, cy=17, fill=main):
        points = [(cx-10,cy+5),(cx-9,cy-2),(cx-4,cy-8),(cx+3,cy-10),
                  (cx+9,cy-5),(cx+11,cy+2),(cx+7,cy+8),(cx-2,cy+10),(cx-8,cy+8)]
        poly(points, fill)
        d.line([(cx-5,cy-4),(cx,cy-7),(cx+4,cy-5)], fill=light, width=2)
        d.point((cx+4,cy+1), fill=dark)

    def crystal(cx=16, cy=16, fill=main):
        poly([(cx,cy-12),(cx+7,cy-5),(cx+6,cy+5),(cx,cy+12),(cx-7,cy+5),(cx-6,cy-5)], fill)
        line([(cx,cy-10),(cx,cy+10)], light, 2)
        poly([(cx,cy-10),(cx+5,cy-4),(cx,cy-1)], light, None)
        poly([(cx,cy-1),(cx+5,cy-4),(cx+4,cy+4)], dark, None)

    def tool(kind: str, head_color: tuple[int, int, int]):
        # The shared handle/head silhouettes keep tiers related; only the head alloy changes.
        line([(8,27),(22,10)], INK, 7)
        line([(8,27),(22,10)], HANDLE, 4)
        line([(10,24),(13,20)], HANDLE_LIGHT, 1)
        hc = rgba(head_color)
        if kind == "pick":
            line([(15,11),(21,7),(27,10)], INK, 6)
            line([(15,10),(21,6),(27,9)], hc, 3)
            d.point((16,8), fill=light)
        else:
            poly([(17,12),(19,5),(25,4),(28,8),(25,16),(21,15)], hc)
            line([(21,7),(25,6)], light, 2)

    if key == "core_shard":
        crystal(16,16,main)
        poly([(16,6),(19,11),(16,16),(13,12)], light, None)
        d.point((11,22), fill=light)
    elif key == "twig":
        line([(6,25),(25,7)], INK, 5); line([(6,24),(25,6)], main, 3)
        line([(14,17),(12,10)], INK, 3); line([(14,17),(12,10)], light, 1)
        line([(19,12),(25,14)], INK, 3); line([(19,12),(25,14)], main, 1)
    elif key == "pebble":
        poly([(6,21),(7,14),(12,9),(20,8),(26,13),(27,20),(22,25),(12,26)], main)
        line([(10,15),(14,11),(19,11)], light, 2); d.point((22,18), fill=dark)
    elif key == "grass":
        for pts in [[(8,25),(9,15),(12,20),(14,9),(16,25)],
                    [(14,25),(19,12),(20,19),(25,15),(23,25)]]:
            line(pts, INK, 3); line(pts, main, 1)
        line([(7,26),(26,26)], dark, 2)
    elif key == "charcoal":
        poly([(6,22),(8,13),(14,7),(23,9),(27,16),(24,24),(15,27)], main)
        line([(11,14),(16,10)], light, 2); d.point((21,21), fill=dark)
    elif key.endswith("_ingot"):
        poly([(5,14),(10,9),(23,9),(28,14),(24,23),(8,23)], main)
        line([(10,14),(24,14)], light, 2)
        line([(9,19),(23,19)], dark, 1)
    elif key == "obsidian":
        crystal(16,16,main)
        poly([(16,5),(20,12),(16,15)], light, None)
        line([(9,23),(14,19)], dark, 1)
    elif key == "obsidian_stone":
        rock(15,18,main)
        poly([(20,15),(23,8),(26,15),(24,20),(20,21)], (74,58,86,255))
        line([(23,10),(23,17)], light, 1)
        # Preserve the catalogue-colour rim pixel used by the world fragment.
        d.point((25,16), fill=main)
    elif key == "frost_crystal":
        crystal(16,16,main)
        line([(10,14),(22,14)], light, 2); d.point((12,10), fill=light)
    elif key == "weathered_stone":
        rock(16,17,main)
        line([(11,17),(14,15),(17,17),(20,14)], light, 1)
        d.point((12,22), fill=dark)
    elif key == "bog_moss":
        # Low clustered moss tufts with a few broad leaf pixels, no rock base.
        for x,y in [(10,18),(16,15),(22,19)]:
            d.ellipse((x-4,y-4,x+3,y+2), fill=main, outline=INK)
            d.point((x-1,y-2), fill=light)
        line([(7,23),(25,23)], dark, 2)
    elif key == "thunder_stone":
        rock(16,17,main)
        poly([(18,9),(13,17),(17,17),(14,24),(22,15),(18,15)], (255,231,142,255), INK)
    elif key == "crude_axe":
        line([(8,27),(22,10)], INK, 6); line([(8,26),(22,9)], HANDLE, 3)
        poly([(17,13),(17,6),(23,4),(28,9),(24,16),(20,16)], (132,126,110,255))
        d.line([(20,8),(23,7)], fill=light, width=1)
        d.point((18,13), fill=HANDLE_LIGHT); d.point((20,15), fill=HANDLE_LIGHT)
    elif key.endswith("_pick"):
        tier = key[:-5]
        head = (150,110,70) if tier == "wood" else color
        tool("pick",head)
    elif key.endswith("_axe"):
        tier = key[:-4]
        head = (150,110,70) if tier == "wood" else color
        tool("axe",head)
    elif key in {"bench", "fine_bench"}:
        rect((5,10,27,16), main); line([(7,10),(24,10)], light, 2)
        rect((8,17,11,26), HANDLE); rect((22,17,25,26), HANDLE)
        line([(10,20),(23,20)], dark, 1)
        if key == "fine_bench":
            rect((13,4,19,9), dark); d.point((16,6), fill=light)
            d.rectangle((5,15,27,17), fill=light)
    elif key in {"smelter", "hearth", "blast_furnace"}:
        if key == "smelter":
            poly([(6,12),(10,7),(22,7),(27,12),(25,25),(8,25)], main)
            rect((12,15,21,22), (226,113,54,255)); rect((14,18,19,23), (250,189,83,255), None)
            d.rectangle((20,3,24,8), fill=dark)
        elif key == "hearth":
            poly([(5,18),(9,12),(23,12),(27,18),(24,25),(8,25)], main)
            poly([(12,18),(12,13),(16,8),(18,13),(22,10),(22,19),(18,22),(13,22)], (233,124,53,255))
            d.point((17,15), fill=(255,217,105,255))
        else:
            poly([(8,26),(8,11),(12,6),(20,6),(24,11),(24,26)], main)
            rect((12,2,20,7), dark); rect((12,15,20,23), (222,100,51,255))
            rect((14,18,18,23), (255,186,74,255), None)
    elif key.endswith("_detector"):
        # A common compass body with a small biome-coded face and pointer.
        d.ellipse((5,5,26,26), fill=dark, outline=INK, width=2)
        d.ellipse((8,8,23,23), fill=main, outline=light, width=1)
        if key == "burnt_forest_detector":
            poly([(16,10),(19,15),(17,15),(18,20),(13,16),(15,15)], (255,178,91,255), None)
        elif key == "snowfield_detector":
            line([(16,10),(16,21)], light, 2); line([(11,13),(21,18)], light, 1); line([(21,13),(11,18)], light, 1)
        elif key == "wind_detector":
            line([(10,13),(19,13),(21,11)], light, 1); line([(12,17),(22,17)], light, 1); line([(9,20),(16,20)], dark, 1)
        elif key == "bog_detector":
            poly([(16,10),(20,15),(18,20),(14,20),(12,16)], (132,165,84,255), None)
            d.point((16,14), fill=light)
        else:
            d.ellipse((12,12,19,19), fill=(249,224,133,255))
            for x,y in [(16,9),(16,22),(9,16),(22,16)]: d.point((x,y), fill=light)
        line([(20,21),(27,28)], INK, 4); line([(20,21),(27,28)], HANDLE, 2)
    elif key == "staff":
        line([(9,27),(22,7)], INK, 5); line([(9,26),(21,7)], HANDLE, 3)
        crystal(22,8,main); d.point((21,5), fill=light)
    elif key in {"worn_pack", "leather_pack"}:
        rect((7,9,24,25), main)
        d.arc((10,3,21,16), 180, 360, fill=INK, width=3)
        line([(11,8),(11,22)], dark, 2); line([(20,8),(20,22)], dark, 2)
        rect((11,14,20,19), light); d.point((16,16), fill=dark)
        if key == "leather_pack":
            line([(8,12),(23,12)], light, 1); d.point((9,22), fill=HANDLE_LIGHT)
    elif key == "hide":
        poly([(8,7),(13,9),(17,7),(21,10),(26,8),(25,15),(28,20),(23,25),(17,23),(12,27),(7,22),(9,16)], main)
        line([(11,13),(16,15),(21,12)], light, 2); d.point((20,20), fill=dark)
    elif key in {"raw_meat", "cooked_meat"}:
        poly([(7,17),(9,11),(15,9),(20,11),(23,8),(27,13),(25,20),(20,24),(13,25),(8,22)], main)
        d.ellipse((5,14,11,20), fill=(236,217,190,255), outline=INK)
        line([(13,13),(17,12)], light, 2)
        if key == "cooked_meat":
            line([(12,19),(18,16),(22,18)], dark, 2); d.point((16,21), fill=light)
    elif key == "potion":
        rect((12,4,19,8), light); rect((13,2,18,4), dark)
        poly([(12,9),(19,9),(20,13),(25,18),(24,25),(7,25),(6,18),(11,13)], main)
        d.rectangle((8,18,23,23), fill=dark)
        d.rectangle((9,18,21,22), fill=main)
        d.point((12,16), fill=light)
    else:
        raise KeyError(f"No icon design for {key}")
    return image


def write_aseprite(icons: dict[str, Image.Image]) -> None:
    if not ASEPRITE.is_file():
        return
    sheet_size = (COLS * SIZE, ROWS * SIZE)
    with tempfile.TemporaryDirectory() as temp:
        tmp = Path(temp)
        names = []
        for index, (key, art) in enumerate(icons.items()):
            layer = Image.new("RGBA", sheet_size)
            layer.alpha_composite(art, ((index % COLS) * SIZE, (index // COLS) * SIZE))
            layer.save(tmp / f"{index}.png")
            names.append(key)
        (tmp / "layers.txt").write_text("\n".join(names), encoding="utf-8")
        script = tmp / "assemble.lua"
        script.write_text(r'''local dir=app.params.dir
local names={}
for line in io.lines(dir.."/layers.txt") do names[#names+1]=line end
local first=Image{fromFile=dir.."/0.png"}
local sprite=Sprite(first.width,first.height,ColorMode.RGB)
sprite.gridBounds=Rectangle(0,0,32,32)
for i,name in ipairs(names) do
  local layer=(i==1) and sprite.layers[1] or sprite:newLayer()
  layer.name=name
  local img=Image{fromFile=dir.."/"..(i-1)..".png"}
  sprite:newCel(layer,sprite.frames[1],img,Point(0,0))
end
sprite:saveAs(app.params.out)
''', encoding="utf-8")
        output = OUT / "item_icons.aseprite"
        subprocess.run(
            [str(ASEPRITE), "-b", "--script-param", f"dir={tmp.as_posix()}",
             "--script-param", f"out={output.resolve().as_posix()}", "--script", str(script)],
            check=True,
        )


def build() -> None:
    if len(KEYS) != 48 or len(set(KEYS)) != 48:
        raise ValueError("The requested item key list must contain 48 unique entries")
    missing = set(KEYS) - ITEM_KINDS.keys()
    if missing:
        raise ValueError(f"Unknown catalogue keys: {sorted(missing)}")
    OUT.mkdir(parents=True, exist_ok=True)
    icons: dict[str, Image.Image] = {}
    for key in KEYS:
        kind = ITEM_KINDS[key]
        art = make_icon(key, kind.color)
        if art.size != (32, 32) or art.getchannel("A").getbbox() is None:
            raise ValueError(f"Invalid icon for {key}")
        art.save(OUT / f"{key}.png", optimize=True)
        icons[key] = art

    atlas = Image.new("RGBA", (COLS * SIZE, ROWS * SIZE), (0, 0, 0, 0))
    preview = Image.new("RGBA", atlas.size, (35, 39, 37, 255))
    preview_draw = ImageDraw.Draw(preview)
    for index, (key, art) in enumerate(icons.items()):
        x, y = (index % COLS) * SIZE, (index // COLS) * SIZE
        atlas.alpha_composite(art, (x, y))
        preview.alpha_composite(art, (x, y))
        preview_draw.rectangle((x, y, x + SIZE - 1, y + SIZE - 1), outline=(63, 68, 64, 255))
    atlas.save(OUT / "item_icons_atlas.png", optimize=True)
    preview.resize((atlas.width * 3, atlas.height * 3), Image.Resampling.NEAREST).save(
        OUT / "item_icons_preview.png", optimize=True
    )
    write_aseprite(icons)
    print(f"Built {len(icons)} transparent 32x32 item icons in {OUT}")


if __name__ == "__main__":
    build()
