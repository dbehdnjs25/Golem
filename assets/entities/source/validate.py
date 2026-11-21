"""Read-only validation of the delivered entity PNGs and Aseprite layers."""
from pathlib import Path
import struct
import zlib

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SIZES = {
    "player": (48, 64), "wolf": (64, 48), "rabbit": (32, 32),
    "golem": (64, 80), "burnt_forest_golem": (64, 80),
    "snowfield_golem": (64, 80), "wind_plateau_golem": (64, 80),
}


def validate(key, size):
    data = (ROOT / f"{key}.aseprite").read_bytes()
    length, magic, frames, width, height, depth = struct.unpack_from("<I5H", data)
    assert (length, magic, frames, width, height, depth) == (
        len(data), 0xA5E0, 1, *size, 32
    ), key
    frame_size, frame_magic, old_count = struct.unpack_from("<IHH", data, 128)
    assert frame_magic == 0xF1FA and frame_size + 128 == len(data)
    count = old_count or struct.unpack_from("<I", data, 140)[0]
    offset = 144
    layers, cels = [], {}
    for _ in range(count):
        chunk_size, kind = struct.unpack_from("<IH", data, offset)
        payload = data[offset + 6:offset + chunk_size]
        if kind == 0x2004:
            name_len = struct.unpack_from("<H", payload, 16)[0]
            layers.append(payload[18:18 + name_len].decode("utf-8"))
        elif kind == 0x2005:
            layer, x, y, opacity, cel_type = struct.unpack_from("<HhhBH", payload)
            assert opacity == 255 and cel_type in (0, 2), key
            cw, ch = struct.unpack_from("<HH", payload, 16)
            raw = zlib.decompress(payload[20:]) if cel_type == 2 else payload[20:]
            assert len(raw) == cw * ch * 4
            image = Image.frombytes("RGBA", (cw, ch), raw)
            colors = {image.getpixel((x, y)) for y in range(ch) for x in range(cw)}
            colors = {p for p in colors if p[3]}
            assert len(colors) <= 1, (key, layers[layer], colors)
            assert all(p[3] == 255 for p in colors)
            cels[layer] = (image, x, y)
        offset += chunk_size
    assert layers[0] == "Outline", (key, layers)
    assert len(layers) >= 7
    merged = Image.new("RGBA", size)
    contour = Image.new("RGBA", size)
    for layer in range(len(layers)):
        if layer in cels:
            image, x, y = cels[layer]
            merged.alpha_composite(image, (x, y))
            if layer == 0:
                contour.alpha_composite(image, (x, y))
    with Image.open(ROOT / f"{key}.png") as source:
        png = source.convert("RGBA")
    assert png.size == size
    assert png.tobytes() == merged.tobytes(), (key, "PNG differs from layers")
    assert set(png.getchannel("A").tobytes()) == {0, 255}, key
    alpha = png.getchannel("A")
    bounds = alpha.getbbox()
    assert bounds and bounds[0] >= 2 and bounds[1] >= 2
    assert bounds[2] <= width - 2 and bounds[3] <= height - 2
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if alpha.getpixel((x, y)) and any(
                not alpha.getpixel(p)
                for p in ((x-1, y), (x+1, y), (x, y-1), (x, y+1))
            ):
                assert contour.getpixel((x, y)) == (48, 48, 36, 255), (key, x, y)
    print(f"PASS {key}: {width}x{height}, {len(layers)} monochrome layers, binary alpha, PNG matches Aseprite")


if __name__ == "__main__":
    for key, size in SIZES.items():
        validate(key, size)
