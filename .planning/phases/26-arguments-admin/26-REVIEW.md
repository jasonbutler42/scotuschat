---
phase: 26-arguments-admin
reviewed: 2026-07-07T00:00:00Z
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
  critical: 3
  warning: 6
  info: 0
  total: 9
status: issues_found
---

# Phase 26: Code Review Report

**Reviewed:** 2026-07-07
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the Phase 26 arguments-admin API (router, schemas, services) and the SvelteKit
argument list/detail pages plus the shared `RunStatusCard` component and the accompanying
tests. The overall pattern discipline (mass-assignment allow-lists, IDOR scoping,
`synchronize_session=False`, validate-before-mutate ordering) is consistently applied and
matches the project's documented conventions. However, three defects break stated
invariants in ways that can destroy or strand data, and several quality issues weaken the
guarantees the code claims to provide.

Most impactful: `delete_argument` does not actually enforce its own "DRAFT only" contract
(it only rejects PUBLISHED/UNPUBLISHED, silently permitting deletion of PIPELINE-state
arguments that a running AdminJob still points at); the Speakers-card advocate `<select>`
is missing an option for `SideEnum.UNKNOWN`, which is the side value on every
freshly-parsed, not-yet-resolved advocate participant, so simply opening and saving the
form can silently reclassify an unresolved advocate as "Petitioner's Counsel"; and
`rerun_job` never spawns an ingest subprocess for jobs that were uploaded to local disk
(no DO Spaces configured), leaving the new job stuck in `PENDING/INGEST` forever with no
operator-visible error.

## Critical Issues

### CR-01: `delete_argument` permits deleting PIPELINE-state arguments, contradicting its own "DRAFT only" contract

**File:** `api/services/admin_arguments.py:622-652`
**Issue:**
The docstring states "Delete an argument only if it is a DRAFT (ADMIN-01, D-03/AEDIT-09)"
and the router docstring (`api/routers/admin.py:951`) repeats the same claim, but the
actual guard only blocks `PUBLISHED` and `UNPUBLISHED`:

```python
# D-03 / AEDIT-09: delete gate keys on status, not published_at.
if argument.status in (ArgumentStatusEnum.PUBLISHED, ArgumentStatusEnum.UNPUBLISHED):
    return False
```

`ArgumentStatusEnum` has four members: `PIPELINE`, `DRAFT`, `PUBLISHED`, `UNPUBLISHED`
(`api/models/models.py:67-71`). Because `PIPELINE` is not in the blocked tuple, a direct
`DELETE /api/admin/arguments/{argument_id}` call against a still-in-progress argument
succeeds: it deletes the argument's utterances, pipeline runs, participants, and
case-arguments, and NULLs `AdminJob.argument_id` on any job still referencing it. A
job that is currently `PAUSED` at the `RESOLVE` step (waiting on an operator) becomes
permanently stuck — `resolve_job`/`update_resolve_row_for_job` will subsequently fail
with `ValueError` because `job.argument_id` is now `None`, with no path back to a
working state short of manual DB surgery.

The SvelteKit edit page's `can_delete = argument.status === 'draft'`
(`app/src/routes/admin/arguments/[id]/+page.server.ts:77`) prevents this from being
reachable through the normal UI (the button is disabled for any non-draft status,
including `pipeline`), but the project's own convention — stated repeatedly elsewhere in
this same file ("server-side COUNT is authoritative; client disabled-state is
defense-in-depth only") — requires the backend to independently enforce this. It
currently does not for the `pipeline` state.

There is also no test coverage for this case: `test_delete_argument_returns_false_for_unpublished`
exists, but no `test_delete_argument_returns_false_for_pipeline` test exists to catch
the gap.

**Fix:**
```python
# D-03 / AEDIT-09: only DRAFT arguments may be deleted.
if argument.status != ArgumentStatusEnum.DRAFT:
    return False
```

### CR-02: `rerun_job` never spawns ingest for jobs uploaded to local disk (no DO Spaces configured)

**File:** `api/routers/admin.py:1042-1076`, `api/services/admin_jobs.py:524-548`
**Issue:**
`create_job`'s upload path stores the PDF on local disk when `settings.do_spaces_bucket`
is falsy (`api/routers/admin.py:301-313`) and never sets `spaces_key`; nothing on
`AdminJob` records the local file path (it's derived deterministically from `job.id` at
creation time: `data/uploads/{job.id}.pdf`). `rerun_job` (service) copies
`pdf_url`/`spaces_key`/`original_filename`/`source_dockets` onto the new job, but for a
locally-uploaded original job, both `pdf_url` and `spaces_key` are `None`. The router's
rerun endpoint only handles two cases:

```python
if new_job.spaces_key:
    spawn_pipeline_step("ingest", new_job.id, ["--spaces-key", new_job.spaces_key] + docket_args)
elif new_job.pdf_url:
    spawn_pipeline_step("ingest", new_job.id, ["--url", new_job.pdf_url] + docket_args)
```

There is no `else` branch. For a dev-mode, disk-backed original job, neither condition is
true, so **no ingest subprocess is spawned** for the new job. The endpoint still returns
`202` + a new `AdminJobResponse` with `status=PENDING`, giving the operator every
indication the rerun started successfully — but the job will sit at `PENDING/INGEST`
forever with no error surfaced anywhere (polling `GET /jobs/{id}` just keeps returning
`PENDING`, since `try_advance_ingest_to_parse` never fires — status never reaches
`COMPLETED`).

**Fix:** Preserve the original job's local file (or its path) so rerun can reuse it, e.g.
store the resolved local path on `AdminJob` at creation time and add a third branch:
```python
elif new_job.original_filename and not new_job.spaces_key and not new_job.pdf_url:
    # Local-disk-backed original — copy (or symlink) data/uploads/{original_id}.pdf
    # to data/uploads/{new_job.id}.pdf, then:
    spawn_pipeline_step("ingest", new_job.id, ["--local-file", str(copied_path)] + docket_args)
```
At minimum, if this path truly cannot be supported, `rerun_job` should raise a
`ValueError` (mapped to 422) rather than silently creating a job that can never progress.

### CR-03: Advocate role `<select>` has no option for `SideEnum.UNKNOWN`, so saving an unresolved advocate row silently reassigns its side

**File:** `app/src/routes/admin/arguments/[id]/+page.svelte:456-460`
**Issue:**
`list_argument_speakers` (`api/services/admin_arguments.py:101-218`) includes every
non-BENCH `ArgumentParticipant` in the "advocate" branch, regardless of `side` — and
`SideEnum` includes `UNKNOWN` (the default side for a freshly-resolved advocate that has
not yet been assigned a role) and legacy `ADVOCATE` (`api/models/models.py:36-42`). The
role `<select>` in the Speakers card only renders three options:

```svelte
<option value="PETITIONER" selected={speaker.side === 'PETITIONER'}>Petitioner's Counsel</option>
<option value="RESPONDENT" selected={speaker.side === 'RESPONDENT'}>Respondent's Counsel</option>
<option value="AMICUS" selected={speaker.side === 'AMICUS'}>Amicus Curiae</option>
```

When `speaker.side` is `'UNKNOWN'` (or legacy `'ADVOCATE'`), none of the three `selected`
expressions is true, so no `<option>` is marked selected. Per standard HTML `<select>`
behavior, the browser then treats the **first** listed option (`PETITIONER`) as the
current value. If an operator opens the Speakers card and clicks "Save" for that row
(e.g., only intending to fill in a Title), the form submits `side=PETITIONER` and the
participant — whose side genuinely has not been determined yet — is silently written as
"Petitioner's Counsel" with no confirmation or warning. This is a data-accuracy bug that
runs against the project's apolitical/no-silent-inference constraint on speaker
attribution (CLAUDE.md: "Every speaker ... gets identical schema, depth, and treatment.
No derived insight").

**Fix:** Add an explicit "Unresolved" placeholder option so the select reflects true
state and an accidental Save does not change `side`:
```svelte
<option value="UNKNOWN" selected={speaker.side === 'UNKNOWN'} disabled>Unresolved — choose a role</option>
<option value="PETITIONER" selected={speaker.side === 'PETITIONER'}>Petitioner's Counsel</option>
<option value="RESPONDENT" selected={speaker.side === 'RESPONDENT'}>Respondent's Counsel</option>
<option value="AMICUS" selected={speaker.side === 'AMICUS'}>Amicus Curiae</option>
```
(The server-side `ParticipantSideUpdate.side: SideEnum` already rejects `BENCH`; it would
need to also keep rejecting/ignoring `UNKNOWN` submissions if the placeholder is left
selected, or the Save button should be disabled while `side === 'UNKNOWN'`.)

## Warnings

### WR-01: Advocate row `colspan` does not cover all remaining table columns

**File:** `app/src/routes/admin/arguments/[id]/+page.svelte:413-417,428`
**Issue:**
The Speakers table header defines 5 columns: Name, Role, Title, Utterances, Action. Bench
rows correctly render 5 `<td>`s (Name + 4). The advocate branch renders `<td>` (Name) plus
a single `<td colspan="3">` that visually contains the Role select, Title input, the
utterance count, *and* the Save button — i.e., content for 4 logical columns squeezed into
a cell declared to span only 3:
```svelte
<td colspan="3" style="padding: 8px; vertical-align: top;">
```
Advocate rows therefore total 4 spanned column-units (`1 + 3`) against the table's 5
declared columns, while bench rows total 5. This is a malformed/inconsistent table
structure that will misalign column boundaries between adjacent advocate and bench rows
(borders, widths) — most visible when a Speakers list mixes bench and advocate rows.

**Fix:** Use `colspan="4"` to cover Role, Title, Utterances, and Action:
```svelte
<td colspan="4" style="padding: 8px; vertical-align: top;">
```

### WR-02: Duplicate, diverging docket-normalization logic between the router and the metadata-update service

**File:** `api/services/admin_arguments.py:732-744` vs `api/routers/admin.py:115-153`
**Issue:**
`api/routers/admin.py::_normalize_dockets` is the canonical strip/dedupe/order-preserving
normalizer, and it additionally rejects any docket value starting with `-`
(T-24-08, CLI-arg-injection defense before the value can reach subprocess argv). Phase 19's
`update_argument_metadata` in `admin_arguments.py` reimplements the same strip/dedupe logic
inline, but without the `-`-prefix rejection:
```python
seen: set[str] = set()
normalized: list[str] = []
for d in body.source_dockets:
    stripped = d.strip()
    if stripped and stripped not in seen:
        seen.add(stripped)
        normalized.append(stripped)
```
Today this specific call site never reaches subprocess argv (it writes to
`Argument.source_dockets`, a different column than `AdminJob.source_dockets`, which is the
only field `_dockets_to_ingest_args` consumes), so there is no active injection path — but
the duplicated logic is a maintenance hazard: a future change that wires
`Argument.source_dockets` into any CLI-argument builder would silently reintroduce the
T-24-08 vulnerability class this project has otherwise been careful to close in one place.

**Fix:** Extract the normalization (including the leading-`-` rejection) into a single
shared helper (e.g., a small `api/services/dockets.py`) and have both `_normalize_dockets`
and `update_argument_metadata` call it.

### WR-03: `docket_number_norm` is not actually normalized on admin edits, unlike ingest's dedup key

**File:** `api/services/admin_arguments.py:435-442`
**Issue:**
`update_argument`'s own comment acknowledges the gap:
```python
# docket_number_norm: same normalization as ingest (strip leading zeros, etc.)
# ...
# ingest.py does not export a normalizer for docket_number_norm, so we
# set it to the same stripped value ...
lead_case.docket_number_norm = new_docket
```
If ingest's duplicate-detection normalization (used at ingest time) differs from a plain
`.strip()` (e.g., it strips leading zeros or punctuation), an admin-edited docket number
can end up with a `docket_number_norm` that is out of sync with what a subsequent ingest
run would compute for an equivalent docket string — risking either a missed duplicate
detection or a false duplicate flag on the next ingest.

**Fix:** Export the normalizer used by ingest (mirroring the existing `_derive_slug`
re-export pattern already used in this file) and call it here instead of a bare `.strip()`.

### WR-04: Overly broad `except (UnidentifiedImageError, Exception)` masks all photo-processing errors

**File:** `api/routers/admin.py:691-699` and `api/routers/admin.py:717-722`
**Issue:**
`Exception` is a superclass of `UnidentifiedImageError`, so listing both is equivalent to
a bare `except Exception:` — every error while opening/verifying an uploaded or fetched
image (including out-of-memory conditions, decompression-bomb guards tripping, or a bug in
this code) is swallowed and converted into a generic "Uploaded file is not a valid image."
422, with no logging. This matches the "bare except" anti-pattern called out in the review
scope and will make genuine bugs in this code path invisible in production.

**Fix:**
```python
try:
    with Image.open(BytesIO(file_bytes)) as img:
        img_format = img.format
        img.verify()
except UnidentifiedImageError:
    raise HTTPException(status_code=422, detail="Uploaded file is not a valid image.")
except Exception:
    logger.exception("Unexpected error validating uploaded image")
    raise HTTPException(status_code=422, detail="Uploaded file is not a valid image.")
```

### WR-05: Photo-by-URL fetch has no domain allowlist (partial SSRF mitigation only)

**File:** `api/routers/admin.py:704-715`
**Issue:**
Unlike `_validate_pdf_url`, which restricts PDF ingestion to `*.supremecourt.gov` HTTPS
URLs, the photo-by-URL handler only checks `scheme == 'https'` before the server fetches
the URL:
```python
_parsed_url = _urlparse(photo_url)
if _parsed_url.scheme != 'https':
    raise HTTPException(status_code=422, detail="Photo URL must use HTTPS.")
...
async with httpx.AsyncClient(timeout=10.0) as client:
    r = await client.get(photo_url, follow_redirects=False)
```
`follow_redirects=False` mitigates one SSRF vector (redirect-based bypass of an allowlist),
but there is no allowlist here to bypass — any HTTPS host reachable from the API host
(including internal/private network endpoints that happen to terminate TLS) can be
targeted by an operator-supplied URL. This endpoint is admin-token gated, which lowers
severity relative to an unauthenticated SSRF, but it's still a meaningful gap relative to
the PDF-ingest precedent this codebase otherwise follows.

**Fix:** At minimum, resolve the hostname and reject loopback/link-local/private ranges
before fetching (defense-in-depth even for a trusted-operator surface), or restrict to a
configured allowlist of trusted photo hosts.

### WR-06: Structural "guard" tests scan raw source text (including comments/docstrings) with a naive regex

**File:** `api/tests/test_admin_arguments_service.py:137-154`
**Issue:**
`test_service_file_has_synchronize_session_false` counts `update(`/`delete(` occurrences
across the *entire module source* (via `inspect.getsource` + regex `\b(update|delete)\(`)
and compares that count against occurrences of the literal string
`"synchronize_session=False"`. This module's own docstrings use the phrase `update()`
(with the literal parenthesis) in prose (e.g., line 13: "EVERY update() statement includes
.execution_options(synchronize_session=False)"), which the regex will also match as a
"statement." Because the test only compares aggregate counts over the whole file rather
than pairing each real `update(...)`/`delete(...)` call with its own guard, it can pass
even if a *specific* new call is missing the guard (as long as the aggregate counts still
happen to balance), and it can also fail for unrelated prose changes that add the word
"update(" to a comment. This does not affect production correctness, but it means the test
provides weaker assurance of the underlying invariant than its name/intent claims.

**Fix:** Parse the module with `ast` and assert, for every `ast.Call` whose func resolves
to `sqlalchemy.update`/`sqlalchemy.delete`, that the enclosing statement's chained call
includes `.execution_options(synchronize_session=False)` — or at minimum restrict the
regex scan to code lines only (strip triple-quoted docstrings and `#` comments) so prose
mentions of `update()`/`delete()` cannot inflate the count.

---

_Reviewed: 2026-07-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
