"""Standing tree sprites keyed by the timber already assigned to each biome."""

from pathlib import Path

import pygame

from game.items.item_kinds import WOOD, ItemKind
from game.world.biomes import BIOMES

_ASSETS = Path(__file__).resolve().parents[3] / "assets"
_FILES = {biome.timber: _ASSETS / "trees" / f"{biome.key}.png" for biome in BIOMES}
_FILES[WOOD] = _ASSETS / "grassland" / "objects" / "tree_base.png"
_images: dict[ItemKind, pygame.Surface] = {}


def tree_image(kind: ItemKind) -> pygame.Surface | None:
    """Return the full standing tree; its bottom center is the ground anchor."""
    path = _FILES.get(kind)
    if path is None:
        return None
    if kind not in _images:
        image = pygame.image.load(str(path))
        if pygame.display.get_surface() is not None:
            image = image.convert_alpha()
        _images[kind] = image
    return _images[kind]
