---
phase: 51-design-system-noun-alignment
plan: 09
type: artifact-report
created: 2026-08-31
status: awaiting operator rulings (blocking checkpoint in plan 51-10)
---

# Admin artifacts surfaced by the D-04 conversion pass

D-08's instruction was that the admin pass must **surface** what it finds rather than
silently preserve it or silently change it. Operator's own framing: admin *"needs a
refactor but there are also some artifacts that survived through various changes so I
expect I'll bring those up."*

Nothing in this list has been changed. Every row is a decision, and the conversion
deliberately stopped at each one.

**How to rule:** write `fix now`, `defer`, or `leave as is` in the ruling column. A `defer`
needs a real destination — a todo file or a backlog item — not a note in this file, which
is archived with the phase.

---

## A. Colours with no semantic role (10 values, 29 sites)

The token map recorded these as open rows and forbade inventing tokens for them without a
decision. They are not stray one-offs: **eight of the ten form two coherent admin lifecycle
scales**, structurally parallel to the `--color-status-*` family that already exists.

**Trust tier** (`tierBadgeStyle`, duplicated verbatim across three files):

| id | value | encodes | files |
|---|---|---|---|
| A-01 | `#38bdf8` | tier `verified` | admin/arguments, admin/help, admin/review |
| A-02 | `#34d399` | tier `trusted` | admin/arguments, admin/help, admin/review |
| A-03 | `#facc15` | tier `provisional` | admin/arguments, admin/help, admin/review |
| A-04 | `#f87171` | tier `uncertain` | admin/arguments, admin/help, admin/review |

**Review state** (`reviewBadgeStyle` / `reviewStateBadgeStyle`):

| id | value | encodes | files |
|---|---|---|---|
| A-05 | `#2dd4bf` | `operator_confirmed` | admin/help, admin/review |
| A-06 | `#e879f9` | `operator_edited` | admin/help, admin/review |
| A-07 | `#475569` | `unreviewed` | admin/help, admin/review |
| A-08 | `#fb7185` | discrepancy badge | admin/review |

**Not part of a scale:**

| id | value | sites | what it is |
|---|---|---|---|
| A-09 | `#64748b` | 6 | A slate mid-tone between `--slate-700` and `--slate-400`. Used as a muted caption colour in DocketPillInput and admin/help, and as the fallback branch of `reviewStateBadgeStyle`. Two different jobs wearing one value. |
| A-10 | `#f59e0b` | 4 | The `.pill` component in admin/people — border, text, focus ring, and active fill. Close to `--amber-600` (`#d97706`) but not identical. |

**Proposed treatment (A-01 … A-08):** promote both scales into the two-layer token
architecture the way `--color-status-*` already is — eight new primitives feeding
`--color-tier-*` and `--color-review-*` semantic roles, admin-only, and covered by the
existing P-04 ban on status colours reaching a public surface. That is a real decision
about whether these axes deserve tokens, which is why the pass stopped here.

**Proposed treatment (A-09):** split it. Decide whether the muted-caption use is
`--color-text-secondary` (it looks like it wants to be) and give the badge fallback
whichever review-state token the decision above produces.

**Proposed treatment (A-10):** decide whether `.pill` is a distinct thing or should adopt
`--color-status-warning` / `--color-stage-accent`.

> **P-03 check, requested by the token map and now done.** `#475569` (A-07) was eliminated
> from *speaker-side differentiation* in Phase 4 for apolitical-framing reasons, and the map
> asked whether its surviving sites re-encode speaker importance. **They do not.** Both
> occurrences colour a record's `review_state === 'unreviewed'` badge on an admin row — a
> pipeline lifecycle state on an argument, not a property of a Justice or an advocate. Safe
> to tokenise.

| ruling |
|---|
| A-01…A-08: |
| A-09: |
| A-10: |

---

## B. Spacing values off the 7-step scale (233 sites)

Reported, never rounded — rounding is how a scale acquires decisions nobody made.

| id | value | sites | note |
|---|---|---|---|
| B-01 | `12px` | 154 | **The single biggest artifact in the codebase.** Sits between `--space-sm` (8) and `--space-md` (16), and appears in padding, gap, margin, margin-bottom, margin-top and padding-right across 14 files. At this frequency it is not an accident — it is an unnamed step the admin UI actually uses. |
| B-02 | `2px` | 26 | Fine adjustment, mostly badge padding. |
| B-03 | `6px` | 10 | Between `--space-xs` and `--space-sm`. |
| B-04 | `20px` | 5 | All `padding-left`, between `--space-md` and `--space-lg`. |
| B-05 | `10px` | 3 | |
| B-06 | `14px` | 2 | |
| B-07 | `1px` | 3 | Hairline offsets. |
| B-08 | `60px` | 1 | One-off. |

**Proposed treatment:** B-01 is the only one that looks like a missing scale step rather
than drift. Three options, and this is a taste call: add a `--space-ms` (12px) step and
convert all 154; convert them to `--space-md` (16px) and accept a visible loosening across
the admin UI; or leave them as the deliberate exception the scale does not cover. **Do not
decide this by grep** — option two changes admin density everywhere and wants your eye.

B-02 … B-08 are plausibly genuine exceptions. Recommend `leave as is` unless a sight-check
says otherwise.

| ruling |
|---|
| B-01: |
| B-02…B-08: |

---

## C. `font-weight: 500` (2 sites, both ResolveCard.svelte)

The map mapped these to `--font-weight-semibold` (600) **and flagged them**, because 500 may
have been a deliberate mid-weight. They are now converted; the two sites are in
`ResolveCard.svelte` around the resolve-row labels.

**This is the one conversion in the whole pass that changes rendered output** — everything
else was a rename of an identical value. Worth a sight-check on the Resolve card.

| ruling |
|---|
| C-01: |

---

## D. Structural artifacts the pass encountered

| id | file | what looks wrong | proposed treatment |
|---|---|---|---|
| D-01 | admin/help, admin/arguments, admin/review | `tierBadgeStyle` is **duplicated verbatim in three files**, with the comment in admin/help openly saying "Copied verbatim from admin/arguments". `reviewBadgeStyle`/`reviewStateBadgeStyle` are a second near-duplicate pair with slightly different fallbacks. | Adopt `lib/primitives/Badge.svelte` at all of these sites and delete the copies. Blocked on A-01…A-08: a shared primitive needs a token, not a hex. |
| D-02 | admin/help | Three page-level style constants (`cardStyle`, `cardHeadingStyle`, `bodyTextStyle`) are built as strings in the script block rather than as markup or classes. Converted in place, but they are a styling mechanism the rest of the codebase does not use. | Decide whether admin/help should be restructured or left as the odd one out. |
| D-03 | admin/pipeline, admin/pipeline/[job_id] | Status colours live in a `BADGE_COLOR` lookup object and a `borderLeft` helper — converted, but the same lifecycle vocabulary is expressed three different ways across the pipeline screens. | Fold into `Badge` alongside D-01. |
| D-04 | all admin | **Not yet checked.** Long-text behaviour in dense tables (UI-SPEC row E5) was preserved exactly as found, per the plan's instruction not to invent a wrap or truncation rule. Which cells look wrong needs your eye at 375px on real data. | Operator sight-check in 51-10. |

| ruling |
|---|
| D-01: |
| D-02: |
| D-03: |
| D-04: |

---

## E. What the pass did NOT find

Recorded so the absence is on the record rather than assumed:

- **No touch-target violation.** No control was found below its 44px / 36px guarantee, and
  the 85 `min-height` conversions were all identical-value renames (`44px` →
  `var(--touch-target)`), so none could have introduced one.
- **No P-04 violation.** No `--color-status-*` reference exists outside `lib/admin/`,
  `routes/admin/`, or `lib/primitives/`.
- **No P-01 violation.** No derived per-speaker or per-argument statistic was added; the
  pass changed styling mechanism only.
- **No behaviour change.** Empty states, live-polling, error and validation copy,
  destructive-confirmation wording and count displays are untouched — the diff is
  1,566 value substitutions and nothing else.
