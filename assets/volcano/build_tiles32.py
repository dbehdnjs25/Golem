"""Build seamless, low-contrast scorched basalt without repeating plate outlines."""
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

root = Path(__file__).parent / 'tiles32'
root.mkdir(parents=True, exist_ok=True)
tile = Image.new('RGB', (32, 32))
rng = random.Random(20261015)
grain = [[rng.uniform(-1, 1) for _ in range(32)] for _ in range(32)]
heat_grain = [[rng.uniform(-1, 1) for _ in range(32)] for _ in range(32)]


def color(x, y):
    x, y = x % 32, y % 32
    # Small, wrapped grain avoids closed shapes and bright landmarks per tile.
    rock = sum(grain[(y+dy) % 32][(x+dx) % 32]
               for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9
    warmth = sum(heat_grain[(y+dy) % 32][(x+dx) % 32]
                 for dy in (-1, 0, 1) for dx in (-2, -1, 0, 1, 2)) / 15
    tone = round(rock * 7 + grain[y][x] * 2)
    heat = max(0, round(warmth * 16))
    return 48 + tone + heat, 35 + tone, 33 + tone


for y in range(32):
    for x in range(32):
        tile.putpixel((x, y), color(x, y))
for i in range(32):
    assert color(0, i) == color(32, i)
    assert color(i, 0) == color(i, 32)


base = tile.copy()


def mark(x, y, rgb):
    tile.putpixel((x % 32, y % 32), rgb)


# Small ash-coated chips give the ground relief without large repeated outlines.
for x, y, width in [(3, 4, 3), (15, 2, 2), (25, 7, 3), (11, 15, 2),
                     (2, 22, 2), (17, 26, 3), (28, 18, 2), (8, 29, 2)]:
    for dx in range(width):
        mark(x + dx, y, (72, 62, 56))
        mark(x + dx, y + 1, (54, 47, 44))
    mark(x + width - 1, y + 2, (34, 28, 28))

# Short, disconnected ember seams; no lattice or repeating enclosed rock plates.
for path in [[(6, 10), (7, 10), (8, 11), (8, 12)],
             [(23, 24), (24, 23), (25, 23)],
             [(19, 8), (19, 9)]]:
    for x, y in path:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            mark(x + dx, y + dy, (76, 39, 31))
    for x, y in path:
        mark(x, y, (133, 59, 34))
    x, y = path[len(path)//2]
    mark(x, y, (170, 86, 43))

# Preserve the subdued shared edge, so details never create seams between tiles.
for y in range(32):
    for x in range(32):
        if x < 2 or x >= 30 or y < 2 or y >= 30:
            mark(x, y, color(x, y))
tiles = [tile]
entries = [dict(id=0, name='화산암 기본 땅', file='volcano_00.webp', rect=[0, 0, 32, 32],
                category='ground', family=0, position='기본')]


def lava(surface, variant):
    mask = Image.new('L', (32, 32))
    drawing = ImageDraw.Draw(mask)
    if variant == 1:
        drawing.line([(5, 18), (9, 17), (12, 14), (17, 14), (20, 16), (25, 15)], fill=255, width=4, joint='curve')
        drawing.polygon([(11, 14), (14, 11), (18, 12), (20, 15), (16, 17)], fill=255)
    elif variant == 2:
        drawing.polygon([(7, 16), (9, 12), (13, 11), (15, 13), (19, 12),
                         (23, 15), (22, 19), (18, 22), (14, 21), (13, 18), (9, 19)], fill=255)
    else:
        drawing.line([(12, 6), (13, 10), (10, 13), (11, 17), (16, 20), (17, 25)], fill=255, width=4, joint='curve')
        drawing.polygon([(10, 14), (15, 15), (18, 19), (16, 22), (12, 20)], fill=255)
    filled = {(x, y) for y in range(3, 29) for x in range(3, 29) if mask.getpixel((x, y))}
    for x, y in filled:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            if (x+dx, y+dy) not in filled:
                surface.putpixel((x+dx, y+dy), (59, 34, 29))
    for x, y in filled:
        depth = next((radius for radius in range(1, 4)
                      if any((x+dx, y+dy) not in filled for dx, dy in
                             [(-radius, 0), (radius, 0), (0, -radius), (0, radius)])), 4)
        palette = [(88, 38, 27), (140, 49, 25), (182, 71, 29), (207, 97, 36)]
        # Uneven temperature breaks the uniform bright outline and solid fill.
        cooling = 1 if grain[y][x] < -.25 else 0
        surface.putpixel((x, y), palette[max(0, depth-1-cooling)])
    # Dark rafts of cooled basalt overlap the molten surface rather than float
    # outside it. Keep hot channels around them, so the lava remains connected.
    crust = Image.new('L', (32, 32))
    cd = ImageDraw.Draw(crust)
    shapes = {1: [[(12, 12), (16, 11), (17, 13), (14, 14)]],
              2: [[(9, 13), (12, 12), (14, 14), (12, 16), (9, 15)],
                  [(17, 18), (20, 17), (21, 19), (18, 21), (16, 20)]],
              3: [[(12, 16), (15, 16), (17, 19), (15, 20), (13, 18)]]}
    for shape in shapes[variant]:
        cd.polygon(shape, fill=255)
    for x, y in filled:
        if crust.getpixel((x, y)):
            surface.putpixel((x, y), (51, 37, 33) if grain[y][x] > 0 else (65, 39, 31))


for group, (name, category) in enumerate([('화산암 조각', 'stones'), ('흩어진 불씨', 'embers'),
                                         ('용암 흐름과 웅덩이', 'lava'), ('화산 지대 혼합', 'mixed')]):
    family = len(tiles)
    for variant in range(1, 4):
        rng = random.Random(20261016 + group * 10 + variant)
        surface = base.copy()
        centers = []
        candidates = [(x, y) for y in range(6, 25) for x in range(6, 25)]
        rng.shuffle(candidates)
        for item in range(0 if group == 2 else variant + 2):
            x, y = next((x, y) for x, y in candidates
                        if all((x-px)**2 + (y-py)**2 >= 49 for px, py in centers))
            centers.append((x, y))
            kind = group if group < 3 else item % 2
            if kind == 0:
                width = rng.randint(2, 4)
                for dx in range(width):
                    surface.putpixel((x+dx-1, y), (77, 64, 56))
                    surface.putpixel((x+dx-1, y+1), (56, 46, 42))
                surface.putpixel((x+width-2, y+2), (34, 28, 28))
            else:
                path = [(x, y)]
                for px, py in path:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        surface.putpixel((px+dx, py+dy), (77, 39, 30))
                for px, py in path:
                    surface.putpixel((px, py), (132, 59, 33))
                surface.putpixel(path[len(path)//2], (178, 88, 42))
        if group in (2, 3):
            lava(surface, variant)
        i = len(tiles)
        tiles.append(surface)
        entries.append(dict(id=i, name=f'{name} · 랜덤 {variant}', file=f'volcano_{i:02}.webp',
                            rect=[i % 4 * 32, i // 4 * 32, 32, 32], category=category,
                            family=family, position=f'랜덤 {variant}'))

sheet = Image.new('RGB', (128, 128), (48, 35, 33))
for entry, surface in zip(entries, tiles):
    for y in range(32):
        for x in range(32):
            if x < 2 or x >= 30 or y < 2 or y >= 30:
                assert surface.getpixel((x, y)) == base.getpixel((x, y))
    surface.save(root / entry['file'], 'WEBP', lossless=True, exact=True)
    with Image.open(root / entry['file']) as saved:
        assert saved.convert('RGB').tobytes() == surface.tobytes()
    sheet.paste(surface, tuple(entry['rect'][:2]))
assert len({surface.tobytes() for surface in tiles}) == len(tiles)
sheet.save(root / 'volcano-32.webp', 'WEBP', lossless=True, exact=True)
meta = dict(image='volcano-32.webp', tilewidth=32, tileheight=32, columns=4, tilecount=len(tiles),
            margin=0, spacing=0, tiles=entries)
(root / 'tileset.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
preview = Image.new('RGB', (256, 256))
for y in range(8):
    for x in range(8):
        preview.paste(tile, (x*32, y*32))
preview.save(root / 'repeat-preview.png')
rng = random.Random(93)
for y in range(8):
    for x in range(8):
        preview.paste(rng.choice(tiles), (x*32, y*32))
preview.save(root / 'variants-preview.png')
print('Verified: 13 unique volcanic tiles, shared edges, lossless WebP, mixed preview.')
