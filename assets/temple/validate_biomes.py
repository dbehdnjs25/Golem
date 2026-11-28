"""Check tile dimensions, metadata, atlas contents and Aseprite exports."""
from pathlib import Path
import json
import os
import struct
import subprocess
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parent
EXE = os.environ.get('ASEPRITE', r'C:\Users\ykb62\Desktop\aseprite.exe')
KEYS = ('grassland', 'burnt_forest', 'snowfield', 'wind_plateau', 'bog', 'wasteland')


def main():
    with tempfile.TemporaryDirectory(prefix='temple-validation-') as temporary:
        for key in KEYS:
            folder = ROOT / key / 'tiles32'
            manifest = json.loads((folder / 'tiles.json').read_text(encoding='utf-8'))
            assert len(manifest['tiles']) == 20
            with Image.open(folder / 'temple-atlas.png') as image:
                atlas = image.convert('RGBA')
            assert atlas.size == (128, 160)
            for tile in manifest['tiles']:
                with Image.open(folder / tile['png']) as image:
                    pixels = image.convert('RGBA')
                assert pixels.size == (32, 32), (key, tile['name'])
                assert pixels.getchannel('A').getextrema() == (255, 255)
                x, y, w, h = tile['rect']
                assert pixels.tobytes() == atlas.crop((x, y, x+w, y+h)).tobytes()
                data = (folder / tile['aseprite']).read_bytes()
                assert struct.unpack_from('<H', data, 4)[0] == 0xA5E0
                assert struct.unpack_from('<HH', data, 8) == (32, 32)
            exported = Path(temporary) / f'{key}.png'
            subprocess.run([EXE, '--batch', str(folder / 'temple-atlas.aseprite'),
                            '--save-as', str(exported)], check=True, capture_output=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            with Image.open(exported) as image:
                assert image.convert('RGBA').tobytes() == atlas.tobytes()
            print(f'{key}: 20 tiles, metadata and layered Aseprite round-trip OK')
        with Image.open(ROOT / 'tiles32' / 'temple-atlas.png') as original:
            with Image.open(ROOT / 'grassland' / 'tiles32' / 'temple-atlas.png') as current:
                assert original.convert('RGBA').tobytes() == current.convert('RGBA').crop((0, 0, 128, 128)).tobytes()
        print('PASS: 120 tiles; original grassland art preserved exactly.')


if __name__ == '__main__':
    main()
