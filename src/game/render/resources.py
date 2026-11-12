"""Cached resource art shared by world nodes and inventory icons."""

from pathlib import Path

import pygame

from game.items.item_kinds import COPPER_ORE, GOLD_ORE, IRON_ORE, STONE, WOOD, ZINC_ORE, ItemKind

_ROOT = Path(__file__).resolve().parents[3] / "assets" / "resources"
_FILES = {
    STONE: "stone.png",
    WOOD: "wood.png",
    COPPER_ORE: "copper_ore.png",
    IRON_ORE: "iron_ore.png",
    GOLD_ORE: "gold_ore.png",
    ZINC_ORE: "zinc_ore.png",
}
_images: dict[tuple[ItemKind, int], pygame.Surface] = {}


def resource_image(kind: ItemKind, size: int = 32) -> pygame.Surface | None:
    """Return alpha art at the requested size, or None for unillustrated kinds."""
    filename = _FILES.get(kind)
    if filename is None:
        return None
    key = (kind, size)
    if key not in _images:
        if size == 32:
            image = pygame.image.load(str(_ROOT / filename))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
        else:
            original = resource_image(kind)
            assert original is not None
            image = pygame.transform.scale(original, (size, size))
        _images[key] = image
    return _images[key]
