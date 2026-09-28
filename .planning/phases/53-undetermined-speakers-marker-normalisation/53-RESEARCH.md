# Phase 53: Undetermined Speakers & Marker Normalisation - Research

**Researched:** 2026-09-28
**Domain:** Corpus-import speaker/marker classification, trust-tier derivation, SvelteKit chat-transcript rendering
**Confidence:** HIGH (every code claim below is from a same-session `Read` of the cited file; the two design docs and CONTEXT.md/UI-SPEC.md are the operator's own locked decisions, not researched claims)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Carried forward — already approved, do not re-open**

- **D-01:** Treatment D as mocked in Figma `KICu66PtMLHk4fmxJYPggx` node `33:2`: a 540px
  bubble (vs the standard 582px) centred between two 40px rails, **neither filled** at rest,
  labelled "undetermined speaker". Treatments A/B/C are rejected — C deliberately, because it
  asserts a side. Do not re-explore.
- **D-02:** The "undetermined speaker" label is italic at 70% opacity, landed as
  **design-system additions** in `app/src/app.css` and `.planning/codebase/DESIGN-SYSTEM.md`
  (italic is a new type axis). No inline raw values in `app/src`.
- **D-03:** Room events stay stage directions, unattributed: Laughter/Laughs/Laugh, Recess,
  Luncheon Recess, Cross Talk, **Voice Overlap**. Laughter inside a speaker's turn still
  splits into speech + a separate room-event row — this must not regress (it is easy to break
  by "just stop splitting parentheticals").
- **D-04:** Inaudible is a transcription failure, not a room event: a whole-turn inaudible
  marker with a known speaker is **not** a stage direction. It keeps `raw_speaker_label` and
  `person_id`, and renders as that speaker's ordinary attributed bubble with the marker as its
  body. Consequence: those rows gain a real `person_id` and derive `corpus/direct` → TRUSTED.
- **D-05:** A source-sentinel speaker (`speakers.json` `type: "U"`) is a fact **stored on the
  utterance at import**, never re-derived from `raw_speaker_label == "<INAUDIBLE>"`. It
  contributes **PROVISIONAL** to the trust floor (not UNCERTAIN, not VERIFIED — we accepted a
  limit, we verified nothing). No human action required.
- **D-06:** Majority-undetermined denominator = **non-stage-direction utterances** (what
  `_load_constituents` already iterates). Measured to yield the identical 6 arguments as the
  all-turns denominator; do not re-litigate. Threshold is **strictly greater than 50%**
  (16762 at 50.2% is held; 49.8% is not).
- **D-07:** PROVISIONAL / trust never reaches a public response. Any public schema module or
  frontend path this phase adds that is not already in the leak-ban lists is registered in
  `api/tests/test_trust_public_leak_ban.py` (PLUMBING-07).

**Canonical marker form**

- **D-08:** Canonical display form is **round parens around the curated label**:
  `(Inaudible)`, `(Laughter)`, `(Voice Overlap)`, `(Recess)`, `(Luncheon Recess)`,
  `(Cross Talk)`. Square brackets, lowercase, inner/trailing periods and stray spaces all
  collapse to this.
- **D-09:** Variant **words collapse to the curated label** too — `(Laughs)` → `(Laughter)`,
  `(voive overlap)` → `(Voice Overlap)`. This is exactly what
  `detect_stage_direction` already returns; the importer keeps that value instead of
  discarding it. No second normaliser.
- **D-10:** Canonicalisation is **stored, with the source form kept**: the importer writes the
  canonical form to `utterances.text` and preserves the verbatim source form in a separate
  column. Public and admin both show canonical; the raw form stays recoverable and auditable.
  Applies to **every whole-turn marker row** (room events and inaudible alike). Corpus source
  files are untouched. — **Reversibility:** costly — changes stored `text`, so the D-13 content
  digest changes for affected conversations; acceptable only because the pre-launch DB is
  reseeded, not reconciled.
- **D-11:** A marker **inline within a spoken sentence is left exactly as the source wrote
  it** — canonicalisation applies only where the whole row is the marker.

**Inaudible-body bubble**

- **D-12:** A whole-turn inaudible body renders **italic, in muted ink** (the stage-direction
  text colour token), inside the ordinary bubble — speaker name, rail and avatar unchanged. It
  reads as the transcriber's note rather than words the person said. Same treatment for every
  speaker. Italic/muted must come from design-system tokens/classes (D-02's type axis), not
  inline values.
- **D-13:** **Identical** body styling inside Treatment D bubbles (the ~5,860 double-unknown
  turns: sentinel speaker + inaudible body). One rule: a whole-turn inaudible body looks the
  same wherever it appears, whoever the speaker.

**Explanation card**

- **D-14:** The card lives only on the public transcript page, as a popover opened from either
  dashed `?` avatar of an undetermined bubble, same shape and placement as the speaker bio
  card (`SpeakerPopover.svelte`). Title "Undetermined speaker". Body copy verbatim from Figma
  node `33:70`:
  1. "The words here were captured clearly. What the record does not say is which person
     spoke them."
  2. "Oyez attributes each turn by listening to the argument audio. Where a voice could not be
     matched to a participant, the turn is left unattributed rather than guessed."
     — **ship as written** (operator confirmed).
  3. "Everyone who spoke was present in the courtroom that day — the record simply does not
     identify which of them this was."
- **D-15:** When the undetermined turn's body is the canonical inaudible marker, **sentence 1
  is swapped** for: "The words in this turn were not captured, and the record does not say
  which person spoke." Paragraphs 2 and 3 unchanged. The switch keys off the stored data (the
  row is a whole-turn inaudible marker), never off who the person might be.

**Touch and keyboard access**

- **D-16:** On touch devices (no hover), **tapping an undetermined bubble does what hover
  does** — reveals both dashed `?` avatars; tapping either opens the card. Resting state is the
  approved mockup on every device; the bubble does not open the card directly.
  Keyboard: the `?` avatars are focusable buttons revealed on focus, matching the existing
  avatar-button pattern (WCAG — Claude's, not a taste call).

**>50% publish gate**

- **D-17:** A >50%-undetermined argument contributes **UNCERTAIN** to its floor, so it is
  blocked by the **existing typed-reason override** exactly like any other UNCERTAIN argument:
  the operator can publish it one at a time with a logged, non-sticky `override_reason`. No new
  mechanism. Phase 54's bulk publish skips it automatically because it never publishes
  UNCERTAIN.
- **D-18:** The admin "why blocked" panel **states the fact with the number**, e.g.
  "68% of turns have an undetermined speaker (more than half)." Needs a new blocker code with
  the percentage carried in the blocker payload (today blockers are `{code, count}`), and a
  label in each of the three admin surfaces that render blocker codes
  (`admin/arguments/[id]`, `admin/arguments`, `admin/review`). Operator-facing only.

### Claude's Discretion

- Column names/types for the stored sentinel fact (D-05), the verbatim marker source form
  (D-10), and whatever stored fact tells the frontend a row is a whole-turn inaudible marker
  (D-12/D-15) — **stored, not string-matched on the frontend**, per the same lesson as D-05.
- Alembic migration shape; reseed procedure; digest implications of D-10.
- Fixing `_WHOLE_TURN_MARKER_RE`, which currently rejects trailing-period forms like
  `(Inaudible).` / `[Inaudible].` (~128 turns) — required for D-08 to be true.
- Removing `ChatBubble.svelte`'s `raw_speaker_label` fallback for undetermined rows (no literal
  `<INAUDIBLE>` may reach the page).
- Whether `<UNKNOWN>` (1 utterance, the crier) takes the same path as `<INAUDIBLE>` — both are
  `type: "U"`; treat identically unless there's a reason not to.
- Rounding of the displayed percentage in D-18 (integer is fine; the gate itself compares the
  exact ratio).
- Mobile/narrow-viewport geometry of Treatment D within the existing `@media (max-width: 768px)`
  bubble/rail tokens.

### Deferred Ideas (OUT OF SCOPE)

- How admin transcript/review views present undetermined turns — raised as a possible gray
  area, not discussed; admin keeps current behaviour unless a plan needs it.
- Bulk publish (Phase 54 — it inherits the >50% hold for free, see D-17); inline (mid-sentence)
  markers, which are left verbatim; consecutive undetermined turns (WON'T FIX, operator
  2026-09-23); the PDF pipeline path (Phase 999.11); any backfill migration — the corpus is
  reseeded (memory: reseed, do not migrate).

### UI-SPEC.md (checker-approved, do not re-litigate)

`.planning/phases/53-undetermined-speakers-marker-normalisation/53-UI-SPEC.md` is the binding
visual/interaction contract for the five surfaces with a real visual delta (Treatment D bubble,
explanation card, attributed-bubble inaudible body, canonical marker form, admin blocker
sentence). Its geometry, token, copy and interaction tables are locked; this research does not
restate them in full but references them by section below. Key numbers a plan will need:

- New geometry token `--bubble-max-width-undetermined`: `67%` desktop / `93%` at `≤768px`,
  expression `min(var(--bubble-max-width-undetermined), 63ch)`.
- New type-axis tokens: `--font-style-italic: italic;` and `--opacity-muted: 0.7;` — added to
  `app/src/app.css` `:root` and documented in `DESIGN-SYSTEM.md`'s Typography section.
- Both rail avatar buttons carry identical `aria-label="Undetermined speaker details"`; the row
  wrapper carries `aria-label="Undetermined speaker"`.
- The admin blocker sentence template is locked verbatim:
  `` `${percent}% of turns have an undetermined speaker (more than half).` ``
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SPEAKER-01 | An utterance whose corpus speaker is a `type: "U"` sentinel renders as Treatment D | §Architecture Patterns (render-loop third kind), §Code Examples (import_convokit sentinel path), §Pitfalls #1/#2/#6 |
| SPEAKER-02 | Hovering reveals a question-mark avatar in both rails; clicking opens an explanation card in the speaker-bio card shape | §Architecture Patterns (Treatment D component + explanation-card popover), UI-SPEC Interaction & State Contract (already locked, not re-derived here) |
| SPEAKER-03 | The source-sentinel fact is stored on the utterance at import, never re-derived from `raw_speaker_label` | §Code Examples (`_is_unattributed_speaker_type`, `_incoming_utterance_rows`), §Don't Hand-Roll |
| SPEAKER-04 | A stored source-sentinel speaker contributes PROVISIONAL to the trust floor rather than UNCERTAIN | §Code Examples (`api/services/trust.py::_load_constituents`), §Pitfalls #3 |
| SPEAKER-05 | An argument more than 50% undetermined is not publishable without explicit operator intervention | §Code Examples (`_load_constituents` denominator + blocker), §Architecture Patterns (publish gate needs zero new code in `admin_arguments.py`) |
| SPEAKER-06 | Every whole-turn marker in the curated vocabulary displays in its canonical form; inline markers untouched | §Code Examples (`_split_turn_into_rows`, `_WHOLE_TURN_MARKER_RE` fix), §Pitfalls #4 |
| SPEAKER-07 | A whole-turn inaudible marker with a known speaker renders as an ordinary attributed bubble whose body is the marker | §Code Examples (`_split_turn_into_rows`/`_incoming_utterance_rows`/`_import_utterances` rework), §Pitfalls #1 |
| SPEAKER-08 | Voice Overlap remains a stage direction; laughter inside a turn still splits into speech + room-event row | §Pitfalls #5 (regression guard, existing tests already pin this) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Apolitical framing is a hard constraint** — identical treatment across speakers; absent
  data renders as absent (no filler for a row with no data). Treatment D and the inaudible-body
  styling must apply the same rule to every speaker (already what D-12/D-13 require).
- **Pipeline is offline only** — this phase's importer changes are CLI-only; never expose a
  pipeline step as an HTTP endpoint.
- **Raw PDFs / corpus source files are immutable** — D-10's canonicalisation only ever touches
  `utterances.text`, never `data/corpus/*`.
- **Alembic is the sole DDL authority** — the new stored facts (D-05, D-10, D-12/D-15) go
  through a new Alembic migration (next revision `0033`), never `Base.metadata.create_all`.
- **Reseed, do not migrate** (project memory + CLAUDE.md doctrine) — new columns are additive
  and nullable/defaulted so existing rows are valid without a backfill UPDATE; the corpus is
  re-imported from scratch to populate them, per `alembic/versions/0032_person_display_name_and_oyez_unique.py`'s
  own precedent-setting docstring ("Per the project's standing reseed-not-migrate constraint,
  this migration contains NO UPDATE, NO raw-SQL data statement, and NO backfill of any kind").
- **Testing Policy** — no static source-text contract tests for frontend behaviour (a Svelte
  component under test must be exercised, not grepped); tests retire with the behaviour they
  pinned; no phase-numbered test files (name by unit under test, not `test_phase53_*`).
- **Defect Policy** — an already-existing bug this phase's own investigation surfaces (e.g. the
  `_WHOLE_TURN_MARKER_RE` trailing-period gap, or the latent "two consecutive undetermined
  turns silently merge into one run" defect found below) is Claude's to fix and report in one
  line, not an operator question — both are pre-determined by D-08/S5 already.
- **Repository-root `conftest.py` rule** — any new pytest fixture/hook that must fire
  regardless of invocation shape belongs in the root `conftest.py`, not a subdirectory one. Not
  expected to be needed by this phase (no new invocation-shape-independent hook), flagged only
  because the constraint is standing.

## Summary

Phase 53 closes an asymmetry the codebase already half-solved: `api/services/trust.py`'s
*participant* branch already lifts a NULL-`person_id` floor from UNCERTAIN to VERIFIED when a
human has confirmed the row unattributable; the *utterance* branch has no equivalent and
floors to UNCERTAIN unconditionally. The fix is not a new trust concept — it is threading a
**stored, import-time fact** (this speaker was ConvoKit's own `type: "U"` sentinel, not an
unresolved-but-real speaker) through five layers that today either discard it or never carry
it: the importer's turn-splitter, the `Utterance` model/migration, the trust-floor service, the
public utterance schema, and the SvelteKit render loop.

A second, independent defect sits one function away: `pipeline/corpus/stage_directions.py`'s
`detect_stage_direction` already normalises marker text to a canonical label, but
`pipeline/commands/import_convokit.py::_split_turn_into_rows` uses that return value **only as
a boolean** ("is this a stage direction, yes/no") and throws the canonical string away,
re-storing the raw verbatim segment. Worse, that same boolean conflates two different real-world
events — a *room event* (Laughter, Recess, Cross Talk, Voice Overlap: no speaker, nothing lost)
and a *transcription failure* (Inaudible: a known speaker's words were lost) — into one
`is_stage_direction` column, so a whole-turn `(Inaudible)` marker today gets `person_id=NULL,
raw_speaker_label=NULL, side=UNKNOWN`, discarding an attribution the source actually supplied.
Fixing this requires splitting `_split_turn_into_rows`'s two-state return
(`is_stage_direction: bool`) into a three-state classification (room event / inaudible /
speech) and re-plumbing `_incoming_utterance_rows`'s speaker-resolution guard, which today
skips resolution entirely for a turn whose only segment is a marker.

Both fixes are purely additive at the schema layer (new nullable/defaulted columns via a new
Alembic migration, no backfill — the corpus is reseeded) and purely additive at the trust layer
(a new PROVISIONAL branch, a new blocker code) — no existing passing test needs to change
behaviour, several existing tests already pin the "keep working" cases (Voice Overlap stays a
stage direction, Laughter still splits, a genuinely-unresolved non-sentinel utterance still
floors to UNCERTAIN), and the phase's own investigation surfaces one latent frontend defect
(consecutive undetermined turns silently merging into a single multi-bubble "run" today) that
the UI-SPEC's third render-item kind fixes as a side effect of correct classification order.

**Primary recommendation:** add one Alembic migration (new nullable/defaulted `Utterance`
columns: a sentinel-speaker boolean, a whole-turn-marker-kind fact, and a verbatim-source-text
column), rework `_split_turn_into_rows`/`_incoming_utterance_rows`/`_import_utterances` to carry
a three-way row classification instead of today's boolean, add one new branch to
`api/services/trust.py::_load_constituents` (sentinel → PROVISIONAL; >50% ratio → one
UNCERTAIN blocker with a percentage payload), and add a third `renderItems` kind
(`'undetermined'`) to the transcript route with a new Treatment D component and explanation-card
popover mode, keyed only off the new stored facts — never off `raw_speaker_label` string
content, per D-05/D-12's explicit "stored, not re-derived" rule.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sentinel-speaker classification (`speakers.json` `type: "U"`) | Pipeline (offline importer) | Database (new column) | Must be computed once at import time and stored — the API/frontend must never re-derive it from `raw_speaker_label` text (D-05) |
| Marker canonicalisation (whole-turn `(Inaudible)`, `(Laughter)`, etc.) | Pipeline (offline importer) | Database (`text` + new verbatim column) | `detect_stage_direction` is a pure pipeline-layer function; canonical form is written once at import, read everywhere downstream |
| Trust-tier floor (PROVISIONAL for sentinel, UNCERTAIN for >50%) | API / Backend (`api/services/trust.py`) | Database (`Argument.trust_tier` materialized column) | Trust derivation is explicitly backend-only per `provenance-and-trust-model.md` — "trust is operator-facing, never public" |
| Publish gate (>50% blocks without override) | API / Backend (`api/services/admin_arguments.py::publish_argument`) | — | Reuses the existing UNCERTAIN-tier override gate verbatim (D-17); needs zero new gate logic, only a new tier-contributing rule upstream in trust.py |
| Treatment D bubble + rails + hover reveal | Browser / Client (SvelteKit component + `app.css` tokens) | Frontend Server (SSR renders the initial markup) | Pure presentational branch on data already in the server-loaded payload; no new fetch, no new endpoint |
| Explanation card | Browser / Client (shared `Popover.Root`) | — | Same popover mechanism `SpeakerPopover.svelte` already uses; client-side interaction only |
| Public utterance schema fields (sentinel flag, marker-kind flag, canonical text) | API / Backend (`api/schemas/utterance.py`) | Database (ORM columns) | Rendering facts, not trust facts — expected to reach the public response (UI-SPEC's explicit note); the leak-ban test already covers this module |
| Admin "why blocked" panel percentage | Browser / Client (three admin `+page.svelte` files) | API / Backend (blocker payload) | Presentational only, but the underlying percentage is computed once in `_load_constituents` and passed through unchanged |

## Standard Stack

No new library, package, or service is introduced by this phase. The stack is unchanged from
Phase 52: SQLAlchemy 2.0 async + Alembic (backend/migration), FastAPI + Pydantic v2 (schema),
SvelteKit 2.x / Svelte 5 Runes + `bits-ui` (already a dependency, reused for the popover),
hand-rolled inline-style CSS custom properties (no component library, confirmed by
`53-UI-SPEC.md`'s own `Tool: none` / no-`components.json` finding).

### Package Legitimacy Audit

Not applicable — this phase installs no new package in any ecosystem. No `npm install` / `pip
install` command is part of this phase's work.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ OFFLINE PIPELINE (pipeline/commands/import_convokit.py)             │
│                                                                      │
│  ConvoKit turn.text                                                 │
│        │                                                            │
│        ▼                                                            │
│  _split_turn_into_rows()  ──►  per \n-segment:                      │
│        │                       detect_stage_direction(segment)      │
│        │                       ├─ None            → speech row      │
│        │                       ├─ room-event label → marker row,    │
│        │                       │                     NO speaker     │
│        │                       └─ "Inaudible"      → marker row,    │
│        │                                             KEEPS speaker  │
│        ▼                                                            │
│  _incoming_utterance_rows()  ──►  speaker resolution guard:         │
│        │                          speakers.json type == "U"?        │
│        │                          ├─ yes → sentinel fact = True,    │
│        │                          │        person_id stays NULL     │
│        │                          └─ no  → resolve/create Person    │
│        ▼                                                            │
│  _import_utterances()  ──►  writes Utterance row:                   │
│                              text = CANONICAL form (D-08/D-09)      │
│                              verbatim_source_text = raw segment     │
│                              speaker_undetermined = sentinel fact    │
│                              is_whole_turn_marker(_kind) = room/     │
│                                inaudible/none                        │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │ (new Alembic migration 0033)
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│ DATABASE (PostgreSQL via Alembic)                                    │
│  utterances: + speaker_undetermined (bool)                          │
│              + whole_turn_marker_kind (enum/nullable string)         │
│              + verbatim_source_text (nullable text)                 │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │
                 ┌───────────────┴────────────────┐
                 ▼                                 ▼
┌───────────────────────────────┐   ┌─────────────────────────────────┐
│ TRUST SERVICE                 │   │ PUBLIC API                       │
│ api/services/trust.py         │   │ api/schemas/utterance.py         │
│ _load_constituents():         │   │ UtteranceResponse gains:         │
│  - speaker_undetermined=True  │   │  speaker_undetermined,           │
│    → PROVISIONAL              │   │  is_whole_turn_marker (rendering │
│  - >50% undetermined ratio    │   │  facts only — never trust_tier,  │
│    → +1 UNCERTAIN, new        │   │  never review_state)             │
│    blocker code + percent     │   │                                  │
└───────────────┬───────────────┘   └────────────────┬─────────────────┘
                │ (existing gate,                     │ GET /arguments/{id}/utterances
                │  no new code)                        ▼
                ▼                    ┌──────────────────────────────────┐
┌───────────────────────────┐        │ SvelteKit +page.svelte            │
│ admin_arguments.py         │        │ renderItems: 'stage' | 'run' |    │
│ publish_argument()         │        │   'undetermined' (NEW, 3rd kind)  │
│ (UNCERTAIN → override      │        │ classified BEFORE run-grouping,   │
│  required, unchanged)      │        │ never merges two consecutive      │
└───────────────┬────────────┘        │ undetermined rows (S5 fix)        │
                │                     │        │                          │
                ▼                     │        ▼                          │
┌───────────────────────────┐        │ Treatment D component:             │
│ Three admin +page.svelte   │        │  rails empty at rest, dashed "?"   │
│ files: blockerSentence()   │        │  on hover/focus/tap, popover on    │
│ new branch renders the     │        │  click (shared Popover.Root)       │
│ %-carrying blocker code     │        └──────────────────────────────────┘
└─────────────────────────────┘
```

### Recommended Project Structure

No new top-level directories. Touched/added files, by layer:

```
pipeline/
├── corpus/stage_directions.py          # _WHOLE_TURN_MARKER_RE trailing-period fix
└── commands/import_convokit.py         # _split_turn_into_rows / _incoming_utterance_rows /
                                          # _import_utterances rework (3-way classification)

alembic/versions/
└── 0033_<slug>.py                       # new Utterance columns (additive, nullable/defaulted)

api/
├── models/models.py                     # Utterance model: new columns
├── services/trust.py                    # _load_constituents: PROVISIONAL branch + >50% blocker
├── schemas/utterance.py                 # UtteranceResponse: new rendering-fact fields
└── tests/test_trust_public_leak_ban.py  # only if a genuinely NEW public route/schema file is
                                          # added (utterance.py is already covered)

app/src/
├── app.css                              # --font-style-italic, --opacity-muted,
│                                          # --bubble-max-width-undetermined tokens
├── lib/public/
│   ├── ChatBubble.svelte                # inaudible-body italic/muted branch; remove/guard the
│   │                                     # raw_speaker_label fallback
│   ├── UndeterminedBubble.svelte (NEW)  # Treatment D — name is a suggestion, not locked
│   └── UndeterminedSpeakerCard.svelte (NEW, or inline in the route) # explanation card content
└── routes/arguments/[slug]/+page.svelte # renderItems third kind; onAvatarClick second mode

.planning/codebase/DESIGN-SYSTEM.md      # document the two new type-axis tokens
```

### Pattern 1: Three-way whole-turn classification (replaces today's boolean)

**What:** `_split_turn_into_rows` today returns `(row_text, is_stage_direction: bool)`. It must
become a three-way classification so a room event (no speaker) and an inaudible marker (keeps
speaker) are distinguishable by the caller.

**When to use:** Any place that currently branches on `is_stage_direction` for a
marker-detected row (`_split_turn_into_rows`, `_incoming_utterance_rows`, `_import_utterances`).

**Current code (the boolean being replaced), verified this session:**
```python
# pipeline/commands/import_convokit.py:1970-2001 (verified — read this session)
def _split_turn_into_rows(text: str) -> list[tuple[str, bool]]:
    segments = text.split("\n")
    rows: list[tuple[str, bool]] = []
    pending: list[str] = []

    def _flush_pending() -> None:
        if pending:
            rows.append(("\n".join(pending), False))
            pending.clear()

    for segment in segments:
        if stage_directions.detect_stage_direction(segment) is not None:
            _flush_pending()
            rows.append((segment, True))
        else:
            pending.append(segment)
    _flush_pending()
    return rows
```

Note `rows.append((segment, True))` stores the **raw segment**, not
`detect_stage_direction(segment)`'s canonical return value — this is the exact discard the
decision-tree note describes ("the importer discards it one line later"). The fix threads the
canonical label through as the row's `text`, and separately threads *which* curated label it
was (room event vs. Inaudible) so the caller can decide whether to keep the speaker.

**The consuming guard that must also change** (`_incoming_utterance_rows`,
verified this session, `pipeline/commands/import_convokit.py:2064-2107`):
```python
split_rows = _split_turn_into_rows(turn["text"])
...
speaker_id: str | None = None
raw_speaker_label: str | None = None
if any(not is_stage for _, is_stage in split_rows):
    speaker_id = turn.get("speaker")
    ...
```
Today, a turn whose **only** segment is a whole-turn `(Inaudible)` marker has `split_rows ==
[("(Inaudible)", True)]`; `any(not is_stage ...)` is `False`, so speaker resolution **never
runs at all** for that turn — this is the exact SPEAKER-07 defect. The three-way
classification must change this guard to run speaker resolution whenever any segment is speech
**or** a whole-turn inaudible marker (not only when a segment is plain speech) — a room-event
segment is the only kind that should suppress resolution.

### Pattern 2: Trust-tier PROVISIONAL branch mirrors the existing participant-branch lift

**What:** The participant branch of `_load_constituents` already lifts a NULL-`person_id` floor
from UNCERTAIN to VERIFIED for a specific stored fact (`review_state ==
OPERATOR_CONFIRMED`), appending the tier directly rather than calling `derive_tier`. The
utterance branch needs the identical shape for the sentinel fact, appending PROVISIONAL
directly (not via `derive_tier`, since `derive_tier` has no rule that maps to PROVISIONAL from
an utterance with no `source`/`method` — the sentinel case is not a provenance triple, it is a
distinct concept: "the source itself said it doesn't know").

**Current code, verified this session (`api/services/trust.py:105-115`):**
```python
for person_id, is_stage_direction, source, method in utterance_rows:
    if is_stage_direction:  # No speaker to attribute, no risk
        continue
    if person_id is None:  # Unresolved speaker floors to UNCERTAIN
        tiers.append(TrustTier.UNCERTAIN)
        _bump("unresolved_utterance_speaker")
        continue
    tier = derive_tier(source.value, method.value, UNREVIEWED)
    tiers.append(tier)
    if tier is TrustTier.UNCERTAIN:
        _bump("llm_corrective_utterance")
```
The new branch must check the stored sentinel fact **before** the `person_id is None` fallback,
so a sentinel row appends PROVISIONAL and does NOT bump `unresolved_utterance_speaker` (that
blocker code must stay reserved for a genuinely-unresolved, non-sentinel utterance — the
existing test `test_blocker_unresolved_utterance_speaker` and
`test_unresolved_speaker_drags_trusted_argument_to_uncertain` in
`api/tests/test_trust_recompute.py` pin exactly this path and must keep passing unchanged).
The query at the top of `_load_constituents` (`select(Utterance.person_id,
Utterance.is_stage_direction, ImportRun.source, ImportRun.method)`) needs the new sentinel
column added to its `select(...)` and to the loop's unpacking.

### Pattern 3: >50% blocker is a single post-loop check, not a per-row bump

**What:** D-18's blocker needs a payload beyond today's `{code, count}` shape (a `percent`
field) and represents an argument-level ratio, not a per-row occurrence — so it cannot be
produced by the existing `_bump(code)` per-row helper. Compute it once after the utterance-row
loop completes, using the same denominator basis the loop already iterates
(non-stage-direction utterances — D-06):

```python
# Sketch — not verified against a written implementation (none exists yet).
# Pattern only: reuses variables already being accumulated in the existing loop.
total_non_stage = 0
undetermined_count = 0
for person_id, is_stage_direction, speaker_undetermined, source, method in utterance_rows:
    if is_stage_direction:
        continue
    total_non_stage += 1
    if speaker_undetermined:
        undetermined_count += 1
        tiers.append(TrustTier.PROVISIONAL)
        continue
    ...  # existing person_id/derive_tier branches, unchanged

if total_non_stage > 0 and undetermined_count / total_non_stage > 0.5:
    tiers.append(TrustTier.UNCERTAIN)
    percent = round(undetermined_count / total_non_stage * 100)
    blockers.append({
        "code": "majority_undetermined_speaker",  # name is a suggestion, not locked
        "count": undetermined_count,
        "percent": percent,
    })
```
Because `floor_tier` takes `min()` over `_TIER_ORDER`, appending a single `TrustTier.UNCERTAIN`
entry to `tiers` is sufficient to floor the whole argument — **no change is needed to
`admin_arguments.py::publish_argument`**, which already blocks on `current_tier is
TrustTier.UNCERTAIN` and already requires a non-blank `override_reason` (D-17's "no new
mechanism" is literally true at the code level, verified this session,
`api/services/admin_arguments.py:817-831`).

### Pattern 4: Render-loop third kind, classified before run-grouping

**What:** `renderItems` (`app/src/routes/arguments/[slug]/+page.svelte:203-221`, verified this
session) currently classifies each utterance into `'stage'` or `'run'`:
```typescript
const renderItems = $derived.by(() => {
    const items: RenderItem[] = [];
    for (const u of data.utterances) {
        if (u.is_stage_direction) {
            items.push({ kind: 'stage', utterance: u });
            continue;
        }
        const last = items[items.length - 1];
        if (
            last?.kind === 'run' &&
            last.utterances[last.utterances.length - 1].raw_speaker_label === u.raw_speaker_label
        ) {
            last.utterances.push(u);
        } else {
            items.push({ kind: 'run', utterances: [u] });
        }
    }
    return items;
});
```
A sentinel-speaker row's `raw_speaker_label` is `None` (`_incoming_utterance_rows` sets it to
`None` whenever `speaker_id` is cleared for the sentinel case — verified this session,
`import_convokit.py:2100-2117`). **Latent defect found by this research:** two consecutive
sentinel utterances both carry `raw_speaker_label === null`, so today's equality check
(`null === null`) is `true` and they silently merge into one `'run'` item with a two-bubble
stack sharing one rail avatar — exactly the "one person spoke twice or two people spoke once"
ambiguity S5 says must be shown honestly (each its own bubble), not collapsed. This is a
pre-existing bug the phase's own UI-SPEC contract (S5: "each is always classified as its own
singleton") requires fixing as a side effect of adding the new `'undetermined'` kind — the new
kind must be checked **before** the `'run'`-continuation branch, exactly as `'stage'` is checked
first today:
```typescript
for (const u of data.utterances) {
    if (u.is_stage_direction) { items.push({ kind: 'stage', utterance: u }); continue; }
    if (u.speaker_undetermined) { items.push({ kind: 'undetermined', utterance: u }); continue; }
    // existing 'run' continuation/creation logic, unchanged
}
```
Per the Defect Policy, this is Claude's to fix silently (the correct behaviour — never merge —
is already settled by S5/UI-SPEC), reported in one line in the phase summary, not an
operator question.

### Anti-Patterns to Avoid

- **Deriving the sentinel fact or the whole-turn-marker fact from string content anywhere
  outside the importer** (`raw_speaker_label == "<INAUDIBLE>"`, or client-side regex on
  `utterance.text`). D-05 and D-12 both explicitly forbid this — store the fact once at import,
  read it everywhere else.
- **Re-implementing marker detection or a second normaliser.** `detect_stage_direction` already
  does the canonicalisation (D-09); the fix is entirely in *what the importer does with its
  return value*, never a new regex or a second vocabulary.
- **Bumping `unresolved_utterance_speaker` for a sentinel row.** That blocker code's existing
  tests (`test_blocker_unresolved_utterance_speaker`,
  `test_unresolved_speaker_drags_trusted_argument_to_uncertain`) pin it to the
  genuinely-unresolved, non-sentinel case; a sentinel row must take a different, non-blocking
  path (PROVISIONAL, no `_bump`, or a separate non-UNCERTAIN-tagged bump if visibility is
  wanted — but never the existing UNCERTAIN-tagged code).
- **Writing the >50% check as a per-row `_bump` call.** It is an argument-level ratio computed
  once, not an occurrence count; forcing it through the existing per-row `_bump(code)` helper
  either double-counts or requires a second pass — compute it directly after the loop.
- **Touching `pipeline/parser/state_machine.py` or `pipeline/commands/parse.py`.** The PDF path
  has its own independent stage-direction detection (verified this session — no import of
  `pipeline.corpus.stage_directions` anywhere in `pipeline/commands/parse.py`), and is
  explicitly deferred (Phase 999.11, corpus-first/PDF-deferred doctrine). Any new `Utterance`
  column added by this phase's migration must have a model-level default so the PDF path's
  existing `Utterance(...)` constructor call (which does not set the new columns — verified
  this session, `pipeline/commands/parse.py:371-381`) keeps working unmodified.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Marker text canonicalisation | A second normaliser / regex table in the importer or frontend | `pipeline.corpus.stage_directions.detect_stage_direction`'s existing return value | It already does fuzzy-match + canonical-label lookup (0.8 cutoff, curated vocabulary) — D-09 is explicit that this is "keep the value, not build a normaliser" |
| Explanation-card popover mechanics | A second `Popover.Root` instance, a modal, a custom dismiss handler | The page's existing single shared `Popover.Root` / `onAvatarClick`-style handler (`SpeakerPopover.svelte`'s pattern) | UI-SPEC: "not a second popover instance... exactly like every existing avatar button" |
| Publish-gate override UI/flow | A new blocking mechanism for the >50% case | The existing `TrustGateBlocked` / `override_reason` flow in `admin_arguments.py::publish_argument` | D-17 is explicit: "No new mechanism" — a new UNCERTAIN-tier contributor is sufficient |
| Avatar-reveal focus/hover state machine | A new keyboard-navigation library or ARIA pattern | The existing avatar-button `<button>`-always-in-DOM / `opacity`-only-visibility pattern every other rail avatar uses | UI-SPEC: "the existing avatar-button pattern, extended, not a new one" |

**Key insight:** every piece of new interaction and copy in this phase already has a working
precedent somewhere in the same two files (`SpeakerPopover.svelte` / the route's
`onAvatarClick`) or the same two pipeline modules (`stage_directions.py` /
`import_convokit.py`). The entire phase is *plumbing a fact through layers that already know how
to render/gate on facts of this shape* — not inventing a new rendering or trust primitive.

## Runtime State Inventory

Not applicable — this is a schema-addition phase (new nullable/defaulted `Utterance` columns),
not a rename/refactor/migration of existing identifiers. Per the project's standing
reseed-not-migrate doctrine (confirmed by `alembic/versions/0032`'s own precedent, "this
migration contains NO UPDATE, NO raw-SQL data statement, and NO backfill of any kind"), no
runtime state (stored data, live service config, OS-registered state, secrets, build artifacts)
carries the old shape forward across this change — the dev/pre-launch database is reseeded via
a fresh corpus import, not migrated in place. Confirmed no counter-evidence found in
`api/services/admin_dev.py::reset_to_fixture` or the corpus importer.

## Common Pitfalls

### Pitfall 1: The speaker-resolution guard skips resolution for a whole-turn-marker-only turn

**What goes wrong:** SPEAKER-07 silently fails to attribute a known speaker to a whole-turn
`(Inaudible)` row, because `_incoming_utterance_rows`'s `if any(not is_stage for _, is_stage in
split_rows):` guard treats "every segment is a marker" as "this turn has no speaker to
resolve" — true for a room event, false for an inaudible marker with a known speaker.
**Why it happens:** The guard was written before whole-turn Inaudible needed to keep a
speaker; it correctly encodes "a pure stage-direction turn has no speaker" for room events and
was never revisited when Inaudible needed different treatment.
**How to avoid:** The guard must trigger speaker resolution whenever any segment is speech OR a
whole-turn inaudible marker — only a pure room-event turn should skip it.
**Warning signs:** A test seeding a turn whose only segment is `"(Inaudible)"` with a known
`speaker` key, asserting the resulting `Utterance.person_id` is non-null and
`Utterance.raw_speaker_label` is set — if this assertion fails, the guard was not updated.

### Pitfall 2: A sentinel row bumping the wrong blocker code silently re-blocks a PROVISIONAL argument

**What goes wrong:** If the new sentinel branch in `_load_constituents` is added *after* the
existing `if person_id is None:` fallback rather than *before* it, every sentinel row still
falls into the old UNCERTAIN + `unresolved_utterance_speaker` path, and SPEAKER-04 silently
does nothing (an argument that should now be publishable without override stays blocked).
**Why it happens:** The existing `if person_id is None:` check has no way to distinguish "a
speaker we never got to" from "the source's own sentinel" without the new stored fact — adding
the fact but ordering the check wrong reproduces the exact bug being fixed.
**How to avoid:** Check the sentinel fact first; fall through to the existing `person_id is
None` UNCERTAIN path only for a non-sentinel unresolved speaker.
**Warning signs:** `test_unresolved_speaker_drags_trusted_argument_to_uncertain` and any new
sentinel-specific test both pass in isolation but a combined-argument test (one sentinel row +
one genuinely-unresolved row) produces an unexpected tier — check ordering first.

### Pitfall 3: `_seed_argument`'s test helper has no sentinel-flag parameter

**What goes wrong:** `api/tests/test_trust_recompute.py::_seed_argument`'s
`utterance_specs=[(resolved, is_stage_direction, side), ...]` tuple shape (verified this
session) has no slot for the new sentinel fact. A plan that writes a new test for D-05/SPEAKER-04
without first extending this helper will either duplicate a parallel seeding helper (Testing
Policy's under-2:1 LOC guideline argues against this) or hand-write raw `Utterance(...)`
construction inline, diverging from the existing convention.
**Why it happens:** The helper predates this phase; it was never meant to be exhaustive over
every future column.
**How to avoid:** Extend the tuple shape (e.g. a 4th optional element, defaulting to `False`)
rather than writing a second seeding helper.
**Warning signs:** A new test file duplicating `_seed_argument`'s ~40 lines of boilerplate
almost verbatim.

### Pitfall 4: `_WHOLE_TURN_MARKER_RE` genuinely cannot match the trailing-period forms today

**What goes wrong:** `(Inaudible).` / `[Inaudible].` (128 turns per the decision-tree note) fail
`detect_stage_direction` entirely today (verified this session — the regex
`^\s*[\[\(]([^\[\]\(\)]*)[\]\)]\s*$` requires only whitespace, never a period, between the
closing bracket and end-of-string), so they render as plain speech rows, not markers at all —
not merely un-canonicalised. A plan that assumes these 128 turns already reach the
canonicalisation step (and only need the *label* fixed) will silently leave them raw.
**Why it happens:** The regex was written to catch stray *inner* punctuation
(`(Inaudible.)`, handled by `_normalize`'s `re.sub(r"[^\w\s]", "", token)` on the captured
group) but never a trailing period *outside* the brackets.
**How to avoid:** Widen the closing-bracket alternative to tolerate a trailing period, e.g.
`[\]\)][.]*\s*$` in place of `[\]\)]\s*$` — confirmed sufficient for the two forms on record
(`(Inaudible).`, `[Inaudible].`); no other trailing-punctuation form is recorded in the 31-form
measurement.
**Warning signs:** `pipeline/tests/test_corpus_stage_directions.py` has no existing case for a
trailing period at all — a new test asserting `detect_stage_direction("(Inaudible).") ==
"Inaudible"` is the direct regression check this fix needs and does not yet exist.

### Pitfall 5: Laughter-inside-a-turn splitting is easy to break "fixing" the marker classification

**What goes wrong:** The rework of `_split_turn_into_rows` to distinguish room-event vs.
inaudible markers touches the exact function whose splitting behaviour
`test_inline_marker_segment_splits_spoken_remainder_into_own_rows` and
`test_whole_turn_stage_direction_produces_separate_row` (verified this session, both in
`pipeline/tests/test_import_convokit_utterances.py`, both use `"(Laughter)"` — a room event,
unaffected by the Inaudible reclassification) already pin. A change that collapses the
segment-flush logic (e.g. "just stop splitting parentheticals" per the standing pitfall list in
`STATE.md`) breaks these.
**Why it happens:** The room-event/inaudible split and the segment-flush/rejoin logic are
adjacent code in the same function; a change to one can accidentally touch the other.
**How to avoid:** Both existing tests must be re-run (not just left un-deleted) after the
rework — they are the regression guard for D-03/SPEAKER-08, and they already exist, so no new
test is needed for this specific guarantee, only continued passing.
**Warning signs:** Either test starts failing, or a new test using `"(Inaudible)"` in the same
inline-splitting position is added and *also* needs to pass with the speech remainder intact.

### Pitfall 6: `ChatBubble.svelte`'s `raw_speaker_label` fallback is reachable from more than the obvious path

**What goes wrong:** UI-SPEC's Copywriting Contract requires the literal sentinel string never
reach the page "defensively as well as by construction." Since Treatment D is a **new** render
branch that bypasses `ChatBubble.svelte` entirely for sentinel rows, it is tempting to leave
`ChatBubble.svelte:49`'s `utterance.speaker_name ?? utterance.raw_speaker_label ?? ''`
unchanged (reasoning "it's never called with a sentinel row anymore"). But `raw_speaker_label`
is `null` for sentinel rows in the data model (verified this session), so the fallback's
*danger* was never actually "renders `<INAUDIBLE>` literally" via this exact field — it was a
different, adjacent risk already flagged as "unverified in a browser" in the design notes. The
UI-SPEC's defensive request should be read as: after the render-loop change, confirm in a real
browser that no code path can still hand `ChatBubble` a sentinel utterance (e.g. a bug in the
new `renderItems` classification falling through to `'run'`), not necessarily rewriting line 49
itself.
**Why it happens:** The literal `<INAUDIBLE>` string source is `speakers.json`'s speaker `name`
field on the (never-created) sentinel Person, not `raw_speaker_label` — the importer already
sets `raw_speaker_label = None` for these rows (verified this session), so the exact mechanism
by which `<INAUDIBLE>` could reach the page was never fully nailed down, only "believed" per
the design note's own "Still OPEN" section.
**How to avoid:** Verify in a real browser (Playwright MCP — see project memory) what
`ChatBubble` actually renders for a sentinel row *before* this phase's changes, to confirm
exactly which code path produced the suspected literal-string leak, then confirm it is
unreachable *after* the render-loop change — rather than assuming line 49 is the culprit and
leaving the real path unverified a second time.
**Warning signs:** The design note's own "Still OPEN" item 1 is carried forward unresolved a
second time.

## Code Examples

### Existing: `detect_stage_direction` canonical-label return (unchanged by this phase)

```python
# Source: pipeline/corpus/stage_directions.py:60-92 (verified this session)
def detect_stage_direction(text: str | None) -> str | None:
    if not text:
        return None
    match = _WHOLE_TURN_MARKER_RE.match(text)
    if not match:
        return None
    inner = _normalize(match.group(1))
    if not inner:
        return None
    if inner.isdigit() or inner in _REJECTED_LITERALS:
        return None
    if inner in _CANONICAL_LABELS:
        return _CANONICAL_LABELS[inner]
    close_matches = difflib.get_close_matches(
        inner, _CANONICAL_LABELS.keys(), n=1, cutoff=_FUZZY_CUTOFF
    )
    if close_matches:
        return _CANONICAL_LABELS[close_matches[0]]
    return None
```
`_CANONICAL_LABELS` (verified this session, `pipeline/corpus/stage_directions.py:25-34`) is the
authoritative room-event/inaudible split: `"inaudible" -> "Inaudible"` is the ONE entry that is
a transcription failure; every other entry (`laughter`/`laughs`/`laugh` -> `"Laughter"`,
`"voice overlap"`, `"recess"`, `"luncheon recess"`, `"cross talk"`) is a room event. A plan can
classify a detected label as "inaudible" vs. "room event" with a single string comparison
against the literal `"Inaudible"` return value — no new vocabulary table needed.

### Existing: sentinel-speaker guard (unchanged signature, needs a stored-fact side effect added)

```python
# Source: pipeline/commands/import_convokit.py:1623-1634 (verified this session)
def _is_unattributed_speaker_type(speaker_meta: dict) -> bool:
    speaker_type = speaker_meta.get("type")
    if speaker_type is None:
        return False
    return str(speaker_type).strip().lower() in _UNATTRIBUTED_TYPE_VALUES
```
`_UNATTRIBUTED_TYPE_VALUES = {"u", "unattributed", "unknown"}` (verified this session, line
163) — the exact vocabulary D-05 stores a fact from. This function's boolean return already IS
the sentinel fact; the rework is entirely about **propagating** this existing boolean into the
row dict `_incoming_utterance_rows` builds (today it is consumed once to null out
`speaker_id`/`raw_speaker_label` and then thrown away — verified this session,
`import_convokit.py:2094-2101`) and then into the `Utterance` row `_import_utterances` writes
(today there is no column to carry it to).

### Existing: the frozen content-digest contract (unaffected by new columns, affected by D-10's `text` change)

```python
# Source: api/domain/content_digest.py:67-102 (verified this session)
# Per-row fields, in exactly this order: sequence, raw_speaker_label, text,
# is_stage_direction. Any OTHER key on a row is ignored.
```
New columns (sentinel flag, marker-kind flag, verbatim-source-text) are **outside** this frozen
four-field list and therefore never change the digest by their mere presence — only D-10's
change to the `text` value itself (raw segment -> canonical form) changes digests for affected
rows, which is explicitly accepted (reseed, not reconcile).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_WHOLE_TURN_MARKER_RE`'s fix (`[\]\)][.]*\s*$`) is sufficient for all 128 trailing-period turns and introduces no new false-positive match | Pitfall 4 | A too-permissive regex could start matching a legal-list marker followed by a period (`(a).`), though `_REJECTED_LITERALS`/digit-rejection still applies to the captured inner group regardless of the trailing-period change, so this risk is low but not verified against the full corpus |
| A2 | The suggested new column names (`speaker_undetermined`, `whole_turn_marker_kind`, `verbatim_source_text`) are available names with no collision — not verified against a full grep of `api/models/models.py`'s `Utterance` class beyond the columns already shown | Architecture Patterns / Pattern 1 | Low risk — these are illustrative names explicitly left to Claude's Discretion by CONTEXT.md; the planner should treat any name in this document as a suggestion, not a locked contract |
| A3 | A single boolean-plus-string-enum shape (`speaker_undetermined: bool`, `whole_turn_marker_kind: 'room_event' \| 'inaudible' \| None`) is sufficient to drive both D-05 (trust) and D-12/D-15 (frontend body-styling + card copy-swap) without a fourth column — not cross-checked against every downstream read site exhaustively | Architecture Patterns | If a downstream site needs to distinguish "this row IS the sentinel" from "this row's marker IS Inaudible" independently (D-04's known-speaker-with-Inaudible-body case has `speaker_undetermined = False` but still needs the marker-kind fact) the two facts must stay on separate columns, which the sketch above already assumes — flagged only because it was reasoned, not read from an existing schema |
| A4 | No existing test in `api/tests/` or `pipeline/tests/` asserts the CURRENT (soon-to-change) behaviour of a whole-turn `(Inaudible)` turn being classified `is_stage_direction=True` — verified by grep only (`grep -rn "Inaudible" pipeline/tests api/tests"` returned only `detect_stage_direction` unit tests, none touching the importer's row-classification output) | Testing / Pitfall 5 | If a test elsewhere DOES pin this (missed by the grep pattern used), it needs retirement per the Testing Policy — the planner should re-grep before writing the plan's task list |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **Exact stored-fact column shape (names, types, nullability defaults).**
   - What we know: CONTEXT.md explicitly leaves this to Claude's Discretion; the shape must be
     additive/nullable-or-defaulted (reseed-not-migrate) and must not collide with existing
     `Utterance` columns (`id`, `argument_id`, `import_run_id`, `sequence`,
     `raw_speaker_label`, `text`, `is_stage_direction`, `section_hint`, `side`, `person_id`).
   - What's unclear: whether the whole-turn-marker fact should be a single nullable
     string/enum column (room event label / "Inaudible" / null) or two independent booleans.
   - Recommendation: a plan should pick the shape during planning (not defer to execution),
     since it drives both the trust-service query and the public schema simultaneously — see
     Assumption A3 above for the reasoning that argues for two independent facts.

2. **Whether the >50% blocker code needs a corresponding admin-list-level pre-computation, or is only ever surfaced via the publish-attempt 422.**
   - What we know: `api/services/admin_review.py:1082` already attaches
     `summarize_tier_blockers`'s output to every review-queue row unconditionally (verified
     this session) — so the new blocker, once `_load_constituents` emits it, automatically
     reaches `admin/review`'s "why blocked" panel with no additional wiring. The
     publish-attempt 422 path (`admin/arguments/[id]`, `admin/arguments`) already reuses the
     same `summarize_tier_blockers` call inside `publish_argument`'s `TrustGateBlocked` raise.
   - What's unclear: nothing structural — this was resolved during research (see Pattern 3);
     flagged here only so the planner does not re-derive it from scratch.
   - Recommendation: no new endpoint or query is needed; the existing `blockers` plumbing to
     all three admin surfaces already carries any new blocker code emitted by `_load_constituents`.

3. **`<UNKNOWN>`'s single occurrence (the court crier) — same path as `<INAUDIBLE>` or a special case?**
   - What we know: both are `type: "U"` in `speakers.json`, already treated identically by
     `_is_unattributed_speaker_type` today (the same set `_UNATTRIBUTED_TYPE_VALUES = {"u",
     "unattributed", "unknown"}` matches both).
   - What's unclear: nothing technical — CONTEXT.md's Claude's Discretion note says "treat
     identically unless there's a reason not to," and no reason surfaced in this research.
   - Recommendation: treat identically; no special-case code needed.

## Environment Availability

Not applicable — this phase adds no new external tool, service, or runtime dependency. Every
tool it touches (Python 3.12/pytest/Alembic/PostgreSQL, Node/npm/SvelteKit/svelte-check) is
already installed and verified working by Phase 52's own plans in this same environment.
`node` is not on `PATH` in a non-interactive shell in this sandbox (project memory) — prefix any
`npm`/`node`/`gsd-tools` invocation with
`export PATH="$HOME/.nvm/versions/node/v24.18.0/bin:$PATH"`.

## Validation Architecture

Skipped — `.planning/config.json`'s `workflow.nyquist_validation` is explicitly `false`.

## Security Domain

Skipped — `.planning/config.json`'s `workflow.security_enforcement` is explicitly `false`.

## Verify Commands (this repo's actual invocations)

Confirmed from Phase 52's own plans and `.planning/config.json`:

```bash
# Python build/syntax check (test_command/build_command from .planning/config.json)
./.venv/bin/python -m compileall -q pipeline api scripts tests alembic

# Targeted pipeline tests (adjust module name to whatever this phase's plan creates/extends)
./.venv/bin/python -m pytest pipeline/tests/test_corpus_stage_directions.py -q
./.venv/bin/python -m pytest pipeline/tests/test_import_convokit_utterances.py -q

# Targeted API/trust tests
./.venv/bin/python -m pytest api/tests/test_trust_recompute.py -q
./.venv/bin/python -m pytest api/tests/test_admin_arguments_routes.py -q
./.venv/bin/python -m pytest api/tests/test_trust_public_leak_ban.py -q

# Full suite gate (bare invocation — repo-root conftest.py's DB-isolation redirect only
# fires reliably on this invocation shape; see CLAUDE.md's pytest-isolation rule)
./.venv/bin/python -m pytest -q

# Frontend build/typecheck (from app/package.json, verified this session)
npm --prefix app run check
npm --prefix app run build
```

## Sources

### Primary (HIGH confidence — read this session)

- `pipeline/corpus/stage_directions.py` — full file, `detect_stage_direction`,
  `_WHOLE_TURN_MARKER_RE`, `_CANONICAL_LABELS`
- `pipeline/commands/import_convokit.py` — `_is_unattributed_speaker_type`,
  `_is_justice_type`, `_resolve_and_link_participant`, `_split_turn_into_rows`,
  `_incoming_utterance_rows`, `_import_utterances`, `_UNATTRIBUTED_TYPE_VALUES`
- `api/services/trust.py` — full file, `_load_constituents`, `recompute_argument_tier`,
  `summarize_tier_blockers`, `TrustGateBlocked`
- `api/domain/trust.py` — full file, `TrustTier`, `derive_tier`, `floor_tier`
- `api/services/admin_arguments.py` — `publish_argument` (lines 751-850)
- `api/services/admin_review.py` (grep-verified line ranges) — `list_review_queue_arguments`
  attaching `blockers` to every row
- `api/routers/admin.py` (lines 1170-1220) — `TrustGateBlocked` → 422 structured detail
- `api/domain/content_digest.py` — full file, the frozen 4-field digest contract
- `api/schemas/utterance.py` — full file, `UtteranceResponse`
- `api/models/models.py` — `Utterance` model (lines 557-580)
- `alembic/versions/0032_person_display_name_and_oyez_unique.py` — full file, reseed-not-migrate
  precedent
- `alembic/versions/0027_trust_tier_and_candidate_status.py` — docstring, migration-mechanics
  precedent
- `app/src/lib/public/ChatBubble.svelte` — full file
- `app/src/lib/public/StageDirection.svelte` — full file
- `app/src/lib/public/SpeakerPopover.svelte` — full file
- `app/src/routes/arguments/[slug]/+page.svelte` — full file
- `app/src/app.css` — `:root` token block, media-query overrides (lines 1-260)
- `api/tests/test_trust_public_leak_ban.py` — `BANNED_KEYS`, `PUBLIC_SCHEMA_MODULE_PATHS`,
  `PUBLIC_FRONTEND_PATHS`
- `api/tests/test_trust_recompute.py` — `_seed_argument` helper shape, all
  `test_blocker_*`/`test_unresolved_*`/`test_recompute_*` tests
- `pipeline/tests/test_corpus_stage_directions.py`, `pipeline/tests/test_import_convokit_utterances.py`,
  `pipeline/tests/test_content_digest.py` — existing regression coverage
- `pipeline/commands/parse.py` — confirmed PDF-path independence from
  `pipeline.corpus.stage_directions`
- `app/package.json` — `check`/`build` scripts
- `pytest.ini`, root `conftest.py` — invocation-shape discipline
- `.planning/config.json` — `nyquist_validation: false`, `security_enforcement: false`,
  `test_command`, `build_command`

### Secondary (operator-authored design docs, treated as locked, not researched)

- `.planning/phases/53-undetermined-speakers-marker-normalisation/53-CONTEXT.md`
- `.planning/phases/53-undetermined-speakers-marker-normalisation/53-UI-SPEC.md`
- `.planning/notes/undetermined-speaker-display.md`
- `.planning/notes/transcript-rendering-decision-tree.md`
- `.planning/notes/provenance-and-trust-model.md`
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`

### Tertiary

None — no WebSearch/external documentation lookup was needed; this phase is entirely
internal-codebase plumbing with no new library or external API.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency; every tool already verified working in Phase 52
- Architecture: HIGH — every code path cited was read this session, not inferred from the
  design notes alone (the design notes describe intent; the code reading confirms exact
  current behaviour, including two discrepancies the notes did not fully specify: the
  speaker-resolution guard skip, and the latent consecutive-undetermined-merge defect)
- Pitfalls: HIGH — five of six pitfalls are grounded in a specific verified code location and/or
  an existing test that pins the behaviour; the sixth (Pitfall 6) is explicitly flagged as
  needing a live-browser check rather than asserted as fact

**Research date:** 2026-09-28
**Valid until:** No expiry driver — this is internal-codebase research with no external
version dependency; re-verify only if Phase 52's changes to `import_convokit.py`/`trust.py`
are further modified before this phase executes.
