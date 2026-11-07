"""Build pixel UI assets used by the Golem HUD."""
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
DIGIT_SCALE = 2


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
        draw.rectangle((16, 1, 23, 3), fill=(38, 41, 39, 245))
    else:
        rounded_pixel_rect((1, 1, 38, 38), 3, (76, 81, 78, 255))
        rounded_pixel_rect((2, 2, 37, 37), 2, (105, 111, 106, 255))
        rounded_pixel_rect((4, 4, 35, 35), 1, (32, 35, 34, 245))
        draw.rectangle((16, 1, 23, 3), fill=(32, 35, 34, 245))
    return image


def draw_pixel_digit(draw, digit, x, y, color):
    for row, bits in enumerate(PIXEL_DIGITS[str(digit)]):
        for column, bit in enumerate(bits):
            if bit == "1":
                left = x + column * DIGIT_SCALE
                top = y + row * DIGIT_SCALE
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
    is_selected = index == 2
    slot = selected if is_selected else empty
    preview.alpha_composite(slot, (x, 10))
    number_color = (143, 134, 106, 255) if is_selected else (105, 111, 106, 255)
    draw_pixel_digit(draw, index + 1, x + 17, 10 - 3, number_color)
preview.save(ROOT / "hotbar_preview.png")

# Larger pixel heart used inside the health bar's enlarged square cap.
heart = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
heart_draw = ImageDraw.Draw(heart)
heart_rows = (
    "001100001100",
    "011110011110",
    "111111111111",
    "111111111111",
    "111111111111",
    "011111111110",
    "001111111100",
    "000111111000",
    "000011110000",
    "000001100000",
)
for row, bits in enumerate(heart_rows):
    for column, bit in enumerate(bits):
        if bit == "1":
            if row <= 1:
                color = (236, 143, 159, 255)
            elif row >= 7:
                color = (145, 48, 65, 255)
            else:
                color = (207, 76, 100, 255)
            heart_draw.point((column, row + 1), fill=color)
heart.save(ROOT / "health_heart.png")

# Static library preview of the connected square heart cap and filled bar.
bar_preview = Image.new("RGBA", (140, 20), (0, 0, 0, 0))
bar_draw = ImageDraw.Draw(bar_preview)
bar_draw.rectangle((0, 0, 19, 19), fill=(172, 86, 112, 255))
bar_draw.rectangle((1, 1, 18, 18), fill=(211, 132, 153, 255))
bar_draw.rectangle((3, 3, 16, 16), fill=(32, 35, 34, 255))
bar_draw.rectangle((19, 3, 139, 16), fill=(172, 86, 112, 255))
bar_draw.rectangle((20, 4, 138, 15), fill=(211, 132, 153, 255))
bar_draw.rectangle((22, 6, 136, 13), fill=(32, 35, 34, 255))
bar_draw.rectangle((22, 6, 94, 13), fill=(207, 76, 100, 255))
bar_preview.alpha_composite(heart, (4, 4))
bar_preview.save(ROOT / "health_bar_preview.png")

print("Built the Golem hotbar and health bar assets.")
