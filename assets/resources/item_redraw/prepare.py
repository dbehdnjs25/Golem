"""Generate native Aseprite conversion jobs and export completed imagegen sources."""
from pathlib import Path
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASEPRITE = Path("C:/Users/ykb62/Desktop/aseprite.exe")
ITEMS = json.loads((HERE / "prompts.json").read_text(encoding="utf-8"))["items"]
PALETTES = {
    "wood": ["987148","C2A16B","624D35"],
    "stone": ["898777","BCB89B","585D50"],
    "copper": ["B77C50","E0AC72","79543B"],
    "iron": ["9AABA6","D1D4BE","627672"],
    "gold": ["C9A64E","EDD484","897038"],
    "brass": ["AD9757","D6C486","756941"],
    "steel": ["788B94","B4C2C1","4D606A"],
    "green": ["78914F","B2BC79","4A613C"],
    "ice": ["83B9C5","C8E4D9","527D94"],
    "violet": ["826887","B8A1BB","524359"],
    "black": ["55544E","827D6A","363C35"],
    "ember": ["CC803B","EFBE69","895133"],
    "red": ["B46A65","DEA18A","794A48"],
    "rose": ["B5687E","DFA2AA","7D465F"],
    "teal": ["6FAF9D","B9D8B1","42776F"],
    "cream": ["C1B38C","E7DBB5","8C8165"],
}

def materials(key):
    if key.endswith(("_axe","_pick")):
        grade=key.split("_")[0]
        return ["wood", "stone" if grade=="crude" else grade, "cream"]
    if key.endswith("_ingot"):
        return [key.split("_")[0]]
    special={
        "core_shard":["teal","ice"],"twig":["wood"],"pebble":["stone"],
        "grass":["green"],"charcoal":["black"],"obsidian":["violet","black"],
        "obsidian_stone":["stone","violet","black"],"frost_crystal":["ice"],
        "weathered_stone":["stone","cream"],"bog_moss":["green","wood"],
        "thunder_stone":["gold","cream"],"bench":["wood","iron"],
        "fine_bench":["wood","iron","brass"],"smelter":["stone","black","ember"],
        "hearth":["stone","black","ember"],"blast_furnace":["steel","copper","ember"],
        "burnt_forest_detector":["wood","brass","ember"],
        "snowfield_detector":["wood","brass","ice"],
        "wind_detector":["wood","brass","teal"],
        "bog_detector":["wood","brass","green"],
        "wasteland_detector":["wood","gold","ice"],
        "staff":["wood","violet","green"],"worn_pack":["wood","cream"],
        "leather_pack":["wood","brass"],"hide":["wood","cream"],
        "raw_meat":["red","cream"],"cooked_meat":["wood","cream"],
        "potion":["rose","ice","wood"],
    }
    return special[key]

def write_jobs():
    (HERE / "final32").mkdir(exist_ok=True)
    source=(HERE / "conversion_template.lua").read_text(encoding="utf-8")
    start=source.index("local specs = {")
    end=source.index("if app.params.key then",start)
    rows=[]
    for key,_ in ITEMS:
        names=list(dict.fromkeys(materials(key)))
        mats=",".join(n+'={'+",".join('"'+c+'"' for c in PALETTES[n])+'}' for n in names)
        rows.append('  {"'+key+'",32,32,{'+mats+'}},')
    source=source[:start]+"local specs = {\n"+"\n".join(rows)+"\n}\n"+source[end:]
    source=source.replace("C:/Project/pygame_project/assets/entities",HERE.as_posix())
    source=source.replace("/remaining/source/","/source/")
    source=source.replace('root.."/"..spec[1]', 'root.."/final32/"..spec[1]')
    source=source.replace('root.."/"..key', 'root.."/final32/"..key')
    source=source.replace("assets/entities/remaining/prepare.lua","assets/resources/item_redraw/prepare.lua")
    (HERE / "prepare.lua").write_text(source,encoding="utf-8")

def export_available():
    for key,_ in ITEMS:
        if (HERE/"source"/f"{key}.png").exists() and not (HERE/"final32"/f"{key}.png").exists():
            result=subprocess.run([str(ASEPRITE),"-b","--script-param",f"key={key}",
                                   "--script",str(HERE/"prepare.lua")],
                                  capture_output=True,text=True,creationflags=0x08000000)
            if result.returncode or not (HERE/"final32"/f"{key}.png").exists():
                raise RuntimeError(f"{key}: {result.stdout} {result.stderr}")
            print("Exported",key,flush=True)
    print("Ready",sum((HERE/"final32"/f"{k}.png").exists() for k,_ in ITEMS),"/",len(ITEMS),flush=True)

if __name__=="__main__":
    write_jobs()
    export_available()
