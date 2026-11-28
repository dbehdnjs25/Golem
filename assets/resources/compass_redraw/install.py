from pathlib import Path
import runpy
import shutil
import subprocess
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/"item_redraw"
keys=["burnt_forest_detector","snowfield_detector","wind_detector","bog_detector","wasteland_detector"]
check=runpy.run_path(str(OLD/"validate.py"))["validate"]
check.__globals__["ROOT"]=HERE/"final32"
for key in keys:
    check(key,(32,32))
for key in keys:
    for ext in (".png",".aseprite"):
        src=HERE/"final32"/(key+ext)
        shutil.copy2(src,HERE.parent/"items"/src.name)
        shutil.copy2(src,OLD/"final32"/src.name)
for script in (HERE/"preview.lua",OLD/"preview32.lua"):
    subprocess.run(["C:/Users/ykb62/Desktop/aseprite.exe","-b","--script",str(script)],check=True,capture_output=True)
for src,dst in (("atlas32.png","item_icons_atlas.png"),("atlas32.aseprite","item_icons.aseprite"),
                ("atlas32.aseprite","item_icons_atlas.aseprite"),("preview32.png","item_icons_preview.png")):
    shutil.copy2(OLD/src,HERE.parent/"items"/dst)
print("Installed and validated all five 32px compass icons.")
