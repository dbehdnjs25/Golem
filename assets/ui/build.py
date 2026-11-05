"""Build the carved-stone hotbar pieces and a transparent preview."""
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).parent
PIXEL_DIGITS = {
    "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"),
    "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "110", "001", "110"),
}
DIGIT_SCALE = 3
def build_slot(selected=False):
    image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    def rounded_pixel_rect(box, radius, fill):
        left, top, right, bottom = box
        for y in range(top, bottom + 1):
            inset = max(0, radius - min(y - top, bottom - y) - 1)
            draw.line((left + inset, y, right - inset, y), fill=fill)

    # Pixel-stepped corners keep the frame square overall, with a soft 2px cut.
    if selected:
        rounded_pixel_rect((1, 1, 38, 38), 3, (205, 194, 156, 255))
        rounded_pixel_rect((2, 2, 37, 37), 2, (143, 134, 106, 255))
        rounded_pixel_rect((4, 4, 35, 35), 1, (38, 41, 39, 245))
    else:
        rounded_pixel_rect((1, 1, 38, 38), 3, (76, 81, 78, 255))
        rounded_pixel_rect((2, 2, 37, 37), 2, (105, 111, 106, 255))
        rounded_pixel_rect((4, 4, 35, 35), 1, (32, 35, 34, 245))
    return image


def draw_pixel_digit(draw, digit, x, y, color):
    for row, bits in enumerate(PIXEL_DIGITS[str(digit)]):
        for column, bit in enumerate(bits):
            if bit == "1":
                left = x + column * DIGIT_SCALE
                top = y + row * DIGIT_SCALE
                draw.rectangle(
                    (left + 1, top + 1, left + DIGIT_SCALE, top + DIGIT_SCALE),
                    fill=(15, 18, 17, 255),
                )
                draw.rectangle(
                    (left, top, left + DIGIT_SCALE - 1, top + DIGIT_SCALE - 1),
                    fill=color,
                )


empty = build_slot()
selected = build_slot(True)
empty.save(ROOT / "hotbar_slot.png")
selected.save(ROOT / "hotbar_slot_selected.png")

# Individual relic sockets float on transparency; there is no backing plate.
preview = Image.new("RGBA", (232, 60), (0, 0, 0, 0))
draw = ImageDraw.Draw(preview)
for index in range(5):
    x = 4 + index * 44
    slot = selected if index == 2 else empty
    preview.alpha_composite(slot, (x, 10))
    draw_pixel_digit(draw, index + 1, x + 15, 10 - 7, (205, 207, 190, 255))
preview.save(ROOT / "hotbar_preview.png")

print("Built the Golem hotbar slots and transparent preview.")
