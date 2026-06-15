# Feature Research

**Domain:** Operator-facing admin interface for a content ingestion pipeline (single operator, internal tool)
**Researched:** 2026-06-15
**Confidence:** HIGH

---

## Feature Landscape

### Table Stakes (Operator Expects These)

Features the operator assumes exist. Missing these = admin tool is not usable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Password-protected login | Any admin route must be gated; session must persist across refreshes | LOW | Username+password from env vars; SvelteKit `hooks.server.ts` intercepts all `/admin/*` before load functions run. Session stored as HttpOnly cookie. |
| Logout | Every auth system has logout | LOW | Clear session cookie; redirect to `/admin/login`. |
| Pipeline trigger — URL input | Ingest is already URL-driven (supremecourt.gov PDF URLs); the operator knows the URL before running | LOW | Input + submit button; validate URL format client-side before submitting. URL must pass existing `_validate_url()` SSRF guard on the backend. |
| Pipeline trigger — file upload | Operator may have PDFs locally that are not yet on supremecourt.gov | MEDIUM | `<input type="file" accept=".pdf">`; upload to server, store in `data/` directory as if ingest downloaded it; then proceed through parse/resolve. Drag-and-drop is a bonus, not table stakes. |
| Step-by-step status display | Operator must know whether ingest / parse / resolve succeeded or is still running | MEDIUM | Three named step cards, each with a status badge: pending → running → completed / failed / needs_review. Read from `pipeline_runs` table, which already has this state machine (PIPE-10 validated). |
| Auto-advance when no discrepancies | If resolve finds zero unresolved labels, move straight to completed without blocking the operator | LOW | Backend resolve step already gates `needs_review` (PIPE-09 validated). UI polls status and advances the stepper automatically when status = completed. |
| Pause-for-review when discrepancies exist | Operator must see which speaker labels went unresolved before marking a run done | MEDIUM | When resolve run status = `needs_review`, UI shows a list of unresolved `argument_participants` rows for that argument. Operator assigns or creates a person record per row. |
| People directory list | Operator needs to see all speaker records to spot duplicates and gaps | LOW | Paginated or scrollable table of people rows: full_name, role, photo_url present/absent indicator. |
| People edit form | Operator must be able to edit name, role, bio text, photo URL, tenure dates | LOW | Standard form with labeled fields; save persists to `people` and `court_tenures` tables via new admin API endpoints. |
| Pipeline run history | Operator needs to see past runs to diagnose failures and find run IDs | LOW | List of recent `pipeline_runs` rows per argument: step, status, timestamps, failure_reason. |
| Error display on failure | If parse or resolve fails, the operator must see the failure_reason | LOW | `pipeline_runs.failure_reason` column already populated by pipeline. Surface it inline in the step card. |

---

### Differentiators (Valuable but Not Assumed)

Features that make the admin tool faster and less error-prone for a solo operator.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Pipeline state resumable across sessions | If browser closes mid-run, operator can return and see current status | LOW | `pipeline_runs` rows are already persisted to DB (PIPE-14 requirement). UI just reads current state on page load rather than relying on in-memory state. Mostly provided by the existing schema. |
| Inline participant review after resolve | After a run, operator can see each resolved participant and fill in missing metadata (bio, photo URL) without leaving the pipeline view | MEDIUM | After resolve completes, render `argument_participants` for the argument with each person's current metadata. Clicking a person opens an inline edit panel. Avoids separate trip to the people directory for newly encountered speakers. |
| "Create new person" during resolve review | When a speaker label is completely new, operator can create a person record inline rather than navigating away | MEDIUM | Modal or inline form with full_name + role; saves to `people` and creates the `argument_participant` link. Returns to review queue without full page navigation. |
| Unresolved count badge | Before operator opens the review step, show how many labels still need attention | LOW | COUNT of `argument_participants WHERE person_id IS NULL` for the current argument. Keeps operator oriented. |
| Alias auto-save during review | When operator assigns a label to a person during review, optionally save to `speaker_alias` so future runs auto-resolve it | LOW | Checkbox on the review form: "Remember this label mapping." Writes to `speaker_alias` table. High value because the same Justices appear in every argument. |
| Tab-separated dual trigger (URL / Upload) | Toggle between URL and file upload in one widget rather than two separate pages | LOW | Tabbed input: [Enter URL] [Upload PDF]. No navigation required to switch modes. Single submit button. |
| Photo URL validation / preview | Show a small avatar preview when a photo URL is entered so the operator can verify it resolves | LOW | `<img>` with onerror handler in the edit form. If the URL 404s, show a warning inline. Prevents broken avatar display in the public UI. |

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem useful but create disproportionate complexity or undermine existing design decisions.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Real-time log streaming (SSE / WebSocket) | "I want to see the LLM processing each utterance in real-time" | SSE from FastAPI requires keeping a long-lived connection open through PgBouncer transaction-mode pooling. Adds infra complexity (async generator, client EventSource) for marginal value when a single argument parses in under 60 seconds. | Poll `pipeline_runs.status` every 3–5 seconds. Status flips from `running` to `completed/failed` atomically. Operator sees the result without per-utterance streaming. |
| Celery / Redis task queue | "Background workers for robust job execution" | Introduces two new infra components for a tool used by one operator processing ~2–5 arguments per month. PgBouncer transaction mode already constrains async DB access. | Run pipeline steps as synchronous subprocess calls spawned by the FastAPI admin endpoint, with DB status written before and after. If the process crashes, `pipeline_runs.status` stays `running` — operator re-triggers. |
| Bulk import (multiple PDFs at once) | "Save time by uploading a batch" | Each PDF requires sequential ingest → parse → resolve with potential human review between steps. Batching obscures which argument needs attention. Resolve discrepancies are per-argument; batching creates a confusing multi-argument review queue. | Process one argument at a time. Run time per argument is short (~1–3 minutes). No meaningful time saving from batching. |
| Granular role-based access control (RBAC) | "Different people should have different permissions" | Single operator; there is no second user. Adding roles adds schema complexity with zero current benefit. | Simple `ADMIN_USERNAME` + `ADMIN_PASSWORD` env var check. If a second operator ever joins, revisit auth at that milestone. |
| Audit log UI for people edits | "Show a history of every change made" | The `pipeline_runs` table already functions as an append-only audit log for pipeline operations. A separate UI audit trail for people edits requires change-tracking columns or an event sourcing table — significant scope for a single operator. | Pipeline history panel (existing `pipeline_runs` rows) covers the primary audit need. People edits are low-frequency and low-risk. |
| Dashboard with analytics / metrics | "Show me ingestion stats, parse success rates" | Even speaker-neutral metrics (utterances per argument) create editorial-adjacent views. Violates the project's apolitical framing if any per-speaker counts are surfaced. | Plain pipeline run history table — step, status, timestamp. No derived analytics. |
| Fuzzy-match suggestion during resolve review | "Auto-suggest the closest person when a label is unresolved" | Levenshtein / fuzzy matching over the people table adds a query-time dependency. The alias table already handles all recurring Justices after the first run. New advocates are genuinely novel and need human selection, not an algorithmic guess. | Present a dropdown / searchable list of all people records. Operator picks explicitly; no algorithmic ranking. |
| Inline utterance text editing | "Let me fix a transcription error in the transcript" | Utterances are derived from the immutable PDF source. Editing them violates the "all derived data can be regenerated" principle (PIPE-02). Re-parse produces new utterance rows; the old run is preserved per PIPE-11. | If a transcript has a known parse error, re-run parse. The `pipeline_run_id` + max-run filter design was built to support exactly this. |
| Public registration / invite system | "Let a researcher or colleague log in" | No second operator currently exists. Building an invitation or registration system is premature and introduces user management scope. | Hard-code single operator credentials in env vars. |

---

## Feature Dependencies

```
[Auth / session cookie]
    └──required by──> [All /admin/* routes]

[Pipeline trigger — URL input or file upload]
    └──required by──> [Ingest step execution]
                          └──required by──> [Parse step execution]
                                                └──required by──> [Resolve step execution]
                                                                      └──required by──> [Inline participant review]

[People directory list]
    └──enhances──> [Inline participant review — "Create new person" flow]

[Alias auto-save during review]
    └──requires──> [Resolve step execution]
    └──enhances──> [Future runs auto-advance without review]

[Pipeline run history]
    └──required by──> [Resumable state — operator returns to interrupted run]
```

### Dependency Notes

- **Auth required by all admin routes:** `hooks.server.ts` must run before any `+page.server.ts` load function in the `/admin/*` tree. A `+layout.server.ts` at `src/routes/admin/` ensures hooks fire even for routes with no server-load file.
- **Ingest required before parse:** Parse reads the PDF path written by ingest (`pipeline_runs.pdf_path`). There is no way to parse an argument that has not been ingested.
- **Parse required before resolve:** Resolve reads utterance rows written by parse, filtered by `pipeline_run_id`. Attempting resolve with no parse run is a schema-level impossibility.
- **Resolve required before participant review:** `argument_participants.person_id` is only populated after resolve runs. The review UI has nothing to show until resolve has run at least once.
- **People directory enhances participant review:** If a new speaker does not exist in `people`, the operator must create them. The "Create new person" inline form can call the same backend logic as the people editor, avoiding duplication.

---

## MVP Definition

### Launch With (v1.1)

Minimum viable set that makes the pipeline operable from a browser.

- [ ] Auth — login form, session cookie, `hooks.server.ts` guard for `/admin/*`
- [ ] Pipeline trigger — URL input tab + file upload tab in one widget
- [ ] Step-by-step status display — three cards (Ingest / Parse / Resolve), each with status badge, error text on failure
- [ ] Auto-advance when no discrepancies — poll `pipeline_runs.status`; advance stepper to completed automatically
- [ ] Pause-for-review when discrepancies — render `argument_participants WHERE person_id IS NULL`; operator assigns person or creates new
- [ ] Alias auto-save during review — checkbox on each assignment; writes to `speaker_alias`
- [ ] People directory list — scrollable table, full_name / role / photo present/absent
- [ ] People edit form — fields: full_name, role_id, bio text, photo_url, tenure start/end dates

### Add After Validation (v1.1 polish, same milestone)

Features to add once core pipeline runner and people editor are working.

- [ ] Unresolved count badge — show on the resolve step card before operator clicks into review; requires only a COUNT query
- [ ] Photo URL preview in people edit form — `<img>` with onerror; one-line addition to the form
- [ ] Pipeline run history panel — list `pipeline_runs` for an argument; useful for diagnosing re-runs

### Future Consideration (v1.2+)

- [ ] Automated enrichment (Oyez / FJC API) — already marked Out of Scope in PROJECT.md for v1.1
- [ ] Batch ingestion — only warranted if the operator is processing >10 arguments per week

---

## Feature Prioritization Matrix

| Feature | Operator Value | Implementation Cost | Priority |
|---------|---------------|---------------------|----------|
| Auth + session cookie | HIGH | LOW | P1 |
| Pipeline trigger (URL + upload) | HIGH | LOW–MEDIUM | P1 |
| Step-by-step status display | HIGH | MEDIUM | P1 |
| Auto-advance / pause-for-review | HIGH | MEDIUM | P1 |
| Inline participant review + alias save | HIGH | MEDIUM | P1 |
| People directory list | HIGH | LOW | P1 |
| People edit form | HIGH | LOW | P1 |
| Unresolved count badge | MEDIUM | LOW | P2 |
| Photo URL preview | LOW | LOW | P2 |
| Pipeline run history panel | MEDIUM | LOW | P2 |
| "Create new person" inline during review | MEDIUM | MEDIUM | P2 |
| Batch ingestion | LOW | HIGH | P3 |
| SSE real-time log streaming | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when core is stable
- P3: Nice to have, future consideration

---

## Competitor / Reference Pattern Analysis

This is an internal operator tool with no direct competitors. The closest analogous patterns are:

| Pattern | Reference | Our Approach |
|---------|-----------|--------------|
| Pipeline step stepper | Jenkins Blue Ocean — stage nodes with color-coded status | Three named cards (Ingest / Parse / Resolve) with status badges; simpler because steps are always sequential, never parallel |
| Resolve discrepancy review | CMS import review queues (WordPress importer, Contentful import review) — flagged items shown in a list with action buttons | Inline list of unresolved `argument_participants`; assign person from dropdown or create new; dismiss/save per row |
| Entity directory editor | Django Admin, EasyAdmin — paginated list with row-level edit | Paginated table with edit button per row; full edit form on click (not inline table editing — too fiddly for date fields and multiline bio text) |
| File + URL dual input | GitHub new repo — tab between "Import" (URL) and "Create" (form) | Tabs within a single form widget: [Paste URL] [Upload File]; submit button shared |
| Auth guard in SvelteKit | `hooks.server.ts` + `event.locals` pattern | `sequence()` in `hooks.server.ts`; admin session in `event.locals.admin`; `+layout.server.ts` at `/admin/` to force hook execution for all nested routes |

---

## Sources

- UI patterns for async workflows: https://blog.logrocket.com/ux-design/ui-patterns-for-async-workflows-background-jobs-and-data-pipelines/
- Background task progress UI: https://appmaster.io/blog/background-tasks-progress-ui
- Jenkins Blue Ocean pipeline run details view: https://www.jenkins.io/doc/book/blueocean/pipeline-run-details/
- File upload UX best practices: https://uploadcare.com/blog/file-uploader-ux-best-practices/
- SvelteKit hooks middleware and auth guards: https://teta.so/blog/sveltekit-hooks-middleware-auth-guards
- Authentication in Svelte using cookies: https://blog.logrocket.com/authentication-svelte-using-cookies/
- Designing for the operator experience: https://medium.com/statuscode/designing-for-the-operator-experience-21b63db8143
- CRUD admin UI design guide: https://medium.com/@tanya_anokhina/designers-guide-to-user-data-and-crud-4e53f7c5150d
- Review queue patterns: https://docs.amigo.ai/data/review-queue

---

*Feature research for: Operator admin interface — SCOTUS Chat v1.1*
*Researched: 2026-06-15*
