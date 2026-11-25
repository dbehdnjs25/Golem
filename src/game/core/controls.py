"""Which key does what, and the player's own changes to it.

Pure state: a table from action to keys. Nothing here reads the keyboard --
the scene hands a pressed key in and asks what it means. Loading and saving
take a path, so tests never touch the real settings file.

Rebinding a key that another action already uses SWAPS the two rather than
leaving one action with no key at all. An action that cannot be reached is
worse than two keys trading places, because the player may not notice until
the moment they need it.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import pygame

MOVE_UP = "move_up"
MOVE_DOWN = "move_down"
MOVE_LEFT = "move_left"
MOVE_RIGHT = "move_right"
SPRINT = "sprint"
DODGE = "dodge"
ACTION = "action"  # dig, swing, build, eat -- whatever the hand is holding
SYNC = "sync"
INVENTORY = "inventory"
CRAFT = "craft"
DRAW_UP = "draw_up"
DRAW_DOWN = "draw_down"
DRAW_LEFT = "draw_left"
DRAW_RIGHT = "draw_right"
SLOT_1 = "slot_1"
SLOT_2 = "slot_2"
SLOT_3 = "slot_3"
SLOT_4 = "slot_4"
SLOT_5 = "slot_5"
ZOOM_IN = "zoom_in"
ZOOM_OUT = "zoom_out"

SLOTS = (SLOT_1, SLOT_2, SLOT_3, SLOT_4, SLOT_5)

# Order is the order the settings screen lists them in.
LABELS: dict[str, str] = {
    MOVE_UP: "위로 이동",
    MOVE_DOWN: "아래로 이동",
    MOVE_LEFT: "왼쪽으로 이동",
    MOVE_RIGHT: "오른쪽으로 이동",
    SPRINT: "달리기",
    DODGE: "회피",
    ACTION: "행동 (채굴·공격·설치·먹기)",
    SYNC: "코어에 넣기",
    INVENTORY: "가방",
    CRAFT: "제작",
    DRAW_UP: "마법 획 ↑",
    DRAW_DOWN: "마법 획 ↓",
    DRAW_LEFT: "마법 획 ←",
    DRAW_RIGHT: "마법 획 →",
    SLOT_1: "핫바 1",
    SLOT_2: "핫바 2",
    SLOT_3: "핫바 3",
    SLOT_4: "핫바 4",
    SLOT_5: "핫바 5",
    ZOOM_IN: "확대",
    ZOOM_OUT: "축소",
}
ACTIONS: tuple[str, ...] = tuple(LABELS)

DEFAULTS: dict[str, tuple[int, ...]] = {
    MOVE_UP: (pygame.K_w,),
    MOVE_DOWN: (pygame.K_s,),
    MOVE_LEFT: (pygame.K_a,),
    MOVE_RIGHT: (pygame.K_d,),
    SPRINT: (pygame.K_LSHIFT, pygame.K_RSHIFT),
    DODGE: (pygame.K_SPACE,),
    ACTION: (pygame.K_f,),
    SYNC: (pygame.K_e,),
    INVENTORY: (pygame.K_i,),
    CRAFT: (pygame.K_c,),
    DRAW_UP: (pygame.K_UP,),
    DRAW_DOWN: (pygame.K_DOWN,),
    DRAW_LEFT: (pygame.K_LEFT,),
    DRAW_RIGHT: (pygame.K_RIGHT,),
    SLOT_1: (pygame.K_1,),
    SLOT_2: (pygame.K_2,),
    SLOT_3: (pygame.K_3,),
    SLOT_4: (pygame.K_4,),
    SLOT_5: (pygame.K_5,),
    # Side by side under the right hand, so a view can be nudged without
    # leaving the keys that move. The old +/- sat at the far corner of the
    # board, which is a reach for something used while walking.
    ZOOM_IN: (pygame.K_o,),
    ZOOM_OUT: (pygame.K_p,),
}

# Never rebindable: the way out of a screen and the way into this one. A
# player who binds "open settings" to something they then forget has no way
# back, so these stay put.
SETTINGS_KEY = pygame.K_F1
BACK_KEY = pygame.K_ESCAPE
RESERVED = frozenset({SETTINGS_KEY, BACK_KEY, pygame.K_F11})

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "controls.json"


class Controls:
    def __init__(self, bindings: dict[str, tuple[int, ...]] | None = None) -> None:
        self._keys: dict[str, tuple[int, ...]] = dict(DEFAULTS)
        if bindings:
            for action, keys in bindings.items():
                if action in self._keys and keys:
                    self._keys[action] = tuple(keys)

    def keys_for(self, action: str) -> tuple[int, ...]:
        return self._keys[action]

    def is_key(self, key: int, action: str) -> bool:
        return key in self._keys[action]

    def any_held(self, held: Iterable[int], action: str) -> bool:
        return any(key in self._keys[action] for key in held)

    def action_of(self, key: int) -> str | None:
        """The first action ``key`` is bound to, in listing order."""
        for action in ACTIONS:
            if key in self._keys[action]:
                return action
        return None

    def rebind(self, action: str, key: int) -> bool:
        """Give ``action`` this one key. False, and nothing changed, if reserved.

        Whatever held the key before takes ``action``'s old first key in
        exchange, so nothing is ever left unbound.
        """
        if key in RESERVED or action not in self._keys:
            return False
        old = self._keys[action]
        for other, keys in self._keys.items():
            if other != action and key in keys:
                rest = tuple(k for k in keys if k != key)
                self._keys[other] = rest if rest else old[:1]
        self._keys[action] = (key,)
        return True

    def reset(self) -> None:
        self._keys = dict(DEFAULTS)

    # --- persistence -----------------------------------------------------
    def to_dict(self) -> dict[str, list[str]]:
        """Key NAMES, not codes, so the file reads -- and edits -- by hand."""
        return {action: [pygame.key.name(k) for k in self._keys[action]] for action in ACTIONS}

    @classmethod
    def from_dict(cls, data: object) -> Controls:
        """Build from a saved table, skipping anything unreadable.

        A hand-edited file with one typo should cost that one binding, not
        every binding and not a crash on start.
        """
        bindings: dict[str, tuple[int, ...]] = {}
        if isinstance(data, dict):
            for action, names in data.items():
                if not isinstance(names, list):
                    continue
                keys = tuple(k for k in (_key_code(n) for n in names) if k is not None)
                if keys and not RESERVED.intersection(keys):
                    bindings[str(action)] = keys
        return cls(bindings)

    @classmethod
    def load(cls, path: Path) -> Controls:
        try:
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return cls()  # no file yet, or a broken one: the defaults

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), "utf-8")


def _key_code(name: object) -> int | None:
    if not isinstance(name, str):
        return None
    try:
        return pygame.key.key_code(name)
    except ValueError:
        return None


def key_label(key: int) -> str:
    return pygame.key.name(key).upper() or "?"
