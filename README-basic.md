# MarkMe-basic

The console version of [MarkMe](README.md). Drag files onto
`markme-basic.exe` and each one becomes `<name>.md` in the same folder,
converted by [pandoc](https://pandoc.org). Nothing is uploaded anywhere - it
just runs pandoc for you, one file at a time, printing results in a console
window.

For a version with a window you drag files into, use `markme.exe`.

Inspired by [Eggy](https://github.com/DwightIvany/eggy): plain Python first,
then a single-file exe.

## Requirements

- Windows
- Python 3.9+ (only if running the source; not needed for the exe)
- Conversion tools, depending on what you drop in. The exe does not bundle
  these - it finds them on PATH, in their standard install locations, or via
  the `PANDOC` / `SOFFICE` environment variables:

| To convert | Install |
|---|---|
| `.docx` `.odt` `.rtf` `.html` `.htm` `.epub` `.txt` `.csv` `.tsv` `.tex` `.latex` `.rst` `.org` `.textile` - and anything else pandoc can read | [pandoc](https://pandoc.org/installing.html) |
| `.doc` (legacy Word) | [LibreOffice](https://www.libreoffice.org/download/download/) - used headlessly to turn `.doc` into `.docx`, then pandoc converts that |

## Running

From a terminal:

```powershell
python markme-basic.py report.docx notes.html
```

Or double-click / drag files onto `markme-basic.exe`. Results are printed for
each file, then a summary, then the window waits for Enter so you can read it.

## Using MarkMe-basic

Drop one or more files. Each becomes `<name>.md` next to the source. If the
`.md` already exists it is skipped - pass `--force` to overwrite. Embedded
images are extracted to `<name>_media/` and linked from the Markdown.

### Works

| Input | Notes |
|---|---|
| `.docx` `.odt` `.rtf` | Word / OpenDocument / Rich Text |
| `.doc` | legacy Word - needs LibreOffice installed (see Requirements) |
| `.html` `.htm` | web pages saved to disk |
| `.epub` | ebooks |
| `.txt` | treated as Markdown text |
| `.csv` `.tsv` | become Markdown pipe tables |
| `.tex` `.latex` `.rst` `.org` `.textile` | other markup formats |

Anything else pandoc can read is attempted too (pandoc guesses the format).

### Not supported

- `.pdf` - pandoc does not read PDF. Use `software/python/convert-to-md.py`.
- `.ppt` `.pptx` `.ppsx` - pandoc cannot read PowerPoint (yet).
- `.xls` `.xlsx` - open the spreadsheet, save as `.csv`, drop the `.csv`.

## Building the exe

```powershell
pip install pyinstaller
pyinstaller --onefile --name markme-basic markme-basic.py
```

The exe lands in `dist/markme-basic.exe`. Copy it anywhere and drop files on it.

## Files

| File | Purpose |
|---|---|
| `markme-basic.py` | The application (single file) |
| `README-basic.md` | This file |
