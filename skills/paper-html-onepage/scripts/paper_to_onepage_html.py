#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import base64
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET


# curl is the zero-dependency network fallback (mirrors /web-search-fallback
# Route 1 & 4). It keeps the skill working when the `requests` library or the
# MCP web_search / webReader tools are unavailable or rate-limited (429).
CURL_BIN = shutil.which('curl')


def ensure_deps():
    global requests
    missing = []
    try:
        import requests  # noqa: F401
    except Exception:
        missing.append('requests')
    try:
        import fitz  # noqa: F401
    except Exception:
        missing.append('PyMuPDF')
    if missing:
        cmd = [sys.executable, '-m', 'pip', 'install', *missing]
        try:
            subprocess.check_call(cmd)
        except Exception as exc:
            # PyMuPDF is mandatory; `requests` is optional thanks to the curl fallback.
            if 'PyMuPDF' in missing:
                raise RuntimeError(f'Failed to install required dependency PyMuPDF: {exc}') from exc
            print(f'[WARN] could not install requests ({exc}); will rely on curl fallback', file=sys.stderr)
    # Re-evaluate `requests` after a possible install; None => use the curl path.
    try:
        import requests as _requests  # noqa: F401
        requests = _requests
    except Exception:
        requests = None  # type: ignore


ensure_deps()
import fitz  # type: ignore


def _curl_fetch_text(url, params=None, timeout=30):
    """Fetch a URL body as text via curl (web-search-fallback Route 1 & 4)."""
    if not CURL_BIN:
        raise RuntimeError('curl not found on PATH')
    full_url = url
    if params:
        full_url = f'{url}?{urllib.parse.urlencode(params)}'
    proc = subprocess.run(
        [CURL_BIN, '-sL', '--max-time', str(int(timeout)), '-A', 'paper-html-onepage/1.0', full_url],
        capture_output=True,
        timeout=timeout + 15,
    )
    if proc.returncode != 0:
        raise RuntimeError(f'curl exited with code {proc.returncode}')
    body = proc.stdout.decode('utf-8', errors='replace')
    if not body.strip():
        raise RuntimeError('curl returned an empty body')
    return body


def _curl_download_file(url, out_path, timeout=120):
    """Download a binary file via curl (fallback for requests streaming)."""
    if not CURL_BIN:
        raise RuntimeError('curl not found on PATH')
    proc = subprocess.run(
        [CURL_BIN, '-sL', '--max-time', str(int(timeout)), '-A', 'paper-html-onepage/1.0', '-o', out_path, url],
        capture_output=True,
        timeout=timeout + 30,
    )
    if proc.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise RuntimeError(f'curl download failed (exit {proc.returncode})')
    return out_path


def _http_get_text(url, params=None, timeout=25):
    """GET text with a graceful requests -> curl fallback."""
    if requests is not None:
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            print(f'[WARN] requests GET failed for {url} ({exc}); trying curl fallback', file=sys.stderr)
    return _curl_fetch_text(url, params=params, timeout=timeout)


ARXIV_API = 'http://export.arxiv.org/api/query'
RULES_FILENAME = 'categoryRules.md'


def search_arxiv(query: str, max_results: int = 5):
    params = {
        'search_query': f'all:{query}',
        'start': 0,
        'max_results': max_results,
        'sortBy': 'relevance',
        'sortOrder': 'descending',
    }
    text = _http_get_text(ARXIV_API, params=params, timeout=25)
    root = ET.fromstring(text)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    entries = []
    for e in root.findall('atom:entry', ns):
        title = (e.findtext('atom:title', default='', namespaces=ns) or '').strip().replace('\n', ' ')
        summary = (e.findtext('atom:summary', default='', namespaces=ns) or '').strip().replace('\n', ' ')
        published = (e.findtext('atom:published', default='', namespaces=ns) or '')[:10]
        authors = [a.findtext('atom:name', default='', namespaces=ns) for a in e.findall('atom:author', ns)]
        links = e.findall('atom:link', ns)
        pdf_url = None
        abs_url = None
        for l in links:
            href = l.attrib.get('href', '')
            title_attr = l.attrib.get('title', '')
            typ = l.attrib.get('type', '')
            if title_attr == 'pdf' or typ == 'application/pdf':
                pdf_url = href
            if 'arxiv.org/abs/' in href:
                abs_url = href
        if abs_url and not pdf_url:
            pdf_url = abs_url.replace('/abs/', '/pdf/') + '.pdf'
        entries.append({
            'title': title,
            'summary': summary,
            'published': published,
            'authors': [a for a in authors if a],
            'pdf_url': pdf_url,
            'abs_url': abs_url,
        })
    return entries


def fetch_arxiv_by_id(arxiv_id: str):
    params = {'id_list': arxiv_id.strip()}
    try:
        text = _http_get_text(ARXIV_API, params=params, timeout=25)
    except Exception as exc:
        print(f'[WARN] arXiv metadata fetch failed for {arxiv_id}: {exc}', file=sys.stderr)
        return None
    root = ET.fromstring(text)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    e = root.find('atom:entry', ns)
    if e is None:
        return None
    title = (e.findtext('atom:title', default='', namespaces=ns) or '').strip().replace('\n', ' ')
    summary = (e.findtext('atom:summary', default='', namespaces=ns) or '').strip().replace('\n', ' ')
    published = (e.findtext('atom:published', default='', namespaces=ns) or '')[:10]
    authors = [a.findtext('atom:name', default='', namespaces=ns) for a in e.findall('atom:author', ns)]
    links = e.findall('atom:link', ns)
    pdf_url = None
    abs_url = None
    for l in links:
        href = l.attrib.get('href', '')
        title_attr = l.attrib.get('title', '')
        typ = l.attrib.get('type', '')
        if title_attr == 'pdf' or typ == 'application/pdf':
            pdf_url = href
        if 'arxiv.org/abs/' in href:
            abs_url = href
    if abs_url and not pdf_url:
        pdf_url = abs_url.replace('/abs/', '/pdf/') + '.pdf'
    return {
        'title': title,
        'summary': summary,
        'published': published,
        'authors': [a for a in authors if a],
        'pdf_url': pdf_url or '',
        'abs_url': abs_url or '',
    }


def download_pdf(url: str, out_path: str):
    if requests is not None:
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(out_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            f.write(chunk)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return
            raise RuntimeError('downloaded file is empty')
        except Exception as exc:
            print(f'[WARN] requests download failed for {url} ({exc}); trying curl fallback', file=sys.stderr)
    _curl_download_file(url, out_path)


def extract_pdf_text(pdf_path: str, max_pages: int = 80):
    # Follow the pdf-reader skill: PyMuPDF-based extraction from the local PDF.
    doc = fitz.open(pdf_path)
    pages = min(len(doc), max_pages)
    chunks = []
    page_texts = []
    for i in range(pages):
        txt = doc.load_page(i).get_text('text')
        txt = txt.replace('\x00', ' ')
        page_texts.append(txt)
        chunks.append(f"\n\n--- PAGE {i+1} ---\n" + txt)
    doc.close()
    full = ''.join(chunks)
    return full, pages, page_texts


def clean_text(t: str):
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def normalize_mojibake(text: str):
    fixes = {
        '鈥?': '-',
        '鈥': '-',
        '锟': '',
        '鉂?': 'x',
        '路': '·',
        '芒': 'z',
        '尾': 'beta',
        '伓': '',
    }
    out = text
    for k, v in fixes.items():
        out = out.replace(k, v)
    return out


def normalize_pdf_text(text: str):
    text = normalize_mojibake(text)
    text = re.sub(r'--- PAGE \d+ ---', ' ', text)
    text = text.replace('\x00', ' ')
    return clean_text(text)


def default_category_rules():
    return {
        'categories': {
            'locomotion': {
                'match_title_any': ['beyondmimic'],
                'match_text_any': ['humanoid', 'locomotion', 'motion tracking', 'guided diffusion', 'spin-kicks', 'cartwheels'],
                'cards': {
                    'summary_title': 'Motion Control Summary',
                    'method_title': 'Control / Training Highlights',
                    'result_title': 'Locomotion Results',
                    'risk_title': 'Deployment / Generalization Risks',
                    'lens_title': 'Locomotion Reading Lens',
                    'lens_text': 'Focus on motion source, tracking objective, policy parameterization, robustness outside nominal trajectories, and whether skill composition is shown beyond canned demos.',
                },
            },
            'world_model': {
                'match_title_any': ['dreamdojo', 'robot world model'],
                'match_text_any': ['world model', 'latent action', 'continuous latent actions', 'world model pretraining'],
                'cards': {
                    'summary_title': 'World Model Summary',
                    'method_title': 'Representation / Training Highlights',
                    'result_title': 'Data / Transfer Signals',
                    'risk_title': 'Coverage / Control Risks',
                    'lens_title': 'World Model Reading Lens',
                    'lens_text': 'Check data scale first, then action representation, then how the model is connected to control. Many papers look strong on video prediction but weak on downstream action grounding.',
                },
            },
            'world_action_model': {
                'match_title_any': ['dreamzero', 'world action models are zero-shot policies'],
                'match_text_any': ['world action model', 'world action models', 'zero-shot policies'],
                'cards': {
                    'summary_title': 'World Action Model Summary',
                    'method_title': 'Action Modeling Highlights',
                    'result_title': 'Zero-shot / Transfer Results',
                    'risk_title': 'Transfer / Embodiment Risks',
                    'lens_title': 'WAM Reading Lens',
                    'lens_text': 'Verify whether the action model really supports policy behavior, or whether the gains mainly come from world priors and post-training. The cross-embodiment claim deserves extra scrutiny.',
                },
            },
            'vision_action_model': {
                'match_title_any': [],
                'match_text_any': ['vision action model', 'vision-language-action', 'vla', 'vision encoder'],
                'cards': {
                    'summary_title': 'Vision Action Model Summary',
                    'method_title': 'Perception / Action Highlights',
                    'result_title': 'Execution Results',
                    'risk_title': 'Perception / Latency Risks',
                    'lens_title': 'VAM Reading Lens',
                    'lens_text': 'Pay attention to observation stack, action head design, and deployment latency. VAM papers often hide failure modes in visual corner cases and control lag.',
                },
            },
            'multimodal_interpretation': {
                'match_title_any': ['mimic:', 'multimodal inversion'],
                'match_text_any': ['multimodal inversion', 'vlm', 'model interpretation', 'conceptualization'],
                'cards': {
                    'summary_title': 'Interpretation Summary',
                    'method_title': 'Inversion Highlights',
                    'result_title': 'Interpretability Results',
                    'risk_title': 'Interpretation Risks',
                    'lens_title': 'Interpretation Reading Lens',
                    'lens_text': 'Ask whether the inversion is faithful to model internals or mainly visually plausible. Good images do not automatically imply valid model interpretation.',
                },
            },
            'general': {
                'match_title_any': [],
                'match_text_any': [],
                'cards': {
                    'summary_title': 'Core Summary',
                    'method_title': 'Method Highlights',
                    'result_title': 'Benchmarks & Results',
                    'risk_title': 'Limitations & Risks',
                    'lens_title': 'Reading Lens',
                    'lens_text': 'Start from task definition, then identify the core representation, objective, and evaluation setup before trusting the headline claims.',
                },
            },
        }
    }


def parse_rules_json_from_markdown(text: str):
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, flags=re.S | re.I)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def load_category_rules(start_dir: str):
    cur = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(cur, RULES_FILENAME)
        if os.path.exists(candidate):
            raw = open(candidate, 'r', encoding='utf-8', errors='ignore').read()
            parsed = parse_rules_json_from_markdown(raw)
            if parsed and isinstance(parsed, dict) and 'categories' in parsed:
                return parsed, candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return default_category_rules(), ''


def first_sentences(text: str, n=4):
    sents = re.split(r'(?<=[\.!?。！？])\s+', clean_text(text))
    return ' '.join(sents[:n]).strip()


def find_section(text: str, keys):
    lower = text.lower()
    positions = []
    for k in keys:
        p = lower.find(k.lower())
        if p >= 0:
            positions.append((p, k))
    if not positions:
        return ''
    positions.sort()
    start = positions[0][0]
    end = min(len(text), start + 4500)
    return text[start:end]


def find_heading_block(text: str, headings, max_chars=3500):
    lines = [ln.strip() for ln in text.splitlines()]
    targets = [h.lower() for h in headings]
    for i, line in enumerate(lines):
        low = line.lower()
        if any(low == h or low.startswith(h + ' ') or low.startswith(h + ':') for h in targets):
            block = [line]
            for nxt in lines[i + 1:]:
                nxt_clean = nxt.strip()
                if not nxt_clean:
                    if block:
                        block.append('')
                    continue
                if re.match(r'^\d+(\.\d+)*\s+[A-Z]', nxt_clean):
                    break
                if nxt_clean.lower() in targets:
                    break
                if re.match(r'^(abstract|introduction|method|methods|approach|architecture|experiments?|results?|evaluation|discussion|limitations?|conclusion|references)\b', nxt_clean, flags=re.I):
                    break
                block.append(nxt_clean)
                if len('\n'.join(block)) >= max_chars:
                    break
            joined = '\n'.join(block)
            return joined.strip()
    return ''


def infer_arxiv_id(pdf_path: str, first_page_text: str):
    candidates = []
    base = os.path.basename(pdf_path)
    candidates.extend(re.findall(r'(\d{4}\.\d{4,5})(?:v\d+)?', base))
    candidates.extend(re.findall(r'arXiv:(\d{4}\.\d{4,5})(?:v\d+)?', first_page_text, flags=re.I))
    for c in candidates:
        if c:
            return c
    return ''


def infer_title_and_authors(first_page_text: str):
    lines = [ln.strip() for ln in first_page_text.splitlines() if ln.strip()]
    title_lines = []
    for line in lines[:12]:
        if re.search(r'arXiv:\d{4}\.\d{4,5}', line, flags=re.I):
            break
        if re.search(r'@(?!\w)|Abstract\b|Introduction\b', line, flags=re.I):
            break
        if re.search(r'(University|Institute|NVIDIA|Stanford|Berkeley|Abstract)', line) and title_lines:
            break
        if re.match(r'^[\d\W_]+$', line):
            continue
        title_lines.append(line)
        if len(' '.join(title_lines)) > 180:
            break
    title = ' '.join(title_lines[:3]).strip(' ,;')

    author_lines = []
    passed_title = False
    for line in lines[:20]:
        if not passed_title and title and line in title_lines:
            continue
        passed_title = True
        if re.search(r'^(Abstract|Introduction)\b', line, flags=re.I):
            break
        if re.search(r'(University|Institute|NVIDIA|Stanford|Berkeley|Austin|Project Leads|Co-First)', line):
            break
        if any(ch.isdigit() for ch in line) or ',' in line:
            author_lines.append(line)
    authors = clean_text(' '.join(author_lines[:3]))
    authors = re.sub(r'\s+', ' ', authors)
    return title, authors


def summarize_authors(raw_authors: str):
    if not raw_authors:
        return []
    text = re.sub(r'[\d*†‡§¶∗]+', ' ', raw_authors)
    parts = [clean_text(x) for x in re.split(r',| and ', text) if clean_text(x)]
    out = []
    for p in parts:
        if len(p.split()) <= 8 and not re.search(r'(University|Institute|NVIDIA|Stanford|Berkeley)', p, flags=re.I):
            out.append(p)
    return out[:12]


def slugify_filename(text: str):
    text = re.sub(r'[<>:"/\\|?*]+', ' ', text)
    text = re.sub(r'\s+', '_', text.strip())
    text = re.sub(r'_+', '_', text).strip('._')
    return text or 'paper_summary'


def abbreviate_title_phrase(text: str):
    words = [w for w in re.findall(r'[A-Za-z][A-Za-z0-9+-]*', text) if w.lower() not in {
        'a', 'an', 'the', 'for', 'of', 'to', 'and', 'or', 'with', 'using', 'via', 'in', 'on', 'from', 'by', 'make', 'good'
    }]
    if 2 <= len(words) <= 4:
        acronym = ''.join(w[0].upper() for w in words)
        if len(acronym) >= 2:
            return acronym
    return ''


def derive_paper_keyword(meta, pdf_path=''):
    title = (meta.get('title') or '').strip()
    summary = (meta.get('summary') or '').strip()
    combined = f'{title}\n{summary}'.lower()
    phrase_aliases = [
        ('dreamdojo', 'DreamDojo'),
        ('dreamzero', 'DreamZero'),
        ('selective adversarial motion prior', 'AMP'),
        ('adversarial motion priors', 'AMP'),
        ('adversarial motion prior', 'AMP'),
        ('world action models', 'WAM'),
        ('world action model', 'WAM'),
        ('vision-language-action', 'VLA'),
    ]
    for phrase, alias in phrase_aliases:
        if phrase in combined:
            return alias

    camel_hits = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', title)
    if camel_hits:
        return camel_hits[0]

    title_head = clean_text(title.split(':', 1)[0]) or title
    short_acronym = abbreviate_title_phrase(title_head)
    if short_acronym:
        return short_acronym

    words = [
        w for w in re.findall(r'[A-Za-z0-9][A-Za-z0-9+-]*', title_head)
        if w.lower() not in {'a', 'an', 'the', 'for', 'of', 'to', 'and', 'or', 'with', 'using', 'via', 'in', 'on', 'from', 'by'}
    ]
    if words:
        return '_'.join(words[:4])

    if pdf_path:
        return os.path.splitext(os.path.basename(pdf_path))[0]
    return 'paper_summary'


def derive_title_suffix(meta, keyword):
    title = (meta.get('title') or '').strip()
    words = [
        w for w in re.findall(r'[A-Za-z0-9][A-Za-z0-9+-]*', title)
        if w.lower() not in {
            'a', 'an', 'the', 'for', 'of', 'to', 'and', 'or', 'with', 'using', 'via', 'in', 'on', 'from', 'by',
            'make', 'good', 'complex'
        }
    ]
    keyword_tokens = {x.lower() for x in re.findall(r'[A-Za-z0-9]+', keyword)}
    filtered = [w for w in words if w.lower() not in keyword_tokens]
    if filtered:
        return '_'.join(filtered[:3])
    return 'summary'


def choose_output_path(meta, requested_out, source_path=''):
    if requested_out:
        return requested_out
    keyword = derive_paper_keyword(meta, source_path)
    stem = slugify_filename(keyword)
    candidate = os.path.join(os.getcwd(), stem + '.html')
    if not os.path.exists(candidate):
        return candidate
    suffix = slugify_filename(derive_title_suffix(meta, keyword))
    return os.path.join(os.getcwd(), f'{stem}_{suffix}.html')


def choose_pdf_path_for_output(out_path):
    base, _ = os.path.splitext(os.path.abspath(out_path))
    return base + '.pdf'


def uniquify_path(path):
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    suffix = 2
    while True:
        candidate = f'{stem}_{suffix}{ext}'
        if not os.path.exists(candidate):
            return candidate
        suffix += 1


def extract_pdf_meta(pdf_path: str, page_texts):
    first_page = page_texts[0] if page_texts else ''
    arxiv_id = infer_arxiv_id(pdf_path, first_page)
    meta = None
    if arxiv_id:
        meta = fetch_arxiv_by_id(arxiv_id)
    if meta:
        return meta

    title, raw_authors = infer_title_and_authors(first_page)
    summary = find_heading_block(first_page, ['abstract'])
    if summary.lower().startswith('abstract'):
        summary = re.sub(r'^abstract\s*', '', summary, flags=re.I)
    return {
        'title': title or os.path.splitext(os.path.basename(pdf_path))[0],
        'summary': summary,
        'published': '',
        'authors': summarize_authors(raw_authors),
        'pdf_url': '',
        'abs_url': f'https://arxiv.org/abs/{arxiv_id}' if arxiv_id else '',
    }


def extract_metrics(text: str, limit=8):
    rows = []
    patterns = [
        r'([A-Za-z][A-Za-z0-9\-_/ ]{1,20})\s*[:=]\s*([0-9]+(?:\.[0-9]+)?\s*(?:%|fps|fps\b|dB|ms|m|h|x)?)',
        r'([0-9]+(?:\.[0-9]+)?\s*(?:%|fps|dB|ms|x))',
    ]
    for m in re.finditer(patterns[0], text):
        k = clean_text(m.group(1))
        v = clean_text(m.group(2))
        if re.search(r'(arxiv|preprint|doi|page|figure|table)', k, flags=re.I):
            continue
        if len(k) <= 24 and len(v) <= 16:
            rows.append((k, v))
        if len(rows) >= limit:
            break
    if not rows:
        for m in re.finditer(patterns[1], text):
            rows.append((f'Metric {len(rows)+1}', clean_text(m.group(1))))
            if len(rows) >= min(4, limit):
                break
    return rows


def bulletize(text: str, max_items=4, max_len=150):
    sents = re.split(r'(?<=[\.!?。！？])\s+', clean_text(text))
    out = []
    for s in sents:
        s = s.strip()
        if 18 <= len(s) <= max_len:
            out.append(s)
        if len(out) >= max_items:
            break
    return out


def render_fulltext_html(meta, full_text, pages_read, out_path):
    title = html.escape(meta.get('title') or 'Paper Fulltext')
    authors = ', '.join(meta.get('authors') or [])
    pub = meta.get('published') or ''
    abs_url = meta.get('abs_url') or ''
    body_text = html.escape(full_text)
    page_count = full_text.count('--- PAGE ')
    html_doc = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title} — Fulltext</title>
<style>
body{{font-family:'Segoe UI','Microsoft YaHei',sans-serif;background:#f8f9fb;color:#1a1a2e;margin:0;padding:20px;line-height:1.55}}
.wrap{{max-width:1100px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:20px}}
h1{{margin:0 0 6px 0;color:#0f3460}} .sub{{color:#6b7280;font-size:13px;margin-bottom:16px}}
pre{{white-space:pre-wrap;word-wrap:break-word;background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:14px;font-size:13px}}
</style>
</head>
<body>
  <div class="wrap">
    <h1>{title}</h1>
    <div class="sub">{html.escape(authors)} · {html.escape(pub)} · pages-read={pages_read} · detected-pages={page_count} · <a href="{html.escape(abs_url)}">source</a></div>
    <pre>{body_text}</pre>
  </div>
</body>
</html>
'''
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_doc)


def render_onepage_html(meta, full_text, pages_read, out_path):
    analysis_text = normalize_pdf_text(full_text)
    rules, rules_path = load_category_rules(os.path.dirname(os.path.abspath(out_path)))
    paper_type = classify_paper(meta, analysis_text, rules)
    abstract = meta.get('summary', '') or find_heading_block(full_text, ['abstract']) or first_sentences(analysis_text, 5)
    abstract = re.sub(r'^abstract\s*', '', normalize_pdf_text(abstract), flags=re.I)
    blocks = build_category_blocks(paper_type, {**meta, 'summary': abstract}, analysis_text, full_text, rules)
    beginner_points = [
        'Problem: what practical control or prediction gap is the paper solving?',
        'Method: what are the inputs, core module, and outputs?',
        'Evaluation: what tasks and metrics are used to validate improvement?',
        'Limits: where does the paper admit brittleness or missing coverage?',
    ]
    metrics = blocks.get('metrics') or extract_metrics(analysis_text, 8)

    def li(items):
        return '\n'.join(f'<li>{html.escape(x)}</li>' for x in items)

    metric_rows = '\n'.join(
        f'<tr><td>{html.escape(k)}</td><td><b>{html.escape(v)}</b></td></tr>' for k, v in metrics
    ) or '<tr><td>N/A</td><td>N/A</td></tr>'

    title = html.escape(meta.get('title') or 'Paper Summary')
    authors = ', '.join(meta.get('authors') or [])
    pub = meta.get('published') or ''
    abs_url = meta.get('abs_url') or ''

    html_doc = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title} — One-page Summary</title>
<style>
@page {{ size:A4; margin:8mm; }}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI','Microsoft YaHei',sans-serif;font-size:10px;line-height:1.35;background:#f8f9fb;color:#1a1a2e;padding:10px;max-width:210mm;margin:auto}}
h1{{font-size:15px;text-align:center;color:#0f3460;margin-bottom:3px}}
.sub{{text-align:center;font-size:9px;color:#666;margin-bottom:8px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.grid3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}}
.card{{background:#fff;border-radius:6px;padding:8px 10px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card h2{{font-size:11px;color:#0f3460;border-bottom:2px solid #e94560;padding-bottom:3px;margin-bottom:5px}}
.card h3{{font-size:10px;color:#533483;margin:4px 0 2px}}
table{{width:100%;border-collapse:collapse;font-size:9px;margin-top:3px}}
th{{background:#0f3460;color:#fff;padding:3px 4px;text-align:center;font-weight:600}}
td{{padding:2px 4px;text-align:center;border-bottom:1px solid #e0e0e0}}
tr:nth-child(even) td{{background:#f4f6fb}}
ul{{padding-left:14px}} li{{margin-bottom:1px}}
.compact{{font-size:9px}}
.footer{{text-align:center;font-size:8px;color:#999;margin-top:6px}}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="sub">{html.escape(authors)} · {html.escape(pub)} · pages-read={pages_read} · <a href="{html.escape(abs_url)}">source</a></div>

<div class="grid2">
  <div class="card">
    <h2>{html.escape(blocks['summary_title'])}</h2>
    <p class="compact">{html.escape(first_sentences(blocks['summary_text'], 6))}</p>
    <h3>{html.escape(blocks['method_title'])}</h3>
    <ul class="compact">{li(blocks['method_points'])}</ul>
  </div>
  <div class="card">
    <h2>{html.escape(blocks['result_title'])}</h2>
    <ul class="compact">{li(blocks['result_points'])}</ul>
    <h3>Key Metrics</h3>
    <table>
      <tr><th>Metric</th><th>Value</th></tr>
      {metric_rows}
    </table>
  </div>
</div>

<div class="grid2" style="margin-top:8px">
  <div class="card">
    <h2>Beginner Interpretation</h2>
    <ul class="compact">{li(beginner_points)}</ul>
    <h3>{html.escape(blocks['lens_title'])}</h3>
    <p class="compact">{html.escape(blocks['lens_text'])}</p>
  </div>
  <div class="card">
    <h2>{html.escape(blocks['risk_title'])}</h2>
    <ul class="compact">{li(blocks['risk_points'] if blocks['risk_points'] else ['No explicit limitation section was cleanly extracted; verify appendix and failure cases manually.'])}</ul>
    <h3>Practical Reading Path</h3>
    <p class="compact">Read the abstract and setup first, then inspect the training objective and ablations, and only then trust the demo videos or preference studies.</p>
  </div>
</div>

<div class="footer">Auto-generated by paper-html-onepage skill · PDF read via PyMuPDF · category={html.escape(paper_type)}{(' · rules=' + html.escape(os.path.basename(rules_path))) if rules_path else ''}</div>
</body>
</html>
'''

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_doc)


def strip_html_tags(text: str):
    text = html.unescape(text)
    text = re.sub(r'<script.*?>.*?</script>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<style.*?>.*?</style>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = normalize_mojibake(text)
    return clean_text(text)


def load_text_from_item(path: str, max_pages: int):
    ext = os.path.splitext(path)[1].lower()
    title = os.path.splitext(os.path.basename(path))[0]
    if ext == '.pdf':
        txt, pages, _ = extract_pdf_text(path, max_pages=max_pages)
        return {'title': title, 'text': txt, 'pages': pages, 'source': path}
    if ext in ('.html', '.htm'):
        raw = open(path, 'r', encoding='utf-8', errors='ignore').read()
        return {'title': title, 'text': strip_html_tags(raw), 'pages': 1, 'source': path}
    raw = open(path, 'r', encoding='utf-8', errors='ignore').read()
    return {'title': title, 'text': raw, 'pages': 1, 'source': path}


def inline_markdown_to_html(text: str):
    escaped = html.escape(text.strip())
    escaped = re.sub(r'`([^`]+)`', lambda m: f'<code>{m.group(1)}</code>', escaped)
    escaped = re.sub(r'\*\*([^\*]+)\*\*', lambda m: f'<b>{m.group(1)}</b>', escaped)
    escaped = re.sub(r'\*([^\*]+)\*', lambda m: f'<i>{m.group(1)}</i>', escaped)
    return escaped


def parse_reflection_markdown(raw_text: str):
    blocks = []
    lines = raw_text.replace('\r\n', '\n').split('\n')
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if re.match(r'^#{1,6}\s+', stripped):
            level = len(stripped) - len(stripped.lstrip('#'))
            blocks.append({'type': 'heading', 'level': min(level, 3), 'text': stripped[level:].strip()})
            i += 1
            continue
        img_match = re.match(r'^!\[(.*?)\]\((.*?)\)\s*$', stripped)
        if img_match:
            blocks.append({'type': 'image', 'alt': img_match.group(1).strip(), 'src': img_match.group(2).strip()})
            i += 1
            continue
        if re.match(r'^\d+\.\s+', stripped):
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                if not cur:
                    i += 1
                    break
                if not re.match(r'^\d+\.\s+', cur):
                    break
                item = re.sub(r'^\d+\.\s+', '', cur)
                i += 1
                subparts = []
                while i < len(lines):
                    nxt = lines[i].strip()
                    if not nxt:
                        i += 1
                        break
                    if re.match(r'^\d+\.\s+', nxt) or re.match(r'^#{1,6}\s+', nxt) or re.match(r'^!\[(.*?)\]\((.*?)\)\s*$', nxt):
                        break
                    subparts.append(nxt)
                    i += 1
                if subparts:
                    item += '\n' + '\n'.join(subparts)
                items.append(item)
            blocks.append({'type': 'olist', 'items': items})
            continue
        if re.match(r'^[-*]\s+', stripped):
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                if not cur:
                    i += 1
                    break
                if not re.match(r'^[-*]\s+', cur):
                    break
                items.append(re.sub(r'^[-*]\s+', '', cur))
                i += 1
            blocks.append({'type': 'ulist', 'items': items})
            continue
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt:
                i += 1
                break
            if re.match(r'^#{1,6}\s+', nxt) or re.match(r'^\d+\.\s+', nxt) or re.match(r'^[-*]\s+', nxt) or re.match(r'^!\[(.*?)\]\((.*?)\)\s*$', nxt):
                break
            para_lines.append(nxt)
            i += 1
        blocks.append({'type': 'paragraph', 'text': '\n'.join(para_lines)})
    return blocks


def reflection_title_from_path(path: str):
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r'[_\-]+', ' ', stem).strip() or 'Reflection'


def reflection_subtitle(blocks):
    for idx, block in enumerate(blocks):
        if block['type'] == 'paragraph':
            text = clean_text(block['text'])
            if text:
                return text[:180]
    return 'Structured reflection converted from local notes.'


def reflection_questions(blocks):
    hits = []
    patterns = ['?', '？', '还需要再查', '待确认', '值得探讨', '为什么', '查证']
    for idx, block in enumerate(blocks):
        if block['type'] != 'paragraph':
            continue
        text = clean_text(block['text'])
        if any(p in text for p in patterns):
            hits.append(text)
        if len(hits) >= 4:
            break
    return hits


def reflection_chips(title: str, raw: str, blocks):
    chips = []
    combined = f'{title}\n{raw}'.lower()
    mapping = [
        ('sim2real', 'Sim2Real'),
        ('ppo', 'PPO'),
        ('locomotion', 'Locomotion'),
        ('kinematic retarget', 'Kinematic Retargeting'),
        ('retargeting', 'Retargeting'),
        ('mujoco', 'MuJoCo'),
        ('isaac lab', 'Isaac Lab'),
        ('isaaclab', 'Isaac Lab'),
        ('domain randomization', 'Domain Randomization'),
        ('pd control', 'PD Control'),
        ('generalist policy', 'Generalist Policy'),
        ('teleoperation', 'Teleoperation'),
        ('sim2sim', 'Sim2Sim'),
    ]
    for needle, label in mapping:
        if needle in combined and label not in chips:
            chips.append(label)
        if len(chips) >= 4:
            break
    if not chips:
        chips = ['Interview Notes', 'Structured Reflection']
    return chips


def local_image_to_data_uri(img_src: str, base_dir: str):
    if re.match(r'^[a-zA-Z]+://', img_src):
        return img_src
    abs_path = os.path.abspath(os.path.join(base_dir, img_src))
    if not os.path.exists(abs_path):
        return abs_path.replace('\\', '/')
    mime_type, _ = mimetypes.guess_type(abs_path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    with open(abs_path, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode('ascii')
    return f'data:{mime_type};base64,{encoded}'


def render_reflection_blocks(blocks, base_dir: str):
    rendered = []
    section_open = False

    def open_section(title='Reflection'):
        nonlocal section_open
        if section_open:
            rendered.append('</div>')
        rendered.append(f'<div class="section"><h2>{html.escape(title)}</h2>')
        section_open = True

    open_section('Reflection')
    for idx, block in enumerate(blocks):
        if block['type'] == 'heading':
            open_section(block['text'])
            continue
        if block['type'] == 'paragraph':
            text = clean_text(block['text'])
            css = 'query' if any(x in text for x in ['?', '？', '还需要再查', '待确认', '值得探讨', '为什么', '查证']) else 'para'
            rendered.append(f'<p class="{css}">{inline_markdown_to_html(text)}</p>')
            continue
        if block['type'] == 'olist':
            rendered.append('<ol>')
            for item in block['items']:
                parts = [inline_markdown_to_html(x) for x in item.split('\n') if x.strip()]
                if not parts:
                    continue
                rendered.append(f'<li>{parts[0]}{"".join(f"<div class=\"subline\">{x}</div>" for x in parts[1:])}</li>')
            rendered.append('</ol>')
            continue
        if block['type'] == 'ulist':
            rendered.append('<ul>')
            for item in block['items']:
                rendered.append(f'<li>{inline_markdown_to_html(item)}</li>')
            rendered.append('</ul>')
            continue
        if block['type'] == 'image':
            img_src = local_image_to_data_uri(block['src'], base_dir)
            rendered.append(
                f'<figure><img src="{html.escape(img_src)}" alt="{html.escape(block["alt"] or "reflection image")}" />'
                f'<figcaption>{html.escape(block["alt"] or os.path.basename(block["src"]))}</figcaption></figure>'
            )
            continue
    if section_open:
        rendered.append('</div>')
    return ''.join(rendered)


def render_reflection_html(reflection_path: str, out_path: str):
    raw = open(reflection_path, 'r', encoding='utf-8', errors='ignore').read()
    blocks = parse_reflection_markdown(raw)
    title = reflection_title_from_path(reflection_path)
    subtitle = reflection_subtitle(blocks)
    questions = reflection_questions(blocks)
    body_html = render_reflection_blocks(blocks, os.path.dirname(os.path.abspath(reflection_path)))
    chip_text = reflection_chips(title, raw, blocks)
    question_html = ''.join(f'<li>{inline_markdown_to_html(x)}</li>' for x in questions) or '<li>No explicit question-like sentence detected.</li>'
    html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{html.escape(title)}</title>
<style>
@page {{ size: A4; margin: 8mm; }}
:root {{ --bg:#f4efe6; --paper:#fffdf8; --ink:#1f1d1a; --muted:#635b4f; --line:#d8cfbf; --accent:#8e4b2c; --query:#fff2d9; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:radial-gradient(circle at top left,#f8f1e4 0,transparent 35%),linear-gradient(180deg,#efe7da 0%,#f7f2ea 100%); color:var(--ink); font-family:'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif; font-size:10px; line-height:1.42; }}
.page {{ width:210mm; min-height:297mm; margin:0 auto; padding:8mm; }}
.sheet {{ background:var(--paper); border:1px solid var(--line); border-radius:14px; padding:10px 12px; box-shadow:0 10px 30px rgba(56,43,28,.08); }}
.hero {{ display:grid; grid-template-columns:1.3fr .8fr; gap:10px; margin-bottom:10px; }}
.hero-main,.hero-side,.section {{ border:1px solid var(--line); border-radius:12px; padding:10px; background:#fffefa; }}
.hero-main {{ background:linear-gradient(135deg,#fffdf7 0%,#f6ede1 100%); }}
h1 {{ margin:0 0 6px; font-size:22px; line-height:1.1; color:var(--accent); }}
h2 {{ margin:0 0 6px; font-size:12px; color:var(--accent); }}
.subtitle,.hero-side,.footer,figcaption {{ color:var(--muted); }}
.chips {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:8px; }}
.chip {{ padding:3px 7px; border-radius:999px; border:1px solid #d3c1ae; background:#fff7ed; font-size:9px; }}
.columns {{ column-count:2; column-gap:10px; }}
.section {{ break-inside:avoid; margin:0 0 10px; }}
p {{ margin:4px 0; }}
p.query {{ background:var(--query); border-left:3px solid #b47f1d; padding:6px 7px; border-radius:8px; }}
ol,ul {{ margin:5px 0 5px 18px; padding:0; }}
li {{ margin:3px 0; }}
.subline {{ margin-top:3px; color:#4d463d; }}
figure {{ margin:8px 0; break-inside:avoid; }}
img {{ width:100%; display:block; border-radius:8px; border:1px solid var(--line); }}
code {{ background:#f6f2ea; padding:1px 4px; border-radius:4px; }}
.footer {{ margin-top:8px; text-align:center; font-size:8.5px; }}
</style>
</head>
<body>
<div class="page"><div class="sheet">
  <div class="hero">
    <div class="hero-main">
      <h1>{html.escape(title)}</h1>
      <div class="subtitle">{html.escape(subtitle)}</div>
      <div class="chips">{''.join(f'<span class="chip">{html.escape(x)}</span>' for x in chip_text)}</div>
    </div>
    <div class="hero-side">
      <h2>Review Focus</h2>
      <ul>{question_html}</ul>
    </div>
  </div>
  <div class="columns">{body_html}</div>
  <div class="footer">Generated by paper-html-onepage --reflection from {html.escape(os.path.basename(reflection_path))}</div>
</div></div>
</body>
</html>"""
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_doc)


def build_from_reflection(reflection_path, out_path):
    src_abs = os.path.abspath(reflection_path)
    if not os.path.exists(src_abs):
        raise SystemExit(f'Not found: {reflection_path}')
    if not out_path:
        out_path = os.path.splitext(src_abs)[0] + '.html'
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    render_reflection_html(src_abs, out_path)
    return out_path


def infer_axes(text: str):
    axes = []
    checks = [
        ('Data Source', ['dataset', 'data', 'hours', 'human video', 'robot data', 'play data']),
        ('Training Paradigm', ['pretrain', 'post-train', 'finetune', 'distill', 'causal', 'autoregressive']),
        ('Action Modeling', ['action', 'latent action', 'chunk', 'relative', 'policy']),
        ('Real-world Control', ['real-time', 'closed-loop', 'hz', 'teleoperation', 'real world']),
        ('Generalization', ['zero-shot', 'ood', 'unseen', 'generalization']),
    ]
    lower = text.lower()
    for name, keys in checks:
        hit = any(k in lower for k in keys)
        axes.append((name, 'Strong evidence' if hit else 'Not explicit'))
    return axes


def extract_first_match(text: str, patterns):
    for p in patterns:
        m = re.search(p, text, flags=re.I)
        if m:
            return clean_text(m.group(0))
    return 'N/A'


def extract_fps_hz(text: str):
    return extract_first_match(
        text,
        [
            r'\b\d+(?:\.\d+)?\s*(?:fps|FPS)\b',
            r'\b\d+(?:\.\d+)?\s*(?:hz|Hz|HZ)\b',
            r'\breal[- ]?time\b.{0,30}\b\d+(?:\.\d+)?\b',
        ],
    )


def extract_dataset_snippets(text: str, limit=4):
    lines = re.split(r'[\n\r\.]', text)
    keys = ['dataset', 'data', 'hours', 'in-lab', 'egodex', 'dreamdojo', 'play data', 'trajector', 'human video']
    out = []
    for ln in lines:
        s = clean_text(ln)
        low = s.lower()
        if len(s) < 8:
            continue
        if any(k in low for k in keys):
            out.append(s[:160])
        if len(out) >= limit:
            break
    return out or ['N/A']


def extract_method_snippets(text, limit=5):
    lines = re.split(r'[\n\r\.]', text)
    keys = [
        'latent action', 'relative', 'chunk', 'distill', 'self forcing',
        'causal', 'autoregressive', 'closed-loop', 'flow matching',
        'temporal consistency', 'post-train', 'pretrain', 'fine-tune'
    ]
    out = []
    for ln in lines:
        s = clean_text(ln)
        low = s.lower()
        if len(s) < 8:
            continue
        if any(k in low for k in keys):
            out.append(s[:170])
        if len(out) >= limit:
            break
    return out or ['N/A']


def extract_data_scale(text: str):
    return extract_first_match(
        text,
        [
            r'\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*(?:hours|h)\b',
            r'\b\d+(?:\.\d+)?\s*(?:minutes|min)\b',
            r'\b\d+(?:,\d+)?\s*(?:skills|scenes|objects)\b',
        ],
    )


def classify_paper(meta, text: str, rules):
    title = meta.get('title', '').lower()
    summary = meta.get('summary', '').lower()
    blob = f"{title}\n{summary}\n{text}".lower()
    categories = rules.get('categories', {})
    for key, spec in categories.items():
        if key == 'general':
            continue
        title_hits = spec.get('match_title_any', [])
        if any(tok.lower() in title for tok in title_hits):
            return key
    for key, spec in categories.items():
        if key == 'general':
            continue
        text_hits = spec.get('match_text_any', [])
        if any(tok.lower() in blob for tok in text_hits):
            return key
    return 'general'


def fallback_points(primary, fallback_text, limit):
    return primary or bulletize(fallback_text, limit) or ['N/A']


def build_category_blocks(paper_type, meta, analysis_text, full_text, rules):
    title_blob = f"{meta.get('title', '')} {meta.get('summary', '')}"
    card_overrides = rules.get('categories', {}).get(paper_type, {}).get('cards', {})
    if paper_type == 'locomotion':
        method_src = (
            find_heading_block(full_text, ['method', 'methods', 'approach']) or
            find_section(analysis_text, ['motion tracking', 'guided diffusion', 'policy', 'reward', 'controller'])
        )
        eval_src = (
            find_heading_block(full_text, ['results', 'experiments', 'evaluation']) or
            find_section(analysis_text, ['human-like', 'preference', 'walking', 'running', 'skills', 'compose'])
        )
        risk_src = (
            find_heading_block(full_text, ['discussion', 'limitations']) or
            find_section(analysis_text, ['real-world', 'robustness', 'sim-to-real', 'failure'])
        )
        return {
            'summary_title': card_overrides.get('summary_title', 'Motion Control Summary'),
            'summary_text': meta.get('summary', '') or first_sentences(analysis_text, 6),
            'method_title': card_overrides.get('method_title', 'Control / Training Highlights'),
            'method_points': fallback_points(bulletize(method_src, 5), title_blob, 5),
            'result_title': card_overrides.get('result_title', 'Locomotion Results'),
            'result_points': fallback_points(bulletize(eval_src, 5), analysis_text, 5),
            'risk_title': card_overrides.get('risk_title', 'Deployment / Generalization Risks'),
            'risk_points': fallback_points(bulletize(risk_src, 3), analysis_text, 3),
            'lens_title': card_overrides.get('lens_title', 'Locomotion Reading Lens'),
            'lens_text': card_overrides.get('lens_text', 'Focus on motion source, tracking objective, policy parameterization, robustness outside nominal trajectories, and whether skill composition is shown beyond canned demos.'),
            'metrics': extract_metrics(analysis_text, 6),
        }
    if paper_type == 'world_model':
        method_src = (
            find_heading_block(full_text, ['method', 'methods', 'approach']) or
            find_section(analysis_text, ['latent action', 'pretrain', 'world model', 'continuous actions', 'video prediction'])
        )
        eval_src = (
            find_heading_block(full_text, ['results', 'experiments', 'evaluation']) or
            find_section(analysis_text, ['44k hours', 'transfer', 'generalization', 'dexterous', 'post-training'])
        )
        metrics = [('Data Scale', extract_data_scale(analysis_text)), ('Control Rate', extract_fps_hz(analysis_text))]
        metrics = [(k, v) for k, v in metrics if v != 'N/A'] or extract_metrics(analysis_text, 6)
        return {
            'summary_title': card_overrides.get('summary_title', 'World Model Summary'),
            'summary_text': meta.get('summary', '') or first_sentences(analysis_text, 6),
            'method_title': card_overrides.get('method_title', 'Representation / Training Highlights'),
            'method_points': fallback_points(extract_method_snippets(method_src or analysis_text, 5), analysis_text, 5),
            'result_title': card_overrides.get('result_title', 'Data / Transfer Signals'),
            'result_points': fallback_points(extract_dataset_snippets(eval_src or analysis_text, 5), analysis_text, 5),
            'risk_title': card_overrides.get('risk_title', 'Coverage / Control Risks'),
            'risk_points': fallback_points(bulletize(find_section(analysis_text, ['scarcity', 'coverage', 'action labels', 'limitation']), 3), analysis_text, 3),
            'lens_title': card_overrides.get('lens_title', 'World Model Reading Lens'),
            'lens_text': card_overrides.get('lens_text', 'Check data scale first, then action representation, then how the model is connected to control. Many papers look strong on video prediction but weak on downstream action grounding.'),
            'metrics': metrics,
        }
    if paper_type == 'world_action_model':
        method_src = (
            find_heading_block(full_text, ['method', 'methods', 'approach']) or
            find_section(analysis_text, ['world action model', 'jointly predicting video and action', 'cross-embodiment', 'post-training'])
        )
        eval_src = (
            find_heading_block(full_text, ['results', 'experiments', 'evaluation']) or
            find_section(analysis_text, ['zero-shot', 'few-shot', 'unseen tasks', 'unseen environments', 'x-embodiments'])
        )
        metrics = [('Data Scale', extract_data_scale(analysis_text)), ('Control Rate', extract_fps_hz(analysis_text))]
        metrics = [(k, v) for k, v in metrics if v != 'N/A'] or extract_metrics(analysis_text, 6)
        return {
            'summary_title': card_overrides.get('summary_title', 'World Action Model Summary'),
            'summary_text': meta.get('summary', '') or first_sentences(analysis_text, 6),
            'method_title': card_overrides.get('method_title', 'Action Modeling Highlights'),
            'method_points': fallback_points(extract_method_snippets(method_src or analysis_text, 5), analysis_text, 5),
            'result_title': card_overrides.get('result_title', 'Zero-shot / Transfer Results'),
            'result_points': fallback_points(bulletize(eval_src, 5), analysis_text, 5),
            'risk_title': card_overrides.get('risk_title', 'Transfer / Embodiment Risks'),
            'risk_points': fallback_points(bulletize(find_section(analysis_text, ['cross-embodiment', 'few-shot', 'unseen', 'limitation']), 3), analysis_text, 3),
            'lens_title': card_overrides.get('lens_title', 'WAM Reading Lens'),
            'lens_text': card_overrides.get('lens_text', 'Verify whether the action model really supports policy behavior, or whether the gains mainly come from world priors and post-training. The cross-embodiment claim deserves extra scrutiny.'),
            'metrics': metrics,
        }
    if paper_type == 'vision_action_model':
        method_src = find_section(analysis_text, ['vision action model', 'vision encoder', 'policy head', 'action tokens'])
        eval_src = find_section(analysis_text, ['real-world', 'latency', 'success rate', 'manipulation'])
        return {
            'summary_title': card_overrides.get('summary_title', 'Vision Action Model Summary'),
            'summary_text': meta.get('summary', '') or first_sentences(analysis_text, 6),
            'method_title': card_overrides.get('method_title', 'Perception / Action Highlights'),
            'method_points': fallback_points(bulletize(method_src, 5), analysis_text, 5),
            'result_title': card_overrides.get('result_title', 'Execution Results'),
            'result_points': fallback_points(bulletize(eval_src, 5), analysis_text, 5),
            'risk_title': card_overrides.get('risk_title', 'Perception / Latency Risks'),
            'risk_points': fallback_points(bulletize(find_section(analysis_text, ['latency', 'occlusion', 'failure', 'real-world']), 3), analysis_text, 3),
            'lens_title': card_overrides.get('lens_title', 'VAM Reading Lens'),
            'lens_text': card_overrides.get('lens_text', 'Pay attention to observation stack, action head design, and deployment latency. VAM papers often hide failure modes in visual corner cases and control lag.'),
            'metrics': extract_metrics(analysis_text, 6),
        }
    if paper_type == 'multimodal_interpretation':
        method_src = find_section(analysis_text, ['inversion', 'feature alignment', 'regularizers', 'semantic realism'])
        eval_src = find_section(analysis_text, ['quantitatively', 'qualitatively', 'visual quality', 'semantic metrics'])
        return {
            'summary_title': card_overrides.get('summary_title', 'Interpretation Summary'),
            'summary_text': meta.get('summary', '') or first_sentences(analysis_text, 6),
            'method_title': card_overrides.get('method_title', 'Inversion Highlights'),
            'method_points': fallback_points(bulletize(method_src, 5), analysis_text, 5),
            'result_title': card_overrides.get('result_title', 'Interpretability Results'),
            'result_points': fallback_points(bulletize(eval_src, 5), analysis_text, 5),
            'risk_title': card_overrides.get('risk_title', 'Interpretation Risks'),
            'risk_points': fallback_points(bulletize(find_section(analysis_text, ['limitations', 'semantic realism', 'qualitative']), 3), analysis_text, 3),
            'lens_title': card_overrides.get('lens_title', 'Interpretation Reading Lens'),
            'lens_text': card_overrides.get('lens_text', 'Ask whether the inversion is faithful to model internals or mainly visually plausible. Good images do not automatically imply valid model interpretation.'),
            'metrics': extract_metrics(analysis_text, 6),
        }
    return {
        'summary_title': card_overrides.get('summary_title', 'Core Summary'),
        'summary_text': meta.get('summary', '') or first_sentences(analysis_text, 6),
        'method_title': card_overrides.get('method_title', 'Method Highlights'),
        'method_points': fallback_points(bulletize(find_section(analysis_text, ['method', 'approach', 'model', 'architecture']), 5), analysis_text, 5),
        'result_title': card_overrides.get('result_title', 'Benchmarks & Results'),
        'result_points': fallback_points(bulletize(find_section(analysis_text, ['results', 'experiments', 'evaluation', 'benchmark']), 5), analysis_text, 5),
        'risk_title': card_overrides.get('risk_title', 'Limitations & Risks'),
        'risk_points': fallback_points(bulletize(find_section(analysis_text, ['limitations', 'failure', 'future work']), 3), analysis_text, 3),
        'lens_title': card_overrides.get('lens_title', 'Reading Lens'),
        'lens_text': card_overrides.get('lens_text', 'Start from task definition, then identify the core representation, objective, and evaluation setup before trusting the headline claims.'),
        'metrics': extract_metrics(analysis_text, 6),
    }


def render_compare_html(items, out_path, style_variant='colorful'):
    summaries = []
    for it in items:
        text = it['text']
        summary = first_sentences(text, 2)
        if not summary:
            summary = clean_text(text[:220])
        methods = extract_method_snippets(text, 5)
        datasets = extract_dataset_snippets(text, 4)
        speed = extract_fps_hz(text)
        scale = extract_data_scale(text)
        summaries.append({
            'title': it['title'],
            'summary': summary or 'N/A',
            'methods': methods or ['N/A'],
            'datasets': datasets or ['N/A'],
            'speed': speed,
            'scale': scale,
        })

    common = []
    diff = []
    speeds = [s['speed'] for s in summaries]
    scales = [s['scale'] for s in summaries]
    if len(set(speeds)) == 1:
        common.append(f'Speed metric style aligned: {speeds[0]}')
    else:
        diff.append('Speed/FPS differs: ' + ' vs '.join(speeds))
    if len(set(scales)) == 1:
        common.append(f'Data scale signal aligned: {scales[0]}')
    else:
        diff.append('Data scale differs: ' + ' vs '.join(scales))

    kw = ['latent action', 'relative', 'chunk', 'distill', 'causal', 'autoregressive', 'closed-loop', 'post-train', 'pretrain']
    for k in kw:
        hits = []
        for s in summaries:
            joined = ' '.join(s['methods']).lower()
            hits.append(k in joined)
        if all(hits):
            common.append(f'Method commonality: {k}')
        elif any(hits):
            diff.append(f'Method difference: {k} appears only in subset')

    def li(items_):
        return '\n'.join(f'<li>{html.escape(x)}</li>' for x in items_)

    def table_rows(items_, kind):
        if not items_:
            items_ = ['N/A']
        return '\n'.join(
            f'<tr><td>{i+1}</td><td>{html.escape(kind)}</td><td style="text-align:left">{html.escape(v)}</td></tr>'
            for i, v in enumerate(items_)
        )

    col_html = []
    for s in summaries:
        col_html.append(f"""
        <div class=\"card\">
          <h2>{html.escape(s['title'])}</h2>
          <h3>Core</h3>
          <p class=\"compact\">{html.escape(s['summary'])}</p>
          <h3>Method Signals</h3>
          <ul class=\"compact\">{li(s['methods'])}</ul>
          <h3>Dataset Signals</h3>
          <ul class=\"compact\">{li(s['datasets'])}</ul>
          <h3>Key Data Metrics</h3>
          <table><tr><th>Item</th><th>Value</th></tr>
          <tr><td>Speed/FPS</td><td>{html.escape(s['speed'])}</td></tr>
          <tr><td>Data Scale</td><td>{html.escape(s['scale'])}</td></tr>
          </table>
        </div>
        """)

    if style_variant == 'colorful':
        title_text = 'Comparative Summary (Colorful Minimal)'
        style_css = f"""
@page {{ size:A4; margin:8mm; }}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:linear-gradient(180deg,#eef4ff 0%,#f8f9fb 60%);color:#1a1a2e;font-size:10px;line-height:1.35;padding:10px;max-width:210mm;margin:auto}}
h1{{font-size:15px;text-align:center;color:#0f3460;margin-bottom:4px}}
.sub{{text-align:center;font-size:9px;color:#555;margin-bottom:8px}}
.grid{{display:grid;grid-template-columns:repeat({max(2, min(3, len(summaries)))},1fr);gap:8px}}
.card{{background:#fff;border:1px solid #dbeafe;border-radius:8px;padding:8px 10px;box-shadow:0 2px 8px rgba(15,52,96,.12)}}
.card h2{{font-size:11px;color:#0f3460;border-bottom:2px solid #e94560;padding-bottom:3px;margin-bottom:4px}}
.card h3{{font-size:10px;color:#533483;margin:4px 0 2px}}
.compact{{font-size:9px}}
ul{{padding-left:14px}}
table{{width:100%;border-collapse:collapse;font-size:9px;margin-top:3px}}
th{{background:#0f3460;color:#fff;padding:3px 4px;text-align:center;font-weight:600}}
td{{padding:2px 4px;text-align:center;border-bottom:1px solid #e0e0e0}}
tr:nth-child(even) td{{background:#f4f6fb}}
.section{{margin-top:8px;background:#fff;border:1px solid #dbeafe;border-radius:8px;padding:8px 10px;box-shadow:0 2px 8px rgba(15,52,96,.12)}}
.footer{{text-align:center;font-size:8px;color:#666;margin-top:6px}}
"""
    else:
        title_text = 'Comparative Summary (Minimal)'
        style_css = f"""
@page {{ size:A4; margin:8mm; }}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#f8f9fb;color:#1a1a2e;font-size:10px;line-height:1.35;padding:10px;max-width:210mm;margin:auto}}
h1{{font-size:15px;text-align:center;color:#0f3460;margin-bottom:4px}}
.sub{{text-align:center;font-size:9px;color:#555;margin-bottom:8px}}
.grid{{display:grid;grid-template-columns:repeat({max(2, min(3, len(summaries)))},1fr);gap:8px}}
.card{{background:#fff;border-radius:6px;padding:8px 10px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card h2{{font-size:11px;color:#0f3460;border-bottom:2px solid #e94560;padding-bottom:3px;margin-bottom:4px}}
.card h3{{font-size:10px;color:#533483;margin:4px 0 2px}}
.compact{{font-size:9px}}
ul{{padding-left:14px}}
table{{width:100%;border-collapse:collapse;font-size:9px;margin-top:3px}}
th{{background:#0f3460;color:#fff;padding:3px 4px;text-align:center;font-weight:600}}
td{{padding:2px 4px;text-align:center;border-bottom:1px solid #e0e0e0}}
tr:nth-child(even) td{{background:#f4f6fb}}
.section{{margin-top:8px;background:#fff;border-radius:6px;padding:8px 10px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.footer{{text-align:center;font-size:8px;color:#666;margin-top:6px}}
"""

    html_doc = f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"UTF-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
<title>Paper Compare — One Page</title>
<style>
{style_css}
</style>
</head>
<body>
<h1>{title_text}</h1>
<div class=\"sub\">Method + Data focused compare for {len(summaries)} paper(s)</div>
<div class=\"grid\">
{''.join(col_html)}
</div>
<div class=\"section\">
  <h2>Common Points (Method/Data)</h2>
  <table>
    <tr><th>#</th><th>Type</th><th>Detail</th></tr>
    {table_rows(common if common else ['No strong common axis extracted automatically.'], 'Common')}
  </table>
  <h2 style=\"margin-top:6px\">Differences (Method/Data)</h2>
  <table>
    <tr><th>#</th><th>Type</th><th>Detail</th></tr>
    {table_rows(diff if diff else ['No strong differences extracted automatically.'], 'Difference')}
  </table>
</div>
<div class=\"footer\">Generated by paper-html-onepage --compare</div>
</body>
</html>
"""
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_doc)
def derive_intermediate_paths(out_path):
    base, ext = os.path.splitext(out_path)
    if not ext:
        ext = '.html'
        out_path = out_path + ext
        base = out_path[:-len(ext)]
    html_full_path = base + '_fulltext.html'
    return out_path, html_full_path


def cleanup_file_quietly(path):
    try:
        os.remove(path)
    except OSError:
        pass


def ensure_local_source_pdf(pdf_path, target_pdf_path):
    src_abs = os.path.abspath(pdf_path)
    dest_abs = os.path.abspath(target_pdf_path)
    os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
    if dest_abs == src_abs:
        return src_abs, False

    if os.path.exists(dest_abs):
        size_match = False
        try:
            size_match = os.path.getsize(dest_abs) == os.path.getsize(src_abs)
        except OSError:
            size_match = False
        if size_match:
            return dest_abs, False
        dest_abs = uniquify_path(dest_abs)

    shutil.copy2(src_abs, dest_abs)
    return dest_abs, True


def build_from_url(url, out_path, max_pages, keep_pdf, keep_fulltext_html):
    # Accept arXiv abs/pdf pages or any direct PDF link. Resolve to a real PDF URL.
    arxiv_match = re.search(r'(\d{4}\.\d{4,5})(?:v\d+)?', url)
    arxiv_id = arxiv_match.group(1) if arxiv_match else ''
    pdf_url = url
    if arxiv_id and '/abs/' in url:
        pdf_url = url.replace('/abs/', '/pdf/')
        if not pdf_url.endswith('.pdf'):
            pdf_url += '.pdf'

    # Download to a temp file first so metadata can drive the output filename.
    fd, tmp_pdf = tempfile.mkstemp(prefix='paper_', suffix='.pdf')
    os.close(fd)
    try:
        download_pdf(pdf_url, tmp_pdf)
    except Exception as exc:
        cleanup_file_quietly(tmp_pdf)
        raise RuntimeError(f'Failed to download {pdf_url} via requests and curl: {exc}') from exc

    full_text, pages_read, page_texts = extract_pdf_text(tmp_pdf, max_pages=max_pages)

    # Prefer arXiv metadata; otherwise derive title/abstract from the PDF itself.
    meta = fetch_arxiv_by_id(arxiv_id) if arxiv_id else None
    if not meta:
        meta = extract_pdf_meta(tmp_pdf, page_texts)
    meta.setdefault('pdf_url', pdf_url)
    meta.setdefault('abs_url', f'https://arxiv.org/abs/{arxiv_id}' if arxiv_id else url)

    out_path = choose_output_path(meta, out_path, '')
    out_path, html_full_path = derive_intermediate_paths(out_path)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    semantic_pdf_path = choose_pdf_path_for_output(out_path)

    render_fulltext_html(meta, full_text, pages_read, html_full_path)
    render_onepage_html(meta, full_text, pages_read, out_path)

    kept_pdf = ''
    copied_source = False
    if keep_pdf:
        kept_pdf, copied_source = ensure_local_source_pdf(tmp_pdf, semantic_pdf_path)
    cleanup_file_quietly(tmp_pdf)

    if keep_fulltext_html:
        print(f'[OK] fulltext html: {html_full_path}')
    else:
        cleanup_file_quietly(html_full_path)
    if kept_pdf:
        status = 'copied' if copied_source else 'ready'
        print(f'[OK] source pdf {status}: {kept_pdf}')
    return out_path


def build_from_query(query, out_path, max_pages, pick, keep_pdf, keep_fulltext_html):
    cands = search_arxiv(query, max_results=max(5, pick))
    if not cands:
        raise RuntimeError(f'No arXiv result for query: {query}')
    idx = max(1, pick) - 1
    if idx >= len(cands):
        idx = 0
    meta = cands[idx]
    if not meta.get('pdf_url'):
        raise RuntimeError('Selected paper has no PDF URL.')
    out_path = choose_output_path(meta, out_path, '')
    out_path, html_full_path = derive_intermediate_paths(out_path)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    semantic_pdf_path = choose_pdf_path_for_output(out_path)
    fd, tmp_pdf = tempfile.mkstemp(prefix='paper_', suffix='.pdf')
    os.close(fd)
    download_pdf(meta['pdf_url'], tmp_pdf)
    full_text, pages_read, _ = extract_pdf_text(tmp_pdf, max_pages=max_pages)
    render_fulltext_html(meta, full_text, pages_read, html_full_path)
    render_onepage_html(meta, full_text, pages_read, out_path)
    kept_pdf = ''
    copied_source = False
    if keep_pdf:
        kept_pdf, copied_source = ensure_local_source_pdf(tmp_pdf, semantic_pdf_path)
    if keep_fulltext_html:
        print(f'[OK] fulltext html: {html_full_path}')
    else:
        cleanup_file_quietly(html_full_path)
    if kept_pdf:
        status = 'copied' if copied_source else 'ready'
        print(f'[OK] source pdf {status}: {kept_pdf}')
    cleanup_file_quietly(tmp_pdf)
    return out_path


def build_from_pdf(pdf_path, out_path, max_pages, keep_fulltext_html):
    full_text, pages_read, page_texts = extract_pdf_text(pdf_path, max_pages=max_pages)
    meta = extract_pdf_meta(pdf_path, page_texts)
    out_path = choose_output_path(meta, out_path, pdf_path)
    out_path, html_full_path = derive_intermediate_paths(out_path)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    local_pdf_path, copied_source = ensure_local_source_pdf(pdf_path, choose_pdf_path_for_output(out_path))
    render_fulltext_html(meta, full_text, pages_read, html_full_path)
    render_onepage_html(meta, full_text, pages_read, out_path)
    if copied_source:
        print(f'[OK] source pdf copied: {local_pdf_path}')
    else:
        print(f'[OK] source pdf ready: {local_pdf_path}')
    if keep_fulltext_html:
        print(f'[OK] fulltext html: {html_full_path}')
    else:
        cleanup_file_quietly(html_full_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description='Keyword to one-page paper HTML summary.')
    ap.add_argument('--query', help='search keyword for arXiv')
    ap.add_argument('--pdf', help='local PDF path (skip search)')
    ap.add_argument('--url', help='direct paper URL (arXiv abs/pdf or any PDF link); downloads with requests -> curl fallback')
    ap.add_argument('--reflection', help='local markdown/txt reflection path; preserve content and render as one-page reflection html')
    ap.add_argument('--out', help='output html path; if omitted, auto-name from detected paper keyword/title')
    ap.add_argument('--max-pages', type=int, default=80)
    ap.add_argument('--pick', type=int, default=1)
    ap.add_argument('--keep-pdf', dest='keep_pdf', action='store_true', help='keep the local source pdf next to the output html (default for --url/--query)')
    ap.add_argument('--no-keep-pdf', dest='keep_pdf', action='store_false', help='discard downloaded pdf after rendering; restores the old temp-file behavior')
    ap.add_argument('--keep-fulltext-html', action='store_true', help='keep the intermediate fulltext html; default deletes it after summary generation')
    ap.add_argument('--compare', action='store_true', help='compare 2+ papers/files into one colorful/minimal page')
    ap.add_argument('--items', nargs='*', help='paths for compare mode (pdf/html/txt); if omitted, interactive prompt')
    ap.add_argument('--compare-style', choices=['colorful', 'minimal'], default='colorful', help='compare style; default colorful')
    ap.set_defaults(keep_pdf=True)
    args = ap.parse_args()

    if args.compare:
        if not args.out:
            raise SystemExit('Compare mode requires --out.')
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        items = args.items or []
        if not items:
            raw = input('Enter 2+ file paths separated by | : ').strip()
            items = [x.strip().strip('"') for x in raw.split('|') if x.strip()]
        if len(items) < 2:
            raise SystemExit('Compare mode requires at least 2 file paths.')
        loaded = []
        for p in items:
            if not os.path.exists(p):
                raise SystemExit(f'Not found: {p}')
            loaded.append(load_text_from_item(p, args.max_pages))
        render_compare_html(loaded, args.out, style_variant=args.compare_style)
        print(f'[OK] compare HTML generated: {args.out}')
    elif args.reflection:
        final_out = build_from_reflection(args.reflection, args.out)
    elif args.pdf:
        final_out = build_from_pdf(args.pdf, args.out, args.max_pages, args.keep_fulltext_html)
    elif args.url:
        final_out = build_from_url(args.url, args.out, args.max_pages, args.keep_pdf, args.keep_fulltext_html)
    else:
        if not args.query:
            raise SystemExit('Provide --query, --pdf, --url, --reflection, or use --compare.')
        final_out = build_from_query(args.query, args.out, args.max_pages, args.pick, args.keep_pdf, args.keep_fulltext_html)

    if not args.compare:
        print(f'[OK] HTML generated: {final_out}')


if __name__ == '__main__':
    main()
