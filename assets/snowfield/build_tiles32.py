"""Build seamless 32px snowfield ground and frost detail tiles."""
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw

root=Path(__file__).parent/'tiles32'
root.mkdir(parents=True,exist_ok=True)
rng=random.Random(20261031)
noise=[[rng.uniform(-1,1) for _ in range(32)] for _ in range(32)]
base=Image.new('RGB',(32,32))
for y in range(32):
    for x in range(32):
        soft=sum(noise[(y+dy)%32][(x+dx)%32] for dy in (-1,0,1) for dx in (-2,-1,0,1,2))/15
        n=round(soft*5+noise[y][x])
        base.putpixel((x,y),(245+n,247+n,249+n))

def drift(s,x,y,rng):
    d=ImageDraw.Draw(s)
    shape=[(x-6,y+1),(x-4,y-1),(x-1,y-2),(x+2,y-1),(x+5,y+1),(x+4,y+3),(x-3,y+3)]
    d.polygon(shape,fill='#e7eef0')
    d.line([(x-4,y+1),(x-1,y),(x+2,y),(x+4,y+1)],fill='#fcfdfd')
    d.line([(x-3,y+3),(x+3,y+3)],fill='#d0dfe3')

def ice(s,x,y,rng):
    d=ImageDraw.Draw(s)
    d.polygon([(x-5,y-1),(x-3,y-4),(x+1,y-5),(x+5,y-2),(x+4,y+2),(x+1,y+4),(x-4,y+3)],fill='#c9dce2')
    d.polygon([(x-3,y-3),(x+1,y-5),(x+3,y-2),(x,y),(x-4,y+1)],fill='#f0f6f7')
    d.line([(x-3,y+2),(x+2,y+1)],fill='#789bab')
    d.point((x+3,y-1),fill='#f0f6f5')

def frost_grass(s,x,y,rng):
    d=ImageDraw.Draw(s)
    for dx,h in [(-3,4),(0,6),(3,3)]:
        d.line([(x+dx,y+2),(x+dx+1,y),(x+dx+2,y-h)],fill='#778d91')
        d.line([(x+dx+1,y),(x+dx+2,y-h)],fill='#dce9e9')
    d.point((x+2,y-6),fill='#f2f6f2')
    d.line([(x-4,y+3),(x+4,y+3)],fill='#9aafb1')

def frost_crack(s,x,y,rng):
    d=ImageDraw.Draw(s)
    paths=[[(x-5,y-3),(x-2,y-1),(x-1,y+2),(x+2,y+3),(x+5,y+1)],
           [(x-1,y+2),(x-3,y+4)],[(x+2,y+3),(x+3,y+5)]]
    for path in paths:
        d.line([(a,b+1) for a,b in path],fill='#c0d7df',width=1)
        d.line(path,fill='#86a8b7',width=1)

def stones(s,x,y,rng):
    d=ImageDraw.Draw(s)
    d.polygon([(x-5,y+2),(x-3,y-2),(x,y-4),(x+4,y-2),(x+5,y+2),(x+1,y+3)],fill='#84979c')
    d.polygon([(x-3,y-2),(x,y-4),(x+3,y-2),(x+1,y-1),(x-3,y)],fill='#e4edef')
    d.line([(x-3,y+2),(x+3,y+2)],fill='#657c83')
    d.point((x+2,y),fill='#bdcdd0')

def mixed(s,x,y,rng):
    frost_grass(s,x-2,y+1,rng);ice(s,x+1,y-1,rng)


def snow_mound(s,variant):
    d=ImageDraw.Draw(s)
    profiles=[
        [(7,23),(9,21),(12,20),(15,19),(18,20),(22,21),(25,23)],
        [(4,22),(7,21),(10,19),(14,20),(17,18),(21,19),(25,21),(27,22)],
        [(9,22),(10,19),(13,17),(16,16),(19,17),(22,20),(23,22)],
        [(5,23),(8,22),(10,19),(12,18),(14,20),(16,21),(18,18),(21,17),(24,19),(27,22)],
        [(6,22),(8,19),(9,15),(12,13),(15,16),(18,19),(22,20),(26,22)],
        [(4,22),(7,19),(11,18),(14,20),(17,18),(21,17),(25,19),(27,22)]
    ]
    # Leave the snowfield underneath untouched; the soft contour alone defines
    # the piled-up edge and lets the white ground flow through below it.
    top=profiles[variant-1]
    d.line(top,fill='#d6e3e8',width=1)
    peak=min(range(len(top)),key=lambda i:top[i][1])
    right_shadow=[(x+1,y+1) for x,y in top[peak:]]
    if len(right_shadow)>1:
        d.line(right_shadow,fill='#ccdce2',width=1)


tiles=[base]
entries=[dict(id=0,name='\uC124\uC6D0 \uAE30\uBCF8 \uB545',file='snow_00.webp',rect=[0,0,32,32],category='ground',family=0,position='\uAE30\uBCF8')]
groups=[('\uB208\uB355\uC774','ground',drift),('\uC5BC\uC74C \uC870\uAC01','ground',ice),
        ('\uC11C\uB9AC \uD480','plants',frost_grass),('\uC11C\uB9AC \uADE0\uC5F4','ground',frost_crack),
        ('\uB208 \uB36E\uC778 \uB3CC','stones',stones),('\uC5BC\uC74C\uACFC \uD480','mixed',mixed)]
for family,(name,category,draw) in enumerate(groups,start=1):
    for variant,(x,y) in enumerate([(10,12),(21,16),(14,21)],start=1):
        s=base.copy();draw(s,x,y,random.Random(500+family*13+variant))
        i=len(tiles);tiles.append(s)
        entries.append(dict(id=i,name=f'{name} ? {variant}',file=f'snow_{i:02}.webp',
                            rect=[i%4*32,i//4*32,32,32],category=category,family=family,position=f'\uBCC0\uD615 {variant}'))
# Add larger snowdrifts after the legacy IDs so saved maps keep their tile meanings.
for variant in range(1,7):
    s=base.copy();snow_mound(s,variant)
    i=len(tiles);tiles.append(s)
    entries.append(dict(id=i,name=f'\uB208\uB354\uBBF8 \uBCC0\uD615 {variant}',file=f'snow_{i:02}.webp',
                        rect=[i%4*32,i//4*32,32,32],category='ground',family=7,position=f'\uD06C\uAE30\uC640 \uBAA8\uC591 {variant}'))
for entry in entries:
    if 0<entry.get('family',0)<7:
        entry['hidden']=True
        tiles[entry['id']]=base.copy()
sheet=Image.new('RGB',(128,((len(tiles)+3)//4)*32))
for entry,s in zip(entries,tiles):
    for y in range(32):
        for x in range(32):
            if x<3 or x>=29 or y<3 or y>=29:
                assert s.getpixel((x,y))==base.getpixel((x,y)),(entry['id'],x,y)
    s.save(root/entry['file'],'WEBP',lossless=True,exact=True)
    with Image.open(root/entry['file']) as saved:assert saved.convert('RGB').tobytes()==s.tobytes()
    sheet.paste(s,tuple(entry['rect'][:2]))
assert len(tiles)==25
assert len({tiles[e['id']].tobytes() for e in entries if not e.get('hidden')})==7
assert all(tiles[e['id']].tobytes()==base.tobytes() for e in entries if e.get('hidden'))
sheet.save(root/'snowfield-32.webp','WEBP',lossless=True,exact=True)
meta=dict(image='snowfield-32.webp',tilewidth=32,tileheight=32,columns=4,tilecount=25,margin=0,spacing=0,tiles=entries)
(root/'tileset.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
preview=Image.new('RGB',(256,256));r=random.Random(85)
for y in range(8):
    for x in range(8):preview.paste(tiles[0] if r.random()<.6 else r.choice(tiles[1:]),(x*32,y*32))
preview.save(root/'variants-preview.png')
print('Verified: 25 snowfield IDs with 7 visible ground/snowdrift tiles, seamless borders, lossless WebP.')


