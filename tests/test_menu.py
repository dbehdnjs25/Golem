"""The main menu: Play, a save slot, a new game or the old one carried on."""

import pygame

from game import config, saves
from game.core.scene import SceneManager
from game.scenes.menu import ERASE, SLOTS, TITLE, MenuScene
from game.scenes.play import PlayScene


def _key(scene, key: int) -> None:
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


def _menu(tmp_path, seeds=(11, 22, 33)) -> tuple[SceneManager, MenuScene]:
    queue = list(seeds)
    menu = MenuScene(save_folder=tmp_path, new_seed=lambda: queue.pop(0))
    manager = SceneManager()
    manager.push(menu)
    menu.update(config.FIXED_DT)
    return manager, menu


def _open_slot(manager: SceneManager, menu: MenuScene, slot: int) -> PlayScene:
    _key(menu, pygame.K_RETURN)  # 플레이
    assert menu.screen == SLOTS
    for _ in range(slot):
        _key(menu, pygame.K_DOWN)
    _key(menu, pygame.K_RETURN)
    game = manager.current
    assert isinstance(game, PlayScene)
    return game


def test_it_opens_on_play_and_quit():
    menu = MenuScene()
    assert menu.screen == TITLE
    assert [label for _, label in menu.rows()] == ["플레이", "종료"]


def test_an_empty_slot_starts_a_new_game_in_it(tmp_path):
    manager, menu = _menu(tmp_path)
    game = _open_slot(manager, menu, 1)
    assert game.save_slot == 1
    assert game.seed == 11
    assert saves.info(1, tmp_path) is None  # nothing on disk until it is left


def test_leaving_the_game_saves_it_and_comes_back_to_the_menu(tmp_path):
    manager, menu = _menu(tmp_path)
    game = _open_slot(manager, menu, 0)
    game.player.pos.x += 123
    manager.pop()  # what the Esc menu's last row and the close button do
    assert manager.current is menu
    assert saves.info(0, tmp_path) is not None
    menu.update(config.FIXED_DT)
    assert menu.infos[0] is not None


def test_a_full_slot_carries_on_where_it_was_left(tmp_path):
    manager, menu = _menu(tmp_path)
    game = _open_slot(manager, menu, 2)
    game.player.pos.update(4321, 1234)
    manager.pop()
    menu.update(config.FIXED_DT)
    _key(menu, pygame.K_ESCAPE)  # back to the title, then in again
    again = _open_slot(manager, menu, 2)
    assert again is not game
    assert again.player.pos == pygame.Vector2(4321, 1234)
    assert again.seed == 11  # the same world, not a fresh roll
    assert again.save_slot == 2


def test_two_new_games_are_two_different_worlds(tmp_path):
    manager, menu = _menu(tmp_path)
    first = _open_slot(manager, menu, 0)
    manager.pop()
    menu.update(config.FIXED_DT)
    _key(menu, pygame.K_ESCAPE)
    second = _open_slot(manager, menu, 1)
    assert (first.seed, second.seed) == (11, 22)


def test_the_esc_menu_quits_through_a_save(tmp_path):
    manager, menu = _menu(tmp_path)
    game = _open_slot(manager, menu, 0)
    _key(game, pygame.K_ESCAPE)
    for _ in range(2):
        _key(game, pygame.K_DOWN)  # the last row: save and leave
    _key(game, pygame.K_RETURN)
    assert manager.current is menu
    assert saves.info(0, tmp_path) is not None


def test_delete_asks_first_and_then_erases(tmp_path):
    manager, menu = _menu(tmp_path)
    _open_slot(manager, menu, 0)
    manager.pop()
    menu.update(config.FIXED_DT)
    assert menu.screen == SLOTS and menu.cursor == 0
    _key(menu, pygame.K_DELETE)
    assert menu.screen == ERASE
    _key(menu, pygame.K_RETURN)  # the cursor starts on "cancel"
    assert saves.info(0, tmp_path) is not None
    _key(menu, pygame.K_DELETE)
    _key(menu, pygame.K_UP)
    _key(menu, pygame.K_RETURN)
    assert saves.info(0, tmp_path) is None
    assert menu.screen == SLOTS


def test_a_save_that_will_not_load_is_reported_not_raised(tmp_path):
    manager, menu = _menu(tmp_path)
    _open_slot(manager, menu, 0)
    manager.pop()
    (tmp_path / "slot1.save").write_bytes(b"broken")
    menu.update(config.FIXED_DT)
    _key(menu, pygame.K_RETURN)
    assert manager.current is menu
    assert "불러올 수 없어요" in menu.message


def test_rows_can_be_clicked(tmp_path):
    manager, menu = _menu(tmp_path)
    play = menu._rows(config.SCREEN_SIZE)[0]
    menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=play.center))
    assert menu.screen == SLOTS


def test_quit_empties_the_stack():
    manager = SceneManager()
    menu = MenuScene()
    manager.push(menu)
    _key(menu, pygame.K_DOWN)
    _key(menu, pygame.K_RETURN)
    assert manager.is_empty


def test_the_menu_draws(tmp_path):
    _, menu = _menu(tmp_path)
    surface = pygame.Surface(config.SCREEN_SIZE)
    for screen in (TITLE, SLOTS, ERASE):
        menu.screen = screen
        menu.draw(surface)


def test_a_new_day_saves_the_game_by_itself(tmp_path):
    # So a crash or a pulled plug costs at most the day in progress.
    game = PlayScene(seed=4, save_slot=0, save_folder=tmp_path)
    game.clock.elapsed = config.DAY_TOTAL - config.FIXED_DT / 2
    assert saves.info(0, tmp_path) is None
    game.update(config.FIXED_DT)
    assert game.clock.day == 2
    assert saves.info(0, tmp_path).day == 2


def test_a_game_with_no_slot_never_writes(tmp_path, monkeypatch):
    writes: list[int] = []
    monkeypatch.setattr(saves, "save", lambda *a, **k: writes.append(1))
    game = PlayScene(seed=4)
    game.clock.elapsed = config.DAY_TOTAL - config.FIXED_DT / 2
    game.update(config.FIXED_DT)
    assert writes == []
