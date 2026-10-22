"""Build 32px seamless wasteland ground and dry-land detail tiles."""
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw

root=Path(__file__).parent/'tiles32'
root.mkdir(parents=True,exist_ok=True)
rng=random.Random(20261026)
noise=[[rng.uniform(-1,1) for _ in range(32)] for _ in range(32)]
base=Image.new('RGB',(32,32))
for y in range(32):
    for x in range(32):
        soft=sum(noise[(y+dy)%32][(x+dx)%32] for dy in (-1,0,1) for dx in (-2,-1,0,1,2))/15
        n=round(soft*7+noise[y][x]*2)
        base.putpixel((x,y),(157+n,126+n,83+n))


def scrub(s,x,y,rng):
    d=ImageDraw.Draw(s)
    d.line([(x-4,y+2),(x,y),(x+4,y+1)],fill='#62553a')
    d.line([(x,y),(x-2,y-3)],fill='#756044')
    d.line([(x,y),(x+2,y-4)],fill='#67553b')
    for px,py in [(x-3,y+1),(x-2,y-2),(x+3,y),(x+2,y-3)]:
        d.point((px,py),fill='#85804c')


def cactus(s,x,y,rng):
    d=ImageDraw.Draw(s)
    d.line([(x-2,y+4),(x+2,y-5)],fill='#596047',width=3)
    d.line([(x-2,y),(x-5,y-2),(x-5,y-5)],fill='#596047',width=2)
    d.line([(x+1,y-2),(x+4,y-3),(x+4,y-6)],fill='#596047',width=2)
    d.point((x+2,y-5),fill='#8d8758')
    d.line([(x-3,y+5),(x+4,y+5)],fill='#675342')


def rocks(s,x,y,rng):
    d=ImageDraw.Draw(s)
    d.polygon([(x-5,y+2),(x-3,y-2),(x+1,y-4),(x+5,y-1),(x+4,y+3),(x-2,y+4)],fill='#927852')
    d.polygon([(x-3,y-2),(x+1,y-4),(x+3,y-1),(x-1,y),(x-4,y+2)],fill='#c1a16c')
    d.line([(x-2,y+2),(x+3,y+1)],fill='#745d43')
    d.ellipse((x+5,y+2,x+7,y+4),fill='#a68b5d')


def tracks(s,x,y,rng):
    d=ImageDraw.Draw(s)
    for dy,width in [(-3,7),(0,11),(3,6)]:
        d.line([(x-width//2,y+dy),(x,y+dy-1),(x+width//2,y+dy)],fill='#b18d5b')
        d.line([(x-width//2+1,y+dy+1),(x+width//2-1,y+dy+1)],fill='#d1b17b')


def mixed(s,x,y,rng):
    scrub(s,x-2,y,rng);rocks(s,x+2,y+2,rng)


tiles=[base]
entries=[dict(id=0,name='황무지 기본 땅',file='waste_00.webp',rect=[0,0,32,32],category='ground',family=0,position='기본')]
groups=[('마른 덤불','plants',scrub),('선인장','plants',cactus),('풍화된 사암','stones',rocks),
        ('바람 자국','ground',tracks),('덤불과 사암','mixed',mixed)]
for family,(name,category,draw) in enumerate(groups,start=1):
    for variant,(x,y) in enumerate([(10,12),(20,17),(13,22)],start=1):
        s=base.copy();draw(s,x,y,random.Random(40+family*7+variant))
        i=len(tiles);tiles.append(s)
        entries.append(dict(id=i,name=f'{name} · 랜덤 {variant}',file=f'waste_{i:02}.webp',
                            rect=[i%4*32,i//4*32,32,32],category=category,family=family,position=f'랜덤 {variant}'))
sheet=Image.new('RGB',(128,128))
for entry,s in zip(entries,tiles):
    for y in range(32):
        for x in range(32):
            if x<3 or x>=29 or y<3 or y>=29:
                assert s.getpixel((x,y))==base.getpixel((x,y)), (entry['name'],x,y)
    s.save(root/entry['file'],'WEBP',lossless=True,exact=True)
    with Image.open(root/entry['file']) as saved:assert saved.convert('RGB').tobytes()==s.tobytes()
    sheet.paste(s,tuple(entry['rect'][:2]))
assert len({s.tobytes() for s in tiles})==16
sheet.save(root/'wasteland-32.webp','WEBP',lossless=True,exact=True)
meta=dict(image='wasteland-32.webp',tilewidth=32,tileheight=32,columns=4,tilecount=16,margin=0,spacing=0,tiles=entries)
(root/'tileset.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
preview=Image.new('RGB',(256,256));rng=random.Random(56)
for y in range(8):
    for x in range(8):preview.paste(tiles[0] if rng.random()<.6 else rng.choice(tiles[1:]),(x*32,y*32))
preview.save(root/'variants-preview.png')
print('Verified: 16 wasteland tiles, shared 3px edges, lossless WebP, mixed preview.')
