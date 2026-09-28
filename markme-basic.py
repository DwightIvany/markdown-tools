#!/usr/bin/env python3
"""MarkMe - drag-and-drop document to Markdown converter.

Drop files on markme.exe (or pass them on the command line). Each file is
converted to <name>.md in the same folder using pandoc.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

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
    ".doc": "legacy .doc is not supported by pandoc - open in Word/LibreOffice and save as .docx",
    ".markdown": "already Markdown",
    ".md": "already Markdown",
    ".pdf": "pandoc does not read PDF - see software/python/convert-to-md.py",
    ".ppsx": "PowerPoint input is not supported by your pandoc version",
    ".ppt": "PowerPoint input is not supported by your pandoc version",
    ".pptx": "PowerPoint input is not supported by your pandoc version",
    ".xls": "spreadsheets are not supported - save as .csv and drop the .csv",
    ".xlsx": "spreadsheets are not supported - save as .csv and drop the .csv",
}

USAGE = """{title} - convert documents to Markdown (via pandoc)

Usage: drag files onto markme-basic.exe, or from a terminal:
  python markme-basic.py [--force] FILE [FILE ...]

Each FILE is converted to <name>.md in the same folder. Existing .md files
are skipped unless --force is given. Embedded images go to <name>_media/.
""".format(title=APP_TITLE)


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


def convert_file(pandoc: str, path: Path, force: bool) -> tuple[bool, str]:
    """Convert one file. Returns (ok, message) - message is a note or error."""
    ext = path.suffix.lower()
    if ext in NOT_CONVERTIBLE:
        return False, NOT_CONVERTIBLE[ext]
    reader = READERS.get(ext)  # None: let pandoc guess from the extension

    out = path.with_suffix(".md")
    if out.exists() and not force:
        return False, f"skipped ({out.name} exists - use --force to overwrite)"

    media = out.parent / (out.stem + "_media")
    cmd = [pandoc, "--to=gfm", "--wrap=none", f"--extract-media={media}"]
    if reader:
        cmd.append(f"--from={reader}")
    cmd += ["--output", str(out), str(path)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        return False, f"pandoc failed to start: {exc}"
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "unknown error").strip().splitlines()
        return False, f"pandoc: {detail[0] if detail else 'unknown error'}"
    return True, f"-> {out.name}"


def pause() -> None:
    """Hold the console window open (frozen exe); tolerate EOF stdin."""
    try:
        input("Press Enter to close...")
    except EOFError:
        pass


def main(argv: list[str] | None = None) -> int:
    args = [a for a in (argv if argv is not None else sys.argv[1:])]
    force = "--force" in args or "-f" in args
    files = [a for a in args if a not in ("--force", "-f")]

    frozen = getattr(sys, "frozen", False)
    if not files:
        print(USAGE)
        if frozen:
            pause()
        return 2

    pandoc = find_pandoc()
    if not pandoc:
        print(f"{APP_TITLE}: pandoc.exe not found.", file=sys.stderr)
        print("Install pandoc (https://pandoc.org/installing.html) or set the PANDOC environment variable.", file=sys.stderr)
        if frozen:
            pause()
        return 2

    ok_count = 0
    fail_count = 0
    for name in files:
        path = Path(name)
        if path.is_dir():
            print(f"FAIL {name}: folders are not supported - drop files")
            fail_count += 1
            continue
        if not path.is_file():
            print(f"FAIL {name}: file not found")
            fail_count += 1
            continue
        ok, message = convert_file(pandoc, path, force)
        tag = "OK  " if ok else "FAIL"
        print(f"{tag} {path.name} {message}")
        if ok:
            ok_count += 1
        else:
            fail_count += 1

    print(f"\n{ok_count} converted, {fail_count} failed.")
    if frozen:
        pause()
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
