"""The main menu: Play, then one of three save slots.

An empty slot starts a new game there (a fresh world seed each time); a full
one carries on exactly where that game was left. Delete erases a slot, after
asking. Leaving a game -- the Esc menu or the window's close button -- saves
it back into its slot and returns here.

Keyboard first, like the rest of the game (arrows or W/S, Enter, Esc), and
the rows can be clicked too. The layout is one pure function, ``_rows``, that
both drawing and clicking read, so a click lands on what is drawn.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from pathlib import Path

import pygame

from game import config, saves
from game.core.controls import Controls
from game.core.scene import Scene
from game.scenes.play import PlayScene, _draw_frame, _font

TITLE = "title"  # Play / Quit
SLOTS = "slots"  # the three slots and Back
ERASE = "erase"  # "really delete?"

PLAY, QUIT, BACK = "play", "quit", "back"
_TITLE_ROWS = ((PLAY, "플레이"), (QUIT, "종료"))
_CONFIRM = {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}
_UP = {pygame.K_UP, pygame.K_w}
_DOWN = {pygame.K_DOWN, pygame.K_s}
_ROW_W, _ROW_H, _GAP = 520, 64, 14


def _fresh_seed() -> int:
    return random.SystemRandom().randrange(2**32)


def _slot_label(slot: int, info: saves.SlotInfo | None) -> str:
    if info is None:
        return f"세이브 {slot + 1}  ·  비어 있음 (새 게임)"
    when = time.strftime("%m월 %d일 %H:%M", time.localtime(info.saved_at))
    return f"세이브 {slot + 1}  ·  {info.day}일째  ·  {when}"


class MenuScene(Scene):
    def __init__(
        self,
        controls: Controls | None = None,
        controls_path: Path | None = None,
        save_folder: Path = saves.SAVE_DIR,
        new_seed: Callable[[], int] = _fresh_seed,
    ) -> None:
        self.controls = controls if controls is not None else Controls()
        self.controls_path = controls_path
        self.save_folder = save_folder
        self.new_seed = new_seed
        self.screen = TITLE
        self.cursor = 0
        self.message = ""  # a line under the list, e.g. a save that would not load
        self.infos: list[saves.SlotInfo | None] = []
        self._erasing = 0  # the slot the "really delete?" screen is about
        self._stale = True  # re-read the slots before showing them

    # --- what is listed -------------------------------------------------------
    def rows(self) -> list[tuple[str, str]]:
        """(id, label) for every row on the current screen."""
        if self.screen == TITLE:
            return list(_TITLE_ROWS)
        if self.screen == ERASE:
            return [("yes", "지우기"), (BACK, "취소")]
        slots = [(str(i), _slot_label(i, info)) for i, info in enumerate(self.infos)]
        return [*slots, (BACK, "뒤로")]

    def _rows(self, size: tuple[int, int]) -> list[pygame.Rect]:
        """Where each row sits on a screen of ``size``."""
        count = len(self.rows())
        top = size[1] // 2 - 20
        return [
            pygame.Rect((size[0] - _ROW_W) // 2, top + i * (_ROW_H + _GAP), _ROW_W, _ROW_H)
            for i in range(count)
        ]

    # --- logic ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self._stale:
            # Back from a game, which has just saved itself: show the new date.
            self.infos = [saves.info(i, self.save_folder) for i in range(saves.SLOTS)]
            self._stale = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._key(event.key)
        elif event.type == pygame.MOUSEMOTION:
            hit = self._hit(event.pos)
            if hit is not None:
                self.cursor = hit
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = self._hit(event.pos)
            if hit is not None:
                self.cursor = hit
                self._choose()

    def _hit(self, pos: tuple[int, int]) -> int | None:
        for index, rect in enumerate(self._rows(config.SCREEN_SIZE)):
            if rect.collidepoint(pos):
                return index
        return None

    def _key(self, key: int) -> None:
        count = len(self.rows())
        if key in _UP:
            self.cursor = (self.cursor - 1) % count
        elif key in _DOWN:
            self.cursor = (self.cursor + 1) % count
        elif key in _CONFIRM:
            self._choose()
        elif key == pygame.K_ESCAPE:
            self._back()
        elif key in (pygame.K_DELETE, pygame.K_BACKSPACE) and self._holds_a_game():
            self._erasing = self.cursor
            self._go(ERASE, cursor=1)  # "cancel" first: deleting takes intent

    def _holds_a_game(self) -> bool:
        """The cursor is on a slot with a save in it."""
        return (
            self.screen == SLOTS
            and self.cursor < saves.SLOTS
            and self.infos[self.cursor] is not None
        )

    def _go(self, screen: str, cursor: int = 0) -> None:
        self.screen, self.cursor, self.message = screen, cursor, ""
        if screen == SLOTS:
            self.infos = [saves.info(i, self.save_folder) for i in range(saves.SLOTS)]

    def _back(self) -> None:
        if self.screen == ERASE:
            self._go(SLOTS, cursor=self._erasing)
        elif self.screen == SLOTS:
            self._go(TITLE)

    def _choose(self) -> None:
        choice = self.rows()[self.cursor][0]
        if self.screen == TITLE:
            if choice == PLAY:
                self._go(SLOTS)
            elif choice == QUIT and self.manager is not None:
                self.manager.pop()
        elif self.screen == ERASE:
            if choice == "yes":
                saves.erase(self._erasing, self.save_folder)
            self._go(SLOTS, cursor=self._erasing)
        elif choice == BACK:
            self._go(TITLE)
        else:
            self._start(int(choice))

    def _start(self, slot: int) -> None:
        """Carry on the game in ``slot``, or begin a new one there."""
        if self.infos[slot] is None:
            game = PlayScene(
                self.controls,
                self.controls_path,
                seed=self.new_seed(),
                save_slot=slot,
                save_folder=self.save_folder,
            )
        else:
            try:
                game = saves.load(slot, self.save_folder)
            except Exception:  # noqa: BLE001 - any unreadable save is reported, not raised
                self.message = (
                    f"세이브 {slot + 1}을(를) 불러올 수 없어요. "
                    "Delete로 지우고 새로 시작할 수 있어요."
                )
                return
            game.use_controls(self.controls, self.controls_path)
            game.save_slot, game.save_folder = slot, self.save_folder
        self._stale = True
        if self.manager is not None:
            self.manager.push(game)

    # --- drawing ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18, 20, 19))
        width, height = surface.get_size()
        title = _font(64).render(config.TITLE, True, config.WHITE)
        surface.blit(title, title.get_rect(center=(width // 2, height // 2 - 170)))
        if self.screen == SLOTS:
            heading = "세이브를 고르세요"
        elif self.screen == ERASE:
            heading = f"세이브 {self._erasing + 1}을(를) 지울까요? 되돌릴 수 없어요."
        else:
            heading = ""
        if heading:
            line = _font(20).render(heading, True, (200, 200, 205))
            surface.blit(line, line.get_rect(center=(width // 2, height // 2 - 70)))
        for index, ((_, label), rect) in enumerate(
            zip(self.rows(), self._rows((width, height)), strict=True)
        ):
            _draw_frame(surface, rect, selected=index == self.cursor)
            text = _font(22).render(label, True, config.WHITE)
            surface.blit(text, text.get_rect(center=rect.center))
        hint = "↑↓ 고르기 · Enter 선택 · Esc 뒤로"
        if self.screen == SLOTS:
            hint += " · Delete 세이브 지우기"
        foot = _font(15).render(self.message or hint, True, (160, 160, 170))
        surface.blit(foot, foot.get_rect(midbottom=(width // 2, height - 30)))
