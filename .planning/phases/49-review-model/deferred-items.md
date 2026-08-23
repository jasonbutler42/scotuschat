# Deferred Items — Phase 49 (out of scope for 49-02)

## `api/tests/test_admin_jobs_service.py` — two trust-tier regression tests broken by plan 49-01's D-18 change, intersecting a deliberately-deferred PDF-pipeline wiring gap

**Found during:** 49-02 Task 3, running the full `api/tests -q` suite for the first time
since plan 49-01 landed.

**Failing tests:**
- `test_resolve_job_recomputes_tier_when_last_speaker_resolves`
- `test_repeated_writer_call_leaves_tier_unchanged`

Both assert `argument.trust_tier is TrustTier.TRUSTED` after `resolve_job` /
`update_resolve_row_for_job` (both in `api/services/admin_jobs.py`) resolve or edit an
`ArgumentParticipant` row; both now observe `TrustTier.UNCERTAIN` instead.

**Root cause:** Plan 49-01 (D-18) changed `api/services/trust.py::_load_constituents` to
feed `derive_tier` a real `(source, method, review_state)` triple for every
*resolved* `ArgumentParticipant` row, instead of contributing nothing. Neither
`resolve_job` nor `update_resolve_row_for_job` ever writes `ArgumentParticipant.source`/
`.method` — only `person_id` (and, for the latter, `side`/`descriptor`) — so a participant
resolved through either path now has `source=NULL, method=NULL`, and
`derive_tier("", "", "unreviewed")` floors to `UNCERTAIN`. This was silently latent because
49-01 never ran `api/tests/test_admin_jobs_service.py` in its own verification.

**Why not fixed here:** 49-CONTEXT.md D-20 locks the exact `source`/`method` mapping for
every participant-resolution mechanism that exists TODAY — corpus auto-match (`corpus`/
`direct`), PDF alias-table HIT (`pdf_pipeline`/`normalized`, explicitly **not yet wired**,
per the same document's "Out of scope" list: "Wiring the PDF alias-HIT participant method;
the mapping is recorded, not built (D-20), consistent with the corpus-first scope
decision"), and operator popover assignment (`admin.py:1423`, unchanged by design, D-22).
Neither `resolve_job` nor `update_resolve_row_for_job` appears in that table at all — there
is no locked decision for what provenance an admin-driven resolve-job/Resolve-card action
should stamp. Inventing one here would be a new architectural decision (Rule 4), not a bug
fix, and would risk conflicting with whatever Phase 50's corpus-first PDF-pipeline wiring
plan eventually decides for this exact code path. Neither file
(`api/services/admin_jobs.py`, `api/tests/test_admin_jobs_service.py`) is in plan 49-02's
`files_modified` list, and the fix genuinely requires a decision this plan has no mandate to
make.

**Contrast with the fix this plan DID make:** `pipeline/commands/import_convokit.py`'s
`ArgumentParticipant` creation had the exact same NULL-source/method gap and was fixed in
this plan (see 49-02-SUMMARY.md) — that fix was in-scope because it implements an
ALREADY-LOCKED D-20 mapping row (corpus resolution -> `corpus`/`direct` -> TRUSTED) in a file
already in this plan's `files_modified` list, not a new decision.

**Status:** open — out of scope for 49-02. Candidate follow-up: either fold into whatever
plan wires the PDF-pipeline participant provenance (D-20's deferred row), or raise as its
own small decision — "what source/method (if any) should an admin-driven resolve_job/
Resolve-card resolution stamp on `ArgumentParticipant`?" — via `/gsd-review-backlog` or a
phase-49 cleanup plan.
