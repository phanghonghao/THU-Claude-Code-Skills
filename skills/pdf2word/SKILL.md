---
name: pdf2word
description: Convert PDF files to Word (.docx) while preserving layout, tables, images, and formatting. Use when user mentions "pdf2word", "PDF转Word", "PDF to Word", "PDF转docx", or needs to convert a PDF to an editable Word document.
---

# PDF to Word Converter (pdf2docx)

Convert PDF files to Word (.docx) using the `pdf2docx` library (based on PyMuPDF + python-docx). Preserves paragraphs, tables, images, and font styles.

## When to Use

- User mentions: "pdf2word", "PDF转Word", "PDF to Word", "PDF转docx"
- Need to convert a PDF into an editable Word document
- Need to fill in a PDF form but need Word format first

## Dependencies

```bash
python -m pip install pdf2docx 2>&1 | tail -3
```

## Usage

```bash
python "<LOCAL_USER>/.claude/skills/pdf2word/pdf2word.py" <input.pdf> [output.docx] [--start PAGE] [--end PAGE] [--pages 0,1,2]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `input.pdf` | Yes | Input PDF file path |
| `output.docx` | No | Output Word file path (default: same name as PDF with `.docx` extension) |
| `--start` | No | Start page (0-indexed, default: 0) |
| `--end` | No | End page (exclusive, default: all pages) |
| `--pages` | No | Specific pages to convert (comma-separated, 0-indexed) |

### Examples

```bash
# Convert entire PDF
python "<LOCAL_USER>/.claude/skills/pdf2word/pdf2word.py" "report.pdf"

# Convert with custom output name
python "<LOCAL_USER>/.claude/skills/pdf2word/pdf2word.py" "report.pdf" "output.docx"

# Convert pages 1-3 (0-indexed: 0,1,2)
python "<LOCAL_USER>/.claude/skills/pdf2word/pdf2word.py" "report.pdf" --start 0 --end 3

# Convert specific pages
python "<LOCAL_USER>/.claude/skills/pdf2word/pdf2word.py" "report.pdf" --pages 0,2,4
```

## Workflow

1. Install `pdf2docx` if not present
2. Run `pdf2word.py` with the PDF path
3. Output `.docx` is saved alongside the original PDF (or at specified path)
4. Use `assignment-word` skill's `info` command to inspect the resulting docx structure

## Limitations

- Complex layouts (multi-column, floating elements) may not convert perfectly
- Scanned/image-based PDFs will not have editable text
- Very large PDFs may be slow — use `--start/--end` to convert page ranges

## Rules

1. Always use `PYTHONIOENCODING=utf-8` on Windows
2. Always use `python -m pip install` for dependencies
3. Report any conversion warnings to the user
