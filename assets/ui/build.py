"""Build the pixel-art hotbar components and preview."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).parent

def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def build_slot(selected=False):
    image=Image.new("RGBA",(40,40),(0,0,0,0));d=ImageDraw.Draw(image)
    if selected:
        rounded(d,(1,1,38,38),5,(53,44,33,248),(245,199,105,255),2)
        rounded(d,(4,4,35,35),3,(39,37,39,235),(180,137,72,255),1)
        d.line((8,5,31,5),fill=(255,225,160,210),width=1)
        d.line((5,9,5,30),fill=(245,204,120,150),width=1)
    else:
        rounded(d,(1,1,38,38),5,(24,27,39,245),(105,113,137,255),2)
        rounded(d,(4,4,35,35),3,(32,36,49,238),(57,64,83,255),1)
        d.line((8,5,31,5),fill=(144,151,172,145),width=1)
        d.line((7,34,32,34),fill=(15,17,25,180),width=1)
    return image

# Composite backdrop matching the five-slot gameplay hotbar (44px pitch).
panel=Image.new("RGBA",(232,60),(0,0,0,0));d=ImageDraw.Draw(panel)
rounded(d,(0,5,231,59),9,(13,16,26,222),(83,91,116,245),2)
rounded(d,(3,8,228,56),7,(26,29,41,228),(47,53,70,210),1)
d.line((12,7,219,7),fill=(158,168,194,135),width=1)
d.line((10,57,220,57),fill=(7,9,16,180),width=1)
panel.save(ROOT/"hotbar_panel.png")
empty=build_slot(False);selected=build_slot(True)
empty.save(ROOT/"hotbar_slot.png");selected.save(ROOT/"hotbar_slot_selected.png")
preview=panel.copy()
for i in range(5):preview.alpha_composite(selected if i==2 else empty,(6+i*44,10))
pd=ImageDraw.Draw(preview)
# Small amber focus tick makes the active slot legible even without color.
pd.line((6+2*44+11,53,6+2*44+29,53),fill=(249,206,120,245),width=2)
preview.save(ROOT/"hotbar_preview.png")
print("Built 5-slot hotbar UI assets.")
