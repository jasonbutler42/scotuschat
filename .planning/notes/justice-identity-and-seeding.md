# Justice Identity & Fixture-Reset Seeding

**Status:** design note, written 2026-09-23 during v1.9 scoping. Not a plan. The
investigation behind it is complete and reproducible; the design is a proposal.

**Operator asks (2026-09-23):** load all justices from the corpus/CSV data and have
them persist through `reset_to_fixture`. Two decisions already made:

- **Join key:** add a verified `oyez_speaker_id` to the justice data (chosen over
  name-overrides or a corpus-first identity spine).
- **Name display:** the full form on the bio card, the corpus form on utterances.

## Two separate problems

### 1. Persistence — small

`reset_to_fixture` (`api/services/admin_dev.py:142`) opens with `TRUNCATE ... CASCADE`
over nine tables; `people` and `court_tenures` are both on the list. It then reseeds
only the four `FIXTURE_SET` conversations through `run_import_convokit`. Nothing
re-runs the justice importer, so every reset wipes the justices.

Precedent for the gap is already in that file's own comments: `seed_aliases.py`'s
`speaker_alias` rows are CASCADE'd away and deliberately not restored.

Fix: a justice-seed step after the TRUNCATE, before the corpus reseed.

### 2. Identity — the real work

The carried White/Black/Clark/Douglas dedup item (deferred since v1.7 Phase 42) is
**not four justices. It is 49 of the 114** justice entries in `speakers.json`.

`import_justices_csv` dedups on exact `Person.full_name`.
`import_convokit::_resolve_person` checks `oyez_speaker_id` first, then exact
`full_name`. CSV-seeded rows carry no `oyez_speaker_id`, so both tools fall through to
the same exact-string comparison — and the two sources spell names differently:

| CSV (reconstructed from parts) | Corpus (`speakers.json`) |
|---|---|
| `Byron Raymond White` | `Byron R. White` |
| `Hugo Lafayette Black` | `Hugo L. Black` |
| `Tom Campbell Clark` | `Tom C. Clark` |
| `Oliver Wendell Holmes` | `Oliver W. Holmes, Jr.` |
| `Neil M. Gorsuch` | `Neil Gorsuch` *(reverse direction)* |

**65 of 114 match exactly; 49 do not.** Ordering does not help — seed-then-import
yields 49 duplicate people where the *duplicate* owns the utterances;
import-then-seed yields the same 49 with ownership flipped. There is also no unique
constraint on `people.full_name` or `people.oyez_speaker_id`, so nothing at the DB
level prevents it.

Only four are visible today because only four fixture arguments are imported. Seeding
all justices scales the defect by roughly 12x.

## Why a derivation rule was rejected

Abbreviating the CSV middle name (`Byron Raymond White` -> `Byron R. White`)
reproduces **100 of 114** corpus forms. The remaining 14 split across three
incompatible conventions:

- corpus keeps the full middle — `Ruth Bader Ginsburg`, `Sandra Day O'Connor`,
  `Harlan Fiske Stone`, `John Paul Stevens`, `William Howard Taft`,
  `Henry Brockholst Livingston`
- corpus drops the middle entirely — `Neil Gorsuch`, `Stanley Reed`, `Harold Burton`,
  `Noah Swayne`, `Rufus Peckham`
- special punctuation/suffix — `Lucius Q.C. Lamar`, `Oliver W. Holmes, Jr.`,
  `John M. Harlan II`

A rule that is right 88% of the time is the worst outcome available here: it looks
correct until someone notices a justice's name is quietly wrong. Since a verified
per-person mapping is needed anyway for `oyez_speaker_id`, the corpus display form
rides along in the same artifact.

## Proposed design

**Data artifact.** A verified justices mapping, one row per justice, carrying
`oyez_speaker_id`, the corpus display form, and the CSV identity.
`.planning/notes/justice-identity-mapping-DRAFT.csv` is a machine-generated **draft**
of exactly this, 114 rows: 65 exact, 45 derived by (first-initial, last-name), and
**4 flagged for the operator**:

| Corpus name | Candidates | Note |
|---|---|---|
| `John M. Harlan` | `John Marshall Harlan` / `John Marshall Harlan, II` | the elder, 1877-1911 |
| `John M. Harlan II` | same two | his grandson, 1955-1971 |
| `Salmon P. Chase` | `Salmon Portland Chase` / `Samuel Chase` | `Samuel Chase` is a different justice (1796-1811) |
| `Henry Brockholst Livingston` | none | CSV files him under first name "Brockholst" |

The draft is **unverified** — it is an input to planning, not a deliverable. Every
`derived` row still wants an eye before it becomes authoritative data.

**Schema.** One nullable column, `people.display_name`. `full_name` keeps its Phase 38
contract as the value derived from name parts (`Byron Raymond White`, shown on the bio
card); `display_name` holds the corpus form (`Byron R. White`, shown on utterances).
Advocates get NULL and fall through.

**Code changes:**

| Where | Change |
|---|---|
| `pipeline/commands/import_justices_csv.py` | write `oyez_speaker_id` + `display_name` from the mapping; keep the existing `incoming_source="seed"` authority gate so a re-run cannot overwrite operator edits |
| `pipeline/commands/import_convokit.py::_resolve_person` | **none** — it already prefers `oyez_speaker_id`; that lookup simply starts hitting |
| `api/services/arguments.py:242` | `COALESCE(display_name, full_name)` in place of `Person.full_name` for `speaker_name` |
| `api/services/admin_dev.py::reset_to_fixture` | seed justices after the TRUNCATE, before the corpus reseed |
| migration | partial unique index on `people.oyez_speaker_id` — the missing structural guard that made 49 duplicates possible |

**No data migration.** Per the reseed-don't-migrate doctrine, existing duplicates are
cleared by the reset itself.

## Open questions for planning

- `SpeakerPopover.svelte:58` derives avatar initials from `full_name`. With the full
  form, `Byron Raymond White` may render `BR` rather than `BW`. Same question applies
  to the bubble-rail avatars in `ChatBubble.svelte`.
- Seeding ~116 justices means the People directory lists justices with zero imported
  arguments. Confirm that is wanted (the operator's ask implies yes).
- Runtime cost of the seed step inside `reset_to_fixture` is unmeasured.

## What this closes

The Person-dedup mismatch carried since v1.7 Phase 42, listed in PROJECT.md's Out of
Scope for v1.8 and in STATE.md's deferred items. It has survived two milestones because
each previous pass treated it as four bad rows rather than a missing join key.
