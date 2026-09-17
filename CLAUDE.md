# CLAUDE.md — Pygame Project Guide

Conventions and references for working in this repo. Read before adding features.

## Stack

- **pygame-ce** (Community Edition, `pip install pygame-ce`, imported as `pygame`).
  Do **not** install stock `pygame` alongside it — they conflict.
- Python **>= 3.10**. Dev tools: **pytest + pytest-cov**, **ruff** (lint+format),
  **mypy** (strict).
- `src/` layout; the package is `game` under `src/`. Editable install: `pip install -e ".[dev]"`.

## The one rule that makes this testable: separate `update` from `draw`

- **Logic goes in `update(dt, ...)`** — takes the timestep (and input) as explicit
  arguments. No wall-clock, no `pygame.key.get_pressed()` reached from inside, no
  globals. Deterministic → unit-testable headlessly.
- **Rendering goes in `draw(surface)`** — the *only* code that touches SDL surfaces.
- **`pygame.display` / event pump / `pygame.quit`** live only in `core/app.py`.
  Scenes and entities never touch them; they receive parsed events and request
  transitions via the `SceneManager`.

When adding a feature, write the logic as a pure `update(dt)` first, test it, then
wire drawing.

## Fixed timestep

The loop advances logic in fixed `FIXED_DT = 1/60` steps via `core/loop.FixedTimestep`
(accumulator pattern, frame time clamped to `MAX_FRAME_TIME` to avoid the
"spiral of death"). Always pass `FIXED_DT` to `update` — never a raw frame delta —
so runs are reproducible. The accumulator is pure and has its own tests.

## Testing (TDD workflow)

1. Write a failing test in `tests/` (mirrors `src/game/`).
2. Implement the minimal logic to pass.
3. Refactor. Keep `update` pure so tests stay display-free.

Headless setup lives in `tests/conftest.py`: it sets `SDL_VIDEODRIVER=dummy` and
`SDL_AUDIODRIVER=dummy` **before** pygame is imported, and provides:
- session-scoped autouse `pygame.init()/quit()` fixture (needed for `Vector2`,
  `Surface`, fonts — even with no window),
- a `surface` fixture: an off-screen `pygame.Surface((64,64))` for `draw()` tests
  (assert pixels with `surface.get_at((x, y))`),
- `requires_display` marker to skip the rare test needing a real renderer.

Run: `pytest` (coverage on by default). Prefer testing `entities/`, `systems/`,
`core/` — not pixel output.

## Where things go

| Concern | Location |
|---|---|
| Constants (size, fps, colours) | `game/config.py` (no pygame import) |
| Window / clock / event pump | `game/core/app.py` |
| Fixed-timestep maths | `game/core/loop.py` |
| Scene base + stack manager | `game/core/scene.py` |
| A game state (menu, play, pause) | `game/scenes/*.py` |
| Player/enemy/bullet logic | `game/entities/*.py` |
| Cross-entity systems (physics, collision, spawning) | `game/systems/*.py` (add when needed) |
| Terrain: biomes, the map circle, resource distribution | `game/world/*.py` |
| Assets | `assets/{images,sounds,fonts}/` |

The `Ball` entity + `PlayScene` are **example scaffolding** demonstrating the
pattern — replace or delete them once the real game is designed.

## Commands

```bash
python -m game        # run
pytest                # test + coverage
ruff check . && ruff format --check .
mypy
```

## References

**pygame-ce / API**
- pygame-ce: https://github.com/pygame-community/pygame-ce · PyPI https://pypi.org/project/pygame-ce/
- API docs (compatible): https://www.pygame.org/docs/

**Headless testing**
- HeadlessNoWindowsNeeded: https://www.pygame.org/wiki/HeadlessNoWindowsNeeded
- DummyVideoDriver: https://www.pygame.org/wiki/DummyVideoDriver

**Game loop / timestep**
- Fix Your Timestep! (Gaffer On Games): https://gafferongames.com/post/fix_your_timestep/
- pygame ConstantGameSpeed: https://www.pygame.org/wiki/ConstantGameSpeed

**Structure / tutorials**
- The Ultimate Pygame Structure (template): https://github.com/SebZanardo/The-Ultimate-Pygame-Structure
- Python game code structure: https://liamquiroz.com/python-game-code-structure/

**Tooling**
- Ruff: https://docs.astral.sh/ruff/configuration/
- pytest-cov: https://pytest-cov.readthedocs.io/
