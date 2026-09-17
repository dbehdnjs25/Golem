"""Build a deterministic 32px meadow tileset and a standalone HTML preview."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from PIL import Image

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

ROOT = Path(__file__).parent / 'tiles32'
ROOT.mkdir(exist_ok=True)
GRASS = '#75994f'
DARK = '#608343'
LIGHT = '#89a759'
STEM = '#4d743c'
base = pygame.Surface((32, 32), pygame.SRCALPHA)
base.fill(GRASS)


def pixel(s, x, y, color):
    s.set_at((x % 32, y % 32), pygame.Color(color))


# Periodic, subtle texture: no border, inset, shadow, or transparent gutter.
for x, y, color in [(2, 3, LIGHT), (12, 1, DARK), (23, 5, LIGHT),
                     (7, 11, DARK), (18, 9, LIGHT), (29, 13, DARK),
                     (2, 20, LIGHT), (13, 18, DARK), (23, 23, LIGHT),
                     (7, 28, LIGHT), (18, 29, DARK), (30, 27, LIGHT)]:
    pixel(base, x, y, color)
    pixel(base, x + 1, y, color)


def tuft(s, x, y):
    for dx, dy in [(-2, -2), (-1, -1), (0, 0), (0, -1), (0, -3), (1, -1), (2, -2)]:
        pixel(s, x+dx, y+dy, STEM)
    pixel(s, x, y-2, '#9bb969')


def flower(s, x, y, petal, shade):
    pixel(s, x, y+2, STEM)
    pixel(s, x, y+3, STEM)
    pixel(s, x+1, y+2, DARK)
    for dx, dy in [(0, -1), (-1, 0), (1, 0), (0, 1)]:
        pixel(s, x+dx, y+dy, petal if dy < 1 else shade)
    pixel(s, x, y, '#eed180')


def stone(s, x, y, large=False):
    points = [(1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2), (3, 2), (1, 3), (2, 3)]
    if large:
        points += [(3, 0), (4, 1), (4, 2), (3, 3), (1, 4), (2, 4), (3, 4)]
    for dx, dy in points:
        pixel(s, x+dx, y+dy, '#737c66' if dy >= 3 else '#a0a38a')
    pixel(s, x+1, y, '#c5c3a5')
    pixel(s, x+1, y+1, '#b8b89b')
    pixel(s, x+2, y+2, '#8b947c')


def clover(s, x, y):
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        pixel(s, x+dx, y+dy, '#4e803e')
        pixel(s, x+dx+1, y+dy, '#609545')
    pixel(s, x, y+2, STEM)


NAMES = ['기본 잔디', '작은 풀', '풀 무리', '하얀 꽃', '노란 꽃', '분홍 꽃', '파란 꽃', '보라 꽃',
         '작은 조약돌', '조약돌 두 개', '작은 돌무리', '클로버', '하얀 꽃 무리', '노란 꽃 무리', '혼합 들꽃', '꽃과 조약돌']
tiles = []
for index in range(16):
    s = base.copy()
    if index == 1:
        tuft(s, 16, 19)
    elif index == 2:
        tuft(s, 10, 12); tuft(s, 23, 23)
    elif index in (3, 4, 5, 6, 7):
        colors = [('#f2eed5', '#c9d1ac'), ('#f2d366', '#d6b151'), ('#e7a0a3', '#c57e8a'), ('#8cbed2', '#709aaa'), ('#baa1d3', '#9c82b7')]
        flower(s, 15, 15, *colors[index-3])
    elif index == 8:
        stone(s, 15, 16)
    elif index == 9:
        stone(s, 9, 12); stone(s, 22, 21)
    elif index == 10:
        stone(s, 11, 15, True); stone(s, 19, 19); pixel(s, 20, 13, '#aaa98e')
    elif index == 11:
        clover(s, 12, 12); clover(s, 21, 22)
    elif index == 12:
        flower(s, 10, 10, '#f2eed5', '#c9d1ac'); flower(s, 22, 20, '#f2eed5', '#c9d1ac')
    elif index == 13:
        flower(s, 12, 20, '#f2d366', '#d6b151'); flower(s, 23, 10, '#f2d366', '#d6b151')
    elif index == 14:
        flower(s, 9, 12, '#f2eed5', '#c9d1ac'); flower(s, 22, 20, '#e7a0a3', '#c57e8a'); flower(s, 21, 9, '#8cbed2', '#709aaa')
    elif index == 15:
        flower(s, 11, 12, '#f2eed5', '#c9d1ac'); stone(s, 20, 20)
    tiles.append(s)

sheet = pygame.Surface((128, 128), pygame.SRCALPHA)
entries = []


def save_webp(surface, path):
    image = Image.frombytes('RGBA', surface.get_size(), pygame.image.tobytes(surface, 'RGBA'))
    image.save(path, format='WEBP', lossless=True, exact=True, method=6)
    with Image.open(path) as saved:
        assert saved.convert('RGBA').tobytes() == image.tobytes()


for i, tile in enumerate(tiles):
    filename = f'grass_{i:02}.webp'
    save_webp(tile, ROOT / filename)
    sheet.blit(tile, ((i % 4)*32, (i // 4)*32))
    entries.append(dict(id=i, name=NAMES[i], file=filename, rect=[(i%4)*32, (i//4)*32, 32, 32]))
save_webp(sheet, ROOT / 'grassland-32.webp')
(ROOT / 'tileset.json').write_text(json.dumps(dict(image='grassland-32.webp', tilewidth=32, tileheight=32, columns=4, tilecount=16, margin=0, spacing=0, tiles=entries), ensure_ascii=False, indent=2), encoding='utf-8')

# Check the deliverables and all four shared boundary strips.
for tile in tiles:
    assert tile.get_size() == (32, 32)
    for x in range(32):
        for y in range(32):
            assert tile.get_at((x, y)).a == 255
            if x < 4 or x >= 28 or y < 4 or y >= 28:
                assert tile.get_at((x, y)) == base.get_at((x, y))
assert len({pygame.image.tobytes(t, 'RGBA') for t in tiles}) == 16
embedded = base64.b64encode((ROOT / 'grassland-32.webp').read_bytes()).decode()
for entry in entries:
    entry['url'] = 'data:image/webp;base64,' + base64.b64encode((ROOT / entry['file']).read_bytes()).decode()
html = (Path(__file__).parent/'tiles32.template.html').read_text(encoding='utf-8')
html = html.replace('__ATLAS__', embedded).replace('__TILES__', json.dumps(entries, ensure_ascii=False))
(ROOT/'preview.html').write_text(html, encoding='utf-8')
print('Verified: 16 unique 32x32 opaque tiles, identical 4px boundary strips; 128x128 atlas; standalone HTML.')
