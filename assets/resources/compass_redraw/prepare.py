"""Export only the five replacement compass icons through native Aseprite."""
from pathlib import Path
import subprocess
import json

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/"item_redraw"
SPECS={
    "burnt_forest_detector":["CC803B","EFBE69","895133"],
    "snowfield_detector":["83B9C5","C8E4D9","527D94"],
    "wind_detector":["91B29B","C7D5B7","5A8375"],
    "bog_detector":["78914F","B2BC79","4A613C"],
    "wasteland_detector":["C9A64E","EDD484","897038"],
}
(HERE/"final32").mkdir(exist_ok=True)
source=(OLD/"prepare.lua").read_text(encoding="utf-8")
start=source.index("local specs = {")
end=source.index("if app.params.key then",start)
rows=[]
for key,accent in SPECS.items():
    materials={"bronze":["AD9757","D6C486","756941"],"dial":["C1B38C","E7DBB5","8C8165"],"needle":accent}
    mats=",".join(n+"={"+",".join('"'+c+'"' for c in colors)+"}" for n,colors in materials.items())
    rows.append('  {"'+key+'",32,32,{'+mats+'}},')
source=source[:start]+"local specs = {\n"+"\n".join(rows)+"\n}\n"+source[end:]
source=source.replace(OLD.as_posix(),HERE.as_posix())
(HERE/"prepare.lua").write_text(source,encoding="utf-8")
for key in SPECS:
    if (HERE/"source"/f"{key}.png").exists() and not (HERE/"final32"/f"{key}.png").exists():
        subprocess.run(["C:/Users/ykb62/Desktop/aseprite.exe","-b","--script-param",f"key={key}",
                        "--script",str(HERE/"prepare.lua")],check=True,capture_output=True)
        print("Exported",key)
print("Ready",len(list((HERE/"final32").glob("*.png"))),"/ 5")
