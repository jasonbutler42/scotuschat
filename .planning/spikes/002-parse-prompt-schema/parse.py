"""
Spike 002: Rule-based SCOTUS transcript parser.
Parses all 4 transcripts from Spike 001, produces ParsedUtterance JSON + HTML viewer.
Usage: python parse.py
"""

import io
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import pdfplumber

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SPIKE_001_DIR = Path(__file__).parent.parent / "001-pdf-text-extraction" / "pdfs"
OUT_DIR = Path(__file__).parent / "results"
OUT_DIR.mkdir(exist_ok=True)

PDF_MAP = [
    ("obergefell",   "obergefell-14-556-q1.pdf",   "Obergefell v. Hodges (Q1, 2015)"),
    ("masterpiece",  "masterpiece-16-111.pdf",      "Masterpiece Cakeshop (2017)"),
    ("dobbs",        "dobbs-19-1392.pdf",            "Dobbs v. Jackson (2021)"),
    ("rahimi",       "rahimi-22-915.pdf",            "United States v. Rahimi (2023)"),
]

# ─── Regex patterns ───────────────────────────────────────────────────────────

# Legal transcript line numbers: "1 " … "25 " at column 0
LINE_NUM_RE = re.compile(r"^\s{0,3}(\d{1,2})\s")

# Header/footer lines to skip entirely
HEADER_RE = re.compile(
    r"^(?:Official|ALDERSON|Heritage|HERITAGE|Alderson|www\.|http|\(202\)|\d{3,4}\s+L\s+Street)",
    re.IGNORECASE,
)

# Pure page-number lines (just digits, nothing else)
PAGE_NUM_RE = re.compile(r"^\d+$")

# Table-of-contents / section-marker lines — not utterances, but signal section transitions
TOC_SECTION_RE = re.compile(
    r"^(?:ORAL\s+ARGUMENT\s+OF|REBUTTAL\s+ARGUMENT\s+(?:OF)?|REBUTTAL\s+ARGUMENT\s*:?)"
    r"(?:\s+.*)?$",
    re.IGNORECASE,
)

# Speaker label: ALL-CAPS prefix followed by colon.
# Handles: JUSTICE X, CHIEF JUSTICE X, MR. X, MS. X, GENERAL X, and bare
# ALL-CAPS names (e.g. "QUESTION:" used in some older transcripts).
SPEAKER_RE = re.compile(
    r"^("
    r"CHIEF\s+JUSTICE(?:\s+[A-Z][A-Z\s'.\-]+?)?"
    r"|JUSTICE\s+[A-Z][A-Z\s'.\-]+"
    r"|MR\.\s+[A-Z][A-Z\s'.\-]+"
    r"|MS\.\s+[A-Z][A-Z\s'.\-]+"
    r"|MRS\.\s+[A-Z][A-Z\s'.\-]+"
    r"|GENERAL\s+[A-Z][A-Z\s'.\-]+"
    r"|QUESTION"
    r")"
    r":\s*(.*)",
    re.DOTALL,
)

# Standalone stage direction: entire line is "(text)" or ends with a closing paren
# Also matches trailing stage directions like "The case is submitted. (Whereupon, ...)"
STAGE_DIR_RE = re.compile(r"^\(([^)]+)\)\.?\s*$")

# Stage direction that terminates a sentence: "...text. (Whereupon, ...)"
# Captured so we can split the sentence from the direction.
TERMINAL_STAGE_RE = re.compile(r"^(.*?)\s*(\([^)]{4,}\)\.?)\s*$", re.DOTALL)

# Word-index page detector: a line of the form "word [N] page:line page:line ..."
WORD_INDEX_RE = re.compile(r"^\w[\w\s,'.\-]{0,30}\s+\[\d+\]\s+\d+:\d+")

# Inline stage direction within a line: "(text)" surrounded by other content
INLINE_STAGE_RE = re.compile(r"\(([^)]{2,60})\)")

# Section hint mapping from TOC marker text → canonical value
SECTION_HINT_MAP = [
    (re.compile(r"\bREBUTTAL\b",    re.IGNORECASE), "rebuttal"),
    (re.compile(r"\bAMICUS\b",      re.IGNORECASE), "amicus"),
    (re.compile(r"\bRESPONDENT\b",  re.IGNORECASE), "respondent"),
    (re.compile(r"\bPETITIONER\b",  re.IGNORECASE), "petitioner"),
    (re.compile(r"\bUNITED STATES\b",re.IGNORECASE),"amicus"),
]

# Lines that look like case captions (false-positive speaker labels)
CAPTION_SKIP_RE = re.compile(r"^(?:ET AL\.|APPEARANCES|PETITIONERS?|RESPONDENTS?)$")


# ─── Data model ──────────────────────────────────────────────────────────────

@dataclass
class ParsedUtterance:
    sequence: int
    raw_speaker_label: Optional[str]
    text: str
    is_stage_direction: bool
    section_hint: Optional[str]


# ─── PDF extraction ───────────────────────────────────────────────────────────

def strip_line_number(line: str) -> str:
    m = LINE_NUM_RE.match(line)
    return line[m.end() - 1:].strip() if m else line.strip()


def _is_word_index_page(raw_text: str) -> bool:
    """
    Returns True if this PDF page looks like the alphabetical word index
    at the back of SCOTUS transcripts (entries look like "word [N] page:line ...").
    """
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    hits = sum(1 for l in lines if WORD_INDEX_RE.match(l))
    return hits >= 3  # 3+ index-style lines → this is a word-index page


def extract_pages(pdf_path: Path) -> list[str]:
    """
    Return cleaned text for each argument page (skips cover/TOC/word-index).
    Word-index pages are detected dynamically — they span multiple pages in
    some transcripts, so a fixed end_offset is unreliable.
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for i in range(3, total):          # skip first 3: cover, caption, TOC
            raw = pdf.pages[i].extract_text(layout=False) or ""
            if _is_word_index_page(raw):   # stop at first word-index page
                break
            lines = []
            for raw_line in raw.split("\n"):
                line = strip_line_number(raw_line)
                if HEADER_RE.match(line):
                    continue
                if PAGE_NUM_RE.match(line):
                    continue
                lines.append(line)
            pages.append("\n".join(lines))
    return pages


# ─── Parser state machine ─────────────────────────────────────────────────────

def _resolve_section_hint(toc_text: str) -> Optional[str]:
    for pattern, hint in SECTION_HINT_MAP:
        if pattern.search(toc_text):
            return hint
    return None


def _split_inline_stages(text: str) -> list[tuple[str, bool]]:
    """
    Split a text string on inline stage directions.
    Returns list of (segment_text, is_stage_direction).
    E.g. "So I think -- (Laughter.) -- the point is"
      → [("So I think --", False), ("(Laughter.)", True), ("-- the point is", False)]
    Only splits on patterns that look like genuine stage directions, not legal citations.
    """
    segments = []
    last = 0
    for m in INLINE_STAGE_RE.finditer(text):
        # Heuristic: genuine stage directions are short, title-case or all-caps, not page refs
        content = m.group(1)
        if re.search(r"\d{1,3}:\d{1,2}", content):   # "12:5" — page:line ref, skip
            continue
        before = text[last:m.start()].strip()
        if before:
            segments.append((before, False))
        segments.append((m.group(0), True))
        last = m.end()
    tail = text[last:].strip()
    if tail:
        segments.append((tail, False))
    return segments if len(segments) > 1 else [(text, False)]


def parse_pages(pages: list[str]) -> list[ParsedUtterance]:
    utterances: list[ParsedUtterance] = []
    seq = 0

    # pending_section_hint: set when a TOC marker is seen; consumed by the NEXT speaker flush.
    pending_section_hint: Optional[str] = None
    # current_section_hint: hint that belongs to the utterance currently being built.
    # Cleared after flush so it does NOT cascade to subsequent utterances.
    current_section_hint: Optional[str] = None

    current_speaker: Optional[str] = None
    current_text_parts: list[str] = []

    def flush():
        nonlocal current_speaker, current_text_parts, seq, current_section_hint
        if not current_text_parts and current_speaker is None:
            return
        raw_text = " ".join(p for p in current_text_parts if p)
        if not raw_text.strip():
            current_speaker = None
            current_text_parts = []
            current_section_hint = None
            return

        # Check for a terminal stage direction embedded at the end of the text
        # e.g. "The case is submitted. (Whereupon, at 11:54 a.m., the case was submitted.)"
        tm = TERMINAL_STAGE_RE.match(raw_text.strip())
        if tm and tm.group(1).strip() and STAGE_DIR_RE.match(tm.group(2)):
            # Emit the spoken part first
            seq += 1
            utterances.append(ParsedUtterance(
                sequence=seq,
                raw_speaker_label=current_speaker,
                text=tm.group(1).strip(),
                is_stage_direction=False,
                section_hint=current_section_hint,
            ))
            current_section_hint = None
            # Then emit the stage direction
            seq += 1
            utterances.append(ParsedUtterance(
                sequence=seq,
                raw_speaker_label=None,
                text=tm.group(2).strip(),
                is_stage_direction=True,
                section_hint=None,
            ))
        else:
            seq += 1
            utterances.append(ParsedUtterance(
                sequence=seq,
                raw_speaker_label=current_speaker,
                text=raw_text.strip(),
                is_stage_direction=False,
                section_hint=current_section_hint,
            ))
            current_section_hint = None

        current_speaker = None
        current_text_parts = []

    def emit_stage(text: str):
        nonlocal seq
        seq += 1
        utterances.append(ParsedUtterance(
            sequence=seq,
            raw_speaker_label=None,
            text=text,
            is_stage_direction=True,
            section_hint=None,
        ))

    for page_text in pages:
        for line in page_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # ── Table-of-contents / section markers ──────────────────────────
            if TOC_SECTION_RE.match(line):
                pending_section_hint = _resolve_section_hint(line)
                continue

            # ── Standalone stage direction ────────────────────────────────────
            if STAGE_DIR_RE.match(line):
                flush()
                emit_stage(line)
                continue

            # ── Speaker turn ──────────────────────────────────────────────────
            m = SPEAKER_RE.match(line)
            if m:
                label = m.group(1).strip().rstrip(":")
                if CAPTION_SKIP_RE.match(label):
                    continue
                rest = m.group(2).strip()

                # Flush previous speaker (their hint is already stored in current_section_hint)
                flush()

                # Consume the pending hint for THIS new speaker only
                current_section_hint = pending_section_hint
                pending_section_hint = None

                # Check if rest has inline stage directions
                if rest and INLINE_STAGE_RE.search(rest):
                    segments = _split_inline_stages(rest)
                    first = True
                    for seg_text, is_stage in segments:
                        if not seg_text.strip():
                            continue
                        if is_stage:
                            emit_stage(seg_text)
                        else:
                            seq += 1
                            utterances.append(ParsedUtterance(
                                sequence=seq,
                                raw_speaker_label=label,
                                text=seg_text.strip(),
                                is_stage_direction=False,
                                section_hint=current_section_hint if first else None,
                            ))
                            first = False
                    current_section_hint = None
                    current_speaker = label
                    current_text_parts = []
                elif rest:
                    current_speaker = label
                    current_text_parts = [rest]
                    # current_section_hint already set above; will be used at flush()
                else:
                    current_speaker = label
                    current_text_parts = []
                continue

            # ── Continuation line ─────────────────────────────────────────────
            if current_speaker is not None:
                if INLINE_STAGE_RE.search(line):
                    segments = _split_inline_stages(line)
                    if len(segments) > 1:
                        if current_text_parts:
                            current_text_parts.append(segments[0][0])
                        flush()
                        for seg_text, is_stage in segments[1:]:
                            if not seg_text.strip():
                                continue
                            if is_stage:
                                emit_stage(seg_text)
                            else:
                                current_speaker = (
                                    utterances[-1].raw_speaker_label
                                    if utterances else current_speaker
                                )
                                current_text_parts = [seg_text]
                        continue
                current_text_parts.append(line)

    flush()
    return utterances


# ─── QA stats ────────────────────────────────────────────────────────────────

def compute_qa(utterances: list[ParsedUtterance]) -> dict:
    speakers = sorted({u.raw_speaker_label for u in utterances if u.raw_speaker_label})
    stage_dirs = [u for u in utterances if u.is_stage_direction]
    section_hints = [u for u in utterances if u.section_hint]

    # Detect potential issues
    issues = []

    # Very short utterances (< 5 chars) that aren't stage directions
    short = [u for u in utterances if not u.is_stage_direction and len(u.text) < 5]
    if short:
        issues.append({
            "type": "very_short_utterance",
            "count": len(short),
            "examples": [{"seq": u.sequence, "speaker": u.raw_speaker_label, "text": u.text}
                         for u in short[:5]],
        })

    # Utterances with suspiciously many lines (possible missed speaker turn)
    long_texts = [u for u in utterances if u.text.count(" ") > 300]
    if long_texts:
        issues.append({
            "type": "suspiciously_long_utterance",
            "count": len(long_texts),
            "examples": [{"seq": u.sequence, "speaker": u.raw_speaker_label,
                          "word_count": u.text.count(" ")} for u in long_texts[:3]],
        })

    # Unknown speaker labels (not Justice/advocate pattern)
    unexpected_speakers = [
        s for s in speakers
        if not any(s.startswith(p) for p in
                   ["JUSTICE", "CHIEF JUSTICE", "MR.", "MS.", "GENERAL", "QUESTION"])
    ]
    if unexpected_speakers:
        issues.append({
            "type": "unexpected_speaker_label",
            "labels": unexpected_speakers,
        })

    return {
        "total_utterances": len(utterances),
        "speaker_labels": speakers,
        "stage_direction_count": len(stage_dirs),
        "stage_directions": [{"seq": u.sequence, "text": u.text} for u in stage_dirs],
        "section_hint_count": len(section_hints),
        "section_hints": [{"seq": u.sequence, "hint": u.section_hint, "text": u.text[:80]}
                          for u in section_hints],
        "issues": issues,
    }


# ─── HTML viewer ─────────────────────────────────────────────────────────────

def build_html(all_results: list[dict]) -> str:
    tabs = ""
    panels = ""
    for idx, r in enumerate(all_results):
        active_cls = "active" if idx == 0 else ""
        short = r["label"].split("(")[0].strip()
        tabs += f'<button class="tab {active_cls}" onclick="showTab({idx})">{_esc(short)}</button>\n'

        qa = r["qa"]
        issues_html = ""
        for issue in qa["issues"]:
            examples_str = ""
            if "examples" in issue:
                for ex in issue["examples"]:
                    examples_str += f'<div class="ex">#{ex.get("seq","?")} {_esc(str(ex))}</div>'
            issues_html += f'<div class="issue"><strong>{_esc(issue["type"])}</strong> (×{issue.get("count",len(issue.get("labels",[])))}) {examples_str}</div>'

        speakers_html = "".join(
            f'<span class="badge">{_esc(s)}</span>' for s in qa["speaker_labels"]
        )

        utterances_html = ""
        for u in r["utterances"]:
            css = "stage" if u["is_stage_direction"] else "speech"
            speaker = u["raw_speaker_label"] or "(stage direction)"
            hint_html = f'<span class="hint">{_esc(u["section_hint"])}</span>' if u.get("section_hint") else ""
            utterances_html += f"""<div class="utt {css}">
  <div class="uh"><span class="seq">#{u["sequence"]}</span>
  <span class="sp">{_esc(speaker)}</span>{hint_html}</div>
  <div class="ut">{_esc(u["text"][:500])}</div>
</div>"""

        panels += f"""<div class="panel" id="p{idx}" style="display:{'block' if idx==0 else 'none'}">
<h2>{_esc(r["label"])}</h2>
<div class="summary">
  <strong>Utterances:</strong> {qa["total_utterances"]} &nbsp;|
  <strong>Stage dirs:</strong> {qa["stage_direction_count"]} &nbsp;|
  <strong>Section hints:</strong> {qa["section_hint_count"]}
  {"&nbsp;| <span class='warn'>⚠ " + str(len(qa['issues'])) + " issue(s)</span>" if qa["issues"] else ""}
  <br>{speakers_html}
  {"<div class='issues-box'>" + issues_html + "</div>" if issues_html else ""}
</div>
<div class="utterances">{utterances_html}</div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Spike 002 — Rule-Based Parse Results</title>
<style>
*{{box-sizing:border-box}}body{{font-family:system-ui,sans-serif;margin:0;background:#0f1117;color:#e2e8f0}}
h1{{padding:.8rem 1.5rem;margin:0;background:#1e293b;border-bottom:2px solid #334155;font-size:1rem;color:#94a3b8}}
.tabs{{display:flex;gap:.4rem;padding:.6rem 1.5rem;background:#1e293b;flex-wrap:wrap}}
.tab{{padding:.35rem .9rem;border:1px solid #334155;border-radius:4px;background:#0f1117;color:#94a3b8;cursor:pointer;font-size:.82rem}}
.tab.active{{background:#2563eb;color:#fff;border-color:#2563eb}}
.panel{{padding:1.5rem;max-width:860px}}
h2{{margin:0 0 1rem;font-size:1rem;color:#e2e8f0}}
.summary{{background:#1e293b;border-radius:6px;padding:.9rem;margin-bottom:1.2rem;font-size:.82rem;line-height:2}}
.badge{{display:inline-block;background:#1d4ed8;color:#bfdbfe;border-radius:3px;padding:.08rem .4rem;font-size:.7rem;margin:.1rem}}
.hint{{background:#7c3aed;color:#ede9fe;border-radius:3px;padding:.08rem .35rem;font-size:.7rem;margin-left:.4rem}}
.warn{{color:#f59e0b}}
.issues-box{{margin-top:.5rem;padding:.5rem;background:#1c1208;border-radius:4px;border-left:3px solid #f59e0b}}
.issue{{font-size:.78rem;color:#fcd34d;margin:.2rem 0}}.ex{{font-size:.72rem;color:#94a3b8;margin-left:1rem}}
.utt{{padding:.5rem .7rem;border-left:3px solid #334155;margin-bottom:.35rem;border-radius:0 4px 4px 0}}
.utt.speech{{border-color:#2563eb;background:#0c1929}}
.utt.stage{{border-color:#d97706;background:#1c1208}}
.uh{{display:flex;align-items:center;gap:.4rem;margin-bottom:.15rem}}
.seq{{font-size:.66rem;color:#475569;min-width:2rem}}
.sp{{font-size:.76rem;font-weight:600;color:#93c5fd}}.utt.stage .sp{{color:#fcd34d}}
.ut{{font-size:.8rem;line-height:1.5;color:#cbd5e1}}
</style></head><body>
<h1>Spike 002 — Rule-Based Parser | {sum(r["qa"]["total_utterances"] for r in all_results)} utterances across {len(all_results)} transcripts</h1>
<div class="tabs">{tabs}</div>
{panels}
<script>
function showTab(n){{
  document.querySelectorAll('.panel').forEach((p,i)=>p.style.display=i===n?'block':'none');
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',i===n));
}}
</script></body></html>"""


def _esc(s) -> str:
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    all_results = []
    for key, filename, label in PDF_MAP:
        pdf_path = SPIKE_001_DIR / filename
        if not pdf_path.exists():
            print(f"MISSING: {pdf_path}")
            continue

        print(f"\n{'='*60}\n  {label}\n{'='*60}")
        pages = extract_pages(pdf_path)
        print(f"  Extracted {len(pages)} argument pages")

        utterances = parse_pages(pages)
        qa = compute_qa(utterances)

        print(f"  Utterances:     {qa['total_utterances']}")
        print(f"  Stage dirs:     {qa['stage_direction_count']}")
        print(f"  Section hints:  {qa['section_hint_count']}")
        print(f"  Speakers:       {qa['speaker_labels']}")
        if qa["issues"]:
            print(f"  Issues ({len(qa['issues'])}):")
            for issue in qa["issues"]:
                print(f"    - {issue['type']}: {issue.get('count', issue.get('labels'))}")

        result = {
            "key": key,
            "label": label,
            "utterances": [asdict(u) for u in utterances],
            "qa": qa,
        }
        out_path = OUT_DIR / f"{key}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Saved: {out_path}")
        all_results.append(result)

    html = build_html(all_results)
    viewer = Path(__file__).parent / "viewer.html"
    viewer.write_text(html, encoding="utf-8")
    print(f"\n✓ Viewer: {viewer}")
    print(f"✓ JSON:   {OUT_DIR}")


if __name__ == "__main__":
    main()
