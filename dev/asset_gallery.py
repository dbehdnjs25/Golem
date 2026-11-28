"""Local asset library. Run with ``python dev/asset_gallery.py``.

A dev tool, not part of the game: nothing in ``src/game`` imports it.

Layout: folders on the left, a thumbnail grid in the middle, and the selected
asset's details on the right. Files that share a name (``tree.aseprite`` and
``tree.png``) are shown as one asset.

- Click selects and shows details; Ctrl+click adds, Shift+click selects a run.
- Double-click (or Enter) opens the Aseprite source.
- Right-click for open / show in Explorer / copy path / delete.
- Arrows move, Ctrl+A selects all shown, Delete sends to the Recycle Bin,
  Ctrl+F searches, Esc clears, F5 reloads. The list also reloads by itself
  the moment files change on disk, and a newly saved asset is selected.
- The left list is fixed categories (타일 / 나무 / 아이템 / 엔티티 / UI / 기타),
  not folders; ``categorize`` says which file goes where.

Badges: ASE / PNG / WEBP say which files exist. "갱신 필요" means the
exported image no longer matches the Aseprite source's first frame, so the
game is still drawing the old one (checked pixel by pixel in the background).
"게임" means the game's code names both the file and its folder, or a tileset
lists it -- a guess, but a good warning before deleting.
"""

from __future__ import annotations

import contextlib
import ctypes
import functools
import hashlib
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
import tkinter as tk
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT / "assets"
CODE = PROJECT / "src" / "game"
ASEPRITE = Path(os.environ.get("ASEPRITE", r"C:\Users\ykb62\Desktop\aseprite.exe"))
IMAGE_EXTS = (".png", ".webp", ".gif", ".jpg", ".bmp")
ALL_EXTS = (".aseprite", *IMAGE_EXTS)
REFRESH_MS = 3000
# Scrolling glides instead of jumping: every frame covers this share of the
# distance still to go, so a wheel notch eases out over roughly 0.2 s.
GLIDE_MS = 10
GLIDE_EASE = 0.25
ALL = "*"  # the tree row for every folder

SORTS = {
    "이름순": lambda e: (e.name.casefold(), e.folder),
    "폴더순": lambda e: (e.folder.casefold(), e.name.casefold()),
    "최근 수정순": lambda e: -e.mtime,
    "큰 이미지순": lambda e: -e.bytes,
}
FILTERS = ("전체", "갱신 필요", "Aseprite 원본만", "이미지만 (원본 없음)", "게임에서 사용")

# --- categories -----------------------------------------------------------------
# The left-hand list is not the folders on disk but these fixed categories, in
# this order. A row is the "/"-joined labels from the top, so "엔티티/골렘/늪지".
# An asset that matches a category but none of its children (a working file
# under trees/, the biome-less temple tiles) sits on the parent row itself.
BIOME_LABELS = ("초원", "사막", "불탄 숲", "바람 고원", "늪지", "설원")
ITEM_LABELS = ("도구", "광석", "주괴", "기타")
Node = tuple[str, tuple["Node", ...]]  # a label and the rows under it
CATEGORY_TREE: tuple[Node, ...] = (
    ("타일", tuple((b, ()) for b in BIOME_LABELS)),
    ("나무", tuple((b, ()) for b in BIOME_LABELS)),
    ("아이템", tuple((i, ()) for i in ITEM_LABELS)),
    ("엔티티", (("동물", ()), ("골렘", tuple((b, ()) for b in BIOME_LABELS)))),
    ("UI", ()),
    ("기타", ()),
)
# Folder and file name words that name a biome.
BIOME_WORDS = {
    "grassland": "초원",
    "desert": "사막",
    "wasteland": "사막",
    "burnt-forest": "불탄 숲",
    "burnt_forest": "불탄 숲",
    "wind_plateau": "바람 고원",
    "wind": "바람 고원",
    "bog": "늪지",
    "snowfield": "설원",
}
TILE_ROOTS = {"grassland", "desert", "burnt-forest", "wind_plateau", "bog", "snowfield", "temple"}


def _biome_of(parts: tuple[str, ...], name: str) -> str | None:
    """The biome named by a folder on the way, else by the start of the name."""
    for part in parts:
        if part in BIOME_WORDS:
            return BIOME_WORDS[part]
    for word, label in BIOME_WORDS.items():
        if name == word or name.startswith(word + "_"):
            return label
    return None


def _item_kind(name: str) -> str:
    if name.endswith(("_axe", "_pick", "_detector")) or name == "staff":
        return "도구"
    if name.endswith("_ore") or name == "stone" or name.endswith("_stone"):
        return "광석"
    if name.endswith("_ingot"):
        return "주괴"
    return "기타"


def categorize(rel: str) -> str:
    """Which row of the category list an asset (path under assets/, no
    extension) belongs on. New art lands in the right place by where it is
    saved: ``<biome>/tiles32/``, ``trees/<biome>``, ``resources/items/``,
    ``entities/animals/``, ``entities/golems/<biome>/`` (or ``<biome>_golem``),
    ``ui/``. Anything else is 기타."""
    parts = tuple(p.casefold() for p in rel.split("/"))
    folders, name = parts[:-1], parts[-1]
    top = folders[0] if folders else ""
    if top == "ui":
        return "UI"
    if top == "entities":
        if "golem" in name or any("golem" in p for p in folders):
            biome = _biome_of(folders[1:], name)
            return f"엔티티/골렘/{biome}" if biome else "엔티티/골렘"
        return "엔티티/동물"
    if top == "trees" or "tree" in name:
        biome = _biome_of(folders[1:], name) if top == "trees" else _biome_of(folders, name)
        return f"나무/{biome}" if biome else "나무"
    if top == "resources":
        return f"아이템/{_item_kind(name)}"
    if top in TILE_ROOTS and "tiles32" in folders:
        biome = _biome_of(folders, name)
        return f"타일/{biome}" if biome else "타일"
    return "기타"


def stand_in(category: str) -> str:
    """What the game draws once this category's art is deleted. The game
    treats a missing picture as "stop using it" (tests/test_floor.py holds it
    to that), so deleting here never stops it from running."""
    top = category.split("/")[0]
    return {
        "타일": "  · 타일 → 그 지역 색으로 칠한 바닥",
        "나무": "  · 나무 → 나무 아이템 그림, 그것도 없으면 색 동그라미",
        "아이템": "  · 아이템 → 색 네모(가방) · 색 동그라미(땅 위)",
    }.get(top, f"  · {top} → 그림 없이 단순한 모양")


def category_rows() -> list[tuple[str, int]]:
    """Every row of the fixed list, top to bottom: its path and its depth."""
    rows: list[tuple[str, int]] = []

    def walk(prefix: str, nodes: tuple[Node, ...], depth: int) -> None:
        for label, kids in nodes:
            path = f"{prefix}/{label}" if prefix else label
            rows.append((path, depth))
            walk(path, kids, depth + 1)

    walk("", CATEGORY_TREE, 1)
    return rows


# --- data ---------------------------------------------------------------------


@dataclass
class Asset:
    key: Path  # the shared path without its extension
    files: dict[str, Path] = field(default_factory=dict)
    mtimes: dict[str, float] = field(default_factory=dict)
    bytes: int = 0
    used: bool = False
    # Whether the exported image differs from the Aseprite source's first
    # frame, pixel for pixel. Unknown (False) until the background check runs.
    # Timestamps cannot answer this: a file restored from git or a backup
    # keeps whatever date it had, and looked out of date when it was not.
    stale: bool = False

    @property
    def name(self) -> str:
        return self.key.name

    @property
    def folder(self) -> str:
        parent = self.key.parent.relative_to(ROOT).as_posix()
        return "" if parent == "." else parent

    @property
    def rel(self) -> str:
        return self.key.relative_to(ROOT).as_posix()

    @property
    def category(self) -> str:
        return categorize(self.rel)

    @property
    def mtime(self) -> float:
        return max(self.mtimes.values())

    @property
    def image(self) -> Path | None:
        return next((self.files[e] for e in IMAGE_EXTS if e in self.files), None)

    @property
    def preview_source(self) -> Path:
        """What to draw: the exported image the game reads, else the source."""
        image = self.image
        return image if image is not None else self.files[".aseprite"]

    @property
    def pair(self) -> tuple[str, float, str, float] | None:
        """Source and export, with their dates, when both exist."""
        image = self.image
        if image is None or ".aseprite" not in self.files:
            return None
        source = self.files[".aseprite"]
        return (
            str(source),
            self.mtimes[".aseprite"],
            str(image),
            self.mtimes[image.suffix.lower()],
        )

    @property
    def stamp(self) -> tuple[str, float]:
        source = self.preview_source
        return str(source), self.mtimes[source.suffix.lower()]


def names_in_code() -> tuple[set[str], set[str]]:
    """What the game can reach: string literals in its code, and tileset files.

    Returns ``(words, tile_files)``. An asset counts as used when its name is
    one of the words AND so is the folder it sits in -- that is how the game
    builds paths (``_ROOT / "items" / f"{kind.key}.png"``) -- or when a
    tileset lists it by file name. The folder check keeps out the drafts and
    redraws that merely share a name with something in the game.
    """
    words: set[str] = set()
    literal = re.compile(r"""["']([^"'\n]{1,80})["']""")
    for path in CODE.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for word in literal.findall(text):
            clean = word.replace("\\", "/").casefold()
            words.add(clean)
            words.add(Path(clean).stem)
    tiles: set[str] = set()
    for path in ROOT.rglob("tileset.json"):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for word in literal.findall(text):
            tiles.add(f"{path.parent.as_posix()}/{word}".casefold())
    return words, tiles


def collect() -> list[Asset]:
    assets: dict[Path, Asset] = {}
    for path in ROOT.rglob("*"):
        ext = path.suffix.lower()
        if ext not in ALL_EXTS or not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            info = path.stat()
        except OSError:
            continue
        asset = assets.setdefault(path.with_suffix(""), Asset(path.with_suffix("")))
        asset.files[ext] = path
        asset.mtimes[ext] = info.st_mtime
        asset.bytes += info.st_size
    words, tiles = names_in_code()
    for asset in assets.values():
        runtime = [p for e, p in asset.files.items() if e in IMAGE_EXTS]
        by_code = asset.name.casefold() in words and asset.key.parent.name.casefold() in words
        by_tileset = any(p.as_posix().casefold() in tiles for p in runtime)
        asset.used = bool(runtime) and (by_code or by_tileset)
    return list(assets.values())


def signature() -> tuple[tuple[str, float], ...]:
    """Cheap fingerprint of the folder, to notice outside changes."""
    marks = []
    for path in ROOT.rglob("*"):
        if path.suffix.lower() in ALL_EXTS:
            with contextlib.suppress(OSError):
                marks.append((str(path), path.stat().st_mtime))
    return tuple(sorted(marks))


class FolderWatch:
    """Tells the library the moment anything under assets/ is created, renamed,
    deleted or saved -- so a new sprite shows up as soon as Aseprite writes it,
    not on the next 3-second check. Windows' change notification does the
    waiting on a background thread; the window only reads a timestamp."""

    FLAGS = 0x1 | 0x2 | 0x10  # file name, folder name, last write

    def __init__(self, root: Path) -> None:
        self.root = root
        self.last_change = 0.0  # monotonic time of the latest notice; 0 = none
        self.alive = False  # while True, the slow 3-second scan is not needed
        if os.name == "nt":
            threading.Thread(target=self._work, daemon=True).start()

    def _work(self) -> None:
        kernel = ctypes.windll.kernel32
        kernel.FindFirstChangeNotificationW.restype = wintypes.HANDLE
        handle = kernel.FindFirstChangeNotificationW(str(self.root), True, self.FLAGS)
        if handle in (None, wintypes.HANDLE(-1).value):
            return  # the 3-second check still covers it
        self.alive = True
        try:
            while kernel.WaitForSingleObject(handle, 0xFFFFFFFF) == 0:
                self.last_change = time.monotonic()
                if not kernel.FindNextChangeNotification(handle):
                    return
        finally:
            self.alive = False
            kernel.FindCloseChangeNotification(handle)

    def settled(self, quiet: float = 0.25) -> bool:
        """A change arrived and nothing more for ``quiet`` seconds: a save that
        writes the source and then its PNG is read once, after both."""
        changed = self.last_change
        if changed and time.monotonic() - changed >= quiet:
            self.last_change = 0.0 if self.last_change == changed else self.last_change
            return True
        return False


def glide_step(now: float, goal: float) -> int:
    """One frame of easing from ``now`` toward ``goal``, in whole pixels so the
    cards never land between pixels. Always moves at least one pixel."""
    target = round(goal)
    gap = target - now
    if abs(gap) <= 1:
        return target
    step = gap * GLIDE_EASE
    return round(now + (step if abs(step) >= 1 else (1 if gap > 0 else -1)))


def recycle_file(path: Path) -> None:
    """Move one validated asset to the Windows Recycle Bin."""
    path = path.resolve(strict=True)
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError(f"에셋 폴더 밖의 파일은 삭제할 수 없습니다: {path}")

    class FileOperation(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", wintypes.WORD),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    operation = FileOperation()
    names = ctypes.create_unicode_buffer(str(path) + "\0\0")
    operation.wFunc = 3  # FO_DELETE
    operation.pFrom = ctypes.cast(names, wintypes.LPCWSTR)
    operation.fFlags = 0x40 | 0x10 | 0x4 | 0x400  # undo, no confirm, silent, no error UI
    shell = ctypes.windll.shell32.SHFileOperationW
    shell.argtypes = [ctypes.POINTER(FileOperation)]
    shell.restype = ctypes.c_int
    result = shell(ctypes.byref(operation))
    if result or operation.fAnyOperationsAborted or path.exists():
        raise OSError(f"휴지통 이동 실패 ({result}): {path.name}")


# --- background image loading ----------------------------------------------------


class Loader:
    """Decodes images (and exports Aseprite files) off the UI thread."""

    def __init__(self) -> None:
        self.cache = Path(tempfile.gettempdir()) / "pygame-asset-gallery"
        self.cache.mkdir(exist_ok=True)
        self.requests: queue.LifoQueue[tuple[str, float]] = queue.LifoQueue()
        self.results: queue.Queue[tuple[tuple[str, float], Image.Image | str]] = queue.Queue()
        self.asked: set[tuple[str, float]] = set()
        self.compares: queue.Queue[tuple[str, float, str, float]] = queue.Queue()
        self.compared: queue.Queue[tuple[tuple[str, float, str, float], bool]] = queue.Queue()
        self.compare_asked: set[tuple[str, float, str, float]] = set()
        for _ in range(3):
            threading.Thread(target=self._work, daemon=True).start()
        threading.Thread(target=self._compare_work, daemon=True).start()

    def compare(self, pair: tuple[str, float, str, float]) -> None:
        if pair not in self.compare_asked:
            self.compare_asked.add(pair)
            self.compares.put(pair)

    def _compare_work(self) -> None:
        while True:
            pair = self.compares.get()
            source, source_time, image, image_time = pair
            try:
                drawn = self._decode(Path(source), source_time)
                exported = self._decode(Path(image), image_time)
                # A different size is a scaled export (trees are drawn at half
                # size and doubled), not an out-of-date one: not flagged.
                differs = drawn.size == exported.size and drawn.tobytes() != exported.tobytes()
            except Exception:
                differs = False  # cannot tell -- do not cry wolf
            self.compared.put((pair, differs))

    def ask(self, stamp: tuple[str, float]) -> None:
        if stamp not in self.asked:
            self.asked.add(stamp)
            self.requests.put(stamp)  # LIFO: what scrolled into view last goes first

    def forget(self) -> None:
        self.asked.clear()

    def _work(self) -> None:
        while True:
            stamp = self.requests.get()
            try:
                self.results.put((stamp, self._decode(Path(stamp[0]), stamp[1])))
            except Exception as error:  # shown on the card, never raised
                self.results.put((stamp, str(error) or type(error).__name__))

    def _decode(self, path: Path, mtime: float) -> Image.Image:
        if path.suffix.lower() == ".aseprite":
            digest = hashlib.sha1(f"{path}|{mtime}".encode()).hexdigest()[:16]
            out = self.cache / f"{digest}.png"
            if not out.exists():
                if not ASEPRITE.exists():
                    raise FileNotFoundError("Aseprite 실행 파일 없음")
                subprocess.run(
                    [
                        str(ASEPRITE),
                        "--batch",
                        "--frame-range",
                        "0,0",
                        str(path),
                        "--save-as",
                        str(out),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=60,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            path = out
        with Image.open(path) as opened:
            return opened.convert("RGBA")


def checker(width: int, height: int, cell: int, dark: str, light: str) -> Image.Image:
    board = Image.new("RGBA", (width, height), dark)
    draw = ImageDraw.Draw(board)
    for y in range(0, height, cell):
        for x in range(0, width, cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=light)
    return board


def fit(image: Image.Image, width: int, height: int, scale: float | None = None) -> Image.Image:
    """Scale to fit (or by ``scale``): crisp when enlarging, smooth when shrinking."""
    if scale is None:
        scale = min(width / image.width, height / image.height)
        if scale >= 1:
            scale = max(1, int(scale))  # whole steps keep every pixel the same size
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    method = Image.Resampling.NEAREST if scale >= 1 else Image.Resampling.LANCZOS
    return image.resize(size, method)


# --- drawing helpers: rounded glass in greys ---------------------------------------

TEXT = "#ededf0"
MUTED = "#8e8e96"
FAINT = "#5c5c64"
INK = "#121214"  # dark text on the light, filled pills
STAGE = "#0b0b0d"
BASE = (11, 11, 13)
FONT = "Malgun Gothic"
# The same face as files, for text baked into card images.
FONT_FILES = {"normal": "malgun.ttf", "bold": "malgunbd.ttf"}
MENU = {
    "bg": "#1c1c1f",
    "fg": TEXT,
    "activebackground": "#3a3a40",
    "activeforeground": TEXT,
    "bd": 0,
    "relief": "flat",
}


def white(alpha: int) -> tuple[int, int, int, int]:
    return (255, 255, 255, alpha)


def rounded(
    w: int,
    h: int,
    r: int,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] | None = None,
    width: int = 1,
) -> Image.Image:
    """An antialiased rounded rectangle: drawn at 3x, then shrunk."""
    ss = 3
    big = Image.new("RGBA", (max(1, w) * ss, max(1, h) * ss), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, max(1, w) * ss - 1, max(1, h) * ss - 1),
        radius=r * ss,
        fill=fill,
        outline=outline,
        width=width * ss if outline else 0,
    )
    return big.resize((max(1, w), max(1, h)), Image.Resampling.LANCZOS)


# The same few shapes are drawn over and over (every card frame, badge and
# thumbnail corner); each costs ~7 ms to supersample, so keep them. Callers
# must not draw on what these return -- copy first.
shape = functools.lru_cache(maxsize=512)(rounded)


@functools.lru_cache(maxsize=64)
def round_mask(w: int, h: int, r: int) -> Image.Image:
    return rounded(w, h, r, white(255)).getchannel("A")


def backdrop(w: int, h: int) -> Image.Image:
    """The dark stage behind the glass: a few soft grey glows and a little grain."""
    sw, sh = max(8, w // 6), max(8, h // 6)
    small = Image.new("RGB", (sw, sh), BASE)
    draw = ImageDraw.Draw(small)
    side = max(sw, sh)
    for fx, fy, fr, v in (
        (0.10, 0.15, 0.30, 74),
        (0.80, 0.10, 0.26, 58),
        (0.62, 0.82, 0.36, 52),
        (0.15, 0.90, 0.20, 40),
        (0.45, 0.42, 0.16, 34),
    ):
        r = fr * side
        draw.ellipse((fx * sw - r, fy * sh - r, fx * sw + r, fy * sh + r), fill=(v, v, v))
    small = small.filter(ImageFilter.GaussianBlur(side * 0.09))
    big = small.resize((w, h), Image.Resampling.BICUBIC)
    grain = Image.effect_noise((w, h), 18).convert("RGB")
    return Image.blend(big, grain, 0.025)


def glass(back: Image.Image, box: tuple[int, int, int, int], r: int) -> Image.Image:
    """Frosted glass over ``box`` of the backdrop: blurred, lifted, edged.

    The corners outside the radius stay plain backdrop, so the panel reads as
    rounded although Tk can only place rectangles.
    """
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    pad = 40
    outer = (
        max(0, x0 - pad),
        max(0, y0 - pad),
        min(back.width, x1 + pad),
        min(back.height, y1 + pad),
    )
    blurred = back.crop(outer).filter(ImageFilter.GaussianBlur(22))
    blurred = blurred.crop((x0 - outer[0], y0 - outer[1], x0 - outer[0] + w, y0 - outer[1] + h))
    pane = Image.alpha_composite(blurred.convert("RGBA"), rounded(w, h, r, white(15), white(34)))
    # A faint sheen down from the top edge, as light catching the glass.
    sheen = Image.linear_gradient("L").resize((w, h)).point(lambda v: max(0, 14 - v // 9))
    shine = Image.new("RGBA", (w, h), white(0))
    shine.putalpha(sheen)
    pane = Image.alpha_composite(pane, shine)
    out = back.crop(box).convert("RGBA")
    out.paste(pane, (0, 0), round_mask(w, h, r))
    return out.convert("RGB")


PILL = {
    # name: (fill, outline, hover fill, text colour)
    "glass": (white(16), white(38), white(32), TEXT),
    "on": (white(56), white(110), white(70), TEXT),
    "primary": ((236, 236, 240, 240), None, (255, 255, 255, 255), INK),
    "danger": (white(26), white(150), white(44), TEXT),
    "off": (white(7), white(18), white(7), FAINT),
}


# Zoom steps for the preview. Below 1x anything goes; from 1x up only whole
# numbers, so every pixel of the art stays the same size on screen.
LADDER = sorted(
    {round(0.05 * 1.25**k, 4) for k in range(14) if 0.05 * 1.25**k < 1}
    | {1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64}
)


# --- the window ----------------------------------------------------------------


class Gallery:
    def __init__(self, window: tk.Tk) -> None:
        self.window = window
        self.ui = window.winfo_fpixels("1i") / 96  # 1.0 at 100% Windows scaling
        self.loader = Loader()
        self.folder_watch = FolderWatch(ROOT)
        self.assets: list[Asset] = []
        self.shown: list[Asset] = []
        self.images: dict[tuple[str, float], Image.Image | str] = {}
        self.thumbs: dict[tuple[tuple[str, float], int], Image.Image] = {}
        # Whole cards, pre-rendered: one image per card is what lets the grid
        # scroll smoothly (Tk repaints ~11 items per card far more slowly).
        self.card_photos: dict[tuple[object, ...], ImageTk.PhotoImage] = {}
        self.pil_fonts: dict[tuple[int, str], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
        self.photos: dict[tuple[object, ...], ImageTk.PhotoImage] = {}
        self.fonts: dict[tuple[int, str], tkfont.Font] = {}
        self.differs: dict[tuple[str, float, str, float], bool] = {}
        self.selected: set[Path] = set()
        self.anchor: int | None = None
        self.focus: int | None = None
        self.hover: int | None = None
        self.side_hover: int | None = None
        self.folder = ALL
        # The top level starts open; the rows below it start folded.
        self.expanded: set[str] = {ALL} | {label for label, _ in CATEGORY_TREE}
        self.counts: dict[str, int] = {}
        self.rows: list[tuple[str, int, bool]] = []  # folder path, depth, has children
        self.filter = FILTERS[0]
        self.sort = "폴더순"
        # The preview's own view: a scale (None = fit the box) and the art
        # pixel at the box's centre (None = the art's centre). Reset whenever
        # a different asset is shown.
        self.view_scale: float | None = None
        self.view_center: tuple[float, float] | None = None
        self.view_key: tuple[str, float] | None = None
        self.preview_box = (0, 0, 0, 0)
        self.pan_from: tuple[int, int, float, float] | None = None
        self.backing = "체크"
        self.size = 128
        # What is on screen (whole pixels) and where it is gliding to.
        self.scroll_y = 0.0
        self.scroll_goal = 0.0
        self.side_y = 0.0
        self.side_goal = 0.0
        self.glide_pending: str | None = None
        self.side_glide_pending: str | None = None
        self.drawn_rows: set[int] = set()  # grid rows whose cards are on the canvas
        self.card_items: dict[int, int] = {}  # shown index -> its canvas image
        self.drag_from: tuple[float, float] | None = None
        self.columns = 1
        self.cell = (1, 1)
        self.card = (1, 1)
        self.flash = ""
        self.flash_until = 0.0
        self.last_signature: tuple[tuple[str, float], ...] = ()
        self.detail_photo: ImageTk.PhotoImage | None = None
        self.bg: dict[str, ImageTk.PhotoImage] = {}
        self.layout_pending: str | None = None
        self.draw_pending: str | None = None
        self.size_seen = (0, 0)

        window.title("에셋 라이브러리 · Pygame Project")
        window.geometry(f"{self.px(1500)}x{self.px(940)}")
        window.minsize(self.px(980), self.px(600))
        window.configure(bg=STAGE)
        self.stage = tk.Canvas(window, bg=STAGE, highlightthickness=0, bd=0)
        self.stage.place(x=0, y=0, relwidth=1, relheight=1)
        self.panes = {
            name: tk.Canvas(window, bg=STAGE, highlightthickness=0, bd=0)
            for name in ("top", "side", "grid", "detail", "bottom")
        }
        self.query = tk.StringVar()
        self.entry = tk.Entry(
            self.panes["top"],
            textvariable=self.query,
            relief="flat",
            bd=0,
            fg=TEXT,
            insertbackground=TEXT,
            font=(FONT, 10),
            highlightthickness=0,
        )
        self._placeholder("이름 또는 경로 검색   Ctrl+F")
        self.query.trace_add("write", lambda *_: self._refilter())
        self._bind()
        self.reload()
        window.after(50, self._poll_images)
        window.after(REFRESH_MS, self._watch)

    # --- small utilities -------------------------------------------------------
    def px(self, n: float) -> int:
        return int(round(n * self.ui))

    def font(self, size: int, weight: str = "normal") -> tkfont.Font:
        key = (size, weight)
        if key not in self.fonts:
            self.fonts[key] = tkfont.Font(family=FONT, size=size, weight=weight)
        return self.fonts[key]

    def pil_font(
        self, size: int, weight: str = "normal"
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        """The PIL twin of ``font``: same face, same size in pixels."""
        key = (size, weight)
        if key not in self.pil_fonts:
            px = max(1, round(size * self.ui * 96 / 72))
            try:
                self.pil_fonts[key] = ImageFont.truetype(FONT_FILES[weight], px)
            except OSError:
                self.pil_fonts[key] = ImageFont.load_default()
        return self.pil_fonts[key]

    @staticmethod
    def fit_pil(text: str, width: int, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> str:
        """``fit_text`` for baked text: one line, cut from the front."""
        if font.getlength(text) <= width:
            return text
        while text and font.getlength("…" + text) > width:
            text = text[1:]
        return "…" + text

    def photo(self, key: tuple[object, ...], build) -> ImageTk.PhotoImage:  # type: ignore[no-untyped-def]
        """A cached Tk image. The cache also keeps it alive -- Tk does not."""
        if key not in self.photos:
            self.photos[key] = ImageTk.PhotoImage(build())
        return self.photos[key]

    def fit_text(self, text: str, width: int, font: tkfont.Font) -> str:
        """One line, cut from the FRONT: the end of a path is the telling part."""
        if font.measure(text) <= width:
            return text
        while text and font.measure("…" + text) > width:
            text = text[1:]
        return "…" + text

    def _typing(self, event: tk.Event) -> bool:
        return isinstance(event.widget, tk.Entry)

    # --- the search box hint (Tk has none) ---------------------------------------
    def _placeholder(self, hint: str) -> None:
        self._hint = hint
        self._hint_on = False

        def show(_: object = None) -> None:
            if not self.query.get() and self.window.focus_get() is not self.entry:
                self._hint_on = True
                self.entry.configure(fg=FAINT)
                self.entry.delete(0, "end")
                self.entry.insert(0, hint)

        def hide(_: object = None) -> None:
            if self._hint_on:
                self._hint_on = False
                self.entry.delete(0, "end")
                self.entry.configure(fg=TEXT)

        self.entry.bind("<FocusIn>", hide)
        self.entry.bind("<FocusOut>", show)
        self.window.after(10, show)

    def _search_text(self) -> str:
        return "" if self._hint_on else self.query.get().strip().casefold()

    # --- input wiring ------------------------------------------------------------
    def _bind(self) -> None:
        w = self.window
        w.bind("<Configure>", self._on_configure)
        w.bind("<Control-f>", lambda _: (self.entry.focus_set(), "break")[1])
        w.bind("<F5>", lambda _: self.reload())
        w.bind("<Escape>", self._escape)
        w.bind("<Left>", lambda e: self._arrow(e, -1))
        w.bind("<Right>", lambda e: self._arrow(e, 1))
        w.bind("<Up>", lambda e: self._arrow(e, -self.columns))
        w.bind("<Down>", lambda e: self._arrow(e, self.columns))
        w.bind("<Control-a>", self._select_all_key)
        w.bind("<Delete>", self._delete_key)
        w.bind("<Return>", self._enter_key)
        grid = self.panes["grid"]
        grid.bind("<Button-1>", self._grid_press)
        grid.bind("<B1-Motion>", self._grid_drag)
        grid.bind("<ButtonRelease-1>", lambda _: setattr(self, "drag_from", None))
        grid.bind("<Double-Button-1>", self._double)
        grid.bind("<Button-3>", self._context)
        grid.bind("<Motion>", self._grid_motion)
        grid.bind("<Leave>", lambda _: self._set_hover(None))
        grid.bind("<MouseWheel>", self._grid_wheel)
        side = self.panes["side"]
        side.bind("<Button-1>", self._side_click)
        side.bind("<Motion>", self._side_motion)
        side.bind("<Leave>", lambda _: self._side_hover(None))
        side.bind("<MouseWheel>", self._side_wheel)
        detail = self.panes["detail"]
        detail.bind("<MouseWheel>", self._preview_wheel)
        detail.bind("<ButtonPress-1>", self._preview_press)
        detail.bind("<B1-Motion>", self._preview_drag)
        detail.bind("<ButtonRelease-1>", lambda _: setattr(self, "pan_from", None))
        detail.bind("<Double-Button-1>", self._preview_reset)
        detail.bind("<Motion>", self._preview_cursor)

    def _on_configure(self, event: tk.Event) -> None:
        if event.widget is not self.window:
            return
        size = (self.window.winfo_width(), self.window.winfo_height())
        if size == self.size_seen:
            return
        self.size_seen = size
        if self.layout_pending:
            self.window.after_cancel(self.layout_pending)
        self.layout_pending = self.window.after(90, self._layout)

    # --- layout: where the panes sit, and their glass ---------------------------------
    def _boxes(self) -> dict[str, tuple[int, int, int, int]]:
        W, H = self.size_seen
        p = self.px(14)
        top_h, bot_h = self.px(64), self.px(54)
        side_w, det_w = self.px(240), self.px(364)
        y0 = p + top_h + p
        y1 = H - p - bot_h - p
        return {
            "top": (p, p, W - p, p + top_h),
            "bottom": (p, H - p - bot_h, W - p, H - p),
            "side": (p, y0, p + side_w, y1),
            "detail": (W - p - det_w, y0, W - p, y1),
            "grid": (p + side_w + p, y0, W - p - det_w - p, y1),
        }

    def _search_box(self) -> tuple[int, int, int, int]:
        h = self.px(38)
        x = self.px(20) + self.font(15, "bold").measure("에셋 라이브러리") + self.px(26)
        y = (self.px(64) - h) // 2
        return x, y, x + self.px(330), y + h

    def _layout(self) -> None:
        self.layout_pending = None
        W, H = self.size_seen
        if W < 50 or H < 50:
            return
        back = backdrop(W, H)
        self.bg["stage"] = ImageTk.PhotoImage(back)
        self.stage.delete("all")
        self.stage.create_image(0, 0, anchor="nw", image=self.bg["stage"])
        self.bg_images: dict[str, Image.Image] = {}
        for name, box in self._boxes().items():
            x0, y0, x1, y1 = box
            pane = self.panes[name]
            pane.place(x=x0, y=y0, width=x1 - x0, height=y1 - y0)
            image = glass(back, box, self.px(20))
            if name == "top":
                image = self._inset_search(image)
            self.bg_images[name] = image
            self.bg[name] = ImageTk.PhotoImage(image)
            pane.delete("bg")
            pane.create_image(0, 0, anchor="nw", image=self.bg[name], tags="bg")
            pane.tag_lower("bg")
        self._masks()
        self.draw_all()

    def _inset_search(self, image: Image.Image) -> Image.Image:
        """Sink the search field into the top bar, and colour the Entry to match."""
        x0, y0, x1, y1 = self._search_box()
        field = rounded(x1 - x0, y1 - y0, (y1 - y0) // 2, (0, 0, 0, 150), white(30))
        out = image.convert("RGBA")
        out.alpha_composite(field, (x0, y0))
        r, g, b, _ = out.getpixel(((x0 + x1) // 2, (y0 + y1) // 2))
        self.entry.configure(bg=f"#{r:02x}{g:02x}{b:02x}")
        self.entry.place(
            x=x0 + self.px(16),
            y=y0 + self.px(8),
            width=x1 - x0 - self.px(30),
            height=y1 - y0 - self.px(16),
        )
        return out.convert("RGB")

    def _masks(self) -> None:
        """Strips of each scrolling pane's own glass, laid over what scrolls past.

        A Tk canvas cannot clip, so cards scrolling off the top would cover
        the rounded edge. These put the edge back on top of them.
        """
        self.mask_h = {"grid": (self.px(14), self.px(14)), "side": (self.px(50), self.px(12))}
        for name, (top, bottom) in self.mask_h.items():
            image = self.bg_images[name]
            w, h = image.size
            self.bg[f"{name}-top"] = ImageTk.PhotoImage(image.crop((0, 0, w, top)))
            self.bg[f"{name}-bottom"] = ImageTk.PhotoImage(image.crop((0, h - bottom, w, h)))

    def _lay_masks(self, name: str) -> None:
        pane = self.panes[name]
        h = pane.winfo_height()
        _, bottom = self.mask_h[name]
        tags = ("content", "mask")
        pane.create_image(0, 0, anchor="nw", image=self.bg[f"{name}-top"], tags=tags)
        pane.create_image(0, h - bottom, anchor="nw", image=self.bg[f"{name}-bottom"], tags=tags)

    def draw_all(self) -> None:
        if not hasattr(self, "bg_images"):
            return
        self.draw_top()
        self.draw_side()
        self.draw_grid()
        self.draw_detail()
        self.draw_bottom()

    # --- pills: every button, selector and badge ----------------------------------
    def pill(
        self,
        pane: tk.Canvas,
        x: int,
        y: int,
        text: str,
        command,  # type: ignore[no-untyped-def]
        *,
        tag: str,
        style: str = "glass",
        h: int | None = None,
        w: int | None = None,
        size: int = 10,
        right: bool = False,
    ) -> int:
        """Draw a rounded button; returns the x of its far edge."""
        # Prefixed so no button can ever be named "all" or "current": those are
        # Tk's own canvas tags, and binding one binds every item on the pane.
        # (A button tagged "all" once made every bottom-bar click select all.)
        tag = f"pill:{tag}"
        h = h or self.px(34)
        f = self.font(size, "bold" if style == "primary" else "normal")
        w = w or f.measure(text) + self.px(30)
        if right:
            x -= w
        fill, outline, hover, ink = PILL[style]
        normal = self.photo(("pill", w, h, style), lambda: rounded(w, h, h // 2, fill, outline))
        lit = self.photo(("pill-hover", w, h, style), lambda: rounded(w, h, h // 2, hover, outline))
        body = pane.create_image(x, y, anchor="nw", image=normal, tags=(tag, "content"))
        pane.create_text(x + w / 2, y + h / 2, text=text, fill=ink, font=f, tags=(tag, "content"))
        if style != "off" and command is not None:
            pane.tag_bind(
                tag,
                "<Enter>",
                lambda _: (pane.itemconfigure(body, image=lit), pane.configure(cursor="hand2")),
            )
            pane.tag_bind(
                tag,
                "<Leave>",
                lambda _: (pane.itemconfigure(body, image=normal), pane.configure(cursor="")),
            )
            pane.tag_bind(tag, "<ButtonRelease-1>", lambda _: command())
        else:
            for sequence in ("<Enter>", "<Leave>", "<ButtonRelease-1>"):
                pane.tag_bind(tag, sequence, lambda _: None)
        return x if right else x + w

    def badge(self, pane: tk.Canvas, x: int, y: int, text: str, style: str) -> int:
        h = self.px(19)
        f = self.font(7, "bold")
        w = f.measure(text) + self.px(14)
        look = {
            "plain": (white(24), white(40), "#d2d2d8"),
            "solid": ((228, 228, 232, 235), None, INK),
            "ring": (white(0), white(190), TEXT),
        }[style]
        image = self.photo(("badge", w, h, style), lambda: rounded(w, h, h // 2, look[0], look[1]))
        pane.create_image(x, y, anchor="nw", image=image, tags="content")
        pane.create_text(x + w / 2, y + h / 2, text=text, fill=look[2], font=f, tags="content")
        return x + w + self.px(5)

    def menu(self, pane: tk.Canvas, tag: str, options, current: str, choose) -> None:  # type: ignore[no-untyped-def]
        x0, _, _, y1 = pane.bbox(f"pill:{tag}")
        menu = tk.Menu(self.window, tearoff=0, font=(FONT, 10), **MENU)
        for option in options:
            mark = "✓  " if option == current else "     "
            menu.add_command(label=mark + option, command=lambda o=option: choose(o))
        menu.tk_popup(pane.winfo_rootx() + x0, pane.winfo_rooty() + y1 + self.px(6))

    # --- the top bar ----------------------------------------------------------------
    def draw_top(self) -> None:
        pane = self.panes["top"]
        pane.delete("content")
        mid = self.px(64) // 2
        pane.create_text(
            self.px(22),
            mid,
            anchor="w",
            text="에셋 라이브러리",
            fill=TEXT,
            font=self.font(15, "bold"),
            tags="content",
        )
        _, y0, x1, _ = self._search_box()
        y = mid - self.px(17)
        x = x1 + self.px(12)
        x = self.pill(pane, x, y, f"{self.filter}  ▾", self._pick_filter, tag="filter") + self.px(8)
        self.pill(pane, x, y, f"{self.sort}  ▾", self._pick_sort, tag="sort")
        right = pane.winfo_width() - self.px(16)
        right = self.pill(pane, right, y, "⟳  새로고침", self.reload, tag="refresh", right=True)
        right -= self.px(14)
        right = self.pill(
            pane,
            right,
            y,
            "+",
            lambda: self._resize(24),
            tag="bigger",
            w=self.px(34),
            right=True,
            size=12,
        )
        pane.create_text(
            right - self.px(8),
            mid,
            anchor="e",
            text=f"크기 {self.size}",
            fill=MUTED,
            font=self.font(9),
            tags="content",
        )
        label_w = self.font(9).measure(f"크기 {self.size}") + self.px(16)
        self.pill(
            pane,
            right - label_w,
            y,
            "−",
            lambda: self._resize(-24),
            tag="smaller",
            w=self.px(34),
            right=True,
            size=12,
        )

    def _pick_filter(self) -> None:
        self.menu(self.panes["top"], "filter", FILTERS, self.filter, self._set_filter)

    def _pick_sort(self) -> None:
        self.menu(self.panes["top"], "sort", list(SORTS), self.sort, self._set_sort)

    def _set_filter(self, value: str) -> None:
        self.filter = value
        self.draw_top()
        self._refilter()

    def _set_sort(self, value: str) -> None:
        self.sort = value
        self.draw_top()
        self._refilter()

    def _resize(self, step: int) -> None:
        self.size = max(72, min(240, self.size + step))
        self.thumbs.clear()
        self.card_photos.clear()
        self.draw_top()
        self._refilter(keep_scroll=True)

    # --- the folder list ------------------------------------------------------------
    def _build_rows(self) -> None:
        """The fixed category list, minus the rows under a collapsed parent."""
        every = category_rows()
        parents = {path.rpartition("/")[0] for path, _ in every}
        rows: list[tuple[str, int, bool]] = [(ALL, 0, True)]
        if ALL in self.expanded:
            for path, depth in every:
                above = path.split("/")[:-1]
                if all("/".join(above[: i + 1]) in self.expanded for i in range(len(above))):
                    rows.append((path, depth, path in parents))
        self.rows = rows

    def _side_geometry(self) -> tuple[int, int]:
        return self.px(54), self.px(32)  # first row's top, row height

    def draw_side(self) -> None:
        pane = self.panes["side"]
        pane.delete("content")
        w, h = pane.winfo_width(), pane.winfo_height()
        top, row_h = self._side_geometry()
        f = self.font(10)
        count_font = self.font(9)
        for index, (path, depth, kids) in enumerate(self.rows):
            y = top + index * row_h - self.side_y
            if y + row_h < 0 or y > h:
                continue
            chosen = path == self.folder
            if chosen or index == self.side_hover:
                style = ("side-on", w) if chosen else ("side-hover", w)
                fill = white(40) if chosen else white(14)
                edge = white(70) if chosen else None
                image = self.photo(
                    style + (row_h,),
                    lambda f=fill, e=edge: rounded(
                        w - self.px(20), row_h - self.px(4), self.px(10), f, e
                    ),
                )
                pane.create_image(
                    self.px(10), y + self.px(2), anchor="nw", image=image, tags="content"
                )
            x = self.px(20) + depth * self.px(16)
            if kids:
                arrow = "▾" if path in self.expanded else "▸"
                pane.create_text(
                    x,
                    y + row_h / 2,
                    anchor="w",
                    text=arrow,
                    fill=MUTED,
                    font=self.font(9),
                    tags="content",
                )
            name = "전체" if path == ALL else path.rpartition("/")[2]
            pane.create_text(
                x + self.px(16),
                y + row_h / 2,
                anchor="w",
                text=name,
                fill=TEXT if chosen else "#c8c8ce",
                font=f,
                tags="content",
            )
            pane.create_text(
                w - self.px(22),
                y + row_h / 2,
                anchor="e",
                text=str(self.counts.get(path, 0)),
                fill=MUTED,
                font=count_font,
                tags="content",
            )
        self._lay_masks("side")
        pane.create_text(
            self.px(22),
            self.px(28),
            anchor="w",
            text="분류",
            fill=TEXT,
            font=self.font(12, "bold"),
            tags="content",
        )

    def _side_index(self, event: tk.Event) -> int | None:
        top, row_h = self._side_geometry()
        if event.y < top - self.px(4):
            return None
        index = int((event.y + self.side_y - top) // row_h)
        return index if 0 <= index < len(self.rows) else None

    def _side_click(self, event: tk.Event) -> None:
        index = self._side_index(event)
        if index is None:
            return
        path, depth, kids = self.rows[index]
        arrow_x = self.px(20) + depth * self.px(16)
        if kids and (event.x < arrow_x + self.px(14) or path == self.folder):
            self.expanded.symmetric_difference_update({path})
            self._build_rows()
        if path != self.folder:
            self.folder = path
            self._refilter()
        self.draw_side()

    def _side_motion(self, event: tk.Event) -> None:
        self._side_hover(self._side_index(event))

    def _side_hover(self, index: int | None) -> None:
        if index != self.side_hover:
            self.side_hover = index
            self.panes["side"].configure(cursor="hand2" if index is not None else "")
            self.draw_side()

    def _side_wheel(self, event: tk.Event) -> None:
        top, row_h = self._side_geometry()
        h = self.panes["side"].winfo_height()
        most = max(0, top + len(self.rows) * row_h + self.px(16) - h)
        self.side_goal = max(0, min(most, self.side_goal - event.delta / 120 * row_h * 2))
        if self.side_glide_pending is None:
            self.side_glide_pending = self.window.after(GLIDE_MS, self._side_glide)

    def _side_glide(self) -> None:
        self.side_glide_pending = None
        self.side_y = glide_step(self.side_y, self.side_goal)
        self.draw_side()
        if self.side_y != round(self.side_goal):
            self.side_glide_pending = self.window.after(GLIDE_MS, self._side_glide)

    # --- data -----------------------------------------------------------------
    def reload(self) -> None:
        before = {a.key for a in self.assets}
        self.assets = collect()
        self.last_signature = signature()
        stamps = {a.stamp for a in self.assets}
        self.images = {k: v for k, v in self.images.items() if k in stamps}
        self.thumbs = {k: v for k, v in self.thumbs.items() if k[0] in stamps}
        self.loader.asked &= stamps
        self.selected &= {a.key for a in self.assets}
        for asset in self.assets:
            pair = asset.pair
            if pair is None:
                continue
            if pair in self.differs:
                asset.stale = self.differs[pair]
            else:
                self.loader.compare(pair)
        counts: dict[str, int] = {ALL: len(self.assets)}
        for asset in self.assets:
            parts = asset.category.split("/")
            for depth in range(1, len(parts) + 1):
                path = "/".join(parts[:depth])
                counts[path] = counts.get(path, 0) + 1
        self.counts = counts
        self._build_rows()
        self._refilter(keep_scroll=True)
        added = [a for a in self.assets if a.key not in before]
        if before and added:
            self._point_at(max(added, key=lambda a: a.mtime), len(added))

    def _point_at(self, asset: Asset, count: int) -> None:
        """Select a freshly saved asset, open its category and scroll to it."""
        parts = asset.category.split("/")
        self.expanded |= {"/".join(parts[: i + 1]) for i in range(len(parts) - 1)}
        self._build_rows()
        index = {a.key: i for i, a in enumerate(self.shown)}.get(asset.key)
        if index is not None:
            self.selected = {asset.key}
            self.focus = self.anchor = index
            self._measure_grid()
            self._ensure_visible(index)
            self._after_selection()
        more = f" 외 {count - 1}개" if count > 1 else ""
        self._say(f"새 에셋: {asset.name}{more}  →  {asset.category.replace('/', ' › ')}")
        self.draw_side()

    def _rest_of_reload(self) -> None:
        self._build_rows()
        self._refilter(keep_scroll=True)

    def _visible_assets(self) -> list[Asset]:
        folder = "" if self.folder == ALL else self.folder
        text = self._search_text()
        mode = self.filter
        out = []
        for asset in self.assets:
            where = asset.category
            if folder and not (where == folder or where.startswith(folder + "/")):
                continue
            if text and text not in asset.rel.casefold():
                continue
            if mode == "갱신 필요" and not asset.stale:
                continue
            if mode == "Aseprite 원본만" and ".aseprite" not in asset.files:
                continue
            if mode == "이미지만 (원본 없음)" and ".aseprite" in asset.files:
                continue
            if mode == "게임에서 사용" and not asset.used:
                continue
            out.append(asset)
        out.sort(key=SORTS.get(self.sort, SORTS["폴더순"]))
        return out

    def _refilter(self, keep_scroll: bool = False) -> None:
        focused = self._focused()
        self.shown = self._visible_assets()
        index = {a.key: i for i, a in enumerate(self.shown)}
        self.focus = index.get(focused.key) if focused is not None else None
        if not keep_scroll:
            self.scroll_y = self.scroll_goal = 0
            self.anchor = None
        self.draw_all()

    # --- the grid ---------------------------------------------------------------
    def _grid_metrics(self) -> tuple[int, int, int, int]:
        """Left, top, usable width and height of the scrolling area."""
        pane = self.panes["grid"]
        pad = self.px(14)
        return pad, pad, pane.winfo_width() - pad - self.px(18), pane.winfo_height() - 2 * pad

    def _measure_grid(self) -> None:
        _, _, width, _ = self._grid_metrics()
        thumb = self.px(self.size)
        gap = self.px(12)
        self.columns = max(1, (width + gap) // (thumb + self.px(20) + gap))
        card_w = (width - gap * (self.columns - 1)) // self.columns
        self.card = (card_w, thumb + self.px(92))
        self.cell = (card_w + gap, self.card[1] + gap)

    def _content_height(self) -> int:
        rows = -(-len(self.shown) // self.columns)
        return max(0, rows * self.cell[1] - self.px(12))

    def _clamped(self, y: float) -> float:
        _, _, _, height = self._grid_metrics()
        return max(0.0, min(y, self._content_height() - height))

    def _clamp_scroll(self) -> None:
        self.scroll_y = round(self._clamped(self.scroll_y))
        self.scroll_goal = self._clamped(self.scroll_goal)
        if self.glide_pending is None:
            self.scroll_goal = self.scroll_y

    def _schedule_draw(self) -> None:
        if not self.draw_pending:
            self.draw_pending = self.window.after(16, self._draw_grid_now)

    def _draw_grid_now(self) -> None:
        self.draw_pending = None
        self.draw_grid()

    def draw_grid(self) -> None:
        pane = self.panes["grid"]
        pane.delete("content")
        if pane.winfo_width() < 50:
            return
        self._measure_grid()
        self._clamp_scroll()
        left, top, width, height = self._grid_metrics()
        if not self.shown:
            pane.create_text(
                left + width / 2,
                top + self.px(60),
                fill=MUTED,
                font=self.font(11),
                text="보여 줄 에셋이 없어요. 검색어나 필터를 바꿔 보세요.",
                tags="content",
            )
        self.drawn_rows = set()
        self.card_items = {}
        self._fill_rows(pane)
        self._lay_masks("grid")
        self._draw_scrollbar(pane)

    def _visible_rows(self) -> range:
        _, _, _, height = self._grid_metrics()
        rows = -(-len(self.shown) // self.columns)
        first = max(0, int(self.scroll_y // self.cell[1]))
        return range(first, min(rows, int((self.scroll_y + height) // self.cell[1]) + 1))

    def _fill_rows(self, pane: tk.Canvas) -> None:
        """Drop the rows that left the view and draw the ones that entered it."""
        wanted = set(self._visible_rows())
        for row in self.drawn_rows - wanted:
            pane.delete(f"row{row}")
            for i in range(row * self.columns, (row + 1) * self.columns):
                self.card_items.pop(i, None)
        for row in sorted(wanted - self.drawn_rows):
            mark = pane.create_line(0, 0, 0, 0)  # canvas ids only grow
            for i in range(row * self.columns, min(len(self.shown), (row + 1) * self.columns)):
                self._draw_card(pane, i)
            for item in pane.find_all():
                if item > mark:
                    pane.addtag_withtag(f"row{row}", item)
                    pane.addtag_withtag("cards", item)
            pane.delete(mark)
        self.drawn_rows = wanted

    def _scroll_to(self, y: int) -> None:
        """Show the grid at ``y`` by sliding the cards already drawn, which is
        what keeps scrolling smooth: rebuilding every card costs ~50 ms."""
        pane = self.panes["grid"]
        if self.draw_pending is not None or not self.drawn_rows:
            self.scroll_y = y
            self.draw_grid()
            return
        dy = y - self.scroll_y
        if not dy:
            return
        self.scroll_y = y
        pane.move("cards", 0, -dy)
        self._fill_rows(pane)
        pane.tag_raise("mask")
        pane.delete("bar")
        self._draw_scrollbar(pane)

    def _glide(self) -> None:
        self.glide_pending = None
        self._scroll_to(glide_step(self.scroll_y, self.scroll_goal))
        if self.scroll_y != round(self.scroll_goal):
            self.glide_pending = self.window.after(GLIDE_MS, self._glide)

    def _card_box(self, i: int) -> tuple[int, int, int, int]:
        left, top, _, _ = self._grid_metrics()
        row, col = divmod(i, self.columns)
        x = left + col * self.cell[0]
        y = int(top + row * self.cell[1] - self.scroll_y)
        return x, y, x + self.card[0], y + self.card[1]

    def _draw_card(self, pane: tk.Canvas, i: int) -> None:
        x0, y0, _, _ = self._card_box(i)
        self.card_items[i] = pane.create_image(
            x0, y0, anchor="nw", image=self._card_photo(i), tags="content"
        )

    def _card_photo(self, i: int) -> ImageTk.PhotoImage:
        asset = self.shown[i]
        chosen = asset.key in self.selected
        state = "on" if chosen else ("hover" if i == self.hover else "off")
        art = self._thumb(asset, self.px(self.size))
        badges = tuple(self._badges(asset))
        key = (
            asset.stamp,
            asset.folder,
            state,
            self.card,
            self.size,
            badges,
            art if isinstance(art, str) else "art",
        )
        photo = self.card_photos.get(key)
        if photo is None:
            if len(self.card_photos) > 800:
                self.card_photos.clear()
            photo = ImageTk.PhotoImage(self._card_image(asset, state, art, badges))
            self.card_photos[key] = photo
        return photo

    def _card_image(
        self,
        asset: Asset,
        state: str,
        art: Image.Image | str,
        badges: tuple[tuple[str, str], ...],
    ) -> Image.Image:
        """One card -- frame, thumbnail, name, folder, badges, tick -- as a
        single image."""
        cw, ch = self.card
        fill, edge, width = {
            "off": (white(11), white(26), 1),
            "hover": (white(22), white(48), 1),
            "on": (white(30), white(215), 2),
        }[state]
        card = shape(cw, ch, self.px(16), fill, edge, width).copy()
        draw = ImageDraw.Draw(card)
        thumb = self.px(self.size)
        tx, ty = (cw - thumb) // 2, self.px(10)
        if isinstance(art, Image.Image):
            card.alpha_composite(art, (tx, ty))
        else:
            card.alpha_composite(shape(thumb, thumb, self.px(12), (0, 0, 0, 70)), (tx, ty))
            draw.multiline_text(
                (tx + thumb / 2, ty + thumb / 2),
                art,
                fill=MUTED,
                font=self.pil_font(9),
                anchor="mm",
                align="center",
            )
        pad = self.px(12)
        name_font, folder_font = self.pil_font(10, "bold"), self.pil_font(8)
        draw.text(
            (pad, ty + thumb + self.px(8)),
            self.fit_pil(asset.name, cw - 2 * pad, name_font),
            fill=TEXT,
            font=name_font,
            anchor="la",
        )
        draw.text(
            (pad, ty + thumb + self.px(31)),
            self.fit_pil(asset.folder or "assets", cw - 2 * pad, folder_font),
            fill=MUTED,
            font=folder_font,
            anchor="la",
        )
        bx, by = pad, ch - self.px(29)
        badge_font = self.pil_font(7, "bold")
        bh = self.px(19)
        for label, style in badges:
            back, ring, color = {
                "plain": (white(24), white(40), "#d2d2d8"),
                "solid": ((228, 228, 232, 235), None, INK),
                "ring": (white(0), white(190), TEXT),
            }[style]
            bw = round(badge_font.getlength(label)) + self.px(14)
            card.alpha_composite(shape(bw, bh, bh // 2, back, ring), (bx, by))
            draw.text((bx + bw / 2, by + bh / 2), label, fill=color, font=badge_font, anchor="mm")
            bx += bw + self.px(5)
        if state == "on":
            dot = self.px(20)
            dx, dy = cw - dot - self.px(8), self.px(8)
            card.alpha_composite(shape(dot, dot, dot // 2, (240, 240, 244, 245)), (dx, dy))
            # Drawn, not typed: the card font has no tick glyph.
            u = dot / 20
            draw.line(
                [
                    (dx + 6 * u, dy + 10.5 * u),
                    (dx + 9 * u, dy + 13.5 * u),
                    (dx + 14.5 * u, dy + 7 * u),
                ],
                fill=INK,
                width=max(2, round(2 * u)),
                joint="curve",
            )
        return card

    def _badges(self, asset: Asset) -> list[tuple[str, str]]:
        names = {
            ".aseprite": "ASE",
            ".png": "PNG",
            ".webp": "WEBP",
            ".gif": "GIF",
            ".jpg": "JPG",
            ".bmp": "BMP",
        }
        out = [(names[ext], "plain") for ext in ALL_EXTS if ext in asset.files]
        if asset.used:
            out.append(("게임", "solid"))
        if asset.stale:
            out.append(("갱신 필요", "ring"))
        return out

    def _thumb(self, asset: Asset, size: int) -> Image.Image | str:
        stamp = asset.stamp
        got = self.images.get(stamp)
        if got is None:
            self.loader.ask(stamp)
            return "불러오는 중…"
        if isinstance(got, str):
            return f"미리보기 오류\n{got[:50]}"
        key = (stamp, size)
        if key not in self.thumbs:
            board = checker(size, size, max(6, size // 12), "#18181b", "#202024")
            art = fit(got, size - self.px(14), size - self.px(14))
            board.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
            board.putalpha(round_mask(size, size, self.px(12)))
            self.thumbs[key] = board
        return self.thumbs[key]

    def _draw_scrollbar(self, pane: tk.Canvas) -> None:
        _, top, _, height = self._grid_metrics()
        total = self._content_height()
        if total <= height:
            return
        bar_h = max(self.px(40), int(height * height / total))
        y = top + int((height - bar_h) * self.scroll_y / (total - height))
        w = self.px(6)
        x = pane.winfo_width() - self.px(14)
        thumb = self.photo(("bar", w, bar_h), lambda: rounded(w, bar_h, w // 2, white(70)))
        pane.create_image(x, y, anchor="nw", image=thumb, tags=("content", "bar"))

    # --- grid input -----------------------------------------------------------------
    def _index_at(self, x: float, y: float) -> int | None:
        left, top, width, _ = self._grid_metrics()
        if x < left or x > left + width:
            return None
        col = int((x - left) // self.cell[0])
        row = int((y - top + self.scroll_y) // self.cell[1])
        if col >= self.columns or row < 0:
            return None
        i = row * self.columns + col
        if i >= len(self.shown):
            return None
        x0, y0, x1, y1 = self._card_box(i)
        return i if x0 <= x <= x1 and y0 <= y <= y1 else None

    def _grid_press(self, event: tk.Event) -> None:
        pane = self.panes["grid"]
        pane.focus_set()
        if event.x > pane.winfo_width() - self.px(22):  # the scrollbar strip
            self.drag_from = (event.y, self.scroll_y)
            return
        i = self._index_at(event.x, event.y)
        if i is None:
            return
        key = self.shown[i].key
        if event.state & 0x1 and self.anchor is not None:
            lo, hi = sorted((self.anchor, i))
            self.selected.update(a.key for a in self.shown[lo : hi + 1])
        elif event.state & 0x4:
            self.selected.symmetric_difference_update({key})
            self.anchor = i
        else:
            self.selected = {key}
            self.anchor = i
        self.focus = i
        self._after_selection()

    def _grid_drag(self, event: tk.Event) -> None:
        if self.drag_from is None:
            return
        _, _, _, height = self._grid_metrics()
        total = self._content_height()
        if total <= height:
            return
        start_y, start_scroll = self.drag_from
        # The thumb follows the pointer exactly; only the wheel glides.
        self.scroll_goal = self._clamped(start_scroll + (event.y - start_y) * total / height)
        self._scroll_to(round(self.scroll_goal))

    def _grid_wheel(self, event: tk.Event) -> None:
        self.scroll_goal = self._clamped(self.scroll_goal - event.delta / 120 * self.px(110))
        if self.glide_pending is None:
            self.glide_pending = self.window.after(GLIDE_MS, self._glide)

    def _grid_motion(self, event: tk.Event) -> None:
        self._set_hover(self._index_at(event.x, event.y))

    def _set_hover(self, i: int | None) -> None:
        if i != self.hover:
            before, self.hover = self.hover, i
            pane = self.panes["grid"]
            pane.configure(cursor="hand2" if i is not None else "")
            for j in (before, i):
                if j is not None and j in self.card_items and self.draw_pending is None:
                    pane.itemconfigure(self.card_items[j], image=self._card_photo(j))

    def _double(self, event: tk.Event) -> None:
        i = self._index_at(event.x, event.y)
        if i is not None:
            self.open_asset(self.shown[i])

    def _ensure_visible(self, i: int) -> None:
        _, top, _, height = self._grid_metrics()
        row = i // self.columns
        y0 = row * self.cell[1]
        y1 = y0 + self.card[1]
        if y0 < self.scroll_y:
            self.scroll_y = self.scroll_goal = y0
        elif y1 > self.scroll_y + height:
            self.scroll_y = self.scroll_goal = y1 - height

    def _arrow(self, event: tk.Event, step: int) -> str | None:
        if self._typing(event) or not self.shown:
            return None
        i = 0 if self.focus is None else max(0, min(len(self.shown) - 1, self.focus + step))
        if event.state & 0x1:
            self.selected.add(self.shown[i].key)
        else:
            self.selected = {self.shown[i].key}
            self.anchor = i
        self.focus = i
        self._ensure_visible(i)
        self._after_selection()
        return "break"

    def _select_all_key(self, event: tk.Event) -> str | None:
        if self._typing(event):
            return None
        self.select_shown()
        return "break"

    def _delete_key(self, event: tk.Event) -> str | None:
        if self._typing(event):
            return None
        self.confirm_delete()
        return "break"

    def _enter_key(self, event: tk.Event) -> str | None:
        if self._typing(event):
            self.panes["grid"].focus_set()
            return "break"
        focus = self._focused()
        if focus is not None:
            self.open_asset(focus)
        return "break"

    def _escape(self, event: tk.Event) -> None:
        if self._typing(event) and self._search_text():
            self.query.set("")
            return
        if self.selected:
            self.clear_selection()
        elif self._search_text():
            self.query.set("")
        self.panes["grid"].focus_set()

    def select_shown(self) -> None:
        self.selected = {a.key for a in self.shown}
        self._after_selection()

    def clear_selection(self) -> None:
        self.selected.clear()
        self._after_selection()

    def _after_selection(self) -> None:
        self.draw_grid()
        self.draw_detail()
        self.draw_bottom()

    def _focused(self) -> Asset | None:
        if self.focus is None or self.focus >= len(self.shown):
            return None
        return self.shown[self.focus]

    # --- the detail pane ----------------------------------------------------------
    def draw_detail(self) -> None:
        pane = self.panes["detail"]
        pane.delete("content")
        w = pane.winfo_width()
        if w < 50:
            return
        pad = self.px(20)
        inner = w - 2 * pad
        asset = self._focused()
        if (asset.stamp if asset else None) != self.view_key:
            self.view_key = asset.stamp if asset else None
            self.view_scale = None
            self.view_center = None
        title = asset.name if asset else "선택한 에셋 없음"
        pane.create_text(
            pad,
            self.px(26),
            anchor="w",
            text=self.fit_text(title, inner, self.font(13, "bold")),
            fill=TEXT,
            font=self.font(13, "bold"),
            tags="content",
        )
        sub = f"assets/{asset.rel}" if asset else "에셋을 클릭하면 여기에 크게 보여요."
        pane.create_text(
            pad,
            self.px(50),
            anchor="w",
            text=self.fit_text(sub, inner, self.font(9)),
            fill=MUTED,
            font=self.font(9),
            tags="content",
        )
        box_h = self.px(290)
        box_y = self.px(70)
        self._draw_preview(pane, asset, pad, box_y, inner, box_h)
        y = box_y + box_h + self.px(12)
        x = pad
        for option in ("맞춤", "1x", "2x", "4x", "8x"):
            x = self.pill(
                pane,
                x,
                y,
                option,
                lambda o=option: self._set_zoom(o),
                tag=f"zoom-{option}",
                style="on" if self._zoom_label() == option else "glass",
                h=self.px(28),
                size=9,
            ) + self.px(5)
        y += self.px(34)
        x = pad
        for option in ("체크", "어둡게", "밝게", "잔디"):
            x = self.pill(
                pane,
                x,
                y,
                option,
                lambda o=option: self._set_backing(o),
                tag=f"back-{option}",
                style="on" if option == self.backing else "glass",
                h=self.px(28),
                size=9,
            ) + self.px(5)
        y += self.px(44)
        if asset is not None:
            lines = self._detail_lines(asset)
            text = pane.create_text(
                pad,
                y,
                anchor="nw",
                text="\n".join(lines),
                fill="#cfcfd5",
                font=self.font(9),
                width=inner,
                tags="content",
            )
            y = pane.bbox(text)[3] + self.px(16)
        # Deleting lives here too, beside what is being looked at: it was only
        # in the bottom corner, where nobody looking at an asset finds it.
        many = asset is not None and asset.key in self.selected and len(self.selected) > 1
        bin_label = f"휴지통으로 보내기 ({len(self.selected)}개)" if many else "휴지통으로 보내기"
        actions = (
            ("Aseprite에서 열기", "primary", self.open_asset),
            ("탐색기에서 보기", "glass", self.reveal),
            ("경로 복사", "glass", self.copy_path),
            (bin_label, "danger", self.delete_asset),
        )
        # Keep all four on the pane however long the notes above them run.
        button_h, step = self.px(36), self.px(43)
        y = min(y, pane.winfo_height() - self.px(18) - step * (len(actions) - 1) - button_h)
        for label, style, action in actions:
            command = (lambda a=action: a(asset)) if asset else None
            self.pill(
                pane,
                pad,
                y,
                label,
                command,
                tag=f"act-{label.split(' (')[0]}",
                style=style if asset else "off",
                w=inner,
                h=button_h,
            )
            y += step

    def _detail_lines(self, asset: Asset) -> list[str]:
        image = self.images.get(asset.stamp)
        if image is None:
            dims = "불러오는 중…"
        elif isinstance(image, str):
            dims = f"미리보기 오류: {image}"
        else:
            dims = f"{image.width} × {image.height} px"
        lines = [dims, ""]
        for ext in ALL_EXTS:
            if ext in asset.files:
                path = asset.files[ext]
                when = time.strftime("%m-%d %H:%M", time.localtime(asset.mtimes[ext]))
                size = path.stat().st_size if path.exists() else 0
                lines.append(f"{ext[1:].upper():<9}  {size / 1024:6.1f} KB    {when}")
        if asset.stale:
            lines += ["", "◌ Aseprite 원본과 이미지가 달라요. 다시 내보내야 게임에 반영돼요."]
        if asset.used:
            lines += ["", "● 게임이 읽는 파일이에요. 지우면 게임이 실행되지 않을 수 있어요."]
        if ".aseprite" not in asset.files:
            lines += ["", "Aseprite 원본이 없어요."]
        return lines

    def _draw_preview(
        self, pane: tk.Canvas, asset: Asset | None, x: int, y: int, w: int, h: int
    ) -> None:
        self.preview_box = (x, y, w, h)
        if self.backing == "체크":
            board = checker(w, h, self.px(10), "#17171a", "#1f1f23")
        else:
            colour = {"어둡게": "#0b0b0d", "밝게": "#e8e8ec", "잔디": "#6f8f4e"}[self.backing]
            board = Image.new("RGBA", (w, h), colour)
        image = self._preview_image(asset)
        if image is not None:
            self._paint_view(board, image)
        board.putalpha(round_mask(w, h, self.px(16)))
        board.alpha_composite(rounded(w, h, self.px(16), white(0), white(40)))
        self.detail_photo = ImageTk.PhotoImage(board)
        pane.create_image(x, y, anchor="nw", image=self.detail_photo, tags="content")
        if image is not None:
            scale, _, _ = self._view(image)
            label = f"{scale * 100:.0f}%"
            f = self.font(8, "bold")
            lw, lh = f.measure(label) + self.px(16), self.px(20)
            chip = self.photo(
                ("zoom-chip", lw, lh), lambda: rounded(lw, lh, lh // 2, (0, 0, 0, 150))
            )
            cx, cy = x + w - lw - self.px(10), y + h - lh - self.px(10)
            pane.create_image(cx, cy, anchor="nw", image=chip, tags="content")
            pane.create_text(
                cx + lw / 2, cy + lh / 2, text=label, fill=TEXT, font=f, tags="content"
            )
            hint = "휠 확대·축소  ·  드래그 이동  ·  더블클릭 맞춤"
            hf = self.font(8)
            hw = hf.measure(hint) + self.px(18)
            back = self.photo(
                ("hint-chip", hw, lh), lambda: rounded(hw, lh, lh // 2, (0, 0, 0, 150))
            )
            hx = x + self.px(10)
            pane.create_image(hx, cy, anchor="nw", image=back, tags="content")
            pane.create_text(
                hx + hw / 2, cy + lh / 2, text=hint, fill="#c4c4ca", font=hf, tags="content"
            )

    def _preview_image(self, asset: Asset | None) -> Image.Image | None:
        if asset is None:
            return None
        image = self.images.get(asset.stamp)
        if image is None:
            self.loader.ask(asset.stamp)
            return None
        return None if isinstance(image, str) else image

    def _fit_scale(self, image: Image.Image) -> float:
        _, _, w, h = self.preview_box
        scale = min((w - self.px(24)) / image.width, (h - self.px(24)) / image.height)
        return max(1, int(scale)) if scale >= 1 else scale

    def _view(self, image: Image.Image) -> tuple[float, float, float]:
        """Scale, and the art pixel that sits at the middle of the box."""
        scale = self.view_scale or self._fit_scale(image)
        cx, cy = self.view_center or (image.width / 2, image.height / 2)
        return scale, cx, cy

    def _paint_view(self, board: Image.Image, image: Image.Image) -> None:
        """Draw only the part of the art that is in view, at the view's scale.

        Cropping before scaling keeps an 8x zoom of a large sheet cheap: only
        the visible corner is ever enlarged.
        """
        w, h = board.size
        scale, cx, cy = self._view(image)
        half_w, half_h = w / 2 / scale, h / 2 / scale
        sx0, sy0 = max(0, int(cx - half_w)), max(0, int(cy - half_h))
        sx1 = min(image.width, int(cx + half_w) + 2)
        sy1 = min(image.height, int(cy + half_h) + 2)
        if sx1 <= sx0 or sy1 <= sy0:
            return
        piece = image.crop((sx0, sy0, sx1, sy1))
        size = (max(1, round((sx1 - sx0) * scale)), max(1, round((sy1 - sy0) * scale)))
        method = Image.Resampling.NEAREST if scale >= 1 else Image.Resampling.LANCZOS
        piece = piece.resize(size, method)
        left = round((sx0 - cx) * scale + w / 2)
        top = round((sy0 - cy) * scale + h / 2)
        # Clip to the board by hand: alpha_composite wants it to fit.
        src_x, src_y = max(0, -left), max(0, -top)
        dst_x, dst_y = max(0, left), max(0, top)
        piece = piece.crop(
            (
                src_x,
                src_y,
                min(piece.width, src_x + w - dst_x),
                min(piece.height, src_y + h - dst_y),
            )
        )
        if piece.width > 0 and piece.height > 0:
            board.alpha_composite(piece, (dst_x, dst_y))

    def _in_preview(self, event: tk.Event) -> bool:
        x, y, w, h = self.preview_box
        return x <= event.x <= x + w and y <= event.y <= y + h

    def _preview_wheel(self, event: tk.Event) -> None:
        image = self._preview_image(self._focused())
        if image is None or not self._in_preview(event):
            return
        scale, cx, cy = self._view(image)
        if event.delta > 0:
            new = min((v for v in LADDER if v > scale * 1.001), default=LADDER[-1])
        else:
            new = max((v for v in LADDER if v < scale * 0.999), default=LADDER[0])
        # Keep the art pixel under the cursor where it is.
        bx, by, w, h = self.preview_box
        mx, my = event.x - bx - w / 2, event.y - by - h / 2
        px_, py_ = cx + mx / scale, cy + my / scale
        self.view_scale = new
        self._set_center(image, px_ - mx / new, py_ - my / new)
        self.draw_detail()

    def _set_center(self, image: Image.Image, cx: float, cy: float) -> None:
        self.view_center = (max(0.0, min(image.width, cx)), max(0.0, min(image.height, cy)))

    def _preview_press(self, event: tk.Event) -> None:
        image = self._preview_image(self._focused())
        if image is None or not self._in_preview(event):
            self.pan_from = None
            return
        scale, cx, cy = self._view(image)
        self.pan_from = (event.x, event.y, cx, cy)

    def _preview_drag(self, event: tk.Event) -> None:
        image = self._preview_image(self._focused())
        if image is None or self.pan_from is None:
            return
        x0, y0, cx, cy = self.pan_from
        scale, _, _ = self._view(image)
        if self.view_scale is None:
            self.view_scale = scale  # dragging out of fit keeps the size it had
        self._set_center(image, cx - (event.x - x0) / scale, cy - (event.y - y0) / scale)
        self.draw_detail()

    def _preview_reset(self, event: tk.Event) -> None:
        if self._in_preview(event):
            self._set_zoom("맞춤")

    def _preview_cursor(self, event: tk.Event) -> None:
        """A move cursor over the art. Changed only on crossing its edge, so the
        buttons below keep the hand cursor they set for themselves."""
        inside = self._in_preview(event) and self._preview_image(self._focused()) is not None
        if inside != getattr(self, "_over_art", False):
            self._over_art = inside
            self.panes["detail"].configure(cursor="fleur" if inside else "")

    def _zoom_label(self) -> str:
        if self.view_scale is None:
            return "맞춤"
        return f"{self.view_scale:g}x"

    def _set_zoom(self, value: str) -> None:
        self.view_scale = None if value == "맞춤" else float(value[:-1])
        self.view_center = None
        self.draw_detail()

    def _set_backing(self, value: str) -> None:
        self.backing = value
        self.draw_detail()

    # --- the bottom bar -------------------------------------------------------------
    def draw_bottom(self) -> None:
        pane = self.panes["bottom"]
        pane.delete("content")
        w, h = pane.winfo_width(), pane.winfo_height()
        mid = h // 2
        if self.flash and time.monotonic() < self.flash_until:
            status = self.flash
        else:
            parts = [f"{len(self.shown)} / {len(self.assets)}개", f"선택 {len(self.selected)}개"]
            pending = sum(1 for a in self.assets if a.pair and a.pair not in self.differs)
            if pending:
                parts.append(f"원본과 비교 중 {pending}개")
            stale = sum(1 for a in self.shown if a.stale)
            if stale:
                parts.append(f"갱신 필요 {stale}개")
            parts.append("Ctrl·Shift+클릭 여러 개  ·  더블클릭 Aseprite  ·  우클릭 메뉴")
            status = "     ·     ".join(parts)
        pane.create_text(
            self.px(22), mid, anchor="w", text=status, fill=MUTED, font=self.font(9), tags="content"
        )
        y = mid - self.px(17)
        right = w - self.px(12)
        count = len(self.selected)
        right = self.pill(
            pane,
            right,
            y,
            f"선택 삭제 ({count})",
            self.confirm_delete if count else None,
            tag="delete",
            style="danger" if count else "off",
            right=True,
        ) - self.px(8)
        right = self.pill(
            pane,
            right,
            y,
            "선택 해제",
            self.clear_selection if count else None,
            tag="clear",
            style="glass" if count else "off",
            right=True,
        ) - self.px(8)
        self.pill(
            pane, right, y, "보이는 것 모두 선택", self.select_shown, tag="select-all", right=True
        )

    def _say(self, text: str) -> None:
        self.flash = text
        self.flash_until = time.monotonic() + 3
        self.draw_bottom()
        self.window.after(3100, self.draw_bottom)

    # --- background work ------------------------------------------------------------
    def _poll_images(self) -> None:
        arrived = set()
        try:
            while True:
                stamp, image = self.loader.results.get_nowait()
                self.images[stamp] = image
                arrived.add(stamp)
        except queue.Empty:
            pass
        compared = False
        try:
            while True:
                pair, differs = self.loader.compared.get_nowait()
                self.differs[pair] = differs
                compared = True
        except queue.Empty:
            pass
        if compared:
            for asset in self.assets:
                if asset.pair in self.differs:
                    asset.stale = self.differs[asset.pair]
            if self.filter == "갱신 필요":
                self._refilter(keep_scroll=True)
            self.draw_bottom()
        if self.folder_watch.settled() and signature() != self.last_signature:
            self.reload()
        if arrived or compared:
            self._refresh_cards(arrived, all_cards=compared)
            focus = self._focused()
            if focus is not None and focus.stamp in arrived:
                self.draw_detail()
        self.window.after(50, self._poll_images)

    def _refresh_cards(self, stamps: set[tuple[str, float]], all_cards: bool) -> None:
        """Swap in the new image of just the cards that changed -- a thumbnail
        that finished loading, a badge that appeared -- instead of rebuilding
        the grid, which would stall a scroll in progress."""
        if self.draw_pending is not None:
            return  # a full redraw is coming anyway
        pane = self.panes["grid"]
        for i, item in self.card_items.items():
            if i < len(self.shown) and (all_cards or self.shown[i].stamp in stamps):
                pane.itemconfigure(item, image=self._card_photo(i))

    def _watch(self) -> None:
        """Pick up files changed by other tools (or other tabs) without F5.

        A fallback: walking every file takes ~75 ms on this thread, a visible
        stall mid-scroll, so it only runs when the change watch is not."""
        try:
            if not self.folder_watch.alive and signature() != self.last_signature:
                self.reload()
        finally:
            self.window.after(REFRESH_MS, self._watch)

    # --- actions ------------------------------------------------------------------
    def _path_of(self, asset: Asset) -> Path:
        return asset.files.get(".aseprite") or next(iter(asset.files.values()))

    def open_asset(self, asset: Asset) -> None:
        try:
            subprocess.Popen([str(ASEPRITE), str(self._path_of(asset))])
        except OSError as error:
            messagebox.showerror("열기 실패", str(error), parent=self.window)

    def reveal(self, asset: Asset) -> None:
        subprocess.Popen(["explorer", "/select,", str(self._path_of(asset))])

    def copy_path(self, asset: Asset) -> None:
        path = self._path_of(asset)
        self.window.clipboard_clear()
        self.window.clipboard_append(str(path))
        self._say(f"경로를 복사했어요: {path}")

    def _context(self, event: tk.Event) -> None:
        i = self._index_at(event.x, event.y)
        if i is None:
            return
        asset = self.shown[i]
        if asset.key not in self.selected:
            self.selected = {asset.key}
            self.anchor = i
        self.focus = i
        self._after_selection()
        menu = tk.Menu(self.window, tearoff=0, font=(FONT, 10), **MENU)
        menu.add_command(label="Aseprite에서 열기", command=lambda: self.open_asset(asset))
        menu.add_command(label="탐색기에서 보기", command=lambda: self.reveal(asset))
        menu.add_command(label="경로 복사", command=lambda: self.copy_path(asset))
        menu.add_separator()
        menu.add_command(label=f"삭제 ({len(self.selected)}개)…", command=self.confirm_delete)
        menu.tk_popup(event.x_root, event.y_root)

    def delete_asset(self, asset: Asset) -> None:
        """Bin what is selected, or just this one if it is not among them."""
        if asset.key not in self.selected:
            self.selected = {asset.key}
            self._after_selection()
        self.confirm_delete()

    def confirm_delete(self) -> None:
        chosen = [a for a in self.assets if a.key in self.selected]
        targets = sorted(p for a in chosen for p in a.files.values())
        if not targets:
            return
        used = [a for a in chosen if a.used]
        dialog = tk.Toplevel(self.window, bg="#141416")
        dialog.title("휴지통으로 보내기")
        dialog.geometry(f"{self.px(720)}x{self.px(540)}")
        dialog.transient(self.window)
        label = {"bg": "#141416", "anchor": "w", "justify": "left"}
        tk.Label(
            dialog,
            text=f"{len(chosen)}개 에셋 · 파일 {len(targets)}개를 휴지통으로 보냅니다.",
            fg=TEXT,
            font=(FONT, 13, "bold"),
            **label,
        ).pack(fill="x", padx=18, pady=(18, 4))
        tk.Label(
            dialog,
            fg=MUTED,
            font=(FONT, 9),
            **label,
            text="같은 이름으로 묶인 Aseprite·PNG·WebP 파일이 함께 지워져요. "
            "휴지통에서 되살릴 수 있어요.",
        ).pack(fill="x", padx=18)
        if used:
            names = ", ".join(a.name for a in used[:8]) + (" …" if len(used) > 8 else "")
            tk.Label(
                dialog,
                bg="#2a2a2e",
                fg=TEXT,
                font=(FONT, 10, "bold"),
                justify="left",
                anchor="w",
                wraplength=self.px(680),
                padx=14,
                pady=10,
                text=f"● 게임이 읽는 에셋 {len(used)}개가 들어 있어요: {names}\n"
                + "\n".join(sorted({stand_in(a.category) for a in used}))
                + "\n게임은 그대로 실행돼요. 다음에 게임을 켤 때부터 적용돼요.",
            ).pack(fill="x", padx=18, pady=(12, 0))
        # The buttons are packed FIRST, against the bottom edge. Packed last,
        # they got whatever the file list left over -- and a Text asks for 24
        # lines, so they got nothing and the dialog had no way to confirm.
        buttons = tk.Frame(dialog, bg="#141416")
        buttons.pack(side="bottom", fill="x", padx=18, pady=(0, 18))
        body = tk.Frame(dialog, bg="#141416")
        body.pack(fill="both", expand=True, padx=18, pady=12)
        listing = tk.Text(
            body,
            height=6,  # a floor, not a size: it grows into whatever room is left
            wrap="none",
            bg="#1c1c1f",
            fg="#d0d0d6",
            relief="flat",
            font=("Consolas", 10),
            padx=10,
            pady=8,
            highlightthickness=0,
        )
        listing.pack(fill="both", expand=True)
        listing.insert("1.0", "\n".join(p.relative_to(ROOT).as_posix() for p in targets))
        listing.configure(state="disabled")

        def execute() -> None:
            dialog.destroy()
            errors = []
            for path in targets:
                try:
                    recycle_file(path)
                except Exception as error:
                    errors.append(str(error))
            self.selected.clear()
            self.reload()
            if errors:
                messagebox.showerror("삭제하지 못한 파일", "\n".join(errors), parent=self.window)

        flat = {
            "relief": "flat",
            "bd": 0,
            "padx": 18,
            "pady": 8,
            "font": (FONT, 10),
            "cursor": "hand2",
        }
        tk.Button(
            buttons,
            text="휴지통으로 이동",
            command=execute,
            bg="#e8e8ec",
            fg=INK,
            activebackground="#ffffff",
            **flat,
        ).pack(side="right")
        cancel = tk.Button(
            buttons,
            text="취소",
            command=dialog.destroy,
            bg="#2a2a2e",
            fg=TEXT,
            activebackground="#3a3a40",
            activeforeground=TEXT,
            **flat,
        )
        cancel.pack(side="right", padx=10)
        cancel.focus_set()
        dialog.bind("<Escape>", lambda _: dialog.destroy())
        dialog.grab_set()


def main() -> None:
    with contextlib.suppress(AttributeError, OSError):
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # sharp text on scaled displays
    window = tk.Tk()
    Gallery(window)
    window.mainloop()


if __name__ == "__main__":
    main()
