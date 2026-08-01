# Items & Inventory UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give inventory contents an item identity, then let the player open the Core like a chest and drag stacks between it and the backpack, with a transfer delay proportional to the megabytes moved.

**Architecture:** `ItemKind` is a frozen dataclass in a catalogue table (same pattern as the existing tools). `Folder` becomes `dict[key, count]` with an MB cap and a `reserved_mb` field so an in-flight transfer cannot lose its landing space to mining. Transfers are a serial queue of `TransferJob`s owned by `PlayScene`. The window is **not** a new scene — `SceneManager` only draws the top of the stack, so the window is overlay state on `PlayScene`. All geometry and hit-testing are pure functions in a new `ui/` package, tested without a surface.

**Tech Stack:** Python 3.10+, pygame-ce 2.5, pytest + pytest-cov, ruff, mypy (strict).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-30-inventory-ui-design.md`. Read it before Task 1.
- Logic lives in `update(dt, ...)` and takes the timestep explicitly. Rendering lives in `draw(surface)`. Nothing outside `core/app.py` touches `pygame.display`, the event pump, or `pygame.quit`.
- **No input polling inside scenes.** `pygame.key.get_pressed()` and `pygame.key.get_mods()` are banned; modifier state is tracked from KEYDOWN/KEYUP events.
- Run tools from the venv on Windows: `.venv/Scripts/pytest.exe`, `.venv/Scripts/ruff.exe`, `.venv/Scripts/mypy.exe`. Bare `pytest` / `python -m pytest` will fail — the global interpreter has no pytest.
- ruff line-length 100, target py310. mypy runs on `packages = ["game"]` only, so tests need no annotations but every function under `src/game/**` does.
- Every module starts with `from __future__ import annotations`.
- Money numbers already in `config.py`, do not change: `FRAGMENT_MB = 3`, `BACKPACK_CAP_MB = 100`, `DOCUMENTS_CAP_MB = 750`.
- After every task run the **full check**, and do not commit until it is clean:
  `.venv/Scripts/ruff.exe format . && .venv/Scripts/ruff.exe check . && .venv/Scripts/mypy.exe && .venv/Scripts/pytest.exe`
  (`ruff format .` rewrites files to the repo style — run it before `check`, and re-`git add` anything it touches.)
- The suite must be green at **every** commit. Task 2 therefore migrates `Folder`'s call sites in the same commit that changes `Folder`.
- Commit messages in English; documentation prose in Korean.
- **New imports go at the top of the test file, with the existing ones.** ruff's E402
  fails on a mid-file `import`, so when a task says "append these tests", hoist their
  imports rather than pasting them inline.
- **Keep scene-driving test loops under ~150 steps (2.5s).** `EnemySpawner` fires every
  3 simulated seconds and a virus that reaches the player can kill it, which triggers
  the death penalty and corrupts an inventory assertion. Where a test only needs to
  check what a drop *decided*, assert on `transfers.active` instead of running the clock.

---

### Task 1: `ItemKind` catalogue

The data table every later task keys off. Nothing else changes yet, so the suite stays green trivially.

**Files:**
- Create: `src/game/items/item_kinds.py`
- Test: `tests/test_item_kinds.py`

**Interfaces:**
- Consumes: `game.config.FRAGMENT_MB`, `game.config.FRAGMENT_COLOR` (both already exist).
- Produces:
  - `ItemKind(key: str, name: str, mb: int, color: tuple[int, int, int])` — frozen dataclass
  - `FRAGMENT: ItemKind`
  - `CATALOGUE: tuple[ItemKind, ...]` — display order
  - `ITEM_KINDS: dict[str, ItemKind]` — key lookup

- [ ] **Step 1: Write the failing test**

Create `tests/test_item_kinds.py`:

```python
import dataclasses

import pytest

from game import config
from game.items.item_kinds import CATALOGUE, FRAGMENT, ITEM_KINDS, ItemKind


def test_fragment_row_matches_config():
    assert FRAGMENT.key == "fragment"
    assert FRAGMENT.mb == config.FRAGMENT_MB
    assert len(FRAGMENT.color) == 3


def test_catalogue_leads_with_fragment():
    assert CATALOGUE[0] is FRAGMENT


def test_lookup_maps_every_catalogue_key():
    assert set(ITEM_KINDS) == {k.key for k in CATALOGUE}
    assert ITEM_KINDS["fragment"] is FRAGMENT


def test_kinds_are_frozen_and_hashable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        FRAGMENT.mb = 99  # type: ignore[misc]
    assert {FRAGMENT: 1}[FRAGMENT] == 1  # usable as a dict key


def test_every_kind_has_a_positive_size():
    assert all(k.mb > 0 for k in CATALOGUE)


def test_keys_are_unique():
    keys = [k.key for k in CATALOGUE]
    assert len(keys) == len(set(keys))


def test_kind_is_a_dataclass_with_a_name():
    assert isinstance(FRAGMENT, ItemKind)
    assert FRAGMENT.name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_item_kinds.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.items.item_kinds'`

- [ ] **Step 3: Write the implementation**

Create `src/game/items/item_kinds.py`:

```python
"""The catalogue of item kinds. Data only — a frozen row per kind, no behaviour.

Same shape as ``items/tools.py``: the table lives here, the systems that act on
it live in ``systems/`` and ``inventory/``. Adding an item kind is adding a row.

``key`` is the stable identifier that goes into save files; ``name`` is what the
player reads. They are separate so renaming the display text never invalidates a
save.
"""

from __future__ import annotations

from dataclasses import dataclass

from game import config


@dataclass(frozen=True)
class ItemKind:
    key: str  # stable id, used for storage and comparison
    name: str  # shown in the inventory list
    mb: int  # storage size of one unit
    color: tuple[int, int, int]  # list icon colour


FRAGMENT = ItemKind(
    key="fragment",
    name="데이터 조각",
    mb=config.FRAGMENT_MB,
    color=config.FRAGMENT_COLOR,
)

# Draw order for inventory lists. Fixed on purpose: rows must not shuffle under
# the cursor as counts change, or drag targets move while the player is aiming.
CATALOGUE: tuple[ItemKind, ...] = (FRAGMENT,)

ITEM_KINDS: dict[str, ItemKind] = {kind.key: kind for kind in CATALOGUE}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/pytest.exe tests/test_item_kinds.py -v`
Expected: 7 passed

- [ ] **Step 5: Full check**

Run: `.venv/Scripts/ruff.exe format . && .venv/Scripts/ruff.exe check . && .venv/Scripts/mypy.exe && .venv/Scripts/pytest.exe`
Expected: all green, 106 passed

- [ ] **Step 6: Commit**

```bash
git add src/game/items/item_kinds.py tests/test_item_kinds.py
git commit -m "feat(items): add ItemKind catalogue"
```

---

### Task 2: Rework `Folder` to hold typed items, and migrate every call site

`Folder` currently is an int counter. This task replaces it and updates every reader in the same commit — there is no intermediate state where the suite can pass. `E` keeps its current "sync everything now" behaviour here; Task 6 replaces it with the window.

**Files:**
- Modify: `src/game/inventory/storage.py` (full rewrite)
- Modify: `src/game/entities/fragment.py:18` (`mb_value` → `kind`)
- Modify: `src/game/systems/mining.py:50-53`
- Modify: `src/game/systems/combat.py:94-96`
- Modify: `src/game/scenes/play.py:19` (import), `:167-168` (sync)
- Test: `tests/test_storage.py` (full rewrite), `tests/test_mining.py:61,83`, `tests/test_combat.py:109-113`, `tests/test_play_scene.py:39-77,113`

**Interfaces:**
- Consumes: `ItemKind`, `FRAGMENT`, `CATALOGUE`, `ITEM_KINDS` from Task 1.
- Produces:
  - `Folder(cap_mb: int, items: dict[ItemKind, int] = {}, reserved_mb: int = 0)`
    (The spec sketched `dict[str, int]`. Keying by the frozen `ItemKind` itself is
    strictly better: `used_mb` needs no catalogue lookup, so it cannot raise on a
    kind the catalogue does not list. `key` is still what gets written to a save
    file when spec D lands — that is a serialisation concern, not a storage one.)
  - `Folder.used_mb -> int`, `Folder.free_mb -> int` (`cap - used - reserved`)
  - `Folder.fits(kind: ItemKind, n: int) -> int`
  - `Folder.count(kind: ItemKind) -> int`
  - `Folder.add(kind: ItemKind, n: int = 1) -> int`
  - `Folder.remove(kind: ItemKind, n: int = 1) -> int`
  - `Folder.rows() -> list[tuple[ItemKind, int]]` (catalogue order, zero-count rows omitted)
  - `Folder.reserve(mb: int) -> None`, `Folder.release(mb: int) -> None`
  - `Fragment.kind: ItemKind`
  - `transfer()` and `Folder.is_full` are **deleted**.

- [ ] **Step 1: Write the failing storage tests**

Replace the whole of `tests/test_storage.py`:

```python
from game.inventory.storage import Folder
from game.items.item_kinds import FRAGMENT, ItemKind

# Deliberately NOT in the catalogue: a folder must handle any kind it is handed,
# so used_mb cannot depend on a catalogue lookup.
HEAVY = ItemKind(key="heavy", name="큰 파일", mb=10, color=(1, 2, 3))


def test_add_counts_per_kind_and_bills_megabytes():
    f = Folder(cap_mb=30)  # 10 fragments
    assert f.add(FRAGMENT, 3) == 3
    assert f.count(FRAGMENT) == 3
    assert f.used_mb == 9
    assert f.free_mb == 21


def test_add_caps_at_capacity_and_reports_actual():
    f = Folder(cap_mb=30)
    assert f.add(FRAGMENT, 100) == 10
    assert f.add(FRAGMENT, 1) == 0
    assert f.free_mb == 0


def test_remove_is_bounded_by_what_is_stored():
    f = Folder(cap_mb=30)
    f.add(FRAGMENT, 4)
    assert f.remove(FRAGMENT, 3) == 3
    assert f.count(FRAGMENT) == 1
    assert f.remove(FRAGMENT, 99) == 1
    assert f.count(FRAGMENT) == 0


def test_removing_an_absent_kind_reports_zero():
    f = Folder(cap_mb=30)
    assert f.remove(HEAVY, 5) == 0


def test_kinds_are_counted_separately_and_share_the_cap():
    f = Folder(cap_mb=30)
    f.add(HEAVY, 2)  # 20 MB
    assert f.count(HEAVY) == 2
    assert f.count(FRAGMENT) == 0
    assert f.add(FRAGMENT, 5) == 3  # only 10 MB left -> 3 fragments


def test_fits_reports_what_would_actually_go_in():
    f = Folder(cap_mb=30)
    assert f.fits(FRAGMENT, 4) == 4
    assert f.fits(FRAGMENT, 50) == 10
    f.add(FRAGMENT, 9)
    assert f.fits(FRAGMENT, 5) == 1


def test_rows_follow_catalogue_order_and_skip_empties():
    f = Folder(cap_mb=100)
    assert f.rows() == []
    f.add(FRAGMENT, 2)
    assert f.rows() == [(FRAGMENT, 2)]
    f.add(FRAGMENT, 3)
    assert f.rows() == [(FRAGMENT, 5)]  # count changed, position did not
    f.remove(FRAGMENT, 5)
    assert f.rows() == []  # an emptied row leaves the list


def test_reserved_space_cannot_be_taken_by_anything_else():
    f = Folder(cap_mb=30)
    f.reserve(21)
    assert f.free_mb == 9
    assert f.fits(FRAGMENT, 10) == 3
    assert f.add(FRAGMENT, 10) == 3


def test_release_gives_the_space_back():
    f = Folder(cap_mb=30)
    f.reserve(30)
    assert f.fits(FRAGMENT, 1) == 0
    f.release(30)
    assert f.fits(FRAGMENT, 10) == 10


def test_release_cannot_drive_the_reservation_negative():
    f = Folder(cap_mb=30)
    f.reserve(3)
    f.release(99)
    assert f.reserved_mb == 0
    assert f.free_mb == 30


def test_two_folders_do_not_share_the_default_dict():
    a, b = Folder(cap_mb=30), Folder(cap_mb=30)
    a.add(FRAGMENT, 1)
    assert b.count(FRAGMENT) == 0


def test_the_old_int_api_is_gone():
    import game.inventory.storage as storage

    assert not hasattr(storage, "transfer")
    assert not hasattr(Folder(cap_mb=30), "is_full")
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_storage.py -v`
Expected: FAIL — `TypeError: Folder.add() takes from 1 to 2 positional arguments but 3 were given` (and friends)

- [ ] **Step 3: Rewrite `storage.py`**

Replace the whole of `src/game/inventory/storage.py`:

```python
"""Capacity-limited storage, measured in megabytes.

Two instances are used by the game: a small field backpack (fills while mining,
forces return trips) and the larger ``/Documents`` drive store at the core.

A folder is a list of rows, not a grid of slots — the game's material is a file
system, so ``12 fragments`` is one line, and the limit is megabytes rather than
a slot count. Kinds with different sizes therefore compete for the same space.

``reserved_mb`` is space promised to a transfer that is still in flight. It is
subtracted from ``free_mb``, so mining and other transfers cannot take the
landing space out from under a job that has already left its source folder.

Rows are keyed by the ``ItemKind`` itself (it is frozen, therefore hashable), not
by its ``key`` string: sizing the contents then needs no catalogue lookup and
cannot fail on an unlisted kind. Saving writes ``kind.key`` — that is the save
format's business, not this module's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game.items.item_kinds import CATALOGUE, ItemKind


@dataclass
class Folder:
    cap_mb: int
    items: dict[ItemKind, int] = field(default_factory=dict)
    reserved_mb: int = 0

    @property
    def used_mb(self) -> int:
        return sum(kind.mb * n for kind, n in self.items.items())

    @property
    def free_mb(self) -> int:
        return self.cap_mb - self.used_mb - self.reserved_mb

    def count(self, kind: ItemKind) -> int:
        return self.items.get(kind, 0)

    def fits(self, kind: ItemKind, n: int) -> int:
        """How many of ``n`` would actually go in right now."""
        return max(0, min(n, self.free_mb // kind.mb))

    def add(self, kind: ItemKind, n: int = 1) -> int:
        """Add up to ``n``, bounded by free space. Return the number added."""
        added = self.fits(kind, n)
        if added:
            self.items[kind] = self.count(kind) + added
        return added

    def remove(self, kind: ItemKind, n: int = 1) -> int:
        """Remove up to ``n``, bounded by what is stored. Return the number removed."""
        removed = max(0, min(n, self.count(kind)))
        if removed:
            left = self.count(kind) - removed
            if left:
                self.items[kind] = left
            else:
                del self.items[kind]  # an empty row leaves the list
        return removed

    def rows(self) -> list[tuple[ItemKind, int]]:
        """``(kind, count)`` in catalogue order, empties omitted.

        A kind absent from ``CATALOGUE`` is invisible here. Every kind the game
        actually creates is in the catalogue; leaving one out is a bug in the
        table, not a case to handle.
        """
        return [(kind, self.items[kind]) for kind in CATALOGUE if self.items.get(kind)]

    def reserve(self, mb: int) -> None:
        self.reserved_mb += mb

    def release(self, mb: int) -> None:
        self.reserved_mb = max(0, self.reserved_mb - mb)
```

- [ ] **Step 4: Run the storage tests**

Run: `.venv/Scripts/pytest.exe tests/test_storage.py -v --no-cov`
Expected: 12 passed

- [ ] **Step 5: Point `Fragment` at its item kind**

In `src/game/entities/fragment.py`, replace line 18 and add the import. The whole dataclass becomes:

```python
from game.items.item_kinds import FRAGMENT, ItemKind


@dataclass
class Fragment:
    pos: pygame.Vector2
    hp: float = config.FRAGMENT_HP
    kind: ItemKind = FRAGMENT  # what mining it out yields
    on_depleted: Callable[[Fragment], None] | None = None
```

Keep `from game import config` — `config.FRAGMENT_HP` still needs it. `config.FRAGMENT_MB` is now reached through `FRAGMENT.mb` instead.

- [ ] **Step 6: Migrate mining**

In `src/game/systems/mining.py`, replace lines 50-53:

```python
    if backpack.fits(target.kind, 1) == 0:
        return FULL  # block before damaging -> fragment preserved
    if target.damage(active_tool.dps * dt):
        backpack.add(target.kind, 1)
```

- [ ] **Step 7: Migrate the death penalty**

In `src/game/systems/combat.py`, replace `apply_death_penalty` (lines 94-96):

```python
def apply_death_penalty(backpack: Folder) -> None:
    """Drop half of every row, keeping the rounded-up half. Documents are untouched.

    Per-row rather than per-total so no kind can be sheltered by dropping another.
    ``rows()`` returns a fresh list, so mutating during the loop is safe.
    """
    for kind, n in backpack.rows():
        backpack.remove(kind, n // 2)
```

- [ ] **Step 8: Migrate the scene**

In `src/game/scenes/play.py`:

Line 19, replace the import:
```python
from game.inventory.storage import Folder
```

Add below it:
```python
from game.items.item_kinds import FRAGMENT
```

Lines 167-168, replace the sync with the two-step move (`transfer` is gone):
```python
        if sync and self.core.is_in_sync_range(self.player.pos):
            moved = self.documents.add(FRAGMENT, self.backpack.count(FRAGMENT))
            self.backpack.remove(FRAGMENT, moved)
```

- [ ] **Step 9: Migrate the affected tests**

`tests/test_mining.py` — add `from game.items.item_kinds import FRAGMENT` at the top, then:
- line 61: `assert bp.count(FRAGMENT) == 1`
- lines 83-84:
```python
    bp = Folder(cap_mb=config.FRAGMENT_MB)  # holds exactly 1
    bp.add(FRAGMENT, 1)  # now full
```

`tests/test_combat.py` — add `from game.items.item_kinds import FRAGMENT`, then replace lines 109-113:
```python
@pytest.mark.parametrize("start,expected", [(5, 3), (4, 2), (1, 1), (0, 0)])
def test_death_penalty_halves_round_up(start, expected):
    backpack = Folder(cap_mb=1000)
    backpack.add(FRAGMENT, start)
    combat.apply_death_penalty(backpack)
    assert backpack.count(FRAGMENT) == expected
```

`tests/test_play_scene.py` — add `from game.items.item_kinds import FRAGMENT`, then rewrite every `.count` reference. Lines 39-77 become:

```python
def test_standing_on_core_does_not_sync_by_itself():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)  # stand on the core
    scene.backpack.add(FRAGMENT, 3)
    scene.update(config.FIXED_DT)
    assert scene.backpack.count(FRAGMENT) == 3  # sync is manual now
    assert scene.documents.count(FRAGMENT) == 0


def test_sync_key_transfers_backpack_at_core():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.backpack.add(FRAGMENT, 3)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.backpack.count(FRAGMENT) == 0
    assert scene.documents.count(FRAGMENT) == 3


def test_sync_key_does_nothing_out_of_range():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(1000, 1000)  # outside the core's sync zone
    scene.backpack.add(FRAGMENT, 3)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.backpack.count(FRAGMENT) == 3
    assert scene.documents.count(FRAGMENT) == 0


def test_sync_key_is_consumed_after_one_step():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.backpack.add(FRAGMENT, 3)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    scene.backpack.add(FRAGMENT, 2)  # mined more without pressing again
    scene.update(config.FIXED_DT)
    assert scene.backpack.count(FRAGMENT) == 2  # one press, one transfer
    assert scene.documents.count(FRAGMENT) == 3
```

Lines 107-114 become:
```python
def test_death_applies_penalty_and_starts_respawn():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(500, 500)  # away from the core's sync zone
    scene.backpack.add(FRAGMENT, 5)
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    assert scene.backpack.count(FRAGMENT) == 3  # halved, round up
    assert scene._respawn_timer > 0
```

- [ ] **Step 10: Run the full suite**

Run: `.venv/Scripts/pytest.exe`
Expected: all pass. If anything still references `mb_value`, `is_full`, `transfer`, or bare `.count`, fix it — `.venv/Scripts/ruff.exe check .` will not catch attribute errors, so read the failure.

- [ ] **Step 11: Full check**

Run: `.venv/Scripts/ruff.exe format . && .venv/Scripts/ruff.exe check . && .venv/Scripts/mypy.exe`
Expected: all clean

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "refactor(inventory): hold typed items in Folder, reserve space for transfers"
```

---

### Task 3: Transfer queue

Pure logic, no UI, no scene. The delay and the anti-duplication / anti-loss rules live here.

**Files:**
- Create: `src/game/inventory/transfer.py`
- Modify: `src/game/config.py` (add `TRANSFER_TIME_PER_MB`)
- Test: `tests/test_transfer.py`

**Interfaces:**
- Consumes: `Folder` (Task 2), `ItemKind`/`FRAGMENT` (Task 1).
- Produces:
  - `TransferJob(kind: ItemKind, count: int, dst: Folder, elapsed: float = 0.0)`
  - `TransferJob.total_mb -> int`, `.duration -> float`, `.progress -> float` (0..1), `.remaining -> float`
  - `TransferQueue(jobs: list[TransferJob] = [])`
  - `TransferQueue.active -> TransferJob | None`
  - `TransferQueue.enqueue(kind, n, *, src: Folder, dst: Folder) -> int`
  - `TransferQueue.update(dt: float) -> None`

- [ ] **Step 1: Add the config constant**

In `src/game/config.py`, after the `# --- Storage ---` block (line 47), insert:

```python
# --- Transfer ---------------------------------------------------------------
# Time cost of moving one megabyte between the backpack and the core. Billed per
# MB rather than per item so heavier kinds are automatically slower to shift.
TRANSFER_TIME_PER_MB: Final[float] = 0.02  # a full 100 MB backpack takes ~2s
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_transfer.py`:

```python
from game import config
from game.inventory.storage import Folder
from game.inventory.transfer import TransferJob, TransferQueue
from game.items.item_kinds import FRAGMENT


def _pair():
    return Folder(cap_mb=100), Folder(cap_mb=750)


def test_enqueue_takes_from_the_source_immediately():
    src, dst = _pair()
    src.add(FRAGMENT, 10)
    q = TransferQueue()
    assert q.enqueue(FRAGMENT, 4, src=src, dst=dst) == 4
    assert src.count(FRAGMENT) == 6
    assert dst.count(FRAGMENT) == 0  # not there yet


def test_items_land_only_after_the_full_duration():
    src, dst = _pair()
    src.add(FRAGMENT, 4)
    q = TransferQueue()
    q.enqueue(FRAGMENT, 4, src=src, dst=dst)
    duration = 4 * FRAGMENT.mb * config.TRANSFER_TIME_PER_MB
    q.update(duration - 0.001)
    assert dst.count(FRAGMENT) == 0
    q.update(0.001)
    assert dst.count(FRAGMENT) == 4
    assert q.active is None


def test_duration_scales_with_megabytes_not_item_count():
    src, dst = _pair()
    src.add(FRAGMENT, 6)
    q = TransferQueue()
    q.enqueue(FRAGMENT, 6, src=src, dst=dst)
    assert q.active is not None
    assert q.active.total_mb == 6 * FRAGMENT.mb
    assert q.active.duration == q.active.total_mb * config.TRANSFER_TIME_PER_MB


def test_in_flight_items_are_in_neither_folder():
    src, dst = _pair()
    src.add(FRAGMENT, 5)
    q = TransferQueue()
    q.enqueue(FRAGMENT, 5, src=src, dst=dst)
    q.update(0.01)
    assert src.count(FRAGMENT) == 0
    assert dst.count(FRAGMENT) == 0


def test_destination_space_is_reserved_so_mining_cannot_steal_it():
    src = Folder(cap_mb=100)
    dst = Folder(cap_mb=100)
    src.add(FRAGMENT, 10)
    q = TransferQueue()
    q.enqueue(FRAGMENT, 10, src=src, dst=dst)  # 30 MB in flight to dst
    assert dst.fits(FRAGMENT, 100) == 23  # 100 - 30 reserved = 70 MB -> 23
    dst.add(FRAGMENT, 100)  # something else fills every free byte
    q.update(999)
    assert dst.count(FRAGMENT) == 33  # 23 + the 10 in flight; nothing vanished
    assert dst.reserved_mb == 0


def test_jobs_run_one_at_a_time_in_order():
    src, dst = _pair()
    src.add(FRAGMENT, 6)
    q = TransferQueue()
    q.enqueue(FRAGMENT, 2, src=src, dst=dst)
    q.enqueue(FRAGMENT, 4, src=src, dst=dst)
    assert len(q.jobs) == 2
    first = 2 * FRAGMENT.mb * config.TRANSFER_TIME_PER_MB
    q.update(first)
    assert dst.count(FRAGMENT) == 2  # only the first landed
    assert q.active is not None
    assert q.active.count == 4


def test_leftover_time_carries_into_the_next_job():
    src, dst = _pair()
    src.add(FRAGMENT, 4)
    q = TransferQueue()
    q.enqueue(FRAGMENT, 2, src=src, dst=dst)
    q.enqueue(FRAGMENT, 2, src=src, dst=dst)
    q.update(999)  # one huge step must not strand the queue
    assert dst.count(FRAGMENT) == 4
    assert q.jobs == []


def test_enqueue_is_clamped_by_the_destination_at_drop_time():
    src = Folder(cap_mb=100)
    dst = Folder(cap_mb=9)  # 3 fragments
    src.add(FRAGMENT, 10)
    q = TransferQueue()
    assert q.enqueue(FRAGMENT, 10, src=src, dst=dst) == 3
    assert src.count(FRAGMENT) == 7  # the remainder stays put


def test_enqueue_is_clamped_by_the_source():
    src, dst = _pair()
    src.add(FRAGMENT, 2)
    q = TransferQueue()
    assert q.enqueue(FRAGMENT, 99, src=src, dst=dst) == 2


def test_a_full_destination_creates_no_job():
    src = Folder(cap_mb=100)
    dst = Folder(cap_mb=0)
    src.add(FRAGMENT, 5)
    q = TransferQueue()
    assert q.enqueue(FRAGMENT, 5, src=src, dst=dst) == 0
    assert q.jobs == []
    assert src.count(FRAGMENT) == 5


def test_progress_runs_zero_to_one():
    job = TransferJob(kind=FRAGMENT, count=10, dst=Folder(cap_mb=750))
    assert job.progress == 0.0
    job.elapsed = job.duration / 2
    assert job.progress == 0.5
    job.elapsed = job.duration * 2
    assert job.progress == 1.0  # clamped
    assert job.remaining == 0.0


def test_update_on_an_empty_queue_is_a_no_op():
    q = TransferQueue()
    q.update(1.0)
    assert q.active is None
```

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_transfer.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.inventory.transfer'`

- [ ] **Step 4: Write the implementation**

Create `src/game/inventory/transfer.py`:

```python
"""Delayed moves between two folders.

A drop does three things at once: clamp the amount to what the destination can
actually take, reserve that space in the destination, and remove the items from
the source. The job then holds them until its time is up.

Taking from the source first prevents duplication (there is never a moment where
both folders show the items). Reserving in the destination prevents the mirror
failure: without it, a core-to-backpack job could finish while the backpack is
full of freshly mined fragments and the cargo would have nowhere to go. The
reservation lives on the ``Folder`` rather than in this queue so that *every*
writer sees it — mining does not know the queue exists.

Consequence: a job always lands in full. Partial acceptance happens once, at
drop time, and never again.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game import config
from game.inventory.storage import Folder
from game.items.item_kinds import ItemKind


@dataclass
class TransferJob:
    kind: ItemKind
    count: int
    dst: Folder
    elapsed: float = 0.0

    @property
    def total_mb(self) -> int:
        return self.kind.mb * self.count

    @property
    def duration(self) -> float:
        return self.total_mb * config.TRANSFER_TIME_PER_MB

    @property
    def progress(self) -> float:
        if self.duration <= 0:
            return 1.0
        return min(1.0, self.elapsed / self.duration)

    @property
    def remaining(self) -> float:
        return max(0.0, self.duration - self.elapsed)


@dataclass
class TransferQueue:
    jobs: list[TransferJob] = field(default_factory=list)

    @property
    def active(self) -> TransferJob | None:
        return self.jobs[0] if self.jobs else None

    def enqueue(self, kind: ItemKind, n: int, *, src: Folder, dst: Folder) -> int:
        """Start moving up to ``n`` of ``kind``. Return the number actually taken."""
        moving = dst.fits(kind, min(n, src.count(kind)))
        if moving <= 0:
            return 0
        src.remove(kind, moving)
        job = TransferJob(kind=kind, count=moving, dst=dst)
        dst.reserve(job.total_mb)
        self.jobs.append(job)
        return moving

    def update(self, dt: float) -> None:
        """Advance the head job; spend any leftover time on the next one."""
        while dt > 0 and self.jobs:
            job = self.jobs[0]
            job.elapsed += dt
            if job.elapsed < job.duration:
                return
            dt = job.elapsed - job.duration
            self.jobs.pop(0)
            job.dst.release(job.total_mb)
            job.dst.add(job.kind, job.count)  # fits: the space was reserved
```

- [ ] **Step 5: Run the tests**

Run: `.venv/Scripts/pytest.exe tests/test_transfer.py -v --no-cov`
Expected: 12 passed

- [ ] **Step 6: Full check**

Run: `.venv/Scripts/ruff.exe format . && .venv/Scripts/ruff.exe check . && .venv/Scripts/mypy.exe && .venv/Scripts/pytest.exe`
Expected: all green

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(inventory): add delayed transfer queue"
```

---

### Task 4: Window geometry and drag arithmetic

Every "which row is under the cursor" question, answered without a surface. Pure functions, so they are unit-tested directly.

**Files:**
- Create: `src/game/ui/__init__.py`, `src/game/ui/inventory_panel.py`
- Modify: `src/game/config.py` (window layout block)
- Test: `tests/test_inventory_panel.py`, `tests/test_config.py` (one added assertion)

**Interfaces:**
- Consumes: config layout constants below.
- Produces:
  - `LEFT: str`, `RIGHT: str`
  - `window_rect() -> pygame.Rect`, `panel_rect(side: str) -> pygame.Rect`, `footer_rect() -> pygame.Rect`
  - `row_rect(side: str, index: int) -> pygame.Rect`
  - `panel_at(point: tuple[int, int]) -> str | None`
  - `hit_test(point: tuple[int, int]) -> tuple[str, int] | None`
  - `drag_amount(total: int, *, half: bool, one: bool) -> int`
  - `Drag(side: str, kind: ItemKind, count: int, pos: pygame.Vector2)`

- [ ] **Step 1: Add the layout constants**

In `src/game/config.py`, append at the end of the file:

```python
# --- Inventory window -------------------------------------------------------
# Two panels side by side, centred on screen: core on the left, backpack on the
# right, with a transfer progress strip underneath.
INV_PANEL_W: Final[int] = 300
INV_HEADER_H: Final[int] = 30  # capacity readout at the top of each panel
INV_ROW_H: Final[int] = 28
INV_ROWS: Final[int] = 8  # visible rows per panel
INV_PANEL_H: Final[int] = INV_HEADER_H + INV_ROWS * INV_ROW_H
INV_GAP: Final[int] = 12  # between the two panels
INV_FOOTER_H: Final[int] = 34
INV_ICON: Final[int] = 14
INV_FONT_SIZE: Final[int] = 16
INV_BG: Final[tuple[int, int, int]] = (18, 18, 28)
INV_PANEL_BG: Final[tuple[int, int, int]] = (34, 34, 50)
INV_ROW_BG: Final[tuple[int, int, int]] = (44, 44, 62)
INV_BORDER: Final[tuple[int, int, int]] = (90, 90, 120)
INV_TEXT: Final[tuple[int, int, int]] = (220, 220, 235)
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_inventory_panel.py`:

```python
import pygame

from game import config
from game.items.item_kinds import FRAGMENT
from game.ui import inventory_panel as panel


def test_window_holds_both_panels_and_the_footer():
    win = panel.window_rect()
    assert win.width == 2 * config.INV_PANEL_W + config.INV_GAP
    assert win.height == config.INV_PANEL_H + config.INV_FOOTER_H
    assert win.centerx == config.SCREEN_WIDTH // 2


def test_panels_do_not_overlap_and_left_is_the_core():
    left, right = panel.panel_rect(panel.LEFT), panel.panel_rect(panel.RIGHT)
    assert left.right + config.INV_GAP == right.left
    assert left.width == right.width == config.INV_PANEL_W


def test_footer_spans_the_window_below_the_panels():
    foot = panel.footer_rect()
    win = panel.window_rect()
    assert foot.width == win.width
    assert foot.top == panel.panel_rect(panel.LEFT).bottom


def test_rows_stack_below_the_header_inside_the_panel():
    p = panel.panel_rect(panel.LEFT)
    first = panel.row_rect(panel.LEFT, 0)
    second = panel.row_rect(panel.LEFT, 1)
    assert first.top >= p.top + config.INV_HEADER_H
    assert second.top - first.top == config.INV_ROW_H
    assert p.contains(panel.row_rect(panel.LEFT, config.INV_ROWS - 1))


def test_hit_test_finds_the_row_under_a_point():
    r = panel.row_rect(panel.RIGHT, 2)
    assert panel.hit_test(r.center) == (panel.RIGHT, 2)


def test_hit_test_misses_the_header():
    p = panel.panel_rect(panel.LEFT)
    assert panel.hit_test((p.centerx, p.top + 2)) is None


def test_hit_test_misses_outside_the_window():
    assert panel.hit_test((0, 0)) is None
    assert panel.hit_test((config.SCREEN_WIDTH - 1, config.SCREEN_HEIGHT - 1)) is None


def test_panel_at_reports_the_side_or_none():
    assert panel.panel_at(panel.panel_rect(panel.LEFT).center) == panel.LEFT
    assert panel.panel_at(panel.panel_rect(panel.RIGHT).center) == panel.RIGHT
    assert panel.panel_at((0, 0)) is None
    assert panel.panel_at(panel.footer_rect().center) is None  # footer is not a drop target


def test_drag_amount_defaults_to_everything():
    assert panel.drag_amount(9, half=False, one=False) == 9


def test_shift_takes_half_rounded_up():
    assert panel.drag_amount(9, half=True, one=False) == 5
    assert panel.drag_amount(8, half=True, one=False) == 4
    assert panel.drag_amount(1, half=True, one=False) == 1


def test_ctrl_takes_exactly_one_and_wins_over_shift():
    assert panel.drag_amount(9, half=False, one=True) == 1
    assert panel.drag_amount(9, half=True, one=True) == 1


def test_drag_amount_never_exceeds_the_stack():
    assert panel.drag_amount(0, half=False, one=True) == 0
    assert panel.drag_amount(0, half=True, one=False) == 0


def test_drag_carries_what_the_drop_needs():
    d = panel.Drag(side=panel.LEFT, kind=FRAGMENT, count=3, pos=pygame.Vector2(1, 2))
    assert (d.side, d.kind, d.count) == (panel.LEFT, FRAGMENT, 3)
```

Add to `tests/test_config.py`:

```python
def test_inventory_panel_height_matches_its_rows():
    assert config.INV_PANEL_H == config.INV_HEADER_H + config.INV_ROWS * config.INV_ROW_H
    win_w = 2 * config.INV_PANEL_W + config.INV_GAP
    assert win_w <= config.SCREEN_WIDTH
    assert config.INV_PANEL_H + config.INV_FOOTER_H <= config.SCREEN_HEIGHT
```

- [ ] **Step 3: Run to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_inventory_panel.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.ui'`

- [ ] **Step 4: Create the package**

Create `src/game/ui/__init__.py`:

```python
"""Screen-space widgets: layout, hit-testing and drawing for overlays.

Separate from ``systems/`` because everything here works in screen coordinates
and knows about the cursor. The geometry is pure, so it is tested without a
display; only the ``draw`` functions touch a surface.
"""
```

- [ ] **Step 5: Write the geometry**

Create `src/game/ui/inventory_panel.py`:

```python
"""The core-and-backpack window: where each row sits, and what the cursor hit.

Layout is computed from ``config`` every call rather than cached, so there is no
state to invalidate when the constants are tuned. The rects are cheap.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from game import config
from game.items.item_kinds import ItemKind

LEFT = "left"  # the core, /Documents
RIGHT = "right"  # the player's backpack

_ROW_INSET = 4  # horizontal padding of a row inside its panel


@dataclass
class Drag:
    """A stack lifted off a row and following the cursor."""

    side: str
    kind: ItemKind
    count: int
    pos: pygame.Vector2


def window_rect() -> pygame.Rect:
    width = 2 * config.INV_PANEL_W + config.INV_GAP
    height = config.INV_PANEL_H + config.INV_FOOTER_H
    return pygame.Rect(
        (config.SCREEN_WIDTH - width) // 2,
        (config.SCREEN_HEIGHT - height) // 2,
        width,
        height,
    )


def panel_rect(side: str) -> pygame.Rect:
    win = window_rect()
    x = win.left if side == LEFT else win.left + config.INV_PANEL_W + config.INV_GAP
    return pygame.Rect(x, win.top, config.INV_PANEL_W, config.INV_PANEL_H)


def footer_rect() -> pygame.Rect:
    win = window_rect()
    return pygame.Rect(
        win.left, win.top + config.INV_PANEL_H, win.width, config.INV_FOOTER_H
    )


def row_rect(side: str, index: int) -> pygame.Rect:
    panel = panel_rect(side)
    return pygame.Rect(
        panel.left + _ROW_INSET,
        panel.top + config.INV_HEADER_H + index * config.INV_ROW_H,
        config.INV_PANEL_W - 2 * _ROW_INSET,
        config.INV_ROW_H - 2,
    )


def panel_at(point: tuple[int, int]) -> str | None:
    """Which panel contains ``point``, if any. The footer is not a drop target."""
    for side in (LEFT, RIGHT):
        if panel_rect(side).collidepoint(point):
            return side
    return None


def hit_test(point: tuple[int, int]) -> tuple[str, int] | None:
    """``(side, row index)`` under ``point``, or None for the header/outside."""
    side = panel_at(point)
    if side is None:
        return None
    top = panel_rect(side).top + config.INV_HEADER_H
    index = (point[1] - top) // config.INV_ROW_H
    if index < 0 or index >= config.INV_ROWS:
        return None
    return side, int(index)


def drag_amount(total: int, *, half: bool, one: bool) -> int:
    """How much of a stack a modifier lifts. Ctrl beats Shift."""
    if one:
        return min(1, total)
    if half:
        return (total + 1) // 2  # round up, so 1 still moves
    return total
```

- [ ] **Step 6: Run the tests**

Run: `.venv/Scripts/pytest.exe tests/test_inventory_panel.py tests/test_config.py -v --no-cov`
Expected: 13 + 6 passed

- [ ] **Step 7: Full check**

Run: `.venv/Scripts/ruff.exe format . && .venv/Scripts/ruff.exe check . && .venv/Scripts/mypy.exe && .venv/Scripts/pytest.exe`
Expected: all green

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(ui): add inventory window geometry and drag arithmetic"
```

---

### Task 5: Text rendering and the panel painter

This is the game's first on-screen text. pygame's built-in font has no Hangul glyphs, so the item names would render as blank boxes — the helper looks for a system font that has them and falls back to the default when none is installed.

**Files:**
- Create: `src/game/ui/text.py`
- Modify: `src/game/ui/inventory_panel.py` (append `draw`)
- Test: `tests/test_ui_text.py`, `tests/test_inventory_panel.py` (append draw smoke tests)

**Interfaces:**
- Consumes: `Folder` (Task 2), `TransferJob` (Task 3), `Drag`/geometry (Task 4).
- Produces:
  - `text.font() -> pygame.font.Font` (cached)
  - `inventory_panel.draw(surface, *, documents: Folder, backpack: Folder, active: TransferJob | None, drag: Drag | None) -> None`

- [ ] **Step 1: Write the failing font test**

Create `tests/test_ui_text.py`:

```python
import pygame

from game.ui.text import font


def test_font_is_usable_and_cached():
    f = font()
    assert isinstance(f, pygame.font.Font)
    assert font() is f  # cached, not rebuilt every frame


def test_font_renders_korean_without_raising():
    surf = font().render("데이터 조각", True, (255, 255, 255))
    assert surf.get_width() > 0


def test_font_renders_ascii_and_digits():
    surf = font().render("123 / 750 MB", True, (255, 255, 255))
    assert surf.get_width() > 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_ui_text.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.ui.text'`

- [ ] **Step 3: Write the font helper**

Create `src/game/ui/text.py`:

```python
"""One shared UI font.

pygame's bundled default font has no Hangul glyphs, so item names would render
as empty boxes. Prefer a system font that covers them and fall back to the
default when none is installed — the fallback keeps the game running on a bare
CI box, it just draws the names badly.

Cached because building a Font is slow and this is called every frame.
"""

from __future__ import annotations

import pygame

from game import config

# First match wins. Malgun Gothic ships with Windows, the rest cover Linux/macOS.
_PREFERRED = "malgungothic,notosanscjkkr,notosanskr,applesdgothicneo,gulim,arialunicodems"

_font: pygame.font.Font | None = None


def font() -> pygame.font.Font:
    global _font
    if _font is None:
        path = pygame.font.match_font(_PREFERRED)
        _font = pygame.font.Font(path, config.INV_FONT_SIZE)
    return _font
```

- [ ] **Step 4: Run the font tests**

Run: `.venv/Scripts/pytest.exe tests/test_ui_text.py -v --no-cov`
Expected: 3 passed

- [ ] **Step 5: Write the failing draw tests**

Add to the imports at the top of `tests/test_inventory_panel.py`:

```python
from game.inventory.storage import Folder
from game.inventory.transfer import TransferJob
```

Then append:

```python
def _folders():
    core = Folder(cap_mb=config.DOCUMENTS_CAP_MB)
    bag = Folder(cap_mb=config.BACKPACK_CAP_MB)
    core.add(FRAGMENT, 41)
    bag.add(FRAGMENT, 9)
    return core, bag


def test_draw_runs_on_a_full_screen_surface():
    core, bag = _folders()
    surface = pygame.Surface(config.SCREEN_SIZE)
    panel.draw(surface, documents=core, backpack=bag, active=None, drag=None)


def test_draw_runs_with_a_job_and_a_drag():
    core, bag = _folders()
    surface = pygame.Surface(config.SCREEN_SIZE)
    job = TransferJob(kind=FRAGMENT, count=12, dst=core)
    job.elapsed = job.duration / 3
    drag = panel.Drag(side=panel.RIGHT, kind=FRAGMENT, count=4, pos=pygame.Vector2(400, 300))
    panel.draw(surface, documents=core, backpack=bag, active=job, drag=drag)


def test_draw_runs_on_empty_folders(surface):
    panel.draw(
        surface,
        documents=Folder(cap_mb=750),
        backpack=Folder(cap_mb=100),
        active=None,
        drag=None,
    )  # the 64x64 fixture surface: clipping must not raise
```

- [ ] **Step 6: Run to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_inventory_panel.py -v --no-cov`
Expected: FAIL — `AttributeError: module 'game.ui.inventory_panel' has no attribute 'draw'`

- [ ] **Step 7: Write the painter**

Append to `src/game/ui/inventory_panel.py` (and add the imports `from game.inventory.storage import Folder`, `from game.inventory.transfer import TransferJob`, `from game.ui.text import font` at the top):

```python
def _draw_panel(surface: pygame.Surface, side: str, folder: Folder, title: str) -> None:
    rect = panel_rect(side)
    pygame.draw.rect(surface, config.INV_PANEL_BG, rect)
    pygame.draw.rect(surface, config.INV_BORDER, rect, 1)

    glyphs = font()
    header = f"{title}   {folder.used_mb} / {folder.cap_mb} MB"
    surface.blit(glyphs.render(header, True, config.INV_TEXT), (rect.left + 8, rect.top + 7))

    for index, (kind, count) in enumerate(folder.rows()[: config.INV_ROWS]):
        row = row_rect(side, index)
        pygame.draw.rect(surface, config.INV_ROW_BG, row)
        icon = pygame.Rect(0, 0, config.INV_ICON, config.INV_ICON)
        icon.center = (row.left + 14, row.centery)
        pygame.draw.rect(surface, kind.color, icon)
        label = glyphs.render(kind.name, True, config.INV_TEXT)
        surface.blit(label, (row.left + 28, row.centery - label.get_height() // 2))
        amount = glyphs.render(f"×{count}", True, config.INV_TEXT)
        surface.blit(
            amount, (row.right - amount.get_width() - 8, row.centery - amount.get_height() // 2)
        )


def _draw_footer(surface: pygame.Surface, active: TransferJob | None) -> None:
    rect = footer_rect()
    pygame.draw.rect(surface, config.INV_BG, rect)
    pygame.draw.rect(surface, config.INV_BORDER, rect, 1)
    if active is None:
        return
    glyphs = font()
    label = glyphs.render(
        f"전송 중: {active.kind.name} ×{active.count}   {active.remaining:.1f}초",
        True,
        config.INV_TEXT,
    )
    surface.blit(label, (rect.left + 8, rect.centery - label.get_height() // 2))

    bar = pygame.Rect(rect.right - 168, rect.centery - 5, 160, 10)
    pygame.draw.rect(surface, config.INV_PANEL_BG, bar)
    filled = bar.copy()
    filled.width = int(bar.width * active.progress)
    pygame.draw.rect(surface, config.CORE_COLOR, filled)


def _draw_drag(surface: pygame.Surface, drag: Drag) -> None:
    glyphs = font()
    label = glyphs.render(f"{drag.kind.name} ×{drag.count}", True, config.INV_TEXT)
    box = label.get_rect()
    box.topleft = (int(drag.pos.x) + 12, int(drag.pos.y) + 12)
    pygame.draw.rect(surface, config.INV_ROW_BG, box.inflate(8, 6))
    surface.blit(label, box)


def draw(
    surface: pygame.Surface,
    *,
    documents: Folder,
    backpack: Folder,
    active: TransferJob | None,
    drag: Drag | None,
) -> None:
    """Paint the whole window. No state changes — the scene owns all of it."""
    pygame.draw.rect(surface, config.INV_BG, window_rect())
    _draw_panel(surface, LEFT, documents, "코어 /Documents")
    _draw_panel(surface, RIGHT, backpack, "백팩")
    _draw_footer(surface, active)
    if drag is not None:
        _draw_drag(surface, drag)
```

- [ ] **Step 8: Run the tests**

Run: `.venv/Scripts/pytest.exe tests/test_inventory_panel.py tests/test_ui_text.py -v --no-cov`
Expected: 16 + 3 passed

- [ ] **Step 9: Full check**

Run: `.venv/Scripts/ruff.exe format . && .venv/Scripts/ruff.exe check . && .venv/Scripts/mypy.exe && .venv/Scripts/pytest.exe`
Expected: all green

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat(ui): render the inventory window"
```

---

### Task 6: Open the window from the scene

`E` stops being an instant sync and starts opening the window. Player controls freeze; the world does not. The four sync tests written in the last commit are replaced here.

**Files:**
- Modify: `src/game/scenes/play.py` (imports, `__init__`, `handle_event`, `update`, `draw`)
- Test: `tests/test_play_scene.py:39-77` (replace the sync tests)

**Interfaces:**
- Consumes: `TransferQueue` (Task 3), `inventory_panel` (Tasks 4-5).
- Produces on `PlayScene`:
  - `inventory_open: bool`
  - `transfers: TransferQueue`
  - `_open_inventory() -> None`, `_close_inventory() -> None`

- [ ] **Step 1: Write the failing tests**

In `tests/test_play_scene.py`, delete the four tests at lines 39-77 (`test_standing_on_core_does_not_sync_by_itself` through `test_sync_key_is_consumed_after_one_step`) and put these in their place:

```python
def _at_core():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    return scene


def test_e_opens_the_window_at_the_core():
    scene = _at_core()
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.inventory_open is True


def test_e_does_nothing_out_of_range():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(1000, 1000)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    assert scene.inventory_open is False


def test_e_again_closes_the_window():
    scene = _at_core()
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)  # the toggle is latched, then consumed in update
    assert scene.inventory_open is False


def test_escape_closes_the_window_instead_of_leaving_the_scene():
    manager = SceneManager()
    scene = PlayScene()
    manager.push(scene)
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    scene.handle_event(_key_event(pygame.K_ESCAPE))
    assert scene.inventory_open is False
    assert manager.current is scene  # still in the game


def test_escape_still_leaves_the_scene_when_the_window_is_shut():
    manager = SceneManager()
    scene = PlayScene()
    manager.push(scene)
    scene.handle_event(_key_event(pygame.K_ESCAPE))
    assert manager.current is None


def test_standing_at_the_core_transfers_nothing_by_itself():
    scene = _at_core()
    scene.backpack.add(FRAGMENT, 3)
    scene.update(config.FIXED_DT)
    assert scene.backpack.count(FRAGMENT) == 3
    assert scene.documents.count(FRAGMENT) == 0


def test_open_window_blocks_movement_but_not_the_world():
    scene = _at_core()
    scene.handle_event(_key_event(pygame.K_e))
    scene.handle_event(_key_event(pygame.K_d))  # try to walk right
    start_x = scene.player.pos.x
    enemy = Virus(pos=pygame.Vector2(scene.player.pos.x + 400, scene.player.pos.y))
    scene.enemies.append(enemy)
    enemy_start_x = enemy.pos.x
    scene.update(config.FIXED_DT)
    assert scene.player.pos.x == start_x  # frozen
    assert enemy.pos.x < enemy_start_x  # the world kept moving


def test_open_window_blocks_firing():
    scene = _at_core()
    scene.handle_event(_key_event(pygame.K_e))
    scene.hotbar.select(1)  # weapon
    scene._mouse_held = True
    scene._mouse_screen = pygame.Vector2(0, 0)
    scene.update(config.FIXED_DT)
    assert scene.projectiles == []


def test_leaving_the_core_closes_the_window():
    scene = _at_core()
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    scene.player.pos = pygame.Vector2(1000, 1000)  # teleported out (knockback, later)
    scene.update(config.FIXED_DT)
    assert scene.inventory_open is False


def test_death_closes_the_window():
    scene = _at_core()
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    scene.player.hp = 0
    scene.update(config.FIXED_DT)
    assert scene.inventory_open is False


def test_transfers_keep_running_while_dead():
    scene = _at_core()
    scene.documents.add(FRAGMENT, 4)
    scene.transfers.enqueue(FRAGMENT, 4, src=scene.documents, dst=scene.backpack)
    scene.player.hp = 0
    scene.update(config.FIXED_DT)  # death step
    for _ in range(60):
        scene.update(config.FIXED_DT)
    assert scene.backpack.count(FRAGMENT) >= 1  # the job landed despite the respawn wait


def test_draw_runs_with_the_window_open(surface):
    scene = _at_core()
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    scene.draw(surface)
```

Add `from game.core.scene import SceneManager` to the imports at the top of the file.
`from game.items.item_kinds import FRAGMENT` should already be there from Task 2 — verify.

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_play_scene.py -v --no-cov`
Expected: FAIL — `AttributeError: 'PlayScene' object has no attribute 'inventory_open'`

- [ ] **Step 3: Wire the scene state**

In `src/game/scenes/play.py`:

Replace the module docstring's last clause and the imports block so it reads:

```python
"""Core-loop gameplay scene: mine fragments, fill the backpack, return to the
core and press E to open its storage window. Wires the entities and systems
together; accumulates input from events (no polling) and owns all rendering."""
```

Add to the imports:
```python
from game.inventory.transfer import TransferQueue
from game.ui import inventory_panel
```

Add below `_MOVE_KEYS` (line 26):
```python
# Tracked so drag modifiers work without polling pygame.key.get_mods().
_MOD_KEYS = {pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_LCTRL, pygame.K_RCTRL}
```

In `__init__`, replace `self._sync_pressed = False` (line 74) with:
```python
        self._toggle_inventory = False
        self.inventory_open = False
        self.transfers = TransferQueue()
```

- [ ] **Step 4: Route the input**

In `handle_event`, change the movement-key capture (line 84) to also latch modifiers:

```python
            if event.key in _MOVE_KEYS or event.key in _MOD_KEYS:
                self._held_keys.add(event.key)
```

Replace the `K_e` branch (lines 94-95) and the `K_ESCAPE` branch (lines 96-97):

```python
            elif event.key == pygame.K_e:
                self._toggle_inventory = True
            elif event.key == pygame.K_ESCAPE:
                if self.inventory_open:
                    self._close_inventory()
                elif self.manager is not None:
                    self.manager.pop()
```

Note the asymmetry: `E` is *latched* and consumed in `update` (like dodge — it has to
check the player's distance to the core, which is simulation state), while `ESC`
acts immediately (it needs no simulation state, and popping the scene already
worked this way). Tests must call `update` after pressing `E`, not after `ESC`.

- [ ] **Step 5: Wire the update loop**

The instant sync goes away here, so also delete `from game.items.item_kinds import FRAGMENT`
from the imports — nothing in `play.py` uses it any more and ruff will fail on F401.

Replace `update` (lines 120-172) with:

```python
    def update(self, dt: float) -> None:
        # consumed once per step whether or not we are dead, so a press during
        # the respawn wait cannot queue up an action for the frame we come back
        dodge = self._dodge_pressed
        toggle = self._toggle_inventory
        self._dodge_pressed = False
        self._toggle_inventory = False

        # in-flight cargo has already left its source folder: it must keep
        # moving through death, the respawn wait, and a closed window
        self.transfers.update(dt)

        if self._respawn_timer > 0:
            self._respawn_timer -= dt
            if self._respawn_timer <= 0:
                self.player.pos = pygame.Vector2(self.core.pos)
                self.player.hp = self.player.max_hp
                self.player.iframe_timer = config.RESPAWN_IFRAMES
            return

        if toggle:
            if self.inventory_open:
                self._close_inventory()
            elif self.core.is_in_sync_range(self.player.pos):
                self.inventory_open = True
        if self.inventory_open and not self.core.is_in_sync_range(self.player.pos):
            self._close_inventory()  # no remote looting

        busy = self.inventory_open  # cursor belongs to the UI, not the gun
        move = pygame.Vector2(0, 0) if busy else self._move_dir()
        held = self._mouse_held and not busy

        self.player.update(dt, move, config.WORLD_SIZE, dodge and not busy)
        self.camera.update(dt, self.player.pos, self._mouse_screen, held)
        aim_world = self.camera.screen_to_world(self._mouse_screen)

        tool = self.hotbar.active_tool
        mining.update_mining(
            dt,
            active_tool=tool,
            held=held,
            aim_world=aim_world,
            player_pos=self.player.pos,
            fragments=self.fragments,
            backpack=self.backpack,
        )
        self._fire_timer, shots = combat.fire_weapon(
            dt,
            weapon=tool,
            held=held,
            aim_world=aim_world,
            player_pos=self.player.pos,
            fire_timer=self._fire_timer,
        )
        self.projectiles.extend(shots)
        combat.update_projectiles(dt, self.projectiles, self.enemies, config.WORLD_SIZE)
        combat.update_enemies(dt, self.enemies, self.player, config.WORLD_SIZE)

        new_fragment = self.spawner.update(dt, self.fragments, self.core, self.rng)
        if new_fragment is not None and self.rng.random() < config.TROJAN_CHANCE:
            new_fragment.on_depleted = self._hatch_virus
        self.enemy_spawner.update(dt, self.enemies, self.player.pos, self.core, self.rng)

        if self.player.hp <= 0:
            self._close_inventory()
            combat.apply_death_penalty(self.backpack)
            self._respawn_timer = config.RESPAWN_DELAY

    def _close_inventory(self) -> None:
        self.inventory_open = False
```

(Task 7 gives `_close_inventory` a second job, which is why it is a method now.)

- [ ] **Step 6: Draw the overlay**

At the end of `draw`, replace the final `self._draw_hud(surface)` with:

```python
        self._draw_hud(surface)
        if self.inventory_open:
            inventory_panel.draw(
                surface,
                documents=self.documents,
                backpack=self.backpack,
                active=self.transfers.active,
                drag=None,  # Task 7 supplies the real drag
            )
```

- [ ] **Step 7: Run the tests**

Run: `.venv/Scripts/pytest.exe tests/test_play_scene.py -v --no-cov`
Expected: all pass. If `test_open_window_blocks_movement_but_not_the_world` fails on the enemy, check that `Virus.update` moves toward the player — the enemy is spawned 400px to the right, so its x must decrease.

- [ ] **Step 8: Full check**

Run: `.venv/Scripts/ruff.exe format . && .venv/Scripts/ruff.exe check . && .venv/Scripts/mypy.exe && .venv/Scripts/pytest.exe`
Expected: all green

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat(play): open the core storage window with E"
```

---

### Task 7: Drag and drop

The last piece: lift a row, drop it on the other panel, watch the bar fill.

**Files:**
- Modify: `src/game/scenes/play.py` (`handle_event`, `_close_inventory`, `draw`)
- Test: `tests/test_play_scene.py` (append)

**Interfaces:**
- Consumes: `inventory_panel.hit_test`, `.panel_at`, `.drag_amount`, `.Drag`, `.LEFT`, `.RIGHT`; `TransferQueue.enqueue`.
- Produces on `PlayScene`: `drag: Drag | None`, `_pick_up(point) -> None`, `_drop(point) -> None`.

- [ ] **Step 1: Write the failing tests**

Add `from game.ui import inventory_panel as panel` to the imports at the top of
`tests/test_play_scene.py`, then append:

```python
def _open_with_stock(core_n=0, bag_n=0):
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.documents.add(FRAGMENT, core_n)
    scene.backpack.add(FRAGMENT, bag_n)
    scene.handle_event(_key_event(pygame.K_e))
    scene.update(config.FIXED_DT)
    return scene


def _press(scene, point, button=1):
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button, pos=point))


def _release(scene, point, button=1):
    scene.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=button, pos=point))


def test_pressing_a_row_lifts_the_whole_stack():
    scene = _open_with_stock(bag_n=9)
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    assert scene.drag is not None
    assert scene.drag.count == 9
    assert scene.drag.side == panel.RIGHT


def test_shift_lifts_half():
    scene = _open_with_stock(bag_n=9)
    scene.handle_event(_key_event(pygame.K_LSHIFT))
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    assert scene.drag is not None
    assert scene.drag.count == 5


def test_ctrl_lifts_one():
    scene = _open_with_stock(bag_n=9)
    scene.handle_event(_key_event(pygame.K_LCTRL))
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    assert scene.drag is not None
    assert scene.drag.count == 1


def test_the_lifted_stack_follows_the_cursor():
    scene = _open_with_stock(bag_n=9)
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(300, 200)))
    assert scene.drag is not None
    assert scene.drag.pos == pygame.Vector2(300, 200)


def test_pressing_an_empty_row_lifts_nothing():
    scene = _open_with_stock(bag_n=9)
    _press(scene, panel.row_rect(panel.RIGHT, 3).center)  # below the only row
    assert scene.drag is None


def test_dropping_on_the_other_panel_starts_a_transfer():
    scene = _open_with_stock(bag_n=9)
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    _release(scene, panel.panel_rect(panel.LEFT).center)
    assert scene.drag is None
    assert scene.backpack.count(FRAGMENT) == 0  # left the source at once
    assert scene.documents.count(FRAGMENT) == 0  # in flight
    assert scene.transfers.active is not None


def test_the_transfer_lands_after_its_delay():
    scene = _open_with_stock(bag_n=9)
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    _release(scene, panel.panel_rect(panel.LEFT).center)
    steps = int(scene.transfers.active.duration / config.FIXED_DT) + 2
    for _ in range(steps):
        scene.update(config.FIXED_DT)
    assert scene.documents.count(FRAGMENT) == 9


def test_dropping_on_the_same_panel_does_nothing():
    scene = _open_with_stock(bag_n=9)
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    _release(scene, panel.row_rect(panel.RIGHT, 1).center)
    assert scene.drag is None
    assert scene.backpack.count(FRAGMENT) == 9
    assert scene.transfers.jobs == []


def test_dropping_outside_the_window_cancels():
    scene = _open_with_stock(bag_n=9)
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    _release(scene, (2, 2))
    assert scene.drag is None
    assert scene.backpack.count(FRAGMENT) == 9
    assert scene.transfers.jobs == []


def test_dragging_from_the_core_to_the_backpack_works_too():
    scene = _open_with_stock(core_n=5)
    _press(scene, panel.row_rect(panel.LEFT, 0).center)
    _release(scene, panel.panel_rect(panel.RIGHT).center)
    for _ in range(60):
        scene.update(config.FIXED_DT)
    assert scene.backpack.count(FRAGMENT) == 5


def test_a_drop_bigger_than_the_destination_moves_what_fits():
    scene = _open_with_stock(core_n=250)  # 750 MB, the core is full
    _press(scene, panel.row_rect(panel.LEFT, 0).center)
    _release(scene, panel.panel_rect(panel.RIGHT).center)
    assert scene.transfers.active is not None
    assert scene.transfers.active.count == 33  # 100 MB backpack / 3 MB each
    assert scene.documents.count(FRAGMENT) == 217  # the rest never left


def test_mining_cannot_steal_space_promised_to_an_inbound_transfer():
    scene = _open_with_stock(core_n=10)
    _press(scene, panel.row_rect(panel.LEFT, 0).center)
    _release(scene, panel.panel_rect(panel.RIGHT).center)
    assert scene.backpack.fits(FRAGMENT, 99) == 23  # 100 - 30 reserved
    scene.backpack.add(FRAGMENT, 99)  # simulate mining everything possible
    for _ in range(60):
        scene.update(config.FIXED_DT)
    assert scene.backpack.count(FRAGMENT) == 33  # nothing was lost


def test_closing_the_window_drops_a_held_stack_back_where_it_came_from():
    scene = _open_with_stock(bag_n=9)
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)  # lifted, not yet dropped
    assert scene.drag is not None
    scene.handle_event(_key_event(pygame.K_ESCAPE))
    assert scene.drag is None
    assert scene.backpack.count(FRAGMENT) == 9  # a lift never left the folder
    assert scene.transfers.jobs == []


def test_closing_the_window_does_not_cancel_a_queued_transfer():
    scene = _open_with_stock(bag_n=9)
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    _release(scene, panel.panel_rect(panel.LEFT).center)
    scene.handle_event(_key_event(pygame.K_ESCAPE))
    assert len(scene.transfers.jobs) == 1
    for _ in range(120):
        scene.update(config.FIXED_DT)
    assert scene.documents.count(FRAGMENT) == 9  # arrived with the window shut


def test_clicks_are_ignored_while_the_window_is_shut():
    scene = PlayScene()
    scene.player.pos = pygame.Vector2(scene.core.pos)
    scene.backpack.add(FRAGMENT, 9)
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    assert scene.drag is None
    assert scene._mouse_held is True  # it reaches the gun instead


def test_draw_runs_mid_drag(surface):
    scene = _open_with_stock(bag_n=9)
    _press(scene, panel.row_rect(panel.RIGHT, 0).center)
    scene.draw(surface)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/pytest.exe tests/test_play_scene.py -v --no-cov`
Expected: FAIL — `AttributeError: 'PlayScene' object has no attribute 'drag'`

- [ ] **Step 3: Add the drag state**

In `src/game/scenes/play.py`, add to `__init__` next to `self.transfers`:

```python
        self.drag: inventory_panel.Drag | None = None
```

- [ ] **Step 4: Intercept the mouse while the window is open**

In `handle_event`, replace the two mouse-button branches (lines 102-105) with:

```python
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.inventory_open:
                self._pick_up(event.pos)
            else:
                self._mouse_held = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.inventory_open:
                self._drop(event.pos)
            else:
                self._mouse_held = False
```

And in the `MOUSEMOTION` branch, keep the drag glued to the cursor:

```python
        elif event.type == pygame.MOUSEMOTION:
            self._mouse_screen = pygame.Vector2(event.pos)
            if self.drag is not None:
                self.drag.pos = pygame.Vector2(event.pos)
```

- [ ] **Step 5: Implement pick up and drop**

Add these methods to `PlayScene`, just above `_hatch_virus`:

```python
    # --- inventory window ------------------------------------------------
    def _folder(self, side: str) -> Folder:
        return self.documents if side == inventory_panel.LEFT else self.backpack

    def _pick_up(self, point: tuple[int, int]) -> None:
        hit = inventory_panel.hit_test(point)
        if hit is None:
            return
        side, index = hit
        rows = self._folder(side).rows()
        if index >= len(rows):
            return  # an empty line below the last row
        kind, total = rows[index]
        count = inventory_panel.drag_amount(
            total,
            half=bool(self._held_keys & {pygame.K_LSHIFT, pygame.K_RSHIFT}),
            one=bool(self._held_keys & {pygame.K_LCTRL, pygame.K_RCTRL}),
        )
        if count <= 0:
            return
        self.drag = inventory_panel.Drag(
            side=side, kind=kind, count=count, pos=pygame.Vector2(point)
        )

    def _drop(self, point: tuple[int, int]) -> None:
        drag, self.drag = self.drag, None
        if drag is None:
            return
        target = inventory_panel.panel_at(point)
        if target is None or target == drag.side:
            return  # dropped on empty space or back where it came from
        self.transfers.enqueue(
            drag.kind, drag.count, src=self._folder(drag.side), dst=self._folder(target)
        )
```

- [ ] **Step 6: Cancel the drag when the window closes**

Replace `_close_inventory`:

```python
    def _close_inventory(self) -> None:
        self.inventory_open = False
        self.drag = None  # a held stack is still in its folder, so just let go
```

- [ ] **Step 7: Feed the drag to the painter**

In `draw`, change `drag=None,` to `drag=self.drag,`.

- [ ] **Step 8: Run the tests**

Run: `.venv/Scripts/pytest.exe tests/test_play_scene.py -v --no-cov`
Expected: all pass

- [ ] **Step 9: Full check**

Run: `.venv/Scripts/ruff.exe format . && .venv/Scripts/ruff.exe check . && .venv/Scripts/mypy.exe && .venv/Scripts/pytest.exe`
Expected: all green

- [ ] **Step 10: Play it**

Run: `.venv/Scripts/python.exe -m game`

Check by hand, because none of this is caught by tests:
- Item names render as Hangul, not empty boxes. If they are boxes, no CJK font was found — check `pygame.font.match_font` in `ui/text.py`.
- Mine a few fragments, stand on the core, press `E`. The backpack row shows on the right.
- Drag it left. The row empties immediately, the footer bar fills, then the core row appears.
- Close with `E` mid-transfer, walk away, come back: the cargo arrived.
- `Esc` with the window open returns to the game, not to the menu.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "feat(play): drag stacks between the core and the backpack"
```

---

## Follow-ups this plan deliberately leaves open

- `TRANSFER_TIME_PER_MB = 0.02` is a first guess. Tune after playing with enemies near the core (spec A).
- `INV_ROWS = 8` caps the visible list. With one item kind it cannot overflow; scrolling waits until the catalogue grows.
- Spec A's core repair will call `documents.remove(FRAGMENT, n)` — the API it needs exists after Task 2.
- `SceneManager` still draws only the top scene. Spec C fixes that when a real pause screen needs it.
