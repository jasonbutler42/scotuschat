# Transcript Rendering — Scenario Inventory & Decision Tree

**Status:** consolidated record of operator decisions made 2026-09-23. Companion to
`undetermined-speaker-display.md`, which carries the measurements and the reasoning.
Not a plan.

Two orthogonal axes produce every case below:

- **Speaker** — do we know who spoke? (`speakers.json` `type` field)
- **Content** — do we know what they said? (the transcript's own marker vocabulary)

They were conflated for most of this investigation. Keeping them separate is what makes the
tree tractable.

## Decision tree

```mermaid
flowchart TD
    A["ConvoKit turn<br/>text + speaker id"] --> B["Split text on newline<br/>into segments"]
    B --> C{"Segment is a whole-turn marker<br/>in the curated vocabulary?"}

    C -->|"No — ordinary speech"| S1["Speech segment"]
    C -->|"Room event<br/>Laughter · Recess · Luncheon Recess<br/>Cross Talk · Voice Overlap"| R1["Stage-direction row"]
    C -->|"Transcription failure<br/>Inaudible"| F1["Lost-words row<br/>keeps its speaker"]

    R1 --> R2["person_id = NULL<br/>raw_speaker_label = NULL<br/>is_stage_direction = true"]
    R2 --> R3["DISPLAY · StageDirection.svelte<br/>centred, italic, belongs to neither side<br/>text NORMALISED to canonical label"]
    R3 --> R4["TRUST · skipped from the floor<br/>no speaker to attribute, no risk"]

    S1 --> D{"speakers.json type == 'U'?<br/>the source's own sentinel"}
    F1 --> D

    D -->|"No — a real speaker"| E["Resolve or create Person<br/>oyez_speaker_id, then full_name"]
    D -->|"Yes — source says it does not know"| U["No Person, no participant<br/>person_id = NULL<br/>sentinel fact STORED on the utterance"]

    E --> E1{"Content known?"}
    E1 -->|"Yes"| E2["DISPLAY · attributed bubble<br/>name + role, avatar in its own side rail"]
    E1 -->|"No — Inaudible"| E3["DISPLAY · attributed bubble<br/>name + role, body = NORMALISED marker<br/>'this person spoke, we do not know what they said'"]
    E2 --> E4["TRUST · derive_tier corpus/direct = TRUSTED"]
    E3 --> E4

    U --> U1{"Content known?"}
    U1 -->|"Yes"| U2["DISPLAY · Treatment D<br/>narrower bubble, CENTRED<br/>rail reserved both sides, neither filled<br/>label 'undetermined speaker'"]
    U1 -->|"No — Inaudible"| U3["DISPLAY · Treatment D<br/>body = NORMALISED marker<br/>double unknown"]
    U2 --> U4["TRUST · PROVISIONAL<br/>not UNCERTAIN — source-final, not pending"]
    U3 --> U4

    E4 --> Z["Argument tier = floor across all rows"]
    R4 --> Z
    U4 --> Z

    Z --> Y{"More than 50% of the argument's<br/>non-stage-direction turns undetermined?"}
    Y -->|"No"| Y1["Publishable normally<br/>PROVISIONAL clears the gate"]
    Y -->|"Yes — 6 arguments corpus-wide"| Y2["NOT publishable without<br/>operator intervention"]
```

## Scenario inventory

| # | Scenario | Speaker | Content | Display | Tier contribution | Volume |
|---|---|---|---|---|---|---|
| 1 | Ordinary attributed speech | known | known | attributed bubble, own side rail | TRUSTED | ~1.59M turns |
| 2 | Undetermined speaker, words fine | **unknown** | known | **Treatment D** — centred, both rails empty, "undetermined speaker" | **PROVISIONAL** | ~69,000 turns |
| 3 | Consecutive undetermined turns | unknown ×2+ | known | same as 2 — **accepted as ambiguous, won't fix** | PROVISIONAL | 1.1% of 88,102 |
| 4 | Attributed, whole turn inaudible | known | **unknown** | attributed bubble, body = normalised marker | TRUSTED | **~13,221** |
| 5 | Undetermined **and** inaudible | **unknown** | **unknown** | Treatment D, body = normalised marker | PROVISIONAL | ~5,860 |
| 6 | Inline `(Inaudible)` mid-sentence | known | partial | verbatim inside the bubble — untouched | TRUSTED | ~30,800 |
| 7 | Laughter | n/a | n/a | stage direction, normalised | skipped | 1,020 |
| 8 | Voice Overlap | n/a | n/a | **stage direction** (operator, 2026-09-23), normalised | skipped | ~719 |
| 9 | Recess / Luncheon Recess / Cross Talk | n/a | n/a | stage direction, normalised | skipped | rare |
| 10 | Argument >50% undetermined | — | — | — | not publishable without intervention | **6 arguments** |

Row 6 is the one place the operator's *"whatever is in the utterance, is in the utterance"*
rule applies literally and nothing is normalised — the marker is inside a sentence a person
actually spoke, so touching it would be editing speech.

## Normalisation — what "normalised" means above

`pipeline/corpus/stage_directions.py::detect_stage_direction` **already returns a canonical
label** (`"Inaudible"`, `"Laughter"`, `"Voice Overlap"`, ...) with fuzzy matching at 0.8, which
is why real corpus typos like `(voive overlap)` and `(inaudioble)` are already caught. The
importer uses that return value **as a boolean only** and stores the raw segment text;
`StageDirection.svelte` then renders `{utterance.text}` verbatim.

So the canonical label exists today and is discarded one line later. Normalising is a matter of
keeping it, not building it.

The source is genuinely inconsistent — **31 distinct verbatim forms**, led by `(Inaudible)`
14,995, `[Inaudible]` 3,911, `(Voice Overlap)` 672, `(Inaudible).` 95, `[inaudible]` 39, plus
`( Voice Overlap)` and `(Inaudible.)`. Rendered raw, round and square brackets alternate
between adjacent turns.

**Operator decision 2026-09-23: normalise, "or it will look like a bug."**

> **ASSUMPTION FLAGGED FOR CONFIRMATION.** The operator said *"stage directions should be
> normalised."* Taken literally that covers only rows 7-9 (~1,700 turns), because rows 4 and 5
> are no longer stage directions under the same day's decision. But the "looks like a bug"
> problem is overwhelmingly in rows 4 and 5 (~19,081 turns), so this document applies
> normalisation to **every marker in the curated vocabulary, wherever it is displayed** —
> stage-direction rows and lost-words bubble bodies alike. Row 6, the inline case, is
> deliberately excluded. If the narrower reading was intended, rows 4 and 5 revert to raw text.

## Rules that must not regress

- **Laughter inside a speaker's turn still splits.** Warren's `"It's on now.\n(Laughter)"`
  becomes his speech plus a separate room-event row. Easy to break by reaching for a simpler
  "stop splitting parentheticals" fix.
- **`(a)`, `(b)`, `(ph)` are never stage directions** — legal list markers and the
  phonetic-spelling convention. `_REJECTED_LITERALS` guards this deliberately.
- **The importer never creates a Person for a `type: "U"` speaker.** An earlier version did,
  producing a bogus `<INAUDIBLE>` advocate.
- **Trust never reaches a public surface.** PROVISIONAL is operator-facing only; reader-facing
  honesty is Treatment D's explanation card.

## Still open

1. The **denominator** for the >50% rule — this note's percentages count all utterances; the
   implementation would naturally count non-stage-direction utterances. Not the same number,
   and the boundary is tight (50.2% then 49.8%).
2. The **normalisation scope assumption** flagged above.
3. **Unverified in a browser:** `ChatBubble.svelte:49` falls back to `raw_speaker_label`, which
   is believed to render a literal `<INAUDIBLE>` today. Treatment D replaces it, but nobody has
   seen the current behaviour on screen.
