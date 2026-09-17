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
