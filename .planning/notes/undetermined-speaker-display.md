# Undetermined Speakers — Measurements & Display Decision

**Status:** operator-approved display direction, 2026-09-23. Trust/publishability
decision still OPEN. Not a plan.

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

## Still OPEN

1. **The publishability decision has NOT been made.** `api/services/trust.py:108` floors an
   argument to UNCERTAIN for any utterance with `person_id IS NULL`, commented
   *"Unresolved speaker floors to UNCERTAIN"*. It cannot distinguish "the corpus says nobody
   knows" from "we have not resolved this yet" because both arrive as NULL. Publish is
   hard-blocked on UNCERTAIN, so **59.3% of the corpus currently needs a per-argument operator
   override to publish, and there is no bulk publish path.** Approving a display treatment
   implies these arguments are meant to be seen, but the trust decision is separate and still
   unmade.
   - Whatever distinguishes the two cases must be **stored, not inferred** — same lesson as the
     justice join key. Deriving it from `raw_speaker_label == "<INAUDIBLE>"` would be the
     fragile version.
2. **"Known speaker, unknown words" has never been mocked.** 15,099 whole-turn `(Inaudible)`
   rows where we know who spoke and not what they said — the inverse problem. Currently
   classified as a stage direction (see 3).
3. **`(Inaudible)` is classified as a stage direction.** A stage direction describes an event
   in the room; this describes a failure of the transcript. Rendering them identically tells
   the reader "an inaudible occurred". Detector: `pipeline/corpus/stage_directions.py`.
4. **Two design-system deviations in Treatment D** need confirming or overruling: the label
   uses **italic** (Phase 51 locked two weights; italic is a new axis) and **70% opacity** as
   the subtlety lever, because the type scale has nothing below caption/14.
5. **Unverified in a browser:** `ChatBubble.svelte:49` falls back to `raw_speaker_label` when
   there is no `speaker_name`, which is believed to render a literal `<INAUDIBLE>` on the page
   today. Treatment D replaces this, but the current behaviour was never observed on screen.

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
