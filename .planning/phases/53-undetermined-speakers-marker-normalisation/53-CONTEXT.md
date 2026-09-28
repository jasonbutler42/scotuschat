# Phase 53: Undetermined Speakers & Marker Normalisation - Context

**Gathered:** 2026-09-28
**Status:** Ready for planning

<domain>
## Phase Boundary

A turn the source could not attribute is shown honestly (Treatment D) rather than guessed at
or rendered broken; such arguments become publishable through a PROVISIONAL trust floor, with
the >50%-undetermined arguments held back; a whole-turn inaudible marker keeps the speaker the
source gave it; and every whole-turn marker in the curated vocabulary reads in one canonical
form everywhere.

**In scope:** SPEAKER-01 through SPEAKER-08.

**Out of scope:** bulk publish (Phase 54 — it inherits the >50% hold for free, see D-17);
inline (mid-sentence) markers, which are left verbatim; consecutive undetermined turns
(WON'T FIX, operator 2026-09-23); the PDF pipeline path (Phase 999.11); any backfill
migration — the corpus is reseeded (memory: reseed, do not migrate).

</domain>

<decisions>
## Implementation Decisions

### Carried forward — already approved, do not re-open

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

### Canonical marker form

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

### Inaudible-body bubble

- **D-12:** A whole-turn inaudible body renders **italic, in muted ink** (the stage-direction
  text colour token), inside the ordinary bubble — speaker name, rail and avatar unchanged. It
  reads as the transcriber's note rather than words the person said. Same treatment for every
  speaker. Italic/muted must come from design-system tokens/classes (D-02's type axis), not
  inline values.
- **D-13:** **Identical** body styling inside Treatment D bubbles (the ~5,860 double-unknown
  turns: sentinel speaker + inaudible body). One rule: a whole-turn inaudible body looks the
  same wherever it appears, whoever the speaker.

### Explanation card

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

### Touch and keyboard access

- **D-16:** On touch devices (no hover), **tapping an undetermined bubble does what hover
  does** — reveals both dashed `?` avatars; tapping either opens the card. Resting state is the
  approved mockup on every device; the bubble does not open the card directly.
  Keyboard: the `?` avatars are focusable buttons revealed on focus, matching the existing
  avatar-button pattern (WCAG — Claude's, not a taste call).

### >50% publish gate

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Decision record
- `.planning/notes/undetermined-speaker-display.md` — measurements (do not re-run the 900MB
  pass), Treatment D, trust decision, vocabulary split, marker-form data (31 forms)
- Figma `KICu66PtMLHk4fmxJYPggx` › Public › `unattributed-speaker-exploration` ›
  `unattributed-D`, node `33:2` — rest, hover, S5 and explanation card (`33:62`) states
- `.planning/ROADMAP.md` § Phase 53 — success criteria and notes
- `.planning/REQUIREMENTS.md` — SPEAKER-01…08

### Doctrine
- `.planning/seeds/SEED-002-scotus-teams-video-call-presentation.md` — faithful vs amplified;
  identical treatment
- `.planning/notes/provenance-and-trust-model.md` — trust tiers
- `.planning/notes/transcript-rendering-decision-tree.md` — how rows render
- `.planning/codebase/DESIGN-SYSTEM.md` + `app/src/app.css` — where D-02/D-12 additions land

### Code
- `pipeline/corpus/stage_directions.py` — curated vocabulary + canonical labels
- `pipeline/commands/import_convokit.py` — `_is_unattributed_speaker_type`,
  `_split_turn_into_rows`, `_incoming_utterance_rows`, `_import_utterances`
- `api/domain/content_digest.py` — D-13 frozen digest fields (`text`, `is_stage_direction`)
- `api/services/trust.py` — `_load_constituents` utterance branch, `summarize_tier_blockers`
- `api/domain/trust.py` — tier ordering, PROVISIONAL
- `api/services/admin_arguments.py` `publish_argument` — the override gate
- `api/tests/test_trust_public_leak_ban.py` — leak-ban registration
- `app/src/lib/public/ChatBubble.svelte`, `StageDirection.svelte`, `SpeakerPopover.svelte`
- `app/src/routes/arguments/[slug]/+page.svelte` — run grouping, rails, `onAvatarClick`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `detect_stage_direction` already returns the canonical label — keep it (D-09).
- `SpeakerPopover.svelte` + the route's `onAvatarClick` — the shape and anchoring for the
  explanation card.
- The existing typed-reason override and `TrustGateBlocked` blocker payload — D-17 needs only a
  new blocker code.

### Established Patterns
- Trust participant branch already lifts a NULL-person_id floor on a stored fact
  (`OPERATOR_CONFIRMED`); the utterance branch short-circuits to UNCERTAIN on `person_id is
  None` before any rule could apply — that asymmetry is the defect D-05 fixes.
- Stage-direction rows are excluded from the floor (`trust.py`) — D-04 inaudible rows must now
  be non-stage rows and so count.
- `$derived`, never `const`, off props in bubble components (stale-prop defect class).
- Run grouping keys on consecutive same speaker — undetermined rows must not merge into a
  neighbour's run, and two consecutive undetermined rows render as two bubbles (S5, honest).

### Integration Points
- `_incoming_utterance_rows` is shared by first import and reconcile — both change together.
- Public utterance schema (`api/schemas/utterance.py`) gains the stored facts; leak-ban check.
- Three admin pages render blocker codes (D-18).

</code_context>

<specifics>
## Specific Ideas

- Sentence-1 swap copy (D-15): "The words in this turn were not captured, and the record does
  not say which person spoke."
- Blocker wording (D-18): "68% of turns have an undetermined speaker (more than half)."

</specifics>

<deferred>
## Deferred Ideas

- How admin transcript/review views present undetermined turns — raised as a possible gray
  area, not discussed; admin keeps current behaviour unless a plan needs it.

</deferred>

---

*Phase: 53-undetermined-speakers-marker-normalisation*
*Context gathered: 2026-09-28*
