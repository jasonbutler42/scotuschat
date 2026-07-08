---
phase: 26-arguments-admin
reviewed: 2026-07-08T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - api/routers/admin.py
  - api/schemas/admin_arguments.py
  - api/services/admin_arguments.py
  - api/services/admin_jobs.py
  - api/tests/test_admin_arguments_routes.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_jobs_service.py
  - app/src/lib/components/RunStatusCard.svelte
  - app/src/routes/admin/arguments/+page.svelte
  - app/src/routes/admin/arguments/[id]/+page.server.ts
  - app/src/routes/admin/arguments/[id]/+page.svelte
findings:
  critical: 2
  warning: 7
  info: 3
  total: 12
status: issues_found
---

# Phase 26: Code Review Report

**Reviewed:** 2026-07-08
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This is a fresh, full-scope review of all 11 files currently in the Phase 26 arguments-admin
surface, performed after gap-closure plan 26-05 (commits `d957f810`, `44a09c48`, `d322d297`).

**Gap-closure verification — both targeted fixes landed correctly and are confirmed working:**

1. **`delete_argument`'s status gate** (`api/services/admin_arguments.py:666-670`) is now a
   single positive `if argument.status != ArgumentStatusEnum.DRAFT: return False` condition,
   correctly rejecting `PIPELINE` in addition to `PUBLISHED`/`UNPUBLISHED`. Confirmed against
   `SideEnum`/`ArgumentStatusEnum` definitions in `api/models/models.py`, and covered by new
   tests `test_delete_argument_gate_keys_on_draft`, `test_delete_argument_returns_false_for_pipeline`
   (both route- and service-level).
2. **`update_participant_side`** (`api/services/admin_arguments.py:542-547`) now raises
   `ValueError` for `SideEnum.UNKNOWN` and legacy `SideEnum.ADVOCATE` in addition to `BENCH`,
   before touching the database. The matching UI change
   (`app/src/routes/admin/arguments/[id]/+page.svelte`) adds an explicit "Unresolved — choose
   a role" placeholder option, seeds a per-row `speakerSideById` state that collapses
   `UNKNOWN`/legacy `ADVOCATE` to a `'UNKNOWN'` sentinel, and disables the Save button while
   that sentinel is selected. Verified this is a functionally complete fix (disabling Save
   makes the previously-suggested `disabled` attribute on the `<option>` unnecessary), and
   backed by an always-run unit test (`test_update_participant_side_rejects_unresolved_side`)
   plus a route-level regression test.

**New/carried-forward issues found in this pass:** two of the three Critical issues from the
prior review round (rerun_job never spawning ingest for locally-uploaded jobs) were **not**
addressed by 26-05 and remain exploitable exactly as previously documented; five Warnings from
the prior round (colspan mismatch, duplicate docket normalization, unnormalized
`docket_number_norm`, overly-broad photo-validation `except`, and photo-URL SSRF gap) are also
unchanged. In addition, this pass identified a new Critical: `PATCH /arguments/{id}` (and the
sibling `MetadataUpdate`/`update_argument_metadata` path) accept and persist empty-string
`case_name`/`docket_number` with no non-empty validation anywhere in the stack, and the edit
form has no HTML `required` attribute on either field — an operator who accidentally clears
either field and clicks Save silently corrupts the case's identity data (and, for `case_name`
on a `DRAFT` argument, its public URL slug).

## Critical Issues

### CR-01: `rerun_job` still never spawns ingest for jobs uploaded to local disk (no DO Spaces configured) — unresolved from prior review

**File:** `api/routers/admin.py:1042-1076`, `api/services/admin_jobs.py:524-548`
**Issue:**
`create_job`'s upload path (`api/routers/admin.py:301-313`) stores the PDF at
`data/uploads/{job.id}.pdf` and sets neither `spaces_key` nor `pdf_url` when
`settings.do_spaces_bucket` is falsy. `rerun_job` (service, lines 524-548) copies
`pdf_url`/`spaces_key`/`original_filename`/`source_dockets` onto the new job, but the router's
rerun endpoint only handles two source types:

```python
if new_job.spaces_key:
    spawn_pipeline_step("ingest", new_job.id, ["--spaces-key", new_job.spaces_key] + docket_args)
elif new_job.pdf_url:
    spawn_pipeline_step("ingest", new_job.id, ["--url", new_job.pdf_url] + docket_args)
```

There is still no `else` branch and no local-file path is ever persisted on `AdminJob`, so for
a dev-mode disk-backed original job, **no ingest subprocess is spawned** for the rerun. The
endpoint still returns `202` with a fresh `PENDING`-status `AdminJobResponse`, giving the
operator every indication the rerun started — but the job sits at `PENDING/INGEST` forever with
no error surfaced anywhere (the poll endpoint's `try_advance_ingest_to_parse` never fires since
`status` never reaches `COMPLETED`).

This is the same defect flagged as CR-02 in the pre-gap-closure review; the 26-05 commits
(`d957f810`, `44a09c48`, `d322d297`) touched only `delete_argument`,
`update_participant_side`, and the Speakers `<select>` — none of the diffs touch
`rerun_job` or the local-upload path. Confirmed unresolved by direct inspection of current
`git show d957f810 44a09c48 d322d297 --stat` output (no `admin_jobs.py` rerun changes, no
router rerun-branch changes).

**Fix:** Persist the resolved local file path (or a stable, re-derivable location) on
`AdminJob` at creation time, and add a third branch:
```python
elif new_job.original_filename and not new_job.spaces_key and not new_job.pdf_url:
    # Local-disk-backed original — copy data/uploads/{original_id}.pdf to
    # data/uploads/{new_job.id}.pdf, then:
    spawn_pipeline_step("ingest", new_job.id, ["--local-file", str(copied_path)] + docket_args)
```
At minimum, if this path truly cannot be supported yet, `rerun_job` should raise a
`ValueError` (mapped to 422) instead of silently creating a job that can never progress.

### CR-02: `PATCH /arguments/{id}` allows blank `case_name`/`docket_number` to be persisted, corrupting slug and dedup-key data

**File:** `api/schemas/admin_arguments.py:205-224` (`ArgumentUpdate`),
`api/services/admin_arguments.py:424-461` (`update_argument`),
`app/src/routes/admin/arguments/[id]/+page.svelte:148-190` (form inputs)
**Issue:**
`ArgumentUpdate.case_name` and `.docket_number` are `Optional[str] = None` with no
`min_length`/non-empty constraint. `update_argument` treats "provided" as "not `None`," not
"non-empty":

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

The `?/save` form action (`app/src/routes/admin/arguments/[id]/+page.server.ts:126-127`)
always sends a (possibly empty) trimmed string for both fields — never `undefined`/omitted:
```ts
const case_name = ((formData.get('case_name') as string) ?? '').trim();
const docket_number = ((formData.get('docket_number') as string) ?? '').trim();
```
and the corresponding `<input>` elements have no `required` attribute
(`+page.svelte:148-164` for `case_name`, `172-190` for `docket_number`). If an operator clears
either field (accidentally or otherwise) and clicks "Save changes," the request body carries
`case_name: ""` / `docket_number: ""`, which is not `None`, so the write proceeds: for a
`DRAFT` argument, `_derive_slug("")` returns `""` (confirmed in
`pipeline/commands/ingest.py:85-101` — no length check), and — absent a same-empty-slug
collision — the lead `Case` row ends up with `case_name=""`, `slug=""`. For any status
(including `PUBLISHED`), `docket_number`/`docket_number_norm` can similarly be wiped to `""`.
This breaks the case's public URL, its display title on any published page, and the
uniqueness/dedup semantics of `docket_number`. There is no confirmation step and no way to
recover except direct DB correction.

The same "not-`None` treated as provided, no non-empty check" pattern exists in the sibling
`update_argument_metadata` (`api/services/admin_arguments.py:781-795` for `case_name`,
`763-764` for `source_docket`), reachable via `MetadataUpdate`.

**Fix:** Add non-empty validation at the schema layer (Pydantic v2 `Field(min_length=1)` with
a validator that treats whitespace-only as empty, or a `field_validator` that rejects blank
after `.strip()`), and add `required` to both `<input>` elements as defense-in-depth:
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
```svelte
<input type="text" id="case_name" name="case_name" required value={data.argument.case_name} ... />
<input type="text" id="docket_number" name="docket_number" required value={data.argument.docket_number} ... />
```

## Warnings

### WR-01: Advocate row `colspan` still does not cover all remaining table columns — unresolved from prior review

**File:** `app/src/routes/admin/arguments/[id]/+page.svelte:428-432` (header), `:443`
**Issue:** The Speakers table header still declares 5 columns (Name, Role, Title, Utterances,
Action). Bench rows render 5 `<td>`s total. The advocate branch still renders one `<td>`
(Name) plus a single `<td colspan="3">` (line 443) holding the Role select, Title input,
utterance count, and Save button — 4 pieces of content packed into a cell that only declares
3 spanned columns, so advocate rows total 4 column-units against the table's 5. This
misaligns column boundaries whenever a Speakers list mixes bench and advocate rows. Not
touched by the 26-05 commits.
**Fix:** `<td colspan="4" style="padding: 8px; vertical-align: top;">`.

### WR-02: Duplicate, diverging docket-normalization logic between the router and the metadata-update service — unresolved from prior review

**File:** `api/services/admin_arguments.py:751-762` vs `api/routers/admin.py:115-153`
**Issue:** `_normalize_dockets` in the router is the canonical strip/dedupe/order-preserving
normalizer and additionally rejects any docket value starting with `-` (T-24-08 CLI-arg
injection defense). `update_argument_metadata` still reimplements the same strip/dedupe logic
inline without the `-`-prefix rejection. No active injection path today (this call site writes
`Argument.source_dockets`, not the field `_dockets_to_ingest_args` consumes), but it's a
maintenance hazard if that ever changes.
**Fix:** Extract the shared normalization (including the leading-`-` rejection) into one helper
used by both call sites.

### WR-03: `docket_number_norm` is still not actually normalized on admin edits, unlike ingest's dedup key — unresolved from prior review

**File:** `api/services/admin_arguments.py:435-442`
**Issue:** `update_argument`'s own comment acknowledges the gap and sets
`lead_case.docket_number_norm = new_docket` — the raw, hyphen-containing value — while
`pipeline/commands/ingest.py:385` computes `docket_number_norm=docket.replace("-", "")` for
newly-ingested cases. An admin-edited docket therefore gets a `docket_number_norm` computed by
a different rule than ingest uses, risking a future normalization-consumer (duplicate
detection, lookups) treating equivalent dockets as different.
**Fix:** Export ingest's normalization as a small reusable function (mirroring the existing
`_derive_slug` re-export pattern) and call it here instead of a bare `.strip()`.

### WR-04: Overly broad `except (UnidentifiedImageError, Exception)` still masks all photo-processing errors — unresolved from prior review

**File:** `api/routers/admin.py:695`, `api/routers/admin.py:721`
**Issue:** `Exception` is a superclass of `UnidentifiedImageError`; listing both is equivalent
to a bare `except Exception:`. Both photo-processing code paths (file upload and URL fetch)
still swallow every error (OOM, decompression-bomb-guard trips, bugs in this code) into a
generic 422 with no logging.
**Fix:**
```python
except UnidentifiedImageError:
    raise HTTPException(status_code=422, detail="Uploaded file is not a valid image.")
except Exception:
    logger.exception("Unexpected error validating uploaded image")
    raise HTTPException(status_code=422, detail="Uploaded file is not a valid image.")
```

### WR-05: Photo-by-URL fetch still has no domain allowlist / private-range check — unresolved from prior review

**File:** `api/routers/admin.py:704-715`
**Issue:** Unlike `_validate_pdf_url` (restricted to `*.supremecourt.gov` HTTPS), the
photo-by-URL handler only checks `scheme == 'https'` before fetching. `follow_redirects=False`
blocks one bypass vector but there's still no allowlist to bypass — any HTTPS host reachable
from the API host (including internal/private endpoints terminating TLS) can be targeted via
an operator-supplied URL. Admin-token-gated, which lowers severity, but still a gap relative to
this codebase's own PDF-ingest precedent.
**Fix:** Resolve the hostname and reject loopback/link-local/private ranges before fetching, or
restrict to a configured allowlist of trusted photo hosts.

### WR-06: Structural "guard" test still scans raw source text (including comments/docstrings) with a naive regex — unresolved from prior review

**File:** `api/tests/test_admin_arguments_service.py:137-154`
**Issue:** `test_service_file_has_synchronize_session_false` compares aggregate counts of
`\b(update|delete)\(` matches against occurrences of the literal string
`"synchronize_session=False"` across the *whole module source*, including docstrings/comments
that use the phrase `update()` in prose. This can pass even when a specific new call is
missing its guard (as long as aggregate counts balance), and can fail for unrelated prose
edits. Same pattern also appears in `test_delete_argument_all_deletes_have_synchronize_session_false`
(lines 220-247), scoped to the `delete_argument` function body only, which reduces but does not
eliminate the same class of false-confidence.
**Fix:** Parse with `ast` and assert, per `ast.Call` resolving to `sqlalchemy.update`/`delete`,
that the enclosing statement chains `.execution_options(synchronize_session=False)` — or at
minimum strip docstrings/comments before running the regex.

### WR-07: `speakerSideById` seed is not re-derived if the Speakers component is reused across a route-param change

**File:** `app/src/routes/admin/arguments/[id]/+page.svelte:67-74`
**Issue:** `speakerSideById` is a `$state` object initialized once from `data.argument.speakers`
at component setup:
```ts
let speakerSideById = $state<Record<number, string>>(
    Object.fromEntries(
        (data.argument.speakers ?? [])
            .filter((s) => !s.is_bench)
            .map((s) => [s.participant_id, VALID_SIDES.has(s.side) ? s.side : 'UNKNOWN'])
    )
);
```
Unlike `deleteConfirming`/`deleteSubmitting`, which are explicitly reset via an `$effect` keyed
on `data.argument.id` (lines 89-94) specifically because SvelteKit can reuse the same `[id]`
page component instance across a route-param-only navigation, `speakerSideById` has no such
reset. If the component instance is ever reused for a different argument id (e.g., browser
back/forward across two previously-visited argument edit pages), a participant id not present
in the stale map reads as `undefined` from `speakerSideById[...]`. Because
`undefined !== 'UNKNOWN'`, the Save-button's disabled condition
(`speakerSideById[speaker.participant_id] === 'UNKNOWN'`) evaluates `false` even though the
`<select>` visually defaults to its first `<option value="UNKNOWN">` — the guard the 26-05 fix
just added can silently become non-authoritative for that row's Save button (the backend
`update_participant_side` guard still rejects the resulting `UNKNOWN` submission with 422, so
this is a UX/robustness gap rather than a data-corruption path).
**Fix:** Mirror the existing delete-state pattern:
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

## Info

### IN-01: `update_participant_side` route docstring is stale re: the 26-05 UNKNOWN/ADVOCATE guard

**File:** `api/routers/admin.py:1127-1130`
**Issue:** The docstring still only documents `"BENCH guard ... Returns 422 on side == BENCH."`
The function (and the service it calls) now also 422s for `side == UNKNOWN` and legacy
`side == ADVOCATE` (T-26-14) — this is undocumented at the route layer, unlike the service
docstring (`api/services/admin_arguments.py:526-531`), which was updated correctly.
**Fix:** Add a line noting the UNKNOWN/legacy-ADVOCATE rejection, matching the service
docstring.

### IN-02: Server actions collapse all non-2xx upstream responses (including 5xx) into a fixed 422 `fail()`

**File:** `app/src/routes/admin/arguments/[id]/+page.server.ts:111-113` (`updateParticipantSide`),
`:167` (`save`), `:189` (`publish`), `:210` (`unpublish`)
**Issue:** Each action's `if (!res.ok)` branch returns `fail(422, {...})` regardless of the
actual upstream status code (a 500 from FastAPI is reported to the operator identically to a
genuine 422 validation error). This is a pre-existing, codebase-wide pattern in this file (not
introduced by Phase 26), but it makes distinguishing "your input was invalid" from "the server
is broken" impossible from the admin UI, which can slow down debugging real backend failures.
**Fix:** Forward `res.status` (clamped to a safe range) instead of hardcoding `422`, or branch
explicitly on `res.status >= 500` vs `422`.

### IN-03: Minor dead code / weak typing

**File:** `app/src/routes/admin/arguments/+page.svelte:150-151`,
`app/src/routes/admin/arguments/[id]/+page.svelte:286-288`,
`api/routers/admin.py:1106-1109`
**Issue:** (a) `arg.status ?? 'pipeline'` / `data.argument.status ?? 'pipeline'` fallbacks are
unreachable given `ArgumentListItem.status`/`ArgumentDetail.status` are non-optional required
fields in the Pydantic schema — harmless but suggests the schema contract isn't fully trusted
at the call site. (b) `update_participant_side`'s route is declared
`response_model=dict`, unlike its sibling routes which use dedicated Pydantic response models
— a small consistency/typing gap.
**Fix:** Either remove the defensive `?? 'pipeline'` fallbacks (schema already guarantees a
value) or add a comment explaining why they're kept; consider a small
`ParticipantSideUpdateResponse` schema for the route's `response_model`.

---

_Reviewed: 2026-07-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
