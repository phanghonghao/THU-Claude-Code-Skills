---
name: assignment-word
description: Edit and fill Word (.docx) documents — inspect structure, replace text, batch fill placeholders, insert images, and fill tables. Use when user mentions "assignment-word", "docx_editor", "填Word", "填docx", "Word填写", "replace docx", "fill docx", or needs to programmatically modify a Word document.
---

# Assignment Word Editor (docx_editor.py)

Programmatically edit Word (.docx) documents using python-docx. Supports text replacement (preserving formatting), batch placeholder filling, image insertion, and table data filling.

## When to Use

- User mentions: "assignment-word", "docx_editor", "填Word", "填docx", "Word填写", "replace docx"
- Need to inspect, fill, or modify a Word document programmatically
- After converting PDF to Word with `pdf2word`, need to fill in content

## Dependencies

```bash
python -m pip install python-docx 2>&1 | tail -3
```

## Commands

### info — Print document structure

Prints paragraphs, tables, headers/footers with index numbers for targeting edits.

```bash
PYTHONIOENCODING=utf-8 python "<LOCAL_USER>/.claude/skills/assignment-word/docx_editor.py" info "<docx_path>"
```

### replace — Find and replace text (preserving formatting)

```bash
PYTHONIOENCODING=utf-8 python "<LOCAL_USER>/.claude/skills/assignment-word/docx_editor.py" replace "<docx_path>" --old "OLD_TEXT" --new "NEW_TEXT" [-o output.docx]
```

### fill — Batch replace placeholders from JSON

JSON format: `{ "placeholder1": "value1", "placeholder2": "value2" }`

```bash
PYTHONIOENCODING=utf-8 python "<LOCAL_USER>/.claude/skills/assignment-word/docx_editor.py" fill "<docx_path>" --data replacements.json [-o output.docx]
```

### image — Insert image after matching text

```bash
PYTHONIOENCODING=utf-8 python "<LOCAL_USER>/.claude/skills/assignment-word/docx_editor.py" image "<docx_path>" --after "图1" --img "figure.png" [-o output.docx]
```

### table — Fill table data from JSON

JSON format: `{ "cells": { "0,0": "value", "1,2": "value" } }` (row,col → value)

```bash
PYTHONIOENCODING=utf-8 python "<LOCAL_USER>/.claude/skills/assignment-word/docx_editor.py" table "<docx_path>" --idx 0 --data table_data.json [-o output.docx]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `-o, --output` | Output file path. Default: in-place edit (original backed up as `.bak`) |
| `--old` | Old text to find (for `replace`) |
| `--new` | New replacement text (for `replace`) |
| `--data` | Path to JSON data file (for `fill` and `table`) |
| `--after` | Text to search for, image inserted after this paragraph (for `image`) |
| `--img` | Image file path to insert (for `image`) |
| `--idx` | Table index (0-based, for `table`) |

## Workflow

1. Use `info` to inspect document structure and find placeholder text
2. Use `replace` for simple text substitutions
3. Use `fill` for batch replacements from a JSON file
4. Use `image` to insert images at specific locations
5. Use `table` to fill specific table cells with data

## Rules

1. Always use `PYTHONIOENCODING=utf-8` on Windows
2. Default behavior is **in-place edit** with `.bak` backup
3. Use `-o` to save to a new file instead of modifying the original
4. Text replacement preserves original run formatting (bold, italic, font, size)
5. For `fill`, placeholders like `{{姓名}}` will be matched and replaced
6. **Chinese font fix**: Always use `set_run_font(run)` instead of `run.font.name = '宋体'` — python-docx's `font.name` only sets Western fonts (ascii/hAnsi), NOT East Asian (w:eastAsia). Without setting eastAsia, Chinese characters render in Word's default font causing garbled text

## Chinese Font Fix (Critical)

python-docx's `run.font.name = '宋体'` only sets `w:ascii` and `w:hAnsi` attributes. Chinese characters use `w:eastAsia` which must be set via XML:

```python
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def set_run_font(run, font_name='宋体'):
    run.font.name = font_name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.insert(0, rFonts)
    rFonts.set(qn('w:eastAsia'), font_name)
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
```

This applies to:
- Creating new documents from scratch (every run)
- Setting default style font (`set_style_font()`)
- Filling table cells (`set_tc_text()` already includes this fix)
- Any code that sets `run.font.name` for Chinese content
