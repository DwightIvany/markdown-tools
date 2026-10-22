#!/usr/bin/env python3
"""MarkMe - drag documents into the window, get Markdown beside each one.

Drop one or more files anywhere in the MarkMe window. Each file is converted
to <name>.md in the same folder using pandoc, and the result is shown in the
list. Drop uses plain ctypes (WM_DROPFILES) - no extra packages to install.
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk

APP_TITLE = "MarkMe"

# extension -> pandoc reader
READERS = {
    ".csv": "csv",
    ".docx": "docx",
    ".epub": "epub",
    ".htm": "html",
    ".html": "html",
    ".latex": "latex",
    ".odt": "odt",
    ".org": "org",
    ".rst": "rst",
    ".rtf": "rtf",
    ".tex": "latex",
    ".text": "markdown",
    ".textile": "textile",
    ".tsv": "tsv",
    ".txt": "markdown",
}

# extension -> friendly message instead of converting
NOT_CONVERTIBLE = {
    ".markdown": "already Markdown",
    ".md": "already Markdown",
    ".pdf": "pandoc does not read PDF - see software/python/convert-to-md.py",
    ".ppsx": "PowerPoint input is not supported by your pandoc version",
    ".ppt": "PowerPoint input is not supported by your pandoc version",
    ".pptx": "PowerPoint input is not supported by your pandoc version",
    ".xls": "spreadsheets are not supported - save as .csv and drop the .csv",
    ".xlsx": "spreadsheets are not supported - save as .csv and drop the .csv",
}


def find_pandoc() -> str | None:
    """Locate pandoc.exe: PANDOC env var, PATH, then common install spots."""
    env = os.environ.get("PANDOC")
    if env and Path(env).is_file():
        return env
    on_path = shutil.which("pandoc")
    if on_path:
        return on_path
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Pandoc" / "pandoc.exe",
        Path.home() / "AppData" / "Local" / "Pandoc" / "pandoc.exe",
        Path(r"C:\Program Files\Pandoc\pandoc.exe"),
    ]
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return None


def find_soffice() -> str | None:
    """Locate soffice.exe (LibreOffice): SOFFICE env var, PATH, then common install spots."""
    env = os.environ.get("SOFFICE")
    if env and Path(env).is_file():
        return env
    on_path = shutil.which("soffice")
    if on_path:
        return on_path
    candidates = [
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    ]
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return None


def convert_file(pandoc: str, soffice: str | None, path: Path, force: bool) -> tuple[bool, str]:
    """Convert one file. Returns (ok, message) - message is a note or error."""
    ext = path.suffix.lower()
    if ext in NOT_CONVERTIBLE:
        return False, NOT_CONVERTIBLE[ext]
    reader = READERS.get(ext)  # None: let pandoc guess from the extension

    out = path.with_suffix(".md")
    if out.exists() and not force:
        return False, f"skipped ({out.name} exists - turn on Overwrite)"

    # pandoc does not read legacy .doc: have LibreOffice turn it into a
    # temp .docx first. A private profile keeps the conversion synchronous
    # even when LibreOffice is already running.
    source = path
    tmpdir = None
    if ext == ".doc":
        if not soffice:
            return False, "LibreOffice not found - install it to convert .doc, or save the file as .docx"
        tmpdir = Path(tempfile.mkdtemp(prefix="markme-"))
        source = tmpdir / (path.stem + ".docx")
        try:
            proc = subprocess.run(
                [soffice, f"-env:UserInstallation=file:///{(tmpdir / 'loprofile').as_posix()}",
                 "--headless", "--convert-to", "docx", "--outdir", str(tmpdir), str(path)],
                capture_output=True, text=True,
            )
        except OSError as exc:
            shutil.rmtree(tmpdir, ignore_errors=True)
            return False, f"LibreOffice failed to start: {exc}"
        if proc.returncode != 0 or not source.is_file():
            shutil.rmtree(tmpdir, ignore_errors=True)
            detail = (proc.stderr or proc.stdout or "conversion failed").strip().splitlines()
            return False, f"LibreOffice: {detail[0] if detail else 'conversion failed'}"

    media = out.parent / (out.stem + "_media")
    cmd = [pandoc, "--to=gfm", "--wrap=none", f"--extract-media={media}"]
    if reader:
        cmd.append(f"--from={reader}")
    cmd += ["--output", str(out), str(source)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
        return False, f"pandoc failed to start: {exc}"
    if tmpdir:
        shutil.rmtree(tmpdir, ignore_errors=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "unknown error").strip().splitlines()
        return False, f"pandoc: {detail[0] if detail else 'unknown error'}"
    return True, f"-> {out.name}"


class FileDrop:
    """Accept files dropped from Windows Explorer onto a Tk window.

    Standard-library only: registers the window with DragAcceptFiles and
    intercepts WM_DROPFILES. The callback receives a list of dropped paths
    and runs on Tk's thread via an after() poll, so it is safe to touch
    widgets from there.
    """
    WM_DROPFILES = 0x0233
    WM_DESTROY = 0x0002
    GWLP_WNDPROC = -4

    _WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_size_t,  # LRESULT
        ctypes.c_size_t,  # HWND
        ctypes.c_uint,    # UINT msg
        ctypes.c_size_t,  # WPARAM
        ctypes.c_size_t,  # LPARAM
    )

    def __init__(self, widget: tk.Misc, callback) -> None:
        self._callback = callback
        self._pending: list[list[str]] = []
        hwnd = int(widget.frame(), 16)

        user32 = ctypes.windll.user32
        user32.GetWindowLongPtrW.restype = ctypes.c_size_t
        user32.GetWindowLongPtrW.argtypes = [ctypes.c_size_t, ctypes.c_int]
        user32.SetWindowLongPtrW.restype = ctypes.c_size_t
        user32.SetWindowLongPtrW.argtypes = [ctypes.c_size_t, ctypes.c_int, ctypes.c_size_t]
        user32.CallWindowProcW.restype = ctypes.c_size_t
        user32.CallWindowProcW.argtypes = [ctypes.c_size_t] * 5
        self._user32 = user32

        shell32 = ctypes.windll.shell32
        shell32.DragAcceptFiles.argtypes = [ctypes.c_size_t, ctypes.c_bool]
        shell32.DragQueryFileW.argtypes = [ctypes.c_size_t, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
        shell32.DragQueryFileW.restype = ctypes.c_uint
        shell32.DragFinish.argtypes = [ctypes.c_size_t]
        self._shell32 = shell32

        self._newproc = self._WNDPROC(self._wndproc)  # keep a reference alive
        self._oldproc = user32.GetWindowLongPtrW(hwnd, self.GWLP_WNDPROC)
        user32.SetWindowLongPtrW(hwnd, self.GWLP_WNDPROC, ctypes.cast(self._newproc, ctypes.c_void_p).value)
        shell32.DragAcceptFiles(hwnd, True)

        self._widget = widget
        self._poller = None
        widget.bind("<Destroy>", self._on_tk_destroy, add="+")
        self._start_polling()

    def _wndproc(self, hwnd, msg, wparam, lparam):
        if msg == self.WM_DROPFILES:
            try:
                files = self._query_files(wparam)
            except Exception:
                files = []
            if files:
                self._pending.append(files)  # polled from Tk; no Tk calls here
            return 0
        if msg == self.WM_DESTROY:
            self._restore(hwnd)
            return self._user32.CallWindowProcW(self._oldproc, hwnd, msg, wparam, lparam)
        return self._user32.CallWindowProcW(self._oldproc, hwnd, msg, wparam, lparam)

    def _query_files(self, hdrop) -> list[str]:
        shell32 = self._shell32
        count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
        paths = []
        for i in range(count):
            length = shell32.DragQueryFileW(hdrop, i, None, 0) + 1
            buf = ctypes.create_unicode_buffer(length)
            shell32.DragQueryFileW(hdrop, i, buf, length)
            paths.append(buf.value)
        shell32.DragFinish(hdrop)
        return paths

    def _start_polling(self) -> None:
        if self._poller is None:
            self._poller = self._widget.after(100, self._poll)

    def _poll(self) -> None:
        self._poller = None
        if self._pending:
            files = [f for batch in self._pending for f in batch]
            self._pending = []
            self._callback(files)
        self._start_polling()  # drops can arrive any time; never stop watching

    def _on_tk_destroy(self, _event=None) -> None:
        if self._poller is not None:
            try:
                self._widget.after_cancel(self._poller)
            except tk.TclError:
                pass
            self._poller = None

    def _restore(self, hwnd) -> None:
        self._user32.SetWindowLongPtrW(hwnd, self.GWLP_WNDPROC, self._oldproc)
        self._shell32.DragAcceptFiles(hwnd, False)


class MarkMeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(APP_TITLE)
        root.geometry("560x440")
        root.minsize(420, 300)

        self.pandoc = find_pandoc()
        self.soffice = find_soffice()
        self.queue: list[Path] = []
        self.pumping = False
        self.ok_count = 0
        self.fail_count = 0

        style = ttk.Style(root)
        style.configure("Drop.TLabel", font=("Segoe UI", 14), padding=8)

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        self.drop_label = ttk.Label(
            top,
            text="\u21d3  Drop files anywhere in this window  \u21d3",
            style="Drop.TLabel",
            anchor="center",
        )
        self.drop_label.pack(fill="x")

        mid = ttk.Frame(root, padding=(10, 0))
        mid.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(mid, font=("Segoe UI", 10), activestyle="none")
        scrollbar = ttk.Scrollbar(mid, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.listbox.insert("end", " Waiting for files...")
        self.listbox.itemconfigure(0, foreground="#888888")
        self._placeholder = True

        bottom = ttk.Frame(root, padding=10)
        bottom.pack(fill="x")
        self.overwrite = tk.BooleanVar(value=False)
        ttk.Checkbutton(bottom, text="Overwrite existing .md", variable=self.overwrite).pack(side="left")
        ttk.Button(bottom, text="Browse...", command=self.browse).pack(side="right")
        ttk.Button(bottom, text="Quit", command=root.destroy).pack(side="right", padx=(0, 6))

        self.status = ttk.Label(root, text="", padding=(10, 0, 10, 8))
        self.status.pack(fill="x")

        if not self.pandoc:
            self.set_status(
                "pandoc.exe not found - install pandoc or set the PANDOC environment variable.",
                error=True,
            )

        # Realize the window before hooking it: during its first update Tk
        # re-subclasses the toplevel, discarding any window proc installed
        # earlier - drag-and-drop would then silently do nothing.
        self.root.update()
        self.drop = FileDrop(root, self.on_files)
        root.bind("<Escape>", lambda _e: root.destroy())

    def set_status(self, text: str, error: bool = False) -> None:
        self.status.configure(text=text, foreground="#b00020" if error else "#333333")

    def browse(self) -> None:
        result = self.root.tk.call(
            "tk_getOpenFile", "-multiple", "1", "-title", "Choose files to convert"
        )
        names = self.root.tk.splitlist(result)
        if names:
            self.on_files(list(names))

    def on_files(self, names: list[str]) -> None:
        first = not self.queue and not self.pumping
        if self._placeholder:
            self.listbox.delete(0)
            self._placeholder = False
        for name in names:
            path = Path(name)
            if path.is_dir():
                self.add_result(path.name, False, "folders are not supported - drop files")
                continue
            if not path.is_file():
                self.add_result(name, False, "file not found")
                continue
            index = self.listbox.size()
            self.listbox.insert("end", f" ... {path.name}")
            self.queue.append((path, index))
        if first and self.queue:
            self.set_status("Converting...")
            self.pump()

    def pump(self) -> None:
        if not self.queue:
            self.pumping = False
            self.set_status(f"Done - {self.ok_count} converted, {self.fail_count} failed.")
            return
        self.pumping = True
        path, index = self.queue.pop(0)
        ok, message = convert_file(self.pandoc, self.soffice, path, self.overwrite.get()) if self.pandoc else (False, "pandoc not found")
        self.add_result(path.name, ok, message, index)
        if ok:
            self.ok_count += 1
        else:
            self.fail_count += 1
        self.root.after(10, self.pump)

    def add_result(self, name: str, ok: bool, message: str, index: int | None = None) -> None:
        mark = "\u2713" if ok else "\u2717"
        color = "#1a7f37" if ok else "#b00020"
        line = f" {mark} {name}  -  {message}"
        if index is None:
            self.listbox.insert("end", line)
            index = self.listbox.index("end") - 1
        else:
            self.listbox.delete(index)
            self.listbox.insert(index, line)
        self.listbox.itemconfigure(index, foreground=color)
        self.listbox.see(index)


def main() -> None:
    root = tk.Tk()
    MarkMeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
