# Phase 52: Justice Identity - Research

**Researched:** 2026-09-24
**Domain:** SQLAlchemy/Alembic identity modeling + idempotent CSV/corpus import resolution + a small server-side name-formatting fix, in an existing FastAPI/SvelteKit codebase
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The 4 rows the draft flagged as needing the operator are **resolved and
  accepted**, on the evidence of the CSV's own oath/termination dates rather than any
  name-matching heuristic (Harlan elder vs. grandson, Salmon P. Chase vs. Samuel Chase,
  Henry Brockholst Livingston). Do not re-open these four. Reversibility: reversible.
- **D-02:** The 45 `derived` rows are gated by a mechanical structural test plus an operator
  spot-check, not a full 114-row manual read. The test asserts the `oyez_speaker_id` slug,
  the corpus display form and the CSV first/last name agree structurally — a check on a
  hand-verified artifact, not a derivation rule.
- **D-03:** Mapping coverage is verified complete: all 114 `j__`-prefixed speakers in
  `data/corpus/speakers.json` are mapped, with no unmapped ids and no mapping rows pointing
  at a non-existent speaker.
- **D-04:** `Amy Coney Barrett` and `Ketanji Brown Jackson` are seeded with NULL
  `oyez_speaker_id` and NULL `display_name` — seated after the corpus's 2019 cutoff. The
  partial unique index permits multiple NULLs.
- **D-05:** Holmes: do not change his suffix in the CSV. Bio card reads `Oliver Wendell
  Holmes`; utterances read `Oliver W. Holmes, Jr.` — each faithful to its own source, neither
  file edited. The only suffix disagreement across all 114 rows.
- **D-06:** The verified mapping lives at `data/corpus/justice_identity_mapping.csv` — a new
  file beside the source CSV, 114 rows. `supreme_court_justices_sections.csv` is NOT
  modified. Reversibility: costly.
- **D-07:** A mapping row joins its CSV justice by explicit name parts (`first_name` /
  `middle_name` / `last_name` / `name_suffix`), not a reconstructed `full_name` string —
  independent of the Phase 38 `format_full_name` contract.
- **D-08:** The draft's `confidence` column (`exact`/`derived`/`AMBIGUOUS`/`UNRESOLVED`) is
  dropped from the shipped artifact.
- **D-09:** `people.display_name` is read-only — visible on the admin person page, never
  added to `PersonUpdate`'s mass-assignment allow-list (`extra="forbid"` stays intact).
- **D-10:** `people.oyez_speaker_id` becomes visible and read-only on the admin person page.
- **D-11:** The admin People directory keeps listing `full_name` only, as today.
- **D-12:** Avatar initials are computed server-side from structured name parts and shipped
  as a single field on the speaker payloads. The client stops parsing names. Reversibility:
  costly — adds a field to two public response schemas.
- **D-13:** When a person has no structured parts, fall back to the current
  first-token/last-token rule with known suffix tokens dropped (`split_legacy_full_name`
  deliberately refuses three shapes; a corpus-resolved advocate can legitimately have no parts).
- **D-14:** On any reset failure, the frontend action re-reads fixture state before asserting
  anything and reports what it actually found — a deliberate amendment to `43-UI-SPEC.md`'s
  Copywriting Contract ("No third variant is ever returned").
- **D-15:** The reset reports per-fixture progress (`seeding justices → fixture 2 of 4`).
- **D-16:** The justice seed runs after the TRUNCATE and before the corpus reseed, per
  `.planning/notes/justice-identity-and-seeding.md`.
- **D-17:** The per-writer tier recompute optimisation is out of scope (belongs to Phase 54).

### Claude's Discretion

- Which name form feeds the initials — measured: identical for all 114 justices once
  suffixes are skipped. Pick whichever is cleaner.
- The five dual-service justices (Rutledge, E.D. White, Hughes, Stone, Rehnquist) — both CSV
  passes must land the same `oyez_speaker_id` on the same row without tripping the partial
  unique index.
- Trivial-ACCEPT provenance restamp — gate each restamp on `_values_differ` so a byte-identical
  re-seed can't demote an OPERATOR-stamped row to `seed`.
- Stale `created_at` in `reset_to_fixture` (folded todo, Claude's per Defect Policy).
- Converging the two initials helpers (`SpeakerPopover.svelte:57`, `+page.svelte:181`).
- `import_convokit::_resolve_person` needs no change — confirmed this session by reading it.
- Naming collision awareness: `display_name` already exists in `api/schemas/admin_review.py:53`
  for an unrelated DTO concept — not a blocker, do not conflate.

### Deferred Ideas (OUT OF SCOPE)

- Per-writer tier recompute during bulk reseed — belongs with Phase 54 (bulk publish).
- Extending the corpus past 2019 so Barrett and Jackson resolve — not a v1.9 concern.
- Search over speaker names (Phase 55), bulk publish (Phase 54), the PDF pipeline path
  (Phase 999.11), and any backfill migration of existing duplicate rows (the reseed clears
  them, per reseed-don't-migrate).
- Twelve further todos matched Phase 52 on keyword overlap alone and were reviewed and left
  pending — none touch justice identity, the people schema, or `reset_to_fixture` (full list
  in `52-CONTEXT.md`'s Deferred Ideas section).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| JUSTICE-01 | A verified per-justice mapping joins the CSV tenure data to the corpus by `oyez_speaker_id`, covering all 114 corpus justices, stored as data rather than derived by name matching | See "Architecture Patterns" data-flow diagram and the draft-vs-shipped column-shape mismatch called out in the Summary; `data/corpus/justice_identity_mapping.csv` (D-06/D-07/D-08) is the artifact |
| JUSTICE-02 | `import_justices_csv` writes `oyez_speaker_id` from that mapping, so `import_convokit::_resolve_person` matches on its first and preferred key | See Code Examples (current dedup lookup, line 272-275) and confirmed-no-change `_resolve_person` (already prefers `oyez_speaker_id`, line 1756) |
| JUSTICE-03 | A `people.display_name` column carries the corpus name form; the bio card shows `full_name`, utterance attribution shows `display_name`, falling back to `full_name` when null | See Standard Stack (migration pattern), Code Examples (`arguments.py:242` COALESCE), Pitfall 3 (which schemas carry which field) |
| JUSTICE-04 | `reset_to_fixture` seeds all justices after its TRUNCATE, so they persist through every fixture reset | See Runtime State Inventory and Code Examples (`admin_dev.py:228-235` insertion point) |
| JUSTICE-05 | A partial unique index on `people.oyez_speaker_id` makes duplicate justice rows structurally impossible | See "Partial unique index syntax" in Architecture Patterns — no in-repo precedent exists, syntax cross-checked via web search |
| JUSTICE-06 | Avatar initials derive from first and last name, skipping suffixes | See Code Examples (current bug reproduction, both call sites verified byte-identical) and Pitfall 3 |
</phase_requirements>

## Summary

This phase has almost no external-library surface — it is a schema change (one nullable
column, one partial unique index), a join-key change in one already-present-but-unused
column (`oyez_speaker_id`), a data artifact promotion (draft CSV -> verified CSV), and a
handful of precisely located code edits in files this research read directly. Every claim
below about "where X lives" and "what X does today" is grounded in the actual source read
this session, not in the CONTEXT.md's own paraphrase of it — CONTEXT.md's code citations
were independently re-verified and are accurate down to the exact `select()` call shapes.

The one area that is **not** already fully designed by CONTEXT.md/the design note and needs
a planning decision is the D-14 "re-read fixture state" mechanism: no existing endpoint
does the check the amended error-copy contract needs, and this research surfaces that gap
explicitly rather than inventing an endpoint shape research shouldn't own.

The other thing this research adds beyond CONTEXT.md: the **draft mapping CSV's own column
shape does not match the shipped artifact's column shape**. `justice-identity-mapping-DRAFT.csv`
has `oyez_speaker_id,corpus_display_name,csv_full_name,confidence` (a reconstructed
`full_name` string, no split parts, a `confidence` column). D-06/D-07/D-08 require
`data/corpus/justice_identity_mapping.csv` to instead carry explicit `first_name` /
`middle_name` / `last_name` / `name_suffix` columns matching the source CSV's own headers,
and to drop `confidence` entirely. Promoting the draft is therefore not a copy — it is a
reshape, and the 4 resolved rows' `csv_full_name` ambiguity (`"John Marshall Harlan | John
Marshall Harlan, II"`) has to be split into the correct one of the two candidate part-sets
per D-01's own table.

**Primary recommendation:** Treat this as five independent, sequenceable changes — (1) a new
Alembic migration adding `people.display_name` + the partial unique index on
`oyez_speaker_id`, (2) the mapping CSV reshape + verification script/test, (3) the
`import_justices_csv.py` dedup-key and write-path change, (4) the `COALESCE` in
`arguments.py` + the two new admin-page read-only fields + the two new schema fields for
initials, (5) the `reset_to_fixture` seed-step insertion + the D-14/D-15 UI-SPEC amendment
— and plan each as its own task/wave, because they touch disjoint files with only the
migration as a shared dependency.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Verified justice mapping (JUSTICE-01) | Data (`data/corpus/*.csv`) | Pipeline (verification script/test) | A CSV is data; a structural test reading it belongs in `pipeline/tests` next to the importer it feeds |
| `oyez_speaker_id`/`display_name` write path (JUSTICE-02/03) | Pipeline (`import_justices_csv.py`) | — | Already the sole writer of justice `Person` rows |
| Partial unique index (JUSTICE-05) | Database / Migrations | — | Alembic is the sole DDL authority per CLAUDE.md |
| `reset_to_fixture` seed step (JUSTICE-04) | API / Backend (`api/services/admin_dev.py`) | — | Already owns TRUNCATE + reseed orchestration |
| Utterance attribution COALESCE (JUSTICE-03) | API / Backend (`api/services/arguments.py`) | — | Already the sole `speaker_name` projection point for the public transcript |
| Admin read-only Identity fields (D-09/D-10) | Frontend Server (SSR) + API schema | Browser (markup) | `PersonDetail`/`PersonUpdate` schemas gate what's writable; the Svelte page only renders |
| Avatar initials (JUSTICE-06) | API / Backend (new computed field) | Browser (renders the field, stops computing) | D-12 explicitly moves the computation server-side; browser tier becomes a pure consumer |
| Reset error-copy re-read (D-14) | API / Backend (needs a new or reused read) | Frontend Server (SSR action) | The re-read is a data question the backend must answer; the action only relays it |

## Package Legitimacy Audit

Not applicable — this phase introduces no new external package in any ecosystem. Every
change is to first-party code (`api/`, `pipeline/`, `app/`, `alembic/`) or to a data file
(`data/corpus/justice_identity_mapping.csv`). `npm view` / `pip index versions` checks were
not run because there is nothing to check.

## Standard Stack

No new dependency. Confirmed versions already pinned in this repo, verified by reading the
installed environment directly this session:

| Library | Version | Purpose | Provenance |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.52 | ORM + `Index(..., postgresql_where=...)` for the partial unique index | `[VERIFIED: .venv/lib/python3.12/site-packages, sqlalchemy.__version__ printed this session]` |
| Alembic | (repo's pinned version, already the sole DDL authority per CLAUDE.md) | migration authoring | `[CITED: alembic/versions/0031_argument_slug.py — the immediately-prior migration, read this session]` |
| Pydantic v2 | already in use (`ConfigDict(extra="forbid")` confirmed in `PersonUpdate`) | schema validation | `[VERIFIED: api/schemas/admin_people.py:260, read this session]` |

**Installation:** none — no `pip install` / `npm install` needed for this phase.

## Architecture Patterns

### Data flow (identity resolution)

```
data/corpus/supreme_court_justices_sections.csv (source, untouched, D-06)
                │
                ▼
data/corpus/justice_identity_mapping.csv  (NEW, D-06 — 114 rows,
   first_name/middle_name/last_name/name_suffix + oyez_speaker_id +
   corpus_display_name; no confidence column, D-08)
                │
                ▼
pipeline/commands/import_justices_csv.py::run_import_justices_csv
   — looked up TODAY by Person.full_name (line 272-275);
     MUST become a lookup keyed on oyez_speaker_id from the mapping
   — writes oyez_speaker_id + display_name on both the create branch
     (line ~396-409) and the upgrade-in-place branch (line ~277-391)
                │
                ▼
people.oyez_speaker_id  (String(100), nullable, NO unique constraint today —
   migration 0017 added the column bare; THIS phase's migration adds the
   partial unique index, JUSTICE-05)
                │
                ▼
pipeline/commands/import_convokit.py::_resolve_person (line 1733-1782)
   — ALREADY checks oyez_speaker_id FIRST (line 1756), full_name SECOND
     (line 1764) — NO CHANGE NEEDED, confirmed by reading the function body
                │
                ▼
api/services/arguments.py:242 — Person.full_name.label("speaker_name")
   MUST become func.coalesce(Person.display_name, Person.full_name)
   (func already imported at arguments.py:17)
```

### Pattern 1: Blank-only prefill through the authority ladder (already established, reuse verbatim)

**What:** every write to an existing `Person` row inside `import_justices_csv.py`'s upgrade
branch goes through `apply_person_value_change` (from `api/services/admin_review.py`) with
`incoming_source=ImportSource.SEED.value`, and the caller only applies the value when the
decision is `ACCEPT`/`ACCEPT_AND_RECORD`.
**When to use:** for any new field this phase makes the importer able to update on an
existing row post-creation (in practice, `display_name` on a rerun — see Pitfall 2 below).
**Example (verified, `pipeline/commands/import_justices_csv.py:308-319`):**
```python
if prepared.first_name is not None:
    decision = await apply_person_value_change(
        session,
        person=person,
        field="first_name",
        incoming_value=prepared.first_name,
        incoming_source=ImportSource.SEED.value,
        incoming_method=ImportMethod.DIRECT.value,
        import_run_id=None,
    )
    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
        setattr(person, "first_name", prepared.first_name)
```
`[VERIFIED: pipeline/commands/import_justices_csv.py:308-319]`

### Pattern 2: Nullable-column + unique-constraint migration (established precedent, 0031)

**What:** the immediately-prior migration (0031) added exactly one nullable column plus its
unique constraint in one migration, with an explicit downgrade, matching the shape this
phase's `display_name` + partial-unique-index migration needs.
**Example (verified, `alembic/versions/0031_argument_slug.py` docstring, read this session):**
> "Adds ONE new nullable column and its unique constraint: `arguments.slug` — sa.String(200),
> nullable, UNIQUE (constraint name `uq_arguments_slug`)... Nullable (not NOT NULL) because
> this project reseeds rather than migrates data."
`[VERIFIED: alembic/versions/0031_argument_slug.py:1-15]`

### Partial unique index syntax (JUSTICE-05)

No partial-index precedent exists yet in this repo's `alembic/versions/` — grep across all
32 migrations found zero `postgresql_where` usages. The syntax itself is a well-documented
SQLAlchemy/Alembic feature:

```python
# Source: SQLAlchemy postgresql dialect docs, cross-checked via web search this session
op.create_index(
    "uq_people_oyez_speaker_id",
    "people",
    ["oyez_speaker_id"],
    unique=True,
    postgresql_where=sa.text("oyez_speaker_id IS NOT NULL"),
)
```
`[CITED: sqlalchemy.org postgresql dialect docs / alembic issue tracker discussion of postgresql_where, web search this session]` —
the `IS NOT NULL` predicate is what makes D-04's NULL-`oyez_speaker_id` rows (Barrett,
Jackson) exempt from the constraint while still making a genuine duplicate impossible
(Success Criterion 4).

### Recommended file-level task boundaries

```
alembic/versions/003X_person_display_name_and_oyez_unique.py   # NEW migration
api/models/models.py                                            # + display_name column
data/corpus/justice_identity_mapping.csv                         # NEW data artifact (D-06)
pipeline/commands/import_justices_csv.py                        # dedup key + write path
pipeline/tests/test_import_justices_csv.py                      # update dedup tests (see Pitfall 1)
NEW: pipeline/tests/test_justice_identity_mapping.py (or similar) # D-02's structural test
api/services/arguments.py                                       # COALESCE at line 242
api/schemas/admin_people.py                                     # PersonDetail + 2 new fields
api/schemas/speakers.py + api/schemas/utterance.py               # + initials field (D-12)
api/domain/person_names.py (or a new module)                    # initials derivation, D-12/D-13
app/src/lib/public/SpeakerPopover.svelte                        # stop computing, consume field
app/src/routes/arguments/[slug]/+page.svelte                    # stop computing, consume field
app/src/routes/admin/people/[id]/+page.svelte + +page.server.ts # 2 new read-only fields
api/services/admin_dev.py                                       # justice seed step + D-15 progress
app/src/routes/admin/+page.server.ts                            # D-14 error-copy amendment
```

### Anti-Patterns to Avoid

- **Do not touch `import_convokit.py::_resolve_person`.** It already prefers
  `oyez_speaker_id` (verified, line 1756) — the CONTEXT.md's "no change needed" claim is
  correct. Any plan task that proposes editing this function's identity-lookup order is
  solving an already-solved problem.
- **Do not derive the mapping from a name-matching rule.** Already rejected (88% accuracy,
  documented in `.planning/notes/justice-identity-and-seeding.md`). The verification script/
  test this phase adds is a **check on a hand-verified artifact** (D-02), never a re-derivation.
- **Do not add `display_name` or `oyez_speaker_id` to `PersonUpdate`'s allow-list.** `extra="forbid"`
  is verified live at `api/schemas/admin_people.py:260`; adding either field there defeats
  D-09/D-10's read-only intent and would let a re-seed silently collide with an operator PATCH.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deciding whether a re-run write overwrites an operator edit | A new authority check | `api.domain.authority.decide_write` / `api.services.admin_review.apply_person_value_change` | Already the project's one authority ladder; the importer already calls it at 4 sites for name parts — extend the same call pattern for `display_name`, don't invent a second gate |
| Partial-unique-index enforcement in application code | A pre-INSERT `SELECT ... WHERE oyez_speaker_id = ...` existence check in Python | The Postgres partial unique index itself (JUSTICE-05's own point) | Success Criterion 4 explicitly requires "refused by the database itself, not only by application code" — an app-level check alone does not satisfy this requirement even if functionally equivalent under normal load |
| Splitting a full name into parts for initials | A third bespoke string-splitter | `api.domain.person_names._KNOWN_SUFFIXES` + structured `first_name`/`last_name` columns already on `Person` | The two existing client-side splitters (`SpeakerPopover.svelte:57`, `+page.svelte:181`) are exactly this anti-pattern, and are what produced the `JI` bug — D-12 replaces both with one server computation, do not add a third variant anywhere |

**Key insight:** Every piece of machinery this phase needs except the partial index and the
`display_name` column already exists in the codebase and has already been exercised by prior
phases (authority ladder, blank-only prefill, `oyez_speaker_id`-first resolution). The work
is almost entirely "flip the dedup key and wire two new columns through," not "design a new
subsystem."

## Runtime State Inventory

This phase is not a rename/refactor/migration of an existing identifier, so the standard
five-category audit doesn't directly apply — but D-16 through D-17 concern
`reset_to_fixture`, which **is** exactly the kind of "what runtime state resets and what
doesn't" question this section exists for. Answering it explicitly:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `people` and `court_tenures` rows are TRUNCATE'd by `reset_to_fixture` (`TRUNCATE_SQL`, `api/services/admin_dev.py:142-154`) — verified, both tables named explicitly | Add a justice-seed call (`run_import_justices_csv`) after the TRUNCATE, before the four-fixture reseed loop (D-16) |
| Live service config | None — this phase touches no n8n/Datadog/Tailscale-style out-of-git config | None |
| OS-registered state | None | None |
| Secrets/env vars | None — no new env var; `DEFAULT_CSV_PATH` (`pipeline/commands/import_justices_csv.py:85`) is a repo-relative path, not env-configured | None |
| Build artifacts | None — no compiled/installed artifact carries `oyez_speaker_id` or `display_name` | None |

One item the standard five categories don't name but is load-bearing here: **the
`speaker_alias` table is CASCADE'd by the same TRUNCATE and deliberately not restored** —
this is pre-existing behavior (verified comment, `api/services/admin_dev.py:135-141`), not
something this phase introduces or must fix, but a plan task touching this file should not
"helpfully" restore it, since that comment documents it as an intentional, separately-scoped gap.

## Common Pitfalls

### Pitfall 1: The existing `test_import_justices_csv.py` dedup tests assert `full_name`-keyed behavior

**What goes wrong:** `pipeline/tests/test_import_justices_csv.py` (1391 lines, verified) has
tests like `test_upgrades_existing_person_in_place`, `test_idempotent_rerun_creates_no_duplicates`,
and `test_rerun_last_name_operator_edited_to_different_value_survives` that construct existing
`Person` rows and rely on `full_name` string equality to trigger the upgrade branch. Once the
dedup key changes to `oyez_speaker_id`-from-mapping, these tests' setup (`Person(full_name=...)`
with no `oyez_speaker_id`) will silently take the CREATE branch instead of UPGRADE, and several
will start failing for a reason unrelated to what they're meant to test.
**Why it happens:** `select(Person).where(Person.full_name == full_name)` (verified, line
272-275) is the literal statement being replaced.
**How to avoid:** Every existing test in this file that constructs a "pre-existing person to
be upgraded" fixture must be updated to seed `oyez_speaker_id` on that fixture, matching the
new lookup key — this is mechanical but touches ~15 test functions, not a small tail risk.
**Warning signs:** a green `test_idempotent_rerun_creates_no_duplicates` today does not mean
it will still test idempotency correctly after the key change; re-read each test's fixture
setup, don't just trust the name.

### Pitfall 2: `display_name` needs its own blank-only-prefill decision on rerun, and CONTEXT.md doesn't spell out which branch it belongs in

**What goes wrong:** The design note and CONTEXT.md establish that `import_justices_csv.py`
writes `oyez_speaker_id` + `display_name` "from the mapping," but the existing upgrade branch
(lines 277-391) is entirely built around name-PART fields going through
`apply_person_value_change` one at a time. `display_name` is a single corpus-sourced string
with no "part" decomposition — it needs its own `apply_person_value_change` call (or a
simpler blank-only write, since D-09 makes it read-only everywhere in the API layer, meaning
no operator edit can ever outrank a reseed) sited correctly relative to the other four field
writes.
**Why it happens:** the design note pre-dates the D-09 "read-only, not in `PersonUpdate`"
decision — since no operator can ever hand-edit `display_name`, the authority ladder's whole
purpose (protecting an operator edit from a reseed) has no adversary to protect against here,
which is a legitimate reason to make this one field's write simpler (plain blank-only, or
even always-set-from-mapping) than the name-part precedent it superficially resembles.
**How to avoid:** treat this as a discretion point for the plan to resolve explicitly, not
silently copy the name-part call shape without asking whether the ladder call is doing
anything for a field nobody can ever operator-edit.
**Warning signs:** a plan that adds a `display_name` authority-ladder call identical to the
name-part ones without explaining why an unwritable field needs write-conflict arbitration.

### Pitfall 3: `speaker.name` in the transcript roster is NOT the same field as `speaker.full_name` in the popover

**What goes wrong:** the two `getInitials` call sites operate on two different fields
end-to-end: `+page.svelte`'s roster builds `{ name: key }` where `key` is `u.speaker_name`
(from `UtteranceResponse.speaker_name`, driven by `arguments.py:242`'s soon-to-be-COALESCE
value), while `SpeakerPopover.svelte`'s `initials` derivation reads `speaker.full_name`
directly (from `SpeakerPopoverEntry.full_name`, which per JUSTICE-03/D-11 stays the CSV's
fuller form, unchanged). A plan that assumes "one shared `SpeakerDetail`/roster type" can
accidentally wire the new server-computed `initials` field onto only one of the two schemas
and miss the other, silently leaving one of the two `getInitials` call sites broken.
**Why it happens:** `SpeakerDetail` (the shared frontend type, `app/src/lib/types/speaker.ts`)
backs the popover only; the roster in `+page.svelte` is a locally-built `{name, role,
person_id}[]` derived from utterances, not from `SpeakerDetail` at all.
**How to avoid:** the two public schemas gaining an `initials` field per D-12 are, by this
research's reading, `SpeakerPopoverEntry` (`api/schemas/speakers.py`) and `UtteranceResponse`
(`api/schemas/utterance.py`) — verify this pairing explicitly during planning rather than
assuming a single shared schema covers both call sites.
**Warning signs:** a plan task titled "add initials field to SpeakerDetail" that doesn't also
touch `UtteranceResponse`/the roster-building code in `+page.svelte`.

### Pitfall 4: No existing endpoint performs the D-14 "re-read fixture state" check

**What goes wrong:** D-14 requires the frontend `resetToFixture` action to, on any failure,
"re-read fixture state before asserting anything" and choose among three failure-shaped
outcomes plus a fourth (silent full-success) outcome. The only read surfaces that exist today
are `GET /api/admin/arguments` (no `oyez_transcript_id`/conversation-id filter param,
verified) and `GET /api/admin/people` variants (irrelevant to fixture state). Nothing today
lets the frontend action ask "did all 4 `FIXTURE_SET` conversations land, in the states
`reset_to_fixture` was trying to put them in?" the way `reset_to_fixture` itself checks
internally (`select(Argument).where(Argument.oyez_transcript_id == conversation_id)`,
verified, line 267-270).
**Why it happens:** this check has only ever needed to exist inside the same request/
transaction that just performed the write; nothing has needed to ask the question from a
separate, later request before.
**How to avoid:** this is a genuine open design point for the plan, not a research gap to
paper over — the plan must decide whether to (a) add a new dev-only GET endpoint
(`/api/admin/dev/reset-to-fixture/status` or similar) that re-runs the same 4-conversation
existence+state check `reset_to_fixture` does internally, or (b) reuse
`GET /api/admin/arguments` and filter client-side by the 4 known `case_name` values from
`FIXTURE_SET` (fragile — case names are display strings, not identifiers). Option (a) matches
the existing pattern of a dedicated, narrowly-scoped dev-only endpoint (`admin_dev.py`
already has exactly this shape for `reset-to-fixture` and `seed-unresolved-speaker`).
**Warning signs:** a plan that hand-waves the re-read as "call the reset endpoint again" —
re-running `reset_to_fixture` is itself another destructive TRUNCATE, not a read, and cannot
be what D-14 means.

### Pitfall 5: The frontend `PersonDetail` type in `+page.server.ts` is a hand-maintained duplicate of the API schema

**What goes wrong:** `app/src/routes/admin/people/[id]/+page.server.ts` declares its own
local `interface PersonDetail` (verified, lines 22-65) that mirrors — but does not import
from — `api/schemas/admin_people.py::PersonDetail`. Adding `display_name`/`oyez_speaker_id`
to the Pydantic schema without also adding them to this TypeScript interface means the
Svelte page's `data.person.display_name` is `undefined` at the type level even though the
JSON payload carries the value, or (worse, if using `any`) a silent runtime access with no
compile-time signal.
**Why it happens:** SvelteKit's `+page.server.ts` re-declares response shapes locally; there
is no shared-type codegen between FastAPI and SvelteKit in this repo.
**How to avoid:** treat "add 2 fields to the API schema" and "add 2 fields to the local
TypeScript interface" as two line items in the same task, not one.
**Warning signs:** a plan task scoped only to `api/schemas/admin_people.py` for D-09/D-10,
with no corresponding `+page.server.ts` edit.

## Code Examples

### Current dedup lookup (the exact code JUSTICE-01/02 changes)

```python
# Source: pipeline/commands/import_justices_csv.py:272-275 (verified, read this session)
result = await session.execute(
    select(Person).where(Person.full_name == full_name)
)
person = result.scalar_one_or_none()
```

### Current `_resolve_person` (the exact code that needs NO change, per D-13's discretion note — verified)

```python
# Source: pipeline/commands/import_convokit.py:1755-1771 (verified, read this session)
result = await session.execute(
    select(Person).where(Person.oyez_speaker_id == speaker_id)
)
person = result.scalar_one_or_none()
if person is not None:
    await _apply_extracted_name_provenance(session, person, person.full_name)
    counters["people_matched"] = counters.get("people_matched", 0) + 1
    return person

result = await session.execute(select(Person).where(Person.full_name == full_name))
person = result.scalar_one_or_none()
if person is not None:
    if person.oyez_speaker_id is None:
        person.oyez_speaker_id = speaker_id  # D-11 backfill
    ...
```

### Current utterance attribution query (the exact line JUSTICE-03 changes)

```python
# Source: api/services/arguments.py:242 (verified, read this session; func imported at line 17)
select(
    Utterance,
    Person.full_name.label("speaker_name"),
    Role.name.label("speaker_role"),
)
.outerjoin(Person, Utterance.person_id == Person.id)
.outerjoin(Role, Person.role_id == Role.id)
```
Becomes `func.coalesce(Person.display_name, Person.full_name).label("speaker_name")`.

### Current avatar-initials bug (the exact code JUSTICE-06 replaces, both call sites verified byte-identical)

```javascript
// Source: app/src/lib/public/SpeakerPopover.svelte:57-61 (verified)
// and app/src/routes/arguments/[slug]/+page.svelte:181-186 (verified, identical logic)
const parts = speaker.full_name.trim().split(/\s+/).filter(Boolean);
if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
return '?';
```
For `"John Marshall Harlan, II"`: `parts = ["John","Marshall","Harlan,","II"]` →
`parts[0][0]="J"`, `parts[3][0]="I"` → `"JI"`. This is the exact, verified mechanism of the
bug JUSTICE-06 names.

### Known suffix set the initials logic should reuse (verified, exact line)

```python
# Source: api/domain/person_names.py:234 (verified, read this session)
_KNOWN_SUFFIXES = {"Jr.", "Sr.", "II", "III", "IV"}
```

### Admin page insertion point for the two new read-only fields (D-09/D-10)

```svelte
<!-- Source: app/src/routes/admin/people/[id]/+page.svelte:383-389 (verified) -->
<output
    id="full_name_preview"
    aria-labelledby="full_name_label full_name_explanation"
    aria-live="polite"
    style="..."
>{fullNamePreview}</output>
<!-- NEW fields go here, immediately after this closing </div> (line ~389) and
     before the "Name parts" grid div (line ~391/402) -->
```

### Existing frontend `PersonDetail` interface needing the same 2 fields (D-09/D-10, Pitfall 5)

```typescript
// Source: app/src/routes/admin/people/[id]/+page.server.ts:22-65 (verified)
interface PersonDetail {
    id: number;
    full_name: string;
    // ... existing fields ...
    review_state: string;
    provenance_metadata: { ... } | null;
    // display_name: string | null;         <- NEW, D-09
    // oyez_speaker_id: string | null;       <- NEW, D-10
}
```

### `reset_to_fixture`'s exact TRUNCATE + insertion point for the justice seed (D-16)

```python
# Source: api/services/admin_dev.py:228-235 (verified)
resolved_corpus_dir = Path(corpus_dir) if corpus_dir else DEFAULT_CORPUS_DIR
_require_corpus_files(resolved_corpus_dir)

await db.execute(text(TRUNCATE_SQL))
await db.commit()
# <- D-16: justice seed step goes here, before the FIXTURE_SET reseed loop below
```

`run_import_justices_csv` takes an `args`-shaped object (verified,
`pipeline/commands/import_justices_csv.py:204-222`: `args.csv` optional attribute, defaults
to `DEFAULT_CSV_PATH`) — the same `SimpleNamespace(...)` call convention `reset_to_fixture`
already uses for `run_import_convokit` (verified, line 246-251) is the established pattern to
reuse here, e.g. `await run_import_justices_csv(SimpleNamespace(csv=None))` if the mapping
path stays at its default, or explicitly passing the new mapping CSV path if the importer's
signature grows a second path argument for the mapping file (a planning decision — see Open
Questions).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Dedup justices by exact `Person.full_name` string match | Dedup by `oyez_speaker_id` from a verified mapping | This phase (JUSTICE-01/02) | Eliminates the 49-of-114 duplicate-row defect at its root, not just for the 4 previously-visible cases |
| Client-side name-string-splitting for avatar initials (2 independent copies) | Server-computed `initials` field on 2 public schemas | This phase (JUSTICE-06, D-12) | Fixes `JI` -> `JH`; removes a class of bug (a third splitter cannot be added by accident later) |
| `reset_to_fixture` silently drops all justices | Justice roster persists through every reset | This phase (JUSTICE-04) | People directory shows the full bench after a reset, not an empty one |

**Deprecated/outdated:** The rejected first-initial derivation rule
(`Byron Raymond White` -> `Byron R. White`, 100/114 correct) is not "deprecated" so much as
never adopted — CONTEXT.md is explicit that re-litigating it is out of scope for this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The two public schemas D-12 adds an `initials` field to are `SpeakerPopoverEntry` (`api/schemas/speakers.py`) and `UtteranceResponse` (`api/schemas/utterance.py`) | Pitfall 3, Code Examples | If wrong, one of the two frontend call sites (`SpeakerPopover.svelte` or the `+page.svelte` roster) doesn't receive the new field and keeps computing initials client-side, silently leaving half the JUSTICE-06 fix undone |
| A2 | `display_name`'s write on a rerun should be a simpler blank-only assignment rather than a full `apply_person_value_change` authority-ladder call, since D-09 makes the field un-operator-editable everywhere | Pitfall 2 | Low risk either way functionally (both converge on the same stored value in practice), but affects code consistency/readability; worth an explicit planning decision rather than silent copy-paste |
| A3 | The D-14 re-read mechanism should be a new dev-only GET endpoint mirroring `reset_to_fixture`'s own internal existence+state check, rather than reusing `GET /api/admin/arguments` | Pitfall 4 | If the plan instead tries to reuse `/arguments` and filter by case name client-side, it inherits a fragile, non-identifier-based match; a new endpoint is more code but structurally correct |
| A4 | `run_import_justices_csv`'s signature will need to accept (or default to) the new mapping CSV path in addition to the existing tenure-data CSV path | Code Examples (reset_to_fixture insertion), Architecture Patterns | If the importer instead reads the mapping path from a fixed module-level constant (mirroring `DEFAULT_CSV_PATH`'s own pattern) rather than a second `args` attribute, the `reset_to_fixture` call site doesn't need to change at all — this is a genuinely open, low-risk implementation choice |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **What shape does the D-14 re-read take?**
   - What we know: no existing endpoint answers "did all 4 FIXTURE_SET conversations land in
     their expected post-reset state," and `reset_to_fixture`'s own internal check
     (`select(Argument).where(Argument.oyez_transcript_id == conversation_id)`) is the
     nearest existing logic to reuse.
   - What's unclear: whether the plan adds a new dev-only GET endpoint, exposes a slimmer
     read-only variant of the same check, or takes a different approach entirely.
   - Recommendation: add a narrowly-scoped new endpoint under `api/routers/admin_dev.py`
     (matching its existing pattern of two narrow dev-only POST endpoints) rather than
     retrofitting a general-purpose admin endpoint for this one-off need.

2. **Does `run_import_justices_csv` need a second CSV-path argument, or does the mapping
   file get its own `DEFAULT_MAPPING_CSV_PATH` constant?**
   - What we know: `DEFAULT_CSV_PATH` (line 85) is the existing single-constant pattern for
     the tenure-data CSV; D-06 explicitly calls the new mapping file's path pattern-matching
     of that same convention.
   - What's unclear: whether the importer takes one CSV or two, and whether both are
     override-able from `args` the way the existing `--csv` flag works.
   - Recommendation: mirror the existing pattern exactly — a second `DEFAULT_MAPPING_CSV_PATH`
     module constant plus an optional `args.mapping_csv` attribute, consistent with how
     `args.csv` already works.

3. **Where does the D-02 structural verification test live?**
   - What we know: it needs to read both the source CSV and the new mapping CSV and assert
     the oyez_speaker_id / corpus form / CSV name-parts agree structurally for the 38
     mechanically-checkable `derived` rows.
   - What's unclear: whether this is a `pipeline/tests/test_*.py` (runs under pytest, part of
     the normal suite) or a standalone one-off verification script run once during planning/
     execution and not kept as a permanent regression test.
   - Recommendation: per this project's Testing Policy ("tests exist to catch regressions"),
     keep it as a permanent `pipeline/tests/test_justice_identity_mapping.py` — a future
     accidental edit to the mapping CSV (e.g. a typo'd `oyez_speaker_id`) is exactly the kind
     of regression this suite exists to catch, and the file is small enough that re-running
     the check costs nothing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 venv | migrations, pipeline, tests | Yes | 3.12 (`.venv/bin/python3.12` present) | — |
| SQLAlchemy 2.0 | models, migration | Yes | 2.0.52, verified via `sqlalchemy.__version__` | — |
| PostgreSQL | migration apply, tests | Not directly probed this session (`pg_isready` not on PATH in this shell; `.env`/`DATABASE_URL` is a protected secret file, not read) | — | Existing dev DB usage is already established by the passing test suite in prior phases; no new infra needed |
| node (for `svelte-check` / frontend build) | frontend edits | Assumed present per project MEMORY note ("export the nvm bin dir before any gsd-tools call") | — | — |

**Missing dependencies with no fallback:** none identified — this phase adds no new
external dependency.

**Missing dependencies with fallback:** PostgreSQL reachability was not directly probed in
this research session (tooling/secret-guard constraints); this is a pre-existing, already-
working piece of dev infrastructure per the rest of the test suite and needs no phase-specific
verification here.

<!-- Validation Architecture section omitted: .planning/config.json workflow.nyquist_validation is explicitly false -->

<!-- Security Domain section omitted: .planning/config.json workflow.security_enforcement is explicitly false -->

## Sources

### Primary (HIGH confidence — read directly this session)
- `api/models/models.py` (Person model, full class body) — no `display_name` column exists
  today; `oyez_speaker_id` exists nullable with no unique constraint
- `alembic/versions/0017_add_oyez_external_ids.py` — original bare-column addition
- `alembic/versions/0031_argument_slug.py` — nullable-column + unique-constraint precedent
- `pipeline/commands/import_justices_csv.py` (full read, lines 1-472) — dedup lookup, create/
  upgrade branches, `run_import_justices_csv` signature
- `pipeline/commands/import_convokit.py` (`_resolve_person`, `_lookup_person_readonly`,
  lines 1700-1815) — confirmed no-change claim
- `api/services/admin_dev.py` (full `reset_to_fixture`, `TRUNCATE_SQL`, `FIXTURE_SET`) —
  TRUNCATE scope, insertion point, existing comments on `speaker_alias` non-restoration
- `api/services/arguments.py:220-260` — exact `speaker_name` query to COALESCE
- `api/domain/person_names.py` (`format_full_name`, `prepare_person_name`,
  `split_legacy_full_name`, `_KNOWN_SUFFIXES`) — suffix set, canonical formatting
- `api/schemas/admin_people.py` (`PersonDetail`, `PersonUpdate`) — confirmed missing fields,
  confirmed `extra="forbid"`
- `api/schemas/speakers.py`, `api/schemas/utterance.py` — confirmed current field sets
- `app/src/lib/public/SpeakerPopover.svelte`, `app/src/routes/arguments/[slug]/+page.svelte`,
  `app/src/lib/types/speaker.ts` — both initials implementations, confirmed byte-identical
  logic, confirmed which schema backs which call site
- `app/src/routes/admin/people/[id]/+page.svelte`, `+page.server.ts` — insertion point,
  local `PersonDetail` TS interface
- `app/src/routes/admin/+page.server.ts` — `resetToFixture` action, `RESET_MID_ERROR`/
  `RESET_ENV_ERROR` literals
- `api/routers/admin_dev.py`, `api/routers/admin.py` — confirmed no existing "read fixture
  state" endpoint
- `.planning/notes/justice-identity-mapping-DRAFT.csv`, `data/corpus/supreme_court_justices_sections.csv`,
  `data/corpus/speakers.json` — exact column shapes, confirmed draft/target schema mismatch
- `pipeline/tests/test_import_justices_csv.py` — confirmed existing dedup-test fixture shapes
- `conftest.py`, `pytest.ini`, `.planning/config.json` — verified test/build commands
  (`./.venv/bin/python -m pytest`, `python3 -m compileall -q pipeline api scripts tests
  alembic`), `nyquist_validation: false`, `security_enforcement: false`

### Secondary (MEDIUM confidence)
- SQLAlchemy `postgresql_where` / partial-index syntax — web search this session, cross-
  checked against sqlalchemy.org dialect docs and an alembic issue-tracker discussion; no
  in-repo precedent exists to verify against directly

### Tertiary (LOW confidence)
- None — every claim in this document either traces to a file read this session or to a
  cross-checked web source; the Assumptions Log above captures the genuine open decisions
  instead of asserting them as fact.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency, all versions read from the live environment
- Architecture: HIGH — every integration point named in the phase description was opened
  and read this session; line numbers are current as of 2026-09-24
- Pitfalls: HIGH — each pitfall traces to a specific verified file/line, not a general
  category of risk

**Research date:** 2026-09-24
**Valid until:** 30 days (stable, internal-codebase research; re-verify line numbers if the
branch has moved significantly by execution time)
