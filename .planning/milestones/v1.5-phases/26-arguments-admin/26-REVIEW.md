---
phase: 26-arguments-admin
reviewed: 2026-07-08T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - api/routers/admin.py
  - api/schemas/admin_arguments.py
  - api/schemas/admin_jobs.py
  - api/services/admin_arguments.py
  - api/services/admin_jobs.py
  - api/tests/test_admin_arguments_routes.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_jobs_list.py
  - api/tests/test_admin_jobs_service.py
  - app/src/lib/components/RunStatusCard.svelte
  - app/src/routes/admin/arguments/+page.svelte
  - app/src/routes/admin/arguments/[id]/+page.server.ts
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/routes/admin/pipeline/+page.svelte
findings:
  critical: 3
  warning: 11
  info: 4
  total: 18
status: issues_found
---

# Phase 26: Code Review Report

**Reviewed:** 2026-07-08
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

This is a full, fresh re-review of the Phase 26 arguments-admin surface reflecting the
phase's complete current state — all six plans (26-01 through 26-06), including the
gap-closure plans that added `is_archived` badges (`RunStatusCard.svelte`,
`app/src/routes/admin/pipeline/+page.svelte`, `list_jobs`) and the Speakers/status-log
rework of the argument edit page. It supersedes and overwrites the prior partial
26-REVIEW.md (which covered only plans 26-01–26-04 pre-gap-closure).

Two Critical defects carried forward from the earlier review pass remain **unresolved**
in the current source (`rerun_job` silently orphaning locally-uploaded reruns; blank
`case_name`/`docket_number` being persisted with no non-empty validation anywhere in the
stack) — confirmed by direct re-inspection of the current files, not assumed from the
old report. This pass adds one new Critical (an unhandled unique-constraint violation in
`update_argument_metadata`), plus several Warnings not previously documented: non-atomic
status transitions that can double-write audit-log rows under concurrent requests,
missing `max_length` validation on several fields that mirror a precedent the code
already applied elsewhere (`ResolveRowUpdate.title`), and a client-side stale-state gap
in the Speakers editor. Several previously-flagged issues (advocate-row `colspan`
mismatch, docket-normalization duplication, the broad photo-validation `except`, the
photo-URL SSRF gap, `speakerSideById` staleness) were independently re-derived from the
current source during this pass and are confirmed still present.

## Critical Issues

### CR-01: `rerun_job` never spawns ingest for jobs originally uploaded to local disk

**File:** `api/routers/admin.py:1042-1076`, `api/services/admin_jobs.py:544-568`

**Issue:** `create_job`'s upload path (`api/routers/admin.py:301-313`) writes the PDF to
`data/uploads/{job.id}.pdf` and leaves both `spaces_key` and `pdf_url` `NULL` whenever
`settings.do_spaces_bucket` is falsy (local/dev mode). `rerun_job` (service,
`api/services/admin_jobs.py:544-568`) copies `pdf_url`/`spaces_key`/`original_filename`/
`source_dockets` onto the new `AdminJob`, but the router only spawns ingest for two of the
three possible source types:
```python
if new_job.spaces_key:
    spawn_pipeline_step("ingest", new_job.id, ["--spaces-key", new_job.spaces_key] + docket_args)
elif new_job.pdf_url:
    spawn_pipeline_step("ingest", new_job.id, ["--url", new_job.pdf_url] + docket_args)
```
There is no `else` branch, and the local file path itself is never persisted on `AdminJob`
in the first place — so even a bespoke local-file branch could not resolve where the
original PDF lives. For any job originally created via local-disk upload,
`POST /jobs/{id}/rerun` returns `202` with a fresh `PENDING/INGEST` `AdminJobResponse` —
giving every visual indication the rerun started — but no subprocess is ever spawned. The
new job sits at `PENDING` forever with no error surfaced anywhere (the poll endpoint's
`try_advance_ingest_to_parse` never fires because `status` never reaches `COMPLETED`).

**Fix:** Persist the resolved local file path on `AdminJob` at creation time (or a stable,
re-derivable location keyed by `job.id`), and add a third branch that copies/re-links the
original PDF and spawns ingest with `--local-file`. At minimum, until local-file rerun is
supported, `rerun_job` should raise `ValueError` (→ 422) for this case instead of silently
creating a job that can never progress.

### CR-02: Blank `case_name` / `docket_number` can be saved, corrupting slug and dedup-key data

**File:** `api/schemas/admin_arguments.py:205-223` (`ArgumentUpdate`),
`api/services/admin_arguments.py:444-461, 424-435` (`update_argument`),
`api/services/admin_arguments.py:780-795, 750-764` (`update_argument_metadata` /
`MetadataUpdate`), `app/src/routes/admin/arguments/[id]/+page.svelte:148-190`,
`app/src/routes/admin/arguments/[id]/+page.server.ts:126-127`

**Issue:** `ArgumentUpdate.case_name`/`.docket_number` are `Optional[str] = None` with no
non-empty constraint, and the service treats "not `None`" as "provided," not "non-empty":
```python
if body.case_name is not None:
    lead_case.case_name = body.case_name.strip()
    if argument.status == ArgumentStatusEnum.DRAFT:
        new_slug = _derive_slug(lead_case.case_name)   # _derive_slug("") == ""
        ...
        lead_case.slug = new_slug
```
```python
if body.docket_number is not None:
    new_docket = body.docket_number.strip()
    if new_docket != lead_case.docket_number:
        ...
        lead_case.docket_number = new_docket
        lead_case.docket_number_norm = new_docket
```
The `?/save` form action always sends a trimmed string for both fields — never
`undefined`/omitted:
```ts
const case_name = ((formData.get('case_name') as string) ?? '').trim();
const docket_number = ((formData.get('docket_number') as string) ?? '').trim();
```
and neither `<input>` has a `required` attribute. If an operator clears either field and
clicks "Save changes," the request carries `case_name: ""` / `docket_number: ""` — not
`None` — so the write proceeds. For a `DRAFT` argument, `_derive_slug("")` returns `""`
(confirmed against `pipeline/commands/ingest.py`'s `_derive_slug`, no length guard), and,
absent a same-empty-slug collision, the lead `Case` row ends up with `case_name=""` and
`slug=""`. `docket_number`/`docket_number_norm` can similarly be wiped to `""` regardless
of lifecycle status. This corrupts the case's public URL, its display title, and the
uniqueness semantics of `docket_number`, with no confirmation step and no recovery path
short of a direct DB fix. The identical "not-`None` means provided" gap exists in
`update_argument_metadata`'s `case_name`/`source_docket` handling, reachable via
`MetadataUpdate`.

**Fix:** Reject blank/whitespace-only values at the schema layer:
```python
from pydantic import field_validator

class ArgumentUpdate(BaseModel):
    case_name: Optional[str] = None
    docket_number: Optional[str] = None
    argued_date: Optional[str] = None

    @field_validator("case_name", "docket_number")
    @classmethod
    def _reject_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("must not be blank")
        return v
```
and add `required` to both `<input>` elements as UI-level defense-in-depth.

### CR-03: `update_argument_metadata` has no guard against the `(source_docket, question_number)` unique constraint — unhandled 500 instead of 422

**File:** `api/services/admin_arguments.py:714-798` (endpoint: `api/routers/admin.py:924-943`)

**Issue:** `Argument` carries `UniqueConstraint("source_docket", "question_number", name="uq_arguments_source_docket_question")`
(`api/models/models.py:199-207`). The pipeline's *create-run* flow protects against this
with a dedicated preflight endpoint (`GET /arguments/check-duplicate`, called by the
frontend before submit — see `app/src/routes/admin/pipeline/+page.svelte:76-104`). But
`update_argument_metadata` — the PATCH used by the job-detail metadata card to edit
`source_docket`/`source_dockets`/`question_number` on an *existing* argument — never
checks for a collision before writing, and the router only translates `ValueError` to 422
(`api/routers/admin.py:938-942`). If an operator edits a job's docket/question to a
combination that already belongs to a different argument, `db.commit()` raises an
unhandled `IntegrityError` → FastAPI's default 500 response. There is no global exception
handler for `IntegrityError` in `api/main.py`, so nothing upstream catches this.

**Fix:** Before writing, check for an existing different argument with the same
`(source_docket, question_number)` (reusing the same logic as
`check_duplicate_argument`), and raise `ValueError("docket_question_collision")` the same
way `update_argument` handles `slug_collision`/`docket_collision`:
```python
collision = await db.execute(
    select(Argument.id).where(
        Argument.source_docket == values_to_set.get("source_docket", argument.source_docket),
        Argument.question_number == values_to_set.get("question_number", argument.question_number),
        Argument.id != argument_id,
    )
)
if collision.scalar_one_or_none() is not None:
    raise ValueError("docket_question_collision")
```

## Warnings

### WR-01: Advocate row `colspan` does not cover all remaining table columns

**File:** `app/src/routes/admin/arguments/[id]/+page.svelte:425-433` (header), `:443` (advocate `<td>`)

**Issue:** The Speakers table header declares 5 columns (Name, Role, Title, Utterances,
Action). Bench rows correctly render 5 `<td>`s. The advocate branch renders one `<td>`
(Name) plus a single `<td colspan="3">` holding the Role `<select>`, Title `<input>`,
utterance count, *and* the Save `<button>` — 4 pieces of content packed into a cell that
only spans 3 columns, so advocate rows total 4 column-units against the header's 5. This
misaligns column boundaries whenever the Speakers list mixes bench and advocate rows, and
leaves the "Action" header with no dedicated cell on advocate rows.

**Fix:** Change `colspan="3"` to `colspan="4"`, or split the form's contents into
per-column `<td>` cells matching the header.

### WR-02: Duplicate, diverging docket-normalization logic between the router and the metadata-update service

**File:** `api/services/admin_arguments.py:750-762` vs `api/routers/admin.py:115-153`

**Issue:** `_normalize_dockets` in the router is the canonical strip/dedupe/order-preserving
normalizer and additionally rejects any docket value starting with `-`
(T-24-08 CLI-arg-injection defense). `update_argument_metadata` reimplements the same
strip/dedupe logic inline, without the leading-`-` rejection. No active injection path
exists today through this call site (it writes `Argument.source_dockets`, not the field
`_dockets_to_ingest_args` consumes for subprocess argv), but it is a maintenance hazard if
`source_dockets` is ever wired into a rerun/respawn path without re-deriving from this
already-"sanitized" value.

**Fix:** Extract one shared normalization helper (including the leading-`-` rejection) and
use it at both call sites.

### WR-03: `docket_number_norm` is not normalized consistently with ingest on admin edits

**File:** `api/services/admin_arguments.py:435-442`

**Issue:** `update_argument` sets `lead_case.docket_number_norm = new_docket` — the raw,
hyphen-containing value — while `pipeline/commands/ingest.py:385` computes
`docket_number_norm=docket.replace("-", "")` for newly-ingested cases. An admin-edited
docket therefore gets a `docket_number_norm` computed by a different rule than ingest
uses, risking any future normalization-consumer (duplicate detection, lookups) treating
equivalent dockets as different depending on whether the row was last touched by ingest or
by this admin PATCH.

**Fix:** Export ingest's normalization as a small reusable function (mirroring the
existing `_derive_slug` re-export pattern already used in this file) and call it here
instead of a bare `.strip()`.

### WR-04: Overly broad `except (UnidentifiedImageError, Exception)` masks all photo-processing errors

**File:** `api/routers/admin.py:695, 721`

**Issue:** `Exception` is already a superclass of `UnidentifiedImageError`, so listing both
is equivalent to a bare `except Exception:`. Both photo-processing code paths (file upload
and URL fetch) silently report *any* exception — a transient I/O error, a Pillow decompression-bomb
guard trip, an out-of-memory condition, or a genuine bug in this handler — to the
operator as "not a valid image," with no logging, making real failures indistinguishable
from actually-invalid uploads.

**Fix:**
```python
except UnidentifiedImageError:
    raise HTTPException(status_code=422, detail="Uploaded file is not a valid image.")
except Exception:
    logger.exception("Unexpected error validating uploaded image")
    raise HTTPException(status_code=422, detail="Uploaded file is not a valid image.")
```

### WR-05: Photo-by-URL fetch has no domain allowlist / private-range check (SSRF)

**File:** `api/routers/admin.py:704-716`

**Issue:** Unlike `_validate_pdf_url` (restricted to HTTPS + `*.supremecourt.gov`), the
photo-by-URL handler only checks `scheme == 'https'` before the server itself issues the
request:
```python
async with httpx.AsyncClient(timeout=10.0) as client:
    r = await client.get(photo_url, follow_redirects=False)
```
`follow_redirects=False` blocks the redirect-chasing SSRF variant only; there is still no
allowlist preventing a direct request to any HTTPS host reachable from the API host,
including internal/private endpoints that terminate TLS. This is gated behind the
admin token (which meaningfully lowers severity relative to an unauthenticated endpoint),
but it is a real gap relative to this same codebase's own precedent (T-07-01) for the
structurally identical `pdf_url` ingestion path.

**Fix:** Resolve the hostname and reject loopback/link-local/private ranges (RFC1918,
127.0.0.0/8, 169.254.0.0/16, ::1, fc00::/7) before fetching, or restrict to a configured
allowlist of trusted photo hosts, mirroring `_validate_pdf_url`.

### WR-06: Structural "guard" tests scan raw source text with a naive regex, including comments/docstrings

**File:** `api/tests/test_admin_arguments_service.py:137-154, 220-247`

**Issue:** `test_service_file_has_synchronize_session_false` compares an aggregate count of
`\b(update|delete)\(` matches against occurrences of the literal string
`"synchronize_session=False"` across the *whole module source*, including any
docstring/comment prose that happens to mention `update()`/`delete()`. This can pass even
when one specific new call is missing its guard (as long as aggregate counts balance by
coincidence), and can spuriously fail on unrelated prose edits.
`test_delete_argument_all_deletes_have_synchronize_session_false` narrows the scope to the
`delete_argument` function body, which reduces but does not eliminate the same class of
false-confidence (a comment mentioning `delete(` inside that function body would still
count toward the total).

**Fix:** Parse with `ast` and assert, for each `ast.Call` resolving to `sqlalchemy.update`/
`delete`, that the enclosing expression chains `.execution_options(synchronize_session=False)`
— or at minimum strip comments/docstrings before running the regex.

### WR-07: `speakerSideById` local state is not re-derived when the component is reused across a different argument id

**File:** `app/src/routes/admin/arguments/[id]/+page.svelte:67-74, 89-94`

**Issue:** `speakerSideById` is a `$state` map computed once from `data.argument.speakers`
at component setup time:
```ts
let speakerSideById = $state<Record<number, string>>(
    Object.fromEntries(
        (data.argument.speakers ?? [])
            .filter((s) => !s.is_bench)
            .map((s) => [s.participant_id, VALID_SIDES.has(s.side) ? s.side : 'UNKNOWN'])
    )
);
```
The Edit link on the arguments list page is a plain `<a href="/admin/arguments/{id}">`
(`app/src/routes/admin/arguments/+page.svelte:237-240`, no `data-sveltekit-reload`), so
SvelteKit performs a client-side (soft) navigation between two different argument ids,
reusing the same `+page.svelte` component instance and only replacing the `data` prop —
`$state` initializers do not re-run on prop changes. The component already patches this
exact hazard for `deleteConfirming`/`deleteSubmitting` via an explicit `$effect` keyed on
`data.argument.id` (commented "Pitfall 7", lines 89-94), but the same fix was not applied
to `speakerSideById`. After navigating from argument A to argument B via the list page's
Edit link, the advocate role `<select>` values initially shown for B's speakers can
reflect A's stale `participant_id → side` map (or read as `undefined` for ids that didn't
exist in A), and because `undefined !== 'UNKNOWN'` the Save button's disabled guard
(`speakerSideById[participant_id] === 'UNKNOWN'`) can evaluate `false` even though the
`<select>` is still effectively unresolved for that row. The backend's `T-26-14` guard
still rejects an actual `UNKNOWN`/`ADVOCATE` submission with 422, so this is a
correctness/UX robustness gap rather than a silent data-corruption path — but it can
produce a confusing "Save" attempt that appears enabled when it should not be, or a
dropdown that visually shows the wrong role immediately after navigation.

**Fix:** Recompute `speakerSideById` inside an `$effect` keyed on `data.argument.id`,
mirroring the existing delete-state reset:
```ts
$effect(() => {
    data.argument.id;
    speakerSideById = Object.fromEntries(
        (data.argument.speakers ?? [])
            .filter((s) => !s.is_bench)
            .map((s) => [s.participant_id, VALID_SIDES.has(s.side) ? s.side : 'UNKNOWN'])
    );
});
```

### WR-08: `approve_job` / `publish_argument` / `unpublish_argument` use check-then-act instead of the project's atomic rowcount pattern

**File:** `api/services/admin_jobs.py:487-541`; `api/services/admin_arguments.py:467-503, 578-611`

**Issue:** This module explicitly documents and uses an atomic `rowcount == 1` guard
pattern ("Pattern 3") for `try_advance_ingest_to_parse`/`try_advance_parse_to_resolve`
specifically to prevent double-execution races. `approve_job` does not follow this
pattern: it loads `argument`, checks `argument.status != PIPELINE` in Python, then issues
an `UPDATE ... WHERE Argument.id == job.argument_id` with **no status predicate** in the
`WHERE` clause, followed by an unconditional `db.add(ArgumentStatusLog(...))`. Two
concurrent `POST /jobs/{id}/approve` calls can both pass the Python-level check before
either commits, resulting in two `ArgumentStatusLog(status=DRAFT)` rows for the same
transition — contradicting the "exactly one log row" invariant asserted by
`test_approve_job_writes_one_draft_log_row`. `publish_argument`/`unpublish_argument` have
the identical shape (status checked in Python, then an `UPDATE`/`INSERT` with no status
predicate in the `WHERE` clause).

**Fix:** Add the expected prior status to each `UPDATE ... WHERE` clause (e.g.
`Argument.status == ArgumentStatusEnum.PIPELINE` for `approve_job`) and check
`result.rowcount == 1` before writing the corresponding `ArgumentStatusLog` row, mirroring
`try_advance_ingest_to_parse`.

### WR-09: Missing `max_length` on several schema fields that map to fixed-width DB columns

**File:** `api/schemas/admin_arguments.py:205-223, 226-249`; `api/schemas/admin_jobs.py:83-99`

**Issue:** `ResolveRowUpdate.title` was explicitly capped with `Field(max_length=500)`
(`api/schemas/admin_jobs.py:190`), documented inline as fixing exactly this failure mode
("WR-03: ... without this, an over-length title would raise an unhandled asyncpg
DataError (500) instead of the 422 validation-error pattern"). The identical, unfixed risk
exists for:
- `ArgumentUpdate.case_name` (no limit) → `Case.case_name` is `String(500)`
- `ArgumentUpdate.docket_number` (no limit) → `Case.docket_number` is `String(50)`
- `MetadataUpdate.case_name` (no limit) → `Case.case_name` is `String(500)`
- `MetadataUpdate.source_docket` / each element of `source_dockets` (no limit) →
  `Argument.source_docket` / `source_dockets` are `String(50)` / `ARRAY(String(50))`
- `PersonCreate.full_name` (no limit) → `Person.full_name` is `String(300)`
- `PersonCreate.role_name` (no limit) → `Role.name` is `String(100)`, also unique

Any over-length submission on these fields raises an unhandled DB error (500) instead of a
422 the operator can act on.

**Fix:** Add `Field(max_length=...)` matching each field's column width, consistent with
the `ResolveRowUpdate.title` precedent already established in this codebase.

### WR-10: `tenure_gap_warnings` recomputes bench-coverage logic already computed by `list_argument_speakers`

**File:** `api/services/admin_arguments.py:261-298` vs. `171-184, 342`

**Issue:** `get_argument_detail` computes `tenure_gap_warnings` via a standalone `exists()`
query per bench participant, then — a few lines later — calls `list_argument_speakers`
(line 342), which independently recomputes the identical "does any `CourtTenure` cover
`argued_date`" fact via `_bench_role_and_missing_tenure` for the same rows. This is
duplicated business logic maintained in two places (a raw SQL `exists()` vs. the shared
helper), with an extra per-bench-row DB round trip; if the two implementations of
"covered" ever diverge (e.g. inclusive/exclusive date-boundary handling), the legacy
`tenure_gap_warnings` field and `speakers[].missing_tenure` could silently disagree for
the same argument.

**Fix:** Derive `tenure_gap_warnings` from the already-computed `speakers` list
(`[s for s in speakers if s["is_bench"] and s["missing_tenure"]]`) instead of a second
independent query.

### WR-11: `create_role` / inline Role find-or-create are non-atomic against `Role.name`'s unique constraint

**File:** `api/routers/admin.py:981-992`; `api/services/admin_jobs.py:871-881`

**Issue:** Both do a SELECT-then-INSERT for `Role` by `name`, which is `UNIQUE` in the
schema (`api/models/models.py:93`). Concurrent requests creating the same new role name
race, and the loser hits an unhandled `IntegrityError` → 500 instead of gracefully falling
back to the row the winner just created.

**Fix:** Use `INSERT ... ON CONFLICT (name) DO NOTHING RETURNING id` followed by a SELECT
fallback, or wrap in `try/except IntegrityError` and re-SELECT.

## Info

### IN-01: `update_participant_side` route docstring is stale re: the UNKNOWN/legacy-ADVOCATE guard

**File:** `api/routers/admin.py:1106-1145` (docstring around lines 1127-1130)

**Issue:** The route docstring still only documents `"BENCH guard ... Returns 422 on side
== BENCH."` The function (and the service it calls,
`api/services/admin_arguments.py:526-531`, T-26-14) also 422s for `side == UNKNOWN` and
legacy `side == ADVOCATE` — this is documented correctly at the service layer but not at
the route layer.

**Fix:** Add a line noting the UNKNOWN/legacy-ADVOCATE rejection to the route docstring,
matching the service docstring.

### IN-02: `+page.server.ts` actions collapse all non-2xx upstream responses (including 5xx) into a fixed 422 `fail()`

**File:** `app/src/routes/admin/arguments/[id]/+page.server.ts:111-113, 167, 189, 210`

**Issue:** Each action's `if (!res.ok)` branch returns `fail(422, {...})` regardless of the
actual upstream status code — a 500 from FastAPI (e.g. CR-03 above) is reported to the
operator identically to a genuine validation error. This makes distinguishing "your input
was invalid" from "the server errored" impossible from the admin UI, slowing down
debugging of real backend failures.

**Fix:** Forward a clamped version of `res.status` instead of hardcoding `422`, or branch
explicitly on `res.status >= 500` vs. `422`.

### IN-03: Minor dead code / weak typing

**File:** `app/src/routes/admin/arguments/+page.svelte:150-151`,
`app/src/routes/admin/arguments/[id]/+page.svelte:286-288`, `api/routers/admin.py:1106-1109`

**Issue:** (a) The `arg.status ?? 'pipeline'` / `data.argument.status ?? 'pipeline'`
fallbacks are unreachable given `ArgumentListItem.status`/`ArgumentDetail.status` are
non-optional required fields in the Pydantic response schema. (b)
`update_participant_side`'s route is declared `response_model=dict`, unlike sibling
routes which use dedicated Pydantic response models — a small typing consistency gap.

**Fix:** Either remove the defensive `?? 'pipeline'` fallbacks or add a comment explaining
why they're intentionally kept; consider a small `ParticipantSideUpdateResponse` schema
for the route's `response_model`.

### IN-04: Non-keyed `{#each}` blocks over server-refreshed / polled lists

**File:** `app/src/routes/admin/arguments/+page.svelte:141`;
`app/src/routes/admin/pipeline/+page.svelte:628`;
`app/src/routes/admin/arguments/[id]/+page.svelte:436`

**Issue:** None of these list/table iterations use a keyed `{#each list as item (item.id)}`.
This matters most for `pipeline/+page.svelte`'s job table, which re-renders every second
via `invalidateAll()` polling (`app/src/routes/admin/pipeline/+page.svelte:37-43`) —
without a stable key, Svelte diffs rows positionally rather than by identity, which is
fragile for any future stateful per-row UI (inline editing, animations, focus retention).

**Fix:** Add explicit keys, e.g. `{#each data.jobs as job (job.id)}`.

---

_Reviewed: 2026-07-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
