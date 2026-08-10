---
name: word2pdf
description: Convert Word (.doc / .docx) to PDF. Auto-detects binary .doc (OLE2) vs .docx (Office Open XML) via magic bytes, then converts using Microsoft Word COM or LibreOffice headless. Use when user mentions "word2pdf", "Word转PDF", "Word to PDF", "doc转PDF", "docx转PDF", or needs to convert a Word document to PDF.
---

# Word to PDF Converter

Convert Word documents (.doc / .docx) to PDF with automatic format detection.

## When to Use

- User mentions: "word2pdf", "Word转PDF", "Word to PDF", "doc转PDF", "docx转PDF"
- Need to convert a Word document to PDF for sharing or submission
- Need to check whether a file is .doc or .docx before converting

## How It Works

1. **Format Detection** — reads first 8 bytes to identify:
   - `D0 CF 11 E0 ...` → `.doc` (OLE2 Compound Binary Format)
   - `50 4B 03 04` → `.docx` (ZIP / Office Open XML)
2. **Conversion** — tries in order:
   - Microsoft Word COM automation (`win32com`) — best fidelity for both formats
   - LibreOffice headless (`soffice --headless`) — fallback for both formats

## Usage

```bash
python "<LOCAL_USER>/.claude/skills/word2pdf/word2pdf.py" <input.doc|input.docx> [output.pdf]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `input` | Yes | Input Word file path (.doc or .docx) |
| `output` | No | Output PDF path (default: same name with `.pdf` extension) |

### Examples

```bash
# Convert .docx (auto-detect format, output = input_name.pdf)
python "<LOCAL_USER>/.claude/skills/word2pdf/word2pdf.py" "report.docx"

# Convert .doc (legacy binary format)
python "<LOCAL_USER>/.claude/skills/word2pdf/word2pdf.py" "old_document.doc"

# Convert with custom output path
python "<LOCAL_USER>/.claude/skills/word2pdf/word2pdf.py" "report.docx" "output.pdf"
```

## Dependencies

- **Primary**: Microsoft Word (installed) + `pywin32`
  ```bash
  python -m pip install pywin32
  ```
- **Fallback**: LibreOffice (any recent version)

## Workflow

1. Validate input file exists
2. Detect format via magic bytes (report `.doc` or `.docx`)
3. Try Microsoft Word COM conversion
4. If unavailable, try LibreOffice headless
5. Report output path, file size, and page count

## Rules

1. Always use `PYTHONIOENCODING=utf-8` on Windows
2. Report detected format to user before converting
3. Report any conversion warnings or errors
4. If neither Word nor LibreOffice is available, inform the user to install one
