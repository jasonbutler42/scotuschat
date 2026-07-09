"""
Spike 001: PDF Text Extraction
Extract text from 4 SCOTUS transcript PDFs and analyze structure.
Produces: data/NNN-casename.json (raw pages) + viewer.html
"""

import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pdfplumber

PDF_DIR = Path(__file__).parent / "pdfs"
OUT_DIR = Path(__file__).parent / "data"
OUT_DIR.mkdir(exist_ok=True)

PDFS = [
    ("obergefell-14-556-q1.pdf", "Obergefell v. Hodges (Q1, 2015)"),
    ("masterpiece-16-111.pdf", "Masterpiece Cakeshop (2017)"),
    ("dobbs-19-1392.pdf", "Dobbs v. Jackson (2021)"),
    ("rahimi-22-915.pdf", "United States v. Rahimi (2023)"),
]

# Matches legal transcript line numbers: 1-25 at column 0
# e.g. " 1" or "  1" or "25"
LINE_NUM_RE = re.compile(r"^\s{0,3}(\d{1,2})\s")

# Speaker label: ALL CAPS name followed by colon
# e.g. "JUSTICE SOTOMAYOR:", "MR. SMITH:", "GENERAL:"
SPEAKER_RE = re.compile(
    r"^((?:CHIEF\s+)?(?:JUSTICE|MR\.|MS\.|MRS\.|DR\.|GENERAL|SOLICITOR)\s+[A-Z][A-Z\s\.']+?|[A-Z][A-Z\s\.]{2,}?):\s*(.*)$"
)

# Stage directions: text wrapped in parens on its own line
STAGE_DIR_RE = re.compile(r"^\s*\(([^)]+)\)\s*$")

# Page header/footer patterns in SCOTUS transcripts
HEADER_RE = re.compile(
    r"^(?:ALDERSON REPORTING|HERITAGE REPORTING|OFFICIAL\s+|SUPREME\s+COURT|\d+\s+ORAL\s+ARGUMENT|Alderson|Heritage|\s*\d+\s*$)",
    re.IGNORECASE,
)


def strip_line_numbers(text: str) -> str:
    """Remove the 1-25 line numbers from legal transcript pages."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        m = LINE_NUM_RE.match(line)
        if m:
            # Remove the line number prefix
            rest = line[m.end() - 1:].strip() if m.end() > 1 else line.strip()
            cleaned.append(rest)
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


def classify_line(line: str) -> dict:
    stripped = line.strip()
    if not stripped:
        return {"type": "blank", "text": ""}

    if STAGE_DIR_RE.match(stripped):
        return {"type": "stage_direction", "text": stripped}

    m = SPEAKER_RE.match(stripped)
    if m:
        return {
            "type": "speaker_turn",
            "speaker": m.group(1).strip(),
            "text": m.group(2).strip(),
        }

    if HEADER_RE.match(stripped):
        return {"type": "header_footer", "text": stripped}

    # Pure page number line (just digits)
    if re.match(r"^\d+$", stripped):
        return {"type": "page_number", "text": stripped}

    return {"type": "continuation", "text": stripped}


def extract_pdf(pdf_path: Path, label: str) -> dict:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"  Pages: {len(pdf.pages)}")
        print(f"{'='*60}")

        for i, page in enumerate(pdf.pages):
            raw_text = page.extract_text(layout=False) or ""
            cleaned = strip_line_numbers(raw_text)

            lines = [classify_line(ln) for ln in cleaned.split("\n")]

            # Count line types on this page
            type_counts = {}
            for ln in lines:
                type_counts[ln["type"]] = type_counts.get(ln["type"], 0) + 1

            pages.append(
                {
                    "page_num": i + 1,
                    "raw_text": raw_text,
                    "cleaned_text": cleaned,
                    "lines": lines,
                    "line_type_counts": type_counts,
                }
            )

            if i < 3 or i == len(pdf.pages) - 1:
                print(f"\n--- Page {i+1} (sample) ---")
                preview = raw_text[:500].replace("\n", "[NL]\n")
                print(preview)
                print(f"  Line types: {type_counts}")

    # Aggregate stats across document
    all_type_counts = {}
    for page in pages:
        for t, c in page["line_type_counts"].items():
            all_type_counts[t] = all_type_counts.get(t, 0) + c

    # Find unique speaker labels
    speaker_labels = set()
    for page in pages:
        for ln in page["lines"]:
            if ln["type"] == "speaker_turn":
                speaker_labels.add(ln["speaker"])

    print(f"\n  Document totals: {all_type_counts}")
    print(f"  Unique speaker labels ({len(speaker_labels)}): {sorted(speaker_labels)}")

    return {
        "label": label,
        "path": str(pdf_path),
        "page_count": len(pages),
        "pages": pages,
        "document_stats": all_type_counts,
        "speaker_labels": sorted(speaker_labels),
    }


def build_html(results: list[dict]) -> str:
    tabs = ""
    panels = ""
    for idx, r in enumerate(results):
        active = "active" if idx == 0 else ""
        short = r["label"].split("(")[0].strip()
        tabs += f'<button class="tab {active}" onclick="showTab({idx})">{short}</button>\n'

        # Sample first 10 pages of analysis
        sample_pages = r["pages"][:10]
        page_html = ""
        for page in sample_pages:
            page_html += f'<div class="page">\n<h3>Page {page["page_num"]}</h3>\n'
            page_html += f'<div class="raw-col"><h4>Raw pdfplumber output</h4><pre>{_esc(page["raw_text"][:2000])}</pre></div>\n'
            page_html += '<div class="classified-col"><h4>Classified lines</h4>\n'
            for ln in page["lines"][:40]:
                t = ln["type"]
                css = {
                    "speaker_turn": "speaker",
                    "stage_direction": "stage",
                    "header_footer": "header",
                    "page_number": "pagenum",
                    "continuation": "cont",
                    "blank": "blank",
                }.get(t, "")
                label = ln.get("speaker", "") or t
                text = ln.get("text", "")
                page_html += f'<div class="line {css}"><span class="tag">{_esc(label)}</span> {_esc(text[:120])}</div>\n'
            page_html += "</div></div>\n"

        # Speaker labels summary
        speakers_str = ", ".join(r["speaker_labels"]) or "(none detected)"
        stats_str = json.dumps(r["document_stats"], indent=2)

        panels += f"""<div class="panel" id="panel-{idx}" style="display:{'block' if idx==0 else 'none'}">
<h2>{_esc(r["label"])}</h2>
<div class="summary">
  <strong>Pages:</strong> {r["page_count"]} &nbsp;|&nbsp;
  <strong>Speaker labels:</strong> {_esc(speakers_str)}<br>
  <strong>Line type counts:</strong> <code>{_esc(stats_str)}</code>
</div>
{page_html}
</div>\n"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Spike 001 — PDF Text Extraction</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; background: #0f1117; color: #e2e8f0; }}
h1 {{ padding: 1rem 1.5rem; margin: 0; background: #1e293b; border-bottom: 2px solid #334155; font-size: 1.1rem; color: #94a3b8; }}
.tabs {{ display: flex; gap: 0.5rem; padding: 0.75rem 1.5rem; background: #1e293b; }}
.tab {{ padding: 0.4rem 1rem; border: 1px solid #334155; border-radius: 4px; background: #0f1117; color: #94a3b8; cursor: pointer; font-size: 0.85rem; }}
.tab.active {{ background: #2563eb; color: #fff; border-color: #2563eb; }}
.panel {{ padding: 1.5rem; }}
.summary {{ background: #1e293b; border-radius: 6px; padding: 1rem; margin-bottom: 1.5rem; font-size: 0.85rem; line-height: 1.8; }}
.page {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 2rem; border-bottom: 1px solid #1e293b; padding-bottom: 2rem; }}
.page h3 {{ grid-column: 1/-1; margin: 0 0 0.5rem; color: #64748b; font-size: 0.9rem; }}
h4 {{ margin: 0 0 0.5rem; font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }}
pre {{ background: #1e293b; padding: 0.75rem; border-radius: 4px; font-size: 0.72rem; white-space: pre-wrap; overflow-y: auto; max-height: 400px; }}
.line {{ padding: 0.15rem 0; font-size: 0.78rem; display: flex; gap: 0.5rem; align-items: baseline; }}
.tag {{ font-size: 0.68rem; padding: 0.1rem 0.4rem; border-radius: 3px; min-width: 90px; text-align: center; }}
.speaker .tag {{ background: #1d4ed8; color: #bfdbfe; }}
.stage .tag {{ background: #92400e; color: #fde68a; }}
.header .tag {{ background: #374151; color: #9ca3af; }}
.pagenum .tag {{ background: #374151; color: #6b7280; }}
.cont .tag {{ background: #14532d; color: #86efac; }}
.blank .tag {{ background: #1e293b; color: #475569; }}
</style>
</head>
<body>
<h1>Spike 001 — PDF Text Extraction (pdfplumber) | 4 SCOTUS Transcripts</h1>
<div class="tabs">{tabs}</div>
{panels}
<script>
function showTab(n) {{
  document.querySelectorAll('.panel').forEach((p,i) => p.style.display = i===n?'block':'none');
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', i===n));
}}
</script>
</body>
</html>"""


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main():
    results = []
    for filename, label in PDFS:
        path = PDF_DIR / filename
        if not path.exists():
            print(f"MISSING: {path}")
            continue
        data = extract_pdf(path, label)
        out_path = OUT_DIR / f"{filename.replace('.pdf', '.json')}"
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        results.append(data)

    html = build_html(results)
    viewer_path = Path(__file__).parent / "viewer.html"
    viewer_path.write_text(html, encoding="utf-8")
    print(f"\n✓ Viewer: {viewer_path}")
    print(f"✓ JSON data: {OUT_DIR}")


if __name__ == "__main__":
    main()
