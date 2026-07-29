---
status: resolved
trigger: "UAT Test 6 (Phase 38, 38-UAT.md): docket value with double-quote character entered via DocketPillInput on Pipeline Runner new-job form crashes pipeline ingest with [Errno 22] Invalid argument when interpolated raw into a PDF filename in pipeline/commands/ingest.py:291. goal: find_root_cause_only"
created: 2026-07-27T00:00:00Z
updated: 2026-07-29T00:00:00Z
---

**Stale-record correction (2026-07-29):** This file's `status: diagnosed` was never updated after the fix shipped, because this debug session's own goal was `find_root_cause_only` (no fix expected from this session). The actual fix landed one day later as Phase 38 Plan 10 (gap closure G-38-6), tracked in `38-UAT.md`, not in this file. The v1.6 pre-close artifact audit read this stale `diagnosed` status and inserted Phase 40.1 as a duplicate urgent gap-closure phase; that duplication was caught and reconciled during Phase 40.1's planning step (see `.planning/phases/40.1-sanitize-docket-input-to-close-path-traversal-arbitrary-file/40.1-SUMMARY.md`) before any redundant code was written. Backfilling `fix`/`verification`/`files_changed` below from the real Phase 38 Plan 10 record.

## Current Focus

hypothesis: CONFIRMED — primary_docket flows unsanitized from DocketPillInput (free-text pill input) through the new-job form POST, +page.server.ts, and the FastAPI create_job route into pipeline/commands/ingest.py where it is f-string interpolated directly into a filesystem path. The only existing guard (_normalize_dockets' startswith("-") check) defends against a different threat class (CLI argv-flag-injection, T-24-08) and does not touch filesystem-path or character-shape safety. Additionally confirmed this is exploitable as a path-traversal / arbitrary-file-write, not merely a crash, because pathlib's `/` operator both honors `../` segments (resolved by the OS at write time) and silently discards the left operand entirely when the right operand is an absolute path (POSIX `/...` or Windows drive-letter path) — verified experimentally.
test: complete — traced every hop; ran pathlib experiments confirming traversal/absolute-override behavior
expecting: n/a — investigation complete, goal is find_root_cause_only
next_action: return ROOT CAUSE FOUND diagnosis (no fix — goal: find_root_cause_only)

## Symptoms

expected: |
  A docket "number" value entered via DocketPillInput should either be constrained to
  valid-docket-shaped input, or safely sanitized before being used to construct a
  filesystem path during pipeline ingest — never passed raw into a file path.
actual: |
  Entering an unusual docket value (long free text, or containing special characters)
  crashes the pipeline ingest job instead of being rejected with a clear validation
  error or safely handled.
errors: |
  [Errno 22] Invalid argument: 'data\pdfs\I wonder if there is a limit to how long the docket "numbers" can be-q1.pdf'
reproduction: |
  UAT Test 6, Phase 38 (full-name-vs-name-parts-rethink): On the Pipeline Runner's
  new-job form, enter a free-text string containing a double-quote character as the
  docket "number" via DocketPillInput, leave Question at its default, run the job.
started: |
  Discovered during UAT for Phase 38 (not necessarily a Phase 38 regression --
  DocketPillInput itself was touched by Phase 38 Plan 05, but the filename-construction
  code in ingest.py appears pre-existing)

## Eliminated

- hypothesis: "The bug is a Phase 38 regression in DocketPillInput.svelte itself (e.g. Phase 38 Plan 05's provenance-pill rendering broke an existing validation path)."
  evidence: Read DocketPillInput.svelte in full. addPill() only does `.trim()` and a duplicate check (`if (v && !pills.includes(v))`) — no regex/allow-list/length constraint exists in the current version, and the Phase 38 Plan 05 change (adding CopyableExtractedValue provenance rendering) is purely additive/rendering-only per the D-38-05 decision log entry ("all current plain-string callers ... keep exact legacy markup and remain untouched"). Nothing in git-blame-relevant code suggests a stricter guard was ever removed. The bug is pre-existing; Phase 38 only made the crash reachable via a form UAT pass, it didn't introduce the vulnerable code path.
  timestamp: 2026-07-27T00:00:00Z

## Evidence

- timestamp: 2026-07-27T00:00:00Z
  checked: pipeline/commands/ingest.py (full file, 471 lines)
  found: |
    Line 291: `pdf_filename = f"{primary_docket}-q{args.question}.pdf"` — primary_docket
    is interpolated with zero character/length validation. No other sanitization
    call (no os.path.basename, no re.sub, no allow-list) exists anywhere in this
    file between argparse and this f-string. pdf_path = Path("data/pdfs") / pdf_filename
    (line 301) — a plain pathlib join with no traversal/absolute-path guard.
  implication: Confirms the reported grep lead exactly; this is the crash site and also the path-traversal site.

- timestamp: 2026-07-27T00:00:00Z
  checked: app/src/lib/components/DocketPillInput.svelte (full file)
  found: |
    `addPill()` (lines 61-68): `const v = docketInput.trim(); if (v && !pills.includes(v)) { pills = [...pills, v]; } docketInput = '';`
    No regex, no allow-list of characters, no max length, no docket-shape validation
    (e.g. no enforcement of the real SCOTUS docket format like "22-915"). The only
    Phase 38 change to this component was additive provenance rendering
    (CopyableExtractedValue for confidence/raw display) — the plain editable-pill
    input path (addPill/removePill) is untouched from before Phase 38.
  implication: Confirms zero validation exists at the point of entry (the actual UI control named in the bug report).

- timestamp: 2026-07-27T00:00:00Z
  checked: app/src/routes/admin/pipeline/+page.svelte and +page.server.ts (full files)
  found: |
    +page.svelte passes DocketPillInput's hidden `docket[]` inputs straight through
    a native form POST with no client-side validation added around it.
    +page.server.ts's default action (lines 40-49) only does: trim each raw docket
    value, drop blanks, dedupe via a Set preserving order. `primary_docket = dockets[0]`
    is then forwarded verbatim as a multipart FormData field to FastAPI
    (`POST {FASTAPI_BASE_URL}/api/admin/jobs`). No format/length/character check.
  implication: The SvelteKit server layer (the "service layer" between form and API) adds no sanitization either — trim+dedupe is the entire extent of processing.

- timestamp: 2026-07-27T00:00:00Z
  checked: api/routers/admin.py create_job route (POST /api/admin/jobs, lines 210-332) and _normalize_dockets (lines 126-164)
  found: |
    `primary_docket: Optional[str] = Form(None)` has no Pydantic Field constraints
    (no max_length, no pattern/regex) — contrast with ResolveRowUpdate.title which
    explicitly uses `Field(default=None, max_length=500)` documented as needed
    "without this, an over-length title would raise an unhandled ... DataError...
    instead of the 422 validation-error pattern used everywhere else" — i.e. the
    codebase has a clear precedent/pattern for adding max_length guards but it was
    never applied to primary_docket/source_dockets.
    _normalize_dockets itself only trims, drops blanks, dedupes, and rejects values
    whose *stripped* form `startswith("-")` — this exists specifically for T-24-08
    (CLI-arg-injection: a docket value like "--dockets" or "-1" could be
    misinterpreted as a subprocess argv flag). A double-quote character does not
    start with "-", so it sails through this guard untouched. This guard's own
    docstring and api/tests/test_docket_arg_safety.py confirm its scope is
    explicitly argv-injection, not filesystem-path safety or docket-shape validation.
  implication: Confirms the ONLY existing docket-input guard anywhere in the stack (frontend -> SvelteKit server -> FastAPI) is the argv-flag guard, which is orthogonal to this bug's threat class. No allow-list, no length cap, no filesystem-illegal-character rejection exists at the API boundary either.

- timestamp: 2026-07-27T00:00:00Z
  checked: api/services/pipeline_spawn.py and pipeline/__main__.py (_scrape_job_id)
  found: |
    spawn_pipeline_step uses `subprocess.Popen(cmd, ...)` with cmd as a list and
    shell=False (default) — confirmed via docstring "Security: shell=False
    (default) ... never interpolated into a shell string (T-07-02)". So there is
    no shell-metacharacter/command-injection risk from the docket value reaching
    subprocess argv; the value arrives at argparse as a single clean argv element
    (`--primary-docket`, `<value>`) regardless of its special characters. This
    rules out shell injection as an additional finding — the vulnerability is
    scoped to filesystem-path construction only, not command execution.
  implication: Narrows the exploitability finding correctly — the threat is path traversal / arbitrary file write via the fs.write call, not RCE via shell.

- timestamp: 2026-07-27T00:00:00Z
  checked: python3 experiment (pathlib behavior) — see transcript
  found: |
    `Path("data/pdfs") / "../../../tmp/evil-q1.pdf"` -> `data/pdfs/../../../tmp/evil-q1.pdf`
    (Python does not need to .resolve() for the OS to honor ".." at actual write
    time via write_bytes()/open()). More severe: `Path("data/pdfs") / "/etc/cron.d/evil-q1.pdf"`
    -> `/etc/cron.d/evil-q1.pdf` — pathlib's `/` operator silently DISCARDS the
    left operand entirely when the right-hand string is an absolute path. The same
    applies on Windows for a value starting with a drive letter (e.g. "C:\\...").
    Since primary_docket is attacker/operator-controlled free text with no
    character restrictions, a value like "../../../../home/user/.ssh/authorized_keys"
    or (POSIX) "/etc/whatever" would let the write escape data/pdfs/ entirely.
  implication: This is a genuine path-traversal / arbitrary-file-write vulnerability, not just a crash-on-illegal-character bug. Severity is reduced by the fact that /api/admin/jobs is gated behind verify_admin_token (admin-authenticated surface, per api/routers/admin.py:102-116/119-123) — so this is an authenticated-operator-can-write-anywhere-the-process-has-permission-to issue, not an unauthenticated RCE/traversal. Still meaningful: a compromised/malicious admin session, or an admin fat-fingering/pasting an unexpected string, can overwrite arbitrary files reachable by the pipeline process's OS user.

- timestamp: 2026-07-27T00:00:00Z
  checked: pipeline/parser/cover_extractor.py DOCKET_RE and api/schemas/admin_arguments.py ArgumentUpdate.docket_number validator
  found: |
    `DOCKET_RE = re.compile(r'No\.\s+(\d{1,2}-\d+)', re.IGNORECASE)` exists in
    cover_extractor.py, but it is used ONLY to extract a docket number FROM the
    PDF's own cover-page text during the later parse step (pipeline/commands/parse.py) --
    it is never applied to validate operator-supplied input at ingest/job-creation
    time. ArgumentUpdate.docket_number (used for the post-ingest metadata PATCH
    editor, api/schemas/admin_arguments.py:222-233) has a field_validator but it
    only enforces "non-blank string" -- no shape/regex/length/character
    constraint either. Grepped app/src/lib/components/*.svelte and
    ArgumentDetailsCard.svelte for pattern=/maxlength/regex constraints on docket
    fields: none found anywhere in the frontend.
  implication: Answers item 3 of the request directly -- there is NO existing "22-915"-shaped docket-format validator enforced anywhere in the operator-input path (new-job creation OR post-ingest metadata edit OR any frontend field). The only docket regex in the codebase (DOCKET_RE) validates PDF-extracted text on a completely different, unrelated code path (parse step, not ingest/job-creation), so the new-job path isn't "bypassing" a sibling validator so much as no such validator for operator input exists at all yet.

- timestamp: 2026-07-27T00:00:00Z
  checked: grep for other filename-construction call sites keyed on primary_docket/docket_number/source_docket across pipeline/ and api/
  found: |
    Only pipeline/commands/ingest.py:291 constructs a filesystem path directly
    from primary_docket. pipeline/commands/parse.py reads/writes
    cover_meta["primary_docket"] only as a DB column value (source_docket
    UPDATE), never as a path component. pipeline/parser/cover_extractor.py's
    DOCKET_RE result also only feeds a dict/DB value. No other call site builds
    a Path/filename from primary_docket, source_dockets, or docket_number.
  implication: Answers item 4 -- ingest.py:291 is the sole vulnerable call site for docket-derived filesystem paths; this is not a repeated pattern requiring a multi-file fix, though the fix should still land as a shared/reusable sanitizer given the "safely sanitized" language in the Truth statement, in case future call sites are added.

## Resolution

root_cause: |
  primary_docket (operator-supplied free text entered via DocketPillInput on the
  Pipeline Runner new-job form) has no character-shape allow-list, length limit,
  or filesystem-safety sanitization anywhere along its full data flow --
  DocketPillInput.svelte (trim + dedupe only) -> +page.svelte (no added
  validation) -> +page.server.ts default action (trim + dedupe only) ->
  FastAPI POST /api/admin/jobs (Form(None), no Pydantic Field constraints) ->
  _normalize_dockets (trim, drop-blank, dedupe, and reject only a leading "-",
  a guard scoped exclusively to CLI argv-flag-injection per T-24-08, not
  filesystem-path safety) -> spawned ingest subprocess argv -> argparse ->
  pipeline/commands/ingest.py:291
  `pdf_filename = f"{primary_docket}-q{args.question}.pdf"`, which is then
  joined onto Path("data/pdfs") and written to disk with zero sanitization.
  A double-quote character in the value is illegal in a Windows filename,
  producing the reported OSError [Errno 22]. Separately (deepened beyond the
  original lead), the same missing sanitization also permits path-traversal
  and absolute-path override: pathlib's `/` operator honors "../" segments
  at actual write time and silently discards the base directory entirely
  when the right operand is an absolute path (POSIX leading "/" or a Windows
  drive letter), so this is an arbitrary-file-write primitive, not merely a
  crash-on-special-character bug -- bounded in severity by the route being
  gated behind admin-token auth (authenticated-operator surface, not
  unauthenticated/external).
fix: |
  Phase 38 Plan 07 added `api/domain/docket_values.py::normalize_docket_value()` —
  a shared, framework-free domain rule (character allow-list
  `^[A-Za-z0-9][A-Za-z0-9_-]*$`, 64-char length cap, deterministic
  blank/length/pattern error ordering) chosen over a strict SCOTUS
  docket-shape regex because post-ingest editing, the ConvoKit historical
  importer, and existing data/pdfs/ filenames already use non-standard
  shapes. Wired in at two independent enforcement layers per the original
  diagnosis's two-layer-defense recommendation:
  1. `api/routers/admin.py::_normalize_dockets` (Phase 38 Plan 07) — calls
     the shared rule for `primary_docket` and every `source_dockets` entry,
     as the first statement of `create_job`, before any AdminJob row or
     ingest subprocess is created. The existing T-24-08 leading-"-"
     argv-injection guard is preserved unchanged alongside it.
  2. `pipeline/commands/ingest.py::_validate_docket_value()` (Phase 38
     Plan 10) — a second, independent enforcement point covering the direct
     CLI invocation path that bypasses FastAPI entirely. Delegates to the
     same shared rule, then adds structural PurePath assertions (no path
     separator, no ".." segment, not absolute, exactly one path part), plus
     a post-`.resolve()` containment assertion immediately before the
     vulnerable filename is used, so the write path is proven to stay
     inside `data/pdfs/` even if the character rule were ever bypassed.
  An optional frontend mirror (`app/src/lib/docketValues.ts`,
  `DocketPillInput.svelte`) gives fast reject-on-type UX feedback using the
  byte-identical pattern/length constants.
verification: |
  Operator UAT (38-UAT.md, gap_id G-38-6, resolved 2026-07-27): re-ran the
  exact originally reported double-quote string — rejected inline before a
  pill or job is created, typed text preserved, no [Errno 22]. Additionally
  re-verified the traversal case (../../../tmp/evil) and a Windows
  drive-letter path, both rejected inline with nothing written outside
  data/pdfs/; confirmed a real docket (22-915) still starts a run normally;
  confirmed the post-ingest metadata editor is unaffected; confirmed
  non-docket run failures still show the generic error message. Operator
  response: "Approved" (2026-07-27).
  Consolidated regression gate (38-10-PLAN.md Task 1): 119 passed, 0
  failures across 9 suites (test_docket_values.py, test_docket_arg_safety.py,
  test_docket_ui_contract.py, pipeline/tests/test_ingest.py,
  test_ingest_startup_guard.py, test_admin_jobs_list.py,
  test_admin_jobs_phase35.py, test_admin_jobs_phase35_frontend.py,
  test_admin_dashboard_routes.py). On-disk data/pdfs corpus check: all 58
  existing filenames satisfy the shared docket rule, 0 violations.
  Independently re-confirmed 2026-07-29 (Phase 40.1 planning step) by
  direct source inspection of api/domain/docket_values.py,
  pipeline/commands/ingest.py's call sites and containment assertion, and
  api/routers/admin.py's _normalize_dockets wiring — all match this
  description exactly.
files_changed:
  - api/domain/docket_values.py
  - api/routers/admin.py
  - pipeline/commands/ingest.py
  - app/src/lib/docketValues.ts
  - app/src/lib/components/DocketPillInput.svelte
  - api/tests/test_docket_values.py
  - api/tests/test_docket_arg_safety.py
  - api/tests/test_docket_ui_contract.py
