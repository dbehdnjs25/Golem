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
    body='#596047';highlight='#858362';shadow='#675342'
    silhouette=rng.randrange(4)
    if silhouette==0:  # classic tall saguaro with two arms
        d.line([(x,y+4),(x+1,y-5)],fill=body,width=3)
        d.line([(x,y),(x-3,y-1),(x-3,y-4)],fill=body,width=2)
        d.line([(x+1,y-2),(x+4,y-3),(x+4,y-6)],fill=body,width=2)
        d.point((x+2,y-5),fill=highlight)
    elif silhouette==1:  # broad, low cactus with uneven arms
        d.line([(x-1,y+4),(x,y-2),(x+1,y-5)],fill=body,width=3)
        d.line([(x,y+1),(x-4,y),(x-4,y-3)],fill=body,width=2)
        d.line([(x,y-1),(x+3,y-2),(x+4,y-5)],fill=body,width=2)
        d.point((x+1,y-5),fill=highlight)
    elif silhouette==2:  # leaning trunk and one long side branch
        d.line([(x-2,y+4),(x,y+1),(x+1,y-5)],fill=body,width=3)
        d.line([(x,y),(x-3,y-1),(x-4,y-4)],fill=body,width=2)
        d.point((x+2,y-5),fill=highlight)
    else:  # clustered round cactus columns
        d.line([(x-3,y+3),(x-3,y-1)],fill=body,width=3)
        d.line([(x,y+4),(x,y-4)],fill=body,width=3)
        d.line([(x+3,y+3),(x+3,y-2)],fill=body,width=3)
        d.point((x+1,y-4),fill=highlight)
    d.line([(x-4,y+5),(x+4,y+5)],fill=shadow)



def rocks(s,x,y,rng):
    d=ImageDraw.Draw(s)
    d.polygon([(x-5,y+2),(x-3,y-2),(x+1,y-4),(x+5,y-1),(x+4,y+3),(x-2,y+4)],fill='#927852')
    d.polygon([(x-3,y-2),(x+1,y-4),(x+3,y-1),(x-1,y),(x-4,y+2)],fill='#c1a16c')
    d.line([(x-2,y+2),(x+3,y+1)],fill='#745d43')
    d.ellipse((x+4,y+2,x+5,y+3),fill='#a68b5d')


def tracks(s,x,y,rng):
    d=ImageDraw.Draw(s)
    for dy,width in [(-3,7),(0,11),(3,6)]:
        d.line([(x-width//2,y+dy),(x,y+dy-1),(x+width//2,y+dy)],fill='#b18d5b')
        d.line([(x-width//2+1,y+dy+1),(x+width//2-1,y+dy+1)],fill='#d1b17b')


def mixed(s,x,y,rng):
    scrub(s,x-2,y,rng);rocks(s,x+2,y+2,rng)


def cracked(s,shape,pose,rng):
    d=ImageDraw.Draw(s)
    # Broken polygonal plates with tapered, branching fissures. Keep the whole
    # network inside the center so the tile edges still join the plain ground.
    networks=[
        # Shape 1: two short, separated forked cracks instead of one long seam.
        [[(8,9),(11,11),(12,14),(15,16)],[(12,14),(10,17),(9,20)],
         [(19,10),(17,13),(19,16),(22,18)],[(19,16),(17,19)]],
        [[(9,8),(13,9),(15,12),(19,11),(22,14),(20,18),(22,22)],
         [(15,12),(13,16),(15,19),(13,23)],[(20,18),(17,21),(16,24)],
         [(9,8),(8,12),(10,15)]],
        [[(8,14),(11,11),(15,12),(18,9),(22,10),(24,13)],
         [(11,11),(12,16),(9,19),(10,23)],[(15,12),(17,16),(15,20),(18,23)],
         [(22,10),(21,15),(23,18)]],
        # A wide zigzag running across the tile, with a few short side splits.
        [[(6,10),(10,12),(12,16),(16,15),(19,18),(24,17)],
         [(12,16),(10,20),(11,24)],[(16,15),(17,11),(20,9)],
         [(19,18),(21,22),(24,23)]],
        # A broken ring around a dry plate, visibly different from the long seams.
        # Shape 5: a broad, open zigzag with a detached short branch.
        [[(7,12),(11,10),(14,12),(17,16),(21,17),(25,14)],
         [(14,12),(15,8),(18,6)],[(17,16),(15,20),(17,23)]],
        # Several separate, deep splits form a sparse starburst.
        [[(15,15),(12,12),(9,8)],[(15,15),(19,12),(23,9)],
         [(15,15),(12,19),(9,23)],[(15,15),(19,18),(22,23)],
         [(12,12),(10,13)],[(19,18),(21,17)]]
    ]
    # Vary the location for every generated tile. Keep a single main split and
    # at most one branch so the soil stays mostly intact.
    shift_x,shift_y=rng.randint(-1,1),rng.randint(-1,1)
    pose_offsets=[(0,0),(2,-1),(-1,2),(-2,-1)]
    pose_x,pose_y=pose_offsets[pose]
    source=networks[shape-1]
    paths=[source[0]]
    branches=source[1:]
    if branches and rng.random()<0.55:
        paths.append(rng.choice(branches))
    def transform(x,y):
        # Four unmistakable orientations, each also moved to a distinct spot.
        if pose==1:
            x,y=32-y,x
        elif pose==2:
            x,y=32-x,32-y
        elif pose==3:
            x,y=y,32-x
        return x+shift_x+pose_x,y+shift_y+pose_y
    for path in paths:
        path=[transform(x,y) for x,y in path]
        d.line([(x+1,y+1) for x,y in path],fill='#b99463',width=1)
        d.line(path,fill='#76563a',width=1)
        for x,y in path[1:-1]:
            d.point((x,y),fill='#60482f')
    # Fine hairline offshoots make the larger plates less geometric.
    offshoots=[[(11,14,-2,1),(20,10,1,-2),(16,17,-2,2)],
               [(15,19,-2,1),(20,18,2,1),(10,15,-1,2)],
               [(12,16,-2,2),(17,16,2,2),(21,15,2,-1)],
               [(10,12,-2,-1),(19,18,2,1),(17,11,1,-2)],
               [(10,13,-2,1),(18,20,1,2),(15,8,-1,-2)],
               [(12,12,-2,-1),(19,12,2,-1),(12,19,-2,2)]]
    if rng.random()<0.35:
        x,y,dx,dy=rng.choice(offshoots[shape-1])
        points=[transform(x,y),transform(x+dx,y+dy),transform(x+dx*2,y+dy*2)]
        d.line(points,fill='#80603f',width=1)


tiles=[base]
entries=[dict(id=0,name='황무지 기본 땅',file='waste_00.webp',rect=[0,0,32,32],category='ground',family=0,position='기본')]
groups=[('마른 덤불','plants',scrub),('선인장','plants',cactus),('풍화된 사암','stones',rocks),
        ('바람 자국','ground',tracks),('덤불과 사암','mixed',mixed)]
for family,(name,category,draw) in enumerate(groups,start=1):
    for variant,(x,y) in enumerate([(10,12),(20,17),(13,20)],start=1):
        s=base.copy();draw(s,x,y,random.Random(40+family*7+variant))
        i=len(tiles);tiles.append(s)
        entries.append(dict(id=i,name=f'{name} · 랜덤 {variant}',file=f'waste_{i:02}.webp',
                            rect=[i%4*32,i//4*32,32,32],category=category,family=family,position=f'랜덤 {variant}',hidden=(family==4)))
family=len(tiles)
pose_names=['\uAE30\uBCF8 \uBC29\uD5A5','90\u00B0 \uD68C\uC804 \u00B7 \uC6B0\uCE21','180\u00B0 \uD68C\uC804 \u00B7 \uC544\uB798\uCABD','270\u00B0 \uD68C\uC804 \u00B7 \uC88C\uCE21']
for shape in range(1,7):
    for pose,pose_name in enumerate(pose_names):
        s=base.copy();cracked(s,shape,pose,random.Random(70+shape*11+pose))
        i=len(tiles);tiles.append(s)
        entries.append(dict(id=i,name=f'\uAC08\uB77C\uC9C4 \uB545 {shape} \u00B7 {pose_name}',file=f'waste_{i:02}.webp',
                            rect=[i%4*32,i//4*32,32,32],category='ground',family=family,position=f'{pose_name} {shape}'))
# Add more cactus silhouettes while leaving existing tile IDs intact.
for variant,(x,y) in enumerate([(10,12),(20,17),(13,20)],start=4):
    s=base.copy();cactus(s,x,y,random.Random(249 if variant==6 else 240+variant))
    i=len(tiles);tiles.append(s)
    entries.append(dict(id=i,name=f'\uC120\uC778\uC7A5 \u00B7 \uBAA8\uC591 {variant}',file=f'waste_{i:02}.webp',
                        rect=[i%4*32,i//4*32,32,32],category='plants',family=2,position=f'\uBAA8\uC591 {variant}'))
for entry in entries:
    if entry.get('family') in (1,2,3,4,5):
        entry['hidden']=True
        tiles[entry['id']]=base.copy()
sheet=Image.new('RGB',(128,((len(tiles)+3)//4)*32))
for entry,s in zip(entries,tiles):
    for y in range(32):
        for x in range(32):
            if x<3 or x>=29 or y<3 or y>=29:
                assert s.getpixel((x,y))==base.getpixel((x,y)), (entry['id'],entry['name'],x,y)
    s.save(root/entry['file'],'WEBP',lossless=True,exact=True)
    with Image.open(root/entry['file']) as saved:assert saved.convert('RGB').tobytes()==s.tobytes()
    sheet.paste(s,tuple(entry['rect'][:2]))
assert len(tiles)==43
assert all(tiles[e['id']].tobytes()==base.tobytes() for e in entries if e.get('hidden'))
sheet.save(root/'wasteland-32.webp','WEBP',lossless=True,exact=True)
meta=dict(image='wasteland-32.webp',tilewidth=32,tileheight=32,columns=4,tilecount=43,margin=0,spacing=0,tiles=entries)
(root/'tileset.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
preview=Image.new('RGB',(256,256));rng=random.Random(56)
for y in range(8):
    for x in range(8):preview.paste(tiles[0] if rng.random()<.6 else rng.choice(tiles[1:]),(x*32,y*32))
preview.save(root/'variants-preview.png')
print('Verified: 43 wasteland tiles, cracked earth variants, shared edges, lossless WebP.')
