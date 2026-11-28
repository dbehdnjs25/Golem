"""Cached resource art shared by world nodes and inventory icons."""

from pathlib import Path

import pygame

from game.items.item_kinds import (
    CATALOGUE,
    COPPER_ORE,
    GOLD_ORE,
    IRON_ORE,
    STONE,
    WOOD,
    ZINC_ORE,
    ItemKind,
)
from game.render import art
from game.render.trees import tree_image

_ROOT = Path(__file__).resolve().parents[3] / "assets" / "resources"
_ITEMS = _ROOT / "items"
_FILES = {
    STONE: "stone.png",
    WOOD: "wood.png",
    COPPER_ORE: "copper_ore.png",
    IRON_ORE: "iron_ore.png",
    GOLD_ORE: "gold_ore.png",
    ZINC_ORE: "zinc_ore.png",
}
_ICON_FILES = {
    kind: _ROOT / "wood.png" if kind.key.endswith("_wood") else _ITEMS / f"{kind.key}.png"
    for kind in CATALOGUE
}
_images: dict[tuple[ItemKind, int], pygame.Surface] = {}
_generation = art.generation  # see render/art: a saved picture is read again


def resource_image(kind: ItemKind, size: int = 32) -> pygame.Surface | None:
    """Return alpha art at the requested size, or None for unillustrated kinds."""
    global _generation
    if _generation != art.generation:
        _images.clear()
        _generation = art.generation
    filename = _FILES.get(kind)
    key = (kind, size)
    if key not in _images:
        # Hand-finished resource art takes precedence over catalogue placeholders.
        icon_path = _ROOT / filename if filename is not None else _ICON_FILES.get(kind)
        if icon_path is not None:
            art.note(icon_path)
        if icon_path is not None and icon_path.is_file():
            image = pygame.image.load(str(icon_path))
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
            if image.get_size() != (size, size):
                image = pygame.transform.scale(image, (size, size))
        else:
            tree = tree_image(kind)
            if tree is None:
                return None
            scale = size / max(tree.get_size())
            image = pygame.transform.scale(tree, (max(1, round(tree.get_width() * scale)), size))
        _images[key] = image
    return _images[key]


def world_resource_image(kind: ItemKind) -> pygame.Surface | None:
    """Detailed boulders use 48px world art; small litter keeps its 32px footprint."""
    return resource_image(kind, 48 if kind in _FILES else 32)
