---
phase: 28-dashboard
reviewed: 2026-07-11T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - api/routers/admin.py
  - api/schemas/admin_dashboard.py
  - api/services/admin_arguments.py
  - api/services/admin_jobs.py
  - api/services/admin_people.py
  - api/tests/test_admin_dashboard_routes.py
  - api/tests/test_admin_dashboard_stats.py
  - app/src/lib/components/StatCard.svelte
  - app/src/routes/admin/+page.server.ts
  - app/src/routes/admin/+page.svelte
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 28: Code Review Report

**Reviewed:** 2026-07-11
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the seven new dashboard aggregation endpoints (`/arguments/stats`, `/arguments/recent-drafts`, `/people/stats`, `/people/incomplete`, `/people/tenure-gaps`, `/jobs/stats`, `/utterances/count`), their backing service functions in `admin_arguments.py` / `admin_jobs.py` / `admin_people.py`, the new `admin_dashboard.py` schema module, and the new dashboard frontend (`StatCard.svelte`, `+page.server.ts`, `+page.svelte`), plus the two new test files.

The route-ordering discipline (literal `/stats`, `/incomplete`, `/tenure-gaps`, `/recent-drafts` routes registered before their `{id}`-parameterized siblings) is correctly applied in every case, matching the project's established `check-duplicate` precedent — I traced the router file end-to-end to confirm this rather than trusting the inline comments. All new routes correctly inherit router-level admin-token auth; no new route bypasses it. The apolitical constraint (no derived-insight/outcome fields) is honored in the new schemas. No SQL injection, XSS, hardcoded-secret, or auth-bypass issues found in the diff, and no crash/data-loss defect was found in the new aggregation logic itself (status filtering, 30-day window math, and enum handling were all traced and check out against `ArgumentStatusEnum`'s four actual values).

Two quality/maintainability issues are worth fixing (WARNING) and two are worth noting for awareness (INFO). Nothing in this diff rises to the Critical bar.

## Warnings

### WR-01: StatCard.svelte's shared props are untyped, unlike every other component in the codebase

**File:** `app/src/lib/components/StatCard.svelte:10`
**Issue:** `let { title, children } = $props();` has no type annotation. This is the first shared card component in the codebase (per its own header comment) and is meant to be the template other admin cards will copy — but every other component added to `app/src/lib/components/` types its `$props()` destructure (`TopNav.svelte`, `MobileNavBar.svelte`, `SectionRail.svelte`, `DocketPillInput.svelte`, `CreatePersonPopover.svelte`, `FailedStepGuidance.svelte`, `ResolveCard.svelte`, `RunStatusCard.svelte`, `ArgumentDetailsCard.svelte` all declare an inline object type or a named `XxxProps` interface). `StatCard` breaks that pattern, and specifically loses the `Snippet` type for `children` — a future caller that forgets to pass the `children` snippet gets no compile-time error, only a runtime failure at `{@render children()}` (line 31) when `children` is `undefined`.
**Fix:**
```svelte
<script lang="ts">
	import type { Snippet } from 'svelte';

	let { title, children }: { title: string; children: Snippet } = $props();
</script>
```

### WR-02: New DB-gated test fixture mixes manual rollback with an active `session.begin()` context, echoing the project's own ESCALATED test-leak concern

**File:** `api/tests/test_admin_dashboard_stats.py:58-71`
**Issue:**
```python
async with AsyncSessionLocal() as session:
    async with session.begin():
        yield session
        await session.rollback()
```
`session.rollback()` is called manually while still inside the `async with session.begin():` block. `rollback()` ends the transaction that `begin()` is tracking; when the `async with session.begin():` block itself then exits normally afterward, it will attempt its own commit/close on a transaction that has already been torn down. In this specific file the risk is muted because none of the seven tested service functions call `db.commit()` internally (all are read-only aggregations), so there is nothing left to persist after the manual rollback — but this is the exact same fixture shape used across `test_admin_jobs_phase25.py`, `test_admin_jobs_stats.py`, `test_admin_jobs_list.py`, `test_admin_jobs_source.py`, `test_argument_oyez_field.py`, and `test_admin_people_phase25.py`, and the project's own memory log records an ESCALATED incident of exactly this class ("tests leak real Person/Argument rows into shared dev DB, broke import-justices once"). This new file seeds real `Person`/`Argument`/`CourtTenure`/`ArgumentParticipant` rows using the same pattern (e.g. `test_get_tenure_gap_justices_combined_top_five` seeds 6 Justices with tenure/argument rows), so it is propagating a transaction-management pattern already flagged as risky rather than using the safer idiom.
**Fix:** Don't call `rollback()` while `session.begin()`'s context manager is still open — let the `finally` block own the rollback instead:
```python
@pytest_asyncio.fixture
async def db_session():
    from api.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
```
This also removes the redundant `session.begin()` wrapper (AsyncSession auto-begins on first use), eliminating the double transaction-teardown path entirely. Worth applying to the other five files that share this pattern in a follow-up, not just this one.

## Info

### IN-01: Seven near-identical try/catch fetch blocks in +page.server.ts could be extracted to a shared helper

**File:** `app/src/routes/admin/+page.server.ts:56-162`
**Issue:** Each of the seven dashboard data sources repeats the same 10-12 line shape (declare a typed default, `try { fetch → if res.ok assign : else console.error } catch console.error`). This mirrors an existing precedent (`admin/pipeline/[job_id]/+page.server.ts`) so it's not a new anti-pattern, but at 7 repetitions (vs. fewer in the precedent file) the duplication is now large enough that a copy-paste error in one block (wrong header, wrong URL, forgotten `res.ok` check) is easy to introduce and easy to miss in review.
**Fix:** Extract a small generic helper, e.g.:
```ts
async function fetchOrDefault<T>(fetchFn: typeof fetch, url: string, fallback: T): Promise<T> {
	try {
		const res = await fetchFn(url, { headers: { 'X-Admin-Token': ADMIN_TOKEN } });
		if (res.ok) return await res.json();
		console.error(`[load] ${url} fetch failed: returned ${res.status}`);
	} catch (err) {
		console.error(`[load] ${url} fetch threw:`, err instanceof Error ? err.message : String(err));
	}
	return fallback;
}
```
and call it seven times instead of hand-rolling each block.

### IN-02: Dashboard header counts and their "Needs Attention" sub-lists are drawn from independent, non-snapshotted queries

**File:** `api/services/admin_people.py:325-358`, `api/routers/admin.py:680-724`, `app/src/routes/admin/+page.server.ts:71-84,134-147`
**Issue:** `PeopleStats` (`get_people_stats`) and the "People" Needs Attention sub-list (`get_incomplete_people`) each independently call `list_people(db)` — a full, unfiltered directory scan with its own tenure/argument-count prefetch queries — and the two are fetched via two separate HTTP round-trips from `+page.server.ts` with no shared transaction or snapshot. The same is true for `get_tenure_gap_justices` vs. the Justices sub-list. Under concurrent edits (an operator updating a Person record in another tab while the dashboard loads), the top-of-card total and the sub-list rows can legitimately disagree for the duration of one page load. This is a low-probability issue for a single-operator internal tool and is explicitly out of scope as a performance concern, but it's worth being aware of if the dashboard is ever used by multiple concurrent operators — a single combined aggregation endpoint (or read-committed snapshot) would remove the possibility entirely.
**Fix:** No action required now; if multi-operator concurrent use becomes common, consider a single `/api/admin/dashboard` endpoint that computes all seven values inside one transaction/snapshot instead of three independent `list_people()` calls plus four independent single-purpose queries.

---

_Reviewed: 2026-07-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
