"""Build docs/SettleUp_Complete_Technical_Guide.pdf from the Markdown source.

Documentation tooling only (not needed to run SettleUp):
    pip install markdown pygments playwright pypdfium2
Mermaid diagrams are rendered by mermaid.js inside Microsoft Edge (Playwright channel
"msedge"). Set MERMAID_JS to a local mermaid.min.js, otherwise the jsDelivr CDN is used.

Usage (from the repository root):
    python docs/tools/build_pdf.py

How it works
  1. Markdown -> HTML (python-markdown + Pygments), mermaid blocks -> <pre class="mermaid">.
  2. A title page and a table of contents are generated from the headings.
  3. Pass 1 prints a PDF; pypdfium2 (PDFium) finds on which page each heading landed (each heading
     carries a tiny invisible marker).
  4. Pass 2 prints the final PDF with those page numbers in the table of contents.
"""
import html
import os
import re
import sys
import tempfile
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter
from playwright.sync_api import sync_playwright
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "SettleUp_Complete_Technical_Guide.md"
OUTPUT = ROOT / "docs" / "SettleUp_Complete_Technical_Guide.pdf"
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.min.js"

CSS = """
@page { size: A4; margin: 20mm 17mm 20mm 17mm; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 10.2pt;
       line-height: 1.5; color: #1e293b; }
h1, h2, h3 { color: #134e4a; line-height: 1.25; break-after: avoid; }
h1 { font-size: 21pt; margin: 0 0 14pt; padding-bottom: 6pt; border-bottom: 2.5pt solid #0f766e;
     break-before: page; }
h2 { font-size: 13.5pt; margin: 18pt 0 6pt; padding-bottom: 2pt; border-bottom: 0.6pt solid #cbd5e1; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; }
p { margin: 5pt 0; }
a { color: #0f766e; text-decoration: none; }
ul, ol { margin: 4pt 0 6pt; padding-left: 18pt; }
li { margin: 1.5pt 0; }
code { font-family: Consolas, "Cascadia Mono", monospace; font-size: 8.8pt; background: #f1f5f9;
       padding: 0.5pt 3pt; border-radius: 3pt; color: #0f172a; }
pre { margin: 6pt 0 8pt; }
.codehilite { background: #f8fafc !important; border: 0.6pt solid #e2e8f0; border-left: 3pt solid #14b8a6;
              border-radius: 4pt; padding: 6pt 9pt; break-inside: avoid; }
.codehilite pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-size: 8.4pt; line-height: 1.42; }
.codehilite code, pre code { background: none; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 9pt; break-inside: auto; }
th { background: #f0fdfa; color: #134e4a; text-align: left; font-weight: 600; }
th, td { border: 0.6pt solid #cbd5e1; padding: 3.5pt 6pt; vertical-align: top; }
tr { break-inside: avoid; }
blockquote { margin: 8pt 0; padding: 6pt 12pt; background: #f0fdfa; border-left: 3pt solid #0f766e; }
pre.mermaid { text-align: center; background: #fff; border: 0.6pt solid #e2e8f0; border-radius: 4pt;
              padding: 8pt; break-inside: avoid; font-family: inherit; }
pre.mermaid svg { max-width: 100%; height: auto; max-height: 225mm; }
.marker { font-size: 1px; color: #ffffff; letter-spacing: 0; }
.title-page { height: 250mm; display: flex; flex-direction: column; justify-content: center; }
.title-page .band { width: 64pt; height: 6pt; background: #0f766e; margin-bottom: 18pt; }
.title-page h1.t { break-before: auto; border: 0; font-size: 34pt; margin: 0; color: #0f172a; }
.title-page .sub { font-size: 15pt; color: #0f766e; margin-top: 8pt; }
.title-page .meta { margin-top: 36pt; font-size: 10.5pt; color: #475569; line-height: 1.8; }
.title-page .note { margin-top: 60pt; font-size: 9pt; color: #64748b; max-width: 120mm; }
.toc { break-before: page; }
.toc h1 { break-before: auto; }
.toc ol { list-style: none; padding: 0; margin: 0; }
.toc li { display: flex; align-items: baseline; margin: 0; }
.toc li.l1 { font-weight: 600; margin-top: 5pt; font-size: 10pt; }
.toc li.l2 { padding-left: 16pt; font-size: 9pt; color: #334155; }
.toc li .dots { flex: 1; border-bottom: 0.8pt dotted #94a3b8; margin: 0 4pt; transform: translateY(-3pt); }
.toc li .pg { min-width: 18pt; text-align: right; font-variant-numeric: tabular-nums; }
strong { color: #0f172a; }
"""

FOOTER = """
<div style="width:100%; font-size:7.5pt; color:#64748b; padding:0 17mm; display:flex;
            justify-content:space-between; font-family:'Segoe UI',Arial,sans-serif;">
  <span>SettleUp — Complete Technical Guide</span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>"""


def split_front_matter(text: str) -> tuple[dict, str]:
    meta = {}
    if text.startswith("---"):
        _, block, text = text.split("---", 2)
        for line in block.strip().splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
    return meta, text


def render_markdown(text: str) -> tuple[str, list[dict]]:
    # Turn ```mermaid blocks into placeholders that markdown will not touch.
    diagrams: list[str] = []

    def stash(match):
        diagrams.append(match.group(1))
        return f"\n\nMERMAIDPLACEHOLDER{len(diagrams) - 1}\n\n"

    text = re.sub(r"```mermaid\n(.*?)```", stash, text, flags=re.S)
    md = markdown.Markdown(
        extensions=["extra", "codehilite", "toc", "sane_lists"],
        extension_configs={"codehilite": {"guess_lang": False, "css_class": "codehilite"},
                           "toc": {"toc_depth": "1-2"}},
    )
    body = md.convert(text)
    for index, diagram in enumerate(diagrams):
        body = body.replace(f"<p>MERMAIDPLACEHOLDER{index}</p>",
                            f'<pre class="mermaid">{html.escape(diagram)}</pre>')
    return body, md.toc_tokens


def flatten(tokens) -> list[dict]:
    items = []
    for token in tokens:
        items.append({"id": token["id"], "name": html.unescape(token["name"]), "level": token["level"]})
        items.extend(flatten(token["children"]))
    return items


def add_markers(body: str, headings: list[dict]) -> str:
    """Append an invisible, extractable marker to every h1/h2 so pypdf can locate it."""
    for number, heading in enumerate(headings):
        pattern = re.compile(rf'(<h{heading["level"]} id="{re.escape(heading["id"])}">)(.*?)(</h{heading["level"]}>)', re.S)
        body = pattern.sub(rf'\1\2<span class="marker">qqH{number:03d}qq</span>\3', body, count=1)
    return body


def build_html(meta: dict, body: str, headings: list[dict], pages: dict[int, int], mermaid_src: str) -> str:
    toc_items = []
    for number, heading in enumerate(headings):
        css = "l1" if heading["level"] == 1 else "l2"
        page = pages.get(number, "")
        toc_items.append(
            f'<li class="{css}"><a href="#{heading["id"]}">{html.escape(heading["name"])}</a>'
            f'<span class="dots"></span><span class="pg">{page}</span></li>'
        )
    title_page = f"""
    <section class="title-page">
      <div class="band"></div>
      <h1 class="t">SettleUp</h1>
      <div class="sub">{html.escape(meta.get('subtitle', ''))}</div>
      <div class="sub" style="color:#334155;font-size:13pt">Complete Technical Guide —
        Backend, PostgreSQL, API and Interview Preparation</div>
      <div class="meta">
        Final-year BTech Computer Science project (three-member team)<br>
        React · FastAPI · SQLAlchemy · PostgreSQL<br>
        Version {html.escape(meta.get('version', ''))} · {html.escape(meta.get('date', ''))}
      </div>
      <div class="note">This guide documents the application exactly as implemented in the
        repository. Code listings are taken from the source files; test results are from
        recorded test runs. Features that are not implemented are marked as future scope.</div>
    </section>"""
    toc = f'<section class="toc"><h1>Table of Contents</h1><ol>{"".join(toc_items)}</ol></section>'
    return f"""<!doctype html><html><head><meta charset="utf-8">
    <title>SettleUp — Complete Technical Guide</title>
    <style>{CSS}{HtmlFormatter(style="friendly").get_style_defs(".codehilite")}</style>
    <script src="{mermaid_src}"></script></head>
    <body>{title_page}{toc}<main>{body}</main>
    <script>
      mermaid.initialize({{ startOnLoad: false, theme: "neutral", securityLevel: "strict",
                            er: {{ useMaxWidth: true }}, flowchart: {{ useMaxWidth: true }},
                            sequence: {{ useMaxWidth: true }} }});
      mermaid.run({{ querySelector: "pre.mermaid" }})
        .then(() => {{ window.__mermaidDone = true; }})
        .catch((e) => {{ window.__mermaidError = String(e); window.__mermaidDone = true; }});
    </script></body></html>"""


def print_pdf(browser, html_text: str, out_path: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as handle:
        handle.write(html_text)
        temp_html = Path(handle.name)
    try:
        page = browser.new_page()
        page.goto(temp_html.as_uri(), wait_until="load")
        page.wait_for_function("window.__mermaidDone === true", timeout=120_000)
        error = page.evaluate("window.__mermaidError || null")
        if error:
            raise RuntimeError(f"Mermaid failed: {error}")
        page.pdf(path=str(out_path), format="A4", print_background=True,
                 display_header_footer=True, header_template="<div></div>", footer_template=FOOTER,
                 margin={"top": "18mm", "bottom": "18mm", "left": "17mm", "right": "17mm"},
                 outline=True, tagged=True)
        page.close()
    finally:
        temp_html.unlink(missing_ok=True)


def find_pages(pdf_path: Path, count: int) -> dict[int, int]:
    pages: dict[int, int] = {}
    document = pdfium.PdfDocument(str(pdf_path))
    for index in range(len(document)):
        text = document[index].get_textpage().get_text_range()
        for match in re.findall(r"qqH(\d{3})qq", text):
            pages.setdefault(int(match), index + 1)
    document.close()
    missing = [i for i in range(count) if i not in pages]
    if missing:
        print(f"warning: {len(missing)} headings not located: {missing[:10]}")
    return pages


def main() -> int:
    meta, text = split_front_matter(SOURCE.read_text(encoding="utf-8"))
    body, tokens = render_markdown(text)
    headings = flatten(tokens)
    body = add_markers(body, headings)
    mermaid_src = Path(os.environ["MERMAID_JS"]).resolve().as_uri() if os.environ.get("MERMAID_JS") else MERMAID_CDN

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        draft = OUTPUT.with_suffix(".draft.pdf")
        print_pdf(browser, build_html(meta, body, headings, {}, mermaid_src), draft)
        pages = find_pages(draft, len(headings))
        print_pdf(browser, build_html(meta, body, headings, pages, mermaid_src), OUTPUT)
        draft.unlink(missing_ok=True)
        browser.close()

    final_pages = find_pages(OUTPUT, len(headings))
    shifted = sum(1 for k, v in pages.items() if final_pages.get(k) != v)
    document = pdfium.PdfDocument(str(OUTPUT))
    page_count = len(document)
    document.close()
    print(f"wrote {OUTPUT} ({page_count} pages, {len(headings)} headings, "
          f"{shifted} TOC entries moved between passes)")
    return 0 if shifted == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
