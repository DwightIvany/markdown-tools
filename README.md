# MarkMe

MarkMe converts common documents to Markdown. Drag one or more files
**into the MarkMe window** and each one becomes `<name>.md` in the same
folder, converted by [pandoc](https://pandoc.org). Results show up in the
list as each file finishes. Nothing is uploaded anywhere.

A console version that works by dropping files on an icon lives in
[markme-basic.py](markme-basic.py) - see [README-basic.md](README-basic.md).

Inspired by [Eggy](https://github.com/DwightIvany/eggy): plain Python
(tkinter) first, then a single-file exe.

## Requirements

- Windows
- [pandoc](https://pandoc.org/installing.html) on PATH (or in the standard
  install location, or pointed to by the `PANDOC` environment variable)
- Python 3.9+ (only if running the source; not needed for the exe)

## Running

```powershell
python markme.py
```

Or double-click `markme.exe`.

## Using MarkMe

- Drag files from Explorer into the window - one or many at once.
- Or click **Browse...** to pick files.
- Each file becomes `<name>.md` next to the source. Embedded images are
  extracted to `<name>_media/` and linked from the Markdown.
- If the `.md` already exists it is skipped, unless **Overwrite existing
  .md** is checked.
- `✓` green rows converted; `✗` red rows explain why not.
- Esc or **Quit** closes the app.

### Works

| Input | Notes |
|---|---|
| `.docx` `.odt` `.rtf` | Word / OpenDocument / Rich Text |
| `.html` `.htm` | web pages saved to disk |
| `.epub` | ebooks |
| `.txt` | treated as Markdown text |
| `.csv` `.tsv` | become Markdown pipe tables |
| `.tex` `.latex` `.rst` `.org` `.textile` | other markup formats |

Anything else pandoc can read is attempted too (pandoc guesses the format).

### Not supported

- `.pdf` - pandoc does not read PDF. Use `software/python/convert-to-md.py`.
- `.doc` - legacy binary Word. Open in Word/LibreOffice, save as `.docx`.
- `.ppt` `.pptx` `.ppsx` - pandoc cannot read PowerPoint (yet).
- `.xls` `.xlsx` - open the spreadsheet, save as `.csv`, drop the `.csv`.

The drag-and-drop uses only the Python standard library (Windows
`WM_DROPFILES` via ctypes) - there is no tkinterdnd2 or similar to install.

## Building the exe

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name markme markme.py
```

The exe lands in `dist/markme.exe`. `--windowed` means no console flashes
when files are dropped on it.

## Files

| File | Purpose |
|---|---|
| `markme.py` | The application (single file, tkinter UI) |
| `markme-basic.py` | Console variant - drop files on its icon instead |
| `README.md` | This file |
| `README-basic.md` | Readme for the console variant |
