from game import config


def test_world_is_larger_than_screen():
    assert config.WORLD_WIDTH > config.SCREEN_WIDTH
    assert config.WORLD_HEIGHT > config.SCREEN_HEIGHT


def test_capacities_are_positive_multiples_of_fragment_mb():
    assert config.FRAGMENT_MB > 0
    assert config.BACKPACK_CAP_MB >= config.FRAGMENT_MB
    assert config.DOCUMENTS_CAP_MB > config.BACKPACK_CAP_MB


def test_sync_radius_exceeds_core_radius():
    assert config.CORE_SYNC_RADIUS > config.CORE_RADIUS


def test_hotbar_start_within_max():
    assert 0 < config.HOTBAR_START_UNLOCKED <= config.HOTBAR_MAX_SLOTS


def test_combat_constants_are_sane():
    from game import config

    assert config.PLAYER_MAX_HP > 0
    assert config.WEAPON_FIRE_RATE > 0
    assert config.PROJECTILE_SPEED > 0
    assert 0.0 <= config.TROJAN_CHANCE <= 1.0
    assert config.DODGE_IFRAMES >= config.DODGE_DURATION
    assert len(config.VIRUS_COLOR) == 3
