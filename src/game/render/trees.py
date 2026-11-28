"""Standing tree sprites keyed by the timber already assigned to each biome."""

from pathlib import Path

import pygame

from game.items.item_kinds import WOOD, ItemKind
from game.render import art
from game.world.biomes import BIOMES

_ASSETS = Path(__file__).resolve().parents[3] / "assets"
_FILES = {biome.timber: _ASSETS / "trees" / f"{biome.key}.png" for biome in BIOMES}
_FILES[WOOD] = _ASSETS / "grassland" / "objects" / "grassland_tree.png"
_images: dict[ItemKind, pygame.Surface] = {}
_missing: set[ItemKind] = set()  # art not on disk; drawn plain until it appears
_own_shadow: dict[ItemKind, bool] = {}
_generation = art.generation  # the caches above hold pictures from this one
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
    _keep_current()
    path = _FILES.get(kind)
    if path is None or kind in _missing:
        return None
    if kind not in _images:
        art.note(path)
        if not path.is_file():
            # Art being redrawn can be briefly absent. A plain node is better
            # than the whole game stopping when that biome comes into view.
            _missing.add(kind)
            return None
        image = pygame.image.load(str(path))
        if image.get_size() != WORLD_TREE_SIZE:
            # Preserve the user's 48x64 grassland source and scale only its display.
            image = pygame.transform.scale(image, WORLD_TREE_SIZE)
        if pygame.display.get_surface() is not None:
            image = image.convert_alpha()
        _images[kind] = image
    return _images[kind]


def _keep_current() -> None:
    """Forget every tree if the art on disk has changed since it was read."""
    global _generation
    if _generation != art.generation:
        _images.clear()
        _missing.clear()
        _own_shadow.clear()
        _generation = art.generation


def has_own_shadow(kind: ItemKind) -> bool:
    """Whether the tree's art already has a shadow painted under it.

    Read off the picture rather than listed by hand: soft, half-see-through
    pixels along the bottom are a painted shadow (the outline and the trunk
    are solid). Such a tree gets no second shadow from the code -- the
    grassland tree drew two, one painted and one laid under it.
    """
    if kind not in _own_shadow:
        picture = tree_image(kind)
        if picture is None:
            return False
        width, height = picture.get_size()
        soft = sum(
            1
            for y in range(height * 7 // 8, height)
            for x in range(width)
            if 0 < picture.get_at((x, y)).a < 255
        )
        _own_shadow[kind] = soft >= width // 4
    return _own_shadow[kind]
