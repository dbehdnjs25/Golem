"""Not every grassland tree is the same tree.

Three variants were drawn beside the original -- wide, tall and bent -- and
until now the game loaded only the one picture, so a grove was the same
silhouette repeated until it read as wallpaper rather than as woodland.

Which one a tree wears is decided by WHERE IT STANDS, not by a die rolled
when it is drawn. A tree that changed shape as the camera passed over it
would be worse than a tree that never changed at all, and the world is
generated from a seed precisely so that two players with the same seed see
the same place.
"""

import pygame

from game.items.item_kinds import WOOD
from game.render import trees
from game.world.biomes import RING_BIOMES

AT = pygame.Vector2(3000, 3000)


def test_the_grassland_has_more_than_one_tree():
    assert len(trees.looks_for(WOOD)) > 1


def test_every_variant_is_the_size_of_the_original():
    # They are scaled to one world size together, so a stray canvas would
    # stretch one of them and nothing else.
    sizes = {picture.get_size() for picture in trees.looks_for(WOOD)}
    assert len(sizes) == 1


def test_a_tree_keeps_its_shape():
    first = trees.tree_image(WOOD, AT)
    for _ in range(5):
        assert trees.tree_image(WOOD, AT) is first


def test_two_places_are_not_always_the_same_tree():
    seen = {
        id(trees.tree_image(WOOD, pygame.Vector2(x * 97, x * 53)))
        for x in range(60)
        if trees.tree_image(WOOD, pygame.Vector2(x * 97, x * 53)) is not None
    }
    assert len(seen) == len(trees.looks_for(WOOD))


def test_every_variant_gets_used():
    pictures = {id(p) for p in trees.looks_for(WOOD)}
    found = {
        id(trees.tree_image(WOOD, pygame.Vector2(x * 31, y * 41)))
        for x in range(12)
        for y in range(12)
    }
    assert pictures <= found


def test_a_tree_asked_for_without_a_place_is_the_first_one():
    # Inventory icons and anything else that wants "a tree" rather than THAT
    # tree. The original is what the catalogue has always shown.
    assert trees.tree_image(WOOD) is trees.looks_for(WOOD)[0]


def test_moving_a_pixel_does_not_reshape_a_tree():
    # Positions are floats and a tree jitters by fractions as it is placed.
    # Rounding to whole pixels keeps one tree one tree.
    here = trees.tree_image(WOOD, pygame.Vector2(3000.0, 3000.0))
    nudged = trees.tree_image(WOOD, pygame.Vector2(3000.4, 3000.4))
    assert nudged is here


def test_a_biome_tree_never_has_more_than_one_look():
    # Only the grassland was given variants. A ring biome keeps its single
    # drawing, and asking with a place must not break it -- nor must a biome
    # whose art is mid-redraw and briefly absent, which answers nothing at
    # all rather than crashing.
    for biome in RING_BIOMES:
        looks = trees.looks_for(biome.timber)
        assert len(looks) <= 1
        assert trees.tree_image(biome.timber, AT) is (looks[0] if looks else None)


def test_a_kind_with_no_art_is_still_nothing():
    from game.items.item_kinds import STONE

    assert trees.looks_for(STONE) == ()
    assert trees.tree_image(STONE, AT) is None


def test_the_shadow_rule_reads_the_tree_that_is_there():
    # Whether a variant paints its own shadow is a question about that
    # picture, not about the kind.
    assert isinstance(trees.has_own_shadow(WOOD), bool)
