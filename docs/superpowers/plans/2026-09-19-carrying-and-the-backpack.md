# 4단계: 소지품 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기본 인벤토리를 없애고 배낭을 유일한 저장소로 만든다. 핫바가 도구와 재료를 함께 담고, 슬롯 격자에서 옮길 수 있고, 죽으면 배낭이 짐 더미가 된다.

**Architecture:** 칸을 옮기는 규칙은 전부 순수 함수/메서드다 — pygame 표면을 만지지 않으므로 헤드리스로 테스트된다. 렌더링과 마우스 좌표→칸 변환만 `scenes/play.py`에 있다.

**Tech Stack:** pygame-ce, Python >= 3.10, pytest + pytest-cov, ruff, mypy (strict)

**Spec:** `docs/superpowers/specs/2026-08-29-world-rebuild-concept-design.md`

**선행:** 1~3단계 완료

## Global Constraints

- 로직은 순수 `update(dt, ...)`, 렌더링은 `draw(surface)`. `pygame.display` / 이벤트 펌프 / `pygame.quit`는 `core/app.py`에만.
- `config.py`는 pygame을 import하지 않는다.
- 고정 타임스텝 `FIXED_DT = 1/60`. 난수는 주입한다.
- TDD: 실패하는 테스트 → 최소 구현 → 리팩터.
- 명령어: `./.venv/Scripts/python.exe -m pytest` · `-m ruff check . && -m ruff format --check .` · `-m mypy`
- 각 작업의 마지막 단계는 커밋이다.

## 이 단계의 결정

**기본 인벤토리가 없다.** 아이템이 들어갈 곳은 배낭뿐, 배낭이 없으면 핫바 5칸이 전부다. 맨손으로 시작한다. 코어 파편은 스택 16이라 한 칸이면 점화에 충분하므로 오프닝이 성립한다.

**핫바가 도구와 재료를 함께 담는다.**

**주운 것은 배낭으로 간다. 배낭이 아예 없을 때만 핫바로 간다** — 배낭이 꽉 찼을 때가 아니라. 핫바 5칸은 죽음을 견디는 유일한 자리이므로, 게임이 멋대로 채우면 그 보호를 플레이어 대신 써버리는 셈이다.

## `Container`의 모델을 바꾼다

지금은 `dict[ItemKind, int]`이고 칸 수가 계산으로 나온다. 1단계에는 UI가 없어 그게 맞았지만, **격자에서 "3번 칸"을 집으려면 주소를 가진 칸 배열이 필요하다.** `slots: list[Stack | None]`로 바꾼다.

`reserved_slots`는 사라진다. "이동 중인 물건의 착지 공간"을 예약하는 장치였는데, 칸에 직접 넣고 빼는 모델에서는 옮기는 순간이 원자적이다.

## 범위 밖

- **제작** — 5단계. 그때까지 배낭은 세계에 하나 떨어뜨려 둔 임시 조치로 얻는다.
- **배낭 등급 사다리** — 표는 만들되 상위 배낭을 얻는 경로는 5단계다.
- **짐 더미 회수 UI** — 5단계. 4단계는 더미를 남기는 데까지.
- **스테미나·달리기**(5단계), **습격**(6단계).

## File Structure

| 파일 | 책임 |
|---|---|
| `inventory/stack.py` | **신규** `Stack` — 한 칸에 든 것 |
| `inventory/storage.py` | `Container`가 칸 배열이 된다 |
| `inventory/hotbar.py` | 도구와 `Stack`을 함께 담는다 |
| `inventory/packs.py` | **신규** 배낭 종류 표 |
| `inventory/grid.py` | **신규** 격자 화면의 순수 상태 |
| `systems/carrying.py` | **신규** 줍기 라우팅 |
| `entities/loot.py` | **신규** 짐 더미 |
| `systems/mining.py`, `combat.py` | 라우팅·죽음 추종 |
| `scenes/play.py` | 배낭 보유, 격자 UI, 짐 더미 |

---

### Task 1: 칸 배열이 된 `Container`

**Files:** Create `inventory/stack.py` · Modify `inventory/storage.py`, `config.py`, `scenes/play.py` · Test `tests/test_stack.py`(신규), `test_storage.py`(전면 교체), `test_config.py`, `test_mining.py`, `test_combat.py`, `test_play_scene.py`

**Produces:**
- `Stack(kind, count)` — 프로퍼티 `room`, `is_full`; 메서드 `merge(other) -> int`, `split(n) -> Stack`. 생성 시 `stack_max` 초과면 `ValueError`
- `Container` — 필드 `slots: list[Stack | None]`; `empty(size)`; 프로퍼티 `size`, `used`, `free`; 메서드 `count(kind)`, `fits(kind, n)`, `add(kind, n=1) -> int`, `remove(kind, n=1) -> int`, `take(index) -> Stack | None`, `put(index, stack) -> Stack | None`, `rows()`
- `config.INVENTORY_SLOTS`는 사라진다

**핵심 동작 — 테스트로 못박을 것:**
- `add`는 **열린 스택을 먼저 채우고** 빈 칸을 연다
- `remove`는 **뒤 칸부터 비운다** — 보고 있던 스택이 커서 밑에서 움직이지 않게
- `put`은 같은 종류면 합치고 남은 것을 돌려주고, 다른 종류면 **맞바꾼다**
- `fits`는 열린 스택의 여유 + 빈 칸 × `stack_max`

- [ ] **Step 1:** `tests/test_stack.py`를 쓴다 — room/is_full, merge가 옮긴 양을 반환하고 원본에서 빠짐, 다른 종류면 0, split이 있는 만큼만, 초과 생성은 `ValueError`
- [ ] **Step 2:** 실패 확인 (`ModuleNotFoundError`)
- [ ] **Step 3:** `Stack` 구현
- [ ] **Step 4:** `tests/test_storage.py`를 위 동작 전부로 다시 쓴다. `test_the_old_dict_model_is_gone`으로 `items`/`reserved_slots`/`slots_used`가 없음을 못박는다
- [ ] **Step 5:** `Container` 구현
- [ ] **Step 6:** 사용처 추종 — `config`에서 `INVENTORY_SLOTS` 삭제, `Container(slots=N)` → `Container.empty(N)`, `slots_used`→`used`, `free_slots`→`free`, `reserve`/`release` 테스트 삭제, `_draw_hud`의 게이지
- [ ] **Step 7:** 검증 4종 + 잔재 `grep -rn "INVENTORY_SLOTS\|slots_used\|free_slots\|reserved_slots"` → 없음
- [ ] **Step 8:** 커밋 `refactor(inventory): give the container addressable slots`

---

### Task 2: 핫바가 도구와 재료를 함께 담는다

**Files:** Modify `inventory/hotbar.py` · Test `tests/test_hotbar.py`

**Produces:** `Hotbar` 프로퍼티 `active_tool`(도구일 때만, 스택이면 `None`), `active_stack`(그 반대); 메서드 `count`, `add`, `remove`, `has_room_for(kind) -> bool`, `take(index)`, `put(index, held)`

한 칸은 **도구 / `Stack` / 없음** 중 하나다. `active_tool`과 `active_stack`이 각각 한쪽만 답하므로 부르는 쪽이 타입을 검사하지 않는다 — `mining`과 `combat`이 지금 `active_tool`을 쓰고 있어 그대로 동작한다.

**핵심 동작:**
- `add`는 **도구를 절대 밀어내지 않는다.** 열린 스택 → 빈 칸 순
- `has_room_for`는 넣어보지 않고 답한다 (`mining`이 캐기 전에 물어봐야 하므로)

- [ ] **Step 1:** 테스트 — 스택을 담으면 `active_tool`이 `None`, 도구 칸은 `active_stack`이 `None`, 도구가 있는 칸은 건드리지 않음, 열린 스택 먼저, 도구로 꽉 찬 핫바는 0, `has_room_for`가 빈 칸 없이도 열린 스택을 봄
- [ ] **Step 2:** 실패 확인 (`AttributeError: 'active_stack'`)
- [ ] **Step 3:** 구현 · **Step 4:** 검증 · **Step 5:** 커밋 `feat(inventory): let the hotbar hold materials as well as tools`

---

### Task 3: 배낭 — 유일한 저장소

**Files:** Create `inventory/packs.py`, `systems/carrying.py` · Modify `items/item_kinds.py`, `systems/mining.py`, `scenes/play.py` · Test `tests/test_packs.py`(신규), `test_carrying.py`(신규), `test_mining.py`, `test_play_scene.py`

**Produces:**
- 카탈로그에 `WORN_PACK`("낡은 배낭"), `LEATHER_PACK`("가죽 배낭") — 둘 다 **스택 1** (입는 것이지 쌓는 것이 아니다)
- `packs.PACK_SLOTS: dict[ItemKind, int]`, `packs.is_pack(kind)`, `packs.slots_of(kind)` — 보통 아이템은 0을 답한다
- `carrying.store(kind, n, backpack, hotbar) -> int`, `carrying.room_for(kind, backpack, hotbar) -> int`
- `mining.update_mining(...) -> tuple[str, ItemKind | None]` — 캔 종류를 함께 돌려준다. `backpack: Container | None`, `hotbar: Hotbar`를 받는다
- `PlayScene.backpack: Container | None` — 착용 전에는 `None`

`store`와 `room_for`는 **같은 분기를 쓴다.** "넣을 수 있다"고 해놓고 안 들어가는 버그가 구조적으로 불가능해야 한다.

```python
def store(kind, n, backpack, hotbar) -> int:
    if backpack is not None:
        return backpack.add(kind, n)
    return hotbar.add(kind, n)


def room_for(kind, backpack, hotbar) -> int:
    if backpack is not None:
        return backpack.fits(kind, 1)
    return 1 if hotbar.has_room_for(kind) else 0
```

**배낭은 캐낸 즉시 착용된다** — 담기는 물건이 아니라 담는 물건이므로 저장소를 거치지 않는다. 그래서 `update_mining`이 캔 종류를 돌려줘야 한다.

```python
    def _wear_if_pack(self, kind: ItemKind | None) -> None:
        """A pack is worn the moment it is dug up -- it is what holds things.

        A bigger one replaces a smaller one. Swapping without losing what was
        inside is the grid screen's job, in Task 5.
        """
        if kind is None or not packs.is_pack(kind):
            return
        if self.backpack is None or packs.slots_of(kind) > self.backpack.size:
            self.backpack = Container.empty(packs.slots_of(kind))
```

**파편을 셀 때 핫바도 세야 한다** — 배낭 없이 시작하므로 파편이 핫바에 있다. 씬에 `_carried(kind)`와 `_spend(kind, n)`(배낭 먼저, 그다음 핫바)를 두고 점화/저장고 블록을 그것으로 다시 쓴다.

**임시 배낭 하나를 세계에 둔다.** 제작은 5단계라 그때까지 얻을 길이 없다. `_scatter_starting_shards` 끝에 `WORN_PACK` 노드 하나. **5단계에서 제작으로 대체된다.**

- [ ] **Step 1:** `tests/test_packs.py` — 모든 팩이 카탈로그 행이고 스택 1, 크기 순 정렬, 보통 아이템은 팩이 아님
- [ ] **Step 1b:** `tests/test_carrying.py` — 배낭이 있으면 배낭으로, 없으면 핫바로, **배낭이 꽉 차면 핫바로 새지 않음**, 도구로 꽉 찬 핫바는 0, 부분 수량 보고, `room_for`가 `store`와 일치
- [ ] **Step 2:** 실패 확인 · **Step 3:** 아이템·표·라우팅 구현
- [ ] **Step 4:** `mining`을 라우팅에 연결 — 모든 `return X` → `return X, None`, 수확만 `return COLLECTED, target.kind`. 막는 조건은 `carrying.room_for(...) == 0`
- [ ] **Step 5:** 씬 배선 — `backpack=None` 시작, `_wear_if_pack`, `_carried`/`_spend`, 임시 배낭
- [ ] **Step 6:** 검증 · **Step 7:** 커밋 `feat(inventory): make the backpack the only place items go`

---

### Task 4: 죽음 — 배낭이 짐 더미가 된다

**Files:** Create `entities/loot.py` · Modify `systems/combat.py`, `scenes/play.py`, `config.py`, 스펙 문서 · Test `tests/test_combat.py`, `test_play_scene.py`

**Produces:**
- `LootPile(pos, contents: Container, pack: ItemKind | None)`
- `combat.apply_death_penalty(pos, backpack, worn) -> LootPile | None` — 핫바는 인자로 받지도 않는다
- `config.LOOT_RADIUS`, `config.LOOT_COLOR`
- `PlayScene.loot: LootPile | None`(한 번에 하나), `PlayScene.worn_pack: ItemKind | None`

**떨구는 양은 구현 전에 확정해야 한다.** 기본 인벤토리가 사라지면서 스펙의 "절반을 떨군다"가 갈 곳을 잃었다 — 모든 것이 배낭에 있으므로 배낭을 떨구면 100%가 나간다.

- **(가) 통째로 떨군다** — 회수하면 전부 돌아온다. 죽음의 비용은 회수 원정 그 자체
- **(나) 각 칸의 절반은 소멸하고 나머지가 더미에 들어간다** — 회수에 성공해도 절반은 영영 잃는다

`apply_death_penalty` 안의 한 줄 차이지만 게임의 무게가 다르다. 정해지면 **스펙의 죽음 절도 같은 내용으로 고친다.**

**정해진 것:** 핫바는 손대지 않는다. 짐 더미는 한 번에 하나이고, 회수 전에 또 죽으면 이전 것이 사라진다.

- [ ] **Step 1~6:** 결정 후 TDD, 스펙 동기화, 커밋 `feat(combat): drop the backpack into a loot pile on death`

---

### Task 5: 슬롯 격자 UI

**Files:** Create `inventory/grid.py` · Modify `scenes/play.py`, `config.py` · Test `tests/test_grid.py`(신규), `test_play_scene.py`

**Produces:** `grid.HOTBAR`, `grid.PACK`; `Grid(held: object | None)` — `click(where, index, backpack, hotbar)`, `close(backpack, hotbar)`. `config.GRID_COLS = 5`. `PlayScene`가 **I**로 연다

`Grid`는 **커서가 집어든 것만** 갖는다. 칸이 화면 어디에 그려지는지는 씬의 일이고, 이 클래스는 표면을 만지지 않는다 — 그래서 "여기 눌렀다 저기 눌렀다" 전체가 헤드리스로 테스트된다.

**핵심 동작:**
- 빈 손 + 찬 칸 → 집는다. 든 손 + 빈 칸 → 놓는다
- 같은 종류 위 → 합치고 남은 것은 손에 남는다. 다른 종류 위 → 맞바꿔서 손으로 온다
- **도구는 배낭에 못 들어간다** (핫바 칸끼리만 오간다)
- 배낭이 `None`이면 `PACK` 클릭은 아무 일도 없다
- **닫을 때 손에 든 것을 되돌려 놓는다** — 배낭 우선, 안 들어가면 핫바. 키 한 번에 물건을 잃는 건 누구도 내린 결정이 아니다

- [ ] **Step 1:** `tests/test_grid.py` — 위 동작 전부
- [ ] **Step 2:** 실패 확인 · **Step 3:** `Grid` 구현
- [ ] **Step 4:** 씬에 붙인다 — `I` 토글, 열려 있으면 이동·채굴·사격 정지(시계와 회복은 계속), 마우스 좌표→칸 변환, `_draw_grid`
- [ ] **Step 5:** 검증 · **Step 6:** 커밋 `feat(play): add the slot grid screen`

---

## 이 계획이 끝나면

배낭이 유일한 저장소가 되고, 핫바가 도구와 재료를 함께 담고, 격자에서 둘 사이를 옮길 수 있고, 죽으면 배낭이 짐 더미가 된다.

배낭을 **만드는** 방법은 아직 없다 — 세계에 하나 떨어뜨려 둔 임시 조치로 굴러간다. 5단계의 제작이 그 자리를 채운다.
