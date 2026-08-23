# Phase 49 — Evidence Record

**Plan:** 49-06 (dev-only unresolved-speaker seeder, live D-32 walkthrough, full-suite gate,
requirement traceability)
**Recorded:** 2026-08-23

This file is the phase's evidence-of-record. Every command below is transcribed verbatim (or
with only credentials redacted); no threshold was adjusted to make a check pass. One finding —
a real gap in the review queue's own discrepancy-inclusion logic — was discovered during this
plan's own D-32 walkthrough and fixed in the same plan, not smoothed over. A second finding
corrects a false premise inherited from `49-RESEARCH.md`. Both are recorded in full under
**Findings**, and both are also entered in `.planning/WINDOWS.md`.

---

## 1. Corrected premise (49-RESEARCH.md Pitfall 4)

**What the research doc claimed:** "no live corpus path can produce an unresolved speaker,
because `_resolve_person` always resolves-or-creates."

**What is actually true, verified against the live dev database before this plan started work:**
argument 1788 had 11 `argument_participants` rows with `person_id IS NULL` at that time, linked
to `admin_jobs` row 1147 (status `paused`). The mechanism: a job parked at the resolve step has
created participant rows but has not yet run `_resolve_person` — pre-resolve, `person_id IS NULL`
is a normal, reachable live state. `_resolve_person` resolves-or-creates only once the resolve
step actually executes.

**Disposition.** The dev-only seeder (D-33a) built in this plan's Task 1 is NOT justified by that
false claim. Its real justification, stated in its own docstring and nowhere citing the false
premise: a deterministic, repeatable mechanism that does not depend on hand-parking a real
pipeline job is what D-32/D-33's walkthroughs need to be reproducible on demand, and it closes
two UAT items (26-UAT Test 26, 14-UAT Test 8) that have been blocked since June 2026. Recorded in
`.planning/WINDOWS.md` (entry 13, kind `deviation`) so `49-RESEARCH.md`'s Pitfall 4 is not carried
into Phase 50 uncorrected.

---

## 2. Task 1 — the seeder, verified live

### 2a. Environment

```
$ ./.venv/bin/alembic current
0029 (head)
```

No new migration authored by this plan (environment note confirmed: none needed).

### 2b. Live run against the real Complexity fixture (not a synthetic test row)

After a fresh `reset_to_fixture` (argument id varies per reset — the Complexity fixture's
`oyez_transcript_id` is always `"15169"`, which is what the seeder actually keys on):

```
seed_unresolved_speaker_fixture(db) ->
{'argument_id': 1793, 'participant_id': 3586, 'raw_speaker_label': 'Lloyd N. Cutler',
 'trust_tier': 'uncertain', 'already_seeded': False}
```

Participant 3586's `side` was **already `SideEnum.UNKNOWN`** in the real corpus data before the
seeder touched it — not synthetic, a residual pre-Resolve-rework state the Complexity fixture
already contains (this is exactly why 26-UAT Test 26 was reachable without inventing a fixture,
matching the corrected premise above). After the seeder ran: `person_id=NULL`,
`review_state=needs_review`; all 5 `Utterance` rows carrying `raw_speaker_label='Lloyd N. Cutler'`
on that argument also read `person_id=NULL` (the Task 1 fix that nulls the matching utterances,
not just the participant — see **Finding 1** in 49-06's own commit history / SUMMARY).

Idempotency, same process:

```
seed_unresolved_speaker_fixture(db) -> {..., 'already_seeded': True}  # same participant_id
```

`GET /api/admin/review/arguments` (in-process ASGI call, admin token read from
`settings.admin_token`, never printed) confirms the argument appears with that exact constituent:

```
{"id": 1793, "case_name": "Baltimore & Ohio Railroad Company v. United States",
 "trust_tier": "uncertain", "attention_count": 1}
constituent: {"participant_id": 3586, "person_id": None, "display_name": "Lloyd N. Cutler",
              "side": "UNKNOWN", "review_state": "needs_review"}
```

`POST /api/admin/dev/seed-unresolved-speaker` returns 404 with `ENVIRONMENT=production` (verified
via `importlib.reload(api.main)` after mutating `settings.environment`, never via a sys.modules
purge that would have broken this plan's own autouse DB fixtures — see the test module's own
comment for why).

### 2c. A genuine second correction found while implementing Task 1

`26-UAT Test 26` needs `ArgumentParticipant.side == 'UNKNOWN'`; `14-UAT Test 8` needs
`Utterance.person_id IS NULL`. Neither is what the plan's own literal Task 1 action text
initially produced ("select the first non-BENCH participant ordered by id ASC" would have picked
participant 3548/Howard J. Trienens, `side=PETITIONER`, on the pre-fix live data — never
`UNKNOWN`; and nulling only the participant's `person_id` never touches the independent
`Utterance.person_id` column the public chat page actually reads). Both gaps were found by
tracing the actual consumer source (`api/services/admin_arguments.py::list_argument_speakers`,
`api/services/arguments.py`, `ChatBubble.svelte`) before writing the fixture, not assumed, and
fixed in the same task: the seeder now prefers an `UNKNOWN`-side participant when one exists, and
nulls the matching `Utterance` rows too. See the Task 1 fix commit for the full docstring
explanation.

---

## 3. Task 2 — Dev Tools control, and the 26-UAT/14-UAT re-triage

The frontend control (`app/src/routes/admin/+page.svelte`), its form action, and the UAT file
updates are described in the Task 2 commit. Per this plan's `<human-check>` requirement, every
clause is recorded below with its actual (script/API, not browser) observed result — the
credential-access denial that blocked 49-01/49-03/49-05's own browser walkthroughs blocks this
one too, and no workaround was attempted.

| `<human-check>` clause | Observed result |
|---|---|
| Click Reset to Fixture, wait for success, then click Seed unresolved speaker; success line names the Complexity fixture and reports `uncertain` | Ran the equivalent backend calls directly (`reset_to_fixture` then `seed_unresolved_speaker_fixture`) against the live dev DB — both succeeded; response `trust_tier: 'uncertain'`. The literal on-screen button/line rendering was NOT observed. |
| 26-UAT Test 26 — Speakers card shows the placeholder and the Save gate | Confirmed via API + source: constituent's `side` reads `UNKNOWN`; `list_argument_speakers` passes that value through unchanged; the frontend's `speakerSideById` map collapses non-`VALID_SIDES` values to the literal `'UNKNOWN'`, which is exactly the `<option value="UNKNOWN">Unresolved — choose a role</option>` branch and the `speakerSideById[...] === 'UNKNOWN'` Save-disable guard. Data state confirmed live; the actual rendered placeholder/disabled button was NOT observed in a browser. |
| 14-UAT Test 8 — non-resolved utterance renders as a non-interactive avatar | Confirmed via direct query: 5 `Utterance` rows for this speaker now read `person_id IS NULL`; `ChatBubble.svelte`'s `{#if utterance.person_id != null && onAvatarClick}` gate means these should render as a plain circle. **Second precondition, outside this seeder's scope:** the argument must be `PUBLISHED` to reach the public chat page at all, and `reset_to_fixture` deliberately leaves this fixture `CANDIDATE`/`DRAFT` (a fixture other Phase 44/49 work relies on staying editable) — this seeder does not publish it. Neither the data state nor the publish step was visually confirmed. |
| `/admin/review` shows a constituent reading "Unresolved speaker" and offering "Confirm as unattributable" but not plain "Confirm" | Confirmed via source (`app/src/routes/admin/review/+page.svelte:482,506,515,521`): the display-name branch renders the literal string `"Unresolved speaker"` when `person_id === null`; Confirm's render guard requires `person_id !== null`; Confirm-as-unattributable's requires `person_id === null`. Confirmed via API that this exact constituent has `person_id: null`. Not visually observed. |
| Click "Confirm as unattributable"; tier badge changes; row stays visible with its new review-state badge | Ran `resolve_participant_review(action="confirm_unattributable")` against the live seeded participant. Row-level: `review_state` -> `operator_confirmed`, confirmed via API the row stays listed (`attention_count` unchanged). **Argument-level tier badge did NOT change** — see **Finding 2** below; this is a genuine, verified correction to this clause's literal wording, not an assumption. |

---

## 4. Finding 2 — Task 2's "tier badge changes" clause does not hold on the real Complexity fixture

**What was expected:** clicking "Confirm as unattributable" would visibly change the argument's
trust-tier badge.

**What was observed, live:** the Complexity fixture (15169) has 25-30 utterances ConvoKit itself
could never attribute to a speaker (`unresolved_utterance_speaker` blocker, pre-existing, unrelated
to this plan — the same ConvoKit "unattributed speaker" sentinel `48-EVIDENCE.md` Finding 1
already documented for this exact fixture). `floor_tier` takes the worst tier across every
constituent, so this argument's `trust_tier` reads `uncertain` before AND after
`confirm_unattributable` lifts the one participant's own floor:

```
before: blockers = [{'unresolved_utterance_speaker': 30}, {'unresolved_participant': 1}]
after:  blockers = [{'unresolved_utterance_speaker': 30}, {'uncertain_participant': 1}]
argument.trust_tier: 'uncertain' -> 'uncertain'  (unchanged)
```

**This is correct behavior, not a bug** — `floor_tier`'s worst-of-all-constituents design is
exactly what D-11 specifies, and the recompute genuinely ran (the blocker breakdown changed from
`unresolved_participant` to `uncertain_participant`, proving the recompute is live, not stale).
The plan's own Task 3 wording for the parallel D-32 clause ("the argument's tier badge reflects a
fresh recompute") is accurate; Task 2's wording ("confirm the argument's tier badge changes") is
not, for this specific real fixture. Recorded here rather than silently narrowed or assumed true.

---

## 5. Task 3 — D-32 live authority-conflict walkthrough

### 5a. The repeatable script

Run via `./.venv/bin/python -` (stdin) against the live dev database after a fresh
`reset_to_fixture`, using the real Complexity fixture argument and its first resolved advocate
participant (id varies per reset — this run's ids: argument 1793, participant 3586... no —
**this walkthrough used a DIFFERENT participant than the seeder's own target**, to keep D-32
independent of D-33a: participant 3586 in this transcript is `Howard J. Trienens`,
`side=PETITIONER`, the first participant on the argument, chosen specifically because it is
already-resolved and uninvolved with the seeder's own target row):

```python
import asyncio
from sqlalchemy import select
import api.core.database as db_module
from api.models.models import Argument, ArgumentParticipant
from api.services.admin_arguments import update_participant_side
from api.services.admin_review import apply_participant_value_change, resolve_participant_review
from api.models.models import SideEnum
from api.services.trust import summarize_tier_blockers

ARGUMENT_ID = 1793
PARTICIPANT_ID = 3586

class FakeApp:
    pass

async def show(db, label):
    p = (await db.execute(select(ArgumentParticipant).where(ArgumentParticipant.id == PARTICIPANT_ID))).scalar_one()
    arg = (await db.execute(select(Argument).where(Argument.id == ARGUMENT_ID))).scalar_one()
    print(f"[{label}] participant.descriptor={p.descriptor!r} review_state={p.review_state.value} argument.trust_tier={arg.trust_tier.value}")

async def main():
    async with db_module.lifespan(FakeApp()):
        async with db_module.AsyncSessionLocal() as db:
            await show(db, "BEFORE ANYTHING")

        # Step 1: operator edit through the real admin write path (Speakers card Save button).
        async with db_module.AsyncSessionLocal() as db:
            result = await update_participant_side(
                db, ARGUMENT_ID, PARTICIPANT_ID, side=SideEnum.PETITIONER,
                descriptor="Lead counsel for petitioner (operator edit)",
            )
            print("STEP 1 update_participant_side result:", result)

        async with db_module.AsyncSessionLocal() as db:
            await show(db, "AFTER STEP 1 (operator edit)")

        # Step 2: a second, lower-authority writer (simulating a future corpus
        # re-import) disagrees with the operator's value.
        async with db_module.AsyncSessionLocal() as db:
            participant = (await db.execute(select(ArgumentParticipant).where(ArgumentParticipant.id == PARTICIPANT_ID))).scalar_one()
            decision = await apply_participant_value_change(
                db, participant=participant, field="descriptor",
                incoming_value="Counsel of record (corpus re-import)",
                incoming_source="corpus", incoming_method="direct",
            )
            await db.commit()
            print("STEP 2 apply_participant_value_change decision:", decision)

        async with db_module.AsyncSessionLocal() as db:
            await show(db, "AFTER STEP 2 (corpus re-import disagrees)")

        # Step 3: confirm via the review queue that the operator's value survived
        # and the discrepancy is visible.
        from httpx import ASGITransport, AsyncClient
        from api.main import app
        from api.core.config import settings
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/admin/review/arguments", headers={"X-Admin-Token": settings.admin_token})
            body = resp.json()
            match = next(item for item in body if item["id"] == ARGUMENT_ID)
            constituent = next(c_ for c_ in match["constituents"] if c_["participant_id"] == PARTICIPANT_ID)
            print("STEP 3 queue constituent:", constituent)

        # Step 4: resolve the row from the queue (Re-flag is the only available
        # action for an operator_edited, resolved participant).
        async with db_module.AsyncSessionLocal() as db:
            reflag_result = await resolve_participant_review(db, PARTICIPANT_ID, action="reflag")
            print("STEP 4 reflag result:", reflag_result)

        async with db_module.AsyncSessionLocal() as db:
            await show(db, "AFTER STEP 4 (reflag / resolve)")
            blockers = await summarize_tier_blockers(db, ARGUMENT_ID)
            print("blockers final:", blockers)

asyncio.run(main())
```

### 5b. Transcript (verbatim, this run's real output)

```
[BEFORE ANYTHING] participant.descriptor=None review_state=unreviewed argument.trust_tier=uncertain
STEP 1 update_participant_side result: {'id': 3586, 'side': 'PETITIONER', 'descriptor': 'Lead counsel for petitioner (operator edit)', 'write_decision': 'accept', 'descriptor_write_decision': 'accept_and_record'}
[AFTER STEP 1 (operator edit)] participant.descriptor='Lead counsel for petitioner (operator edit)' review_state=operator_edited argument.trust_tier=uncertain
STEP 2 apply_participant_value_change decision: WriteDecision.REJECT_AND_RECORD
[AFTER STEP 2 (corpus re-import disagrees)] participant.descriptor='Lead counsel for petitioner (operator edit)' review_state=operator_edited argument.trust_tier=uncertain
STEP 3 queue constituent: {'participant_id': 3586, 'person_id': 1762, 'display_name': 'Howard J. Trienens', 'side': 'PETITIONER', 'review_state': 'operator_edited', 'has_open_discrepancy': True, 'discrepancies': [{'id': 5, 'field': 'descriptor', 'existing_value': 'Lead counsel for petitioner (operator edit)', 'existing_source': 'corpus', 'existing_method': 'direct', 'incoming_value': 'Counsel of record (corpus re-import)', 'incoming_source': 'corpus', 'incoming_method': 'direct', 'created_at': '2026-08-23T16:03:44.273766+00:00'}]}
STEP 4 reflag result: {'id': 3586, 'argument_id': 1793, 'review_state': 'needs_review'}
[AFTER STEP 4 (reflag / resolve)] participant.descriptor='Lead counsel for petitioner (operator edit)' review_state=needs_review argument.trust_tier=uncertain
blockers final: [{'code': 'unresolved_utterance_speaker', 'count': 25}, {'code': 'uncertain_participant', 'count': 1}]
```

**Result:** the operator's value (`'Lead counsel for petitioner (operator edit)'`) survives
untouched through the corpus re-import's disagreement (`REJECT_AND_RECORD`); the discrepancy is
visible with both competing values and provenances; `reflag` (the only available action on an
`operator_edited`, resolved row) closes it, confirmed by a direct row query afterward
(`resolved_at` set on discrepancy id 5). The tier "reflects a fresh recompute" (Task 3's own
wording) — it does, correctly reading `uncertain` throughout because of this fixture's own
pre-existing, unrelated `unresolved_utterance_speaker` count (see Finding 2 above for the
identical dynamic on Task 2's differently-worded clause).

### 5c. Finding 1 (this plan's central finding) — the discrepancy was invisible before a same-plan fix

**Before the fix below, STEP 3 above failed**: `next(...)` over `match["constituents"]` raised
`StopIteration` — the constituent with the open discrepancy was not in the list at all, even
though the discrepancy row existed in the database and the argument itself appeared in the queue
(via the unrelated degraded-tier leg).

**Root cause.** `_argument_attention_predicate()` (`api/services/admin_review.py`) had exactly
three legs — `needs_review`, `person_id IS NULL`, `trust_tier` degraded — and
`list_review_queue_arguments`'s own per-constituent inclusion check mirrored only those same two
participant-level conditions. An operator-edited, already-resolved participant with an open
discrepancy satisfies none of them: `review_state` is `operator_edited`, not `needs_review`;
`person_id` is NOT NULL; and this one field edit does not necessarily move the argument's own
`trust_tier`. This is **exactly the D-32 scenario** — REVIEW-02/REVIEW-04's central claim — so the
gap was not peripheral.

The People-tab predicate (`_person_attention_predicate`) already had the equivalent leg (`Person.id.in_(discrepant_person_ids_subq)`), and its own docstring explicitly says it matches
"the same inclusion philosophy" the Arguments tab was supposed to share — the Arguments side had
simply never gotten that leg.

**Fix (same plan, same file):** `_argument_attention_predicate` gained a fourth leg
(`ArgumentParticipant.id.in_(select(ValueDiscrepancy.target_id).where(target_type=
'argument_participant', resolved_at IS NULL))`); `list_review_queue_arguments`'s per-constituent
`is_flagged` check was widened to match, pre-fetching the discrepant-participant-id set once
rather than per row. `get_review_queue_stats` shares the same predicate by construction (D-30), so
the dashboard count picks this up automatically.

**Verification:** re-ran the exact script above after the fix — STEP 3 now succeeds (transcript
in §5b). Two new regression tests
(`test_discrepancy_alone_includes_argument_and_lists_constituent`,
`test_argument_no_longer_listed_once_its_only_discrepancy_closes`) pin an argument whose ONLY
issue is an open participant discrepancy, proving it is included while open and drops out once
closed. Recorded in `.planning/WINDOWS.md` entry 12 (kind `deviation`, status `fixed`).

---

## 6. Full-suite gate

**Methodology note, worth recording precisely:** an earlier full-suite run in this same
session reported 2 spurious failures (`test_admin_dev_routes.py::test_reset_against_empty_database`,
`::test_reset_incomplete_reseed_raises`), both `asyncpg.exceptions.DeadlockDetectedError` on the
same database OID (17111) — because this executor was concurrently running direct scripts
against `DATABASE_URL` (the D-32/seeder verification above) while the pytest suite was
concurrently running against `TEST_DATABASE_URL` in the background. In this sandbox the two
resolve to the same underlying Postgres database, so the two processes' TRUNCATEs/locks
collided — an artifact of running verification scripts and the suite at the same time, not a
code defect. Re-running the two named tests in isolation (`pytest api/tests/test_admin_dev_routes.py`)
passed cleanly (9/9). The number below is from a subsequent **fully isolated** run — nothing else
touching either database while it ran.

```
$ ./.venv/bin/python -m pytest
...
1414 passed, 5 xfailed, 12 warnings in 302.14s (0:05:02)
```

Compared against the Phase 48 baseline this plan inherited (1209 passed / 5 xfailed / 0 failed /
0 skipped) and against 49-05's own end-of-wave number (1403 passed / 5 xfailed / 0 failed): **1414
= 1403 + 11** (9 tests in the new `test_admin_dev_unresolved_fixture.py` + 2 new discrepancy-leg
regression tests in `test_admin_review_service.py`). **0 failed, 0 new skips, 5 xfailed**
(unchanged — the never-implemented Phase 31 stubs).

```
$ python3 -m compileall -q pipeline api scripts tests alembic
$ echo $?
0
```

```
$ npm --prefix app run check
...
COMPLETED 812 FILES 0 ERRORS 37 WARNINGS 11 FILES_WITH_PROBLEMS
```

0 errors, 37 warnings — unchanged from the 49-03/49-04/49-05 baseline (the `readonlyMode` split
touched no new warning-producing pattern).

```
$ git diff --stat api/domain/trust.py
(empty)
$ grep -Ev '^\s*#' api/domain/authority.py | grep -Ec 'import (fastapi|sqlalchemy|alembic)'
0
$ ./.venv/bin/alembic current
0029 (head)
```

`api/domain/trust.py` byte-identical throughout the phase; `api/domain/authority.py` still
imports nothing beyond its own dependencies; no new migration authored.

---

## 7. Requirement traceability

Cross-checked against `49-VALIDATION.md`'s requirement-to-command contract table (§ Per-Task
Verification Map). One divergence found and recorded, not silently substituted.

| Requirement | Delivering plan(s) | `49-VALIDATION.md`'s command | Actual command run | Result | Divergence |
|---|---|---|---|---|---|
| REVIEW-01 | 49-01 / 49-02 / 49-03 | `pytest api/tests/test_review_state_schema.py -x` | same | 6 passed | none |
| REVIEW-02 | 49-04 / 49-06 | `pytest api/tests/test_authority_matrix.py -x` | same | 67 passed | none — plus this plan's own live D-32 walkthrough (§5) |
| REVIEW-03 | 49-01 / 49-05 / 49-06 | `pytest api/tests/test_admin_review_service.py -x` | same | 30 passed | none |
| REVIEW-04 | 49-01 / 49-04 / 49-05 / 49-06 | `pytest api/tests/test_admin_review_service.py::test_resolve_recomputes_trust -x` | `pytest api/tests/test_admin_review_service.py -x` (whole module — no test named `test_resolve_recomputes_trust` exists) | 30 passed | **YES** — `49-VALIDATION.md` names a test function that was never written under that name; the actual coverage for "resolve action recomputes trust" is `test_patch_confirm_advances_review_state_and_recomputes_tier` (49-01) plus the confirm/confirm_unattributable/reflag recompute assertions in the same module (49-04). Recorded here rather than quietly matched. |
| REVIEW-05 | 49-02 | `pytest api/tests/test_legacy_review_mechanism_removed.py -x` | same | 2 passed | none |
| D-34 | 49-04 | `pytest api/tests/test_trust_public_leak_ban.py -x` | same | 59 passed | none |

Supplementary coverage this table doesn't name individually: `test_phase49_cleanup_contract.py`
(20 passed, popover/status-card/help-page source contracts), `test_phase49_review_ui_contract.py`
(14 passed, the queue screen's structural contract plus 2 of 4 backstop tests),
`test_admin_dev_unresolved_fixture.py` (9 passed, this plan's own D-33a seeder).

---

## 8. Threat traceability

| Threat Ref | Where the mitigation actually lands | Test |
|---|---|---|
| T-49-authority | `api/domain/authority.py::decide_write` (fail-closed `UNKNOWN` rung, equal-or-lower authority never overwrites); `api/services/admin_review.py::apply_participant_value_change`/`apply_person_value_change` (the one gate) | `api/tests/test_authority_matrix.py` (67 tests, exhaustive rank×rank×differs matrix + named behavior tests) plus this plan's live §5 walkthrough |
| T-49-idor | Scoped SELECT-then-UPDATE repeated in the WHERE of every write (`resolve_participant_review`, `resolve_person_review`, `apply_participant_value_change`, `close_open_discrepancies` all filter by both the row's own id AND its parent scope) | `api/tests/test_admin_review_service.py`, `api/tests/test_authority_matrix.py` |
| T-49-massassign | `api/schemas/admin_review.py::ReviewActionRequest` (closed three-value `Literal`, no field name/target id/value from the client); this plan's own `POST /api/admin/dev/seed-unresolved-speaker` has no request body/query/header at all (target conversation is a module constant) | `api/tests/test_authority_matrix.py`; this plan's `api/tests/test_admin_dev_unresolved_fixture.py` (`conversation_id` grep gate) |
| T-49-leak | `api/tests/test_trust_public_leak_ban.py`'s `BANNED_KEYS` (7 keys, 59 parametrized cases) plus an AST import ban on `api.domain.authority`/`api.schemas.admin_review` from public schema modules | `api/tests/test_trust_public_leak_ban.py` |

This plan's own threat register (`49-06-PLAN.md` frontmatter) names four scoped-to-this-plan
refs reusing the same `T-49-*` ids for the seeder specifically — all four are `mitigate` and
verified by `api/tests/test_admin_dev_unresolved_fixture.py`'s named tests plus the grep gates in
this plan's own Task 1 acceptance criteria (all passing, confirmed in the Task 1 commit).

---

## 9. Consolidated outstanding human-verification items

Every browser-based verification this phase could not complete, in one list, for a single
sitting. All are recorded in `.planning/WINDOWS.md` (`kind: unrun-verify`) so they are visible at
ship time. None was worked around; this sandbox's permission policy denies reading `.env`
(`ADMIN_USERNAME`/`ADMIN_PASSWORD`/`SESSION_SECRET`), so no authenticated `/admin/**` browser
session was reachable by any plan in this phase.

1. **[49-01]** Confirm-vs-"Resolve speaker"-link conditional rendering on `/admin/review`, not
   re-verified live since the tracer feedback gate fix.
2. **[49-03]** `CreatePersonPopover` Bench/Advocate side-inheritance walkthrough: toggle a row to
   Bench, open "Create new bench person," confirm Bench pre-selected, close/reopen, create a
   person, confirm the Resolved-As box shows the name; repeat on an Advocate row.
3. **[49-03]** `/admin/help` visual + apolitical read-through: badge colors, no horizontal scroll
   at 375px, no ranking/comparison language by eye.
4. **[49-05]** The full `/admin/review` screen's seven-item walkthrough: tab switching; filter
   composition surviving a back-button press and the active-filter indicator; expand/collapse
   including the zero-constituent blockers fallback; Confirm/Confirm-as-unattributable/Re-flag
   acting on the right row with D-26's stay-visible behavior; all five dashboard StatCards sitting
   evenly in one row; the StatCard's singular/zero-state link text; no horizontal scroll at 375px.
5. **[49-06]** 26-UAT Test 26 — the Speakers card's "Unresolved — choose a role" placeholder and
   disabled Save button, on the now-live-and-reachable data state (§2/§3).
6. **[49-06]** 14-UAT Test 8 — the non-interactive avatar for an unresolved utterance. Requires
   BOTH the seeded state AND a deliberate publish step this seeder does not perform (§3).
7. **[49-06]** D-32's authority-conflict walkthrough — fully verified end-to-end at the data/API
   layer (§5), including a real defect found and fixed; the Discrepancy badge's actual visual
   rendering was never observed.
8. **[49-06]** The new "Seed unresolved speaker" Dev Tools button and its success line — backend
   and form action fully tested; the button's rendering/behavior was never observed.

**Recommended single-sitting order for a human:** (a) open `/admin`, click Reset to Fixture, then
Seed unresolved speaker — confirms item 8 and sets up items 5/7 in one motion; (b) open the
Complexity fixture's argument edit page — confirms item 5; (c) open `/admin/review` — confirms
items 1, 4, 7; (d) exercise the `CreatePersonPopover`/`/admin/help` flows on any argument — items
2, 3; (e) publish the Complexity fixture and view its public page — item 6 (understand this leaves
a fixture in a modified state until the next reset).

---

## 10. Backstop and unresolved items

**Four UI-SPEC backstop statements** (all from 49-05, each pinned by a held-out test rather than
left as an unverifiable assertion):

| Statement | Test |
|---|---|
| E1 zero-one-many: `'{N} constituent{s} need review'` renders correctly at both 1 and many | `test_phase49_review_ui_contract.py::test_backstop_E1_attention_count_keys_singular_plural_on_strict_equality_one` |
| E5 zero-one-many: one-block vs. many-block constituent layout shares one `{#each}` loop, 16px gap | `test_phase49_review_ui_contract.py::test_backstop_E5_constituent_blocks_share_one_each_loop_with_16px_gap` |
| E6 partial: a one-sided discrepancy (missing existing or incoming value) never renders an empty quoted pair | `test_admin_review_service.py::test_backstop_E6_partial_one_sided_discrepancy_serializes_null_not_empty_string` |
| E6 long-text: an unusually long discrepancy value round-trips untruncated, no row-breaking | `test_admin_review_service.py::test_backstop_E6_long_text_discrepancy_value_round_trips_untruncated` |

**Two `unclassified` edge-probe rows** (both still carried as flagged, unresolved planner
assumptions — neither auto-resolved nor dropped):

- **REVIEW-02** (surfaced in 49-04): when a re-import disagrees with a value that has ALREADY been
  disagreed with and resolved, is the fresh discrepancy a new row or a reopen of the old one?
  49-04 took the new-row reading (D-15's per-row `resolved_at` exists precisely so a repeat
  disagreement is distinguishable) and added no UNIQUE constraint on the natural key. Still open
  for operator confirmation.
- **REVIEW-05** (surfaced in 49-02): what does "no parallel mechanism" mean for *historical*
  artifacts? 49-02's reading — migration files, migration-specific test modules, and `downgrade()`
  bodies are history and exempt; everything else is a live parallel mechanism — is implemented and
  tested but was never operator-confirmed as the intended reading.

**Planner assumptions recorded across the six plans, current status:**

- Plan 49-01: verify-module substitution (named module didn't exist) — resolved, documented,
  no outstanding action.
- Plan 49-02: `test_admin_jobs_service.py`'s two D-18 regression failures — **fixed** in 49-04
  (WINDOWS entry 11).
- Plan 49-04: the `must_clear_regression`'s prescribed fix (route through operator/manual
  authority) was itself wrong; the actual fix (provenance backfill) is documented and tested —
  closed, no outstanding action.
- Plan 49-04/49-05: the frontend `readonlyMode` split — **fixed** in 49-06 (this plan; see the
  `readonlyMode` split commit and the closed todo).
- Plan 49-05: Person's provenance-note format deviates from the plan's literal spec
  (`{Source} · {confidence}` instead of `{Source} · {method}`, since `Person` has no `method`
  field) — resolved, documented, no outstanding action.
- Plan 49-06: this plan's own two findings (§1 corrected premise, §5c discrepancy-inclusion gap)
  — both resolved within this plan.

---

## 11. Open after this phase

- **All eight consolidated human-verification items (§9)** — genuinely blocked on authenticated
  browser access this sandbox denies, not on any known code defect. Every underlying data/API
  layer they depend on has been verified by this plan.
- **14-UAT Test 8's second precondition** (the Complexity fixture must be deliberately published
  to reach the public chat page) is a real, permanent gap between what this seeder does and what
  that UAT test needs — recorded, not silently closed by inaction.
- **The two `unclassified` edge-probe rows (§10)** remain open for operator confirmation; neither
  blocks this phase's own delivered behavior.
- **`.planning/todos/pending/2026-08-18-pdf-provenance-live-fixture-verification.md`** — unrelated
  to this phase, still deferred per the corpus-first scope decision.
- **This session's discovery that `TEST_DATABASE_URL` and `DATABASE_URL` resolve to the same
  underlying Postgres database in this sandbox** (both hit database OID 17111 — see §6's
  methodology note) is worth a look before Phase 50: running a direct verification script against
  the "dev" database while a pytest run is also in flight against "the test database" is NOT
  isolated here the way the codebase's own conftest.py comments assume it is elsewhere. Not a
  code defect; a sandbox-environment fact future executors should know before repeating the
  concurrency mistake this plan made once.
