"""Standing tree sprites keyed by the timber already assigned to each biome.

Most timbers have one drawing. The grassland has four -- the original and
three variants beside it -- and which one a tree wears is decided by WHERE IT
STANDS rather than by a die rolled when it is drawn. A tree that changed shape
as the camera crossed it would be worse than a tree that never changed, and
the world is generated from a seed exactly so that the same seed is the same
place twice.
"""

from pathlib import Path

import pygame

from game.items.item_kinds import WOOD, ItemKind
from game.render import art
from game.world.biomes import BIOMES

_ASSETS = Path(__file__).resolve().parents[3] / "assets"
_FILES: dict[ItemKind, tuple[Path, ...]] = {
    biome.timber: (_ASSETS / "trees" / f"{biome.key}.png",) for biome in BIOMES
}
# The original first: it is what the catalogue has always shown, and it is
# what anything asking for "a tree" rather than THAT tree gets.
_GRASS = _ASSETS / "grassland" / "objects"
_FILES[WOOD] = (
    _GRASS / "grassland_tree.png",
    *(_GRASS / "variants" / f"grassland_tree_{look}.png" for look in ("wide", "tall", "bent")),
)
_images: dict[ItemKind, tuple[pygame.Surface, ...]] = {}
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


def looks_for(kind: ItemKind) -> tuple[pygame.Surface, ...]:
    """Every drawing this timber has, original first. Empty if it has none."""
    _keep_current()
    paths = _FILES.get(kind)
    if paths is None or kind in _missing:
        return ()
    if kind not in _images:
        pictures: list[pygame.Surface] = []
        for path in paths:
            art.note(path)
            if not path.is_file():
                continue
            image = pygame.image.load(str(path))
            if image.get_size() != WORLD_TREE_SIZE:
                # Preserve the 48x64 sources and scale only their display.
                image = pygame.transform.scale(image, WORLD_TREE_SIZE)
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
            pictures.append(image)
        if not pictures:
            # Art being redrawn can be briefly absent. A plain node is better
            # than the whole game stopping when that biome comes into view.
            _missing.add(kind)
            return ()
        _images[kind] = tuple(pictures)
    return _images[kind]


def tree_image(kind: ItemKind, at: pygame.Vector2 | None = None) -> pygame.Surface | None:
    """A 96x128 standing tree, anchored at its bottom center in the world.

    Given a place, the place picks which of this timber's drawings stands
    there -- the same one every time, for as long as the tree is there.
    Without one, the original: inventory icons and anything else that wants
    "a tree" rather than that particular tree.
    """
    looks = looks_for(kind)
    if not looks:
        return None
    if at is None or len(looks) == 1:
        return looks[0]
    return looks[_scramble(round(at.x), round(at.y)) % len(looks)]


def _scramble(x: int, y: int) -> int:
    """A stable number from a place.

    Its own arithmetic rather than ``hash``, which is salted per process: two
    runs of the same world would otherwise grow different woods. Whole pixels,
    because a tree is placed with a fraction of jitter on it and half a pixel
    must not reshape it.
    """
    n = (x * 0x1F1F_1F1F) ^ (y * 0x27D4_EB2D)
    n = (n ^ (n >> 15)) * 0x2545_F491
    return (n ^ (n >> 13)) & 0x7FFF_FFFF


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
