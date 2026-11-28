"""Validate and install the complete approved 16px item redraw."""
from pathlib import Path
import json
import runpy
import shutil

HERE=Path(__file__).resolve().parent
TARGET=HERE.parent/"items"
items=json.loads((HERE/"prompts.json").read_text(encoding="utf-8"))["items"]
if __name__=="__main__":
    validate=runpy.run_path(str(HERE/"validate.py"))["validate"]
    for key,_ in items:
        validate(key,(16,16))
    assert all((HERE/f).exists() for f in ("atlas16.png","atlas16.aseprite","preview16.png"))
    backup=HERE/"before_install16"
    backup.mkdir(exist_ok=True)
    TARGET.mkdir(exist_ok=True)
    pairs=[(HERE/"final16"/f"{key}{ext}",TARGET/f"{key}{ext}")
           for key,_ in items for ext in (".png",".aseprite")]
    pairs.extend([
        (HERE/"atlas16.png",TARGET/"item_icons_atlas.png"),
        (HERE/"atlas16.aseprite",TARGET/"item_icons.aseprite"),
        (HERE/"atlas16.aseprite",TARGET/"item_icons_atlas.aseprite"),
        (HERE/"preview16.png",TARGET/"item_icons_preview.png"),
    ])
    for source,target in pairs:
        if target.exists() and not (backup/target.name).exists():
            shutil.copy2(target,backup/target.name)
        shutil.copy2(source,target)
        assert source.read_bytes()==target.read_bytes(),target
    print(f"Installed {len(items)} 16x16 PNG/Aseprite pairs and matching atlas/preview.")
