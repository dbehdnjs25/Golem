import random

import pygame

from game import config
from game.entities.core import Core
from game.entities.fragment import Fragment
from game.items.item_kinds import STONE
from game.systems.spawner import Spawner, TreeSpawner, is_tree
from game.world.map import WorldMap

WORLD = WorldMap()
CORE = Core(pos=WORLD.center)
PLAYER = CORE.pos + pygame.Vector2(1_000, 0)


def _filled(player=PLAYER, seed=1):
    trees: list[Fragment] = []
    TreeSpawner().fill(trees, CORE, random.Random(seed), WORLD, player)
    return trees


def _near(trees, player=PLAYER):
    return [t for t in trees if t.pos.distance_to(player) <= config.SPAWN_RADIUS]


def test_the_ground_starts_forested():
    trees = _filled()
    # Not to the last tree -- a clump that will not fit is skipped -- but close.
    assert len(_near(trees)) >= config.TREE_SPAWN_MAX * 0.9


def test_every_tree_is_its_own_biomes_timber():
    for tree in _filled():
        assert tree.grove
        assert tree.kind is WORLD.biome_at(tree.pos).timber


def test_trees_keep_their_distance_from_each_other():
    trees = _filled()
    for i, a in enumerate(trees):
        for b in trees[i + 1 :]:
            assert a.pos.distance_to(b.pos) >= config.TREE_GAP - 1e-6


def test_trees_grow_in_clumps():
    # Most trees have another within a couple of gaps: woods, not a sprinkle.
    trees = _filled()
    close = sum(
        1
        for a in trees
        if any(b is not a and a.pos.distance_to(b.pos) < config.TREE_GAP * 2.5 for b in trees)
    )
    assert close >= len(trees) * 0.7


def test_no_tree_grows_on_the_core():
    for tree in _filled(player=CORE.pos):
        assert tree.pos.distance_to(CORE.pos) >= CORE.sync_radius + config.TREE_GAP


def test_new_trees_grow_out_of_sight():
    spawner = TreeSpawner()
    trees: list[Fragment] = []
    rng = random.Random(3)
    for _ in range(200):
        spawner.update(config.TREE_SPAWN_INTERVAL, trees, CORE, rng, WORLD, PLAYER)
    assert trees
    for tree in trees:
        assert tree.pos.distance_to(PLAYER) >= config.TREE_HIDDEN_RADIUS - config.TREE_GAP * 3


def test_walking_away_forgets_the_old_trees_and_grows_new_ones():
    trees = _filled()
    spawner = TreeSpawner()
    rng = random.Random(4)
    far = PLAYER + pygame.Vector2(0, config.TREE_FORGET_RADIUS * 2)
    for _ in range(400):
        spawner.update(config.TREE_SPAWN_INTERVAL, trees, CORE, rng, WORLD, far)
    assert all(t.pos.distance_to(far) <= config.TREE_FORGET_RADIUS for t in trees)
    assert len(_near(trees, far)) >= config.TREE_SPAWN_MAX * 0.5


def test_the_cap_counts_only_trees_nearby():
    spawner = TreeSpawner()
    trees = _filled()
    count = len(_near(trees))
    for _ in range(50):
        spawner.update(config.TREE_SPAWN_INTERVAL, trees, CORE, random.Random(5), WORLD, PLAYER)
    assert len(_near(trees)) <= max(count, config.TREE_SPAWN_MAX) + 5


def test_the_tree_spawner_leaves_everything_else_alone():
    rock = Fragment(pos=PLAYER + pygame.Vector2(5_000, 0), kind=STONE)
    trees = [rock]
    spawner = TreeSpawner()
    spawner.update(config.TREE_SPAWN_INTERVAL, trees, CORE, random.Random(6), WORLD, PLAYER)
    assert rock in trees  # far away, but not a grove tree: never forgotten


def test_grove_trees_do_not_use_up_the_node_spawners_room():
    nodes = _filled()
    spawned = Spawner().update(config.SPAWN_INTERVAL, nodes, CORE, random.Random(7), WORLD, PLAYER)
    assert spawned is not None


def test_is_tree_knows_every_biomes_timber():
    from game.world.biomes import BIOMES

    assert all(is_tree(biome.timber) for biome in BIOMES)
    assert not is_tree(STONE)


def test_a_missing_tree_picture_is_drawn_plain_rather_than_crashing(monkeypatch, tmp_path):
    from game.items.item_kinds import WOOD
    from game.render import trees

    monkeypatch.setitem(trees._FILES, WOOD, tmp_path / "gone.png")
    monkeypatch.setattr(trees, "_images", {})
    monkeypatch.setattr(trees, "_missing", set())
    assert trees.tree_image(WOOD) is None


def _tree_png(path, shadow: bool):
    art = pygame.Surface((48, 64), pygame.SRCALPHA)
    pygame.draw.rect(art, (90, 60, 30, 255), (20, 30, 8, 30))  # trunk
    if shadow:
        pygame.draw.ellipse(art, (20, 30, 20, 90), (8, 56, 32, 8))  # soft, under the trunk
    pygame.image.save(art, str(path))


def test_a_tree_drawn_with_its_own_shadow_gets_no_second_one(monkeypatch, tmp_path):
    from game.items.item_kinds import WOOD
    from game.render import trees

    monkeypatch.setattr(trees, "_images", {})
    monkeypatch.setattr(trees, "_missing", set())
    monkeypatch.setattr(trees, "_own_shadow", {})
    _tree_png(tmp_path / "shaded.png", shadow=True)
    monkeypatch.setitem(trees._FILES, WOOD, tmp_path / "shaded.png")
    assert trees.has_own_shadow(WOOD)


def test_a_tree_drawn_without_one_still_gets_the_codes_shadow(monkeypatch, tmp_path):
    from game.items.item_kinds import WOOD
    from game.render import trees

    monkeypatch.setattr(trees, "_images", {})
    monkeypatch.setattr(trees, "_missing", set())
    monkeypatch.setattr(trees, "_own_shadow", {})
    _tree_png(tmp_path / "bare.png", shadow=False)
    monkeypatch.setitem(trees._FILES, WOOD, tmp_path / "bare.png")
    assert not trees.has_own_shadow(WOOD)


def test_the_grassland_tree_brings_its_own_shadow_and_the_others_do_not():
    from game.items.item_kinds import WOOD
    from game.render import trees
    from game.world.biomes import RING_BIOMES

    assert trees.has_own_shadow(WOOD)
    for biome in RING_BIOMES:
        if trees._FILES[biome.timber].is_file():
            assert not trees.has_own_shadow(biome.timber), biome.key
