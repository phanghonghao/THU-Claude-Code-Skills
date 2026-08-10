---
name: html2md
description: Convert HTML to clean Markdown, optimized for slide-style presentation decks and huge files with inlined base64 images/videos. Strips data URIs BEFORE parsing (so a 10 MB deck converts in seconds, not minutes), detects `.slide` blocks and emits one `## Slide NN — Title` section per slide, and turns common deck semantic-divs (stat-num/stat-label, cards, timelines) into readable Markdown. Triggers: html2md, html to md, html→md, 转换 deck 为 markdown, deck 转 md, slide html to md.
---

# html2md — HTML → Markdown (deck-aware, base64-safe)

A stdlib-only converter (`html2md.py`) tuned for two cases generic converters
choke on:

1. **Slide decks** — a `.slide`-per-page HTML presentation. A normal converter
   flattens it into one wall of text; this one keeps the slide structure and
   emits `## Slide NN — Title` headers.
2. **Huge embedded HTML** — decks saved as single `.html` with every image and
   video inlined as base64 (often 5–50 MB). `markitdown` and friends spend
   minutes decoding megabytes of base64 into useless inline blobs; this strips
   the data URIs *first*, then parses.

## When to Use

- User mentions: `html2md`, `/html2md`, "html to md", "html→md", "把 deck 转成 markdown", "deck 转 md"
- You have a **slide-style HTML deck** (each slide is a `<div class="slide">` / `<section class="slide">`) and want structured per-slide Markdown
- You have a **bloated HTML file** (multi-MB) that is mostly base64 — `markitdown` hangs or produces garbage
- You want to **extract the text content** of a deck so an LLM can critique / revise it

## When NOT to Use (use a different skill instead)

| Need | Better skill |
|------|--------------|
| Generic non-deck HTML page | `markitdown` (`/markitdown`) — broad format support |
| DOCX with math | `/word2md` (correct OMML→LaTeX) |
| PDF → Markdown | `/any2md --pdf-backend pymupdf` or `/pdf-reader` |
| Want to **render a deck to PDF** (md/html → pdf) | `/html2pdf` |
| A whole web page from a URL | the `web_reader` MCP tool |

## How to Use

```bash
# Convert, write to a sibling .md file
PYTHONIOENCODING=utf-8 python ~/.claude/skills/html2md/html2md.py "deck.html" "deck.md"

# Convert, print to stdout
PYTHONIOENCODING=utf-8 python ~/.claude/skills/html2md/html2md.py "deck.html"

# Extract the base64 images/videos to disk and rewrite refs (instead of [IMAGE] placeholders)
PYTHONIOENCODING=utf-8 python ~/.claude/skills/html2md/html2md.py "deck.html" "deck.md" --extract-assets

# Drop [IMAGE]/[VIDEO] placeholders entirely (pure text)
PYTHONIOENCODING=utf-8 python ~/.claude/skills/html2md/html2md.py "deck.html" "deck.md" --no-assets

# Flat document — don't try to split slides
PYTHONIOENCODING=utf-8 python ~/.claude/skills/html2md/html2md.py "page.html" "page.md" --no-slides
```

**Always set `PYTHONIOENCODING=utf-8`** on Windows — Chinese/CJK decks mojibake
without it.

### Arguments

| Arg | Required | Description |
|-----|----------|-------------|
| `input` | yes | Input `.html` file |
| `output` | no | Output `.md` path (default: stdout) |
| `--extract-assets` | no | Save base64 blobs to `<stem>_assets/` and reference them by path (default: replace with `[IMAGE]` / `[VIDEO]`) |
| `--no-assets` | no | Omit asset placeholders entirely — pure text |
| `--no-slides` | no | Don't split into per-slide sections; one flat document |

## What It Detects

- **Slide structure**: any `<div class="…slide…">` / `<section class="…slide…">`. Reads `.slide-num`, `.slide-title`, `.slide-title-en` to build the `## Slide NN — Title  / _EN subtitle_` header. Falls back to `<!-- === NN LABEL === -->` HTML comments if classes are absent.
- **Semantic divs** common in decks: `.stat-num` + `.stat-label`, `.phase-year`/`.phase-name`/`.phase-tag`, `.label`/`.source-link`/`.source-note`, `.maic-ms-*` timeline milestones, `.action-*` 5W1H cards. These become readable inline Markdown (`**13%** — global ATP share`) instead of being lost.
- **Source links**: `<a class="source-link" href="…">Source: MIDA</a>` → `[→ Source: MIDA](url)`.
- **Tables**: `<table>` → pipe tables.
- **Document `<title>`**: becomes the top-level `# Title`.

## Dependencies

**None.** Pure Python 3 stdlib (`html.parser`, `re`, `base64`, `hashlib`).
Works on any machine with Python ≥ 3.8.

## Notes / Gotchas

- The slide-splitter caps each slide's inner HTML at 200 KB to defeat greedy
  regex across nested `<div>`s. If a slide is genuinely larger than that, raise
  the limit in `split_slides()`.
- `--extract-assets` is the way to **recover** the inlined videos/images from a
  bloated deck: it writes each blob to `<input-stem>_assets/<kind>_<hash>.<ext>`
  and emits `![image](assets/...)`. Hashes dedupe identical assets.
- For a **dark/light themed BFLab deck** with `.presentation { width:1280px;
  height:720px }` and `.slide { position:absolute }`, the splitter works as-is.
- This skill **does not render HTML or produce PDF** — for that use `/html2pdf`
  (Chrome headless `--print-to-pdf`, one PDF page per slide).

## Workflow: critique-then-revise a deck

A common use of this skill is to get the text of a deck out so it can be
reviewed or rewritten:

1. `html2md deck_embedded.html deck.md` — extract clean per-slide Markdown.
2. Read `deck.md` + the critique notes (e.g. `eunice_suggestion.md`).
3. Author a revised deck HTML (a *new* file — don't edit the original).
4. `/html2pdf` the revised HTML to PDF.
