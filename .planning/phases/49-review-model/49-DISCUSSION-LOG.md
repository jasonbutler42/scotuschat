# Phase 49: Review Model - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-21
**Phase:** 49-review-model
**Areas discussed:** Item granularity, What earns a slot, Resolve in place or link out, Where it lives, Legacy fold (REVIEW-05), Discrepancy record shape, Review→trust precedence, How REVIEW-02 gets proven, Participant method vocabulary

All eight initially-offered gray areas were selected, plus a ninth (participant method
vocabulary) added at the closing check. All four todo fold candidates were accepted.

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Item granularity | Argument rows vs. flagged constituents; mixed list vs. tabs | ✓ |
| What earns a slot | The inclusion predicate for the queue | ✓ |
| Resolve in place or link out | Inline editing vs. deep-linking to existing surfaces | ✓ |
| Where it lives | New route vs. tab vs. filter preset | ✓ |
| Legacy fold (REVIEW-05) | name_needs_review / name_extraction_metadata replacement | ✓ |
| Discrepancy record shape | Table vs. JSONB; where it hangs | ✓ |
| Review→trust precedence | The derive_tier rule 1 vs. 48 D-11 collision | ✓ |
| How REVIEW-02 gets proven | No live re-import producer until Phase 50 | ✓ |

---

## Item granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Argument row, expandable | Argument at top level, constituents on expand; satisfies REVIEW-03 and REVIEW-04 together | ✓ |
| One row per flagged constituent | Flat list, closest to REVIEW-04's wording; fans one bad argument into many rows | |
| One row per argument only | Click through to the detail page; cheapest, degrades the queue to a list of links | |

| Option | Description | Selected |
|--------|-------------|----------|
| Separate Arguments \| People tabs | Two entity shapes, different columns; mirrors the Bench/Advocate tab pattern | ✓ |
| One mixed list | Truest to "every item needing attention"; rows go sparse | |
| People stay in the People directory | Least new UI; splits REVIEW-03 across two screens | |

| Option | Description | Selected |
|--------|-------------|----------|
| Worst tier first | UNCERTAIN → PROVISIONAL → TRUSTED, oldest within tier | ✓ |
| Oldest argued date first | Chronological backlog sweep | |
| Newest first | Matches /admin/arguments today | |
| You decide | Defer to research/planning | |

| Option | Description | Selected |
|--------|-------------|----------|
| Unbounded, like today | Consistent with /admin/arguments and /admin/people | ✓ |
| Server-side paging from day one | New pattern; the one screen guaranteed to be large | |
| Hard cap with "showing N of M" | Cheap honesty without paging controls | |

**Notes:** The volume tension was recorded deliberately in CONTEXT.md D-04 rather than
dismissed — research should raise it if the unbounded query is already slow against the
real corpus.

---

## What earns a slot

| Option | Description | Selected |
|--------|-------------|----------|
| Attention-worthy | needs_review OR unresolved person_id OR tier below TRUSTED | ✓ |
| Flagged only | Strictly needs_review; risks shipping an empty queue | |
| The whole unreviewed pool | Never looks finishable on a corpus of thousands | |

| Option | Description | Selected |
|--------|-------------|----------|
| Both import and conflicts | Import flags unresolvable participants; discrepancies flag conflicts | ✓ |
| Conflicts only | Keeps needs_review's meaning narrow | |
| Import only | Discrepancies get a separate signal | |

| Option | Description | Selected |
|--------|-------------|----------|
| Included, marked, sorted to top | A public UNCERTAIN argument is the most urgent row | ✓ |
| Included behind a filter, default off | Queue is primarily pre-publication triage | |
| Excluded | Would leave 48 D-08's promise unfulfilled | |

| Option | Description | Selected |
|--------|-------------|----------|
| Tier + review state + status | Status matters: candidates are invisible elsewhere | ✓ |
| Exactly tier + review state | Only what REVIEW-03 names | |
| Add side / entity type | More slicing; side has a known silent-fallback bug | |

---

## Resolve in place or link out

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid: confirm inline, edit links out | Inline PATCH for confirm; deep-link to ResolveCard for edits | ✓ |
| Fully inline in the queue | Best sweep flow; second consumer of the popover stack | |
| Queue is triage only | Zero new editing surface; a round-trip per item is the job | |

| Option | Description | Selected |
|--------|-------------|----------|
| No — per-item only | A bulk button makes "a human checked it" unfalsifiable | ✓ |
| Yes, per argument | Time saver at corpus scale, coarser confirmation | |
| Only for rows already expanded | Middle ground; more UI state | |

| Option | Description | Selected |
|--------|-------------|----------|
| Re-flag allowed, un-review not | Push back to needs_review; never back to unreviewed | ✓ |
| One-way only | Strongest sacred-work reading; a mis-click has no recourse | |
| Full reset allowed | Makes review_state a mutable label, not a record | |

| Option | Description | Selected |
|--------|-------------|----------|
| Stays visible, shows new state | Catch a mis-click; rows leave on refresh | ✓ |
| Disappears immediately | Visible progress; mis-clicks vanish | |
| You decide | Defer to research/planning | |

---

## Where it lives

| Option | Description | Selected |
|--------|-------------|----------|
| New /admin/review route | Different row unit, filters, and audience from /admin/arguments | ✓ |
| Tab on /admin/arguments | Reuses page and filters; needs the candidate exclusion relaxed | |
| Filter preset on /admin/arguments | Smallest phase; wrong row unit | |

| Option | Description | Selected |
|--------|-------------|----------|
| Stays excluded | Exactly what 48 D-04 anticipated; nothing regresses | ✓ |
| Add a Candidate filter option | Two screens showing the same rows | |
| Candidates visible by default | Changes what every existing stat card counts | |

| Option | Description | Selected |
|--------|-------------|----------|
| Match today's inline-style admin | Phase 51 reworks it; no design debt front-loaded | ✓ |
| Run /gsd-ui-phase 49 first | A considered layout for the first new screen in a while | |
| Establish shared components here | Widens a schema phase into a refactor | |

| Option | Description | Selected |
|--------|-------------|----------|
| Nav link + dashboard count | Reuses the StatCard pattern | ✓ |
| Nav link only | No aggregate query, no stale count | |
| Also link from argument detail | Would close the loop 48 D-19 opened | |

---

## Legacy fold (REVIEW-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — Person carries review_state | Replaces both legacy columns; no D-10 violation | ✓ |
| No — participant-only | Fewest columns; People directory loses its filter | |

| Option | Description | Selected |
|--------|-------------|----------|
| One shared PG enum | Matches argument_status / trust_tier precedent | ✓ |
| Varchar + CHECK | Dodges PG's cannot-drop-a-value problem (hit twice already) | |
| Separate enum per table | More DDL; derive_tier treats them as one vocabulary | |

| Option | Description | Selected |
|--------|-------------|----------|
| Edit → operator_edited; add explicit Confirm | No value-diffing; both states get an honest producer | ✓ |
| Diff the values | Most precise; fragile with normalization in the middle | |
| Edit → operator_edited only | Leaves operator_confirmed dead for Person | |

| Option | Description | Selected |
|--------|-------------|----------|
| Carry Phase 38 D-15 unchanged | review_state records the action; metadata stays an audit trail | ✓ |
| Carry it and append operator actions | Richer audit; unbounded growth, duplicates argument_status_log | |
| You decide | Defer to research/planning | |

---

## Discrepancy record shape

| Option | Description | Selected |
|--------|-------------|----------|
| Its own discrepancy table | Queryable, joinable, per-value on (row, field, run) | ✓ |
| JSONB moved onto import_run | Cheapest migration; cannot filter without unnesting JSON | |
| JSONB on the target row | Co-located; cannot answer "what did this run disagree about" | |

| Option | Description | Selected |
|--------|-------------|----------|
| Left alone this phase | A different concept sharing a name; on the deferred PDF route | ✓ |
| Migrate it into the new table | Drags ResolveCard's HIT/MISS rendering into a corpus phase | |
| Rename it to avoid confusion | Cheap clarity; one migration plus a frontend rename | |

**Notes:** The lifecycle question was paused for clarification. The operator's framing:
*"I can't tell if giving each discrepancy its own lifecycle rather than resolving them
based on resolving the row is due diligence or an example of YAGNI. Do you envision one
discrepancy per row?"*

Answered: not one per row — the natural key is (target row, field, import_run), so
typically one per row per run, but a corpus re-import can disagree on `last_name` *and*
`name_suffix`, or `person_id` *and* `side`, at once; and they accumulate across runs. The
original option conflated two separable things. A per-discrepancy `resolved_at` is due
diligence (without it a fresh disagreement is indistinguishable from a stale one already
dealt with). A per-discrepancy accept/reject **workflow** is YAGNI (accept is an edit,
reject is a confirm — both already exist). The question was reframed with the merge as a
new option.

| Option (reframed) | Description | Selected |
|--------|-------------|----------|
| Row-resolve closes them, per-row resolved_at | One operator action; repeat disagreements stay distinguishable | ✓ |
| Independently resolvable, with its own UI | A second workflow over existing capabilities | |
| Append-only, no resolved state | Pushes the hard reasoning into every reader | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, recorded as a discrepancy too | The design note's worked example verbatim | ✓ |
| No — only equal-or-higher authority | Literal REVIEW-02; fills the queue with settled noise | |
| Recorded, but never raises a queue item | Audit only, queue stays actionable | |

---

## Review→trust precedence

Grounding fact surfaced before the questions: at `api/services/trust.py:104-109` a
*resolved* participant contributes nothing to the floor (48 D-13), and an unresolved one
appends UNCERTAIN directly, bypassing `derive_tier` entirely.

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit confirm lifts it | Rule 1 wins, but only via a distinct confirm-as-unattributable action | ✓ |
| UNCERTAIN always wins | Strictest 48 D-11 reading; such arguments become override-only forever | |
| Can't confirm an unresolved row at all | Cleanest invariant; no path for genuinely unattributable rows | |

| Option | Description | Selected |
|--------|-------------|----------|
| Full derive_tier per participant | The designed path; no signature change (48 D-13 holds) | ✓ |
| review_state only | Smaller schema; the row cannot state its own provenance | |
| Nothing unless flagged | A confirm could never lift an argument out of UNCERTAIN | |

| Option | Description | Selected |
|--------|-------------|----------|
| Store both source and method on the row | Self-describing; an argument accumulates runs, so inheritance is ambiguous | ✓ |
| Inherit from the argument's import_run | Fewer columns; no single answer once Phase 50 lands | |
| Store method only, imply source | Breaks on `normalized`, which spans corpus and pdf | |

| Option | Description | Selected |
|--------|-------------|----------|
| No — strictly per-argument rows | Preserves 48 D-10 exactly; no fan-out, no dirty-marking | ✓ |
| Yes, via fan-out write | Reintroduces precisely the fan-out D-10 rejected | |
| Yes, via read-time join | Direct D-10 violation | |

---

## How REVIEW-02 gets proven

Grounding fact surfaced before the questions: `import_convokit.py:493` skips existing
arguments outright (`skipped_existing`), so no code path today compares an incoming value
against a stored one.

| Option | Description | Selected |
|--------|-------------|----------|
| Record + display + one real writer | Nothing ships uncalled; Phase 50 reuses the function | ✓ |
| Record + display only | How 48's rule 3 shipped unreachable for a whole phase | |
| Also build corpus re-import here | Complete, and annexes the core of Phase 50 | |

| Option | Description | Selected |
|--------|-------------|----------|
| pytest + a live authority-conflict walkthrough | Each vehicle proves what it honestly can (48 D-21's shape) | ✓ |
| pytest only | The queue would ship never having been looked at | |
| Add a synthetic re-import harness | Strongest proof; throwaway once Phase 50 lands | |

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — build the unresolved-speaker fixture | Unresolved participants are now first-class, so it stops being synthetic | ✓ |
| No — leave them for Phase 50 | Keeps the phase focused | |
| Close 26-UAT only | Test 8 pairs better with Phase 51's UI work | |

| Option | Description | Selected |
|--------|-------------|----------|
| Editability with the review work; other three as cleanup | Editability is a prerequisite; the rest are independent | ✓ |
| All four folded into the relevant plans | More scattered, fewer plans | |
| Editability only; defer the other three again | Back to the backlog they've sat in for weeks | |

---

## Participant method vocabulary

Added at the closing check as a ninth area — the entity sketch's last open item, made
load-bearing by the decision that participants store source+method and run through
`derive_tier`.

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse ImportMethod verbatim | No mapping layer, no new enum; the five values cover every mechanism | ✓ |
| Participant-specific vocabulary | More precise; costs a mapping layer and a second vocabulary | |
| Reuse ImportMethod plus one new value | Precision where it blurs; PG can never drop the value | |

| Option | Description | Selected |
|--------|-------------|----------|
| normalized → PROVISIONAL *(recommended)* | A name match is weaker evidence than an external ID | |
| direct → TRUSTED | Corpus is still the source; the remedy is the same review either way | ✓ |
| normalized and flag needs_review | Would fill the queue with most of the corpus | |

**Notes — the one place the operator overrode the recommendation, and was right.**
The operator's challenge: *"My concern about the direct → TRUSTED other choices is
something you brought up: the corpus is trusted so pulling from it should be trusted.
Maybe a better framing is, 'How often does this happen?' Is the only expected time we see
this during stage direction and laughter? If so, then I will go with your
recommendation."*

Reading the code answered it against the recommendation:

- `import_convokit.py:774` **backfills `oyez_speaker_id`** on a `full_name` match, so
  each person traverses that path at most once ever — a one-time first-encounter
  handshake, not a recurring class of weaker links.
- It is **not** stage directions or laughter: unattributed speakers are skipped (`:861`)
  and stage directions are utterance rows with no speaker (`:1093`); neither reaches
  `_resolve_person`.
- The cohort that does hit it is the **most trustworthy in the database** — justices
  seeded from the curated CSV (created with no `oyez_speaker_id`) and operator-created
  people — plus, rarely, two Oyez IDs sharing a `full_name`, which is the
  White/Black/Clark/Douglas dedup mismatch already out of v1.8 scope.

`normalized` would therefore have tiered *down* the seed-justice and operator-created
rows on a first-encounter-only basis, producing a tier that flips to TRUSTED on the next
import of the same person — a race with the backfill, not a trust signal. Recommendation
withdrawn; `direct` recorded as correct.

| Option | Description | Selected |
|--------|-------------|----------|
| No — review_state carries the authority | Matches the design note's worked example; keeps original provenance | ✓ |
| Yes — overwrite to operator/manual | Plain column comparison; loses original provenance from the row | |
| Store both | Two places answering "what authority is this row" | |

| Option | Description | Selected |
|--------|-------------|----------|
| Record the mapping, don't build it | Consistent with corpus-first; cannot be proven live | ✓ |
| pdf_pipeline/normalized, built now | Contradicts corpus-first; no PDF fixture exists | |
| seed/direct → TRUSTED | Same participant reads differently depending on which column wins | |

---

## Claude's Discretion

Recorded with a lean in CONTEXT.md so planning does not re-open them:

- Migration defaults and backfill — lean: follow 48's precedent (NOT NULL,
  `server_default 'unreviewed'`, no in-migration derivation), with the one required
  legacy mapping `name_needs_review = true → 'needs_review'`.
- Endpoint shapes for the queue list, the inline-confirm PATCH, and the
  confirm-as-unattributable action.
- Whether the queue's filters reuse the segmented-control pattern or plain selects —
  lean: segmented for status, selects for the two new axes.
- The discrepancy table's name — lean: something unconfusable with
  `admin_jobs.discrepancies`.
- Whether the dashboard count is a dedicated COUNT or derives from the queue endpoint —
  lean: dedicated COUNT, since the queue list is unbounded.

## Deferred Ideas

No scope creep arose during the discussion — every area stayed inside the phase
boundary. The deferred list in CONTEXT.md is composed of things this phase deliberately
declines (corpus re-import compare-and-record → Phase 50; PDF alias-HIT wiring → deferred
PDF route; the legacy discrepancy blob → Phase 50; queue paging → if it proves slow;
shared component extraction → Phase 51) and three outright rejections recorded so they
are not revisited as oversights (bulk confirm, a per-discrepancy accept/reject workflow,
appending operator actions to `provenance_metadata`).
