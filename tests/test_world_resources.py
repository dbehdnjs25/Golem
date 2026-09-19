import random

from game.items.item_kinds import COPPER_ORE, GOLD_ORE, IRON_ORE, STONE, ZINC_ORE, ItemKind
from game.world.resources import ore_at


def _draw(fraction: float, n: int = 3000, seed: int = 1) -> dict[ItemKind, int]:
    rng = random.Random(seed)
    counts: dict[ItemKind, int] = {}
    for _ in range(n):
        kind = ore_at(fraction, rng)
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def test_it_always_returns_a_real_ore():
    rng = random.Random(0)
    allowed = {STONE, COPPER_ORE, IRON_ORE, GOLD_ORE, ZINC_ORE}
    for step in range(21):
        assert ore_at(step / 20, rng) in allowed


def test_the_inner_grassland_is_mostly_stone_and_copper():
    counts = _draw(0.1)
    assert set(counts) <= {STONE, COPPER_ORE}
    assert counts[STONE] > counts[COPPER_ORE]


def test_gold_does_not_appear_in_the_grassland():
    # 0.5 is exactly the grassland's rim, which counts as the ring -- the bands
    # are half-open, so probe just inside it.
    for fraction in (0.1, 0.3, 0.49):
        assert GOLD_ORE not in _draw(fraction)


def test_zinc_appears_only_in_the_outer_grassland():
    # Zinc is smelting-only and deliberately awkward: brass costs the trip out
    # to the grassland's rim, not a deeper mine.
    assert ZINC_ORE not in _draw(0.1)  # the inner grassland
    assert ZINC_ORE in _draw(0.4)  # its outer half
    assert ZINC_ORE not in _draw(0.9)  # out in the ring


def test_the_outer_ring_favours_the_high_tiers():
    counts = _draw(0.95)
    assert counts[GOLD_ORE] > counts[STONE]
    assert counts[IRON_ORE] > counts[STONE]


def test_better_ore_gets_likelier_further_out():
    near = _draw(0.3)
    far = _draw(0.95)
    assert far.get(IRON_ORE, 0) > near.get(IRON_ORE, 0)
    assert far.get(STONE, 0) < near.get(STONE, 0)


def test_it_is_reproducible_from_a_seed():
    rng_a = random.Random(4)
    rng_b = random.Random(4)
    assert [ore_at(0.8, rng_a) for _ in range(20)] == [ore_at(0.8, rng_b) for _ in range(20)]


def test_a_share_of_nodes_are_trees_at_every_distance():
    # Trees are not on the ore table. Folding them in would make deep ground
    # grow fewer trees, which is backwards -- the spec has them thicken with
    # distance like everything else.
    from game.items.item_kinds import WOOD
    from game.world.resources import node_at

    for fraction in (0.1, 0.5, 0.95):
        rng = random.Random(2)
        drawn = [node_at(fraction, rng) for _ in range(2000)]
        trees = sum(1 for k in drawn if k is WOOD)
        assert 0 < trees < len(drawn)  # some, but never all


def test_the_tree_share_does_not_fall_away_from_the_core():
    from game.items.item_kinds import WOOD
    from game.world.resources import node_at

    def share(fraction: float) -> float:
        rng = random.Random(5)
        drawn = [node_at(fraction, rng) for _ in range(4000)]
        return sum(1 for k in drawn if k is WOOD) / len(drawn)

    assert share(0.95) >= share(0.1) - 0.02


def test_node_at_still_yields_ore_the_ore_table_knows():
    from game.world.resources import node_at

    rng = random.Random(0)
    allowed = {STONE, COPPER_ORE, IRON_ORE, GOLD_ORE, ZINC_ORE}
    from game.items.item_kinds import WOOD

    for step in range(21):
        assert node_at(step / 20, rng) in allowed | {WOOD}
