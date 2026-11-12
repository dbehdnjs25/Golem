"""Standing tree sprites keyed by the timber already assigned to each biome."""

from pathlib import Path

import pygame

from game.items.item_kinds import WOOD, ItemKind
from game.world.biomes import BIOMES

_ASSETS = Path(__file__).resolve().parents[3] / "assets"
_FILES = {biome.timber: _ASSETS / "trees" / f"{biome.key}.png" for biome in BIOMES}
_FILES[WOOD] = _ASSETS / "grassland" / "objects" / "tree_base.png"
_images: dict[ItemKind, pygame.Surface] = {}
WORLD_TREE_SIZE = (96, 128)
_shadow: pygame.Surface | None = None


def tree_shadow() -> pygame.Surface:
    """A flat ground shadow anchors the larger tree without blurring its sprite."""
    global _shadow
    if _shadow is None:
        _shadow = pygame.Surface((56, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(_shadow, (24, 32, 20, 64), _shadow.get_rect())
    return _shadow


def tree_image(kind: ItemKind) -> pygame.Surface | None:
    """Return a 96x128 standing tree, anchored at its bottom center in the world."""
    path = _FILES.get(kind)
    if path is None:
        return None
    if kind not in _images:
        image = pygame.image.load(str(path))
        if image.get_size() != WORLD_TREE_SIZE:
            # Preserve the user's 48x64 grassland source and scale only its display.
            image = pygame.transform.scale(image, WORLD_TREE_SIZE)
        if pygame.display.get_surface() is not None:
            image = image.convert_alpha()
        _images[kind] = image
    return _images[kind]
