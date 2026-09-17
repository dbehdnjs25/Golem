from game import config


def test_world_is_larger_than_screen():
    assert config.WORLD_WIDTH > config.SCREEN_WIDTH
    assert config.WORLD_HEIGHT > config.SCREEN_HEIGHT


def test_slot_counts_are_sane():
    assert config.INVENTORY_SLOTS > 0
    assert config.BACKPACK_SLOTS > 0
    assert config.CORE_STORE_SLOTS > config.INVENTORY_SLOTS
    assert config.STACK_MAX_DEFAULT > 0


def test_sync_radius_exceeds_core_radius():
    assert config.CORE_SYNC_RADIUS > config.CORE_RADIUS


def test_title_is_the_new_concept():
    assert config.TITLE == "Golem"


def test_combat_constants_are_sane():
    assert config.PLAYER_MAX_HP > 0
    assert config.WEAPON_FIRE_RATE > 0
    assert config.PROJECTILE_SPEED > 0
    assert config.DODGE_IFRAMES >= config.DODGE_DURATION
    assert len(config.GOLEM_COLOR) == 3


def test_the_trojan_constant_is_gone():
    assert not hasattr(config, "TROJAN_CHANCE")


def test_the_map_is_sized_for_a_three_minute_walk_to_the_biomes():
    # The grassland's rim is exactly three minutes from the core at base speed.
    # Everything else about the map's size follows from that one number.
    assert config.GRASSLAND_RADIUS / config.PLAYER_SPEED == 180.0


def test_the_grassland_is_a_third_of_the_map():
    assert 0.30 < (config.GRASSLAND_RADIUS / config.MAP_RADIUS) ** 2 < 0.36


def test_the_temple_band_is_a_fraction_of_the_ring_not_an_absolute_radius():
    # Absolute radii silently land in the wrong place when the map is rescaled.
    assert not hasattr(config, "TEMPLE_BAND_INNER")
    assert not hasattr(config, "TEMPLE_BAND_OUTER")
    assert 0.0 < config.TEMPLE_BAND_INNER_FRAC < config.TEMPLE_BAND_OUTER_FRAC < 1.0
