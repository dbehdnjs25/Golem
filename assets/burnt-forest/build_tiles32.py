"""Build seamless ash ground and charred woodland decorations, 32px each."""
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).parent / 'tiles32'
root.mkdir(parents=True, exist_ok=True)
rng = random.Random(20261017)
noise = [[rng.uniform(-1, 1) for _ in range(32)] for _ in range(32)]
base = Image.new('RGB', (32, 32))
for y in range(32):
    for x in range(32):
        soft = sum(noise[(y+dy)%32][(x+dx)%32] for dy in (-1,0,1) for dx in (-1,0,1))/9
        n = round(soft*6 + noise[y][x]*2)
        base.putpixel((x,y), (78+n, 72+n, 64+n))


def branch(s, x, y, rng):
    d = ImageDraw.Draw(s)
    flip = rng.choice([-1, 1])
    turn = rng.choice([False, True])
    def points(path):
        return [(x+(dy if turn else dx)*flip, y+(dx if turn else dy)) for dx,dy in path]
    main = points([(-5,2),(-2,1),(0,-1),(3,-2),(5,-3)])
    fork = points([(-1,0),(-2,-2),(-2,-4)])
    d.line([(px,py+1) for px,py in main],fill='#3b3832')
    d.line(main,fill='#292827',width=2)
    d.line(fork,fill='#2c2a27')
    if rng.random() < .6:
        d.line(points([(2,-2),(3,0),(5,1)]),fill='#302d29')
    d.point(main[1],fill='#62584a')
    d.point(main[-1],fill='#73624d')


def charcoal(s, x, y, rng):
    d = ImageDraw.Draw(s)
    for dx,dy in [(-3,0),(1,-2),(3,2),(-1,3)]:
        d.rectangle((x+dx,y+dy,x+dx+2,y+dy+1),fill='#302f2d')
        d.point((x+dx,y+dy),fill='#615d54')


def ember(s, px, py):
    d = ImageDraw.Draw(s)
    d.ellipse((px-2,py-1,px+2,py+2),fill='#634435')
    d.line([(px-1,py+2),(px+2,py+1)],fill='#302c28',width=2)
    d.line([(px-1,py+1),(px+1,py)],fill='#993d25',width=2)
    d.line([(px,py+1),(px+1,py)],fill='#d1692d')
    d.point((px,py),fill='#efad53')


tiles=[base]
entries=[dict(id=0,name='재가 덮인 숲 바닥',file='burnt_00.webp',rect=[0,0,32,32],
              category='ground',family=0,position='기본')]
for group,(name,category,draw) in enumerate([('탄 나뭇가지','wood',branch),
                                           ('숯 조각','charcoal',charcoal)]):
    family=len(tiles)
    centers = [(11,12),(21,19),(14,22)]
    if draw is branch:
        centers += [(21,10),(10,21),(15,15)]
    for variant,(x,y) in enumerate(centers,start=1):
        s=base.copy()
        draw(s,x,y,random.Random(group*10+variant))
        i=len(tiles);tiles.append(s)
        entries.append(dict(id=i,name=f'{name} · 랜덤 {variant}',file=f'burnt_{i:02}.webp',
                            rect=[i%4*32,i//4*32,32,32],category=category,family=family,position=f'랜덤 {variant}'))
# Reserve the retired three-ember IDs so existing maps keep their other IDs.
for i in range(10,13):
    tiles.append(base.copy())
    entries.append(dict(id=i,file=f'burnt_{i:02}.webp',rect=[i%4*32,i//4*32,32,32],hidden=True))
for count in (1, 2):
    family=len(tiles)
    rng=random.Random(20261020+count)
    for variant in range(1,7 if count==2 else 4):
        s=base.copy()
        centers=[]
        candidates=[(x,y) for x in range(7,25) for y in range(7,25)]
        rng.shuffle(candidates)
        for _ in range(count):
            x,y=next((x,y) for x,y in candidates
                     if all((x-px)**2+(y-py)**2>=64 for px,py in centers))
            centers.append((x,y))
            ember(s,x,y)
        assert sum(s.getpixel((x,y))==(239,173,83) for y in range(32) for x in range(32))==count
        i=len(tiles);tiles.append(s)
        entries.append(dict(id=i,name=f'불씨 {count}개 · 랜덤 {variant}',file=f'burnt_{i:02}.webp',
                            rect=[i%4*32,i//4*32,32,32],category='embers',family=family,position=f'랜덤 {variant}'))
for old_id,new_id in [(10,16),(11,17),(12,18)]:
    tiles[old_id]=tiles[new_id].copy()
    entries[old_id].update(name=entries[new_id]['name'],category='embers',family=16,
                           position=entries[new_id]['position'],replacement=new_id)
visible=[s for entry,s in zip(entries,tiles) if not entry.get('hidden')]
sheet=Image.new('RGB',(128,((len(tiles)+3)//4)*32),(78,72,64))
for entry,s in zip(entries,tiles):
    for y in range(32):
        for x in range(32):
            if x<3 or x>=29 or y<3 or y>=29: assert s.getpixel((x,y))==base.getpixel((x,y))
    s.save(root/entry['file'],'WEBP',lossless=True,exact=True)
    with Image.open(root/entry['file']) as saved: assert saved.convert('RGB').tobytes()==s.tobytes()
    sheet.paste(s,tuple(entry['rect'][:2]))
assert len({s.tobytes() for s in visible})==len(visible)
assert all(sum(s.getpixel((x,y))==(239,173,83) for y in range(32) for x in range(32))<=2 for s in tiles)
sheet.save(root/'burnt-forest-32.webp','WEBP',lossless=True,exact=True)
meta=dict(image='burnt-forest-32.webp',tilewidth=32,tileheight=32,columns=4,tilecount=len(tiles),margin=0,spacing=0,tiles=entries)
(root/'tileset.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
preview=Image.new('RGB',(256,256))
rng=random.Random(19)
for y in range(8):
    for x in range(8): preview.paste(tiles[0] if rng.random()<.4 else rng.choice(visible[1:]),(x*32,y*32))
preview.save(root/'variants-preview.png')
print(f'Verified: {len(visible)} selectable burnt forest tiles, at most two embers, shared edges, lossless WebP.')
