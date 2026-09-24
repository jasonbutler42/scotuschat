# Phase 52: Justice Identity - Context

**Gathered:** 2026-09-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Every justice in the corpus resolves to exactly one `people` row, joined to the
corpus on a verified `oyez_speaker_id`, seeded through every `reset_to_fixture`,
with the corpus name form driving utterance attribution and the fuller CSV form
driving the bio card.

Closes the Person-dedup item carried since v1.7 Phase 42. It is not four bad
rows — it is 49 of 114, visible as four only because four fixtures are imported.

**In scope:** JUSTICE-01 through JUSTICE-06, plus three folded `reset_to_fixture`
todos (see Folded Todos).

**Out of scope:** search over speaker names (Phase 55), bulk publish (Phase 54),
the PDF pipeline path (Phase 999.11), and any backfill migration of existing
duplicate rows — the reseed clears them.

</domain>

<decisions>
## Implementation Decisions

### Mapping Verification

- **D-01:** The 4 rows the draft flagged as needing the operator are **resolved
  and accepted**, on the evidence of the CSV's own oath/termination dates rather
  than any name-matching heuristic:

  | `oyez_speaker_id` | corpus form | CSV row | evidence |
  |---|---|---|---|
  | `j__john_m_harlan` | `John M. Harlan` | `John,Marshall,Harlan,` | 1877-12-10 → 1911-10-14, the elder |
  | `j__john_m_harlan2` | `John M. Harlan II` | `John,Marshall,Harlan,II` | 1955-03-28 → 1971-09-23, the grandson |
  | `j__salmon_p_chase` | `Salmon P. Chase` | `Salmon,Portland,Chase,` | Chief 1864–1873 |
  | `j__brockholst_livingston` | `Henry Brockholst Livingston` | `Brockholst,,Livingston,` | 1807–1823 |

  `Samuel Chase` was never a genuine contest — he holds his own corpus id
  `j__samuel_chase` and his own CSV row (1796–1811), already matched `exact`.
  The other corpus Livingstons are advocates (`type: "A"`), not justices.
  **Do not re-open these four.** — **Reversibility:** reversible — a mapping row
  is one CSV line.

- **D-02:** The 45 `derived` rows are gated by **a mechanical structural test plus
  an operator spot-check**, not by a full 114-row manual read. 38 of the 45 are a
  plain middle-initial abbreviation and are fully covered by the test; the
  remaining 7 were presented to the operator and confirmed correct on 2026-09-24:
  `Harold Burton`, `Lucius Q.C. Lamar`, `Neil Gorsuch`, `Noah Swayne`,
  `Oliver W. Holmes, Jr.`, `Rufus Peckham`, `Stanley Reed`.

  The test asserts that the `oyez_speaker_id` slug, the corpus display form and
  the CSV first/last name agree structurally. This is a **check on a
  hand-verified artifact**, not a derivation rule — the rejected rule was
  rejected as a *source of truth*, and this does not revive it.

- **D-03:** Mapping coverage is verified complete: all 114 `j__`-prefixed
  speakers in `data/corpus/speakers.json` are mapped, with no unmapped ids and no
  mapping rows pointing at a non-existent speaker.

- **D-04:** `Amy Coney Barrett` and `Ketanji Brown Jackson` are seeded with
  **NULL `oyez_speaker_id` and NULL `display_name`**. They are in the CSV but
  seated in 2020 and 2022, after the ConvoKit corpus's 2019 cutoff. They appear
  in the admin People directory with zero arguments, like any justice whose cases
  are not imported. The partial unique index permits multiple NULLs, so nothing
  breaks; if the corpus is ever extended they resolve then.

- **D-05:** **Holmes: do not change his suffix in the CSV.** He was born `Jr.`
  but dropped it after his father died, before his time on the bench, so the
  CSV's `Oliver Wendell Holmes` is the historically right form for his tenure.
  His bio card reads `Oliver Wendell Holmes` and his utterances read
  `Oliver W. Holmes, Jr.` — each faithful to its own source, neither file edited.
  He is the **only** suffix disagreement across all 114 rows (verified by sweep;
  the Harlan row only appeared in the sweep because it still carried two
  unresolved candidates). *The operator initially chose to add the suffix and
  reversed that decision the same session — the reversal is the live decision.*

### Mapping Artifact

- **D-06:** The verified mapping lives at **`data/corpus/justice_identity_mapping.csv`**
  — a new file beside the source CSV, 114 rows. `supreme_court_justices_sections.csv`
  is **not** modified. This matches the importer's existing `DEFAULT_CSV_PATH`
  pattern and lets a future row be corrected without a code change or a
  migration. — **Reversibility:** costly — the importer, the reset seed step and
  the structural test all read this path.

- **D-07:** A mapping row joins its CSV justice by **explicit name parts**
  (`first_name` / `middle_name` / `last_name` / `name_suffix` matching the CSV's
  own columns), not by a reconstructed `full_name` string. This keeps the join
  independent of the Phase 38 `format_full_name` contract — a formatting change
  cannot silently break every row.

- **D-08:** The draft's `confidence` column (`exact` / `derived` / `AMBIGUOUS` /
  `UNRESOLVED`) is **dropped** from the shipped artifact. Once verified every row
  is equally authoritative, and a surviving `derived` label would misdescribe a
  row the operator has signed off on.

### Admin Surface

- **D-09:** `people.display_name` is **read-only** — visible on the admin person
  page so the operator can see which name form drives utterance attribution, but
  not writable. It is the corpus's word, exactly as `full_name` is the name
  parts' word. It is **not** added to `PersonUpdate`'s mass-assignment
  allow-list, so the Phase 38 D-01 discipline (`extra="forbid"`, a posted
  `full_name` gets a 422) stays intact and a re-seed can never collide with an
  operator edit.

- **D-10:** `people.oyez_speaker_id` becomes **visible and read-only** on the
  admin person page. It appears nowhere in the frontend today; it is now the
  load-bearing join key and the thing that makes a duplicate structurally
  impossible, so whether a row is corpus-joined should be legible at a glance —
  Barrett and Jackson would show blank.

- **D-11:** The admin People directory keeps listing **`full_name` only**, as
  today. `display_name` is a rendering detail for utterances, not an identity the
  directory needs to expose — and for 65 of 114 justices the two forms are
  identical.

### Avatar Initials (JUSTICE-06)

- **D-12:** Initials are computed **server-side from structured name parts** and
  shipped as a single field on the speaker payloads. The client stops parsing
  names — which is precisely what produced `JI` for `John Marshall Harlan, II`.
  One implementation, one place to test, replacing the two independent
  string-splitting helpers. — **Reversibility:** costly — adds a field to two
  public response schemas.

- **D-13:** When a person has **no structured parts**, fall back to the current
  first-token/last-token rule with known suffix tokens dropped. Justices always
  have parts (they come from the CSV), but `split_legacy_full_name`
  (`api/domain/person_names.py:269`) deliberately refuses three shapes — a suffix
  without a leading comma, a single-part name, and a particle name — so a
  corpus-resolved advocate can legitimately carry `full_name` and no parts. The
  fallback means no regression for anyone rendering correctly today.

### Reset to Fixture

- **D-14:** On **any** reset failure, the frontend action **re-reads fixture
  state before asserting anything** and reports what it actually found. The
  endpoint is dev-only and idempotent, so the verification read is cheap. This
  amends `43-UI-SPEC.md`'s Copywriting Contract ("No third variant is ever
  returned") to whatever state set the re-read produces — a **deliberate spec
  amendment**, which is why this was a todo rather than a drive-by edit. Today
  `RESET_MID_ERROR` asserts probable corruption for every failure mode including
  ones where the backend pre-flighted and deleted nothing.

- **D-15:** The reset reports **per-fixture progress**. The backend already
  iterates `FIXTURE_SET` in declaration order, so it can report
  `seeding justices → fixture 2 of 4`. The new justice seed step is itself a
  reported step. A measured real-corpus reset is 3m13s of database writes alone,
  and today that is indistinguishable from a hang.

- **D-16:** The justice seed runs **after the TRUNCATE and before the corpus
  reseed**, per `.planning/notes/justice-identity-and-seeding.md`.

- **D-17:** The per-writer tier recompute optimisation suggested by the
  timeout todo is **out of scope**. It is a publish-path performance question and
  Phase 54 is the bulk-publish phase. Measure the reset with the seed step added
  and carry the note forward.

### Claude's Discretion

Settled by correctness or measurement, not taste — handled without a checkpoint
per the Defect Policy:

- **Which name form feeds the initials.** Measured: for all 114 justices, initials
  computed from the corpus form and from the CSV form are **identical** once
  suffixes are skipped (zero differ). Not a decision — pick whichever is cleaner.
- **The five dual-service justices.** `John Rutledge`, `Edward Douglass White`,
  `Charles Evans Hughes`, `Harlan Fiske Stone` and `William H. Rehnquist` each
  appear **twice** in the CSV (Associate section and Chief section) — one person,
  two tenures, deduped today by exact `full_name`. Once the importer writes
  `oyez_speaker_id`, both passes must land the same id on the same row without
  tripping the new partial unique index.
- **Trivial-ACCEPT provenance restamp.** `decide_write` returns `ACCEPT` both for
  a genuine gap-fill and for a trivial agreement, and callers restamp
  `source`/`method` for both — so a byte-identical justice re-seed can demote an
  OPERATOR-stamped row to `seed`. Gate each restamp on `_values_differ`. Flagged
  in STATE.md as "relevant to Phase 52"; full write-up in the archived
  `49/deferred-items.md`.
- **Stale `created_at` in `reset_to_fixture`** (folded todo) — the reset reuses
  one transaction, so every row gets the transaction's start timestamp.
- **Converging the two initials helpers** — `SpeakerPopover.svelte:57` and
  `getInitials` in `arguments/[slug]/+page.svelte:181` (6 call sites) are
  independent copies of the same logic.
- **`import_convokit::_resolve_person` needs no change** — it already prefers
  `oyez_speaker_id`; that lookup simply starts hitting.
- **Naming collision awareness:** `display_name` already exists as a field name
  in `api/schemas/admin_review.py:53` for an unrelated DTO concept (a constituent
  label). Not a blocker; do not conflate them.

### Folded Todos

All three fold because this phase modifies `reset_to_fixture` and makes it slower
by adding a ~116-justice seed step.

- **`2026-08-20-reset-error-copy-overclaims-db-corruption.md`** (ui) — the reset
  failure message asserts possible DB corruption for every failure mode, including
  the backend's 503 corpus-missing case where the pre-flight ran before the
  TRUNCATE and nothing was deleted. Addressed by D-14.
- **`2026-08-20-reset-has-no-timeout-or-progress.md`** (ui) — a 3m13s destructive
  operation with no `AbortSignal`, inheriting undici's 300s `headersTimeout`, and
  no progress signal of any kind. Addressed by D-15; the seed step pushes the
  operation closer to that ceiling.
- **`2026-08-20-reset-to-fixture-stale-created-at-timestamps.md`** (api) — the
  reset reuses one transaction, so `created_at` values are stale. Claude's, per
  the Defect Policy.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase design — already settled, do NOT re-derive
- `.planning/notes/justice-identity-and-seeding.md` — the join-key decision, the
  49-of-114 name-mismatch measurement, why a derivation rule was rejected, the
  proposed schema and code changes. The authoritative design note for this phase.
- `.planning/notes/justice-identity-mapping-DRAFT.csv` — 114 rows, the input this
  phase verifies and promotes. **Not a deliverable**; `data/corpus/justice_identity_mapping.csv`
  is (D-06).

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — JUSTICE-01 through JUSTICE-06 (lines 16–21)
- `.planning/ROADMAP.md` § "Phase 52: Justice Identity" — goal, 5 success
  criteria, and the notes block that locks the rejected derivation rule
- `.planning/STATE.md` § "Decisions that arrive already made" and § "Open
  decisions that belong to a phase"

### Locked contracts this phase touches
- `.planning/milestones/v1.6-phases/38-full-name-vs-name-parts-rethink/38-CONTEXT.md`
  — D-01 (`full_name` derived from parts, never client-authorable), D-04 (partial-PATCH
  omitted-vs-cleared), D-05 (canonical `First Middle Last, Suffix` format),
  D-06/D-07 (never change capitalization or punctuation). D-09 above preserves
  this discipline for `display_name`.
- `.planning/milestones/v1.7-phases/43-dev-only-reset-to-fixture/` — the
  Copywriting Contract locking the reset to exactly two error strings. **D-14
  amends it.** Read the UI-SPEC before touching the copy.

### Standing policy
- `CLAUDE.md` § Defect Policy — what is fixed silently vs. escalated
- `CLAUDE.md` § Testing Policy — no static source-text contract tests for
  frontend behavior; the initials change is verified in a real browser or by the
  operator's eye, not by grepping a `.svelte` file
- `CLAUDE.md` § Key Constraints — Alembic is the sole DDL authority; asyncpg
  `statement_cache_size=0`

### Source data
- `data/corpus/supreme_court_justices_sections.csv` — two sections (Chief at
  line 1, Associate at line 21), 121 justice rows covering 116 distinct people
  (5 served twice). **Not modified by this phase** (D-05, D-06).
- `data/corpus/speakers.json` — 114 `j__`-prefixed justice speakers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/commands/import_justices_csv.py:407` — already carries the comment
  *"oyez_speaker_id intentionally left NULL — the corpus…"*. That comment marks
  the exact change site. The file's `DEFAULT_CSV_PATH` (line 85) is the pattern
  the new mapping path follows.
- `api/domain/authority.py::decide_write` — the authority ladder. The importer
  already calls it with `incoming_source=ImportSource.SEED.value` at four sites
  (lines 314, 326, 338, 350), and the existing gate is what stops a re-run
  overwriting operator edits. Do not re-implement any part of the ladder.
- `api/domain/person_names.py` — `prepare_person_name`, `format_full_name`,
  `split_legacy_full_name`, and `_KNOWN_SUFFIXES` (line 234, `{"Jr.", "Sr.",
  "II", "III", "IV"}`). The suffix set the initials logic needs already exists.
- `api/services/admin_dev.py` — `_require_corpus_files` establishes the
  pre-flight-before-destructive-statement pattern; the file's own comments
  already document the identical "TRUNCATE'd and not restored" gap for
  `speaker_alias` rows.

### Established Patterns
- **Mass-assignment allow-list.** `PersonUpdate` declares every writable field
  explicitly with `extra="forbid"` (T-09-01 discipline). Any new writable field
  is a deliberate allow-list extension — D-09 chooses not to make one.
- **`model_fields_set`, not `is not None`,** distinguishes "omitted" from
  "explicitly cleared" on PATCH. Relevant if any new field ever becomes writable.
- **Reseed, don't migrate.** No backfill of existing duplicate rows; the reset
  clears them.
- **Alembic is the sole DDL authority.** The `display_name` column and the
  partial unique index are both migrations; never `Base.metadata.create_all`.

### Integration Points
- `pipeline/commands/import_justices_csv.py` — write `oyez_speaker_id` and
  `display_name` from the mapping; keep the `incoming_source="seed"` gate.
- `pipeline/commands/import_convokit.py::_resolve_person` — **no change**. It
  already prefers `oyez_speaker_id`.
- `pipeline/commands/import_convokit.py:1703-1715` — splits `full_name` into
  parts only when none are already stored. This is why corpus advocates usually
  have parts, and `split_legacy_full_name`'s three refusal shapes are why they
  sometimes do not (D-13).
- `api/services/arguments.py:242` — `Person.full_name.label("speaker_name")`
  becomes `COALESCE(display_name, full_name)`.
- `api/services/admin_dev.py::reset_to_fixture` — `TRUNCATE_SQL` lists `people`
  and `court_tenures`; the justice seed goes after it, before the corpus reseed.
- `app/src/routes/admin/+page.server.ts` — `resetToFixture` action (~line 237,
  no `AbortSignal`) and `RESET_MID_ERROR` (~lines 190-266, every `fail()` branch
  currently silent).
- `api/schemas/speakers.py::SpeakerPopoverEntry` — carries `full_name` only. The
  bio card keeps reading `full_name` (JUSTICE-03), so it needs no name change —
  but it is one of the two schemas gaining an initials field (D-12).
- `app/src/lib/public/SpeakerPopover.svelte:57` and
  `app/src/routes/arguments/[slug]/+page.svelte:181` — the two initials helpers,
  7 call sites total.
- **`api/tests/test_trust_public_leak_ban.py`** — this phase adds no new public
  route, schema module or frontend path, so no PLUMBING-07 registration is owed.
  Confirm that holds if planning introduces one.

### Verified measurements (do not re-run)
- 114 corpus justices, 114 mapping rows, zero unmapped either direction.
- 121 CSV justice rows → 116 distinct people; 5 appear twice (Associate + Chief).
- 6 CSV people unmatched by the draft: the 4 now resolved (D-01) plus Barrett and
  Jackson (D-04).
- 38 of 45 `derived` rows are a plain middle-initial abbreviation; 7 are not.
- 1 suffix disagreement across all 114 (Holmes).
- 0 justices whose initials differ between the two name forms.

</code_context>

<specifics>
## Specific Ideas

- **On Holmes, in the operator's words:** *"He was born with Jr. but dropped it
  after his father died (as was common at the time) which was before his time on
  the bench. If this wasn't a SCOTUS project, I would keep it to prevent any
  ambiguity between him and his father but no one reading this is going to see
  his name and confuse him with his father."* The general principle: disambiguating
  punctuation earns its place only when a real reader might actually confuse two
  people.
- **On the error copy** (from the todo, endorsed by D-14): *"Asserting probable
  data corruption when the code has no basis for the claim is worse than a generic
  failure message: it sends the operator to inspect a database that is fine, and
  it would train them to disbelieve the warning on the day it is real."*
- The four "flagged" rows were an artifact of the generating script's surname
  matching, not genuine ambiguity. Tenure dates resolved all four without
  judgment. Worth remembering before trusting a future draft's confidence labels.

</specifics>

<deferred>
## Deferred Ideas

- **Per-writer tier recompute during bulk reseed** — D-17. Belongs with Phase 54
  (bulk publish). Measure the reset with the seed step first.
- **Extending the corpus past 2019** so Barrett and Jackson resolve — not a v1.9
  concern; the mapping and the NULL-tolerant index already accommodate it.

### Reviewed Todos (not folded)

Twelve further todos matched Phase 52 on keyword overlap alone and were reviewed
and left pending — none touch justice identity, the people schema, or
`reset_to_fixture`:

- `2026-08-12-speakers-bench-classification-silent-fallback.md` — bench/advocate
  labelling from `ArgumentParticipant.side`; a resolve-path concern, not an
  identity one
- `2026-08-14-revisit-pre-relocation-checkout-removal.md` — dev environment
- `2026-08-18-pdf-provenance-live-fixture-verification.md` — deferred with the
  PDF route (Phase 999.11)
- `2026-08-28-transcript-long-utterance-paragraph-splitting.md`,
  `2026-08-28-transcript-style-switcher.md`,
  `2026-08-29-bionic-reading-investigation.md`,
  `2026-09-03-transcript-nav-return-to-top-segment.md` — transcript rendering
- `2026-09-03-consolidated-dockets-unreachable-without-pdf-path.md` — PDF route
- `2026-09-03-dense-admin-tables-at-mobile-widths.md` — admin layout
- `2026-09-03-speaker-colour-on-bubbles-and-photo-avatars.md`,
  `2026-09-03-speaker-popover-height-and-scroll-placement.md` — speaker card
  presentation. Adjacent to D-12's avatar work but a separate visual concern;
  not folded.
- `2026-08-31-harden-variant-switcher.md` — design system

</deferred>

---

*Phase: 52-Justice Identity*
*Context gathered: 2026-09-24*
