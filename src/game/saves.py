"""Three save slots on disk: the whole game, exactly as it was left.

The whole ``PlayScene`` is pickled -- every golem, tree, temple room, dropped
stack and the dice mid-roll -- rather than a hand-written list of fields, so a
system added later is saved without anyone remembering to add it here.

One catch makes that work: the game compares its catalogue entries by
identity (``kind is CORE_SHARD``, ``room.kind is BOSS``). A plain pickle would
load copies, equal but not the same object, and every one of those checks
would quietly fail. So every module-level constant in ``game`` -- the frozen
item kinds, biomes and the rest, the tuples and dicts of them, and the named
strings -- is written as a reference to where it lives, and loading hands
back that very object.

A slot is two files: ``slotN.save`` (the pickle) and ``slotN.json`` (a few
lines for the menu, so listing slots never unpickles a whole world). Written
to a temporary file first and swapped in, so a crash mid-save leaves the
previous save rather than half of one.

Pickle runs code when it loads, so only load saves this game wrote.
"""

from __future__ import annotations

import dataclasses
import importlib
import io
import json
import pickle
import pkgutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from game.scenes.play import PlayScene

SLOTS = 3
VERSION = 1
SAVE_DIR = Path(__file__).resolve().parents[2] / "saves"


@dataclass(frozen=True)
class SlotInfo:
    """What the menu shows for a slot that holds a game."""

    day: int
    saved_at: float  # seconds since the epoch


# --- constants by reference --------------------------------------------------
_Token = tuple[str, tuple[Any, ...]]
_by_id: dict[int, _Token] = {}
_by_text: dict[str, _Token] = {}


def _is_constant(value: object) -> bool:
    return (
        dataclasses.is_dataclass(value)
        and not isinstance(value, type)
        and value.__dataclass_params__.frozen  # type: ignore[attr-defined]
    )


def _index() -> None:
    """Find every constant once: named ones first, then those inside tuples,
    lists and dicts, so an entry gets its shortest address."""
    if _by_id:
        return
    import game

    for found in pkgutil.walk_packages(game.__path__, "game."):
        if found.name != "game.__main__":
            importlib.import_module(found.name)
    modules = sorted((n, m) for n, m in sys.modules.items() if n.startswith("game"))
    for name, module in modules:
        for attr, value in vars(module).items():
            if _is_constant(value):
                _by_id.setdefault(id(value), (name, (attr,)))
            elif isinstance(value, str) and attr.isupper():
                _by_text.setdefault(value, (name, (attr,)))
    for name, module in modules:
        for attr, value in vars(module).items():
            if isinstance(value, tuple | list):
                for i, item in enumerate(value):
                    if _is_constant(item):
                        _by_id.setdefault(id(item), (name, (attr, i)))
            elif isinstance(value, dict):
                for key, item in value.items():
                    if _is_constant(item) and isinstance(key, str | int):
                        _by_id.setdefault(id(item), (name, (attr, key)))


def _resolve(token: _Token) -> object:
    module, path = token
    value: Any = vars(sys.modules[module])[path[0]]
    for step in path[1:]:
        value = value[step]
    return value


class _Pickler(pickle.Pickler):
    def persistent_id(self, obj: object) -> _Token | None:
        token = _by_id.get(id(obj))
        if token is not None:
            return token
        if type(obj) is str:
            return _by_text.get(obj)
        return None


class _Unpickler(pickle.Unpickler):
    def persistent_load(self, pid: Any) -> object:
        module, path = pid
        return _resolve((str(module), tuple(path)))


def dumps(scene: PlayScene) -> bytes:
    _index()
    out = io.BytesIO()
    _Pickler(out, protocol=pickle.HIGHEST_PROTOCOL).dump((VERSION, scene))
    return out.getvalue()


def loads(data: bytes) -> PlayScene:
    _index()
    version, scene = _Unpickler(io.BytesIO(data)).load()
    if version != VERSION:
        raise ValueError(f"save version {version}, this game reads {VERSION}")
    return scene  # type: ignore[no-any-return]


# --- slots on disk -------------------------------------------------------------
def _paths(slot: int, folder: Path) -> tuple[Path, Path]:
    if not 0 <= slot < SLOTS:
        raise ValueError(f"no slot {slot}")
    return folder / f"slot{slot + 1}.save", folder / f"slot{slot + 1}.json"


def _swap_in(path: Path, data: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def save(scene: PlayScene, slot: int, folder: Path = SAVE_DIR) -> None:
    game_file, info_file = _paths(slot, folder)
    folder.mkdir(parents=True, exist_ok=True)
    _swap_in(game_file, dumps(scene))
    info = {"day": scene.clock.day, "saved_at": time.time()}
    _swap_in(info_file, json.dumps(info).encode("utf-8"))


def load(slot: int, folder: Path = SAVE_DIR) -> PlayScene:
    """The game in ``slot``. Raises if it is missing or will not read."""
    game_file, _ = _paths(slot, folder)
    return loads(game_file.read_bytes())


def info(slot: int, folder: Path = SAVE_DIR) -> SlotInfo | None:
    """What the slot holds, or None if it is empty."""
    game_file, info_file = _paths(slot, folder)
    if not game_file.exists():
        return None
    try:
        raw = json.loads(info_file.read_text(encoding="utf-8"))
        return SlotInfo(day=int(raw["day"]), saved_at=float(raw["saved_at"]))
    except (OSError, ValueError, KeyError, TypeError):
        return SlotInfo(day=0, saved_at=game_file.stat().st_mtime)


def erase(slot: int, folder: Path = SAVE_DIR) -> None:
    for path in _paths(slot, folder):
        path.unlink(missing_ok=True)
