# Phase 48 — Evidence Record

**Plan:** 48-09 (live fixture reseed, zero-drift proof, full-suite gate, requirement
traceability, operator sign-off)
**Recorded:** 2026-08-20

This file is the phase's evidence-of-record. Every command below is transcribed verbatim
(or with only credentials redacted); no threshold was adjusted to make a check pass. Two
findings surfaced during this run that the plan's own must-haves did not anticipate — they
are recorded in full under **Findings**, not smoothed over.

---

## 1. Environment

```
$ ./.venv/bin/python -m alembic current
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
0027 (head)
```

Resolved database name (from `DATABASE_URL`, credentials redacted): **`scotus`** — the
local dev database. Confirmed before running the destructive reset (T-48-RESETDB
precondition).

---

## 2. Live reseed

```
POST /api/admin/dev/reset-to-fixture
Header: X-Admin-Token: <redacted>
```

Wall-clock duration: ~112s (consistent with the documented 80-120s estimate for a real
four-pass corpus reset).

Response body (verbatim):

```json
{
    "fixtures": [
        {
            "conversation_id": "15169",
            "case_name": "Baltimore & Ohio Railroad Company v. United States",
            "role": "Complexity",
            "argument_id": 1784,
            "argument_status": "candidate",
            "admin_job_status": "paused"
        },
        {
            "conversation_id": "13015",
            "case_name": "Archawski v. Hanioti",
            "role": "Draft",
            "argument_id": 1785,
            "argument_status": "draft",
            "admin_job_status": "completed"
        },
        {
            "conversation_id": "18897",
            "case_name": "Anderson v. Liberty Lobby, Inc.",
            "role": "Published",
            "argument_id": 1786,
            "argument_status": "published",
            "admin_job_status": "completed"
        },
        {
            "conversation_id": "22372",
            "case_name": "Abbott v. United States",
            "role": "Mid-pipeline",
            "argument_id": 1787,
            "argument_status": "candidate",
            "admin_job_status": "running"
        }
    ]
}
```

No `ResetIncompleteError`; all four fixtures landed at their target state
(candidate/draft/published/candidate) with a paired `AdminJob` each.

---

## 3. Fixture state table (queried directly, post-reseed)

Query: for each `oyez_transcript_id` in `{15169, 13015, 18897, 22372}`, `arguments.id`,
`.status`, `.trust_tier`, `.published_at IS NULL`, `.resolved_at`, and the ordered
`argument_status_log` rows.

| oyez_transcript_id | arguments.id | status | trust_tier | published_at IS NULL | resolved_at |
|---|---|---|---|---|---|
| 15169 (Complexity) | 1784 | candidate | **uncertain** | true | NULL |
| 13015 (Draft) | 1785 | draft | trusted | true | 2026-08-20 17:04:20.872746+00 |
| 18897 (Published) | 1786 | published | trusted | false | 2026-08-20 17:06:17.841485+00 |
| 22372 (Mid-pipeline) | 1787 | candidate | **uncertain** | true | NULL |

Status matches the must-have exactly: `candidate` for 15169/22372, `draft` for 13015,
`published` for 18897. **`trust_tier` does NOT match** the must-have's "every fixture
argument's `trust_tier` reads `trusted`" for 15169 and 22372 — see **Finding 1** below.

### Status-log listing, ordered exactly as instructed (`created_at ASC, id ASC`)

**15169** (arguments.id=1784) — 1 row:

| status | override_reason IS NULL | trust_tier_at_transition | created_at | log.id |
|---|---|---|---|---|
| candidate | true | NULL | 2026-08-20 17:04:19.587356+00 | 104 |

One born-state row, oldest by construction (only row). Matches the must-have.

**13015** (arguments.id=1785) — 2 rows, **ordered by `created_at ASC, id ASC` as the plan
instructs**:

| status | override_reason IS NULL | trust_tier_at_transition | created_at | log.id |
|---|---|---|---|---|
| draft | true | NULL | 2026-08-20 17:04:20.872746+00 | 108 |
| candidate | true | NULL | 2026-08-20 17:05:09.085533+00 | 105 |

**This inverts the expected order** — under the plan's specified sort, the `draft` row
reads OLDER than the `candidate` birth row. See **Finding 2** below for the root cause and
the true (insertion-order) sequence.

**18897** (arguments.id=1786) — 3 rows, ordered by `created_at ASC, id ASC`:

| status | override_reason IS NULL | trust_tier_at_transition | created_at | log.id |
|---|---|---|---|---|
| candidate | true | NULL | 2026-08-20 17:05:41.787640+00 | 106 |
| draft | true | NULL | 2026-08-20 17:06:17.841485+00 | 109 |
| published | true | NULL | 2026-08-20 17:06:18.127102+00 | 110 |

Born state oldest, correctly ordered by both `created_at` and `id`. No override was used
(all `override_reason IS NULL`, as expected for a normal, non-blocked publish — 18897's
tier was already `trusted` by the time `publish_argument` ran).

**22372** (arguments.id=1787) — 1 row:

| status | override_reason IS NULL | trust_tier_at_transition | created_at | log.id |
|---|---|---|---|---|
| candidate | true | NULL | 2026-08-20 17:06:17.139810+00 | 107 |

One born-state row, oldest by construction. Matches the must-have.

---

## 4. Zero-drift proof

```
$ ./.venv/bin/python -m pipeline recompute-trust --all
recompute-trust: 4 scanned, 4 unchanged, 0 changed.

$ ./.venv/bin/python -m pipeline recompute-trust --all
recompute-trust: 4 scanned, 4 unchanged, 0 changed.
```

**`scanned` (4) equals the number of arguments the reseed created. `changed` is 0, twice in
a row.** This is the phase's central, falsifiable claim (D-09/D-21/T-48-VACUOUSGATE): every
writer path (specifically writer #1, corpus import birth, per 48-RESEARCH.md's "Complete
Writer-Path Enumeration") stamped `trust_tier` correctly at write time — including the two
fixtures that stamped `uncertain` rather than `trusted` (Finding 1). The check is not merely
"nothing drifted" on an empty scan; it is "nothing drifted" on a full, real four-argument
scan, and the same zero-changed result reproduces identically on the second run
(idempotence).

---

## 5. Findings

These are genuine discoveries from live evidence-gathering, not defects introduced by this
plan (48-09's `files_modified` is limited to this evidence file — no source code was
changed to produce or investigate either finding). Per the plan's own prohibition
("Do not weaken any assertion to make the gate pass... is a finding to fix in the owning
plan, not a threshold to adjust here"), both are reported as found.

### Finding 1 — Two of the four corpus fixtures read `uncertain`, not `trusted`

**What the plan expected:** "TRUST-01/D-21: after the reseed, the corpus fixture arguments
read `trust_tier = trusted`" (must_haves.truths) and Task 1's `<action>`: "If step 3 shows
any fixture's tier as something other than `trusted`... Corpus import mints a `Person` for
every corpus speaker, so an `uncertain` corpus fixture means a writer or the derivation is
wrong."

**What was observed:** 15169 (Complexity) and 22372 (Mid-pipeline) both read `uncertain`.
13015 (Draft) and 18897 (Published) both read `trusted`.

**Investigation.** `summarize_tier_blockers` against the live rows:

```
argument 1784 (15169): [{'code': 'unresolved_utterance_speaker', 'count': 25}]
argument 1787 (22372): [{'code': 'unresolved_utterance_speaker', 'count': 1}]
```

`recompute-trust --argument-id <id> --dry-run` confirms both are `1 scanned, 1 unchanged,
0 changed` — the tier is stable, not drifting; it is being derived correctly given the
constituent data.

Tracing the 25 and 1 unresolved rows to `pipeline/commands/import_convokit.py:1043-1150`:
ConvoKit's own corpus data carries an "unattributed speaker" sentinel (e.g. `<INAUDIBLE>`,
crosstalk) that the importer resolves to `participant = None` by design (line 1057's
comment: *"a speaker can legitimately resolve to None (ConvoKit's own unattributed-speaker
sentinel)"*), landing the row with `is_stage_direction=False`, `person_id=None` — this is
NOT the same code path as a stage direction (which D-12 excludes from the floor), so D-11's
"an unresolved speaker floors the argument to UNCERTAIN" applies exactly as designed. This
importer behavior predates Phase 48 (Phase 29's counter `unattributed_speakers_skipped`
already tracks it).

**Conclusion.** The plan's own assumption — "corpus import mints a Person for every corpus
speaker" — is not universally true of the real corpus: ConvoKit's unattributed-speaker
sentinel is a genuine, pre-existing exception to that claim, and 15169 was independently
selected (per `.planning/FIXTURES.md`, `high_speaker_dedup`/`multi_advocate_resolution`
flags) for reasons unrelated to this property — it happens to also contain unattributed
rows. This is **not a Phase 48 code defect**: `derive_tier`/`floor_tier`/
`recompute_argument_tier` are all working exactly as D-07/D-11/D-12 specify, and the
zero-drift proof above confirms the stamp is stable and correct for the data as it exists.
The defect, if any, is in the **plan's and D-21's stated expectation**, not in delivered
code.

**A second-order consequence worth flagging:** D-21 rejected a synthetic unresolved-speaker
fixture as "partly synthetic" on the premise that "corpus import mints a Person for every
corpus speaker." That premise is false — 15169 (an already-existing, real, non-synthetic
fixture) genuinely contains 25 unattributed-speaker utterances right now, live in the reseed
data. This means STATE.md's "14-UAT Test 8" and "26-UAT Test 26" (both blocked on "an
argument containing an unresolved speaker, which has never existed") may already be
answerable using the existing Complexity fixture rather than requiring a new one — worth a
follow-up look before assuming that gap needs new fixture work.

**Disposition:** reported here; not silently fixed; not treated as a Phase 48 code defect;
flagged for operator confirmation at the Task 3 checkpoint (see below) and recorded for
`/gsd-verify-work`.

### Finding 2 — The Draft fixture's `resolved_at` / birth-log `created_at` carry a stale timestamp

**What was observed:** 13015's `resolved_at` (2026-08-20 17:04:20.872746+00) and its
`draft`-transition `ArgumentStatusLog.created_at` (same value, to the microsecond) are
EARLIER than its own `candidate` birth-log `created_at` (17:05:09.085533+00) — even though
the birth log was written to the database first (lower primary key: `log.id=105` for
`candidate` vs. `log.id=108` for `draft`). Sorting strictly by `created_at ASC` (as the
plan's action text specifies) therefore inverts the sequence, showing `draft` before
`candidate`.

**Root cause.** Both `resolved_at=func.now()` (the `Argument` UPDATE) and
`created_at=server_default=func.now()` (the `ArgumentStatusLog` INSERT) are evaluated inside
`api/services/admin_jobs.py::approve_job`. PostgreSQL's `now()` returns the **transaction's**
start time, not per-statement wall-clock time. `api/services/admin_dev.py::reset_to_fixture`
reuses ONE FastAPI `AsyncSession` (its own `db` argument) across the entire per-fixture
verification loop (steps 3-4: a read-only `SELECT` against `Argument`/`AdminJob` for each of
the four fixtures, back-to-back, with no commit between them). That session's transaction
opens on the FIRST such `SELECT` (right after 15169's import lands, ≈17:04:20) and stays open
— uncommitted — through the rest of the verification loop for all four fixtures. When state
realization (step 5) then calls `jobs_service.approve_job(db, draft_job_id)` for 13015 (the
FIRST write on that same session), its `UPDATE`/`INSERT` statements run inside that SAME
stale, still-open transaction, so `func.now()` returns the transaction's ≈17:04:20 start
time rather than the real wall-clock time the approval actually happened (≈17:05:09, after
all four corpus imports had completed). `approve_job`'s own `db.commit()` (line 616) then
ends that transaction, so the very next write on the same session — `approve_job` +
`publish_argument` for 18897 — opens a fresh transaction and gets an accurate, current
`now()` (confirmed: 18897's `resolved_at`, draft-log `created_at`, and published-log
`created_at` are all self-consistent with real wall-clock progression).

**Scope of impact.** This is systematic, not a one-off: every `reset_to_fixture` reseed will
stamp the Draft fixture's `resolved_at` and birth→draft transition `created_at` with a stale
timestamp (the read-verification transaction's start time), while every subsequent
transition in the same reset call gets an accurate one. The TRUE chronological (insertion)
order is still correct — `ORDER BY id ASC` shows `candidate` (log.id=105) before `draft`
(log.id=108) — so the underlying invariant ("the argument was born before it was approved")
genuinely holds; only the **stored timestamp value** is wrong, which matters because several
of this plan's own acceptance criteria and future audit/reporting logic key on
`created_at`/`resolved_at` rather than primary-key order.

**Disposition — UPDATED after operator direction mid-plan.** This finding has two distinct
halves, and only one was in scope to fix here:

1. **Display-ordering half — FIXED in this plan.** `api/services/admin_arguments.py`'s
   `get_argument_detail` (~line 448) built the operator-facing Status History list with
   `.order_by(ArgumentStatusLog.created_at.asc(), ArgumentStatusLog.id.asc())` — `created_at`
   as the PRIMARY sort key. Because `created_at` can be stale (as demonstrated live above),
   this meant the Status History page would have rendered the Draft fixture's transitions
   **backwards** (draft before candidate) had an operator opened it during this reseed cycle.
   Fixed to `.order_by(ArgumentStatusLog.id.asc())` — `id` is monotonic by construction
   (auto-increment primary key) and is the only key that reliably preserves insertion order
   for this append-only table, regardless of any writer's transaction-timing behavior (not
   just `reset_to_fixture`'s). A regression test
   (`api/tests/test_admin_arguments_service.py::test_get_argument_detail_status_log_orders_by_id_not_created_at`)
   constructs the exact skew explicitly (independent of reset timing — two log rows with
   `created_at` values deliberately set to disagree with insertion order) and asserts the
   returned order matches insertion order. Confirmed RED against the old
   `created_at`-first ordering (assertion failed, returning draft-then-candidate) and GREEN
   against the fix. Commit: `<see Task Commits in 48-09-SUMMARY.md>`.

   **Other append-only-style queries checked for the same shape** (`grep -rn ".order_by(" |
   grep -i created_at`, excluding tests): two more call sites in `api/services/admin_jobs.py`
   order by `created_at` first — `list_jobs` (`AdminJob.created_at.desc()`, line ~279) and
   `get_run_id_for_step` (`ImportRun.created_at.desc()`, line ~410). Neither was changed:
   `list_jobs` orders many *distinct* `AdminJob` entities (each normally created in its own
   separate transaction) for a "most recent first" dashboard list, not a single entity's
   append-only history, so the specific stale-shared-transaction failure mode demonstrated
   above does not clearly apply. `get_run_id_for_step` selects the latest `ImportRun` for one
   `(argument_id, step)` pair — structurally closer to the `ArgumentStatusLog` shape (an
   argument can accumulate multiple `ImportRun` rows), but each `ImportRun` write in the
   pipeline's normal operation (`ingest`/`parse`/`resolve` as separate CLI subprocess
   invocations) runs in its own transaction, so there is no live reproduction of the same
   defect for this path today. Both are listed here as follow-up candidates for whoever next
   touches `admin_jobs.py`, not fixed speculatively.

2. **The underlying `reset_to_fixture` stale-transaction cause — NOT fixed, remains open.**
   The `resolved_at` and `created_at` VALUES STORED for the Draft fixture are still stale
   (unchanged from §3's table above — this plan did not re-run the reseed and did not modify
   `api/services/admin_dev.py::reset_to_fixture`'s session/transaction structure, per explicit
   operator direction: it is dev-only, and the orchestrator is filing it as a separate todo).
   Any future direct read of `resolved_at` or `argument_status_log.created_at` for a freshly
   reseeded Draft fixture will still see the transaction-start timestamp, not the real
   transition time, until that separate fix lands. The `id`-ordering fix above corrects how
   the data is DISPLAYED; it does not correct what value is STORED.

---

## 6. Phase gate

### 6a. Full suite

First run (before the Finding 2 display-ordering fix below):

```
$ ./.venv/bin/python -m pytest
...
1208 passed, 5 xfailed, 12 warnings in 323.88s (0:05:23)
```

Compared against STATE.md's 2026-08-18 baseline (1049 passed / 5 xfailed / 0 failed /
0 skipped): **passed 1208 > 1049** (this phase added tests), **failed 0**, **xfailed 5**
(unchanged — the never-implemented Phase 31 stubs, no new stub landed), **skipped 0** (not
mentioned in the summary line, which pytest omits when the count is zero — confirmed by the
absence of any "skipped" category). This also matches the number the phase's own upstream
plans (48-01 through 48-10) already recorded as the running total, so this is a
re-confirmation, not a surprise.

**Second run, after the Finding 2 display-ordering fix** (`api/services/admin_arguments.py`'s
`get_argument_detail` status-log ordering, plus its one new regression test):

```
$ ./.venv/bin/python -m pytest
...
1209 passed, 5 xfailed, 12 warnings in 239.02s (0:03:59)
```

1209 = 1208 + the one new regression test
(`test_get_argument_detail_status_log_orders_by_id_not_created_at`). Still 0 failed, still
5 xfailed, still 0 skipped. This is the number that stands as this plan's final full-suite
result.

### 6b. Build

```
$ python3 -m compileall -q pipeline api scripts tests alembic
$ echo $?
0
```

### 6c. Frontend check

`node` was on PATH for this run (v24.18.0, nvm-managed):

```
$ cd app && npm run check
...
COMPLETED 806 FILES 0 ERRORS 36 WARNINGS 10 FILES_WITH_PROBLEMS
```

0 errors, 36 warnings — matches the pre-existing warning count recorded before this plan
began (plan 48-08's Python contract test exists as the Node-free fallback gate but was not
needed this run since `node` was reachable).

### 6d. Completeness greps

```
$ grep -rn "ArgumentStatusEnum\.PIPELINE" api/ pipeline/ scripts/ --include=*.py | grep -v "/tests/" | grep -v "^api/models/models.py:"
(no output)

$ grep -rnE "status *[!=]== *'pipeline'" app/src
(no output)

$ grep -rn "ArgumentStatusEnum\.PIPELINE" api/tests/ pipeline/tests/ --include=*.py | wc -l
32
```

Both completeness greps return no lines — no live comparison against the retired `pipeline`
born state survives outside the enum declaration, deliberate comments, and test fixtures.
The retired enum member still has 32 deliberate test-fixture references (D-01: the dead
value stays defined forever, never purged).

### 6e. Wave 0 module confirmation

```
$ ./.venv/bin/python -m pytest api/tests/test_trust_domain.py -q
44 passed in 2.05s

$ ./.venv/bin/python -m pytest api/tests/test_trust_recompute.py -q
18 passed in 10.49s

$ ./.venv/bin/python -m pytest api/tests/test_admin_arguments_service.py::test_delete_argument_cascades_argument_status_log api/tests/test_admin_arguments_service.py::test_delete_argument_cascades_multiple_status_log_rows -q
2 passed in 2.68s
```

All three Wave 0 items from 48-VALIDATION.md exist, run individually, and exit 0 with
0 skipped. `./.venv/bin/python -m pytest api/tests/test_trust_domain.py
api/tests/test_trust_recompute.py -q` together: 62 passed, 0 skipped (satisfies Task 2's
acceptance criterion verbatim).

### 6f. Requirement traceability

| Requirement | Delivering plan(s) | Automated command | Result |
|---|---|---|---|
| TRUST-01 | 48-01 | `./.venv/bin/python -m pytest api/tests/test_trust_domain.py` | 44 passed |
| TRUST-02 | 48-01 / 48-04 / 48-05 / 48-06 | `./.venv/bin/python -m pytest api/tests/test_trust_recompute.py` + §4's zero-drift run (4 scanned, 0 changed, ×2) | 18 passed + zero-drift confirmed |
| TRUST-03 | 48-02 / 48-04 / 48-05 | `./.venv/bin/python -m pytest pipeline/tests/test_import_convokit_core.py` + §3's fixture table (15169/22372 born `candidate` with a single, self-consistent birth log) | 39 passed + fixture table recorded |
| TRUST-04 | 48-07 / 48-08 | `./.venv/bin/python -m pytest api/tests/test_published_gate.py` | 31 passed |
| TRUST-05 | 48-07 / 48-08 | `./.venv/bin/python -m pytest api/tests/test_admin_arguments_routes.py` | 29 passed |
| D-22 (carried defect, cascade fix) | 48-02 | `./.venv/bin/python -m pytest api/tests/test_admin_arguments_service.py::test_delete_argument_cascades_argument_status_log api/tests/test_admin_arguments_service.py::test_delete_argument_cascades_multiple_status_log_rows` | 2 passed |
| D-23 (public-leak ban) | 48-03 / 48-07 | `./.venv/bin/python -m pytest api/tests/test_trust_public_leak_ban.py` | 11 passed |

`48-VALIDATION.md`'s `nyquist_compliant` and `wave_0_complete` flags are ready to flip to
`true` on the basis of §6e/§6f above — not flipped here, per this plan's own instruction that
`/gsd-validate-phase` owns that file.

---

## 7. Open items — what this phase did NOT close

- **14-UAT Test 8 and 26-UAT Test 26 remain open.** D-21 rejected a synthetic
  unresolved-speaker fixture as "partly synthetic." Finding 1 above shows the premise behind
  that rejection is not fully accurate — the existing Complexity fixture (15169) already
  contains 25 genuinely unresolved-speaker utterances — but this plan does not itself re-open
  or re-scope those UAT items; it only records the discrepancy for whoever picks them up next.
- **The PDF legs (`parse.py`, `resolve.py`) are wired but not live-verified**, per the
  corpus-first scope decision and the open todo
  `2026-08-18-pdf-provenance-live-fixture-verification.md`.
- **`derive_tier`'s `("operator", "manual")` rule is unreachable today** (no writer sets
  `source=operator`). **CONFIRMED by the operator on 2026-08-21** at the Task 3 checkpoint
  (step 7) — an operator-authored, unreviewed row derives VERIFIED, per the authority ladder.
  `api/domain/trust.py`'s module docstring updated to record this as an operator-confirmed
  derivation rule rather than an outstanding flagged assumption (logic unchanged). This
  closes plan 48-01's flagged assumption; no longer an open item as of this plan.
- **The `verification: backstop` truths across the plan set abstain rather than pass** — they
  cannot be discharged by any automated check in this repository (must_haves' own framing).
- **Finding 1 (two corpus fixtures read `uncertain`)** is not a defect in this phase's
  delivered code — `derive_tier` is correct and the plan's must-have assumption ("corpus
  import mints a Person for every corpus speaker") was wrong given ConvoKit's own
  unattributed-speaker sentinel rows. It does mean the plan's stated must-have ("every
  fixture argument's `trust_tier` reads `trusted`") is not literally true of 2 of 4
  fixtures — recorded as an open item to accept, not a defect to fix, and not silently
  narrowed to "the ones that matter."
- **Finding 2, display-ordering half, is FIXED** (see §5's updated Disposition) —
  `get_argument_detail`'s Status History query now orders by `id ASC`, with a regression
  test locking it. **The underlying cause remains open and unfixed by design**: the STORED
  `resolved_at` / `argument_status_log.created_at` values for the Draft fixture are still
  stale (confirmed unchanged after this fix — no reseed was run). `reset_to_fixture`'s
  session/transaction reuse in `api/services/admin_dev.py` was explicitly left untouched per
  operator direction (dev-only, being filed as a separate todo by the orchestrator). Two
  other `created_at`-first queries (`admin_jobs.py`'s `list_jobs` and `get_run_id_for_step`)
  were checked and NOT changed — see §5 Finding 2 for why each was judged not clearly the
  same defect; both are flagged as follow-up candidates.
- **A transient flake** was observed once in `test_published_gate.py`
  (`test_publish_succeeds_with_override_and_logs_reason_and_tier` plus the whitespace-only
  override cases) immediately after an executor run during plan 48-10; three consecutive
  re-runs and this plan's own full-suite run (§6a) were all clean. Suspected leftover
  `scotus_test` rows rather than a defect in the gate logic itself.
- **The unpublish-error-rendering fix (48-10)** is verified by static contract test only,
  never observed live — the failure path needs the backend call itself to fail. The operator
  accepted this on that basis (48-10-SUMMARY.md); not re-litigated here.
- **NEW (operator observation, Task 3 checkpoint step 2, 2026-08-21) — requested widening of
  Resolve-card editability scope, deliberately deferred out of Phase 48, not implemented
  here.** Operator's own words: *"The Resolve card doesn't have the same functionality once
  it's out of Candidate status. I should still be able to edit the people in an argument in
  any state EXCEPT when it's published."*

  - **Current rule:** editability keys on `status == CANDIDATE`. Sites found:
    `api/services/admin_people.py:968`
    (`editable = argument.status == ArgumentStatusEnum.CANDIDATE`),
    `api/services/admin_jobs.py:285`, and the frontend
    `readonlyMode = argument.status !== 'candidate'` in
    `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:294`.
  - **Requested rule:** editable in `candidate`, `draft`, and `unpublished`; read-only only
    when `published`.
  - **Critical caveat:** not every `!= CANDIDATE` check in this codebase is an editability
    guard. `api/services/admin_jobs.py:591` is `approve_job`'s double-approve guard and MUST
    stay CANDIDATE-only; `admin_jobs.py:719` and `:825` need individual classification too. A
    mechanical find-and-replace across every `CANDIDATE`-keyed check would break approve
    semantics.
  - **Second caveat:** editing participants changes trust-tier inputs, so
    `recompute_argument_tier` must fire on any newly-reachable edit path. Plan 48-04 wired
    recompute into the four `admin_jobs` writers under the assumption that those writers only
    ever ran against a CANDIDATE argument; widening editability makes those same write paths
    reachable in states (`draft`, `unpublished`) where they previously could not run, so that
    coverage needs re-checking rather than assumed to already hold.
  - **Workflow interaction to note:** editing an `unpublished` argument can drop its tier to
    `uncertain`, which then blocks re-publishing without a fresh override. That is correct
    behavior per D-16 (the override is never sticky), but it is a real, user-visible workflow
    consequence of the requested change, worth stating up front rather than discovering later.
  - **Not an oversight:** the CANDIDATE-only rule is a deliberate pre-existing design
    decision, not a bug. `api/services/admin_dev.py`'s fixture comments explicitly cite
    "resolve-card editability keys on Argument.status staying CANDIDATE" as an invariant the
    Complexity fixture's design preserves. Revising it is a design change requiring its own
    discussion/plan cycle, not a fix folded into this one.

---

## 8. Operator sign-off

<!-- OPERATOR-SIGNOFF-BEGIN -->

**Recorded:** 2026-08-21

The operator completed the live walkthrough against the reseeded dev database (unchanged
throughout this plan — no reseed was re-run) and returned the following, verbatim:

1. Candidates hidden from `/admin/arguments` — **PASS**.
2. Resolve card editable on the Complexity (candidate) fixture — **PASS**, with an
   observation recorded as a new open item above (Resolve-card editability scope), not
   implemented in this plan.
3. Status History order (candidate before draft) on the Draft fixture's detail page —
   **PASS**, confirmed after commit `1b7564a78` (the `id`-ordering fix).
4. Published fixture publicly visible at its `/cases/...` URL with no mention of trust,
   tier, or provenance on the public page — **PASS**.
5. `recompute-trust --all` transcript shows `scanned = 4`, `changed = 0` — **PASS**.
6. §7's open items (including both new findings from this plan) — **ACCEPTED**, as
   deliberately deferred rather than overlooked.
7. `derive_tier`'s `("operator", "manual")` rule (an operator-authored, unreviewed row
   derives VERIFIED) — **CONFIRMED**. This closes plan 48-01's flagged assumption. Recorded
   as an operator-confirmed derivation rule in `api/domain/trust.py`'s module docstring
   (logic unchanged, docstring wording only, commit recorded in 48-09-SUMMARY.md's Task
   Commits).

**Overall: APPROVED.** All 7 verification steps passed. The phase's central claim — every
argument is born a candidate with a logged birth transition, a materialized trust tier
recomputed by every writer at write time, and a promotion gate that is hard-blocked while
uncertain and overridable only with a deliberate, logged, non-sticky reason — is confirmed
live, on real corpus data, with the one display-ordering defect this plan's own live
verification surfaced (Finding 2) fixed and regression-tested before sign-off.

<!-- OPERATOR-SIGNOFF-END -->
