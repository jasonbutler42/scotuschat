# Phase 53: Undetermined Speakers & Marker Normalisation - Pattern Map

**Mapped:** 2026-09-28
**Files analyzed:** 15 (new + modified)
**Analogs found:** 15 / 15

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/0033_<slug>.py` (new) | migration | batch | `alembic/versions/0032_person_display_name_and_oyez_unique.py` | exact |
| `api/models/models.py` (`Utterance` class, modified) | model | CRUD | itself (existing `Utterance` columns) | exact |
| `pipeline/corpus/stage_directions.py` (`_WHOLE_TURN_MARKER_RE`, modified) | utility | transform | itself (existing regex + `detect_stage_direction`) | exact |
| `pipeline/commands/import_convokit.py` (`_split_turn_into_rows`, `_incoming_utterance_rows`, `_import_utterances`, modified) | service | batch/transform | itself (existing three functions) | exact |
| `api/services/trust.py` (`_load_constituents`, `summarize_tier_blockers`, modified) | service | CRUD/transform | itself (existing participant-branch PROVISIONAL lift) | exact |
| `api/schemas/utterance.py` (`UtteranceResponse`, modified) | model (Pydantic schema) | request-response | itself (existing `speaker_initials` field addition, D-12 precedent) | exact |
| `api/tests/test_trust_public_leak_ban.py` (modified — register new module/fields if needed) | test | batch | itself (`PUBLIC_SCHEMA_MODULE_PATHS`, `BANNED_KEYS`) | exact |
| `api/tests/test_trust_recompute.py` (`_seed_argument` extended, modified) | test | CRUD | itself (existing tuple-shape helper) | exact |
| `pipeline/tests/test_corpus_stage_directions.py` (new case, modified) | test | transform | itself | exact |
| `pipeline/tests/test_import_convokit_utterances.py` (new case, modified) | test | batch | itself | exact |
| `app/src/app.css` (new tokens, modified) | config (design tokens) | — | itself (`:root` token block) | exact |
| `app/src/lib/public/UndeterminedBubble.svelte` (new, name a suggestion) | component | request-response (render) | `app/src/lib/public/ChatBubble.svelte` | role-match |
| `app/src/lib/public/ChatBubble.svelte` (inaudible-body branch, modified) | component | request-response (render) | itself | exact |
| `app/src/lib/public/StageDirection.svelte` (italic-token conversion, modified) | component | request-response (render) | itself | exact |
| `app/src/routes/arguments/[slug]/+page.svelte` (`renderItems` third kind, second popover mode, modified) | route/controller (SvelteKit page) | request-response | itself (existing `renderItems`, `onAvatarClick`, shared `Popover.Root`) | exact |
| Explanation-card content (new, inline in route or `UndeterminedSpeakerCard.svelte`) | component | request-response (render) | `app/src/lib/public/SpeakerPopover.svelte` | role-match |
| `app/src/routes/admin/arguments/+page.svelte`, `admin/arguments/[id]/+page.svelte`, `admin/review/+page.svelte` (`blockerSentence()` new branch, modified — 3 files) | component/route | request-response | themselves (existing verbatim-duplicated `blockerSentence` function) | exact |

## Pattern Assignments

### `alembic/versions/0033_<slug>.py` (migration, batch)

**Analog:** `alembic/versions/0032_person_display_name_and_oyez_unique.py`

**Reseed-not-migrate docstring pattern to copy verbatim in spirit** (confirmed by RESEARCH.md, verified same session):
```
"""Per the project's standing reseed-not-migrate constraint, this migration
contains NO UPDATE, NO raw-SQL data statement, and NO backfill of any kind."""
```
Apply the same discipline: every new `Utterance` column must be `nullable=True` or carry a
server/model default so the pre-existing rows (and the PDF-path `Utterance(...)` constructor in
`pipeline/commands/parse.py:371-381`, which does not set these columns) remain valid with no
`UPDATE`/backfill statement in `upgrade()`. Use `op.add_column(...)` only; no `op.execute("UPDATE ...")`.

---

### `api/models/models.py` — `Utterance` (model, CRUD)

**Analog:** itself, lines 557-580 (verified this session)

**Current columns to extend from:**
```python
class Utterance(Base):
    __tablename__ = "utterances"

    id = Column(BigInteger, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    import_run_id = Column(Integer, ForeignKey("import_run.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    raw_speaker_label = Column(String(200), nullable=True)   # None for stage directions
    text = Column(Text, nullable=False)
    is_stage_direction = Column(Boolean, nullable=False, default=False)
    section_hint = Column(String(50), nullable=True)
    side = Column(SAEnum(SideEnum, ...), nullable=False, default=SideEnum.UNKNOWN)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=True)
```
New columns follow this file's existing convention: `Column(<type>, nullable=True)` or
`nullable=False, default=<value>` — never a raw SQL default. Match the existing inline comment
style (`# None for stage directions`) to document the new columns' semantics (sentinel fact,
marker-kind fact, verbatim source text) per CONTEXT.md's Claude's Discretion naming freedom.

---

### `pipeline/corpus/stage_directions.py` — `_WHOLE_TURN_MARKER_RE` fix (utility, transform)

**Analog:** itself — `detect_stage_direction`, lines 60-92 (verified this session, reproduced in RESEARCH.md)

**Pattern to copy (regex-widen, same function, same style):** the existing regex
`^\s*[\[\(]([^\[\]\(\)]*)[\]\)]\s*$` needs its closing-bracket alternative widened to tolerate an
optional trailing period: replace `[\]\)]\s*$` with `[\]\)][.]*\s*$`. Keep `_normalize`,
`_CANONICAL_LABELS`, `_REJECTED_LITERALS`, `difflib.get_close_matches` untouched — this is a
one-line regex change, not a rewrite (D-09: no second normaliser).

---

### `pipeline/commands/import_convokit.py` (service, batch/transform)

**Analog:** itself — `_split_turn_into_rows` (lines 1970-2001), `_incoming_utterance_rows`
(lines 2064-2117), `_is_unattributed_speaker_type` (lines 1623-1634) — all verified this session.

**Current boolean-return pattern being replaced:**
```python
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

**Core rework pattern:** keep the same flush/pending shape (`_flush_pending`, `pending: list[str]`,
speech accumulation) but change the marker-row append from `rows.append((segment, True))` (raw
segment discarded canonical form) to carrying three things per row: the canonical text
(`detect_stage_direction(segment)`'s return value, not `segment`), a marker-kind classification
(compare the canonical return value against the literal `"Inaudible"` — the one
`_CANONICAL_LABELS` entry that is a transcription failure per RESEARCH.md — vs. every other
value, a room event), and the verbatim `segment` for the new source-text column.

**Guard that must change (currently silently skips resolution for a whole-turn-marker-only turn):**
```python
split_rows = _split_turn_into_rows(turn["text"])
...
speaker_id: str | None = None
raw_speaker_label: str | None = None
if any(not is_stage for _, is_stage in split_rows):
    speaker_id = turn.get("speaker")
    ...
```
Change the predicate from "any segment is plain speech" to "any segment is speech OR a whole-turn
inaudible marker" — only a pure room-event segment should suppress speaker resolution. This is
the exact SPEAKER-07 fix (Pitfall 1 in RESEARCH.md).

**Sentinel-fact propagation source (unchanged signature, reuse directly):**
```python
def _is_unattributed_speaker_type(speaker_meta: dict) -> bool:
    speaker_type = speaker_meta.get("type")
    if speaker_type is None:
        return False
    return str(speaker_type).strip().lower() in _UNATTRIBUTED_TYPE_VALUES
```
`_UNATTRIBUTED_TYPE_VALUES = {"u", "unattributed", "unknown"}` already covers both `<INAUDIBLE>`
and `<UNKNOWN>` (CONTEXT.md's "treat identically" note) — the fix is propagating this existing
boolean into the row dict and then into the `Utterance` row `_import_utterances` writes, not
changing this function.

---

### `api/services/trust.py` — `_load_constituents` (service, CRUD/transform)

**Analog:** itself, lines 105-115 (verified this session, reproduced in RESEARCH.md) — the
participant branch's existing NULL-`person_id` → VERIFIED lift is the shape to mirror.

**Current utterance-branch code being extended:**
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
**Pattern to copy:** insert a sentinel check (new stored fact, e.g. `speaker_undetermined`)
**before** the `person_id is None` fallback — append `TrustTier.PROVISIONAL` directly (not via
`derive_tier`, per RESEARCH.md's reasoning: no provenance triple exists for a sentinel row) and do
**not** call `_bump("unresolved_utterance_speaker")` for this case (that code's existing tests pin
it to the genuinely-unresolved, non-sentinel path — Pitfall 2). Add the new column to the
`select(Utterance.person_id, Utterance.is_stage_direction, ImportRun.source, ImportRun.method)`
query and the loop's unpacking.

**>50% blocker — single post-loop check pattern (sketch from RESEARCH.md, not yet implemented):**
```python
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
        "code": "majority_undetermined_speaker",
        "count": undetermined_count,
        "percent": percent,
    })
```
Do not force this through the existing per-row `_bump(code)` helper — it is an argument-level
ratio, computed once after the loop, matching the existing `blockers.append({...})` dict shape
already used elsewhere in the file (`{code, count}` → extended with `percent`).

---

### `api/schemas/utterance.py` — `UtteranceResponse` (schema, request-response)

**Analog:** itself, lines 22-40 (verified this session) — the D-12/Phase 52 precedent for adding
a server-computed rendering field.

**Pattern to copy exactly (field + nullable + inline comment referencing the driving decision):**
```python
class UtteranceResponse(BaseModel):
    """One spoken utterance or stage direction from the argument transcript."""

    id: int
    sequence: int
    raw_speaker_label: Optional[str] = None
    text: str
    is_stage_direction: bool
    side: str
    section_hint: Optional[str] = None
    person_id: Optional[int] = None
    import_run_id: int
    speaker_name: Optional[str] = None
    speaker_role: Optional[str] = None
    # D-12: server-computed ... nullable because ... is nullable when person_id is null.
    speaker_initials: Optional[str] = None

    model_config = {"from_attributes": True}
```
Add the new rendering-fact fields (sentinel flag, whole-turn-marker-kind flag) the same way
`speaker_initials` was added: typed, `Optional[...] = None`, with a one-line comment naming the
decision (D-05/D-12) it serves. Per UI-SPEC's "Public schema note": these are rendering facts,
expected to reach the public response — never `trust_tier`/`review_state` (already banned).

---

### `api/tests/test_trust_public_leak_ban.py` (test, batch)

**Analog:** itself, lines 54-127 (verified this session)

`PUBLIC_SCHEMA_MODULE_PATHS` already includes `api/schemas/utterance.py` — no new entry needed
for the schema itself. `BANNED_KEYS` currently:
```python
BANNED_KEYS = (
    "trust_tier", "review_state", "source", "method", "incoming_value",
    "existing_value", "resolved_at", "content_digest", "oyez_speaker_id",
    "argument_discrepancies",
)
```
No new key needs banning by this phase (the new fields are rendering facts, not trust facts —
D-07 is already satisfied by keeping the sentinel/marker-kind fields off this list, not adding
them to it). Only register a **new** file here (PLUMBING-07) if this phase adds a genuinely new
public schema module not already in `PUBLIC_SCHEMA_MODULE_PATHS` — current plan does not require
one (`utterance.py` already covered).

---

### `api/tests/test_trust_recompute.py` — `_seed_argument` (test, CRUD)

**Analog:** itself (verified this session per RESEARCH.md Pitfall 3) — tuple shape
`utterance_specs=[(resolved, is_stage_direction, side), ...]`.

**Pattern to copy:** extend the tuple shape with a 4th optional element defaulting to `False`
(e.g. `(resolved, is_stage_direction, side, speaker_undetermined=False)`), rather than writing a
second seeding helper — Testing Policy's under-2:1 LOC guideline argues against duplication.

---

### `app/src/app.css` — new tokens (config)

**Analog:** itself, `:root` token block (lines 1-260, verified this session) — existing named-axis
convention (`--font-weight-regular`, `--font-weight-semibold`).

**Pattern to copy:**
```css
--font-style-italic: italic;
--opacity-muted: 0.7;
--bubble-max-width-undetermined: 67%; /* desktop */
```
plus the `@media (max-width: 768px)` override block already used for `--bubble-max-width` at 93%.
Also convert `StageDirection.svelte`'s existing raw `font-style: italic;` literal (line ~29) to
`var(--font-style-italic)` in the same pass (D-02 note: "the one spot Phase 51's conversion sweep
did not reach").

---

### `app/src/lib/public/ChatBubble.svelte` (component, request-response)

**Analog:** itself, full file (verified this session) — existing `$derived` props discipline and
`displayName` fallback.

**Stale-prop discipline to preserve (critical, project memory: svelte-state-proxy-vs-grep):**
```typescript
// Every value below is $derived, NOT const. A plain `const` off a prop is
// captured once at component init and then frozen ...
const isBench = $derived(utterance.side === 'BENCH');
const displayName = $derived(utterance.speaker_name ?? utterance.raw_speaker_label ?? '');
```
New conditional style branch must follow the same `$derived` discipline:
```typescript
const isMarkerBody = $derived(utterance.whole_turn_marker_kind === 'inaudible'); // field name illustrative
```
and apply inline style per the UI-SPEC's exact contract:
```
font-style: {isMarkerBody ? var(--font-style-italic) : normal};
color: {isMarkerBody ? var(--color-stage-text) : var(--color-text-primary)};
```
Verify in a real browser (Playwright MCP) that `raw_speaker_label` fallback (line 49,
`utterance.speaker_name ?? utterance.raw_speaker_label ?? ''`) is unreachable for a sentinel row
post-change — Pitfall 6, do not assume line 49 alone is the leak path.

---

### `app/src/lib/public/UndeterminedBubble.svelte` (new component, request-response)

**Analog:** `app/src/lib/public/ChatBubble.svelte` (role-match — same "single centred bubble,
inline `style=`, CSS custom properties" convention; no component library, per UI-SPEC "Tool: none")

**Pattern to copy:** same `RADIUS_BY_POSITION`-style single-bubble radius (`single` entry: 6px all
corners), same `--color-surface` fill / `--color-border` 1px border / `--space-sm` padding
`ChatBubble` already uses for a singleton bubble, but with `max-width: min(var(--bubble-max-width-undetermined), 63ch)`
instead of `ChatBubble`'s own max-width token (per UI-SPEC Layout & Placement Contract). Body
`<p>` reuses `ChatBubble`'s own inaudible-body italic/muted branch (D-13: "identical treatment
inside Treatment D bubbles") — do not fork a second styling rule; either reuse the same style
expression or extract a shared helper.

---

### Explanation card (new, request-response)

**Analog:** `app/src/lib/public/SpeakerPopover.svelte` (role-match — same shape/placement per D-14)

**Pattern to copy from `.popover-card`'s existing wrapper contract** (per UI-SPEC, verified
against the route's shared instance):
```
padding: var(--space-xl);
min-width: 300px; max-width: 400px;
background-color: var(--color-surface);
border: 1px solid var(--color-border);
border-radius: 8px;
```
and the section-divider rule between paragraphs:
```
border-top: 1px solid var(--color-border);
margin-top: var(--space-lg);
padding-top: var(--space-lg);
```
No avatar/photo/name/role/tenure — title + body only, unlike `SpeakerPopover`'s full bio card.

---

### `app/src/routes/arguments/[slug]/+page.svelte` (route, request-response)

**Analog:** itself — `renderItems` (lines ~203-221 per RESEARCH.md), `onAvatarClick` (line 26),
shared `Popover.Root` (lines 242-256), verified this session.

**Existing shared-popover + avatar-click pattern to extend (do not add a second `Popover.Root`):**
```typescript
let isPopoverOpen = $state(false);
let currentSpeaker = $state<SpeakerDetail | null>(null);
let currentAnchor = $state<HTMLElement | null>(null);

function onAvatarClick(personId: number, anchor: HTMLElement): void {
    const speaker = speakersMap.get(personId) ?? null;
    currentSpeaker = speaker;
    currentAnchor = anchor;
    isPopoverOpen = speaker !== null;
}
```
```svelte
<Popover.Root bind:open={isPopoverOpen} onOpenChange={(open) => { if (!open) currentSpeaker = null; }}>
    <Popover.Content customAnchor={currentAnchor}>
        <SpeakerPopover ... />
    </Popover.Content>
</Popover.Root>
```
**Pattern to copy:** add a second content mode (e.g. `currentMode: 'speaker' | 'undetermined'`) to
the same `Popover.Root` instance rather than a new one; a new `onUndeterminedAvatarClick(anchor)`
handler sets `currentAnchor` and switches mode, conditionally rendering
`{#if currentMode === 'undetermined'}<UndeterminedSpeakerCard .../>{:else}<SpeakerPopover .../>{/if}`
inside the existing `Popover.Content`.

**`renderItems` third-kind pattern (fixes the latent consecutive-merge defect as a side effect):**
```typescript
const renderItems = $derived.by(() => {
    const items: RenderItem[] = [];
    for (const u of data.utterances) {
        if (u.is_stage_direction) { items.push({ kind: 'stage', utterance: u }); continue; }
        if (u.speaker_undetermined) { items.push({ kind: 'undetermined', utterance: u }); continue; }
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
Check the new `'undetermined'` kind **before** the `'run'`-continuation branch, exactly as
`'stage'` is checked first today — this is Claude's to fix silently per the Defect Policy (S5 is
already locked), reported in one line, not an operator question.

---

### `app/src/routes/admin/arguments/+page.svelte`, `admin/arguments/[id]/+page.svelte`, `admin/review/+page.svelte` (component/route, request-response)

**Analog:** themselves — `blockerSentence(code, count)`, lines 129-147 (verified this session,
`admin/arguments/+page.svelte`), verbatim-duplicated across all three files.

**Current pattern (five existing branches) to extend with a sixth:**
```typescript
function blockerSentence(code: string, count: number): string {
    const plural = count === 1 ? '' : 's';
    if (code === 'unresolved_utterance_speaker') {
        return `${count} utterance${plural} ${count === 1 ? 'has' : 'have'} no resolved speaker`;
    }
    if (code === 'unresolved_participant') {
        return `${count} participant${plural} ${count === 1 ? 'is' : 'are'} unresolved`;
    }
    if (code === 'llm_corrective_utterance') {
        return `${count} utterance${plural} came from the LLM corrective pass`;
    }
    if (code === 'uncertain_participant') {
        return `${count} participant${plural} ${count === 1 ? 'has' : 'have'} unverified provenance`;
    }
    if (code === 'no_constituents') {
        return 'this argument has no utterances yet';
    }
    return `${count} occurrence${plural} of "${code}"`;
}
```
**Pattern to copy:** the function signature must widen to accept the new `percent` field (today's
signature is `(code, count)` only — the blocker object itself already carries `{code, count}` and
must grow a `percent` field per Pattern 3 above). Add one new `if` branch, following the exact
shape of the existing five, using the **locked** template from UI-SPEC's Copywriting Contract:
```typescript
if (code === 'majority_undetermined_speaker') {
    return `${percent}% of turns have an undetermined speaker (more than half).`;
}
```
Must be updated identically in all three files (they are verbatim-duplicated today — do not
extract a shared module unless already planned elsewhere; matching the existing duplication
convention is lower risk for this phase's scope). Rendered through the existing unchanged
`<li>{blockerSentence(b.code, b.count)}</li>` markup — no new markup, per UI-SPEC.

---

## Shared Patterns

### Stored-fact, never-string-matched discipline (D-05/D-12)
**Source:** `pipeline/commands/import_convokit.py::_is_unattributed_speaker_type` (existing) +
`api/services/trust.py`'s participant-branch `review_state == OPERATOR_CONFIRMED` lift (existing)
**Apply to:** every new column, schema field, and frontend branch this phase adds — always key
off a stored boolean/enum fact written once at import, never off `raw_speaker_label` string
content or client-side regex on `utterance.text`.

### `$derived` (never `const`) off component props
**Source:** `app/src/lib/public/ChatBubble.svelte` (existing, documented inline)
**Apply to:** `UndeterminedBubble.svelte`, any new conditional in `ChatBubble.svelte`,
`UndeterminedSpeakerCard.svelte` — all prop-derived values.

### Shared single `Popover.Root` instance, never a second popover
**Source:** `app/src/routes/arguments/[slug]/+page.svelte` (existing `SpeakerPopover` wiring)
**Apply to:** the explanation card — extend the same instance with a second content mode.

### Reseed-not-migrate additive migrations
**Source:** `alembic/versions/0032_person_display_name_and_oyez_unique.py` (existing docstring
precedent)
**Apply to:** the new `0033` migration — nullable/defaulted columns only, no `UPDATE`/backfill.

### Existing typed-reason override gate, unchanged
**Source:** `api/services/admin_arguments.py::publish_argument` (verified lines 817-831 per
RESEARCH.md — blocks on `current_tier is TrustTier.UNCERTAIN`, requires non-blank `override_reason`)
**Apply to:** SPEAKER-05's >50% gate — zero new code needed here; only the new UNCERTAIN-tier
contributor in `trust.py` upstream.

## No Analog Found

None — every file in this phase's scope has an exact or role-match analog already in the
codebase; this phase is plumbing existing patterns through new columns/branches, not introducing
a new architectural shape (confirmed by RESEARCH.md's own "Don't Hand-Roll" table).

## Metadata

**Analog search scope:** `pipeline/`, `api/`, `app/src/`, `alembic/versions/` (guided by
RESEARCH.md's already-verified file list; no additional Glob/Grep sweep was needed since
RESEARCH.md's Sources section already enumerates every file this phase touches with session-verified
line ranges)
**Files scanned:** 18 (all confirmed git-tracked via `git ls-files`)
**Pattern extraction date:** 2026-09-28
