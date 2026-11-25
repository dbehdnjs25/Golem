"""The boss on the field: called, fought, killed, and shown.

Everything before this stood a boss up in a table. This is the part where one
is actually in the room, takes a shot, and leaves something behind when it
stops moving.
"""

import pygame

from game import config
from game.entities.boss import TRICKS
from game.items.item_kinds import CORE_SIGIL
from game.scenes.play import PlayScene
from game.world import biomes


def _ready(index: int = 0) -> tuple[PlayScene, object]:
    """A scene standing over the sleeping thing in a temple's last room.

    Walked straight to it rather than through the building: what thirteen
    rooms and a locked door do is tests/test_dungeon_in_play's business, and
    this is about what happens once the boss opens its eyes.
    """
    scene = PlayScene()
    scene.core.ignite()
    temple = scene.temples[index]
    place = temple.interior()
    place.at = place.boss_room.index
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 0.6, 0))
    scene.update(config.FIXED_DT)  # walking in puts them inside
    place.at = place.boss_room.index  # and straight to the last room
    scene.player.pos.update(temple.pos)
    return scene, temple


def _call(scene) -> None:
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    scene.update(config.FIXED_DT)


# --- the altar answers ----------------------------------------------------


def test_the_altar_stands_the_boss_of_that_biome_up():
    for index, biome in enumerate(biomes.RING_BIOMES):
        scene, temple = _ready(index)
        _call(scene)
        assert scene.boss is not None
        assert scene.boss.kind.biome is biome


def test_calling_seals_the_room():
    scene, temple = _ready()
    _call(scene)
    assert scene.arena.sealed


def test_nothing_wakes_in_a_room_that_is_not_the_last_one():
    # The start room is the one the player lands in, and there is nothing
    # asleep in it.
    scene = PlayScene()
    scene.core.ignite()
    temple = scene.temples[0]
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 0.6, 0))
    scene.update(config.FIXED_DT)
    scene.player.pos.update(temple.pos)
    _call(scene)
    assert scene.boss is None


def test_one_boss_at_a_time():
    scene, temple = _ready()
    _call(scene)
    first = scene.boss
    _call(scene)
    assert scene.boss is first


# --- it fights ------------------------------------------------------------


def test_it_walks_at_the_player():
    scene, temple = _ready()
    _call(scene)
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 0.8, 0))
    before = scene.boss.pos.distance_to(scene.player.pos)
    for _ in range(30):
        scene.update(config.FIXED_DT)
    assert scene.boss.pos.distance_to(scene.player.pos) < before


def test_standing_in_it_hurts():
    scene, temple = _ready()
    _call(scene)
    scene.player.pos.update(scene.boss.pos)
    full = scene.player.hp
    for _ in range(60):
        scene.player.pos.update(scene.boss.pos)
        scene.update(config.FIXED_DT)
    assert scene.player.hp < full


def test_a_shot_hurts_it():
    scene, temple = _ready()
    _call(scene)
    full = scene.boss.hp
    scene.projectiles.append(
        _shot_at(scene.boss.pos),
    )
    scene.update(config.FIXED_DT)
    assert scene.boss.hp < full


def _shot_at(where):
    from game.entities.projectile import Projectile

    return Projectile(pos=pygame.Vector2(where), vel=pygame.Vector2(0, 0), damage=50.0)


def test_the_sealed_room_holds_the_player_in():
    scene, temple = _ready()
    _call(scene)
    scene.player.pos.update(temple.pos + pygame.Vector2(temple.radius * 3, 0))
    scene.update(config.FIXED_DT)
    assert temple.contains(scene.player.pos)


# --- and dies -------------------------------------------------------------


def _kill(scene) -> None:
    while scene.boss is not None:
        scene.projectiles.append(_shot_at(scene.boss.pos))
        scene.update(config.FIXED_DT)


def test_killing_it_teaches_its_supreme_glyph():
    scene, temple = _ready()
    _call(scene)
    kind = scene.boss.kind
    _kill(scene)
    from game.systems import spoils

    assert scene.grimoire.knows(spoils.glyph_of(kind))
    assert spoils.glyph_of(kind).name == TRICKS[kind.tricks[2]].name


def test_killing_it_leaves_a_sigil_to_carry_home():
    scene, temple = _ready()
    _call(scene)
    _kill(scene)
    # On the floor or in hand -- what matters is that it exists to be taken.
    on_floor = any(f.kind is CORE_SIGIL for f in scene.fragments)
    assert on_floor or scene._carried(CORE_SIGIL)


def test_killing_it_opens_the_door_again():
    scene, temple = _ready()
    _call(scene)
    _kill(scene)
    assert not scene.arena.sealed


def test_a_dead_boss_cannot_be_called_back():
    scene, temple = _ready()
    _call(scene)
    _kill(scene)
    assert temple.boss_killed
    scene.player.pos.update(temple.pos)
    _call(scene)
    assert scene.boss is None


def test_the_kill_counts_towards_the_raid_calendar():
    scene, temple = _ready()
    before = scene.core.bosses_killed
    _call(scene)
    _kill(scene)
    assert scene.core.bosses_killed == before + 1


def test_the_cap_does_not_move_until_the_sigil_comes_home():
    scene, temple = _ready()
    _call(scene)
    before = scene.core.level_cap
    _kill(scene)
    assert scene.core.level_cap == before


def test_it_says_so():
    scene, temple = _ready()
    _call(scene)
    _kill(scene)
    assert scene.note


# --- what shows on screen -------------------------------------------------


def _drawn(scene) -> pygame.Surface:
    surface = pygame.Surface(config.SCREEN_SIZE)
    scene.camera.center_on(scene.player.pos)
    scene.draw(surface)
    return surface


def _has(surface, rect, colour) -> bool:
    for x in range(rect.left, rect.right, 2):
        for y in range(rect.top, rect.bottom, 2):
            if surface.get_at((x, y))[:3] == colour:
                return True
    return False


def test_a_called_boss_has_a_bar_across_the_top():
    scene, temple = _ready()
    before = _drawn(scene)
    band = pygame.Rect(0, 0, config.SCREEN_WIDTH, config.BOSS_BAR_Y + config.BOSS_BAR_H + 4)
    assert not _has(before, band, config.BOSS_BAR_COLOR)
    _call(scene)
    assert _has(_drawn(scene), band, config.BOSS_BAR_COLOR)


def test_the_bar_says_when_the_second_phase_opens():
    scene, temple = _ready()
    _call(scene)
    band = pygame.Rect(0, 0, config.SCREEN_WIDTH, config.BOSS_BAR_Y + config.BOSS_BAR_H + 4)
    assert not _has(_drawn(scene), band, config.BOSS_PHASE2_COLOR)
    scene.boss.damage(scene.boss.kind.hp * 0.6)
    assert _has(_drawn(scene), band, config.BOSS_PHASE2_COLOR)


def test_the_bar_goes_away_with_the_boss():
    scene, temple = _ready()
    _call(scene)
    _kill(scene)
    band = pygame.Rect(0, 0, config.SCREEN_WIDTH, config.BOSS_BAR_Y + config.BOSS_BAR_H + 4)
    assert not _has(_drawn(scene), band, config.BOSS_BAR_COLOR)


def test_burnt_ground_is_drawn_where_a_trick_left_it():
    from game.systems import gimmicks

    scene = PlayScene()
    scene.camera.center_on(scene.player.pos)
    gimmicks.scorch(pygame.Vector2(scene.player.pos), scene.patches)
    surface = _drawn(scene)
    at = scene.camera.world_to_view(scene.patches[0].pos)
    # The rim, not the middle: the fill is translucent on purpose and the
    # player is standing on the centre of it.
    radius = scene.patches[0].radius
    rim = pygame.Rect(int(at.x - radius) - 4, int(at.y) - 4, 10, 10)
    assert _has(surface, rim, config.BURNING_COLOR)


def test_a_mark_is_drawn_too():
    from game.systems import gimmicks

    scene = PlayScene()
    scene.camera.center_on(scene.player.pos)
    # Off to one side, so the player's own circle is not drawn over it.
    gimmicks.mark(scene.player.pos + pygame.Vector2(200, 0), scene.marks, scene.mark_timers)
    surface = _drawn(scene)
    at = scene.camera.world_to_view(scene.marks[0])
    near = pygame.Rect(int(at.x) - 24, int(at.y) - 24, 48, 48)
    assert _has(surface, near, config.MARK_COLOR)


def test_a_winding_charge_shows_the_lane_it_will_run():
    # A path, not a place: the one blow whose telegraph is a shape you walk
    # out of sideways rather than a circle you leave.
    scene, temple = _ready()
    _call(scene)
    scene.player.pos.update(temple.pos + pygame.Vector2(200, 0))
    for _ in range(int((config.BOSS_MOVE_GAP + 0.1) / config.FIXED_DT)):
        scene.brawl.update(
            config.FIXED_DT,
            scene.boss,
            scene.player,
            temple.pos,
            temple.radius,
            forced="charge" if scene.brawl.move is None else None,
        )
    assert scene.brawl.move == "charge"
    surface = _drawn(scene)
    # Somewhere along the lane, between the boss and where it is headed.
    middle = scene.camera.world_to_view(scene.boss.pos.lerp(scene.brawl.aim, 0.5))
    near = pygame.Rect(int(middle.x) - 60, int(middle.y) - 60, 120, 120)
    assert _has(surface, near, config.WARNING_COLOR)


def test_a_boss_mid_blow_does_not_drift_forward():
    scene, temple = _ready()
    _call(scene)
    scene.player.pos.update(temple.pos + pygame.Vector2(300, 0))
    for _ in range(int((config.BOSS_MOVE_GAP + 0.1) / config.FIXED_DT)):
        scene.update(config.FIXED_DT)
    if scene.brawl.move is None:  # it was between blows; nothing to check
        return
    stood = pygame.Vector2(scene.boss.pos)
    for _ in range(6):
        scene.update(config.FIXED_DT)
        if scene.brawl.phase != "wind":
            break
    else:
        assert scene.boss.pos == stood
