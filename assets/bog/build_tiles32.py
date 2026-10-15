"""Build a seamless, opaque bog water tile using the existing pixel-art pipeline."""
import json
import math
import random
from pathlib import Path

from PIL import Image

root = Path(__file__).parent / 'tiles32'
root.mkdir(parents=True, exist_ok=True)
tile = Image.new('RGB', (32, 32), '#3b5549')


# Subtle periodic currents have no isolated bright marks that reveal the repeat.
# Every term has an integer period, including across the last/first pixel seam.
def water_color(x, y):
    u, v = 2 * math.pi * x / 32, 2 * math.pi * y / 32
    flow = (.40 * math.sin(u + 2 * v + .8)
            + .27 * math.cos(u - 3 * v + 1.7)
            + .19 * math.sin(2 * u + v + .3)
            + .14 * math.cos(u + 5 * v + 2.2))
    tone = round(flow * 3)
    return (59 + tone, 85 + tone, 73 + tone)


for y in range(32):
    for x in range(32):
        tile.putpixel((x, y), water_color(x, y))

# Verify the actual wrap joins, not only the formula's periodicity.
for i in range(32):
    assert water_color(0, i) == water_color(32, i)
    assert water_color(i, 0) == water_color(i, 32)
    for a, b in [((31, i), (0, i)), ((i, 31), (i, 0))]:
        assert max(abs(c-d) for c, d in zip(tile.getpixel(a), tile.getpixel(b))) <= 2

def mark(surface, x, y, color):
    surface.putpixel((x, y), tuple(bytes.fromhex(color[1:])))


def ripple(surface, x, y, rng):
    for dx, dy in [(-3, 0), (-2, -1), (-1, -1), (1, -1), (2, 0),
                   (-2, 2), (-1, 3), (0, 3), (1, 3)]:
        mark(surface, x + dx, y + dy, '#486455')


def moss(surface, x, y, rng):
    for dy in range(-2, 3):
        for dx in range(-3, 4):
            if abs(dx) + abs(dy) <= 4 and rng.random() < .7:
                mark(surface, x + dx, y + dy, rng.choice(['#4b6349', '#536d4d', '#59734f']))


def duckweed(surface, x, y, rng):
    for dx, dy in [(-3, -1), (1, -2), (-1, 2), (3, 3)]:
        mark(surface, x + dx, y + dy, '#6e8452')
        mark(surface, x + dx + 1, y + dy, '#5b754c')


def reeds(surface, x, y, rng):
    for dx, height in [(-2, 4), (0, 6), (2, 3)]:
        for dy in range(height):
            mark(surface, x + dx, y - dy, '#79805a' if dx == 0 else '#606e4b')
        mark(surface, x + dx, y - height, '#655540')
    for dx in range(-3, 4):
        mark(surface, x + dx, y + 1, '#354e42')
    mark(surface, x - 3, y - 2, '#687a4f')
    mark(surface, x + 3, y - 1, '#687a4f')


def driftwood(surface, x, y, rng):
    for dx in range(-3, 4):
        dy = dx // 3
        mark(surface, x + dx, y + dy, '#6a6750')
        mark(surface, x + dx, y + dy + 1, '#454f3f')
    mark(surface, x + 1, y - 1, '#6a6750')
    mark(surface, x + 2, y - 2, '#777157')


tiles = [tile]
entries = [dict(id=0, name='늪지 기본 땅', file='bog_00.webp', rect=[0, 0, 32, 32],
                category='ground', family=0, position='기본')]
for name, category, draw in [('잔물결', 'water', ripple), ('물 위 이끼', 'plants', moss),
                              ('개구리밥', 'plants', duckweed), ('갈대', 'plants', reeds),
                              ('떠 있는 나뭇가지', 'debris', driftwood)]:
    family = len(tiles)
    rng = random.Random(20260921 + family)
    centers = []
    for variant in range(1, 4):
        candidates = [(x, y) for y in range(11, 24) for x in range(9, 24)]
        rng.shuffle(candidates)
        x, y = next((x, y) for x, y in candidates
                    if all((x-px)**2 + (y-py)**2 >= 36 for px, py in centers))
        centers.append((x, y))
        surface = tile.copy()
        draw(surface, x, y, rng)
        i = len(tiles)
        tiles.append(surface)
        entries.append(dict(id=i, name=f'{name} · 랜덤 {variant}', file=f'bog_{i:02}.webp',
                            rect=[i % 4 * 32, i // 4 * 32, 32, 32], category=category,
                            family=family, position=f'랜덤 {variant}'))

sheet = Image.new('RGB', (128, 128))
for entry, surface in zip(entries, tiles):
    for y in range(32):
        for x in range(32):
            if x < 4 or x >= 28 or y < 4 or y >= 28:
                assert surface.getpixel((x, y)) == tile.getpixel((x, y))
    surface.save(root / entry['file'], 'WEBP', lossless=True, exact=True)
    with Image.open(root / entry['file']) as saved:
        assert saved.convert('RGB').tobytes() == surface.tobytes()
    sheet.paste(surface, tuple(entry['rect'][:2]))
assert len({surface.tobytes() for surface in tiles}) == len(tiles)
sheet.save(root / 'bog-32.webp', 'WEBP', lossless=True, exact=True)
meta = dict(image='bog-32.webp', tilewidth=32, tileheight=32, columns=4, tilecount=len(tiles),
            margin=0, spacing=0, tiles=entries)
(root / 'tileset.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
preview = Image.new('RGB', (256, 256))
for y in range(8):
    for x in range(8):
        preview.paste(tile, (x * 32, y * 32))
preview.save(root / 'repeat-preview.png')
rng = random.Random(84)
for y in range(8):
    for x in range(8):
        preview.paste(tiles[0] if rng.random() < .55 else rng.choice(tiles[1:]), (x * 32, y * 32))
preview.save(root / 'variants-preview.png')
print('Verified: 16 unique opaque bog tiles, unchanged base, common 4px borders, lossless WebP.')
