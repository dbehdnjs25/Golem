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
  when files change on disk.

Badges: ASE / PNG / WEBP say which files exist. "갱신 필요" means the
exported image no longer matches the Aseprite source's first frame, so the
game is still drawing the old one (checked pixel by pixel in the background).
"게임" means the game's code names both the file and its folder, or a tileset
lists it -- a guess, but a good warning before deleting.
"""

from __future__ import annotations

import contextlib
import ctypes
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
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw, ImageTk

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT / "assets"
CODE = PROJECT / "src" / "game"
ASEPRITE = Path(os.environ.get("ASEPRITE", r"C:\Users\ykb62\Desktop\aseprite.exe"))
IMAGE_EXTS = (".png", ".webp", ".gif", ".jpg", ".bmp")
ALL_EXTS = (".aseprite", *IMAGE_EXTS)
REFRESH_MS = 3000
ALL = "*"  # the tree row for every folder

# Colours
BG = "#141922"
PANEL = "#1b222d"
CARD = "#222b38"
CARD_HOVER = "#2a3545"
LINE = "#2f3a4a"
TEXT = "#e6edf6"
MUTED = "#8d9bb0"
ACCENT = "#5fd0a8"
WARN = "#f0b35a"
DANGER = "#ef7a7a"
BADGE = {".aseprite": "#7c6cf0", ".png": "#3f8fd8", ".webp": "#2fa39a"}
FONT = "Malgun Gothic"

SORTS = {
    "이름순": lambda e: (e.name.casefold(), e.folder),
    "폴더순": lambda e: (e.folder.casefold(), e.name.casefold()),
    "최근 수정순": lambda e: -e.mtime,
    "큰 이미지순": lambda e: -e.bytes,
}
FILTERS = ("전체", "갱신 필요", "Aseprite 원본만", "이미지만 (원본 없음)", "게임에서 사용")


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


# --- the window ----------------------------------------------------------------


class Gallery:
    def __init__(self, window: tk.Tk) -> None:
        self.window = window
        self.ui = window.winfo_fpixels("1i") / 96  # 1.0 at 100% Windows scaling
        self.loader = Loader()
        self.assets: list[Asset] = []
        self.shown: list[Asset] = []
        self.images: dict[tuple[str, float], Image.Image | str] = {}
        self.thumbs: dict[tuple[tuple[str, float], int], ImageTk.PhotoImage] = {}
        self.selected: set[Path] = set()
        self.anchor: int | None = None  # where a Shift+click run starts
        self.focus: int | None = None  # the one shown on the right
        self.hover: int | None = None
        self.layout_pending: str | None = None
        self.draw_pending: str | None = None
        self.columns = 1
        self.cell = (1, 1)
        self.card = (1, 1)
        self.last_signature: tuple[tuple[str, float], ...] = ()
        self.detail_photo: ImageTk.PhotoImage | None = None
        self.differs: dict[tuple[str, float, str, float], bool] = {}

        window.title("에셋 라이브러리 · Pygame Project")
        window.geometry(f"{int(1500 * self.ui)}x{int(940 * self.ui)}")
        window.minsize(int(900 * self.ui), int(560 * self.ui))
        window.configure(bg=BG)
        self._style()
        self._build()
        self._bind_keys()
        self.reload()
        window.after(50, self._poll_images)
        window.after(REFRESH_MS, self._watch)

    def px(self, n: float) -> int:
        return int(n * self.ui)

    # --- construction -----------------------------------------------------
    def _style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        base = (FONT, 10)
        style.configure(".", background=BG, foreground=TEXT, font=base, borderwidth=0)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))
        style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED, font=(FONT, 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=(FONT, 15, "bold"))
        style.configure("Head.TLabel", background=PANEL, foreground=TEXT, font=(FONT, 12, "bold"))
        style.configure(
            "TEntry",
            fieldbackground=CARD,
            foreground=TEXT,
            insertcolor=TEXT,
            bordercolor=LINE,
            lightcolor=LINE,
            darkcolor=LINE,
            padding=6,
        )
        style.configure(
            "TCombobox",
            fieldbackground=CARD,
            background=CARD,
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=LINE,
            lightcolor=LINE,
            darkcolor=LINE,
            padding=4,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", CARD)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", CARD)],
            selectforeground=[("readonly", TEXT)],
        )
        self.window.option_add("*TCombobox*Listbox.background", CARD)
        self.window.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.window.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.window.option_add("*TCombobox*Listbox.font", base)
        style.configure(
            "TButton",
            background=CARD,
            foreground=TEXT,
            padding=(10, 5),
            bordercolor=LINE,
            lightcolor=CARD,
            darkcolor=CARD,
        )
        style.map(
            "TButton",
            background=[("active", CARD_HOVER), ("disabled", PANEL)],
            foreground=[("disabled", "#56627a")],
        )
        style.configure("Accent.TButton", background="#2f6f5c")
        style.map("Accent.TButton", background=[("active", "#3a8a72"), ("disabled", CARD)])
        style.configure("Danger.TButton", background="#6b2f37")
        style.map("Danger.TButton", background=[("active", "#8a3a45"), ("disabled", PANEL)])
        style.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=TEXT,
            rowheight=self.px(26),
            bordercolor=PANEL,
            font=base,
        )
        style.map("Treeview", background=[("selected", "#2c4a44")], foreground=[("selected", TEXT)])
        style.configure(
            "Vertical.TScrollbar",
            background=CARD,
            troughcolor=BG,
            bordercolor=BG,
            arrowcolor=MUTED,
            lightcolor=CARD,
            darkcolor=CARD,
        )
        style.configure(
            "Horizontal.TScale",
            background=CARD,
            troughcolor=CARD,
            bordercolor=BG,
            lightcolor=CARD,
            darkcolor=CARD,
        )

    def _build(self) -> None:
        pad = self.px(14)
        # top bar
        top = ttk.Frame(self.window, padding=(pad, pad, pad, self.px(8)))
        top.pack(fill="x")
        ttk.Label(top, text="에셋 라이브러리", style="Title.TLabel").pack(side="left")
        self.query = tk.StringVar()
        search = ttk.Entry(top, textvariable=self.query, width=34)
        search.pack(side="left", padx=(pad * 2, self.px(8)))
        self.search = search
        self._placeholder(search, "이름 또는 경로 검색  (Ctrl+F)")
        self.filter = tk.StringVar(value=FILTERS[0])
        ttk.Combobox(
            top, textvariable=self.filter, values=FILTERS, state="readonly", width=18
        ).pack(side="left", padx=self.px(4))
        self.sort = tk.StringVar(value="폴더순")
        ttk.Combobox(
            top, textvariable=self.sort, values=list(SORTS), state="readonly", width=12
        ).pack(side="left", padx=self.px(4))
        ttk.Button(top, text="⟳ 새로고침", command=self.reload).pack(side="right")
        self.size = tk.IntVar(value=128)
        ttk.Scale(
            top,
            from_=72,
            to=240,
            variable=self.size,
            length=self.px(150),
            command=lambda _: self._relayout(),
        ).pack(side="right", padx=self.px(8))
        ttk.Label(top, text="크기", style="Muted.TLabel").pack(side="right")

        body = ttk.Frame(self.window)
        body.pack(fill="both", expand=True)

        # left: folders
        left = ttk.Frame(body, style="Panel.TFrame", width=self.px(230))
        left.pack(side="left", fill="y", padx=(pad, 0), pady=(0, pad))
        left.pack_propagate(False)
        ttk.Label(left, text="폴더", style="Head.TLabel").pack(anchor="w", padx=12, pady=(12, 6))
        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.tree.pack(fill="both", expand=True, padx=(6, 0), pady=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._relayout(reset=True))

        # right: details
        right = ttk.Frame(body, style="Panel.TFrame", width=self.px(360))
        right.pack(side="right", fill="y", padx=(0, pad), pady=(0, pad))
        right.pack_propagate(False)
        self._build_detail(right)

        # middle: grid
        middle = ttk.Frame(body)
        middle.pack(side="left", fill="both", expand=True, padx=pad, pady=(0, pad))
        self.canvas = tk.Canvas(middle, bg=BG, highlightthickness=0)
        self.scroll = ttk.Scrollbar(middle, orient="vertical", command=self._yview)
        self.scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.bind("<Configure>", lambda _: self._relayout())
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<Double-Button-1>", self._double)
        self.canvas.bind("<Button-3>", self._context)
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<Leave>", lambda _: self._set_hover(None))

        # bottom: status + bulk actions
        bottom = ttk.Frame(self.window, padding=(pad, 0, pad, self.px(10)))
        bottom.pack(fill="x", side="bottom", before=body)
        self.status = ttk.Label(bottom, style="Muted.TLabel")
        self.status.pack(side="left")
        self.delete_button = ttk.Button(
            bottom, text="선택 삭제", style="Danger.TButton", command=self.confirm_delete
        )
        self.delete_button.pack(side="right")
        ttk.Button(bottom, text="선택 해제", command=self.clear_selection).pack(
            side="right", padx=self.px(6)
        )
        ttk.Button(bottom, text="보이는 것 모두 선택", command=self.select_shown).pack(side="right")

        for var in (self.query, self.filter, self.sort):
            var.trace_add("write", lambda *_: self._relayout(reset=True))

    def _build_detail(self, right: ttk.Frame) -> None:
        self.d_title = ttk.Label(
            right, text="선택한 에셋 없음", style="Head.TLabel", wraplength=self.px(330)
        )
        self.d_title.pack(anchor="w", padx=14, pady=(12, 2))
        self.d_path = ttk.Label(right, style="PanelMuted.TLabel", wraplength=self.px(330))
        self.d_path.pack(anchor="w", padx=14)
        self.d_canvas = tk.Canvas(
            right, bg=PANEL, highlightthickness=0, width=self.px(332), height=self.px(300)
        )
        self.d_canvas.pack(padx=14, pady=10)
        controls = ttk.Frame(right, style="Panel.TFrame")
        controls.pack(fill="x", padx=14)
        self.zoom = tk.StringVar(value="맞춤")
        ttk.Combobox(
            controls,
            textvariable=self.zoom,
            state="readonly",
            width=7,
            values=("맞춤", "1x", "2x", "4x", "8x"),
        ).pack(side="left")
        self.backdrop = tk.StringVar(value="체크")
        ttk.Combobox(
            controls,
            textvariable=self.backdrop,
            state="readonly",
            width=7,
            values=("체크", "어둡게", "밝게", "잔디"),
        ).pack(side="left", padx=6)
        self.zoom.trace_add("write", lambda *_: self.show_detail())
        self.backdrop.trace_add("write", lambda *_: self.show_detail())
        self.d_info = ttk.Label(
            right, style="Panel.TLabel", justify="left", wraplength=self.px(330)
        )
        self.d_info.pack(anchor="w", padx=14, pady=(12, 6))
        buttons = ttk.Frame(right, style="Panel.TFrame")
        buttons.pack(fill="x", padx=14, pady=(4, 0))
        self.d_buttons = [
            ttk.Button(
                buttons,
                text="Aseprite에서 열기",
                style="Accent.TButton",
                command=lambda: self._with_focus(self.open_asset),
            ),
            ttk.Button(
                buttons, text="탐색기에서 보기", command=lambda: self._with_focus(self.reveal)
            ),
            ttk.Button(buttons, text="경로 복사", command=lambda: self._with_focus(self.copy_path)),
        ]
        for button in self.d_buttons:
            button.pack(fill="x", pady=3)
        self._set_detail_buttons(False)

    def _placeholder(self, entry: ttk.Entry, hint: str) -> None:
        """Grey hint text in an empty search box (Tk has none built in)."""

        def show(_: object = None) -> None:
            if not self.query.get() and self.window.focus_get() is not entry:
                entry.configure(foreground=MUTED)
                entry.delete(0, "end")
                entry.insert(0, hint)
                self._hint_on = True

        def hide(_: object = None) -> None:
            if getattr(self, "_hint_on", False):
                self._hint_on = False
                entry.delete(0, "end")
                entry.configure(foreground=TEXT)

        self._hint_on = False
        self._hint = hint
        entry.bind("<FocusIn>", hide)
        entry.bind("<FocusOut>", show)
        self.window.after(10, show)

    def _search_text(self) -> str:
        return "" if self._hint_on else self.query.get().strip().casefold()

    def _bind_keys(self) -> None:
        w = self.window
        w.bind("<Control-f>", lambda _: (self.search.focus_set(), "break")[1])
        w.bind("<F5>", lambda _: self.reload())
        w.bind("<Escape>", self._escape)
        for key, step in (("<Left>", -1), ("<Right>", 1)):
            w.bind(key, lambda e, s=step: self._arrow(e, s))
        w.bind("<Up>", lambda e: self._arrow(e, -self.columns))
        w.bind("<Down>", lambda e: self._arrow(e, self.columns))
        w.bind("<Control-a>", self._select_all_key)
        w.bind("<Delete>", self._delete_key)
        w.bind("<Return>", self._enter_key)

    def _typing(self, event: tk.Event) -> bool:
        return isinstance(event.widget, (tk.Entry, ttk.Entry, ttk.Combobox))

    # --- data -----------------------------------------------------------------
    def reload(self) -> None:
        self.assets = collect()
        self.last_signature = signature()
        stamps = {a.stamp for a in self.assets}
        self.images = {k: v for k, v in self.images.items() if k in stamps}
        self.thumbs = {k: v for k, v in self.thumbs.items() if k[0] in stamps}
        self.loader.asked &= stamps
        live = {a.key for a in self.assets}
        self.selected &= live
        for asset in self.assets:
            pair = asset.pair
            if pair is None:
                continue
            if pair in self.differs:
                asset.stale = self.differs[pair]
            else:
                self.loader.compare(pair)
        self._fill_tree()
        self._relayout()

    def _fill_tree(self) -> None:
        chosen = self.tree.selection()
        keep = chosen[0] if chosen else ""
        self.tree.delete(*self.tree.get_children())
        counts: dict[str, int] = {}
        for asset in self.assets:
            parts = asset.folder.split("/") if asset.folder else []
            for depth in range(len(parts) + 1):
                path = "/".join(parts[:depth])
                counts[path] = counts.get(path, 0) + 1
        self.tree.insert("", "end", iid=ALL, text=f"  전체  ({counts.get('', 0)})", open=True)
        for path in sorted(p for p in counts if p):
            parent = path.rpartition("/")[0] or ALL
            name = path.rpartition("/")[2]
            self.tree.insert(
                parent, "end", iid=path, text=f"  {name}  ({counts[path]})", open=parent == ALL
            )
        target = keep if keep and self.tree.exists(keep) else ALL
        self.tree.selection_set(target)
        self.tree.see(target)

    def _visible_assets(self) -> list[Asset]:
        chosen = self.tree.selection()
        folder = chosen[0] if chosen and chosen[0] != ALL else ""
        text = self._search_text()
        mode = self.filter.get()
        out = []
        for asset in self.assets:
            if folder and not (asset.folder == folder or asset.folder.startswith(folder + "/")):
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
        out.sort(key=SORTS.get(self.sort.get(), SORTS["폴더순"]))
        return out

    # --- grid layout and drawing ----------------------------------------------
    def _relayout(self, reset: bool = False) -> None:
        if self.layout_pending:
            self.window.after_cancel(self.layout_pending)
        self.layout_pending = self.window.after(60, lambda: self._layout(reset))

    def _layout(self, reset: bool) -> None:
        self.layout_pending = None
        focused = (
            self.shown[self.focus].key
            if self.focus is not None and self.focus < len(self.shown)
            else None
        )
        self.shown = self._visible_assets()
        index = {a.key: i for i, a in enumerate(self.shown)}
        self.focus = index.get(focused) if focused is not None else None
        self.anchor = None if reset else self.anchor
        width = max(1, self.canvas.winfo_width())
        thumb = self.px(int(self.size.get()))
        self.thumbs = {k: v for k, v in self.thumbs.items() if k[1] == thumb}
        gap = self.px(12)
        min_w = thumb + self.px(16)
        self.columns = max(1, (width + gap) // (min_w + gap))
        # spread the spare width across the cards so the grid fills the row
        card_w = (width - gap * (self.columns - 1)) // self.columns
        card_h = thumb + self.px(88)
        self.cell = (card_w + gap, card_h + gap)
        self.card = (card_w, card_h)
        rows = -(-len(self.shown) // self.columns)
        self.canvas.configure(scrollregion=(0, 0, width, max(1, rows * self.cell[1])))
        if reset:
            self.canvas.yview_moveto(0)
        self._update_status()
        self.show_detail()
        self._draw()

    def _schedule_draw(self) -> None:
        if not self.draw_pending:
            self.draw_pending = self.window.after(16, self._draw)

    def _draw(self) -> None:
        self.draw_pending = None
        canvas = self.canvas
        canvas.delete("all")
        if not self.shown:
            canvas.create_text(
                canvas.winfo_width() // 2,
                self.px(80),
                fill=MUTED,
                font=(FONT, 12),
                text="보여 줄 에셋이 없어요. 검색어나 필터를 바꿔 보세요.",
            )
            return
        top = canvas.canvasy(0)
        bottom = top + canvas.winfo_height()
        first_row = max(0, int(top // self.cell[1]))
        last_row = int(bottom // self.cell[1]) + 1
        start = first_row * self.columns
        stop = min(len(self.shown), (last_row + 1) * self.columns)
        for i in range(start, stop):
            self._draw_card(i)

    def _card_box(self, i: int) -> tuple[int, int, int, int]:
        row, col = divmod(i, self.columns)
        x, y = col * self.cell[0], row * self.cell[1]
        return x, y, x + self.card[0], y + self.card[1]

    def _draw_card(self, i: int) -> None:
        asset = self.shown[i]
        c = self.canvas
        x0, y0, x1, y1 = self._card_box(i)
        chosen = asset.key in self.selected
        fill = CARD_HOVER if i == self.hover else CARD
        c.create_rectangle(
            x0,
            y0,
            x1,
            y1,
            fill=fill,
            outline=ACCENT if chosen else LINE,
            width=self.px(3) if chosen else 1,
        )
        thumb = self.px(int(self.size.get()))
        tx = x0 + (self.card[0] - thumb) // 2
        ty = y0 + self.px(8)
        photo = self._thumb(asset, thumb)
        if isinstance(photo, ImageTk.PhotoImage):
            c.create_image(tx, ty, image=photo, anchor="nw")
        else:
            c.create_rectangle(tx, ty, tx + thumb, ty + thumb, fill=PANEL, outline="")
            c.create_text(
                tx + thumb // 2,
                ty + thumb // 2,
                text=photo,
                width=thumb - 8,
                fill=DANGER if photo.startswith("오류") else MUTED,
                font=(FONT, 9),
            )
        pad = self.px(8)
        c.create_text(
            x0 + pad,
            ty + thumb + self.px(6),
            anchor="nw",
            text=asset.name,
            fill=TEXT,
            font=(FONT, 10, "bold"),
            width=self.card[0] - 2 * pad,
        )
        c.create_text(
            x0 + pad,
            ty + thumb + self.px(30),
            anchor="nw",
            text=self._fit_text(asset.folder or "assets", self.card[0] - 2 * pad),
            fill=MUTED,
            font=(FONT, 8),
        )
        # badges along the bottom
        bx = x0 + pad
        by = y1 - self.px(24)
        for label, colour in self._badges(asset):
            text_id = c.create_text(
                bx + self.px(5),
                by + self.px(1),
                anchor="nw",
                text=label,
                fill="#ffffff",
                font=(FONT, 7, "bold"),
            )
            bx0, by0, bx1, by1 = c.bbox(text_id)
            rect = c.create_rectangle(
                bx0 - self.px(4), by0 - 1, bx1 + self.px(4), by1 + 1, fill=colour, outline=""
            )
            c.tag_lower(rect, text_id)
            bx = bx1 + self.px(8)
        if chosen:
            c.create_oval(
                x1 - self.px(22),
                y0 + self.px(6),
                x1 - self.px(6),
                y0 + self.px(22),
                fill=ACCENT,
                outline="",
            )
            c.create_text(
                x1 - self.px(14), y0 + self.px(14), text="✓", fill=BG, font=(FONT, 8, "bold")
            )

    def _fit_text(self, text: str, width: int) -> str:
        """One line, cut from the FRONT: the end of a path is the telling part."""
        if not hasattr(self, "_small"):
            self._small = tkfont.Font(family=FONT, size=8)
        if self._small.measure(text) <= width:
            return text
        while text and self._small.measure("…" + text) > width:
            text = text[1:]
        return "…" + text

    def _badges(self, asset: Asset) -> list[tuple[str, str]]:
        out = [
            (ext[1:].upper()[:4].replace("ASEP", "ASE"), BADGE.get(ext, "#556"))
            for ext in ALL_EXTS
            if ext in asset.files
        ]
        if asset.stale:
            out.append(("갱신 필요", "#a8701f"))
        if asset.used:
            out.append(("게임", "#3d6e3a"))
        return out

    def _thumb(self, asset: Asset, size: int) -> ImageTk.PhotoImage | str:
        stamp = asset.stamp
        got = self.images.get(stamp)
        if got is None:
            self.loader.ask(stamp)
            return "불러오는 중…"
        if isinstance(got, str):
            return f"오류: {got[:60]}"
        key = (stamp, size)
        photo = self.thumbs.get(key)
        if photo is None:
            board = self._board(size)
            art = fit(got, size - 8, size - 8)
            board.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
            photo = self.thumbs[key] = ImageTk.PhotoImage(board)
        return photo

    _boards: dict[int, Image.Image] = {}

    def _board(self, size: int) -> Image.Image:
        if size not in self._boards:
            self._boards[size] = checker(size, size, max(6, size // 12), "#252e3b", "#2e3948")
        return self._boards[size].copy()

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
                pair = asset.pair
                if pair in self.differs:
                    asset.stale = self.differs[pair]
            self._update_status()
            if self.filter.get() == "갱신 필요":
                self._relayout()
            arrived.add(("", 0.0))  # redraw for the badges
        if arrived:
            self._schedule_draw()
            focus = self._focused()
            if focus is not None and focus.stamp in arrived:
                self.show_detail()
        self.window.after(50, self._poll_images)

    def _watch(self) -> None:
        """Pick up files changed by other tools (or other tabs) without F5."""
        try:
            if signature() != self.last_signature:
                self.reload()
        finally:
            self.window.after(REFRESH_MS, self._watch)

    # --- scrolling --------------------------------------------------------------
    def _yview(self, *args: str) -> None:
        self.canvas.yview(*args)
        self._schedule_draw()

    def _on_scroll(self, first: str, last: str) -> None:
        self.scroll.set(first, last)
        self._schedule_draw()

    def _wheel(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(-int(event.delta / 120) * 2, "units")
        self._schedule_draw()

    def _ensure_visible(self, i: int) -> None:
        _, y0, _, y1 = self._card_box(i)
        total = max(1, -(-len(self.shown) // self.columns) * self.cell[1])
        top = self.canvas.canvasy(0)
        height = self.canvas.winfo_height()
        if y0 < top:
            self.canvas.yview_moveto(y0 / total)
        elif y1 > top + height:
            self.canvas.yview_moveto((y1 - height) / total)
        self._schedule_draw()

    # --- selection --------------------------------------------------------------
    def _index_at(self, event: tk.Event) -> int | None:
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        col, row = int(x // self.cell[0]), int(y // self.cell[1])
        if col >= self.columns:
            return None
        i = row * self.columns + col
        if i >= len(self.shown):
            return None
        x0, y0, x1, y1 = self._card_box(i)
        return i if x0 <= x <= x1 and y0 <= y <= y1 else None

    def _click(self, event: tk.Event) -> None:
        self.canvas.focus_set()
        i = self._index_at(event)
        if i is None:
            return
        key = self.shown[i].key
        if event.state & 0x1 and self.anchor is not None:  # Shift: a run
            lo, hi = sorted((self.anchor, i))
            self.selected.update(a.key for a in self.shown[lo : hi + 1])
        elif event.state & 0x4:  # Ctrl: toggle one
            self.selected.symmetric_difference_update({key})
            self.anchor = i
        else:
            self.selected = {key}
            self.anchor = i
        self.focus = i
        self._after_selection()

    def _double(self, event: tk.Event) -> None:
        i = self._index_at(event)
        if i is not None:
            self.open_asset(self.shown[i])

    def _motion(self, event: tk.Event) -> None:
        self._set_hover(self._index_at(event))

    def _set_hover(self, i: int | None) -> None:
        if i != self.hover:
            self.hover = i
            self.canvas.configure(cursor="hand2" if i is not None else "")
            self._schedule_draw()

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
            self.canvas.focus_set()
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
        self.canvas.focus_set()

    def select_shown(self) -> None:
        self.selected = {a.key for a in self.shown}
        self._after_selection()

    def clear_selection(self) -> None:
        self.selected.clear()
        self._after_selection()

    def _after_selection(self) -> None:
        self._update_status()
        self.show_detail()
        self._schedule_draw()

    def _focused(self) -> Asset | None:
        if self.focus is None or self.focus >= len(self.shown):
            return None
        return self.shown[self.focus]

    def _update_status(self) -> None:
        stale = sum(1 for a in self.shown if a.stale)
        parts = [f"{len(self.shown)} / {len(self.assets)}개 표시"]
        pending = sum(1 for a in self.assets if a.pair and a.pair not in self.differs)
        if pending:
            parts.append(f"원본과 비교 중 {pending}개")
        if stale:
            parts.append(f"갱신 필요 {stale}개")
        parts.append(f"선택 {len(self.selected)}개")
        parts.append("Ctrl+클릭 여러 개 · Shift+클릭 범위 · 더블클릭 Aseprite · 우클릭 메뉴")
        self.status.configure(text="   ·   ".join(parts))
        state = "normal" if self.selected else "disabled"
        self.delete_button.configure(text=f"선택 삭제 ({len(self.selected)})", state=state)

    # --- the detail panel ---------------------------------------------------------
    def _set_detail_buttons(self, on: bool) -> None:
        for button in self.d_buttons:
            button.configure(state="normal" if on else "disabled")

    def _with_focus(self, action) -> None:  # type: ignore[no-untyped-def]
        focus = self._focused()
        if focus is not None:
            action(focus)

    def show_detail(self) -> None:
        asset = self._focused()
        c = self.d_canvas
        c.delete("all")
        self.detail_photo = None
        if asset is None:
            self.d_title.configure(text="선택한 에셋 없음")
            self.d_path.configure(text="에셋을 클릭하면 여기에 크게 보여요.")
            self.d_info.configure(text="")
            self._set_detail_buttons(False)
            return
        self._set_detail_buttons(True)
        self.d_title.configure(text=asset.name)
        self.d_path.configure(text=f"assets/{asset.rel}")
        w, h = int(c["width"]), int(c["height"])
        backdrop = self.backdrop.get()
        if backdrop == "체크":
            board = checker(w, h, self.px(10), "#252e3b", "#2e3948")
        else:
            colour = {"어둡게": "#0d1117", "밝게": "#e9edf2", "잔디": "#6f8f4e"}[backdrop]
            board = Image.new("RGBA", (w, h), colour)
        image = self.images.get(asset.stamp)
        dims = "불러오는 중…"
        if image is None:
            self.loader.ask(asset.stamp)
        elif isinstance(image, str):
            dims = f"미리보기 오류: {image}"
        else:
            zoom = self.zoom.get()
            scale = None if zoom == "맞춤" else float(zoom[:-1])
            art = fit(image, w - 16, h - 16, scale)
            # too big for the box at a fixed zoom: show the middle of it
            left = max(0, (art.width - w) // 2)
            top = max(0, (art.height - h) // 2)
            art = art.crop((left, top, left + min(art.width, w), top + min(art.height, h)))
            board.alpha_composite(art, ((w - art.width) // 2, (h - art.height) // 2))
            dims = f"{image.width} × {image.height} px"
        self.detail_photo = ImageTk.PhotoImage(board)
        c.create_image(0, 0, image=self.detail_photo, anchor="nw")
        lines = [dims, ""]
        for ext in ALL_EXTS:
            if ext in asset.files:
                path = asset.files[ext]
                when = time.strftime("%m-%d %H:%M", time.localtime(asset.mtimes[ext]))
                size = path.stat().st_size if path.exists() else 0
                lines.append(f"{ext[1:].upper():<9} {size / 1024:6.1f} KB   {when}")
        if asset.stale:
            lines += [
                "",
                "⚠ Aseprite 원본과 이미지가 달라요.",
                "  다시 내보내야 게임에 반영돼요.",
            ]
        if asset.used:
            lines += [
                "",
                "● 게임 코드나 타일셋에 이 이름이 나와요.",
                "  지우면 게임이 실행되지 않을 수 있어요.",
            ]
        if ".aseprite" not in asset.files:
            lines += ["", "Aseprite 원본이 없어요."]
        self.d_info.configure(text="\n".join(lines))

    # --- actions ------------------------------------------------------------------
    def open_asset(self, asset: Asset) -> None:
        path = asset.files.get(".aseprite") or next(iter(asset.files.values()))
        try:
            subprocess.Popen([str(ASEPRITE), str(path)])
        except OSError as error:
            messagebox.showerror("열기 실패", str(error), parent=self.window)

    def reveal(self, asset: Asset) -> None:
        path = asset.files.get(".aseprite") or next(iter(asset.files.values()))
        subprocess.Popen(["explorer", "/select,", str(path)])

    def copy_path(self, asset: Asset) -> None:
        path = asset.files.get(".aseprite") or next(iter(asset.files.values()))
        self.window.clipboard_clear()
        self.window.clipboard_append(str(path))
        self.status.configure(text=f"경로를 복사했어요: {path}")

    def _context(self, event: tk.Event) -> None:
        i = self._index_at(event)
        if i is None:
            return
        asset = self.shown[i]
        if asset.key not in self.selected:
            self.selected = {asset.key}
            self.anchor = i
        self.focus = i
        self._after_selection()
        menu = tk.Menu(
            self.window,
            tearoff=0,
            bg=CARD,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=BG,
            font=(FONT, 10),
            bd=0,
        )
        menu.add_command(label="Aseprite에서 열기", command=lambda: self.open_asset(asset))
        menu.add_command(label="탐색기에서 보기", command=lambda: self.reveal(asset))
        menu.add_command(label="경로 복사", command=lambda: self.copy_path(asset))
        menu.add_separator()
        menu.add_command(label=f"삭제 ({len(self.selected)}개)…", command=self.confirm_delete)
        menu.tk_popup(event.x_root, event.y_root)

    def confirm_delete(self) -> None:
        chosen = [a for a in self.assets if a.key in self.selected]
        targets = sorted(p for a in chosen for p in a.files.values())
        if not targets:
            return
        used = [a for a in chosen if a.used]
        dialog = tk.Toplevel(self.window, bg=BG)
        dialog.title("휴지통으로 보내기")
        dialog.geometry(f"{self.px(720)}x{self.px(540)}")
        dialog.transient(self.window)
        head = f"{len(chosen)}개 에셋 · 파일 {len(targets)}개를 휴지통으로 보냅니다."
        ttk.Label(dialog, text=head, style="Title.TLabel").pack(anchor="w", padx=16, pady=(16, 4))
        ttk.Label(
            dialog,
            style="Muted.TLabel",
            text=(
                "같은 이름으로 묶인 Aseprite·PNG·WebP 파일이 함께 지워져요. "
                "휴지통에서 되살릴 수 있어요."
            ),
        ).pack(anchor="w", padx=16)
        if used:
            names = ", ".join(a.name for a in used[:8]) + (" …" if len(used) > 8 else "")
            warn = tk.Label(
                dialog,
                bg="#3a2a14",
                fg=WARN,
                font=(FONT, 10, "bold"),
                justify="left",
                anchor="w",
                wraplength=self.px(680),
                padx=12,
                pady=8,
                text=f"⚠ 게임에서 쓰는 것으로 보이는 에셋 {len(used)}개: {names}\n"
                "지우면 게임이 실행되지 않을 수 있어요.",
            )
            warn.pack(fill="x", padx=16, pady=(10, 0))
        body = ttk.Frame(dialog)
        body.pack(fill="both", expand=True, padx=16, pady=10)
        listing = tk.Text(
            body,
            wrap="none",
            bg=PANEL,
            fg=TEXT,
            relief="flat",
            font=("Consolas", 10),
            padx=8,
            pady=6,
        )
        bar = ttk.Scrollbar(body, command=listing.yview)
        bar.pack(side="right", fill="y")
        listing.pack(fill="both", expand=True)
        listing.configure(yscrollcommand=bar.set)
        listing.insert("1.0", "\n".join(p.relative_to(ROOT).as_posix() for p in targets))
        listing.configure(state="disabled")
        buttons = ttk.Frame(dialog, padding=(16, 0, 16, 16))
        buttons.pack(fill="x")

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

        ttk.Button(buttons, text="휴지통으로 이동", style="Danger.TButton", command=execute).pack(
            side="right"
        )
        cancel = ttk.Button(buttons, text="취소", command=dialog.destroy)
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
