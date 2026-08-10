#!/usr/bin/env python3
"""
html2md — HTML → Markdown converter (Python stdlib only, no deps).

Design goals:
  - Works on huge HTML files (e.g. decks with megabytes of base64 images/videos
    inlined). Base64 data URIs are stripped FIRST, before any parsing, so the
    parser never sees them.
  - Handles slide-style presentation decks: detects `.slide` blocks and emits
    one `## Slide NN — Title` section per slide (preserves deck structure that
    a generic converter flattens).
  - Converts the common semantic-div patterns decks use (stat-num/stat-label,
    card/label/h3/p, phase-card, timeline milestones) into readable markdown,
    not a wall of text.
  - Preserves source links (`<a class="source-link" href="...">Source: X</a>`
    → `(Source: X)[url]`) and image references as `![alt](src)`.

Usage:
  PYTHONIOENCODING=utf-8 python html2md.py <INPUT.html> [OUTPUT.md] [options]

Options:
  --no-assets        Omit [IMAGE]/[VIDEO] placeholders entirely
  --extract-assets   Save base64 images/videos to <stem>_assets/ and rewrite
                     src/href to point at the extracted files (default: replace
                     with [IMAGE]/[VIDEO] placeholder)
  --no-slides        Do not detect/split slides; treat as one flat document
  --wrap <n>         Wrap paragraphs at n chars (0 = no wrap, default 0)
"""

import argparse
import base64
import hashlib
import html as ihtml
import os
import re
import sys
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Step 1 — strip base64 data URIs BEFORE parsing (the whole point).
# ---------------------------------------------------------------------------

_DATA_URI_RE = re.compile(
    r'data:(image|video|audio)/(png|jpe?g|gif|webp|svg\+xml|mp4|webm|ogg|wav|pdf);base64,([A-Za-z0-9+/=\s]+)',
    re.IGNORECASE,
)

# also catch generic data: URIs that slipped through
_GENERIC_DATA_RE = re.compile(
    r'data:[a-z0-9.+-]+/[a-z0-9.+-]+;base64,[A-Za-z0-9+/=\s]+',
    re.IGNORECASE,
)


def strip_data_uris(html: str, extract_dir: str = None, asset_log: dict = None):
    """Replace base64 data URIs. If extract_dir given, write files & return paths."""
    assets = []

    def repl(m):
        kind = m.group(1).lower()
        ext = m.group(2).lower()
        ext = 'jpg' if ext == 'jpeg' else ext
        ext = ext.replace('svg+xml', 'svg')
        data = m.group(3).strip()
        if extract_dir:
            try:
                raw = base64.b64decode(data)
                fname = f"{kind}_{hashlib.md5(raw).hexdigest()[:10]}.{ext}"
                os.makedirs(extract_dir, exist_ok=True)
                fpath = os.path.join(extract_dir, fname)
                if not os.path.exists(fpath):
                    with open(fpath, 'wb') as fh:
                        fh.write(raw)
                rel = os.path.relpath(fpath, os.path.dirname(extract_dir.rstrip('/\\')) or '.')
                assets.append(rel)
                if asset_log is not None:
                    asset_log[rel] = len(raw)
                return rel
            except Exception:
                return f"[{kind.upper()}-DECODE-ERROR]"
        return f"[{kind.upper()}]"

    out = _DATA_URI_RE.sub(repl, html)
    out = _GENERIC_DATA_RE.sub(
        lambda m: m.group(0) if extract_dir else "[ASSET]", out
    )
    return out, assets


# ---------------------------------------------------------------------------
# Step 2 — strip <script> / <style> / <head> metadata / comments.
# ---------------------------------------------------------------------------

def strip_noncontent(html: str) -> str:
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.S | re.I)
    html = re.sub(r'<style\b[^>]*>.*?</style>', '', html, flags=re.S | re.I)
    html = re.sub(r'<noscript\b[^>]*>.*?</noscript>', '', html, flags=re.S | re.I)
    html = re.sub(r'<head\b[^>]*>.*?</head>', '', html, flags=re.S | re.I)
    # drop <svg> icon blobs (inline icons) — keep text instead
    html = re.sub(r'<svg\b[^>]*>.*?</svg>', '', html, flags=re.S | re.I)
    return html


# ---------------------------------------------------------------------------
# Step 3 — split into slides if this is a deck.
# ---------------------------------------------------------------------------

# A slide is a <div|section> whose class attribute contains "slide" as a
# STANDALONE token. This deliberately excludes slide-num / slide-title /
# slide-title-en (compound classes where "slide" is only a prefix). We then
# walk forward tracking <div|section> depth to find the matching close tag,
# instead of relying on a greedy regex that stops at the first inner </div>.

_OPEN_TAG_RE = re.compile(r'<(div|section)\b([^>]*?)(/?)>', re.I)
_TAG_TOKEN_RE = re.compile(
    r'<(/?)(div|section)\b[^>]*?(/?)>', re.I
)
_CLASS_RE = re.compile(r'class\s*=\s*"([^"]*)"|class\s*=\s*\'([^\']*)\'', re.I)
_SLIDE_NUM_RE = re.compile(
    r'class="[^"]*\bslide-num\b[^"]*"[^>]*>(.*?)</div>', re.S | re.I
)
_SLIDE_TITLE_RE = re.compile(
    r'class="[^"]*\bslide-title\b(?!-)[^"]*"[^>]*>(.*?)</div>', re.S | re.I
)
_SLIDE_TITLE_EN_RE = re.compile(
    r'class="[^"]*\bslide-title-en\b[^"]*"[^>]*>(.*?)</div>', re.S | re.I
)
_SLIDE_ID_COMMENT_RE = re.compile(
    r'<!--\s*=+\s*(\d+\s*[\w\s/.-]+?)=+\s*-->', re.I
)


def _is_slide_open(attrs: str):
    """True if this tag's class list contains 'slide' as an exact token."""
    m = _CLASS_RE.search(attrs)
    if not m:
        return False
    classes = (m.group(1) or m.group(2) or '').split()
    return 'slide' in classes


def _strip_first_block_by_class(inner: str, cls_token: str):
    """Remove the first <div class="...{cls_token}...">…</div> subtree (depth-1)."""
    pat = re.compile(
        r'<div[^>]*class="[^"]*\b' + re.escape(cls_token) + r'\b[^"]*"[^>]*>',
        re.I,
    )
    m = pat.search(inner)
    if not m:
        return inner
    start = m.start()
    content_start = m.end()
    depth = 1
    for tm in re.finditer(r'<(/?)div\b[^>]*?(/?)>', inner[content_start:], re.I):
        if tm.group(2) == '/':
            continue
        if tm.group(1) == '/':
            depth -= 1
            if depth == 0:
                end = content_start + tm.end()
                return inner[:start] + inner[end:]
        else:
            depth += 1
    return inner


def _find_slide_blocks(body_html: str):
    """Yield (inner_html, classes) for each top-level slide container."""
    candidates = []
    for m in _OPEN_TAG_RE.finditer(body_html):
        if m.group(3) == '/':        # self-closing
            continue
        if _is_slide_open(m.group(2)):
            candidates.append(m)
    blocks = []
    last_end = 0
    for m in candidates:
        if m.start() < last_end:     # nested inside a slide we already captured
            continue
        content_start = m.end()
        depth = 1
        inner_end = None
        block_end = None
        for tm in _TAG_TOKEN_RE.finditer(body_html, content_start):
            self_closing = tm.group(3) == '/'
            if self_closing:
                continue
            if tm.group(1) == '/':   # closing tag
                depth -= 1
                if depth == 0:
                    inner_end = tm.start()
                    block_end = tm.end()
                    break
            else:                    # opening tag
                depth += 1
        if inner_end is not None:
            blocks.append((body_html[content_start:inner_end],
                           body_html[m.start():m.end()]))
            last_end = block_end
    return blocks


def split_slides(body_html: str):
    """Return list of (num, title, title_en, inner_html). None if not a deck."""
    # Prefer HTML-comment slide markers if present (most robust).
    comment_nums = {}
    for cm in _SLIDE_ID_COMMENT_RE.finditer(body_html):
        parts = cm.group(1).split()
        if parts and parts[0].isdigit():
            comment_nums[parts[0]] = ' '.join(parts[1:])

    blocks = _find_slide_blocks(body_html)
    if len(blocks) < 2:
        return None
    slides = []
    for i, (inner, opentag) in enumerate(blocks):
        # extract num/title/title-en from the slide-head FIRST (before stripping)
        nm = _SLIDE_NUM_RE.search(inner)
        if nm:
            num = re.sub(r'<[^>]+>', '', nm.group(1)).strip()
        else:
            num = str(i + 1)
        if not num:
            num = str(i + 1)
        tm = _SLIDE_TITLE_RE.search(inner)
        title = ''
        if tm:
            title = re.sub(r'<[^>]+>', ' ', tm.group(1)).strip()
            title = re.sub(r'\s+', ' ', title)
        te = _SLIDE_TITLE_EN_RE.search(inner)
        title_en = ''
        if te:
            title_en = re.sub(r'<[^>]+>', ' ', te.group(1)).strip()
            title_en = re.sub(r'\s+', ' ', title_en)
        # the .slide-head (num/title/title-en) is already promoted to the
        # section header — drop it from the body so it isn't duplicated
        body_inner = _strip_first_block_by_class(inner, 'slide-head')
        slides.append((num, title, title_en, body_inner))
    return slides


# ---------------------------------------------------------------------------
# Step 4 — the actual HTML → Markdown parser (stdlib html.parser).
#
# Design philosophy: keep it SIMPLE and HONEST.
#   - Block-level elements (div, p, section, ...) emit a newline before them so
#     content doesn't run together. We do NOT inject bold/italic based on class
#     names — that produced stray markers in earlier versions.
#   - Inline formatting (**) comes ONLY from real <strong>/<b>/<h1-6> and (*)
#     from real <em>/<i>. What you see in the HTML is what you get in the MD.
#   - LIFO stack: handle_endtag pops the top entry. This relies on well-formed
#     HTML (deck generators emit clean HTML). Void elements (img, br, hr, ...)
#     never get pushed, so they can't unbalance the stack.
# ---------------------------------------------------------------------------

# tags whose entire subtree we drop
DROP_TAGS = {'nav', 'button', 'form', 'input', 'select', 'option', 'iframe',
             'header', 'footer', 'svg', 'canvas'}

# void elements — no closing tag, never pushed onto the stack
VOID_TAGS = {'img', 'br', 'hr', 'source', 'input', 'meta', 'link', 'area',
             'base', 'col', 'embed', 'param', 'track', 'wbr'}

# block-level tags that should start on a new line
BLOCK_TAGS = {'div', 'p', 'section', 'article', 'ul', 'ol', 'li', 'blockquote',
              'figure', 'figcaption', 'table', 'thead', 'tbody', 'tfoot',
              'address', 'main', 'aside'}

# inline tags with (open, close) markdown wrappers
INLINE_WRAP = {
    'strong': ('**', '**'),
    'b': ('**', '**'),
    'em': ('*', '*'),
    'i': ('*', '*'),
    'code': ('`', '`'),
    'mark': ('**', '**'),
    'del': ('~~', '~~'),
    'ins': ('', ''),
    'u': ('', ''),
    'small': ('', ''),
    'sub': ('', ''),
    'sup': ('', ''),
    'abbr': ('', ''),
    'cite': ('', ''),
    'q': ('"', '"'),
}

HEADING_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
LIST_TAGS = {'ul', 'ol'}


def _need_space(out):
    """True if the last emitted char is alphanumeric and needs a separator."""
    if not out:
        return False
    last = out[-1][-1:] if out[-1] else ''
    return last and last not in ' \n\t|*-#[>'


class _MDBuilder(HTMLParser):
    def __init__(self, want_assets=True):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []        # LIFO; each entry is the close-text (str|None)
        self.drop_depth = 0    # >0 → inside a DROP subtree
        self.list_stack = []   # list of [ordered_bool, counter]
        self.in_table = False
        self.row_cells = 0
        self.want_assets = want_assets

    # ----- low-level emit helpers -----
    def _e(self, s):
        self.out.append(s)

    def _nl(self):
        """Ensure output ends with exactly one newline (block separator)."""
        if self.out and not self.out[-1].endswith('\n'):
            self._e('\n')

    def _sp(self):
        """Emit a separating space only if the previous char needs one."""
        if _need_space(self.out):
            self._e(' ')

    # ----- void / self-closing elements -----
    def _emit_img(self, attrs_d):
        alt = attrs_d.get('alt', '').strip()
        src = attrs_d.get('src', '').strip()
        if not self.want_assets:
            return
        if src.startswith('data:'):
            self._sp()
            self._e(f'![{alt}]' if alt else '[IMAGE]')
            return
        if src:
            self._sp()
            self._e(f'![{alt}]({src})')

    def _emit_video(self, attrs_d):
        if not self.want_assets:
            return
        src = (attrs_d.get('src') or attrs_d.get('href') or '').strip()
        if src:
            self._sp()
            self._e('[VIDEO]')

    # ----- start tags -----
    def handle_starttag(self, tag, attrs):
        self._dispatch(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag, attrs):
        self._dispatch(tag, attrs, self_closing=True)

    def _dispatch(self, tag, attrs, self_closing):
        attrs_d = dict(attrs)
        cls = attrs_d.get('class', '')

        if self.drop_depth > 0:
            if tag in DROP_TAGS and not self_closing:
                self.drop_depth += 1
            return

        if tag in DROP_TAGS:
            if not self_closing:
                self.drop_depth += 1
                self.stack.append(None)
            return

        # void elements — handle and return, never push
        if tag == 'br':
            self._e('\n')
            return
        if tag == 'hr':
            self._nl()
            self._e('\n---\n')
            return
        if tag == 'img':
            self._emit_img(attrs_d)
            return
        if tag in ('video', 'source', 'audio'):
            self._emit_video(attrs_d)
            if tag == 'video' and not self_closing:
                self.stack.append(None)
            return
        if tag in VOID_TAGS:
            return

        # anchor
        if tag == 'a':
            href = attrs_d.get('href', '').strip()
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                if 'source-link' in cls or 'web-link' in cls:
                    self._nl()
                    self._e('→ ')
                else:
                    self._sp()
                self._e('[')
                self.stack.append(f']({href})')
            else:
                self.stack.append(None)
            return

        # headings
        if tag in HEADING_TAGS:
            lvl = int(tag[1])
            self._nl()
            if lvl <= 2:
                self._e('\n' + '#' * lvl + ' ')
                self.stack.append('\n\n')
            else:
                # h3-h6 → bold line (avoids 6-deep heading clutter in MD)
                self._e('**')
                self.stack.append('**  \n')
            return

        # lists
        if tag in LIST_TAGS:
            self._nl()
            self.list_stack.append([tag == 'ol', 0])
            self.stack.append(None)
            return
        if tag == 'li':
            self._nl()
            if self.list_stack:
                ordered, ctr = self.list_stack[-1]
                if ordered:
                    ctr += 1
                    self.list_stack[-1][1] = ctr
                    self._e(f'{ctr}. ')
                else:
                    self._e('- ')
            self.stack.append(None)
            return

        # tables
        if tag == 'table':
            self._nl()
            self.in_table = True
            self.stack.append(None)
            return
        if tag == 'tr':
            self._nl()
            self._e('| ')
            self.row_cells = 0
            self.stack.append(' |')
            return
        if tag in ('td', 'th'):
            self.stack.append(' | ')
            return

        # inline wrappers
        if tag in INLINE_WRAP:
            self._sp()
            self._e(INLINE_WRAP[tag][0])
            self.stack.append(INLINE_WRAP[tag][1])
            return

        # block-level containers → newline before, None on stack
        if tag in BLOCK_TAGS or tag == 'p':
            self._nl()
            self.stack.append(None)
            return

        # span and other inline containers — no markers, just track
        self.stack.append(None)

    # ----- end tags -----
    def handle_endtag(self, tag):
        if not self.stack:
            return
        if self.drop_depth > 0:
            # we are inside a dropped subtree; pop until we close the drop root
            top = self.stack.pop()
            if top is None and self.drop_depth > 0:
                # ambiguous — can't tell which None is the drop root, so be
                # conservative and only decrement when we know we opened a drop
                pass
            return
        close_text = self.stack.pop()
        if close_text is None:
            return
        self._e(close_text)
        if tag == 'table':
            self.in_table = False
        if tag in LIST_TAGS and self.list_stack:
            self.list_stack.pop()

    # ----- text -----
    def handle_data(self, data):
        if self.drop_depth > 0:
            return
        if not data:
            return
        # collapse internal whitespace
        if data.strip():
            text = re.sub(r'\s+', ' ', data)
            leading = data[:1].isspace()
            trailing = data[-1:].isspace()
            if leading:
                self._sp()
            self._e(text)
            if trailing:
                self._sp()
        else:
            # pure whitespace between inline elements → one separator space
            self._sp()

    def handle_entityref(self, name):
        if self.drop_depth > 0:
            return
        self._e(ihtml.unescape('&' + name + ';'))

    def handle_charref(self, name):
        if self.drop_depth > 0:
            return
        self._e(ihtml.unescape('&#' + name + ';'))


def html_to_markdown(body_html: str, want_assets=True) -> str:
    p = _MDBuilder(want_assets=want_assets)
    p.feed(body_html)
    p.close()
    md = ''.join(p.out)
    # tidy: collapse 3+ blank lines, trailing spaces, empty markers
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = re.sub(r'[ \t]+\n', '\n', md)
    md = re.sub(r'\*\s*\*', '', md)            # empty bold
    md = re.sub(r'\[\s*\]\([^)]*\)', '', md)    # empty link
    md = re.sub(r' +', ' ', md)
    return md.strip() + '\n'


# ---------------------------------------------------------------------------
# Step 5 — orchestrate.
# ---------------------------------------------------------------------------

def convert_file(in_path: str, out_path: str = None, *,
                 extract_assets=False, want_assets=True,
                 detect_slides=True, title=None):
    with open(in_path, 'r', encoding='utf-8', errors='replace') as fh:
        raw = fh.read()

    base = os.path.abspath(in_path)
    stem = os.path.splitext(base)[0]
    extract_dir = None
    asset_log = {}
    if extract_assets:
        extract_dir = stem + '_assets'
        os.makedirs(extract_dir, exist_ok=True)

    body, _ = strip_data_uris(raw, extract_dir, asset_log if extract_assets else None)
    body = strip_noncontent(body)

    # also keep <title> if present
    if title is None:
        m = re.search(r'<title[^>]*>(.*?)</title>', raw, re.S | re.I)
        if m:
            title = re.sub(r'\s+', ' ', m.group(1)).strip()

    chunks = []
    if title:
        chunks.append(f'# {title}\n')

    if detect_slides:
        slides = split_slides(body)
    else:
        slides = None

    if slides:
        chunks.append(f'_Presentation deck — {len(slides)} slides_\n')
        for num, t, te, inner in slides:
            heading = f'## Slide {num}'
            if t:
                heading += f' — {t}'
            if te:
                heading += f'  \n_{te}_'
            chunks.append(heading + '\n')
            chunks.append(html_to_markdown(inner, want_assets=want_assets))
            chunks.append('')
    else:
        chunks.append(html_to_markdown(body, want_assets=want_assets))

    md = '\n'.join(chunks)
    md = re.sub(r'\n{3,}', '\n\n', md).strip() + '\n'

    if extract_assets and asset_log:
        note = '_Extracted assets:_\n' + '\n'.join(
            f'- `{p}` ({sz/1024:.0f} KB)' for p, sz in sorted(asset_log.items())
        )
        md = md + '\n' + note + '\n'

    if out_path:
        with open(out_path, 'w', encoding='utf-8') as fh:
            fh.write(md)
        return out_path
    return md


def main():
    ap = argparse.ArgumentParser(description='HTML → Markdown (handles huge base64 decks)')
    ap.add_argument('input', help='input .html file')
    ap.add_argument('output', nargs='?', help='output .md (default: stdout)')
    ap.add_argument('--extract-assets', action='store_true',
                    help='save base64 images/videos to <stem>_assets/ and rewrite refs')
    ap.add_argument('--no-assets', action='store_true',
                    help='omit [IMAGE]/[VIDEO] placeholders entirely')
    ap.add_argument('--no-slides', action='store_true',
                    help='do not detect/split deck slides')
    args = ap.parse_args()

    out = convert_file(
        args.input,
        args.output,
        extract_assets=args.extract_assets,
        want_assets=not args.no_assets,
        detect_slides=not args.no_slides,
    )
    if not args.output:
        sys.stdout.buffer.write(out.encode('utf-8'))
    else:
        sys.stderr.write(f'wrote {args.output}\n')


if __name__ == '__main__':
    main()
