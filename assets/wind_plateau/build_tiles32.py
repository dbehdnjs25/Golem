"""Build seamless 32px windswept highland ground and decoration variants."""
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw

root=Path(__file__).parent/'tiles32'
root.mkdir(parents=True,exist_ok=True)
rng=random.Random(20261024)
noise=[[rng.uniform(-1,1) for _ in range(32)] for _ in range(32)]
base=Image.new('RGB',(32,32))
for y in range(32):
    for x in range(32):
        soft=sum(noise[(y+dy)%32][(x+dx)%32] for dy in (-1,0,1) for dx in (-2,-1,0,1,2))/15
        tone=round(soft*6+noise[y][x])
        base.putpixel((x,y),(127+tone,135+tone,115+tone))


def grass(s,x,y,rng):
    d=ImageDraw.Draw(s)
    for dx,height in [(-3,4),(0,6),(2,4)]:
        d.line([(x+dx,y),(x+dx+1,y-2),(x+dx+4,y-height)],fill='#65704f')
        d.line([(x+dx+2,y-3),(x+dx+4,y-height)],fill='#a8ad7b')
    d.line([(x-3,y+1),(x+3,y+1)],fill='#727b5d')


def pebbles(s,x,y,rng):
    d=ImageDraw.Draw(s)
    for dx,dy in [(-3,-2),(2,0),(-1,3)]:
        d.rectangle((x+dx,y+dy,x+dx+2,y+dy+1),fill='#969b8b')
        d.point((x+dx,y+dy),fill='#bdc0aa')
        d.line([(x+dx,y+dy+2),(x+dx+2,y+dy+2)],fill='#69715f')


def rock(s,x,y,rng):
    d=ImageDraw.Draw(s)
    d.ellipse((x-5,y+1,x+6,y+4),fill='#727965')
    d.polygon([(x-5,y),(x-2,y-5),(x+3,y-4),(x+5,y),(x+3,y+3),(x-3,y+2)],fill='#979c8b')
    d.polygon([(x-5,y),(x-2,y-5),(x+3,y-4),(x+1,y-1)],fill='#b9bcaa')
    d.line([(x-3,y+1),(x+3,y)],fill='#7a826f')
    d.line([(x-1,y-3),(x+2,y-3)],fill='#c8cab5')


def erosion(s,x,y,rng):
    d=ImageDraw.Draw(s)
    for dx,dy,length in [(-5,-2,8),(-3,1,10),(0,4,5)]:
        d.line([(x+dx,y+dy),(x+dx+length//2,y+dy-1),(x+dx+length,y+dy-1)],fill='#75806a')
        d.line([(x+dx+1,y+dy+1),(x+dx+length-1,y+dy)],fill='#959e83')


def mixed(s,x,y,rng):
    grass(s,x-2,y-2,rng)
    pebbles(s,x+2,y,rng)


tiles=[base]
entries=[dict(id=0,name='바람 고원 기본 땅',file='plateau_00.webp',rect=[0,0,32,32],category='ground',family=0,position='기본')]
for group,(name,category,draw) in enumerate([('바람에 눕는 풀','plants',grass),('고원 자갈','stones',pebbles),
                                           ('풍화된 바위','stones',rock),('바람에 깎인 땅','ground',erosion),
                                           ('고원 풀과 자갈','mixed',mixed)]):
    family=len(tiles)
    for variant,(x,y) in enumerate([(10,12),(20,16),(13,22)],start=1):
        s=base.copy();draw(s,x,y,random.Random(group*10+variant))
        i=len(tiles);tiles.append(s)
        entries.append(dict(id=i,name=f'{name} · 랜덤 {variant}',file=f'plateau_{i:02}.webp',
                            rect=[i%4*32,i//4*32,32,32],category=category,family=family,position=f'랜덤 {variant}'))
sheet=Image.new('RGB',(128,128))
for entry,s in zip(entries,tiles):
    for y in range(32):
        for x in range(32):
            if x<3 or x>=29 or y<3 or y>=29: assert s.getpixel((x,y))==base.getpixel((x,y))
    s.save(root/entry['file'],'WEBP',lossless=True,exact=True)
    with Image.open(root/entry['file']) as saved: assert saved.convert('RGB').tobytes()==s.tobytes()
    sheet.paste(s,tuple(entry['rect'][:2]))
assert len({s.tobytes() for s in tiles})==16
sheet.save(root/'wind_plateau-32.webp','WEBP',lossless=True,exact=True)
meta=dict(image='wind_plateau-32.webp',tilewidth=32,tileheight=32,columns=4,tilecount=16,margin=0,spacing=0,tiles=entries)
(root/'tileset.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
preview=Image.new('RGB',(256,256))
rng=random.Random(76)
for y in range(8):
    for x in range(8): preview.paste(tiles[0] if rng.random()<.6 else rng.choice(tiles[1:]),(x*32,y*32))
preview.save(root/'variants-preview.png')
print('Verified: 16 unique highland tiles, common 3px borders, lossless WebP, mixed preview.')
