"""Restore runtime PNGs without modifying sources or any terrain tileset.

Exports first frames from existing Aseprite documents. UI sources other than the
hotbar were lost in the migration: recover the committed heart and construct
the missing pixel frames using the existing charcoal/sage UI palette.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import argparse
import math

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
ASEPRITE = Path(os.environ.get("ASEPRITE", "C:/Users/ykb62/Desktop/aseprite.exe"))
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def export(source, target, layer=None):
    args = [str(ASEPRITE), "-b", "--frame-range", "0,0"]
    if layer:
        args += ["--layer", layer]
    args += [str(source), "--save-as", str(target)]
    subprocess.run(args, check=True, creationflags=CREATE_NO_WINDOW)
    if not target.is_file():
        raise RuntimeError(f"Export missing: {target}")


def frame(size, selected=False):
    image = Image.new("RGBA", size)
    draw = ImageDraw.Draw(image)
    w, h = size
    outer = (205, 194, 156, 255) if selected else (76, 81, 78, 255)
    inner = (143, 134, 106, 255) if selected else (105, 111, 106, 255)
    draw.rectangle((1, 0, w-2, h-1), fill=outer)
    draw.rectangle((0, 1, w-1, h-2), fill=outer)
    draw.rectangle((1, 1, w-2, h-2), fill=inner)
    draw.rectangle((3, 3, w-4, h-4), fill=(32, 35, 34, 245))
    return image


def recover_wasteland(source):
    """Recover the previous 96x128 export from its preserved generated original.

    Uses the same palette, sampling, outline and debris rules as the detailed
    art pass. This is only needed because that tree's Aseprite source was lost.
    """
    with Image.open(source) as opened:
        src = opened.convert("RGBA")
    bounds = src.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
    if bounds is None:
        raise ValueError("Empty wasteland source")
    left, top, right, bottom = bounds
    sw, sh = right-left, bottom-top
    scale = min(92/sw, 124/sh)
    dw, dh = math.floor(sw*scale+.5), math.floor(sh*scale+.5)
    ox, oy = (96-dw)//2, 126-dh
    grid = {}
    for y in range(dh):
        for x in range(dw):
            p = src.getpixel((left+math.floor((x+.5)*sw/dw), top+math.floor((y+.5)*sh/dh)))
            if p[3] >= 128:
                grid[x+ox, y+oy] = p[:3]
    seen = set()
    for start in list(grid):
        if start in seen:
            continue
        queue = [start]
        seen.add(start)
        for x,y in queue:
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    neighbor = (x+dx,y+dy)
                    if neighbor in grid and neighbor not in seen:
                        seen.add(neighbor)
                        queue.append(neighbor)
        if len(queue) <= 2:
            for point in queue:
                del grid[point]
    palette = [(120,96,71),(179,148,107),(223,195,153),
               (137,101,47),(181,138,59),(216,183,94)]
    image = Image.new("RGBA", (96,128))
    for (x,y),p in grid.items():
        edge = any(n not in grid for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
        color = (73,59,45) if edge else min(palette, key=lambda c:
            2*(p[0]-c[0])**2 + 3*(p[1]-c[1])**2 + (p[2]-c[2])**2)
        image.putpixel((x,y), (*color,255))
    image.save(ROOT/"trees/wasteland.png")
    print("Recovered trees/wasteland.png from preserved detailed artwork")


def main():
    files = {
        "trees": ("bog", "burnt_forest", "snowfield", "wind_plateau"),
        "grassland/objects": ("tree_base",),
        "resources": ("stone", "wood", "copper_ore", "iron_ore", "gold_ore", "zinc_ore"),
    }
    for folder, names in files.items():
        for name in names:
            export(ROOT/folder/f"{name}.aseprite", ROOT/folder/f"{name}.png")
            print(f"Exported {folder}/{name}.png")

    ui = ROOT / "ui"
    heart = subprocess.check_output(
        ["git", "show", "HEAD:assets/ui/health_heart.png"], cwd=ROOT.parent,
        creationflags=CREATE_NO_WINDOW,
    )
    (ui/"health_heart.png").write_bytes(heart)
    with tempfile.TemporaryDirectory(prefix="golem-ui-export-") as directory:
        for name, index in (("hotbar_slot", 0), ("hotbar_slot_selected", 2)):
            path = Path(directory)/f"{name}.png"
            export(ui/"hotbar.aseprite", path, f"Slot {index+1}")
            with Image.open(path) as sheet:
                assert sheet.size == (232, 60), "Unexpected hotbar layout"
                left = 4 + 44*index
                sheet.crop((left, 10, left+40, 50)).save(ui/f"{name}.png")

    for name, size in {
        "stamina_bar": (136, 9), "dodge_bar": (136, 5),
        "boss_bar": (32, 13), "inventory_panel": (32, 32),
        "inventory_header": (32, 18), "inventory_slot": (22, 22),
        "item_tooltip": (160, 24),
    }.items():
        # The narrow dodge gauge needs a one-pixel well rather than a 3px inset.
        art = frame(size) if size[1] >= 7 else Image.new("RGBA", size, (76, 81, 78, 255))
        if size[1] < 7:
            ImageDraw.Draw(art).rectangle((1, 1, size[0]-2, size[1]-2), fill=(32, 35, 34, 255))
        art.save(ui/f"{name}.png")
    frame((22, 22), selected=True).save(ui/"inventory_slot_selected.png")

    stamina = Image.new("RGBA", (9, 9))
    draw = ImageDraw.Draw(stamina)
    draw.polygon([(5,0),(1,5),(4,5),(3,8),(8,3),(5,3)], fill=(147,192,136,255))
    draw.line([(5,1),(3,4)], fill=(201,222,165,255))
    stamina.save(ui/"stamina_icon.png")
    bag = Image.new("RGBA", (16, 16))
    draw = ImageDraw.Draw(bag)
    draw.rectangle((5,1,10,5), outline=(76,81,78,255), width=2)
    draw.rectangle((2,4,13,14), fill=(76,81,78,255))
    draw.rectangle((3,5,12,13), fill=(150,125,84,255))
    draw.rectangle((5,9,10,13), fill=(105,88,61,255))
    draw.line((4,6,11,6), fill=(205,194,156,255))
    bag.save(ui/"backpack_icon.png")
    print("Restored all 13 UI PNGs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wasteland-source", type=Path,
                        help="Preserved detailed wasteland redraw, if its Aseprite is missing")
    args = parser.parse_args()
    main()
    if args.wasteland_source:
        recover_wasteland(args.wasteland_source)
