"""Local asset gallery. Run with python dev/asset_gallery.py."""
from pathlib import Path
import os
import ctypes
from ctypes import wintypes
import subprocess
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / 'assets'
ASEPRITE = Path(os.environ.get('ASEPRITE', r'C:\Users\ykb62\Desktop\aseprite.exe'))


def recycle_file(path):
    """Move one validated asset to the Windows Recycle Bin."""
    path = path.resolve(strict=True)
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError(f'에셋 폴더 밖의 파일은 삭제할 수 없습니다: {path}')
    class FileOperation(ctypes.Structure):
        _fields_ = [('hwnd', wintypes.HWND), ('wFunc', wintypes.UINT),
                    ('pFrom', wintypes.LPCWSTR), ('pTo', wintypes.LPCWSTR),
                    ('fFlags', wintypes.WORD), ('fAnyOperationsAborted', wintypes.BOOL),
                    ('hNameMappings', ctypes.c_void_p), ('lpszProgressTitle', wintypes.LPCWSTR)]
    operation = FileOperation()
    names = ctypes.create_unicode_buffer(str(path) + '\0\0')
    operation.wFunc = 3  # FO_DELETE
    operation.pFrom = ctypes.cast(names, wintypes.LPCWSTR)
    operation.fFlags = 0x40 | 0x10 | 0x4 | 0x400  # undo, no confirmation, silent, no error UI
    shell = ctypes.windll.shell32.SHFileOperationW
    shell.argtypes = [ctypes.POINTER(FileOperation)]
    shell.restype = ctypes.c_int
    result = shell(ctypes.byref(operation))
    if result or operation.fAnyOperationsAborted or path.exists():
        raise OSError(f'휴지통 이동 실패 ({result}): {path.name}')


def collect():
    entries = {}
    for extension in ('.aseprite', '.png', '.webp', '.gif', '.jpg', '.bmp'):
        for path in sorted(ROOT.rglob('*' + extension)):
            entries.setdefault(path.with_suffix(''), {})[extension] = path
    return list(entries.items())


class Gallery:
    def __init__(self, window):
        self.window = window
        self.cache_dir = tempfile.TemporaryDirectory(prefix='pygame-gallery-')
        self.entries = collect()
        self.images = {}
        self.photos = []
        self.pending = None
        self.selected = set()
        self.selection_mode = tk.BooleanVar(value=False)
        window.title('에셋 갤러리 · Pygame Project')
        window.geometry('1380x900')
        window.minsize(760, 500)
        window.configure(bg='#171c25')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#171c25')
        style.configure('TLabel', background='#171c25', foreground='#e3eaf3', font=('맑은 고딕', 10))
        top = ttk.Frame(window, padding=20)
        top.pack(fill='x')
        ttk.Label(top, text='ASSET LIBRARY', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(top, text='클릭: 크게 보기  ·  더블클릭: Aseprite에서 열기  ·  휠: 스크롤').pack(anchor='w', pady=(4, 16))
        bar = ttk.Frame(top)
        bar.pack(fill='x')
        self.query = tk.StringVar()
        ttk.Label(bar, text='검색 ').pack(side='left')
        ttk.Entry(bar, textvariable=self.query, width=30).pack(side='left', padx=(0, 16))
        self.group = tk.StringVar(value='전체')
        groups = sorted({str(key.relative_to(ROOT).parts[0]) for key, _ in self.entries})
        ttk.Combobox(bar, textvariable=self.group, values=['전체', *groups], state='readonly', width=18).pack(side='left')
        ttk.Label(bar, text='   크기 ').pack(side='left')
        self.size = tk.IntVar(value=160)
        ttk.Scale(bar, from_=96, to=256, variable=self.size, command=lambda _: self.schedule()).pack(side='left', fill='x', expand=True)
        self.count = ttk.Label(top)
        self.count.pack(anchor='w', pady=(12, 0))
        actions = ttk.Frame(top)
        actions.pack(fill='x', pady=(10, 0))
        ttk.Checkbutton(actions, text='파일 선택 모드', variable=self.selection_mode).pack(side='left')
        ttk.Button(actions, text='현재 목록 모두 선택', command=self.select_visible).pack(side='left', padx=8)
        ttk.Button(actions, text='선택 해제', command=self.clear_selection).pack(side='left')
        self.delete_button = ttk.Button(actions, text='선택 삭제 (0)', command=self.confirm_delete, state='disabled')
        self.delete_button.pack(side='right')
        self.canvas = tk.Canvas(window, bg='#171c25', highlightthickness=0)
        scroll = ttk.Scrollbar(window, orient='vertical', command=self.canvas.yview)
        scroll.pack(side='right', fill='y')
        self.canvas.pack(fill='both', expand=True)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.bind('<Configure>', lambda _: self.schedule())
        self.canvas.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(-int(e.delta / 120), 'units'))
        self.query.trace_add('write', lambda *_: self.schedule())
        self.group.trace_add('write', lambda *_: self.schedule())
        self.schedule()

    def schedule(self):
        if self.pending:
            self.window.after_cancel(self.pending)
        self.pending = self.window.after(180, self.render)

    def visible_entries(self):
        query = self.query.get().casefold()
        return [(k, f) for k, f in self.entries if query in str(k.relative_to(ROOT)).casefold()
                and (self.group.get() == '전체' or k.relative_to(ROOT).parts[0] == self.group.get())]

    def select_visible(self):
        self.selection_mode.set(True)
        self.selected.update(k for k, _ in self.visible_entries())
        self.schedule()

    def clear_selection(self):
        self.selected.clear()
        self.schedule()

    def click_asset(self, event, key, files):
        if self.selection_mode.get() or event.state & 0x4:
            if key in self.selected:
                self.selected.remove(key)
            else:
                self.selected.add(key)
            self.schedule()
        else:
            self.detail(key, files)

    def confirm_delete(self):
        targets = sorted({p for key, files in self.entries if key in self.selected for p in files.values()})
        if not targets:
            return
        dialog = tk.Toplevel(self.window)
        dialog.title('선택한 에셋 삭제 확인')
        dialog.geometry('720x520')
        dialog.transient(self.window)
        ttk.Label(dialog, text=f'{len(self.selected)}개 에셋 · {len(targets)}개 파일을 휴지통으로 보냅니다.\n같은 이름으로 묶인 PNG·WebP·Aseprite 파일이 함께 삭제됩니다.\n게임에서 사용하는 파일을 삭제하면 실행에 영향을 줄 수 있습니다.', padding=16).pack(fill='x')
        body = ttk.Frame(dialog)
        body.pack(fill='both', expand=True, padx=16)
        listing = tk.Text(body, wrap='none')
        scrollbar = ttk.Scrollbar(body, command=listing.yview)
        scrollbar.pack(side='right', fill='y')
        listing.pack(fill='both', expand=True)
        listing.configure(yscrollcommand=scrollbar.set)
        listing.insert('1.0', '\n'.join(str(p.relative_to(ROOT)) for p in targets))
        listing.configure(state='disabled')
        buttons = ttk.Frame(dialog, padding=16)
        buttons.pack(fill='x')
        def execute():
            dialog.destroy()
            errors = []
            for path in targets:
                try:
                    recycle_file(path)
                except Exception as error:
                    errors.append(str(error))
            self.entries = collect()
            self.images.clear()
            self.selected.clear()
            if hasattr(self, 'detail_window') and self.detail_window.winfo_exists():
                self.detail_window.destroy()
            self.schedule()
            if errors:
                messagebox.showerror('삭제하지 못한 파일', '\n'.join(errors), parent=self.window)
        ttk.Button(buttons, text='휴지통으로 이동', command=execute).pack(side='right')
        cancel = ttk.Button(buttons, text='취소', command=dialog.destroy)
        cancel.pack(side='right', padx=12)
        cancel.focus_set()
        dialog.bind('<Escape>', lambda _: dialog.destroy())
        dialog.grab_set()

    def load(self, key, files):
        if key in self.images:
            return self.images[key]
        path = next((files[e] for e in ('.png', '.webp', '.gif', '.jpg', '.bmp') if e in files), None)
        if path is None:
            path = Path(self.cache_dir.name) / f'{len(self.images)}.png'
            subprocess.run([str(ASEPRITE), '--batch', '--frame-range', '0,0', str(files['.aseprite']), '--save-as', str(path)], check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        with Image.open(path) as opened:
            image = opened.convert('RGBA')
        self.images[key] = image
        return image

    @staticmethod
    def preview(image, width, height):
        board = Image.new('RGBA', (width, height), '#252e3b')
        draw = ImageDraw.Draw(board)
        for y in range(0, height, 12):
            for x in range(0, width, 12):
                if (x // 12 + y // 12) % 2:
                    draw.rectangle((x, y, x + 11, y + 11), fill='#303b4a')
        scale = min((width - 16) / image.width, (height - 16) / image.height)
        resized = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.NEAREST)
        board.alpha_composite(resized, ((width - resized.width) // 2, (height - resized.height) // 2))
        return ImageTk.PhotoImage(board)

    def render(self):
        self.pending = None
        self.canvas.delete('all')
        self.photos.clear()
        entries = self.visible_entries()
        self.delete_button.configure(text=f'선택 삭제 ({len(self.selected)})', state='normal' if self.selected else 'disabled')
        self.count.config(text=f'{len(entries)} / {len(self.entries)} 에셋 · 동일 이름의 이미지와 Aseprite는 하나로 표시')
        size = int(self.size.get())
        cell_w, cell_h = size + 30, size + 76
        columns = max(1, (self.canvas.winfo_width() - 20) // cell_w)
        for index, (key, files) in enumerate(entries):
            x, y = 20 + (index % columns) * cell_w, 10 + (index // columns) * cell_h
            tag = f'asset{index}'
            if key in self.selected:
                self.canvas.create_rectangle(x - 4, y - 4, x + size + 4, y + size + 66,
                                             outline='#69dbb1', width=3, tags=tag)
            try:
                source = self.load(key, files)
                photo = self.preview(source, size, size)
                self.photos.append(photo)
                self.canvas.create_image(x, y, image=photo, anchor='nw', tags=tag)
                dimensions = f'{source.width} × {source.height}'
            except Exception as error:
                self.canvas.create_text(x + size / 2, y + size / 2, text='미리보기 오류', fill='#ff8c8c', tags=tag)
                dimensions = str(error)[:30]
            self.canvas.create_text(x, y + size + 9, text=key.name, anchor='nw', fill='#edf3fc', font=('Segoe UI', 10, 'bold'), width=size, tags=tag)
            self.canvas.create_text(x, y + size + 43, text=dimensions, anchor='nw', fill='#96a7bd', font=('Segoe UI', 9), tags=tag)
            self.canvas.tag_bind(tag, '<Button-1>', lambda e, k=key, f=files: self.click_asset(e, k, f))
            self.canvas.tag_bind(tag, '<Double-Button-1>', lambda _, f=files: self.open_asset(f))
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), ((len(entries) + columns - 1) // columns) * cell_h + 20))

    def open_asset(self, files):
        path = files.get('.aseprite') or next(iter(files.values()))
        try:
            subprocess.Popen([str(ASEPRITE), str(path)])
        except OSError as error:
            messagebox.showerror('열기 실패', str(error))

    def detail(self, key, files):
        if hasattr(self, 'detail_window') and self.detail_window.winfo_exists():
            self.detail_window.destroy()
        dialog = self.detail_window = tk.Toplevel(self.window)
        dialog.title(key.name)
        dialog.configure(bg='#171c25')
        try:
            source = self.load(key, files)
            photo = self.preview(source, 600, 540)
            label = tk.Label(dialog, image=photo, borderwidth=0)
            label.image = photo
            label.pack(padx=16, pady=16)
            ttk.Label(dialog, text=f'{key.relative_to(ROOT)}\n{source.width} × {source.height} px', wraplength=580).pack(padx=16, pady=8)
            ttk.Button(dialog, text='Aseprite에서 열기', command=lambda: self.open_asset(files)).pack(pady=16)
            dialog.bind('<Escape>', lambda _: dialog.destroy())
        except Exception as error:
            dialog.destroy()
            messagebox.showerror('미리보기 실패', str(error))


if __name__ == '__main__':
    window = tk.Tk()
    Gallery(window)
    window.mainloop()
