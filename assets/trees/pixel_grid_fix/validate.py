"""Read-only checks for actual pixel grid, saved palette and layer colors."""
from pathlib import Path
import struct
import sys
import zlib
from PIL import Image

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "ready"
KEYS = ("bog", "burnt_forest", "snowfield", "wind_plateau", "wasteland")
for key in KEYS:
    data = (ROOT / f"{key}.aseprite").read_bytes()
    assert struct.unpack_from("<5H", data, 4) == (0xA5E0, 1, 48, 64, 8)
    expected = 11 if key == "snowfield" else 8
    count = struct.unpack_from("<H", data, 134)[0] or struct.unpack_from("<I", data, 140)[0]
    offset = 144
    palette, layers, cels = {}, [], []
    for _ in range(count):
        length, kind = struct.unpack_from("<IH", data, offset)
        p = data[offset + 6:offset + length]
        if kind == 0x2019:
            size, first, last = struct.unpack_from("<III", p)
            assert size == expected and first == 0 and last == expected - 1
            at = 20
            for index in range(first, last + 1):
                flags, r, g, b, a = struct.unpack_from("<H4B", p, at)
                at += 6
                palette[index] = (r, g, b, a)
                if flags & 1:
                    name_size = struct.unpack_from("<H", p, at)[0]
                    at += 2 + name_size
        elif kind == 0x2004:
            n = struct.unpack_from("<H", p, 16)[0]
            layers.append(p[18:18+n].decode("utf-8"))
        elif kind == 0x2005:
            layer, x, y, opacity, cel_type = struct.unpack_from("<HhhBH", p)
            assert opacity == 255 and cel_type in (0, 2)
            w, h = struct.unpack_from("<HH", p, 16)
            raw = zlib.decompress(p[20:]) if cel_type == 2 else p[20:]
            assert len(raw) == w*h and set(raw) - {0} == {layer+1}
            cels.append((x,y,w,h,raw))
        offset += length
    assert len(palette) == expected and len(layers) == expected - 1
    assert layers[0] == "Outline" and palette[0][3] == 0
    merged = [(0,0,0,0)] * (48*64)
    for x,y,w,h,raw in cels:
        for i, value in enumerate(raw):
            if value:
                at = (y+i//w)*48+x+i%w
                assert merged[at][3] == 0
                merged[at] = palette[value]
    png = Image.open(ROOT / f"{key}.png").convert("RGBA")
    assert png.size == (48,64)
    pixels = [png.getpixel((x,y)) for y in range(64) for x in range(48)]
    assert pixels == merged
    assert set(pixels) == set(palette.values())
    assert {p[3] for p in pixels} == {0,255}
    print(f"PASS {key}: 48x64, indexed 8-bit, {expected-1}+transparent palette, monochrome layers, exact PNG match")
