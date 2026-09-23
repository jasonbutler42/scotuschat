# Undetermined Speakers — Measurements & Display Decision

**Status:** operator-approved display direction AND trust/publishability decision,
2026-09-23. Not a plan.

## The decision

**Treatment D**, approved by the operator 2026-09-23. Mockup:
`Figma › SCOTUS Chat Design System › Public › unattributed-speaker-exploration › unattributed-D`
(file `KICu66PtMLHk4fmxJYPggx`, node `33:2`).

- A **narrower bubble (540px vs the standard 582px)** sits **centred** with a 40px rail
  reserved on **both** sides and **neither filled**. The layout declines to place the turn
  on a side at all.
- Label reads **"undetermined speaker"**, not "unknown". Operator's reasoning, carried into
  the card copy: the speaker was one of the people in the room; the record just does not say
  which. "Unknown" is too definitive.
- On **hover**, a dashed question-mark avatar appears in **both** rails. Showing it on both
  sides is the point — the interface is declining to guess a side, not decorating one.
- Clicking either avatar opens an **explanation card** in the same shape as the speaker bio
  card, so the affordance reads as "this is who spoke" in both cases.

Treatments A (explicit "Unknown speaker" name row), B (no label, empty rail) and C (side
inferred, "A Justice") are in the same section and were **not** chosen. C was rejected
deliberately: it reads best and is the one that asserts something the source does not support.

## Vocabulary — three different things share the word "inaudible"

This caused real confusion during the investigation. Keep them distinct:

| | What it actually is | Count |
|---|---|---|
| `speaker == "<INAUDIBLE>"` | **speaker unidentified; words fully transcribed** | 88,102 |
| whole-turn `(Inaudible)` | **words lost; speaker often known** | 15,099 |
| inline `(Inaudible)` mid-sentence | words lost inside an otherwise fine turn | ~35,000 |

Only the FIRST is what Treatment D addresses. The others are transcript content and are
rendered verbatim (operator decision, 2026-09-23).

`<INAUDIBLE>` is a badly-named sentinel in the **speaker** dimension, typed `"U"` in
`speakers.json` alongside `<UNKNOWN>`. It never meant the audio was bad. Evidence: the turns
carry sub-second audio timestamps, `speaker_type`/`side` are specifically null, the content is
coherent Q&A, and a separate inline mechanism already exists for genuinely lost words.

## Measurements (full 900MB pass — do not re-run to rediscover these)

**Volume**
- 1,700,789 utterances total; 88,102 unattributed (5.18%)
- `<UNKNOWN>` is **1 utterance** — the court crier adjourning. Ignore it.
- 4,638 of 7,817 conversations (59.3%) contain at least one unattributed turn

**Anatomy of an unattributed turn**
| | |
|---|---|
| follows an **advocate** turn | **89.8%** |
| follows a justice | 9.1% |
| phrased as a question | 41.1% |
| short (<=20 chars) | 22.9% |
| interrupted (leading/trailing `--`) | 14.0% |
| contains an inline lost-words marker | 9.4% |
| **consecutive** with another unattributed turn | **1.1%** |

The 89.8%/1.1% pair is what makes the operator's "let context speak" instinct sound: in ~99%
of cases there is an attributed turn adjacent, so the reader can place the speaker without the
product asserting anything.

**Per-conversation share** — median 3.2%; only **6** conversations in the whole corpus are
majority-unattributed.

| share | conversations |
|---|---|
| <1% | 1,135 |
| 1-5% | 1,702 |
| 5-10% | 653 |
| 10-25% | 540 |
| 25-50% | 602 |
| >=50% | 6 |

**By decade** — does NOT track audio age. 1950s 4.68%, 1960s 3.56%, **1970s 7.83%, 1980s
8.71%**, 1990s 3.80%, 2000s 4.38%, **2010s 0.63%**. The 1970s-80s peak suggests diarization
effort varied by era, not that the audio degraded. Modern arguments are essentially clean.

## S5 — consecutive undetermined turns: WON'T FIX (for now)

1.1% of unattributed turns. Two centred bubbles in a row cannot tell a reader whether one
person spoke twice or two people spoke once each — the only case where context genuinely
fails. **Operator decision 2026-09-23: accepted, nothing to be done about it at this time.**
The mockup shows it honestly rather than hiding it.

## Trust & publishability — DECIDED 2026-09-23

**The concept already exists in the codebase, on the wrong axis.** `api/services/trust.py`'s
*participant* branch lifts the UNCERTAIN floor when `review_state == OPERATOR_CONFIRMED`,
set by Phase 49's `confirm_unattributable` action and commented as *"a deliberate human
judgment that no further speaker resolution is possible or needed for this row."* The
*utterance* branch has no equivalent — no `review_state` column, and it short-circuits to
UNCERTAIN before any such rule could apply. That asymmetry is the whole defect.

**Decisions:**

1. **A source-sentinel speaker maps to PROVISIONAL, not UNCERTAIN.** No human action is
   required, because no human judgment is involved: `speakers.json` types these speakers
   `"U"` — the source itself states, machine-readably and finally, that it does not know.
   PROVISIONAL rather than VERIFIED is deliberate: we have not verified anything, we have
   accepted a limit. PROVISIONAL already exists and already clears the publish gate (only
   UNCERTAIN hard-blocks).
2. **The sentinel fact must be STORED on the utterance at import**, not re-derived later from
   `raw_speaker_label == "<INAUDIBLE>"`. Same lesson as the justice join key: a string-shaped
   inference is the fragile version.
3. **An argument more than 50% undetermined is not publishable without intervention.**
   Six conversations corpus-wide: 16897 (68.0%), 13223 (66.7%), 19600 (58.2%), 16725 (54.7%),
   16352 (52.5%), 16762 (50.2%). The next two sit at 49.8% and 49.6%, so the boundary is
   genuinely discriminating rather than arbitrary.
   - **Definitional detail for planning:** the percentages above use *all utterances in the
     conversation* as the denominator. The natural implementation denominator is
     *non-stage-direction utterances*, which `_load_constituents` already iterates. Those are
     not the same number. Pin the denominator explicitly before implementing; do not assume
     this note's figures survive the change.

With 1-3 in place, essentially the whole corpus becomes publishable, because for corpus
imports the only thing producing UNCERTAIN is this NULL person_id.

PROVISIONAL is operator-facing only — trust never reaches a public surface (apolitical
constraint). Reader-facing honesty is Treatment D's explanation card. Two different jobs,
both covered.

## Whole-turn `(Inaudible)` with a known speaker — DECIDED 2026-09-23

**Operator: "in a case where the entire utterance is inaudible but we know the speaker, we
should NOT treat those as stage direction. It should still be treated as *this person spoke
but we don't know what they said*."**

Today `pipeline/corpus/stage_directions.py` classifies a whole-turn `(Inaudible)` as a stage
direction, and the importer writes stage directions with `raw_speaker_label=None,
person_id=None` — so when a named Justice's words are lost, the attribution the source gave us
is discarded and the turn renders as an anonymous room event. Roughly **11,034 turns** have a
known speaker thrown away this way (15,816 parenthetical-only turns minus the 4,782 whose
speaker is also a sentinel).

**The fix is to split the curated vocabulary into two classes:**

| Class | Markers | Treatment |
|---|---|---|
| **Room event** | Laughter, Laughs, Laugh, Recess, Luncheon Recess, Cross Talk | stage direction, unattributed — unchanged, correct today |
| **Transcription failure** | Inaudible | NOT a stage direction; keep the speaker, render the text verbatim |

- **Voice Overlap (705 whole-turn occurrences) is unclassified and needs an operator call.**
  It is both a room event (people talked over each other) and a transcription failure (the
  words were lost). It could go either way.
- A turn with a sentinel speaker AND `(Inaudible)` text (4,782) is the double-unknown: Treatment
  D handles the speaker, verbatim text handles the content.
- Laughter inside a speaker's turn (e.g. Warren's `"It's on now.\n(Laughter)"`) still splits
  correctly into speech + room event. That behaviour is right and must not regress.
- **No trust consequence:** these turns gain a real `person_id`, so they derive
  `corpus/direct` -> TRUSTED rather than being skipped.
- **Display question, not yet eyeballed:** a bubble from a named Justice whose entire body
  reads `(Inaudible)`. Faithful, but nobody has looked at it on screen.

## Design-system additions — APPROVED 2026-09-23

Italic and 70% opacity for the "undetermined speaker" label are approved. They must land as
design-system additions in `app/src/app.css` and `.planning/codebase/DESIGN-SYSTEM.md`, not as
inline one-offs — Phase 51's whole point was that nothing in `app/src` carries a raw value.
Italic is a new type axis (Phase 51 locked two weights); opacity is the subtlety lever because
the scale has nothing below caption/14.

## Still OPEN

1. **Unverified in a browser:** `ChatBubble.svelte:49` falls back to `raw_speaker_label` when
   there is no `speaker_name`, which is believed to render a literal `<INAUDIBLE>` on the page
   today. Treatment D replaces this, but the current behaviour was never observed on screen.
2. **Voice Overlap classification** (see above).
3. **The publish-gate denominator** (see above).

## What is already correct and should not be re-litigated

- The importer **refuses to create a Person** for a `type: "U"` speaker
  (`_is_unattributed_speaker_type`), with a comment noting an earlier version did create a
  bogus `<INAUDIBLE>` advocate. Utterance text is preserved with `person_id = NULL` — no
  content loss.
- Stage directions are already excluded from the trust floor (`trust.py:106`).
- `stage_directions.py` uses a curated vocabulary (Inaudible, Laughter, Voice Overlap, Recess,
  Luncheon Recess, Cross Talk) fuzzy-matched at 0.8 — catching real corpus typos like
  `(voive overlap)` — and explicitly rejects `(a)`, `(b)`, `(ph)` so legal list markers and the
  phonetic-spelling convention are not misclassified. Laughter (1,020 occurrences) is almost
  always inline inside a speaker's turn and is correctly split into its own row.

## Related decisions recorded the same day

- **Source authority (operator):** the PDF and Oyez carry **equal** authoritativeness for this
  project. Where one provides more information, use it. Note this is *not* what
  `api/domain/authority.py` implements — the ladder ranks `corpus` **above** `pdf_pipeline`.
  Same outcome for speaker attribution, divergent the first time a PDF is richer. Revisit at
  Phase 999.11.
- **Line breaks:** Oyez `\n` are **sentence boundaries**, not paragraphs (98.8% end in
  sentence-final punctuation; median segment 97 chars, longer than a transcript line). The
  corpus carries **no** paragraph structure. PDF indentation remains the only source for it.
