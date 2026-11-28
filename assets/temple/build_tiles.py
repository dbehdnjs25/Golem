"""Package the generated temple atlas into native 32px PNG/Aseprite tiles."""
from pathlib import Path
import json
import os
import subprocess
from PIL import Image

ROOT = Path(__file__).resolve().parent
EXE = os.environ.get('ASEPRITE', r'C:\Users\ykb62\Desktop\aseprite.exe')
NAMES = [
    'floor_plain', 'floor_worn', 'floor_cracked', 'floor_moss',
    'wall_north', 'wall_south', 'wall_west', 'wall_east',
    'corner_nw', 'corner_ne', 'corner_sw', 'corner_se',
    'door_closed', 'door_open', 'stairs_down', 'altar',
]


def run(*args):
    subprocess.run([EXE, '--batch', *map(str, args)], check=True,
                   capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def main():
    out = ROOT / 'tiles32'
    out.mkdir(exist_ok=True)
    source = ROOT / 'source' / 'temple-generated.png'
    with Image.open(source) as image:
        width, height = image.size
    assert width == height
    atlas = out / 'temple-atlas.png'
    run(source, '--scale', str(128 / width), '--save-as', atlas)
    run(atlas, '--save-as', out / 'temple-atlas.aseprite')
    records = []
    for i, name in enumerate(NAMES):
        x, y = i % 4 * 32, i // 4 * 32
        png = out / f'{name}.png'
        run(atlas, '--crop', f'{x},{y},32,32', '--save-as', png)
        run(png, '--save-as', out / f'{name}.aseprite')
        with Image.open(png) as image:
            assert image.size == (32, 32), (name, image.size)
        records.append({'name': name, 'rect': [x, y, 32, 32], 'png': png.name,
                        'aseprite': name + '.aseprite'})
    (out / 'tiles.json').write_text(json.dumps({'tile_size': 32, 'columns': 4,
        'atlas': atlas.name, 'tiles': records}, indent=2), encoding='utf-8')
    print(f'Built and verified {len(records)} tiles, all 32x32.')


if __name__ == '__main__':
    main()
