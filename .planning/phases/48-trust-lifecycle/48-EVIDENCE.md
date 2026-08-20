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

**Disposition:** a pre-existing latent bug in `api/services/admin_dev.py::reset_to_fixture`'s
session/transaction reuse, newly exposed by this plan's live verification, not introduced by
Phase 48's other plans and out of this plan's `files_modified` scope (`48-EVIDENCE.md` only).
Reported here, not fixed here. A `gsd-tools windows append --kind unmet-truth` entry and a
todo are the appropriate next step (see Open Items).

---

## 6. Phase gate

### 6a. Full suite

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
  `source=operator`) and awaits explicit operator confirmation, flagged in plan 48-01 and
  re-raised at the Task 3 checkpoint below (step 7).
- **The `verification: backstop` truths across the plan set abstain rather than pass** — they
  cannot be discharged by any automated check in this repository (must_haves' own framing).
- **Finding 1 (two corpus fixtures read `uncertain`)** is not a defect in this phase's
  delivered code, but it does mean the plan's stated must-have ("every fixture argument's
  `trust_tier` reads `trusted`") is not literally true of 2 of 4 fixtures — recorded, not
  silently narrowed to "the ones that matter."
- **Finding 2 (stale `resolved_at`/`created_at` on the Draft fixture)** is a newly-discovered,
  pre-existing latent bug in `reset_to_fixture`'s session/transaction handling, out of this
  plan's scope to fix. Recommend a `gsd-tools windows append --kind unmet-truth` entry and a
  todo file for a future plan (likely wherever `admin_dev.py` is next touched).
- **A transient flake** was observed once in `test_published_gate.py`
  (`test_publish_succeeds_with_override_and_logs_reason_and_tier` plus the whitespace-only
  override cases) immediately after an executor run during plan 48-10; three consecutive
  re-runs and this plan's own full-suite run (§6a) were all clean. Suspected leftover
  `scotus_test` rows rather than a defect in the gate logic itself.
- **The unpublish-error-rendering fix (48-10)** is verified by static contract test only,
  never observed live — the failure path needs the backend call itself to fail. The operator
  accepted this on that basis (48-10-SUMMARY.md); not re-litigated here.

---

## 8. Operator sign-off

Pending. See Task 3 checkpoint.

<!-- OPERATOR-SIGNOFF-BEGIN -->
<!-- Filled in once the operator responds to the Task 3 checkpoint. -->
<!-- OPERATOR-SIGNOFF-END -->
