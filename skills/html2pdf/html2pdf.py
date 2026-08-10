from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote


BROWSER_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]


PRINT_CSS = """
<style id="codex-html2pdf-print-style">
@page { size: 1280px 720px; margin: 0; }
@media print {
  html, body {
    width: 1280px;
    height: auto;
    background: #fff !important;
    overflow: visible !important;
  }
  body {
    display: block !important;
    min-height: auto !important;
  }
  .presentation {
    width: 1280px !important;
    height: auto !important;
    overflow: visible !important;
    box-shadow: none !important;
    border-radius: 0 !important;
  }
  .slide {
    position: relative !important;
    top: auto !important;
    left: auto !important;
    width: 1280px !important;
    height: 720px !important;
    opacity: 1 !important;
    visibility: visible !important;
    display: flex !important;
    page-break-after: always;
    break-after: page;
    overflow: hidden !important;
  }
  .slide:last-of-type {
    page-break-after: auto;
    break-after: auto;
  }
  .nav-bar, .nav, .navigation, .controls {
    display: none !important;
  }
}
</style>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert HTML to PDF, with special support for slide-style presentation HTML."
    )
    parser.add_argument("input_html", help="Path to input HTML file")
    parser.add_argument("output_pdf", nargs="?", help="Optional output PDF path")
    parser.add_argument(
        "--browser",
        help="Explicit browser executable path. Defaults to auto-detect Chrome/Edge.",
    )
    parser.add_argument(
        "--no-presentation-fix",
        action="store_true",
        help="Disable auto-injected print CSS for slide-style HTML.",
    )
    return parser.parse_args()


def detect_browser(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if path.exists():
            return path
        raise FileNotFoundError(f"Browser not found: {path}")

    for candidate in BROWSER_CANDIDATES:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("No supported browser found. Install Chrome or Edge, or pass --browser.")


def looks_like_presentation(html: str) -> bool:
    signals = [
        '.slide{',
        '.slide {',
        'class="slide',
        "class='slide",
        '.presentation{',
        '.presentation {',
        'position:absolute',
        'position: absolute',
    ]
    matches = sum(1 for signal in signals if signal in html)
    return matches >= 2


def inject_print_css(html: str) -> str:
    if "codex-html2pdf-print-style" in html:
        return html
    if "</head>" in html:
        return html.replace("</head>", PRINT_CSS + "\n</head>", 1)
    return PRINT_CSS + "\n" + html


def file_url(path: Path) -> str:
    resolved = path.resolve()
    return "file:///" + quote(str(resolved).replace("\\", "/"), safe="/:._-")


def build_printable_html(input_path: Path, disable_fix: bool) -> Path:
    html = input_path.read_text(encoding="utf-8")
    if disable_fix or not looks_like_presentation(html):
        return input_path

    temp_dir = Path(tempfile.mkdtemp(prefix="html2pdf_"))
    temp_html = temp_dir / input_path.name

    temp_html.write_text(inject_print_css(html), encoding="utf-8")

    for child in input_path.parent.iterdir():
        target = temp_dir / child.name
        if child.is_dir():
            if not target.exists():
                shutil.copytree(child, target)
        elif child.name != input_path.name:
            shutil.copy2(child, target)

    return temp_html


def print_to_pdf(browser: Path, html_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # Render to an ASCII-named temp file first, then move into place. Chrome's
    # new headless mode refuses to write directly to non-ASCII output paths on
    # Windows ("access denied", 0x5); rendering to a temp path sidesteps that.
    tmp_dir = Path(tempfile.mkdtemp(prefix="html2pdf_out_"))
    tmp_pdf = tmp_dir / "output.pdf"
    try:
        cmd = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",  # suppress the date/title header and URL/page footer
            f"--print-to-pdf={tmp_pdf}",
            file_url(html_path),
        ]
        subprocess.run(cmd, check=True)
        shutil.move(str(tmp_pdf), str(pdf_path))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def count_pages(pdf_path: Path) -> int | None:
    try:
        from PyPDF2 import PdfReader  # type: ignore

        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return None


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_html)
    if not input_path.exists():
        print(f"Input HTML not found: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output_pdf) if args.output_pdf else input_path.with_suffix(".pdf")

    try:
        browser = detect_browser(args.browser)
        printable_html = build_printable_html(input_path, args.no_presentation_fix)
        print_to_pdf(browser, printable_html, output_path)
    except Exception as exc:
        print(f"html2pdf failed: {exc}", file=sys.stderr)
        return 1

    pages = count_pages(output_path)
    print(f"PDF generated: {output_path.resolve()}")
    print(f"Browser used: {browser}")
    if printable_html != input_path:
        print("Presentation print CSS: injected into temporary copy")
    else:
        print("Presentation print CSS: not injected")
    if pages is not None:
        print(f"Pages: {pages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
