# Parse Failure Taxonomy

Derived from running the rule-based parser across 4 SCOTUS transcripts (2015–2023).
Each failure mode is classified by type, severity, frequency, and the correct remediation.

---

## Failure Mode Classification

| ID | Name | Type | Severity | Frequency | Remediation |
|----|------|------|----------|-----------|-------------|
| F01 | Word-index page bleed | **Structural** | Critical | Every transcript | Dynamic detection via word-index line pattern |
| F02 | Section hint cascade | **Structural** | High | Every transcript | Consume hint once per section transition only |
| F03 | Terminal stage direction not split | **Structural** | Medium | ~1 per transcript | TERMINAL_STAGE_RE pattern at flush time |
| F04 | "ON BEHALF OF" TOC variant not caught | **Structural** | Low | ~1 per transcript (rebuttal) | Extend TOC_SECTION_RE to cover this variant |
| F05 | Inline stage direction missed in continuation | **Structural** | Low | Rare | _split_inline_stages on continuation lines |
| F06 | Very short utterances flagged as issues | **False positive** | None | 1–7 per transcript | Remove from QA — these are legitimate |
| F07 | Long utterances flagged as issues | **False positive** | None | 0–8 per transcript | Landmark cases have extended speeches; no cap |
| F08 | Interrupted utterance ("--") split incorrectly | **Structural** | Low | Moderate | Trailing "--" utterances join to speaker context |
| F09 | Start-time stage direction "(10:02 a.m.)" parsed | **Cosmetic** | Low | 1 per transcript | Acceptable; not spoken content but benign |
| F10 | Continuation-only speaker turn (empty rest) | **Structural** | Medium | Occasional | Handled — speaker label on line alone, text follows |
| F11 | Soft-hyphen artifact in text (­­ chars) | **Structural** | Low | Many | Strip U+00AD (soft hyphen) during text cleaning |
| F12 | Case caption lines as false-positive speakers | **Structural** | Low | First 2–3 pages only | CAPTION_SKIP_RE; skipping first 3 pages handles it |

---

## Detailed Descriptions

### F01 — Word-index page bleed *(Critical, Structural)*

**What happens:** The alphabetical word index at the back of every SCOTUS transcript spans
multiple PDF pages (9 pages in Dobbs). A fixed `end_offset` of 1–2 pages misses most of it,
causing word-index text to be appended to the final utterance.

**Evidence:** Dobbs Spike 001 run — seq 321 had 10,393 words (word index merged in).

**Fix implemented:** `_is_word_index_page()` detects pages where 3+ lines match
`word [N] page:line` pattern and stops extraction. Reliable across all 4 transcripts.

**LLM prompt implication:** If using an LLM, the prompt must receive pre-cleaned pages with
the word index already removed. Do not send raw PDF pages to the LLM.

---

### F02 — Section hint cascade *(High, Structural)*

**What happens:** After a section transition (e.g., "REBUTTAL ARGUMENT OF..."), the section
hint propagates to every subsequent utterance instead of only the first.

**Evidence:** Masterpiece Spike 002 iteration 1 — 21 section hints instead of 2.

**Fix implemented:** Separate `pending_section_hint` (set by TOC marker) from
`current_section_hint` (consumed exactly once at flush). The hint is cleared after
application and never cascades.

**LLM prompt implication:** The prompt must explicitly instruct: "section_hint applies only
to the FIRST utterance after the section marker, null for all subsequent utterances."

---

### F03 — Terminal stage direction not split *(Medium, Structural)*

**What happens:** Stage directions that follow a spoken sentence on the same text block
(e.g., "The case is submitted. (Whereupon, at 11:54 a.m., the case was submitted.)")
are treated as part of the speaker's utterance instead of being split out.

**Evidence:** All transcripts end with a "(Whereupon, ...)" form. Dobbs iteration 1 — this
was merged into the Chief Justice's closing remark (10,393 word count).

**Fix implemented:** `TERMINAL_STAGE_RE` detects `text. (stage_direction)` at flush time
and splits into two utterances.

**LLM prompt implication:** The prompt should explicitly cover: "If an utterance ends with
a stage direction like '(Whereupon, ...)', emit the spoken part and the stage direction as
separate utterances."

---

### F04 — "ON BEHALF OF" TOC variant not caught *(Low, Structural)*

**What happens:** In some transcripts, the section announcement takes the form "ON BEHALF OF
THE PETITIONERS" rather than "ORAL ARGUMENT OF..." or "REBUTTAL ARGUMENT OF...". This variant
is not matched by `TOC_SECTION_RE` and gets appended to the preceding speaker's utterance.

**Evidence:** Dobbs seq 319 — "Thank you, General. Rebuttal, General Stewart. ON BEHALF OF
THE PETITIONERS" (the last 4 words are a TOC header, not spoken content).

**Fix needed:** Extend `TOC_SECTION_RE` to match `^ON BEHALF OF\b` as a TOC marker.
Alternatively: strip trailing "ON BEHALF OF [...]" from any utterance at post-processing.

**Frequency:** Appears once per transcript, at the rebuttal boundary. Low severity since it
does not corrupt the utterances themselves — just adds a few words of noise.

---

### F05 — Inline stage direction missed in continuation *(Low, Structural)*

**What happens:** Stage directions embedded mid-sentence in a continuation line (not on the
opening line of a speaker turn) are not always detected for splitting.

**Evidence:** Rare in the 4-transcript corpus. Only caught when `_split_inline_stages` runs
on continuation lines — the current implementation handles it but edge cases exist when the
inline stage direction is the first token on a continuation line.

**Frequency:** ~0–2 per transcript. The `INLINE_STAGE_RE` catches most cases.

---

### F06 — Very short utterances flagged as QA issues *(False Positive)*

**What happens:** Utterances under 5 characters (e.g., "I --", "Yes.", "Right.", "No.") are
flagged as suspicious. They are entirely legitimate — these are interruptions, brief
acknowledgments, and crosstalk that appear constantly in oral arguments.

**Evidence:** 1–7 per transcript. All manually verified as genuine content.

**Action:** Remove the `very_short_utterance` issue detector from QA. These are not errors.
The implementation must preserve them — they are real utterance data.

---

### F07 — Long utterances flagged as QA issues *(False Positive)*

**What happens:** Utterances over ~300 words are flagged as "suspiciously long" by the QA
checker. In landmark, contentious cases (especially Dobbs), Justices routinely deliver
extended speeches 300–500 words long.

**Evidence:** Dobbs had 7 utterances over 300 words; all confirmed legitimate.

**Action:** Remove the `suspiciously_long_utterance` issue detector or raise threshold
significantly (1000+ words). Only word counts over 5,000 indicate parser failure (word index
bleed), and those are now prevented by F01 fix.

---

### F08 — Interrupted utterance splitting *(Low, Structural)*

**What happens:** When a Justice interrupts mid-sentence with "--", the transcript records:
```
JUSTICE X: I think that the --
JUSTICE Y: -- but doesn't that mean --
JUSTICE X: -- right, that's my point.
```
Each of these is correctly treated as a separate utterance. However, the trailing "--" on the
first speaker's utterance and the leading "--" on the third can make the text look garbled
when displayed.

**Evidence:** Many instances across all transcripts. E.g., Obergefell has "The problem ­­",
"I'm sorry.", "Could you ­­" etc.

**Action:** This is correct parser behavior. The UI should handle "--" gracefully in display.
No parser fix needed, but the implementation team should be aware of this pattern.

---

### F09 — Start-time stage direction "(10:02 a.m.)" *(Cosmetic)*

**What happens:** Every transcript begins with a stage direction recording the start time
(e.g., "(10:02 a.m.)", "(10:00 a.m.)"). This is correctly parsed as `is_stage_direction=true`
with sequence=1.

**Action:** Acceptable behavior. The UI should render it as a stage direction (already handled
by the schema). Not an error.

---

### F10 — Speaker label on its own line *(Medium, Structural)*

**What happens:** Occasionally a speaker label appears on one line with no accompanying text,
and all speech follows on the next line:
```
JUSTICE ALITO:
Well, I think the question is...
```
This is handled by the state machine (speaker is set, next line becomes text), but only if
`current_text_parts` is empty and the continuation check runs correctly.

**Evidence:** Observed occasionally in all transcripts. Handled correctly by current parser.

**LLM prompt implication:** The prompt should note: "A speaker label may appear on its own
line — the following continuation lines are that speaker's utterance."

---

### F11 — Soft hyphen artifact (­­) in text *(Low, Structural)*

**What happens:** SCOTUS transcripts use soft hyphens (U+00AD) to represent dashes in
interrupted speech. pdfplumber renders these as `­­` (visible in JSON as `­­`).
This appears in many utterances.

**Evidence:** Multiple utterances across all transcripts contain `­­`.

**Fix needed:** In text post-processing, replace `­` with `--` (standard double dash
for interrupted speech). Apply during the text cleaning step before writing to the database.

---

### F12 — Case caption lines as false-positive speakers *(Low, Structural)*

**What happens:** Case caption pages (pages 1–3 which we skip) occasionally have lines like
`ET AL.:` that match `SPEAKER_RE`. If the page-skip logic fails (e.g., TOC is on page 4),
these would be parsed as speaker turns.

**Evidence:** Spike 001 detected `ET AL.` as a speaker label before page-skipping was applied.
After skipping the first 3 pages, this is prevented.

**Mitigation:** `CAPTION_SKIP_RE` catches the most common false positives. Page-skip logic
is the primary defense.

---

## Summary: What the LLM Needs to Do

The rule-based parser handles ~95% of the work correctly. The remaining 5% where an LLM
adds real value:

| Scenario | Why rules fail | LLM advantage |
|----------|---------------|---------------|
| F04 — "ON BEHALF OF" TOC variant | TOC_SECTION_RE misses it | LLM understands semantic intent |
| F05 — Complex inline stage directions | Regex can't always tell a stage direction from a citation | LLM reads context |
| F08 — Interrupted speech display | Rules can parse correctly but can't "clean up" sensibly | LLM can infer if "--" should be preserved or elided |
| F11 — Soft hyphen normalization | Simple string replacement (NOT an LLM job) | Not needed |
| Novel TOC formats | Unknown future transcript variants | LLM generalizes better |

**Conclusion:** The rule-based parser is the right foundation for Phase 1. An LLM parse step
should be positioned as a **corrective pass** over the rule-based output, not a replacement.
This keeps costs low (only run the LLM on pages with ambiguities) and makes failures easier
to diagnose (the rule-based pass creates a structured log to diff against).
