# Phase 52: Justice Identity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-24
**Phase:** 52-justice-identity
**Areas discussed:** Folded todos, Verifying the mapping, Where the mapping lives, `display_name` in the editor, Avatar initials, Folded reset todos

---

## Folded Todos

| Option | Description | Selected |
|--------|-------------|----------|
| None — keep them pending | Phase 52 adds a seed step but doesn't own reset's UX or transaction shape | |
| Stale created_at timestamps | Reset reuses one transaction so created_at values are stale | ✓ |
| No timeout or progress | Multi-minute destructive op with no observability | ✓ |
| Error copy overclaims DB corruption | Failure message asserts possible corruption where the code knows better | ✓ |

**User's choice:** All three folded.
**Notes:** All three touch `reset_to_fixture`, which this phase modifies and makes slower by adding a ~116-justice seed step.

---

## Which areas to discuss

| Option | Description | Selected |
|--------|-------------|----------|
| Verifying the mapping | Standard for the 45 derived rows; the 4 flagged rows | ✓ |
| Where the mapping lives | Artifact location and shape | ✓ |
| `display_name` in the editor | Visible? Editable? Under the authority ladder? | ✓ |
| Avatar initials | Source of truth for JUSTICE-06 | ✓ |

**User's choice:** All four.

---

## Verifying the mapping

### The 4 flagged rows

| Option | Description | Selected |
|--------|-------------|----------|
| Accept all four | Resolved on the CSV's own oath/termination dates, not a name heuristic | ✓ |
| Accept, but record the evidence in the artifact | Same resolutions with tenure dates carried as a column/comment | |
| Let me look at them myself first | Hold mapping work pending manual review | |

**User's choice:** Accept all four.
**Notes:** Presented with evidence before the question — Harlan elder (1877–1911) vs. grandson (1955–1971), Salmon Portland Chase (Chief 1864–1873) with `Samuel Chase` shown to be a non-contest (own id `j__samuel_chase`, own CSV row 1796–1811, already `exact`), and Brockholst Livingston as the only Livingston justice in the CSV. The draft's "ambiguity" was an artifact of surname matching in the generating script.

### Standard for the 45 derived rows

| Option | Description | Selected |
|--------|-------------|----------|
| Mechanical check + operator spot-check | Structural test over all rows; operator eyeballs the non-abbreviation cases | ✓ |
| Operator reads all 114 first | Nothing promoted until row-by-row sign-off | |
| Mechanical check only | Structural test is the whole gate | |

**User's choice:** Mechanical check + spot-check.
**Notes:** The spot-check was then executed inline rather than deferred to execution. 38 of 45 proved to be plain middle-initial abbreviations; the remaining 7 (`Harold Burton`, `Lucius Q.C. Lamar`, `Neil Gorsuch`, `Noah Swayne`, `Oliver W. Holmes, Jr.`, `Rufus Peckham`, `Stanley Reed`) were presented and confirmed **all seven correct**.

### Barrett and Jackson

| Option | Description | Selected |
|--------|-------------|----------|
| Seed with NULL oyez_speaker_id | Appear in the directory with zero arguments; index permits multiple NULLs | ✓ |
| Seed and flag visibly | Same rows, marked "no corpus presence" | |
| Skip — seed only mapped justices | Bench shows exactly the 114 who speak | |

**User's choice:** Seed with NULL.
**Notes:** Both seated after the corpus's 2019 cutoff. Skipping them would leave two sitting justices absent from the project's own data.

---

## Holmes suffix

| Option | Description | Selected |
|--------|-------------|----------|
| Leave it — each source shown faithfully | Bio card `Oliver Wendell Holmes`, utterances `Oliver W. Holmes, Jr.` | ✓ (on reversal) |
| Add the suffix to his CSV name parts | Set `name_suffix = Jr.` so both surfaces agree | initially selected, then reversed |
| Check for other rows first | Sweep all 114 for suffix disagreement before deciding | |

**User's choice:** Initially "add the suffix," reversed the same session to "don't change his suffix in the CSV."

**Notes:** The operator's reasoning on reversal, verbatim: *"He was born with Jr. but dropped it after his father died (as was common at the time) which was before his time on the bench. If this wasn't a SCOTUS project, I would keep it to prevent any ambiguity between him and his father but no one reading this is going to see his name and confuse him with his father."*

A sweep run after the reversal confirmed Holmes is the **only** suffix disagreement in all 114 rows — so this is a single-row question, not a class. The Harlan row surfaced in the sweep only because it still carried two unresolved candidates at the time.

---

## Where the mapping lives

*(First put to the operator bundled with a third question about where the Holmes correction should live; the operator dismissed the set to reverse the Holmes decision first. Re-asked without that question, which the reversal made moot.)*

### Artifact location

| Option | Description | Selected |
|--------|-------------|----------|
| New CSV in `data/corpus/` | `justice_identity_mapping.csv`, source CSV untouched, matches `DEFAULT_CSV_PATH` pattern, editable without a code change | ✓ |
| Extra columns on the existing justices CSV | One file; mutates a source file and duplicates the id across the 5 dual-service rows | |
| Python constant in the pipeline | Type-checkable; every correction becomes a code change and a deploy | |
| Seeded DB table | Queryable in SQL; heaviest, and `reset_to_fixture` TRUNCATEs aggressively | |

**User's choice:** New CSV in `data/corpus/`.

### Join key

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit name parts | Matches CSV columns directly; independent of the Phase 38 formatting contract | ✓ |
| Reconstructed `full_name` string | Simplest; a formatting change silently breaks every row | |
| CSV row position | Unambiguous today; breaks on any insert or re-export | |

**User's choice:** Explicit name parts.

### `confidence` column

| Option | Description | Selected |
|--------|-------------|----------|
| Drop it | Once verified, every row is equally authoritative | ✓ |
| Keep as provenance | Records how each row was arrived at | |
| Replace with a verified-on date | Ages meaningfully; per-row bookkeeping cost | |

**User's choice:** Drop it.

---

## `display_name` in the editor

### Editability

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only, shown on the person page | Visible but not writable; Phase 38 discipline intact, no re-seed conflict | ✓ |
| Editable, under the authority ladder | Operator can correct a wrong corpus form; adds a field to the allow-list | |
| Invisible — seed-owned entirely | Smallest surface; odd utterance names undiagnosable from the UI | |

**User's choice:** Read-only, shown on the person page.

### `oyez_speaker_id` visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, read-only | The load-bearing join key; corpus-joined vs. not becomes legible | ✓ |
| No — stays internal | Machine key with no operator meaning | |
| Only where it's absent | Show a "not in corpus" marker, hide the identifier | |

**User's choice:** Yes, read-only.
**Notes:** It appears nowhere in the frontend today.

### Directory listing

| Option | Description | Selected |
|--------|-------------|----------|
| Full name only, as today | `display_name` is a rendering detail; identical for 65 of 114 anyway | ✓ |
| Show both when they differ | Makes the 49 mismatches legible; noisy across ~116 rows | |
| Corpus form only | Matches the transcript; directory and person page would disagree | |

**User's choice:** Full name only.

---

## Avatar initials

*Two findings were established before the question: (a) initials computed from the corpus form and the CSV form are identical for all 114 justices once suffixes are skipped, so the name form is not a decision; (b) `split_legacy_full_name` deliberately refuses three shapes, so a corpus-resolved advocate can carry `full_name` and no structured parts.*

### Where initials are computed

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side, one value on the schema | One implementation; client stops parsing names | ✓ |
| Send name parts, fix both client helpers | Presentation stays in the frontend; a third mirror of name logic | |
| Fix the client string-split in place | Smallest change; still guesses structure from a string | |

**User's choice:** Server-side.

### Fallback with no structured parts

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to the string split | Parts when present, suffix-aware split otherwise; no regression | ✓ |
| Fall back to first two characters | Never wrong-but-confident; looks different from every other avatar | |
| Render the placeholder | Honest; would hit a visible number of corpus advocates | |

**User's choice:** Fall back to the string split.

---

## Folded reset todos

### Error copy

| Option | Description | Selected |
|--------|-------------|----------|
| Re-read state, report what's actually there | Endpoint is dev-only and idempotent so the read is cheap; amends the UI-SPEC | ✓ |
| Add a third state for pre-flight refusal | Minimal amendment; can't tell timeout-after-success from partial write | |
| Logging only, leave the copy locked | No amendment; still asserts corruption when there is none | |

**User's choice:** Re-read state.
**Notes:** Flagged to the operator up front that `43-UI-SPEC.md`'s Copywriting Contract ("No third variant is ever returned") locks this, so the change is a deliberate spec amendment.

### Progress

| Option | Description | Selected |
|--------|-------------|----------|
| Per-fixture progress | Backend already iterates `FIXTURE_SET` in order; the seed step becomes visible | ✓ |
| Indeterminate busy state with elapsed time | Much smaller; doesn't say where it is | |
| Just fix the timeout, no progress | Closes the false-failure bug; silence stays silence | |

**User's choice:** Per-fixture progress.

### Tier recompute optimisation

| Option | Description | Selected |
|--------|-------------|----------|
| Out of scope — note it | A publish-path perf question; Phase 54 owns bulk publish | ✓ |
| In scope — the seed step pushes it over | Touches Phase 48 tier machinery four writers depend on | |
| Decide after measuring | Keeps the option open; adds a mid-phase decision point | |

**User's choice:** Out of scope.

---

## Claude's Discretion

Not offered as questions — settled by correctness or measurement, per the project's Defect Policy:

- Which name form feeds the initials (measured: zero of 114 differ)
- The 5 dual-service CSV justices writing one `oyez_speaker_id` to one row without tripping the new unique index
- The trivial-ACCEPT provenance restamp (gate each restamp on `_values_differ`)
- Stale `created_at` from the single-transaction reset
- Converging the two duplicate initials helpers (7 call sites)
- `import_convokit::_resolve_person` requiring no change

---

## Deferred Ideas

- Per-writer tier recompute during bulk reseed → Phase 54
- Extending the corpus past 2019 so Barrett and Jackson resolve → not a v1.9 concern
- Twelve todos matched on keyword overlap and were reviewed but not folded — listed in CONTEXT.md `<deferred>`
