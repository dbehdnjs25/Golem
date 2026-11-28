"""Which picture files the game has read, so a saved one can be read again.

Every loader in ``render/`` calls ``note(path)`` for each file it looks at --
found or not -- and starts over when ``generation`` moves on. ``refresh`` is
called about once a second by the running scene: if any noted file changed,
appeared or vanished since it was read, ``generation`` steps and every cache
is dropped, to be refilled lazily from disk.

Dropping everything rather than the one picture keeps this to one rule; a
handful of PNGs reload in well under a frame.
"""

from __future__ import annotations

from pathlib import Path

generation = 0
_seen: dict[Path, float | None] = {}


def _stamp(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def note(path: Path) -> None:
    """Remember ``path`` as it is now (``None`` if it does not exist)."""
    _seen[path] = _stamp(path)


def refresh(force: bool = False) -> bool:
    """Drop every cached picture if one of them changed on disk. True if so."""
    global generation
    if not force and all(_stamp(path) == stamp for path, stamp in _seen.items()):
        return False
    _seen.clear()
    generation += 1
    return True
